from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import UUID

class EventResponse(BaseModel):
    id: UUID
    event_type: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
