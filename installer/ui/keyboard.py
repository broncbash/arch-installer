"""
installer/ui/keyboard.py
------------------------
Stage 2 — Keyboard Layout

Lets the user:
  1. Browse / filter the full list of console keymaps
  2. Apply one temporarily with loadkeys to preview it
  3. Type in a test box to confirm the layout feels right

The selection is saved to state.keyboard_layout when Next is clicked.
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen
from installer.backend.keyboard import list_keymaps, apply_keymap, get_current_keymap


class KeyboardScreen(BaseScreen):
    """Stage 2 — Keyboard Layout selection screen."""

    # ── Screen metadata (read by BaseScreen._build_shell) ────────────────────
    title = "Keyboard Layout"
    subtitle = "Choose the console keymap for your system"

    # ── Wiki links shown in the info panel (handled by BaseScreen) ────────────
    # Each tuple is (button label, URL to open).
    WIKI_LINKS = [
        ("Console Keymap",       "https://wiki.archlinux.org/title/Linux_console/Keyboard_configuration"),
        ("Locale",               "https://wiki.archlinux.org/title/Locale"),
        ("Xorg Keyboard Config", "https://wiki.archlinux.org/title/Xorg/Keyboard_configuration"),
    ]

    def __init__(self, state, on_next, on_back):
        # Track the current selection before calling super().__init__,
        # because super().__init__ calls build_content() which needs this.
        self._selected_keymap = state.keyboard_layout or get_current_keymap()
        self._apply_in_progress = False

        # This calls _build_shell() → build_content() → refresh_hints()
        super().__init__(
            state=state,
            on_next=on_next,
            on_back=on_back,
        )

        # Next button starts disabled until a keymap is confirmed selected
        self.set_next_enabled(bool(self._selected_keymap))

        # Load the keymap list in the background so the UI isn't frozen
        self._load_keymaps_async()

    # ── Hints for the info panel ──────────────────────────────────────────────

    def get_hints(self) -> dict:
        """Return experience-level-appropriate hint text for the info panel."""
        return {
            "beginner": (
                "🎹  Keyboard Layout\n\n"
                "Choose the layout that matches the physical keys on your keyboard.\n\n"
                "Most English keyboards use 'us'. If you're in the UK, choose 'uk'. "
                "For other countries, try searching for your country code "
                "(e.g. 'de' for Germany, 'fr' for France).\n\n"
                "Use the 'Apply Keymap' button to test it, then type in the box "
                "to make sure your keys produce the right characters."
            ),
            "intermediate": (
                "🎹  Keyboard Layout\n\n"
                "Selects the console keymap written to /etc/vconsole.conf as KEYMAP=.\n\n"
                "This affects the TTY only — X11 and Wayland use separate "
                "configuration (xorg.conf.d or libxkbcommon).\n\n"
                "'Apply Keymap' runs loadkeys for a live preview. "
                "The permanent setting is written via localectl set-keymap "
                "inside the arch-chroot during installation."
            ),
            "advanced": (
                "🎹  Keyboard Layout\n\n"
                "Sets KEYMAP= in /etc/vconsole.conf, applied by systemd-vconsole-setup "
                "on boot.\n\n"
                "Live preview uses loadkeys. Persistent config is written with "
                "localectl set-keymap inside arch-chroot.\n\n"
                "X11/Wayland layout configuration is handled separately at Stage 11. "
                "Compose keys, dead keys, and layout variants are X11 concerns.\n\n"
                "Keymaps are in /usr/share/kbd/keymaps/."
            ),
        }

    # ── Content area (called by BaseScreen._build_shell) ──────────────────────

    def build_content(self) -> Gtk.Widget:
        """
        Build and return the left-side content widget.
        BaseScreen calls this automatically during __init__.
        """
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # ── Filter / search row ───────────────────────────────────────────────
        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        search_label = Gtk.Label(label="Filter:")
        search_label.get_style_context().add_class("section-heading")
        search_row.pack_start(search_label, False, False, 0)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Type to filter — e.g. us, de, fr, uk …")
        self._search_entry.connect("search-changed", self._on_search_changed)
        search_row.pack_start(self._search_entry, True, True, 0)

        root.pack_start(search_row, False, False, 0)

        # ── Keymap list ───────────────────────────────────────────────────────
        # GTK TreeView with a filter model so typing in the search box
        # instantly narrows the list without reloading it.
        list_frame = Gtk.Frame()
        list_frame.get_style_context().add_class("card")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(220)
        scrolled.set_max_content_height(300)

        # ListStore holds the raw data; filter_model is what the TreeView displays
        self._store = Gtk.ListStore(str)          # one column: keymap name
        self._filter_model = self._store.filter_new()
        self._filter_model.set_visible_func(self._row_is_visible)

        self._tree = Gtk.TreeView(model=self._filter_model)
        self._tree.set_headers_visible(False)
        self._tree.set_activate_on_single_click(True)

        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Keymap", renderer, text=0)
        self._tree.append_column(col)

        # cursor-changed fires when the highlighted row changes (single click)
        self._tree.connect("cursor-changed", self._on_selection_changed)
        # row-activated fires on double-click — we use it to apply immediately
        self._tree.connect("row-activated", self._on_row_double_clicked)

        scrolled.add(self._tree)
        list_frame.add(scrolled)
        root.pack_start(list_frame, True, True, 0)

        # ── Loading spinner (visible until keymaps finish loading) ────────────
        self._spinner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._spinner_box.set_halign(Gtk.Align.CENTER)

        spinner = Gtk.Spinner()
        spinner.start()
        self._spinner_box.pack_start(spinner, False, False, 0)

        spinner_lbl = Gtk.Label(label="Loading keymaps…")
        spinner_lbl.get_style_context().add_class("detail-value")
        self._spinner_box.pack_start(spinner_lbl, False, False, 0)

        root.pack_start(self._spinner_box, False, False, 0)

        # ── "Currently selected" display ──────────────────────────────────────
        sel_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        sel_key = Gtk.Label(label="Selected:")
        sel_key.get_style_context().add_class("detail-key")
        sel_row.pack_start(sel_key, False, False, 0)

        self._selected_label = Gtk.Label(label=self._selected_keymap)
        self._selected_label.get_style_context().add_class("detail-value")
        self._selected_label.set_xalign(0)
        sel_row.pack_start(self._selected_label, True, True, 0)

        root.pack_start(sel_row, False, False, 0)

        # ── Test area ─────────────────────────────────────────────────────────
        # A card containing a text entry so the user can type and verify
        # that keys produce the expected characters after applying a keymap.
        test_frame = Gtk.Frame()
        test_frame.get_style_context().add_class("card")

        test_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        test_box.set_margin_start(14)
        test_box.set_margin_end(14)
        test_box.set_margin_top(12)
        test_box.set_margin_bottom(12)

        test_heading = Gtk.Label(label="Test Your Keymap")
        test_heading.get_style_context().add_class("section-heading")
        test_heading.set_xalign(0)
        test_box.pack_start(test_heading, False, False, 0)

        test_hint = Gtk.Label(
            label="Select a keymap, click 'Apply Keymap', then type below to verify it."
        )
        test_hint.get_style_context().add_class("detail-value")
        test_hint.set_xalign(0)
        test_hint.set_line_wrap(True)
        test_box.pack_start(test_hint, False, False, 0)

        # Monospace so special characters and spacing are easy to check
        self._test_entry = Gtk.Entry()
        self._test_entry.set_placeholder_text("Type here after applying a keymap…")
        self._test_entry.override_font(Pango.FontDescription("Monospace 12"))
        test_box.pack_start(self._test_entry, False, False, 0)

        # Apply button + status message on the same row
        apply_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self._apply_btn = Gtk.Button(label="Apply Keymap")
        self._apply_btn.get_style_context().add_class("action-button")
        self._apply_btn.connect("clicked", self._on_apply_clicked)
        apply_row.pack_start(self._apply_btn, False, False, 0)

        self._apply_status = Gtk.Label(label="")
        self._apply_status.set_xalign(0)
        self._apply_status.set_line_wrap(True)
        apply_row.pack_start(self._apply_status, True, True, 0)

        test_box.pack_start(apply_row, False, False, 0)
        test_frame.add(test_box)
        root.pack_start(test_frame, False, False, 0)

        return root

    # ── Async keymap loading ──────────────────────────────────────────────────

    def _load_keymaps_async(self):
        """Fetch the keymap list in a background thread so the UI stays responsive."""
        def _worker():
            keymaps = list_keymaps()
            # GLib.idle_add schedules the UI update back on the main GTK thread
            GLib.idle_add(self._on_keymaps_loaded, keymaps)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_keymaps_loaded(self, keymaps: list):
        """Called on the GTK main thread once the keymap list is ready."""
        self._spinner_box.hide()

        for km in keymaps:
            self._store.append([km])

        # Scroll to and highlight whatever was previously selected
        self._scroll_to_keymap(self._selected_keymap)
        self.set_next_enabled(bool(self._selected_keymap))

        return False  # tells GLib.idle_add not to call this again

    # ── List filtering ────────────────────────────────────────────────────────

    def _row_is_visible(self, model, iter_, data):
        """
        Called by GTK for every row to decide whether to show it.
        Returns True if the row should be visible given the current search text.
        """
        query = self._search_entry.get_text().strip().lower()
        if not query:
            return True   # no filter → show everything
        return query in model.get_value(iter_, 0).lower()

    def _on_search_changed(self, entry):
        """Re-filter the list every time the user types in the search box."""
        self._filter_model.refilter()

        # Convenience: if only one result is left, auto-select it
        if self._filter_model.iter_n_children(None) == 1:
            first_path = Gtk.TreePath.new_first()
            self._tree.set_cursor(first_path, None, False)
            self._on_selection_changed(self._tree)

    # ── Selection handling ────────────────────────────────────────────────────

    def _on_selection_changed(self, tree):
        """Called whenever the highlighted row in the list changes."""
        model, it = tree.get_selection().get_selected()
        if it is None:
            return

        km = model.get_value(it, 0)
        self._selected_keymap = km
        self._selected_label.set_text(km)

        # Clear any old apply status message when a new keymap is picked
        self._apply_status.set_text("")
        ctx = self._apply_status.get_style_context()
        ctx.remove_class("status-ok")
        ctx.remove_class("status-error")

        self.set_next_enabled(True)

    def _on_row_double_clicked(self, tree, path, column):
        """Double-clicking a row applies the keymap immediately — handy shortcut."""
        self._on_apply_clicked(None)

    def _scroll_to_keymap(self, keymap: str):
        """Find a keymap in the list, highlight it, and scroll to it."""
        it = self._filter_model.get_iter_first()
        while it:
            if self._filter_model.get_value(it, 0) == keymap:
                path = self._filter_model.get_path(it)
                self._tree.set_cursor(path, None, False)
                # True = align to centre; 0.4 = slightly above centre looks natural
                self._tree.scroll_to_cell(path, None, True, 0.4, 0)
                return
            it = self._filter_model.iter_next(it)

    # ── Apply keymap via loadkeys ─────────────────────────────────────────────

    def _on_apply_clicked(self, btn):
        """Run loadkeys in a background thread to preview the selected keymap."""
        if self._apply_in_progress or not self._selected_keymap:
            return

        self._apply_in_progress = True
        self._apply_btn.set_sensitive(False)
        self._apply_status.set_text("Applying…")
        ctx = self._apply_status.get_style_context()
        ctx.remove_class("status-ok")
        ctx.remove_class("status-error")

        km = self._selected_keymap  # capture now — don't read self in the thread

        def _worker():
            ok, msg = apply_keymap(km)
            GLib.idle_add(self._on_apply_done, ok, msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_apply_done(self, ok: bool, msg: str):
        """Called back on the GTK main thread when loadkeys finishes."""
        self._apply_in_progress = False
        self._apply_btn.set_sensitive(True)
        self._apply_status.set_text(msg)

        ctx = self._apply_status.get_style_context()
        if ok:
            ctx.add_class("status-ok")
            ctx.remove_class("status-error")
            # Move focus to the test entry so the user can start typing immediately
            self._test_entry.grab_focus()
        else:
            ctx.add_class("status-error")
            ctx.remove_class("status-ok")

        return False  # GLib.idle_add one-shot

    # ── Validation and state save ─────────────────────────────────────────────

    def validate(self):
        """
        Called by BaseScreen when Next is clicked.
        Returns (True, '') to allow navigation, or (False, 'message') to block it.
        """
        if not self._selected_keymap:
            return False, "Please select a keyboard layout before continuing."
        return True, ""

    def on_next(self):
        """
        Called by BaseScreen after validate() passes, just before navigating away.
        This is where we save the selection to the shared state object.
        """
        self.state.keyboard_layout = self._selected_keymap
