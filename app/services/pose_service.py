from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.models.robot_pose import RobotPose
from app.schemas.pose import PoseCreate
from app.services.robot_service import robot_service
from app.services.command_service import command_service

class PoseService:
    async def save_pose(self, db: AsyncSession, user_id: str, robot_id: UUID, pose_data: PoseCreate) -> RobotPose:
        await robot_service._check_ownership(db, user_id, robot_id)
        
        pose = RobotPose(
            robot_id=robot_id,
            name=pose_data.name,
            pose=pose_data.pose
        )
        db.add(pose)
        await db.commit()
        await db.refresh(pose)
        return pose

    async def list_poses(self, db: AsyncSession, user_id: str, robot_id: UUID) -> List[RobotPose]:
        await robot_service._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(RobotPose).where(RobotPose.robot_id == robot_id))
        return list(result.scalars().all())

    async def execute_pose(self, db: AsyncSession, user_id: str, robot_id: UUID, pose_id: UUID):
        await robot_service._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(RobotPose).where(RobotPose.id == pose_id).where(RobotPose.robot_id == robot_id))
        pose = result.scalars().first()
        
        if not pose:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pose not found")
            
        await command_service.execute_command(db, user_id, robot_id, "execute-pose", pose.pose)

    async def delete_pose(self, db: AsyncSession, user_id: str, robot_id: UUID, pose_id: UUID):
        await robot_service._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(RobotPose).where(RobotPose.id == pose_id).where(RobotPose.robot_id == robot_id))
        pose = result.scalars().first()
        
        if not pose:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pose not found")
            
        await db.delete(pose)
        await db.commit()

pose_service = PoseService()
