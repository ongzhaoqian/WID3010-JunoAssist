from abc import ABC, abstractmethod
import webbrowser
from typing import Any

from src.core.config import settings


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
    if settings.use_ros_robot:
        try:
            
            from .ros_jupiter_interface import RosJupiterInterface
            print("ROS robot interface selected. Attempting to initialize RosJupiterInterface...")
            return RosJupiterInterface()
        except RuntimeError as exc:
            print(
                f"WARNING: ROS interface unavailable: {exc}. "
                "Falling back to the mock Jupiter interface."
            )
    return MockJupiterInterface()
