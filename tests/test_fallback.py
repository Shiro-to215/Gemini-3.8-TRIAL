import pytest

from backend.fallback import AllModelsUnavailable, FallbackManager
from backend.gemini_client import GeminiRequestError
from backend.model_manager import ModelManager


def test_quota_falls_back_without_losing_model_order(database):
    manager = ModelManager(database, ["model-a", "model-b"])
    calls = []

    def request(model):
        calls.append(model)
        if model == "model-a":
            raise GeminiRequestError(429, "quota", retry_after=0, message="limited")
        return "answer"

    answer, model, switched = FallbackManager(manager, sleeper=lambda _: None).generate(request)
    assert (answer, model, switched) == ("answer", "model-b", True)
    assert calls == ["model-a", "model-a", "model-b"]


def test_all_models_unavailable_returns_controlled_error(database):
    manager = ModelManager(database, ["model-a"])
    manager.mark_unavailable("model-a", "quota", 3600)
    with pytest.raises(AllModelsUnavailable):
        FallbackManager(manager).generate(lambda _: "never")