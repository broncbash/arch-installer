"""
installer/backend/keyboard.py
------------------------------
Backend functions for Stage 2 — Keyboard Layout.

Wraps two system tools:
  - localectl  : lists available keymaps and reads the current one
  - loadkeys   : temporarily applies a keymap in the live environment
                 (the permanent setting is written during chroot at install time)
"""

import subprocess
import logging

log = logging.getLogger(__name__)


def list_keymaps() -> list:
    """
    Return a sorted list of all available console keymaps.

    Runs: localectl list-keymaps
    Falls back to a short built-in list if localectl is unavailable
    (shouldn't happen on an Arch live ISO, but good to be safe).
    """
    try:
        result = subprocess.run(
            ["localectl", "list-keymaps"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            keymaps = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if keymaps:
                return sorted(keymaps)
    except FileNotFoundError:
        log.warning("localectl not found — using built-in keymap list")
    except subprocess.TimeoutExpired:
        log.warning("localectl timed out — using built-in keymap list")

    # Fallback: a small list of the most common keymaps
    return sorted([
        "us", "uk", "de", "de-latin1", "fr", "fr-latin1",
        "es", "it", "pt-latin1", "ru", "pl", "nl", "sv-latin1",
        "fi", "da-latin1", "no-latin1", "hu", "cz", "sk-qwerty",
        "jp106", "kr", "br-abnt2", "dvorak", "colemak",
    ])


def apply_keymap(keymap: str) -> tuple:
    """
    Temporarily apply a keymap in the live environment using loadkeys.

    This is just a preview — it does NOT persist across reboots.
    The permanent setting is written by localectl set-keymap inside
    the arch-chroot during the actual install.

    Returns a (success: bool, message: str) tuple, following the
    project convention for all backend functions.
    """
    try:
        result = subprocess.run(
            ["loadkeys", keymap],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            log.info("Keymap applied temporarily: %s", keymap)
            return True, f"Keymap '{keymap}' applied. Type below to test it."
        else:
            err = result.stderr.strip() or result.stdout.strip()
            log.warning("loadkeys failed for '%s': %s", keymap, err)

            # This error means we're running inside a graphical session
            # (X11 or Wayland) rather than a bare TTY console.
            # loadkeys only works on a real TTY — which is exactly where the
            # Arch live ISO runs, so this will work fine during an actual install.
            # During development/testing in a desktop environment, we just
            # acknowledge the selection without the live preview.
            if "file descriptor" in err or "console" in err.lower():
                return True, (
                    f"'{keymap}' selected \u2713  \u2014 live preview isn't available "
                    "in a graphical session, but your choice will be applied "
                    "correctly during installation."
                )

            return False, f"Could not apply keymap: {err}"

    except FileNotFoundError:
        return False, "loadkeys not found — cannot preview keymap in this environment."
    except subprocess.TimeoutExpired:
        return False, "loadkeys timed out."


def get_current_keymap() -> str:
    """
    Read the currently active console keymap from localectl status.
    Returns 'us' as a safe default if it can't be determined.

    This is used to pre-select the right entry in the list when
    the screen first loads.
    """
    try:
        result = subprocess.run(
            ["localectl", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            # The line looks like:  "   VC Keymap: us"
            if "VC Keymap:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    km = parts[1].strip()
                    if km and km != "n/a":
                        return km
    except Exception as e:
        log.debug("Could not detect current keymap: %s", e)

    return "us"   # safe default
