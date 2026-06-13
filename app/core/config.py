from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Grabber Robot Service"
    DATABASE_URL: str = "mysql+aiomysql://thathsara:BandaPutha@db/grabber_robot"
    PORT: int = 8002
    
    # JWT Settings (must match auth service)
    SECRET_KEY: str = "CHANGE_THIS_SECRET_KEY_IN_ENV"
    ALGORITHM: str = "HS256"
    
    # MQTT Settings
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
