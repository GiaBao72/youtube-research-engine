from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .analyzer import analyze_video
from .config import Settings
from .design_payload import write_design_payload
from .reporting import write_json, write_markdown_report
from .youtube import collect_video_data


def run_analyze(settings: Settings, url: str) -> dict[str, str]:
    video = collect_video_data(url)

    raw_path = settings.raw_root / f'{video.video_id}.json'
    write_json(raw_path, asdict(video))

    analysis = analyze_video(settings, video)
    analysis_path = settings.raw_root / f'{video.video_id}.analysis.json'
    report_path = settings.reports_root / f'{video.video_id}.md'
    design_path = settings.design_root / f'{video.video_id}.design.json'
    write_json(analysis_path, analysis.to_dict())
    write_markdown_report(report_path, video, analysis)
    write_design_payload(design_path, asdict(video), analysis.to_dict())

    return {
        'video_id': video.video_id,
        'raw': str(raw_path),
        'analysis': str(analysis_path),
        'report': str(report_path),
        'design_payload': str(design_path),
    }


def run_design_payload(settings: Settings, video_id: str) -> dict[str, str]:
    raw_path = settings.raw_root / f'{video_id}.json'
    analysis_path = settings.raw_root / f'{video_id}.analysis.json'
    if not raw_path.exists():
        raise FileNotFoundError(f'Không thấy raw file cho video_id={video_id}')
    if not analysis_path.exists():
        raise FileNotFoundError(f'Không thấy analysis file cho video_id={video_id}')

    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    analysis = json.loads(analysis_path.read_text(encoding='utf-8'))
    design_path = settings.design_root / f'{video_id}.design.json'
    write_design_payload(design_path, raw, analysis)
    return {
        'video_id': video_id,
        'raw': str(raw_path),
        'analysis': str(analysis_path),
        'design_payload': str(design_path),
    }


def cmd_analyze(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[2]
    settings = Settings.load(project_root)
    result = run_analyze(settings, args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[2]
    settings = Settings.load(project_root)
    results = []

    for url in args.urls:
        try:
            results.append(run_analyze(settings, url))
        except Exception as exc:
            results.append({
                'url': url,
                'error': f'{type(exc).__name__}: {exc}',
            })

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_design_payload(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[2]
    settings = Settings.load(project_root)
    result = run_design_payload(settings, args.video_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='youtube-research')
    sub = parser.add_subparsers(dest='command', required=True)

    analyze = sub.add_parser('analyze', help='Phân tích 1 video YouTube')
    analyze.add_argument('url', help='YouTube URL hoặc video ID')
    analyze.set_defaults(func=cmd_analyze)

    batch = sub.add_parser('batch', help='Phân tích nhiều video YouTube')
    batch.add_argument('urls', nargs='+', help='Danh sách YouTube URL hoặc video ID')
    batch.set_defaults(func=cmd_batch)

    design_payload = sub.add_parser('design-payload', help='Sinh design payload từ file phân tích có sẵn')
    design_payload.add_argument('video_id', help='Video ID đã có raw + analysis JSON')
    design_payload.set_defaults(func=cmd_design_payload)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
