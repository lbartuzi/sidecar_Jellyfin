# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings
from pydantic import Field
import json

class Settings(BaseSettings):
    jellyfin_url: str = Field(alias="JELLYFIN_URL")
    jellyfin_api_key: str = Field(alias="JELLYFIN_API_KEY")
    jellyfin_user_id: str = Field(default="", alias="JELLYFIN_USER_ID")

    dry_run: bool = Field(default=True, alias="DRY_RUN")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8088, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    min_group_size: int = Field(default=2, alias="MIN_GROUP_SIZE")

    enable_franchise: bool = Field(default=True, alias="ENABLE_FRANCHISE")
    enable_studio: bool = Field(default=True, alias="ENABLE_STUDIO")
    enable_format: bool = Field(default=True, alias="ENABLE_FORMAT")
    enable_length: bool = Field(default=True, alias="ENABLE_LENGTH")
    enable_audience: bool = Field(default=True, alias="ENABLE_AUDIENCE")
    enable_mood: bool = Field(default=True, alias="ENABLE_MOOD")

    franchise_rules_json: str = Field(default="{}", alias="FRANCHISE_RULES_JSON")

    studio_allowlist_json: str = Field(default="[]", alias="STUDIO_ALLOWLIST_JSON")
    top_studios: int = Field(default=20, alias="TOP_STUDIOS")

    data_dir: str = "/data"

    def franchise_rules(self):
        try:
            obj = json.loads(self.franchise_rules_json or "{}")
            return {k: [kw.lower() for kw in v] for k, v in obj.items()}
        except Exception:
            return {}

    def studio_allowlist(self):
        try:
            arr = json.loads(self.studio_allowlist_json or "[]")
            return [str(x).lower().strip() for x in arr if str(x).strip()]
        except Exception:
            return []

settings = Settings()
