<<<<<<< HEAD
import os
from pathlib import Path


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_local_env()


class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    webapp_url: str = os.getenv("WEBAPP_URL", "")
    api_base_url: str = os.getenv("API_BASE_URL", "")
    stars_provider_token: str = os.getenv("STARS_PROVIDER_TOKEN", "")
    cryptobot_token: str = os.getenv("CRYPTOBOT_TOKEN", "")
    cryptobot_base_url: str = os.getenv(
        "CRYPTOBOT_BASE_URL",
        "https://pay.crypt.bot/api",
    )
    admin_ids: list[int] = [
        int(item.strip())
        for item in os.getenv("ADMIN_IDS", "").split(",")
        if item.strip().isdigit()
    ]


settings = Settings()
=======
import os


class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    webapp_url: str = os.getenv("WEBAPP_URL", "")
    api_base_url: str = os.getenv("API_BASE_URL", "")


settings = Settings()
>>>>>>> 812b10437b3ace4a467d917045a8e96128a6b6a4
