from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.robot_event import RobotEvent

class EventService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        robot_id: UUID,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> RobotEvent:
        event = RobotEvent(
            robot_id=robot_id,
            event_type=event_type,
            payload=payload
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

event_service = EventService()
