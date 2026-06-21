from __future__ import annotations
from src.core.models import EmotionState, Intent
from src.calendar_module.calendar_service import CalendarService
from src.productivity.break_recommender import BreakRecommender
from src.nlp.llm_client import LLMGenerationContext, MalaysianLlamaClient
from src.nlp.phrase_bank import PhraseBank


class ResponseGenerator:
    def __init__(
        self,
        calendar_service: CalendarService,
        llm_client: MalaysianLlamaClient | None = None,
        phrase_bank: PhraseBank | None = None,
    ) -> None:
        self.calendar_service = calendar_service
        self.break_recommender = BreakRecommender()
        self.llm_client = llm_client or MalaysianLlamaClient()
        self.phrases = phrase_bank or PhraseBank()

    def generate(self, intent: Intent, emotion: EmotionState, user_text: str = "") -> str:
        if intent == Intent.CHECK_SCHEDULE:
            items = self.calendar_service.get_today_schedule(include_completed=False)
            if not items:
                return self.phrases.say("schedule_empty")
            first_items = "; ".join(self._describe_schedule_item(item) for item in items)
            return self.phrases.say("schedule_summary", items=first_items)

        if intent == Intent.CHECK_DEADLINE:
            deadlines = self.calendar_service.get_upcoming_deadlines()
            if not deadlines:
                return self.phrases.say("deadline_empty")
            nearest = deadlines[0]
            return self.phrases.say(
                "deadline_nearest",
                title=nearest["title"],
                date=nearest.get("formatted_date") or nearest.get("date") or "not specified",
                time=nearest.get("time") or "not specified",
            )

        if intent == Intent.CHECK_REMINDERS:
            reminders = self.calendar_service.list_reminders(include_completed=False)
            if not reminders:
                return self.phrases.say("reminder_empty")
            first_items = "; ".join(self._describe_reminder_item(item) for item in reminders)
            return self.phrases.say("reminder_summary", items=first_items)

        if intent == Intent.SET_TIMER:
            return self.phrases.say("timer_ask")

        if intent == Intent.ADD_REMINDER:
            return self.phrases.say("reminder_missing")

        if intent == Intent.PLAY_MUSIC:
            return self.phrases.say("music_requested")

        if intent == Intent.REQUEST_BREAK:
            return self.break_recommender.recommend(emotion)

        if intent == Intent.ASK_STATUS:
            suggestion = self.break_recommender.recommend(emotion)
            deadlines = self.calendar_service.get_upcoming_deadlines()
            reminders = self.calendar_service.list_reminders(include_completed=False)
            fragments = [self.phrases.say("status_prefix", suggestion=suggestion)]
            if deadlines:
                nearest = deadlines[0]
                fragments.append(
                    f"Your nearest task is {nearest['title']} on "
                    f"{nearest.get('formatted_date') or nearest.get('date') or 'not specified'} "
                    f"at {nearest.get('time') or 'not specified'}."
                )
            if reminders:
                nearest_reminder = reminders[0]
                fragments.append(
                    f"Your nearest reminder is {nearest_reminder['title']} on "
                    f"{nearest_reminder.get('formatted_date') or nearest_reminder.get('date') or 'not specified'} "
                    f"at {nearest_reminder.get('time') or 'not specified'}."
                )
            return " ".join(fragments)

        if intent == Intent.SLEEP:
            return self.phrases.say("sleep")

        llm_response = self._generate_llm_reply(intent, emotion, user_text)
        if llm_response:
            return llm_response

        return self.phrases.say("fallback")

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
        items = self.calendar_service.get_today_schedule(include_completed=False)[:3]
        deadlines = self.calendar_service.get_upcoming_deadlines()[:2]
        reminders = self.calendar_service.list_reminders(include_completed=False)[:3]

        fragments: list[str] = []
        if items:
            fragments.append("Schedule: " + "; ".join(self._describe_schedule_item(item) for item in items))
        if deadlines:
            fragments.append(
                "Upcoming deadlines: "
                + "; ".join(self._describe_schedule_item(item) for item in deadlines)
            )
        if reminders:
            fragments.append(
                "Reminders: "
                + "; ".join(self._describe_reminder_item(item) for item in reminders)
            )
        return " | ".join(fragments)

    @staticmethod
    def _describe_schedule_item(item: dict) -> str:
        date = item.get("formatted_date") or item.get("date") or "no date"
        time = item.get("time") or "no time"
        item_type = item.get("type") or "schedule"
        priority = item.get("priority") or "medium"
        return f"{item['title']} ({item_type}, {priority} priority) on {date} at {time}"

    @staticmethod
    def _describe_reminder_item(item: dict) -> str:
        date = item.get("formatted_date") or item.get("date") or "no date"
        time = item.get("time") or "no time"
        item_type = item.get("type") or "reminder"
        priority = item.get("priority") or "medium"
        return f"{item['title']} ({item_type}, {priority} priority) on {date} at {time}"
