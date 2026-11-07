import logging
import queue
import sys
import threading
import tkinter as tk


class StatusBanner:
    COLORS = {
        "info": "#263445",
        "listening": "#9F2833",
        "working": "#285A8E",
        "ready": "#286A45",
        "error": "#8C2F39",
    }

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        if sys.platform.startswith("linux"):
            try:
                self.root.attributes("-type", "splash")
            except tk.TclError:
                pass
        self._label = tk.Label(
            self.root,
            fg="white",
            bg=self.COLORS["info"],
            font=("TkDefaultFont", 12, "bold"),
            padx=20,
            pady=10,
        )
        self._label.pack()
        self._events = queue.SimpleQueue()
        self._hide_job = None
        self.root.after(60, self._consume_events)

    def show(self, message: str, tone: str = "info", timeout=None) -> None:
        self._events.put(("show", message, tone, timeout))

    def hide(self) -> None:
        self._events.put(("hide",))

    def close(self) -> None:
        self._events.put(("close",))

    def run(self) -> None:
        self.root.mainloop()

    def _cancel_hide(self) -> None:
        if self._hide_job is not None:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None

    def _consume_events(self) -> None:
        try:
            while True:
                event = self._events.get_nowait()
                action = event[0]
                if action == "close":
                    self._cancel_hide()
                    self.root.destroy()
                    return
                if action == "hide":
                    self._cancel_hide()
                    self.root.withdraw()
                    continue
                _, message, tone, timeout = event
                self._present(message, tone, timeout)
        except queue.Empty:
            pass
        self.root.after(60, self._consume_events)

    def _present(self, message: str, tone: str, timeout) -> None:
        self._cancel_hide()
        color = self.COLORS.get(tone, self.COLORS["info"])
        self._label.configure(text=message, bg=color)
        self.root.configure(bg=color)
        self.root.deiconify()
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = self.root.winfo_screenheight() - height - 80
        self.root.geometry(f"+{x}+{y}")
        if timeout is not None:
            self._hide_job = self.root.after(int(timeout * 1000), self.root.withdraw)


class TrayIcon:
    def __init__(self, on_toggle, on_settings, on_quit) -> None:
        self.on_toggle = on_toggle
        self.on_settings = on_settings
        self.on_quit = on_quit
        self._icon = None
        self._thread = None

    def start(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw

            image = Image.new("RGBA", (64, 64), "#315F8C")
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((25, 9, 39, 39), radius=7, fill="white")
            draw.arc((17, 20, 47, 49), start=0, end=180, fill="white", width=4)
            draw.line((32, 48, 32, 56), fill="white", width=4)
            draw.line((23, 56, 41, 56), fill="white", width=4)
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Start / stop dictation",
                    lambda *_: self.on_toggle(),
                    default=True,
                ),
                pystray.MenuItem("Open settings", lambda *_: self.on_settings()),
                pystray.MenuItem("Quit", lambda *_: self.on_quit()),
            )
            self._icon = pystray.Icon("dictateanywhere", image, "DictateAnywhere", menu)
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()
        except Exception:
            logging.exception("Could not start the tray icon")
            self._icon = None

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
            self._icon = None
