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
