import json
from typing import Any, Dict
import aiomqtt
from app.core.config import settings

class MQTTService:
    def __init__(self):
        self.broker = settings.MQTT_BROKER
        self.port = settings.MQTT_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD

    async def publish_command(self, robot_id: str, command_type: str, payload: Dict[str, Any]):
        subtopic = command_type
        if command_type == "move-joint":
            subtopic = "move"
            # Map joint string (e.g. 'j1') to servo index (e.g. 0)
            joint_map = {"j1": 0, "j2": 1, "j3": 2, "j4": 3}
            joint_str = payload.get("joint")
            servo_index = joint_map.get(joint_str, 0)
            payload = {
                "servo": servo_index,
                "angle": float(payload.get("angle", 0))
            }
        elif command_type == "emergency-stop":
            subtopic = "estop"
        elif command_type == "clear-emergency-stop":
            subtopic = "clear_estop"
            
        topic = f"robot/{robot_id}/commands/{subtopic}"
        message = json.dumps(payload)
        
        try:
            async with aiomqtt.Client(
                hostname=self.broker,
                port=self.port,
                username=self.username,
                password=self.password
            ) as client:
                await client.publish(topic, message)
                print(f"Published to {topic}: {message}")
        except Exception as e:
            print(f"Failed to publish MQTT message: {e}")
            # In a real app we might want to retry or raise, 
            # but for V1 we just log it.

mqtt_service = MQTTService()
