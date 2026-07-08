from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.schemas.sequence import SequenceCreate, SequenceResponse
from app.services.sequence_service import sequence_service

router = APIRouter()

@router.post("", response_model=SequenceResponse, status_code=status.HTTP_201_CREATED)
async def save_sequence(
    robotId: UUID,
    sequence_data: SequenceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await sequence_service.save_sequence(db, user_id, robotId, sequence_data)

@router.get("", response_model=List[SequenceResponse])
async def list_sequences(
    robotId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await sequence_service.list_sequences(db, user_id, robotId)

@router.delete("/{sequenceId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    robotId: UUID,
    sequenceId: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await sequence_service.delete_sequence(db, user_id, robotId, sequenceId)
