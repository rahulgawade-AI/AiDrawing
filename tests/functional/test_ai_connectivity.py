from townplanning.ai import AIRequest
from townplanning.ai import OllamaClient


def test_ai_connectivity():

    client = OllamaClient()

    response = client.generate(
        AIRequest(
            system_prompt="Reply only with valid JSON.",
            user_prompt='Return {"status":"ok"}',
        )
    )

    assert response.success