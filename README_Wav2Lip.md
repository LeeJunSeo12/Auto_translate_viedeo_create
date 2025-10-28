
## Wac2Lip 깃 클론 
git clone https://github.com/Rudrabha/Wav2Lip.git         

지금 Wav2Lip을 선택적으로 사용할 수 있도록 .env를 통해 제공자 선택 기능을 추가하고, 유틸과 작업 분기를 구현하겠습니다. 이어서 관련 파일들을 한꺼번에 읽어 확인하고 필요한 최소 편집을 적용할게요.

[1 tool called]

I'll add Wav2Lip support with a new utility, update the config for provider selection via .env, and adjust the task flow to branch between SadTalker, Wav2Lip, or none. Then I'll run a linter check on changed files.

[10 tools called]

진행 상황: `.env`로 `LIPSYNC_PROVIDER`를 선택하도록 설정을 추가했고, `Wav2Lip` 유틸을 만들어 작업 플로우에서 `sadtalker / wav2lip / none` 세 가지로 분기하도록 편집했습니다. 이제 .env만 세팅하면 두 방식 중 하나를 쉽게 선택해 사용할 수 있습니다.

### .env 설정 옵션
- LIPSYNC_PROVIDER=none | sadtalker | wav2lip
- SadTalker 관련
  - USE_SADTALKER=true (과거 호환용, 설정 시 기본 provider가 sadtalker로 간주)
  - SADTALKER_REPO=C:\...\Auto_translate_viedeo_create\SadTalker
  - SADTALKER_CKPT_DIR=C:\...\Auto_translate_viedeo_create\SadTalker\checkpoints
- Wav2Lip 관련
  - WAV2LIP_REPO=C:\...\Auto_translate_viedeo_create\Wav2Lip
  - WAV2LIP_CKPT=C:\...\Auto_translate_viedeo_create\Wav2Lip\checkpoints\wav2lip_gan.pth

### 변경 사항 요약
- `api/app/config.py`
  - `lipsync_provider`, `wav2lip_repo`, `wav2lip_checkpoint_path` 추가
- `api/app/utils/sadtalker.py`
  - 그대로 사용 (16k WAV 변환, SadTalker 실행, 자막 소프트 트랙 추가)
- `api/app/utils/wav2lip.py` [신규]
  - 16k WAV 변환 `ensure_wav_16k_mono`
  - `run_wav2lip(face, audio, outfile)`로 Wav2Lip 추론 실행
- `api/app/tasks.py`
  - 최종 단계에서 `LIPSYNC_PROVIDER`에 따라 분기
    - sadtalker: 첫 프레임 추출 → 16k WAV → SadTalker → 자막 트랙 부착
    - wav2lip: 원본 영상 사용 → 16k WAV → Wav2Lip → 자막 트랙 부착
    - none: 기존처럼 TTS 오디오로 원본 영상과 자막을 ffmpeg로 머지

### Windows PowerShell 설정 예시
```powershell
# 공통
$env:LIPSYNC_PROVIDER="wav2lip" ; `
$env:WAV2LIP_REPO="C:\YOUR\PROJECT\Auto_translate_viedeo_create\Wav2Lip" ; `
$env:WAV2LIP_CKPT="$env:WAV2LIP_REPO\checkpoints\wav2lip_gan.pth" ; `
$env:REDIS_URL="redis://localhost:6379/0"

# SadTalker를 쓰려면(선택)
$env:LIPSYNC_PROVIDER="sadtalker" ; `
$env:SADTALKER_REPO="C:\YOUR\PROJECT\Auto_translate_viedeo_create\SadTalker" ; `
$env:SADTALKER_CKPT_DIR="$env:SADTALKER_REPO\checkpoints"
```

### Wav2Lip 체크포인트 다운로드(예시, PowerShell)
```powershell
$W="C:\YOUR\PROJECT\Auto_translate_viedeo_create\Wav2Lip"
New-Item -ItemType Directory -Force -Path "$W\checkpoints" | Out-Null
# 아래 링크는 예시입니다. 실제 공식 체크포인트 파일(wav2lip_gan.pth)을 준비해 해당 경로에 위치시키세요.
# 예: 수동 다운로드 후 $env:WAV2LIP_CKPT로 경로 지정
```

이후 사용은 기존과 동일합니다. `.env`에서 `LIPSYNC_PROVIDER`만 바꾸면 바로 SadTalker 또는 Wav2Lip로 결과가 생성됩니다.

- 완료 사항
  - 설정 키 추가와 분기 로직 구현
  - `Wav2Lip` 유틸 추가
  - 린트 확인 완료
- 최종 효과
  - API에서 입모양 합성 엔진을 .env로 선택 가능
  - SadTalker 또는 Wav2Lip 결과 위에 한글 자막 소프트 트랙 포함