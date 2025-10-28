import json
import uuid
from pathlib import Path
from typing import Dict

import whisper

from app.celery_app import celery_app
from app.config import settings
from app.providers.factory import get_tts_provider
from app.utils.logging import get_logger
from app.utils.media import download_video, extract_audio, mux_video_audio, extract_first_frame
from app.utils.progress import append_log, set_result, set_status
from app.utils.storage import job_paths
from app.utils.text import split_text_for_tts, translate_to_korean_natural, contains_hangul
from app.utils.sadtalker import ensure_wav_16k_mono as ensure_wav_16k_mono_sad
from app.utils.sadtalker import run_sadtalker, add_subtitles_soft
from app.utils.wav2lip import ensure_wav_16k_mono as ensure_wav_16k_mono_w2l
from app.utils.wav2lip import run_wav2lip


logger = get_logger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}, name="process_job")
def process_job(self, job_id: str, youtube_url: str, options: Dict | None = None) -> str:
    paths = job_paths(job_id)

    try:
        set_status(job_id, "RUNNING", progress=1)
        append_log(job_id, f"Job accepted. options={json.dumps(options or {})}")
        append_log(job_id, "Downloading video...")
        download_video(youtube_url, Path(paths["video"]))

        set_status(job_id, "RUNNING", progress=10)
        append_log(job_id, "Extracting audio...")
        try:
            extract_audio(Path(paths["video"]), Path(paths["audio"]))
        except Exception as e:  # noqa: BLE001
            append_log(job_id, f"Audio extraction failed: {e}. Trying ffmpeg re-mux to MP4 with audio...")
            # Some DASH videos may download as video-only; try merging bestaudio via ffmpeg once
            # Attempt to let ffmpeg copy streams without re-encoding, then retry extraction
            import subprocess
            tmp_fixed = Path(paths["work"]) / "fixed_with_audio.mp4"
            subprocess.run([
                "ffmpeg","-y","-i", str(paths["video"]), "-c","copy", str(tmp_fixed)
            ], check=False)
            extract_audio(tmp_fixed, Path(paths["audio"]))

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
                num_devices = torch.cuda.device_count() if device == "cuda" else 0
                if device == "cuda":
                    name = torch.cuda.get_device_name(0)
                    cc = torch.cuda.get_device_capability(0)
                    append_log(job_id, f"CUDA devices={num_devices}, name={name}, capability={cc}")
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
                append_log(job_id, f"WhisperX unavailable; fallback to Whisper on CPU: {e}")

        if not used_whisperx:
            # Try CUDA first if available, otherwise gracefully fall back to CPU
            try:
                import torch  # type: ignore

                device = "cuda" if torch.cuda.is_available() else "cpu"
                if device == "cuda":
                    name = torch.cuda.get_device_name(0)
                    cc = torch.cuda.get_device_capability(0)
                    append_log(job_id, f"Whisper device=cuda ({name}, capability={cc})")
                else:
                    append_log(job_id, "Whisper device=cpu")
                model = whisper.load_model(settings.whisper_model, device=device)
            except Exception as e:  # noqa: BLE001
                append_log(job_id, f"Whisper CUDA load failed, falling back to CPU: {e}")
                model = whisper.load_model(settings.whisper_model, device="cpu")

            result = model.transcribe(str(paths["audio"]), task="translate", language="ko")
            text = (result.get("text") or "").strip()
            segments = result.get("segments") or []

        # Translate to Korean if needed (ensure natural Korean output)
        if not contains_hangul(text):
            append_log(job_id, "Translating to Korean...")
            text = translate_to_korean_natural(text)
        Path(paths["ko_text"]).write_text(text, encoding="utf-8")

        # Translate full text once for naturalness
        append_log(job_id, "Translating full transcript to Korean...")
        ko_full = translate_to_korean_natural(text)
        Path(paths["ko_text"]).write_text(ko_full, encoding="utf-8")

        # Korean subtitles per-segment by aligning translated text roughly by length
        # Simple proportional mapping: split ko_full by number of segments
        if segments:
            approx_len = max(1, len(ko_full) // len(segments))
            ko_segments = []
            idx = 0
            for _ in segments:
                ko_segments.append(ko_full[idx : idx + approx_len].strip())
                idx += approx_len
            # append remainder to last
            if ko_segments:
                ko_segments[-1] = (ko_segments[-1] + " " + ko_full[idx:]).strip()
        else:
            ko_segments = []

        # SRT export in Korean
        srt_lines = []
        def fmt(t: float) -> str:
            hh = int(t // 3600)
            mm = int((t % 3600) // 60)
            ss = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

        for i, segment in enumerate(segments, start=1):
            s = float(segment.get("start", 0.0))
            e = float(segment.get("end", 0.0))
            text_ko = (ko_segments[i - 1] if i - 1 < len(ko_segments) else "").strip()
            if not text_ko:
                text_ko = (segment.get("text") or "").strip()
                text_ko = translate_to_korean_natural(text_ko)
            srt_lines.append(str(i))
            srt_lines.append(f"{fmt(s)} --> {fmt(e)}")
            srt_lines.append(text_ko)
            srt_lines.append("")
        Path(paths["subs"]).write_text("\n".join(srt_lines), encoding="utf-8")

        set_status(job_id, "RUNNING", progress=55)
        append_log(job_id, "Synthesizing Korean TTS...")
        provider = get_tts_provider()
        chunks = split_text_for_tts(ko_full)
        provider.synthesize(chunks, Path(paths["tts_audio"]))

        # If lipsync provider is enabled, generate a lip-synced video using the TTS audio
        provider = (settings.lipsync_provider or ("sadtalker" if settings.use_sadtalker else "none")).lower()
        if provider == "sadtalker":
            set_status(job_id, "RUNNING", progress=85)
            append_log(job_id, "Running SadTalker for lip-sync video generation...")
            ref_image = Path(paths["work"]) / "sadtalker_ref.png"
            extract_first_frame(Path(paths["video"]), ref_image)
            wav16k = Path(paths["work"]) / "tts_16k.wav"
            ensure_wav_16k_mono_sad(Path(paths["tts_audio"]), wav16k)
            tmp_sadtalker_out = Path(paths["work"]) / "sadtalker_output.mp4"
            run_sadtalker(ref_image, wav16k, tmp_sadtalker_out, preprocess="full", still=True, size=256)
            set_status(job_id, "RUNNING", progress=90)
            append_log(job_id, "Attaching subtitles to SadTalker video...")
            add_subtitles_soft(tmp_sadtalker_out, Path(paths["subs"]), Path(paths["out_video"]))
        elif provider == "wav2lip":
            set_status(job_id, "RUNNING", progress=85)
            append_log(job_id, "Running Wav2Lip for lip-sync video generation...")
            # 상용 Sync API가 설정되어 있으면 원격 실행, 아니면 로컬 체크포인트로 실행
            tmp_w2l_out = Path(paths["work"]) / "wav2lip_output.mp4"
            run_wav2lip(Path(paths["video"]), Path(paths["tts_audio"]), tmp_w2l_out)
            set_status(job_id, "RUNNING", progress=90)
            append_log(job_id, "Attaching subtitles to Wav2Lip video...")
            add_subtitles_soft(tmp_w2l_out, Path(paths["subs"]), Path(paths["out_video"]))
        else:
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
