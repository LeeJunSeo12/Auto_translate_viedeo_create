import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.utils.logging import configure_json_logging
from app.utils.progress import get_state, get_logs, init_job, get_pubsub
from app.tasks import process_job
from app.schemas import CreateJobRequest, CreateJobResponse, JobStatusResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_json_logging(settings.log_level)
    yield


app = FastAPI(title="AutoShorts API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve results as static files (works both in container and local)
results_dir = Path(settings.base_data_dir) / "results"
results_dir.mkdir(parents=True, exist_ok=True)
app.mount("/results", StaticFiles(directory=str(results_dir)), name="results")


@app.post("/jobs", response_model=CreateJobResponse)
def create_job(req: CreateJobRequest) -> CreateJobResponse:
    import uuid

    job_id = uuid.uuid4().hex
    init_job(job_id, str(req.youtubeUrl))
    process_job.apply_async(args=[job_id, str(req.youtubeUrl), req.options or {}], task_id=job_id)
    return CreateJobResponse(jobId=job_id)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str):
    state = get_state(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")
    logs = get_logs(job_id)
    return JobStatusResponse(
        status=state.get("status", "QUEUED"),
        progress=int(state.get("progress", 0)),
        resultUrl=state.get("result_url") or None,
        logs=logs,
        error=state.get("error") or None,
    )


@app.get("/stream/{job_id}")
async def stream_events(job_id: str):
    pubsub = get_pubsub()
    channel = f"job:{job_id}:events"
    pubsub.subscribe(channel)

    async def event_generator():
        try:
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    yield f"data: {data}\n\n"
                await asyncio.sleep(0.2)
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
