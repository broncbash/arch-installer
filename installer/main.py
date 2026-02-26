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
        ("Install",        lambda: InstallScreen),
        ("Timezone",       lambda: TimezoneScreen),
        ("System Config",  lambda: SystemConfigScreen),
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
        screen = cls(state=self.state, on_next=self._advance, on_back=on_back)
        screen.show_all()
        self._deck.add_named(screen, str(self._stage_index))
        # Defer the switch so GTK can realize the widget first
        GLib.idle_add(self._deck.set_visible_child_name, str(self._stage_index))

    def _advance(self):
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

    def _show_end_dialog(self):
        dlg = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Stage complete",
        )
        dlg.format_secondary_text(
            f"Experience level : {self.state.experience_level}\n"
            f"Keyboard layout  : {self.state.keyboard_layout}\n"
            f"Locale           : {self.state.locale}\n"
            f"Disk             : {self.state.target_disk}\n"
            f"Boot mode        : {self.state.boot_mode}\n"
            f"Partition scheme : {self.state.partition_scheme}\n"
            f"Filesystem       : {self.state.root_filesystem}\n"
            f"Encryption       : {'Yes' if self.state.luks_passphrase else 'No'}\n"
            f"Mirrors          : {len([l for l in self.state.mirrorlist.splitlines() if l.strip().startswith('Server')])} servers\n"
            "(Next stages not yet implemented.)"
        )
        dlg.run()
        dlg.destroy()

def main():
    _load_css()
    win = InstallerWindow()
    Gtk.main()

if __name__ == "__main__":
    main()
