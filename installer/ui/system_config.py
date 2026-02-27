"""
installer/ui/system_config.py
------------------------------
Stage 11 — System Configuration

Covers hostname and root password. Clean and simple.

Experience level behaviour:
  Beginner:     Hostname + root password. Plain language, strong guardrails.
  Intermediate: Same + NTP toggle and hardware clock explanation.
  Advanced:     Same + hosts file preview, locale.conf note.

Saves to:
    state.hostname        — e.g. 'my-arch-pc'
    state.root_password   — root account password string
    state.enable_ntp      — bool (new field, default True)
"""

import re

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen


# Valid hostname: letters, digits, hyphens. Must start/end with letter or digit.
_HOSTNAME_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$')

# Password strength thresholds (score 0-4)
def _pw_score(pw: str) -> int:
    if len(pw) == 0:
        return 0
    score = 0
    if len(pw) >= 8:
        score += 1
    if len(pw) >= 12:
        score += 1
    if re.search(r'[A-Z]', pw) and re.search(r'[a-z]', pw):
        score += 1
    if re.search(r'[0-9]', pw) and re.search(r'[^a-zA-Z0-9]', pw):
        score += 1
    return score

_PW_LABELS = ["", "Weak", "Fair", "Good", "Strong"]
_PW_CLASSES = ["", "passphrase-weak", "passphrase-fair",
               "passphrase-good", "passphrase-strong"]


class SystemConfigScreen(BaseScreen):
    """Stage 11 — System Configuration."""

    title    = "System Configuration"
    subtitle = "Set your hostname and root password"

    WIKI_LINKS = [
        ("Hostname",         "https://wiki.archlinux.org/title/Network_configuration#Set_the_hostname"),
        ("Root password",    "https://wiki.archlinux.org/title/Users_and_groups#Root_account"),
        ("systemd-timesyncd","https://wiki.archlinux.org/title/Systemd-timesyncd"),
    ]

    def __init__(self, state, on_next, on_back):
        self._enable_ntp = getattr(state, "enable_ntp", True)

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(False)
        GLib.idle_add(self._validate_all)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "🖥  System Configuration\n\n"
                "Hostname: the name your computer goes by on the network. "
                "Use letters, numbers, and hyphens only — no spaces.\n\n"
                "Root password: the master password for system administration. "
                "Make it strong — you'll use it for things like installing "
                "software and fixing problems.\n\n"
                "You'll create your personal user account on the next screen."
            ),
            "intermediate": (
                "🖥  System Configuration\n\n"
                "The hostname is written to /etc/hostname and referenced in "
                "/etc/hosts.\n\n"
                "NTP sync keeps your clock accurate via systemd-timesyncd. "
                "It's enabled by default and recommended for most systems.\n\n"
                "Root password is set with  passwd  inside arch-chroot. "
                "Keep it separate from your user password."
            ),
            "advanced": (
                "🖥  System Configuration\n\n"
                "Hostname rules: RFC 1123 compliant, max 63 chars per label, "
                "max 253 chars total. Hyphens allowed but not at start/end.\n\n"
                "/etc/hosts will have 127.0.0.1 and ::1 entries pointing to "
                "your hostname for loopback resolution.\n\n"
                "timesyncd uses pool.ntp.org by default. Edit "
                "/etc/systemd/timesyncd.conf post-install for custom servers."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        root.pack_start(self._build_hostname_card(), False, False, 0)
        root.pack_start(self._build_password_card(), False, False, 0)

        self._ntp_card = self._build_ntp_card()
        root.pack_start(self._ntp_card, False, False, 0)

        self._advanced_card = self._build_advanced_card()
        root.pack_start(self._advanced_card, False, False, 0)

        GLib.idle_add(self._apply_level_visibility)

        return root

    # ── Hostname card ─────────────────────────────────────────────────────────

    def _build_hostname_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Computer name (hostname):")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        hint = Gtk.Label(
            label="Letters, numbers, and hyphens only. No spaces."
        )
        hint.get_style_context().add_class("detail-key")
        hint.set_xalign(0)
        box.pack_start(hint, False, False, 0)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self._hostname_entry = Gtk.Entry()
        self._hostname_entry.set_text(self.state.hostname or "archlinux")
        self._hostname_entry.set_max_length(63)
        self._hostname_entry.set_hexpand(True)
        self._hostname_entry.connect("changed", self._on_hostname_changed)
        entry_row.pack_start(self._hostname_entry, True, True, 0)

        self._hostname_status = Gtk.Label(label="")
        self._hostname_status.set_width_chars(8)
        entry_row.pack_start(self._hostname_status, False, False, 0)

        box.pack_start(entry_row, False, False, 0)

        self._hostname_error = Gtk.Label(label="")
        self._hostname_error.get_style_context().add_class("error-label")
        self._hostname_error.set_xalign(0)
        box.pack_start(self._hostname_error, False, False, 0)

        frame.add(box)
        return frame

    def _on_hostname_changed(self, entry):
        self._validate_all()

    # ── Password card ─────────────────────────────────────────────────────────

    def _build_password_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Root password:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # Password entry row
        pw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self._pw_entry = Gtk.Entry()
        self._pw_entry.set_visibility(False)
        self._pw_entry.set_placeholder_text("Root password")
        self._pw_entry.set_hexpand(True)
        self._pw_entry.connect("changed", self._on_password_changed)
        pw_row.pack_start(self._pw_entry, True, True, 0)

        # Show/hide toggle
        self._pw_show_btn = Gtk.ToggleButton(label="👁")
        self._pw_show_btn.get_style_context().add_class("action-button")
        self._pw_show_btn.connect("toggled", self._on_show_toggled)
        pw_row.pack_start(self._pw_show_btn, False, False, 0)

        box.pack_start(pw_row, False, False, 0)

        # Strength bar
        self._pw_strength = Gtk.ProgressBar()
        self._pw_strength.set_fraction(0.0)
        self._pw_strength.set_show_text(True)
        self._pw_strength.set_text("")
        self._pw_strength.get_style_context().add_class("strength-weak")
        box.pack_start(self._pw_strength, False, False, 0)

        # Confirm entry
        confirm_lbl = Gtk.Label(label="Confirm password:")
        confirm_lbl.get_style_context().add_class("detail-key")
        confirm_lbl.set_xalign(0)
        box.pack_start(confirm_lbl, False, False, 0)

        confirm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self._confirm_entry = Gtk.Entry()
        self._confirm_entry.set_visibility(False)
        self._confirm_entry.set_placeholder_text("Confirm root password")
        self._confirm_entry.set_hexpand(True)
        self._confirm_entry.connect("changed", self._on_password_changed)
        confirm_row.pack_start(self._confirm_entry, True, True, 0)

        self._pw_match_label = Gtk.Label(label="")
        self._pw_match_label.set_width_chars(10)
        confirm_row.pack_start(self._pw_match_label, False, False, 0)

        box.pack_start(confirm_row, False, False, 0)

        self._pw_error = Gtk.Label(label="")
        self._pw_error.get_style_context().add_class("error-label")
        self._pw_error.set_xalign(0)
        box.pack_start(self._pw_error, False, False, 0)

        # Pre-fill if coming back with a password already set
        if self.state.root_password:
            self._pw_entry.set_text(self.state.root_password)
            self._confirm_entry.set_text(self.state.root_password)

        frame.add(box)
        return frame

    def _on_show_toggled(self, btn):
        visible = btn.get_active()
        self._pw_entry.set_visibility(visible)
        self._confirm_entry.set_visibility(visible)

    def _on_password_changed(self, entry):
        pw = self._pw_entry.get_text()
        score = _pw_score(pw)

        # Update strength bar
        fraction = score / 4.0
        self._pw_strength.set_fraction(fraction)
        label = _PW_LABELS[score] if pw else ""
        self._pw_strength.set_text(label)

        # Colour the entry border
        ctx = self._pw_entry.get_style_context()
        for cls in _PW_CLASSES[1:]:
            ctx.remove_class(cls)
        if pw and score > 0:
            ctx.add_class(_PW_CLASSES[score])

        # Colour the strength bar using direct RGBA (GTK3 CSS class on progressbar
        # children doesn't work reliably — override_background_color is reliable)
        from gi.repository import Gdk
        bar_colors = [
            None,                              # score 0 — empty
            Gdk.RGBA(0.973, 0.318, 0.286, 1), # score 1 — red    #f85149
            Gdk.RGBA(0.824, 0.600, 0.133, 1), # score 2 — yellow #d29922
            Gdk.RGBA(0.247, 0.722, 0.314, 1), # score 3 — green  #3fb950
            Gdk.RGBA(0.345, 0.651, 1.000, 1), # score 4 — blue   #58a6ff
        ]
        if pw and score > 0:
            self._pw_strength.override_background_color(Gtk.StateFlags.NORMAL, bar_colors[score])
        else:
            self._pw_strength.override_background_color(Gtk.StateFlags.NORMAL, None)

        self._validate_all()

    # ── NTP card (Intermediate+) ──────────────────────────────────────────────

    def _build_ntp_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Clock settings:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # NTP toggle — CheckButton is compact and clear
        self._ntp_check = Gtk.CheckButton(
            label="Enable NTP time synchronisation  (systemd-timesyncd — recommended)"
        )
        self._ntp_check.get_style_context().add_class("detail-value")
        self._ntp_check.set_active(self._enable_ntp)
        self._ntp_check.connect("toggled", self._on_ntp_toggled)
        box.pack_start(self._ntp_check, False, False, 0)

        # Hardware clock note
        hwclock_lbl = Gtk.Label(
            label="Hardware clock is set to UTC — correct for Linux and safe for dual-boot."
        )
        hwclock_lbl.get_style_context().add_class("detail-key")
        hwclock_lbl.set_xalign(0)
        hwclock_lbl.set_line_wrap(True)
        box.pack_start(hwclock_lbl, False, False, 0)

        frame.add(box)
        return frame

    def _on_ntp_toggled(self, chk):
        self._enable_ntp = chk.get_active()

    # ── Advanced card ─────────────────────────────────────────────────────────

    def _build_advanced_card(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Files that will be written:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        self._hosts_preview = Gtk.Label()
        self._hosts_preview.get_style_context().add_class("detail-value")
        self._hosts_preview.override_font(Pango.FontDescription("Monospace 10"))
        self._hosts_preview.set_xalign(0)
        self._hosts_preview.set_selectable(True)
        self._update_hosts_preview()
        box.pack_start(self._hosts_preview, False, False, 0)

        frame.add(box)
        return frame

    def _update_hosts_preview(self):
        if not hasattr(self, "_hosts_preview"):
            return
        hostname = self._hostname_entry.get_text().strip() if hasattr(self, "_hostname_entry") else "archlinux"
        if not hostname:
            hostname = "archlinux"
        preview = (
            f"/etc/hostname\n"
            f"  {hostname}\n\n"
            f"/etc/hosts\n"
            f"  127.0.0.1   localhost\n"
            f"  ::1         localhost\n"
            f"  127.0.1.1   {hostname}.localdomain  {hostname}"
        )
        self._hosts_preview.set_text(preview)

    # ── Level visibility ──────────────────────────────────────────────────────

    def _apply_level_visibility(self):
        level = self.state.experience_level
        if level == "beginner":
            self._ntp_card.hide()
            self._advanced_card.hide()
        elif level == "intermediate":
            self._ntp_card.show_all()
            self._advanced_card.hide()
        else:
            self._ntp_card.show_all()
            self._advanced_card.show_all()
        return False

    def on_experience_changed(self):
        self._apply_level_visibility()
        self.refresh_hints()

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_all(self):
        ok = True

        # Hostname
        hostname = self._hostname_entry.get_text().strip()
        if not hostname:
            self._hostname_status.set_text("")
            self._hostname_error.set_text("Hostname cannot be empty.")
            ok = False
        elif not _HOSTNAME_RE.match(hostname):
            self._hostname_status.set_text("✗")
            self._hostname_status.get_style_context().remove_class("status-ok")
            self._hostname_status.get_style_context().add_class("status-error")
            self._hostname_error.set_text(
                "Invalid hostname. Use letters, numbers and hyphens only. "
                "Cannot start or end with a hyphen."
            )
            ok = False
        else:
            self._hostname_status.set_text("✓")
            self._hostname_status.get_style_context().remove_class("status-error")
            self._hostname_status.get_style_context().add_class("status-ok")
            self._hostname_error.set_text("")
            self._update_hosts_preview()

        # Password
        pw = self._pw_entry.get_text()
        confirm = self._confirm_entry.get_text()

        if not pw:
            self._pw_match_label.set_text("")
            self._pw_error.set_text("Root password cannot be empty.")
            ok = False
        elif len(pw) < 6:
            self._pw_error.set_text("Password must be at least 6 characters.")
            ok = False
        elif pw != confirm:
            self._pw_match_label.set_text("✗  No match")
            self._pw_match_label.get_style_context().remove_class("status-ok")
            self._pw_match_label.get_style_context().add_class("status-error")
            self._pw_error.set_text("")
            ok = False
        else:
            self._pw_match_label.set_text("✓  Match")
            self._pw_match_label.get_style_context().remove_class("status-error")
            self._pw_match_label.get_style_context().add_class("status-ok")
            self._pw_error.set_text("")

        self.set_next_enabled(ok)

    def validate(self):
        hostname = self._hostname_entry.get_text().strip()
        if not hostname or not _HOSTNAME_RE.match(hostname):
            return False, "Enter a valid hostname."
        pw = self._pw_entry.get_text()
        if not pw or len(pw) < 6:
            return False, "Root password must be at least 6 characters."
        if pw != self._confirm_entry.get_text():
            return False, "Passwords do not match."
        return True, ""

    def on_next(self):
        self.state.hostname      = self._hostname_entry.get_text().strip()
        self.state.root_password = self._pw_entry.get_text()
        self.state.enable_ntp    = self._enable_ntp
