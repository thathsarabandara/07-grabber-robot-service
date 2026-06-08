from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.models.robot import Robot
from app.models.robot_ownership import RobotOwnership
from app.schemas.robot import RobotPairRequest, RobotUpdate
from app.services.event_service import event_service

class RobotService:
    async def pair_robot(self, db: AsyncSession, user_id: str, pair_request: RobotPairRequest) -> Robot:
        # Check if robot exists and serial key matches
        result = await db.execute(select(Robot).where(Robot.robot_id == pair_request.robotId))
        robot = result.scalars().first()
        
        if not robot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
        
        # In a real scenario, we'd hash and verify pair_request.serialKey against robot.serial_key_hash
        # For this implementation, we just check equality (assuming it's a raw string for simplicity)
        if robot.serial_key_hash != pair_request.serialKey:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid serial key")
            
        # Check if already paired
        ownership_result = await db.execute(select(RobotOwnership).where(RobotOwnership.robot_id == robot.id))
        if ownership_result.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Robot is already paired")
            
        # Create ownership
        ownership = RobotOwnership(robot_id=robot.id, user_id=user_id, role="OWNER")
        db.add(ownership)
        await db.commit()
        
        # Log event
        await event_service.log_event(db, robot.id, "ROBOT_PAIRED", {"user_id": user_id})
        
        return robot

    async def get_my_robots(self, db: AsyncSession, user_id: str) -> List[Robot]:
        result = await db.execute(
            select(Robot)
            .join(RobotOwnership, Robot.id == RobotOwnership.robot_id)
            .where(RobotOwnership.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_robot(self, db: AsyncSession, user_id: str, robot_id: UUID) -> Robot:
        # Check ownership
        ownership = await self._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(Robot).where(Robot.id == robot_id))
        robot = result.scalars().first()
        return robot

    async def update_robot(self, db: AsyncSession, user_id: str, robot_id: UUID, update_data: RobotUpdate) -> Robot:
        await self._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(Robot).where(Robot.id == robot_id))
        robot = result.scalars().first()
        
        if update_data.name is not None:
            robot.name = update_data.name
            
        db.add(robot)
        await db.commit()
        await db.refresh(robot)
        return robot

    async def unpair_robot(self, db: AsyncSession, user_id: str, robot_id: UUID):
        ownership = await self._check_ownership(db, user_id, robot_id)
        
        await db.delete(ownership)
        await db.commit()
        
        await event_service.log_event(db, robot_id, "ROBOT_UNPAIRED", {"user_id": user_id})

    async def _check_ownership(self, db: AsyncSession, user_id: str, robot_id: UUID) -> RobotOwnership:
        result = await db.execute(
            select(RobotOwnership)
            .where(RobotOwnership.robot_id == robot_id)
            .where(RobotOwnership.user_id == user_id)
        )
        ownership = result.scalars().first()
        if not ownership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this robot")
        return ownership

robot_service = RobotService()
