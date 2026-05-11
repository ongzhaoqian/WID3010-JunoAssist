from src.robot.jupiter_interface import JupiterInterface


class TextToSpeech:
    def __init__(self, robot: JupiterInterface) -> None:
        self.robot = robot

    def speak(self, text: str) -> None:
        self.robot.speak(text)
