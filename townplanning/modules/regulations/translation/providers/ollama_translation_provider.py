import ollama

from .base import TranslationProvider


class OllamaTranslationProvider(TranslationProvider):

    def __init__(self):
        self.model = "gemma3:12b"

    def translate(self, text: str) -> str:

        prompt = f"""
Translate the following Marathi text into English.

Return ONLY the English translation.

Marathi:
{text}

English:
"""

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": 0,
            },
        )

        return response["message"]["content"].strip()