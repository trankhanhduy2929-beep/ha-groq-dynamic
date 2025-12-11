import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    DOMAIN, CONF_API_KEY, CONF_MODEL, CONF_MAX_TOKENS, CONF_TEMPERATURE,
    CONF_System_PROMPT, CONF_SELECTED_ENTITIES,
    DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_SYSTEM_PROMPT, BASE_URL
)

_LOGGER = logging.getLogger(__name__)

async def validate_api_key(session, api_key):
    """Validate API Key & Filter Chat Models."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with session.get(f"{BASE_URL}/models", headers=headers) as response:
            if response.status != 200:
                return None
            data = await response.json()
            valid_models = []
            for model in data.get("data", []):
                mid = model["id"].lower()
                # Lọc bỏ model âm thanh
                if "whisper" not in mid and "tts" not in mid and "stt" not in mid:
                    valid_models.append(model["id"])
            return valid_models
    except Exception:
        return None

class GroqConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            models = await validate_api_key(session, user_input[CONF_API_KEY])
            if models:
                return self.async_create_entry(
                    title="Groq AI",
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_MODEL: models[0]
                    }
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GroqOptionsFlowHandler(config_entry)

class GroqOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        # SỬA LỖI TẠI ĐÂY: Không dùng self.config_entry nữa
        # Đổi tên thành self.entry để tránh xung đột với HA Core
        self.entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Cập nhật các dòng dưới dùng self.entry thay vì self.config_entry
        api_key = self.entry.data.get(CONF_API_KEY)
        session = async_get_clientsession(self.hass)
        models = await validate_api_key(session, api_key)
        if not models:
            models = ["llama-3.3-70b-versatile", "llama-3.2-11b-vision-preview"]

        # Lấy giá trị hiện tại
        cur_model = self.entry.options.get(CONF_MODEL, self.entry.data.get(CONF_MODEL))
        if cur_model not in models: cur_model = models[0]
        
        cur_prompt = self.entry.options.get(CONF_System_PROMPT, DEFAULT_SYSTEM_PROMPT)
        cur_entities = self.entry.options.get(CONF_SELECTED_ENTITIES, [])
        cur_tokens = self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        cur_temp = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)

        schema = vol.Schema({
            vol.Required(CONF_MODEL, default=cur_model): vol.In(models),
            
            vol.Optional(CONF_System_PROMPT, default=cur_prompt): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            
            vol.Optional(CONF_SELECTED_ENTITIES, default=cur_entities): EntitySelector(
                EntitySelectorConfig(multiple=True)
            ),

            vol.Optional(CONF_MAX_TOKENS, default=cur_tokens): int,
            vol.Optional(CONF_TEMPERATURE, default=cur_temp): float,
        })

        return self.async_show_form(step_id="init", data_schema=schema)
