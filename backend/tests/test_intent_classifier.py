from src.nlp.intent_classifier import IntentClassifier
from src.core.models import Intent


def test_wake_intent():
    classifier = IntentClassifier()
    assert classifier.classify("Hey, Juno") == Intent.WAKE


def test_timer_intent():
    classifier = IntentClassifier()
    assert classifier.classify("Set a 25 minute timer") == Intent.SET_TIMER
    assert classifier.extract_timer_minutes("Set a 25 minute timer") == 25


def test_schedule_intent():
    classifier = IntentClassifier()
    assert classifier.classify("What is my schedule today?") == Intent.CHECK_SCHEDULE
