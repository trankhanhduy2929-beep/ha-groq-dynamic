import logging
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, CONF_API_KEY, CONF_MODEL, CONF_MAX_TOKENS, CONF_TEMPERATURE,
    DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE, BASE_URL
)

_LOGGER = logging.getLogger(__name__)

async def validate_api_key(session, api_key):
    """Validate the API key and fetch available models."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with session.get(f"{BASE_URL}/models", headers=headers) as response:
            if response.status != 200:
                _LOGGER.error("Groq API Error: %s", await response.text())
                return None
            data = await response.json()
            # Trả về danh sách ID của các model
            return [model["id"] for model in data.get("data", [])]
    except Exception as e:
        _LOGGER.exception("Connection error")
        return None

class GroqConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Groq Dynamic."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            models = await validate_api_key(session, user_input[CONF_API_KEY])
            
            if models:
                # Lưu danh sách model vào data để dùng sau này (hoặc chỉ lưu key)
                return self.async_create_entry(
                    title="Groq AI", 
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_MODEL: models[0] if models else "llama3-8b-8192" 
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
    """Handle options flow to change Model dynamically."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Lấy lại danh sách model mới nhất mỗi khi mở cấu hình
        api_key = self.config_entry.data.get(CONF_API_KEY)
        session = async_get_clientsession(self.hass)
        models = await validate_api_key(session, api_key)
        
        if not models:
            models = [self.config_entry.options.get(CONF_MODEL, "llama3-8b-8192")]

        current_model = self.config_entry.options.get(CONF_MODEL, self.config_entry.data.get(CONF_MODEL))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_MODEL, default=current_model): vol.In(models),
                vol.Optional(CONF_MAX_TOKENS, default=self.config_entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)): int,
                vol.Optional(CONF_TEMPERATURE, default=self.config_entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)): float,
            }),
        )
