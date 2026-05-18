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
            voices = self.engine.getProperty('voices')
            for v in voices:
                if v.name == "English (Received Pronunciation)":
                    self.engine.setProperty('voice', v.id)
                    self.id = v.id
                    break
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
            accent = "en-u"#ange to en-us, en-sc, etc.
            rospy.loginfo(f'JUNO says ({accent}): {text}')
            subprocess.Popen(['espeak-ng', '-v', accent, text])

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    node = JunoTTSNode()
    node.run()
