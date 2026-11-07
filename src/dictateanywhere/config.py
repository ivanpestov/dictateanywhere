import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class Settings:
    hotkey: str = "f2"
    language: str = "ru"
    model: str = "small"
    device: str = "auto"
    cpu_threads: int = 4
    beep: bool = True
    auto_send: bool = False
    prompt: str = "Это русская голосовая заметка с правильной пунктуацией."


def application_dir() -> Path:
    override = os.environ.get("DICTATEANYWHERE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "DictateAnywhere"
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "dictateanywhere"


def settings_path() -> Path:
    return application_dir() / "config.json"


def save_settings(settings: Settings) -> None:
    directory = application_dir()
    directory.mkdir(parents=True, exist_ok=True)
    with settings_path().open("w", encoding="utf-8") as stream:
        json.dump(asdict(settings), stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def load_settings() -> Settings:
    settings = Settings()
    path = settings_path()
    if not path.exists():
        save_settings(settings)
        return settings

    with path.open(encoding="utf-8-sig") as stream:
        values = json.load(stream)
    known = {item.name for item in fields(Settings)}
    for name, value in values.items():
        if name in known:
            setattr(settings, name, value)
    return settings
