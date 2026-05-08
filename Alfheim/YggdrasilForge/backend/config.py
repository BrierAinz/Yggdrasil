"""YggdrasilForge configuration — Pydantic BaseSettings with env support."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8081
    DEBUG: bool = False

    # Blender MCP
    BLENDER_MCP_URL: str = "http://127.0.0.1:9897"

    # AI Services (via Blender MCP — no direct API keys needed)
    HUNYUAN3D_ENABLED: bool = True
    RODIN_ENABLED: bool = True
    POLYHAVEN_ENABLED: bool = True
    SKETCHFAB_ENABLED: bool = True

    # Generation polling
    POLL_INTERVAL_SECONDS: int = 5
    POLL_TIMEOUT_SECONDS: int = 600  # 10 min max wait

    # Database
    DATA_DIR: str = str(Path(__file__).parent.parent / "data")
    DB_PATH: str = ""  # defaults to DATA_DIR/forge.db
    OUTPUT_DIR: str = ""  # defaults to DATA_DIR/outputs

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ]

    # YggdrasilStudio bridge
    STUDIO_URL: str = "http://localhost:8080"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context) -> None:
        """Set derived defaults after initialization."""
        data = Path(self.DATA_DIR)
        if not self.DB_PATH:
            self.DB_PATH = str(data / "forge.db")
        if not self.OUTPUT_DIR:
            self.OUTPUT_DIR = str(data / "outputs")


settings = Settings()
