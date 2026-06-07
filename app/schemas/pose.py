from pydantic import BaseModel, ConfigDict
from typing import Any, Dict
from datetime import datetime
from uuid import UUID

class PoseCreate(BaseModel):
    name: str
    pose: Dict[str, Any]

class PoseResponse(BaseModel):
    id: UUID
    name: str
    pose: Dict[str, Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
