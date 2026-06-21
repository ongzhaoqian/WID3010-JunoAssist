from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta


@dataclass
class PhraseBank:
    """Centralised response phrase bank for JUNO.

    The backend keeps the robot's phrasing here instead of scattering fixed
    sentences across every intent handler. Templates remain deterministic enough
    for testing, while still allowing lightweight natural variation at runtime.
    """

    seed: int | None = None
    templates: dict[str, list[str]] = field(default_factory=lambda: {
        "wake_confirmation": [
            "I heard the wake command. Would you like me to power JUNO on? Please answer yes to continue.",
            "JUNO is ready to wake. Should I power on now? Please say yes if you would like me to continue.",
            "Wake command received. Would you like me to come online? Say yes to confirm.",
        ],
        "idle_sleep": [
            "JUNO is sleeping for now. Say Hey, John when you would like me to wake up.",
            "I am currently in sleep mode. Wake me by saying Hey, John.",
            "JUNO is standing by. Say Hey, John to wake me up.",
        ],
        "confirmation_cancelled": [
            "No problem. I will return to idle mode.",
            "Understood. JUNO will stay in sleep mode.",
            "Confirmation cancelled. I will remain idle.",
        ],
        "online": [
            "JUNO Assist is now online. Opening your dashboard.",
            "I am online now. Your dashboard is opening.",
            "JUNO is ready. I am bringing up your dashboard.",
        ],
        "prompt_help": [
            "What can I help you with?",
            "How can I support you now?",
            "What would you like to do next?",
        ],
        "sleep": [
            "JUNO is going back to sleep mode.",
            "All right, I will return to sleep mode.",
            "Okay, JUNO is powering down into sleep mode.",
        ],
        "not_ready": [
            "JUNO is not ready yet.",
            "I am not fully ready yet. Please try again shortly.",
        ],
        "timer_ask": [
            "How long do you want to have the study timer for? Answer in minutes and seconds.",
            "Sure. How long should the study timer be? Please answer in minutes and seconds.",
            "I can start that. How many minutes and seconds would you like for the study timer?",
        ],
        "timer_ask_minutes": [
            "How many minutes for the timer?",
            "Sure. How many minutes would you like?",
            "I can set that. How many minutes?",
        ],
        "timer_ask_seconds": [
            "Got it, {minutes} minutes. How many extra seconds? Say zero if none.",
            "Okay, {minutes} minutes. Any extra seconds to add? Say zero to skip.",
        ],
        "timer_paused": [
            "Timer paused. Say resume to continue, or delete to cancel it.",
            "I have paused the timer. Say resume to keep going, or delete to remove it.",
        ],
        "timer_resumed": [
            "Timer resumed. Keep going!",
            "Done. The timer is running again.",
        ],
        "timer_deleted": [
            "Timer deleted. I have reset everything.",
            "Done. The timer has been removed.",
        ],
        "timer_not_running": [
            "There is no active timer running at the moment.",
            "I do not have a timer running right now.",
        ],
        "timer_already_paused": [
            "The timer is already paused. Say resume to continue or delete to remove it.",
        ],
        "timer_unclear_minutes": [
            "Sorry, I did not catch the number of minutes. Please say a number, for example: twenty five, or say cancel.",
            "I could not understand the minutes. Please say a number like ten or thirty, or say cancel.",
        ],
        "timer_unclear_seconds": [
            "I did not catch the seconds. Please say a number like zero, ten, or thirty, or say cancel.",
            "Sorry, I could not understand the seconds. Say zero if you do not want extra seconds, or say cancel.",
        ],
        "timer_started": [
            "Study timer started for {duration}.",
            "Done. I have started a study timer for {duration}.",
            "Your study session is ready. The timer is set for {duration}.",
        ],
        "timer_finished": [
            "Time is up. Your {label} has finished.",
            "Ding. Your {label} is complete.",
            "Your focus timer has reached zero. Time for a short reset.",
        ],
        "timer_unclear": [
            "I could not understand the duration clearly. Please answer with a time such as 25 minutes, 1 minute 30 seconds, half an hour, or say cancel to exit timer setup.",
            "I did not catch the timer duration. You can say 20 minutes, 90 seconds, 2:30, one hour, or say cancel if you do not want to set it now.",
        ],
        "timer_cancelled": [
            "No problem. I will cancel the timer setup for now.",
            "Understood. I will leave the study timer unset for now.",
            "All right, I have exited timer setup.",
        ],
        "timer_cancelled_after_unclear": [
            "I still could not identify a duration, so I will cancel the timer setup for now. You can ask me to start a study timer again whenever you are ready.",
            "I did not receive a clear duration, so I will exit timer setup for now.",
        ],
        "schedule_empty": [
            "You do not have any scheduled items in the current list.",
            "There are no scheduled items in the current list yet.",
        ],
        "schedule_summary": [
            "Here are your upcoming scheduled items: {items}.",
            "Your current scheduled items are: {items}.",
        ],
        "schedule_added": [
            "Added {purpose} to your schedule for {when}, with {priority} priority.",
            "Done. I have scheduled {purpose} for {when}. Priority is {priority}.",
            "I have added {purpose} to the dashboard schedule: {when}, {priority} priority.",
        ],
        "schedule_missing": [
            "I can add that to your schedule, but I need the purpose first. For example, say: add schedule date 2026-05-20 time 15:30 purpose revision priority high.",
            "I could not identify the schedule purpose. Please include the date, time, purpose, and priority.",
        ],
        "deadline_empty": [
            "I could not find any upcoming deadlines.",
            "There are no upcoming deadlines in the current list.",
        ],
        "deadline_nearest": [
            "Your nearest academic task is {title}, due {when}.",
            "The closest task I found is {title}, scheduled for {when}.",
        ],
        "reminder_empty": [
            "You do not have any active reminders in the current list.",
            "There are no active reminders in the dashboard list yet.",
        ],
        "reminder_summary": [
            "Here are your current reminders: {items}.",
            "Your active reminders are: {items}.",
        ],
        "reminder_missing": [
            "I can add a reminder, but I need the reminder title first. For example, say: remind me to submit the report date 2026-05-20 time 15:30 priority high.",
            "I could not identify the reminder details clearly. Please include the title, date, time, type, and priority where possible.",
        ],
        "music_requested": [
            "Which mood would you like? I can play Focus, Calm, Happy, Gentle, or Cool Down.",
            "Sure. Tell me what mood you want — Focus, Calm, Happy, Gentle, or Cool Down.",
        ],
        "stress_acknowledgment": [
            "You seem stressed.",
        ],
        "break_offer_ask": [
            "Do you want a break?",
        ],
        "break_offer_declined": [
            "No problem. Let me know if you change your mind.",
        ],
        "break_offer_declined_resume_study": [
            "No problem. Resuming your study timer.",
        ],
        "break_offer_unclear": [
            "Sorry, I did not catch that. Do you want a break?",
        ],
        "game_or_music_offer": [
            "Would you like to play a game, or play music?",
            "Do you want to play a game, or would you rather play music?",
        ],
        "game_or_music_unclear": [
            "Sorry, I did not catch that. Would you like to play a game, or play music?",
        ],
        "stop_acknowledged": [
            "Stopped.",
            "Speech and music stopped.",
            "Okay, I have stopped speaking and stopped the music.",
        ],
        "status_prefix": [
            "Here is what I suggest: {suggestion}",
            "Based on the current state, {suggestion}",
        ],
        "fallback": [
            "I am not sure how to help with that yet. Could you try phrasing it as a schedule, timer, music, reminder, or break request?",
            "I am not sure how to help with that yet, but I can handle schedules, timers, music, reminders, and breaks.",
        ],
        "direct_sleep": [
            "JUNO is now in sleep mode.",
            "JUNO has returned to sleep mode.",
        ],
        "reminder_added": [
            "Reminder added: {title}, {when}, with {priority} priority.",
            "Done. I have added the reminder: {title}. That's {when}, priority {priority}.",
            "I have added {title} to your reminders for {when}.",
        ],
        "reminder_removed": [
            "Reminder removed.",
            "Done. I have removed that reminder.",
        ],
        "break_ask_after_study": [
            "Your study timer is up. Would you like to take a short break?",
        ],
        "break_ask_after_stress": [
            "You have been stressed for a while. Would you like to take a short break?",
        ],
        "break_confirmed": [
            "Sounds good. Starting a 5-minute break timer now.",
        ],
        "break_declined_after_study": [
            "Understood. Let me know when you're ready for your next session.",
        ],
        "break_declined_after_stress": [
            "Understood, continuing your study timer.",
        ],
        "break_resumed_study": [
            "Break's over. Resuming your study timer.",
        ],
        "break_confirmation_unclear": [
            "Sorry, I did not catch that. Would you like a short break? Please say yes or no.",
        ],
        "schedule_reminder_30": [
            "Upcoming: {title} in {remaining_label}.",
            "Heads up, {title} starts in {remaining_label}.",
        ],
        "schedule_reminder_due": [
            "{title} starts now.",
            "It is time for {title}.",
        ],
        "schedule_reminder_overdue": [
            "{title} is overdue by {overdue_label}.",
            "Heads up, {title} is now overdue by {overdue_label}.",
        ],
        "schedule_upcoming_multiple": [
            "Schedules: {titles} start in {remaining_label}.",
        ],
        "schedule_due_now_single": [
            "Schedule: {title} starts now.",
        ],
        "schedule_due_now_multiple": [
            "Schedules: {titles} start now.",
        ],
        "reminder_due_now_single": [
            "Reminder: {title} due now.",
        ],
        "reminder_due_now_multiple": [
            "Reminders: {titles} due now.",
        ],
        "schedule_marked_complete": [
            "Marked {title} as complete.",
            "Done. {title} is now marked complete.",
        ],
        "schedule_marked_incomplete": [
            "Marked {title} as not complete.",
            "Got it. {title} is back on your list.",
        ],
        "reminder_updated": [
            "Reminder updated: {title} is now set for {when}, with {priority} priority.",
            "Done. I have updated the reminder: {title}. That's {when} now, priority {priority}.",
            "I have changed {title} to {when}, {priority} priority.",
        ],
        "reminder_alert_30": [
            "Reminder: {title} is in {remaining_label}.",
            "Don't forget — {title} is coming up in {remaining_label}.",
        ],
        "reminder_upcoming_multiple": [
            "Reminders: {titles} are in {remaining_label}.",
        ],
        "reminder_alert_due": [
            "Reminder: {title} is due now.",
            "{title} is due now.",
        ],
        "reminder_alert_overdue": [
            "Reminder: {title} is overdue by {overdue_label}.",
            "{title} is overdue by {overdue_label}.",
        ],
        "reminder_marked_complete": [
            "Marked {title} as complete.",
            "Done. {title} is now marked complete.",
        ],
        "reminder_marked_incomplete": [
            "Marked {title} as not complete.",
            "Got it. {title} is back on your list.",
        ],
    })

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    @staticmethod
    def _humanize_when(date_str: str | None, time_str: str | None) -> str:
        """Convert a date/time pair into natural speech phrasing.

        Examples: "today at 5:38 PM", "tomorrow at 9:00 AM", "in about 3 hours",
        "next Monday at 9:00 AM", "a week from now at 2:00 PM",
        "two weeks from now at 2:00 PM", "on June 25 at 2:00 PM".
        """
        if not date_str or not time_str:
            return "not specified"
        try:
            due_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return f"{date_str} at {time_str}"

        now = datetime.now()
        delta_minutes = (due_at - now).total_seconds() / 60
        time_label = due_at.strftime("%-I:%M %p")

        same_day = due_at.date() == now.date()
        is_tomorrow = due_at.date() == (now + timedelta(days=1)).date()
        days_ahead = (due_at.date() - now.date()).days

        if same_day and 0 <= delta_minutes < 60:
            minutes = round(delta_minutes)
            return "in about a minute" if minutes <= 1 else f"in about {minutes} minutes"
        if same_day and 60 <= delta_minutes < 6 * 60:
            hours = round(delta_minutes / 60)
            return "in about an hour" if hours <= 1 else f"in about {hours} hours"
        if same_day:
            return f"today at {time_label}"
        if is_tomorrow:
            return f"tomorrow at {time_label}"

        # Exact one/two-week marks, same weekday as today
        if days_ahead == 7:
            return f"a week from now at {time_label}"
        if days_ahead == 14:
            return f"two weeks from now at {time_label}"

        # Within the next ~3 weeks, refer to it by weekday name where natural
        if 2 <= days_ahead <= 13:
            weekday_name = due_at.strftime("%A")
            if days_ahead <= 6:
                return f"this {weekday_name} at {time_label}"
            return f"next {weekday_name} at {time_label}"

        return f"on {due_at.strftime('%B %d')} at {time_label}"
    
    @staticmethod
    def _minutes_until(date_str: str | None, time_str: str | None) -> str:
        """Compute whole minutes remaining until a date/time, for templates
        that want an exact countdown rather than a fixed '30 minutes' label."""
        if not date_str or not time_str:
            return "a few"
        try:
            due_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return "a few"
        minutes = round((due_at - datetime.now()).total_seconds() / 60)
        return str(max(minutes, 0))

    def say(self, key: str, **values: Any) -> str:
        options = self.templates.get(key)
        if not options:
            return key.format(**values)

        # Auto-derive a natural "{when}" phrase whenever both date and time
        # are supplied, so call sites don't need to compute it themselves.
        if "date" in values and "time" in values and "when" not in values:
            values["when"] = self._humanize_when(values.get("date"), values.get("time"))

        # Auto-derive "{minutes_until}" the same way, for templates that want
        # an exact countdown rather than a fixed threshold label.
        if "date" in values and "time" in values and "minutes_until" not in values:
            values["minutes_until"] = self._minutes_until(values.get("date"), values.get("time"))

        template = self._random.choice(options)
        safe_values = {name: ("not specified" if value in (None, "") else value) for name, value in values.items()}
        return template.format(**safe_values)