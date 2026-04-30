from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .reporting import write_json


def _clean(text: str, limit: int | None = None) -> str:
    text = re.sub(r'\s+', ' ', (text or '')).strip()
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + '…'
    return text


def _pick(items: list[str], n: int) -> list[str]:
    return [_clean(x) for x in items[:n] if _clean(x)]


def build_production_package(raw: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    title = raw.get('title') or raw.get('video_id') or 'Untitled'
    summary = analysis.get('summary') or ''
    hooks = analysis.get('hook_variants') or []
    titles = analysis.get('title_variants') or []
    shorts = analysis.get('shorts_ideas') or []
    next_ideas = analysis.get('next_video_ideas') or []
    structure = analysis.get('rewrite_outline') or analysis.get('structure') or []
    deep = analysis.get('deep_analysis') or {}
    cuts = deep.get('best_cut_moments') or []
    timeline = deep.get('timeline_map') or []

    primary_title = _clean(titles[0] if titles else title, 100)
    primary_hook = _clean(hooks[0] if hooks else summary, 160)
    script_outline = _pick(structure, 6)
    visual_prompts = [
        f"B-roll minh hoạ cho ý: {_clean(item, 120)}" for item in script_outline[:4]
    ] or [
        f"B-roll theo chủ đề: {_clean(title, 120)}"
    ]

    subtitle_cues = [
        {
            'time': item.get('time', ''),
            'text': _clean(item.get('clip_angle') or item.get('label') or '', 120),
        }
        for item in (cuts[:5] or timeline[:5])
        if _clean(item.get('clip_angle') or item.get('label') or '', 120)
    ]

    return {
        'meta': {
            'video_id': raw.get('video_id'),
            'source_url': raw.get('url'),
            'source_title': title,
            'source_channel': raw.get('channel'),
            'analysis_mode': analysis.get('analysis_mode', 'unknown'),
        },
        'moneyprinter': {
            'title': primary_title,
            'hook': primary_hook,
            'script_outline': script_outline,
            'script_body': [
                _clean(summary, 500),
                *_pick(analysis.get('view_drivers') or [], 4),
                *_pick(next_ideas, 3),
            ],
            'visual_prompts': visual_prompts,
            'voiceover_style': 'energetic, concise, faceless-youtube-short',
            'aspect_ratio': '9:16',
        },
        'subtitle_package': {
            'style': 'high-contrast short-form captions',
            'language': 'vi',
            'cues': subtitle_cues,
        },
        'ffmpeg_movipy_postprocess': {
            'target_aspect_ratio': '9:16',
            'suggested_operations': [
                'crop_center_9_16',
                'burn_subtitles',
                'normalize_audio',
                'add_watermark',
            ],
            'editor_notes': _pick(analysis.get('shorts_ideas') or [], 3),
        },
        'creative': {
            'title_options': _pick(titles, 5),
            'hook_options': _pick(hooks, 5),
            'shorts_ideas': _pick(shorts, 5),
            'content_drivers': _pick(deep.get('content_drivers') or [], 5),
            'best_cut_moments': cuts[:5],
            'timeline_map': timeline[:5],
        },
    }


def write_production_package(output_dir: Path, raw: dict[str, Any], analysis: dict[str, Any]) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package = build_production_package(raw, analysis)
    video_id = raw.get('video_id') or 'unknown'

    package_path = output_dir / f'{video_id}.production.json'
    title_path = output_dir / f'{video_id}.title.txt'
    hook_path = output_dir / f'{video_id}.hook.txt'
    script_path = output_dir / f'{video_id}.script.txt'

    write_json(package_path, package)
    title_path.write_text(package['moneyprinter']['title'] + '\n', encoding='utf-8')
    hook_path.write_text(package['moneyprinter']['hook'] + '\n', encoding='utf-8')
    script_lines = package['moneyprinter']['script_outline'] + [''] + package['moneyprinter']['script_body']
    script_path.write_text('\n'.join(script_lines).strip() + '\n', encoding='utf-8')

    return {
        'package': str(package_path),
        'title': str(title_path),
        'hook': str(hook_path),
        'script': str(script_path),
    }
