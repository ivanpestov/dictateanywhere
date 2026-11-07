import logging
import threading

from .audio import MicrophoneRecorder, SAMPLE_RATE, TonePlayer
from .config import Settings
from .engine import SpeechEngine
from .keyboard import TextInserter


class DictationController:
    def __init__(self, settings: Settings, banner) -> None:
        self.settings = settings
        self.banner = banner
        self.recorder = MicrophoneRecorder()
        self.engine = SpeechEngine(settings)
        self._ready = False
        self._processing = False
        self._lock = threading.Lock()

    def load(self) -> None:
        self.banner.show("Loading the speech model…", "working")
        try:
            device = self.engine.load()
            self._ready = True
            logging.info("Speech model loaded on %s", device)
            self.banner.show(
                f"Ready — press {self.settings.hotkey.upper()} ({device})",
                "ready",
                timeout=4,
            )
        except Exception:
            logging.exception("Could not load the speech model")
            self.banner.show("Model loading failed. See the log file.", "error", 8)

    def toggle(self) -> None:
        logging.info("Dictation toggle requested")
        with self._lock:
            if self._processing:
                return
            if not self._ready:
                self.banner.show("The speech model is still loading…", "info", 2)
                return
            if not self.recorder.active:
                try:
                    self.recorder.start()
                except Exception:
                    logging.exception("Could not start audio capture")
                    self.banner.show("Microphone is unavailable.", "error", 4)
                    return
                logging.info("Recording started")
                self._feedback(880)
                self.banner.show(
                    f"Listening… press {self.settings.hotkey.upper()} to finish",
                    "listening",
                )
                return
            self._processing = True

        threading.Thread(target=self._finish_recording, daemon=True).start()

    def _finish_recording(self) -> None:
        try:
            audio = self.recorder.stop()
            logging.info("Recording stopped after %.2f seconds", audio.size / SAMPLE_RATE)
            self._feedback(660)
            if audio.size < SAMPLE_RATE * 0.35:
                self.banner.show("The recording is too short.", "info", 2)
                return
            self.banner.show("Transcribing…", "working")
            text = self.engine.transcribe(audio)
            if not text:
                self.banner.show("No speech detected.", "info", 2)
                return
            TextInserter.insert(text, send=self.settings.auto_send)
            logging.info("Sent paste for %s recognized characters", len(text))
            self.banner.show("Paste sent to the active window.", "ready", 1.5)
        except Exception:
            logging.exception("Could not complete dictation")
            self.banner.show("Dictation failed. See the log file.", "error", 5)
        finally:
            self._processing = False

    def _feedback(self, frequency: int) -> None:
        if self.settings.beep:
            TonePlayer.play(frequency)

    def shutdown(self) -> None:
        if self.recorder.active:
            self.recorder.stop()
