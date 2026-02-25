"""
installer/ui/network.py — DEBUG VERSION
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from installer.ui.base_screen import BaseScreen
from installer.backend import network as net_backend

WIKI_LINKS = [
    ("Network configuration",                    "https://wiki.archlinux.org/title/Network_configuration"),
    ("iwd",                                      "https://wiki.archlinux.org/title/Iwd"),
    ("Installation guide — Connect to internet", "https://wiki.archlinux.org/title/Installation_guide#Connect_to_the_internet"),
]

class NetworkScreen(BaseScreen):
    title    = "Network Setup"
    subtitle = "Connect to the internet before continuing."

    def __init__(self, state, on_next=None, on_back=None):
        self._connected = False
        self._wifi_networks: list[dict] = []
        self._selected_ssid: str = ""
        super().__init__(state=state, on_next=on_next, on_back=on_back)
        self._refresh_status()

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "An internet connection lets you browse the Arch Wiki right inside "
                "the installer, and is required later to download packages.\n\n"
                "If you plugged in an ethernet cable, you're probably already "
                "connected — check the status above and click Next.\n\n"
                "For Wi-Fi, click Scan, pick your network, and enter your password."
            ),
            "intermediate": (
                "Ethernet connections are brought up automatically via DHCP. "
                "Wi-Fi is managed by iwd (iwctl under the hood).\n\n"
                "This stage is required for the integrated Arch Wiki viewer and "
                "for reflector (Stage 7) and pacstrap (Stage 9).\n\n"
                "You can skip if you intend to install without internet access."
            ),
            "advanced": (
                "Ethernet: DHCP via systemd-networkd or dhcpcd depending on ISO.\n"
                "Wi-Fi: managed via iwd.\n\n"
                "Commands used:\n"
                "  iwctl station <iface> scan\n"
                "  iwctl station <iface> get-networks\n"
                "  iwctl --passphrase <pw> station <iface> connect <ssid>\n\n"
                "Connectivity is confirmed via DNS resolution + TCP connect to "
                "archlinux.org:443. Skip to proceed without network."
            ),
        }

    def validate(self):
        if not self._connected:
            return False, "Not connected. Use Skip to continue without network."
        return True, ""

    def on_next(self):
        self.state.network_connected = self._connected
        self.state.network_skipped   = False
        self.state.network_ok        = self._connected

    def build_content(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        box.pack_start(self._build_status_card(),    False, False, 0)
        box.pack_start(self._build_wiki_links(),     False, False, 0)

        wifi_lbl = Gtk.Label(label="Wi-Fi")
        wifi_lbl.get_style_context().add_class("section-heading")
        wifi_lbl.set_xalign(0)
        box.pack_start(wifi_lbl, False, False, 0)

        box.pack_start(self._build_scan_row(),       False, False, 0)
        box.pack_start(self._build_network_list(),   False, False, 0)
        box.pack_start(self._build_passphrase_row(), False, False, 0)

        self.connect_feedback = Gtk.Label(label="")
        self.connect_feedback.set_xalign(0)
        self.connect_feedback.set_line_wrap(True)
        box.pack_start(self.connect_feedback, False, False, 0)

        skip_btn = Gtk.Button(label="Skip — continue without network  →")
        skip_btn.get_style_context().add_class("nav-btn")
        skip_btn.set_halign(Gtk.Align.START)
        skip_btn.set_tooltip_text(
            "The Arch Wiki viewer will be limited and pacstrap will fail "
            "without a connection."
        )
        skip_btn.connect("clicked", self._on_skip)
        box.pack_start(skip_btn, False, False, 8)
        return box

    def _build_status_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status_icon  = Gtk.Label(label="⏳")
        self.status_label = Gtk.Label(label="Checking connectivity…")
        self.status_label.set_xalign(0)
        self.status_label.set_hexpand(True)

        self.btn_refresh = Gtk.Button(label="Refresh")
        self.btn_refresh.connect("clicked", lambda _: self._refresh_status())

        header.pack_start(self.status_icon,  False, False, 0)
        header.pack_start(self.status_label, True,  True,  0)
        header.pack_end(self.btn_refresh,    False, False, 0)
        vbox.pack_start(header, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(4)
        grid.set_margin_top(8)

        self._detail_values: dict[str, Gtk.Label] = {}
        for i, key in enumerate(["Interface", "IP address", "Type", "SSID"]):
            k = Gtk.Label(label=f"{key}:")
            k.get_style_context().add_class("detail-key")
            k.set_xalign(1)
            v = Gtk.Label(label="—")
            v.get_style_context().add_class("detail-value")
            v.set_xalign(0)
            v.set_selectable(True)
            grid.attach(k, 0, i, 1, 1)
            grid.attach(v, 1, i, 1, 1)
            self._detail_values[key] = v

        vbox.pack_start(grid, False, False, 0)
        frame.add(vbox)
        return frame

    def _build_wiki_links(self) -> Gtk.Widget:
        # Outer labeled frame
        frame = Gtk.Frame()
        frame.get_style_context().add_class("wiki-frame")

        # Frame label widget (replaces the default plain-text label)
        frame_label = Gtk.Label()
        frame_label.set_markup("<b>📖  Arch Wiki</b>")
        frame_label.get_style_context().add_class("wiki-frame-title")
        frame.set_label_widget(frame_label)

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        inner.set_margin_top(8)
        inner.set_margin_bottom(10)
        inner.set_margin_start(12)
        inner.set_margin_end(12)

        for label, url in WIKI_LINKS:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("wiki-link-button")
            btn.connect("clicked", self._open_wiki, url)
            inner.pack_start(btn, False, False, 0)

        frame.add(inner)
        return frame

    def _build_scan_row(self) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_scan = Gtk.Button(label="🔍  Scan for Networks")
        self.btn_scan.get_style_context().add_class("action-button")
        self.btn_scan.connect("clicked", self._on_scan)
        self.scan_spinner = Gtk.Spinner()
        row.pack_start(self.btn_scan,     False, False, 0)
        row.pack_start(self.scan_spinner, False, False, 0)
        return row

    def _build_network_list(self) -> Gtk.Widget:
        self.network_store = Gtk.ListStore(str, str, str)
        self.network_list  = Gtk.TreeView(model=self.network_store)
        self.network_list.set_headers_visible(True)
        self.network_list.get_selection().connect("changed", self._on_network_selected)

        for col_idx, (heading, col_num) in enumerate([
            ("Network (SSID)", 0),
            ("Security",       1),
            ("Signal",         2),
        ]):
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(heading, renderer, text=col_num)
            col.set_resizable(True)
            if col_idx == 0:
                col.set_expand(True)
            self.network_list.append_column(col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(160)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.network_list)
        scrolled.get_style_context().add_class("card")
        return scrolled

    def _build_passphrase_row(self) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.pass_entry = Gtk.Entry()
        self.pass_entry.set_placeholder_text("Passphrase (leave empty for open networks)")
        self.pass_entry.set_visibility(False)
        self.pass_entry.set_hexpand(True)
        self.pass_entry.connect("activate", self._on_connect)

        self.show_pass_btn = Gtk.ToggleButton(label="👁")
        self.show_pass_btn.connect("toggled",
            lambda btn: self.pass_entry.set_visibility(btn.get_active()))

        self.btn_connect = Gtk.Button(label="Connect")
        self.btn_connect.get_style_context().add_class("action-button")
        self.btn_connect.set_sensitive(False)
        self.btn_connect.connect("clicked", self._on_connect)

        self.connect_spinner = Gtk.Spinner()

        row.pack_start(self.pass_entry,      True,  True,  0)
        row.pack_start(self.show_pass_btn,   False, False, 0)
        row.pack_start(self.btn_connect,     False, False, 0)
        row.pack_start(self.connect_spinner, False, False, 0)
        return row

    def _refresh_status(self):
        self.status_icon.set_text("⏳")
        self.status_label.set_text("Checking connectivity…")
        self.btn_refresh.set_sensitive(False)
        threading.Thread(target=self._check_status_thread, daemon=True).start()

    def _check_status_thread(self):
        connected, msg = net_backend.check_connectivity()
        info = net_backend.get_interface_info()
        GLib.idle_add(self._update_status_ui, connected, msg, info)

    def _update_status_ui(self, connected: bool, _msg: str, info: dict):
        self._connected = connected

        if connected:
            self.status_icon.set_text("✅")
            self.status_label.set_text("Connected — internet reachable")
        else:
            self.status_icon.set_text("❌")
            self.status_label.set_text("No connection detected")

        self._detail_values["Interface"].set_text(info.get("interface") or "—")
        self._detail_values["IP address"].set_text(info.get("ip")        or "—")
        self._detail_values["Type"].set_text(info.get("type", "unknown").capitalize())
        self._detail_values["SSID"].set_text(info.get("ssid")            or "—")

        self.btn_refresh.set_sensitive(True)
        self.state.network_ok        = connected
        self.state.network_connected = connected

    def _on_scan(self, _btn):
        self.btn_scan.set_sensitive(False)
        self.scan_spinner.start()
        self.network_store.clear()
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        ok, result = net_backend.list_wifi_networks()
        GLib.idle_add(self._update_network_list, ok, result)

    def _update_network_list(self, ok: bool, result):
        self.scan_spinner.stop()
        self.btn_scan.set_sensitive(True)
        self.network_store.clear()

        if not ok:
            self.connect_feedback.set_text(f"Scan failed: {result}")
            return

        self._wifi_networks = result
        for nw in result:
            prefix = "▶ " if nw["connected"] else ""
            self.network_store.append([prefix + nw["ssid"], nw["security"], nw["signal"]])

        if not result:
            self.connect_feedback.set_text("No networks found. Try scanning again.")

    def _on_network_selected(self, selection):
        model, it = selection.get_selected()
        if it:
            self._selected_ssid = model[it][0].lstrip("▶ ").strip()
            self.btn_connect.set_sensitive(True)
        else:
            self._selected_ssid = ""
            self.btn_connect.set_sensitive(False)

    def _on_connect(self, _widget):
        if not self._selected_ssid:
            return
        passphrase = self.pass_entry.get_text()
        self.btn_connect.set_sensitive(False)
        self.connect_spinner.start()
        self.connect_feedback.set_text(f"Connecting to {self._selected_ssid}…")
        threading.Thread(
            target=self._connect_thread,
            args=(self._selected_ssid, passphrase),
            daemon=True,
        ).start()

    def _connect_thread(self, ssid: str, passphrase: str):
        ok, msg = net_backend.connect_wifi(ssid, passphrase)
        GLib.idle_add(self._on_connect_done, ok, msg)

    def _on_connect_done(self, ok: bool, msg: str):
        self.connect_spinner.stop()
        self.btn_connect.set_sensitive(True)
        self.connect_feedback.set_text(msg)
        if ok:
            self._refresh_status()

    def _open_wiki(self, _btn, url: str):
        from installer.wiki.viewer import open_wiki
        open_wiki(url, connected=self._connected)

    def _on_skip(self, _btn):
        self.state.network_connected = False
        self.state.network_skipped   = True
        self.state.network_ok        = False
        if self._on_next_cb:
            self._on_next_cb()
