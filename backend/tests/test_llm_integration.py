from src.calendar_module.calendar_service import CalendarService
from src.core.models import EmotionState, Intent
from src.nlp.llm_client import LLMGenerationContext, MalaysianLlamaClient
from src.nlp.response_generator import ResponseGenerator


class DisabledLLM(MalaysianLlamaClient):
    def __init__(self):
        super().__init__(enabled=False)
        self.called = False

    def generate(self, context: LLMGenerationContext):
        self.called = True
        return None


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
