from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Grabber Robot Service"
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost/robot_db"
    
    # JWT Settings (must match auth service)
    SECRET_KEY: str = "CHANGE_THIS_SECRET_KEY_IN_ENV"
    ALGORITHM: str = "HS256"
    
    # MQTT Settings
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
