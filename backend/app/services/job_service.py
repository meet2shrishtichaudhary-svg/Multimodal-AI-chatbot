import time
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Coroutine
from datetime import datetime

logger = logging.getLogger("mm_chatbot.jobs")

class BackgroundJob:
    def __init__(self, job_id: str, job_type: str, user_id: Optional[str] = None):
        self.job_id = job_id
        self.job_type = job_type
        self.user_id = user_id
        self.status = "queued"  # 'queued', 'processing', 'completed', 'failed'
        self.progress = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class JobManager:
    """
    Lightweight, reliable async task executor with status tracking and bounded retries.
    """
    def __init__(self):
        self._jobs: Dict[str, BackgroundJob] = {}

    @property
    def jobs(self) -> Dict[str, BackgroundJob]:
        return self._jobs

    def submit_job(self, task_name: str, session_id: Optional[str] = None, user_id: Optional[str] = None, total_steps: int = 1) -> BackgroundJob:
        return self.create_job(job_type=task_name, user_id=user_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job and job.status in ["queued", "processing"]:
            job.status = "cancelled"
            job.updated_at = datetime.utcnow()
            return True
        return False

    def create_job(self, job_type: str, user_id: Optional[str] = None) -> BackgroundJob:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = BackgroundJob(job_id=job_id, job_type=job_type, user_id=user_id)
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, user_id: Optional[str] = None) -> list[BackgroundJob]:
        if user_id:
            return [j for j in self._jobs.values() if j.user_id == user_id]
        return list(self._jobs.values())

    async def run_async_task(
        self,
        job_id: str,
        coro_func: Callable[[], Coroutine[Any, Any, Any]],
        max_retries: int = 2
    ):
        job = self.get_job(job_id)
        if not job:
            return

        job.status = "processing"
        job.progress = 10
        job.updated_at = datetime.utcnow()

        attempts = 0
        while attempts <= max_retries:
            try:
                attempts += 1
                result = await coro_func()
                job.status = "completed"
                job.progress = 100
                job.result = result if isinstance(result, dict) else {"output": str(result)}
                job.updated_at = datetime.utcnow()
                logger.info(f"Background job {job_id} ({job.job_type}) completed successfully.")
                return
            except Exception as e:
                logger.warning(f"Background job {job_id} attempt {attempts} failed: {e}")
                if attempts <= max_retries:
                    await asyncio.sleep(1.0 * attempts)
                else:
                    job.status = "failed"
                    job.error = str(e)
                    job.updated_at = datetime.utcnow()

job_manager = JobManager()

