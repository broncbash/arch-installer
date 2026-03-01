"""
installer/wiki/viewer.py
Non-modal Arch Wiki viewer built on WebKit2GTK.

Usage:
    from installer.wiki.viewer import open_wiki
    open_wiki("https://wiki.archlinux.org/title/Iwd")

Multiple viewer windows can be open simultaneously.
"""

import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("WebKit2", "4.1")
    from gi.repository import WebKit2
    WEBKIT_AVAILABLE = True
except (ValueError, ImportError):
    try:
        gi.require_version("WebKit2", "4.0")
        from gi.repository import WebKit2
        WEBKIT_AVAILABLE = True
    except (ValueError, ImportError):
        WEBKIT_AVAILABLE = False

from gi.repository import Gtk, Gdk, GLib


# ---------------------------------------------------------------------------
# CSS for the viewer window (matches main installer dark theme)
# ---------------------------------------------------------------------------
_VIEWER_CSS = b"""
window {
    background-color: #0d1117;
    color: #c9d1d9;
}
.toolbar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 6px 8px;
}
.toolbar button {
    background-color: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    padding: 4px 10px;
    min-width: 0;
}
.toolbar button:hover {
    background-color: #21262d;
    border-color: #58a6ff;
}
.url-bar {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #8b949e;
    padding: 4px 10px;
    font-family: monospace;
    font-size: 11px;
}
.no-network-box {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 32px;
    margin: 48px;
}
.no-network-title {
    font-size: 18px;
    font-weight: bold;
    color: #f0883e;
}
.no-network-body {
    color: #8b949e;
    margin-top: 8px;
}
.no-network-url {
    font-family: monospace;
    color: #58a6ff;
    margin-top: 16px;
    font-size: 12px;
}
"""


def _apply_viewer_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(_VIEWER_CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


# ---------------------------------------------------------------------------
# WikiViewer window
# ---------------------------------------------------------------------------

class WikiViewer(Gtk.Window):
    """A non-modal wiki viewer window."""

    def __init__(self, url: str, connected: bool = True):
        super().__init__(title="Arch Wiki — Installer Reference")
        self.set_default_size(960, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.url = url
        self.connected = connected

        _apply_viewer_css()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        # Toolbar
        toolbar = self._build_toolbar()
        vbox.pack_start(toolbar, False, False, 0)

        # Content area
        if not connected or not WEBKIT_AVAILABLE:
            content = self._build_no_network_page()
        else:
            content = self._build_webview()

        vbox.pack_start(content, True, True, 0)
        self.show_all()

    # ------------------------------------------------------------------
    def _build_toolbar(self) -> Gtk.Box:
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.get_style_context().add_class("toolbar")

        self.btn_back = Gtk.Button(label="◀")
        self.btn_back.get_style_context().add_class("flat")
        self.btn_back.connect("clicked", self._on_back)

        self.btn_forward = Gtk.Button(label="▶")
        self.btn_forward.get_style_context().add_class("flat")
        self.btn_forward.connect("clicked", self._on_forward)

        self.btn_reload = Gtk.Button(label="⟳")
        self.btn_reload.get_style_context().add_class("flat")
        self.btn_reload.connect("clicked", self._on_reload)

        self.url_label = Gtk.Label(label=self.url)
        self.url_label.get_style_context().add_class("url-bar")
        self.url_label.set_hexpand(True)
        self.url_label.set_xalign(0)
        self.url_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

        btn_close = Gtk.Button(label="✕  Close")
        btn_close.connect("clicked", lambda _: self.destroy())

        for w in (self.btn_back, self.btn_forward, self.btn_reload):
            toolbar.pack_start(w, False, False, 0)
        toolbar.pack_start(self.url_label, True, True, 0)
        toolbar.pack_end(btn_close, False, False, 0)

        return toolbar

    # ------------------------------------------------------------------
    def _build_webview(self) -> Gtk.Widget:
        self.webview = WebKit2.WebView()

        # Dark background before page loads
        bg = WebKit2.WebView.get_background_color(self.webview) if hasattr(self.webview, "get_background_color") else None
        try:
            from gi.repository import Gdk as _Gdk
            color = _Gdk.RGBA()
            color.parse("#0d1117")
            self.webview.set_background_color(color)
        except Exception:
            pass

        self.webview.load_uri(self.url)
        self.webview.connect("notify::uri", self._on_uri_changed)
        self.webview.connect("notify::title", self._on_title_changed)

        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.webview)
        return scrolled

    # ------------------------------------------------------------------
    def _build_no_network_page(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("no-network-box")

        if not WEBKIT_AVAILABLE:
            reason = "WebKit2GTK is not installed."
            hint = (
                "Install the webkit2gtk package to enable the in-app wiki viewer.\n"
                "You can still visit the page in an external browser."
            )
        else:
            reason = "No network connection yet."
            hint = (
                "Complete Stage 1 (Network Setup) to browse the Arch Wiki\n"
                "directly in this window. Until then, here is the raw URL:"
            )

        title = Gtk.Label(label=f"📡  {reason}")
        title.get_style_context().add_class("no-network-title")
        title.set_xalign(0)

        body = Gtk.Label(label=hint)
        body.get_style_context().add_class("no-network-body")
        body.set_xalign(0)
        body.set_line_wrap(True)

        url_lbl = Gtk.Label(label=self.url)
        url_lbl.get_style_context().add_class("no-network-url")
        url_lbl.set_xalign(0)
        url_lbl.set_selectable(True)
        url_lbl.set_line_wrap(True)

        for w in (title, body, url_lbl):
            box.pack_start(w, False, False, 6)

        outer.pack_start(box, False, False, 0)
        return outer

    # ------------------------------------------------------------------
    def _on_back(self, _):
        if hasattr(self, "webview") and self.webview.can_go_back():
            self.webview.go_back()

    def _on_forward(self, _):
        if hasattr(self, "webview") and self.webview.can_go_forward():
            self.webview.go_forward()

    def _on_reload(self, _):
        if hasattr(self, "webview"):
            self.webview.reload()

    def _on_uri_changed(self, webview, _param):
        uri = webview.get_uri() or ""
        GLib.idle_add(self.url_label.set_text, uri)

    def _on_title_changed(self, webview, _param):
        title = webview.get_title() or "Arch Wiki"
        GLib.idle_add(self.set_title, f"{title} — Arch Wiki")


# ---------------------------------------------------------------------------
# Public convenience function
# ---------------------------------------------------------------------------

def open_wiki(url: str, connected: bool = True) -> WikiViewer:
    """
    Open a new non-modal wiki viewer window pointed at `url`.
    `connected` should reflect whether network is currently available.
    Returns the WikiViewer instance (caller need not retain it).
    """
    viewer = WikiViewer(url=url, connected=connected)
    viewer.connect("destroy", lambda _: None)  # keeps GC from collecting it
    return viewer
