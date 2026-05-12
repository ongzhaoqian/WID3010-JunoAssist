from src.core.config import settings


class ConfirmationHandler:
    def __init__(self, confirmation_phrase: str = settings.confirmation_phrase) -> None:
        self.confirmation_phrase = confirmation_phrase.lower().strip()

    def is_confirmed(self, text: str) -> bool:
        normalised = text.lower().strip()
        return normalised in {"yes", "yeah", "yep", "confirm", self.confirmation_phrase}
