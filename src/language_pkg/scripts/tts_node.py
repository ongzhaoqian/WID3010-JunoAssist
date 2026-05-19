#!/usr/bin/env python3
import os
import subprocess

import rospy
from std_msgs.msg import String


class JunoTTSNode:
    """ROS TTS node for JUNO responses.

    This preserves the integration branch's British English voice selection and
    adds the `anas` branch's `/juno/tts_done` signal so the STT node can mute
    while JUNO is speaking and resume afterwards.
    """

    def __init__(self):
        rospy.init_node('juno_tts_node', anonymous=True)
        self.engine = None
        self.voice_locale = os.getenv('JUNO_TTS_VOICE_LOCALE', 'en_GB')
        self.rate = int(os.getenv('JUNO_TTS_RATE', '165'))
        self.done_delay = float(os.getenv('JUNO_TTS_DONE_DELAY', '1.0'))

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
            rospy.logwarn('pyttsx3 unavailable. Falling back to espeak/espeak-ng en-gb. Details: %s', exc)

        self.done_pub = rospy.Publisher('/juno/tts_done', String, queue_size=1)
        rospy.Subscriber('/juno/tts', String, self.callback)
        rospy.loginfo('JUNO TTS node subscribed to /juno/tts and will publish /juno/tts_done')

    def _select_british_voice(self):
        if self.engine is None:
            return None
        preferred_tokens = [
            'en_gb', 'en-gb', 'gb', 'uk', 'british', 'received pronunciation',
            'english_rp', 'english-uk', 'english+f3'
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
            if requested in voice_blob or any(token.replace('-', '_') in voice_blob for token in preferred_tokens):
                return voice.id
        return None

    def callback(self, msg):
        text = str(msg.data).strip()
        if not text:
            return

        rospy.loginfo('JUNO says in British English: %s', text)
        try:
            # pyttsx3 runAndWait() returns immediately on this system — use espeak directly
            self._speak_with_espeak(text)
        finally:
            rospy.sleep(self.done_delay)
            self.done_pub.publish(String(data='done'))
            rospy.loginfo('Published /juno/tts_done')

    def _speak_with_espeak(self, text):
        command = os.getenv('JUNO_TTS_COMMAND', 'espeak-ng')
        args = [command, '-v', 'en-gb', '-s', str(self.rate), text]
        try:
            subprocess.run(args, check=False)
        except FileNotFoundError:
            fallback = ['espeak', '-v', 'en-gb', '-s', str(self.rate), text]
            subprocess.run(fallback, check=False)

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    node = JunoTTSNode()
    node.run()
