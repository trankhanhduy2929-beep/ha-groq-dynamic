# Groq Dynamic AI for Home Assistant

Integration cho phép tích hợp Groq Cloud API vào Home Assistant với khả năng:
- **Dynamic Model**: Tự động cập nhật danh sách model mới nhất từ Groq (Llama 3, Mixtral...).
- **Device Control**: Điều khiển thiết bị thông minh (đèn, quạt, rèm...) bằng ngôn ngữ tự nhiên tiếng Việt.
- **Auto Filter**: Tự động lọc bỏ các model không hỗ trợ chat (TTS/Audio).

## Cài đặt qua HACS

1. Vào HACS > Integrations > Menu (3 chấm) > Custom repositories.
2. Dán link repo này vào: `https://github.com/trankhanhduy2929-beep/ha-groq-dynamic`
3. Chọn Category: **Integration**.
4. Nhấn Add, sau đó tìm "Groq Dynamic AI" và cài đặt.
5. Khởi động lại Home Assistant.

## Cấu hình

1. Vào Settings > Devices & Services > Add Integration > Tìm "Groq AI".
2. Nhập API Key từ [Groq Console](https://console.groq.com)."# ha-groq-dynamic" 
