import argparse
import logging
import os
import subprocess
import sys
import threading

from . import __version__
from .config import application_dir, load_settings, settings_path
from .engine import SpeechEngine
from .instance import InstanceLock


def configure_logging() -> None:
    directory = application_dir()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=directory / "dictateanywhere.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def decode_audio(path: str):
    import numpy as np

    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            path,
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(result.stdout, dtype=np.float32)


def open_settings() -> None:
    path = settings_path()
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(
            ["xdg-open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def show_already_running() -> None:
    message = "DictateAnywhere is already running."
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("DictateAnywhere", message)
        root.destroy()
    except Exception:
        print(message)


def run_gui(settings) -> int:
    if (
        sys.platform.startswith("linux")
        and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    ):
        print("Linux Wayland sessions are not supported; log in with X11.", file=sys.stderr)
        return 2

    from .app import DictationController
    from .keyboard import HotkeyService
    from .ui import StatusBanner, TrayIcon

    guard = InstanceLock(application_dir() / "instance.lock")
    if not guard.acquire():
        show_already_running()
        return 0

    banner = StatusBanner()
    controller = DictationController(settings, banner)
    hotkeys = None
    tray = None

    def shutdown() -> None:
        if hotkeys is not None:
            hotkeys.stop()
        if tray is not None:
            tray.stop()
        controller.shutdown()
        banner.close()

    try:
        hotkeys = HotkeyService(settings.hotkey, controller.toggle)
        tray = TrayIcon(controller.toggle, open_settings, shutdown)
        hotkeys.start()
        tray.start()
        logging.info("Application started with hotkey %s", settings.hotkey)
        threading.Thread(target=controller.load, daemon=True).start()
        banner.run()
    finally:
        shutdown()
        guard.release()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dictateanywhere",
        description="Offline push-to-talk dictation for any application.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="download and initialize the configured speech model",
    )
    parser.add_argument("--transcribe", metavar="AUDIO", help="transcribe an audio file")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        configure_logging()
        if args.download:
            device = SpeechEngine(settings).load()
            print(f"Model {settings.model!r} is ready on {device}.")
            return 0
        if args.transcribe:
            audio = decode_audio(args.transcribe)
            engine = SpeechEngine(settings)
            engine.load()
            print(engine.transcribe(audio))
            return 0
        return run_gui(settings)
    except Exception as error:
        logging.exception("Application error")
        print(f"DictateAnywhere: {error}", file=sys.stderr)
        return 1
