import subprocess
from pathlib import Path
from typing import List, Optional

from app.utils.logging import get_logger


logger = get_logger(__name__)


class CommandError(RuntimeError):
    pass


def run_cmd(cmd: List[str], timeout: Optional[int] = None) -> None:
    logger.info("run_cmd %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        raise CommandError(f"Command failed: {cmd} -> {exc}") from exc


def download_video(youtube_url: str, out_video: Path) -> None:
    out_video.parent.mkdir(parents=True, exist_ok=True)
    # Download best mp4
    cmd = [
        "yt-dlp",
        "-f",
        "mp4",
        "-o",
        str(out_video),
        youtube_url,
    ]
    run_cmd(cmd, timeout=60 * 30)


def extract_audio(input_video: Path, out_audio: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vn",
        "-acodec",
        "libmp3lame",
        str(out_audio),
    ]
    run_cmd(cmd, timeout=60 * 10)


def build_mux_command(video: Path, audio: Path, out_video: Path, subs: Optional[Path] = None) -> List[str]:
    # Replace audio, keep video; optional soft subtitles
    cmd: List[str] = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
    ]
    if subs and subs.exists():
        cmd += ["-i", str(subs)]
    cmd += [
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
    ]
    if subs and subs.exists():
        cmd += ["-map", "2:0", "-c:s", "mov_text"]
    cmd += ["-shortest", str(out_video)]
    return cmd


def mux_video_audio(video: Path, audio: Path, out_video: Path, subs: Optional[Path] = None) -> None:
    cmd = build_mux_command(video, audio, out_video, subs)
    run_cmd(cmd, timeout=60 * 20)
