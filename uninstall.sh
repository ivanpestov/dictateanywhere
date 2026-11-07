#!/usr/bin/env bash
set -u

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
PREFIX="$DATA_HOME/dictateanywhere"

if [[ -z "$PREFIX" || "$PREFIX" == "/" || "$PREFIX" == "$HOME" ]]; then
    printf 'Unsafe installation path; refusing to continue.\n' >&2
    exit 1
fi

pkill -f "$PREFIX/venv/bin/dictateanywhere" 2>/dev/null || true
rm -f "$CONFIG_HOME/autostart/dictateanywhere.desktop"
rm -f "$DATA_HOME/applications/dictateanywhere.desktop"
rm -rf -- "$PREFIX"
printf 'DictateAnywhere has been removed.\n'
