from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.schemas.robot import RobotPairRequest, RobotResponse, RobotUpdate, SuccessResponse, RobotRegisterRequest
from app.services.robot_service import robot_service

router = APIRouter()

@router.post("/register", response_model=RobotResponse, status_code=status.HTTP_201_CREATED)
async def register_robot(
    register_request: RobotRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    return await robot_service.register_robot(db, register_request)

@router.post("/pair", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def pair_robot(
    pair_request: RobotPairRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await robot_service.pair_robot(db, user_id, pair_request)
    return SuccessResponse(success=True)

@router.get("", response_model=List[RobotResponse])
async def get_my_robots(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await robot_service.get_my_robots(db, user_id)

@router.get("/{robotId}", response_model=RobotResponse)
async def get_robot(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await robot_service.get_robot(db, user_id, robotId)

@router.patch("/{robotId}", response_model=RobotResponse)
async def update_robot(
    robotId: UUID,
    update_data: RobotUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await robot_service.update_robot(db, user_id, robotId, update_data)

@router.delete("/{robotId}", status_code=status.HTTP_204_NO_CONTENT)
async def unpair_robot(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await robot_service.unpair_robot(db, user_id, robotId)
