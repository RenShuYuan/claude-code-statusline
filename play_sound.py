#!/usr/bin/env python3
"""Cross-platform notification sound player.

Usage: play_sound.py [path_to_wav]
Default path: ~/.claude/sounds/notify_loud.wav

Returns exit code 0 on success, 1 on failure with stderr message.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys


DEFAULT_WAV = os.path.expanduser("~/.claude/sounds/notify_loud.wav")


def play_windows(path: str) -> int:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"(New-Object Media.SoundPlayer '{path}').PlaySync()",
    ]
    return subprocess.run(cmd, capture_output=True).returncode


def play_macos(path: str) -> int:
    return subprocess.run(["afplay", path], capture_output=True).returncode


def play_linux(path: str) -> int:
    for player in ("paplay", "aplay", "play"):
        if shutil.which(player):
            return subprocess.run([player, path], capture_output=True).returncode
    print(
        "no audio player found (tried paplay, aplay, play); "
        "install pulseaudio-utils, alsa-utils, or sox",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a WAV file cross-platform.")
    parser.add_argument("path", nargs="?", default=DEFAULT_WAV)
    args = parser.parse_args()

    path = os.path.expanduser(args.path)
    if not os.path.isfile(path):
        print(f"sound file not found: {path}", file=sys.stderr)
        return 1

    system = platform.system()
    if system == "Windows":
        return play_windows(path)
    if system == "Darwin":
        return play_macos(path)
    if system == "Linux":
        return play_linux(path)
    print(f"unsupported platform: {system}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
