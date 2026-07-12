from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    football_api_key: str = ""
    football_api_base_url: str = "https://api.football-data.org/v4"

    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 10080  # 7 days

    database_url: str = "sqlite+aiosqlite:///./football_watch.db"

    app_env: str = "development"
    cors_origins: str = "http://localhost:8081,http://localhost:19006,exp://localhost:8081"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()

# Supported leagues — code maps to football-data.org competition codes
LEAGUES = {
    "PL":  {"name": "Premier League",       "country": "England",  "emblem": ""},
    "CL":  {"name": "UEFA Champions League","country": "Europe",   "emblem": ""},
    "EL":  {"name": "UEFA Europa League",   "country": "Europe",   "emblem": ""},
    "ECL": {"name": "UEFA Conference League","country": "Europe",  "emblem": ""},
    "PD":  {"name": "La Liga",              "country": "Spain",    "emblem": ""},
    "BL1": {"name": "Bundesliga",           "country": "Germany",  "emblem": ""},
    "SA":  {"name": "Serie A",              "country": "Italy",    "emblem": ""},
    "FL1": {"name": "Ligue 1",              "country": "France",   "emblem": ""},
    "DED": {"name": "Eredivisie",           "country": "Netherlands","emblem": ""},
    "PPL": {"name": "Primeira Liga",        "country": "Portugal", "emblem": ""},
    "WC":  {"name": "FIFA World Cup",       "country": "World",    "emblem": ""},
}
