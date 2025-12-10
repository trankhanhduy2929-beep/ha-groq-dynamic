# Groq Dynamic AI for Home Assistant

Integration mạnh mẽ tích hợp Groq Cloud API vào Home Assistant, biến ngôi nhà của bạn trở nên thông minh thực sự với tốc độ phản hồi siêu nhanh.

## 🚀 Tính năng nổi bật

* **Dynamic Model:** Tự động cập nhật danh sách model mới nhất từ Groq (Llama 3, Mixtral, Gemma...).
* **Smart Device Control:** Điều khiển thiết bị (đèn, quạt, rèm, điều hòa) bằng ngôn ngữ tự nhiên tiếng Việt.
* **AI Vision:** Hỗ trợ nhìn và mô tả hình ảnh từ 3 nguồn:
    * Camera trong Home Assistant (Snapshot).
    * Đường dẫn ảnh Online (URL).
    * File ảnh cục bộ (Local file).
* **Auto Filter:** Tự động lọc bỏ các model không hỗ trợ chat (TTS/Audio) để tránh lỗi.

## 📦 Cài đặt

### Qua HACS (Khuyên dùng)
1.  Vào HACS > Integrations > Menu (3 chấm góc trên) > **Custom repositories**.
2.  Dán đường dẫn kho lưu trữ này vào: `https://github.com/trankhanhduy2929-beep/ha-groq-dynamic`
    *(Thay `USERNAME` bằng tên tài khoản GitHub của bạn)*
3.  Chọn Category: **Integration**.
4.  Nhấn **Add**, sau đó tìm "Groq Dynamic AI" và cài đặt.
5.  Khởi động lại Home Assistant.

## ⚙️ Cấu hình

1.  Vào **Settings** > **Devices & Services** > **Add Integration** > Tìm "Groq AI".
2.  Nhập **API Key** (Lấy miễn phí tại [console.groq.com](https://console.groq.com)).
3.  **Quan trọng:** Sau khi thêm xong, bấm vào nút **Configure** của integration:
    * Chọn Model:
        * Chọn `llama-3.2-11b-vision-preview` (hoặc model có chữ `vision`) nếu muốn dùng tính năng nhìn ảnh/camera.
        * Chọn `llama-3.3-70b` cho các tác vụ chat thông thường.
    * Chỉnh Max Tokens/Temperature tùy ý.

---

## 💡 Hướng dẫn sử dụng Automation

Bạn có thể sử dụng Groq Agent trong Automation thông qua service `conversation.process`.

1. Điều khiển nhà thông minh (Text-only)
Dùng để ra lệnh bật tắt thiết bị mà không cần logic phức tạp.

```yaml
alias: "Chế độ đi ngủ"
trigger:
  - platform: time
    at: "23:00:00"
action:
  - service: conversation.process
    data:
      agent_id: conversation.groq_agent  # ID Agent Groq của bạn
      text: "Tắt hết đèn trong nhà, khóa cửa và chúc tôi ngủ ngon."
    response_variable: ai_response
  
  - service: notify.mobile_app_iphone
    data:
      message: "{{ ai_response.response.speech.plain.speech }}"


2. Camera Vision (Nhìn và mô tả)
Khi nhắc đến entity_id hoặc tên camera trong câu lệnh, AI sẽ tự động chụp ảnh từ camera đó để phân tích.

Yêu cầu: Phải chọn model Vision (ví dụ: llama-3.2-11b-vision-preview) trong cấu hình.

YAML

alias: "Kiểm tra an ninh cổng trước"
trigger:
  - platform: state
    entity_id: binary_sensor.cong_truoc_motion
    to: "on"
action:
  - service: conversation.process
    data:
      agent_id: conversation.groq_agent
      # Mẹo: Trong câu text PHẢI chứa ID camera (ví dụ: camera.cong_truoc)
      text: "Nhìn vào camera.cong_truoc và cho biết có người lạ hay người quen?"
    response_variable: ket_qua
  
  - service: notify.mobile_app_iphone
    data:
      title: "Phát hiện chuyển động"
      message: "{{ ket_qua.response.speech.plain.speech }}"
      data:
        image: "/api/camera_proxy/camera.cong_truoc"
3. Phân tích ảnh từ Internet (URL)
AI sẽ tự động tải ảnh từ link để đọc nội dung.

YAML

alias: "Đọc bản tin thời tiết"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: conversation.process
    data:
      agent_id: conversation.groq_agent
      text: "Hãy xem ảnh dự báo này và tóm tắt thời tiết hôm nay: [https://example.com/du-bao-thoi-tiet.jpg](https://example.com/du-bao-thoi-tiet.jpg)"
    response_variable: weather_summary
    
  - service: tts.google_translate_say
    data:
      entity_id: media_player.google_home
      message: "{{ weather_summary.response.speech.plain.speech }}"
4. Phân tích ảnh file cục bộ
Dùng cho trường hợp ảnh được lưu trong thư mục /config/www/ hoặc thư mục khác.

YAML

action:
  - service: conversation.process
    data:
      agent_id: conversation.groq_agent
      text: "Mô tả bức ảnh này: /config/www/snapshot_last_motion.jpg"
<<<<<<< HEAD
Tác giả: KHÁNH DUY
=======
Tác giả: KHÁNH DUY
>>>>>>> c601e6fe70626236f70a9da29912fee5c4fbe734

