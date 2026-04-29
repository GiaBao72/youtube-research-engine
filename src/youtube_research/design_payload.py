from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .reporting import write_json


def _clean_text(text: str, limit: int | None = None) -> str:
    text = re.sub(r'\s+', ' ', (text or '')).strip()
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + '…'
    return text


def _pick(items: list[str], limit: int) -> list[str]:
    return [_clean_text(item) for item in items[:limit] if _clean_text(item)]


def build_design_payload(raw: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    video_id = raw.get('video_id')
    title = _clean_text(raw.get('title') or video_id or 'Untitled', 120)
    channel = _clean_text(raw.get('channel') or 'N/A', 60)
    summary = _clean_text(analysis.get('summary') or '', 320)
    main_angle = _clean_text(analysis.get('main_angle') or '', 180)
    audience = _clean_text(analysis.get('target_audience') or '', 160)

    title_variants = _pick(analysis.get('title_variants', []), 5)
    hook_variants = _pick(analysis.get('hook_variants', []), 5)
    shorts_ideas = _pick(analysis.get('shorts_ideas', []), 5)
    next_video_ideas = _pick(analysis.get('next_video_ideas', []), 5)
    view_drivers = _pick(analysis.get('view_drivers', []), 5)
    structure = _pick(analysis.get('structure', []), 5)
    rewrite_outline = _pick(analysis.get('rewrite_outline', []), 6)
    notable = analysis.get('notable_moments', [])[:4]

    headline = title_variants[0] if title_variants else title
    subheadline = hook_variants[0] if hook_variants else main_angle
    quote_cards = []
    for item in notable:
        quote = _clean_text(item.get('quote', ''), 140)
        reason = _clean_text(item.get('reason', ''), 120)
        ts = item.get('time', '')
        if quote:
            quote_cards.append({
                'time': ts,
                'headline': quote,
                'subtext': reason,
            })

    carousel_slides = [
        {
            'type': 'cover',
            'title': headline,
            'subtitle': subheadline,
        },
        {
            'type': 'summary',
            'title': 'Tóm tắt nhanh',
            'body': summary,
        },
        {
            'type': 'angle',
            'title': 'Góc chính',
            'body': main_angle,
        },
        {
            'type': 'drivers',
            'title': 'Điểm kéo người xem',
            'bullets': view_drivers[:3],
        },
        {
            'type': 'next',
            'title': 'Ý tưởng khai thác tiếp',
            'bullets': next_video_ideas[:3],
        },
    ]

    return {
        'meta': {
            'video_id': video_id,
            'source_title': title,
            'channel': channel,
            'analysis_mode': analysis.get('analysis_mode', 'unknown'),
        },
        'thumbnail_payload': {
            'primary_text': headline,
            'secondary_text': _clean_text(subheadline, 90),
            'alt_options': title_variants[1:4],
            'style_keywords': view_drivers[:3],
        },
        'shorts_cover_payload': {
            'cover_lines': [
                _clean_text(item, 60) for item in shorts_ideas[:3]
            ],
            'hook_lines': [
                _clean_text(item, 70) for item in hook_variants[:3]
            ],
        },
        'carousel_payload': {
            'title': headline,
            'slides': carousel_slides,
        },
        'quote_cards': quote_cards,
        'content_notes': {
            'target_audience': audience,
            'view_drivers': view_drivers,
            'structure': structure,
            'rewrite_outline': rewrite_outline,
            'next_video_ideas': next_video_ideas,
        },
        'canva_autofill_hint': {
            'recommended_fields': {
                'title': headline,
                'subtitle': subheadline,
                'summary': summary,
                'bullets': view_drivers[:3],
                'cta': next_video_ideas[:1],
            },
            'notes': 'Payload này là lớp trung gian để map vào Canva Brand Template hoặc bất kỳ design system nào.',
        },
    }


def write_design_payload(output_path: Path, raw: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    payload = build_design_payload(raw, analysis)
    write_json(output_path, payload)
    return payload
