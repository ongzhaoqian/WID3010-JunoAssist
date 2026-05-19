#!/usr/bin/env python3
<<<<<<< HEAD
"""ROS Whisper Tiny speech-to-text node for JUNO Assist.

This node replaces the heavy Malaysian Llama + LoRA language node with a
lightweight automatic speech-recognition path using Hugging Face
``openai/whisper-tiny``. The ROS topic boundary is intentionally unchanged:
it still publishes recognised text to ``/speech/transcript`` so the FastAPI
backend and ``RosJupiterInterface`` can continue to consume the same topic.

Inputs:
- ``/audio/raw`` as ``std_msgs/Float32MultiArray`` from ``microphone_node.py``.
- ``/speech/raw_transcript`` as ``std_msgs/String`` as a manual/external ASR
  fallback during demos.

Output:
- ``/speech/transcript`` as ``std_msgs/String``.
"""

from __future__ import annotations

import os
from queue import Empty, Queue
from typing import Any, Optional

import numpy as np
import rospy
from std_msgs.msg import Float32MultiArray, String


class WhisperTinyTranscriberNode:
    """Transcribes microphone audio with ``openai/whisper-tiny``."""

    def __init__(self) -> None:
        rospy.init_node("whisper_tiny_transcriber", anonymous=True)

        self.audio_topic = rospy.get_param("~audio_topic", "/audio/raw")
        self.manual_text_topic = rospy.get_param(
            "~manual_text_topic",
            os.getenv("JUNO_TRANSCRIBER_INPUT_TOPIC", "/speech/raw_transcript"),
        )
        self.output_topic = rospy.get_param(
            "~output_text_topic",
            os.getenv("JUNO_TRANSCRIBER_OUTPUT_TOPIC", "/speech/transcript"),
        )

        self.model_id = os.getenv("JUNO_ASR_MODEL_ID", "openai/whisper-tiny")
        self.sample_rate = int(os.getenv("JUNO_ASR_SAMPLE_RATE", "16000"))
        self.window_seconds = float(os.getenv("JUNO_ASR_WINDOW_SECONDS", "4.0"))
        self.min_rms = float(os.getenv("JUNO_ASR_MIN_RMS", "0.008"))
        self.task = os.getenv("JUNO_ASR_TASK", "translate").strip().lower()
        self.language = os.getenv("JUNO_ASR_LANGUAGE", "").strip() or None
        self.device = self._parse_device(os.getenv("JUNO_ASR_DEVICE", "-1"))

        self._audio_queue: Queue[np.ndarray] = Queue()
        self._asr_pipeline: Optional[Any] = None
        self._load_error: Optional[str] = None

        self.publisher = rospy.Publisher(self.output_topic, String, queue_size=10)
        rospy.Subscriber(self.audio_topic, Float32MultiArray, self.audio_callback)
        rospy.Subscriber(self.manual_text_topic, String, self.manual_text_callback)

        rospy.loginfo("JUNO Whisper Tiny transcriber ready.")
        rospy.loginfo("Audio input topic: %s", self.audio_topic)
        rospy.loginfo("Manual/external transcript input topic: %s", self.manual_text_topic)
        rospy.loginfo("Output transcript topic: %s", self.output_topic)
        rospy.loginfo("ASR model: %s", self.model_id)
        rospy.loginfo("ASR task: %s", self.task)
        rospy.loginfo("ASR sample rate: %s Hz", self.sample_rate)

    def audio_callback(self, msg: Float32MultiArray) -> None:
        if not msg.data:
            return
        chunk = np.asarray(msg.data, dtype=np.float32)
        if chunk.size:
            self._audio_queue.put(chunk)

    def manual_text_callback(self, msg: String) -> None:
        """Allow manual or external ASR text to use the same backend path."""

        text = self._clean_text(str(msg.data))
        if text:
            rospy.loginfo("Manual/external transcript: %s", text)
            self.publisher.publish(String(data=text))

    def run(self) -> None:
        target_samples = max(1, int(self.sample_rate * self.window_seconds))
        buffer: list[np.ndarray] = []
        buffered_samples = 0
        rate = rospy.Rate(20)

        while not rospy.is_shutdown():
            try:
                while True:
                    chunk = self._audio_queue.get_nowait()
                    buffer.append(chunk)
                    buffered_samples += int(chunk.size)
            except Empty:
                pass

            if buffered_samples >= target_samples:
                audio = np.concatenate(buffer).astype(np.float32, copy=False)
                buffer.clear()
                buffered_samples = 0

                rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
                if rms < self.min_rms:
                    rospy.logdebug("Skipping quiet audio window. RMS %.6f < %.6f", rms, self.min_rms)
                else:
                    transcript = self.transcribe(audio)
                    if transcript:
                        rospy.loginfo("Whisper transcript: %s", transcript)
                        self.publisher.publish(String(data=transcript))
                    else:
                        rospy.logdebug("Whisper returned an empty transcript.")

            rate.sleep()

    def transcribe(self, audio: np.ndarray) -> str:
        if not self._ensure_pipeline_loaded():
            rospy.logwarn_throttle(
                10,
                "Whisper Tiny ASR unavailable; use /speech/raw_transcript manual fallback. Error: %s",
                self._load_error,
            )
            return ""

        # Whisper expects mono float audio. The microphone node already publishes
        # float32 samples at roughly 16 kHz, but clipping is still guarded here.
        audio = np.asarray(audio, dtype=np.float32)
        max_abs = float(np.max(np.abs(audio))) if audio.size else 0.0
        if max_abs > 1.0:
            audio = audio / max_abs

        payload = {"array": audio, "sampling_rate": self.sample_rate}
        generate_kwargs: dict[str, str] = {}
        if self.task in {"translate", "transcribe"}:
            generate_kwargs["task"] = self.task
        if self.language:
            generate_kwargs["language"] = self.language

        try:
            if generate_kwargs:
                result = self._asr_pipeline(payload, generate_kwargs=generate_kwargs)
            else:
                result = self._asr_pipeline(payload)
        except TypeError:
            # Older Transformers versions may not accept generate_kwargs in the
            # pipeline call. The fallback still transcribes, just with defaults.
            result = self._asr_pipeline(payload)
        except Exception as exc:  # pragma: no cover - model/runtime dependent
            rospy.logerr("Whisper Tiny transcription failed: %s", exc)
            return ""

        if isinstance(result, dict):
            return self._clean_text(str(result.get("text", "")))
        return self._clean_text(str(result))

    def _ensure_pipeline_loaded(self) -> bool:
        if self._asr_pipeline is not None:
            return True
        if self._load_error is not None:
            return False

        try:
            from transformers import pipeline

            rospy.loginfo("Loading Whisper ASR pipeline: %s", self.model_id)
            self._asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
                device=self.device,
            )
            return True
        except Exception as exc:  # pragma: no cover - dependency/model dependent
            self._load_error = str(exc)
            rospy.logerr("Could not load Whisper Tiny ASR pipeline: %s", exc)
            return False

    @staticmethod
    def _parse_device(value: str):
        value = (value or "-1").strip()
        try:
            return int(value)
        except ValueError:
            return value

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = " ".join(text.strip().split()).strip('"\'` ')
        return cleaned


if __name__ == "__main__":
    try:
        WhisperTinyTranscriberNode().run()
=======
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
        rospy.loginfo("Subscribed to /audio/raw and advertising /speech/transcript")

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
>>>>>>> origin/anas
    except rospy.ROSInterruptException:
        pass
