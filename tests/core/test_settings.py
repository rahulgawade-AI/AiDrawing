from townplanning.core.settings import (
    get_settings,
)


def test_settings():

    settings = get_settings()

    assert settings.APP_NAME

    assert settings.DATABASE_URL.startswith(
        "postgresql"
    )

    assert settings.OPENAI_MODEL

    assert settings.OLLAMA_MODEL