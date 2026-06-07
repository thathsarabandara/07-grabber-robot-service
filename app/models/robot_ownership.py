from datetime import datetime
import uuid
from typing import Optional
from sqlmodel import Field, SQLModel

class RobotOwnership(SQLModel, table=True):
    __tablename__ = "robot_ownerships"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    user_id: str = Field(index=True) # Usually mapped from JWT sub
    role: str = Field(default="OWNER", max_length=50)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
