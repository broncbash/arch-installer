"""
installer/ui/disk_select.py
----------------------------
Stage 4 — Disk Selection

The user picks which physical drive to install Arch onto.
This screen only selects — nothing is written to disk here.

Also auto-detects UEFI vs BIOS boot mode and saves it to state,
since later stages (bootloader, partitioning) need to know this.

Saves to:
    state.target_disk   — e.g. '/dev/sda'
    state.boot_mode     — 'uefi' or 'bios'
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen
from installer.backend.disk import list_disks, detect_boot_mode


class DiskSelectScreen(BaseScreen):
    """Stage 4 — Disk Selection."""

    # ── Screen metadata ───────────────────────────────────────────────────────
    title    = "Disk Selection"
    subtitle = "Choose the drive to install Arch Linux on"

    # ── Wiki links ────────────────────────────────────────────────────────────
    WIKI_LINKS = [
        ("Installation guide — Partition",  "https://wiki.archlinux.org/title/Installation_guide#Partition_the_disks"),
        ("Partitioning",                    "https://wiki.archlinux.org/title/Partitioning"),
        ("Device naming",                   "https://wiki.archlinux.org/title/Persistent_block_device_naming"),
    ]

    def __init__(self, state, on_next, on_back):
        self._disks = []           # list of disk dicts from list_disks()
        self._selected_disk = None # the chosen disk dict, or None

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        # Next starts disabled — user must pick a disk
        self.set_next_enabled(False)

        # Detect boot mode immediately (fast, no thread needed)
        self.state.boot_mode = detect_boot_mode()

        # Load disk list in background
        self._load_disks_async()

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        boot = self.state.boot_mode.upper()
        return {
            "beginner": (
                f"💾  Disk Selection\n\n"
                f"Boot mode detected: {boot}\n\n"
                "Choose the drive you want to install Arch Linux on. "
                "Everything on that drive will be erased during installation.\n\n"
                "⚠️  If a drive shows existing partitions, it contains data. "
                "Make sure you have backups before selecting it.\n\n"
                "If you only see one drive, that's almost certainly the right one. "
                "USB drives and small drives are usually not what you want."
            ),
            "intermediate": (
                f"💾  Disk Selection\n\n"
                f"Boot mode detected: {boot}\n\n"
                "Select the target block device for installation. "
                "The full disk will be used — partition layout is configured "
                "in the next stage.\n\n"
                "NVMe drives appear as nvme0n1, nvme1n1 etc. "
                "SATA/USB drives appear as sda, sdb etc.\n\n"
                "⚠️  The selected disk will be wiped. Confirm you have "
                "backups of any data you need."
            ),
            "advanced": (
                f"💾  Disk Selection\n\n"
                f"Boot mode: {boot}\n"
                "Detected via /sys/firmware/efi presence.\n\n"
                "Selects the target block device. Partition table type "
                "(GPT/MBR) and layout are configured in Stage 5.\n\n"
                "GPT is used for UEFI systems. MBR is available for "
                "legacy BIOS systems in Intermediate/Advanced mode.\n\n"
                "Device list sourced from lsblk. Removable devices "
                "are flagged. Virtual disks (vda etc.) are shown for "
                "VM installs."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # ── Boot mode banner ──────────────────────────────────────────────────
        self._boot_banner = self._make_boot_banner()
        root.pack_start(self._boot_banner, False, False, 0)

        # ── Refresh button row ────────────────────────────────────────────────
        refresh_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        disks_lbl = Gtk.Label(label="Available drives:")
        disks_lbl.get_style_context().add_class("section-heading")
        disks_lbl.set_xalign(0)
        refresh_row.pack_start(disks_lbl, True, True, 0)

        self._refresh_btn = Gtk.Button(label="⟳  Refresh")
        self._refresh_btn.get_style_context().add_class("action-button")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        refresh_row.pack_end(self._refresh_btn, False, False, 0)

        root.pack_start(refresh_row, False, False, 0)

        # ── Disk list ─────────────────────────────────────────────────────────
        # Each disk is shown as a clickable card rather than a tree row,
        # because we want to show a lot of info per drive and cards look
        # much clearer than a table for non-technical users.
        self._disk_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.pack_start(self._disk_list_box, False, False, 0)

        # ── Loading spinner ───────────────────────────────────────────────────
        self._spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._spinner_box.set_halign(Gtk.Align.CENTER)
        spinner = Gtk.Spinner()
        spinner.start()
        self._spinner_box.pack_start(spinner, False, False, 0)
        spin_lbl = Gtk.Label(label="Scanning drives…")
        spin_lbl.get_style_context().add_class("detail-value")
        self._spinner_box.pack_start(spin_lbl, False, False, 0)
        root.pack_start(self._spinner_box, False, False, 0)

        # ── Warning banner (shown when a disk with data is selected) ──────────
        self._warning_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._warning_box.get_style_context().add_class("card")
        self._warning_box.set_margin_top(4)

        warn_icon = Gtk.Label(label="⚠️")
        warn_icon.set_margin_start(12)
        self._warning_box.pack_start(warn_icon, False, False, 0)

        self._warning_label = Gtk.Label()
        self._warning_label.get_style_context().add_class("error-label")
        self._warning_label.set_xalign(0)
        self._warning_label.set_line_wrap(True)
        self._warning_label.set_margin_top(10)
        self._warning_label.set_margin_bottom(10)
        self._warning_label.set_margin_end(12)
        self._warning_box.pack_start(self._warning_label, True, True, 0)

        self._warning_box.set_no_show_all(True)  # hidden by default
        root.pack_start(self._warning_box, False, False, 0)

        # ── Selected disk summary ─────────────────────────────────────────────
        self._summary_frame = Gtk.Frame()
        self._summary_frame.get_style_context().add_class("card")
        self._summary_frame.set_no_show_all(True)  # hidden until a disk is picked

        summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        summary_box.set_margin_start(14)
        summary_box.set_margin_end(14)
        summary_box.set_margin_top(10)
        summary_box.set_margin_bottom(10)

        sel_heading = Gtk.Label(label="Selected drive:")
        sel_heading.get_style_context().add_class("section-heading")
        sel_heading.set_xalign(0)
        summary_box.pack_start(sel_heading, False, False, 0)

        self._summary_label = Gtk.Label()
        self._summary_label.get_style_context().add_class("detail-value")
        self._summary_label.set_xalign(0)
        self._summary_label.set_line_wrap(True)
        summary_box.pack_start(self._summary_label, False, False, 0)

        self._summary_frame.add(summary_box)
        root.pack_start(self._summary_frame, False, False, 0)

        # ── Partition table type (Advanced + BIOS only) ───────────────────────
        self._pt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._pt_row.get_style_context().add_class("card")
        self._pt_row.set_margin_top(4)
        self._pt_row.set_no_show_all(True)

        pt_label = Gtk.Label(label="Partition table:")
        pt_label.get_style_context().add_class("section-heading")
        pt_label.set_margin_start(14)
        pt_label.set_margin_top(10)
        pt_label.set_margin_bottom(10)
        self._pt_row.pack_start(pt_label, False, False, 0)

        self._pt_gpt = Gtk.RadioButton.new_with_label(None, "GPT  (recommended)")
        self._pt_mbr = Gtk.RadioButton.new_with_label_from_widget(self._pt_gpt, "MBR  (legacy)")
        self._pt_gpt.set_margin_top(10)
        self._pt_gpt.set_margin_bottom(10)
        self._pt_mbr.set_margin_top(10)
        self._pt_mbr.set_margin_bottom(10)
        # Default to current state
        if self.state.partition_table == "mbr":
            self._pt_mbr.set_active(True)
        else:
            self._pt_gpt.set_active(True)
        self._pt_gpt.connect("toggled", self._on_pt_changed)
        self._pt_row.pack_start(self._pt_gpt, False, False, 0)
        self._pt_row.pack_start(self._pt_mbr, False, False, 0)

        root.pack_start(self._pt_row, False, False, 0)

        # Apply initial visibility
        GLib.idle_add(self._apply_visibility)

        return root

    def _apply_visibility(self):
        self.on_experience_changed()
        return False

    def _on_pt_changed(self, _btn):
        self.state.partition_table = "gpt" if self._pt_gpt.get_active() else "mbr"

    # ── Boot mode banner ──────────────────────────────────────────────────────

    def _make_boot_banner(self) -> Gtk.Widget:
        """Small banner showing the detected boot mode."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.get_style_context().add_class("card")
        box.set_margin_bottom(4)

        mode = self.state.boot_mode.upper()
        if self.state.boot_mode == "uefi":
            icon, colour_class = "✅", "status-ok"
            detail = "UEFI boot detected — GPT partition table will be used"
        else:
            icon, colour_class = "⚙️", "detail-value"
            detail = "BIOS/Legacy boot detected — MBR partition table will be used"

        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.set_margin_start(12)
        box.pack_start(icon_lbl, False, False, 0)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_margin_top(8)
        text_box.set_margin_bottom(8)

        mode_lbl = Gtk.Label(label=f"Boot mode: {mode}")
        mode_lbl.get_style_context().add_class(colour_class)
        mode_lbl.set_xalign(0)
        text_box.pack_start(mode_lbl, False, False, 0)

        detail_lbl = Gtk.Label(label=detail)
        detail_lbl.get_style_context().add_class("detail-value")
        detail_lbl.set_xalign(0)
        text_box.pack_start(detail_lbl, False, False, 0)

        box.pack_start(text_box, True, True, 0)
        return box

    def on_experience_changed(self):
        """Show/hide advanced options and rebuild disk cards when experience level changes."""
        level = self.state.experience_level
        # Show partition table selector only in Advanced + BIOS mode
        if hasattr(self, '_pt_row'):
            if level == 'advanced' and self.state.boot_mode == 'bios':
                self._pt_row.show()
            else:
                self._pt_row.hide()
        # Rebuild disk cards to show more/less technical detail
        if hasattr(self, '_disks') and self._disks:
            self._rebuild_disk_cards()

    # ── Async disk loading ────────────────────────────────────────────────────

    def _load_disks_async(self):
        """Scan drives in a background thread so the UI doesn't freeze."""
        self._refresh_btn.set_sensitive(False)
        self._spinner_box.show()

        def _worker():
            disks = list_disks()
            GLib.idle_add(self._on_disks_loaded, disks)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_disks_loaded(self, disks: list):
        """Called on the GTK main thread once the disk scan is complete."""
        self._disks = disks
        self._spinner_box.hide()
        self._refresh_btn.set_sensitive(True)
        self._rebuild_disk_cards()
        return False  # GLib one-shot

    def _on_refresh_clicked(self, btn):
        """Re-scan drives — useful if the user plugged something in."""
        self._selected_disk = None
        self._summary_frame.hide()
        self._warning_box.hide()
        self.set_next_enabled(False)

        # Clear existing cards
        for child in self._disk_list_box.get_children():
            self._disk_list_box.remove(child)
            child.destroy()

        self._load_disks_async()

    # ── Disk cards ────────────────────────────────────────────────────────────

    def _rebuild_disk_cards(self):
        """Remove any old cards and build fresh ones for the current disk list."""
        for child in self._disk_list_box.get_children():
            self._disk_list_box.remove(child)
            child.destroy()

        if not self._disks:
            no_disk_lbl = Gtk.Label(
                label="No drives found. Make sure your drive is connected and click Refresh."
            )
            no_disk_lbl.get_style_context().add_class("error-label")
            no_disk_lbl.set_line_wrap(True)
            self._disk_list_box.pack_start(no_disk_lbl, False, False, 0)
            self._disk_list_box.show_all()
            return

        for disk in self._disks:
            card = self._make_disk_card(disk)
            self._disk_list_box.pack_start(card, False, False, 0)

        self._disk_list_box.show_all()

        # If we already had a selection (e.g. user went Back and returned),
        # re-select it so the UI reflects the stored state
        if self.state.target_disk:
            for disk in self._disks:
                if disk["path"] == self.state.target_disk:
                    self._select_disk(disk)
                    break

    def _make_disk_card(self, disk: dict) -> Gtk.Widget:
        """
        Build a clickable card widget for one drive.
        Shows model, path, size, type, and existing partition count.
        """
        # EventBox makes the whole card clickable
        event_box = Gtk.EventBox()
        event_box.get_style_context().add_class("card")
        event_box.get_style_context().add_class("disk-card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_start(14)
        outer.set_margin_end(14)
        outer.set_margin_top(10)
        outer.set_margin_bottom(10)

        # ── Top row: icon + name + size ───────────────────────────────────────
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Drive type icon
        icon = _disk_icon(disk["disk_type"])
        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.set_valign(Gtk.Align.START)
        top_row.pack_start(icon_lbl, False, False, 0)

        # Name and model
        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        title_text = disk["path"]
        if disk["model"]:
            title_text += f"  —  {disk['model']}"

        title_lbl = Gtk.Label(label=title_text)
        title_lbl.get_style_context().add_class("section-heading")
        title_lbl.set_xalign(0)
        name_box.pack_start(title_lbl, False, False, 0)

        # Subtitle: type + size (+ technical details for Intermediate/Advanced)
        level = self.state.experience_level
        sub_text = f"{disk['disk_type']}  •  {disk['size_human']}"
        if disk["removable"]:
            sub_text += "  •  ⚠ Removable"
        sub_lbl = Gtk.Label(label=sub_text)
        sub_lbl.get_style_context().add_class("detail-value")
        sub_lbl.set_xalign(0)
        name_box.pack_start(sub_lbl, False, False, 0)

        if level in ("intermediate", "advanced"):
            # Extra technical row: transport + disk type details
            tech_parts = []
            transport = disk.get("transport", "")
            if transport:
                tech_parts.append(f"Transport: {transport.upper()}")
            disk_type = disk.get("disk_type", "")
            if disk_type and disk_type not in sub_text:
                tech_parts.append(disk_type)
            if disk.get("has_data"):
                tech_parts.append(f"{len(disk['partitions'])} existing partition(s)")
            if tech_parts:
                tech_lbl = Gtk.Label(label="  •  ".join(tech_parts))
                tech_lbl.get_style_context().add_class("detail-key")
                tech_lbl.set_xalign(0)
                name_box.pack_start(tech_lbl, False, False, 0)

        if level == "advanced" and disk.get("partitions"):
            # Show partition details inline on the card
            for part in disk["partitions"][:3]:
                fs  = part.get("fstype") or "unknown"
                mp  = f" → {part['mountpoint']}" if part.get("mountpoint") else ""
                sz  = part.get("size_human", "")
                p_lbl = Gtk.Label(label=f"  {part['path']}  {sz}  {fs}{mp}")
                p_lbl.get_style_context().add_class("detail-value")
                p_lbl.set_xalign(0)
                name_box.pack_start(p_lbl, False, False, 0)
            if len(disk["partitions"]) > 3:
                more_lbl = Gtk.Label(label=f"  … +{len(disk['partitions'])-3} more")
                more_lbl.get_style_context().add_class("detail-value")
                more_lbl.set_xalign(0)
                name_box.pack_start(more_lbl, False, False, 0)

        top_row.pack_start(name_box, True, True, 0)
        outer.pack_start(top_row, False, False, 0)

        # ── Partition list (if any) ───────────────────────────────────────────
        if disk["partitions"]:
            part_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            part_box.set_margin_top(8)
            part_box.set_margin_start(28)  # indent under the icon

            parts_heading = Gtk.Label(
                label=f"Contains {len(disk['partitions'])} existing partition(s):"
            )
            parts_heading.get_style_context().add_class("detail-key")
            parts_heading.set_xalign(0)
            part_box.pack_start(parts_heading, False, False, 0)

            # Show up to 4 partitions; summarise the rest
            for i, part in enumerate(disk["partitions"][:4]):
                fs   = part["fstype"] or "unknown"
                mp   = f"  mounted at {part['mountpoint']}" if part["mountpoint"] else ""
                lbl  = part["label"]
                text = f"  {part['path']}  {part['size_human']}  {fs}"
                if lbl:
                    text += f"  [{lbl}]"
                text += mp

                p_lbl = Gtk.Label(label=text)
                p_lbl.get_style_context().add_class("detail-value")
                p_lbl.set_xalign(0)
                part_box.pack_start(p_lbl, False, False, 0)

            if len(disk["partitions"]) > 4:
                more = Gtk.Label(
                    label=f"  … and {len(disk['partitions']) - 4} more"
                )
                more.get_style_context().add_class("detail-value")
                more.set_xalign(0)
                part_box.pack_start(more, False, False, 0)

            outer.pack_start(part_box, False, False, 0)

        event_box.add(outer)

        # Clicking anywhere on the card selects this disk
        event_box.connect("button-press-event",
                          lambda _w, _e, d=disk: self._select_disk(d))

        # Store a reference to the EventBox so we can update its CSS class
        disk["_card_widget"] = event_box

        return event_box

    # ── Selection logic ───────────────────────────────────────────────────────

    def _select_disk(self, disk: dict):
        """Handle the user clicking on a disk card."""

        # Remove 'selected' class from all cards
        for d in self._disks:
            w = d.get("_card_widget")
            if w:
                w.get_style_context().remove_class("disk-card-selected")

        # Add 'selected' class to the chosen card
        card = disk.get("_card_widget")
        if card:
            card.get_style_context().add_class("disk-card-selected")

        self._selected_disk = disk

        # Update the summary box
        self._update_summary(disk)

        # Show warning if the disk has existing data
        self._update_warning(disk)

        self.set_next_enabled(True)

    def _update_summary(self, disk: dict):
        """Update the selected drive summary box."""
        lines = [
            f"{disk['path']}  —  {disk['model'] or 'Unknown model'}",
            f"Size: {disk['size_human']}  •  Type: {disk['disk_type']}",
        ]
        if disk["partitions"]:
            lines.append(
                f"⚠️  Contains {len(disk['partitions'])} existing partition(s) — "
                "all data will be erased"
            )
        else:
            lines.append("No existing partitions detected")

        self._summary_label.set_text("\n".join(lines))
        self._summary_frame.show()

    def _update_warning(self, disk: dict):
        """Show or hide the data-loss warning based on whether the disk has data."""
        if disk["has_data"]:
            self._warning_label.set_text(
                f"The drive {disk['path']} contains existing partitions and data. "
                "Continuing will permanently erase everything on this drive. "
                "Make sure you have backups before proceeding."
            )
            self._warning_box.show()
        else:
            self._warning_box.hide()

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if not self._selected_disk:
            return False, "Please select a drive before continuing."
        return True, ""

    def on_next(self):
        """Save disk selection to state."""
        self.state.target_disk = self._selected_disk["path"]
        # boot_mode was already saved in __init__ via detect_boot_mode()
        # Set partition table default based on boot mode:
        #   UEFI → GPT (required for UEFI booting)
        #   BIOS → MBR (traditional default, GPT also works but is less common)
        self.state.partition_table = "gpt" if self.state.boot_mode == "uefi" else "mbr"


def _disk_icon(disk_type: str) -> str:
    """Return a simple emoji icon for a given disk type."""
    return {
        "NVMe SSD": "⚡",
        "SSD":      "💾",
        "HDD":      "💿",
        "USB":      "🔌",
        "Virtual":  "🖥️",
    }.get(disk_type, "💾")
