"""
installer/ui/partition.py
--------------------------
Stage 5 — Partition Scheme

The user chooses how to partition their selected disk:

  Auto   — the installer calculates a sensible layout. The user only
            decides about swap. Available at all experience levels.

  Manual — the user defines every partition themselves in an editable
            table. Available at Intermediate and Advanced only.

Nothing is written to disk here. This screen builds a list of
DiskPartition objects and stores them in state.partitions.
The actual partitioning happens much later, after the Review screen.

Saves to:
    state.partition_scheme  — 'auto' or 'manual'
    state.partitions        — list of DiskPartition objects
    state.swap_size_mb      — swap size in MB (0 = no swap partition)
    state.use_swap_file     — True if swap file chosen instead of partition
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from installer.ui.base_screen import BaseScreen
from installer.state import DiskPartition
from installer.backend.disk import get_disk_size_mb, get_ram_mb, suggest_swap_mb


# ── Constants ─────────────────────────────────────────────────────────────────

EFI_SIZE_MB   = 512     # EFI System Partition — 512MB is generous and safe
BOOT_SIZE_MB  = 512     # /boot for BIOS systems that need a separate boot partition

# Filesystems available in the manual partition editor
FILESYSTEMS = ["ext4", "btrfs", "xfs", "f2fs", "vfat", "swap"]


class PartitionScreen(BaseScreen):
    """Stage 5 — Partition Scheme selection screen."""

    # ── Screen metadata ───────────────────────────────────────────────────────
    title    = "Partition Scheme"
    subtitle = "Choose how to partition your disk"

    # ── Wiki links ────────────────────────────────────────────────────────────
    WIKI_LINKS = [
        ("Partitioning",          "https://wiki.archlinux.org/title/Partitioning"),
        ("EFI system partition",  "https://wiki.archlinux.org/title/EFI_system_partition"),
        ("Swap",                  "https://wiki.archlinux.org/title/Swap"),
        ("Btrfs",                 "https://wiki.archlinux.org/title/Btrfs"),
    ]

    def __init__(self, state, on_next, on_back):
        # Read disk info before super().__init__ because build_content() needs it
        self._disk_mb   = get_disk_size_mb(state.target_disk) if state.target_disk else 0
        self._ram_mb    = get_ram_mb()
        self._swap_suggestion_mb = suggest_swap_mb(self._ram_mb)

        # Current scheme choice — start with whatever's in state, default 'auto'
        self._scheme = state.partition_scheme or "auto"

        super().__init__(state=state, on_next=on_next, on_back=on_back)
        self.set_next_enabled(True)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        disk  = self.state.target_disk or "unknown"
        bmode = self.state.boot_mode.upper()
        ptbl  = self.state.partition_table.upper()
        return {
            "beginner": (
                f"🗂️  Partition Scheme\n\n"
                f"Disk: {disk}  •  Boot: {bmode}  •  Table: {ptbl}\n\n"
                "Automatic partitioning is recommended. The installer will "
                "create the correct layout for your system automatically.\n\n"
                "You only need to decide whether to include a swap partition. "
                "Swap acts as overflow memory when your RAM is full. "
                "It's recommended for most systems."
            ),
            "intermediate": (
                f"🗂️  Partition Scheme\n\n"
                f"Disk: {disk}  •  Boot: {bmode}  •  Table: {ptbl}\n\n"
                "Auto mode creates a standard layout:\n"
                "  UEFI: /boot (512MB, vfat) + swap + root\n"
                "  BIOS: /boot (512MB, ext4) + swap + root\n\n"
                "Manual mode lets you define your own partition table. "
                "Use this if you want a separate /home, specific sizes, "
                "or a non-standard layout.\n\n"
                "Swap as a partition is slightly faster; swap as a file "
                "is more flexible (easy to resize later)."
            ),
            "advanced": (
                f"🗂️  Partition Scheme\n\n"
                f"Disk: {disk}  •  Boot: {bmode}  •  Table: {ptbl}\n\n"
                "Auto generates a minimal layout. Manual gives full control.\n\n"
                "Required partitions:\n"
                "  UEFI: EFI vfat ≥ 300MB mounted at /boot/efi (or /boot)\n"
                "  BIOS: root partition only strictly required\n\n"
                "Btrfs users: select btrfs for root — subvolume layout "
                "is configured on the next screen.\n\n"
                "LUKS encryption is configured per-partition on the "
                "Filesystem screen (Stage 6)."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        # ── Disk summary banner ───────────────────────────────────────────────
        root.pack_start(self._build_disk_banner(), False, False, 0)

        # ── Scheme selector: Auto / Manual radio buttons ──────────────────────
        root.pack_start(self._build_scheme_selector(), False, False, 0)

        # ── Auto layout panel (shown when Auto is selected) ───────────────────
        self._auto_panel = self._build_auto_panel()
        root.pack_start(self._auto_panel, False, False, 0)

        # ── Manual layout panel (shown when Manual is selected) ───────────────
        self._manual_panel = self._build_manual_panel()
        root.pack_start(self._manual_panel, True, True, 0)

        # Show the correct panel for the initial scheme
        self._update_panels()

        return root

    # ── Disk summary banner ───────────────────────────────────────────────────

    def _build_disk_banner(self) -> Gtk.Widget:
        """Small card at the top reminding the user which disk they picked."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.get_style_context().add_class("card")
        box.set_margin_bottom(4)

        icon = Gtk.Label(label="💾")
        icon.set_margin_start(14)
        box.pack_start(icon, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_margin_top(10)
        info.set_margin_bottom(10)

        disk_lbl = Gtk.Label(
            label=f"Target disk: {self.state.target_disk or 'none selected'}"
        )
        disk_lbl.get_style_context().add_class("section-heading")
        disk_lbl.set_xalign(0)
        info.pack_start(disk_lbl, False, False, 0)

        size_str = _mb_to_human(self._disk_mb) if self._disk_mb else "unknown size"
        detail_lbl = Gtk.Label(
            label=f"{size_str}  •  {self.state.boot_mode.upper()}  •  "
                  f"{self.state.partition_table.upper()}"
        )
        detail_lbl.get_style_context().add_class("detail-value")
        detail_lbl.set_xalign(0)
        info.pack_start(detail_lbl, False, False, 0)

        box.pack_start(info, True, True, 0)
        return box

    # ── Scheme selector ───────────────────────────────────────────────────────

    def _build_scheme_selector(self) -> Gtk.Widget:
        """Auto / Manual radio buttons."""
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Partitioning method:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # Auto radio
        self._radio_auto = Gtk.RadioButton.new_with_label(None,
            "Automatic  —  let the installer create a standard layout")
        self._radio_auto.connect("toggled", self._on_scheme_toggled)
        box.pack_start(self._radio_auto, False, False, 0)

        # Manual radio (joined to the same group as auto)
        self._radio_manual = Gtk.RadioButton.new_with_label_from_widget(
            self._radio_auto,
            "Manual  —  define your own partition table"
        )
        self._radio_manual.connect("toggled", self._on_scheme_toggled)
        box.pack_start(self._radio_manual, False, False, 0)

        # Note shown for Beginner users under the Manual option
        self._manual_note = Gtk.Label(
            label="  ⚠️  Manual partitioning is available in Intermediate "
                  "and Advanced modes."
        )
        self._manual_note.get_style_context().add_class("detail-value")
        self._manual_note.set_xalign(0)
        self._manual_note.set_line_wrap(True)
        box.pack_start(self._manual_note, False, False, 0)

        frame.add(box)

        # Set initial radio state
        if self._scheme == "manual":
            self._radio_manual.set_active(True)
        else:
            self._radio_auto.set_active(True)

        # Apply experience-level visibility rules
        self._update_manual_availability()

        return frame

    def _on_scheme_toggled(self, btn):
        """Called when either radio button changes."""
        if not btn.get_active():
            return   # only act on the button being turned ON
        if btn == self._radio_auto:
            self._scheme = "auto"
        else:
            self._scheme = "manual"
        self._update_panels()

    def _update_manual_availability(self):
        """Beginner mode: disable Manual option and show the note."""
        is_beginner = self.state.experience_level == "beginner"
        self._radio_manual.set_sensitive(not is_beginner)
        if is_beginner:
            self._manual_note.show()
            # Force back to auto if beginner somehow had manual selected
            self._radio_auto.set_active(True)
            self._scheme = "auto"
        else:
            self._manual_note.hide()

    def on_experience_changed(self):
        """Called by BaseScreen when experience level changes."""
        self._update_manual_availability()
        self._update_panels()
        self.refresh_hints()

    # ── Auto layout panel ─────────────────────────────────────────────────────

    def _build_auto_panel(self) -> Gtk.Widget:
        """
        Shows the proposed automatic partition layout and swap options.
        Rebuilt whenever swap choice changes so the preview stays accurate.
        """
        self._auto_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Swap options
        swap_frame = Gtk.Frame()
        swap_frame.get_style_context().add_class("card")
        swap_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        swap_box.set_margin_start(14)
        swap_box.set_margin_end(14)
        swap_box.set_margin_top(12)
        swap_box.set_margin_bottom(12)

        swap_heading = Gtk.Label(label="Swap:")
        swap_heading.get_style_context().add_class("section-heading")
        swap_heading.set_xalign(0)
        swap_box.pack_start(swap_heading, False, False, 0)

        swap_mb   = self._swap_suggestion_mb
        swap_str  = _mb_to_human(swap_mb)
        ram_str   = _mb_to_human(self._ram_mb) if self._ram_mb else "unknown RAM"

        # No swap
        self._swap_none = Gtk.RadioButton.new_with_label(None, "No swap")
        self._swap_none.connect("toggled", self._on_swap_changed)
        swap_box.pack_start(self._swap_none, False, False, 0)

        # Swap partition
        self._swap_partition = Gtk.RadioButton.new_with_label_from_widget(
            self._swap_none,
            f"Swap partition  ({swap_str} recommended for {ram_str} RAM)"
        )
        self._swap_partition.connect("toggled", self._on_swap_changed)
        swap_box.pack_start(self._swap_partition, False, False, 0)

        # Swap file
        self._swap_file = Gtk.RadioButton.new_with_label_from_widget(
            self._swap_none,
            f"Swap file  ({swap_str} — easier to resize later)"
        )
        self._swap_file.connect("toggled", self._on_swap_changed)
        swap_box.pack_start(self._swap_file, False, False, 0)

        # Set initial swap state from state object
        if self.state.use_swap_file:
            self._swap_file.set_active(True)
        elif self.state.swap_size_mb > 0:
            self._swap_partition.set_active(True)
        else:
            self._swap_none.set_active(True)

        swap_frame.add(swap_box)
        self._auto_outer.pack_start(swap_frame, False, False, 0)

        # Layout preview
        preview_frame = Gtk.Frame()
        preview_frame.get_style_context().add_class("card")
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_box.set_margin_start(14)
        preview_box.set_margin_end(14)
        preview_box.set_margin_top(10)
        preview_box.set_margin_bottom(10)

        preview_heading = Gtk.Label(label="Proposed layout:")
        preview_heading.get_style_context().add_class("section-heading")
        preview_heading.set_xalign(0)
        preview_box.pack_start(preview_heading, False, False, 0)

        self._preview_label = Gtk.Label()
        self._preview_label.get_style_context().add_class("detail-value")
        self._preview_label.set_xalign(0)
        self._preview_label.set_line_wrap(True)
        preview_box.pack_start(self._preview_label, False, False, 0)

        preview_frame.add(preview_box)
        self._auto_outer.pack_start(preview_frame, False, False, 0)

        self._refresh_auto_preview()
        return self._auto_outer

    def _on_swap_changed(self, btn):
        if not btn.get_active():
            return
        self._refresh_auto_preview()

    def _get_swap_choice(self):
        """Return ('none'|'partition'|'file', size_mb)."""
        if self._swap_partition.get_active():
            return "partition", self._swap_suggestion_mb
        if self._swap_file.get_active():
            return "file", self._swap_suggestion_mb
        return "none", 0

    def _refresh_auto_preview(self):
        """Recalculate and display the auto partition layout preview."""
        swap_type, swap_mb = self._get_swap_choice()
        partitions = _build_auto_layout(
            disk_mb=self._disk_mb,
            boot_mode=self.state.boot_mode,
            swap_type=swap_type,
            swap_mb=swap_mb,
        )
        lines = []
        for p in partitions:
            size_str = _mb_to_human(p.size_mb) if p.size_mb > 0 else "rest of disk"
            lines.append(
                f"  {p.mountpoint or p.filesystem:<12}  "
                f"{p.filesystem:<8}  {size_str}"
            )
        self._preview_label.set_text("\n".join(lines) if lines else "No layout available")

    # ── Manual layout panel ───────────────────────────────────────────────────

    def _build_manual_panel(self) -> Gtk.Widget:
        """
        An editable table of partitions with Add / Edit / Delete buttons.
        Each row represents one partition the user wants to create.
        """
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        heading_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        heading_lbl = Gtk.Label(label="Partition table:")
        heading_lbl.get_style_context().add_class("section-heading")
        heading_row.pack_start(heading_lbl, True, True, 0)

        # Toolbar buttons
        self._add_btn = Gtk.Button(label="＋ Add")
        self._add_btn.get_style_context().add_class("action-button")
        self._add_btn.connect("clicked", self._on_add_partition)
        heading_row.pack_end(self._add_btn, False, False, 0)

        self._del_btn = Gtk.Button(label="✕ Remove")
        self._del_btn.get_style_context().add_class("action-button")
        self._del_btn.set_sensitive(False)
        self._del_btn.connect("clicked", self._on_delete_partition)
        heading_row.pack_end(self._del_btn, False, False, 0)

        self._edit_btn = Gtk.Button(label="✎ Edit")
        self._edit_btn.get_style_context().add_class("action-button")
        self._edit_btn.set_sensitive(False)
        self._edit_btn.connect("clicked", self._on_edit_partition)
        heading_row.pack_end(self._edit_btn, False, False, 0)

        outer.pack_start(heading_row, False, False, 0)

        # TreeView — columns: Mountpoint, Filesystem, Size, Encrypt
        # We store a hidden 0th column (index) so we know which DiskPartition
        # object to edit when the user clicks Edit.
        self._manual_store = Gtk.ListStore(int, str, str, str, str)
        # columns:            idx  mount  fs    size  encrypt

        tree = Gtk.TreeView(model=self._manual_store)
        tree.set_headers_visible(True)
        tree.get_selection().connect("changed", self._on_manual_selection_changed)
        self._manual_tree = tree

        for col_idx, (heading, store_col) in enumerate([
            ("Mountpoint",  1),
            ("Filesystem",  2),
            ("Size",        3),
            ("Encrypted",   4),
        ]):
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(heading, renderer, text=store_col)
            col.set_resizable(True)
            if col_idx == 0:
                col.set_expand(True)
            tree.append_column(col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(160)
        scrolled.get_style_context().add_class("card")
        scrolled.add(tree)
        outer.pack_start(scrolled, True, True, 0)

        # Validation message area
        self._manual_error = Gtk.Label(label="")
        self._manual_error.get_style_context().add_class("error-label")
        self._manual_error.set_xalign(0)
        self._manual_error.set_line_wrap(True)
        outer.pack_start(self._manual_error, False, False, 0)

        # Internal list that mirrors the TreeView rows
        self._manual_partitions = []

        # Pre-populate from state if coming Back
        if self.state.partitions and self.state.partition_scheme == "manual":
            for p in self.state.partitions:
                self._manual_partitions.append(p)
            self._rebuild_manual_store()

        return outer

    def _rebuild_manual_store(self):
        """Refresh the TreeView from self._manual_partitions."""
        self._manual_store.clear()
        for i, p in enumerate(self._manual_partitions):
            size_str = _mb_to_human(p.size_mb) if p.size_mb > 0 else "rest of disk"
            enc_str  = "Yes" if p.encrypt else "No"
            self._manual_store.append([i, p.mountpoint, p.filesystem, size_str, enc_str])

    def _on_manual_selection_changed(self, selection):
        has_sel = selection.get_selected()[1] is not None
        self._edit_btn.set_sensitive(has_sel)
        self._del_btn.set_sensitive(has_sel)

    def _on_add_partition(self, btn):
        self._open_partition_dialog(existing=None)

    def _on_edit_partition(self, btn):
        model, it = self._manual_tree.get_selection().get_selected()
        if it is None:
            return
        idx = model.get_value(it, 0)
        self._open_partition_dialog(existing=self._manual_partitions[idx], idx=idx)

    def _on_delete_partition(self, btn):
        model, it = self._manual_tree.get_selection().get_selected()
        if it is None:
            return
        idx = model.get_value(it, 0)
        self._manual_partitions.pop(idx)
        self._rebuild_manual_store()
        self._validate_manual()

    def _open_partition_dialog(self, existing=None, idx=None):
        """
        Open a small dialog to add or edit a partition.
        Fields: mountpoint (text), filesystem (dropdown), size in MB (spin, 0=rest),
        encrypt (checkbox).
        """
        is_edit = existing is not None
        title   = "Edit Partition" if is_edit else "Add Partition"

        dialog = Gtk.Dialog(
            title=title,
            transient_for=self.get_toplevel(),
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.set_default_size(360, 260)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("OK",     Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(12)
        content.set_margin_bottom(8)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # Mountpoint
        grid.attach(Gtk.Label(label="Mountpoint:"), 0, 0, 1, 1)
        mount_entry = Gtk.Entry()
        mount_entry.set_placeholder_text("e.g. /  /boot  /home  swap")
        mount_entry.set_hexpand(True)
        if existing:
            mount_entry.set_text(existing.mountpoint)
        grid.attach(mount_entry, 1, 0, 1, 1)

        # Filesystem
        grid.attach(Gtk.Label(label="Filesystem:"), 0, 1, 1, 1)
        fs_combo = Gtk.ComboBoxText()
        for fs in FILESYSTEMS:
            fs_combo.append_text(fs)
        if existing and existing.filesystem in FILESYSTEMS:
            fs_combo.set_active(FILESYSTEMS.index(existing.filesystem))
        else:
            fs_combo.set_active(0)   # default: ext4
        grid.attach(fs_combo, 1, 1, 1, 1)

        # Size
        grid.attach(Gtk.Label(label="Size (MB):"), 0, 2, 1, 1)
        size_spin = Gtk.SpinButton()
        size_adj  = Gtk.Adjustment(
            value=existing.size_mb if existing else 0,
            lower=0,
            upper=self._disk_mb if self._disk_mb else 2000000,
            step_increment=256,
            page_increment=1024,
        )
        size_spin.set_adjustment(size_adj)
        size_spin.set_numeric(True)
        size_hint = Gtk.Label(label="(0 = use remaining space)")
        size_hint.get_style_context().add_class("detail-value")
        size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        size_row.pack_start(size_spin, False, False, 0)
        size_row.pack_start(size_hint, False, False, 0)
        grid.attach(size_row, 1, 2, 1, 1)

        # Encrypt
        encrypt_check = Gtk.CheckButton(label="Encrypt this partition (LUKS)")
        if existing:
            encrypt_check.set_active(existing.encrypt)
        grid.attach(encrypt_check, 1, 3, 1, 1)

        content.pack_start(grid, False, False, 0)
        content.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            mountpoint = mount_entry.get_text().strip()
            filesystem = FILESYSTEMS[fs_combo.get_active()]
            size_mb    = int(size_spin.get_value())
            encrypt    = encrypt_check.get_active()

            # Build a device path placeholder — real device paths are assigned
            # at install time based on partition order
            device = f"{self.state.target_disk}{len(self._manual_partitions) + 1}"

            part = DiskPartition(
                device=device,
                mountpoint=mountpoint,
                filesystem=filesystem,
                size_mb=size_mb,
                encrypt=encrypt,
            )

            if is_edit and idx is not None:
                self._manual_partitions[idx] = part
            else:
                self._manual_partitions.append(part)

            self._rebuild_manual_store()
            self._validate_manual()

        dialog.destroy()

    def _validate_manual(self) -> bool:
        """
        Check that the manual partition list makes sense.
        Shows an inline error message if not. Returns True if valid.
        """
        parts = self._manual_partitions

        if not parts:
            self._manual_error.set_text(
                "Add at least a root (/) partition to continue."
            )
            return False

        mountpoints = [p.mountpoint for p in parts]

        # Must have a root partition
        if "/" not in mountpoints:
            self._manual_error.set_text(
                "⚠️  A root partition (/) is required."
            )
            return False

        # UEFI requires an EFI partition
        if self.state.boot_mode == "uefi":
            has_efi = any(
                p.filesystem == "vfat" and p.mountpoint in ("/boot", "/boot/efi", "/efi")
                for p in parts
            )
            if not has_efi:
                self._manual_error.set_text(
                    "⚠️  UEFI requires a vfat partition mounted at "
                    "/boot, /boot/efi, or /efi."
                )
                return False

        # No duplicate mountpoints (swap is allowed multiple times — unusual but valid)
        non_swap = [m for m in mountpoints if m != "swap"]
        if len(non_swap) != len(set(non_swap)):
            self._manual_error.set_text(
                "⚠️  Duplicate mountpoints found. Each mountpoint must be unique."
            )
            return False

        # Only one partition may have size_mb = 0 (rest of disk)
        zero_size = [p for p in parts if p.size_mb == 0]
        if len(zero_size) > 1:
            self._manual_error.set_text(
                "⚠️  Only one partition can use 'rest of disk' (size = 0). "
                "That should be your root (/) partition."
            )
            return False

        self._manual_error.set_text("")
        return True

    # ── Panel visibility ──────────────────────────────────────────────────────

    def _update_panels(self):
        """Show the correct panel based on the current scheme selection."""
        if self._scheme == "auto":
            self._auto_panel.show()
            self._manual_panel.hide()
        else:
            self._auto_panel.hide()
            self._manual_panel.show()

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if self._scheme == "manual":
            if not self._manual_partitions:
                return False, "Add at least one partition to continue."
            if not self._validate_manual():
                return False, "Fix the partition errors shown above before continuing."
        else:
            # Auto is always valid as long as we have a disk
            if not self.state.target_disk:
                return False, "No disk selected. Go back and select a disk."
        return True, ""

    def on_next(self):
        """Build the final partition list and save everything to state."""
        self.state.partition_scheme = self._scheme

        if self._scheme == "auto":
            swap_type, swap_mb = self._get_swap_choice()
            self.state.swap_size_mb  = swap_mb if swap_type == "partition" else 0
            self.state.use_swap_file = (swap_type == "file")
            self.state.partitions    = _build_auto_layout(
                disk_mb=self._disk_mb,
                boot_mode=self.state.boot_mode,
                swap_type=swap_type,
                swap_mb=swap_mb,
            )
        else:
            # Manual — partitions already in self._manual_partitions
            self.state.partitions    = list(self._manual_partitions)
            swap_parts = [p for p in self.state.partitions if p.filesystem == "swap"]
            self.state.swap_size_mb  = sum(p.size_mb for p in swap_parts)
            self.state.use_swap_file = False


# ── Helper functions ──────────────────────────────────────────────────────────

def _build_auto_layout(disk_mb: int, boot_mode: str,
                       swap_type: str, swap_mb: int) -> list:
    """
    Build the automatic partition layout as a list of DiskPartition objects.

    UEFI layout:
        /boot       vfat   512MB     (ESP - contains kernels + bootloader)
        swap        swap   swap_mb   (if swap_type == 'partition')
        /           ext4   rest

    BIOS layout:
        /boot       ext4   512MB     (Standard boot partition)
        swap        swap   swap_mb   (if swap_type == 'partition')
        /           ext4   rest

    Swap files don't appear in the partition list — they're created
    by the install backend after the root partition is mounted.
    """
    partitions = []

    # Always include a separate /boot partition.
    # For UEFI, /boot is the ESP (vfat). For BIOS, /boot is standard ext4.
    # This ensures that even with LUKS on root, the bootloader can reach
    # kernels and initramfs images without needing early decryption.
    boot_fs = "vfat" if boot_mode == "uefi" else "ext4"
    partitions.append(DiskPartition(
        device="",
        mountpoint="/boot",
        filesystem=boot_fs,
        size_mb=EFI_SIZE_MB if boot_mode == "uefi" else BOOT_SIZE_MB,
    ))

    if swap_type == "partition" and swap_mb > 0:
        partitions.append(DiskPartition(
            device="",
            mountpoint="swap",
            filesystem="swap",
            size_mb=swap_mb,
        ))

    # Root partition gets all remaining space (size_mb=0 means "rest of disk")
    partitions.append(DiskPartition(
        device="",
        mountpoint="/",
        filesystem="ext4",
        size_mb=0,
    ))

    return partitions


def _mb_to_human(mb: int) -> str:
    """Convert megabytes to a tidy human-readable string. e.g. 512 → '512M', 8192 → '8G'"""
    if mb <= 0:
        return "0M"
    if mb < 1024:
        return f"{mb}M"
    gb = mb / 1024
    if gb == int(gb):
        return f"{int(gb)}G"
    return f"{gb:.1f}G"
