from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_SYSTEM_INSTRUCTION = """あなたは長期的な会話を行うアシスタントです。
- ユーザーの質問に直接答えてください。
- 必要に応じて過去の会話を参照してください。
- 自然な日本語を使用してください。
- ユーザーの発言を踏まえて回答してください。
- 分からないことは分からないと明示し、不確かな情報を断定しないでください。"""


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    database_path: str = os.getenv("DATABASE_PATH", str(ROOT_DIR / "data" / "chat.db"))
    system_instruction: str = os.getenv("SYSTEM_INSTRUCTION", DEFAULT_SYSTEM_INSTRUCTION)
    request_timeout: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
    model_cooldown_seconds: int = int(os.getenv("MODEL_COOLDOWN_SECONDS", "3600"))

    @property
    def models(self) -> list[str]:
        configured = os.getenv("GEMINI_MODELS", "")
        if configured.strip():
            return [model.strip() for model in configured.split(",") if model.strip()]
        # 現行の Gemini API で利用される安定版を優先順にまとめる。
        return ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]


settings = Settings()