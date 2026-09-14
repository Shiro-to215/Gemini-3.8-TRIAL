from types import SimpleNamespace

from backend.gemini_client import GeminiClient


class FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text="テスト回答")


def test_gemini_client_sends_history_and_current_message():
    models = FakeModels()
    client = GeminiClient(api_key="server-only-key", client=SimpleNamespace(models=models))
    result = client.generate("model-a", [{"role": "user", "text": "前の質問"}], "- 日本語", "現在の質問")
    assert result == "テスト回答"
    assert models.calls[0]["model"] == "model-a"
    assert models.calls[0]["contents"][-1]["parts"][0]["text"] == "現在の質問"
    assert "server-only-key" not in repr(models.calls[0])