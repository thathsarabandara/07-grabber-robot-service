import pytest
import uuid
from jose import jwt
from app.core.config import settings
from app.models.robot import Robot
from app.models.robot_ownership import RobotOwnership
from app.models.robot_pose import RobotPose
from app.models.robot_command import RobotCommand

def get_auth_headers(user_id: str):
    token = jwt.encode({"sub": user_id}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.anyio
async def test_poses_unauthorized(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    headers = get_auth_headers("user-abc")
    
    # Save
    response = await client.post(
        f"/api/v1/robots/{robot.id}/poses",
        json={"name": "Pose A", "pose": {"j1": 45}},
        headers=headers
    )
    assert response.status_code == 403

    # List
    response = await client.get(f"/api/v1/robots/{robot.id}/poses", headers=headers)
    assert response.status_code == 403

@pytest.mark.anyio
async def test_poses_success_flow(client, db):
    robot = Robot(robot_id="r1", serial_key_hash="hash", name="R1", model="M1")
    db.add(robot)
    await db.commit()

    # Pair robot
    ownership = RobotOwnership(robot_id=robot.id, user_id="user-abc", role="OWNER")
    db.add(ownership)
    await db.commit()

    headers = get_auth_headers("user-abc")

    # 1. Save pose
    response = await client.post(
        f"/api/v1/robots/{robot.id}/poses",
        json={"name": "Pose A", "pose": {"j1": 45}},
        headers=headers
    )
    assert response.status_code == 201
    pose_data = response.json()
    assert pose_data["name"] == "Pose A"
    pose_id = pose_data["id"]

    # 2. List poses
    response = await client.get(f"/api/v1/robots/{robot.id}/poses", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == pose_id

    # 3. Execute pose
    response = await client.post(
        f"/api/v1/robots/{robot.id}/poses/{pose_id}/execute",
        headers=headers
    )
    assert response.status_code == 202
    
    # Verify execute command created in DB
    from sqlmodel import select
    cmd_res = await db.execute(select(RobotCommand).where(RobotCommand.robot_id == robot.id))
    cmd = cmd_res.scalars().first()
    assert cmd is not None
    assert cmd.command_type == "execute-pose"

    # 4. Delete pose
    response = await client.delete(
        f"/api/v1/robots/{robot.id}/poses/{pose_id}",
        headers=headers
    )
    assert response.status_code == 204

    # Verify deleted from DB
    pose_res = await db.execute(select(RobotPose).where(RobotPose.id == uuid.UUID(pose_id)))
    assert pose_res.scalars().first() is None

    # 5. Delete nonexistent / already deleted pose (404)
    response = await client.delete(
        f"/api/v1/robots/{robot.id}/poses/{pose_id}",
        headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Pose not found"

    # 6. Execute nonexistent / already deleted pose (404)
    response = await client.post(
        f"/api/v1/robots/{robot.id}/poses/{pose_id}/execute",
        headers=headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Pose not found"
