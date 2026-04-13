"""
installer/ui/filesystem.py
---------------------------
Stage 6 — Filesystem + Encryption

The user chooses:
  1. The filesystem for the root partition (ext4 / btrfs / xfs / f2fs)
  2. Whether to use standard Btrfs subvolumes (if btrfs chosen)
  3. Whether to encrypt the system with LUKS

In Beginner mode:
  - Only ext4 is offered (safest, simplest)
  - Encryption is a single "Encrypt my system" checkbox
  - Btrfs options are hidden

In Intermediate mode:
  - ext4, btrfs, xfs are offered
  - Standard Btrfs subvolume layout is offered if btrfs chosen
  - Encryption is a single master toggle

In Advanced mode:
  - All filesystems including f2fs
  - Full Btrfs subvolume control
  - Per-partition encryption toggle (for manual partition layouts)

Saves to:
  state.root_filesystem    — 'ext4' | 'btrfs' | 'xfs' | 'f2fs'
  state.btrfs_subvolumes   — True if standard Btrfs subvolume layout wanted
  state.luks_passphrase    — passphrase string (empty = no encryption)
  state.partitions         — encrypt flag updated on relevant partitions
  state.bootloader_uki     — flagged True if encryption enabled (UKI note)
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from installer.ui.base_screen import BaseScreen


# ── Filesystem options per experience level ───────────────────────────────────

FS_OPTIONS = {
    "beginner":     ["ext4"],
    "intermediate": ["ext4", "btrfs", "xfs"],
    "advanced":     ["ext4", "btrfs", "xfs", "f2fs"],
}

# Human-readable descriptions shown under each filesystem button
FS_DESCRIPTIONS = {
    "ext4":  "Recommended. Stable, fast, and well-supported. Best choice for most users.",
    "btrfs": "Modern filesystem with snapshots, compression, and subvolume support. "
             "More complex but very powerful.",
    "xfs":   "High-performance filesystem. Good for large files and heavy workloads.",
    "f2fs":  "Flash-Friendly Filesystem. Optimised for SSDs and NVMe drives.",
}

from installer.state import BtrfsSubvolume

# Standard Btrfs subvolume layout (the @ naming convention)
BTRFS_SUBVOLS = [
    ("@",          "/",        "noatime,compress=zstd,space_cache=v2"),
    ("@home",      "/home",    "noatime,compress=zstd,space_cache=v2"),
    ("@snapshots", "/.snapshots", "noatime,compress=zstd,space_cache=v2"),
    ("@log",       "/var/log", "noatime,compress=zstd,space_cache=v2"),
    ("@cache",     "/var/cache", "noatime,compress=zstd,space_cache=v2"),
]


class FilesystemScreen(BaseScreen):
    """Stage 6 — Filesystem and Encryption screen."""

    # ── Screen metadata ───────────────────────────────────────────────────────
    title    = "Filesystem & Encryption"
    subtitle = "Choose how your disk will be formatted"

    # ── Wiki links ────────────────────────────────────────────────────────────
    WIKI_LINKS = [
        ("File systems",      "https://wiki.archlinux.org/title/File_systems"),
        ("Btrfs",             "https://wiki.archlinux.org/title/Btrfs"),
        ("dm-crypt / LUKS",   "https://wiki.archlinux.org/title/Dm-crypt"),
        ("Ext4",              "https://wiki.archlinux.org/title/Ext4"),
    ]

    def __init__(self, state, on_next, on_back):
        # Initialise choices from state (handles coming Back)
        self._root_fs      = state.root_filesystem or "ext4"
        self._encrypt      = bool(state.luks_passphrase)
        self._use_btrfs_subvols = state.use_btrfs_subvolumes
        self._custom_subvols = list(state.btrfs_subvolumes)

        super().__init__(state=state, on_next=on_next, on_back=on_back)
        self.set_next_enabled(True)



    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "💽  Filesystem & Encryption\n\n"
                "ext4 is the recommended filesystem for new Arch installs. "
                "It's fast, reliable, and supported everywhere.\n\n"
                "Encryption protects your data if your computer is lost or "
                "stolen. You'll enter a passphrase every time you boot.\n\n"
                "If you're not sure, leave encryption off for now — it can "
                "always be set up later."
            ),
            "intermediate": (
                "💽  Filesystem & Encryption\n\n"
                "ext4 is the safest choice. Btrfs adds snapshots and "
                "compression — great if you want to roll back changes. "
                "xfs is excellent for large files.\n\n"
                "Btrfs subvolumes allow you to take snapshots of @ (root) "
                "independently of @home, which is very useful.\n\n"
                "LUKS encryption wraps your partition in an encrypted "
                "container. The passphrase is required at every boot."
            ),
            "advanced": (
                "💽  Filesystem & Encryption\n\n"
                "Filesystem choice applies to the root partition. EFI and "
                "swap partitions keep their types regardless.\n\n"
                "Btrfs: standard @ subvolume layout is recommended. "
                "Compression (zstd) can be added post-install in fstab.\n\n"
                "LUKS2 is used for encryption (dm-crypt). If you plan to "
                "use a UKI bootloader (Stage 13), encryption requires "
                "the initramfs to include the decrypt hook — this is "
                "handled automatically but noted here for awareness.\n\n"
                "f2fs: flash-friendly, good for NVMe. Less mature than ext4."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        # ── Partition summary ─────────────────────────────────────────────────
        root.pack_start(self._build_partition_summary(), False, False, 0)

        # ── Filesystem selector ───────────────────────────────────────────────
        root.pack_start(self._build_fs_selector(), False, False, 0)

        # ── Btrfs subvolume options (shown only when btrfs selected) ──────────
        self._btrfs_section = self._build_btrfs_section()
        root.pack_start(self._btrfs_section, False, False, 0)

        # ── Encryption section ────────────────────────────────────────────────
        root.pack_start(self._build_encryption_section(), False, False, 0)

        # Defer visibility until after show_all() completes
        from gi.repository import GLib
        GLib.idle_add(self._apply_all_visibility)

        return root

    # ── Partition summary card ────────────────────────────────────────────────

    def _build_partition_summary(self) -> Gtk.Widget:
        """Show the planned partitions from Stage 5 as a read-only reference."""
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        heading = Gtk.Label(label="Planned partitions (from previous step):")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        if self.state.partitions:
            for p in self.state.partitions:
                from installer.ui.partition import _mb_to_human
                size_str = _mb_to_human(p.size_mb) if p.size_mb > 0 else "rest of disk"
                # Root partition filesystem will be set on this screen
                fs_str = p.filesystem if p.filesystem != "ext4" or p.mountpoint != "/" \
                         else f"{p.filesystem} ← choosing below"
                text = f"  {p.mountpoint or p.filesystem:<14}  {fs_str:<10}  {size_str}"
                lbl = Gtk.Label(label=text)
                lbl.get_style_context().add_class("detail-value")
                lbl.set_xalign(0)
                lbl.override_font(Pango.FontDescription("Monospace 10"))
                box.pack_start(lbl, False, False, 0)
        else:
            lbl = Gtk.Label(label="  No partitions defined — go back to Stage 5.")
            lbl.get_style_context().add_class("error-label")
            lbl.set_xalign(0)
            box.pack_start(lbl, False, False, 0)

        frame.add(box)
        return frame

    # ── Filesystem selector ───────────────────────────────────────────────────

    def _build_fs_selector(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Root filesystem:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # We'll store all radio buttons so we can show/hide based on level
        self._fs_radios = {}   # fs_name → (radio_btn, description_label)
        first_radio = None

        for fs in ["ext4", "btrfs", "xfs", "f2fs"]:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

            if first_radio is None:
                radio = Gtk.RadioButton.new_with_label(None, fs)
            else:
                radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, fs)
                # Keep first_radio as the group anchor — don't reassign it

            if first_radio is None:
                first_radio = radio

            radio.connect("toggled", self._on_fs_toggled, fs)
            row.pack_start(radio, False, False, 0)

            desc = Gtk.Label(label=f"    {FS_DESCRIPTIONS[fs]}")
            desc.get_style_context().add_class("detail-value")
            desc.set_xalign(0)
            desc.set_line_wrap(True)
            row.pack_start(desc, False, False, 0)

            box.pack_start(row, False, False, 0)
            self._fs_radios[fs] = (radio, row)

        frame.add(box)

        self._fs_frame = frame

        # Set the correct radio active
        if self._root_fs in self._fs_radios:
            self._fs_radios[self._root_fs][0].set_active(True)

        return frame

    def _on_fs_toggled(self, btn, fs_name):
        if not btn.get_active():
            return
        self._root_fs = fs_name
        self._update_btrfs_visibility()

    def _apply_fs_visibility(self):
        """Show only the filesystem options appropriate for the current level."""
        available = FS_OPTIONS.get(self.state.experience_level, ["ext4"])
        for fs, (radio, row) in self._fs_radios.items():
            if fs in available:
                row.show()
                radio.set_sensitive(True)
            else:
                row.hide()
                # If the currently selected fs is being hidden, fall back to ext4
                if self._root_fs == fs:
                    self._root_fs = "ext4"
                    self._fs_radios["ext4"][0].set_active(True)

    def _apply_all_visibility(self):
        """Apply all visibility rules. Called via idle_add after show_all()."""
        self._apply_fs_visibility()
        self._update_btrfs_visibility()
        self._update_encryption_visibility()
        return False  # GLib one-shot

    def on_experience_changed(self):
        """Called by BaseScreen when experience level changes."""
        self._apply_fs_visibility()
        self._update_btrfs_visibility()
        self._update_encryption_visibility()
        self.refresh_hints()

    # ── Btrfs subvolume section ───────────────────────────────────────────────

    def _build_btrfs_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Btrfs subvolume layout:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        self._btrfs_subvol_check = Gtk.CheckButton(
            label="Use Btrfs subvolumes"
        )
        self._btrfs_subvol_check.set_active(self._use_btrfs_subvols)
        self._btrfs_subvol_check.connect("toggled", self._on_btrfs_toggled)
        box.pack_start(self._btrfs_subvol_check, False, False, 0)

        self._btrfs_options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._btrfs_options_box.set_margin_start(24)

        # Radio buttons for Standard vs Custom
        radio_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self._subvol_mode_standard = Gtk.RadioButton.new_with_label(None, "Standard layout")
        self._subvol_mode_standard.connect("toggled", self._on_subvol_mode_toggled)
        radio_box.pack_start(self._subvol_mode_standard, False, False, 0)

        self._subvol_mode_custom = Gtk.RadioButton.new_with_label_from_widget(
            self._subvol_mode_standard, "Custom layout")
        self._subvol_mode_custom.connect("toggled", self._on_subvol_mode_toggled)
        radio_box.pack_start(self._subvol_mode_custom, False, False, 0)

        self._btrfs_options_box.pack_start(radio_box, False, False, 0)

        # Standard layout info
        self._standard_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for name, mount, opts in BTRFS_SUBVOLS:
            lbl = Gtk.Label(label=f"  {name:<12} → {mount}")
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            lbl.override_font(Pango.FontDescription("Monospace 9"))
            self._standard_info.pack_start(lbl, False, False, 0)
        self._btrfs_options_box.pack_start(self._standard_info, False, False, 0)

        # Custom layout table
        self._custom_layout_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_btn = Gtk.Button(label="＋ Add")
        add_btn.connect("clicked", self._on_add_subvol)
        toolbar.pack_start(add_btn, False, False, 0)
        edit_btn = Gtk.Button(label="✎ Edit")
        edit_btn.connect("clicked", self._on_edit_subvol)
        toolbar.pack_start(edit_btn, False, False, 0)
        del_btn = Gtk.Button(label="✕ Remove")
        del_btn.connect("clicked", self._on_delete_subvol)
        toolbar.pack_start(del_btn, False, False, 0)
        self._custom_layout_box.pack_start(toolbar, False, False, 0)

        self._subvol_store = Gtk.ListStore(int, str, str, str)
        self._subvol_tree = Gtk.TreeView(model=self._subvol_store)
        for i, h in enumerate(["#", "Name", "Mountpoint", "Options"]):
            res = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(h, res, text=i)
            self._subvol_tree.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(120)
        scroll.add(self._subvol_tree)
        self._custom_layout_box.pack_start(scroll, True, True, 0)

        self._btrfs_options_box.pack_start(self._custom_layout_box, True, True, 0)
        box.pack_start(self._btrfs_options_box, True, True, 0)

        frame.add(box)

        # Set initial subvol mode
        if self.state.btrfs_subvolumes:
             self._subvol_mode_custom.set_active(True)
             self._sync_subvol_store()
        else:
             self._subvol_mode_standard.set_active(True)

        return frame

    def _on_btrfs_toggled(self, btn):
        self._use_btrfs_subvols = btn.get_active()
        if self._use_btrfs_subvols:
            self._btrfs_options_box.show()
        else:
            self._btrfs_options_box.hide()

    def _on_subvol_mode_toggled(self, btn):
        if not btn.get_active(): return
        if btn == self._subvol_mode_standard:
            self._standard_info.show()
            self._custom_layout_box.hide()
        else:
            self._standard_info.hide()
            self._custom_layout_box.show()
            if not self._custom_subvols:
                # Pre-populate with standard if empty
                self._custom_subvols = [BtrfsSubvolume(name=n, mountpoint=m, options=o)
                                        for n, m, o in BTRFS_SUBVOLS]
                self._sync_subvol_store()

    def _sync_subvol_store(self):
        self._subvol_store.clear()
        for i, s in enumerate(self._custom_subvols):
            self._subvol_store.append([i, s.name, s.mountpoint, s.options])

    def _on_add_subvol(self, btn):
        self._open_subvol_dialog()

    def _on_edit_subvol(self, btn):
        model, it = self._subvol_tree.get_selection().get_selected()
        if it:
            idx = model.get_value(it, 0)
            self._open_subvol_dialog(self._custom_subvols[idx], idx)

    def _on_delete_subvol(self, btn):
        model, it = self._subvol_tree.get_selection().get_selected()
        if it:
            idx = model.get_value(it, 0)
            self._custom_subvols.pop(idx)
            self._sync_subvol_store()

    def _open_subvol_dialog(self, existing=None, idx=None):
        dialog = Gtk.Dialog(title="Btrfs Subvolume", transient_for=self.get_toplevel(), flags=Gtk.DialogFlags.MODAL)
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "OK", Gtk.ResponseType.OK)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=15)

        grid.attach(Gtk.Label(label="Name:"), 0, 0, 1, 1)
        name_ent = Gtk.Entry(text=existing.name if existing else "@")
        grid.attach(name_ent, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Mountpoint:"), 0, 1, 1, 1)
        mnt_ent = Gtk.Entry(text=existing.mountpoint if existing else "/")
        grid.attach(mnt_ent, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Options:"), 0, 2, 1, 1)
        opt_ent = Gtk.Entry(text=existing.options if existing else "noatime,compress=zstd,space_cache=v2")
        grid.attach(opt_ent, 1, 2, 1, 1)

        dialog.get_content_area().add(grid)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            new_sv = BtrfsSubvolume(name=name_ent.get_text(), mountpoint=mnt_ent.get_text(), options=opt_ent.get_text())
            if existing: self._custom_subvols[idx] = new_sv
            else: self._custom_subvols.append(new_sv)
            self._sync_subvol_store()
        dialog.destroy()

    def _update_btrfs_visibility(self):
        """Show Btrfs section only when btrfs is selected and level > beginner."""
        is_beginner = self.state.experience_level == "beginner"
        if self._root_fs == "btrfs" and not is_beginner:
            self._btrfs_section.show()
            self._on_btrfs_toggled(self._btrfs_subvol_check)
        else:
            self._btrfs_section.hide()

    # ── Encryption section ────────────────────────────────────────────────────

    def _build_encryption_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Encryption (LUKS):")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # Master enable toggle
        self._encrypt_check = Gtk.CheckButton(
            label="Encrypt the system partition"
        )
        self._encrypt_check.set_active(self._encrypt)
        self._encrypt_check.connect("toggled", self._on_encrypt_toggled)
        box.pack_start(self._encrypt_check, False, False, 0)

        # Warning shown when encryption is enabled
        self._encrypt_warning = Gtk.Label(
            label="⚠️  You will need to enter this passphrase every time you boot. "
                  "There is no way to recover your data if you forget it."
        )
        self._encrypt_warning.get_style_context().add_class("detail-value")
        self._encrypt_warning.set_xalign(0)
        self._encrypt_warning.set_line_wrap(True)
        box.pack_start(self._encrypt_warning, False, False, 0)

        # Passphrase fields (shown when encryption is on)
        self._passphrase_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        pass_row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pass_lbl1 = Gtk.Label(label="Passphrase:")
        pass_lbl1.get_style_context().add_class("detail-key")
        pass_lbl1.set_width_chars(14)
        pass_lbl1.set_xalign(1)
        pass_row1.pack_start(pass_lbl1, False, False, 0)

        self._pass_entry = Gtk.Entry()
        self._pass_entry.set_visibility(False)
        self._pass_entry.set_placeholder_text("Enter encryption passphrase")
        self._pass_entry.set_hexpand(True)
        self._pass_entry.connect("changed", self._on_passphrase_changed)
        pass_row1.pack_start(self._pass_entry, True, True, 0)

        # Show/hide passphrase toggle button
        self._show_pass_btn = Gtk.ToggleButton(label="👁")
        self._show_pass_btn.connect(
            "toggled",
            lambda btn: self._pass_entry.set_visibility(btn.get_active())
        )
        pass_row1.pack_start(self._show_pass_btn, False, False, 0)

        self._passphrase_box.pack_start(pass_row1, False, False, 0)

        pass_row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pass_lbl2 = Gtk.Label(label="Confirm:")
        pass_lbl2.get_style_context().add_class("detail-key")
        pass_lbl2.set_width_chars(14)
        pass_lbl2.set_xalign(1)
        pass_row2.pack_start(pass_lbl2, False, False, 0)

        self._pass_confirm = Gtk.Entry()
        self._pass_confirm.set_visibility(False)
        self._pass_confirm.set_placeholder_text("Confirm passphrase")
        self._pass_confirm.set_hexpand(True)
        self._pass_confirm.connect("changed", self._on_passphrase_changed)
        pass_row2.pack_start(self._pass_confirm, True, True, 0)

        self._passphrase_box.pack_start(pass_row2, False, False, 0)

        # Passphrase strength / match indicator
        self._pass_status = Gtk.Label(label="")
        self._pass_status.set_xalign(0)
        self._passphrase_box.pack_start(self._pass_status, False, False, 0)

        box.pack_start(self._passphrase_box, False, False, 0)

        # Pre-fill if coming Back with a passphrase already set
        if self.state.luks_passphrase:
            self._pass_entry.set_text(self.state.luks_passphrase)
            self._pass_confirm.set_text(self.state.luks_passphrase)

        frame.add(box)
        self._encrypt_frame = frame
        return frame

    def _on_encrypt_toggled(self, btn):
        self._encrypt = btn.get_active()
        self._update_encryption_visibility()

    def _update_encryption_visibility(self):
        """Show passphrase fields only when encryption is enabled."""
        if self._encrypt:
            self._passphrase_box.show()
            self._encrypt_warning.show()
        else:
            self._passphrase_box.hide()
            self._encrypt_warning.hide()
            # Clear entries and strength colouring when turning encryption off
            self._pass_entry.set_text("")
            self._pass_confirm.set_text("")
            self._pass_status.set_text("")
            self._set_entry_strength_class(self._pass_entry, None)
            self._set_entry_strength_class(self._pass_confirm, None)

    def _on_passphrase_changed(self, entry):
        """Live feedback on passphrase strength and match."""
        pw  = self._pass_entry.get_text()
        pw2 = self._pass_confirm.get_text()

        # Clear entry colouring and status when empty
        if not pw:
            self._pass_status.set_text("")
            self._set_entry_strength_class(self._pass_entry, None)
            self._set_entry_strength_class(self._pass_confirm, None)
            return

        strength, css_class = _passphrase_strength(pw)

        # Colour the password entry based on strength
        self._set_entry_strength_class(self._pass_entry, css_class)

        # Check match
        if pw2 and pw != pw2:
            self._pass_status.set_text("⚠️  Passphrases do not match")
            self._pass_status.get_style_context().remove_class("status-ok")
            self._pass_status.get_style_context().add_class("status-error")
            # Colour confirm entry red to signal mismatch
            self._set_entry_strength_class(self._pass_confirm, "passphrase-weak")
            return

        # Entries match (or confirm is empty) — colour confirm same as primary
        if pw2:
            self._set_entry_strength_class(self._pass_confirm, css_class)

        if pw2 and pw == pw2:
            self._pass_status.set_text(f"✓  Passphrases match  —  Strength: {strength}")
            self._pass_status.get_style_context().remove_class("status-error")
            self._pass_status.get_style_context().add_class("status-ok")
        else:
            self._pass_status.set_text(f"Strength: {strength}")
            self._pass_status.get_style_context().remove_class("status-ok")
            self._pass_status.get_style_context().remove_class("status-error")

    # All possible strength classes — we remove all before adding the new one
    # so they never stack on top of each other.
    _STRENGTH_CLASSES = [
        "passphrase-weak", "passphrase-fair",
        "passphrase-good", "passphrase-strong",
    ]

    def _set_entry_strength_class(self, entry, css_class):
        """
        Apply a single passphrase strength CSS class to an Entry widget,
        removing any previously applied strength class first.
        Pass css_class=None to clear all strength styling.
        """
        ctx = entry.get_style_context()
        for cls in self._STRENGTH_CLASSES:
            ctx.remove_class(cls)
        if css_class:
            ctx.add_class(css_class)

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if not self.state.partitions:
            return False, "No partitions defined. Go back and complete Stage 5."

        if self._encrypt:
            pw  = self._pass_entry.get_text()
            pw2 = self._pass_confirm.get_text()

            if not pw:
                return False, "Enter a passphrase for encryption, or disable encryption."
            if pw != pw2:
                return False, "Passphrases do not match."
            if len(pw) < 8:
                return False, "Passphrase must be at least 8 characters."

        return True, ""

    def on_next(self):
        """Save all filesystem and encryption choices to state."""
        self.state.root_filesystem  = self._root_fs

        # Only use Btrfs subvolumes if the root filesystem is Btrfs
        if self._root_fs == "btrfs":
            self.state.use_btrfs_subvolumes = self._use_btrfs_subvols
        else:
            self.state.use_btrfs_subvolumes = False

        if self.state.use_btrfs_subvolumes:
            if self._subvol_mode_standard.get_active():
                self.state.btrfs_subvolumes = [BtrfsSubvolume(name=n, mountpoint=m, options=o)
                                              for n, m, o in BTRFS_SUBVOLS]
            else:
                self.state.btrfs_subvolumes = list(self._custom_subvols)
        else:
            self.state.btrfs_subvolumes = []

        if self._encrypt:
            passphrase = self._pass_entry.get_text()
            self.state.luks_passphrase = passphrase

            # Mark the root partition (and /home if present) as encrypted
            for p in self.state.partitions:
                if p.mountpoint in ("/", "/home"):
                    p.encrypt = True

            # Flag for the bootloader stage — encrypted systems need the
            # decrypt hook in the initramfs, which affects UKI generation
            self.state.bootloader_uki_needs_decrypt = True
        else:
            self.state.luks_passphrase = ""
            for p in self.state.partitions:
                p.encrypt = False
            self.state.bootloader_uki_needs_decrypt = False

        # Update the root partition's filesystem in the partitions list
        # so the Review screen shows the correct value
        for p in self.state.partitions:
            if p.mountpoint == "/":
                p.filesystem = self._root_fs


# ── Helper ────────────────────────────────────────────────────────────────────

def _passphrase_strength(pw: str) -> tuple:
    """
    Return a (label, css_class) tuple describing passphrase strength.
    Starts at Weak/red immediately on first character typed.
    """
    if not pw:
        return "Weak", "passphrase-weak"
    # Start at 1 so colour appears immediately
    score = 1
    if len(pw) >= 8:  score += 1
    if len(pw) >= 12: score += 1
    if len(pw) >= 16: score += 1
    if any(c.isupper() for c in pw):     score += 1
    if any(c.islower() for c in pw):     score += 1
    if any(c.isdigit() for c in pw):     score += 1
    if any(not c.isalnum() for c in pw): score += 1

    if score <= 2: return "Weak",   "passphrase-weak"
    if score <= 4: return "Fair",   "passphrase-fair"
    if score <= 6: return "Good",   "passphrase-good"
    return              "Strong", "passphrase-strong"
