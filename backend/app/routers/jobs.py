import asyncio
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_auth_context
from app.services.job_service import job_manager

router = APIRouter(prefix="/jobs", tags=["Background Jobs & Scalability"])

@router.get("")
def list_background_jobs(
    auth_ctx: Dict[str, Any] = Depends(get_auth_context)
):
    """
    Lists recent asynchronous background jobs for the user.
    """
    user_id = auth_ctx["user_id"]
    jobs = job_manager.list_jobs(user_id=user_id)
    return [j.to_dict() for j in jobs]

@router.get("/{job_id}")
def get_job_status(
    job_id: str,
    auth_ctx: Dict[str, Any] = Depends(get_auth_context)
):
    """
    Returns the real-time processing status of a background job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found."
        )
    return job.to_dict()

@router.post("/demo", status_code=status.HTTP_202_ACCEPTED)
async def trigger_demo_job(
    task_name: str = "document_indexing_simulation",
    auth_ctx: Dict[str, Any] = Depends(get_auth_context)
):
    """
    Enqueues a test background task with progressive status updates.
    """
    user_id = auth_ctx["user_id"]
    job = job_manager.create_job(job_type=task_name, user_id=user_id)

    async def _sample_worker():
        await asyncio.sleep(0.5)
        return {"processed_items": 42, "status": "all_chunks_indexed"}

    asyncio.create_task(job_manager.run_async_task(job.job_id, _sample_worker))
    return {"message": "Job accepted and queued for processing.", "job": job.to_dict()}

