#!/usr/bin/env python3
"""ROS camera listener for diagnostics.

Historically this node opened an OpenCV pop-up window with cv2.imshow(). For
JUNO Assist, the preferred user-facing camera view is now the dashboard camera
window, served by the FastAPI backend from /camera/image_raw.

Run with _display_window:=true only when you explicitly need the old local ROS
OpenCV diagnostic window.
"""

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2


class CameraListener:
    def __init__(self):
        self.bridge = CvBridge()
        self.display_window = rospy.get_param("~display_window", False)
        self.frame_count = 0
        self.window_name = rospy.get_param("~window_name", "Camera Feed")

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as exc:
            rospy.logerr("CvBridge Error: %s", exc)
            return

        self.frame_count += 1
        if self.frame_count == 1:
            rospy.loginfo(
                "Camera frames are being received. Dashboard stream should be "
                "available through the backend at /api/vision/camera/stream."
            )

        if self.display_window:
            cv2.imshow(self.window_name, cv_image)
            cv2.waitKey(1)

    def shutdown(self):
        if self.display_window:
            cv2.destroyAllWindows()


def camera_listener_node():
    rospy.init_node("camera_listener_node", anonymous=True)
    topic = rospy.get_param("~camera_topic", "/camera/image_raw")
    listener = CameraListener()
    rospy.Subscriber(topic, Image, listener.image_callback)
    rospy.loginfo(
        "Camera listener subscribed to %s. display_window=%s. Use the JUNO "
        "dashboard for the normal camera view.",
        topic,
        listener.display_window,
    )
    rospy.on_shutdown(listener.shutdown)
    rospy.spin()


if __name__ == "__main__":
    try:
        camera_listener_node()
    except rospy.ROSInterruptException:
        pass
