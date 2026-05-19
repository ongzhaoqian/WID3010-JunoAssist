#!/usr/bin/env python3
"""ROS speech-to-text node for JUNO Assist using Whisper Tiny.

This keeps the successful human-robot interaction control flow from the
`anas` branch while preserving the lighter ASR model from the integration
branch:

- listens to `/audio/raw` from the microphone node;
- mutes transcription while JUNO is speaking on `/juno/tts`;
- resumes only after `/juno/tts_done` is published by the TTS node;
- uses a fixed audio buffer and RMS/VAD threshold before inference;
- publishes recognised text to `/speech/transcript` for the backend bridge;
- keeps `/speech/raw_transcript` as a manual/external ASR fallback.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Optional

import numpy as np
import rospy
from std_msgs.msg import Float32MultiArray, String


class WhisperTinyTranscriber:
    """Transcribes robot microphone audio with `openai/whisper-tiny`.

    The class intentionally mirrors the working `anas` branch behaviour: audio
    is accumulated in a protected buffer, inference runs in a background thread,
    and STT is muted during TTS to prevent JUNO from hearing itself.
    """

    def __init__(self) -> None:
        rospy.init_node("whisper_tiny_transcriber", anonymous=True)

        self.audio_topic = rospy.get_param("~audio_topic", "/audio/raw")
        self.output_topic = rospy.get_param(
            "~output_text_topic",
            os.getenv("JUNO_TRANSCRIBER_OUTPUT_TOPIC", "/speech/transcript"),
        )
        self.manual_text_topic = rospy.get_param(
            "~manual_text_topic",
            os.getenv("JUNO_TRANSCRIBER_INPUT_TOPIC", "/speech/raw_transcript"),
        )
        self.tts_topic = rospy.get_param("~tts_topic", "/juno/tts")
        self.tts_done_topic = rospy.get_param("~tts_done_topic", "/juno/tts_done")

        self.model_id = os.getenv("JUNO_ASR_MODEL_ID", "openai/whisper-tiny")
        self.sample_rate = int(os.getenv("JUNO_ASR_SAMPLE_RATE", "16000"))
        self.window_seconds = float(os.getenv("JUNO_ASR_WINDOW_SECONDS", "3.0"))
        self.buffer_size = max(1, int(self.sample_rate * self.window_seconds))
        self.min_rms = float(os.getenv("JUNO_ASR_MIN_RMS", "0.03"))
        self.task = os.getenv("JUNO_ASR_TASK", "translate").strip().lower()
        self.language = os.getenv("JUNO_ASR_LANGUAGE", "").strip() or None
        self.device = self._parse_device(os.getenv("JUNO_ASR_DEVICE", "-1"))
        self.tts_resume_delay = float(os.getenv("JUNO_ASR_TTS_RESUME_DELAY", "0.5"))

        self.audio_lock = threading.Lock()
        self.audio_buffer = []
        self.current_length = 0
        self._muted = False
        self._asr_pipeline: Optional[Any] = None
        self._load_error: Optional[str] = None

        self.transcript_pub = rospy.Publisher(self.output_topic, String, queue_size=10)
        rospy.Subscriber(self.audio_topic, Float32MultiArray, self.audio_callback)
        rospy.Subscriber(self.manual_text_topic, String, self.manual_text_callback)
        rospy.Subscriber(self.tts_topic, String, self._on_tts_start)
        rospy.Subscriber(self.tts_done_topic, String, self._on_tts_done)

        self.process_thread = threading.Thread(target=self.inference_loop)
        self.process_thread.daemon = True
        self.process_thread.start()

        rospy.loginfo("JUNO Whisper Tiny transcriber ready.")
        rospy.loginfo("Audio input topic: %s", self.audio_topic)
        rospy.loginfo("Output transcript topic: %s", self.output_topic)
        rospy.loginfo("Manual/external transcript input topic: %s", self.manual_text_topic)
        rospy.loginfo("TTS mute topics: %s -> %s", self.tts_topic, self.tts_done_topic)
        rospy.loginfo("ASR model: %s", self.model_id)
        rospy.loginfo("ASR task: %s", self.task)
        rospy.loginfo("ASR window: %.2fs at %d Hz", self.window_seconds, self.sample_rate)
        rospy.loginfo("ASR RMS threshold: %.4f", self.min_rms)

    def _on_tts_start(self, _msg: String) -> None:
        """Pause STT and clear buffered audio when JUNO starts speaking."""
        self._muted = True
        self._clear_audio_buffer()
        rospy.loginfo("TTS started — transcription muted, audio buffer cleared.")

    def _on_tts_done(self, _msg: String) -> None:
        """Resume STT shortly after JUNO finishes speaking."""
        rospy.sleep(self.tts_resume_delay)
        self._clear_audio_buffer()
        self._muted = False
        rospy.loginfo("TTS done — transcription resumed.")

    def audio_callback(self, msg: Float32MultiArray) -> None:
        if self._muted or not msg.data:
            return

        chunk = np.asarray(msg.data, dtype=np.float32)
        if not chunk.size:
            return

        with self.audio_lock:
            self.audio_buffer.append(chunk)
            self.current_length += int(chunk.size)

    def manual_text_callback(self, msg: String) -> None:
        """Allow typed/external ASR text to use the same backend path."""
        text = self._clean_text(str(msg.data))
        if text:
            rospy.loginfo("Manual/external transcript: %s", text)
            self.transcript_pub.publish(String(data=text))

    def inference_loop(self) -> None:
        while not rospy.is_shutdown():
            if not self._muted and self.current_length >= self.buffer_size:
                with self.audio_lock:
                    full_audio = np.concatenate(self.audio_buffer).astype(np.float32, copy=False)
                    audio_to_process = full_audio[: self.buffer_size]
                    remaining_audio = full_audio[self.buffer_size :]
                    self.audio_buffer = [remaining_audio] if remaining_audio.size else []
                    self.current_length = int(remaining_audio.size)

                rms = float(np.sqrt(np.mean(np.square(audio_to_process)))) if audio_to_process.size else 0.0
                if rms < self.min_rms:
                    rospy.logdebug("Skipping quiet audio. RMS %.6f < %.6f", rms, self.min_rms)
                    rospy.sleep(0.05)
                    continue

                transcript = self.transcribe(audio_to_process)
                if transcript:
                    print(f"[TRANSCRIBED SPEECH] {transcript}", flush=True)
                    rospy.loginfo("Whisper transcript: %s", transcript)
                    self.transcript_pub.publish(String(data=transcript))
                    rospy.loginfo("Published transcript to %s: %s", self.output_topic, transcript)

            rospy.sleep(0.05)

    def transcribe(self, audio: np.ndarray) -> str:
        if not self._ensure_pipeline_loaded():
            rospy.logwarn_throttle(
                10,
                "Whisper Tiny ASR unavailable; use /speech/raw_transcript fallback. Error: %s",
                self._load_error,
            )
            return ""

        audio = np.asarray(audio, dtype=np.float32)
        max_abs = float(np.max(np.abs(audio))) if audio.size else 0.0
        if max_abs > 1.0:
            audio = audio / max_abs

        payload = {"array": audio, "sampling_rate": self.sample_rate}
        generate_kwargs = {}
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
            # Older Transformers versions may not accept generate_kwargs.
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

    def _clear_audio_buffer(self) -> None:
        with self.audio_lock:
            self.audio_buffer = []
            self.current_length = 0

    @staticmethod
    def _parse_device(value: str):
        value = (value or "-1").strip()
        try:
            return int(value)
        except ValueError:
            return value

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.strip().split()).strip('"\'` ')


if __name__ == "__main__":
    try:
        node = WhisperTinyTranscriber()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
