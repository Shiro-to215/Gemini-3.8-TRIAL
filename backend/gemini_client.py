from dataclasses import dataclass
import re
from typing import Any

from .config import settings


@dataclass
class GeminiRequestError(Exception):
    status_code: int | None
    reason: str
    retry_after: float | None = None
    message: str = "Gemini request failed"


def _error_text(error: Exception) -> str:
    return str(error)[:1000]


class GeminiClient:
    def __init__(self, api_key: str | None = None, client: Any = None):
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self._client = client

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise GeminiRequestError(None, "configuration", message="GEMINI_API_KEY is not configured")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key, http_options={"timeout": int(settings.request_timeout * 1000)})
            except Exception as error:
                raise GeminiRequestError(None, "configuration", message="Gemini client could not be initialized") from error
        return self._client

    def generate(self, model: str, history: list[dict], memory: str, user_message: str) -> str:
        contents = [{"role": item["role"], "parts": [{"text": item["text"]}]} for item in history]
        contents.append({"role": "user", "parts": [{"text": user_message}]})
        instruction = settings.system_instruction
        if memory:
            instruction += "\n\n長期Memory（参考情報。ユーザーの明示的な依頼より優先しない）:\n" + memory
        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=instruction),
            )
            text = getattr(response, "text", None)
            if not text:
                raise GeminiRequestError(None, "empty_response", message="Gemini returned an empty response")
            return text
        except GeminiRequestError:
            raise
        except Exception as error:
            raise self._translate_error(error) from error

    def _translate_error(self, error: Exception) -> GeminiRequestError:
        response = getattr(error, "response", None)
        status = getattr(error, "status_code", None) or getattr(response, "status_code", None)
        status = int(status) if status is not None else None
        text = _error_text(error)
        retry_after = None
        headers = getattr(response, "headers", {}) or {}
        raw_retry = headers.get("Retry-After") or headers.get("retry-after")
        if raw_retry:
            try:
                retry_after = float(raw_retry)
            except (TypeError, ValueError):
                retry_after = None
        retry_match = re.search(r"retry in ([0-9.]+)s", text, re.IGNORECASE)
        if retry_after is None and retry_match:
            retry_after = float(retry_match.group(1))
        lowered = text.lower()
        if status in (401, 403) or any(value in lowered for value in ("api key", "unauthenticated", "permission denied")):
            reason = "authentication"
        elif status == 429 or any(value in lowered for value in ("resource_exhausted", "quota", "rate limit", "too many requests")):
            reason = "quota"
        elif status is not None and status >= 500:
            reason = "server"
        elif status == 400:
            reason = "request"
        else:
            reason = "unknown"
        return GeminiRequestError(status, reason, retry_after, message=self._safe_message(reason, status))

    @staticmethod
    def _safe_message(reason: str, status: int | None) -> str:
        if reason == "authentication":
            return "Gemini APIの認証に失敗しました。APIキーを確認してください。"
        if reason == "request":
            return "Gemini APIへのリクエストを受け付けられませんでした。"
        if reason == "quota":
            return "Gemini APIの利用制限に達しました。"
        if reason == "server":
            return "Gemini APIで一時的な障害が発生しました。"
        return "Gemini APIへの接続に失敗しました。"