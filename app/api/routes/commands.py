from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.schemas.command import CommandResponse, MoveJointRequest
from app.services.command_service import command_service

router = APIRouter()

@router.post("/move-joint", response_model=CommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def move_joint(
    robotId: UUID,
    request: MoveJointRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await command_service.execute_command(db, user_id, robotId, "move-joint", request.model_dump())

@router.post("/home", response_model=CommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def home_position(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await command_service.execute_command(db, user_id, robotId, "home")

@router.post("/emergency-stop", response_model=CommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def emergency_stop(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await command_service.execute_command(db, user_id, robotId, "emergency-stop")

@router.post("/open-gripper", response_model=CommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def open_gripper(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await command_service.execute_command(db, user_id, robotId, "open-gripper")

@router.post("/close-gripper", response_model=CommandResponse, status_code=status.HTTP_202_ACCEPTED)
async def close_gripper(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await command_service.execute_command(db, user_id, robotId, "close-gripper")
