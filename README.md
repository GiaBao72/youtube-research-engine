# YouTube Research Engine

Tool phân tích video YouTube phục vụ research nội dung. Có CLI, Flask web UI, và Streamlit dashboard để chạy local.

## Tính năng hiện có
- Phân tích 1 video YouTube từ URL hoặc video ID
- Batch analyze nhiều video trong 1 lệnh
- Lấy transcript/subtitle khi có
- Lấy metadata video
  - ưu tiên `yt-dlp` nếu có
  - fallback qua YouTube oEmbed nếu máy chưa cài `yt-dlp`
- Fallback analysis nếu LLM/API lỗi hoặc trả JSON không hợp lệ
- Tìm kênh theo chủ đề bằng YouTube Data API
- Lưu kênh yêu thích local
- Index dữ liệu vào DuckDB
- Optional enrich:
  - keyword extraction với KeyBERT
  - semantic similarity với sentence-transformers
  - topic grouping với BERTopic
- Có 2 UI:
  - Flask app cho analyze + discover channels
  - Streamlit dashboard cho library/search dữ liệu đã index

## Cấu trúc
- `src/youtube_research/` mã nguồn chính
- `outputs/raw/` dữ liệu thô
- `outputs/reports/` báo cáo markdown
- `outputs/youtube_research.duckdb` cơ sở dữ liệu local
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
- `start_dashboard.bat`

## Cấu hình
```env
OPENAI_API_KEY=
YOUTUBE_API_KEY=
OPENAI_BASE_URL=https://llm.chiasegpu.vn/v1
OPENAI_MODEL=cx/gpt-5.4
YRE_LANGUAGE=vi
```

- `OPENAI_API_KEY`: dùng cho phân tích video bằng model
- `YOUTUBE_API_KEY`: dùng cho tìm kênh theo chủ đề bằng YouTube Data API

## Chạy 1 video
```bash
./run.sh analyze "https://www.youtube.com/watch?v=VIDEO_ID"
```

Bản hiện tại có thêm lớp **Deep Video Analysis** trong output:
- scores (hook / pacing / shorts potential / clarity / retention potential)
- content drivers
- timeline map
- weak spots
- best cut moments
- rewrite modes (viral / educational / storytelling)

## Chạy nhiều video
```bash
./run.sh batch \
  "https://www.youtube.com/watch?v=VIDEO_ID_1" \
  "https://www.youtube.com/watch?v=VIDEO_ID_2"
```

## Tìm kênh theo chủ đề
```bash
./run.sh discover-channels "bóng đá chiến thuật" --limit 8 --sort-by relevance
```

Có thể đổi cách sắp xếp:
- `--sort-by relevance`
- `--sort-by subs`

Logic hiện tại:
- tìm **video** theo chủ đề trước
- gom các **channel** xuất hiện trong kết quả video
- chấm điểm theo mức độ liên quan + độ phủ kết quả

## Lưu kênh yêu thích
```bash
./run.sh save-channel "BLV Anh Quân" "https://www.youtube.com/channel/UC..." --channel-id "UC..." --topic "bóng đá chiến thuật" --tags "football,tactical" --note "Kênh đáng theo dõi"
```

## Xem danh sách yêu thích
```bash
./run.sh list-favorites
```

## Đưa dữ liệu vào DuckDB
```bash
./run.sh reindex
```

## Tìm video tương tự (nếu có embeddings)
```bash
./run.sh similar-videos VIDEO_ID --limit 5
```

## Xem keywords đã extract
```bash
./run.sh keywords VIDEO_ID
```

## Analyze cả 1 channel
```bash
./run.sh analyze-channel CHANNEL_ID --limit 5 --order date
```

Ví dụ:
- lấy 5 video mới nhất của channel rồi analyze hàng loạt
- mỗi video vẫn sinh raw JSON, analysis JSON, report Markdown, và index vào DuckDB

## Flask web UI
```bash
./run-web.sh
```
Mở:
- `http://localhost:8787`

## Streamlit dashboard
```bash
chmod +x run-dashboard.sh
./run-dashboard.sh
```
Mở URL Streamlit hiện trên terminal.

## Production export cho MoneyPrinter / auto-subtitle / ffmpeg
Mỗi lần `analyze` hoặc `reindex`, repo sẽ tự sinh package production tại:
- `outputs/production/<video_id>.production.json`
- `outputs/production/<video_id>.title.txt`
- `outputs/production/<video_id>.hook.txt`
- `outputs/production/<video_id>.script.txt`

Bạn cũng có thể export lại riêng cho video cũ:
```bash
./run.sh export-production VIDEO_ID
```

Package này chứa:
- input title/hook/script_outline cho MoneyPrinter
- subtitle cues sơ bộ cho auto-subtitle / caption workflow
- gợi ý post-process cho ffmpeg/MoviePy
- best cut moments + visual prompts để dựng short nhanh hơn

## Build pipeline bundle hoàn chỉnh
Từ production package, có thể sinh thêm bundle để chạy stack ngoài:
```bash
./run.sh build-pipeline VIDEO_ID
```
Hoặc:
```bash
./build-pipeline.sh VIDEO_ID
```

Bundle này nằm tại:
- `outputs/pipeline/<video_id>/`

Bao gồm:
- `moneyprinter.input.json`
- `subtitle.input.json`
- `finalize.input.json`
- `commands.json`
- `README.txt`
- `run_moneyprinter.sh` / `run_moneyprinter.bat`
- `run_subtitle.sh` / `run_subtitle.bat`
- `run_finalize.sh` / `run_finalize.bat`
- `run_all.sh` / `run_all.bat`

Ý nghĩa:
- `moneyprinter.input.json` → feed cho MoneyPrinter/ShortGPT
- `subtitle.input.json` → feed cho auto-subtitle/custom caption flow
- `finalize.input.json` → feed cho ffmpeg/MoviePy post-process
- `commands.json` → command mẫu Linux/Windows để chạy từng bước

### Cách dùng thực tế
1. Analyze video trong `youtube-research-engine`
2. Chạy `build-pipeline VIDEO_ID`
3. Lấy file trong `outputs/pipeline/<video_id>/` để:
   - chạy MoneyPrinter tạo video khung
   - chạy auto-subtitle tạo/burn caption
   - chạy ffmpeg finalize video cuối

### Gợi ý đặt repo ngoài
Để command mẫu đỡ phải sửa, có thể đặt ngang hàng:
- `youtube-research-engine/`
- `MoneyPrinter/`
- `auto-subtitle/`

Nếu repo ngoài nằm chỗ khác, chỉ cần sửa lại đường dẫn trong `commands.json`.

## Ghi chú về optional AI enrich
Các tính năng sau phụ thuộc package/model cài được trên máy:
- `sentence-transformers`
- `keybert`
- `bertopic`

Nếu thiếu hoặc lỗi tải model:
- app chính vẫn chạy
- chỉ phần enrich/semantic/topic bị giảm chức năng

## Output
Mỗi video sẽ tạo ra:
- `outputs/raw/<video_id>.json`
- `outputs/raw/<video_id>.analysis.json`
- `outputs/reports/<video_id>.md`
- `outputs/youtube_research.duckdb`
- `favorites/channels.json`
