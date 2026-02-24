#!/usr/bin/env python3
"""
installer/main.py — Entry point, window manager, stage controller.

Launches Stage 0 (Welcome) for now. Additional stages slot in via
STAGES list as they are implemented.
"""

import sys
import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

# Local imports
from installer.state import InstallState
from installer.ui.welcome import WelcomeScreen

# ── CSS loading ───────────────────────────────────────────────────────────

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


# ── Main window ───────────────────────────────────────────────────────────

class InstallerWindow(Gtk.Window):
    """Top-level window that hosts each stage screen."""

    # Ordered list of (label, screen_class) — add entries as stages are built.
    # Screen class is imported lazily so missing files don't break the app.
    STAGE_CLASSES = [
        ("Welcome",   lambda: WelcomeScreen),
        # ("Keyboard",  lambda: KeyboardScreen),  # Stage 1 — TBD
        # ...
    ]

    def __init__(self):
        super().__init__(title="Arch Linux Installer")
        self.set_default_size(900, 620)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        self.state = InstallState()
        self._stage_index = 0

        # Outer container — swap screens here
        self._deck = Gtk.Stack()
        self._deck.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self._deck.set_transition_duration(220)
        self.add(self._deck)

        self._load_current_stage()
        self.show_all()

    # ---------------------------------------------------------------- stages

    def _load_current_stage(self):
        """Instantiate the current stage screen and show it."""
        _label, cls_factory = self.STAGE_CLASSES[self._stage_index]
        cls = cls_factory()
        screen = cls(state=self.state, on_next=self._advance)
        self._deck.add_named(screen, str(self._stage_index))
        self._deck.set_visible_child_name(str(self._stage_index))
        screen.show_all()

    def _advance(self):
        """Called by each screen when the user clicks Continue."""
        next_idx = self._stage_index + 1
        if next_idx >= len(self.STAGE_CLASSES):
            # All implemented stages done — placeholder
            self._show_end_dialog()
            return
        self._stage_index = next_idx
        self._load_current_stage()

    def _show_end_dialog(self):
        dlg = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Stage complete",
        )
        dlg.format_secondary_text(
            f"Experience level saved: {self.state.experience_level}\n"
            "(Next stages not yet implemented.)"
        )
        dlg.run()
        dlg.destroy()


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    _load_css()
    win = InstallerWindow()
    Gtk.main()


if __name__ == "__main__":
    main()
