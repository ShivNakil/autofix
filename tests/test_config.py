def test_imports():
    from app.config import settings

    assert settings.llm_provider
    assert settings.llm_model
