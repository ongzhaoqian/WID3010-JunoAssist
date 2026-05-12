#!/usr/bin/env python3
import rospy
import numpy as np
import threading
from std_msgs.msg import Float32MultiArray, String
import moonshine_onnx as moonshine

# Settings
SAMPLE_RATE = 16000
BUFFER_SECONDS = 3
BUFFER_SIZE = SAMPLE_RATE * BUFFER_SECONDS


class MoonshineTranscriber:
    """Subscribes to /audio/raw and publishes recognised text to /speech/transcript."""

    def __init__(self):
        rospy.init_node('moonshine_transcriber')

        self.audio_lock = threading.Lock()
        self.audio_buffer = []
        self.current_length = 0

        rospy.loginfo("Loading Moonshine model...")
        self.model_name = "moonshine/tiny"

        self.sub = rospy.Subscriber('/audio/raw', Float32MultiArray, self.audio_callback)
        self.transcript_pub = rospy.Publisher('/speech/transcript', String, queue_size=10)

        self.process_thread = threading.Thread(target=self.inference_loop)
        self.process_thread.daemon = True
        self.process_thread.start()

        rospy.loginfo("Transcriber ready. Publishing transcripts to /speech/transcript")

    def audio_callback(self, msg):
        with self.audio_lock:
            chunk = np.array(msg.data, dtype=np.float32)
            self.audio_buffer.append(chunk)
            self.current_length += len(chunk)

    def inference_loop(self):
        while not rospy.is_shutdown():
            if self.current_length >= BUFFER_SIZE:
                with self.audio_lock:
                    full_audio = np.concatenate(self.audio_buffer)
                    audio_to_process = full_audio[:BUFFER_SIZE]

                    remaining_audio = full_audio[BUFFER_SIZE:]
                    self.audio_buffer = [remaining_audio]
                    self.current_length = len(remaining_audio)

                try:
                    result = moonshine.transcribe(audio_to_process, self.model_name)
                    transcript = result[0].strip() if result else ""
                    if transcript:
                        rospy.loginfo(f"Transcript: {transcript}")
                        self.transcript_pub.publish(String(data=transcript))
                except Exception as e:
                    rospy.logerr(f"Inference error: {e}")

            rospy.sleep(0.05)


if __name__ == '__main__':
    try:
        node = MoonshineTranscriber()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
