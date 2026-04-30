from __future__ import annotations

import html
import json
from pathlib import Path

from flask import Flask, Response, redirect, request, send_file, url_for

from .channels import add_favorite_channel, discover_channels, fetch_channel_videos, load_favorites
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


def _link_if_exists(path: Path, href: str, label: str, button_class: str = 'btn secondary') -> str:
    if not path.exists():
        return ''
    return f'<a class="{button_class}" href="{html.escape(href)}">{html.escape(label)}</a>'


def _existing_artifact_links(paths: list[tuple[Path, str, str, str]]) -> list[str]:
    links = []
    for path, href, label, button_class in paths:
        link = _link_if_exists(path, href, label, button_class)
        if link:
            links.append(link)
    return links


def _result_artifact_groups(result: dict[str, str], raw: dict, report_path: Path, analysis_path: Path, raw_path: Path) -> tuple[list[str], list[str]]:
    video_id = result.get('video_id') or raw.get('video_id') or ''
    production_path = Path(result.get('production_package') or '')
    production_title_path = Path(result.get('production_title') or '')
    production_hook_path = Path(result.get('production_hook') or '')
    production_script_path = Path(result.get('production_script') or '')
    pipeline_dir = Path(result.get('pipeline_bundle_dir') or '')

    primary_links = _existing_artifact_links([
        (report_path, f'/report/{report_path.name}', 'Xem report trong web', 'btn'),
        (report_path, f'/files/reports/{report_path.name}', 'Markdown', 'btn secondary'),
        (production_path, f'/files/production/{production_path.name}', 'Production JSON', 'btn secondary'),
        (production_title_path, f'/files/production/{production_title_path.name}', 'Title TXT', 'btn secondary'),
        (production_hook_path, f'/files/production/{production_hook_path.name}', 'Hook TXT', 'btn secondary'),
        (production_script_path, f'/files/production/{production_script_path.name}', 'Script TXT', 'btn secondary'),
    ])

    secondary_links = _existing_artifact_links([
        (analysis_path, f'/files/raw/{analysis_path.name}', 'Analysis JSON', 'btn secondary'),
        (raw_path, f'/files/raw/{raw_path.name}', 'Raw JSON', 'btn secondary'),
    ])
    if pipeline_dir.exists() and video_id:
        secondary_links.extend(_existing_artifact_links([
            (pipeline_dir / 'README.txt', f'/files/pipeline/{video_id}/README.txt', 'Pipeline README', 'btn secondary'),
            (pipeline_dir / 'commands.json', f'/files/pipeline/{video_id}/commands.json', 'Commands JSON', 'btn secondary'),
            (pipeline_dir / 'moneyprinter.input.json', f'/files/pipeline/{video_id}/moneyprinter.input.json', 'MoneyPrinter Input', 'btn secondary'),
            (pipeline_dir / 'subtitle.input.json', f'/files/pipeline/{video_id}/subtitle.input.json', 'Subtitle Input', 'btn secondary'),
            (pipeline_dir / 'finalize.input.json', f'/files/pipeline/{video_id}/finalize.input.json', 'Finalize Input', 'btn secondary'),
            (pipeline_dir / 'run_moneyprinter.sh', f'/files/pipeline/{video_id}/run_moneyprinter.sh', 'Run MoneyPrinter (.sh)', 'btn secondary'),
            (pipeline_dir / 'run_subtitle.sh', f'/files/pipeline/{video_id}/run_subtitle.sh', 'Run Subtitle (.sh)', 'btn secondary'),
            (pipeline_dir / 'run_finalize.sh', f'/files/pipeline/{video_id}/run_finalize.sh', 'Run Finalize (.sh)', 'btn secondary'),
            (pipeline_dir / 'run_all.sh', f'/files/pipeline/{video_id}/run_all.sh', 'Run All (.sh)', 'btn secondary'),
            (pipeline_dir / 'run_moneyprinter.bat', f'/files/pipeline/{video_id}/run_moneyprinter.bat', 'Run MoneyPrinter (.bat)', 'btn secondary'),
            (pipeline_dir / 'run_subtitle.bat', f'/files/pipeline/{video_id}/run_subtitle.bat', 'Run Subtitle (.bat)', 'btn secondary'),
            (pipeline_dir / 'run_finalize.bat', f'/files/pipeline/{video_id}/run_finalize.bat', 'Run Finalize (.bat)', 'btn secondary'),
            (pipeline_dir / 'run_all.bat', f'/files/pipeline/{video_id}/run_all.bat', 'Run All (.bat)', 'btn secondary'),
        ]))

    return primary_links, secondary_links


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
            'source_url': raw.get('url') or f'https://www.youtube.com/watch?v={raw.get("video_id", raw_path.stem)}',
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
              <a href="/analyze?url={html.escape(item['source_url'])}">Phân tích lại</a>
              <a href="/report/{html.escape(item['report_name'])}">Xem report</a>
              <a href="/files/raw/{html.escape(item['analysis_name'])}">JSON</a>
            </div>
          </div>
        </div>
        ''')
    return '<div class="card"><h2>Gần đây</h2><div class="recent-grid">' + ''.join(cards) + '</div></div>'


def _nav() -> str:
    return '''
    <div class="nav card">
      <a class="nav-link" href="/">Home</a>
      <a class="nav-link" href="/analyze">Analyze</a>
      <a class="nav-link" href="/discover">Khám phá kênh</a>
      <a class="nav-link" href="/favorites">Yêu thích</a>
    </div>
    '''


def _analyze_form(initial_urls: str = '') -> str:
    return f'''
      <div class="card">
        <h1>YouTube Research</h1>
        <p>Nhập 1 hoặc nhiều URL YouTube, mỗi dòng 1 URL. Tool sẽ lấy transcript, phân tích bằng LLM và sinh report Markdown + JSON.</p>
        <form method="post" action="/analyze" id="analyze-form">
          <textarea name="urls" placeholder="https://www.youtube.com/watch?v=iG9CE55wbtY\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ">{html.escape(initial_urls)}</textarea>
          <div class="actions">
            <button type="submit" id="submit-btn">Phân tích ngay</button>
            <span class="hint" id="loading-text"></span>
          </div>
        </form>
      </div>
    '''


def _analyze_form_script() -> str:
    return '''<script>
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
    .wrap {{ max-width: 1160px; margin: 0 auto; padding: 24px 20px 72px; }}
    .card {{ background: rgba(18,25,55,.92); border: 1px solid #253056; border-radius: 20px; padding: 22px; box-shadow: 0 12px 40px rgba(0,0,0,.28); margin-bottom: 18px; }}
    .nav {{ display:flex; gap:10px; padding:14px 18px; position:sticky; top:10px; z-index:10; backdrop-filter: blur(8px); }}
    .nav-link {{ display:inline-block; padding:10px 14px; border-radius:12px; background:#121a38; color:#dbe4ff; text-decoration:none; border:1px solid #27325b; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    h3 {{ margin: 0 0 10px; font-size: 22px; }}
    p {{ color: #aab3cf; line-height: 1.6; }}
    form {{ display: grid; gap: 12px; margin-top: 16px; }}
    textarea, input, select {{ width: 100%; border-radius: 14px; border: 1px solid #33406f; background: #0f1631; color: #fff; padding: 14px; font: inherit; }}
    textarea {{ min-height: 128px; resize: vertical; }}
    button, .btn {{ border: 0; border-radius: 12px; background: #4f46e5; color: white; padding: 12px 18px; font-weight: 600; cursor: pointer; width: fit-content; text-decoration:none; display:inline-block; }}
    .btn.secondary {{ background: #1f2a4d; color: #c7d2fe; }}
    .btn.success {{ background: #0f8a5f; color: #eafff8; }}
    .grid {{ display: grid; gap: 18px; margin-top: 20px; }}
    .result {{ background: #0f1631; border: 1px solid #33406f; border-radius: 16px; padding: 16px; }}
    .result-grid {{ display:grid; grid-template-columns: 280px 1fr; gap: 18px; }}
    .thumb {{ width: 100%; border-radius: 14px; border:1px solid #33406f; background:#0b1020; }}
    .meta {{ display: grid; grid-template-columns: 150px 1fr; gap: 8px 12px; margin: 12px 0 14px; }}
    .label {{ color: #8ea0d9; }}
    .error {{ color: #fca5a5; white-space: pre-wrap; }}
    .ok {{ color:#9ef0c8; }}
    a {{ color: #93c5fd; text-decoration: none; }}
    .summary {{ background:#0b1020; border:1px solid #243052; border-radius:12px; padding:14px; color:#dbe4ff; line-height:1.6; }}
    .actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; align-items:center; }}
    .tag {{ display:inline-block; padding:6px 10px; border-radius:999px; background:#18213f; color:#b8c4f7; font-size:13px; margin:0 8px 8px 0; }}
    .recent-grid, .channel-grid, .fav-grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
    .mini-card, .channel-card, .fav-card {{ display:grid; gap:12px; background:#0f1631; border:1px solid #33406f; border-radius:16px; padding:12px; }}
    .mini-card {{ grid-template-columns: 120px 1fr; }}
    .mini-card img {{ width:120px; height:68px; object-fit:cover; border-radius:10px; }}
    .channel-card img {{ width:100%; max-height:180px; object-fit:cover; border-radius:12px; border:1px solid #33406f; background:#0b1020; }}
    .mini-title, .channel-title, .fav-title {{ font-weight:700; margin-bottom:4px; }}
    .mini-meta, .channel-meta, .fav-meta {{ color:#9eb0e4; font-size:14px; margin-bottom:6px; }}
    .mini-summary, .channel-desc, .fav-note {{ color:#cdd7f7; font-size:14px; line-height:1.45; }}
    .mini-links {{ display:flex; gap:12px; margin-top:8px; font-size:14px; }}
    .topbar {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:14px; }}
    .report {{ background:#0b1020; border:1px solid #243052; border-radius:14px; padding:18px; white-space:pre-wrap; line-height:1.65; color:#dbe4ff; overflow:auto; }}
    .artifact-panel {{ margin-top:16px; border-top:1px solid #243052; padding-top:14px; }}
    .artifact-toggle {{ display:inline-flex; align-items:center; gap:8px; color:#c7d2fe; font-size:14px; cursor:pointer; }}
    .artifact-toggle::marker {{ color:#93c5fd; }}
    .artifact-panel[open] .artifact-toggle {{ color:#e5e7eb; }}
    .artifact-grid {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }}
    .hint {{ font-size:14px; color:#8ea0d9; }}
    @media (max-width: 800px) {{ .result-grid {{ grid-template-columns: 1fr; }} .meta {{ grid-template-columns: 110px 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">{_nav()}{body}</div>
  {script}
</body>
</html>'''


@app.get('/')
def index() -> str:
    body = _analyze_form() + _recent_html()
    return _page(body, _analyze_form_script())


@app.route('/analyze', methods=['GET', 'POST'])
def analyze() -> str:
    raw_urls = request.values.get('urls', '')
    if not raw_urls:
        raw_urls = request.values.get('url', '')
    urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
    if not urls:
        return _page(_analyze_form(raw_urls), _analyze_form_script())

    blocks: list[str] = [
        _analyze_form(raw_urls),
        '<div class="card"><div class="topbar"><h1 style="margin:0">Kết quả phân tích</h1><a class="btn secondary" href="/analyze">← Phân tích tiếp</a></div><div class="grid">',
    ]
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
            primary_links, secondary_links = _result_artifact_groups(result, raw, report_path, analysis_path, raw_path)
            more_artifacts_html = ''
            if secondary_links:
                more_artifacts_html = (
                    '<details class="artifact-panel">'
                    '<summary class="artifact-toggle">More artifacts</summary>'
                    f'<div class="artifact-grid">{"".join(secondary_links)}</div>'
                    '</details>'
                )
            blocks.append(f'''
              <div class="result">
                <div class="result-grid">
                  <div><img class="thumb" src="{html.escape(thumb)}" alt="thumbnail"></div>
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
                    <div class="actions">{''.join(primary_links) or '<span class="hint">Chưa có artifact chính.</span>'}</div>
                    {more_artifacts_html}
                  </div>
                </div>
              </div>
            ''')
        except Exception as exc:
            blocks.append(f'<div class="result"><h3>Lỗi</h3><div class="error"><strong>{html.escape(url)}</strong><br>{html.escape(type(exc).__name__ + ": " + str(exc))}</div></div>')
    blocks.append('</div></div>')
    return _page(''.join(blocks))


@app.get('/discover')
def discover_page() -> str:
    topic = (request.args.get('topic') or '').strip()
    sort_by = (request.args.get('sort_by') or 'relevance').strip()
    channels = []
    error = ''
    if topic:
        try:
            channels = discover_channels(topic, api_key=SETTINGS.youtube_api_key or '', limit=8, sort_by=sort_by)
        except Exception as exc:
            error = f'{type(exc).__name__}: {exc}'

    cards = []
    for ch in channels:
        thumb = ch.get('thumbnail') or ''
        cards.append(f'''
        <div class="channel-card">
          <img src="{html.escape(thumb)}" alt="thumb">
          <div>
            <div class="channel-title">{html.escape(ch.get('name') or 'Unknown')}</div>
            <div class="channel-meta">Subscribers: {html.escape(str(ch.get('subscriber_count') or 'N/A'))} · Videos: {html.escape(str(ch.get('video_count') or 'N/A'))}</div>
            <div class="channel-meta">Relevance score: {html.escape(str(ch.get('relevance_score') or 0))} · Matched videos: {html.escape(str(ch.get('matched_video_count') or 0))}</div>
            <div class="channel-desc">{html.escape(ch.get('description') or '')}</div>
            <div class="summary">Ví dụ video khớp chủ đề: {html.escape(' | '.join(ch.get('sample_video_titles') or []))}</div>
            <div class="actions">
              <a class="btn secondary" href="{html.escape(ch.get('url') or '#')}" target="_blank">Mở kênh</a>
              <form method="post" action="/favorites/add">
                <input type="hidden" name="name" value="{html.escape(ch.get('name') or '')}">
                <input type="hidden" name="url" value="{html.escape(ch.get('url') or '')}">
                <input type="hidden" name="channel_id" value="{html.escape(ch.get('channel_id') or '')}">
                <input type="hidden" name="topic" value="{html.escape(ch.get('topic') or '')}">
                <input type="hidden" name="note" value="Phát hiện từ Discover Channels">
                <button class="btn success" type="submit">Lưu yêu thích</button>
              </form>
            </div>
          </div>
        </div>
        ''')

    result_html = ''
    if error:
        result_html = f'<div class="card"><p class="error">{html.escape(error)}</p></div>'
    elif topic:
        result_html = '<div class="card"><h2>Kết quả</h2><div class="channel-grid">' + ''.join(cards or ['<p class="hint">Không tìm thấy kênh phù hợp.</p>']) + '</div></div>'

    body = f'''
      <div class="card">
        <h1>Khám phá kênh theo chủ đề</h1>
        <p>Nhập niche/chủ đề để tìm các kênh YouTube phù hợp. Hệ thống sẽ tìm video theo chủ đề trước, rồi gom lại thành các kênh liên quan nhất — đỡ bị lệch chỉ vì tên kênh chứa keyword.</p>
        <form method="get" action="/discover">
          <input type="text" name="topic" value="{html.escape(topic)}" placeholder="VD: bóng đá chiến thuật, giáo dục con cái, review sách">
          <select name="sort_by">
            <option value="relevance" {'selected' if sort_by == 'relevance' else ''}>Sắp xếp theo độ liên quan</option>
            <option value="subs" {'selected' if sort_by == 'subs' else ''}>Sắp xếp theo subscriber</option>
          </select>
          <div class="actions">
            <button type="submit">Tìm kênh</button>
            <a class="btn secondary" href="/favorites">Xem yêu thích</a>
          </div>
        </form>
      </div>
      {result_html}
    '''
    return _page(body)


@app.post('/favorites/add')
def favorites_add() -> Response:
    add_favorite_channel(
        project_root=PROJECT_ROOT,
        name=request.form.get('name', ''),
        url=request.form.get('url', ''),
        channel_id=request.form.get('channel_id', ''),
        topic=request.form.get('topic', ''),
        note=request.form.get('note', ''),
        tags=[],
    )
    return redirect(url_for('favorites_page'))


@app.post('/favorites/analyze-channel')
def favorites_analyze_channel() -> str:
    channel_id = (request.form.get('channel_id') or '').strip()
    channel_name = (request.form.get('name') or '').strip()
    limit = int((request.form.get('limit') or '5').strip() or '5')
    order = (request.form.get('order') or 'date').strip() or 'date'
    if not channel_id:
        return _page('<div class="card"><p class="error">Thiếu channel_id để analyze channel.</p></div>')

    try:
        videos = fetch_channel_videos(channel_id, api_key=SETTINGS.youtube_api_key or '', limit=limit, order=order)
    except Exception as exc:
        return _page(f'<div class="card"><p class="error">{html.escape(type(exc).__name__ + ": " + str(exc))}</p></div>')

    results = []
    for item in videos:
        try:
            results.append(run_analyze(SETTINGS, item['url']))
        except Exception as exc:
            results.append({
                'title': item.get('title'),
                'url': item.get('url'),
                'error': f'{type(exc).__name__}: {exc}',
            })

    cards = []
    for item in results:
        if item.get('error'):
            cards.append(f'<div class="result"><div class="error">{html.escape(item.get("title") or item.get("url") or "Unknown")}<br>{html.escape(item["error"])}</div></div>')
        else:
            cards.append(f'''
            <div class="result">
              <div><strong>{html.escape(item.get('video_id') or 'Unknown')}</strong></div>
              <div class="actions">
                <a class="btn secondary" href="/report/{html.escape(Path(item['report']).name)}">Xem report</a>
                <a class="btn secondary" href="/files/raw/{html.escape(Path(item['analysis']).name)}">Analysis JSON</a>
              </div>
            </div>
            ''')

    body = f'''
      <div class="card">
        <div class="topbar">
          <h1 style="margin:0">Analyze channel: {html.escape(channel_name or channel_id)}</h1>
          <a class="btn secondary" href="/favorites">← Quay lại Favorites</a>
        </div>
        <p>Lấy {len(videos)} video từ channel và chạy analyze hàng loạt.</p>
        <div class="grid">{''.join(cards)}</div>
      </div>
    '''
    return _page(body)


@app.get('/favorites')
def favorites_page() -> str:
    items = load_favorites(PROJECT_ROOT)
    cards = []
    for item in items:
        cards.append(f'''
        <div class="fav-card">
          <div>
            <div class="fav-title">{html.escape(item.get('name') or 'Unknown')}</div>
            <div class="fav-meta">{html.escape(item.get('topic') or 'N/A')}</div>
            <div class="fav-note">{html.escape(item.get('note') or '')}</div>
            <div class="actions">
              <a class="btn secondary" href="{html.escape(item.get('url') or '#')}" target="_blank">Mở kênh</a>
            </div>
            <form method="post" action="/favorites/analyze-channel">
              <input type="hidden" name="channel_id" value="{html.escape(item.get('channel_id') or '')}">
              <input type="hidden" name="name" value="{html.escape(item.get('name') or '')}">
              <div class="actions">
                <input type="number" name="limit" value="5" min="1" max="20" style="max-width:120px;">
                <select name="order" style="max-width:180px;">
                  <option value="date">Video mới nhất</option>
                  <option value="viewCount">Nhiều view</option>
                  <option value="relevance">Relevance</option>
                  <option value="title">Title</option>
                </select>
                <button class="btn success" type="submit">Analyze channel</button>
              </div>
            </form>
          </div>
        </div>
        ''')
    body = '<div class="card"><h1>Kênh yêu thích</h1><p>Lưu local tại <code>favorites/channels.json</code>.</p>'
    if items:
        body += '<div class="fav-grid">' + ''.join(cards) + '</div>'
    else:
        body += '<p class="hint">Chưa có kênh nào được lưu.</p>'
    body += '</div>'
    return _page(body)


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
    if kind not in {'raw', 'reports', 'production'}:
        return Response('Invalid file type', status=400)
    if kind == 'raw':
        root = SETTINGS.raw_root
    elif kind == 'reports':
        root = SETTINGS.reports_root
    else:
        root = SETTINGS.production_root
    path = (root / name).resolve()
    if not str(path).startswith(str(root.resolve())) or not path.exists():
        return Response('Not found', status=404)
    return send_file(path)


@app.get('/files/pipeline/<video_id>/<path:name>')
def pipeline_files(video_id: str, name: str) -> Response:
    root = (SETTINGS.pipeline_root / video_id).resolve()
    path = (root / name).resolve()
    if not str(path).startswith(str(root)) or not path.exists():
        return Response('Not found', status=404)
    return send_file(path)


def main() -> None:
    app.run(host='0.0.0.0', port=8787, debug=False)


if __name__ == '__main__':
    main()
