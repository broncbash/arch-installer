#!/usr/bin/env python3
"""
installer/main.py — Entry point, window manager, stage controller.
"""

import sys
import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

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

def _load_css():
    provider = Gtk.CssProvider()
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    try:
        provider.load_from_path(css_path)
    except GLib.Error as exc:
        print(f"[warn] Could not load CSS: {exc}", file=sys.stderr)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

class InstallerWindow(Gtk.Window):
    """Top-level window that hosts each stage screen."""

    STAGE_CLASSES = [
        ("Welcome",        lambda: WelcomeScreen),
        ("Network Setup",  lambda: NetworkScreen),
        ("Keyboard",       lambda: KeyboardScreen),
        ("Locale",         lambda: LocaleScreen),
        ("Disk",           lambda: DiskSelectScreen),
        ("Partitions",     lambda: PartitionScreen),
        ("Filesystem",     lambda: FilesystemScreen),
        ("Mirrors",        lambda: MirrorScreen),
        ("Packages",       lambda: PackageScreen),
        ("Timezone",       lambda: TimezoneScreen),
        ("System Config",  lambda: SystemConfigScreen),
        ("Users",          lambda: UsersScreen),
        ("Review",         lambda: ReviewScreen),
        ("Install",        lambda: InstallScreen),
        ("Bootloader",     lambda: BootloaderScreen),
        ("Complete",       lambda: CompleteScreen),
    ]

    def __init__(self):
        super().__init__(title="Arch Linux Installer")
        self.set_default_size(1024, 640)
        self.set_resizable(True)
        self.set_size_request(800, 560)  # minimum size
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        self.state = InstallState()
        self._stage_index = 0
        self._return_to_review = False  # set by _jump_to_stage; skips forward on Next

        # Outer vertical box — banner on top, deck below
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(outer)

        # ── Dry-run warning banner ─────────────────────────────────────────────
        if self.state.dry_run:
            banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            banner.get_style_context().add_class("dry-run-banner")
            banner.set_margin_start(0)
            banner.set_margin_end(0)

            icon = Gtk.Label(label="🧪")
            icon.set_margin_start(12)
            banner.pack_start(icon, False, False, 0)

            msg = Gtk.Label(
                label="DRY RUN MODE  —  Nothing will be written to disk. "
                      "To perform a real install, set  dry_run = False  in installer/state.py"
            )
            msg.get_style_context().add_class("dry-run-text")
            msg.set_xalign(0)
            banner.pack_start(msg, True, True, 0)

            outer.pack_start(banner, False, False, 0)

        self._deck = Gtk.Stack()
        self._deck.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self._deck.set_transition_duration(220)
        outer.pack_start(self._deck, True, True, 0)

        self._load_current_stage()
        self.show_all()

    def _load_current_stage(self):
        _label, cls_factory = self.STAGE_CLASSES[self._stage_index]
        cls = cls_factory()
        on_back = self._go_back if self._stage_index > 0 else None
        # ReviewScreen accepts an on_jump callback for direct stage navigation
        if cls is ReviewScreen:
            screen = cls(state=self.state, on_next=self._advance,
                         on_back=on_back, on_jump=self._jump_to_stage)
        else:
            screen = cls(state=self.state, on_next=self._advance, on_back=on_back)
        screen.show_all()
        self._deck.add_named(screen, str(self._stage_index))
        # Defer the switch so GTK can realize the widget first
        GLib.idle_add(self._deck.set_visible_child_name, str(self._stage_index))

    def _advance(self):
        # If the user jumped back from Review to edit something, skip straight
        # back to Review once they click Next on the edited screen.
        review_idx = next(
            i for i, (label, _) in enumerate(self.STAGE_CLASSES)
            if label == "Review"
        )
        if self._return_to_review and self._stage_index < review_idx:
            self._return_to_review = False
            # Clear any stale Review card so it rebuilds with updated state
            child = self._deck.get_child_by_name(str(review_idx))
            if child:
                self._deck.remove(child)
                child.destroy()
            self._stage_index = review_idx
            self._load_current_stage()
            return
        next_idx = self._stage_index + 1
        if next_idx >= len(self.STAGE_CLASSES):
            self._show_end_dialog()
            return
        self._stage_index = next_idx
        self._load_current_stage()

    def _go_back(self):
        if self._stage_index <= 0:
            return
        current_name = str(self._stage_index)
        self._deck.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
        self._stage_index -= 1
        GLib.idle_add(self._deck.set_visible_child_name, str(self._stage_index))
        self._deck.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        # Remove the screen we're leaving so it rebuilds fresh if user returns
        child = self._deck.get_child_by_name(current_name)
        if child:
            self._deck.remove(child)
            child.destroy()

    def _jump_to_stage(self, target_index: int):
        """Jump directly to a specific stage (used by Review screen Edit buttons).
        Sets _return_to_review so the next Next click snaps back to Review."""
        if target_index < 0 or target_index >= len(self.STAGE_CLASSES):
            return
        # Clear the target stage card so it rebuilds with current state
        child = self._deck.get_child_by_name(str(target_index))
        if child:
            self._deck.remove(child)
            child.destroy()
        self._return_to_review = True
        self._deck.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
        self._stage_index = target_index
        self._load_current_stage()
        self._deck.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)

    def _show_end_dialog(self):
        """Fallback — should not be reached now that CompleteScreen is wired in."""
        dlg = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="All stages complete",
        )
        dlg.format_secondary_text("No further stages defined.")
        dlg.run()
        dlg.destroy()

def main():
    _load_css()
    win = InstallerWindow()
    Gtk.main()

if __name__ == "__main__":
    main()
