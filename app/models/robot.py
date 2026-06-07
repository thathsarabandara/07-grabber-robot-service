from datetime import datetime
import uuid
from typing import Optional
from sqlmodel import Field, SQLModel

class Robot(SQLModel, table=True):
    __tablename__ = "robots"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: str = Field(unique=True, index=True, max_length=100)
    serial_key_hash: str
    
    name: Optional[str] = Field(default=None, max_length=255)
    firmware_version: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default="OFFLINE", max_length=50)
    
    last_seen: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
