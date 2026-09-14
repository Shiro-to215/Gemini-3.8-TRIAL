from datetime import datetime, timezone
import uuid

from .database import Database


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationManager:
    def __init__(self, database: Database):
        self.database = database

    def create(self, title: str = "新しい会話") -> dict:
        conversation_id = str(uuid.uuid4())
        timestamp = now_iso()
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conversation_id, title[:120], timestamp, timestamp),
            )
        return self.get(conversation_id)

    def get(self, conversation_id: str) -> dict | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            if not row:
                return None
            messages = connection.execute(
                "SELECT id, role, content, model, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            ).fetchall()
        result = dict(row)
        result["messages"] = [dict(message) for message in messages]
        return result

    def list(self) -> list[dict]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def add_message(self, conversation_id: str, role: str, content: str, model: str | None = None) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO messages (conversation_id, role, content, model, created_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, role, content, model, now_iso()),
            )
            connection.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now_iso(), conversation_id))

    def rename_from_first_message(self, conversation_id: str, content: str) -> None:
        title = " ".join(content.split())[:50] or "新しい会話"
        with self.database.connection() as connection:
            connection.execute("UPDATE conversations SET title = ? WHERE id = ? AND title = '新しい会話'", (title, conversation_id))

    def delete(self, conversation_id: str) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cursor.rowcount > 0

    def prompt_history(self, conversation_id: str) -> list[dict]:
        conversation = self.get(conversation_id)
        if not conversation:
            raise KeyError(conversation_id)
        return [{"role": message["role"], "text": message["content"]} for message in conversation["messages"]]