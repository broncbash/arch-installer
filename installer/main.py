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
    """Top-level window that owns the stage stack and drives navigation."""

    # Stage index constants
    STAGE_WELCOME      = 0
    STAGE_NETWORK      = 1
    STAGE_KEYBOARD     = 2
    STAGE_LOCALE       = 3
    STAGE_DISK         = 4
    STAGE_PARTITION    = 5
    STAGE_FILESYSTEM   = 6
    STAGE_MIRRORS      = 7
    STAGE_PACKAGES     = 8
    STAGE_TIMEZONE     = 9
    STAGE_SYSCONFIG    = 10
    STAGE_USERS        = 11
    STAGE_REVIEW       = 12
    STAGE_INSTALL      = 13
    STAGE_BOOTLOADER   = 14
    STAGE_COMPLETE     = 15

    def __init__(self, state: InstallState):
        super().__init__(title="Arch Linux Installer")
        self.state = state
        self._current_stage = 0
        self._return_to_review = False

        # Window setup — maximize to fill the screen (important for VM displays
        # which may be smaller than 1100px). set_default_size is the fallback
        # if the user un-maximizes.
        self.set_default_size(1100, 750)
        self.maximize()
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self._on_close)

        # Icon
        icon = _load_icon()
        if icon:
            self.set_icon(icon)

        # Outer box: dry-run banner + stack
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(outer)

        # Dry-run banner — use no_show_all so show_all() doesn't override hide()
        self._banner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._banner_box.get_style_context().add_class("dry-run-banner")
        self._banner_box.set_no_show_all(True)
        banner_label = Gtk.Label(
            label="⚠  DRY RUN MODE — no changes will be made to your system"
        )
        banner_label.get_style_context().add_class("dry-run-text")
        banner_label.show()
        self._banner_box.pack_start(banner_label, False, False, 6)
        outer.pack_start(self._banner_box, False, False, 0)

        # Stack
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(300)
        outer.pack_start(self._stack, True, True, 0)

        # show_all first, then build stage 0, then apply banner visibility.
        # This order ensures show_all() never fights our explicit hide().
        self.show_all()
        self._build_stage(0)
        self._update_banner()

    # ── Banner ────────────────────────────────────────────────────────────────

    def _update_banner(self):
        """Show or hide the dry-run banner to match state.dry_run."""
        if self.state.dry_run:
            self._banner_box.show_all()
        else:
            self._banner_box.hide()

    # ── Stage building ────────────────────────────────────────────────────────

    def _stage_name(self, index: int) -> str:
        return f"stage_{index}"

    def _build_stage(self, index: int) -> Gtk.Widget:
        """Build the screen widget for the given stage index and add to stack."""
        name = self._stage_name(index)

        # Remove stale card if present
        existing = self._stack.get_child_by_name(name)
        if existing:
            self._stack.remove(existing)

        screen = self._make_screen(index)
        self._stack.add_named(screen, name)
        # Must call show_all() on each new screen — show_all() on the window
        # only covers widgets that existed at that moment.
        screen.show_all()
        return screen

    def _make_screen(self, index: int) -> Gtk.Widget:
        """Instantiate the correct screen class for the given stage."""
        s = self.state

        def on_next():
            self._advance()

        def on_back():
            self._go_back()

        if index == self.STAGE_WELCOME:
            return WelcomeScreen(
                s,
                on_next=on_next,
                on_dry_run_changed=self._update_banner,
            )
        elif index == self.STAGE_NETWORK:
            return NetworkScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_KEYBOARD:
            return KeyboardScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_LOCALE:
            return LocaleScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_DISK:
            return DiskSelectScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_PARTITION:
            return PartitionScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_FILESYSTEM:
            return FilesystemScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_MIRRORS:
            return MirrorScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_PACKAGES:
            return PackageScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_TIMEZONE:
            return TimezoneScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_SYSCONFIG:
            return SystemConfigScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_USERS:
            return UsersScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_REVIEW:
            return ReviewScreen(
                s,
                on_next=on_next,
                on_back=on_back,
                on_jump=self._jump_to_stage,
            )
        elif index == self.STAGE_INSTALL:
            return InstallScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_BOOTLOADER:
            return BootloaderScreen(s, on_next=on_next, on_back=on_back)
        elif index == self.STAGE_COMPLETE:
            return CompleteScreen(s, on_next=on_next, on_back=on_back)
        else:
            raise ValueError(f"Unknown stage index: {index}")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _advance(self):
        """Move forward one stage, or jump back to Review if flagged."""
        if self._return_to_review and self._current_stage < self.STAGE_REVIEW:
            self._return_to_review = False
            # Destroy stale Review card so it rebuilds with fresh state
            stale = self._stack.get_child_by_name(self._stage_name(self.STAGE_REVIEW))
            if stale:
                self._stack.remove(stale)
            self._go_to_stage(self.STAGE_REVIEW)
        else:
            next_stage = self._current_stage + 1
            if next_stage > self.STAGE_COMPLETE:
                return
            self._go_to_stage(next_stage)

        self._update_banner()

    def _go_back(self):
        """Move back one stage."""
        if self._current_stage > 0:
            self._go_to_stage(self._current_stage - 1)

    def _go_to_stage(self, index: int):
        """Switch the stack to the given stage, building it if needed."""
        name = self._stage_name(index)
        if not self._stack.get_child_by_name(name):
            self._build_stage(index)
        self._stack.set_visible_child_name(name)
        self._current_stage = index

    def _jump_to_stage(self, index: int):
        """Called by ReviewScreen edit buttons to jump back to an earlier stage."""
        self._return_to_review = True
        # Rebuild the target stage so it shows current state
        self._build_stage(index)
        self._go_to_stage(index)

    # ── Window close ─────────────────────────────────────────────────────────

    def _on_close(self, *_):
        Gtk.main_quit()
        return False


def main():
    require_root()
    _load_css()
    state = InstallState()
    win = InstallerWindow(state)
    Gtk.main()


if __name__ == "__main__":
    main()
