from backend.model_manager import ModelManager


def test_model_manager_uses_priority_and_persists_unavailability(database):
    manager = ModelManager(database, ["model-a", "model-b"])
    assert manager.current() == "model-a"
    manager.mark_unavailable("model-a", "quota", 3600)
    assert manager.current() == "model-b"
    restarted = ModelManager(database, ["model-a", "model-b"])
    assert restarted.current() == "model-b"