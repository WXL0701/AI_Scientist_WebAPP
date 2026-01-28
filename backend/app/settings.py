from __future__ import annotations

from dataclasses import dataclass
import os


def get_default_ai_scientist_root() -> str:
    # Default for local development
    default_path = "/home/guv/AI_Scientist"
    
    # Check if we are likely in the Docker container where prompts are copied to /app/prompts
    if not os.path.exists(default_path) and os.path.exists("/app/prompts"):
        return "/app"
        
    return default_path


@dataclass(frozen=True)
class Settings:
    data_dir: str = os.getenv("WEBAPP_DATA_DIR", "/data/app/webapp")
    runs_root: str = os.getenv("WEBAPP_RUNS_ROOT", "/data/app/runs")
    ai_scientist_root: str = os.getenv("AI_SCIENTIST_ROOT", get_default_ai_scientist_root())
    runner_image: str = os.getenv("RUNNER_IMAGE", "ai_scientist_runner:local")
    jwt_secret: str = os.getenv("WEBAPP_JWT_SECRET", "change-me")
    jwt_issuer: str = os.getenv("WEBAPP_JWT_ISSUER", "ai-scientist-webapp")
    jwt_exp_seconds: int = int(os.getenv("WEBAPP_JWT_EXP_SECONDS", "604800"))


settings = Settings()
