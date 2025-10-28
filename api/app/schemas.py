from pydantic import BaseModel, AnyHttpUrl
from typing import Optional, Literal


class CreateJobRequest(BaseModel):
    youtubeUrl: AnyHttpUrl
    options: Optional[dict] = None


class CreateJobResponse(BaseModel):
    jobId: str


class JobStatusResponse(BaseModel):
    status: Literal["QUEUED", "RUNNING", "FAILED", "DONE"]
    progress: int
    resultUrl: Optional[str] = None
    logs: Optional[list[str]] = None
    error: Optional[str] = None
