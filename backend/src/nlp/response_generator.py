from __future__ import annotations
from src.core.models import EmotionState, Intent
from src.calendar_module.calendar_service import CalendarService
from src.productivity.break_recommender import BreakRecommender
from src.nlp.llm_client import LLMGenerationContext, MalaysianLlamaClient


class ResponseGenerator:
    def __init__(
        self,
        calendar_service: CalendarService,
        llm_client: MalaysianLlamaClient | None = None,
    ) -> None:
        self.calendar_service = calendar_service
        self.break_recommender = BreakRecommender()
        self.llm_client = llm_client or MalaysianLlamaClient()

    def generate(self, intent: Intent, emotion: EmotionState, user_text: str = "") -> str:
        if intent == Intent.CHECK_SCHEDULE:
            items = self.calendar_service.get_today_schedule()
            if not items:
                return "You do not have any scheduled items in the current list."
            first_items = "; ".join(
                f"{item['title']} at {item['time']}" for item in items[:3]
            )
            return f"Here are your upcoming items: {first_items}."

        if intent == Intent.CHECK_DEADLINE:
            deadlines = self.calendar_service.get_upcoming_deadlines()
            if not deadlines:
                return "I could not find any upcoming deadlines."
            nearest = deadlines[0]
            return (
                f"Your nearest academic task is {nearest['title']} "
                f"on {nearest['date']} at {nearest['time']}."
            )

        if intent == Intent.SET_TIMER:
            return "Sure. I can start a study timer for you."

        if intent == Intent.ADD_REMINDER:
            return "I can add that as a reminder. For the prototype, please use the reminder form in the dashboard."

        if intent == Intent.PLAY_MUSIC:
            return "Playing calming study sounds for you."

        if intent == Intent.REQUEST_BREAK:
            return self.break_recommender.recommend(emotion)

        if intent == Intent.ASK_STATUS:
            suggestion = self.break_recommender.recommend(emotion)
            deadlines = self.calendar_service.get_upcoming_deadlines()
            if deadlines:
                nearest = deadlines[0]
                return (
                    f"{suggestion} Your nearest task is {nearest['title']} "
                    f"on {nearest['date']} at {nearest['time']}."
                )
            return suggestion

        if intent == Intent.SLEEP:
            return "JUNO is going back to sleep mode."

        llm_response = self._generate_llm_reply(intent, emotion, user_text)
        if llm_response:
            return llm_response

        return "Sorry, I can't help with that yet."

    def ai_status(self) -> dict:
        return self.llm_client.status()

    def _generate_llm_reply(
        self,
        intent: Intent,
        emotion: EmotionState,
        user_text: str,
    ) -> str | None:
        schedule_summary = self._schedule_summary()
        context = LLMGenerationContext(
            user_text=user_text,
            intent=intent,
            emotion=emotion,
            schedule_summary=schedule_summary,
        )
        return self.llm_client.generate(context)

    def _schedule_summary(self) -> str:
        items = self.calendar_service.get_today_schedule()[:3]
        deadlines = self.calendar_service.get_upcoming_deadlines()[:2]

        fragments: list[str] = []
        if items:
            fragments.append(
                "Today: "
                + "; ".join(f"{item['title']} at {item['time']}" for item in items)
            )
        if deadlines:
            fragments.append(
                "Upcoming deadlines: "
                + "; ".join(
                    f"{item['title']} on {item['date']} at {item['time']}"
                    for item in deadlines
                )
            )
        return " | ".join(fragments)
