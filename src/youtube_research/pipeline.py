from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .reporting import write_json


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.strip() + '\n', encoding='utf-8')


def _linux_scripts(video_id: str) -> dict[str, str]:
    moneyprinter = f"""#!/usr/bin/env bash
set -euo pipefail
BUNDLE_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"
echo \"[moneyprinter] Bundle: $BUNDLE_DIR\"
echo \"Edit MONEYPRINTER_DIR if repo không nằm cạnh youtube-research-engine\"
MONEYPRINTER_DIR=\"${{MONEYPRINTER_DIR:-../MoneyPrinter}}\"
INPUT_JSON=\"$BUNDLE_DIR/moneyprinter.input.json\"
cd \"$MONEYPRINTER_DIR\"
python main.py --input \"$INPUT_JSON\"
"""
    subtitle = f"""#!/usr/bin/env bash
set -euo pipefail
BUNDLE_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"
echo \"[subtitle] Bundle: $BUNDLE_DIR\"
echo \"Edit input/output path nếu tool subtitle bạn dùng khác command mẫu\"
INPUT_VIDEO=\"$BUNDLE_DIR/moneyprinter_output.mp4\"
OUTPUT_SRT=\"$BUNDLE_DIR/subtitles.srt\"
python -m auto_subtitle \"$INPUT_VIDEO\" --output_srt \"$OUTPUT_SRT\"
"""
    finalize = f"""#!/usr/bin/env bash
set -euo pipefail
BUNDLE_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"
echo \"[finalize] Bundle: $BUNDLE_DIR\"
INPUT_VIDEO=\"$BUNDLE_DIR/moneyprinter_output.mp4\"
INPUT_SRT=\"$BUNDLE_DIR/subtitles.srt\"
OUTPUT_VIDEO=\"$BUNDLE_DIR/final.mp4\"
ffmpeg -y -i \"$INPUT_VIDEO\" -vf subtitles=\"$INPUT_SRT\" -c:a copy \"$OUTPUT_VIDEO\"
"""
    run_all = f"""#!/usr/bin/env bash
set -euo pipefail
DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"
\"$DIR/run_moneyprinter.sh\"
echo \"Nếu MoneyPrinter không tự xuất ra $DIR/moneyprinter_output.mp4 thì hãy copy/rename output vào đó trước khi chạy bước tiếp.\"
\"$DIR/run_subtitle.sh\"
\"$DIR/run_finalize.sh\"
echo \"Done: $DIR/final.mp4\"
"""
    return {
        'run_moneyprinter.sh': moneyprinter,
        'run_subtitle.sh': subtitle,
        'run_finalize.sh': finalize,
        'run_all.sh': run_all,
    }


def _windows_scripts(video_id: str) -> dict[str, str]:
    moneyprinter = r"""@echo off
setlocal
set BUNDLE_DIR=%~dp0
echo [moneyprinter] Bundle: %BUNDLE_DIR%
if "%MONEYPRINTER_DIR%"=="" set MONEYPRINTER_DIR=..\MoneyPrinter
set INPUT_JSON=%BUNDLE_DIR%moneyprinter.input.json
cd /d "%MONEYPRINTER_DIR%"
python main.py --input "%INPUT_JSON%"
"""
    subtitle = r"""@echo off
setlocal
set BUNDLE_DIR=%~dp0
echo [subtitle] Bundle: %BUNDLE_DIR%
set INPUT_VIDEO=%BUNDLE_DIR%moneyprinter_output.mp4
set OUTPUT_SRT=%BUNDLE_DIR%subtitles.srt
python -m auto_subtitle "%INPUT_VIDEO%" --output_srt "%OUTPUT_SRT%"
"""
    finalize = r"""@echo off
setlocal
set BUNDLE_DIR=%~dp0
echo [finalize] Bundle: %BUNDLE_DIR%
set INPUT_VIDEO=%BUNDLE_DIR%moneyprinter_output.mp4
set INPUT_SRT=%BUNDLE_DIR%subtitles.srt
set OUTPUT_VIDEO=%BUNDLE_DIR%final.mp4
ffmpeg -y -i "%INPUT_VIDEO%" -vf subtitles="%INPUT_SRT%" -c:a copy "%OUTPUT_VIDEO%"
"""
    run_all = r"""@echo off
setlocal
set DIR=%~dp0
call "%DIR%run_moneyprinter.bat"
echo Nếu MoneyPrinter chưa xuất đúng file moneyprinter_output.mp4 thì copy/rename output vào bundle trước khi chạy tiếp.
call "%DIR%run_subtitle.bat"
call "%DIR%run_finalize.bat"
echo Done: %DIR%final.mp4
"""
    return {
        'run_moneyprinter.bat': moneyprinter,
        'run_subtitle.bat': subtitle,
        'run_finalize.bat': finalize,
        'run_all.bat': run_all,
    }


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
        'moneyprinter_note': 'Đặt repo MoneyPrinter cạnh repo này hoặc set env MONEYPRINTER_DIR trước khi chạy script.',
        'moneyprinter_command_linux': f'cd ../MoneyPrinter && python main.py --input ../youtube-research/outputs/pipeline/{video_id}/moneyprinter.input.json',
        'moneyprinter_command_windows': f'cd ..\\MoneyPrinter && python main.py --input ..\\youtube-research-engine\\outputs\\pipeline\\{video_id}\\moneyprinter.input.json',
        'subtitle_command_linux': f'python -m auto_subtitle outputs/pipeline/{video_id}/moneyprinter_output.mp4 --output_srt outputs/pipeline/{video_id}/subtitles.srt',
        'subtitle_command_windows': f'python -m auto_subtitle outputs\\pipeline\\{video_id}\\moneyprinter_output.mp4 --output_srt outputs\\pipeline\\{video_id}\\subtitles.srt',
        'ffmpeg_command_linux': f'ffmpeg -i outputs/pipeline/{video_id}/moneyprinter_output.mp4 -vf subtitles=outputs/pipeline/{video_id}/subtitles.srt -c:a copy outputs/pipeline/{video_id}/final.mp4',
        'ffmpeg_command_windows': f'ffmpeg -i outputs\\pipeline\\{video_id}\\moneyprinter_output.mp4 -vf subtitles=outputs\\pipeline\\{video_id}\\subtitles.srt -c:a copy outputs\\pipeline\\{video_id}\\final.mp4',
        'workflow_order': [
            'run moneyprinter skeleton generation',
            'put generated video into bundle as moneyprinter_output.mp4 if needed',
            'run subtitle generation/burn-in',
            'run ffmpeg finalize',
        ],
    }
    write_json(bundle_dir / 'commands.json', commands)

    for name, content in _linux_scripts(video_id).items():
        path = bundle_dir / name
        _write_text(path, content)
        path.chmod(0o755)

    for name, content in _windows_scripts(video_id).items():
        _write_text(bundle_dir / name, content)

    readme = bundle_dir / 'README.txt'
    readme.write_text(
        '\n'.join([
            f'VIDEO_ID: {video_id}',
            '',
            'Files chính:',
            '- moneyprinter.input.json -> feed sang MoneyPrinter/ShortGPT',
            '- subtitle.input.json -> feed sang auto-subtitle/custom caption flow',
            '- finalize.input.json -> feed sang ffmpeg/MoviePy post-process',
            '- commands.json -> command mẫu',
            '- run_moneyprinter(.sh/.bat), run_subtitle(.sh/.bat), run_finalize(.sh/.bat), run_all(.sh/.bat) -> script chạy nhanh',
            '',
            'Lưu ý: output của MoneyPrinter mỗi repo có thể khác. Nếu chưa ra đúng tên file, hãy copy/rename video khung thành moneyprinter_output.mp4 trong bundle này rồi chạy subtitle/finalize.',
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
        'linux_run_all': str(bundle_dir / 'run_all.sh'),
        'windows_run_all': str(bundle_dir / 'run_all.bat'),
    }
