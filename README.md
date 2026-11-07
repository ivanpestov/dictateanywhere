# DictateAnywhere

DictateAnywhere adds offline push-to-talk dictation to any desktop application.
Press a global hotkey, speak, and press it again: the recognized text is pasted
at the current cursor position. Audio is processed locally with Whisper through
`faster-whisper`; no speech is sent to a cloud service.

The application supports Windows and Linux with an X11 session. The default
language is Russian, the default hotkey is **Windows+W** (Super+W on Linux), and
the default Whisper model is `small`.

## Features

- Local speech recognition; audio never leaves the computer.
- Global push-to-talk hotkey and automatic paste into the active application.
- CPU inference by default, with optional NVIDIA CUDA acceleration.
- Optional sound feedback and automatic Enter after paste.
- System tray menu, status notifications, and a JSON settings file.
- Command-line transcription of existing audio files.

## Linux installation (X11)

Requires Python 3.10 or newer, Tkinter, PortAudio, and `xclip` or `xsel`.
On Linux Mint or Ubuntu, the system prerequisites can be installed with:

```bash
sudo apt install python3-venv python3-tk libportaudio2 xclip
```

Clone and install:

```bash
git clone https://github.com/ivanpestov/dictateanywhere.git
cd dictateanywhere
./install.sh
```

The installer creates an isolated environment in
`~/.local/share/dictateanywhere`, downloads the default model (about 500 MB),
adds an application launcher, and enables login autostart. It does not require
root privileges. The speech model is downloaded once; subsequent recognition
works offline.

Wayland is not supported because global hotkeys and synthetic paste require
X11. Check the current session with `echo $XDG_SESSION_TYPE`.

## Windows installation

Install Python 3.10 or newer, then run these commands in the project directory:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\dictateanywhere.exe
```

CPU inference works without additional setup. CUDA inference requires a
compatible NVIDIA driver plus the CUDA libraries required by `faster-whisper`.

## Usage

1. Place the text cursor in any application.
2. Press **Windows+W**. A red status banner indicates active recording.
3. Speak.
4. Press **Windows+W** again. After transcription, the text is pasted at the
   cursor.
5. Review the text before sending it.

The tray icon can also start or stop dictation, open the settings file, and
quit the application.

## Settings

On Linux, settings are stored in:

```text
~/.local/share/dictateanywhere/config.json
```

On Windows, the file is located at:

```text
%LOCALAPPDATA%\DictateAnywhere\config.json
```

| Setting | Default | Description |
|---|---|---|
| `hotkey` | `"win+w"` | Global shortcut, such as `f8` or `ctrl+alt+space` |
| `language` | `"ru"` | Whisper language code |
| `model` | `"small"` | Whisper model name supported by faster-whisper |
| `device` | `"auto"` | `auto`, `cpu`, or `cuda` |
| `cpu_threads` | `4` | Number of CPU inference threads |
| `beep` | `true` | Play tones when recording starts and stops |
| `auto_send` | `false` | Press Enter after pasting text |
| `prompt` | Russian prompt | Optional Whisper initial prompt |

Restart the application after changing settings. Pasting replaces the current
clipboard text. Enable `auto_send` only when immediate submission is desired.

## Command-line use

Download and initialize the configured model:

```bash
dictateanywhere --download
```

Transcribe an existing audio file (requires FFmpeg):

```bash
dictateanywhere --transcribe recording.wav
```

## Development setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/dictateanywhere
```

Application data, models, and logs are kept outside the source tree. Set the
`DICTATEANYWHERE_HOME` environment variable to override the data directory.

## Uninstall

On Linux, run from the source directory:

```bash
./uninstall.sh
```

This stops the installed application and removes its launchers, virtual
environment, downloaded models, settings, and logs.

On Windows, close the application and remove the virtual environment and the
`%LOCALAPPDATA%\DictateAnywhere` directory.

## Privacy

Audio recording and transcription happen locally. Internet access is needed to
install Python dependencies and download the Whisper model. Dictation itself
does not make network requests.

## License

Released under the [MIT License](LICENSE).
