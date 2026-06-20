#!/usr/bin/env python3
import os
import queue
import shutil
import subprocess
import tempfile
import threading

import rospy
from std_msgs.msg import String


def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class JunoTTSNode:
    """ROS TTS node for JUNO responses.

    The backend publishes text to /juno/tts. This node speaks the text and then
    publishes /juno/tts_done so the Whisper STT node can safely resume listening.

    Changes from the previous integration patch:
    - topic names are parameterised;
    - speech is handled on a single worker thread, avoiding pyttsx3 callback
      threading issues;
    - espeak-ng/espeak fallback is checked and logged clearly;
    - /juno/tts_done is published even when the speech backend fails, so STT is
      never left permanently muted.
    """

    def __init__(self):
        rospy.init_node('juno_tts_node', anonymous=True)

        self.tts_topic = rospy.get_param('~tts_topic', os.getenv('JUNO_TTS_TOPIC', '/juno/tts'))
        self.stop_topic = rospy.get_param('~tts_stop_topic', os.getenv('JUNO_TTS_STOP_TOPIC', '/juno/tts_stop'))
        self.done_topic = rospy.get_param('~tts_done_topic', os.getenv('JUNO_TTS_DONE_TOPIC', '/juno/tts_done'))
        self.voice_locale = rospy.get_param('~voice_locale', os.getenv('JUNO_TTS_VOICE_LOCALE', 'en_GB'))
        self.rate = int(rospy.get_param('~rate', _env_int('JUNO_TTS_RATE', 165)))
        self.done_delay = float(rospy.get_param('~done_delay', _env_float('JUNO_TTS_DONE_DELAY', 1.0)))
        self.backend = str(rospy.get_param('~backend', os.getenv('JUNO_TTS_BACKEND', 'auto'))).strip().lower()
        self.command_setting = str(rospy.get_param('~command', os.getenv('JUNO_TTS_COMMAND', 'auto'))).strip()
        self.coqui_model_name = rospy.get_param('~coqui_model', os.getenv('JUNO_TTS_COQUI_MODEL', 'tts_models/en/ljspeech/vits'))
        self.coqui_speaker = rospy.get_param('~coqui_speaker', os.getenv('JUNO_TTS_COQUI_SPEAKER', 'p226'))
        self.audio_player = rospy.get_param('~audio_player', os.getenv('JUNO_TTS_AUDIO_PLAYER', 'auto')).strip()

        self.engine = None
        self.coqui = None
        self.queue = queue.Queue()
        self.done_pub = rospy.Publisher(self.done_topic, String, queue_size=1, latch=True)
        self._stop_event = threading.Event()
        self._current_process = None
        self._process_lock = threading.Lock()

        if self.backend not in {'auto', 'pyttsx3', 'espeak', 'coqui'}:
            rospy.logwarn('Invalid JUNO_TTS_BACKEND=%s. Falling back to auto.', self.backend)
            self.backend = 'auto'

        if self.backend in {'auto', 'pyttsx3'}:
            self._init_pyttsx3()
        if self.backend == 'coqui':
            self._init_coqui()

        rospy.Subscriber(self.tts_topic, String, self.callback, queue_size=10)
        rospy.Subscriber(self.stop_topic, String, self.stop_callback, queue_size=10)
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

        rospy.loginfo(
            'JUNO TTS node subscribed to %s, stop topic=%s, done topic=%s, backend=%s, rate=%s',
            self.tts_topic,
            self.stop_topic,
            self.done_topic,
            self.backend,
            self.rate,
        )

    def _init_pyttsx3(self):
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
            if self.backend == 'pyttsx3':
                rospy.logerr('pyttsx3 requested but unavailable: %s', exc)
            else:
                rospy.logwarn('pyttsx3 unavailable. Will try espeak/espeak-ng fallback. Details: %s', exc)

    def _init_coqui(self):
        try:
            from TTS.api import TTS

            self.coqui = TTS(self.coqui_model_name)
            rospy.loginfo('Initialized Coqui TTS model %s with speaker %s', self.coqui_model_name, self.coqui_speaker)
        except Exception as exc:
            self.coqui = None
            if self.backend == 'coqui':
                rospy.logerr('Coqui TTS requested but unavailable: %s', exc)
            else:
                rospy.logwarn('Coqui TTS unavailable. Will not use Coqui backend. Details: %s', exc)

    def _select_british_voice(self):
        if self.engine is None:
            return None

        preferred_exact_names = {
            'english (received pronunciation)',
            'english_rp',
            'english-uk',
        }
        preferred_tokens = [
            'en_gb', 'en-gb', 'gb', 'uk', 'british', 'received pronunciation',
            'english_rp', 'english-uk', 'english+f3'
        ]
        requested = self.voice_locale.lower().replace('-', '_')

        for voice in self.engine.getProperty('voices'):
            voice_name = str(getattr(voice, 'name', '')).lower()
            if voice_name in preferred_exact_names:
                return voice.id

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
        rospy.loginfo('Queued JUNO speech from %s: %s', self.tts_topic, text)
        self.queue.put(text)

    def stop_callback(self, _msg):
        """Interrupt the current TTS utterance and discard queued speech."""
        rospy.loginfo('Received JUNO TTS stop request on %s', self.stop_topic)
        self._stop_event.set()
        self._clear_speech_queue()
        try:
            if self.engine is not None:
                self.engine.stop()
        except Exception as exc:
            rospy.logwarn('Could not stop pyttsx3 cleanly: %s', exc)
        with self._process_lock:
            process = self._current_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception as exc:
                rospy.logwarn('Could not terminate espeak process cleanly: %s', exc)
        self.done_pub.publish(String(data='stopped'))

    def _clear_speech_queue(self):
        while True:
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break

    def _worker_loop(self):
        while not rospy.is_shutdown():
            try:
                text = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                self._speak(text)
            except Exception as exc:
                rospy.logerr('JUNO TTS failed for text %r: %s', text, exc)
            finally:
                rospy.sleep(0.05 if self._stop_event.is_set() else self.done_delay)
                self.done_pub.publish(String(data='done'))
                rospy.loginfo('Published %s after TTS attempt', self.done_topic)
                self._stop_event.clear()
                self.queue.task_done()

    def _speak(self, text):
        if self._stop_event.is_set():
            rospy.loginfo('Skipping queued speech because a stop request is active.')
            return

        rospy.loginfo('JUNO says (%s): %s', self.voice_locale, text)

        if self.backend == 'coqui':
            if self.coqui is None:
                raise RuntimeError('Coqui TTS backend selected but model is not initialized.')
            self._speak_with_coqui(text)
            return

        if self.backend in {'auto', 'pyttsx3'} and self.engine is not None:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
                return
            except Exception as exc:
                rospy.logwarn('pyttsx3 failed; trying espeak fallback. Details: %s', exc)
                if self.backend == 'pyttsx3':
                    raise

        if self.backend in {'auto', 'espeak'}:
            self._speak_with_espeak(text)
            return

        raise RuntimeError('No TTS backend available. Install pyttsx3, Coqui TTS, or espeak-ng/espeak.')

    def _candidate_commands(self):
        if self.command_setting and self.command_setting.lower() != 'auto':
            return [self.command_setting]
        return ['espeak-ng', 'espeak']

    def _candidate_audio_players(self):
        if self.audio_player and self.audio_player.lower() != 'auto':
            return [self.audio_player]
        return ['aplay', 'paplay', 'ffplay']

    def _candidate_voices(self):
        requested = self.voice_locale.strip().lower().replace('_', '-')
        voices = []
        if requested:
            voices.append(requested)
        voices.extend(['en-gb', 'en-uk', 'en-rp', 'en'])
        result = []
        for voice in voices:
            if voice not in result:
                result.append(voice)
        return result

    def _speak_with_espeak(self, text):
        last_error = None
        for command in self._candidate_commands():
            if shutil.which(command) is None:
                last_error = 'command not found: {}'.format(command)
                rospy.logwarn('%s', last_error)
                continue

            for voice in self._candidate_voices():
                args = [command, '-v', voice, '-s', str(self.rate), text]
                rospy.loginfo('Trying TTS command: %s -v %s', command, voice)
                process = subprocess.Popen(args)
                with self._process_lock:
                    self._current_process = process
                while process.poll() is None:
                    if self._stop_event.is_set() or rospy.is_shutdown():
                        process.terminate()
                        try:
                            process.wait(timeout=1.0)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        rospy.loginfo('Interrupted TTS command for voice %s', voice)
                        with self._process_lock:
                            self._current_process = None
                        return
                    rospy.sleep(0.05)
                with self._process_lock:
                    self._current_process = None
                if process.returncode == 0:
                    return
                last_error = '{} exited with code {} for voice {}'.format(command, process.returncode, voice)
                rospy.logwarn('%s', last_error)

        raise RuntimeError(last_error or 'No espeak-compatible command available')

    def _speak_with_coqui(self, text):
        if self.coqui is None:
            raise RuntimeError('Coqui TTS is not initialized.')

        audio_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                audio_file = tmp.name

            self.coqui.tts_to_file(text=text, file_path=audio_file, speaker=self.coqui_speaker)
            last_error = None

            for player in self._candidate_audio_players():
                if shutil.which(player) is None:
                    rospy.logwarn('Audio player not found: %s', player)
                    continue

                args = [player, audio_file]
                rospy.loginfo('Playing Coqui TTS output with %s', player)
                process = subprocess.Popen(args)
                with self._process_lock:
                    self._current_process = process

                while process.poll() is None:
                    if self._stop_event.is_set() or rospy.is_shutdown():
                        process.terminate()
                        try:
                            process.wait(timeout=1.0)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        rospy.loginfo('Interrupted Coqui TTS playback')
                        with self._process_lock:
                            self._current_process = None
                        return
                    rospy.sleep(0.05)

                with self._process_lock:
                    self._current_process = None

                if process.returncode == 0:
                    return

                last_error = '%s exited with code %s' % (player, process.returncode)
                rospy.logwarn('%s', last_error)

            raise RuntimeError(last_error or 'No audio playback command available for Coqui TTS')
        finally:
            if audio_file is not None:
                try:
                    os.remove(audio_file)
                except OSError:
                    pass

    def run(self):
        rospy.spin()


if __name__ == '__main__':
    node = JunoTTSNode()
    node.run()
