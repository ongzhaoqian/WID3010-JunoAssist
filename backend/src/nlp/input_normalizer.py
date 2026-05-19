from __future__ import annotations

from src.nlp.llm_client import MalaysianLlamaClient


class MalaysianInputNormalizer:
    """Normalises Malaysian-context utterances before intent classification.

    The class deliberately falls back to the original text when the optional
    text LLM is disabled/unavailable. In the current robot-friendly setup,
    multilingual speech is handled earlier by Whisper Tiny ASR and the backend
    keeps deterministic intent handling for reliability.
    """

    def __init__(self, llm_client: MalaysianLlamaClient) -> None:
        self.llm_client = llm_client

    def normalise(self, text: str) -> str:
        raw = " ".join(text.strip().split())
        if not raw:
            return ""
        normalised = self.llm_client.normalise_to_british_english(raw)
        return normalised or raw
