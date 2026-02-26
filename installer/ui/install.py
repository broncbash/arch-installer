"""
installer/ui/install.py
------------------------
Stage 9 — Base System Install

Two-phase screen:

  Phase 1 — Pre-install summary
    Shows a full checklist of what is about to happen.
    User must click "Begin Installation" to proceed.
    Back button is available in this phase.

  Phase 2 — Live install
    Steps execute one by one in a background thread.
    Progress bar advances per step.
    Log output scrolls in real time.
    Back button is disabled during install.
    On success: Next button enabled.
    On failure: error shown, Retry and Abort buttons offered.
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen
from installer.backend.pacstrap import (
    INSTALL_STEPS,
    run_step,
    build_package_list,
)


class InstallScreen(BaseScreen):
    """Stage 9 — Base System Install."""

    title    = "Base System Install"
    subtitle = "Partition, format, and install the Arch Linux base system"

    WIKI_LINKS = [
        ("Installation guide", "https://wiki.archlinux.org/title/Installation_guide"),
        ("pacstrap",           "https://wiki.archlinux.org/title/Pacstrap"),
        ("fstab",              "https://wiki.archlinux.org/title/Fstab"),
    ]

    def __init__(self, state, on_next, on_back):
        self._phase          = "summary"   # 'summary' | 'installing' | 'done' | 'error'
        self._current_step   = 0
        self._failed_step    = None
        self._install_thread = None

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(False)
        GLib.idle_add(self._apply_phase)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        dry = "  [DRY RUN — nothing will actually be written]" if self.state.dry_run else ""
        return {
            "beginner": (
                f"💿  Installing Arch Linux{dry}\n\n"
                "This stage will:\n"
                "• Partition your disk\n"
                "• Format the filesystems\n"
                "• Install the base system\n\n"
                "This may take 5–20 minutes depending on your internet "
                "speed and the packages you selected.\n\n"
                "Do not close the installer or turn off your computer "
                "during installation."
            ),
            "intermediate": (
                f"💿  Base System Install{dry}\n\n"
                "pacstrap installs the packages into /mnt, then genfstab "
                "writes the filesystem table.\n\n"
                "The full log is saved to /tmp/arch-installer.log.\n\n"
                "If an error occurs you can retry the failed step or "
                "abort and go back to fix the configuration."
            ),
            "advanced": (
                f"💿  Base System Install{dry}\n\n"
                "Steps: sgdisk/parted → mkfs → cryptsetup (if LUKS) → "
                "mount → write mirrorlist → pacstrap -K → genfstab -U\n\n"
                "All commands are logged verbatim. In dry-run mode they "
                "are printed but not executed.\n\n"
                "After this stage: timezone, locale, hostname, users, "
                "bootloader, and mkinitcpio remain."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)

        self._stack.add_named(self._build_summary_page(), "summary")
        self._stack.add_named(self._build_install_page(), "install")

        return self._stack

    # ── Summary page ──────────────────────────────────────────────────────────

    def _build_summary_page(self) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        # ── What will happen ──────────────────────────────────────────────────
        steps_frame = Gtk.Frame()
        steps_frame.get_style_context().add_class("card")
        steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        steps_box.set_margin_start(14)
        steps_box.set_margin_end(14)
        steps_box.set_margin_top(10)
        steps_box.set_margin_bottom(10)

        steps_heading = Gtk.Label(label="What will happen:")
        steps_heading.get_style_context().add_class("section-heading")
        steps_heading.set_xalign(0)
        steps_box.pack_start(steps_heading, False, False, 0)

        for step_id, step_label in INSTALL_STEPS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = Gtk.Label(label="◦")
            icon.get_style_context().add_class("detail-key")
            row.pack_start(icon, False, False, 0)
            lbl = Gtk.Label(label=step_label)
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            row.pack_start(lbl, True, True, 0)
            steps_box.pack_start(row, False, False, 0)

        steps_frame.add(steps_box)
        box.pack_start(steps_frame, False, False, 0)

        # ── Configuration summary ─────────────────────────────────────────────
        cfg_frame = Gtk.Frame()
        cfg_frame.get_style_context().add_class("card")
        cfg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cfg_box.set_margin_start(14)
        cfg_box.set_margin_end(14)
        cfg_box.set_margin_top(10)
        cfg_box.set_margin_bottom(10)

        cfg_heading = Gtk.Label(label="Your configuration:")
        cfg_heading.get_style_context().add_class("section-heading")
        cfg_heading.set_xalign(0)
        cfg_box.pack_start(cfg_heading, False, False, 0)

        s = self.state
        cfg_rows = [
            ("Disk",         s.target_disk or "(not set)"),
            ("Partition table", s.partition_table.upper()),
            ("Root filesystem", s.root_filesystem),
            ("Encryption",   "LUKS2" if s.luks_passphrase else "None"),
            ("Desktop",      s.desktop_environment or "None (base only)"),
            ("Bootloader",   s.bootloader),
            ("Mirrors",      f"{len([l for l in s.mirrorlist.splitlines() if l.strip().startswith('Server =')])} servers"),
        ]
        for key, val in cfg_rows:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            k = Gtk.Label(label=f"{key}:")
            k.get_style_context().add_class("detail-key")
            k.set_width_chars(18)
            k.set_xalign(0)
            v = Gtk.Label(label=val)
            v.get_style_context().add_class("detail-value")
            v.set_xalign(0)
            row.pack_start(k, False, False, 0)
            row.pack_start(v, True, True, 0)
            cfg_box.pack_start(row, False, False, 0)

        cfg_frame.add(cfg_box)
        box.pack_start(cfg_frame, False, False, 0)

        # ── Package list ──────────────────────────────────────────────────────
        pkg_frame = Gtk.Frame()
        pkg_frame.get_style_context().add_class("card")
        pkg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pkg_box.set_margin_start(14)
        pkg_box.set_margin_end(14)
        pkg_box.set_margin_top(10)
        pkg_box.set_margin_bottom(10)

        pkgs = build_package_list(self.state)
        pkg_heading = Gtk.Label(label=f"Packages to install  ({len(pkgs)} total):")
        pkg_heading.get_style_context().add_class("section-heading")
        pkg_heading.set_xalign(0)
        pkg_box.pack_start(pkg_heading, False, False, 0)

        pkg_label = Gtk.Label(label="  ".join(pkgs))
        pkg_label.get_style_context().add_class("detail-value")
        pkg_label.set_xalign(0)
        pkg_label.set_line_wrap(True)
        pkg_box.pack_start(pkg_label, False, False, 0)

        pkg_frame.add(pkg_box)
        box.pack_start(pkg_frame, False, False, 0)

        # ── Dry-run notice ────────────────────────────────────────────────────
        if self.state.dry_run:
            notice = Gtk.Frame()
            notice.get_style_context().add_class("card")
            notice_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            notice_box.set_margin_start(14)
            notice_box.set_margin_end(14)
            notice_box.set_margin_top(10)
            notice_box.set_margin_bottom(10)
            notice_icon = Gtk.Label(label="🧪")
            notice_box.pack_start(notice_icon, False, False, 0)
            notice_lbl = Gtk.Label(
                label="DRY RUN MODE: The install will be simulated. "
                      "No changes will be made to your disk."
            )
            notice_lbl.get_style_context().add_class("dry-run-text")
            notice_lbl.set_xalign(0)
            notice_lbl.set_line_wrap(True)
            notice_box.pack_start(notice_lbl, True, True, 0)
            notice.add(notice_box)
            box.pack_start(notice, False, False, 0)

        # ── Begin button ──────────────────────────────────────────────────────
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._begin_btn = Gtk.Button(
            label="🧪  Begin Dry Run" if self.state.dry_run else "⚠️  Begin Installation"
        )
        self._begin_btn.get_style_context().add_class("action-button")
        self._begin_btn.connect("clicked", self._on_begin_clicked)
        btn_row.pack_start(self._begin_btn, False, False, 0)
        box.pack_start(btn_row, False, False, 0)

        scroll.add(box)
        return scroll

    # ── Install page ──────────────────────────────────────────────────────────

    def _build_install_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        # ── Step indicators ───────────────────────────────────────────────────
        steps_frame = Gtk.Frame()
        steps_frame.get_style_context().add_class("card")
        self._steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._steps_box.set_margin_start(14)
        self._steps_box.set_margin_end(14)
        self._steps_box.set_margin_top(10)
        self._steps_box.set_margin_bottom(10)

        self._step_labels = {}
        self._step_icons  = {}

        for step_id, step_label in INSTALL_STEPS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Label(label="○")
            icon.set_width_chars(2)
            icon.set_xalign(0.5)
            self._step_icons[step_id] = icon
            row.pack_start(icon, False, False, 0)
            lbl = Gtk.Label(label=step_label)
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            self._step_labels[step_id] = lbl
            row.pack_start(lbl, True, True, 0)
            self._steps_box.pack_start(row, False, False, 0)

        steps_frame.add(self._steps_box)
        box.pack_start(steps_frame, False, False, 0)

        # ── Progress bar ──────────────────────────────────────────────────────
        self._progress = Gtk.ProgressBar()
        self._progress.set_show_text(True)
        self._progress.set_text("Waiting…")
        self._progress.set_fraction(0.0)
        box.pack_start(self._progress, False, False, 0)

        # ── Log output ────────────────────────────────────────────────────────
        log_frame = Gtk.Frame()
        log_frame.get_style_context().add_class("card")

        log_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        log_inner.set_margin_start(2)
        log_inner.set_margin_end(2)
        log_inner.set_margin_top(2)
        log_inner.set_margin_bottom(2)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        log_scroll.set_min_content_height(180)

        self._log_view = Gtk.TextView()
        self._log_view.set_editable(False)
        self._log_view.set_cursor_visible(False)
        self._log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._log_view.override_font(Pango.FontDescription("Monospace 9"))
        self._log_view.get_style_context().add_class("detail-value")
        self._log_buffer = self._log_view.get_buffer()

        log_scroll.add(self._log_view)
        log_inner.pack_start(log_scroll, True, True, 0)
        log_frame.add(log_inner)
        box.pack_start(log_frame, True, True, 0)

        # ── Status / error row ────────────────────────────────────────────────
        self._status_label = Gtk.Label(label="")
        self._status_label.get_style_context().add_class("detail-value")
        self._status_label.set_xalign(0)
        self._status_label.set_line_wrap(True)
        box.pack_start(self._status_label, False, False, 0)

        # ── Retry / Abort buttons (hidden until error) ────────────────────────
        self._error_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self._retry_btn = Gtk.Button(label="🔄  Retry failed step")
        self._retry_btn.get_style_context().add_class("action-button")
        self._retry_btn.connect("clicked", self._on_retry_clicked)
        self._error_row.pack_start(self._retry_btn, False, False, 0)

        self._abort_btn = Gtk.Button(label="✕  Abort — go back")
        self._abort_btn.get_style_context().add_class("action-button")
        self._abort_btn.connect("clicked", self._on_abort_clicked)
        self._error_row.pack_start(self._abort_btn, False, False, 0)

        self._error_row.set_no_show_all(True)
        box.pack_start(self._error_row, False, False, 0)

        return box

    # ── Phase management ──────────────────────────────────────────────────────

    def _apply_phase(self):
        if self._phase == "summary":
            self._stack.set_visible_child_name("summary")
            self.set_back_enabled(True)
            self.set_next_enabled(False)
        elif self._phase in ("installing", "done", "error"):
            self._stack.set_visible_child_name("install")
            self.set_back_enabled(False)
            self.set_next_enabled(self._phase == "done")
        return False

    # ── Install flow ──────────────────────────────────────────────────────────

    def _on_begin_clicked(self, btn):
        self._phase = "installing"
        self._current_step = 0
        self._apply_phase()
        self._reset_step_icons()
        self._append_log(
            "🧪 DRY RUN — no disk changes will be made\n\n"
            if self.state.dry_run
            else "Starting installation…\n\n"
        )
        self._install_thread = threading.Thread(
            target=self._install_worker, daemon=True
        )
        self._install_thread.start()

    def _install_worker(self):
        """Runs in a background thread — executes each step in sequence."""
        steps = INSTALL_STEPS
        total = len(steps)

        for i, (step_id, step_label) in enumerate(steps):
            # Update UI: mark step as running
            GLib.idle_add(self._set_step_running, step_id, i, total, step_label)

            ok, output = run_step(step_id, self.state)

            if output:
                GLib.idle_add(self._append_log, output + "\n")

            if ok:
                GLib.idle_add(self._set_step_done, step_id, i + 1, total)
            else:
                GLib.idle_add(self._set_step_failed, step_id, output)
                return  # stop on first failure

        # All steps completed
        GLib.idle_add(self._on_install_complete)

    def _set_step_running(self, step_id, idx, total, label):
        self._step_icons[step_id].set_text("⏳")
        self._progress.set_fraction(idx / total)
        self._progress.set_text(f"Step {idx + 1}/{total}: {label}")
        self._append_log(f"\n▶  {label}\n")

    def _set_step_done(self, step_id, done, total):
        self._step_icons[step_id].set_text("✅")
        self._progress.set_fraction(done / total)

    def _set_step_failed(self, step_id, error_msg):
        self._step_icons[step_id].set_text("❌")
        self._phase = "error"
        self._failed_step = step_id
        self._progress.set_text("Installation failed")
        self._status_label.set_text(
            f"❌  Step failed: {dict(INSTALL_STEPS).get(step_id, step_id)}\n"
            f"    {error_msg}"
        )
        self._status_label.get_style_context().add_class("error-label")
        self._error_row.show_all()
        self.set_back_enabled(True)

    def _on_install_complete(self):
        self._phase = "done"
        self._progress.set_fraction(1.0)
        self._progress.set_text(
            "✅  Dry run complete — all steps simulated successfully"
            if self.state.dry_run
            else "✅  Installation complete"
        )
        self._status_label.set_text(
            "Base system installed successfully. Click Next to continue."
        )
        self._status_label.get_style_context().remove_class("error-label")
        self._error_row.hide()
        self.set_next_enabled(True)
        self.state.install_complete = True

    def _on_retry_clicked(self, btn):
        if not self._failed_step:
            return
        self._error_row.hide()
        self._status_label.set_text("")
        self._phase = "installing"
        self.set_back_enabled(False)
        self.set_next_enabled(False)

        failed = self._failed_step
        self._failed_step = None

        # Find the index of the failed step and resume from there
        step_ids = [s[0] for s in INSTALL_STEPS]
        start_idx = step_ids.index(failed) if failed in step_ids else 0
        total = len(INSTALL_STEPS)

        def _retry_worker():
            for i in range(start_idx, total):
                step_id, step_label = INSTALL_STEPS[i]
                GLib.idle_add(self._set_step_running, step_id, i, total, step_label)
                ok, output = run_step(step_id, self.state)
                if output:
                    GLib.idle_add(self._append_log, output + "\n")
                if ok:
                    GLib.idle_add(self._set_step_done, step_id, i + 1, total)
                else:
                    GLib.idle_add(self._set_step_failed, step_id, output)
                    return
            GLib.idle_add(self._on_install_complete)

        threading.Thread(target=_retry_worker, daemon=True).start()

    def _on_abort_clicked(self, btn):
        """Go back to the summary page."""
        self._phase = "summary"
        self._reset_step_icons()
        self._apply_phase()

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _append_log(self, text: str):
        """Append text to the log view and scroll to bottom."""
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, text)
        # Scroll to bottom
        adj = self._log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _reset_step_icons(self):
        for step_id, _ in INSTALL_STEPS:
            if step_id in self._step_icons:
                self._step_icons[step_id].set_text("○")

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if self._phase != "done":
            return False, "Complete the installation before continuing."
        return True, ""

    def on_next(self):
        pass  # install_complete already set in _on_install_complete
