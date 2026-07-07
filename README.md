# 🤖 Grabber Robot Service

> **Repository `07`** · Central command orchestration and state tracking service for the Grabber robotic arm — built on Python 3.11, FastAPI, and SQLModel. Governs hardware pairings, joint limit validations, movement recording/sequences, state tracking caches via Redis, and bridges REST API controls to async MQTT messages using `aiomqtt`.

[![Language](https://img.shields.io/badge/Language-Python%203.11-3776AB?logo=python&style=flat-square)]()
[![Framework](https://img.shields.io/badge/Framework-FastAPI-009688?logo=fastapi&style=flat-square)]()
[![ORM](https://img.shields.io/badge/ORM-SQLModel-green.svg?style=flat-square)]()
[![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20Redis-blue.svg?style=flat-square)]()
[![Messaging](https://img.shields.io/badge/Messaging-MQTT-3C3C3D?logo=mqtt&style=flat-square)]()
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg?style=flat-square)]()

---

## 🎥 Video Demonstration

<div align="center">
  <a href="https://youtu.be/AIpGv0F3Nn4?si=I0dn1miMGKsiwt1f">
    <img src="https://img.youtube.com/vi/AIpGv0F3Nn4/maxresdefault.jpg" alt="Grabber Demo Video" width="70%">
  </a>
  <br/>
  <sub>Click the image above to watch the demonstration video on YouTube.</sub>
</div>

---

## 🧭 What Is This Repository?

The **Robot Service** is the logical control center of the Grabber system. It acts as the core interpreter between operator client interfaces and the physical ESP32 controllers. 

### Key Core Functions
1. **REST-to-MQTT Command Bridge**: Converts standard REST requests from clients into async MQTT messages parsed by the ESP32 firmware.
2. **Hardware Pairing & Permissions**: Enforces explicit device-to-user database bindings (`robot_ownerships` table), ensuring only authorized operators can issue commands.
3. **Background Lifespan Tasks**:
   * **MQTT Subscriber**: Subscribes to hardware heartbeats, logs errors, and updates live status records.
   * **Heartbeat Monitor**: Audits active connections every 5 seconds. If a robot fails to report within 15 seconds, it transitions to `OFFLINE` and notifies connected clients.
4. **Pose & Sequence Recording**: Manages custom coordinate poses and re-playable sequence macros, allowing operators to record and play back movement routines.
5. **Real-time Status Broadcaster**: Mounts a WebSocket endpoint to instantly broadcast state updates to clients.

---

## 📦 Project Structure

The project implements a clean layer division, separating database structures, Pydantic parameters, API routers, and connection managers:

```
07-grabber-robot-service/
├── app/
│   ├── api/                 # Endpoint routers and dependency injection
│   │   ├── deps.py          # JWT extraction utilities
│   │   └── routes/          # Core routers (robots, commands, poses, sequences, health)
│   ├── core/                # Database connections, Redis clients, and server configurations
│   │   ├── config.py        # Pydantic settings config base
│   │   ├── db.py            # Async engine and SQLModel table initializations
│   │   ├── redis.py         # Redis connection client setup
│   │   └── security.py      # JWT token parsing dependencies
│   ├── models/              # SQLModel database schemas (Robot, Command, Pose, Sequence, Event)
│   ├── schemas/             # Pydantic schemas validating payloads
│   ├── services/            # Logical business services (Command, Pose, Sequence executors)
│   └── main.py              # Application lifespan management and WebSocket endpoints
├── Dockerfile               # Production multi-stage build configuration
├── docker-compose.yml       # Dev stack execution setups
├── requirements.txt         # Production library dependencies
└── README.md
```

### Module Code Index

* **App Core & Startup**:
  * [app/main.py](app/main.py): Registers the application lifespan. Runs database initializations (`init_db`) and spawns the background MQTT subscriber and heartbeat monitor tasks. It also hosts the WebSocket endpoint (`/api/v1/robots/ws`) to broadcast state changes.
  * [app/core/db.py](app/core/db.py): Creates the async engine using `aiomysql` and maps `SQLModel.metadata.create_all` to synchronize MySQL tables.
  * [app/core/redis.py](app/core/redis.py): Creates the Redis client for state caching.
  * [app/core/security.py](app/core/security.py): Decodes the JWT access token passed from the API Gateway and sets the operator's `user_id`.

* **API Endpoint Routers**:
  * [app/api/routes/robots.py](app/api/routes/robots.py): Handles robot registration, user pairing, unpairing, and name updates.
  * [app/api/routes/commands.py](app/api/routes/commands.py): Endpoint mapping for physical commands, routing move-joint, homing, and emergency stops.
  * [app/api/routes/poses.py](app/api/routes/poses.py): Endpoint mapping for custom poses (save, list, delete, and execute).
  * [app/api/routes/sequences.py](app/api/routes/sequences.py): Enpoints for re-playable sequence macros.

* **Business Services**:
  * [app/services/robot_service.py](app/services/robot_service.py): Manages robot pairing, verifies serial key hashes, and checks user authorization.
  * [app/services/command_service.py](app/services/command_service.py): Validates requests, saves execution logs, and publishes commands via the MQTT service.
  * [app/services/pose_service.py](app/services/pose_service.py): Handles custom coordinate pose logic.
  * [app/services/sequence_service.py](app/services/sequence_service.py): Records movement sequence frames and triggers macro playbacks.
  * [app/services/mqtt_service.py](app/services/mqtt_service.py): Publishes target angles and emergency halts to the MQTT broker using JSON payloads.
  * [app/services/mqtt_subscriber.py](app/services/mqtt_subscriber.py): Listens to hardware topics, handles heartbeats and error codes, updates status logs, and broadcasts updates via WebSockets.
  * [app/services/websocket_manager.py](app/services/websocket_manager.py): Broadcasts status updates to all active WebSocket clients.

---

## 📊 Database Schema Specifications

The service connects to a MySQL instance and uses **SQLModel** to define table structures:

### 1. Robots Table (`robots`)
Stores registered robotic arms in the ecosystem.
```python
class Robot(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: str = Field(unique=True, index=True, max_length=100) -- e.g., ROB_XYZ
    serial_key_hash: str                                          -- SHA-256 hash
    name: Optional[str] = Field(default=None, max_length=255)
    firmware_version: Optional[str] = Field(default=None, max_length=50)
    model: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default="OFFLINE", max_length=50)
    last_seen: Optional[datetime] = Field(default=None)
```

### 2. Robot Ownerships Table (`robot_ownerships`)
Tracks user-to-robot permission maps.
```python
class RobotOwnership(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)                       -- References robots.id
    user_id: str = Field(index=True)                              -- Matches JWT user ID
    role: str = Field(default="OWNER", max_length=50)
```

### 3. Robot Commands Table (`robot_commands`)
Audit log for all REST commands sent to the robot.
```python
class RobotCommand(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    user_id: str = Field(index=True)
    command_type: str = Field(max_length=100)                      -- e.g., move-joint
    payload: Optional[Dict[str, Any]] = Field(sa_column=sa.Column(sa.JSON))
    status: str = Field(default="PENDING", max_length=50)
    executed_at: Optional[datetime] = Field(default=None)
```

### 4. Robot Poses Table (`robot_poses`)
Stores saved joint coordinates.
```python
class RobotPose(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=255)
    pose: Dict[str, Any] = Field(default={}, sa_column=sa.Column(sa.JSON)) -- e.g., {"j1": 90, "j2": 100}
```

### 5. Robot Sequences Table (`robot_sequences`)
Stores macro lists of movement frames.
```python
class RobotSequence(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    name: str = Field(max_length=255)
    frames: List[Dict[str, Any]] = Field(default=[], sa_column=sa.Column(sa.JSON))
```

### 6. Robot Events Table (`robot_events`)
Diagnostic system event logs (e.g., E-Stop triggered, errors reported by firmware).
```python
class RobotEvent(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    robot_id: uuid.UUID = Field(index=True)
    event_type: str = Field(max_length=100)                        -- e.g., EMERGENCY_STOP
    payload: Optional[Dict[str, Any]] = Field(sa_column=sa.Column(sa.sa.JSON))
```

---

## ⚡ MQTT Messaging & Topics Schema

The robot service uses `aiomqtt` to coordinate communication with the physical arm.

```
Robot Service                     MQTT Broker                      ESP32 Firmware
      |                                |                                 |
      |--- Publish Command ------------>|                                 |
      |    (topic: robot/ROB/commands)  |--- Deliver Command ------------>|
      |                                |                                 |
      |                                |<-- Publish Heartbeat -----------|
      |<-- Receive Heartbeat ----------|    (topic: robot/ROB/heartbeat) |
```

### Outbound Commands Topics
* **Move Joint**: `robot/{robot_id}/commands/move`
  * Payload schema: `{"servo": <servo_index_0_to_3>, "angle": <angle_float>}`
  * Note: Joint values are mapped to servo indices (`j1` -> 0, `j2` -> 1, `j3` -> 2, `j4` -> 3).
* **Emergency Halt**: `robot/{robot_id}/commands/estop`
  * Payload: `{}`
* **Clear E-Stop Lock**: `robot/{robot_id}/commands/clear_estop`
  * Payload: `{}`
* **Home Calibration**: `robot/{robot_id}/commands/home`
  * Payload: `{}`
* **Execute Saved Pose**: `robot/{robot_id}/commands/execute-pose`
  * Payload: `{"j1": 90.0, "j2": 100.0, "j3": 60.0, "j4": 90.0}`

### Subscribed Telemetry Topics
The background subscriber task listens to the following topics:
* **Heartbeat**: `robot/+/heartbeat`
  * Payload: `{"state": "IDLE/BUSY/ERROR", "firmware": "1.0.0"}`
  * Note: Updates the last-seen timestamp and status in Redis and the DB.
* **Status**: `robot/+/status`
  * Payload: `{"state": "IDLE/BUSY/ERROR"}`
* **Errors**: `robot/+/errors`
  * Payload: `{"errorCode": "SERVO_OVERLOAD", "details": "..."}`
  * Note: Logs a database event and transitions the robot's status to `ERROR_STATE`.

---

## ⚙️ Core API Endpoints

### 1. Robot Configurations
* **Pair Robot**: `POST /api/v1/robots/pair`
  * Request Body: `{"robotId": "ROB_XYZ", "serialKey": "SR_8899"}`
* **List My Robots**: `GET /api/v1/robots`
* **Rename Robot**: `PATCH /api/v1/robots/{robot_id}`
  * Request Body: `{"name": "New Robot Nickname"}`
* **Unpair Robot**: `DELETE /api/v1/robots/{robot_id}`

### 2. Live Control Commands
* **Move Joint**: `POST /api/v1/robots/{robot_id}/commands/move-joint`
  * Request Body: `{"joint": "j1", "angle": 90.0}`
* **Home Calibration**: `POST /api/v1/robots/{robot_id}/commands/home`
* **Emergency Halt**: `POST /api/v1/robots/{robot_id}/commands/emergency-stop`
* **Clear Emergency Halt**: `POST /api/v1/robots/{robot_id}/commands/clear-emergency-stop`

### 3. Poses & Sequence Macros
* **Save Current Pose**: `POST /api/v1/robots/{robot_id}/poses`
  * Request Body: `{"name": "Pick Position", "pose": {"j1": 90.0, "j2": 100.0, "j3": 60.0, "j4": 90.0}}`
* **List Saved Poses**: `GET /api/v1/robots/{robot_id}/poses`
* **Execute Saved Pose**: `POST /api/v1/robots/{robot_id}/poses/{pose_id}/execute`
* **Save Sequence**: `POST /api/v1/robots/{robot_id}/sequences`
  * Request Body: `{"name": "Pick Sequence", "frames": [{"j1": 90.0, "j2": 100.0}, {"j1": 120.0, "j2": 80.0}]}`

---

## 🚀 Getting Started

### 1. Environment Configurations
Create a `.env` configuration file in the project root:
```env
PROJECT_NAME="Grabber Service"

# Async MySQL Database URI
DATABASE_URL="mysql+aiomysql://thathsara:BandaPutha@db/grabber_robot"
PORT=8002

# Redis configuration 
REDIS_URL="redis://redis:6379/0"

# JWT configuration (must match JWT_SECRET in Auth Service)
SECRET_KEY=Eiui9vAzU/yEexBweuDV9E/gDNvliTAoit1nKWTJDWQ=
ALGORITHM="HS256"

# MQTT Broker Configuration
MQTT_BROKER=grabber-mqtt-server
MQTT_PORT=1883
MQTT_USERNAME=thathsara
MQTT_PASSWORD=BandaPutha
```

### 2. Local Setup
Ensure you have Python 3.11+, a running MySQL instance, Redis, and an active MQTT broker:
```bash
# Initialize and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the dev server
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 3. Run via Docker Compose
Build and run the container locally:
```bash
docker compose up -d --build
```

---

## 🔗 Related Grabber Repositories

| Repository | Purpose |
|---|---|
| [`01-grabber-architecture`](https://github.com/thathsarabandara/01-grabber-architecture) | System blueprints, MQTT schemas, and database designs |
| [`02-grabber-firmware`](https://github.com/thathsarabandara/02-grabber-firmware) | ESP32 main controller firmware and servo controls |
| [`03-grabber-mobile-app`](https://github.com/thathsarabandara/03-grabber-mobile-app) | Flutter app remote teleoperation HUD |
| [`05-grabber-api-gateway`](https://github.com/thathsarabandara/05-grabber-api-gateway) | Inbound router proxying app REST & WebSocket requests |
| [`06-grabber-auth-service`](https://github.com/thathsarabandara/06-grabber-auth-service) | Service managing user profiles, image updates, and JWT sessions |
| [`08-grabber-telemetry-service`](https://github.com/thathsarabandara/08-grabber-telemetry-service) | Core service publishing live telemetry and webcam captures |
| [`09-grabber-ai-service`](https://github.com/thathsarabandara/09-grabber-ai-service) | Engine orchestrating autonomous sorting tasks and YOLO models |

---

<div align="center">
  <sub>Part of the <strong>Grabber</strong> AI-Powered Industrial Robotic Arm Platform</sub>
</div>
