import time
from collections.abc import Callable

from .gemini_client import GeminiRequestError
from .model_manager import ModelManager, NoAvailableModel


class AllModelsUnavailable(Exception):
    pass


class FallbackManager:
    def __init__(self, model_manager: ModelManager, max_retries: int = 1, sleeper: Callable[[float], None] = time.sleep):
        self.model_manager = model_manager
        self.max_retries = max_retries
        self.sleeper = sleeper

    def generate(self, request: Callable[[str], str]) -> tuple[str, str, bool]:
        attempted = set()
        switched = False
        while True:
            try:
                model = self.model_manager.current()
            except NoAvailableModel as error:
                raise AllModelsUnavailable() from error
            if model in attempted:
                raise AllModelsUnavailable()
            attempted.add(model)
            for attempt in range(self.max_retries + 1):
                try:
                    response = request(model)
                    self.model_manager.mark_available(model)
                    return response, model, switched
                except GeminiRequestError as error:
                    if error.reason in {"authentication", "request", "configuration"}:
                        raise
                    if error.reason in {"quota", "server"} and attempt < self.max_retries:
                        delay = min(max(error.retry_after or 1, 0), 8)
                        if delay:
                            self.sleeper(delay)
                        continue
                    if error.reason == "unknown":
                        raise
                    self.model_manager.mark_unavailable(model, error.message)
                    switched = True
                    break