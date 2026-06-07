from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import UUID

class MoveJointRequest(BaseModel):
    joint: str
    angle: float

class CommandResponse(BaseModel):
    id: UUID
    command_type: str
    status: str
    executed_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
