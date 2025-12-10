import logging
import json
import base64
import re
import os
import aiohttp
from homeassistant.components import conversation, camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL

from .const import (
    DOMAIN, CONF_API_KEY, CONF_MODEL, CONF_MAX_TOKENS, CONF_TEMPERATURE,
    DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, BASE_URL
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    agent = GroqConversationEntity(entry)
    async_add_entities([agent])

class GroqConversationEntity(conversation.ConversationEntity):
    """Groq Agent: Text + Camera + URL + Local File."""

    def __init__(self, entry: ConfigEntry):
        self.entry = entry
        self._attr_name = "Groq Agent"
        self._attr_unique_id = entry.entry_id

    @property
    def supported_languages(self) -> list[str] | str:
        return MATCH_ALL

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        hass = self.hass
        api_key = self.entry.data[CONF_API_KEY]
        model = self.entry.options.get(CONF_MODEL, self.entry.data.get(CONF_MODEL))
        user_text = user_input.text
        
        encoded_image = None
        image_source_info = ""

        # --- ƯU TIÊN 1: TÌM URL HOẶC FILE PATH TRONG TEXT ---
        # Regex tìm link http hoặc đường dẫn tuyệt đối bắt đầu bằng /
        # Ví dụ: https://...jpg hoặc /config/www/...jpg
        url_pattern = re.search(r'(https?://\S+|/\S+\.(?:jpg|jpeg|png))', user_text, re.IGNORECASE)
        
        if url_pattern:
            path_or_url = url_pattern.group(0)
            _LOGGER.info(f"Phát hiện ảnh từ nguồn: {path_or_url}")
            
            try:
                # Xử lý nếu là URL Online
                if path_or_url.startswith("http"):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(path_or_url) as resp:
                            if resp.status == 200:
                                image_data = await resp.read()
                                encoded_image = base64.b64encode(image_data).decode("utf-8")
                                image_source_info = " (ảnh từ URL)"
                
                # Xử lý nếu là File Local (trong thư mục config)
                elif path_or_url.startswith("/"):
                    # Kiểm tra file có tồn tại không
                    if os.path.exists(path_or_url):
                        def read_file():
                            with open(path_or_url, "rb") as f:
                                return f.read()
                        image_data = await hass.async_add_executor_job(read_file)
                        encoded_image = base64.b64encode(image_data).decode("utf-8")
                        image_source_info = " (ảnh từ file local)"
                    else:
                        _LOGGER.warning(f"File không tồn tại: {path_or_url}")

            except Exception as e:
                _LOGGER.error(f"Lỗi đọc ảnh từ URL/File: {e}")

        # --- ƯU TIÊN 2: NẾU KHÔNG CÓ URL, TÌM CAMERA ---
        if not encoded_image:
            all_cameras = hass.states.async_all("camera")
            user_text_lower = user_text.lower()
            for cam in all_cameras:
                friendly = cam.attributes.get("friendly_name", "").lower()
                eid = cam.entity_id.lower()
                if (friendly and friendly in user_text_lower) or (eid in user_text_lower):
                    try:
                        image = await camera.async_get_image(hass, cam.entity_id)
                        encoded_image = base64.b64encode(image.content).decode("utf-8")
                        image_source_info = f" (từ camera {cam.entity_id})"
                        break
                    except Exception as e:
                        _LOGGER.error(f"Lỗi chụp camera: {e}")

        # --- TẠO SYSTEM PROMPT ---
        system_prompt = "Bạn là trợ lý AI thông minh."
        if encoded_image:
            system_prompt += f" Người dùng đang gửi kèm một bức ảnh{image_source_info}. Hãy trả lời dựa trên ảnh đó."
        
        # Danh sách thiết bị (giữ nguyên tính năng điều khiển)
        domains = ["light", "switch", "fan", "cover", "climate"]
        states = hass.states.async_all()
        devs = [f"{s.name} ({s.entity_id}): {s.state}" for s in states if s.domain in domains][:50]
        system_prompt += f"\nThiết bị: {', '.join(devs)}"
        system_prompt += '\nNếu cần điều khiển, trả về JSON: {"domain": "...", "service": "...", "target": ["..."], "response": "..."}'

        # --- GỬI REQUEST ---
        messages = [{"role": "system", "content": system_prompt}]
        if encoded_image:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_text})

        session = async_get_clientsession(hass)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            "temperature": self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        }

        intent_response = intent.IntentResponse(language=user_input.language)

        try:
            async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload) as response:
                if response.status != 200:
                    intent_response.async_set_speech(f"Lỗi API: {response.status}")
                    return conversation.ConversationResult(response=intent_response)
                
                data = await response.json()
                content = data["choices"][0]["message"]["content"]

                # Xử lý JSON điều khiển
                if "{" in content and "}" in content:
                    try:
                        json_str = content[content.find('{'):content.rfind('}')+1]
                        cmd = json.loads(json_str)
                        if "domain" in cmd:
                            await hass.services.async_call(cmd["domain"], cmd["service"], {"entity_id": cmd["target"]})
                            content = cmd.get("response", "Đã thực hiện.")
                    except:
                        pass
                
                intent_response.async_set_speech(content)
                return conversation.ConversationResult(response=intent_response)
        except Exception as e:
            intent_response.async_set_speech(f"Lỗi: {e}")
            return conversation.ConversationResult(response=intent_response)
