
// 로컬 Worker 실행
cd api
>> .\.venv\Scripts\Activate.ps1
>> $env:REDIS_URL="redis://localhost:6379/0"
>> celery -A app.celery_app:celery_app worker --pool=solo --loglevel=INFO


// 로컬 API 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000


// 로컬 프론트 서버 실행
npm run dev


//레디스
도커 컴포즈에서 redis만 따로 실행하면 댐.