#!/usr/bin/env python3
"""Manual transcript publisher for testing the Whisper Tiny transcript path.

Run this instead of a real ASR source during a demo rehearsal, then type Malay,
Manglish, Mandarin, Tamil, or English utterances in the terminal. The language
node will relay the text to /speech/transcript as a fallback to live ASR.
"""

import rospy
from std_msgs.msg import String


def main():
    rospy.init_node('manual_raw_transcript_publisher', anonymous=True)
    topic = rospy.get_param('~output_topic', '/speech/raw_transcript')
    publisher = rospy.Publisher(topic, String, queue_size=10)
    rospy.loginfo('Publishing typed utterances to %s. Press Ctrl+C to stop.', topic)

    while not rospy.is_shutdown():
        try:
            text = input('User utterance > ').strip()
        except EOFError:
            break
        if text:
            publisher.publish(String(data=text))


if __name__ == '__main__':
    main()
