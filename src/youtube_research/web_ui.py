from __future__ import annotations

import html
from typing import Iterable

BASE_CSS = '''
    :root {
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
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: "Plus Jakarta Sans", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(255, 122, 24, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(38, 170, 255, 0.16), transparent 24%),
        linear-gradient(180deg, #07101d 0%, #09111f 42%, #0c1627 100%);
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      background-image: linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.55), transparent 88%);
      pointer-events: none;
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 24px 20px 72px; position: relative; z-index: 1; }
    .nav-shell {
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
    }
    .brand-block { display: flex; align-items: center; gap: 14px; min-width: 0; }
    .brand-mark {
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
    }
    .brand-name { font-size: 17px; font-weight: 700; }
    .brand-note { color: var(--muted); font-size: 13px; }
    .nav-links { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
    .nav-link {
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
    }
    .nav-link:hover { transform: translateY(-1px); background: rgba(255, 122, 24, 0.14); border-color: rgba(255, 122, 24, 0.34); }
    .nav-link.active { background: rgba(255, 122, 24, 0.18); border-color: rgba(255, 122, 24, 0.44); color: #fff3e8; }
    .flash-stack { display: grid; gap: 10px; margin-bottom: 16px; }
    .flash {
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.07);
      background: rgba(15, 23, 42, 0.92);
      color: #edf4ff;
      box-shadow: var(--shadow);
    }
    .flash.success { border-color: rgba(34, 197, 94, 0.34); background: rgba(10, 29, 24, 0.9); }
    .flash.error { border-color: rgba(239, 68, 68, 0.34); background: rgba(37, 14, 17, 0.9); }
    .flash.info { border-color: rgba(56, 189, 248, 0.34); background: rgba(10, 23, 37, 0.9); }
    .card {
      margin-bottom: 18px;
      border: 1px solid var(--border);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(12, 23, 42, 0.94), rgba(8, 17, 31, 0.92));
      box-shadow: var(--shadow);
    }
    .hero-card { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr); gap: 22px; padding: 28px; overflow: hidden; }
    .hero-copy { padding: 10px 8px 10px 2px; }
    .hero-panel { padding: 18px; border-radius: 24px; background: linear-gradient(180deg, rgba(17, 31, 54, 0.95), rgba(12, 24, 43, 0.9)); border: 1px solid rgba(255,255,255,0.08); }
    .eyebrow { color: #ffb36f; text-transform: uppercase; letter-spacing: 0.14em; font-size: 12px; font-weight: 700; margin-bottom: 12px; }
    h1 { margin: 0 0 12px; font-size: clamp(34px, 5vw, 58px); line-height: 1.02; max-width: 12ch; }
    h2 { margin: 0; font-size: 28px; }
    h3 { margin: 0 0 12px; font-size: 24px; line-height: 1.15; }
    p { color: var(--muted); line-height: 1.7; margin: 0; }
    .hero-points { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
    .field-label { display: inline-block; margin-bottom: 10px; color: #f8c48e; font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; }
    form { display: grid; gap: 12px; }
    textarea, input, select {
      width: 100%;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.09);
      background: rgba(5, 12, 22, 0.9);
      color: var(--text);
      padding: 15px 16px;
      font: inherit;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    textarea { min-height: 184px; resize: vertical; }
    textarea:focus, input:focus, select:focus { outline: 2px solid rgba(255, 122, 24, 0.5); border-color: rgba(255, 122, 24, 0.6); }
    button, .btn {
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
    }
    button:hover, .btn:hover { transform: translateY(-1px); box-shadow: 0 18px 34px rgba(255, 122, 24, 0.28); filter: saturate(1.06); }
    .btn.secondary { background: rgba(255,255,255,0.05); color: #eff4ff; border: 1px solid rgba(255,255,255,0.09); box-shadow: none; }
    .btn.success { background: linear-gradient(135deg, #39c98a, #1e9a67); color: #06160f; box-shadow: 0 14px 30px rgba(40, 176, 122, 0.18); }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 16px; }
    .hero-actions { margin-top: 8px; }
    .grid { display: grid; gap: 18px; margin-top: 18px; }
    .section-card { padding: 24px; }
    .section-head { display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 18px; }
    .section-head p { max-width: 460px; }
    .panel-stack { display: grid; gap: 18px; }
    .stats-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
    .stat-card { padding: 18px; border-radius: 22px; background: var(--panel-soft); border: 1px solid rgba(255,255,255,0.07); }
    .stat-label { color: #8ea6ca; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }
    .stat-value { font-size: 30px; font-weight: 700; margin-top: 8px; }
    .stat-note { color: var(--muted); font-size: 14px; margin-top: 6px; }
    .inline-form { display: grid; gap: 10px; }
    .inline-form input[type="text"], .inline-form textarea { width: 100%; border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; background: rgba(255,255,255,0.04); color: var(--text); padding: 10px 12px; font: inherit; }
    .inline-form textarea { min-height: 76px; resize: vertical; }
    .recent-note { margin-top: 8px; color: #ffd09e; font-size: 13px; line-height: 1.5; }
    .btn.danger { background: linear-gradient(135deg, #ff6b57, #d43c28); color: #fff8f6; box-shadow: 0 14px 30px rgba(212, 60, 40, 0.24); }
    .danger-form { margin-top: 10px; }
    .library-card { background: linear-gradient(180deg, rgba(4, 11, 21, 0.96), rgba(7, 16, 31, 0.94)); border-color: rgba(148, 163, 184, 0.16); }
    .library-head { align-items: center; }
    .library-shell { background: rgba(2, 8, 23, 0.82); border-color: rgba(51, 65, 85, 0.95); }
    .library-table { min-width: 1080px; }
    .library-table th { background: rgba(15, 23, 42, 0.92); color: #cbd5e1; }
    .library-table td { padding-top: 22px; padding-bottom: 22px; }
    .recent-video-hero { grid-template-columns: 156px minmax(0, 1fr); gap: 16px; align-items: center; }
    .recent-video-hero img { width: 156px; height: 88px; border-radius: 16px; border-color: rgba(100, 116, 139, 0.4); }
    .recent-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
    .table-pill { display: inline-flex; align-items: center; min-height: 28px; padding: 0 10px; border-radius: 999px; background: rgba(34, 197, 94, 0.14); color: #bbf7d0; border: 1px solid rgba(34, 197, 94, 0.28); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }
    .table-pill.muted { background: rgba(148, 163, 184, 0.12); color: #cbd5e1; border-color: rgba(148, 163, 184, 0.22); }
    .library-meta-block { display: grid; gap: 10px; min-width: 220px; }
    .library-meta-label { color: #7dd3fc; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; }
    .library-meta-value { color: #f8fafc; font-weight: 600; line-height: 1.5; }
    .library-actions-card { padding: 16px; border-radius: 18px; background: rgba(15, 23, 42, 0.82); border: 1px solid rgba(51, 65, 85, 0.7); }
    .quick-links { display: flex; flex-wrap: wrap; gap: 10px 14px; margin-bottom: 14px; }
    .inline-link.strong { color: #86efac; font-weight: 700; }
    .library-edit-form { gap: 8px; }
    .field-label.compact { margin: 0; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: #8fb4ff; }
    .table-actions-split { justify-content: flex-start; }
    .ghost-danger { width: 100%; justify-content: center; box-shadow: none; }
    .result-grid { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 20px; }
    .thumb { width: 100%; height: 100%; object-fit: cover; min-height: 170px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.08); background: #050b14; }
    .meta { display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 10px 14px; margin: 14px 0 16px; }
    .label { color: #8ea6ca; text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; }
    .error { color: #ffb0b0; white-space: pre-wrap; }
    .ok { color: #9ef0c8; }
    a { color: #9fd0ff; text-decoration: none; }
    .summary { padding: 16px 18px; border-radius: 18px; background: rgba(5, 12, 22, 0.84); border: 1px solid rgba(255,255,255,0.06); color: #f0f5ff; line-height: 1.7; }
    .tag { display: inline-flex; align-items: center; min-height: 34px; padding: 0 12px; border-radius: 999px; background: rgba(255,255,255,0.06); color: #d9e7ff; font-size: 13px; margin: 0 8px 8px 0; border: 1px solid rgba(255,255,255,0.05); }
    .tag.soft { background: var(--brand-soft); color: #ffd7b6; border-color: rgba(255, 122, 24, 0.2); }
    .recent-grid, .channel-grid, .fav-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
    .table-shell { overflow-x: auto; border: 1px solid rgba(255,255,255,0.08); border-radius: 22px; background: rgba(5, 12, 22, 0.58); }
    .recent-table { width: 100%; border-collapse: collapse; min-width: 860px; }
    .recent-table th, .recent-table td { padding: 16px 18px; text-align: left; vertical-align: top; border-bottom: 1px solid rgba(255,255,255,0.07); }
    .recent-table th { color: #8ea6ca; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; background: rgba(255,255,255,0.03); }
    .recent-table tbody tr:last-child td { border-bottom: 0; }
    .recent-video { display: grid; grid-template-columns: 124px minmax(0, 1fr); gap: 14px; align-items: start; }
    .recent-video img { width: 124px; height: 72px; object-fit: cover; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); }
    .recent-title { font-weight: 700; font-size: 17px; line-height: 1.3; margin-bottom: 6px; }
    .recent-sub { color: #aebddb; font-size: 14px; line-height: 1.55; }
    .table-actions { display: flex; flex-wrap: wrap; gap: 10px 12px; min-width: 220px; }
    .mini-card, .channel-card, .fav-card { border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; background: linear-gradient(180deg, rgba(12, 25, 43, 0.96), rgba(8, 16, 29, 0.92)); overflow: hidden; }
    .mini-card { display: grid; grid-template-columns: 132px minmax(0, 1fr); }
    .mini-card img { width: 100%; height: 100%; min-height: 132px; object-fit: cover; }
    .mini-body, .channel-card > div, .fav-card > div { padding: 16px; }
    .channel-card img { width: 100%; max-height: 200px; object-fit: cover; border-bottom: 1px solid rgba(255,255,255,0.08); background: #050b14; }
    .mini-kicker { color: #ffb36f; text-transform: uppercase; letter-spacing: 0.12em; font-size: 11px; margin-bottom: 10px; }
    .mini-title, .channel-title, .fav-title { font-weight: 700; font-size: 19px; line-height: 1.25; margin-bottom: 6px; }
    .mini-meta, .channel-meta, .fav-meta { color: #9cb1d2; font-size: 14px; margin-bottom: 10px; }
    .mini-meta span { opacity: 0.7; margin: 0 6px; }
    .mini-summary, .channel-desc, .fav-note { color: #d3def5; font-size: 14px; line-height: 1.6; }
    .mini-links { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 14px; }
    .inline-link { color: #ffd09e; font-size: 14px; }
    .inline-link:hover { color: #fff1df; }
    .topbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }
    .topbar.spread { justify-content: space-between; align-items: flex-start; }
    .topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
    .metric-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .micro-stat { display: inline-flex; align-items: center; min-height: 28px; padding: 0 10px; border-radius: 999px; background: rgba(148, 163, 184, 0.12); color: #dbe7ff; border: 1px solid rgba(148, 163, 184, 0.15); font-size: 12px; }
    .channel-toolbar { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 10px; }
    .stack-form { display: grid; gap: 12px; }
    .stack-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    .stack-row > input, .stack-row > select { flex: 1 1 160px; max-width: 220px; }
    .soft-panel { padding: 16px; border-radius: 18px; background: rgba(15, 23, 42, 0.58); border: 1px solid rgba(255,255,255,0.06); }
    .report-card { padding: 24px; }
    .report { padding: 20px; border-radius: 20px; background: rgba(5, 12, 22, 0.88); border: 1px solid rgba(255,255,255,0.06); white-space: pre-wrap; line-height: 1.72; color: #edf4ff; overflow: auto; }
    .artifact-panel { margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 14px; }
    .artifact-toggle { display: inline-flex; align-items: center; gap: 8px; color: #f5c08a; font-size: 14px; cursor: pointer; }
    .artifact-toggle::marker { color: #ffd09e; }
    .artifact-panel[open] .artifact-toggle { color: #ffe3be; }
    .artifact-grid { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .hint { font-size: 14px; color: var(--muted); }
    code { padding: 2px 6px; border-radius: 8px; background: rgba(255,255,255,0.08); }
    @media (max-width: 960px) {
      .hero-card, .result-grid { grid-template-columns: 1fr; }
      .nav-shell, .section-head { align-items: flex-start; }
      .stats-strip { grid-template-columns: 1fr; }
    }
    @media (max-width: 720px) {
      .wrap { padding: 16px 14px 56px; }
      .nav-shell { border-radius: 20px; padding: 14px; }
      .brand-note { display: none; }
      .nav-links { width: 100%; justify-content: flex-start; }
      .hero-card, .section-card, .result, .report-card { padding: 16px; }
      .meta { grid-template-columns: 1fr; gap: 6px; }
      h1 { max-width: none; }
      .recent-table { min-width: 680px; }
      .recent-video { grid-template-columns: 96px minmax(0, 1fr); }
      .recent-video img { width: 96px; height: 60px; }
      .stack-row > input, .stack-row > select { max-width: none; }
    }
'''


def nav(active_path: str) -> str:
    links = [
        ('/', 'Home'),
        ('/analyze', 'Analyze'),
        ('/discover', 'Khám phá kênh'),
        ('/favorites', 'Yêu thích'),
    ]
    nav_links = []
    for href, label in links:
        active = active_path == href or (href != '/' and active_path.startswith(href))
        class_name = 'nav-link active' if active else 'nav-link'
        nav_links.append(f'<a class="{class_name}" href="{href}">{html.escape(label)}</a>')
    return '''
    <div class="nav-shell">
      <div class="brand-block">
        <div class="brand-mark">YR</div>
        <div>
          <div class="brand-name">YouTube Research</div>
          <div class="brand-note">Research, scripting, production artifacts</div>
        </div>
      </div>
      <div class="nav-links">''' + ''.join(nav_links) + '''</div>
    </div>
    '''


def section_intro(eyebrow: str, title: str, text: str) -> str:
    return (
        '<div class="section-head">'
        f'<div><div class="eyebrow">{html.escape(eyebrow)}</div><h2>{html.escape(title)}</h2></div>'
        f'<p>{html.escape(text)}</p>'
        '</div>'
    )


def flash_stack(messages: Iterable[tuple[str, str]]) -> str:
    items = []
    for category, text in messages:
        safe_category = category if category in {'success', 'error', 'info'} else 'info'
        items.append(f'<div class="flash {safe_category}">{html.escape(text)}</div>')
    if not items:
        return ''
    return '<div class="flash-stack">' + ''.join(items) + '</div>'
