from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from .config import Settings
from .indexing import load_indexed_videos


st.set_page_config(page_title='YouTube Research Dashboard', layout='wide')
project_root = Path(__file__).resolve().parents[2]
settings = Settings.load(project_root)

st.title('YouTube Research Dashboard')
st.caption('Dashboard local bằng Streamlit cho thư viện video đã phân tích.')

rows = load_indexed_videos(settings)
if not rows:
    st.info('Chưa có dữ liệu trong DuckDB. Hãy analyze video hoặc chạy reindex trước.')
    st.stop()

query = st.text_input('Tìm theo title / channel / summary')
channels = sorted({row.get('channel') for row in rows if row.get('channel')})
selected_channel = st.selectbox('Lọc theo channel', ['Tất cả'] + channels)

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
    filtered.append(row)

st.write(f'Kết quả: {len(filtered)} video')
for row in filtered:
    with st.container(border=True):
        st.subheader(row.get('title') or row.get('video_id'))
        st.caption(f"{row.get('channel') or 'N/A'} · {row.get('video_id')}")
        st.write(row.get('summary') or '')
        c1, c2 = st.columns(2)
        with c1:
            st.write('Keywords:', json.loads(row.get('keywords_json') or '[]'))
        with c2:
            st.write('Topic:', row.get('topic_label') or 'N/A')
