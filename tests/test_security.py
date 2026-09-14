from pathlib import Path


def test_frontend_does_not_contain_api_key_or_direct_gemini_call():
    frontend_dir = Path(__file__).parents[1] / "frontend"
    frontend = "\n".join(path.read_text(encoding="utf-8") for path in frontend_dir.iterdir() if path.is_file())
    assert "GEMINI_API_KEY" not in frontend
    assert "generativelanguage.googleapis.com" not in frontend