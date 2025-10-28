# Auto Shorts Translation Pipeline

YouTube URL → extract audio → Whisper translate to Korean → TTS (KR) → mux back to video → downloadable result

## Stack
- Web: Next.js 15 (App Router), TypeScript
- API: FastAPI (Python 3.10+), Uvicorn
- Worker: Celery + Redis
- Media: yt-dlp, ffmpeg, moviepy
- STT: openai-whisper (WhisperX optional)
- TTS: pluggable (ElevenLabs; Azure stub; gTTS fallback)
- Packaging: Docker & docker-compose
- Storage: local ./data (bind mount)
- Observability: JSON logging, retries, timeouts, basic error handling

## Getting Started
1. Copy env file
```powershell
Copy-Item .env.example .env
```
2. Build & run all services
```powershell
docker compose build ; docker compose up
```
   - Open web: `http://localhost:3000`
   - API docs: `http://localhost:8000/docs`

## API
- POST `/jobs` { youtubeUrl, options? } → { jobId }
- GET `/jobs/{jobId}` → { status, progress, resultUrl?, logs? }
- GET `/stream/{jobId}` → Server-Sent Events for live progress

## Storage Layout
- Work: `./data/work/{jobId}` (intermediate)
- Results: `./data/results/{jobId}` (final artifacts)

## Env Vars
- See `.env.example`
- Key ones:
  - `ELEVENLABS_API_KEY`: for TTS
  - `WHISPER_MODEL`: e.g. `large-v3`
  - `TTS_PROVIDER`: `elevenlabs` | `azure` | `gtts`
  - `USE_WHISPERX`: `true|false`

## TTS Provider Switch
- Change `TTS_PROVIDER` in `.env`
- Providers:
  - `elevenlabs`: production
  - `azure`: stub (extend later)
  - `gtts`: local demo fallback

## GPU Notes (Whisper/WhisperX)
- Mount GPU and install CUDA-enabled wheels for faster-whisper/whisperx if needed.
- In containers, ensure `torch`/`cuda` wheels match host drivers.

## Development Quality
- Python: ruff/black configured in `api/pyproject.toml`
- JS: ESLint/Prettier in `web`
- Tests: run `pytest` under `api`

## Cleanup
- Generated files live under `./data`. Safe to delete individual job folders.

## 백엔드 & 인프라 설정 가이드 (macOS/Windows)

### 1) 필수 준비물
- Python 3.10+
- Docker Desktop
- (선택) ffmpeg, yt-dlp (로컬 개발 시만 필요 / Docker 사용 시 컨테이너에 포함)

### 2) 환경 변수(.env) 설정
- 루트(`auto_shorts`) 경로에 `.env` 생성 후 아래 키를 설정하세요. (없으면 `.env.example` 복사)

```dotenv
# 필수
REDIS_URL=redis://redis:6379/0
WHISPER_MODEL=large-v3
TTS_PROVIDER=elevenlabs
LOG_LEVEL=INFO

# 선택 (키가 없으면 gTTS로 폴백)
ELEVENLABS_API_KEY=

# WhisperX 사용 옵션
USE_WHISPERX=false

# Web 연동용
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Azure TTS (스텁)
AZURE_TTS_KEY=
AZURE_TTS_REGION=
```

- 요약
  - **REDIS_URL**: Redis 연결(기본 `redis://redis:6379/0`)
  - **WHISPER_MODEL**: `large-v3` 권장
  - **TTS_PROVIDER**: `elevenlabs` | `gtts` | `azure`
  - **ELEVENLABS_API_KEY**: ElevenLabs 사용 시 필수(없으면 gTTS 폴백)
  - **USE_WHISPERX**: `true`면 WhisperX 시도(환경에 torch/whisperx 필요)

### 3) 로컬 실행(가상환경)

#### macOS
```bash
# (선택) 로컬 도구
brew install ffmpeg ; brew install yt-dlp ; brew install redis

# 가상환경 생성/활성화/설치
cd /Users/ijunseo/Documents/NEON101/auto_shorts/api
python3 -m venv .venv ; source .venv/bin/activate
pip install --upgrade pip ; pip install -r requirements.txt

# Redis 실행 (둘 중 하나)
brew services start redis
# 또는 Docker 단독 실행
docker run --name redis-local -p 6379:6379 -d redis:7-alpine

# API 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000

# (새 터미널) 워커 실행
cd /Users/ijunseo/Documents/NEON101/auto_shorts/api
source .venv/bin/activate ; celery -A app.celery_app:celery_app worker --loglevel=INFO --concurrency=1
```

#### Windows (PowerShell)
```powershell
# 가상환경 생성/활성화/설치
cd C:\Users\ijunseo\Documents\NEON101\auto_shorts\api
py -3.10 -m venv .venv ; .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip ; pip install -r requirements.txt

# Redis 실행 (Docker 권장)
docker run --name redis-local -p 6379:6379 -d redis:7-alpine

# API 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000

# (새 PowerShell) 워커 실행
cd C:\Users\ijunseo\Documents\NEON101\auto_shorts\api
.\.venv\Scripts\Activate.ps1 ; celery -A app.celery_app:celery_app worker --loglevel=INFO --concurrency=1
```

> 참고: 로컬 실행 시 ffmpeg/yt-dlp가 필요합니다. Docker 실행을 사용하면 컨테이너에 포함되어 별도 설치가 필요 없습니다.

### 4) Docker Compose로 인프라 올리기(권장)
```powershell
# 루트에서 실행 (macOS/Windows 동일)
cd /Users/ijunseo/Documents/NEON101/auto_shorts
docker compose build ; docker compose up -d

# 상태/로그 확인
docker compose ps
docker compose logs -f api
docker compose logs -f worker

# 종료/정리
docker compose down
# 볼륨/캐시까지 정리할 때
docker compose down -v ; docker system prune -f
```

### 5) 확인/접속 경로
- API 문서: `http://localhost:8000/docs`
- 결과 파일: `./data/results/{jobId}/translated_video.mp4`
- 정적 서빙: API에서 `/results/{jobId}/translated_video.mp4`로 접근 가능

### 6) 테스트(옵션)
```powershell
# API 컨테이너 내부에서
cd /Users/ijunseo/Documents/NEON101/auto_shorts
docker compose exec api pytest -q
```

### 7) WhisperX 사용
- `.env`에서 `USE_WHISPERX=true`
- 컨테이너 커스텀 이미지 또는 호스트에 torch/whisperx/CUDA 환경 필요
- 미구성 시 자동으로 기본 Whisper로 폴백

### 8) TTS 제공자 전환
- `.env`의 `TTS_PROVIDER`를 변경: `elevenlabs` | `gtts` | `azure`
- `elevenlabs` 사용 시 `ELEVENLABS_API_KEY` 필수
- 키 미설정 시 자동 `gTTS` 폴백(데모용)

### 9) 문제 해결
- ffmpeg/yt-dlp 관련 오류: Docker로 실행하거나, 로컬에 설치(brew/winget/choco)
- ElevenLabs 401/403: `ELEVENLABS_API_KEY` 유효성 확인
- WhisperX ImportError: `USE_WHISPERX=false`로 비활성화하거나 GPU/torch/whisperx 환경 구성
- 처리 지연: 긴 영상은 시간이 소요됩니다. 진행률/로그는 `/stream/{jobId}` SSE로 확인하세요.
