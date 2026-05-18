from __future__ import annotations

from src.nlp.llm_client import MalaysianLlamaClient


class MalaysianInputNormalizer:
    """Normalises Malaysian-context utterances before intent classification.

    The class deliberately falls back to the original text if the Hugging Face
    model or LoRA adapter is disabled/unavailable. This keeps the robot demo
    reliable while enabling multilingual/dialect handling on capable hardware.
    """

    def __init__(self, llm_client: MalaysianLlamaClient) -> None:
        self.llm_client = llm_client

    def normalise(self, text: str) -> str:
        raw = " ".join(text.strip().split())
        if not raw:
            return ""
        normalised = self.llm_client.normalise_to_british_english(raw)
        return normalised or raw
