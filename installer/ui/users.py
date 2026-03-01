"""
installer/ui/users.py
----------------------
Stage 12 — User Setup

Create one or more user accounts for the installed system.

Experience level behaviour:
  Beginner:     Single user form — username, password + confirm, sudo toggle.
                Clean and simple, no extras.
  Intermediate: Same + shell picker (bash / zsh / fish).
  Advanced:     Same + ability to add multiple users. Each user gets their
                own card with full settings. Users can be removed.

Saves to:
    state.users  — list of dicts:
                   {"username": str, "password": str,
                    "sudo": bool, "shell": str}
"""

import re

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango

from installer.ui.base_screen import BaseScreen


# Valid Linux username: lowercase letters, digits, hyphens, underscores.
# Must start with a letter or underscore. Max 32 chars.
_USERNAME_RE = re.compile(r'^[a-z_][a-z0-9_\-]{0,31}$')

SHELLS = [
    ("/bin/bash",  "bash",  "Default shell, widely compatible"),
    ("/bin/zsh",   "zsh",   "Feature-rich, popular with customisations"),
    ("/bin/fish",  "fish",  "Friendly interactive shell, great defaults"),
]

# Extra groups a desktop user typically wants
# (wheel/sudo is handled separately above)
EXTRA_GROUPS = [
    ("audio",    "Audio devices"),
    ("video",    "Video/GPU devices"),
    ("storage",  "Storage devices (USB, etc.)"),
    ("optical",  "Optical drives"),
    ("input",    "Input devices"),
    ("network",  "Network management"),
    ("lp",       "Printing"),
    ("scanner",  "Scanners"),
]

def _pw_score(pw: str) -> int:
    """Score 0=empty, 1=weak(red), 2=fair(yellow), 3=good(green), 4=strong(blue).
    Any non-empty password starts at 1 (weak/red) immediately."""
    if len(pw) == 0:
        return 0
    # Start at 1 so color appears on first keystroke
    score = 1
    if len(pw) >= 8:  score += 1
    if len(pw) >= 12: score += 1
    if re.search(r'[A-Z]', pw) and re.search(r'[a-z]', pw) and        re.search(r'[0-9]', pw) and re.search(r'[^a-zA-Z0-9]', pw): score += 1
    return min(score, 4)

_PW_LABELS  = ["", "Weak", "Fair", "Good", "Strong"]
_PW_CLASSES = ["", "passphrase-weak", "passphrase-fair",
               "passphrase-good",  "passphrase-strong"]
_BAR_COLORS = [
    None,
    Gdk.RGBA(0.973, 0.318, 0.286, 1),  # red
    Gdk.RGBA(0.824, 0.600, 0.133, 1),  # yellow
    Gdk.RGBA(0.247, 0.722, 0.314, 1),  # green
    Gdk.RGBA(0.345, 0.651, 1.000, 1),  # blue
]


class UsersScreen(BaseScreen):
    """Stage 12 — User Setup."""

    title    = "User Setup"
    subtitle = "Create your user account"

    WIKI_LINKS = [
        ("Users and groups", "https://wiki.archlinux.org/title/Users_and_groups"),
        ("sudo",             "https://wiki.archlinux.org/title/Sudo"),
        ("Zsh",              "https://wiki.archlinux.org/title/Zsh"),
    ]

    def __init__(self, state, on_next, on_back):
        # Restore previous users when coming Back
        self._users = [dict(u) for u in state.users] if state.users else []
        # User form widgets — populated in build_content
        self._user_form_widgets = []  # list of dicts, one per user card

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(False)
        GLib.idle_add(self._apply_level_visibility)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "👤  User Setup\n\n"
                "Create your personal account. This is the account you'll "
                "log in with every day — not the root account.\n\n"
                "Enable 'Administrator (sudo)' so you can run system commands "
                "when needed by typing your password.\n\n"
                "Pick a username with only lowercase letters, numbers, "
                "hyphens, and underscores."
            ),
            "intermediate": (
                "👤  User Setup\n\n"
                "Your user is added to the  wheel  group which grants sudo "
                "access. The sudoers file will have  %wheel ALL=(ALL) ALL.\n\n"
                "Shell choice:\n"
                "• bash — default, always available, most compatible\n"
                "• zsh  — more features, tab completion, popular with Oh My Zsh\n"
                "• fish — great out of the box, syntax highlighting, "
                "not POSIX-compatible\n\n"
                "zsh and fish are installed automatically if selected."
            ),
            "advanced": (
                "👤  User Setup\n\n"
                "Multiple users can be created here. Each gets their own "
                "home directory under /home/<username>.\n\n"
                "useradd -m -G wheel -s <shell> <username>\n"
                "passwd <username>\n\n"
                "The wheel group is used for sudo. Root login is kept "
                "enabled but SSH root login will be disabled by default."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        self._root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        # ── User cards container ──────────────────────────────────────────────
        self._cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._root_box.pack_start(self._cards_box, False, False, 0)

        # ── Add user button (Advanced only) ───────────────────────────────────
        self._add_btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._add_user_btn = Gtk.Button(label="➕  Add another user")
        self._add_user_btn.get_style_context().add_class("action-button")
        self._add_user_btn.connect("clicked", self._on_add_user_clicked)
        self._add_btn_row.pack_start(self._add_user_btn, False, False, 0)
        self._root_box.pack_start(self._add_btn_row, False, False, 0)

        # Build cards for any restored users, or one blank card
        if self._users:
            for u in self._users:
                self._add_user_card(
                    username=u.get("username", ""),
                    password=u.get("password", ""),
                    sudo=u.get("sudo", True),
                    shell=u.get("shell", "/bin/bash"),
                )
        else:
            self._add_user_card()

        GLib.idle_add(self._apply_level_visibility)

        return self._root_box

    # ── User card builder ─────────────────────────────────────────────────────

    def _add_user_card(self, username="", password="", sudo=True, shell="/bin/bash"):
        """Build and add a user card to _cards_box."""
        idx = len(self._user_form_widgets)
        widgets = {}

        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_start(14)
        outer.set_margin_end(14)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)

        # ── Card header ───────────────────────────────────────────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        title = Gtk.Label(label=f"User {idx + 1}" if idx > 0 else "Primary user")
        title.get_style_context().add_class("section-heading")
        title.set_xalign(0)
        widgets["title"] = title
        header.pack_start(title, True, True, 0)

        # Remove button (only for non-primary users)
        if idx > 0:
            remove_btn = Gtk.Button(label="✕  Remove")
            remove_btn.get_style_context().add_class("action-button")
            remove_btn.connect("clicked", self._on_remove_user, frame, idx)
            header.pack_start(remove_btn, False, False, 0)

        outer.pack_start(header, False, False, 0)

        # ── Username ──────────────────────────────────────────────────────────
        uname_lbl = Gtk.Label(label="Username:")
        uname_lbl.get_style_context().add_class("detail-key")
        uname_lbl.set_xalign(0)
        outer.pack_start(uname_lbl, False, False, 0)

        uname_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        uname_entry = Gtk.Entry()
        uname_entry.set_text(username)
        uname_entry.set_placeholder_text("e.g.  john")
        uname_entry.set_max_length(32)
        uname_entry.set_hexpand(True)
        uname_entry.connect("changed", lambda e: self._validate_all())
        widgets["username"] = uname_entry
        uname_row.pack_start(uname_entry, True, True, 0)

        uname_status = Gtk.Label(label="")
        uname_status.set_width_chars(2)
        widgets["uname_status"] = uname_status
        uname_row.pack_start(uname_status, False, False, 0)

        outer.pack_start(uname_row, False, False, 0)

        uname_error = Gtk.Label(label="")
        uname_error.get_style_context().add_class("error-label")
        uname_error.set_xalign(0)
        widgets["uname_error"] = uname_error
        outer.pack_start(uname_error, False, False, 0)

        # ── Password ──────────────────────────────────────────────────────────
        pw_lbl = Gtk.Label(label="Password:")
        pw_lbl.get_style_context().add_class("detail-key")
        pw_lbl.set_xalign(0)
        outer.pack_start(pw_lbl, False, False, 0)

        pw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pw_entry = Gtk.Entry()
        pw_entry.set_visibility(False)
        pw_entry.set_placeholder_text("Password")
        pw_entry.set_text(password)
        pw_entry.set_hexpand(True)
        pw_entry.connect("changed", lambda e, w=widgets: self._on_pw_changed(w))
        widgets["password"] = pw_entry
        pw_row.pack_start(pw_entry, True, True, 0)

        show_btn = Gtk.ToggleButton(label="👁")
        show_btn.get_style_context().add_class("action-button")
        show_btn.connect("toggled", lambda b, w=widgets: self._on_show_toggled(b, w))
        pw_row.pack_start(show_btn, False, False, 0)
        outer.pack_start(pw_row, False, False, 0)

        # Strength bar
        strength_bar = Gtk.ProgressBar()
        strength_bar.set_fraction(0.0)
        strength_bar.set_show_text(True)
        strength_bar.set_text("")
        widgets["strength_bar"] = strength_bar
        outer.pack_start(strength_bar, False, False, 0)

        # Confirm
        confirm_lbl = Gtk.Label(label="Confirm password:")
        confirm_lbl.get_style_context().add_class("detail-key")
        confirm_lbl.set_xalign(0)
        outer.pack_start(confirm_lbl, False, False, 0)

        confirm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        confirm_entry = Gtk.Entry()
        confirm_entry.set_visibility(False)
        confirm_entry.set_placeholder_text("Confirm password")
        confirm_entry.set_hexpand(True)
        confirm_entry.connect("changed", lambda e: self._validate_all())
        widgets["confirm"] = confirm_entry
        confirm_row.pack_start(confirm_entry, True, True, 0)

        match_lbl = Gtk.Label(label="")
        match_lbl.set_width_chars(10)
        widgets["match_lbl"] = match_lbl
        confirm_row.pack_start(match_lbl, False, False, 0)
        outer.pack_start(confirm_row, False, False, 0)

        pw_error = Gtk.Label(label="")
        pw_error.get_style_context().add_class("error-label")
        pw_error.set_xalign(0)
        widgets["pw_error"] = pw_error
        outer.pack_start(pw_error, False, False, 0)

        # ── Sudo toggle ───────────────────────────────────────────────────────
        sudo_check = Gtk.CheckButton(
            label="Administrator (sudo)  — can run system commands with their password"
        )
        sudo_check.get_style_context().add_class("detail-value")
        sudo_check.set_active(sudo)
        sudo_check.connect("toggled", lambda b: self._validate_all())
        widgets["sudo"] = sudo_check
        outer.pack_start(sudo_check, False, False, 0)

        # ── Extra groups ──────────────────────────────────────────────────────
        groups_lbl = Gtk.Label(label="Additional groups:")
        groups_lbl.get_style_context().add_class("detail-key")
        groups_lbl.set_xalign(0)
        outer.pack_start(groups_lbl, False, False, 0)

        groups_flow = Gtk.FlowBox()
        groups_flow.set_max_children_per_line(4)
        groups_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        groups_flow.set_row_spacing(4)
        groups_flow.set_column_spacing(4)

        group_checks = {}
        # Default groups to pre-tick for a typical desktop user
        default_groups = {"audio", "video", "storage", "optical", "input"}
        for group_name, group_desc in EXTRA_GROUPS:
            chk = Gtk.CheckButton(label=group_name)
            chk.get_style_context().add_class("detail-value")
            chk.set_tooltip_text(group_desc)
            chk.set_active(group_name in default_groups)
            chk.connect("toggled", lambda b: self._validate_all())
            group_checks[group_name] = chk
            groups_flow.add(chk)

        widgets["group_checks"] = group_checks
        outer.pack_start(groups_flow, False, False, 0)

        # ── Shell picker (Intermediate+) ──────────────────────────────────────
        shell_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        shell_lbl = Gtk.Label(label="Login shell:")
        shell_lbl.get_style_context().add_class("detail-key")
        shell_lbl.set_xalign(0)
        shell_box.pack_start(shell_lbl, False, False, 0)

        shell_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        shell_group = []
        selected_btn = None
        for path, name, desc in SHELLS:
            if shell_group:
                btn = Gtk.RadioButton.new_with_label_from_widget(
                    shell_group[0], name
                )
            else:
                btn = Gtk.RadioButton.new_with_label(None, name)
            btn.get_style_context().add_class("detail-value")
            btn.set_tooltip_text(desc)
            btn.connect("toggled", lambda b: self._validate_all())
            shell_group.append(btn)
            shell_btn_box.pack_start(btn, False, False, 0)
            if path == shell:
                selected_btn = btn

        if selected_btn:
            selected_btn.set_active(True)

        widgets["shell_group"] = shell_group
        shell_box.pack_start(shell_btn_box, False, False, 0)
        widgets["shell_box"] = shell_box
        outer.pack_start(shell_box, False, False, 0)

        frame.add(outer)
        widgets["frame"] = frame
        widgets["idx"] = idx

        self._user_form_widgets.append(widgets)
        self._cards_box.pack_start(frame, False, False, 0)
        frame.show_all()

        # Apply level visibility to this new card's shell section
        self._apply_shell_visibility(widgets)

        self._validate_all()

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_pw_changed(self, widgets):
        pw = widgets["password"].get_text()
        score = _pw_score(pw)

        bar = widgets["strength_bar"]
        bar.set_fraction(score / 4.0)
        bar.set_text(_PW_LABELS[score] if pw else "")

        # Entry border colour
        ctx = widgets["password"].get_style_context()
        for cls in _PW_CLASSES[1:]:
            ctx.remove_class(cls)
        if pw and score > 0:
            ctx.add_class(_PW_CLASSES[score])

        # Bar background colour
        if pw and score > 0:
            bar.override_background_color(Gtk.StateFlags.NORMAL, _BAR_COLORS[score])
        else:
            bar.override_background_color(Gtk.StateFlags.NORMAL, None)

        self._validate_all()

    def _on_show_toggled(self, btn, widgets):
        visible = btn.get_active()
        widgets["password"].set_visibility(visible)
        widgets["confirm"].set_visibility(visible)

    def _on_add_user_clicked(self, btn):
        self._add_user_card()

    def _on_remove_user(self, btn, frame, idx):
        # Remove the card widget
        self._cards_box.remove(frame)
        frame.destroy()
        # Remove from widgets list
        self._user_form_widgets = [
            w for w in self._user_form_widgets if w["idx"] != idx
        ]
        self._validate_all()

    # ── Shell visibility ──────────────────────────────────────────────────────

    def _apply_shell_visibility(self, widgets):
        level = self.state.experience_level
        if level == "beginner":
            widgets["shell_box"].hide()
        else:
            widgets["shell_box"].show_all()

    # ── Level visibility ──────────────────────────────────────────────────────

    def _apply_level_visibility(self):
        level = self.state.experience_level
        # Shell picker: Intermediate+
        for w in self._user_form_widgets:
            self._apply_shell_visibility(w)
        # Add user button: Advanced only
        if level == "advanced":
            self._add_btn_row.show_all()
        else:
            self._add_btn_row.hide()
        return False

    def on_experience_changed(self):
        self._apply_level_visibility()
        self.refresh_hints()

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_all(self):
        all_ok = True

        for widgets in self._user_form_widgets:
            uname = widgets["username"].get_text().strip()
            pw    = widgets["password"].get_text()
            conf  = widgets["confirm"].get_text()

            # Username
            if not uname:
                widgets["uname_status"].set_text("")
                widgets["uname_error"].set_text("Username cannot be empty.")
                all_ok = False
            elif not _USERNAME_RE.match(uname):
                widgets["uname_status"].set_text("✗")
                widgets["uname_status"].get_style_context().remove_class("status-ok")
                widgets["uname_status"].get_style_context().add_class("status-error")
                widgets["uname_error"].set_text(
                    "Lowercase letters, numbers, hyphens and underscores only. "
                    "Must start with a letter or underscore."
                )
                all_ok = False
            else:
                widgets["uname_status"].set_text("✓")
                widgets["uname_status"].get_style_context().remove_class("status-error")
                widgets["uname_status"].get_style_context().add_class("status-ok")
                widgets["uname_error"].set_text("")

            # Password
            if not pw:
                widgets["match_lbl"].set_text("")
                widgets["pw_error"].set_text("Password cannot be empty.")
                all_ok = False
            elif len(pw) < 6:
                widgets["pw_error"].set_text("Password must be at least 6 characters.")
                all_ok = False
            elif pw != conf:
                widgets["match_lbl"].set_text("✗  No match")
                widgets["match_lbl"].get_style_context().remove_class("status-ok")
                widgets["match_lbl"].get_style_context().add_class("status-error")
                widgets["pw_error"].set_text("")
                all_ok = False
            else:
                widgets["match_lbl"].set_text("✓  Match")
                widgets["match_lbl"].get_style_context().remove_class("status-error")
                widgets["match_lbl"].get_style_context().add_class("status-ok")
                widgets["pw_error"].set_text("")

        if hasattr(self, 'next_btn'):
            self.set_next_enabled(all_ok and len(self._user_form_widgets) > 0)

    def validate(self):
        if not self._user_form_widgets:
            return False, "Add at least one user account."
        for widgets in self._user_form_widgets:
            uname = widgets["username"].get_text().strip()
            pw    = widgets["password"].get_text()
            if not uname or not _USERNAME_RE.match(uname):
                return False, f"Invalid username: '{uname}'"
            if not pw or len(pw) < 6:
                return False, "Password must be at least 6 characters."
            if pw != widgets["confirm"].get_text():
                return False, f"Passwords do not match for user '{uname}'."
        return True, ""

    def on_next(self):
        self.state.users = []
        for widgets in self._user_form_widgets:
            uname = widgets["username"].get_text().strip()
            pw    = widgets["password"].get_text()
            sudo  = widgets["sudo"].get_active()

            # Get selected shell from radio group
            shell = "/bin/bash"
            for btn, (path, _, _) in zip(widgets["shell_group"], SHELLS):
                if btn.get_active():
                    shell = path
                    break

            # Collect extra groups
            extra_groups = [
                name for name, chk in widgets["group_checks"].items()
                if chk.get_active()
            ]

            self.state.add_user(uname, pw, sudo=sudo, shell=shell,
                                groups=extra_groups)

            # Add shell package to extras if not bash
            if shell == "/bin/zsh" and "zsh" not in self.state.extra_packages:
                self.state.extra_packages.append("zsh")
            elif shell == "/bin/fish" and "fish" not in self.state.extra_packages:
                self.state.extra_packages.append("fish")
