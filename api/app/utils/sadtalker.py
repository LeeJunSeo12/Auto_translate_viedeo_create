import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.config import settings
from app.utils.logging import get_logger
from app.utils.media import run_cmd


logger = get_logger(__name__)


def ensure_wav_16k_mono(input_audio: Path, out_wav: Path) -> Path:
    """Convert any audio to 16kHz mono WAV for SadTalker.

    Always re-encode to avoid codec surprises.
    """
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_audio),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(out_wav),
    ]
    run_cmd(cmd, timeout=60 * 5)
    return out_wav


def _find_latest_mp4(dir_path: Path) -> Optional[Path]:
    candidates = sorted(dir_path.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def run_sadtalker(source_image: Path, audio_wav_16k: Path, out_video: Path, preprocess: str = "full", still: bool = True, size: int = 256) -> None:
    """Run SadTalker inference.py as a subprocess and copy the resulting mp4 to out_video.

    Requirements:
    - settings.sadtalker_repo must point to the SadTalker repo root (contains inference.py)
    - settings.sadtalker_checkpoint_dir must contain downloaded checkpoints
    """
    repo = Path(settings.sadtalker_repo)
    if not repo.exists():
        raise RuntimeError(f"SadTalker repo not found: {repo}. Set SADTALKER_REPO env var correctly.")
    inference_py = repo / "inference.py"
    if not inference_py.exists():
        raise RuntimeError(f"SadTalker inference.py not found at {inference_py}")

    # Prepare result dir inside the job workspace
    result_dir = out_video.parent / "sadtalker_results"
    result_dir.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        sys.executable,
        str(inference_py),
        "--driven_audio",
        str(audio_wav_16k),
        "--source_image",
        str(source_image),
        "--checkpoint_dir",
        str(settings.sadtalker_checkpoint_dir),
        "--result_dir",
        str(result_dir),
        "--preprocess",
        preprocess,
        "--batch_size",
        "2",
        "--size",
        str(size),
    ]
    if still:
        cmd.append("--still")

    logger.info("Running SadTalker: %s", " ".join(cmd))
    # Use raw subprocess here to control CWD for relative paths used inside the repo
    completed = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    if completed.stdout:
        logger.info("SadTalker stdout: %s", completed.stdout[:2000])
    if completed.stderr:
        logger.info("SadTalker stderr: %s", completed.stderr[:2000])
    if completed.returncode != 0:
        raise RuntimeError(f"SadTalker failed with code {completed.returncode}: {completed.stderr}")

    produced = _find_latest_mp4(result_dir)
    if not produced or not produced.exists():
        raise RuntimeError("SadTalker did not produce an MP4 output in result dir")

    out_video.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(produced, out_video)


def add_subtitles_soft(input_video: Path, subs_path: Path, out_video: Path) -> None:
    """Add SRT subtitles as a soft track (mov_text) without re-encoding video/audio."""
    if not subs_path.exists() or subs_path.stat().st_size == 0:
        shutil.copy2(input_video, out_video)
        return
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(subs_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-map",
        "1:0",
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        str(out_video),
    ]
    run_cmd(cmd, timeout=60 * 10)


