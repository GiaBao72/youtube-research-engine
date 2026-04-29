from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .analyzer import AnalysisResult
from .youtube import VideoData


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _bullet(items: list[str]) -> str:
    return '\n'.join(f'- {item}' for item in items)


def _notable(items: list[dict[str, Any]]) -> str:
    out = []
    for item in items:
        out.append(f"- **{item.get('time','??:??')}** — {item.get('reason','')}\n  - Trích: {item.get('quote','')}")
    return '\n'.join(out)


def _format_duration(seconds: int | None) -> str:
    if not seconds:
        return 'N/A'
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f'{h:02d}:{m:02d}:{s:02d}'
    return f'{m:02d}:{s:02d}'


def write_markdown_report(path: Path, video: VideoData, analysis: AnalysisResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode_label = 'LLM' if analysis.analysis_mode == 'llm' else 'Fallback'
    fallback_note = ''
    if analysis.fallback_reason:
        fallback_note = f'\n- **Lý do fallback:** {analysis.fallback_reason}'

    deep = analysis.deep_analysis or {}
    scores = deep.get('scores', {})
    score_lines = '\n'.join(f'- **{k}**: {v}/10' for k, v in scores.items()) or '- N/A'
    timeline_map = _notable([
        {
            'time': item.get('time', '??:??'),
            'reason': item.get('why_it_matters', ''),
            'quote': item.get('label', ''),
        }
        for item in deep.get('timeline_map', [])
    ])
    best_cuts = _notable([
        {
            'time': item.get('time', '??:??'),
            'reason': item.get('reason', ''),
            'quote': item.get('clip_angle', ''),
        }
        for item in deep.get('best_cut_moments', [])
    ])
    rewrite_modes = deep.get('rewrite_modes', {})

    md = f'''# YouTube Research Report

- **Video ID:** {video.video_id}
- **URL:** {video.url}
- **Tiêu đề:** {video.title or 'N/A'}
- **Kênh:** {video.channel or 'N/A'}
- **Thời lượng:** {_format_duration(video.duration)}
- **Transcript segments:** {len(video.transcript)}
- **Chế độ phân tích:** {mode_label}{fallback_note}
- **Tạo lúc:** {datetime.now().isoformat(timespec='seconds')}

## Tóm tắt
{analysis.summary}

## Đối tượng người xem
{analysis.target_audience}

## Góc chính của video
{analysis.main_angle}

## Phân tích hook
{analysis.hook_analysis}

## Cấu trúc video
{_bullet(analysis.structure)}

## Yếu tố kéo view
{_bullet(analysis.view_drivers)}

## Đoạn đáng chú ý
{_notable(analysis.notable_moments)}

## 5 tiêu đề biến thể
{_bullet(analysis.title_variants)}

## 5 hook biến thể
{_bullet(analysis.hook_variants)}

## Ý tưởng Shorts
{_bullet(analysis.shorts_ideas)}

## Ý tưởng video tiếp theo
{_bullet(analysis.next_video_ideas)}

## Outline viết lại
{_bullet(analysis.rewrite_outline)}

## Deep Analysis - Scores
{score_lines}

## Deep Analysis - Content Drivers
{_bullet(deep.get('content_drivers', []))}

## Deep Analysis - Timeline Map
{timeline_map}

## Deep Analysis - Weak Spots
{_bullet(deep.get('weak_spots', []))}

## Deep Analysis - Best Cut Moments
{best_cuts}

## Deep Analysis - Rewrite Modes (Viral)
{_bullet(rewrite_modes.get('viral', []))}

## Deep Analysis - Rewrite Modes (Educational)
{_bullet(rewrite_modes.get('educational', []))}

## Deep Analysis - Rewrite Modes (Storytelling)
{_bullet(rewrite_modes.get('storytelling', []))}
'''
    path.write_text(md, encoding='utf-8')
