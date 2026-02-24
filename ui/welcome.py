"""
Stage 0 — Welcome / Experience Level screen
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

# Info panel text keyed by experience level
WELCOME_INFO = {
    "beginner": (
        "Welcome to the Arch Installer!\n\n"
        "This installer will guide you through setting up Arch Linux step by step. "
        "At the Beginner level, we'll use safe defaults and plain-English explanations "
        "so you don't need prior Linux experience.\n\n"
        "You can always go back and change your choices before anything is written to disk."
    ),
    "intermediate": (
        "Welcome to the Arch Installer.\n\n"
        "Intermediate mode exposes more configuration options with brief technical context. "
        "You'll have control over things like filesystem choice, mirrors, and bootloader, "
        "while advanced topics like LVM and encryption remain opt-in.\n\n"
        "Nothing is written to disk until the final Review & Confirm step."
    ),
    "advanced": (
        "Welcome to the Arch Installer.\n\n"
        "Advanced mode gives you full control over every stage of the installation — "
        "partition schemes, LUKS encryption, LVM, Btrfs subvolumes, bootloader choice, "
        "and manual package selection.\n\n"
        "All operations follow Arch Wiki standards. "
        "Disk writes happen only after explicit confirmation on the Review screen."
    ),
}

LEVEL_LABELS = {
    "beginner":     ("Beginner",     "Safe defaults · Plain-English guidance · Fewer choices"),
    "intermediate": ("Intermediate", "More options · Brief technical context · Opt-in extras"),
    "advanced":     ("Advanced",     "Full control · All options · Technical detail"),
}


class WelcomeScreen(Gtk.Box):
    """Stage 0 — Welcome and experience-level selection."""

    def __init__(self, state, on_next):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.state = state
        self.on_next = on_next
        self._selected_level = getattr(state, "experience_level", None) or "beginner"

        self._build_ui()
        self._update_info_panel()

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        # ── LEFT: main content ──────────────────────────────────────────────
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(480, -1)
        left.get_style_context().add_class("welcome-left")

        # Logo + title block
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header.set_margin_top(48)
        header.set_margin_start(48)
        header.set_margin_end(48)

        logo_label = Gtk.Label(label="󰣇")          # nerd-font Arch icon (fallback: plain text)
        logo_label.get_style_context().add_class("welcome-logo")

        title = Gtk.Label(label="Arch Linux Installer")
        title.get_style_context().add_class("welcome-title")
        title.set_halign(Gtk.Align.START)

        subtitle = Gtk.Label(label="Version 0.1.0  ·  GPLv3")
        subtitle.get_style_context().add_class("welcome-subtitle")
        subtitle.set_halign(Gtk.Align.START)

        header.pack_start(logo_label, False, False, 0)
        header.pack_start(title,      False, False, 0)
        header.pack_start(subtitle,   False, False, 0)
        left.pack_start(header, False, False, 0)

        # Divider
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(32)
        sep.set_margin_bottom(24)
        sep.set_margin_start(48)
        sep.set_margin_end(48)
        left.pack_start(sep, False, False, 0)

        # Section label
        choose_lbl = Gtk.Label(label="Choose your experience level")
        choose_lbl.get_style_context().add_class("section-label")
        choose_lbl.set_halign(Gtk.Align.START)
        choose_lbl.set_margin_start(48)
        choose_lbl.set_margin_bottom(16)
        left.pack_start(choose_lbl, False, False, 0)

        # Experience level cards
        self._cards = {}
        cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        cards_box.set_margin_start(48)
        cards_box.set_margin_end(48)

        for level in ("beginner", "intermediate", "advanced"):
            card = self._make_level_card(level)
            cards_box.pack_start(card, False, False, 0)
            self._cards[level] = card

        left.pack_start(cards_box, False, False, 0)

        # Spacer
        left.pack_start(Gtk.Box(), True, True, 0)

        # Next button row
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        btn_row.set_margin_start(48)
        btn_row.set_margin_end(48)
        btn_row.set_margin_bottom(40)
        btn_row.set_margin_top(16)

        self.next_btn = Gtk.Button(label="Continue  →")
        self.next_btn.get_style_context().add_class("next-button")
        self.next_btn.set_halign(Gtk.Align.END)
        self.next_btn.connect("clicked", self._on_next_clicked)
        btn_row.pack_end(self.next_btn, False, False, 0)

        left.pack_start(btn_row, False, False, 0)

        # ── RIGHT: info panel ───────────────────────────────────────────────
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right.get_style_context().add_class("info-panel")
        right.set_size_request(340, -1)

        info_header = Gtk.Label(label="ℹ  About this level")
        info_header.get_style_context().add_class("info-panel-header")
        info_header.set_halign(Gtk.Align.START)
        info_header.set_margin_start(28)
        info_header.set_margin_top(32)
        info_header.set_margin_bottom(16)
        right.pack_start(info_header, False, False, 0)

        self.info_text = Gtk.Label()
        self.info_text.set_line_wrap(True)
        self.info_text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.info_text.set_halign(Gtk.Align.START)
        self.info_text.set_valign(Gtk.Align.START)
        self.info_text.set_margin_start(28)
        self.info_text.set_margin_end(24)
        self.info_text.get_style_context().add_class("info-panel-text")
        right.pack_start(self.info_text, False, False, 0)

        # ── Assemble ────────────────────────────────────────────────────────
        self.pack_start(left,  True,  True,  0)
        self.pack_start(right, False, False, 0)

        self._highlight_selected()

    def _make_level_card(self, level):
        name, desc = LEVEL_LABELS[level]

        card = Gtk.EventBox()
        card.get_style_context().add_class("level-card")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_top(14)
        inner.set_margin_bottom(14)
        inner.set_margin_start(18)
        inner.set_margin_end(18)

        name_lbl = Gtk.Label(label=name)
        name_lbl.get_style_context().add_class("card-title")
        name_lbl.set_halign(Gtk.Align.START)

        desc_lbl = Gtk.Label(label=desc)
        desc_lbl.get_style_context().add_class("card-desc")
        desc_lbl.set_halign(Gtk.Align.START)
        desc_lbl.set_line_wrap(True)

        inner.pack_start(name_lbl, False, False, 0)
        inner.pack_start(desc_lbl, False, False, 0)
        card.add(inner)

        card.connect("button-press-event", lambda w, e, lv=level: self._select_level(lv))
        card.connect("enter-notify-event", lambda w, e: w.get_style_context().add_class("hover"))
        card.connect("leave-notify-event", lambda w, e: w.get_style_context().remove_class("hover"))

        return card

    # ----------------------------------------------------------------- state

    def _select_level(self, level):
        self._selected_level = level
        self._highlight_selected()
        self._update_info_panel()

    def _highlight_selected(self):
        for lv, card in self._cards.items():
            ctx = card.get_style_context()
            if lv == self._selected_level:
                ctx.add_class("selected")
            else:
                ctx.remove_class("selected")

    def _update_info_panel(self):
        self.info_text.set_text(WELCOME_INFO[self._selected_level])

    def _on_next_clicked(self, _btn):
        self.state.experience_level = self._selected_level
        self.on_next()
