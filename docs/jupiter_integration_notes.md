# Jupiter Robot Integration Notes

This repository uses `MockJupiterInterface` by default.

To integrate the physical Jupiter Robot, implement a new class such as:

```python
class RealJupiterInterface(JupiterInterface):
    def speak(self, text: str) -> None:
        # call Jupiter speaker / TTS API
        pass

    def listen(self) -> str:
        # call Jupiter microphone / STT API
        pass

    def get_camera_frame(self):
        # return camera frame
        pass

    def open_dashboard(self, url: str) -> None:
        # open dashboard on robot screen or connected browser
        pass

    def set_led_state(self, state: str) -> None:
        # optional LED / expression feedback
        pass
```

Then register it in the existing factory without removing mock/ROS selection. For example:

```python
def get_robot_interface() -> JupiterInterface:
    if settings.robot_interface == "real":
        return RealJupiterInterface()
    if settings.use_ros_robot:
        return RosJupiterInterface()
    return MockJupiterInterface()
```

This keeps laptop/mock mode available for development and demo fallback while allowing a real Jupiter implementation when the correct environment variable is set.

## Recommended Integration Priority

1. Speaker output
2. Microphone input
3. Camera input
4. LED or screen feedback
5. Optional movement or gestures

Movement is optional because the project scope is a desk-based personal assistant.
