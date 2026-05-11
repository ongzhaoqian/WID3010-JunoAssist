#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

def camera_node():
    rospy.init_node('camera_node', anonymous=True)
    pub = rospy.Publisher('/camera/image_raw', Image, queue_size=10)
    rate = rospy.Rate(30)  # 30 Hz
    bridge = CvBridge()

    # Open Juno camera
    camera_device = rospy.get_param("~camera_device", "/dev/video2")
    cap = cv2.VideoCapture(camera_device)
    if not cap.isOpened():
        rospy.logerr("Could not open camera.")
        return

    rospy.loginfo("Camera node started, publishing to /camera/image_raw")

    while not rospy.is_shutdown():
        ret, frame = cap.read()
        if not ret:
            rospy.logwarn("Failed to grab frame")
            continue

        # Convert OpenCV image to ROS Image
        ros_image = bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        pub.publish(ros_image)
        rate.sleep()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        camera_node()
    except rospy.ROSInterruptException:
        pass