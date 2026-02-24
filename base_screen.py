"""
installer/ui/base_screen.py
---------------------------
Base class for every installer screen.
Provides:
  - Standard two-column layout (content left, info panel right)
  - Info panel that updates based on experience level
  - Navigation buttons (Back / Next)
  - Consistent styling hooks
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

from installer.state import InstallState


class BaseScreen(Gtk.Box):
    """
    Inherit from this for every installer stage screen.

    Subclasses must implement:
        build_content(self) -> Gtk.Widget
            Return the left-side content widget for this screen.

        get_hints(self) -> dict
            Return a dict with keys 'beginner', 'intermediate', 'advanced'
            mapping to hint strings shown in the info panel.

        validate(self) -> (bool, str)
            Return (True, "") if the user's selections are valid and we can
            proceed, or (False, "reason") to block navigation and show a message.

        on_next(self)
            Called when Next is clicked and validate() passes.
            Write selections back to self.state here.
    """

    # Subclasses set these
    title: str = "Screen Title"
    subtitle: str = ""

    def __init__(self, state: InstallState,
                 on_back=None, on_next=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.state = state
        self._on_back_cb = on_back
        self._on_next_cb = on_next

        self._build_shell()
        self.refresh_hints()

    # ── Shell layout ─────────────────────────────────────────────────────────

    def _build_shell(self):
        # Title bar
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_box.get_style_context().add_class("screen-title-box")
        title_box.set_margin_start(32)
        title_box.set_margin_end(32)
        title_box.set_margin_top(24)
        title_box.set_margin_bottom(16)

        title_lbl = Gtk.Label(label=self.title)
        title_lbl.get_style_context().add_class("screen-title")
        title_lbl.set_halign(Gtk.Align.START)
        title_box.pack_start(title_lbl, False, False, 0)

        if self.subtitle:
            sub_lbl = Gtk.Label(label=self.subtitle)
            sub_lbl.get_style_context().add_class("screen-subtitle")
            sub_lbl.set_halign(Gtk.Align.START)
            title_box.pack_start(sub_lbl, False, False, 0)

        self.pack_start(title_box, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("screen-sep")
        self.pack_start(sep, False, False, 0)

        # Main body: content (left) + info panel (right)
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_hexpand(True)
        body.set_vexpand(True)

        # Content area
        content_scroll = Gtk.ScrolledWindow()
        content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content_scroll.set_hexpand(True)
        content_scroll.set_vexpand(True)

        content_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_wrapper.set_margin_start(32)
        content_wrapper.set_margin_end(24)
        content_wrapper.set_margin_top(24)
        content_wrapper.set_margin_bottom(24)

        self.content_widget = self.build_content()
        content_wrapper.pack_start(self.content_widget, True, True, 0)
        content_scroll.add(content_wrapper)
        body.pack_start(content_scroll, True, True, 0)

        # Info panel (fixed width)
        info_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        info_panel.get_style_context().add_class("info-panel")
        info_panel.set_size_request(280, -1)

        info_header = Gtk.Label(label="💡  Hints & Info")
        info_header.get_style_context().add_class("info-panel-header")
        info_header.set_halign(Gtk.Align.START)
        info_header.set_margin_start(16)
        info_header.set_margin_end(16)
        info_header.set_margin_top(20)
        info_header.set_margin_bottom(12)
        info_panel.pack_start(info_header, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        info_panel.pack_start(sep2, False, False, 0)

        info_scroll = Gtk.ScrolledWindow()
        info_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        info_scroll.set_vexpand(True)

        self.hint_label = Gtk.Label()
        self.hint_label.get_style_context().add_class("info-panel-text")
        self.hint_label.set_halign(Gtk.Align.START)
        self.hint_label.set_valign(Gtk.Align.START)
        self.hint_label.set_line_wrap(True)
        self.hint_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.hint_label.set_margin_start(16)
        self.hint_label.set_margin_end(16)
        self.hint_label.set_margin_top(12)
        self.hint_label.set_margin_bottom(12)
        info_scroll.add(self.hint_label)
        info_panel.pack_start(info_scroll, True, True, 0)

        # Experience level selector inside info panel
        level_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        level_box.set_margin_start(16)
        level_box.set_margin_end(16)
        level_box.set_margin_top(12)
        level_box.set_margin_bottom(16)

        level_lbl = Gtk.Label(label="Experience Level")
        level_lbl.get_style_context().add_class("info-panel-header")
        level_lbl.set_halign(Gtk.Align.START)
        level_box.pack_start(level_lbl, False, False, 0)

        self._level_combo = Gtk.ComboBoxText()
        for level in ["Beginner", "Intermediate", "Advanced"]:
            self._level_combo.append_text(level)
        idx = {"beginner": 0, "intermediate": 1, "advanced": 2}.get(
            self.state.experience_level, 0)
        self._level_combo.set_active(idx)
        self._level_combo.connect("changed", self._on_level_changed)
        level_box.pack_start(self._level_combo, False, False, 0)

        info_panel.pack_end(level_box, False, False, 0)
        sep3 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        info_panel.pack_end(sep3, False, False, 0)

        body.pack_end(info_panel, False, False, 0)

        vsep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        body.pack_end(vsep, False, False, 0)

        self.pack_start(body, True, True, 0)

        # Navigation bar
        nav_sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(nav_sep, False, False, 0)

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.get_style_context().add_class("nav-bar")
        nav.set_margin_start(32)
        nav.set_margin_end(32)
        nav.set_margin_top(12)
        nav.set_margin_bottom(12)

        self.error_label = Gtk.Label(label="")
        self.error_label.get_style_context().add_class("error-label")
        self.error_label.set_halign(Gtk.Align.START)
        self.error_label.set_hexpand(True)
        nav.pack_start(self.error_label, True, True, 0)

        self.back_btn = Gtk.Button(label="◀  Back")
        self.back_btn.get_style_context().add_class("nav-btn")
        self.back_btn.get_style_context().add_class("nav-btn-back")
        self.back_btn.connect("clicked", self._on_back_clicked)
        nav.pack_end(self.back_btn, False, False, 0)

        self.next_btn = Gtk.Button(label="Next  ▶")
        self.next_btn.get_style_context().add_class("nav-btn")
        self.next_btn.get_style_context().add_class("nav-btn-next")
        self.next_btn.connect("clicked", self._on_next_clicked)
        nav.pack_end(self.next_btn, False, False, 0)

        self.pack_start(nav, False, False, 0)

    # ── Hint panel ───────────────────────────────────────────────────────────

    def refresh_hints(self):
        hints = self.get_hints()
        text = hints.get(self.state.experience_level, "")
        self.hint_label.set_text(text)

    def _on_level_changed(self, combo):
        levels = ["beginner", "intermediate", "advanced"]
        self.state.experience_level = levels[combo.get_active()]
        self.refresh_hints()
        self.on_experience_changed()

    def on_experience_changed(self):
        """Override to show/hide options when experience level changes."""
        pass

    # ── Navigation ───────────────────────────────────────────────────────────

    def _on_back_clicked(self, _btn):
        if self._on_back_cb:
            self._on_back_cb()

    def _on_next_clicked(self, _btn):
        ok, msg = self.validate()
        if not ok:
            self.error_label.set_text(f"⚠  {msg}")
            return
        self.error_label.set_text("")
        self.on_next()
        if self._on_next_cb:
            self._on_next_cb()

    def set_back_enabled(self, enabled: bool):
        self.back_btn.set_sensitive(enabled)

    def set_next_label(self, label: str):
        self.next_btn.set_label(label)

    # ── Subclass interface ────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        """Override: return the main content widget for this screen."""
        placeholder = Gtk.Label(label="(Screen not yet implemented)")
        return placeholder

    def get_hints(self) -> dict:
        """Override: return hints dict keyed by experience level."""
        return {
            "beginner":     "No hints available for this screen yet.",
            "intermediate": "No hints available for this screen yet.",
            "advanced":     "No hints available for this screen yet.",
        }

    def validate(self):
        """Override: return (True, '') or (False, 'error message')."""
        return True, ""

    def on_next(self):
        """Override: commit selections to self.state before navigating away."""
        pass
