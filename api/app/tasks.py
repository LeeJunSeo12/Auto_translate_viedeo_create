import json
import uuid
from pathlib import Path
from typing import Dict

import whisper

from app.celery_app import celery_app
from app.config import settings
from app.providers.factory import get_tts_provider
from app.utils.logging import get_logger
from app.utils.media import download_video, extract_audio, mux_video_audio
from app.utils.progress import append_log, set_result, set_status
from app.utils.storage import job_paths
from app.utils.text import split_text_for_tts


logger = get_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_job(self, job_id: str, youtube_url: str, options: Dict | None = None) -> str:
    paths = job_paths(job_id)

    try:
        set_status(job_id, "RUNNING", progress=1)
        append_log(job_id, "Downloading video...")
        download_video(youtube_url, Path(paths["video"]))

        set_status(job_id, "RUNNING", progress=10)
        append_log(job_id, "Extracting audio...")
        extract_audio(Path(paths["video"]), Path(paths["audio"]))

        set_status(job_id, "RUNNING", progress=25)
        append_log(job_id, f"Loading STT model {settings.whisper_model} (USE_WHISPERX={settings.use_whisperx})...")

        text: str = ""
        segments = []

        used_whisperx = False
        if settings.use_whisperx:
            try:
                import torch  # type: ignore
                import whisperx  # type: ignore

                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                append_log(job_id, f"WhisperX device={device} compute_type={compute_type}")
                wx_model = whisperx.load_model(settings.whisper_model, device, compute_type=compute_type)
                result = wx_model.transcribe(str(paths["audio"]), batch_size=16, language="ko", task="translate")
                text = (result.get("text") or "").strip()
                segments = result.get("segments") or []
                try:
                    align_model, metadata = whisperx.load_align_model(language_code="ko", device=device)
                    aligned = whisperx.align(segments, align_model, metadata, str(paths["audio"]), device=device)
                    segments = aligned.get("segments") or segments
                    append_log(job_id, "WhisperX alignment applied")
                except Exception as e:  # noqa: BLE001
                    append_log(job_id, f"WhisperX alignment skipped: {e}")
                used_whisperx = True
            except Exception as e:  # noqa: BLE001
                append_log(job_id, f"WhisperX unavailable; fallback to Whisper: {e}")

        if not used_whisperx:
            model = whisper.load_model(settings.whisper_model)
            result = model.transcribe(str(paths["audio"]), task="translate", language="ko")
            text = (result.get("text") or "").strip()
            segments = result.get("segments") or []

        Path(paths["ko_text"]).write_text(text, encoding="utf-8")

        # naive SRT export
        srt_lines = []
        for i, segment in enumerate(segments, start=1):
            s = float(segment.get("start", 0.0))
            e = float(segment.get("end", 0.0))

            def fmt(t: float) -> str:
                hh = int(t // 3600)
                mm = int((t % 3600) // 60)
                ss = int(t % 60)
                ms = int((t - int(t)) * 1000)
                return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

            srt_lines.append(str(i))
            srt_lines.append(f"{fmt(s)} --> {fmt(e)}")
            srt_lines.append((segment.get("text") or "").strip())
            srt_lines.append("")
        Path(paths["subs"]).write_text("\n".join(srt_lines), encoding="utf-8")

        set_status(job_id, "RUNNING", progress=55)
        append_log(job_id, "Synthesizing Korean TTS...")
        provider = get_tts_provider()
        chunks = split_text_for_tts(text)
        provider.synthesize(chunks, Path(paths["tts_audio"]))

        set_status(job_id, "RUNNING", progress=80)
        append_log(job_id, "Muxing video + KR audio + subtitles...")
        mux_video_audio(Path(paths["video"]), Path(paths["tts_audio"]), Path(paths["out_video"]), Path(paths["subs"]))

        set_status(job_id, "DONE", progress=100)
        result_url = f"/results/{job_id}/translated_video.mp4"
        set_result(job_id, result_url)
        append_log(job_id, f"Job completed. Result: {result_url}")
        return job_id
    except Exception as e:  # noqa: BLE001
        append_log(job_id, f"Error: {e}")
        set_status(job_id, "FAILED", progress=0, error=str(e))
        raise
