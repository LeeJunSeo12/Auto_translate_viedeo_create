import os
from pathlib import Path
from typing import Tuple

from app.config import settings


def ensure_job_dirs(job_id: str) -> Tuple[Path, Path]:
    base = Path(settings.base_data_dir)
    work = base / "work" / job_id
    results = base / "results" / job_id
    work.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    return work, results


def job_paths(job_id: str) -> dict:
    work, results = ensure_job_dirs(job_id)
    return {
        "work": work,
        "results": results,
        "video": work / "input_video.mp4",
        "audio": work / "input_audio.mp3",
        "subs": work / "subtitles_ko.srt",
        "ko_text": work / "korean_text.txt",
        "tts_audio": work / "korean_audio.mp3",
        "out_video": results / "translated_video.mp4",
        "log": work / "job.log",
    }
