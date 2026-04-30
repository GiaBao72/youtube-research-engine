from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Settings


def _ensure_duckdb():
    try:
        import duckdb  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError('Thiếu duckdb. Hãy cài dependencies mới bằng pip install -r requirements.txt') from exc
    return duckdb


def db_path(settings: Settings) -> Path:
    return settings.output_root / 'youtube_research.duckdb'


def connect_db(settings: Settings):
    duckdb = _ensure_duckdb()
    conn = duckdb.connect(str(db_path(settings)))
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS videos (
          video_id TEXT PRIMARY KEY,
          url TEXT,
          title TEXT,
          channel TEXT,
          duration INTEGER,
          description TEXT,
          transcript_text TEXT,
          analysis_mode TEXT,
          summary TEXT,
          target_audience TEXT,
          main_angle TEXT,
          hook_analysis TEXT,
          structure_json TEXT,
          view_drivers_json TEXT,
          notable_moments_json TEXT,
          title_variants_json TEXT,
          hook_variants_json TEXT,
          shorts_ideas_json TEXT,
          next_video_ideas_json TEXT,
          rewrite_outline_json TEXT,
          keywords_json TEXT,
          embedding_json TEXT,
          topic_label TEXT,
          custom_title TEXT,
          note TEXT,
          indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    for statement in [
        'ALTER TABLE videos ADD COLUMN IF NOT EXISTS custom_title TEXT',
        'ALTER TABLE videos ADD COLUMN IF NOT EXISTS note TEXT',
    ]:
        try:
            conn.execute(statement)
        except Exception:
            pass
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS favorite_channels (
          url TEXT PRIMARY KEY,
          name TEXT,
          channel_id TEXT,
          topic TEXT,
          note TEXT,
          tags_json TEXT,
          added_at TEXT
        )
        '''
    )
    return conn


def index_video(settings: Settings, raw: dict[str, Any], analysis: dict[str, Any], enrich: dict[str, Any] | None = None) -> None:
    conn = connect_db(settings)
    transcript = raw.get('transcript') or []
    transcript_text = '\n'.join(item.get('text', '') for item in transcript if item.get('text'))
    enrich = enrich or {}
    conn.execute(
        '''
        INSERT OR REPLACE INTO videos (
          video_id, url, title, channel, duration, description, transcript_text,
          analysis_mode, summary, target_audience, main_angle, hook_analysis,
          structure_json, view_drivers_json, notable_moments_json,
          title_variants_json, hook_variants_json, shorts_ideas_json,
          next_video_ideas_json, rewrite_outline_json, keywords_json,
          embedding_json, topic_label, indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''',
        [
            raw.get('video_id'),
            raw.get('url'),
            raw.get('title'),
            raw.get('channel'),
            raw.get('duration'),
            raw.get('description'),
            transcript_text,
            analysis.get('analysis_mode'),
            analysis.get('summary'),
            analysis.get('target_audience'),
            analysis.get('main_angle'),
            analysis.get('hook_analysis'),
            json.dumps(analysis.get('structure', []), ensure_ascii=False),
            json.dumps(analysis.get('view_drivers', []), ensure_ascii=False),
            json.dumps(analysis.get('notable_moments', []), ensure_ascii=False),
            json.dumps(analysis.get('title_variants', []), ensure_ascii=False),
            json.dumps(analysis.get('hook_variants', []), ensure_ascii=False),
            json.dumps(analysis.get('shorts_ideas', []), ensure_ascii=False),
            json.dumps(analysis.get('next_video_ideas', []), ensure_ascii=False),
            json.dumps(analysis.get('rewrite_outline', []), ensure_ascii=False),
            json.dumps(enrich.get('keywords', []), ensure_ascii=False),
            json.dumps(enrich.get('embedding', []), ensure_ascii=False),
            enrich.get('topic_label'),
        ],
    )
    conn.close()


def sync_favorites_to_db(settings: Settings, favorites: list[dict[str, Any]]) -> None:
    conn = connect_db(settings)
    for item in favorites:
        conn.execute(
            '''
            INSERT OR REPLACE INTO favorite_channels (url, name, channel_id, topic, note, tags_json, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            [
                item.get('url'),
                item.get('name'),
                item.get('channel_id'),
                item.get('topic'),
                item.get('note'),
                json.dumps(item.get('tags', []), ensure_ascii=False),
                item.get('added_at'),
            ],
        )
    conn.close()


def load_indexed_videos(settings: Settings) -> list[dict[str, Any]]:
    conn = connect_db(settings)
    rows = conn.execute('SELECT * FROM videos ORDER BY indexed_at DESC').fetchdf().to_dict(orient='records')
    conn.close()
    return rows


def load_favorite_channels(settings: Settings) -> list[dict[str, Any]]:
    conn = connect_db(settings)
    rows = conn.execute('SELECT * FROM favorite_channels ORDER BY added_at DESC').fetchdf().to_dict(orient='records')
    conn.close()
    return rows


def update_video_record(settings: Settings, video_id: str, custom_title: str, note: str) -> None:
    conn = connect_db(settings)
    conn.execute(
        'UPDATE videos SET custom_title = ?, note = ? WHERE video_id = ?',
        [custom_title.strip() or None, note.strip() or None, video_id],
    )
    conn.close()


def delete_video_record(settings: Settings, video_id: str) -> None:
    conn = connect_db(settings)
    row = conn.execute('SELECT url FROM videos WHERE video_id = ?', [video_id]).fetchone()
    conn.execute('DELETE FROM videos WHERE video_id = ?', [video_id])
    conn.close()

    if row and row[0]:
        raw_path = settings.raw_root / f'{video_id}.json'
        analysis_path = settings.raw_root / f'{video_id}.analysis.json'
        report_path = settings.reports_root / f'{video_id}.md'
        pipeline_dir = settings.pipeline_root / video_id
        for suffix in ['.json', '.title.txt', '.hook.txt', '.script.txt']:
            production_path = settings.production_root / f'{video_id}{suffix}'
            if production_path.exists():
                production_path.unlink()
        for path in [raw_path, analysis_path, report_path]:
            if path.exists():
                path.unlink()
        if pipeline_dir.exists():
            for child in sorted(pipeline_dir.glob('**/*'), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            pipeline_dir.rmdir()
