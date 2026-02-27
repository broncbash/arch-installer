"""
installer/ui/complete.py
------------------------
Stage 15 — Complete / Reboot

Runs the final post-install configuration steps inside the chroot, then
offers a reboot button.

Steps handled here (everything pacstrap did NOT cover):
  1.  locale-gen              — generate locale
  2.  locale.conf             — write LANG= to /etc/locale.conf
  3.  vconsole.conf           — write KEYMAP= to /etc/vconsole.conf
  4.  timezone                — symlink /etc/localtime, hwclock --systohc
  5.  mkinitcpio              — generate initramfs (mkinitcpio -P)
  6.  bootloader              — install GRUB / systemd-boot / rEFInd
  7.  enable services         — NetworkManager, NTP, display manager
  8.  unmount                 — umount -R /mnt

Then shows a success screen with a Reboot Now button.

All steps go through runner.run_cmd / run_chroot so dry_run is respected.
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen
from installer.backend.runner import run_cmd, run_chroot, run_script


MOUNTPOINT = "/mnt"

# ── Step definitions ──────────────────────────────────────────────────────────

COMPLETE_STEPS = [
    ("locale",      "Generate locale"),
    ("vconsole",    "Set keyboard layout"),
    ("timezone",    "Configure timezone"),
    ("initramfs",   "Generate initramfs  (mkinitcpio -P)"),
    ("bootloader",  "Install bootloader"),
    ("services",    "Enable system services"),
    ("unmount",     "Unmount filesystems"),
]


# ── Backend step functions ────────────────────────────────────────────────────

def _step_locale(state) -> tuple:
    """Generate locale and write locale.conf."""
    logs = []

    # Ensure the locale is uncommented in /etc/locale.gen
    locale = state.locale or "en_US.UTF-8"
    ok, out = run_chroot(
        ["sed", "-i", f"s/^#{locale}/{locale}/", "/etc/locale.gen"],
        state, f"Uncomment {locale} in locale.gen"
    )
    if not ok:
        return False, out
    logs.append(out)

    ok, out = run_chroot(["locale-gen"], state, "Run locale-gen")
    if not ok:
        return False, out
    logs.append(out)

    # Write /etc/locale.conf
    lang = locale.split(".")[0]  # e.g. en_US.UTF-8 → en_US
    ok, out = run_script(
        f"echo 'LANG={locale}' > {MOUNTPOINT}/etc/locale.conf",
        state, "Write /etc/locale.conf"
    )
    if not ok:
        return False, out
    logs.append(out)

    return True, "\n".join(logs)


def _step_vconsole(state) -> tuple:
    """Write /etc/vconsole.conf with the chosen keyboard layout."""
    keymap = state.keyboard_layout or "us"
    ok, out = run_script(
        f"echo 'KEYMAP={keymap}' > {MOUNTPOINT}/etc/vconsole.conf",
        state, f"Write /etc/vconsole.conf (KEYMAP={keymap})"
    )
    return ok, out


def _step_timezone(state) -> tuple:
    """Symlink /etc/localtime and sync hardware clock."""
    logs = []
    tz = state.timezone or "UTC"

    ok, out = run_chroot(
        ["ln", "-sf", f"/usr/share/zoneinfo/{tz}", "/etc/localtime"],
        state, f"Link /etc/localtime → {tz}"
    )
    if not ok:
        return False, out
    logs.append(out)

    ok, out = run_chroot(
        ["hwclock", "--systohc"],
        state, "Sync hardware clock (hwclock --systohc)"
    )
    if not ok:
        return False, out
    logs.append(out)

    return True, "\n".join(logs)


def _step_initramfs(state) -> tuple:
    """Generate the initramfs with mkinitcpio -P."""
    # If LUKS + UKI, the encrypt hook must be present in mkinitcpio.conf.
    # We add it here before running mkinitcpio.
    logs = []
    if state.bootloader_uki_needs_decrypt:
        ok, out = run_chroot(
            ["sed", "-i",
             "s/^HOOKS=(.*block/& encrypt/",
             "/etc/mkinitcpio.conf"],
            state, "Add encrypt hook to mkinitcpio.conf"
        )
        if not ok:
            return False, out
        logs.append(out)

    ok, out = run_chroot(
        ["mkinitcpio", "-P"],
        state, "Generate initramfs (mkinitcpio -P)"
    )
    if not ok:
        return False, out
    logs.append(out)
    return True, "\n".join(logs)


def _step_bootloader(state) -> tuple:
    """Install the chosen bootloader."""
    bl = state.bootloader or "grub"
    logs = []

    if bl == "grub":
        if state.boot_mode == "uefi":
            ok, out = run_chroot(
                ["grub-install",
                 "--target=x86_64-efi",
                 "--efi-directory=/boot",
                 "--bootloader-id=GRUB"],
                state, "grub-install (UEFI)"
            )
        else:
            ok, out = run_chroot(
                ["grub-install",
                 "--target=i386-pc",
                 state.target_disk],
                state, "grub-install (BIOS)"
            )
        if not ok:
            return False, out
        logs.append(out)

        ok, out = run_chroot(
            ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
            state, "Generate grub.cfg"
        )
        if not ok:
            return False, out
        logs.append(out)

    elif bl == "systemd-boot":
        ok, out = run_chroot(
            ["bootctl", "--path=/boot", "install"],
            state, "bootctl install"
        )
        if not ok:
            return False, out
        logs.append(out)

        # Write a basic loader.conf
        ok, out = run_script(
            f"mkdir -p {MOUNTPOINT}/boot/loader && "
            f"printf 'default arch\\ntimeout 3\\n' "
            f"> {MOUNTPOINT}/boot/loader/loader.conf",
            state, "Write loader.conf"
        )
        if not ok:
            return False, out
        logs.append(out)

        # Write a loader entry for the installed kernel
        ok, out = run_script(
            f"mkdir -p {MOUNTPOINT}/boot/loader/entries && "
            f"printf 'title   Arch Linux\\nlinux   /vmlinuz-linux\\n"
            f"initrd  /initramfs-linux.img\\noptions root=LABEL=root rw\\n' "
            f"> {MOUNTPOINT}/boot/loader/entries/arch.conf",
            state, "Write arch.conf loader entry"
        )
        if not ok:
            return False, out
        logs.append(out)

    elif bl == "refind":
        ok, out = run_chroot(
            ["refind-install"],
            state, "refind-install"
        )
        if not ok:
            return False, out
        logs.append(out)

    elif bl == "efistub":
        # Register the kernel directly in UEFI NVRAM via efibootmgr
        efi = state.efi_partition or ""
        disk = state.target_disk or ""
        # Extract partition number (last digit(s))
        part_num = "".join(filter(str.isdigit, efi.replace(disk, ""))) or "1"
        ok, out = run_chroot(
            ["efibootmgr",
             "--disk", disk,
             "--part", part_num,
             "--create",
             "--label", "Arch Linux",
             "--loader", "/vmlinuz-linux",
             "--unicode", "root=LABEL=root rw initrd=\\initramfs-linux.img"],
            state, "Register EFIStub entry via efibootmgr"
        )
        if not ok:
            return False, out
        logs.append(out)

    elif bl == "uki":
        # Build UKI with ukify (or mkinitcpio --uki if ukify unavailable)
        ok, out = run_chroot(
            ["mkinitcpio", "-p", "linux", "--uki",
             "/boot/EFI/Linux/arch-linux.efi"],
            state, "Build Unified Kernel Image"
        )
        if not ok:
            return False, out
        logs.append(out)

    else:
        return False, f"Unknown bootloader: {bl}"

    return True, "\n".join(logs)


def _step_services(state) -> tuple:
    """Enable essential systemd services."""
    logs = []
    services = []

    # Network manager
    nm = state.network_manager or ""
    if nm == "NetworkManager":
        services.append("NetworkManager")
    elif nm == "systemd-networkd":
        services.append("systemd-networkd")
        services.append("systemd-resolved")

    # NTP
    if state.enable_ntp:
        services.append("systemd-timesyncd")

    # Display manager
    dm = state.display_manager or ""
    if dm in ("gdm", "sddm", "lightdm"):
        services.append(dm)

    for svc in services:
        ok, out = run_chroot(
            ["systemctl", "enable", svc],
            state, f"Enable {svc}"
        )
        if not ok:
            return False, out
        logs.append(out)

    if not services:
        return True, "No services to enable."

    return True, "\n".join(logs)


def _step_unmount(state) -> tuple:
    """Unmount all filesystems under /mnt."""
    return run_cmd(
        ["umount", "-R", MOUNTPOINT],
        state, "Unmount all filesystems (umount -R /mnt)"
    )


def run_complete_step(step_id: str, state) -> tuple:
    """Dispatch a complete step by id."""
    fn = {
        "locale":     _step_locale,
        "vconsole":   _step_vconsole,
        "timezone":   _step_timezone,
        "initramfs":  _step_initramfs,
        "bootloader": _step_bootloader,
        "services":   _step_services,
        "unmount":    _step_unmount,
    }.get(step_id)

    if fn is None:
        return False, f"Unknown step: {step_id}"

    try:
        return fn(state)
    except Exception as exc:
        return False, f"Unexpected error in '{step_id}': {exc}"


# ── Screen ────────────────────────────────────────────────────────────────────

class CompleteScreen(BaseScreen):
    """Stage 15 — Complete / Reboot."""

    title    = "Complete Installation"
    subtitle = "Final configuration and reboot"

    WIKI_LINKS = [
        ("Installation guide — chroot", "https://wiki.archlinux.org/title/Installation_guide#Configure_the_system"),
        ("mkinitcpio",                  "https://wiki.archlinux.org/title/Mkinitcpio"),
        ("GRUB",                        "https://wiki.archlinux.org/title/GRUB"),
        ("systemd-boot",                "https://wiki.archlinux.org/title/Systemd-boot"),
    ]

    def __init__(self, state, on_next, on_back=None):
        self._phase        = "ready"   # 'ready' | 'running' | 'done' | 'error'
        self._failed_step  = None
        self._step_icons   = {}

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(False)
        self.set_next_label("🔁  Finish")
        self.set_back_enabled(False)   # no going back once we're here
        GLib.idle_add(self._apply_phase)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        dry = "  [DRY RUN]" if self.state.dry_run else ""
        return {
            "beginner": (
                f"🎉  Almost done!{dry}\n\n"
                "This final stage sets up the last few things your system "
                "needs before it can boot on its own:\n\n"
                "• Locale — your language settings\n"
                "• Keyboard layout in the console\n"
                "• Timezone and hardware clock\n"
                "• Initramfs — the mini-system that starts your kernel\n"
                "• Bootloader — what starts Arch at power-on\n"
                "• System services (network, time sync)\n\n"
                "When it's done, click Reboot to start your new system."
            ),
            "intermediate": (
                f"🎉  Final configuration{dry}\n\n"
                "Steps: locale-gen → locale.conf → vconsole.conf → "
                "localtime symlink → hwclock → mkinitcpio -P → "
                "bootloader install → systemctl enable → umount -R /mnt\n\n"
                "After rebooting, remove the installation media so the "
                "system boots from the installed disk."
            ),
            "advanced": (
                f"🎉  Post-install chroot config{dry}\n\n"
                "locale-gen reads /etc/locale.gen; LANG is written to "
                "/etc/locale.conf. KEYMAP to /etc/vconsole.conf.\n\n"
                "mkinitcpio -P regenerates all presets. If LUKS + UKI is "
                "selected the encrypt hook is injected into "
                "/etc/mkinitcpio.conf first.\n\n"
                "Bootloader: GRUB (grub-install + grub-mkconfig), "
                "systemd-boot (bootctl install + loader entries), "
                "rEFInd (refind-install), EFIStub (efibootmgr), "
                "UKI (mkinitcpio --uki).\n\n"
                "Finally: umount -R /mnt and reboot."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)

        self._stack.add_named(self._build_ready_page(),   "ready")
        self._stack.add_named(self._build_running_page(), "running")
        self._stack.add_named(self._build_done_page(),    "done")

        return self._stack

    # ── Ready page ────────────────────────────────────────────────────────────

    def _build_ready_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # What will happen card
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)

        heading = Gtk.Label(label="Final steps:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        inner.pack_start(heading, False, False, 0)

        for _step_id, label in COMPLETE_STEPS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            dot = Gtk.Label(label="◦")
            dot.get_style_context().add_class("detail-key")
            row.pack_start(dot, False, False, 0)
            lbl = Gtk.Label(label=label)
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            row.pack_start(lbl, True, True, 0)
            inner.pack_start(row, False, False, 0)

        frame.add(inner)
        box.pack_start(frame, False, False, 0)

        # Config summary card
        s = self.state
        summary_frame = Gtk.Frame()
        summary_frame.get_style_context().add_class("card")
        summary_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        summary_inner.set_margin_start(16)
        summary_inner.set_margin_end(16)
        summary_inner.set_margin_top(12)
        summary_inner.set_margin_bottom(12)

        sum_heading = Gtk.Label(label="Configuration:")
        sum_heading.get_style_context().add_class("section-heading")
        sum_heading.set_xalign(0)
        summary_inner.pack_start(sum_heading, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(4)

        rows = [
            ("Locale",      s.locale),
            ("Keyboard",    s.keyboard_layout),
            ("Timezone",    s.timezone),
            ("Bootloader",  s.bootloader),
            ("Services",    self._services_summary()),
        ]
        for r, (key, val) in enumerate(rows):
            k = Gtk.Label(label=key)
            k.get_style_context().add_class("detail-key")
            k.set_xalign(1)
            grid.attach(k, 0, r, 1, 1)
            v = Gtk.Label(label=val)
            v.get_style_context().add_class("detail-value")
            v.set_xalign(0)
            grid.attach(v, 1, r, 1, 1)

        summary_inner.pack_start(grid, False, False, 0)
        summary_frame.add(summary_inner)
        box.pack_start(summary_frame, False, False, 0)

        # Begin button
        begin_label = (
            "🧪  Begin Dry Run" if s.dry_run else "🚀  Finalise Installation"
        )
        begin_btn = Gtk.Button(label=begin_label)
        begin_btn.get_style_context().add_class("nav-btn")
        begin_btn.get_style_context().add_class("nav-btn-next")
        begin_btn.set_halign(Gtk.Align.START)
        begin_btn.connect("clicked", self._on_begin_clicked)
        box.pack_start(begin_btn, False, False, 0)

        return box

    # ── Running page ──────────────────────────────────────────────────────────

    def _build_running_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Step indicators
        steps_frame = Gtk.Frame()
        steps_frame.get_style_context().add_class("card")
        steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        steps_box.set_margin_start(16)
        steps_box.set_margin_end(16)
        steps_box.set_margin_top(10)
        steps_box.set_margin_bottom(10)

        for step_id, label in COMPLETE_STEPS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Label(label="○")
            icon.set_width_chars(2)
            self._step_icons[step_id] = icon
            row.pack_start(icon, False, False, 0)
            lbl = Gtk.Label(label=label)
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            row.pack_start(lbl, True, True, 0)
            steps_box.pack_start(row, False, False, 0)

        steps_frame.add(steps_box)
        box.pack_start(steps_frame, False, False, 0)

        # Progress bar
        self._progress = Gtk.ProgressBar()
        self._progress.set_show_text(True)
        self._progress.set_text("Starting…")
        box.pack_start(self._progress, False, False, 0)

        # Log view
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
        log_scroll.set_vexpand(True)

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

        # Status label
        self._status_label = Gtk.Label(label="")
        self._status_label.get_style_context().add_class("detail-value")
        self._status_label.set_xalign(0)
        self._status_label.set_line_wrap(True)
        box.pack_start(self._status_label, False, False, 0)

        # Retry / Abort row (hidden until error)
        self._error_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._retry_btn = Gtk.Button(label="🔄  Retry failed step")
        self._retry_btn.get_style_context().add_class("action-button")
        self._retry_btn.connect("clicked", self._on_retry_clicked)
        self._error_row.pack_start(self._retry_btn, False, False, 0)
        self._error_row.set_no_show_all(True)
        box.pack_start(self._error_row, False, False, 0)

        return box

    # ── Done page ─────────────────────────────────────────────────────────────

    def _build_done_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        if self.state.dry_run:
            icon_text = "🧪"
            title_text = "Dry Run Complete"
            body_text = (
                "All steps were simulated successfully.\n"
                "No changes were made to your disk.\n\n"
                "Set  dry_run = False  in state.py to perform a real install."
            )
            btn_text = "✓  Close"
        else:
            icon_text = "🎉"
            title_text = "Installation Complete!"
            body_text = (
                f"Arch Linux has been installed successfully.\n\n"
                f"Hostname  :  {self.state.hostname}\n"
                f"Users     :  {', '.join(u['username'] for u in self.state.users)}\n"
                f"Bootloader:  {self.state.bootloader}\n\n"
                "Remove your installation media, then reboot."
            )
            btn_text = "🔁  Reboot Now"

        icon = Gtk.Label(label=icon_text)
        icon.get_style_context().add_class("screen-title")
        box.pack_start(icon, False, False, 0)

        title = Gtk.Label(label=title_text)
        title.get_style_context().add_class("screen-title")
        box.pack_start(title, False, False, 0)

        body = Gtk.Label(label=body_text)
        body.get_style_context().add_class("detail-value")
        body.set_justify(Gtk.Justification.CENTER)
        body.set_line_wrap(True)
        box.pack_start(body, False, False, 0)

        self._reboot_btn = Gtk.Button(label=btn_text)
        self._reboot_btn.get_style_context().add_class("nav-btn")
        self._reboot_btn.get_style_context().add_class("nav-btn-next")
        self._reboot_btn.connect("clicked", self._on_reboot_clicked)
        box.pack_start(self._reboot_btn, False, False, 0)

        return box

    # ── Phase management ──────────────────────────────────────────────────────

    def _apply_phase(self):
        if self._phase == "ready":
            self._stack.set_visible_child_name("ready")
        elif self._phase in ("running", "error"):
            self._stack.set_visible_child_name("running")
        elif self._phase == "done":
            self._stack.set_visible_child_name("done")
        return False

    # ── Install flow ──────────────────────────────────────────────────────────

    def _on_begin_clicked(self, _btn):
        self._phase = "running"
        self._apply_phase()
        self._reset_step_icons()
        self._append_log(
            "🧪 DRY RUN — no changes will be made\n\n"
            if self.state.dry_run
            else "Starting final configuration…\n\n"
        )
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        total = len(COMPLETE_STEPS)
        for i, (step_id, label) in enumerate(COMPLETE_STEPS):
            GLib.idle_add(self._set_step_running, step_id, i, total, label)
            ok, output = run_complete_step(step_id, self.state)
            if output:
                GLib.idle_add(self._append_log, output + "\n")
            if ok:
                GLib.idle_add(self._set_step_done, step_id, i + 1, total)
            else:
                GLib.idle_add(self._set_step_failed, step_id, output)
                return
        GLib.idle_add(self._on_complete)

    def _set_step_running(self, step_id, idx, total, label):
        if step_id in self._step_icons:
            self._step_icons[step_id].set_text("⏳")
        self._progress.set_fraction(idx / total)
        self._progress.set_text(f"Step {idx + 1}/{total}: {label}")
        self._append_log(f"\n▶  {label}\n")

    def _set_step_done(self, step_id, done, total):
        if step_id in self._step_icons:
            self._step_icons[step_id].set_text("✅")
        self._progress.set_fraction(done / total)

    def _set_step_failed(self, step_id, error_msg):
        if step_id in self._step_icons:
            self._step_icons[step_id].set_text("❌")
        self._phase = "error"
        self._failed_step = step_id
        self._progress.set_text("Step failed")
        self._status_label.set_text(
            f"❌  Failed: {dict(COMPLETE_STEPS).get(step_id, step_id)}\n"
            f"    {error_msg}"
        )
        self._status_label.get_style_context().add_class("error-label")
        self._error_row.show_all()

    def _on_complete(self):
        self._phase = "done"
        self._progress.set_fraction(1.0)
        self._progress.set_text(
            "✅  Dry run complete" if self.state.dry_run
            else "✅  Installation complete"
        )
        self.state.install_complete = True
        self._apply_phase()

    def _on_retry_clicked(self, _btn):
        if not self._failed_step:
            return
        self._error_row.hide()
        self._status_label.set_text("")
        self._phase = "running"

        failed = self._failed_step
        self._failed_step = None

        step_ids = [s[0] for s in COMPLETE_STEPS]
        start_idx = step_ids.index(failed) if failed in step_ids else 0
        total = len(COMPLETE_STEPS)

        def _retry():
            for i in range(start_idx, total):
                step_id, label = COMPLETE_STEPS[i]
                GLib.idle_add(self._set_step_running, step_id, i, total, label)
                ok, output = run_complete_step(step_id, self.state)
                if output:
                    GLib.idle_add(self._append_log, output + "\n")
                if ok:
                    GLib.idle_add(self._set_step_done, step_id, i + 1, total)
                else:
                    GLib.idle_add(self._set_step_failed, step_id, output)
                    return
            GLib.idle_add(self._on_complete)

        threading.Thread(target=_retry, daemon=True).start()

    def _on_reboot_clicked(self, _btn):
        if self.state.dry_run:
            Gtk.main_quit()
            return
        import subprocess
        try:
            subprocess.run(["reboot"], check=True)
        except Exception:
            run_cmd(["systemctl", "reboot"], self.state, "Reboot")

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _append_log(self, text: str):
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, text)
        adj = self._log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _reset_step_icons(self):
        for step_id, _ in COMPLETE_STEPS:
            if step_id in self._step_icons:
                self._step_icons[step_id].set_text("○")

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        return True, ""   # Next button is never shown; reboot btn handles exit

    def on_next(self):
        pass

    # ── Services summary helper ───────────────────────────────────────────────

    def _services_summary(self) -> str:
        svcs = []
        nm = self.state.network_manager or ""
        if nm:
            svcs.append(nm)
        if self.state.enable_ntp:
            svcs.append("systemd-timesyncd")
        if self.state.display_manager:
            svcs.append(self.state.display_manager)
        return ", ".join(svcs) if svcs else "None"
