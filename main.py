#!/usr/bin/env python3
"""
installer/main.py
-----------------
Entry point for the Arch Installer.
Creates the main GTK window and manages navigation between stages.
Must be run as root (checks at startup).
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import os
import sys
import logging

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/arch-installer.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger('arch-installer')

# ── Path setup ────────────────────────────────────────────────────────────────
INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(INSTALLER_DIR, 'assets')
sys.path.insert(0, os.path.dirname(INSTALLER_DIR))

from installer.state import InstallState


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = b"""
* {
    font-family: 'Cantarell', 'Noto Sans', 'DejaVu Sans', sans-serif;
}

window {
    background-color: #0d1117;
    color: #e6edf3;
}

/* ── Header bar ── */
.main-header {
    background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
    border-bottom: 1px solid #21262d;
    padding: 0;
}

.header-title {
    font-size: 20px;
    font-weight: 600;
    color: #58a6ff;
}

.header-subtitle {
    font-size: 11px;
    color: #8b949e;
}

.stage-indicator {
    font-family: 'JetBrains Mono', 'Source Code Pro', 'Noto Mono', monospace;
    font-size: 11px;
    color: #8b949e;
    padding: 4px 12px;
    border-radius: 12px;
    background-color: #21262d;
    border: 1px solid #30363d;
}

/* ── Progress steps ── */
.progress-bar-box {
    background-color: #161b22;
    border-bottom: 1px solid #21262d;
    padding: 10px 32px;
}

/* ── Screen titles ── */
.screen-title {
    font-size: 22px;
    font-weight: 600;
    color: #e6edf3;
}

.screen-subtitle {
    font-size: 13px;
    color: #8b949e;
}

/* ── Info panel ── */
.info-panel {
    background-color: #161b22;
    border-left: 1px solid #21262d;
}

.info-panel-header {
    font-size: 12px;
    font-weight: 600;
    color: #58a6ff;
    letter-spacing: 0.5px;
}

.info-panel-text {
    font-size: 12px;
    color: #8b949e;
    line-height: 1.6;
}

/* ── Navigation bar ── */
.nav-bar {
    background-color: #161b22;
    border-top: 1px solid #21262d;
}

.nav-btn {
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    min-width: 110px;
}

.nav-btn-back {
    background-color: #21262d;
    color: #8b949e;
    border: 1px solid #30363d;
}

.nav-btn-back:hover { background-color: #30363d; color: #e6edf3; }

.nav-btn-next {
    background-color: #1f3a5f;
    color: #58a6ff;
    border: 1px solid #1f4f8f;
}

.nav-btn-next:hover { background-color: #243d6b; }

.error-label {
    font-size: 12px;
    color: #f85149;
}

/* ── Form elements ── */
entry {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #e6edf3;
    padding: 6px 10px;
    font-size: 13px;
}

entry:focus { border-color: #58a6ff; }

checkbutton, radiobutton {
    color: #e6edf3;
    font-size: 13px;
}

checkbutton check, radiobutton radio {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
}

checkbutton:checked check, radiobutton:checked radio {
    background-color: #1f3a5f;
    border-color: #58a6ff;
    color: #58a6ff;
}

combobox button {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #e6edf3;
    padding: 4px 8px;
}

label { color: #e6edf3; }

.field-label {
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 4px;
}

.field-desc {
    font-size: 11px;
    color: #8b949e;
    margin-bottom: 8px;
}

.section-header {
    font-size: 15px;
    font-weight: 600;
    color: #58a6ff;
    margin-top: 8px;
    margin-bottom: 4px;
}

separator { background-color: #21262d; }

scrollbar { background-color: #0d1117; }
scrollbar slider {
    background-color: #30363d;
    border-radius: 4px;
    min-width: 6px;
    min-height: 6px;
}
scrollbar slider:hover { background-color: #58a6ff; }

/* ── Welcome screen ── */
.welcome-title {
    font-size: 36px;
    font-weight: 600;
    color: #58a6ff;
}

.welcome-subtitle {
    font-size: 16px;
    color: #8b949e;
}

.level-card {
    background-color: #161b22;
    border: 2px solid #21262d;
    border-radius: 10px;
    padding: 16px;
    transition: border-color 0.15s;
}

.level-card:hover { border-color: #30363d; }
.level-card-selected { border-color: #58a6ff; }

.level-card-title {
    font-size: 15px;
    font-weight: 600;
    color: #e6edf3;
}

.level-card-desc {
    font-size: 12px;
    color: #8b949e;
    margin-top: 4px;
}

/* ── Warning / info boxes ── */
.warning-box {
    background-color: #3d2a10;
    border: 1px solid #6e4f08;
    border-radius: 6px;
    padding: 10px 14px;
}

.warning-text { font-size: 12px; color: #e3b341; }
.info-box {
    background-color: #1a2d4f;
    border: 1px solid #1f4f8f;
    border-radius: 6px;
    padding: 10px 14px;
}
.info-text { font-size: 12px; color: #79c0ff; }
"""

# ── Stage registry (will grow as screens are implemented) ─────────────────────
# Format: (stage_number, label, module_path, class_name)
STAGES = [
    (0,  "Welcome",      "installer.ui.welcome",        "WelcomeScreen"),
    (1,  "Keyboard",     "installer.ui.keyboard",       "KeyboardScreen"),
    (2,  "Locale",       "installer.ui.locale_screen",  "LocaleScreen"),
    (3,  "Network",      "installer.ui.network",        "NetworkScreen"),
    (4,  "Disk",         "installer.ui.disk_select",    "DiskSelectScreen"),
    (5,  "Partitions",   "installer.ui.partition",      "PartitionScreen"),
    (6,  "Filesystem",   "installer.ui.filesystem",     "FilesystemScreen"),
    (7,  "Mirrors",      "installer.ui.mirrors",        "MirrorsScreen"),
    (8,  "Packages",     "installer.ui.packages",       "PackagesScreen"),
    (9,  "Install",      "installer.ui.progress",       "ProgressScreen"),
    (10, "Timezone",     "installer.ui.timezone",       "TimezoneScreen"),
    (11, "System",       "installer.ui.system_config",  "SystemConfigScreen"),
    (12, "Users",        "installer.ui.users",          "UsersScreen"),
    (13, "Bootloader",   "installer.ui.bootloader",     "BootloaderScreen"),
    (14, "Review",       "installer.ui.review",         "ReviewScreen"),
    (15, "Progress",     "installer.ui.progress",       "ProgressScreen"),
    (16, "Complete",     "installer.ui.complete",       "CompleteScreen"),
]


class ArchInstaller(Gtk.Window):
    def __init__(self):
        super().__init__(title="Arch Installer")
        self.set_default_size(1100, 700)
        self.set_border_width(0)
        self.set_resizable(True)

        # Load window icon
        for ico_path in [
            "/usr/share/icons/hicolor/128x128/apps/arch-installer.png",
            os.path.join(ASSETS_DIR, "installer.png"),
        ]:
            if os.path.exists(ico_path):
                try:
                    self.set_icon_from_file(ico_path)
                except Exception:
                    pass
                break

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Shared install state
        self.state = InstallState()

        # Detect boot mode
        self.state.boot_mode = "uefi" if os.path.exists("/sys/firmware/efi") else "bios"
        log.info(f"Boot mode detected: {self.state.boot_mode.upper()}")

        self._current_stage = 0
        self._build_shell()
        self._load_stage(0)

    def _build_shell(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.get_style_context().add_class("main-header")
        header.set_size_request(-1, 56)

        hcontent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hcontent.set_valign(Gtk.Align.CENTER)
        hcontent.set_margin_start(24)

        htitle = Gtk.Label(label="Arch Installer")
        htitle.get_style_context().add_class("header-title")
        htitle.set_halign(Gtk.Align.START)
        hcontent.pack_start(htitle, False, False, 0)

        hsub = Gtk.Label(label="Follow the Arch Way")
        hsub.get_style_context().add_class("header-subtitle")
        hsub.set_halign(Gtk.Align.START)
        hcontent.pack_start(hsub, False, False, 0)

        header.pack_start(hcontent, True, True, 0)

        self.stage_indicator = Gtk.Label(label="Stage 1 of 17")
        self.stage_indicator.get_style_context().add_class("stage-indicator")
        self.stage_indicator.set_margin_end(24)
        self.stage_indicator.set_valign(Gtk.Align.CENTER)
        header.pack_end(self.stage_indicator, False, False, 0)

        root.pack_start(header, False, False, 0)

        # Stage content area (stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        root.pack_start(self.stack, True, True, 0)

        self.add(root)
        self.show_all()

    def _load_stage(self, stage_num: int):
        """Load and display the screen for the given stage number."""
        if stage_num < 0 or stage_num >= len(STAGES):
            log.error(f"Invalid stage number: {stage_num}")
            return

        num, label, module_path, class_name = STAGES[stage_num]
        log.info(f"Loading stage {stage_num}: {label}")

        # Try to import the screen module
        try:
            import importlib
            mod = importlib.import_module(module_path)
            screen_class = getattr(mod, class_name)
            screen = screen_class(
                state=self.state,
                on_back=self._go_back if stage_num > 0 else None,
                on_next=self._go_next,
            )
            if stage_num == 0:
                screen.set_back_enabled(False)
        except (ImportError, AttributeError) as e:
            log.warning(f"Stage {stage_num} ({class_name}) not yet implemented: {e}")
            # Show placeholder
            from installer.ui.base_screen import BaseScreen
            screen = BaseScreen(
                state=self.state,
                on_back=self._go_back if stage_num > 0 else None,
                on_next=self._go_next,
            )
            screen.title = f"Stage {stage_num}: {label}"
            screen.subtitle = "(Not yet implemented — click Next to continue)"
            if stage_num == 0:
                screen.set_back_enabled(False)

        stack_name = f"stage_{stage_num}"
        # Remove old child with this name if it exists (for refresh)
        existing = self.stack.get_child_by_name(stack_name)
        if existing:
            self.stack.remove(existing)

        self.stack.add_named(screen, stack_name)
        screen.show_all()
        self.stack.set_visible_child_name(stack_name)
        self._current_stage = stage_num
        self.state.current_stage = stage_num
        self.stage_indicator.set_text(f"Stage {stage_num + 1} of {len(STAGES)}")

    def _go_next(self):
        next_stage = self._current_stage + 1
        if next_stage < len(STAGES):
            self._load_stage(next_stage)
        else:
            log.info("Installation complete.")

    def _go_back(self):
        prev_stage = self._current_stage - 1
        if prev_stage >= 0:
            self._load_stage(prev_stage)


def check_root():
    if os.geteuid() != 0:
        # Show a GTK error dialog before exiting
        gi.require_version('Gtk', '3.0')
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Root privileges required",
        )
        dialog.format_secondary_text(
            "The Arch Installer must be run as root.\n\n"
            "Please run:\n  sudo python installer/main.py"
        )
        dialog.run()
        dialog.destroy()
        sys.exit(1)


def main():
    check_root()
    log.info("Arch Installer starting")
    log.info(f"Running as UID: {os.geteuid()}")

    win = ArchInstaller()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
