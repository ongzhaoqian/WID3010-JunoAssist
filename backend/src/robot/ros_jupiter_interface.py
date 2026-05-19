from __future__ import annotations

from queue import Queue, Empty
from typing import Any
<<<<<<< HEAD
=======
import logging
>>>>>>> origin/anas
import subprocess
import webbrowser

from .jupiter_interface import JupiterInterface

<<<<<<< HEAD
=======
logger = logging.getLogger("juno.backend.ros")

>>>>>>> origin/anas

class RosJupiterInterface(JupiterInterface):
    """ROS bridge between the FastAPI backend and Jupiter Robot topics.

    Expected ROS topics from the attached Jupiter code:
    - /camera/image_raw       sensor_msgs/Image
    - /speech/transcript      std_msgs/String

    Topics published by this backend:
    - /juno/tts               std_msgs/String
    - /juno/led_state         std_msgs/String
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

        if not rospy.core.is_initialized():
            rospy.init_node("juno_backend_bridge", anonymous=True, disable_signals=True)

        self.tts_pub = rospy.Publisher("/juno/tts", String, queue_size=10)
        self.led_pub = rospy.Publisher("/juno/led_state", String, queue_size=10)

        rospy.Subscriber("/speech/transcript", String, self._transcript_callback)
        rospy.Subscriber("/camera/image_raw", Image, self._camera_callback)

        rospy.loginfo("JUNO backend ROS bridge is ready.")
<<<<<<< HEAD
=======
        logger.info("JUNO backend ROS bridge is ready. Subscribed to /speech/transcript and /camera/image_raw")
>>>>>>> origin/anas

    def _transcript_callback(self, msg: Any) -> None:
        text = str(msg.data).strip()
        if text:
<<<<<<< HEAD
=======
            print(f"[BACKEND ROS TRANSCRIPT] {text}", flush=True)
            self.rospy.loginfo(f"Backend received /speech/transcript: {text}")
            logger.info("Backend received /speech/transcript: %s", text)
>>>>>>> origin/anas
            self.transcript_queue.put(text)

    def _camera_callback(self, msg: Any) -> None:
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.rospy.logwarn(f"Could not convert ROS image to OpenCV frame: {exc}")

    def speak(self, text: str) -> None:
<<<<<<< HEAD
=======
        logger.info("Publishing backend response to /juno/tts: %s", text)
>>>>>>> origin/anas
        self.tts_pub.publish(self.String(data=text))

    def listen(self) -> str:
        try:
            return self.transcript_queue.get(timeout=1.0)
        except Empty:
            return ""

    def get_camera_frame(self) -> Any:
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
        self.led_pub.publish(self.String(data=state))
