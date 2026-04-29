from __future__ import annotations

import html
import json
from pathlib import Path

from flask import Flask, Response, request, send_file

from .cli import run_analyze
from .config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = Settings.load(PROJECT_ROOT)
app = Flask(__name__)


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return 'N/A'
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f'{h:02d}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _recent_items(limit: int = 8) -> list[dict]:
    items = []
    for raw_path in sorted(SETTINGS.raw_root.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        if raw_path.name.endswith('.analysis.json'):
            continue
        analysis_path = SETTINGS.raw_root / f'{raw_path.stem}.analysis.json'
        report_path = SETTINGS.reports_root / f'{raw_path.stem}.md'
        try:
            raw = _read_json(raw_path)
            analysis = _read_json(analysis_path) if analysis_path.exists() else {}
        except Exception:
            continue
        items.append({
            'video_id': raw.get('video_id') or raw_path.stem,
            'title': raw.get('title') or raw_path.stem,
            'channel': raw.get('channel') or 'N/A',
            'duration': _format_duration(raw.get('duration')),
            'summary': analysis.get('summary') or '',
            'thumb': f'https://i.ytimg.com/vi/{raw.get("video_id", raw_path.stem)}/hqdefault.jpg',
            'report_name': report_path.name,
            'analysis_name': analysis_path.name,
            'raw_name': raw_path.name,
        })
        if len(items) >= limit:
            break
    return items


def _recent_html() -> str:
    items = _recent_items()
    if not items:
        return ''
    cards = []
    for item in items:
        cards.append(f'''
        <div class="mini-card">
          <img src="{html.escape(item['thumb'])}" alt="thumb">
          <div>
            <div class="mini-title">{html.escape(item['title'])}</div>
            <div class="mini-meta">{html.escape(item['channel'])} · {html.escape(item['duration'])}</div>
            <div class="mini-summary">{html.escape(item['summary'][:140])}{'…' if len(item['summary']) > 140 else ''}</div>
            <div class="mini-links">
              <a href="/report/{html.escape(item['report_name'])}">Xem report</a>
              <a href="/files/raw/{html.escape(item['analysis_name'])}">JSON</a>
            </div>
          </div>
        </div>
        ''')
    return '<div class="card"><h2>Gần đây</h2><div class="recent-grid">' + ''.join(cards) + '</div></div>'


def _page(body: str, script: str = '') -> str:
    return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Research</title>
  <style>
    :root {{ color-scheme: dark; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Inter, system-ui, sans-serif; margin: 0; background: linear-gradient(180deg,#0b1020 0%,#0f172a 100%); color: #e5e7eb; }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 72px; }}
    .hero {{ margin-bottom: 20px; }}
    .card {{ background: rgba(18,25,55,.92); border: 1px solid #253056; border-radius: 20px; padding: 22px; box-shadow: 0 12px 40px rgba(0,0,0,.28); margin-bottom: 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    h3 {{ margin: 0 0 10px; font-size: 22px; }}
    p {{ color: #aab3cf; line-height: 1.6; }}
    form {{ display: grid; gap: 12px; margin-top: 16px; }}
    textarea {{ width: 100%; min-height: 128px; border-radius: 14px; border: 1px solid #33406f; background: #0f1631; color: #fff; padding: 14px; font: inherit; resize: vertical; }}
    button, .btn {{ border: 0; border-radius: 12px; background: #4f46e5; color: white; padding: 12px 18px; font-weight: 600; cursor: pointer; width: fit-content; text-decoration:none; display:inline-block; }}
    .btn.secondary {{ background: #1f2a4d; color: #c7d2fe; }}
    .grid {{ display: grid; gap: 18px; margin-top: 20px; }}
    .result {{ background: #0f1631; border: 1px solid #33406f; border-radius: 16px; padding: 16px; }}
    .result-grid {{ display:grid; grid-template-columns: 280px 1fr; gap: 18px; }}
    .thumb {{ width: 100%; border-radius: 14px; border:1px solid #33406f; background:#0b1020; }}
    .meta {{ display: grid; grid-template-columns: 150px 1fr; gap: 8px 12px; margin: 12px 0 14px; }}
    .label {{ color: #8ea0d9; }}
    .error {{ color: #fca5a5; white-space: pre-wrap; }}
    a {{ color: #93c5fd; text-decoration: none; }}
    code {{ background: #0b1020; padding: 2px 6px; border-radius: 6px; }}
    .summary {{ background:#0b1020; border:1px solid #243052; border-radius:12px; padding:14px; color:#dbe4ff; line-height:1.6; }}
    .actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }}
    .tag {{ display:inline-block; padding:6px 10px; border-radius:999px; background:#18213f; color:#b8c4f7; font-size:13px; margin:0 8px 8px 0; }}
    .recent-grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
    .mini-card {{ display:grid; grid-template-columns: 120px 1fr; gap:12px; background:#0f1631; border:1px solid #33406f; border-radius:16px; padding:12px; }}
    .mini-card img {{ width:120px; height:68px; object-fit:cover; border-radius:10px; }}
    .mini-title {{ font-weight:700; margin-bottom:4px; }}
    .mini-meta {{ color:#9eb0e4; font-size:14px; margin-bottom:6px; }}
    .mini-summary {{ color:#cdd7f7; font-size:14px; line-height:1.45; }}
    .mini-links {{ display:flex; gap:12px; margin-top:8px; font-size:14px; }}
    .topbar {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:14px; }}
    .report {{ background:#0b1020; border:1px solid #243052; border-radius:14px; padding:18px; white-space:pre-wrap; line-height:1.65; color:#dbe4ff; overflow:auto; }}
    .hint {{ font-size:14px; color:#8ea0d9; }}
    @media (max-width: 800px) {{ .result-grid {{ grid-template-columns: 1fr; }} .meta {{ grid-template-columns: 110px 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">{body}</div>
  {script}
</body>
</html>'''


@app.get('/')
def index() -> str:
    body = f'''
      <div class="card hero">
        <h1>YouTube Research</h1>
        <p>Nhập 1 hoặc nhiều URL YouTube, mỗi dòng 1 URL. Tool sẽ lấy transcript, phân tích bằng LLM và sinh report Markdown + JSON.</p>
        <form method="post" action="/analyze" id="analyze-form">
          <textarea name="urls" placeholder="https://www.youtube.com/watch?v=iG9CE55wbtY\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ"></textarea>
          <div class="actions">
            <button type="submit" id="submit-btn">Phân tích ngay</button>
            <span class="hint" id="loading-text"></span>
          </div>
        </form>
      </div>
      {_recent_html()}
    '''
    script = '''<script>
      const form = document.getElementById('analyze-form');
      const btn = document.getElementById('submit-btn');
      const txt = document.getElementById('loading-text');
      if (form) {
        form.addEventListener('submit', () => {
          btn.disabled = true;
          btn.textContent = 'Đang phân tích...';
          txt.textContent = 'Chờ chút, mình đang lấy transcript + gọi model.';
        });
      }
    </script>'''
    return _page(body, script)


@app.post('/analyze')
def analyze() -> str:
    raw_urls = request.form.get('urls', '')
    urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
    if not urls:
        return _page('''<div class="card"><h1>YouTube Research</h1><p class="error">Bạn chưa nhập URL nào.</p><p><a href="/">← Quay lại</a></p></div>''')

    blocks: list[str] = ['<div class="card"><div class="topbar"><h1 style="margin:0">Kết quả phân tích</h1><a class="btn secondary" href="/">← Phân tích tiếp</a></div><div class="grid">']

    for url in urls:
        try:
            result = run_analyze(SETTINGS, url)
            raw_path = Path(result['raw'])
            analysis_path = Path(result['analysis'])
            report_path = Path(result['report'])
            raw = _read_json(raw_path)
            analysis = _read_json(analysis_path)
            thumb = f'https://i.ytimg.com/vi/{raw.get("video_id")}/hqdefault.jpg'
            mode = analysis.get('analysis_mode', 'llm').upper()
            summary = analysis.get('summary', '')
            blocks.append(f'''
              <div class="result">
                <div class="result-grid">
                  <div>
                    <img class="thumb" src="{html.escape(thumb)}" alt="thumbnail">
                  </div>
                  <div>
                    <h3>{html.escape(raw.get('title') or result['video_id'])}</h3>
                    <div>
                      <span class="tag">{html.escape(raw.get('channel') or 'N/A')}</span>
                      <span class="tag">{html.escape(_format_duration(raw.get('duration')))}</span>
                      <span class="tag">Mode: {html.escape(mode)}</span>
                      <span class="tag">Segments: {len(raw.get('transcript', []))}</span>
                    </div>
                    <div class="meta">
                      <div class="label">Video ID</div><div>{html.escape(result['video_id'])}</div>
                      <div class="label">URL</div><div><a href="{html.escape(url)}" target="_blank">{html.escape(url)}</a></div>
                    </div>
                    <div class="summary">{html.escape(summary)}</div>
                    <div class="actions">
                      <a class="btn" href="/report/{html.escape(report_path.name)}">Xem report trong web</a>
                      <a class="btn secondary" href="/files/reports/{html.escape(report_path.name)}">Markdown</a>
                      <a class="btn secondary" href="/files/raw/{html.escape(analysis_path.name)}">Analysis JSON</a>
                      <a class="btn secondary" href="/files/raw/{html.escape(raw_path.name)}">Raw JSON</a>
                    </div>
                  </div>
                </div>
              </div>
            ''')
        except Exception as exc:
            blocks.append(f'''<div class="result"><h3>Lỗi</h3><div class="error"><strong>{html.escape(url)}</strong>\n{html.escape(type(exc).__name__ + ': ' + str(exc))}</div></div>''')

    blocks.append('</div></div>')
    return _page(''.join(blocks))


@app.get('/report/<path:name>')
def report_view(name: str) -> Response | str:
    path = (SETTINGS.reports_root / name).resolve()
    if not str(path).startswith(str(SETTINGS.reports_root.resolve())) or not path.exists():
        return Response('Not found', status=404)
    content = path.read_text(encoding='utf-8')
    body = f'''
      <div class="card">
        <div class="topbar">
          <h1 style="margin:0">{html.escape(name)}</h1>
          <a class="btn secondary" href="/">← Trang chủ</a>
          <a class="btn secondary" href="/files/reports/{html.escape(name)}">Tải .md</a>
        </div>
        <div class="report">{html.escape(content)}</div>
      </div>
    '''
    return _page(body)


@app.get('/files/<kind>/<path:name>')
def files(kind: str, name: str) -> Response:
    if kind not in {'raw', 'reports'}:
        return Response('Invalid file type', status=400)
    root = SETTINGS.raw_root if kind == 'raw' else SETTINGS.reports_root
    path = (root / name).resolve()
    if not str(path).startswith(str(root.resolve())) or not path.exists():
        return Response('Not found', status=404)
    return send_file(path)


def main() -> None:
    app.run(host='0.0.0.0', port=8787, debug=False)


if __name__ == '__main__':
    main()
