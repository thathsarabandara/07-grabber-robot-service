import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.db import get_db
from app.models.robot import Robot
from app.models.robot_event import RobotEvent
from app.services.mqtt_subscriber import (
    update_robot_state_in_db,
    mqtt_subscriber_task,
    heartbeat_monitor_task
)
from app.services.websocket_manager import ConnectionManager
from app.services.mqtt_service import mqtt_service

@pytest.mark.anyio
async def test_get_db_generator():
    async for db in get_db():
        assert db is not None

@pytest.mark.anyio
async def test_websocket_manager():
    manager = ConnectionManager()
    
    # Mock WebSocket
    mock_ws1 = MagicMock()
    mock_ws1.accept = AsyncMock()
    mock_ws1.send_text = AsyncMock()
    
    mock_ws2 = MagicMock()
    mock_ws2.accept = AsyncMock()
    # Mock ws2 to raise exception to test disconnect handling
    mock_ws2.send_text = AsyncMock(side_effect=Exception("WS Closed"))

    # Connect
    await manager.connect(mock_ws1)
    await manager.connect(mock_ws2)
    assert len(manager.active_connections) == 2

    # Broadcast
    await manager.broadcast({"message": "hello"})
    mock_ws1.send_text.assert_called_once()
    mock_ws2.send_text.assert_called_once()
    
    # Assert ws2 was disconnected due to error
    assert len(manager.active_connections) == 1
    assert mock_ws2 not in manager.active_connections

    # Disconnect remaining
    manager.disconnect(mock_ws1)
    assert len(manager.active_connections) == 0

    # Disconnect already disconnected does nothing
    manager.disconnect(mock_ws1)

@pytest.mark.anyio
async def test_mqtt_publish_exception():
    with patch("aiomqtt.Client", side_effect=Exception("MQTT Conn Error")) as mock_client:
        # Should catch exception internally and print log
        await mqtt_service.publish_command("r1", "move-joint", {"angle": 90.0})
        mock_client.assert_called_once()

@pytest.mark.anyio
async def test_update_robot_state_in_db(db):
    # Setup robot
    robot = Robot(
        robot_id="r-update",
        serial_key_hash="hash",
        name="Robot",
        model="V1",
        status="IDLE",
        last_seen=datetime.utcnow() - timedelta(seconds=120)
    )
    db.add(robot)
    await db.commit()

    # Test state changed updates last_seen and status
    updated_robot = await update_robot_state_in_db("r-update", "RUNNING")
    assert updated_robot is not None
    assert updated_robot.status == "RUNNING"
    last_seen_time = updated_robot.last_seen

    # Test state same but time elapsed < 60 seconds (does NOT update)
    updated_robot_2 = await update_robot_state_in_db("r-update", "RUNNING")
    assert updated_robot_2.last_seen == last_seen_time

    # Test state same but time elapsed > 60 seconds (updates last_seen)
    # Manually shift last_seen back in DB
    updated_robot_2.last_seen = datetime.utcnow() - timedelta(seconds=120)
    db.add(updated_robot_2)
    await db.commit()

    updated_robot_3 = await update_robot_state_in_db("r-update", "RUNNING")
    assert updated_robot_3.last_seen > last_seen_time

    # Test robot not found in DB
    result = await update_robot_state_in_db("nonexistent-r", "IDLE")
    assert result is None

class MockMqttMessage:
    def __init__(self, topic: str, payload: bytes):
        self.topic = topic
        self.payload = payload

@pytest.mark.anyio
@patch("app.services.mqtt_subscriber.asyncio.sleep", new_callable=AsyncMock)
async def test_mqtt_subscriber_task(mock_sleep, db, mock_redis):
    # Setup registered robot
    robot = Robot(
        robot_id="robot-abc",
        serial_key_hash="hash",
        name="Robot ABC",
        model="V1",
        status="IDLE"
    )
    db.add(robot)
    await db.commit()

    async def mock_messages():
        yield MockMqttMessage("robot/robot-abc/heartbeat", b'{"state": "RUNNING", "firmware": "1.0.1"}')
        yield MockMqttMessage("robot/robot-abc/status", b'{"status": "IDLE"}')
        yield MockMqttMessage("robot/robot-abc/errors", b'{"errorCode": "ERR001"}')
        yield MockMqttMessage("robot/robot-abc/telemetry", b'{"temp": 45}')
        yield MockMqttMessage("robot/robot-abc/invalid", b'{}')
        yield MockMqttMessage("invalid_topic", b'{}')
        yield MockMqttMessage("robot/robot-abc/heartbeat", b'invalid-json')
        # Raise CancelledError to break the subscriber loop
        raise asyncio.CancelledError()

    mock_client_instance = AsyncMock()
    mock_client_instance.messages = mock_messages()
    
    # Run task and verify execution of loops
    with patch("aiomqtt.Client") as mock_client:
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        try:
            # We bypass app.main background mock since we call this directly
            await mqtt_subscriber_task()
        except asyncio.CancelledError:
            pass

    # Verify Redis updates and Error Event logged
    redis_status = await mock_redis.get("robot:robot-abc:status")
    assert redis_status is not None
    
    from sqlmodel import select
    event_res = await db.execute(select(RobotEvent).where(RobotEvent.robot_id == robot.id))
    event = event_res.scalars().first()
    assert event is not None
    assert event.event_type == "ERROR"

@pytest.mark.anyio
@patch("app.services.mqtt_subscriber.asyncio.sleep")
async def test_heartbeat_monitor_task(mock_sleep, db, mock_redis):
    # Setup two robots: one active, one offline timed out
    robot_active = Robot(
        robot_id="r-active",
        serial_key_hash="hash",
        name="Active",
        model="V1",
        status="IDLE",
        last_seen=datetime.utcnow()
    )
    robot_offline = Robot(
        robot_id="r-offline",
        serial_key_hash="hash",
        name="Offline",
        model="V1",
        status="IDLE",
        last_seen=datetime.utcnow() - timedelta(seconds=30)
    )
    db.add_all([robot_active, robot_offline])
    await db.commit()

    # Pre-populate Redis last_seen for r-active
    await mock_redis.set("robot:r-active:last_seen", str(int(datetime.utcnow().timestamp())))
    
    # Mock sleep to raise CancelledError after first execution
    mock_sleep.side_effect = [None, asyncio.CancelledError()]

    try:
        await heartbeat_monitor_task()
    except asyncio.CancelledError:
        pass

    # Verify r-offline is transitioned to OFFLINE, r-active remains IDLE
    db.expire_all()
    await db.refresh(robot_active)
    await db.refresh(robot_offline)

    assert robot_active.status == "IDLE"
    assert robot_offline.status == "OFFLINE"

    # Verify Redis status updated for offline robot
    offline_status_val = await mock_redis.get("robot:r-offline:status")
    assert offline_status_val is not None
    assert json.loads(offline_status_val)["status"] == "OFFLINE"

@pytest.mark.anyio
@patch("app.services.mqtt_subscriber.asyncio.sleep")
async def test_heartbeat_monitor_task_exception(mock_sleep, db):
    # Mock sleep to raise Exception to test exception log flow
    mock_sleep.side_effect = Exception("Sleep Error")
    
    # Should catch exception internally and not raise
    with patch("app.services.mqtt_subscriber.logger") as mock_logger:
        # Run one loop iteration by raising CancelledError on second loop
        mock_sleep.side_effect = [None, asyncio.CancelledError()]
        # Mock database fetch to throw exception
        with patch("app.services.mqtt_subscriber.async_session_maker", side_effect=Exception("DB Error")):
            try:
                await heartbeat_monitor_task()
            except asyncio.CancelledError:
                pass
            mock_logger.error.assert_called_with("Error in heartbeat monitor: DB Error")

@pytest.mark.anyio
@patch("app.services.mqtt_subscriber.asyncio.sleep")
async def test_mqtt_subscriber_exception_reconnect(mock_sleep):
    # Test subscriber reconnect flow upon MQTT connection errors
    # Mock Client context manager to raise MqttError first, then CancelledError
    from aiomqtt import MqttError
    
    with patch("aiomqtt.Client", side_effect=[MqttError("Conn Failed"), asyncio.CancelledError()]):
        try:
            await mqtt_subscriber_task()
        except asyncio.CancelledError:
            pass
        mock_sleep.assert_called_with(5)

def test_event_response_schema():
    import uuid
    from app.schemas.event import EventResponse
    uid = uuid.uuid4()
    now = datetime.utcnow()
    res = EventResponse(id=uid, event_type="COMMAND", payload={"angle": 90}, created_at=now)
    assert res.id == uid
    assert res.event_type == "COMMAND"

@pytest.mark.anyio
async def test_security_validation_failures(client):
    from jose import jwt
    from app.core.config import settings
    
    # 1. Missing token
    response = await client.get("/api/v1/robots")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
    
    # 2. Token decode error (ValidationError/JWTError)
    response = await client.get("/api/v1/robots", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
    
    # 3. Token decode success but no sub claim
    token = jwt.encode({"claim": "value"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = await client.get("/api/v1/robots", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

