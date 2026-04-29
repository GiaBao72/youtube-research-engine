from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    workspace_root: Path
    project_root: Path
    output_root: Path
    raw_root: Path
    reports_root: Path
    db_path: Path
    api_key: str | None
    youtube_api_key: str | None
    base_url: str
    model: str
    language: str

    @classmethod
    def load(cls, project_root: Path) -> 'Settings':
        _load_dotenv(project_root / '.env')
        output_root = project_root / 'outputs'
        raw_root = output_root / 'raw'
        reports_root = output_root / 'reports'
        db_path = output_root / 'youtube_research.duckdb'
        raw_root.mkdir(parents=True, exist_ok=True)
        reports_root.mkdir(parents=True, exist_ok=True)
        return cls(
            workspace_root=project_root.parent,
            project_root=project_root,
            output_root=output_root,
            raw_root=raw_root,
            reports_root=reports_root,
            db_path=db_path,
            api_key=os.getenv('OPENAI_API_KEY'),
            youtube_api_key=os.getenv('YOUTUBE_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            language=os.getenv('YRE_LANGUAGE', 'vi'),
        )
