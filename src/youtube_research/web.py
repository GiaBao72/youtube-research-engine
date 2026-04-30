from __future__ import annotations

import html
import json
from pathlib import Path

from flask import Flask, Response, flash, get_flashed_messages, redirect, request, send_file, url_for

from .channels import add_favorite_channel, discover_channels, fetch_channel_videos, load_favorites
from .cli import run_analyze
from .config import Settings
from .indexing import delete_video_record, load_indexed_videos, update_video_record
from .web_ui import BASE_CSS, flash_stack, nav as render_nav, section_intro


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = Settings.load(PROJECT_ROOT)
app = Flask(__name__)
app.secret_key = 'youtube-research-web'


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


def _recent_items(limit: int = 50) -> list[dict]:
    rows = load_indexed_videos(SETTINGS)
    items = []
    for row in rows[:limit]:
        video_id = row.get('video_id') or ''
        if not video_id:
            continue
        report_path = SETTINGS.reports_root / f'{video_id}.md'
        analysis_path = SETTINGS.raw_root / f'{video_id}.analysis.json'
        raw_path = SETTINGS.raw_root / f'{video_id}.json'
        title = row.get('custom_title') or row.get('title') or video_id
        source_url = row.get('url') or f'https://www.youtube.com/watch?v={video_id}'
        summary = row.get('summary') or ''
        note = row.get('note') or ''
        items.append({
            'video_id': video_id,
            'title': title,
            'channel': row.get('channel') or 'N/A',
            'duration': _format_duration(row.get('duration')),
            'summary': summary,
            'note': note,
            'source_url': source_url,
            'thumb': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
            'report_name': report_path.name,
            'analysis_name': analysis_path.name,
            'raw_name': raw_path.name,
        })
    return items


def _analyzed_videos_table() -> str:
    items = _recent_items()
    if not items:
        return (
            '<section class="card section-card library-card">'
            '<div class="section-head library-head"><div><div class="eyebrow">Library</div><h2>Phân tích gần đây</h2></div>'
            '<p>Danh sách video đã phân tích sẽ hiện ở đây để bạn sửa nhanh hoặc xóa khỏi workspace.</p></div>'
            '<p class="hint">Chưa có video nào được phân tích.</p></section>'
        )

    rows = []
    for item in items:
        summary = html.escape(item['summary'][:140]) + ('…' if len(item['summary']) > 140 else '')
        note = html.escape(item['note']) if item['note'] else 'Chưa có ghi chú riêng.'
        rows.append(f'''
        <tr>
          <td>
            <div class="recent-video recent-video-hero">
              <img src="{html.escape(item['thumb'])}" alt="thumb">
              <div>
                <div class="recent-badges">
                  <span class="table-pill">{html.escape(item['duration'])}</span>
                  <span class="table-pill muted">{html.escape(item['channel'])}</span>
                </div>
                <div class="recent-title">{html.escape(item['title'])}</div>
                <div class="recent-sub">{summary}</div>
              </div>
            </div>
          </td>
          <td>
            <div class="library-meta-block">
              <div class="library-meta-label">Kênh</div>
              <div class="library-meta-value">{html.escape(item['channel'])}</div>
              <div class="library-meta-label">Ghi chú hiện tại</div>
              <div class="recent-note">{note}</div>
            </div>
          </td>
          <td>
            <div class="library-actions-card">
              <div class="quick-links">
                <a class="inline-link strong" href="/analyze?url={html.escape(item['source_url'])}">Mở Analyze</a>
                <a class="inline-link" href="/report/{html.escape(item['report_name'])}">Report</a>
                <a class="inline-link" href="/files/raw/{html.escape(item['analysis_name'])}">JSON</a>
              </div>
              <form class="inline-form library-edit-form" method="post" action="/videos/update">
                <input type="hidden" name="video_id" value="{html.escape(item['video_id'])}">
                <label class="field-label compact">Tên hiển thị</label>
                <input type="text" name="custom_title" value="{html.escape(item['title'])}" placeholder="Tên hiển thị">
                <label class="field-label compact">Ghi chú nội bộ</label>
                <textarea name="note" placeholder="Ghi chú nội bộ">{html.escape(item['note'])}</textarea>
                <div class="table-actions table-actions-split">
                  <button class="btn" type="submit">Lưu thay đổi</button>
                </div>
              </form>
              <form class="inline-form danger-form" method="post" action="/videos/delete" onsubmit="return confirm('Xóa toàn bộ output của video này?');">
                <input type="hidden" name="video_id" value="{html.escape(item['video_id'])}">
                <button class="btn danger ghost-danger" type="submit">Xóa video này</button>
              </form>
            </div>
          </td>
        </tr>
        ''')
    return (
        '<section class="card section-card library-card">'
        '<div class="section-head library-head"><div><div class="eyebrow">Library</div><h2>Phân tích gần đây</h2></div>'
        '<p>Bảng này ưu tiên đọc nhanh, mở lại nhanh, rồi mới tới chỉnh sửa. Mỗi dòng là một workspace video hoàn chỉnh.</p></div>'
        '<div class="table-shell library-shell"><table class="recent-table library-table"><thead><tr><th>Video</th><th>Thông tin</th><th>Quản lý</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></div></section>'
    )


def _recent_html() -> str:
    return _analyzed_videos_table()


def _analyze_form(initial_urls: str = '', title: str = 'Biến video thành research package', intro: str = 'Dán 1 hoặc nhiều URL YouTube, mỗi dòng một URL. Hệ thống sẽ lấy transcript, phân tích nội dung và xuất report cùng production artifacts.') -> str:
    return f'''
      <section class="hero card hero-card">
        <div class="hero-copy">
          <div class="eyebrow">Control room</div>
          <h1>{html.escape(title)}</h1>
          <p>{html.escape(intro)}</p>
          <div class="hero-points">
            <span class="tag soft">Transcript + summary</span>
            <span class="tag soft">Report Markdown</span>
            <span class="tag soft">Production bundle</span>
          </div>
        </div>
        <div class="hero-panel">
          <form method="post" action="/analyze" id="analyze-form">
            <label class="field-label" for="urls">YouTube URLs</label>
            <textarea id="urls" name="urls" placeholder="https://www.youtube.com/watch?v=iG9CE55wbtY\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ">{html.escape(initial_urls)}</textarea>
            <div class="actions hero-actions">
              <button type="submit" id="submit-btn">Phân tích ngay</button>
              <a class="btn secondary" href="/discover">Tìm kênh trước</a>
            </div>
            <span class="hint" id="loading-text"></span>
          </form>
        </div>
      </section>
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


def _page(body: str, script: str = '', active_path: str = '/') -> str:
    flashes = flash_stack(get_flashed_messages(with_categories=True))
    return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Research</title>
  <style>
{BASE_CSS}
  </style>
</head>
<body>
  <div class="wrap">{render_nav(active_path)}{flashes}{body}</div>
  {script}
</body>
</html>'''


@app.get('/')
def index() -> str:
    body = _analyze_form() + _recent_html()
    return _page(body, _analyze_form_script(), active_path='/')


@app.route('/analyze', methods=['GET', 'POST'])
def analyze() -> str:
    raw_urls = request.values.get('urls', '')
    if not raw_urls:
        raw_urls = request.values.get('url', '')
    urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
    if not urls:
        return _page(_analyze_form(raw_urls), _analyze_form_script(), active_path='/analyze')

    blocks: list[str] = [
        _analyze_form(
            raw_urls,
            title='Analyze video và mở gói output',
            intro='Giữ nguyên luồng analyze hiện tại nhưng hiển thị lại dưới giao diện rõ ràng hơn để bạn xem kết quả, mở report và quay lại refine nhanh hơn.',
        ),
        '<section class="section-card card">' + section_intro('Output', 'Kết quả phân tích', 'Card kết quả ưu tiên phần dùng thường xuyên. Link kỹ thuật được gom xuống dưới để tránh rối giao diện.') + '<div class="grid">',
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
                    <div class="actions">
                      {''.join(primary_links) or '<span class="hint">Chưa có artifact chính.</span>'}
                    </div>
                    {more_artifacts_html}
                  </div>
                </div>
              </div>
            ''')
        except Exception as exc:
            blocks.append(f'<div class="result"><h3>Lỗi</h3><div class="error"><strong>{html.escape(url)}</strong><br>{html.escape(type(exc).__name__ + ": " + str(exc))}</div></div>')
    blocks.append('</div></div>')
    return _page(''.join(blocks), active_path='/analyze')


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
            <div class="metric-row">
              <span class="micro-stat">Subscribers: {html.escape(str(ch.get('subscriber_count') or 'N/A'))}</span>
              <span class="micro-stat">Videos: {html.escape(str(ch.get('video_count') or 'N/A'))}</span>
              <span class="micro-stat">Relevance: {html.escape(str(ch.get('relevance_score') or 0))}</span>
              <span class="micro-stat">Matched: {html.escape(str(ch.get('matched_video_count') or 0))}</span>
            </div>
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
        result_html = f'<section class="section-card card"><p class="error">{html.escape(error)}</p></section>'
    elif topic:
        result_html = (
            '<section class="section-card card">'
            + section_intro('Results', 'Kênh phù hợp', 'Danh sách kênh được gom từ các video match tốt nhất với chủ đề bạn vừa tìm.')
            + '<div class="channel-grid">' + ''.join(cards or ['<p class="hint">Không tìm thấy kênh phù hợp.</p>']) + '</div></section>'
        )

    body = f'''
      <section class="hero card hero-card">
        <div class="hero-copy">
          <div class="eyebrow">Discover</div>
          <h1>Khám phá kênh theo chủ đề</h1>
          <p>Nhập niche hoặc topic để tìm các kênh YouTube phù hợp. Hệ thống ưu tiên video match theo chủ đề trước rồi mới gom thành kênh để giảm nhiễu keyword.</p>
          <div class="hero-points">
            <span class="tag soft">Topical relevance</span>
            <span class="tag soft">Channel shortlist</span>
            <span class="tag soft">Save to favorites</span>
          </div>
        </div>
        <div class="hero-panel">
          <form method="get" action="/discover">
            <label class="field-label" for="topic">Chủ đề cần tìm</label>
            <input id="topic" type="text" name="topic" value="{html.escape(topic)}" placeholder="VD: bóng đá chiến thuật, giáo dục con cái, review sách">
            <label class="field-label" for="sort_by">Kiểu sắp xếp</label>
            <select id="sort_by" name="sort_by">
              <option value="relevance" {'selected' if sort_by == 'relevance' else ''}>Sắp xếp theo độ liên quan</option>
              <option value="subs" {'selected' if sort_by == 'subs' else ''}>Sắp xếp theo subscriber</option>
            </select>
            <div class="actions hero-actions">
              <button type="submit">Tìm kênh</button>
              <a class="btn secondary" href="/favorites">Xem yêu thích</a>
            </div>
          </form>
        </div>
      </section>
      {result_html}
    '''
    return _page(body, active_path='/discover')


@app.post('/videos/update')
def videos_update() -> Response:
    video_id = (request.form.get('video_id') or '').strip()
    if video_id:
        update_video_record(
            SETTINGS,
            video_id=video_id,
            custom_title=request.form.get('custom_title', ''),
            note=request.form.get('note', ''),
        )
        flash('Da luu thay doi cho video.', 'success')
    else:
        flash('Khong tim thay video de cap nhat.', 'error')
    return redirect(url_for('index'))


@app.post('/videos/delete')
def videos_delete() -> Response:
    video_id = (request.form.get('video_id') or '').strip()
    if video_id:
        delete_video_record(SETTINGS, video_id)
        flash('Da xoa video khoi workspace.', 'success')
    else:
        flash('Khong tim thay video de xoa.', 'error')
    return redirect(url_for('index'))


@app.post('/favorites/add')
def favorites_add() -> Response:
    name = request.form.get('name', '')
    channel_id = request.form.get('channel_id', '')
    if not channel_id:
        flash('Khong the luu kenh vi thieu channel_id.', 'error')
        return redirect(url_for('discover_page'))
    add_favorite_channel(
        project_root=PROJECT_ROOT,
        name=name,
        url=request.form.get('url', ''),
        channel_id=channel_id,
        topic=request.form.get('topic', ''),
        note=request.form.get('note', ''),
        tags=[],
    )
    flash(f'Da luu kenh yeu thich: {name or channel_id}.', 'success')
    return redirect(url_for('favorites_page'))


@app.post('/favorites/analyze-channel')
def favorites_analyze_channel() -> str:
    channel_id = (request.form.get('channel_id') or '').strip()
    channel_name = (request.form.get('name') or '').strip()
    limit = int((request.form.get('limit') or '5').strip() or '5')
    order = (request.form.get('order') or 'date').strip() or 'date'
    if not channel_id:
        return _page('<div class="card"><p class="error">Thiếu channel_id để analyze channel.</p></div>', active_path='/favorites')

    try:
        videos = fetch_channel_videos(channel_id, api_key=SETTINGS.youtube_api_key or '', limit=limit, order=order)
    except Exception as exc:
        return _page(f'<div class="card"><p class="error">{html.escape(type(exc).__name__ + ": " + str(exc))}</p></div>', active_path='/favorites')

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
      <section class="hero card hero-card">
        <div class="hero-copy">
          <div class="eyebrow">Batch analyze</div>
          <h1>Analyze channel: {html.escape(channel_name or channel_id)}</h1>
          <p>Lấy {len(videos)} video từ channel và chạy analyze hàng loạt. Mỗi result giữ lại đúng link cần thiết để mở report hoặc JSON.</p>
          <div class="hero-points">
            <span class="tag soft">{len(videos)} videos queued</span>
            <span class="tag soft">Batch report</span>
            <span class="tag soft">Favorites workflow</span>
          </div>
        </div>
        <div class="hero-panel">
          <div class="soft-panel">
            <div class="field-label">Nguồn</div>
            <div class="summary">{html.escape(channel_name or channel_id)}</div>
            <div class="actions hero-actions">
              <a class="btn secondary" href="/favorites">Quay lại Favorites</a>
            </div>
          </div>
        </div>
      </section>
      <section class="section-card card">{section_intro('Results', 'Kết quả batch analyze', 'Danh sách này chỉ giữ 2 action chính: xem report hoặc mở analysis JSON để tránh lặp link thừa.')}<div class="grid">{''.join(cards)}</div></section>
    '''
    return _page(body, active_path='/favorites')


@app.get('/favorites')
def favorites_page() -> str:
    items = load_favorites(PROJECT_ROOT)
    cards = []
    for item in items:
        cards.append(f'''
        <div class="fav-card">
          <div>
            <div class="channel-toolbar">
              <div>
                <div class="fav-title">{html.escape(item.get('name') or 'Unknown')}</div>
                <div class="fav-meta">{html.escape(item.get('topic') or 'N/A')}</div>
              </div>
              <a class="btn secondary" href="{html.escape(item.get('url') or '#')}" target="_blank">Mở kênh</a>
            </div>
            <div class="fav-note">{html.escape(item.get('note') or '')}</div>
            <form class="stack-form" method="post" action="/favorites/analyze-channel">
              <input type="hidden" name="channel_id" value="{html.escape(item.get('channel_id') or '')}">
              <input type="hidden" name="name" value="{html.escape(item.get('name') or '')}">
              <div class="stack-row">
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
    body = '<section class="hero card hero-card"><div class="hero-copy"><div class="eyebrow">Favorites</div><h1>Kênh yêu thích</h1><p>Lưu local tại <code>favorites/channels.json</code>. Từ đây bạn có thể mở kênh hoặc analyze hàng loạt theo số lượng video mong muốn.</p><div class="hero-points"><span class="tag soft">Local library</span><span class="tag soft">Batch analyze</span><span class="tag soft">Quick access</span></div></div><div class="hero-panel"><div class="stat-card"><div class="stat-label">Saved channels</div><div class="stat-value">' + str(len(items)) + '</div><div class="stat-note">Danh sách kênh được lưu từ Discover hoặc thêm thủ công sau này.</div></div></div></section>'
    if items:
        body += '<section class="section-card card">' + section_intro('Collection', 'Danh sách kênh đã lưu', 'Giữ lại đúng action cần thiết: mở kênh hoặc analyze hàng loạt theo số lượng video mong muốn.') + '<div class="fav-grid">' + ''.join(cards) + '</div></section>'
    else:
        body += '<section class="section-card card"><p class="hint">Chưa có kênh nào được lưu.</p></section>'
    return _page(body, active_path='/favorites')


@app.get('/report/<path:name>')
def report_view(name: str) -> Response | str:
    path = (SETTINGS.reports_root / name).resolve()
    if not str(path).startswith(str(SETTINGS.reports_root.resolve())) or not path.exists():
        return Response('Not found', status=404)
    content = path.read_text(encoding='utf-8')
    source_url = ''
    raw_path = SETTINGS.raw_root / f'{Path(name).stem}.json'
    if raw_path.exists():
        try:
            source_url = _read_json(raw_path).get('url') or ''
        except Exception:
            source_url = ''
    analyze_link = (
        f'<a class="btn secondary" href="/analyze?url={html.escape(source_url)}">Mở Analyze</a>'
        if source_url else ''
    )
    body = f'''
      <div class="card report-card">
        <div class="topbar spread">
          <div>
            <div class="eyebrow">Report</div>
            <h1 style="margin:0">{html.escape(name)}</h1>
          </div>
          <div class="topbar-actions">
            {analyze_link}
            <a class="btn secondary" href="/files/reports/{html.escape(name)}">Tải .md</a>
          </div>
        </div>
        <div class="report">{html.escape(content)}</div>
      </div>
    '''
    return _page(body, active_path='/report')


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
