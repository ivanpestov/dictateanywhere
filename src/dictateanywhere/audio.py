import logging
import threading

import numpy as np

SAMPLE_RATE = 16000


class MicrophoneRecorder:
    def __init__(self) -> None:
        self._stream = None
        self._chunks = []
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        import sounddevice as sd

        if self.active:
            raise RuntimeError("Recording is already active")
        with self._lock:
            self._chunks = []

        def capture(indata, frames, time_info, status) -> None:
            if status:
                logging.warning("Audio capture: %s", status)
            with self._lock:
                self._chunks.append(indata.reshape(-1).copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=capture,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.empty(0, dtype=np.float32)
        stream, self._stream = self._stream, None
        try:
            stream.stop()
            stream.close()
        finally:
            with self._lock:
                chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.empty(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32, copy=False)


class TonePlayer:
    @staticmethod
    def play(frequency: int, duration: float = 0.08) -> None:
        def worker() -> None:
            try:
                import sounddevice as sd

                count = int(SAMPLE_RATE * duration)
                timeline = np.arange(count, dtype=np.float32) / SAMPLE_RATE
                wave = 0.06 * np.sin(2 * np.pi * frequency * timeline)
                sd.play(wave, samplerate=SAMPLE_RATE, blocking=True)
            except Exception:
                logging.exception("Could not play feedback tone")

        threading.Thread(target=worker, daemon=True).start()
