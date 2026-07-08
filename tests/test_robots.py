import pytest
import hashlib
from jose import jwt
from app.core.config import settings
from app.models.robot import Robot
from app.models.robot_ownership import RobotOwnership
from app.models.robot_event import RobotEvent

def get_auth_headers(user_id: str):
    token = jwt.encode({"sub": user_id}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.anyio
async def test_register_robot_success(client, db):
    response = await client.post(
        "/api/v1/robots/register",
        json={
            "robot_id": "robot-123",
            "serial_key": "serial123",
            "name": "Grabber Alpha",
            "model": "GRABBER-V1",
            "firmware_version": "1.0.0"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["robot_id"] == "robot-123"
    assert "id" in data

    # Verify in DB
    from sqlmodel import select
    result = await db.execute(select(Robot).where(Robot.robot_id == "robot-123"))
    robot = result.scalars().first()
    assert robot is not None
    assert robot.name == "Grabber Alpha"
    assert robot.serial_key_hash == hashlib.sha256(b"serial123").hexdigest()

@pytest.mark.anyio
async def test_register_robot_duplicate(client, db):
    # Pre-register a robot
    robot = Robot(
        robot_id="robot-123",
        serial_key_hash=hashlib.sha256(b"serial123").hexdigest(),
        name="Grabber Alpha",
        model="GRABBER-V1"
    )
    db.add(robot)
    await db.commit()

    response = await client.post(
        "/api/v1/robots/register",
        json={
            "robot_id": "robot-123",
            "serial_key": "serial123",
            "name": "Grabber Beta",
            "model": "GRABBER-V1"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Robot already registered"

@pytest.mark.anyio
async def test_pair_robot_success(client, db):
    robot = Robot(
        robot_id="robot-pair",
        serial_key_hash=hashlib.sha256(b"serial123").hexdigest(),
        name="To Pair",
        model="GRABBER-V1"
    )
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    response = await client.post(
        "/api/v1/robots/pair",
        json={"robotId": "robot-pair", "serialKey": "serial123"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify ownership and event in DB
    from sqlmodel import select
    result = await db.execute(
        select(RobotOwnership).where(RobotOwnership.robot_id == robot.id)
    )
    ownership = result.scalars().first()
    assert ownership is not None
    assert ownership.user_id == "user-abc"

    event_result = await db.execute(
        select(RobotEvent).where(RobotEvent.robot_id == robot.id)
    )
    event = event_result.scalars().first()
    assert event is not None
    assert event.event_type == "ROBOT_PAIRED"

@pytest.mark.anyio
async def test_pair_robot_not_found(client, db):
    headers = get_auth_headers("user-abc")
    response = await client.post(
        "/api/v1/robots/pair",
        json={"robotId": "nonexistent", "serialKey": "serial123"},
        headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Robot not found"

@pytest.mark.anyio
async def test_pair_robot_invalid_serial_key(client, db):
    robot = Robot(
        robot_id="robot-invalid-key",
        serial_key_hash=hashlib.sha256(b"serial123").hexdigest(),
        name="Robot",
        model="GRABBER-V1"
    )
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    response = await client.post(
        "/api/v1/robots/pair",
        json={"robotId": "robot-invalid-key", "serialKey": "wrongserial"},
        headers=headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid serial key"

@pytest.mark.anyio
async def test_pair_robot_already_paired(client, db):
    robot = Robot(
        robot_id="robot-already-paired",
        serial_key_hash=hashlib.sha256(b"serial123").hexdigest(),
        name="Robot",
        model="GRABBER-V1"
    )
    db.add(robot)
    await db.commit()

    # Create pre-existing ownership
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-other", role="OWNER")
    db.add(ownership)
    await db.commit()

    headers = get_auth_headers("user-abc")
    response = await client.post(
        "/api/v1/robots/pair",
        json={"robotId": "robot-already-paired", "serialKey": "serial123"},
        headers=headers
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Robot is already paired"

@pytest.mark.anyio
async def test_get_my_robots(client, db):
    robot1 = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    robot2 = Robot(robot_id="r2", serial_key_hash="hash", name="R2", model="M2")
    db.add_all([robot1, robot2])
    await db.commit()

    ownership = RobotOwnership(robot_id=robot1.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    headers = get_auth_headers("user-abc")
    response = await client.get("/api/v1/robots", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["robot_id"] == "r1"

@pytest.mark.anyio
async def test_get_robot_by_id(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    # Get details without pairing (unauthorized)
    headers = get_auth_headers("user-abc")
    response = await client.get(f"/api/v1/robots/{robot.id}", headers=headers)
    assert response.status_code == 403

    # Pair and try again
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    response = await client.get(f"/api/v1/robots/{robot.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "R1"

@pytest.mark.anyio
async def test_update_robot(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    # Try update without pairing
    response = await client.patch(
        f"/api/v1/robots/{robot.id}",
        json={"name": "New Name"},
        headers=headers
    )
    assert response.status_code == 403

    # Pair and try update
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    response = await client.patch(
        f"/api/v1/robots/{robot.id}",
        json={"name": "New Name"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

@pytest.mark.anyio
async def test_unpair_robot(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    # Unpair without ownership
    response = await client.delete(f"/api/v1/robots/{robot.id}", headers=headers)
    assert response.status_code == 403

    # Pair and unpair
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    response = await client.delete(f"/api/v1/robots/{robot.id}", headers=headers)
    assert response.status_code == 204

    # Verify deleted
    from sqlmodel import select
    res = await db.execute(select(RobotOwnership).where(RobotOwnership.robot_id == robot.id))
    assert res.scalars().first() is None
