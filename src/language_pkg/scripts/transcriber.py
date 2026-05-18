#!/usr/bin/env python3
import rospy
import numpy as np
import threading
from std_msgs.msg import Float32MultiArray, String
import moonshine_onnx as moonshine

SAMPLE_RATE = 16000
BUFFER_SECONDS = 3
BUFFER_SIZE = SAMPLE_RATE * BUFFER_SECONDS
VAD_ENERGY_THRESHOLD = 0.03  # RMS threshold — tune if too sensitive


class MoonshineTranscriber:
    """Subscribes to /audio/raw and publishes recognised text to /speech/transcript.

    Mutes during robot TTS (via /juno/tts) and resumes after /juno/tts_done.
    Only runs inference when audio energy exceeds VAD_ENERGY_THRESHOLD.
    """

    def __init__(self):
        rospy.init_node('moonshine_transcriber')

        self.audio_lock = threading.Lock()
        self.audio_buffer = []
        self.current_length = 0
        self._muted = False

        rospy.loginfo("Loading Moonshine model...")
        self.model_name = "moonshine/base"

        self.sub = rospy.Subscriber('/audio/raw', Float32MultiArray, self.audio_callback)
        self.transcript_pub = rospy.Publisher('/speech/transcript', String, queue_size=10)
        rospy.Subscriber('/juno/tts', String, self._on_tts_start)
        rospy.Subscriber('/juno/tts_done', String, self._on_tts_done)

        rospy.loginfo("Subscribed to /audio/raw, /juno/tts, /juno/tts_done")

        self.process_thread = threading.Thread(target=self.inference_loop)
        self.process_thread.daemon = True
        self.process_thread.start()

        rospy.loginfo("Transcriber ready. Publishing transcripts to /speech/transcript")

    def _on_tts_start(self, msg):
        self._muted = True
        with self.audio_lock:
            self.audio_buffer = []
            self.current_length = 0
        rospy.loginfo("TTS started — transcription muted, buffer cleared")

    def _on_tts_done(self, msg):
        self._muted = False
        rospy.loginfo("TTS done — transcription resumed")

    def audio_callback(self, msg):
        if self._muted:
            return
        with self.audio_lock:
            chunk = np.array(msg.data, dtype=np.float32)
            self.audio_buffer.append(chunk)
            self.current_length += len(chunk)

    def inference_loop(self):
        while not rospy.is_shutdown():
            if not self._muted and self.current_length >= BUFFER_SIZE:
                with self.audio_lock:
                    full_audio = np.concatenate(self.audio_buffer)
                    audio_to_process = full_audio[:BUFFER_SIZE]
                    remaining_audio = full_audio[BUFFER_SIZE:]
                    self.audio_buffer = [remaining_audio]
                    self.current_length = len(remaining_audio)

                rms = float(np.sqrt(np.mean(audio_to_process ** 2)))
                if rms < VAD_ENERGY_THRESHOLD:
                    rospy.sleep(0.05)
                    continue

                try:
                    result = moonshine.transcribe(audio_to_process, self.model_name)
                    transcript = result[0].strip() if result else ""
                    if transcript:
                        print(f"[TRANSCRIBED SPEECH] {transcript}", flush=True)
                        rospy.loginfo(f"Transcript: {transcript}")
                        self.transcript_pub.publish(String(data=transcript))
                        rospy.loginfo(f"Published transcript to /speech/transcript: {transcript}")
                except Exception as e:
                    rospy.logerr(f"Inference error: {e}")

            rospy.sleep(0.05)


if __name__ == '__main__':
    try:
        node = MoonshineTranscriber()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
