from pathlib import Path
from typing import Any, Union

from vision.ollama_wrapper import OllamaGenerateResult


class FakeOllamaWrapper:

    def __init__(self):

        self.responses = {}
        self.embeddings = {}

    def add_response(
        self,
        prompt: str,
        response: str
    ) -> None:

        self.responses[prompt] = response

    def add_embedding(
        self,
        text: str,
        embedding: list[float]
    ) -> None:

        self.embeddings[text] = embedding

    def generate_with_image(
        self,
        *,
        model: str,
        prompt: str,
        image: str | Path | bytes,
        image_mime_hint=None,
        system=None,
        options=None,
    ) -> OllamaGenerateResult:

        return OllamaGenerateResult(
            response=self.responses.get(
                prompt,
                "Réponse fake par défaut"
            )
        )

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        system=None,
        options=None,
    ) -> OllamaGenerateResult:

        return OllamaGenerateResult(
            response=self.responses.get(
                prompt,
                "Réponse fake par défaut"
            )
        )

    def embed(
        self,
        *,
        model: str,
        text: str,
    ) -> list[float]:
        
        result = self.embeddings.get(text, [])
        # Si le résultat est une exception, la lever
        if isinstance(result, Exception):
            raise result
        return result