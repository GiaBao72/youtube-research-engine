from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_ID_RE = re.compile(r'(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})')


@dataclass
class VideoData:
    video_id: str
    url: str
    title: str | None
    channel: str | None
    duration: int | None
    description: str | None
    transcript: list[dict[str, Any]]


def extract_video_id(url: str) -> str:
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url):
        return url
    match = YOUTUBE_ID_RE.search(url)
    if not match:
        raise ValueError('Không trích được video ID từ URL')
    return match.group(1)


def fetch_metadata(url: str) -> dict[str, Any]:
    command = ['yt-dlp', '--dump-single-json', '--skip-download', url]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    except FileNotFoundError:
        return fetch_metadata_oembed(url)
    except subprocess.CalledProcessError:
        return fetch_metadata_oembed(url)


def fetch_metadata_oembed(url: str) -> dict[str, Any]:
    query = urlencode({'url': url, 'format': 'json'})
    oembed_url = f'https://www.youtube.com/oembed?{query}'
    try:
        with urlopen(oembed_url, timeout=20) as response:
            data = json.load(response)
        meta = {
            'title': data.get('title'),
            'channel': data.get('author_name'),
            'uploader': data.get('author_name'),
            'thumbnail_url': data.get('thumbnail_url'),
            'provider_name': data.get('provider_name'),
            'metadata_source': 'oembed',
        }
        meta['duration'] = fetch_duration_from_watch_page(url)
        return meta
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {}


def fetch_duration_from_watch_page(url: str) -> int | None:
    try:
        request = Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        )
        with urlopen(request, timeout=20) as response:
            html = response.read().decode('utf-8', errors='ignore')
    except (URLError, TimeoutError, ValueError):
        return None

    patterns = [
        r'"lengthSeconds":"(\d+)"',
        r'<meta itemprop="duration" content="PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?">',
    ]

    match = re.search(patterns[0], html)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None

    match = re.search(patterns[1], html)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    return None


def fetch_transcript(video_id: str, preferred_languages: list[str] | None = None) -> list[dict[str, Any]]:
    languages = preferred_languages or ['vi', 'en']
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)
    return [
        {
            'text': item.text,
            'start': item.start,
            'duration': item.duration,
        }
        for item in fetched
    ]


def collect_video_data(url: str) -> VideoData:
    video_id = extract_video_id(url)
    metadata = fetch_metadata(url)
    transcript = fetch_transcript(video_id)
    return VideoData(
        video_id=video_id,
        url=url,
        title=metadata.get('title'),
        channel=metadata.get('channel') or metadata.get('uploader'),
        duration=metadata.get('duration'),
        description=metadata.get('description'),
        transcript=transcript,
    )
