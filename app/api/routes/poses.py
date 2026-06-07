from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.schemas.pose import PoseCreate, PoseResponse
from app.schemas.robot import SuccessResponse
from app.services.pose_service import pose_service

router = APIRouter()

@router.post("", response_model=PoseResponse, status_code=status.HTTP_201_CREATED)
async def save_pose(
    robotId: UUID,
    pose_data: PoseCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await pose_service.save_pose(db, user_id, robotId, pose_data)

@router.get("", response_model=List[PoseResponse])
async def list_poses(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await pose_service.list_poses(db, user_id, robotId)

@router.post("/{poseId}/execute", response_model=SuccessResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_pose(
    robotId: UUID,
    poseId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await pose_service.execute_pose(db, user_id, robotId, poseId)
    return SuccessResponse(success=True)

@router.delete("/{poseId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pose(
    robotId: UUID,
    poseId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await pose_service.delete_pose(db, user_id, robotId, poseId)
