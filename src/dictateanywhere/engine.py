import numpy as np

from .config import Settings, application_dir


class SpeechEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None

    def load(self) -> str:
        from faster_whisper import WhisperModel

        device = self.settings.device
        if device == "auto":
            import ctranslate2

            try:
                device = "cuda" if ctranslate2.get_cuda_device_count() else "cpu"
            except Exception:
                device = "cpu"
        if device not in {"cpu", "cuda"}:
            raise ValueError("device must be 'auto', 'cpu', or 'cuda'")

        options = {
            "device": device,
            "compute_type": "float16" if device == "cuda" else "int8",
            "download_root": str(application_dir() / "models"),
        }
        if device == "cpu":
            options["cpu_threads"] = int(self.settings.cpu_threads)
        self._model = WhisperModel(self.settings.model, **options)
        return device

    def transcribe(self, audio: np.ndarray) -> str:
        if self._model is None:
            raise RuntimeError("The speech model has not been loaded")
        segments, _ = self._model.transcribe(
            audio,
            language=self.settings.language,
            beam_size=3,
            vad_filter=True,
            initial_prompt=self.settings.prompt or None,
            condition_on_previous_text=False,
        )
        return " ".join(part.text.strip() for part in segments).strip()
