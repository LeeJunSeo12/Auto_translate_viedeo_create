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
        completed = subprocess.run(cmd, check=True, timeout=timeout, capture_output=True, text=True)
        if completed.stdout:
            logger.info("stdout: %s", completed.stdout[:2000])
        if completed.stderr:
            logger.info("stderr: %s", completed.stderr[:2000])
    except subprocess.CalledProcessError as exc:
        msg = exc.stderr if isinstance(exc.stderr, str) and exc.stderr else str(exc)
        raise CommandError(f"Command failed: {cmd} -> {msg}") from exc


def download_video(youtube_url: str, out_video: Path) -> None:
    out_video.parent.mkdir(parents=True, exist_ok=True)
    # Download best video+audio merged as mp4 (avoid video-only DASH)
    # Prefer mp4/m4a to ensure ffmpeg compatibility inside container
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "bestvideo[ext=mp4][vcodec!=av01]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_video),
        youtube_url,
    ]
    run_cmd(cmd, timeout=60 * 30)


def extract_audio(input_video: Path, out_audio: Path) -> None:
    """Extract audio as WAV (PCM) to maximize compatibility inside containers.

    Using MP3 may fail when libmp3lame is not available or licensed differently.
    """
    # Prefer WAV output regardless of extension in storage; ensure .wav
    out_path = out_audio.with_suffix(".wav") if out_audio.suffix.lower() != ".wav" else out_audio
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-map",
        "0:a:0?",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(out_path),
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


def extract_first_frame(input_video: Path, out_image: Path) -> None:
    """Extract the first clear face frame for SadTalker as reference image."""
    cmd = [
        "ffmpeg", "-y", "-i", str(input_video),
        "-vf", "select='eq(n,0)'", "-q:v", "2", str(out_image)
    ]
    run_cmd(cmd, timeout=60)
