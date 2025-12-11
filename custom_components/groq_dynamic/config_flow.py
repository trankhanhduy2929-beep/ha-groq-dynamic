import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_API_KEY, CONF_MODEL, BASE_URL

_LOGGER = logging.getLogger(__name__)

# Hàm kiểm tra API Key có hoạt động không
async def validate_api_key(session, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        # Gọi thử API list models để check key
        async with session.get(f"{BASE_URL}/models", headers=headers) as response:
            if response.status != 200:
                return None
            data = await response.json()
            # Lọc model text để tránh chọn nhầm
            valid_models = []
            for model in data.get("data", []):
                mid = model["id"].lower()
                if "whisper" not in mid and "tts" not in mid:
                    valid_models.append(model["id"])
            return valid_models
    except Exception:
        return None

class GroqConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Xử lý luồng cài đặt ban đầu."""
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
                        CONF_MODEL: models[0] # Mặc định chọn model đầu tiên
                    }
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GroqOptionsFlowHandler(config_entry)

class GroqOptionsFlowHandler(config_entries.OptionsFlow):
    """Xử lý luồng cấu hình (nút Configure)."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Lấy lại list model mỗi khi bấm cấu hình
        api_key = self.config_entry.data.get(CONF_API_KEY)
        session = async_get_clientsession(self.hass)
        models = await validate_api_key(session, api_key)
        
        if not models:
            models = ["llama-3.3-70b-versatile", "llama-3.2-11b-vision-preview"]

        current_model = self.config_entry.options.get(CONF_MODEL, self.config_entry.data.get(CONF_MODEL))
        if current_model not in models:
            current_model = models[0]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_MODEL, default=current_model): vol.In(models),
            }),
        )