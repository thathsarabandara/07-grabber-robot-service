# 🤖 Grabber Robot Service

> **Repository `07`** · The central command orchestration service for the Grabber platform. Validates commands, manages robot states, and bridges HTTP/REST requests to MQTT.

[![Language](https://img.shields.io/badge/Language-Python-3776AB?logo=python)]()
[![Framework](https://img.shields.io/badge/Framework-FastAPI-009688?logo=fastapi)]()
[![Messaging](https://img.shields.io/badge/Messaging-Paho--MQTT-3C3C3D?logo=mqtt)]()
[![Database](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20Redis-blue)]()
[![Status](https://img.shields.io/badge/Status-Planned-yellow)]()

---

## 🧭 What Is This Repository?

The **Robot Service** is the "command brain" of the backend, implemented in **Python / FastAPI**. It handles the logic of what the robot should do next. It is decoupled from authentication and telemetry to ensure that high-frequency data or security updates don't impact the core command pipeline.

---

## 📦 Module Structure

```
07-grabber-robot-service/
├── app/
│   ├── commands/          ← Validate, queue, and publish joint commands via MQTT
│   ├── ownership/         ← Verify caller owns target robot (calls Auth Service)
│   ├── tasks/             ← Task scheduling, timed sequences, automated routines
│   ├── state/             ← Robot connection status, current mode, last-known position
│   ├── mqtt_bridge/       ← Async MQTT client for command/response coordination
│   └── models/            ← SQLAlchemy / SQLModel definitions
├── migrations/            ← Alembic database migrations (PostgreSQL)
├── requirements.txt
└── README.md
```

---

## ⚙️ Core Functions

| Function | Description |
|---|---|
| **Command Validation** | Checks joint limits (J1-J4) before publishing to MQTT using Python logic. |
| **Ownership Verification** | Ensures the requesting user has the `owner` or `operator` role for the specific robot. |
| **MQTT Bridge** | Converts REST API calls into MQTT messages using `paho-mqtt` or `aiomqtt`. |
| **Task Sequencing** | Allows users to record a series of movements and play them back as a "Job". |
| **State Management** | Tracks if a robot is online and its current status in Redis. |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL ≥ 14
- MQTT Broker (Mosquitto / EMQX)

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Run migrations
alembic upgrade head
# Start dev server
uvicorn app.main:app --reload
```

---

## 🔗 Related Repositories
| Repo | Role |
|---|---|
| [`01-grabber-architecture`](../01-grabber-architecture) | Command schema and MQTT topic design |
| [`02-grabber-firmware`](../02-grabber-firmware) | Receives MQTT commands published by this service |
| [`06-grabber-auth-service`](../06-grabber-auth-service) | Provides ownership and permission data |
| [`09-grabber-ai-service`](../09-grabber-ai-service) | Sends target coordinates for automated picking |

---
<div align="center">
  <sub>Part of the <strong>Grabber</strong> AI-Powered Industrial Robotic Arm Platform</sub>
</div>
