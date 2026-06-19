from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


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
            "Your focus session is ready. The timer is set for {duration}.",
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
            "Added {purpose} to your schedule for {date} at {time}, with {priority} priority.",
            "Done. I have scheduled {purpose} on {date} at {time}. Priority is {priority}.",
            "I have added {purpose} to the dashboard schedule: {date}, {time}, {priority} priority.",
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
            "Your nearest academic task is {title} on {date} at {time}.",
            "The closest task I found is {title}, scheduled for {date} at {time}.",
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
            "I will play music based on your current emotion estimate.",
            "Sure. I will choose a playlist that fits your latest emotion estimate.",
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
            "Reminder added: {title} on {date} at {time}, with {priority} priority.",
            "Done. I have added the reminder: {title}. Date {date}, time {time}, priority {priority}.",
            "I have added {title} to your reminders for {date} at {time}.",
        ],
        "reminder_removed": [
            "Reminder removed.",
            "Done. I have removed that reminder.",
        ],
        "schedule_reminder_30": [
            "Upcoming: {title} in 30 minutes.",
            "Heads up, {title} starts in 30 minutes.",
        ],
        "schedule_reminder_due": [
            "{title} starts now.",
            "It is time for {title}.",
        ],
    })

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def say(self, key: str, **values: Any) -> str:
        options = self.templates.get(key)
        if not options:
            return key.format(**values)
        template = self._random.choice(options)
        safe_values = {name: ("not specified" if value in (None, "") else value) for name, value in values.items()}
        return template.format(**safe_values)
