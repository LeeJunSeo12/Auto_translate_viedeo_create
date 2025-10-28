## SadTalker 깃 클론 
git clone https://github.com/OpenTalker/SadTalker.git     





지금 SadTalker를 API 파이프라인에 연결하기 위해, 먼저 SadTalker의 실행 진입점과 필요한 옵션을 확인하겠습니다. 확인 후 `api/app/utils`에 SadTalker 호출 유틸을 추가하고, `tasks.py`에서 `USE_SADTALKER=true`일 때 해당 유틸을 사용해 합성하도록 편집하겠습니다.

[1 tool called]

제가 SadTalker의 사용 가능한 진입점을 파악하기 위해 관련 파일을 열어볼게요. 이어서 `api/app/utils`에 SadTalker 호출 유틸을 추가하고, `tasks.py`에서 `USE_SADTALKER=true`일 때 분기해 사용하도록 편집하겠습니다.

[1 tool called]

I'll add a new SadTalker utility in the API and wire it into the job task flow when USE_SADTALKER is enabled, without touching unrelated files. Then I'll update the task to use the generated lip-synced video for muxing.

[1 tool called]

지금 SadTalker가 요구하는 오디오 포맷을 확인하기 위해 관련 소스 몇 개를 한꺼번에 살펴볼게요. 곧바로 필요한 파일을 읽고 적합한 호출 방식을 정하겠습니다.

[3 tools called]

지금 SadTalker 연동을 위한 유틸을 추가하고, `tasks.py`에서 `USE_SADTALKER` 분기를 붙이겠습니다. 이어서 필요한 최소 라이브러리를 `api/requirements.txt`에 추가합니다.

[3 tools called]

I'll quickly read SadTalker's requirements files to ensure the API environment has necessary dependencies, then update `api/requirements.txt` accordingly.

[2 tools called]

I'll check `docker-compose.yml` to see if the `SadTalker` directory can be mounted into the API container, which affects how we reference the path in code.

[1 tool called]

I'll update the task flow to call SadTalker when USE_SADTALKER is true, generating a lip-synced video from the first frame and TTS audio, then attach subtitles. I'll make the minimal edits in `api/app/tasks.py`.

[6 tools called]

방금 SadTalker 연동용 유틸을 추가하고, `USE_SADTALKER=true`일 때 `tasks.py`가 TTS 오디오로 SadTalker를 실행해 입모양까지 합성하도록 분기까지 마쳤습니다. 이제 실행/설정만 해 주시면 됩니다.

### 무엇을 변경했나요
- api 서버 내부만 최소 수정
  - `api/app/utils/sadtalker.py` 추가: SadTalker 실행, 오디오 변환(16kHz mono WAV), 자막 트랙 합치기 유틸
  - `api/app/tasks.py` 수정: `settings.use_sadtalker`가 true일 때
    - 원본 영상 첫 프레임 추출 → SadTalker 참조 이미지로 사용
    - TTS MP3 → 16kHz mono WAV 변환
    - SadTalker로 음성 구동 합성 영상 생성
    - SRT 자막을 소프트 트랙으로 입혀 최종 결과 저장
  - `api/requirements.txt` 보강: SadTalker 런타임에 필요한 의존성 추가

### 필수 환경 변수
- `USE_SADTALKER=true`
- `SADTALKER_REPO` → SadTalker 레포 경로 (예: `C:\...\Auto_translate_viedeo_create\SadTalker`)
- `SADTALKER_CKPT_DIR` → 체크포인트 경로 (예: `<SADTALKER_REPO>\checkpoints`)

### 체크포인트(모델 가중치) 다운로드 (PowerShell)
아래는 Windows PowerShell용 원클릭 다운로드 예시입니다. 경로만 바꿔서 실행하세요.
```powershell
# 경로 설정
$S = "C:\YOUR\PROJECT\Auto_translate_viedeo_create\SadTalker"; New-Item -ItemType Directory -Force -Path "$S\checkpoints" | Out-Null; New-Item -ItemType Directory -Force -Path "$S\gfpgan\weights" | Out-Null

# 핵심 모델
Invoke-WebRequest "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar" -OutFile "$S\checkpoints\mapping_00109-model.pth.tar"
Invoke-WebRequest "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar" -OutFile "$S\checkpoints\mapping_00229-model.pth.tar"
Invoke-WebRequest "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors" -OutFile "$S\checkpoints\SadTalker_V0.0.2_256.safetensors"
Invoke-WebRequest "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors" -OutFile "$S\checkpoints\SadTalker_V0.0.2_512.safetensors"

# GFPGAN / Face 관련
Invoke-WebRequest "https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth" -OutFile "$S\gfpgan\weights\alignment_WFLW_4HG.pth"
Invoke-WebRequest "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth" -OutFile "$S\gfpgan\weights\detection_Resnet50_Final.pth"
Invoke-WebRequest "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth" -OutFile "$S\gfpgan\weights\GFPGANv1.4.pth"
Invoke-WebRequest "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth" -OutFile "$S\gfpgan\weights\parsing_parsenet.pth"
```

### 로컬(Windows)에서 바로 실행하는 방법(권장)
PowerShell 기준; 세션 내 일시 설정은 `;`로 이어주세요.

1) 의존성 설치
```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install --upgrade pip ; `
pip install -r api\requirements.txt ; `
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 ; `
pip install -r .\SadTalker\requirements.txt
```
- CUDA 버전이 다르면 `cu121` 대신 맞는 인덱스-url로 변경하세요. GPU가 없다면 CPU 전용 PyTorch를 설치하세요.

2) 환경 변수 설정
```powershell
$env:USE_SADTALKER="true" ; `
$env:SADTALKER_REPO="C:\YOUR\PROJECT\Auto_translate_viedeo_create\SadTalker" ; `
$env:SADTALKER_CKPT_DIR="$env:SADTALKER_REPO\checkpoints" ; `
$env:REDIS_URL="redis://localhost:6379/0"
```

3) Redis 실행(없다면 Docker로 간단히)
```powershell
docker run -d --name redis-sadtalker -p 6379:6379 redis:7-alpine
```

4) API/Worker 실행(두 개의 PowerShell 창)
- 창 A:
```powershell
cd api ; . ..\.venv\Scripts\Activate.ps1 ; uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- 창 B:
```powershell
cd api ; . ..\.venv\Scripts\Activate.ps1 ; celery -A app.celery_app:celery_app worker --loglevel=INFO --concurrency=1
```

5) 테스트 호출
```powershell
$body = @{ youtubeUrl = 'https://www.youtube.com/watch?v=VIDEO_ID' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/jobs -Method Post -ContentType 'application/json' -Body $body
# 응답의 jobId로 상태 조회
Invoke-RestMethod http://localhost:8000/jobs/JOB_ID
```
- 완료 후 결과 파일: `web`에서 `/results/{jobId}/translated_video.mp4`로 접근 가능. API 서버 기준 경로는 `data\results\{jobId}\translated_video.mp4`.

### Docker Compose로 실행하려면
기본 Compose는 SadTalker 소스가 컨테이너 안에 없으므로 한 번만 다음을 수행하세요.
- `.env`에 `USE_SADTALKER=true` 추가
- 컨테이너 내부로 SadTalker 복사 및 체크포인트 다운로드
```powershell
docker compose up -d
# 워커 컨테이너명은 환경에 따라 다를 수 있습니다. 아래는 예시입니다.
$W = (docker ps --format "{{.Names}}" | Select-String "worker").ToString()
docker exec -it $W bash -lc "apt-get update ; apt-get install -y git wget ; mkdir -p /app/extern ; git clone https://github.com/OpenTalker/SadTalker.git /app/extern/SadTalker ; cd /app/extern/SadTalker ; bash scripts/download_models.sh"
# API/Worker 둘 다 SadTalker가 필요하면 두 컨테이너에 동일하게 적용하세요.
```
- 환경 변수는 기본값이 `/app/extern/SadTalker`와 `/app/extern/SadTalker/checkpoints`이므로 별도 설정 없이 작동합니다.

### 기대 동작
- 기존 파이프라인(STT → 번역 → TTS)은 그대로 유지
- `USE_SADTALKER=true`일 때:
  - 원본 영상 첫 프레임을 참조 이미지로 사용
  - TTS MP3 → 16kHz mono WAV 변환
  - SadTalker로 입모양 합성 영상 생성
  - 한글 SRT 자막을 소프트 트랙으로 합쳐 최종 결과 저장

상태 메모: SadTalker 유틸 추가와 `tasks.py` 연동을 완료했고, 의존성 갱신도 반영했습니다. 다음은 모델 다운로드와 환경 변수 설정만 진행하면 바로 테스트 가능합니다.

- 변경 요약
  - `api/app/utils/sadtalker.py` 신규 추가: SadTalker 실행/오디오 변환/자막 합치기
  - `api/app/tasks.py`에 SadTalker 분기 추가(`USE_SADTALKER` 기준)
  - `api/requirements.txt`에 SadTalker 런타임 의존성 보강
- 실행 방법
  - Windows PowerShell 기준 명령 제공: 모델 다운로드, env 설정, Redis/API/Worker 구동, 테스트 호출
  - Docker Compose 사용 시 컨테이너 내부에 SadTalker와 체크포인트 설치 방법 안내