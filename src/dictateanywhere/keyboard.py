import re
import time

_KEY_NAMES = {
    "alt": "<alt>",
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "shift": "<shift>",
    "win": "<cmd>",
    "super": "<cmd>",
    "cmd": "<cmd>",
    "space": "<space>",
    "enter": "<enter>",
    "tab": "<tab>",
    "backspace": "<backspace>",
    "esc": "<esc>",
    "escape": "<esc>",
    "insert": "<insert>",
    "delete": "<delete>",
    "home": "<home>",
    "end": "<end>",
    "pageup": "<page_up>",
    "pagedown": "<page_down>",
    "up": "<up>",
    "down": "<down>",
    "left": "<left>",
    "right": "<right>",
}


def normalize_shortcut(value: str) -> str:
    result = []
    for token in value.lower().replace(" ", "").split("+"):
        if not token:
            raise ValueError(f"Invalid hotkey: {value!r}")
        if token in _KEY_NAMES:
            token = _KEY_NAMES[token]
        elif re.fullmatch(r"f\d{1,2}", token):
            token = f"<{token}>"
        elif len(token) != 1:
            raise ValueError(f"Unsupported key in hotkey: {token!r}")
        result.append(token)
    return "+".join(result)


class HotkeyService:
    def __init__(self, shortcut: str, callback) -> None:
        from pynput import keyboard

        keys = keyboard.HotKey.parse(normalize_shortcut(shortcut))
        self._hotkey = keyboard.HotKey(keys, callback)
        self._listener = None
        self._keyboard = keyboard

    def start(self) -> None:
        keyboard = self._keyboard

        def pressed(key) -> None:
            self._hotkey.press(self._listener.canonical(key))

        def released(key) -> None:
            self._hotkey.release(self._listener.canonical(key))

        self._listener = keyboard.Listener(on_press=pressed, on_release=released)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None


class TextInserter:
    @staticmethod
    def insert(text: str, send: bool = False) -> None:
        import pyperclip
        from pynput.keyboard import Controller, Key

        pyperclip.copy(text)
        keyboard = Controller()
        time.sleep(0.08)
        with keyboard.pressed(Key.ctrl):
            keyboard.press("v")
            keyboard.release("v")
        if send:
            time.sleep(0.12)
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
