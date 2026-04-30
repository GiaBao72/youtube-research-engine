from __future__ import annotations

import html
import json
from pathlib import Path

from flask import Flask, Response, redirect, request, send_file, url_for

from .channels import add_favorite_channel, discover_channels, fetch_channel_videos, load_favorites
from .cli import run_analyze
from .config import Settings
from .indexing import delete_video_record, load_indexed_videos, update_video_record


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
            '<section class="card section-card">'
            '<div class="section-head"><div><div class="eyebrow">Library</div><h2>Phân tích gần đây</h2></div>'
            '<p>Danh sách video đã phân tích sẽ hiện ở đây để bạn sửa nhanh hoặc xóa khỏi workspace.</p></div>'
            '<p class="hint">Chưa có video nào được phân tích.</p></section>'
        )

    rows = []
    for item in items:
        rows.append(f'''
        <tr>
          <td>
            <div class="recent-video">
              <img src="{html.escape(item['thumb'])}" alt="thumb">
              <div>
                <div class="recent-title">{html.escape(item['title'])}</div>
                <div class="recent-sub">{html.escape(item['summary'][:120])}{'…' if len(item['summary']) > 120 else ''}</div>
                <div class="recent-note">{html.escape(item['note'] or 'Chưa có ghi chú riêng.')}</div>
              </div>
            </div>
          </td>
          <td>{html.escape(item['channel'])}</td>
          <td>{html.escape(item['duration'])}</td>
          <td>
            <form class="inline-form" method="post" action="/videos/update">
              <input type="hidden" name="video_id" value="{html.escape(item['video_id'])}">
              <input type="text" name="custom_title" value="{html.escape(item['title'])}" placeholder="Tên hiển thị">
              <textarea name="note" placeholder="Ghi chú nội bộ">{html.escape(item['note'])}</textarea>
              <div class="table-actions">
                <button class="btn secondary" type="submit">Lưu</button>
                <a class="inline-link" href="/analyze?url={html.escape(item['source_url'])}">Mở Analyze</a>
                <a class="inline-link" href="/report/{html.escape(item['report_name'])}">Report</a>
                <a class="inline-link" href="/files/raw/{html.escape(item['analysis_name'])}">JSON</a>
              </div>
            </form>
            <form class="inline-form danger-form" method="post" action="/videos/delete" onsubmit="return confirm('Xóa toàn bộ output của video này?');">
              <input type="hidden" name="video_id" value="{html.escape(item['video_id'])}">
              <button class="btn danger" type="submit">Xóa</button>
            </form>
          </td>
        </tr>
        ''')
    return (
        '<section class="card section-card">'
        '<div class="section-head"><div><div class="eyebrow">Library</div><h2>Phân tích gần đây</h2></div>'
        '<p>CRUD cho danh sách video đã phân tích: sửa tên hiển thị, ghi chú nội bộ, mở lại analyze hoặc xóa cả bộ output.</p></div>'
        '<div class="table-shell"><table class="recent-table"><thead><tr><th>Video</th><th>Kênh</th><th>Thời lượng</th><th>Quản lý</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></div></section>'
    )


def _recent_html() -> str:
    return _analyzed_videos_table()


def _nav() -> str:
    return '''
    <div class="nav-shell">
      <div class="brand-block">
        <div class="brand-mark">YR</div>
        <div>
          <div class="brand-name">YouTube Research</div>
          <div class="brand-note">Research, scripting, production artifacts</div>
        </div>
      </div>
      <div class="nav-links">
        <a class="nav-link" href="/">Home</a>
        <a class="nav-link" href="/analyze">Analyze</a>
        <a class="nav-link" href="/discover">Khám phá kênh</a>
        <a class="nav-link" href="/favorites">Yêu thích</a>
      </div>
    </div>
    '''


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


def _page(body: str, script: str = '') -> str:
    return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Research</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #09111f;
      --bg-accent: #13233d;
      --panel: rgba(10, 21, 39, 0.86);
      --panel-strong: rgba(12, 27, 49, 0.96);
      --panel-soft: rgba(19, 35, 61, 0.72);
      --border: rgba(143, 180, 255, 0.16);
      --text: #f4f7fb;
      --muted: #97a8c6;
      --brand: #ff7a18;
      --brand-deep: #d95a00;
      --brand-soft: rgba(255, 122, 24, 0.14);
      --success: #28b07a;
      --shadow: 0 24px 60px rgba(1, 8, 20, 0.44);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: "Space Grotesk", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(255, 122, 24, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(38, 170, 255, 0.16), transparent 24%),
        linear-gradient(180deg, #07101d 0%, #09111f 42%, #0c1627 100%);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.55), transparent 88%);
      pointer-events: none;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px 20px 72px; position: relative; z-index: 1; }}
    .nav-shell {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      margin-bottom: 22px;
      padding: 16px 20px;
      border: 1px solid var(--border);
      border-radius: 24px;
      background: rgba(8, 16, 29, 0.78);
      backdrop-filter: blur(14px);
      box-shadow: var(--shadow);
      position: sticky;
      top: 10px;
      z-index: 12;
    }}
    .brand-block {{ display: flex; align-items: center; gap: 14px; min-width: 0; }}
    .brand-mark {{
      width: 46px;
      height: 46px;
      border-radius: 15px;
      display: grid;
      place-items: center;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: #15100c;
      background: linear-gradient(135deg, #ffd26f, var(--brand));
      box-shadow: 0 10px 24px rgba(255, 122, 24, 0.24);
    }}
    .brand-name {{ font-size: 17px; font-weight: 700; }}
    .brand-note {{ color: var(--muted); font-size: 13px; }}
    .nav-links {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
    .nav-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 0 16px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: #eef4ff;
      text-decoration: none;
      transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
    }}
    .nav-link:hover {{ transform: translateY(-1px); background: rgba(255, 122, 24, 0.14); border-color: rgba(255, 122, 24, 0.34); }}
    .card {{
      margin-bottom: 18px;
      border: 1px solid var(--border);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(12, 23, 42, 0.94), rgba(8, 17, 31, 0.92));
      box-shadow: var(--shadow);
    }}
    .hero-card {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr); gap: 22px; padding: 28px; overflow: hidden; }}
    .hero-copy {{ padding: 10px 8px 10px 2px; }}
    .hero-panel {{ padding: 18px; border-radius: 24px; background: linear-gradient(180deg, rgba(17, 31, 54, 0.95), rgba(12, 24, 43, 0.9)); border: 1px solid rgba(255,255,255,0.08); }}
    .eyebrow {{ color: #ffb36f; text-transform: uppercase; letter-spacing: 0.14em; font-size: 12px; font-weight: 700; margin-bottom: 12px; }}
    h1 {{ margin: 0 0 12px; font-size: clamp(34px, 5vw, 58px); line-height: 1.02; max-width: 12ch; }}
    h2 {{ margin: 0; font-size: 28px; }}
    h3 {{ margin: 0 0 12px; font-size: 24px; line-height: 1.15; }}
    p {{ color: var(--muted); line-height: 1.7; margin: 0; }}
    .hero-points {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; }}
    .field-label {{ display: inline-block; margin-bottom: 10px; color: #f8c48e; font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }}
    form {{ display: grid; gap: 12px; }}
    textarea, input, select {{
      width: 100%;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.09);
      background: rgba(5, 12, 22, 0.9);
      color: var(--text);
      padding: 15px 16px;
      font: inherit;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    textarea {{ min-height: 184px; resize: vertical; }}
    textarea:focus, input:focus, select:focus {{ outline: 2px solid rgba(255, 122, 24, 0.5); border-color: rgba(255, 122, 24, 0.6); }}
    button, .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 46px;
      padding: 0 18px;
      border: 0;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--brand), #ff9448);
      color: #170d06;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      box-shadow: 0 14px 30px rgba(255, 122, 24, 0.22);
      transition: transform 140ms ease, box-shadow 140ms ease, filter 140ms ease;
      width: fit-content;
    }}
    button:hover, .btn:hover {{ transform: translateY(-1px); box-shadow: 0 18px 34px rgba(255, 122, 24, 0.28); filter: saturate(1.06); }}
    .btn.secondary {{ background: rgba(255,255,255,0.05); color: #eff4ff; border: 1px solid rgba(255,255,255,0.09); box-shadow: none; }}
    .btn.success {{ background: linear-gradient(135deg, #39c98a, #1e9a67); color: #06160f; box-shadow: 0 14px 30px rgba(40, 176, 122, 0.18); }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 16px; }}
    .hero-actions {{ margin-top: 8px; }}
    .grid {{ display: grid; gap: 18px; margin-top: 18px; }}
    .section-card {{ padding: 24px; }}
    .section-head {{ display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 18px; }}
    .section-head p {{ max-width: 460px; }}
    .stats-strip {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }}
    .stat-card {{ padding: 18px; border-radius: 22px; background: var(--panel-soft); border: 1px solid rgba(255,255,255,0.07); }}
    .stat-label {{ color: #8ea6ca; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .stat-value {{ font-size: 30px; font-weight: 700; margin-top: 8px; }}
    .stat-note {{ color: var(--muted); font-size: 14px; margin-top: 6px; }}
    .inline-form {{ display: grid; gap: 10px; }}
    .inline-form input[type="text"], .inline-form textarea {{ width: 100%; border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; background: rgba(255,255,255,0.04); color: var(--text); padding: 10px 12px; font: inherit; }}
    .inline-form textarea {{ min-height: 76px; resize: vertical; }}
    .recent-note {{ margin-top: 8px; color: #ffd09e; font-size: 13px; line-height: 1.5; }}
    .btn.danger {{ background: linear-gradient(135deg, #ff6b57, #d43c28); color: #fff8f6; box-shadow: 0 14px 30px rgba(212, 60, 40, 0.24); }}
    .danger-form {{ margin-top: 10px; }}

    .result-grid {{ display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 20px; }}
    .thumb {{ width: 100%; height: 100%; object-fit: cover; min-height: 170px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08); background: #050b14; }}
    .meta {{ display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 10px 14px; margin: 14px 0 16px; }}
    .label {{ color: #8ea6ca; text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; }}
    .error {{ color: #ffb0b0; white-space: pre-wrap; }}
    .ok {{ color: #9ef0c8; }}
    a {{ color: #9fd0ff; text-decoration: none; }}
    .summary {{ padding: 16px 18px; border-radius: 18px; background: rgba(5, 12, 22, 0.84); border: 1px solid rgba(255,255,255,0.06); color: #f0f5ff; line-height: 1.7; }}
    .tag {{ display: inline-flex; align-items: center; min-height: 34px; padding: 0 12px; border-radius: 999px; background: rgba(255,255,255,0.06); color: #d9e7ff; font-size: 13px; margin: 0 8px 8px 0; border: 1px solid rgba(255,255,255,0.05); }}
    .tag.soft {{ background: var(--brand-soft); color: #ffd7b6; border-color: rgba(255, 122, 24, 0.2); }}
    .recent-grid, .channel-grid, .fav-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
    .table-shell {{ overflow-x: auto; border: 1px solid rgba(255,255,255,0.08); border-radius: 22px; background: rgba(5, 12, 22, 0.58); }}
    .recent-table {{ width: 100%; border-collapse: collapse; min-width: 860px; }}
    .recent-table th, .recent-table td {{ padding: 16px 18px; text-align: left; vertical-align: top; border-bottom: 1px solid rgba(255,255,255,0.07); }}
    .recent-table th {{ color: #8ea6ca; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; background: rgba(255,255,255,0.03); }}
    .recent-table tbody tr:last-child td {{ border-bottom: 0; }}
    .recent-video {{ display: grid; grid-template-columns: 124px minmax(0, 1fr); gap: 14px; align-items: start; }}
    .recent-video img {{ width: 124px; height: 72px; object-fit: cover; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); }}
    .recent-title {{ font-weight: 700; font-size: 17px; line-height: 1.3; margin-bottom: 6px; }}
    .recent-sub {{ color: #aebddb; font-size: 14px; line-height: 1.55; }}
    .table-actions {{ display: flex; flex-wrap: wrap; gap: 10px 12px; min-width: 220px; }}
    .mini-card, .channel-card, .fav-card {{ border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; background: linear-gradient(180deg, rgba(12, 25, 43, 0.96), rgba(8, 16, 29, 0.92)); overflow: hidden; }}
    .mini-card {{ display: grid; grid-template-columns: 132px minmax(0, 1fr); }}
    .mini-card img {{ width: 100%; height: 100%; min-height: 132px; object-fit: cover; }}
    .mini-body, .channel-card > div, .fav-card > div {{ padding: 16px; }}
    .channel-card img {{ width: 100%; max-height: 200px; object-fit: cover; border-bottom: 1px solid rgba(255,255,255,0.08); background: #050b14; }}
    .mini-kicker {{ color: #ffb36f; text-transform: uppercase; letter-spacing: 0.12em; font-size: 11px; margin-bottom: 10px; }}
    .mini-title, .channel-title, .fav-title {{ font-weight: 700; font-size: 19px; line-height: 1.25; margin-bottom: 6px; }}
    .mini-meta, .channel-meta, .fav-meta {{ color: #9cb1d2; font-size: 14px; margin-bottom: 10px; }}
    .mini-meta span {{ opacity: 0.7; margin: 0 6px; }}
    .mini-summary, .channel-desc, .fav-note {{ color: #d3def5; font-size: 14px; line-height: 1.6; }}
    .mini-links {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 14px; }}
    .inline-link {{ color: #ffd09e; font-size: 14px; }}
    .inline-link:hover {{ color: #fff1df; }}
    .topbar {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }}
    .report {{ padding: 20px; border-radius: 20px; background: rgba(5, 12, 22, 0.88); border: 1px solid rgba(255,255,255,0.06); white-space: pre-wrap; line-height: 1.72; color: #edf4ff; overflow: auto; }}
    .artifact-panel {{ margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 14px; }}
    .artifact-toggle {{ display: inline-flex; align-items: center; gap: 8px; color: #f5c08a; font-size: 14px; cursor: pointer; }}
    .artifact-toggle::marker {{ color: #ffd09e; }}
    .artifact-panel[open] .artifact-toggle {{ color: #ffe3be; }}
    .artifact-grid {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }}
    .hint {{ font-size: 14px; color: var(--muted); }}
    code {{ padding: 2px 6px; border-radius: 8px; background: rgba(255,255,255,0.08); }}
    @media (max-width: 960px) {{
      .hero-card, .result-grid {{ grid-template-columns: 1fr; }}
      .nav-shell, .section-head {{ align-items: flex-start; }}
      .stats-strip {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 720px) {{
      .wrap {{ padding: 16px 14px 56px; }}
      .nav-shell {{ border-radius: 20px; padding: 14px; }}
      .brand-note {{ display: none; }}
      .nav-links {{ width: 100%; justify-content: flex-start; }}
      .hero-card, .section-card, .result {{ padding: 16px; }}
      .meta {{ grid-template-columns: 1fr; gap: 6px; }}
      h1 {{ max-width: none; }}
      .recent-table {{ min-width: 680px; }}
      .recent-video {{ grid-template-columns: 96px minmax(0, 1fr); }}
      .recent-video img {{ width: 96px; height: 60px; }}
    }}
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
        _analyze_form(
            raw_urls,
            title='Analyze video và mở gói output',
            intro='Giữ nguyên luồng analyze hiện tại nhưng hiển thị lại dưới giao diện rõ ràng hơn để bạn xem kết quả, mở report và quay lại refine nhanh hơn.',
        ),
        '<section class="section-card card"><div class="section-head"><div><div class="eyebrow">Output</div><h2>Kết quả phân tích</h2></div><p>Mỗi card gom phần dùng thường xuyên lên trước, còn artifact kỹ thuật nằm trong More artifacts.</p></div><div class="grid">',
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
                      <a class="btn secondary" href="/analyze?url={html.escape(url)}">Mở trang Analyze</a>
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
        result_html = f'<section class="section-card card"><p class="error">{html.escape(error)}</p></section>'
    elif topic:
        result_html = (
            '<section class="section-card card"><div class="section-head"><div><div class="eyebrow">Results</div><h2>Kênh phù hợp</h2></div>'
            '<p>Danh sách kênh được gom từ các video match tốt nhất với chủ đề bạn vừa tìm.</p></div>'
            '<div class="channel-grid">' + ''.join(cards or ['<p class="hint">Không tìm thấy kênh phù hợp.</p>']) + '</div></section>'
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
    return _page(body)


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
    return redirect(url_for('index'))


@app.post('/videos/delete')
def videos_delete() -> Response:
    video_id = (request.form.get('video_id') or '').strip()
    if video_id:
        delete_video_record(SETTINGS, video_id)
    return redirect(url_for('index'))


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
    body = '<section class="hero card hero-card"><div class="hero-copy"><div class="eyebrow">Favorites</div><h1>Kênh yêu thích</h1><p>Lưu local tại <code>favorites/channels.json</code>. Từ đây bạn có thể mở kênh hoặc analyze hàng loạt theo số lượng video mong muốn.</p><div class="hero-points"><span class="tag soft">Local library</span><span class="tag soft">Batch analyze</span><span class="tag soft">Quick access</span></div></div><div class="hero-panel"><div class="stat-card"><div class="stat-label">Saved channels</div><div class="stat-value">' + str(len(items)) + '</div><div class="stat-note">Danh sách kênh được lưu từ Discover hoặc thêm thủ công sau này.</div></div></div></section>'
    if items:
        body += '<section class="section-card card"><div class="section-head"><div><div class="eyebrow">Collection</div><h2>Danh sách kênh đã lưu</h2></div><p>Chọn số lượng video và kiểu sắp xếp rồi chạy analyze hàng loạt ngay trong card.</p></div><div class="fav-grid">' + ''.join(cards) + '</div></section>'
    else:
        body += '<section class="section-card card"><p class="hint">Chưa có kênh nào được lưu.</p></section>'
    return _page(body)


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
      <div class="card">
        <div class="topbar">
          <h1 style="margin:0">{html.escape(name)}</h1>
          <a class="btn secondary" href="/">← Trang chủ</a>
          {analyze_link}
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
