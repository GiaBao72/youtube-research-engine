from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


def discover_channels(topic: str, api_key: str, limit: int = 10) -> list[dict[str, Any]]:
    if not api_key:
        raise RuntimeError('Thiếu YOUTUBE_API_KEY trong .env')

    search_resp = requests.get(
        'https://www.googleapis.com/youtube/v3/search',
        params={
            'part': 'snippet',
            'q': topic,
            'type': 'channel',
            'maxResults': min(limit, 25),
            'key': api_key,
        },
        timeout=30,
    )
    search_resp.raise_for_status()
    data = search_resp.json()

    channel_ids = [item['snippet']['channelId'] for item in data.get('items', [])]
    details = _fetch_channel_details(channel_ids, api_key) if channel_ids else {}

    results = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        channel_id = snippet.get('channelId')
        detail = details.get(channel_id, {})
        stats = detail.get('statistics', {})
        results.append({
            'name': snippet.get('channelTitle', ''),
            'url': f'https://www.youtube.com/channel/{channel_id}',
            'channel_id': channel_id,
            'topic': topic,
            'description': (snippet.get('description') or '')[:300],
            'thumbnail': ((snippet.get('thumbnails') or {}).get('high') or {}).get('url'),
            'published_at': snippet.get('publishedAt'),
            'subscriber_count': stats.get('subscriberCount'),
            'video_count': stats.get('videoCount'),
            'view_count': stats.get('viewCount'),
        })
    return results


def _fetch_channel_details(channel_ids: list[str], api_key: str) -> dict[str, dict[str, Any]]:
    resp = requests.get(
        'https://www.googleapis.com/youtube/v3/channels',
        params={
            'part': 'snippet,statistics',
            'id': ','.join(channel_ids),
            'key': api_key,
            'maxResults': len(channel_ids),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {item['id']: item for item in data.get('items', [])}


def favorites_path(project_root: Path) -> Path:
    path = project_root / 'favorites' / 'channels.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text('[]\n', encoding='utf-8')
    return path


def load_favorites(project_root: Path) -> list[dict]:
    path = favorites_path(project_root)
    return json.loads(path.read_text(encoding='utf-8'))


def save_favorites(project_root: Path, items: list[dict]) -> None:
    path = favorites_path(project_root)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def add_favorite_channel(project_root: Path, name: str, url: str, topic: str = '', note: str = '', tags: list[str] | None = None, channel_id: str = '') -> dict:
    items = load_favorites(project_root)
    for item in items:
        if item.get('url') == url:
            return item
    record = {
        'name': name,
        'url': url,
        'channel_id': channel_id,
        'topic': topic,
        'note': note,
        'tags': tags or [],
        'added_at': datetime.now().isoformat(timespec='seconds'),
    }
    items.append(record)
    save_favorites(project_root, items)
    return record
