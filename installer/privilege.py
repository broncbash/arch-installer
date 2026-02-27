"""
installer/privilege.py — Root privilege check.

Called once at startup. If the process is not running as root, prints a
clear error message and exits. On a live ISO the installer is launched as
root automatically, so this should never fire in normal use.
"""

import os
import sys


def require_root() -> None:
    """Exit with a helpful message if not running as root."""
    if os.getuid() == 0:
        return  # all good

    print(
        "\n"
        "  ✗  Arch Installer must be run as root.\n"
        "\n"
        "     Please relaunch with:\n"
        "\n"
        "       sudo arch-installer\n"
        "     or\n"
        "       sudo python -m installer.main\n"
        "\n",
        file=sys.stderr,
    )
    sys.exit(1)
