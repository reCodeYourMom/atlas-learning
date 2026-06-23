"""Client LLM injectable pour la génération d'items (T2.2).

Abstraction `LLMClient` → le pipeline ne dépend pas d'un fournisseur précis.
- `GroqClient` : implémentation réelle (Groq, OpenAI-compatible, mode JSON).
- `FakeLLMClient` : déterministe, pour les tests (aucun appel réseau).

Clé API lue dans l'environnement (GROQ_API_KEY) — jamais en dur.
"""
from __future__ import annotations

import os
from typing import List, Protocol


class LLMClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str, *, temperature: float = ...) -> str:
        """Retourne le contenu brut (chaîne JSON) d'une complétion en mode JSON."""
        ...


class GroqClient:
    """Implémentation réelle via Groq. Mode JSON strict (response_format json_object)."""

    def __init__(self, model: str = "llama-3.3-70b-versatile", api_key: str | None = None):
        import src.config  # noqa: F401  charge le .env (GROQ_API_KEY)
        from groq import Groq  # import paresseux : pas de dépendance pour les tests

        self.model = model
        self._client = Groq(api_key=api_key or os.environ["GROQ_API_KEY"])

    def complete_json(self, system: str, user: str, *, temperature: float = 0.7) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return resp.choices[0].message.content


class FakeLLMClient:
    """Renvoie des réponses pré-enregistrées dans l'ordre. Journalise les prompts.

    `calls` permet aux tests de vérifier le contenu exact des prompts (garde-fou PII).
    """

    model = "fake-model"

    def __init__(self, responses: List[str]):
        self._responses = list(responses)
        self.calls: List[dict] = []

    def complete_json(self, system: str, user: str, *, temperature: float = 0.0) -> str:
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        if not self._responses:
            raise AssertionError("FakeLLMClient : plus de réponses pré-enregistrées")
        return self._responses.pop(0)
