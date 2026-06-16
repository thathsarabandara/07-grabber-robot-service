import asyncio
import json
import logging
from datetime import datetime
import aiomqtt
from sqlmodel import select
from app.core.config import settings
from app.core.db import async_session_maker
from app.core.redis import redis_client
from app.models.robot import Robot
from app.services.event_service import event_service
from app.services.websocket_manager import manager

logger = logging.getLogger("mqtt_subscriber")
logging.basicConfig(level=logging.INFO)

async def update_robot_state_in_db(robot_string_id: str, state: str, firmware: str = None):
    """
    Updates the database with the robot status if it changed or if the last update was old.
    To avoid excessive writes, we only write if:
    1. State changed.
    2. DB last_seen is older than 60 seconds.
    """
    async with async_session_maker() as session:
        statement = select(Robot).where(Robot.robot_id == robot_string_id)
        result = await session.execute(statement)
        robot = result.scalar_one_or_none()
        
        if not robot:
            logger.warning(f"Robot {robot_string_id} not registered in DB.")
            return None
        
        now = datetime.utcnow()
        state_changed = robot.status != state
        time_elapsed = (now - robot.last_seen).total_seconds() if robot.last_seen else 999999
        
        if state_changed or time_elapsed > 60:
            robot.status = state
            robot.last_seen = now
            if firmware:
                robot.firmware_version = firmware
            robot.updated_at = now
            session.add(robot)
            await session.commit()
            await session.refresh(robot)
            logger.info(f"Updated DB status for robot {robot_string_id} to {state}")
        
        return robot

async def mqtt_subscriber_task():
    logger.info("Starting MQTT Subscriber background task...")
    
    # Run in a loop to auto-reconnect if MQTT broker restarts or connection drops
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
            ) as client:
                logger.info("MQTT Client connected to broker.")
                
                # Subscribe to topics
                await client.subscribe("robot/+/heartbeat")
                await client.subscribe("robot/+/status")
                await client.subscribe("robot/+/errors")
                await client.subscribe("robot/+/telemetry")
                
                logger.info("Subscribed to robot channels.")
                
                async for message in client.messages:
                    topic = str(message.topic)
                    payload_bytes = message.payload
                    
                    try:
                        payload_str = payload_bytes.decode("utf-8")
                        payload = json.loads(payload_str) if payload_str else {}
                    except Exception:
                        payload = {"status": payload_bytes.decode("utf-8", errors="ignore")}
                    
                    parts = topic.split("/")
                    if len(parts) < 3:
                        continue
                    robot_id = parts[1]
                    subtopic = parts[2]
                    
                    logger.info(f"Received MQTT message on {topic}: {payload}")
                    
                    now_timestamp = int(datetime.utcnow().timestamp())
                    state = "IDLE"
                    firmware = None
                    
                    if subtopic == "heartbeat":
                        state = payload.get("state", "IDLE")
                        firmware = payload.get("firmware")
                    elif subtopic == "status":
                        state = payload.get("state") or payload.get("status") or "IDLE"
                    elif subtopic == "errors":
                        state = "ERROR_STATE"
                        error_code = payload.get("errorCode", "UNKNOWN_ERROR")
                        
                        db_robot = await update_robot_state_in_db(robot_id, state)
                        if db_robot:
                            async with async_session_maker() as session:
                                await event_service.log_event(
                                    db=session,
                                    robot_id=db_robot.id,
                                    event_type="ERROR",
                                    payload={"errorCode": error_code, "details": payload}
                                )
                    elif subtopic == "telemetry":
                        telemetry_key = f"robot:{robot_id}:telemetry"
                        await redis_client.set(telemetry_key, json.dumps(payload))
                        continue
                    
                    if state == "ERROR":
                        state = "ERROR_STATE"
                        
                    # Update Redis
                    await redis_client.set(f"robot:{robot_id}:last_seen", str(now_timestamp))
                    
                    status_data = {
                        "robotId": robot_id,
                        "status": state,
                        "state": state,
                        "lastSeen": now_timestamp,
                        "firmware": firmware
                    }
                    await redis_client.set(f"robot:{robot_id}:status", json.dumps(status_data))
                    
                    if subtopic != "errors":
                        await update_robot_state_in_db(robot_id, state, firmware)
                    
                    # WebSocket broadcast
                    await manager.broadcast({
                        "robotId": robot_id,
                        "status": state,
                        "state": state,
                        "firmware": firmware
                    })
                    
        except aiomqtt.MqttError as e:
            logger.error(f"MQTT client connection error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error in MQTT subscriber: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def heartbeat_monitor_task():
    logger.info("Starting Heartbeat Monitor background task...")
    while True:
        try:
            await asyncio.sleep(5)
            now = datetime.utcnow()
            now_ts = int(now.timestamp())
            
            async with async_session_maker() as session:
                statement = select(Robot).where(Robot.status != "OFFLINE")
                result = await session.execute(statement)
                active_robots = result.scalars().all()
                
                for robot in active_robots:
                    last_seen_ts = None
                    
                    # Try to load from Redis
                    redis_val = await redis_client.get(f"robot:{robot.robot_id}:last_seen")
                    if redis_val:
                        try:
                            last_seen_ts = int(redis_val)
                        except ValueError:
                            pass
                    
                    if last_seen_ts is None:
                        if robot.last_seen:
                            last_seen_ts = int(robot.last_seen.timestamp())
                        else:
                            last_seen_ts = int(robot.created_at.timestamp())
                    
                    if now_ts - last_seen_ts > 15:
                        logger.info(f"Robot {robot.robot_id} heartbeat timeout. Transitioning to OFFLINE.")
                        
                        robot.status = "OFFLINE"
                        robot.updated_at = now
                        session.add(robot)
                        await session.commit()
                        
                        status_data = {
                            "robotId": robot.robot_id,
                            "status": "OFFLINE",
                            "state": "OFFLINE",
                            "lastSeen": last_seen_ts,
                            "firmware": robot.firmware_version
                        }
                        await redis_client.set(f"robot:{robot.robot_id}:status", json.dumps(status_data))
                        
                        await manager.broadcast({
                            "robotId": robot.robot_id,
                            "status": "OFFLINE",
                            "state": "OFFLINE"
                        })
                        
        except Exception as e:
            logger.error(f"Error in heartbeat monitor: {e}")
