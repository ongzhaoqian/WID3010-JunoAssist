#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2

def image_callback(msg):
    bridge = CvBridge()
    try:
        # Convert ROS Image to OpenCV image
        cv_image = bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
    except CvBridgeError as e:
        rospy.logerr(f"CvBridge Error: {e}")
        return

    # Show the image
    cv2.imshow("Camera Feed", cv_image)
    cv2.waitKey(1)  # Needed to update OpenCV window

def camera_listener_node():
    rospy.init_node('camera_listener_node', anonymous=True)
    rospy.Subscriber("/camera/image_raw", Image, image_callback)
    rospy.loginfo("Camera listener node started. Subscribed to /camera/image_raw")
    rospy.spin()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        camera_listener_node()
    except rospy.ROSInterruptException:
        cv2.destroyAllWindows()