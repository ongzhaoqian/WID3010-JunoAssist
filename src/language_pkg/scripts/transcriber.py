#!/usr/bin/env python3
"""ROS speech-to-text node for JUNO Assist.

Primary ASR: openai/whisper-tiny via Hugging Face Transformers pipeline.
Fallback ASR: moonshine/base via moonshine-onnx (used if Whisper fails to load).

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
        self.window_seconds = float(os.getenv("JUNO_ASR_WINDOW_SECONDS", "1.0"))
        self.buffer_size = max(1, int(self.sample_rate * self.window_seconds))
        self.min_rms = float(os.getenv("JUNO_ASR_MIN_RMS", "0.010"))
        self.task = os.getenv("JUNO_ASR_TASK", "transcribe").strip().lower()
        self.language = os.getenv("JUNO_ASR_LANGUAGE", "").strip() or None
        self.device = self._parse_device(os.getenv("JUNO_ASR_DEVICE", "-1"))
        self.tts_resume_delay = float(os.getenv("JUNO_ASR_TTS_RESUME_DELAY", "0.5"))

        self.moonshine_model = os.getenv("JUNO_ASR_MOONSHINE_MODEL", "moonshine/base")

        self.audio_lock = threading.Lock()
        self.audio_buffer = []
        self.current_length = 0
        self._muted = False
        self._last_loud_time: float = 0.0
        self._silence_flush_seconds: float = 0.4
        self._asr_pipeline: Optional[Any] = None
        self._moonshine: Optional[Any] = None
        self._load_error: Optional[str] = None
        self._using_moonshine: bool = False

        self.transcript_pub = rospy.Publisher(self.output_topic, String, queue_size=10)
        rospy.Subscriber(self.audio_topic, Float32MultiArray, self.audio_callback)
        rospy.Subscriber(self.manual_text_topic, String, self.manual_text_callback)
        rospy.Subscriber(self.tts_topic, String, self._on_tts_start)
        rospy.Subscriber(self.tts_done_topic, String, self._on_tts_done)

        self.process_thread = threading.Thread(target=self.inference_loop)
        self.process_thread.daemon = True
        self.process_thread.start()

        rospy.loginfo("JUNO transcriber ready. Primary: %s | Fallback: %s", self.model_id, self.moonshine_model)
        rospy.loginfo("Audio input topic: %s", self.audio_topic)
        rospy.loginfo("Output transcript topic: %s", self.output_topic)
        rospy.loginfo("Manual/external transcript input topic: %s", self.manual_text_topic)
        rospy.loginfo("TTS mute topics: %s -> %s", self.tts_topic, self.tts_done_topic)
        rospy.loginfo("ASR task: %s | window: %.2fs at %d Hz | RMS threshold: %.4f", self.task, self.window_seconds, self.sample_rate, self.min_rms)

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
        import time as _time
        if self._muted or not msg.data:
            return

        chunk = np.asarray(msg.data, dtype=np.float32)
        if not chunk.size:
            return

        chunk_rms = float(np.sqrt(np.mean(np.square(chunk))))
        if chunk_rms >= self.min_rms:
            self._last_loud_time = _time.monotonic()

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
        import time as _time
        while not rospy.is_shutdown():
            # flush early if speech detected then silence for 0.4s (catches short words like "yes")
            silence_flush = (
                not self._muted
                and self.current_length > 0
                and self.current_length < self.buffer_size
                and self._last_loud_time > 0
                and (_time.monotonic() - self._last_loud_time) >= self._silence_flush_seconds
            )
            if not self._muted and self.current_length > 0 and not silence_flush and self.current_length < self.buffer_size:
                rospy.logdebug("[DBG] waiting: samples=%d/%d last_loud=%.2fs ago",
                               self.current_length, self.buffer_size,
                               (_time.monotonic() - self._last_loud_time) if self._last_loud_time else -1)
            if not self._muted and (self.current_length >= self.buffer_size or silence_flush):
                with self.audio_lock:
                    full_audio = np.concatenate(self.audio_buffer).astype(np.float32, copy=False)
                    audio_to_process = full_audio[: self.buffer_size]
                    remaining_audio = full_audio[self.buffer_size :]
                    self.audio_buffer = [remaining_audio] if remaining_audio.size else []
                    self.current_length = int(remaining_audio.size)
                    self._last_loud_time = 0.0

                rms = float(np.sqrt(np.mean(np.square(audio_to_process)))) if audio_to_process.size else 0.0
                rospy.loginfo("[DBG] flush=%s samples=%d rms=%.5f threshold=%.5f",
                              "silence" if silence_flush else "full",
                              audio_to_process.size, rms, self.min_rms)
                if rms < self.min_rms:
                    rospy.loginfo("[DBG] Skipped — below RMS threshold")
                    rospy.sleep(0.05)
                    continue

                # pad short clips to full buffer size so Whisper has enough context
                if audio_to_process.size < self.buffer_size:
                    audio_to_process = np.pad(audio_to_process, (0, self.buffer_size - audio_to_process.size))

                transcript = self.transcribe(audio_to_process)
                rospy.loginfo("[DBG] Whisper raw output: %r", transcript)
                if transcript and not self._is_hallucination(transcript):
                    engine = "Moonshine" if self._using_moonshine else "Whisper"
                    print(f"[TRANSCRIBED SPEECH] ({engine}) {transcript}", flush=True)
                    rospy.loginfo("%s transcript: %s", engine, transcript)
                    self.transcript_pub.publish(String(data=transcript))
                    rospy.loginfo("Published transcript to %s: %s", self.output_topic, transcript)

            rospy.sleep(0.05)

    def transcribe(self, audio: np.ndarray) -> str:
        if not self._ensure_pipeline_loaded():
            rospy.logwarn_throttle(
                10,
                "All ASR engines unavailable; use /speech/raw_transcript fallback. Error: %s",
                self._load_error,
            )
            return ""

        audio = np.asarray(audio, dtype=np.float32)
        max_abs = float(np.max(np.abs(audio))) if audio.size else 0.0
        if max_abs > 1.0:
            audio = audio / max_abs

        if self._using_moonshine:
            return self._transcribe_moonshine(audio)
        return self._transcribe_whisper(audio)

    def _transcribe_whisper(self, audio: np.ndarray) -> str:
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
            result = self._asr_pipeline(payload)
        except Exception as exc:
            rospy.logerr("Whisper transcription failed: %s", exc)
            return ""

        if isinstance(result, dict):
            return self._clean_text(str(result.get("text", "")))
        return self._clean_text(str(result))

    def _transcribe_moonshine(self, audio: np.ndarray) -> str:
        try:
            import moonshine_onnx as moonshine
            result = moonshine.transcribe(audio, self.moonshine_model)
            transcript = result[0].strip() if result else ""
            return self._clean_text(transcript)
        except Exception as exc:
            rospy.logerr("Moonshine transcription failed: %s", exc)
            return ""

    def _ensure_pipeline_loaded(self) -> bool:
        if self._asr_pipeline is not None or self._using_moonshine:
            return True
        if self._load_error is not None:
            return False

        # Try Whisper first
        try:
            from transformers import pipeline

            rospy.loginfo("Loading Whisper ASR pipeline: %s", self.model_id)
            self._asr_pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
                device=self.device,
            )
            rospy.loginfo("Whisper ASR loaded successfully.")
            return True
        except Exception as whisper_exc:
            rospy.logwarn("Whisper failed to load (%s). Trying Moonshine fallback.", whisper_exc)

        # Fallback to Moonshine
        try:
            import moonshine_onnx  # noqa: F401 — verify import works
            rospy.loginfo("Moonshine fallback loaded: %s", self.moonshine_model)
            self._using_moonshine = True
            return True
        except Exception as moonshine_exc:
            self._load_error = "Whisper: %s | Moonshine: %s" % (whisper_exc, moonshine_exc)
            rospy.logerr("Both ASR engines failed to load. %s", self._load_error)
            return False

    @staticmethod
    def _is_hallucination(text: str) -> bool:
        import re as _re

        # non-ASCII (Japanese/Chinese hallucinations on silence)
        if _re.search(r'[^\x00-\x7F]', text):
            rospy.logwarn("Dropping non-ASCII hallucination: %s...", text[:40])
            return True

        # known Whisper silence phrases
        _SILENCE_PHRASES = {
            "thank you for watching",
            "thanks for watching",
            "please subscribe",
            "like and subscribe",
            "see you next time",
            "bye bye",
            "thank you",
            "thanks",
            "sour de la pente",
            "a lot of people are watching",
        }
        lower = text.lower().strip(" .,!?")
        if any(p in lower for p in _SILENCE_PHRASES):
            rospy.logwarn("Dropping known silence hallucination: %s", text[:60])
            return True

        # single char repeated with any separator: J-J-J-J or a.a.a.a
        if _re.search(r'\b(\w)\W\1(\W\1){4,}', text):
            rospy.logwarn("Dropping single-char loop hallucination: %s...", text[:40])
            return True

        # 4-word ngram repeated 3+ times
        words = text.split()
        ngram_size = 4
        if len(words) >= ngram_size * 3:
            ngrams = [" ".join(words[i:i+ngram_size]) for i in range(len(words) - ngram_size + 1)]
            for ng in ngrams:
                if ngrams.count(ng) >= 3:
                    rospy.logwarn("Dropping hallucination loop: %s...", text[:80])
                    return True
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
