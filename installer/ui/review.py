"""
installer/ui/review.py
----------------------
Stage 12 — Review & Confirm

Shows a complete, categorised summary of every selection made across all
prior stages. The user can jump back to any stage to make corrections, then
return here to confirm and kick off the installation.

The "Begin Installation" / "Begin Dry Run" button is the only way to advance
to Stage 13. It is blocked until the user explicitly ticks the confirmation
checkbox.

No data is written to state here — everything was already saved by each
individual screen. This screen is read-only except for the confirm checkbox.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango, GLib

from installer.ui.base_screen import BaseScreen


# Stage numbers used by the "Edit" jump buttons — must match STAGE_CLASSES
# order in main.py.
_STAGE = {
    "locale":     3,
    "disk":       4,
    "partitions": 5,
    "filesystem": 6,
    "mirrors":    7,
    "packages":   8,
    "timezone":   9,
    "sysconfig":  10,
    "users":      11,
    # Review is stage 12 — no edit button for self
    # Install is stage 13, Bootloader is stage 14 — nothing to edit pre-install
}


class ReviewScreen(BaseScreen):
    """Stage 12 — Review & Confirm."""

    title    = "Review & Confirm"
    subtitle = "Check every setting before installation begins"

    WIKI_LINKS = [
        ("Installation guide", "https://wiki.archlinux.org/title/Installation_guide"),
    ]

    def __init__(self, state, on_next, on_back=None, on_jump=None):
        # on_jump(stage_index) lets us teleport back to any earlier stage.
        # main.py passes this in; if it's absent we simply disable edit buttons.
        self._on_jump = on_jump
        self._confirmed = False
        super().__init__(state=state, on_next=on_next, on_back=on_back)
        self.set_next_enabled(False)
        self.set_next_label(
            "🧪  Begin Dry Run" if state.dry_run else "🚀  Begin Installation"
        )

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "📋  Review & Confirm\n\n"
                "This is your last chance to check everything before Arch Linux "
                "is installed.\n\n"
                "Read through each section carefully. If anything looks wrong, "
                "click the  ✏ Edit  button next to that section to go back and "
                "fix it.\n\n"
                "When you're happy with everything, tick the confirmation box at "
                "the bottom and click Begin Installation."
            ),
            "intermediate": (
                "📋  Review & Confirm\n\n"
                "All selections from every stage are shown here. Nothing has been "
                "written to disk yet.\n\n"
                "Click  ✏ Edit  next to any section to jump directly back to that "
                "stage. When you return, you'll land back here automatically.\n\n"
                "Tick the checkbox to confirm, then click Begin Installation to "
                "run the full install sequence."
            ),
            "advanced": (
                "📋  Review & Confirm\n\n"
                "Read-only summary of InstallState. No changes are possible here "
                "— use the Edit buttons to navigate back to specific stages.\n\n"
                "On confirmation, Stage 13 runs the full install sequence: "
                "partition → format → LUKS → mount → mirrorlist → pacstrap → "
                "fstab → locale → hostname → users → bootloader → reboot prompt.\n\n"
                "Dry-run mode simulates the entire sequence without touching disk."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Scrollable summary cards
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        cards_box.set_margin_bottom(8)

        cards_box.pack_start(self._build_system_card(),   False, False, 0)
        cards_box.pack_start(self._build_disk_card(),     False, False, 0)
        cards_box.pack_start(self._build_packages_card(), False, False, 0)
        cards_box.pack_start(self._build_users_card(),    False, False, 0)
        cards_box.pack_start(self._build_next_steps(),    False, False, 0)

        scroll.add(cards_box)
        outer.pack_start(scroll, True, True, 0)

        # Confirmation checkbox — pinned below the scroll area
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(8)
        outer.pack_start(sep, False, False, 0)

        confirm_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        confirm_box.set_margin_top(12)
        confirm_box.set_margin_bottom(4)

        self._confirm_check = Gtk.CheckButton()
        self._confirm_check.connect("toggled", self._on_confirm_toggled)
        confirm_box.pack_start(self._confirm_check, False, False, 0)

        if self.state.dry_run:
            confirm_text = (
                "I have reviewed all settings and want to begin the <b>dry run</b>."
            )
        else:
            confirm_text = (
                "I have reviewed all settings. I understand this will "
                "<b>erase all data</b> on the selected disk and begin installation."
            )
        confirm_lbl = Gtk.Label()
        confirm_lbl.set_markup(confirm_text)
        confirm_lbl.set_line_wrap(True)
        confirm_lbl.set_xalign(0)
        confirm_box.pack_start(confirm_lbl, True, True, 0)

        outer.pack_start(confirm_box, False, False, 0)

        return outer

    # ── Section card helpers ──────────────────────────────────────────────────

    def _make_section_card(self, title: str, icon: str,
                           stage_key: str | None) -> tuple[Gtk.Box, Gtk.Grid]:
        """
        Return (card_box, grid) — a styled card with a heading row
        (icon + title + optional Edit button) and an empty Grid for rows.
        """
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.set_margin_top(10)
        card.set_margin_bottom(12)
        card.set_margin_start(16)
        card.set_margin_end(16)

        # Heading row
        heading_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        heading_row.set_margin_bottom(8)

        heading_lbl = Gtk.Label(label=f"{icon}  {title}")
        heading_lbl.get_style_context().add_class("section-heading")
        heading_lbl.set_xalign(0)
        heading_row.pack_start(heading_lbl, True, True, 0)

        if stage_key and self._on_jump:
            edit_btn = Gtk.Button(label="✏  Edit")
            edit_btn.get_style_context().add_class("action-button")
            stage_idx = _STAGE[stage_key]
            edit_btn.connect("clicked", lambda _b, i=stage_idx: self._on_jump(i))
            heading_row.pack_end(edit_btn, False, False, 0)

        card.pack_start(heading_row, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(8)
        card.pack_start(sep, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(5)
        card.pack_start(grid, False, False, 0)

        frame.add(card)
        return frame, grid

    def _add_row(self, grid: Gtk.Grid, row: int, key: str, value: str,
                 value_class: str = "detail-value") -> int:
        """Append a key/value row to grid and return the next row index."""
        k = Gtk.Label(label=key)
        k.get_style_context().add_class("detail-key")
        k.set_xalign(1)
        k.set_valign(Gtk.Align.START)
        grid.attach(k, 0, row, 1, 1)

        v = Gtk.Label(label=value)
        v.get_style_context().add_class(value_class)
        v.set_xalign(0)
        v.set_line_wrap(True)
        v.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        v.set_hexpand(True)
        grid.attach(v, 1, row, 1, 1)

        return row + 1

    # ── Individual section cards ──────────────────────────────────────────────

    def _build_system_card(self) -> Gtk.Widget:
        s = self.state
        frame, grid = self._make_section_card(
            "System", "🖥", "sysconfig"
        )
        r = 0
        r = self._add_row(grid, r, "Hostname",   s.hostname or "—")
        r = self._add_row(grid, r, "Root pwd",
                          "✓ Set" if s.root_password else "⚠ Not set",
                          "status-ok" if s.root_password else "status-error")
        r = self._add_row(grid, r, "Locale",     s.locale)
        r = self._add_row(grid, r, "Keyboard",   s.keyboard_layout)
        r = self._add_row(grid, r, "Timezone",   s.timezone)
        r = self._add_row(grid, r, "NTP",        "Enabled" if s.enable_ntp else "Disabled")
        r = self._add_row(grid, r, "Initramfs",  getattr(s, "initramfs_generator", "mkinitcpio"))
        r = self._add_row(grid, r, "Network",
                          "Connected" if s.network_ok else
                          "Skipped" if s.network_skipped else "Not connected")
        return frame

    def _build_disk_card(self) -> Gtk.Widget:
        s = self.state
        frame, grid = self._make_section_card(
            "Disk & Partitions", "💾", "disk"
        )
        r = 0
        r = self._add_row(grid, r, "Target disk",  s.target_disk or "— not set —")
        r = self._add_row(grid, r, "Boot mode",    s.boot_mode.upper())
        r = self._add_row(grid, r, "Part. table",  s.partition_table.upper())
        r = self._add_row(grid, r, "Scheme",       s.partition_scheme.capitalize())
        r = self._add_row(grid, r, "Filesystem",   s.root_filesystem)
        if s.root_filesystem == "btrfs":
            r = self._add_row(grid, r, "Btrfs subvols",
                              "Yes" if s.btrfs_subvolumes else "No")
        r = self._add_row(grid, r, "Encryption",
                          "LUKS2 enabled" if s.luks_passphrase else "None",
                          "status-ok" if s.luks_passphrase else "detail-value")
        if s.swap_size_mb:
            r = self._add_row(grid, r, "Swap",
                              f"{s.swap_size_mb} MiB partition")
        elif s.use_swap_file:
            r = self._add_row(grid, r, "Swap", "Swap file")
        else:
            r = self._add_row(grid, r, "Swap", "None")

        # Partition table
        if s.partitions:
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_top(6)
            sep.set_margin_bottom(6)
            grid.attach(sep, 0, r, 2, 1)
            r += 1

            for p in s.partitions:
                from installer.ui.partition import _mb_to_human
                size_str = _mb_to_human(p.size_mb) if p.size_mb > 0 else "rest"
                enc_str  = " 🔐" if p.encrypt else ""
                val = f"{p.filesystem:<8}  {size_str}{enc_str}"
                r = self._add_row(grid, r, p.mountpoint or p.filesystem, val)

        return frame

    def _build_packages_card(self) -> Gtk.Widget:
        s = self.state
        frame, grid = self._make_section_card(
            "Packages", "📦", "packages"
        )
        r = 0
        r = self._add_row(grid, r, "Base",
                          "  ".join(s.base_packages))
        r = self._add_row(grid, r, "Desktop",
                          s.desktop_environment or "None (base only)")
        r = self._add_row(grid, r, "Disp. manager",
                          s.display_manager or "None")
        r = self._add_row(grid, r, "Net. manager",
                          s.network_manager or "None")

        mirror_count = len([
            l for l in s.mirrorlist.splitlines()
            if l.strip().startswith("Server")
        ])
        r = self._add_row(grid, r, "Mirrors",
                          f"{mirror_count} server{'s' if mirror_count != 1 else ''}"
                          if mirror_count else "— not configured —")

        extras = ", ".join(s.extra_packages) if s.extra_packages else "None"
        r = self._add_row(grid, r, "Extras", extras)

        return frame

    def _build_next_steps(self) -> Gtk.Widget:
        """Info card explaining what happens after confirmation."""
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.set_margin_top(10)
        card.set_margin_bottom(12)
        card.set_margin_start(16)
        card.set_margin_end(16)

        heading = Gtk.Label(label="⏭  After Confirmation")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        heading.set_margin_bottom(8)
        card.pack_start(heading, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(8)
        card.pack_start(sep, False, False, 0)

        steps = [
            ("Stage 13", "Base Install — partition, format, pacstrap, fstab, users"),
            ("Stage 14", "Bootloader — install and configure " + (self.state.bootloader or "grub")),
            ("Stage 15", "Complete — set locale, timezone, generate initramfs, reboot"),
        ]
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(5)
        for r, (key, val) in enumerate(steps):
            k = Gtk.Label(label=key)
            k.get_style_context().add_class("detail-key")
            k.set_xalign(1)
            grid.attach(k, 0, r, 1, 1)
            v = Gtk.Label(label=val)
            v.get_style_context().add_class("detail-value")
            v.set_xalign(0)
            grid.attach(v, 1, r, 1, 1)
        card.pack_start(grid, False, False, 0)

        frame.add(card)
        return frame

    def _build_users_card(self) -> Gtk.Widget:
        s = self.state
        frame, grid = self._make_section_card(
            "Users", "👤", "users"
        )
        r = 0
        if not s.users:
            r = self._add_row(grid, r, "Users",
                              "⚠  No users defined", "status-error")
        else:
            for u in s.users:
                sudo_str  = " (sudo)" if u.get("sudo") else ""
                shell_str = u.get("shell", "/bin/bash").replace("/bin/", "")
                groups    = u.get("groups", [])
                groups_str = ", ".join(groups) if groups else "—"
                val = f"{shell_str}{sudo_str}  •  groups: {groups_str}"
                r = self._add_row(grid, r, u["username"], val)

        return frame

    # ── Confirm checkbox ──────────────────────────────────────────────────────

    def _on_confirm_toggled(self, btn):
        self._confirmed = btn.get_active()
        if hasattr(self, "next_btn"):
            self.set_next_enabled(self._confirmed)

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        s = self.state
        if not s.target_disk:
            return False, "No target disk selected — go back to Stage 4."
        if not s.partitions:
            return False, "No partitions defined — go back to Stage 5."
        if not s.root_password:
            return False, "Root password not set — go back to Stage 10."
        if not s.users:
            return False, "No users defined — go back to Stage 11."
        if not self._confirmed:
            return False, "Tick the confirmation checkbox to continue."
        return True, ""

    def on_next(self):
        # Nothing to save — this screen is read-only.
        # Stage 13 (Install) will read directly from state.
        pass
