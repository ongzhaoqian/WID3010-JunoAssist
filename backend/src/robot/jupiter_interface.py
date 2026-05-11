from abc import ABC, abstractmethod
import webbrowser
from typing import Any


class JupiterInterface(ABC):
    """Hardware boundary for Jupiter Robot integration.

    Keep all robot-specific SDK or ROS calls here so the rest of the
    application remains testable and hardware-independent.
    """

    @abstractmethod
    def speak(self, text: str) -> None:
        pass

    @abstractmethod
    def listen(self) -> str:
        pass

    @abstractmethod
    def get_camera_frame(self) -> Any:
        pass

    @abstractmethod
    def open_dashboard(self, url: str) -> None:
        pass

    @abstractmethod
    def set_led_state(self, state: str) -> None:
        pass


class MockJupiterInterface(JupiterInterface):
    """Laptop-friendly implementation for demonstration without hardware."""

    def speak(self, text: str) -> None:
        print(f"[JUNO SPEAKS] {text}")

    def listen(self) -> str:
        return input("[USER SPEAKS] ")

    def get_camera_frame(self) -> Any:
        return None

    def open_dashboard(self, url: str) -> None:
        print(f"[JUNO] Opening dashboard: {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def set_led_state(self, state: str) -> None:
        print(f"[JUNO LED] {state}")


def get_robot_interface() -> JupiterInterface:
    # Replace this factory with a real JupiterRobotInterface when Jupiter SDK/ROS
    # bindings are available in the deployment environment.
    return MockJupiterInterface()
