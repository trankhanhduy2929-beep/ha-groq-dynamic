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
    CONF_System_PROMPT, CONF_SELECTED_ENTITIES,
    DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_SYSTEM_PROMPT, BASE_URL
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    agent = GroqConversationEntity(entry)
    async_add_entities([agent])

class GroqConversationEntity(conversation.ConversationEntity):
    """Groq Agent Ultimate: Vision + Control + Custom Prompt."""

    def __init__(self, entry: ConfigEntry):
        self.entry = entry
        self._attr_name = "Groq Agent"
        self._attr_unique_id = entry.entry_id

    @property
    def supported_languages(self) -> list[str] | str:
        return MATCH_ALL

    async def async_process(self, user_input: conversation.ConversationInput) -> conversation.ConversationResult:
        hass = self.hass
        api_key = self.entry.data[CONF_API_KEY]
        
        # Lấy cấu hình từ Options Flow
        model = self.entry.options.get(CONF_MODEL, self.entry.data.get(CONF_MODEL))
        system_instruction = self.entry.options.get(CONF_System_PROMPT, DEFAULT_SYSTEM_PROMPT)
        selected_entities = self.entry.options.get(CONF_SELECTED_ENTITIES, [])
        
        user_text = user_input.text
        encoded_image = None
        
        # --- 1. XỬ LÝ VISION (URL / FILE / CAMERA) ---
        # A. Tìm URL hoặc File path
        url_pattern = re.search(r'(https?://\S+|/\S+\.(?:jpg|jpeg|png))', user_text, re.IGNORECASE)
        if url_pattern:
            path = url_pattern.group(0)
            try:
                if path.startswith("http"):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(path) as resp:
                            if resp.status == 200:
                                encoded_image = base64.b64encode(await resp.read()).decode("utf-8")
                elif path.startswith("/") and os.path.exists(path):
                     encoded_image = base64.b64encode(await hass.async_add_executor_job(lambda: open(path, "rb").read())).decode("utf-8")
            except Exception as e:
                _LOGGER.error(f"Lỗi đọc ảnh: {e}")

        # B. Nếu không có URL, tìm Camera Entity
        if not encoded_image:
            # Ưu tiên tìm trong selected_entities trước nếu có
            target_cameras = [e for e in selected_entities if e.startswith("camera.")] if selected_entities else []
            if not target_cameras:
                target_cameras = [s.entity_id for s in hass.states.async_all("camera")]
            
            for cam_id in target_cameras:
                state = hass.states.get(cam_id)
                if not state: continue
                # Nếu ID hoặc tên camera có trong câu lệnh
                if cam_id in user_text or (state.name and state.name.lower() in user_text.lower()):
                    try:
                        img = await camera.async_get_image(hass, cam_id)
                        encoded_image = base64.b64encode(img.content).decode("utf-8")
                        break
                    except Exception as e:
                        _LOGGER.error(f"Lỗi chụp camera {cam_id}: {e}")

        # --- 2. XÂY DỰNG CONTEXT THIẾT BỊ ---
        device_states = []
        
        if selected_entities:
            # Nếu người dùng đã chọn thiết bị trong Cấu hình -> Chỉ dùng danh sách này (Tối ưu nhất)
            for entity_id in selected_entities:
                state = hass.states.get(entity_id)
                if state:
                    device_states.append(f"{state.name} ({entity_id}): {state.state}")
        else:
            # Fallback: Nếu không chọn gì, lấy mặc định (giới hạn 50 cái)
            domains = ["light", "switch", "fan", "cover", "climate", "lock"]
            all_states = hass.states.async_all()
            for s in all_states:
                if s.domain in domains:
                    device_states.append(f"{s.name} ({s.entity_id}): {s.state}")
            device_states = device_states[:50]

        devices_str = "\n".join(device_states)

        # --- 3. TẠO PROMPT HOÀN CHỈNH ---
        final_system_prompt = f"""{system_instruction}

[Dữ liệu hiện tại]
{devices_str}

[Quy tắc điều khiển]
Nếu người dùng muốn thay đổi trạng thái thiết bị (Bật/Tắt/Mở/Khóa...), hãy trả về JSON:
{{"domain": "tên_domain", "service": "tên_service", "target": ["entity_id"], "response": "Câu trả lời cho người dùng"}}

Ví dụ: {{"domain": "light", "service": "turn_on", "target": ["light.living_room"], "response": "Đã bật đèn."}}
Nếu không cần điều khiển, hãy trả lời bình thường.
"""

        # --- 4. GỬI API ---
        messages = [{"role": "system", "content": final_system_prompt}]
        
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

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
            "temperature": self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
        }

        session = async_get_clientsession(hass)
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        intent_response = intent.IntentResponse(language=user_input.language)

        try:
            async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload) as response:
                if response.status != 200:
                    err = await response.text()
                    intent_response.async_set_speech(f"Lỗi Groq ({response.status}): {err}")
                    return conversation.ConversationResult(response=intent_response)
                
                data = await response.json()
                content = data["choices"][0]["message"]["content"]

                # Xử lý JSON Output
                try:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        cmd = json.loads(content[json_start:json_end])
                        if "domain" in cmd and "service" in cmd:
                            await hass.services.async_call(
                                cmd["domain"], cmd["service"], 
                                {"entity_id": cmd["target"]}, blocking=True
                            )
                            # Sử dụng câu trả lời từ JSON nếu có
                            content = cmd.get("response", "Đã thực hiện yêu cầu.")
                except Exception as e:
                    _LOGGER.warning(f"Lỗi parse JSON: {e}")

                intent_response.async_set_speech(content)
                return conversation.ConversationResult(response=intent_response)

        except Exception as e:
            intent_response.async_set_speech(f"Lỗi hệ thống: {e}")
            return conversation.ConversationResult(response=intent_response)
