"""
installer/ui/locale_screen.py
------------------------------
Stage 3 — Locale

Lets the user pick their system locale (e.g. en_US.UTF-8).
This controls the language, date/number formats, and character encoding
used by the installed system.

In Beginner mode only UTF-8 locales are shown (the right choice for
virtually everyone). Intermediate and Advanced show the full list.

Saves to:
    state.locale    — e.g. "en_US.UTF-8"
    state.language  — same value (LANG= in /etc/locale.conf)
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from installer.ui.base_screen import BaseScreen
from installer.backend.locale import list_locales, locale_to_lang


class LocaleScreen(BaseScreen):
    """Stage 3 — Locale selection screen."""

    # ── Screen metadata ───────────────────────────────────────────────────────
    title    = "Locale"
    subtitle = "Choose the language and format settings for your system"

    # ── Arch Wiki links shown in the info panel ───────────────────────────────
    WIKI_LINKS = [
        ("Locale",              "https://wiki.archlinux.org/title/Locale"),
        ("locale.gen",          "https://wiki.archlinux.org/title/Locale#Generating_locales"),
        ("locale.conf",         "https://wiki.archlinux.org/title/Locale#Setting_the_system_locale"),
    ]

    def __init__(self, state, on_next, on_back):
        # Initialise our own state before super().__init__ because
        # super() immediately calls build_content() which references these.
        self._selected_locale = state.locale or "en_US.UTF-8"
        self._utf8_only = True   # start in UTF-8-only mode (Beginner default)

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        # Next is enabled straight away because we already have a default
        self.set_next_enabled(True)

        # Load the locale list in the background
        self._load_locales_async()

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "🌐  Locale\n\n"
                "This setting controls your system language and how dates, "
                "times, and numbers are formatted.\n\n"
                "For most English speakers, en_US.UTF-8 or en_GB.UTF-8 is "
                "the right choice. For other languages, search for your "
                "country code (e.g. de_DE.UTF-8 for German).\n\n"
                "Only UTF-8 locales are shown here — these are the modern "
                "standard and the correct choice for all new installs."
            ),
            "intermediate": (
                "🌐  Locale\n\n"
                "Sets LANG= in /etc/locale.conf and determines which locale "
                "is uncommented in /etc/locale.gen before running locale-gen.\n\n"
                "UTF-8 is strongly recommended. Legacy encodings like ISO-8859 "
                "exist for compatibility with old software but should be avoided "
                "on new systems.\n\n"
                "Toggle 'Show all locales' to see non-UTF-8 options."
            ),
            "advanced": (
                "🌐  Locale\n\n"
                "Configures /etc/locale.gen (uncomments the chosen locale) and "
                "writes LANG= to /etc/locale.conf. locale-gen is run in the "
                "arch-chroot during installation.\n\n"
                "LC_* variables can be set individually in locale.conf to mix "
                "locales (e.g. en_US.UTF-8 for language but de_DE.UTF-8 for "
                "number/date formats). That level of customisation is out of "
                "scope for this installer — edit locale.conf post-install.\n\n"
                "Toggle 'Show all locales' to include non-UTF-8 encodings."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # ── Filter row: search box + UTF-8 toggle ─────────────────────────────
        filter_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        search_lbl = Gtk.Label(label="Filter:")
        search_lbl.get_style_context().add_class("section-heading")
        filter_row.pack_start(search_lbl, False, False, 0)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("e.g. en_US, de_DE, fr_FR …")
        self._search_entry.connect("search-changed", self._on_search_changed)
        filter_row.pack_start(self._search_entry, True, True, 0)

        # Toggle to show all locales or UTF-8 only.
        # Shown for Intermediate/Advanced; hidden for Beginner (UTF-8 always on).
        self._utf8_toggle = Gtk.CheckButton(label="UTF-8 only")
        self._utf8_toggle.set_active(True)
        self._utf8_toggle.connect("toggled", self._on_utf8_toggled)
        filter_row.pack_start(self._utf8_toggle, False, False, 0)

        root.pack_start(filter_row, False, False, 0)

        # ── Locale list ───────────────────────────────────────────────────────
        list_frame = Gtk.Frame()
        list_frame.get_style_context().add_class("card")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(240)
        scrolled.set_max_content_height(320)

        self._store = Gtk.ListStore(str)
        self._filter_model = self._store.filter_new()
        self._filter_model.set_visible_func(self._row_is_visible)

        self._tree = Gtk.TreeView(model=self._filter_model)
        self._tree.set_headers_visible(False)
        self._tree.set_activate_on_single_click(True)

        col = Gtk.TreeViewColumn("Locale", Gtk.CellRendererText(), text=0)
        self._tree.append_column(col)

        self._tree.connect("cursor-changed", self._on_selection_changed)

        scrolled.add(self._tree)
        list_frame.add(scrolled)
        root.pack_start(list_frame, True, True, 0)

        # ── Loading spinner ───────────────────────────────────────────────────
        self._spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._spinner_box.set_halign(Gtk.Align.CENTER)
        spinner = Gtk.Spinner()
        spinner.start()
        self._spinner_box.pack_start(spinner, False, False, 0)
        lbl = Gtk.Label(label="Loading locales…")
        lbl.get_style_context().add_class("detail-value")
        self._spinner_box.pack_start(lbl, False, False, 0)
        root.pack_start(self._spinner_box, False, False, 0)

        # ── Selected locale display ───────────────────────────────────────────
        sel_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        sel_key = Gtk.Label(label="Selected:")
        sel_key.get_style_context().add_class("detail-key")
        sel_row.pack_start(sel_key, False, False, 0)

        self._selected_label = Gtk.Label(label=self._selected_locale)
        self._selected_label.get_style_context().add_class("detail-value")
        self._selected_label.set_xalign(0)
        sel_row.pack_start(self._selected_label, True, True, 0)

        root.pack_start(sel_row, False, False, 0)

        # ── What this setting affects (plain-English summary) ─────────────────
        info_card = Gtk.Frame()
        info_card.get_style_context().add_class("card")

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info_box.set_margin_start(14)
        info_box.set_margin_end(14)
        info_box.set_margin_top(10)
        info_box.set_margin_bottom(10)

        affects_lbl = Gtk.Label(label="This setting controls:")
        affects_lbl.get_style_context().add_class("section-heading")
        affects_lbl.set_xalign(0)
        info_box.pack_start(affects_lbl, False, False, 0)

        affects_detail = Gtk.Label(
            label="System language  •  Date & time formats  •  "
                  "Number & currency formats  •  Character encoding"
        )
        affects_detail.get_style_context().add_class("detail-value")
        affects_detail.set_xalign(0)
        affects_detail.set_line_wrap(True)
        info_box.pack_start(affects_detail, False, False, 0)

        info_card.add(info_box)
        root.pack_start(info_card, False, False, 0)

        return root

    # ── Async locale loading ──────────────────────────────────────────────────

    def _load_locales_async(self):
        """Load the locale list in a background thread."""
        utf8_only = self._utf8_only

        def _worker():
            locales = list_locales(utf8_only=utf8_only)
            GLib.idle_add(self._on_locales_loaded, locales)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_locales_loaded(self, locales: list):
        """Called on the GTK main thread once the list is ready."""
        self._store.clear()
        for loc in locales:
            self._store.append([loc])

        self._spinner_box.hide()
        self._scroll_to_locale(self._selected_locale)
        return False  # GLib one-shot

    # ── UTF-8 toggle ──────────────────────────────────────────────────────────

    def _on_utf8_toggled(self, btn):
        """Reload the list when the user switches between UTF-8-only and all."""
        self._utf8_only = btn.get_active()
        self._spinner_box.show_all()
        self._load_locales_async()

    # ── Filtering ─────────────────────────────────────────────────────────────

    def _row_is_visible(self, model, iter_, data):
        query = self._search_entry.get_text().strip().lower()
        if not query:
            return True
        return query in model.get_value(iter_, 0).lower()

    def _on_search_changed(self, entry):
        self._filter_model.refilter()
        if self._filter_model.iter_n_children(None) == 1:
            first = Gtk.TreePath.new_first()
            self._tree.set_cursor(first, None, False)
            self._on_selection_changed(self._tree)

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self, tree):
        model, it = tree.get_selection().get_selected()
        if it is None:
            return
        locale = model.get_value(it, 0)
        self._selected_locale = locale
        self._selected_label.set_text(locale)
        self.set_next_enabled(True)

    def _scroll_to_locale(self, locale: str):
        """Highlight and scroll to the given locale in the list."""
        it = self._filter_model.get_iter_first()
        while it:
            if self._filter_model.get_value(it, 0) == locale:
                path = self._filter_model.get_path(it)
                self._tree.set_cursor(path, None, False)
                self._tree.scroll_to_cell(path, None, True, 0.4, 0)
                return
            it = self._filter_model.iter_next(it)

    # ── Experience level change ───────────────────────────────────────────────

    def on_experience_changed(self):
        """
        Called by BaseScreen when the user changes experience level.
        In Beginner mode we lock the UTF-8 toggle on and hide it.
        In Intermediate/Advanced we show it and let the user control it.
        """
        is_beginner = self.state.experience_level == "beginner"

        if is_beginner:
            # Force UTF-8 only and hide the toggle so beginners aren't confused
            self._utf8_toggle.set_active(True)
            self._utf8_toggle.hide()
            if not self._utf8_only:
                self._utf8_only = True
                self._load_locales_async()
        else:
            self._utf8_toggle.show()

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if not self._selected_locale:
            return False, "Please select a locale before continuing."
        return True, ""

    def on_next(self):
        """Save locale selections to state."""
        self.state.locale   = self._selected_locale
        self.state.language = locale_to_lang(self._selected_locale)
