#!/usr/bin/env python3
import os
import subprocess

import rospy
from std_msgs.msg import String


class JunoTTSNode:
    """ROS TTS node that favours a standard British English voice.

    The backend publishes already-normalised British English text to /juno/tts.
    This node selects an en_GB/UK/British voice when pyttsx3 provides one, or
    falls back to espeak with the en-gb voice.
    """

    def __init__(self):
        rospy.init_node('juno_tts_node', anonymous=True)
        self.engine = None
        self.voice_locale = os.getenv('JUNO_TTS_VOICE_LOCALE', 'en_GB')
        self.rate = int(os.getenv('JUNO_TTS_RATE', '165'))

        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            selected_voice = self._select_british_voice()
            if selected_voice:
                self.engine.setProperty('voice', selected_voice)
                rospy.loginfo('Using pyttsx3 British English voice: %s', selected_voice)
            else:
                rospy.logwarn('No explicit British English pyttsx3 voice found; using default pyttsx3 voice.')
        except Exception as exc:
            self.engine = None
            rospy.logwarn('pyttsx3 unavailable. Falling back to espeak en-gb. Details: %s', exc)

        rospy.Subscriber('/juno/tts', String, self.callback)
        rospy.loginfo('JUNO TTS node subscribed to /juno/tts')

    def _select_british_voice(self):
        if self.engine is None:
            return None
        preferred_tokens = [
            'en_gb', 'en-gb', 'gb', 'uk', 'british', 'english_rp', 'english-uk', 'english+f3'
        ]
        requested = self.voice_locale.lower().replace('-', '_')
        for voice in self.engine.getProperty('voices'):
            voice_blob = ' '.join(
                str(value).lower()
                for value in [
                    getattr(voice, 'id', ''),
                    getattr(voice, 'name', ''),
                    getattr(voice, 'languages', ''),
                ]
            ).replace('-', '_')
            if requested in voice_blob or any(token in voice_blob for token in preferred_tokens):
                return voice.id
        return None

    def callback(self, msg):
        text = str(msg.data).strip()
        if not text:
            return

        rospy.loginfo(f'JUNO says: {text}')
        if self.engine is not None:
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            subprocess.Popen(['espeak', '-v', 'en-gb', '-s', str(self.rate), text])

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    node = JunoTTSNode()
    node.run()
