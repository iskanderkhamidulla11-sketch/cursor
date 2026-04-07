import os


class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    webapp_url: str = os.getenv("WEBAPP_URL", "")
    api_base_url: str = os.getenv("API_BASE_URL", "")


settings = Settings()
