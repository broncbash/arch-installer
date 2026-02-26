#!/usr/bin/env python3
"""
installer/ui/bootloader.py — Stage 13: Bootloader selection.

Beginner:      GRUB, systemd-boot
Intermediate:  + rEFInd
Advanced:      + EFIStub, UKI

If LUKS is enabled and UKI is selected, a decrypt hook warning is shown
and state.bootloader_uki_needs_decrypt is set to True.

Saves to:
  state.bootloader                   — 'grub'|'systemd-boot'|'refind'|'efistub'|'uki'
  state.bootloader_uki               — True if UKI selected
  state.bootloader_uki_needs_decrypt — True if UKI + LUKS
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from installer.ui.base_screen import BaseScreen


# ── Bootloader definitions ────────────────────────────────────────────────────

_BOOTLOADERS = [
    {
        "id":       "grub",
        "name":     "GRUB",
        "levels":   {"beginner", "intermediate", "advanced"},
        "icon":     "🐧",
        "subtitle": "Most compatible — UEFI and legacy BIOS",
    },
    {
        "id":       "systemd-boot",
        "name":     "systemd-boot",
        "levels":   {"beginner", "intermediate", "advanced"},
        "icon":     "⚡",
        "subtitle": "Fast and minimal — UEFI only",
    },
    {
        "id":       "refind",
        "name":     "rEFInd",
        "levels":   {"intermediate", "advanced"},
        "icon":     "🔍",
        "subtitle": "Auto-detects kernels — UEFI only",
    },
    {
        "id":       "efistub",
        "name":     "EFIStub",
        "levels":   {"advanced"},
        "icon":     "🔩",
        "subtitle": "Kernel boots directly — no extra software",
    },
    {
        "id":       "uki",
        "name":     "UKI (Unified Kernel Image)",
        "levels":   {"advanced"},
        "icon":     "🧬",
        "subtitle": "Kernel + initramfs in one signed EFI binary",
    },
]


class BootloaderScreen(BaseScreen):
    """Stage 13 — Bootloader selection."""

    title    = "Bootloader"
    subtitle = "Choose how your system will boot"

    WIKI_LINKS = [
        ("GRUB",                 "https://wiki.archlinux.org/title/GRUB"),
        ("systemd-boot",         "https://wiki.archlinux.org/title/Systemd-boot"),
        ("rEFInd",               "https://wiki.archlinux.org/title/REFInd"),
        ("EFISTUB",              "https://wiki.archlinux.org/title/EFISTUB"),
        ("Unified kernel image", "https://wiki.archlinux.org/title/Unified_kernel_image"),
    ]

    def __init__(self, state, on_next, on_back=None):
        self._selected_id = state.bootloader or "grub"
        # Populated in build_content(); used in on_experience_changed()
        self._card_box: Gtk.Box | None = None
        self._luks_warning: Gtk.Box | None = None
        self._bios_warning: Gtk.Label | None = None
        super().__init__(state=state, on_next=on_next, on_back=on_back)
        self.set_next_enabled(True)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "🥾  Bootloader\n\n"
                "The bootloader is the small program that starts your OS "
                "when you power on your machine.\n\n"
                "GRUB works on virtually every PC — old BIOS and modern UEFI. "
                "It's the safest pick if you're not sure.\n\n"
                "systemd-boot is simpler and faster but only works on modern "
                "UEFI machines (most computers made after ~2012).\n\n"
                "When in doubt, choose GRUB."
            ),
            "intermediate": (
                "🥾  Bootloader\n\n"
                "GRUB is the most flexible option — supports BIOS/UEFI, LUKS, "
                "LVM, and multi-boot. Main config: /etc/default/grub, "
                "regenerated with grub-mkconfig.\n\n"
                "systemd-boot is lightweight; each kernel gets a plain-text "
                "entry in /boot/loader/entries/. UEFI only.\n\n"
                "rEFInd auto-discovers kernels on any partition — great for "
                "multi-boot without manual config. UEFI only."
            ),
            "advanced": (
                "🥾  Bootloader\n\n"
                "GRUB: grub-install + grub-mkconfig. Full GRUB_CMDLINE_LINUX "
                "control, rescue shell, native LUKS2 support.\n\n"
                "systemd-boot: Type 1 (.conf) and Type 2 (UKI .efi) entries; "
                "random-seed; sbsign for Secure Boot.\n\n"
                "rEFInd: EFI executable scanning; MOK/shim for Secure Boot.\n\n"
                "EFIStub: kernel loaded directly by UEFI firmware; use "
                "efibootmgr to create NVRAM entries. Minimal attack surface.\n\n"
                "UKI: single signed .efi bundles kernel + initramfs + cmdline. "
                "Required for Secure Boot without shim. If LUKS is enabled the "
                "initramfs needs the encrypt hook — added automatically here."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # ── BIOS mode notice ──────────────────────────────────────────────────
        self._bios_warning = Gtk.Label(
            label="⚠️  BIOS / legacy boot detected — only GRUB supports this mode."
        )
        self._bios_warning.get_style_context().add_class("error-label")
        self._bios_warning.set_xalign(0)
        self._bios_warning.set_line_wrap(True)
        self._bios_warning.set_no_show_all(True)
        if self.state.boot_mode == "bios":
            self._bios_warning.show()
        root.pack_start(self._bios_warning, False, False, 0)

        # ── Card list (rebuilt whenever experience level changes) ─────────────
        self._card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.pack_start(self._card_box, False, False, 0)

        # ── LUKS + UKI warning ────────────────────────────────────────────────
        self._luks_warning = self._build_luks_warning()
        root.pack_start(self._luks_warning, False, False, 0)

        # Populate cards after show_all() so hide() calls work correctly
        GLib.idle_add(self._apply_visibility)

        return root

    # ── LUKS warning widget ───────────────────────────────────────────────────

    def _build_luks_warning(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.get_style_context().add_class("dry-run-banner")
        box.set_no_show_all(True)

        icon = Gtk.Label(label="🔐")
        icon.set_margin_start(10)
        box.pack_start(icon, False, False, 0)

        msg = Gtk.Label(
            label=(
                "LUKS encryption is enabled. When using a UKI the initramfs "
                "must include the encrypt hook — this installer adds it automatically."
            )
        )
        msg.get_style_context().add_class("dry-run-text")
        msg.set_line_wrap(True)
        msg.set_xalign(0)
        msg.set_margin_top(8)
        msg.set_margin_bottom(8)
        msg.set_margin_end(10)
        box.pack_start(msg, True, True, 0)

        return box

    # ── Card builder ──────────────────────────────────────────────────────────

    def _rebuild_cards(self):
        """Clear and repopulate the card list for the current experience level."""
        for child in self._card_box.get_children():
            self._card_box.remove(child)
            child.destroy()

        level = self.state.experience_level
        available = [bl for bl in _BOOTLOADERS if level in bl["levels"]]

        # If the current selection isn't available at this level, reset to grub
        if not any(bl["id"] == self._selected_id for bl in available):
            self._selected_id = "grub"

        for bl in available:
            evbox = Gtk.EventBox()
            evbox.connect("button-press-event", self._on_card_clicked, bl["id"])

            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            card.get_style_context().add_class("disk-card")
            if bl["id"] == self._selected_id:
                card.get_style_context().add_class("disk-card-selected")

            # Header row: icon | name | checkmark
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            header.set_margin_top(12)
            header.set_margin_bottom(4)
            header.set_margin_start(14)
            header.set_margin_end(14)

            icon_lbl = Gtk.Label(label=bl["icon"])
            header.pack_start(icon_lbl, False, False, 0)

            name_lbl = Gtk.Label(label=bl["name"])
            name_lbl.get_style_context().add_class("section-heading")
            name_lbl.set_xalign(0)
            header.pack_start(name_lbl, True, True, 0)

            check = Gtk.Label(label="✓")
            check.get_style_context().add_class("status-ok")
            check.set_no_show_all(True)
            if bl["id"] == self._selected_id:
                check.show()
            header.pack_end(check, False, False, 0)

            card.pack_start(header, False, False, 0)

            # Subtitle row
            sub = Gtk.Label(label=bl["subtitle"])
            sub.get_style_context().add_class("detail-value")
            sub.set_xalign(0)
            sub.set_margin_start(14)
            sub.set_margin_end(14)
            sub.set_margin_bottom(10)
            card.pack_start(sub, False, False, 0)

            evbox.add(card)
            self._card_box.pack_start(evbox, False, False, 0)

        self._card_box.show_all()
        self._refresh_warnings()

    # ── Visibility / warnings ─────────────────────────────────────────────────

    def _apply_visibility(self):
        """One-shot idle callback — runs after show_all() so hide() works."""
        self._rebuild_cards()
        return False

    def _refresh_warnings(self):
        """Show/hide the LUKS warning; gate Next if BIOS + non-GRUB."""
        show_luks = (
            self._selected_id == "uki"
            and bool(self.state.luks_passphrase)
        )
        if show_luks:
            self._luks_warning.show()
        else:
            self._luks_warning.hide()

        if hasattr(self, "next_btn"):
            if self.state.boot_mode == "bios" and self._selected_id != "grub":
                self.set_next_enabled(False)
                self.error_label.set_text("⚠  Legacy BIOS mode: only GRUB is supported.")
            else:
                self.set_next_enabled(True)
                self.error_label.set_text("")

    # ── Experience level change ───────────────────────────────────────────────

    def on_experience_changed(self):
        """Called by BaseScreen when the experience level combo changes."""
        if self._card_box is not None:
            self._rebuild_cards()

    # ── Card selection ────────────────────────────────────────────────────────

    def _on_card_clicked(self, _evbox, _event, bl_id: str):
        if bl_id == self._selected_id:
            return

        # Walk every EventBox → card → header to toggle styles and checkmarks
        for evbox in self._card_box.get_children():
            card = evbox.get_child()
            if not card or not card.get_children():
                continue
            header = card.get_children()[0]

            # Determine this card's bootloader id from the name label text
            name_text = ""
            for w in header.get_children():
                if isinstance(w, Gtk.Label) and w.get_text() != "✓":
                    # Skip the icon (single emoji) — take the longer name label
                    if len(w.get_text()) > 2:
                        name_text = w.get_text()
                        break

            bl = next((b for b in _BOOTLOADERS if b["name"] == name_text), None)
            if bl is None:
                continue

            if bl["id"] == bl_id:
                card.get_style_context().add_class("disk-card-selected")
            else:
                card.get_style_context().remove_class("disk-card-selected")

            for w in header.get_children():
                if isinstance(w, Gtk.Label) and w.get_text() == "✓":
                    if bl["id"] == bl_id:
                        w.show()
                    else:
                        w.hide()

        self._selected_id = bl_id
        self._refresh_warnings()

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if self.state.boot_mode == "bios" and self._selected_id != "grub":
            return False, "Legacy BIOS mode: only GRUB is supported."
        return True, ""

    def on_next(self):
        self.state.bootloader = self._selected_id
        self.state.bootloader_uki = (self._selected_id == "uki")
        self.state.bootloader_uki_needs_decrypt = (
            self._selected_id == "uki" and bool(self.state.luks_passphrase)
        )
