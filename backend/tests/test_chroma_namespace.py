from app.config import Settings


def test_chroma_path_namespaced_by_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    from app.config import get_settings

    get_settings.cache_clear()
    ollama_settings = get_settings()
    assert ollama_settings.chroma_path == tmp_path / "chroma" / "ollama"

    monkeypatch.setenv("AI_PROVIDER", "groq")
    get_settings.cache_clear()
    groq_settings = get_settings()
    assert groq_settings.chroma_path == tmp_path / "chroma" / "groq"
    assert ollama_settings.chroma_path != groq_settings.chroma_path
