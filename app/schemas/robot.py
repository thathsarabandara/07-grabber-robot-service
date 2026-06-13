from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class RobotRegisterRequest(BaseModel):
    robot_id: str
    serial_key: str
    name: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None

class RobotPairRequest(BaseModel):
    robotId: str
    serialKey: str

class RobotUpdate(BaseModel):
    name: Optional[str] = None

class RobotResponse(BaseModel):
    id: UUID
    robot_id: str
    name: Optional[str]
    firmware_version: Optional[str]
    model: Optional[str]
    status: Optional[str]
    last_seen: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SuccessResponse(BaseModel):
    success: bool
