from datetime import datetime, timedelta, timezone

from .config import settings
from .conversation import now_iso
from .database import Database


class NoAvailableModel(Exception):
    pass


class ModelManager:
    def __init__(self, database: Database, models: list[str] | None = None):
        self.database = database
        self.models = models or settings.models
        self._ensure_states()

    def _ensure_states(self) -> None:
        with self.database.connection() as connection:
            for model in self.models:
                connection.execute(
                    "INSERT OR IGNORE INTO model_states (model, status, updated_at) VALUES (?, 'available', ?)",
                    (model, now_iso()),
                )

    def _rows(self) -> list[dict]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM model_states").fetchall()
        return [dict(row) for row in rows]

    def statuses(self) -> list[dict]:
        current_time = datetime.now(timezone.utc)
        result = []
        with self.database.connection() as connection:
            for model in self.models:
                row = connection.execute("SELECT * FROM model_states WHERE model = ?", (model,)).fetchone()
                state = dict(row)
                if state["unavailable_until"] and datetime.fromisoformat(state["unavailable_until"]) <= current_time:
                    connection.execute(
                        "UPDATE model_states SET status = 'available', unavailable_until = NULL, updated_at = ? WHERE model = ?",
                        (now_iso(), model),
                    )
                    state.update(status="available", unavailable_until=None)
                result.append(state)
        return result

    def available_models(self) -> list[str]:
        return [state["model"] for state in self.statuses() if state["status"] == "available"]

    def current(self) -> str:
        available = self.available_models()
        if not available:
            raise NoAvailableModel()
        return available[0]

    def mark_available(self, model: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE model_states SET status = 'available', last_error = NULL, unavailable_until = NULL, updated_at = ? WHERE model = ?",
                (now_iso(), model),
            )

    def mark_unavailable(self, model: str, error: str, cooldown_seconds: int | None = None) -> None:
        seconds = cooldown_seconds if cooldown_seconds is not None else settings.model_cooldown_seconds
        until = datetime.now(timezone.utc) + timedelta(seconds=max(0, seconds))
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE model_states SET status = 'unavailable', last_error = ?, unavailable_until = ?, updated_at = ? WHERE model = ?",
                (error[:500], until.isoformat(), now_iso(), model),
            )

    def reset(self) -> None:
        with self.database.connection() as connection:
            connection.execute("UPDATE model_states SET status = 'available', last_error = NULL, unavailable_until = NULL, updated_at = ?", (now_iso(),))