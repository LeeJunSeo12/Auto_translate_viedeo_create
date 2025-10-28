import json
import time
from typing import Any, Dict, List, Optional

import redis

from app.config import settings


_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


def _job_logs_key(job_id: str) -> str:
    return f"job:{job_id}:logs"


def _job_events_channel(job_id: str) -> str:
    return f"job:{job_id}:events"


def init_job(job_id: str, youtube_url: str) -> None:
    _redis.hset(
        _job_key(job_id),
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "result_url": "",
            "error": "",
            "youtube_url": youtube_url,
            "started_at": int(time.time()),
        },
    )
    _redis.delete(_job_logs_key(job_id))


def set_status(job_id: str, status: str, progress: Optional[int] = None, error: str = "") -> None:
    mapping: Dict[str, Any] = {"status": status}
    if progress is not None:
        mapping["progress"] = max(0, min(progress, 100))
    if error:
        mapping["error"] = error
    _redis.hset(_job_key(job_id), mapping=mapping)
    publish_event(job_id, {"type": "status", **mapping})


def set_result(job_id: str, result_url: str) -> None:
    _redis.hset(_job_key(job_id), mapping={"result_url": result_url})
    publish_event(job_id, {"type": "result", "result_url": result_url})


def append_log(job_id: str, message: str) -> None:
    _redis.rpush(_job_logs_key(job_id), message)
    _redis.ltrim(_job_logs_key(job_id), -500, -1)
    publish_event(job_id, {"type": "log", "message": message})


def get_state(job_id: str) -> Dict[str, Any]:
    data = _redis.hgetall(_job_key(job_id))
    data["progress"] = int(data.get("progress", 0) or 0)
    return data


def get_logs(job_id: str, limit: int = 200) -> List[str]:
    return _redis.lrange(_job_logs_key(job_id), -limit, -1)


def publish_event(job_id: str, event: Dict[str, Any]) -> None:
    _redis.publish(_job_events_channel(job_id), json.dumps(event, ensure_ascii=False))


def get_pubsub():
    return _redis.pubsub()
