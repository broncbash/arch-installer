#!/usr/bin/env python3
"""
installer/main.py — Entry point, window manager, stage controller.
"""

import sys
import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from installer.privilege import require_root
from installer.state import InstallState
from installer.ui.welcome import WelcomeScreen
from installer.ui.network import NetworkScreen
from installer.ui.keyboard import KeyboardScreen
from installer.ui.locale_screen import LocaleScreen
from installer.ui.disk_select import DiskSelectScreen
from installer.ui.partition import PartitionScreen
from installer.ui.filesystem import FilesystemScreen
from installer.ui.mirrors import MirrorScreen
from installer.ui.packages import PackageScreen
from installer.ui.install import InstallScreen
from installer.ui.timezone import TimezoneScreen
from installer.ui.system_config import SystemConfigScreen
from installer.ui.users import UsersScreen
from installer.ui.bootloader import BootloaderScreen
from installer.ui.review import ReviewScreen
from installer.ui.complete import CompleteScreen

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _load_css():
    provider = Gtk.CssProvider()
    css_path = os.path.join(ASSETS_DIR, "style.css")
    try:
        provider.load_from_path(css_path)
    except GLib.Error as exc:
        print(f"[warn] Could not load CSS: {exc}", file=sys.stderr)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def _load_icon() -> GdkPixbuf.Pixbuf | None:
    """Load the installer icon from assets. Returns None if not found."""
    icon_path = os.path.join(ASSETS_DIR, "installer.png")
    if not os.path.exists(icon_path):
        print(f"[warn] Icon not found at {icon_path}", file=sys.stderr)
        return None
    try:
        return GdkPixbuf.Pixbuf.new_from_file(icon_path)
    except Exception as exc:
        print(f"[warn] Could not load icon: {exc}", file=sys.stderr)
        return None


class InstallerWindow(Gtk.Window):
    """Top-lev
