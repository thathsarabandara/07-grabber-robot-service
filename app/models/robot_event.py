from datetime import datetime
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

class RobotEvent(SQLModel, table=True):
    __tablename__ = "robot_events"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    event_type: str = Field(max_length=100)
    
    payload: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
