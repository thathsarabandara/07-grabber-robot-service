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
        topic = f"robots/{robot_id}/commands/{command_type}"
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
