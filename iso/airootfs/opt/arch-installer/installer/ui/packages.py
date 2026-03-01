"""
installer/ui/packages.py
-------------------------
Stage 8 — Package Selection

Lets the user choose a desktop environment and optional extra packages.

Experience level behaviour:
  Beginner:     DE/WM picker only. Clean cards, one click, done.
  Intermediate: DE/WM picker + curated extras checklist.
  Advanced:     DE/WM picker + extras checklist + free-form package
                entry to add anything from the Arch repos.

The base package set (base, base-devel, linux, linux-firmware) is
always installed and is not shown here — it's implicit.

Saves to:
    state.desktop_environment  — comma-separated selected DE ids, e.g. 'gnome,i3'
                                  or '' for base only
    state.display_manager      — dm of first full DE selected, or '' if none
    state.extra_packages       — list of additional package name strings
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen


# ── Desktop environment / window manager definitions ──────────────────────────
# Cards are shown in a FlowBox so they wrap automatically.

DE_OPTIONS = [
    {
        "id":       "",
        "label":    "None",
        "sublabel": "Base only",
        "icon":     "🖥",
        "desc":     "A minimal install with no graphical environment. "
                    "You'll boot to a terminal. Good for servers or if "
                    "you plan to install a DE/WM manually later.",
        "packages": [],
        "dm":       "",
    },
    # ── Full desktop environments ──────────────────────────────────────────────
    {
        "id":       "gnome",
        "label":    "GNOME",
        "sublabel": "Modern & clean",
        "icon":     "🔵",
        "desc":     "Polished, modern desktop focused on simplicity. "
                    "Wayland by default. Great for users coming from macOS "
                    "or wanting a clean, touch-friendly experience.",
        "packages": ["gnome", "gnome-extra"],
        "dm":       "gdm",
    },
    {
        "id":       "kde",
        "label":    "KDE Plasma",
        "sublabel": "Powerful & customisable",
        "icon":     "🔷",
        "desc":     "Feature-rich, highly customisable desktop. Supports "
                    "both Wayland and X11. Great for users who want full "
                    "control over every aspect of their environment.",
        "packages": ["plasma", "kde-applications"],
        "dm":       "sddm",
    },
    {
        "id":       "xfce",
        "label":    "XFCE",
        "sublabel": "Lightweight & fast",
        "icon":     "🟤",
        "desc":     "Lightweight desktop that's fast and low on resources. "
                    "Good for older hardware or users who prioritise speed. "
                    "Stable, mature, and uses X11.",
        "packages": ["xfce4", "xfce4-goodies", "lightdm", "lightdm-gtk-greeter"],
        "dm":       "lightdm",
    },
    # ── Wayland tiling WMs ────────────────────────────────────────────────────
    {
        "id":       "sway",
        "label":    "Sway",
        "sublabel": "Tiling / Wayland",
        "icon":     "🟩",
        "desc":     "i3-compatible tiling window manager for Wayland. "
                    "Keyboard-driven, minimal resource use. Drop-in "
                    "replacement for i3 if you want Wayland.",
        "packages": ["sway", "swaybg", "swaylock", "swayidle",
                     "waybar", "wofi", "foot", "mako"],
        "dm":       "",
    },
    {
        "id":       "hyprland",
        "label":    "Hyprland",
        "sublabel": "Flashy tiling / Wayland",
        "icon":     "🌈",
        "desc":     "Dynamic tiling WM for Wayland with smooth animations "
                    "and eye candy. Highly customisable via config file. "
                    "Popular for ricing. Requires a capable GPU.",
        "packages": ["hyprland", "waybar", "wofi", "foot",
                     "mako", "hyprpaper", "xdg-desktop-portal-hyprland"],
        "dm":       "sddm",
    },
    {
        "id":       "niri",
        "label":    "Niri",
        "sublabel": "Scrolling / Wayland",
        "icon":     "🌀",
        "desc":     "A scrollable-tiling Wayland compositor — windows are "
                    "arranged in infinite horizontal strips rather than "
                    "the traditional tiling grid. Novel and very slick.",
        "packages": ["niri", "waybar", "fuzzel", "foot", "mako"],
        "dm":       "",
    },
    # ── X11 tiling WMs ────────────────────────────────────────────────────────
    {
        "id":       "i3",
        "label":    "i3",
        "sublabel": "Tiling / X11",
        "icon":     "🔲",
        "desc":     "The classic keyboard-driven tiling window manager for X11. "
                    "Extremely stable, well-documented, huge community. "
                    "Config file driven. Great starting point for tiling WMs.",
        "packages": ["i3-wm", "i3status", "i3lock", "dmenu",
                     "xterm", "picom", "feh", "dunst"],
        "dm":       "lightdm",
    },
    {
        "id":       "bspwm",
        "label":    "bspwm",
        "sublabel": "Binary tree / X11",
        "icon":     "🌿",
        "desc":     "Tiling WM that represents windows as leaves of a binary "
                    "tree. Controlled entirely via sxhkd hotkey daemon and "
                    "shell scripts. Extremely flexible, steeper learning curve.",
        "packages": ["bspwm", "sxhkd", "dmenu", "xterm",
                     "picom", "feh", "dunst", "polybar"],
        "dm":       "lightdm",
    },
]

# ── Curated extras (Intermediate+) ────────────────────────────────────────────

EXTRA_GROUPS = [
    {
        "heading": "Web & Communication",
        "items": [
            ("firefox",                  "Firefox",          "Web browser"),
            ("chromium",                 "Chromium",         "Open-source Chrome"),
            ("thunderbird",              "Thunderbird",       "Email client"),
            ("discord",                  "Discord",          "Voice & chat (AUR)"),
            ("telegram-desktop",         "Telegram",         "Messaging app"),
        ],
    },
    {
        "heading": "Media",
        "items": [
            ("vlc",                      "VLC",              "Video player"),
            ("mpv",                      "mpv",              "Lightweight video player"),
            ("gimp",                     "GIMP",             "Image editor"),
            ("inkscape",                 "Inkscape",         "Vector graphics editor"),
            ("krita",                    "Krita",            "Digital painting"),
            ("rhythmbox",                "Rhythmbox",        "Music player"),
            ("spotify-launcher",         "Spotify",          "Music streaming client"),
            ("obs-studio",               "OBS Studio",       "Screen recording & streaming"),
            ("kdenlive",                 "Kdenlive",         "Video editor"),
        ],
    },
    {
        "heading": "Office & Productivity",
        "items": [
            ("libreoffice-fresh",        "LibreOffice",      "Full office suite"),
            ("onlyoffice-bin",           "OnlyOffice",       "MS Office-compatible (AUR)"),
            ("obsidian",                 "Obsidian",         "Markdown note-taking (AUR)"),
            ("evince",                   "Evince",           "PDF viewer"),
            ("okular",                   "Okular",           "Multi-format document viewer"),
        ],
    },
    {
        "heading": "Development",
        "items": [
            ("git",                      "Git",              "Version control"),
            ("vim",                      "Vim",              "Terminal text editor"),
            ("neovim",                   "Neovim",           "Modern Vim fork"),
            ("code",                     "VS Code",          "Code editor (AUR)"),
            ("docker docker-compose",    "Docker",           "Container platform"),
            ("python python-pip",        "Python + pip",     "Python runtime and package manager"),
            ("nodejs npm",               "Node.js + npm",    "JavaScript runtime"),
            ("gcc gdb make",             "GCC toolchain",    "C/C++ compiler and debugger"),
            ("rustup",                   "Rust",             "Rust language toolchain"),
        ],
    },
    {
        "heading": "System & Utilities",
        "items": [
            ("cups cups-pdf",            "CUPS",             "Printing support + PDF printer"),
            ("bluez bluez-utils",        "Bluetooth",        "Bluetooth stack and tools"),
            ("pipewire pipewire-pulse wireplumber",
                                         "PipeWire",         "Modern audio server"),
            ("flatpak",                  "Flatpak",          "Sandboxed app support"),
            ("snap",                     "Snap",             "Snap package support (AUR)"),
            ("openssh",                  "OpenSSH",          "SSH client and server"),
            ("ufw",                      "UFW",              "Uncomplicated firewall"),
            ("htop",                     "htop",             "Interactive process viewer"),
            ("neofetch",                 "Neofetch",         "System info display"),
            ("tmux",                     "tmux",             "Terminal multiplexer"),
            ("zsh",                      "Zsh",              "Z shell"),
            ("fish",                     "Fish",             "Friendly interactive shell"),
            ("ranger",                   "Ranger",           "Terminal file manager"),
            ("thunar",                   "Thunar",           "Lightweight graphical file manager"),
            ("timeshift",                "Timeshift",        "System snapshot / backup (AUR)"),
            ("gparted",                  "GParted",          "Graphical partition editor"),
            ("veracrypt",                "VeraCrypt",        "Disk encryption tool (AUR)"),
        ],
    },
    {
        "heading": "Gaming",
        "items": [
            ("steam",                    "Steam",            "Game platform"),
            ("lutris",                   "Lutris",           "Game manager (Wine/Proton)"),
            ("gamemode",                 "GameMode",         "CPU/GPU performance optimiser"),
            ("lib32-mesa lib32-vulkan-icd-loader",
                                         "32-bit GPU libs",  "Required for many games"),
        ],
    },
    {
        "heading": "Fonts & Themes",
        "items": [
            ("noto-fonts noto-fonts-emoji",
                                         "Noto Fonts",       "Wide Unicode + emoji coverage"),
            ("ttf-jetbrains-mono",       "JetBrains Mono",   "Developer monospace font"),
            ("ttf-fira-code",            "Fira Code",        "Ligature monospace font"),
        ],
    },
]


class PackageScreen(BaseScreen):
    """Stage 8 — Package Selection screen."""

    title    = "Package Selection"
    subtitle = "Choose a desktop environment and any extra software"

    WIKI_LINKS = [
        ("Desktop environments", "https://wiki.archlinux.org/title/Desktop_environment"),
        ("Wayland compositors",  "https://wiki.archlinux.org/title/Wayland#Compositors"),
        ("i3",                   "https://wiki.archlinux.org/title/I3"),
        ("Hyprland",             "https://wiki.archlinux.org/title/Hyprland"),
    ]

    def __init__(self, state, on_next, on_back):
        # Restore previous selections when coming Back
        saved = state.desktop_environment or ''
        self._selected_des = set(x for x in saved.split(',') if x)  # set of de_ids
        self._de_checks    = {}   # de_id → CheckButton (the card checkbox)
        self._extra_pkgs   = list(state.extra_packages)  # mutable copy
        self._de_cards     = {}   # de_id → EventBox card widget
        self._extra_checks = {}   # pkg_str → CheckButton

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        # Next is always enabled — base-only is a valid choice
        self.set_next_enabled(True)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        return {
            "beginner": (
                "📦  Package Selection\n\n"
                "Choose a desktop environment — this determines what your "
                "system looks like when you log in.\n\n"
                "GNOME is recommended for most new users. KDE is great if "
                "you like to customise everything. XFCE is best for older "
                "or lower-spec hardware.\n\n"
                "You can always install more software after the system is "
                "running using pacman."
            ),
            "intermediate": (
                "📦  Package Selection\n\n"
                "Pick your desktop environment, then tick any extras you want "
                "pre-installed. Everything can be added or removed later with "
                "pacman.\n\n"
                "PipeWire is recommended over PulseAudio for modern systems. "
                "CUPS is needed for printer support. Flatpak gives you access "
                "to a large library of sandboxed apps."
            ),
            "advanced": (
                "📦  Package Selection\n\n"
                "All package names are passed directly to pacstrap. You can "
                "enter any valid package name from the Arch repos or AUR "
                "(note: AUR packages require an AUR helper post-install).\n\n"
                "base, base-devel, linux, and linux-firmware are always "
                "included and don't need to be added here.\n\n"
                "NetworkManager is added automatically unless you specify "
                "a different network stack."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # ── DE picker ─────────────────────────────────────────────────────────
        root.pack_start(self._build_de_section(), False, False, 0)

        # ── Curated extras (Intermediate+) ────────────────────────────────────
        self._extras_frame = self._build_extras_section()
        root.pack_start(self._extras_frame, False, False, 0)

        # ── Custom package entry (Advanced) ───────────────────────────────────
        self._custom_frame = self._build_custom_section()
        root.pack_start(self._custom_frame, False, False, 0)

        # Defer visibility until after show_all() runs
        GLib.idle_add(self._apply_level_visibility)

        return root

    # ── DE section ────────────────────────────────────────────────────────────

    def _build_de_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Desktop environment:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # DE cards in a wrapping flow (handles any number of options)
        cards_box = Gtk.FlowBox()
        cards_box.set_min_children_per_line(3)
        cards_box.set_max_children_per_line(5)
        cards_box.set_selection_mode(Gtk.SelectionMode.NONE)
        cards_box.set_homogeneous(True)
        cards_box.set_row_spacing(6)
        cards_box.set_column_spacing(6)

        for de in DE_OPTIONS:
            card = self._make_de_card(de)
            self._de_cards[de["id"]] = card
            cards_box.add(card)

        box.pack_start(cards_box, False, False, 0)

        # Description label that updates when a card is clicked
        self._de_desc = Gtk.Label()
        self._de_desc.get_style_context().add_class("detail-value")
        self._de_desc.set_xalign(0)
        self._de_desc.set_line_wrap(True)
        self._de_desc.set_margin_top(6)
        box.pack_start(self._de_desc, False, False, 0)

        frame.add(box)

        # Apply initial selection highlights
        self._update_de_highlights()

        return frame

    def _make_de_card(self, de: dict) -> Gtk.Widget:
        eb = Gtk.EventBox()
        eb.get_style_context().add_class("level-card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Top row: checkbox left-aligned
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        top_row.set_margin_start(6)
        top_row.set_margin_top(6)

        chk = Gtk.CheckButton()
        chk.set_active(de["id"] in self._selected_des)
        chk.connect("toggled", self._on_de_check_toggled, de["id"])
        # Prevent the checkbox click from also firing the EventBox handler
        chk.connect("button-press-event", lambda w, e: e.get_event_type().value_nick != "button-press")
        top_row.pack_start(chk, False, False, 0)
        self._de_checks[de["id"]] = chk

        outer.pack_start(top_row, False, False, 0)

        # Main content
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_start(10)
        inner.set_margin_end(10)
        inner.set_margin_top(2)
        inner.set_margin_bottom(10)

        icon = Gtk.Label(label=de["icon"])
        icon.set_xalign(0.5)
        inner.pack_start(icon, False, False, 0)

        lbl = Gtk.Label(label=de["label"])
        lbl.get_style_context().add_class("card-title")
        lbl.set_xalign(0.5)
        inner.pack_start(lbl, False, False, 0)

        sub = Gtk.Label(label=de["sublabel"])
        sub.get_style_context().add_class("card-desc")
        sub.set_xalign(0.5)
        sub.set_line_wrap(True)
        inner.pack_start(sub, False, False, 0)

        outer.pack_start(inner, False, False, 0)
        eb.add(outer)
        eb.connect("button-press-event", self._on_de_clicked, de["id"])
        eb.connect("enter-notify-event",
                   lambda w, e: w.get_style_context().add_class("hover"))
        eb.connect("leave-notify-event",
                   lambda w, e: w.get_style_context().remove_class("hover"))

        return eb

    def _on_de_clicked(self, widget, event, de_id):
        # Toggle selection and update the checkbox to match
        if de_id in self._selected_des:
            self._selected_des.discard(de_id)
        else:
            self._selected_des.add(de_id)
        # Sync the checkbox without re-triggering _on_de_check_toggled
        chk = self._de_checks.get(de_id)
        if chk:
            chk.handler_block_by_func(self._on_de_check_toggled)
            chk.set_active(de_id in self._selected_des)
            chk.handler_unblock_by_func(self._on_de_check_toggled)
        self._update_de_highlights()
        # Show description for clicked card
        de = next(d for d in DE_OPTIONS if d["id"] == de_id)
        self._de_desc.set_text(de["desc"])

    def _on_de_check_toggled(self, chk, de_id):
        if chk.get_active():
            self._selected_des.add(de_id)
        else:
            self._selected_des.discard(de_id)
        self._update_de_highlights()
        # Show description for the toggled card
        de = next(d for d in DE_OPTIONS if d["id"] == de_id)
        if hasattr(self, "_de_desc"):
            self._de_desc.set_text(de["desc"])

    def _update_de_highlights(self):
        for did, card in self._de_cards.items():
            ctx = card.get_style_context()
            if did in self._selected_des:
                ctx.add_class("selected")
                ctx.remove_class("hover")
            else:
                ctx.remove_class("selected")

    # ── Extras section ────────────────────────────────────────────────────────

    def _build_extras_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Common extras:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        # Two-column grid of checkboxes
        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(4)

        row = 0
        col = 0
        for group in EXTRA_GROUPS:
            # Group heading spans both columns
            grp_lbl = Gtk.Label(label=group["heading"])
            grp_lbl.get_style_context().add_class("section-heading")
            grp_lbl.set_xalign(0)
            grp_lbl.set_margin_top(6)
            grid.attach(grp_lbl, 0, row, 2, 1)
            row += 1
            col = 0

            for pkg_str, label, desc in group["items"]:
                chk = Gtk.CheckButton()
                chk.set_no_show_all(False)

                # Label + description inline
                chk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                name_lbl = Gtk.Label(label=label)
                name_lbl.get_style_context().add_class("detail-value")
                name_lbl.set_xalign(0)
                desc_lbl = Gtk.Label(label=f"— {desc}")
                desc_lbl.get_style_context().add_class("detail-key")
                desc_lbl.set_xalign(0)
                chk_box.pack_start(name_lbl, False, False, 0)
                chk_box.pack_start(desc_lbl, False, False, 0)
                chk.add(chk_box)

                # Pre-check if any of the packages are already in extra_pkgs
                pkgs = pkg_str.split()
                if any(p in self._extra_pkgs for p in pkgs):
                    chk.set_active(True)

                chk.connect("toggled", self._on_extra_toggled, pkg_str)
                self._extra_checks[pkg_str] = chk

                grid.attach(chk, col, row, 1, 1)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

            if col != 0:
                row += 1
                col = 0

        # Scrollable wrapper so many extras don't push content off screen
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(200)
        scroll.set_max_content_height(260)
        scroll.add(grid)

        box.pack_start(scroll, False, False, 0)
        frame.add(box)
        return frame

    def _on_extra_toggled(self, chk, pkg_str):
        pkgs = pkg_str.split()
        if chk.get_active():
            for p in pkgs:
                if p not in self._extra_pkgs:
                    self._extra_pkgs.append(p)
        else:
            for p in pkgs:
                self._extra_pkgs = [x for x in self._extra_pkgs if x != p]
        self._update_custom_list()

    # ── Custom package entry (Advanced) ───────────────────────────────────────

    def _build_custom_section(self) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        heading = Gtk.Label(label="Additional packages:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)

        hint = Gtk.Label(
            label="Enter any package name from the Arch repos. "
                  "Separate multiple packages with spaces."
        )
        hint.get_style_context().add_class("detail-key")
        hint.set_xalign(0)
        hint.set_line_wrap(True)
        box.pack_start(hint, False, False, 0)

        # Entry row
        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self._custom_entry = Gtk.Entry()
        self._custom_entry.set_placeholder_text("e.g. htop neofetch tmux")
        self._custom_entry.set_hexpand(True)
        self._custom_entry.connect("activate", self._on_add_custom)
        entry_row.pack_start(self._custom_entry, True, True, 0)

        add_btn = Gtk.Button(label="Add")
        add_btn.get_style_context().add_class("action-button")
        add_btn.connect("clicked", self._on_add_custom)
        entry_row.pack_start(add_btn, False, False, 0)

        box.pack_start(entry_row, False, False, 0)

        # Running list of custom packages as removable chips
        self._chips_box = Gtk.FlowBox()
        self._chips_box.set_min_children_per_line(3)
        self._chips_box.set_max_children_per_line(8)
        self._chips_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._chips_box.set_homogeneous(False)
        box.pack_start(self._chips_box, False, False, 0)

        frame.add(box)

        # Populate chips from restored state
        self._rebuild_chips()

        return frame

    def _on_add_custom(self, widget):
        text = self._custom_entry.get_text().strip()
        if not text:
            return
        for pkg in text.split():
            pkg = pkg.strip()
            if pkg and pkg not in self._extra_pkgs:
                self._extra_pkgs.append(pkg)
        self._custom_entry.set_text("")
        self._rebuild_chips()

    def _rebuild_chips(self):
        """Rebuild the package chip list from self._extra_pkgs."""
        # Remove all existing chips
        for child in self._chips_box.get_children():
            self._chips_box.remove(child)

        # Find which packages came from the curated checklist
        curated_pkgs = set()
        for group in EXTRA_GROUPS:
            for pkg_str, _, _ in group["items"]:
                for p in pkg_str.split():
                    curated_pkgs.add(p)

        # Only show chips for manually-added packages (not curated ones)
        custom_pkgs = [p for p in self._extra_pkgs if p not in curated_pkgs]

        for pkg in custom_pkgs:
            chip = self._make_chip(pkg)
            self._chips_box.add(chip)

        self._chips_box.show_all()

    def _make_chip(self, pkg: str) -> Gtk.Widget:
        """Create a small removable tag for a custom package."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.get_style_context().add_class("card")
        box.set_margin_start(2)
        box.set_margin_end(2)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        lbl = Gtk.Label(label=pkg)
        lbl.get_style_context().add_class("detail-value")
        lbl.set_margin_start(6)
        lbl.set_margin_end(2)
        box.pack_start(lbl, False, False, 0)

        rm_btn = Gtk.Button(label="✕")
        rm_btn.get_style_context().add_class("action-button")
        rm_btn.set_relief(Gtk.ReliefStyle.NONE)
        rm_btn.connect("clicked", self._on_remove_chip, pkg)
        box.pack_start(rm_btn, False, False, 0)

        return box

    def _on_remove_chip(self, btn, pkg):
        self._extra_pkgs = [p for p in self._extra_pkgs if p != pkg]
        self._rebuild_chips()

    def _update_custom_list(self):
        """Called when curated checkboxes change — refresh the chip display."""
        self._rebuild_chips()

    # ── Level visibility ──────────────────────────────────────────────────────

    def _apply_level_visibility(self):
        level = self.state.experience_level
        if level == "beginner":
            self._extras_frame.hide()
            self._custom_frame.hide()
        elif level == "intermediate":
            self._extras_frame.show_all()
            self._custom_frame.hide()
        else:  # advanced
            self._extras_frame.show_all()
            self._custom_frame.show_all()
        return False  # GLib one-shot

    def on_experience_changed(self):
        self._apply_level_visibility()
        self.refresh_hints()

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        # Always valid — base-only is fine
        return True, ""

    def on_next(self):
        # Collect packages from all selected DEs in DE_OPTIONS order
        de_pkgs = []
        dm = ""
        selected_ids = []
        for de in DE_OPTIONS:
            if de["id"] in self._selected_des:
                selected_ids.append(de["id"])
                for p in de["packages"]:
                    if p not in de_pkgs:
                        de_pkgs.append(p)
                # Use the display manager of the first full DE that has one
                if not dm and de["dm"]:
                    dm = de["dm"]

        self.state.desktop_environment = ",".join(selected_ids)
        self.state.display_manager     = dm

        # Merge DE packages + user extras, deduplicated, preserving order
        combined = de_pkgs + [p for p in self._extra_pkgs if p not in de_pkgs]
        self.state.extra_packages = combined
