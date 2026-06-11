import os
import sys
import uuid
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Add backend to path relatively
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(backend_dir)

load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))

from app.core.database import SessionLocal
from app.models.models import User, RenderJob, JobStatus

db = SessionLocal()

test_user_id = str(uuid.uuid4())
test_job_id = str(uuid.uuid4())

print(f"Test User ID: {test_user_id}")
print(f"Test Job ID: {test_job_id}")

try:
    print("\n1. Testing User Auto-Creation (Shadow Profile)...")
    user_uuid = uuid.UUID(test_user_id)
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        dummy_email = f"guest_{test_user_id[:8]}@blueprint.local"
        new_user = User(id=user_uuid, email=dummy_email)
        db.add(new_user)
        db.commit()
        print("[SUCCESS] Shadow user profile successfully created!")
    else:
        print("User already exists.")

    print("\n2. Testing RenderJob creation...")
    job_uuid = uuid.UUID(test_job_id)
    new_job = RenderJob(
        job_id=job_uuid,
        user_id=user_uuid,
        prompt="A modern brutalist concrete villa, cinematic lighting",
        sketch_path="https://yocozhacvvemwdbapdzd.supabase.co/storage/v1/object/public/sketches/test.png",
        status=JobStatus.COMPLETED,
        render_path="https://yocozhacvvemwdbapdzd.supabase.co/storage/v1/object/public/renders/test_out.png"
    )
    db.add(new_job)
    db.commit()
    print("[SUCCESS] Render job successfully created with status=COMPLETED!")

    print("\n3. Testing User History fetch...")
    history = db.query(RenderJob).filter(
        RenderJob.user_id == user_uuid,
        RenderJob.status == JobStatus.COMPLETED
    ).all()
    print(f"[SUCCESS] History query returned {len(history)} jobs!")
    for j in history:
        print(f"- Job: {j.job_id}, Prompt: '{j.prompt}', Status: {j.status}")

    print("\n4. Cleanup testing records...")
    # Cascade delete will delete render jobs automatically
    db.delete(db.query(User).filter(User.id == user_uuid).first())
    db.commit()
    print("[SUCCESS] Cleanup completed!")

except Exception as e:
    db.rollback()
    print(f"[ERROR] DB Test failed: {e}")
finally:
    db.close()
