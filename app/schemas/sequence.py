from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List
from datetime import datetime
from uuid import UUID

class SequenceCreate(BaseModel):
    name: str
    frames: List[Dict[str, Any]]

class SequenceResponse(BaseModel):
    id: UUID
    name: str
    frames: List[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
