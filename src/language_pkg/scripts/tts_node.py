#!/usr/bin/env python3
import subprocess
import rospy
from std_msgs.msg import String


class JunoTTSNode:
    """Simple ROS TTS node for course demo.

    It subscribes to /juno/tts and speaks messages using pyttsx3 if available,
    otherwise it falls back to espeak. Replace this node with Jupiter's built-in
    speech output API if available.
    """

    def __init__(self):
        rospy.init_node('juno_tts_node', anonymous=True)
        self.engine = None

        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 165)
            rospy.loginfo('Using pyttsx3 for JUNO speech output.')
        except Exception:
            rospy.logwarn('pyttsx3 unavailable. Falling back to espeak command.')

        rospy.Subscriber('/juno/tts', String, self.callback)
        rospy.loginfo('JUNO TTS node subscribed to /juno/tts')

    def callback(self, msg):
        text = str(msg.data).strip()
        if not text:
            return

        rospy.loginfo(f'JUNO says: {text}')
        if self.engine is not None:
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            subprocess.Popen(['espeak', text])

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    node = JunoTTSNode()
    node.run()
