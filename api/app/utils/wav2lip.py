import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

from app.config import settings
from app.utils.logging import get_logger
from app.utils.media import run_cmd


logger = get_logger(__name__)


def ensure_wav_16k_mono(input_audio: Path, out_wav: Path) -> Path:
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


def run_wav2lip_sync_api(face_video_or_image: Path, audio_wav_16k: Path, out_video: Path, timeout_sec: int = 60 * 20) -> None:
    """Use Sync.so commercial Wav2Lip API to generate lipsynced video.

    Requires SYNC_API_KEY in env. Downloads the resulting video to out_video.
    """
    api_key = settings.sync_api_key
    base_url = settings.sync_base_url.rstrip("/")
    if not api_key:
        raise RuntimeError("SYNC_API_KEY is required to use Wav2Lip commercial API")

    # 1) Upload files to a temporary hosting if necessary. The Sync API expects URLs.
    # For simplicity here, we use a pre-signed upload via a minimal file server assumption.
    # In production, replace with your own file storage and provide URLs.
    # As a fallback for local usage, we can use file:// URLs only if the API supports it (likely not).
    # So we implement a naive upload to tmpfiles.org (anonymous) or similar; but to avoid external deps,
    # we will error if URLs are not provided via options. The caller should provide accessible URLs.
    raise_if_no_public_url = True
    video_url = os.getenv("W2L_VIDEO_URL")
    audio_url = os.getenv("W2L_AUDIO_URL")
    if not video_url or not audio_url:
        # As a minimal helper, if not provided, try to spin up an error explaining requirement.
        raise RuntimeError("W2L_VIDEO_URL and W2L_AUDIO_URL must be provided as public URLs for Sync API")

    # 2) Submit generation job
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "input": [
            {"type": "video", "url": video_url},
            {"type": "audio", "url": audio_url},
        ],
        "model": "lipsync-2",
        "options": {"sync_mode": "cut_off"},
        "outputFileName": "auto_video"
    }
    create_url = f"{base_url}/generations"
    resp = requests.post(create_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    job_id = data.get("id") or data.get("data", {}).get("id")
    if not job_id:
        raise RuntimeError(f"Sync API: missing job id in response: {data}")

    # 3) Poll
    get_url = f"{base_url}/generations/{job_id}"
    start = time.time()
    status = None
    output_url: Optional[str] = None
    while time.time() - start < timeout_sec:
        time.sleep(10)
        r = requests.get(get_url, headers=headers, timeout=30)
        r.raise_for_status()
        g = r.json()
        status = g.get("status") or g.get("data", {}).get("status")
        output_url = g.get("output_url") or g.get("data", {}).get("outputUrl")
        if status in ("COMPLETED", "FAILED"):
            break
    if status != "COMPLETED" or not output_url:
        raise RuntimeError(f"Sync API generation failed or timed out. status={status}")

    # 4) Download
    out_video.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(output_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(out_video, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


def run_wav2lip_local(face_video_or_image: Path, audio_path: Path, out_video: Path) -> None:
    repo = Path(settings.wav2lip_repo)
    if not repo.exists():
        raise RuntimeError(f"Wav2Lip repo not found: {repo}. Set WAV2LIP_REPO env var correctly.")
    inference_py = repo / "inference.py"
    if not inference_py.exists():
        raise RuntimeError(f"Wav2Lip inference.py not found at {inference_py}")

    ckpt = Path(settings.wav2lip_checkpoint_path)
    if not ckpt.exists():
        raise RuntimeError(f"Wav2Lip checkpoint not found at {ckpt}. Set WAV2LIP_CKPT env var correctly.")

    out_video.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        os.environ.get("PYTHON", "python"),
        str(inference_py),
        "--checkpoint_path",
        str(ckpt),
        "--face",
        str(face_video_or_image),
        "--audio",
        str(audio_path),
        "--outfile",
        str(out_video),
        "--static",
        "False",
        "--wav2lip_batch_size",
        "32",
    ]
    logger.info("Running Wav2Lip (local): %s", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    if completed.stdout:
        logger.info("Wav2Lip stdout: %s", completed.stdout[:2000])
    if completed.stderr:
        logger.info("Wav2Lip stderr: %s", completed.stderr[:2000])
    if completed.returncode != 0:
        raise RuntimeError(f"Wav2Lip failed with code {completed.returncode}: {completed.stderr}")


def run_wav2lip(face_video_or_image: Path, audio_path: Path, out_video: Path) -> None:
    """Auto-select Sync API if configured with URLs; otherwise run local inference."""
    api_key = settings.sync_api_key
    video_url = os.getenv("W2L_VIDEO_URL")
    audio_url = os.getenv("W2L_AUDIO_URL")
    if api_key and video_url and audio_url:
        run_wav2lip_sync_api(face_video_or_image, audio_path, out_video)
        return
    run_wav2lip_local(face_video_or_image, audio_path, out_video)



