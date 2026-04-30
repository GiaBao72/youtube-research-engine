# YouTube Research Engine - Windows Guide

Hướng dẫn nhanh để chạy trên Windows.

## 1) Yêu cầu
- Windows 10/11
- Python 3.10+
- Khi cài Python, nhớ tick **Add Python to PATH**

## 2) Clone repo
```powershell
git clone https://github.com/GiaBao72/youtube-research-engine.git
cd youtube-research-engine
```

## 3) Chạy web UI nhanh nhất
Chỉ cần double-click:
- `start_web.bat`

File này sẽ tự:
- tạo `.venv` nếu chưa có
- cài dependencies
- tạo `.env` từ `.env.example` nếu thiếu
- chạy web UI tại `http://127.0.0.1:8787`

## 4) Chạy chuẩn bị local CLI
Double-click:
- `start_local.bat`

File này sẽ chuẩn bị môi trường local cho bạn.

Sau đó có thể chạy CLI bằng PowerShell/CMD:
```powershell
.venv\Scripts\python -m youtube_research.cli analyze "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 5) Cấu hình API key
Mở file `.env` và điền:
```env
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://llm.chiasegpu.vn/v1
OPENAI_MODEL=cx/gpt-5.4
YRE_LANGUAGE=vi
```

Nếu không có `OPENAI_API_KEY`, app có thể:
- lỗi ở chế độ phân tích model
- hoặc rơi về fallback mode tùy flow

## 6) URL sau khi chạy
- Local: `http://127.0.0.1:8787`
- LAN thường là: `http://<ip-may-ban>:8787`

## 7) Update code sau này
Trong thư mục repo:
```powershell
git pull origin main
.venv\Scripts\pip install -r requirements.txt
```

## 8) Production export
Sau khi analyze video, repo sẽ tự sinh thêm package để nối sang MoneyPrinter / subtitle / ffmpeg tại:
- `outputs\production\<video_id>.production.json`
- `outputs\production\<video_id>.title.txt`
- `outputs\production\<video_id>.hook.txt`
- `outputs\production\<video_id>.script.txt`

Có thể export lại riêng bằng:
```powershell
.venv\Scripts\python -m youtube_research.cli export-production VIDEO_ID
```

## 9) Build pipeline bundle
Sinh bundle hoàn chỉnh cho stack ngoài:
```powershell
.venv\Scripts\python -m youtube_research.cli build-pipeline VIDEO_ID
```
Hoặc:
- `build_pipeline.bat VIDEO_ID`

Bundle sẽ nằm ở:
- `outputs\pipeline\<video_id>\`

Trong đó có:
- `moneyprinter.input.json`
- `subtitle.input.json`
- `finalize.input.json`
- `commands.json`
- `README.txt`

## 8) Nếu lỗi thường gặp
### Không tìm thấy Python
- cài lại Python
- tick `Add Python to PATH`

### Port 8787 đang bận
- tắt instance cũ
- hoặc đổi port trong `src/youtube_research/web.py`

### Thiếu module
- chạy lại `start_web.bat`
- hoặc:
```powershell
.venv\Scripts\pip install -r requirements.txt
```
