"""
installer/ui/mirrors.py
------------------------
Stage 7 — Mirror Selection
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen
from installer.backend.mirrors import (
    fetch_mirrors,
    count_mirrors,
    locale_to_country_code,
    country_code_to_reflector_name,
    ALL_COUNTRIES,
    FALLBACK_MIRRORLIST,
)

SORT_OPTIONS = [
    ("rate",    "Rate      — fastest download speed (recommended)"),
    ("score",   "Score     — Arch mirror score (combines multiple factors)"),
    ("age",     "Age       — most recently synchronised"),
    ("country", "Country   — alphabetical by country"),
    ("delay",   "Delay     — lowest sync delay"),
]


class MirrorScreen(BaseScreen):
    """Stage 7 — Mirror Selection screen."""

    title    = "Mirror Selection"
    subtitle = "Choose the servers used to download Arch Linux packages"

    WIKI_LINKS = [
        ("Mirrors",       "https://wiki.archlinux.org/title/Mirrors"),
        ("reflector",     "https://wiki.archlinux.org/title/Reflector"),
        ("Mirror status", "https://archlinux.org/mirrors/status/"),
    ]

    def __init__(self, state, on_next, on_back):
        # Always default to United States; override if locale gives a known country
        code     = locale_to_country_code(state.locale or "en_US.UTF-8")
        detected = country_code_to_reflector_name(code)
        known    = {r for r, _ in ALL_COUNTRIES}
        self._default_country = detected if detected in known else "United States"

        # Restore previous selection when coming Back, else use default
        if state.mirror_countries:
            self._selected_countries = set(state.mirror_countries)
        else:
            self._selected_countries = {self._default_country}

        self._fetching      = False
        self._pulse_timer   = None
        self._pulse_seconds = 0

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(bool(state.mirrorlist))

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        country = self._default_country
        return {
            "beginner": (
                f"🌐  Mirror Selection\n\n"
                f"Mirrors are the servers your system downloads packages "
                f"from. Closer mirrors are faster.\n\n"
                f"Detected location: {country}\n\n"
                "Tick the checkbox next to your country, then click "
                "'Fetch Mirrors'. This takes about 10–20 seconds and "
                "requires an internet connection.\n\n"
                "If you're offline, click 'Use Fallback Mirrorlist'."
            ),
            "intermediate": (
                f"🌐  Mirror Selection\n\n"
                "reflector fetches and ranks Arch mirrors by speed.\n\n"
                "You can tick multiple countries — useful if you're near "
                "a border or want more options.\n\n"
                "10 mirrors is a good balance of speed and redundancy. "
                "HTTPS is strongly recommended."
            ),
            "advanced": (
                "🌐  Mirror Selection\n\n"
                "reflector arguments are built from your selections and "
                "passed directly. 'Rate' measures actual download speed "
                "(downloads test files). 'Score' uses Arch's scoring.\n\n"
                "Age excludes mirrors that haven't synced recently. "
                "24h is safe; lower = fresher but fewer mirrors.\n\n"
                "Result written to /etc/pacman.d/mirrorlist during chroot."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        root.pack_start(self._build_config_section(), False, False, 0)
        root.pack_start(self._build_fetch_row(),      False, False, 0)
        root.pack_start(self._build_log_section(),    False, False, 0)
        root.pack_start(self._build_result_section(), True,  True,  0)

        # Both calls deferred via idle_add so they run after show_all()
        # has finished — otherwise show_all() overrides our hide() calls.
        GLib.idle_add(self._apply_level_visibility)
        GLib.idle_add(self._scroll_to_default)

        if self.state.mirrorlist:
            self._show_mirrorlist(self.state.mirrorlist, from_cache=True)

        return root

    # ── Config section ────────────────────────────────────────────────────────

    def _build_config_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_start(14)
        outer.set_margin_end(14)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)

        # ── Country list with checkboxes ──────────────────────────────────────
        heading = Gtk.Label(label="Country / region  (tick one or more):")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        outer.pack_start(heading, False, False, 0)

        country_scroll = Gtk.ScrolledWindow()
        country_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        country_scroll.set_min_content_height(150)
        country_scroll.set_max_content_height(150)

        # ListStore: col 0 = checked (bool), col 1 = reflector name, col 2 = display name
        self._country_store = Gtk.ListStore(bool, str, str)
        for reflector_name, display_name in ALL_COUNTRIES:
            checked = reflector_name in self._selected_countries
            self._country_store.append([checked, reflector_name, display_name])

        self._country_tree = Gtk.TreeView(model=self._country_store)
        self._country_tree.set_headers_visible(False)
        # NOTE: do NOT use set_activate_on_single_click(True) here —
        # it fires row-activated which double-toggles and undoes the checkbox.

        # Checkbox column — toggling is handled solely by CellRendererToggle
        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.set_activatable(True)
        toggle_renderer.connect("toggled", self._on_country_toggled)
        chk_col = Gtk.TreeViewColumn("", toggle_renderer, active=0)
        chk_col.set_fixed_width(32)
        self._country_tree.append_column(chk_col)

        # Country name column — clicking it also toggles via button-press-event
        text_renderer = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn("Country", text_renderer, text=2)
        name_col.set_expand(True)
        self._country_tree.append_column(name_col)

        # Let clicking the text column also toggle the checkbox
        self._country_tree.connect("button-press-event", self._on_tree_click)

        country_scroll.add(self._country_tree)
        outer.pack_start(country_scroll, False, False, 0)

        # ── Number of mirrors (Intermediate+) ─────────────────────────────────
        self._num_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        num_lbl = Gtk.Label(label="Number of mirrors:")
        num_lbl.get_style_context().add_class("detail-key")
        num_lbl.set_width_chars(22)
        num_lbl.set_xalign(0)
        self._num_row.pack_start(num_lbl, False, False, 0)
        self._num_combo = Gtk.ComboBoxText()
        for n in ["5", "10", "20", "30"]:
            self._num_combo.append_text(n)
        self._num_combo.set_active(1)  # default: 10
        self._num_row.pack_start(self._num_combo, False, False, 0)
        outer.pack_start(self._num_row, False, False, 0)

        # ── Protocol (Advanced) ───────────────────────────────────────────────
        self._proto_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        proto_lbl = Gtk.Label(label="Protocol:")
        proto_lbl.get_style_context().add_class("detail-key")
        proto_lbl.set_width_chars(22)
        proto_lbl.set_xalign(0)
        self._proto_row.pack_start(proto_lbl, False, False, 0)
        self._proto_https = Gtk.CheckButton(label="HTTPS")
        self._proto_https.set_active(True)
        self._proto_row.pack_start(self._proto_https, False, False, 0)
        self._proto_http = Gtk.CheckButton(label="HTTP")
        self._proto_http.set_active(False)
        self._proto_row.pack_start(self._proto_http, False, False, 0)
        outer.pack_start(self._proto_row, False, False, 0)

        # ── Sort method (Advanced) ────────────────────────────────────────────
        self._sort_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sort_lbl = Gtk.Label(label="Sort by:")
        sort_lbl.get_style_context().add_class("detail-key")
        sort_lbl.set_width_chars(22)
        sort_lbl.set_xalign(0)
        self._sort_row.pack_start(sort_lbl, False, False, 0)
        self._sort_combo = Gtk.ComboBoxText()
        for _, label in SORT_OPTIONS:
            self._sort_combo.append_text(label)
        self._sort_combo.set_active(0)
        self._sort_row.pack_start(self._sort_combo, True, True, 0)
        outer.pack_start(self._sort_row, False, False, 0)

        # ── Age limit (Advanced) ──────────────────────────────────────────────
        self._age_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        age_lbl = Gtk.Label(label="Max mirror age (hours):")
        age_lbl.get_style_context().add_class("detail-key")
        age_lbl.set_width_chars(22)
        age_lbl.set_xalign(0)
        self._age_row.pack_start(age_lbl, False, False, 0)
        self._age_spin = Gtk.SpinButton()
        age_adj = Gtk.Adjustment(value=24, lower=1, upper=168,
                                 step_increment=1, page_increment=12)
        self._age_spin.set_adjustment(age_adj)
        self._age_spin.set_numeric(True)
        self._age_row.pack_start(self._age_spin, False, False, 0)
        age_hint = Gtk.Label(label="(24 = last 24 hours)")
        age_hint.get_style_context().add_class("detail-value")
        self._age_row.pack_start(age_hint, False, False, 0)
        outer.pack_start(self._age_row, False, False, 0)

        frame.add(outer)
        return frame

    def _on_country_toggled(self, renderer, path):
        """CellRendererToggle callback — flip the checkbox."""
        it      = self._country_store.get_iter_from_string(path)
        current = self._country_store.get_value(it, 0)
        name    = self._country_store.get_value(it, 1)
        self._country_store.set_value(it, 0, not current)
        if not current:
            self._selected_countries.add(name)
        else:
            self._selected_countries.discard(name)

    def _on_tree_click(self, tree, event):
        """Single-click anywhere on a row toggles its checkbox."""
        result = tree.get_path_at_pos(int(event.x), int(event.y))
        if result is None:
            return False
        path, column, _, _ = result
        # Only act on the name column (column index 1), not the toggle column
        # — the toggle renderer handles its own column already.
        if column == tree.get_column(1):
            it      = self._country_store.get_iter(path)
            current = self._country_store.get_value(it, 0)
            name    = self._country_store.get_value(it, 1)
            self._country_store.set_value(it, 0, not current)
            if not current:
                self._selected_countries.add(name)
            else:
                self._selected_countries.discard(name)
        return False

    def _scroll_to_default(self):
        """Scroll to the first checked entry (United States) after realize."""
        it = self._country_store.get_iter_first()
        while it:
            if self._country_store.get_value(it, 1) == self._default_country:
                path = self._country_store.get_path(it)
                self._country_tree.scroll_to_cell(path, None, True, 0.0, 0)
                break
            it = self._country_store.iter_next(it)
        return False  # GLib one-shot

    # ── Fetch row ─────────────────────────────────────────────────────────────

    def _build_fetch_row(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self._fetch_btn = Gtk.Button(label="🔄  Fetch Mirrors")
        self._fetch_btn.get_style_context().add_class("action-button")
        self._fetch_btn.connect("clicked", self._on_fetch_clicked)
        box.pack_start(self._fetch_btn, False, False, 0)

        self._fallback_btn = Gtk.Button(label="Use Fallback Mirrorlist")
        self._fallback_btn.get_style_context().add_class("action-button")
        self._fallback_btn.connect("clicked", self._on_fallback_clicked)
        box.pack_start(self._fallback_btn, False, False, 0)

        self._spinner = Gtk.Spinner()
        self._spinner.set_no_show_all(True)
        box.pack_start(self._spinner, False, False, 0)

        return box

    # ── Log / status section ──────────────────────────────────────────────────

    def _build_log_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        self._cmd_label = Gtk.Label(label="")
        self._cmd_label.get_style_context().add_class("detail-value")
        self._cmd_label.set_xalign(0)
        self._cmd_label.set_line_wrap(True)
        self._cmd_label.set_selectable(True)
        self._cmd_label.set_size_request(-1, 20)
        box.pack_start(self._cmd_label, False, False, 0)

        self._fetch_status = Gtk.Label(label="Click 'Fetch Mirrors' to begin.")
        self._fetch_status.get_style_context().add_class("detail-value")
        self._fetch_status.set_xalign(0)
        self._fetch_status.set_size_request(-1, 20)
        box.pack_start(self._fetch_status, False, False, 0)

        frame.add(box)
        return frame

    # ── Result section ────────────────────────────────────────────────────────

    def _build_result_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")
        frame.set_no_show_all(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        self._result_heading = Gtk.Label()
        self._result_heading.get_style_context().add_class("section-heading")
        self._result_heading.set_xalign(0)
        box.pack_start(self._result_heading, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(140)

        self._result_view = Gtk.TextView()
        self._result_view.set_editable(False)
        self._result_view.set_cursor_visible(False)
        self._result_view.override_font(Pango.FontDescription("Monospace 10"))
        self._result_view.get_style_context().add_class("detail-value")
        scroll.add(self._result_view)

        box.pack_start(scroll, True, True, 0)
        frame.add(box)

        self._result_frame = frame
        return frame

    # ── Level visibility ──────────────────────────────────────────────────────

    def _apply_level_visibility(self):
        level = self.state.experience_level
        if level == "beginner":
            self._num_row.hide()
        else:
            self._num_row.show()
        if level == "advanced":
            self._proto_row.show()
            self._sort_row.show()
            self._age_row.show()
        else:
            self._proto_row.hide()
            self._sort_row.hide()
            self._age_row.hide()
        return False  # GLib one-shot when called via idle_add

    def on_experience_changed(self):
        self._apply_level_visibility()
        self.refresh_hints()

    # ── Fetch params ──────────────────────────────────────────────────────────

    def _get_fetch_params(self) -> dict:
        countries = list(self._selected_countries) or [self._default_country]
        num_text  = self._num_combo.get_active_text() or "10"
        number    = int(num_text)
        protocols = []
        if self._proto_https.get_active():
            protocols.append("https")
        if self._proto_http.get_active():
            protocols.append("http")
        if not protocols:
            protocols = ["https"]
        sort_idx = self._sort_combo.get_active()
        sort_by  = SORT_OPTIONS[sort_idx][0] if sort_idx >= 0 else "rate"
        age      = int(self._age_spin.get_value())
        return dict(countries=countries, protocols=protocols,
                    sort_by=sort_by, number=number, age=age)

    # ── Fetch logic ───────────────────────────────────────────────────────────

    def _on_fetch_clicked(self, btn):
        if self._fetching:
            return
        if not self._selected_countries:
            self._fetch_status.set_text("⚠  Tick at least one country first.")
            return

        params = self._get_fetch_params()

        cmd_parts = ["reflector"]
        for c in params["countries"]:
            cmd_parts.append(f"--country '{c}'")
        for p in params["protocols"]:
            cmd_parts.append(f"--protocol {p}")
        cmd_parts += [
            f"--sort {params['sort_by']}",
            f"--latest {params['number']}",
            f"--age {params['age']}",
        ]
        cmd_str = " ".join(cmd_parts)

        self._fetching = True
        self._fetch_btn.set_sensitive(False)
        self._fallback_btn.set_sensitive(False)
        self._spinner.show()
        self._spinner.start()
        self.set_next_enabled(False)

        self._cmd_label.set_text(f"$ {cmd_str}")
        self._fetch_status.set_text("⏳  Running…")

        self._pulse_seconds = 0
        if self._pulse_timer:
            GLib.source_remove(self._pulse_timer)
        self._pulse_timer = GLib.timeout_add(1000, self._on_pulse_tick)

        def _worker():
            success, content = fetch_mirrors(**params)
            GLib.idle_add(self._on_fetch_done, success, content)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_pulse_tick(self):
        self._pulse_seconds += 1
        self._fetch_status.set_text(f"⏳  Running… ({self._pulse_seconds}s elapsed)")
        return True

    def _on_fetch_done(self, success: bool, content: str):
        self._fetching = False
        self._fetch_btn.set_sensitive(True)
        self._fallback_btn.set_sensitive(True)
        self._spinner.stop()
        self._spinner.hide()

        if self._pulse_timer:
            GLib.source_remove(self._pulse_timer)
            self._pulse_timer = None

        if success:
            n = count_mirrors(content)
            self._fetch_status.set_text(
                f"✅  Complete — {n} mirrors fetched in {self._pulse_seconds}s"
            )
            self._show_mirrorlist(content)
        else:
            self._fetch_status.set_text(
                f"❌  Failed after {self._pulse_seconds}s: {content} "
                "— using fallback mirrorlist."
            )
            self._show_mirrorlist(FALLBACK_MIRRORLIST, fallback=True)

        return False

    def _on_fallback_clicked(self, btn):
        self._cmd_label.set_text("")
        self._fetch_status.set_text("📋  Using bundled fallback mirrorlist.")
        self._show_mirrorlist(FALLBACK_MIRRORLIST, fallback=True)

    def _show_mirrorlist(self, content: str, fallback: bool = False,
                         from_cache: bool = False):
        n = count_mirrors(content)
        if from_cache:
            heading = f"Mirrorlist loaded ({n} mirrors)"
        elif fallback:
            heading = (f"Fallback mirrorlist ({n} mirrors) — "
                       "run reflector post-install for best performance")
        else:
            countries_str = ", ".join(sorted(self._selected_countries))
            heading = f"Fetched {n} mirror(s) — {countries_str}"

        self._result_heading.set_text(heading)
        self._result_view.get_buffer().set_text(content)
        self._result_frame.show()
        self.state.mirrorlist       = content
        self.state.mirror_countries = list(self._selected_countries)
        self.set_next_enabled(True)

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if not self.state.mirrorlist:
            return False, "Fetch mirrors or use the fallback mirrorlist before continuing."
        return True, ""

    def on_next(self):
        pass
