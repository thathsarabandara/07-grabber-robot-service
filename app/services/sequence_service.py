from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.models.robot_sequence import RobotSequence
from app.schemas.sequence import SequenceCreate
from app.services.robot_service import robot_service

class SequenceService:
    async def save_sequence(self, db: AsyncSession, user_id: str, robot_id: UUID, sequence_data: SequenceCreate) -> RobotSequence:
        await robot_service._check_ownership(db, user_id, robot_id)
        
        sequence = RobotSequence(
            robot_id=robot_id,
            name=sequence_data.name,
            frames=sequence_data.frames
        )
        db.add(sequence)
        await db.commit()
        await db.refresh(sequence)
        return sequence

    async def list_sequences(self, db: AsyncSession, user_id: str, robot_id: UUID) -> List[RobotSequence]:
        await robot_service._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(RobotSequence).where(RobotSequence.robot_id == robot_id))
        return list(result.scalars().all())

    async def delete_sequence(self, db: AsyncSession, user_id: str, robot_id: UUID, sequence_id: UUID):
        await robot_service._check_ownership(db, user_id, robot_id)
        
        result = await db.execute(select(RobotSequence).where(RobotSequence.id == sequence_id).where(RobotSequence.robot_id == robot_id))
        sequence = result.scalars().first()
        
        if not sequence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
            
        await db.delete(sequence)
        await db.commit()

sequence_service = SequenceService()
