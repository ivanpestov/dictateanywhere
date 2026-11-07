import logging
import re
import subprocess
import sys
import time

_TERMINAL_MARKERS = (
    "terminal",
    "ghostty",
    "xterm",
    "kitty",
    "alacritty",
    "konsole",
    "wezterm",
    "tilix",
    "terminator",
    "urxvt",
    "rxvt",
    "kgx",
    "hyper",
)


def _active_window_details():
    if not sys.platform.startswith("linux"):
        return None
    try:
        from Xlib import X, display

        connection = display.Display()
        try:
            root = connection.screen().root
            active = root.get_full_property(
                connection.intern_atom("_NET_ACTIVE_WINDOW"),
                X.AnyPropertyType,
            )
            if active is None or not len(active.value):
                return None
            window = connection.create_resource_object("window", active.value[0])
            names = [name.lower() for name in (window.get_wm_class() or ())]
            hints = {}
            for name in ("_GTK_UNIQUE_BUS_NAME", "_GTK_WINDOW_OBJECT_PATH"):
                value = window.get_full_property(
                    connection.intern_atom(name), X.AnyPropertyType
                )
                if value is not None:
                    hints[name] = value.value.decode()
            return names, hints
        finally:
            connection.close()
    except Exception:
        return None


def _terminal_window_active() -> bool:
    details = _active_window_details()
    if details is None:
        return False
    names, _ = details
    return any(
        name == "st" or any(marker in name for marker in _TERMINAL_MARKERS)
        for name in names
    )


def _paste_ghostty() -> bool:
    details = _active_window_details()
    if details is None:
        return False
    names, hints = details
    if not any("ghostty" in name for name in names):
        return False
    bus_name = hints.get("_GTK_UNIQUE_BUS_NAME")
    object_path = hints.get("_GTK_WINDOW_OBJECT_PATH")
    if not bus_name or not object_path:
        return False
    try:
        subprocess.run(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                bus_name,
                "--object-path",
                object_path,
                "--method",
                "org.gtk.Actions.Activate",
                "paste",
                "[]",
                "{}",
            ],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        logging.exception("Could not activate the Ghostty paste action")
        return False
    return True


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


_X11_KEYSYMS = {
    "<space>": "space",
    "<enter>": "Return",
    "<tab>": "Tab",
    "<backspace>": "BackSpace",
    "<esc>": "Escape",
    "<insert>": "Insert",
    "<delete>": "Delete",
    "<home>": "Home",
    "<end>": "End",
    "<page_up>": "Page_Up",
    "<page_down>": "Page_Down",
    "<up>": "Up",
    "<down>": "Down",
    "<left>": "Left",
    "<right>": "Right",
}


class _X11HotkeyGrab:
    def __init__(self, shortcut: str) -> None:
        self._shortcut = shortcut
        self._connection = None
        self._keycode = None
        self._modifiers = []

    def start(self) -> None:
        if self._connection is not None:
            return
        from Xlib import X, XK, display

        modifier_masks = {
            "<alt>": X.Mod1Mask,
            "<ctrl>": X.ControlMask,
            "<shift>": X.ShiftMask,
            "<cmd>": X.Mod4Mask,
        }
        tokens = normalize_shortcut(self._shortcut).split("+")
        modifiers = 0
        for token in tokens[:-1]:
            if token not in modifier_masks:
                raise ValueError(f"Invalid hotkey modifier: {token!r}")
            modifiers |= modifier_masks[token]
        key = tokens[-1]
        if len(key) == 1:
            keysym = ord(key)
            if keysym >= 0x100:
                keysym |= 0x01000000
        else:
            key_name = _X11_KEYSYMS.get(key)
            if key_name is None and re.fullmatch(r"<f\d{1,2}>", key):
                key_name = key[1:-1].upper()
            keysym = XK.string_to_keysym(key_name) if key_name else 0
        if not keysym:
            raise ValueError(f"Unsupported X11 hotkey: {self._shortcut!r}")

        connection = display.Display()
        try:
            keycode = connection.keysym_to_keycode(keysym)
            if not keycode:
                raise ValueError(f"Unsupported X11 hotkey: {self._shortcut!r}")
            variants = [
                modifiers | caps | num
                for caps in (0, X.LockMask)
                for num in (0, X.Mod2Mask)
            ]
            root = connection.screen().root
            for variant in variants:
                root.grab_key(
                    keycode,
                    variant,
                    False,
                    X.GrabModeAsync,
                    X.GrabModeAsync,
                )
            connection.sync()
        except Exception:
            connection.close()
            raise

        self._connection = connection
        self._keycode = keycode
        self._modifiers = variants

    def drain(self) -> None:
        if self._connection is None:
            return
        self._connection.sync()
        while self._connection.pending_events():
            self._connection.next_event()

    def stop(self) -> None:
        if self._connection is None:
            return
        try:
            root = self._connection.screen().root
            for modifiers in self._modifiers:
                root.ungrab_key(self._keycode, modifiers)
            self._connection.sync()
        finally:
            self._connection.close()
            self._connection = None
            self._keycode = None
            self._modifiers = []


class HotkeyService:
    def __init__(self, shortcut: str, callback) -> None:
        from pynput import keyboard

        self._grab = (
            _X11HotkeyGrab(shortcut) if sys.platform.startswith("linux") else None
        )

        def activated() -> None:
            try:
                callback()
            finally:
                if self._grab is not None:
                    self._grab.drain()

        keys = keyboard.HotKey.parse(normalize_shortcut(shortcut))
        self._hotkey = keyboard.HotKey(keys, activated)
        self._listener = None
        self._keyboard = keyboard

    def start(self) -> None:
        keyboard = self._keyboard

        def pressed(key) -> None:
            self._hotkey.press(self._listener.canonical(key))

        def released(key) -> None:
            self._hotkey.release(self._listener.canonical(key))

        try:
            self._listener = keyboard.Listener(on_press=pressed, on_release=released)
            self._listener.start()
            self._listener.wait()
            if self._grab is not None:
                self._grab.start()
        except Exception:
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
            if self._grab is not None:
                self._grab.stop()
            raise

    def stop(self) -> None:
        try:
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
        finally:
            if self._grab is not None:
                self._grab.stop()


class TextInserter:
    @staticmethod
    def insert(text: str, send: bool = False) -> None:
        import pyperclip
        from pynput.keyboard import Controller, Key

        pyperclip.copy(text)
        keyboard = Controller()
        if not _paste_ghostty():
            modifiers = [Key.ctrl]
            if _terminal_window_active():
                modifiers.append(Key.shift)
            time.sleep(0.08)
            with keyboard.pressed(*modifiers):
                keyboard.press("v")
                keyboard.release("v")
        if send:
            time.sleep(0.12)
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
