from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

# 1. This schema validates the data coming IN from the user
class RenderCreate(BaseModel):
    user_id: UUID = Field(..., description="The UUID of the user creating the job")
    prompt: str = Field(..., min_length=3, description="Text prompt guiding the diffusion model")
    sketch_base64: str = Field(..., description="The raw canvas stroke data encoded as a Base64 string")

# 2. This schema formats the data going OUT back to the frontend
class RenderResponse(BaseModel):
    job_id: UUID
    status: str
    prompt: str
    sketch_path: str
    render_path: Optional[str] = None
    created_at: datetime

    # This tells Pydantic to read data directly from SQLAlchemy ORM objects
    class Config:
        from_attributes = True