from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import RenderJob, JobStatus, User
from app.workers.tasks import process_render_job
from app.core.storage import upload_sketch
from pydantic import BaseModel
import uuid

from app.utils.rate_limiter import RateLimiter

router = APIRouter()

class RenderRequest(BaseModel):
    user_id: str
    prompt: str
    sketch_base64: str
    mode: str = "sketch"
    control_strength: float = 0.7
    steps: int = 25
    cfg_scale: float = 7.0

# Notice the empty string "" here, which maps to exactly /api/renders
@router.post("", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def create_render_job(request: RenderRequest, db: Session = Depends(get_db)):
    """Creates a new job, uploads sketch to storage, and sends it to the Celery queue."""
    
    try:
        user_uuid = uuid.UUID(request.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # --- NEW: Frictionless Auth / Auto-Create User ---
    # Check if this user exists in the database
    user = db.query(User).filter(User.id == user_uuid).first()
    
    # If they don't exist, create a blank "shadow profile" for them instantly!
    if not user:
        # Postgres requires an email, so we generate a dummy one for guest sessions
        dummy_email = f"guest_{request.user_id[:8]}@blueprint.local"
        
        new_user = User(id=user_uuid, email=dummy_email)
        db.add(new_user)
        db.commit()
    # --------------------------------------------------

    # --- Upload the sketch base64 to Supabase Storage first ---
    try:
        sketch_url = upload_sketch(request.sketch_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload sketch to Supabase storage: {e}")

    job_id = uuid.uuid4()
    
    # Create the database record with the clean sketch URL and hyperparameters
    new_job = RenderJob(
        job_id=job_id,
        user_id=user_uuid,
        prompt=request.prompt,
        status=JobStatus.QUEUED,
        sketch_path=sketch_url,
        control_strength=request.control_strength,
        steps=request.steps,
        cfg_scale=request.cfg_scale
    )
    db.add(new_job)
    db.commit()
    
    # Trigger the background worker!
    process_render_job.delay(
        str(job_id),
        request.control_strength,
        request.steps,
        request.cfg_scale
    )
    
    return {"job_id": str(job_id), "status": "queued"}

# The endpoint used by the polling system (if needed as a fallback)
@router.get("/{job_id}")
def get_render_job(job_id: str, db: Session = Depends(get_db)):
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job = db.query(RenderJob).filter(RenderJob.job_id == job_uuid).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/history/{user_id}")
def get_user_history(user_id: str, db: Session = Depends(get_db)):
    """Fetches all completed render jobs for a specific user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    history = db.query(RenderJob).filter(
        RenderJob.user_id == user_uuid,
        RenderJob.status == JobStatus.COMPLETED
    ).order_by(RenderJob.created_at.desc()).all()
    
    if not history:
        return []
        
    return history