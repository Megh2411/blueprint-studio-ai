import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Float, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Define our allowed job statuses
class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Links jobs to the user; if a user is deleted, their jobs are deleted
    jobs = relationship("RenderJob", back_populates="user", cascade="all, delete-orphan")

class RenderJob(Base):
    __tablename__ = "render_jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt = Column(Text, nullable=False)
    sketch_path = Column(String, nullable=False)  # URL to the sketch bucket
    render_path = Column(String, nullable=True)   # URL to the final AI render bucket
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    
    # Hyperparameters
    control_strength = Column(Float, default=0.7, nullable=True)
    steps = Column(Integer, default=25, nullable=True)
    cfg_scale = Column(Float, default=7.0, nullable=True)
    
    # Telemetry metrics
    metrics = Column(JSON, nullable=True)
    
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="jobs")

# This script creates the tables in Supabase if we run it directly
if __name__ == "__main__":
    from app.core.database import engine
    print("Creating tables in Supabase...")
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Tables created successfully!")