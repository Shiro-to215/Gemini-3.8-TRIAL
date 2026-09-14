from .conversation import now_iso
from .database import Database


class MemoryManager:
    def __init__(self, database: Database):
        self.database = database

    def list(self) -> list[dict]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def create(self, content: str) -> dict:
        content = content.strip()
        if not content:
            raise ValueError("Memory cannot be empty")
        timestamp = now_iso()
        with self.database.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO memories (content, created_at, updated_at) VALUES (?, ?, ?)",
                (content, timestamp, timestamp),
            )
            memory_id = cursor.lastrowid
        return self.get(memory_id)

    def get(self, memory_id: int) -> dict | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return dict(row) if row else None

    def update(self, memory_id: int, content: str) -> dict | None:
        content = content.strip()
        if not content:
            raise ValueError("Memory cannot be empty")
        with self.database.connection() as connection:
            connection.execute("UPDATE memories SET content = ?, updated_at = ? WHERE id = ?", (content, now_iso(), memory_id))
        return self.get(memory_id)

    def delete(self, memory_id: int) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0

    def prompt_context(self) -> str:
        memories = self.list()
        return "\n".join(f"- {memory['content']}" for memory in memories)