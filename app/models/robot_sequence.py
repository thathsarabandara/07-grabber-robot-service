from datetime import datetime
import uuid
from typing import Any, List, Dict
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

class RobotSequence(SQLModel, table=True):
    __tablename__ = "robot_sequences"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=255)
    
    # Store list of frame states. Each frame is a dict like {'j1': 90, 'j2': 90, 'j3': 50, 'j4': 90, 'time': 123456789}
    frames: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
