import aiosqlite
from typing import Optional

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    post_url TEXT NOT NULL,
    post_key TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    card_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS completions (
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    completed_at INTEGER NOT NULL,
    UNIQUE(task_id, user_id)
);

CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER PRIMARY KEY,
    banned_until INTEGER
);

-- Храним последние "служебные" сообщения бота (топы/правила/мой прогресс), чтобы удалять старые
CREATE TABLE IF NOT EXISTS bot_messages (
    chat_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    kind TEXT NOT NULL,             -- rules/me/top/month_top
    message_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(chat_id, topic_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_completions_completed_at ON completions(completed_at);
"""

class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def is_banned(self, user_id: int, now_ts: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT banned_until FROM bans WHERE user_id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            await cur.close()

            if not row:
                return False
            banned_until = row[0]
            if banned_until is None:
                return True
            return now_ts < banned_until

    async def count_user_tasks_in_range(self, user_id: int, start_ts: int, end_ts: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT COUNT(*) FROM tasks
                WHERE created_by = ? AND created_at BETWEEN ? AND ?
                """,
                (user_id, start_ts, end_ts),
            )
            row = await cur.fetchone()
            await cur.close()
            return int(row[0])

    async def get_task_by_post_key(self, post_key: str) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, chat_id, topic_id, created_by, post_url, post_key, created_at, active, card_message_id
                FROM tasks
                WHERE post_key = ?
                """,
                (post_key,),
            )
            row = await cur.fetchone()
            await cur.close()

            if not row:
                return None
            return {
                "id": row[0],
                "chat_id": row[1],
                "topic_id": row[2],
                "created_by": row[3],
                "post_url": row[4],
                "post_key": row[5],
                "created_at": row[6],
                "active": bool(row[7]),
                "card_message_id": row[8],
            }

    async def create_task(
        self,
        chat_id: int,
        topic_id: int,
        created_by: int,
        post_url: str,
        post_key: str,
        created_at: int,
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                INSERT INTO tasks(chat_id, topic_id, created_by, post_url, post_key, created_at, active)
                VALUES(?, ?, ?, ?, ?, ?, 1)
                """,
                (chat_id, topic_id, created_by, post_url, post_key, created_at),
            )
            await db.commit()
            return int(cur.lastrowid)

    async def set_task_card_message_id(self, task_id: int, card_message_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE tasks SET card_message_id = ? WHERE id = ?",
                (card_message_id, task_id),
            )
            await db.commit()

    async def get_task(self, task_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, chat_id, topic_id, created_by, post_url, post_key, created_at, active, card_message_id
                FROM tasks WHERE id = ?
                """,
                (task_id,),
            )
            row = await cur.fetchone()
            await cur.close()

            if not row:
                return None
            return {
                "id": row[0],
                "chat_id": row[1],
                "topic_id": row[2],
                "created_by": row[3],
                "post_url": row[4],
                "post_key": row[5],
                "created_at": row[6],
                "active": bool(row[7]),
                "card_message_id": row[8],
            }

    async def count_completions(self, task_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM completions WHERE task_id = ?",
                (task_id,),
            )
            row = await cur.fetchone()
            await cur.close()
            return int(row[0])

    async def add_completion(self, task_id: int, user_id: int, ts: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    "INSERT INTO completions(task_id, user_id, completed_at) VALUES(?, ?, ?)",
                    (task_id, user_id, ts),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_completion(self, task_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "DELETE FROM completions WHERE task_id = ? AND user_id = ?",
                (task_id, user_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def count_user_completions_in_range(self, user_id: int, start_ts: int, end_ts: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT COUNT(*) FROM completions
                WHERE user_id = ? AND completed_at BETWEEN ? AND ?
                """,
                (user_id, start_ts, end_ts),
            )
            row = await cur.fetchone()
            await cur.close()
            return int(row[0])

    async def top_completions_in_range(self, start_ts: int, end_ts: int, limit: int = 20):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT user_id, COUNT(*) as c
                FROM completions
                WHERE completed_at BETWEEN ? AND ?
                GROUP BY user_id
                ORDER BY c DESC
                LIMIT ?
                """,
                (start_ts, end_ts, limit),
            )
            rows = await cur.fetchall()
            await cur.close()
            return [(int(r[0]), int(r[1])) for r in rows]

    # ====== bot_messages (для чистки старых "топов/правил/стат") ======

    async def get_last_bot_message_id(self, chat_id: int, topic_id: int, kind: str) -> Optional[int]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT message_id FROM bot_messages
                WHERE chat_id = ? AND topic_id = ? AND kind = ?
                """,
                (chat_id, topic_id, kind),
            )
            row = await cur.fetchone()
            await cur.close()
            return int(row[0]) if row else None

    async def set_last_bot_message_id(self, chat_id: int, topic_id: int, kind: str, message_id: int, created_at: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO bot_messages(chat_id, topic_id, kind, message_id, created_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, topic_id, kind)
                DO UPDATE SET message_id=excluded.message_id, created_at=excluded.created_at
                """,
                (chat_id, topic_id, kind, message_id, created_at),
            )
            await db.commit()