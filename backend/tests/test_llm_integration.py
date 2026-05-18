from src.calendar_module.calendar_service import CalendarService
from src.core.models import EmotionState, Intent
from src.nlp.input_normalizer import MalaysianInputNormalizer
from src.nlp.llm_client import LLMGenerationContext, MalaysianLlamaClient
from src.nlp.response_generator import ResponseGenerator


class DisabledLLM(MalaysianLlamaClient):
    def __init__(self):
        super().__init__(enabled=False)
        self.called = False

    def generate(self, context: LLMGenerationContext):
        self.called = True
        return None


class FakeNormalisingLLM(MalaysianLlamaClient):
    def __init__(self):
        super().__init__(enabled=True)

    def normalise_to_british_english(self, text: str):
        if "jadual" in text.lower():
            return "What is my schedule today?"
        return text


def test_unknown_intent_falls_back_when_llm_disabled(tmp_path):
    calendar = CalendarService(str(tmp_path / "juno_test.db"))
    llm = DisabledLLM()
    generator = ResponseGenerator(calendar, llm_client=llm)

    response = generator.generate(
        intent=Intent.UNKNOWN,
        emotion=EmotionState.NEUTRAL,
        user_text="Can you help me plan my study?",
    )

    assert llm.called
    assert "I am not sure how to help" in response


def test_deterministic_schedule_intent_does_not_call_llm(tmp_path):
    calendar = CalendarService(str(tmp_path / "juno_test.db"))
    llm = DisabledLLM()
    generator = ResponseGenerator(calendar, llm_client=llm)

    response = generator.generate(
        intent=Intent.CHECK_SCHEDULE,
        emotion=EmotionState.NEUTRAL,
        user_text="What do I have today?",
    )

    assert not llm.called
    assert "scheduled items" in response


def test_llm_status_exposes_lora_adapter_id():
    llm = MalaysianLlamaClient(enabled=False)
    status = llm.status()

    assert status["model_id"] == "mesolitica/Malaysian-Llama-3.2-3B-Instruct"
    assert status["adapter_id"] == "mackwongyy/malaysian-feedback-lora-5k-data"
    assert status["output_policy"] == "standard British English"


def test_input_normalizer_uses_llm_translation_when_available():
    normalizer = MalaysianInputNormalizer(FakeNormalisingLLM())

    assert normalizer.normalise("Apa jadual saya hari ini?") == "What is my schedule today?"
