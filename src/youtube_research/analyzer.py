from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from openai import OpenAI

from .config import Settings
from .youtube import VideoData


PROMPT = '''Bạn là chuyên gia research nội dung YouTube.
Phân tích video dựa trên transcript và metadata.
Trả về JSON hợp lệ với schema:
{
  "summary": "...",
  "target_audience": "...",
  "main_angle": "...",
  "hook_analysis": "...",
  "structure": ["..."],
  "view_drivers": ["..."],
  "notable_moments": [
    {"time": "MM:SS", "reason": "...", "quote": "..."}
  ],
  "title_variants": ["..."],
  "hook_variants": ["..."],
  "shorts_ideas": ["..."],
  "next_video_ideas": ["..."],
  "rewrite_outline": ["..."],
  "deep_analysis": {
    "scores": {
      "hook_strength": 0,
      "pacing": 0,
      "shorts_potential": 0,
      "clarity": 0,
      "retention_potential": 0
    },
    "content_drivers": ["..."],
    "timeline_map": [
      {"time": "MM:SS", "label": "...", "why_it_matters": "..."}
    ],
    "weak_spots": ["..."],
    "best_cut_moments": [
      {"time": "MM:SS", "reason": "...", "clip_angle": "..."}
    ],
    "rewrite_modes": {
      "viral": ["..."],
      "educational": ["..."],
      "storytelling": ["..."]
    }
  }
}
Yêu cầu:
- Viết bằng tiếng Việt.
- Cụ thể, ngắn gọn, thực dụng.
- Không bịa thông tin ngoài transcript.
- title_variants: 5 mục
- hook_variants: 5 mục
- shorts_ideas: 3-5 mục
- next_video_ideas: 3-5 mục
- scores chấm theo thang 10
- deep_analysis phải hữu ích cho editor/writer/strategist
'''


@dataclass
class AnalysisResult:
    summary: str
    target_audience: str
    main_angle: str
    hook_analysis: str
    structure: list[str]
    view_drivers: list[str]
    notable_moments: list[dict[str, Any]]
    title_variants: list[str]
    hook_variants: list[str]
    shorts_ideas: list[str]
    next_video_ideas: list[str]
    rewrite_outline: list[str]
    deep_analysis: dict[str, Any]
    analysis_mode: str = 'llm'
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _transcript_to_text(video: VideoData, limit_chars: int = 18000) -> str:
    lines = []
    for item in video.transcript:
        start = int(item['start'])
        mm = start // 60
        ss = start % 60
        lines.append(f'[{mm:02d}:{ss:02d}] {item["text"]}')
    text = '\n'.join(lines)
    return text[:limit_chars]


def analyze_video(settings: Settings, video: VideoData) -> AnalysisResult:
    if not settings.api_key:
        return build_fallback_analysis(video, 'Thiếu OPENAI_API_KEY trong .env')

    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    payload = {
        'video': {
            'video_id': video.video_id,
            'url': video.url,
            'title': video.title,
            'channel': video.channel,
            'duration': video.duration,
            'description': (video.description or '')[:4000],
        },
        'transcript': _transcript_to_text(video),
    }

    try:
        response = client.chat.completions.create(
            model=settings.model,
            temperature=0.4,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': PROMPT},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
            ],
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        if 'deep_analysis' not in data:
            data['deep_analysis'] = default_deep_analysis()
        return AnalysisResult(**data, analysis_mode='llm')
    except Exception as exc:
        return build_fallback_analysis(video, f'{type(exc).__name__}: {exc}')


def default_deep_analysis() -> dict[str, Any]:
    return {
        'scores': {
            'hook_strength': 5,
            'pacing': 5,
            'shorts_potential': 5,
            'clarity': 5,
            'retention_potential': 5,
        },
        'content_drivers': [],
        'timeline_map': [],
        'weak_spots': [],
        'best_cut_moments': [],
        'rewrite_modes': {
            'viral': [],
            'educational': [],
            'storytelling': [],
        },
    }


def build_fallback_analysis(video: VideoData, reason: str) -> AnalysisResult:
    transcript_text = _transcript_to_text(video, limit_chars=6000)
    lines = [line for line in transcript_text.splitlines() if line.strip()]
    first_lines = lines[:8]
    first_quotes = [line.split('] ', 1)[1] for line in first_lines[:5] if '] ' in line]

    title = video.title or 'Video YouTube này'
    channel = video.channel or 'kênh chưa rõ'

    structure = [
        'Mở đầu vấn đề/chủ đề chính của video',
        'Triển khai bằng ví dụ hoặc luận điểm trong transcript',
        'Đẩy ý chính bằng các đoạn nhấn mạnh/câu đáng nhớ',
        'Kết lại bằng insight hoặc lời kêu gọi hành động',
    ]

    notable_moments = []
    for line in first_lines[:5]:
        if '] ' not in line:
            continue
        ts, quote = line.split('] ', 1)
        notable_moments.append({
            'time': ts.strip('[]'),
            'reason': 'Đoạn mở đầu hoặc đoạn sớm trong transcript, hữu ích để rà nhanh nội dung.',
            'quote': quote[:180],
        })

    deep = default_deep_analysis()
    deep['scores'] = {
        'hook_strength': 6,
        'pacing': 5,
        'shorts_potential': 6,
        'clarity': 6,
        'retention_potential': 5,
    }
    deep['content_drivers'] = [
        'Chủ đề xuất hiện sớm trong transcript',
        'Có các câu mở đầu có thể dùng làm hook/cut',
    ]
    deep['timeline_map'] = [
        {
            'time': item['time'],
            'label': 'Mốc đáng xem nhanh',
            'why_it_matters': item['reason'],
        }
        for item in notable_moments[:3]
    ]
    deep['weak_spots'] = [
        'Bản fallback chưa đánh giá sâu các đoạn tụt nhịp.',
        'Cần chạy lại LLM để có nhận định sâu hơn về pacing và retention.',
    ]
    deep['best_cut_moments'] = [
        {
            'time': item['time'],
            'reason': 'Có câu nói đủ ngắn để cắt clip thử nghiệm.',
            'clip_angle': item['quote'][:100],
        }
        for item in notable_moments[:3]
    ]
    deep['rewrite_modes'] = {
        'viral': ['Mở mạnh hơn ngay 5 giây đầu', 'Đưa câu gây tò mò lên trước khi giải thích'],
        'educational': ['Nêu bài học chính trước', 'Chia lại nội dung theo 3 ý rõ ràng'],
        'storytelling': ['Mở bằng tình huống', 'Tăng nhịp ở các đoạn chuyển ý'],
    }

    return AnalysisResult(
        summary=(
            f'Fallback mode: chưa lấy được phân tích LLM nên đây là tóm tắt sơ bộ cho "{title}" từ {channel}. '
            f'Cần chạy lại khi API ổn định để có insight sâu hơn.'
        ),
        target_audience='Người đang nghiên cứu nhanh nội dung video để lấy ý chính, hook và ý tưởng tái sử dụng.',
        main_angle='Tạm suy ra từ phần mở đầu transcript và metadata hiện có; chưa phải bản phân tích sâu bằng LLM.',
        hook_analysis='Ưu tiên kiểm tra 30-60 giây đầu transcript vì đó thường là nơi chứa hook. Bản fallback chỉ đánh dấu hướng đọc nhanh.',
        structure=structure,
        view_drivers=[
            'Chủ đề thể hiện ngay ở tiêu đề/video metadata',
            'Các câu mở đầu trong transcript có thể dùng để suy ra hook',
            'Có transcript sẵn nên có thể tiếp tục phân tích thủ công hoặc retry LLM',
        ],
        notable_moments=notable_moments,
        title_variants=[
            f'{title} - bản rút gọn insight chính',
            f'3 ý đáng chú ý từ {title}',
            f'Xem nhanh: {title}',
            f'{title} có gì đáng học?',
            f'Tóm tắt nhanh video từ {channel}',
        ],
        hook_variants=[
            f'Video này mở ra câu hỏi gì ngay từ đầu?',
            f'30 giây đầu của "{title}" có gì đáng chú ý?',
            'Nếu chỉ xem 1 đoạn ngắn, nên xem đoạn nào?',
            'Insight nào có thể tách ra thành clip ngắn?',
            'Điểm nào khiến người xem muốn ở lại tiếp?',
        ],
        shorts_ideas=[quote[:100] for quote in first_quotes[:3]] or [
            'Cắt 1 câu mở đầu mạnh từ transcript',
            'Lấy 1 đoạn giải thích ngắn làm Shorts',
            'Biến 1 insight chính thành clip 30-45 giây',
        ],
        next_video_ideas=[
            f'Phân tích sâu hơn chủ đề của {title}',
            'Tách 1 luận điểm trong video thành video riêng',
            'So sánh video này với 1 video cùng chủ đề',
        ],
        rewrite_outline=[
            'Mở bằng hook rút từ 30 giây đầu',
            'Nêu vấn đề/chủ đề chính',
            'Đưa 2-3 luận điểm hoặc ví dụ nổi bật',
            'Kết bằng insight ngắn gọn + CTA',
        ],
        deep_analysis=deep,
        analysis_mode='fallback',
        fallback_reason=reason,
    )
