from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .reporting import write_json


def build_pipeline_bundle(production_pkg: dict[str, Any], pipeline_root: Path) -> dict[str, Any]:
    meta = production_pkg.get('meta', {})
    mp = production_pkg.get('moneyprinter', {})
    subtitle = production_pkg.get('subtitle_package', {})
    post = production_pkg.get('ffmpeg_movipy_postprocess', {})
    video_id = meta.get('video_id') or 'unknown'

    bundle_dir = pipeline_root / video_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    moneyprinter_input = {
        'title': mp.get('title'),
        'hook': mp.get('hook'),
        'script_outline': mp.get('script_outline', []),
        'script_body': mp.get('script_body', []),
        'visual_prompts': mp.get('visual_prompts', []),
        'voiceover_style': mp.get('voiceover_style'),
        'aspect_ratio': mp.get('aspect_ratio', '9:16'),
    }
    subtitle_input = {
        'video_id': video_id,
        'style': subtitle.get('style'),
        'language': subtitle.get('language'),
        'cues': subtitle.get('cues', []),
    }
    finalize_input = {
        'video_id': video_id,
        'target_aspect_ratio': post.get('target_aspect_ratio', '9:16'),
        'suggested_operations': post.get('suggested_operations', []),
        'editor_notes': post.get('editor_notes', []),
    }

    write_json(bundle_dir / 'moneyprinter.input.json', moneyprinter_input)
    write_json(bundle_dir / 'subtitle.input.json', subtitle_input)
    write_json(bundle_dir / 'finalize.input.json', finalize_input)

    commands = {
        'moneyprinter_note': 'Đặt repo MoneyPrinter cạnh repo này hoặc sửa đường dẫn trong file commands.',
        'moneyprinter_command_linux': f'cd ../MoneyPrinter && python main.py --input ../youtube-research/outputs/pipeline/{video_id}/moneyprinter.input.json',
        'moneyprinter_command_windows': f'cd ..\\MoneyPrinter && python main.py --input ..\\youtube-research-engine\\outputs\\pipeline\\{video_id}\\moneyprinter.input.json',
        'subtitle_command_linux': f'python -m auto_subtitle outputs/pipeline/{video_id}/moneyprinter_output.mp4 --output_srt outputs/pipeline/{video_id}/subtitles.srt',
        'ffmpeg_command_linux': f'ffmpeg -i outputs/pipeline/{video_id}/moneyprinter_output.mp4 -vf subtitles=outputs/pipeline/{video_id}/subtitles.srt -c:a copy outputs/pipeline/{video_id}/final.mp4',
        'workflow_order': [
            'run moneyprinter skeleton generation',
            'run subtitle generation/burn-in',
            'run ffmpeg finalize',
        ],
    }
    write_json(bundle_dir / 'commands.json', commands)

    readme = bundle_dir / 'README.txt'
    readme.write_text(
        '\n'.join([
            f'VIDEO_ID: {video_id}',
            '',
            '1) moneyprinter.input.json -> feed sang MoneyPrinter/ShortGPT',
            '2) subtitle.input.json -> feed sang auto-subtitle/custom caption flow',
            '3) finalize.input.json -> feed sang ffmpeg/MoviePy post-process',
            '',
            'Xem commands.json để có command mẫu.',
        ]) + '\n',
        encoding='utf-8',
    )

    return {
        'bundle_dir': str(bundle_dir),
        'moneyprinter_input': str(bundle_dir / 'moneyprinter.input.json'),
        'subtitle_input': str(bundle_dir / 'subtitle.input.json'),
        'finalize_input': str(bundle_dir / 'finalize.input.json'),
        'commands': str(bundle_dir / 'commands.json'),
        'readme': str(readme),
    }
