"""
installer/ui/timezone.py
-------------------------
Stage 10 — Timezone Selection

Lets the user pick their timezone from a searchable list built from
/usr/share/zoneinfo. Falls back to a bundled list if that directory
is not available.

A live clock preview updates every second to show the current time
in the selected zone.

Experience level behaviour:
  Beginner:     Searchable list, live time preview, good default.
  Intermediate: Same + UTC offset shown.
  Advanced:     Same + raw zoneinfo path shown, NTP note.

Saves to:
    state.timezone  — e.g. 'America/Los_Angeles'
"""

import os
import threading
import datetime

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen


# ── Timezone data ─────────────────────────────────────────────────────────────

# Locale → likely timezone mapping for auto-detection
LOCALE_TO_TZ = {
    "en_US": "America/New_York",
    "en_GB": "Europe/London",
    "de_DE": "Europe/Berlin",
    "fr_FR": "Europe/Paris",
    "es_ES": "Europe/Madrid",
    "it_IT": "Europe/Rome",
    "pt_BR": "America/Sao_Paulo",
    "pt_PT": "Europe/Lisbon",
    "nl_NL": "Europe/Amsterdam",
    "pl_PL": "Europe/Warsaw",
    "ru_RU": "Europe/Moscow",
    "zh_CN": "Asia/Shanghai",
    "zh_TW": "Asia/Taipei",
    "ja_JP": "Asia/Tokyo",
    "ko_KR": "Asia/Seoul",
    "ar_SA": "Asia/Riyadh",
    "hi_IN": "Asia/Kolkata",
    "tr_TR": "Europe/Istanbul",
    "sv_SE": "Europe/Stockholm",
    "nb_NO": "Europe/Oslo",
    "da_DK": "Europe/Copenhagen",
    "fi_FI": "Europe/Helsinki",
    "cs_CZ": "Europe/Prague",
    "hu_HU": "Europe/Budapest",
    "ro_RO": "Europe/Bucharest",
    "uk_UA": "Europe/Kiev",
    "he_IL": "Asia/Jerusalem",
    "th_TH": "Asia/Bangkok",
    "vi_VN": "Asia/Ho_Chi_Minh",
    "id_ID": "Asia/Jakarta",
    "ms_MY": "Asia/Kuala_Lumpur",
    "en_AU": "Australia/Sydney",
    "en_NZ": "Pacific/Auckland",
    "en_CA": "America/Toronto",
    "en_ZA": "Africa/Johannesburg",
    "es_MX": "America/Mexico_City",
    "es_AR": "America/Argentina/Buenos_Aires",
    "es_CL": "America/Santiago",
}

# Fallback list used if /usr/share/zoneinfo is not available
FALLBACK_TIMEZONES = [
    "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos", "Africa/Nairobi",
    "America/Anchorage", "America/Argentina/Buenos_Aires", "America/Chicago",
    "America/Denver", "America/Los_Angeles", "America/Mexico_City",
    "America/New_York", "America/Phoenix", "America/Sao_Paulo",
    "America/Santiago", "America/Toronto", "America/Vancouver",
    "Asia/Baghdad", "Asia/Bangkok", "Asia/Colombo", "Asia/Dubai",
    "Asia/Ho_Chi_Minh", "Asia/Hong_Kong", "Asia/Jakarta", "Asia/Jerusalem",
    "Asia/Karachi", "Asia/Kathmandu", "Asia/Kolkata", "Asia/Kuala_Lumpur",
    "Asia/Riyadh", "Asia/Seoul", "Asia/Shanghai", "Asia/Singapore",
    "Asia/Taipei", "Asia/Tehran", "Asia/Tokyo",
    "Atlantic/Reykjavik",
    "Australia/Adelaide", "Australia/Brisbane", "Australia/Melbourne",
    "Australia/Perth", "Australia/Sydney",
    "Europe/Amsterdam", "Europe/Athens", "Europe/Belgrade", "Europe/Berlin",
    "Europe/Brussels", "Europe/Bucharest", "Europe/Budapest",
    "Europe/Copenhagen", "Europe/Dublin", "Europe/Helsinki",
    "Europe/Istanbul", "Europe/Kiev", "Europe/Lisbon", "Europe/London",
    "Europe/Madrid", "Europe/Moscow", "Europe/Oslo", "Europe/Paris",
    "Europe/Prague", "Europe/Rome", "Europe/Sofia", "Europe/Stockholm",
    "Europe/Vienna", "Europe/Warsaw", "Europe/Zurich",
    "Pacific/Auckland", "Pacific/Fiji", "Pacific/Honolulu",
    "UTC",
]


def _load_timezones() -> list:
    """
    Load timezone list from /usr/share/zoneinfo.
    Falls back to FALLBACK_TIMEZONES if not available.
    """
    zoneinfo = "/usr/share/zoneinfo"
    if not os.path.isdir(zoneinfo):
        return sorted(FALLBACK_TIMEZONES)

    zones = []
    for region in sorted(os.listdir(zoneinfo)):
        region_path = os.path.join(zoneinfo, region)
        if not os.path.isdir(region_path):
            continue
        # Skip meta-directories
        if region in ("posix", "right", "Etc", "SystemV", "leaps"):
            continue
        for city in sorted(os.listdir(region_path)):
            city_path = os.path.join(region_path, city)
            # Skip subdirectories (e.g. America/Indiana/*)
            if os.path.isdir(city_path):
                for sub in sorted(os.listdir(city_path)):
                    zones.append(f"{region}/{city}/{sub}")
            elif os.path.isfile(city_path) and not city.endswith(".list"):
                zones.append(f"{region}/{city}")

    # Add UTC explicitly
    if "UTC" not in zones:
        zones.append("UTC")

    return sorted(zones)


def _utc_offset(tz_name: str) -> str:
    """Return a UTC offset string like 'UTC-8' or 'UTC+5:30'."""
    try:
        import zoneinfo as zi
        tz = zi.ZoneInfo(tz_name)
    except Exception:
        try:
            import pytz
            tz = pytz.timezone(tz_name)
        except Exception:
            return ""

    now = datetime.datetime.now(tz)
    offset = now.utcoffset()
    if offset is None:
        return "UTC"
    total_minutes = int(offset.total_seconds() / 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"
    return f"UTC{sign}{hours}"


def _get_time_in(tz_name: str) -> str:
    """Return the current time formatted for display."""
    try:
        import zoneinfo as zi
        tz = zi.ZoneInfo(tz_name)
        now = datetime.datetime.now(tz)
        return now.strftime("%H:%M:%S  %A, %B %-d %Y")
    except Exception:
        try:
            import pytz
            tz = pytz.timezone(tz_name)
            now = datetime.datetime.now(tz)
            return now.strftime("%H:%M:%S  %A, %B %-d %Y")
        except Exception:
            return datetime.datetime.utcnow().strftime("%H:%M:%S UTC")


def _guess_timezone(locale: str) -> str:
    """Guess a timezone from the locale string."""
    # Try full locale first (e.g. 'en_US'), then language only
    lang_region = locale.split(".")[0]  # strip encoding
    if lang_region in LOCALE_TO_TZ:
        return LOCALE_TO_TZ[lang_region]
    lang = lang_region.split("_")[0]
    for key, tz in LOCALE_TO_TZ.items():
        if key.startswith(lang + "_"):
            return tz
    return "UTC"


class TimezoneScreen(BaseScreen):
    """Stage 10 — Timezone Selection."""

    title    = "Timezone"
    subtitle = "Select your local timezone"

    WIKI_LINKS = [
        ("Time zone",      "https://wiki.archlinux.org/title/Time_zone"),
        ("System time",    "https://wiki.archlinux.org/title/System_time"),
        ("timedatectl",    "https://wiki.archlinux.org/title/Systemd-timesyncd"),
    ]

    def __init__(self, state, on_next, on_back):
        # Determine default timezone
        if state.timezone and state.timezone != "UTC":
            self._selected_tz = state.timezone
        else:
            self._selected_tz = _guess_timezone(state.locale or "en_US.UTF-8")

        self._all_timezones = _load_timezones()
        self._clock_timer   = None   # GLib timer id

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(True)
        GLib.idle_add(self._apply_level_visibility)
        GLib.idle_add(self._scroll_to_selected)

        # Start the live clock
        self._clock_timer = GLib.timeout_add(1000, self._on_clock_tick)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "🕐  Timezone\n\n"
                "Select the timezone for your location. This sets your "
                "system clock so timestamps on files and logs are correct.\n\n"
                "Start typing to search — for example type 'Los Angeles' "
                "or 'London' to find your city quickly.\n\n"
                "The clock preview updates live to show the current time "
                "in the selected zone."
            ),
            "intermediate": (
                "🕐  Timezone\n\n"
                "The timezone is written to /etc/localtime as a symlink "
                "to /usr/share/zoneinfo/<Region>/<City>.\n\n"
                "NTP sync (systemd-timesyncd) will be enabled by default "
                "and keeps the clock accurate after install.\n\n"
                "Hardware clock is set to UTC, which is the Arch default "
                "and works best for dual-boot systems."
            ),
            "advanced": (
                "🕐  Timezone\n\n"
                "Sets: ln -sf /usr/share/zoneinfo/<tz> /etc/localtime\n"
                "Then: hwclock --systohc\n\n"
                "systemd-timesyncd is enabled automatically. If you prefer "
                "chrony or ntpd, disable timesyncd post-install.\n\n"
                "Hardware clock is kept as UTC. Windows dual-boot users "
                "may need to set Windows to use UTC too."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        # ── Clock preview card ────────────────────────────────────────────────
        root.pack_start(self._build_clock_card(), False, False, 0)

        # ── Search + list card ────────────────────────────────────────────────
        root.pack_start(self._build_list_card(), False, False, 0)

        # ── Detail row (Intermediate+) ────────────────────────────────────────
        self._detail_row = self._build_detail_row()
        root.pack_start(self._detail_row, False, False, 0)

        GLib.idle_add(self._apply_level_visibility)

        return root

    # ── Clock card ────────────────────────────────────────────────────────────

    def _build_clock_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(14)
        box.set_margin_bottom(14)

        self._tz_label = Gtk.Label(label=self._selected_tz)
        self._tz_label.get_style_context().add_class("section-heading")
        self._tz_label.set_xalign(0)
        box.pack_start(self._tz_label, False, False, 0)

        self._clock_label = Gtk.Label(label=_get_time_in(self._selected_tz))
        self._clock_label.override_font(Pango.FontDescription("Monospace 20"))
        self._clock_label.get_style_context().add_class("screen-title")
        self._clock_label.set_xalign(0)
        box.pack_start(self._clock_label, False, False, 0)

        self._offset_label = Gtk.Label(label=_utc_offset(self._selected_tz))
        self._offset_label.get_style_context().add_class("detail-key")
        self._offset_label.set_xalign(0)
        box.pack_start(self._offset_label, False, False, 0)

        frame.add(box)
        return frame

    # ── List card ─────────────────────────────────────────────────────────────

    def _build_list_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        # Search entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_lbl = Gtk.Label(label="🔍")
        search_box.pack_start(search_lbl, False, False, 0)

        self._search_entry = Gtk.Entry()
        self._search_entry.set_placeholder_text(
            "Search timezones… e.g. 'Los Angeles', 'London', 'Tokyo'"
        )
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("changed", self._on_search_changed)
        search_box.pack_start(self._search_entry, True, True, 0)

        # Clear button
        clear_btn = Gtk.Button(label="✕")
        clear_btn.get_style_context().add_class("action-button")
        clear_btn.connect("clicked", lambda _: self._search_entry.set_text(""))
        search_box.pack_start(clear_btn, False, False, 0)

        box.pack_start(search_box, False, False, 0)

        # Timezone list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)
        scroll.set_max_content_height(200)

        # ListStore: col 0 = timezone string
        self._tz_store = Gtk.ListStore(str)
        for tz in self._all_timezones:
            self._tz_store.append([tz])

        # Filter model
        self._tz_filter = self._tz_store.filter_new()
        self._filter_text = ""
        self._tz_filter.set_visible_func(self._tz_visible)

        self._tz_tree = Gtk.TreeView(model=self._tz_filter)
        self._tz_tree.set_headers_visible(False)
        self._tz_tree.set_activate_on_single_click(True)

        col = Gtk.TreeViewColumn("Timezone", Gtk.CellRendererText(), text=0)
        col.set_expand(True)
        self._tz_tree.append_column(col)

        self._tz_tree.connect("row-activated", self._on_row_activated)
        self._tz_tree.get_selection().connect("changed", self._on_selection_changed)

        scroll.add(self._tz_tree)
        box.pack_start(scroll, False, False, 0)

        frame.add(box)
        return frame

    # ── Detail row (Intermediate+) ────────────────────────────────────────────

    def _build_detail_row(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Zoneinfo path
        path_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        path_key = Gtk.Label(label="Zoneinfo path:")
        path_key.get_style_context().add_class("detail-key")
        path_key.set_xalign(0)
        path_box.pack_start(path_key, False, False, 0)
        self._path_label = Gtk.Label(
            label=f"/usr/share/zoneinfo/{self._selected_tz}"
        )
        self._path_label.get_style_context().add_class("detail-value")
        self._path_label.set_xalign(0)
        self._path_label.set_selectable(True)
        path_box.pack_start(self._path_label, False, False, 0)
        box.pack_start(path_box, True, True, 0)

        # UTC offset
        offset_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        offset_key = Gtk.Label(label="UTC offset:")
        offset_key.get_style_context().add_class("detail-key")
        offset_key.set_xalign(0)
        offset_box.pack_start(offset_key, False, False, 0)
        self._offset_detail = Gtk.Label(label=_utc_offset(self._selected_tz))
        self._offset_detail.get_style_context().add_class("screen-title")
        self._offset_detail.set_xalign(0)
        offset_box.pack_start(self._offset_detail, False, False, 0)
        box.pack_start(offset_box, False, False, 0)

        frame.add(box)
        return frame

    # ── Filter ────────────────────────────────────────────────────────────────

    def _tz_visible(self, model, it, data):
        if not self._filter_text:
            return True
        val = model.get_value(it, 0).lower()
        # Search by any word in the timezone string
        return all(w in val for w in self._filter_text.lower().split())

    def _on_search_changed(self, entry):
        self._filter_text = entry.get_text()
        self._tz_filter.refilter()

    # ── Selection ─────────────────────────────────────────────────────────────

    def _on_row_activated(self, tree, path, column):
        model = tree.get_model()
        it = model.get_iter(path)
        tz = model.get_value(it, 0)
        self._set_timezone(tz)

    def _on_selection_changed(self, selection):
        model, it = selection.get_selected()
        if it:
            tz = model.get_value(it, 0)
            self._set_timezone(tz)

    def _set_timezone(self, tz: str):
        self._selected_tz = tz
        self._update_clock_card()

    def _update_clock_card(self):
        tz = self._selected_tz
        self._tz_label.set_text(tz)
        self._clock_label.set_text(_get_time_in(tz))
        offset = _utc_offset(tz)
        self._offset_label.set_text(offset)
        if hasattr(self, "_path_label"):
            self._path_label.set_text(f"/usr/share/zoneinfo/{tz}")
        if hasattr(self, "_offset_detail"):
            self._offset_detail.set_text(offset)

    def _on_clock_tick(self) -> bool:
        """Called every second by GLib timer to update the clock display."""
        if hasattr(self, "_clock_label"):
            self._clock_label.set_text(_get_time_in(self._selected_tz))
        return True  # keep repeating

    def _scroll_to_selected(self):
        """Scroll the list to the pre-selected timezone after realize."""
        for i, row in enumerate(self._tz_filter):
            if row[0] == self._selected_tz:
                path = Gtk.TreePath.new_from_indices([i])
                self._tz_tree.scroll_to_cell(path, None, True, 0.3, 0)
                self._tz_tree.get_selection().select_path(path)
                break
        return False  # GLib one-shot

    # ── Level visibility ──────────────────────────────────────────────────────

    def _apply_level_visibility(self):
        if self.state.experience_level == "beginner":
            self._detail_row.hide()
        else:
            self._detail_row.show_all()
        return False

    def on_experience_changed(self):
        self._apply_level_visibility()
        self.refresh_hints()

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        if not self._selected_tz:
            return False, "Select a timezone before continuing."
        return True, ""

    def on_next(self):
        self.state.timezone = self._selected_tz

    def destroy(self):
        """Clean up the clock timer when the screen is destroyed."""
        if self._clock_timer:
            GLib.source_remove(self._clock_timer)
            self._clock_timer = None
        super().destroy()
