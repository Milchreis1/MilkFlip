import os
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    SCRAPE_INTERVAL_MINUTES: int = Field(default=10, env="SCRAPE_INTERVAL_MINUTES")
    MAX_BUDGET_EUR: float = Field(default=500.0, env="MAX_BUDGET_EUR")
    MIN_PROFIT_EUR: float = Field(default=20.0, env="MIN_PROFIT_EUR")
    PRICE_THRESHOLD_PERCENT: float = Field(default=35.0, env="PRICE_THRESHOLD_PERCENT")
    ROLLING_AVERAGE_DAYS: int = Field(default=30, env="ROLLING_AVERAGE_DAYS")
    MIN_LISTING_IMAGES: int = Field(default=1, env="MIN_LISTING_IMAGES")
    ALERT_COOLDOWN_HOURS: int = Field(default=24, env="ALERT_COOLDOWN_HOURS")
    MAX_SELLER_LISTINGS: int = Field(default=5, env="MAX_SELLER_LISTINGS")
    TELEGRAM_BOT_TOKEN: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(default="", env="TELEGRAM_CHAT_ID")
    DATABASE_URL: str = Field(default="postgresql://localhost/flipper", env="DATABASE_URL")
    API_PORT: int = Field(default=8000, env="API_PORT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    _scraper_paused: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def is_paused(self) -> bool:
        return self._scraper_paused

    def pause(self):
        object.__setattr__(self, "_scraper_paused", True)

    def resume(self):
        object.__setattr__(self, "_scraper_paused", False)

    def update_env_file(self, key: str, value: str):
        env_path = ".env"
        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)


settings = Settings()
