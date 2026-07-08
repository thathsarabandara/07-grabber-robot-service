import pytest
from jose import jwt
from app.core.config import settings
from app.models.robot import Robot
from app.models.robot_ownership import RobotOwnership
from app.models.robot_command import RobotCommand
from app.models.robot_event import RobotEvent

def get_auth_headers(user_id: str):
    token = jwt.encode({"sub": user_id}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.anyio
async def test_commands_unauthorized(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    response = await client.post(f"/api/v1/robots/{robot.id}/commands/home", headers=headers)
    assert response.status_code == 403

@pytest.mark.anyio
async def test_commands_success_all(client, db, mock_mqtt):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    # Pair robot
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    headers = get_auth_headers("user-abc")

    # 1. move-joint
    response = await client.post(
        f"/api/v1/robots/{robot.id}/commands/move-joint",
        json={"joint": "j1", "angle": 45.0},
        headers=headers
    )
    assert response.status_code == 202
    data = response.json()
    assert data["command_type"] == "move-joint"
    assert data["status"] == "PENDING"

    # Verify Command and Event in DB
    from sqlmodel import select
    cmd_res = await db.execute(select(RobotCommand).where(RobotCommand.robot_id == robot.id))
    cmd = cmd_res.scalars().first()
    assert cmd is not None
    assert cmd.command_type == "move-joint"
    assert cmd.payload == {"joint": "j1", "angle": 45.0}

    evt_res = await db.execute(
        select(RobotEvent).where(RobotEvent.robot_id == robot.id).where(RobotEvent.event_type == "COMMAND_EXECUTED")
    )
    assert evt_res.scalars().first() is not None

    # 2. home
    response = await client.post(f"/api/v1/robots/{robot.id}/commands/home", headers=headers)
    assert response.status_code == 202

    # 3. open-gripper
    response = await client.post(f"/api/v1/robots/{robot.id}/commands/open-gripper", headers=headers)
    assert response.status_code == 202

    # 4. close-gripper
    response = await client.post(f"/api/v1/robots/{robot.id}/commands/close-gripper", headers=headers)
    assert response.status_code == 202

    # 5. emergency-stop
    response = await client.post(f"/api/v1/robots/{robot.id}/commands/emergency-stop", headers=headers)
    assert response.status_code == 202
    # Verify Emergency Stop Event in DB
    evt_estop = await db.execute(
        select(RobotEvent).where(RobotEvent.robot_id == robot.id).where(RobotEvent.event_type == "EMERGENCY_STOP")
    )
    assert evt_estop.scalars().first() is not None

    # 6. clear-emergency-stop
    response = await client.post(f"/api/v1/robots/{robot.id}/commands/clear-emergency-stop", headers=headers)
    assert response.status_code == 202

    # Verify MQTT publish calls were triggered
    assert mock_mqtt.called
