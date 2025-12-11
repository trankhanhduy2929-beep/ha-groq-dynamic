"""Constants for the Groq Dynamic integration."""

DOMAIN = "groq_dynamic"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_System_PROMPT = "system_prompt"
CONF_SELECTED_ENTITIES = "selected_entities"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.6
DEFAULT_SYSTEM_PROMPT = (
    "Bạn là trợ lý nhà thông minh hữu ích. "
    "Hãy trả lời ngắn gọn, thân thiện bằng tiếng Việt."
)

BASE_URL = "https://api.groq.com/openai/v1"
