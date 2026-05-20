#!/usr/bin/env python3
import os

import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


def _param_or_env(param_name, env_name, default):
    value = rospy.get_param(param_name, None)
    if value is None or value == "":
        value = os.getenv(env_name, default)
    return value


def camera_node():
    rospy.init_node("camera_node", anonymous=True)

    camera_topic = _param_or_env("~camera_topic", "JUNO_CAMERA_TOPIC", "/camera/image_raw")
    camera_device = _param_or_env("~camera_device", "JUNO_CAMERA_DEVICE", "/dev/video2")
    fps = float(_param_or_env("~fps", "JUNO_CAMERA_FPS", "30"))
    width = int(_param_or_env("~width", "JUNO_CAMERA_WIDTH", "640"))
    height = int(_param_or_env("~height", "JUNO_CAMERA_HEIGHT", "480"))

    pub = rospy.Publisher(camera_topic, Image, queue_size=10)
    rate = rospy.Rate(fps)
    bridge = CvBridge()

    cap = cv2.VideoCapture(camera_device)
    if width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps > 0:
        cap.set(cv2.CAP_PROP_FPS, fps)

    if not cap.isOpened():
        rospy.logerr("Could not open camera device: %s", camera_device)
        return

    rospy.loginfo(
        "Camera node started. device=%s topic=%s requested=%sx%s@%sfps",
        camera_device,
        camera_topic,
        width,
        height,
        fps,
    )

    while not rospy.is_shutdown():
        ret, frame = cap.read()
        if not ret:
            rospy.logwarn_throttle(2.0, "Failed to grab camera frame")
            rate.sleep()
            continue

        ros_image = bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        ros_image.header.stamp = rospy.Time.now()
        ros_image.header.frame_id = "juno_webcam"
        pub.publish(ros_image)
        rate.sleep()

    cap.release()


if __name__ == "__main__":
    try:
        camera_node()
    except rospy.ROSInterruptException:
        pass
