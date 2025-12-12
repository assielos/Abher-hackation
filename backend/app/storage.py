from __future__ import annotations

from pathlib import Path
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "data" / "reports"
VIDEOS_DIR = BASE_DIR / "data" / "videos"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)


def save_report_file(request_id: int, filename: str, content: bytes) -> Path:
    safe_name = f"request_{request_id}_{filename}"
    dest = REPORTS_DIR / safe_name
    dest.write_bytes(content)
    return dest


def save_video_file(request_id: int, filename: str, content: bytes) -> Path:
    safe_name = f"request_{request_id}_{filename}"
    dest = VIDEOS_DIR / safe_name
    dest.write_bytes(content)
    return dest


def get_video_file(request_id: int) -> Tuple[Path, bool]:
    pattern = f"request_{request_id}_"
    for file in VIDEOS_DIR.iterdir():
        if file.name.startswith(pattern):
            return file, True
    return VIDEOS_DIR / "", False

