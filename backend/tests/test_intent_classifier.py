from src.nlp.intent_classifier import IntentClassifier
from src.core.models import Intent


def test_wake_intent():
    classifier = IntentClassifier()
    assert classifier.classify("Hey, John") == Intent.WAKE


def test_timer_intent():
    classifier = IntentClassifier()
    assert classifier.classify("Set a 25 minute timer") == Intent.SET_TIMER
    assert classifier.extract_timer_minutes("Set a 25 minute timer") == 25


def test_schedule_intent():
    classifier = IntentClassifier()
    assert classifier.classify("What is my schedule today?") == Intent.CHECK_SCHEDULE


def test_add_schedule_intent_and_date_formatting():
    classifier = IntentClassifier()
    command = "date 2026-05-20 time 15:30 purpose project discussion priority urgent"
    assert classifier.classify(command) == Intent.ADD_SCHEDULE
    parsed = classifier.extract_schedule_item(command)
    assert parsed["title"] == "Project discussion"
    assert parsed["formatted_date"] == "20 May, 2026"
    assert parsed["priority"] == "high"


def test_schedule_date_time_parser_accepts_spoken_formats():
    classifier = IntentClassifier()

    parsed = classifier.extract_schedule_item(
        "add schedule on 25 May at nine pm purpose project discussion priority high"
    )
    assert parsed["date"].endswith("-05-25")
    assert parsed["time"] == "21:00"
    assert parsed["title"] == "Project discussion"

    parsed = classifier.extract_schedule_item(
        "add schedule next monday at half past nine purpose consultation"
    )
    assert parsed["date"] is not None
    assert parsed["time"] == "09:30"

    parsed = classifier.extract_schedule_item(
        "add schedule date 25/05/2026 time quarter to six purpose revision"
    )
    assert parsed["date"] == "2026-05-25"
    assert parsed["time"] == "05:45"


def test_reminder_parser_removes_spoken_date_and_time_from_title():
    classifier = IntentClassifier()
    parsed = classifier.extract_reminder_item(
        "remind me to submit report on twenty fifth of May at nine p m priority high"
    )
    assert parsed["title"] == "Submit report"
    assert parsed["date"].endswith("-05-25")
    assert parsed["time"] == "21:00"
    assert parsed["priority"] == "high"


def test_stop_command_is_narrow_but_interrupts_outputs():
    classifier = IntentClassifier()
    assert classifier.classify("stop") == Intent.STOP
    assert classifier.classify("stop speaking") == Intent.STOP
    assert classifier.classify("stop music") == Intent.STOP
    assert classifier.classify("stop by the office") == Intent.UNKNOWN
