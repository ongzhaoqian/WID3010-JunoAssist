#!/usr/bin/env python3
"""Publish a one-off test phrase to JUNO's TTS topic.

Usage after sourcing the catkin workspace:
    rosrun language_pkg tts_test_publisher.py "Hello, I am JUNO."
"""
import sys
import time

import rospy
from std_msgs.msg import String


if __name__ == '__main__':
    rospy.init_node('juno_tts_test_publisher', anonymous=True)
    topic = rospy.get_param('~tts_topic', '/juno/tts')
    text = ' '.join(sys.argv[1:]).strip() or 'Hello, I am JUNO and my speech output is working.'
    pub = rospy.Publisher(topic, String, queue_size=1, latch=True)

    deadline = time.time() + 3.0
    while pub.get_num_connections() == 0 and not rospy.is_shutdown() and time.time() < deadline:
        rospy.sleep(0.05)

    pub.publish(String(data=text))
    rospy.loginfo('Published test TTS to %s: %s', topic, text)
    rospy.sleep(0.5)
