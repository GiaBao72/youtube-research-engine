# YouTube Research Engine

Tool phân tích video YouTube phục vụ research nội dung. Có CLI và web UI đơn giản để chạy local.

## Tính năng hiện có
- Phân tích 1 video YouTube từ URL hoặc video ID
- Batch analyze nhiều video trong 1 lệnh
- Lấy transcript/subtitle khi có
- Lấy metadata video
  - ưu tiên `yt-dlp` nếu có
  - fallback qua YouTube oEmbed nếu máy chưa cài `yt-dlp`
- Fallback analysis nếu LLM/API lỗi hoặc trả JSON không hợp lệ
- Xuất report Markdown + JSON

## Cấu trúc
- `src/youtube_research/` mã nguồn chính
- `outputs/raw/` dữ liệu thô
- `outputs/reports/` báo cáo markdown
- `.env.example` cấu hình mẫu

## Cài đặt
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# sửa .env với API key/model/base URL của bạn
```

## Windows
Nếu bạn chạy trên Windows, xem hướng dẫn riêng tại:
- `README_WINDOWS.md`

Có sẵn file tiện ích:
- `start_local.bat`
- `start_web.bat`

## Cấu hình
```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://llm.chiasegpu.vn/v1
OPENAI_MODEL=cx/gpt-5.4
YRE_LANGUAGE=vi
```

## Chạy 1 video
```bash
./run.sh analyze "https://www.youtube.com/watch?v=VIDEO_ID"
```

Hoặc:
```bash
source ../.venv/bin/activate
PYTHONPATH=src python -m youtube_research.cli analyze "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Chạy nhiều video
```bash
./run.sh batch \
  "https://www.youtube.com/watch?v=VIDEO_ID_1" \
  "https://www.youtube.com/watch?v=VIDEO_ID_2"
```

## Giao diện web
Cài dependencies rồi chạy:
```bash
source ../.venv/bin/activate
pip install -r requirements.txt
./run-web.sh
```

Mở trình duyệt tại:
- `http://localhost:8787`
- hoặc `http://SERVER_IP:8787`

Tính năng web hiện tại:
- nhập nhiều URL, mỗi dòng 1 video
- bấm chạy và xem kết quả ngay
- mở nhanh report Markdown / raw JSON / analysis JSON

## Output
Mỗi video sẽ tạo ra:
- `outputs/raw/<video_id>.json`
- `outputs/raw/<video_id>.analysis.json`
- `outputs/reports/<video_id>.md`

## Ghi chú
- Ưu tiên transcript YouTube có sẵn.
- Nếu transcript không có, tool sẽ báo rõ lỗi cho video đó.
- Nếu metadata không lấy được từ `yt-dlp`, tool sẽ fallback sang oEmbed.
- Nếu LLM lỗi, report vẫn được sinh ở chế độ `Fallback` để không gãy pipeline.
- `duration` có thể vẫn thiếu với một số video nếu YouTube chặn watch-page scraping.
- Chưa gồm auto-cut video; bản này tập trung vào research.
