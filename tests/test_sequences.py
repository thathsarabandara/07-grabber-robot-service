import pytest
import uuid
from jose import jwt
from app.core.config import settings
from app.models.robot import Robot
from app.models.robot_ownership import RobotOwnership
from app.models.robot_sequence import RobotSequence

def get_auth_headers(user_id: str):
    token = jwt.encode({"sub": user_id}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.anyio
async def test_sequences_unauthorized(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    
    # Save
    response = await client.post(
        f"/api/v1/robots/{robot.id}/sequences",
        json={"name": "Seq A", "frames": [{"pose1": 10}, {"pose2": 20}]},
        headers=headers
    )
    assert response.status_code == 403

    # List
    response = await client.get(f"/api/v1/robots/{robot.id}/sequences", headers=headers)
    assert response.status_code == 403

@pytest.mark.anyio
async def test_sequences_success_flow(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    # Pair robot
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    headers = get_auth_headers("user-abc")

    # 1. Save sequence
    response = await client.post(
        f"/api/v1/robots/{robot.id}/sequences",
        json={"name": "Seq A", "frames": [{"pose1": 10}, {"pose2": 20}]},
        headers=headers
    )
    assert response.status_code == 201
    seq_data = response.json()
    assert seq_data["name"] == "Seq A"
    seq_id = seq_data["id"]

    # 2. List sequences
    response = await client.get(f"/api/v1/robots/{robot.id}/sequences", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == seq_id

    # 3. Delete sequence
    response = await client.delete(
        f"/api/v1/robots/{robot.id}/sequences/{seq_id}",
        headers=headers
    )
    assert response.status_code == 204

    # Verify deleted from DB
    from sqlmodel import select
    seq_res = await db.execute(select(RobotSequence).where(RobotSequence.id == uuid.UUID(seq_id)))
    assert seq_res.scalars().first() is None

    # 4. Delete nonexistent sequence (404)
    response = await client.delete(
        f"/api/v1/robots/{robot.id}/sequences/{seq_id}",
        headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Sequence not found"
