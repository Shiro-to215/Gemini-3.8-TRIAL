from backend.conversation import ConversationManager
from backend.memory import MemoryManager


def test_conversation_history_is_persistent(database):
    manager = ConversationManager(database)
    conversation = manager.create()
    manager.add_message(conversation["id"], "user", "こんにちは")
    manager.add_message(conversation["id"], "model", "こんにちは！", "gemini-test")
    loaded = manager.get(conversation["id"])
    assert [message["content"] for message in loaded["messages"]] == ["こんにちは", "こんにちは！"]
    assert manager.prompt_history(conversation["id"])[1]["role"] == "model"


def test_memory_crud(database):
    manager = MemoryManager(database)
    memory = manager.create("日本語で回答する")
    assert manager.list()[0]["content"] == "日本語で回答する"
    updated = manager.update(memory["id"], "簡潔な日本語で回答する")
    assert updated["content"].startswith("簡潔")
    assert manager.delete(memory["id"]) is True
    assert manager.list() == []