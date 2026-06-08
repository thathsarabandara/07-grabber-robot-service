from typing import Any, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.robot_command import RobotCommand
from app.services.mqtt_service import mqtt_service
from app.services.event_service import event_service
from app.services.robot_service import robot_service

class CommandService:
    async def execute_command(
        self, 
        db: AsyncSession, 
        user_id: str, 
        robot_id: UUID, 
        command_type: str, 
        payload: Dict[str, Any] = None
    ) -> RobotCommand:
        # Validate ownership
        await robot_service._check_ownership(db, user_id, robot_id)
        
        # In a real app we'd also check if the robot is online.
        
        # Create command record
        command = RobotCommand(
            robot_id=robot_id,
            user_id=user_id,
            command_type=command_type,
            payload=payload,
            status="PENDING"
        )
        db.add(command)
        await db.commit()
        await db.refresh(command)
        
        # Get actual string ID for MQTT topic
        from app.models.robot import Robot
        from sqlalchemy.future import select
        result = await db.execute(select(Robot).where(Robot.id == robot_id))
        robot = result.scalars().first()
        
        if robot:
            # Publish to MQTT
            await mqtt_service.publish_command(robot.robot_id, command_type, payload or {})
            
            # Log specific events like Emergency Stop
            if command_type == "emergency-stop":
                await event_service.log_event(db, robot_id, "EMERGENCY_STOP", {"user_id": user_id})
            else:
                await event_service.log_event(db, robot_id, "COMMAND_EXECUTED", {"command_id": str(command.id), "type": command_type})
                
        return command

command_service = CommandService()
