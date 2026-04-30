from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import streamlit as st

from .config import Settings
from .enrich import cosine_similarity
from .indexing import load_favorite_channels, load_indexed_videos


st.set_page_config(page_title='YouTube Research Dashboard', layout='wide')
project_root = Path(__file__).resolve().parents[2]
settings = Settings.load(project_root)

st.title('YouTube Research Dashboard')
st.caption('Dashboard local cho thư viện video đã phân tích, semantic lookup, favorite channels, và channel summary.')

rows = load_indexed_videos(settings)
favorites = load_favorite_channels(settings)

if not rows:
    st.info('Chưa có dữ liệu trong DuckDB. Hãy analyze video hoặc chạy reindex trước.')
    st.stop()


def parse_json_field(value: str):
    try:
        return json.loads(value or '[]')
    except Exception:
        return []


def read_analysis_json(video_id: str) -> dict:
    path = settings.raw_root / f'{video_id}.analysis.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def existing_paths(paths: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    return [(label, path) for label, path in paths if path.exists()]


def similar_rows(target_row: dict, all_rows: list[dict], limit: int = 5):
    target_vec = parse_json_field(target_row.get('embedding_json'))
    out = []
    for row in all_rows:
        if row.get('video_id') == target_row.get('video_id'):
            continue
        score = cosine_similarity(target_vec, parse_json_field(row.get('embedding_json')))
        if score > 0:
            out.append((score, row))
    out.sort(key=lambda x: x[0], reverse=True)
    return out[:limit]


def score_card(label: str, value: int | float | str):
    st.metric(label, value)


def timeline_item(item: dict):
    with st.container(border=True):
        st.markdown(f"**{item.get('time', '??:??')} — {item.get('label', 'Untitled')}**")
        st.write(item.get('why_it_matters', ''))


def cut_item(item: dict):
    with st.container(border=True):
        st.markdown(f"**{item.get('time', '??:??')}**")
        st.write(item.get('reason', ''))
        st.caption(item.get('clip_angle', ''))


def summarize_channel(channel_name: str, channel_rows: list[dict]):
    analyses = [read_analysis_json(row.get('video_id') or '') for row in channel_rows]
    analyses = [a for a in analyses if a]
    if not analyses:
        return None

    score_acc = defaultdict(list)
    content_drivers = Counter()
    weak_spots = Counter()
    title_variants = Counter()
    hook_variants = Counter()
    shorts_ideas = Counter()

    for analysis in analyses:
        deep = analysis.get('deep_analysis') or {}
        for k, v in (deep.get('scores') or {}).items():
            if isinstance(v, (int, float)):
                score_acc[k].append(v)
        content_drivers.update(deep.get('content_drivers') or [])
        weak_spots.update(deep.get('weak_spots') or [])
        title_variants.update(analysis.get('title_variants') or [])
        hook_variants.update(analysis.get('hook_variants') or [])
        shorts_ideas.update(analysis.get('shorts_ideas') or [])

    avg_scores = {k: round(sum(v) / len(v), 2) for k, v in score_acc.items() if v}
    return {
        'channel_name': channel_name,
        'video_count': len(channel_rows),
        'avg_scores': avg_scores,
        'common_drivers': [x for x, _ in content_drivers.most_common(5)],
        'common_weak_spots': [x for x, _ in weak_spots.most_common(5)],
        'title_patterns': [x for x, _ in title_variants.most_common(5)],
        'hook_patterns': [x for x, _ in hook_variants.most_common(5)],
        'shorts_patterns': [x for x, _ in shorts_ideas.most_common(5)],
    }


tab1, tab2, tab3 = st.tabs(['Library', 'Video Detail', 'Favorite Channels'])

with tab1:
    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input('Tìm theo title / channel / summary')
    channels = sorted({row.get('channel') for row in rows if row.get('channel')})
    selected_channel = c2.selectbox('Lọc theo channel', ['Tất cả'] + channels)
    mode = c3.selectbox('Mode', ['Tất cả', 'llm', 'fallback'])

    filtered = []
    for row in rows:
        haystack = ' '.join([
            str(row.get('title') or ''),
            str(row.get('channel') or ''),
            str(row.get('summary') or ''),
        ]).lower()
        if query and query.lower() not in haystack:
            continue
        if selected_channel != 'Tất cả' and row.get('channel') != selected_channel:
            continue
        if mode != 'Tất cả' and row.get('analysis_mode') != mode:
            continue
        filtered.append(row)

    st.write(f'Kết quả: {len(filtered)} video')
    for row in filtered:
        with st.container(border=True):
            st.subheader(row.get('title') or row.get('video_id'))
            st.caption(f"{row.get('channel') or 'N/A'} · {row.get('video_id')} · mode={row.get('analysis_mode')}")
            st.write(row.get('summary') or '')
            a, b, c = st.columns(3)
            a.write('Keywords:', parse_json_field(row.get('keywords_json')))
            b.write('Topic:', row.get('topic_label') or 'N/A')
            c.write('Duration:', row.get('duration') or 'N/A')

with tab2:
    options = {f"{row.get('title') or row.get('video_id')} [{row.get('video_id')}]": row for row in rows}
    selected_label = st.selectbox('Chọn video', list(options.keys()))
    selected = options[selected_label]
    video_id = selected.get('video_id') or ''
    deep = (read_analysis_json(video_id).get('deep_analysis') or {})
    scores = deep.get('scores', {})
    production_files = existing_paths([
        ('Production JSON', settings.production_root / f'{video_id}.production.json'),
        ('Title TXT', settings.production_root / f'{video_id}.title.txt'),
        ('Hook TXT', settings.production_root / f'{video_id}.hook.txt'),
        ('Script TXT', settings.production_root / f'{video_id}.script.txt'),
    ])
    pipeline_root = settings.pipeline_root / video_id
    pipeline_files = existing_paths([
        ('Pipeline README', pipeline_root / 'README.txt'),
        ('Commands JSON', pipeline_root / 'commands.json'),
        ('MoneyPrinter Input', pipeline_root / 'moneyprinter.input.json'),
        ('Subtitle Input', pipeline_root / 'subtitle.input.json'),
        ('Finalize Input', pipeline_root / 'finalize.input.json'),
        ('Run MoneyPrinter (.sh)', pipeline_root / 'run_moneyprinter.sh'),
        ('Run Subtitle (.sh)', pipeline_root / 'run_subtitle.sh'),
        ('Run Finalize (.sh)', pipeline_root / 'run_finalize.sh'),
        ('Run All (.sh)', pipeline_root / 'run_all.sh'),
        ('Run MoneyPrinter (.bat)', pipeline_root / 'run_moneyprinter.bat'),
        ('Run Subtitle (.bat)', pipeline_root / 'run_subtitle.bat'),
        ('Run Finalize (.bat)', pipeline_root / 'run_finalize.bat'),
        ('Run All (.bat)', pipeline_root / 'run_all.bat'),
    ])

    st.subheader(selected.get('title') or selected.get('video_id'))
    st.caption(f"{selected.get('channel') or 'N/A'} · {selected.get('video_id')}")
    st.write(selected.get('summary') or '')

    base1, base2 = st.columns(2)
    with base1:
        st.markdown('**Title variants**')
        st.write(parse_json_field(selected.get('title_variants_json')))
        st.markdown('**Hook variants**')
        st.write(parse_json_field(selected.get('hook_variants_json')))
        st.markdown('**Keywords**')
        st.write(parse_json_field(selected.get('keywords_json')))
    with base2:
        st.markdown('**Shorts ideas**')
        st.write(parse_json_field(selected.get('shorts_ideas_json')))
        st.markdown('**Next video ideas**')
        st.write(parse_json_field(selected.get('next_video_ideas_json')))
        st.markdown('**Structure**')
        st.write(parse_json_field(selected.get('structure_json')))

    st.markdown('## Deep Video Analysis')
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        score_card('Hook', scores.get('hook_strength', 'N/A'))
    with s2:
        score_card('Pacing', scores.get('pacing', 'N/A'))
    with s3:
        score_card('Shorts', scores.get('shorts_potential', 'N/A'))
    with s4:
        score_card('Clarity', scores.get('clarity', 'N/A'))
    with s5:
        score_card('Retention', scores.get('retention_potential', 'N/A'))

    st.markdown('### Content Drivers')
    st.write(deep.get('content_drivers', []))

    c_timeline, c_cuts = st.columns(2)
    with c_timeline:
        st.markdown('### Timeline Map')
        timeline = deep.get('timeline_map', [])
        if timeline:
            for item in timeline:
                timeline_item(item)
        else:
            st.info('Chưa có timeline map.')

    with c_cuts:
        st.markdown('### Best Cut Moments (Editor)')
        cuts = deep.get('best_cut_moments', [])
        if cuts:
            for item in cuts:
                cut_item(item)
        else:
            st.info('Chưa có cut moments.')

    st.markdown('### Weak Spots (Critique)')
    weak_spots = deep.get('weak_spots', [])
    if weak_spots:
        for item in weak_spots:
            st.warning(item)
    else:
        st.info('Chưa có weak spots.')

    st.markdown('### Rewrite Modes')
    rw1, rw2, rw3 = st.columns(3)
    with rw1:
        st.markdown('**Viral**')
        st.write((deep.get('rewrite_modes') or {}).get('viral', []))
    with rw2:
        st.markdown('**Educational**')
        st.write((deep.get('rewrite_modes') or {}).get('educational', []))
    with rw3:
        st.markdown('**Storytelling**')
        st.write((deep.get('rewrite_modes') or {}).get('storytelling', []))

    st.markdown('### Production Package')
    if production_files:
        p1, p2 = st.columns(2)
        for idx, (label, path) in enumerate(production_files):
            with (p1 if idx % 2 == 0 else p2):
                st.link_button(label, path.as_uri())
                st.caption(str(path))
    else:
        st.info('Chưa có production package cho video này.')

    st.markdown('### Pipeline Runner')
    if pipeline_files:
        c1, c2 = st.columns(2)
        for idx, (label, path) in enumerate(pipeline_files):
            with (c1 if idx % 2 == 0 else c2):
                st.link_button(label, path.as_uri())
                st.caption(str(path))
    else:
        st.info('Chưa có pipeline bundle cho video này.')

    st.markdown('### Similar videos')
    sims = similar_rows(selected, rows)
    if sims:
        for score, row in sims:
            with st.container(border=True):
                st.write(f"**{row.get('title') or row.get('video_id')}**")
                st.caption(f"{row.get('channel') or 'N/A'} · similarity={score:.4f}")
                st.write(row.get('summary') or '')
    else:
        st.info('Chưa có embedding hoặc chưa tìm được video tương tự.')

with tab3:
    st.write(f'Favorite channels: {len(favorites)}')
    if not favorites:
        st.info('Chưa có favorite channels trong DB. Hãy lưu từ web UI rồi chạy reindex nếu cần sync.')

    channel_names = sorted({row.get('channel') for row in rows if row.get('channel')})
    selected_summary_channel = st.selectbox('Channel summary', ['-- Chọn channel --'] + channel_names)
    if selected_summary_channel != '-- Chọn channel --':
        channel_rows = [row for row in rows if row.get('channel') == selected_summary_channel]
        summary = summarize_channel(selected_summary_channel, channel_rows)
        if summary:
            st.markdown('## Channel Summary')
            st.caption(f"{summary['channel_name']} · {summary['video_count']} video đã phân tích")
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            with sc1:
                score_card('Hook', summary['avg_scores'].get('hook_strength', 'N/A'))
            with sc2:
                score_card('Pacing', summary['avg_scores'].get('pacing', 'N/A'))
            with sc3:
                score_card('Shorts', summary['avg_scores'].get('shorts_potential', 'N/A'))
            with sc4:
                score_card('Clarity', summary['avg_scores'].get('clarity', 'N/A'))
            with sc5:
                score_card('Retention', summary['avg_scores'].get('retention_potential', 'N/A'))

            c1, c2 = st.columns(2)
            with c1:
                st.markdown('### Common Drivers')
                st.write(summary['common_drivers'])
                st.markdown('### Hook Patterns')
                st.write(summary['hook_patterns'])
                st.markdown('### Shorts Patterns')
                st.write(summary['shorts_patterns'])
            with c2:
                st.markdown('### Common Weak Spots')
                st.write(summary['common_weak_spots'])
                st.markdown('### Title Patterns')
                st.write(summary['title_patterns'])

    st.markdown('## Favorite Channels')
    for row in favorites:
        with st.container(border=True):
            st.subheader(row.get('name') or 'Unknown')
            st.caption(row.get('topic') or 'N/A')
            st.write(row.get('note') or '')
            st.write('Tags:', parse_json_field(row.get('tags_json')))
            if row.get('url'):
                st.markdown(f"[Mở kênh]({row.get('url')})")
