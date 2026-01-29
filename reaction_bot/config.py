import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    chat_id: int
    topic_id: int                 # тема заданий
    welcome_topic_id: int         # тема приветствий
    db_path: str
    tz: str
    weekly_task_limit: int
    welcome_delete_after: int


def load_config() -> Config:
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        chat_id=int(os.environ["CHAT_ID"]),
        topic_id=int(os.environ["TOPIC_ID"]),
        welcome_topic_id=int(os.environ["WELCOME_TOPIC_ID"]),
        db_path=os.getenv("DB_PATH", "bot.db"),
        tz=os.getenv("TZ", "Europe/Moscow"),
        weekly_task_limit=int(os.getenv("WEEKLY_TASK_LIMIT", "10")),
        welcome_delete_after=int(os.getenv("WELCOME_DELETE_AFTER", "60")),
    )