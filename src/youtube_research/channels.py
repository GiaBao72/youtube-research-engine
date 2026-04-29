from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


def discover_channels(topic: str, api_key: str, limit: int = 10, sort_by: str = 'relevance') -> list[dict[str, Any]]:
    if not api_key:
        raise RuntimeError('Thiếu YOUTUBE_API_KEY trong .env')

    videos = _search_videos(topic, api_key=api_key, limit=max(limit * 4, 20))
    if not videos:
        return []

    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        'score': 0,
        'matched_videos': [],
        'topic': topic,
    })

    for idx, video in enumerate(videos):
        channel_id = video.get('channel_id')
        if not channel_id:
            continue
        group = grouped[channel_id]
        group['score'] += max(1, 30 - idx)
        group['name'] = video.get('channel_title') or group.get('name')
        group['channel_id'] = channel_id
        group['url'] = f'https://www.youtube.com/channel/{channel_id}'
        group['matched_videos'].append({
            'title': video.get('title'),
            'video_id': video.get('video_id'),
            'published_at': video.get('published_at'),
        })

    details = _fetch_channel_details(list(grouped.keys()), api_key) if grouped else {}

    results = []
    for channel_id, group in grouped.items():
        detail = details.get(channel_id, {})
        snippet = detail.get('snippet', {})
        stats = detail.get('statistics', {})
        sample_titles = [v['title'] for v in group['matched_videos'][:3] if v.get('title')]
        results.append({
            'name': snippet.get('title') or group.get('name') or '',
            'url': group.get('url'),
            'channel_id': channel_id,
            'topic': topic,
            'description': (snippet.get('description') or '')[:300],
            'thumbnail': ((snippet.get('thumbnails') or {}).get('high') or {}).get('url'),
            'published_at': snippet.get('publishedAt'),
            'subscriber_count': stats.get('subscriberCount'),
            'video_count': stats.get('videoCount'),
            'view_count': stats.get('viewCount'),
            'relevance_score': group['score'],
            'matched_video_count': len(group['matched_videos']),
            'sample_video_titles': sample_titles,
        })

    if sort_by == 'subs':
        results.sort(
            key=lambda x: (
                int(x.get('subscriber_count') or 0),
                x.get('relevance_score') or 0,
                x.get('matched_video_count') or 0,
            ),
            reverse=True,
        )
    else:
        results.sort(
            key=lambda x: (
                x.get('relevance_score') or 0,
                x.get('matched_video_count') or 0,
                int(x.get('subscriber_count') or 0),
            ),
            reverse=True,
        )
    return results[:limit]


def _search_videos(topic: str, api_key: str, limit: int = 25) -> list[dict[str, Any]]:
    resp = requests.get(
        'https://www.googleapis.com/youtube/v3/search',
        params={
            'part': 'snippet',
            'q': topic,
            'type': 'video',
            'order': 'relevance',
            'maxResults': min(limit, 50),
            'key': api_key,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    out = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        out.append({
            'video_id': (item.get('id') or {}).get('videoId'),
            'title': snippet.get('title'),
            'channel_id': snippet.get('channelId'),
            'channel_title': snippet.get('channelTitle'),
            'description': snippet.get('description'),
            'published_at': snippet.get('publishedAt'),
        })
    return out


def fetch_channel_videos(channel_id: str, api_key: str, limit: int = 5, order: str = 'date') -> list[dict[str, Any]]:
    if not api_key:
        raise RuntimeError('Thiếu YOUTUBE_API_KEY trong .env')
    resp = requests.get(
        'https://www.googleapis.com/youtube/v3/search',
        params={
            'part': 'snippet',
            'channelId': channel_id,
            'type': 'video',
            'order': order,
            'maxResults': min(limit, 50),
            'key': api_key,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    videos = []
    for item in data.get('items', []):
        snippet = item.get('snippet', {})
        video_id = (item.get('id') or {}).get('videoId')
        if not video_id:
            continue
        videos.append({
            'video_id': video_id,
            'title': snippet.get('title'),
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'published_at': snippet.get('publishedAt'),
            'channel_id': snippet.get('channelId'),
            'channel_title': snippet.get('channelTitle'),
        })
    return videos


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
