from __future__ import annotations

from queue import Queue, Empty
from threading import Lock
from typing import Any
import subprocess
import time
import webbrowser

from src.core.config import settings

from .jupiter_interface import JupiterInterface


class RosJupiterInterface(JupiterInterface):
    """ROS bridge between the FastAPI backend and Jupiter Robot topics.

    Expected ROS topics from the attached Jupiter code:
    - /camera/image_raw       sensor_msgs/Image
    - /speech/transcript      std_msgs/String

    Topics published by this backend:
    - /juno/tts               std_msgs/String
    - /juno/led_state         std_msgs/String

    The TTS publisher is latched and waits briefly for a subscriber before
    sending speech. This avoids the common startup issue where the backend
    processes the first transcript correctly but the first response is dropped
    because the ROS TTS node has not fully connected yet.
    """

    def __init__(self) -> None:
        try:
            import rospy
            from std_msgs.msg import String
            from sensor_msgs.msg import Image
            from cv_bridge import CvBridge
        except Exception as exc:  # pragma: no cover - only used on ROS machine
            raise RuntimeError(
                "ROS Jupiter interface requested, but rospy/cv_bridge/sensor_msgs "
                "could not be imported. Source your catkin workspace first and run "
                "this backend inside the ROS Python environment."
            ) from exc

        self.rospy = rospy
        self.String = String
        self.Image = Image
        self.bridge = CvBridge()
        self.transcript_queue: Queue[str] = Queue()
        self.latest_frame: Any = None
        self._frame_lock = Lock()

        self.camera_topic = settings.camera_topic
        self.tts_topic = settings.tts_topic
        self.led_topic = settings.led_topic
        self.tts_wait_seconds = max(0.0, settings.tts_publisher_wait_seconds)
        self.tts_publish_retries = max(1, settings.tts_publish_retries)
        self.tts_publish_retry_delay = max(0.0, settings.tts_publish_retry_delay)

        if not rospy.core.is_initialized():
            rospy.init_node("juno_backend_bridge", anonymous=True, disable_signals=True)

        # latch=True lets a restarted TTS subscriber receive the latest response,
        # and the explicit connection wait below protects normal startup.
        self.tts_pub = rospy.Publisher(self.tts_topic, String, queue_size=10, latch=True)
        self.led_pub = rospy.Publisher(self.led_topic, String, queue_size=10, latch=True)

        rospy.Subscriber("/speech/transcript", String, self._transcript_callback)
        rospy.Subscriber(self.camera_topic, Image, self._camera_callback)

        rospy.loginfo(
            "JUNO backend ROS bridge is ready. Camera topic=%s, TTS topic=%s, LED topic=%s",
            self.camera_topic,
            self.tts_topic,
            self.led_topic,
        )

    def _transcript_callback(self, msg: Any) -> None:
        text = str(msg.data).strip()
        if text:
            self.rospy.loginfo("Backend received transcript: %s", text)
            self.transcript_queue.put(text)

    def _camera_callback(self, msg: Any) -> None:
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            with self._frame_lock:
                self.latest_frame = frame
        except Exception as exc:
            self.rospy.logwarn(f"Could not convert ROS image to OpenCV frame: {exc}")

    def _wait_for_tts_subscriber(self) -> bool:
        """Wait briefly for language_pkg/tts_node.py to subscribe."""
        if self.tts_wait_seconds <= 0:
            return self.tts_pub.get_num_connections() > 0

        deadline = time.monotonic() + self.tts_wait_seconds
        while not self.rospy.is_shutdown() and time.monotonic() < deadline:
            if self.tts_pub.get_num_connections() > 0:
                return True
            self.rospy.sleep(0.05)
        return self.tts_pub.get_num_connections() > 0

    def speak(self, text: str) -> None:
        text = str(text).strip()
        if not text:
            return

        connected = self._wait_for_tts_subscriber()
        if not connected:
            self.rospy.logwarn(
                "Publishing JUNO speech without an active subscriber on %s. "
                "Check that language_pkg/scripts/tts_node.py is running.",
                self.tts_topic,
            )

        msg = self.String(data=text)
        for attempt in range(1, self.tts_publish_retries + 1):
            self.tts_pub.publish(msg)
            self.rospy.loginfo(
                "Published JUNO speech to %s (attempt %d/%d): %s",
                self.tts_topic,
                attempt,
                self.tts_publish_retries,
                text,
            )
            if attempt < self.tts_publish_retries:
                self.rospy.sleep(self.tts_publish_retry_delay)

    def listen(self) -> str:
        try:
            return self.transcript_queue.get(timeout=1.0)
        except Empty:
            return ""

    def get_camera_frame(self) -> Any:
        with self._frame_lock:
            if self.latest_frame is None:
                return None
            try:
                return self.latest_frame.copy()
            except AttributeError:
                return self.latest_frame

    def open_dashboard(self, url: str) -> None:
        # On a robot with GUI, this opens the dashboard locally. If the robot is
        # headless, access the dashboard from another laptop using the robot IP.
        try:
            subprocess.Popen(["xdg-open", url])
        except Exception:
            try:
                webbrowser.open(url)
            except Exception:
                pass

    def set_led_state(self, state: str) -> None:
        state = str(state).strip()
        if not state:
            return
        self.led_pub.publish(self.String(data=state))
        self.rospy.loginfo("Published JUNO LED state to %s: %s", self.led_topic, state)
