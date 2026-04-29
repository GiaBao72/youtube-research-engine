from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .analyzer import analyze_video
from .channels import add_favorite_channel, discover_channels, load_favorites
from .config import Settings
from .reporting import write_json, write_markdown_report
from .youtube import collect_video_data


def run_analyze(settings: Settings, url: str) -> dict[str, str]:
    video = collect_video_data(url)

    raw_path = settings.raw_root / f'{video.video_id}.json'
    write_json(raw_path, asdict(video))

    analysis = analyze_video(settings, video)
    analysis_path = settings.raw_root / f'{video.video_id}.analysis.json'
    report_path = settings.reports_root / f'{video.video_id}.md'
    write_json(analysis_path, analysis.to_dict())
    write_markdown_report(report_path, video, analysis)

    return {
        'video_id': video.video_id,
        'raw': str(raw_path),
        'analysis': str(analysis_path),
        'report': str(report_path),
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


def cmd_discover_channels(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[2]
    settings = Settings.load(project_root)
    results = discover_channels(args.topic, api_key=settings.youtube_api_key or '', limit=args.limit)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_save_channel(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[2]
    record = add_favorite_channel(
        project_root=project_root,
        name=args.name,
        url=args.url,
        channel_id=args.channel_id or '',
        topic=args.topic or '',
        note=args.note or '',
        tags=[tag.strip() for tag in (args.tags or '').split(',') if tag.strip()],
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def cmd_list_favorites(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parents[2]
    records = load_favorites(project_root)
    print(json.dumps(records, ensure_ascii=False, indent=2))
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

    discover = sub.add_parser('discover-channels', help='Tìm kênh YouTube theo chủ đề')
    discover.add_argument('topic', help='Chủ đề cần tìm')
    discover.add_argument('--limit', type=int, default=8, help='Số lượng kết quả tối đa')
    discover.set_defaults(func=cmd_discover_channels)

    save = sub.add_parser('save-channel', help='Lưu kênh vào danh sách yêu thích')
    save.add_argument('name', help='Tên kênh')
    save.add_argument('url', help='URL kênh')
    save.add_argument('--channel-id', default='', help='YouTube channel ID')
    save.add_argument('--topic', default='', help='Chủ đề của kênh')
    save.add_argument('--note', default='', help='Ghi chú')
    save.add_argument('--tags', default='', help='Tags, ngăn cách bằng dấu phẩy')
    save.set_defaults(func=cmd_save_channel)

    favorites = sub.add_parser('list-favorites', help='Xem danh sách kênh yêu thích')
    favorites.set_defaults(func=cmd_list_favorites)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
