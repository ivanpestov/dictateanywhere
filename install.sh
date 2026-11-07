#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
PREFIX="$DATA_HOME/dictateanywhere"
SYSTEM_PYTHON="${PYTHON:-python3}"

printf '\nDictateAnywhere installer for Linux/X11\n\n'

if ! command -v "$SYSTEM_PYTHON" >/dev/null 2>&1; then
    printf 'Python 3 is required: sudo apt install python3\n' >&2
    exit 1
fi
if ! "$SYSTEM_PYTHON" -c 'import tkinter' >/dev/null 2>&1; then
    printf 'Tkinter is required: sudo apt install python3-tk\n' >&2
    exit 1
fi
if ! command -v xclip >/dev/null 2>&1 && ! command -v xsel >/dev/null 2>&1; then
    printf 'A clipboard helper is required: sudo apt install xclip\n' >&2
    exit 1
fi

"$SYSTEM_PYTHON" -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/python" -m pip install --disable-pip-version-check \
    --upgrade "$SOURCE_DIR"
if ! "$PREFIX/venv/bin/python" -c 'import sounddevice' >/dev/null 2>&1; then
    printf 'PortAudio is required: sudo apt install libportaudio2\n' >&2
    exit 1
fi

printf 'Preparing the default Whisper model (about 500 MB)…\n'
"$PREFIX/venv/bin/dictateanywhere" --download

mkdir -p "$CONFIG_HOME/autostart" "$DATA_HOME/applications"
cat > "$CONFIG_HOME/autostart/dictateanywhere.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DictateAnywhere
Comment=Offline push-to-talk dictation
Exec="$PREFIX/venv/bin/dictateanywhere"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
cat > "$DATA_HOME/applications/dictateanywhere.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DictateAnywhere
Comment=Offline push-to-talk dictation
Exec="$PREFIX/venv/bin/dictateanywhere"
Icon=audio-input-microphone
Terminal=false
Categories=Utility;Accessibility;
EOF

nohup "$PREFIX/venv/bin/dictateanywhere" >/dev/null 2>&1 &
printf '\nInstallation complete. Press Windows+W to start and stop dictation.\n'
printf 'Settings: %s/config.json\n' "$PREFIX"
printf 'To uninstall, run ./uninstall.sh from the source tree.\n'
