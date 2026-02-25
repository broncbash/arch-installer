# CLAUDE.md — Arch Installer Project Context
# Paste this file at the start of every Claude session to restore full context.
# Update this file at the end of every session before committing.

---

## Project Overview

A full-featured, GTK3-based graphical Arch Linux installer built from scratch in Python.
No Calamares. No archinstall. Completely original.

**GitLab repo:** https://gitlab.com/broncbash/arch-installer (private until public release)
**Local repo:**   ~/arch-installer

### Design Philosophy
- Follows Arch Wiki installation standards exactly
- Experience-level system: Beginner / Intermediate / Advanced
  - Beginner: safe defaults, plain-English explanations, fewer choices
  - Intermediate: more options exposed, brief technical context
  - Advanced: full control, all options, technical detail
- Every screen has an info/hint panel that adapts to the selected experience level
- Every screen has one or more "Learn: <wiki url>" links that open an in-app wiki viewer
- GTK3 + Python (same stack as the systemd-manager project)
- Dark GitHub-style theme (matching systemd-manager aesthetic)
- polkit / pkexec for privilege escalation where needed

---

## Tech Stack

| Component        | Choice                        |
|------------------|-------------------------------|
| Language         | Python 3                      |
| GUI toolkit      | GTK3 (python-gobject)         |
| Wiki viewer      | WebKit2GTK (webkit2gtk pkg)   |
| Privilege        | pkexec (polkit)               |
| Disk ops         | parted, sgdisk, mkfs.* tools  |
| Install engine   | pacstrap                      |
| Chroot ops       | arch-chroot subprocess calls  |
| VCS              | Git → GitLab (private)        |
| License          | GPLv3                         |

---

## Installer Stage Map

Each stage is a separate GTK screen. Completed stages are marked ✅.
**Network is Stage 1** (moved early — required for wiki viewer and later for reflector/pacstrap).

| # | Stage                        | Status         | Notes                                                   |
|---|------------------------------|----------------|---------------------------------------------------------|
| 0 | Welcome / Experience Level   | ✅ Complete     | welcome.py, main.py, style.css done                     |
| 1 | Network Setup                | ✅ Complete     | network.py (UI+backend), wiki viewer done               |
| 2 | Keyboard Layout              | 🔲 Not started |                                                         |
| 3 | Language / Locale            | 🔲 Not started |                                                         |
| 4 | Disk Selection               | 🔲 Not started | Most critical — do early                                |
| 5 | Partition Scheme             | 🔲 Not started | MBR/GPT, auto vs manual                                 |
| 6 | Filesystem + Encryption      | 🔲 Not started | ext4/btrfs/xfs, LUKS optional. Note UKI dependency.     |
| 7 | Mirror Selection             | 🔲 Not started | reflector integration                                   |
| 8 | Package Selection            | 🔲 Not started | base, DE, extras                                        |
| 9 | Base Install (pacstrap)      | 🔲 Not started | Live progress bar                                       |
|10 | Timezone                     | 🔲 Not started |                                                         |
|11 | Locale / Hostname            | 🔲 Not started |                                                         |
|12 | User + Root Setup            | 🔲 Not started |                                                         |
|13 | Bootloader                   | 🔲 Not started | GRUB / systemd-boot / rEFInd / EFIStub / UKI            |
|14 | Review & Confirm             | 🔲 Not started | Full summary before any writes                          |
|15 | Installation Progress        | 🔲 Not started | Live log + progress                                     |
|16 | Complete / Reboot            | 🔲 Not started |                                                         |

---

## Architecture Decisions

### File Structure
```
arch-installer/
├── CLAUDE.md                   ← YOU ARE HERE — paste to resume sessions
├── README.md                   ← GitHub/GitLab public readme
├── PKGBUILD                    ← Arch package build (add webkit2gtk dependency)
├── LICENSE                     ← GPLv3
├── arch-installer.desktop
├── docs/
│   └── design-notes.md        ← Longer design decisions and research notes
├── installer/
│   ├── __init__.py
│   ├── main.py                 ← Entry point, stage controller, window manager ✅
│   ├── state.py                ← Global install state object (passed between stages) ✅
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── base_screen.py      ← Base class all screens inherit from ✅
│   │   ├── welcome.py          ← Stage 0  ✅
│   │   ├── network.py          ← Stage 1  ✅
│   │   ├── keyboard.py         ← Stage 2
│   │   ├── locale_screen.py    ← Stage 3
│   │   ├── disk_select.py      ← Stage 4
│   │   ├── partition.py        ← Stage 5
│   │   ├── filesystem.py       ← Stage 6
│   │   ├── mirrors.py          ← Stage 7
│   │   ├── packages.py         ← Stage 8
│   │   ├── timezone.py         ← Stage 10
│   │   ├── system_config.py    ← Stage 11
│   │   ├── users.py            ← Stage 12
│   │   ├── bootloader.py       ← Stage 13
│   │   ├── review.py           ← Stage 14
│   │   ├── progress.py         ← Stage 15
│   │   └── complete.py         ← Stage 16
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── network.py          ← connectivity checks, iwd wrapper ✅
│   │   ├── disk.py             ← parted/sgdisk wrappers, partition logic
│   │   ├── filesystem.py       ← mkfs.*, mount/umount helpers
│   │   ├── pacstrap.py         ← pacstrap runner with progress parsing
│   │   ├── chroot.py           ← arch-chroot command runner
│   │   ├── bootloader.py       ← GRUB/systemd-boot/rEFInd/EFIStub/UKI install logic
│   │   └── config.py           ← fstab, locale.gen, mkinitcpio, etc.
│   ├── wiki/
│   │   ├── __init__.py
│   │   └── viewer.py           ← Gtk.Window + WebKit2.WebView wiki viewer ✅
│   └── assets/
│       ├── installer.svg
│       ├── installer.png
│       └── style.css           ← Shared GTK CSS ✅
└── tests/
    └── test_disk.py            ← Unit tests for disk backend (safe, no writes)
```

### State Object (installer/state.py)
All user selections flow through a single `InstallState` dataclass.
No screen writes to disk until Stage 14 (Review & Confirm) is accepted.
This makes it safe to go back and change options at any point.

### Key Design Rules
1. **Nothing is written to disk until the user confirms on the Review screen.**
2. Every backend function is wrapped to return `(success: bool, message: str)`.
3. All long operations run in background threads; GTK updates via `GLib.idle_add`.
4. Logging goes to `/tmp/arch-installer.log` during install.
5. The info panel on every screen pulls from a dict keyed by `experience_level` string.
6. Every screen defines a `WIKI_LINKS` list of `(label, url)` tuples rendered inside
   a labeled "📖 Arch Wiki" frame. Clicking opens the wiki viewer window.
7. The wiki viewer is non-modal — users can keep it open while using the installer.
8. The wiki viewer gracefully handles no network connection (shows friendly message + raw URL).

---

## How to Run

```bash
cd ~/arch-installer
python3 -m installer.main
```

---

## Feature Design: Arch Wiki Viewer

### Overview
Every installer screen has a `WIKI_LINKS` list of `(label, url)` tuples. These render
inside a bordered "📖 Arch Wiki" frame in the content area. Clicking opens a separate
non-modal `Gtk.Window` containing a `WebKit2.WebView` pointed at that wiki page.

### Implementation
- File: `installer/wiki/viewer.py`
- Class: `WikiViewer(Gtk.Window)`
  - Takes a URL, opens a ~960×720 non-modal window
  - Has a simple toolbar: Back, Forward, Reload, URL bar (read-only), Close
  - Themed to match the dark installer aesthetic
- Called from each screen's `_open_wiki()` method
- Multiple viewer windows can be open simultaneously (one per link clicked)

### Network dependency
- Wiki viewer requires an active network connection to load pages
- If no connection is detected, or WebKit2GTK is not installed, viewer shows:
  *"No network connection yet. Connect in Stage 1 (Network Setup) to browse the wiki."*
  with the raw URL displayed for manual reference

### Dependency
- Requires `webkit2gtk` package (add to PKGBUILD and README prerequisites)
- Python binding via `gi.repository`: `gi.require_version("WebKit2", "4.1")`
  (falls back to 4.0 if 4.1 not available)

### Example WIKI_LINKS usage (per screen)
```python
WIKI_LINKS = [
    ("Installation Guide",  "https://wiki.archlinux.org/title/Installation_guide"),
    ("Partitioning",        "https://wiki.archlinux.org/title/Partitioning"),
]
```

---

## Feature Design: BaseScreen

Every stage screen (Stage 1 onwards) extends `BaseScreen` from `installer/ui/base_screen.py`.

### What BaseScreen provides
- Two-column layout: scrollable content area (left) + fixed info panel (right, 280px)
- Title + subtitle bar at top
- Info panel with "💡 Hints & Info" header, scrollable hint text, experience level combo
- Navigation bar at bottom: ◀ Back | error label | Next ▶
- `_nav_ready` guard (300ms timer) prevents spurious Next clicks on screen load
- Experience level combo in info panel updates hints live and persists to state

### Subclass interface
```python
class MyScreen(BaseScreen):
    title = "My Screen"
    subtitle = "Optional subtitle"

    def build_content(self) -> Gtk.Widget:
        # Return the left-side content widget

    def get_hints(self) -> dict:
        return {
            "beginner":     "...",
            "intermediate": "...",
            "advanced":     "...",
        }

    def validate(self) -> tuple[bool, str]:
        # Return (True, "") or (False, "error message")

    def on_next(self):
        # Write selections to self.state
```

---

## Feature Design: Stage Controller (main.py)

- `Gtk.Stack` with `SLIDE_LEFT` / `SLIDE_RIGHT` transitions (220ms)
- `_load_current_stage()` instantiates the screen and uses `GLib.idle_add` to defer
  the `set_visible_child_name` call so GTK fully realizes the widget first
- `_go_back()` removes and destroys the current screen from the stack before sliding
  back, so it always rebuilds fresh (picks up any state changes like experience level)
- All screens receive `on_next=self._advance` and `on_back=self._go_back` (or `None`
  for Stage 0 which has no Back button)
- Add new stages by importing the class and adding to `STAGE_CLASSES`:
  ```python
  STAGE_CLASSES = [
      ("Welcome",       lambda: WelcomeScreen),
      ("Network Setup", lambda: NetworkScreen),
      ("Keyboard",      lambda: KeyboardScreen),   # ← add like this
  ]
  ```

---

## Feature Design: Bootloader Options (Stage 13)

Five bootloader options, with visibility gated by experience level:

| Bootloader     | Beginner | Intermediate | Advanced | Notes                                      |
|----------------|----------|--------------|----------|--------------------------------------------|
| GRUB           | ✅        | ✅            | ✅        | Default. BIOS + UEFI. Most compatible.     |
| systemd-boot   | ✅        | ✅            | ✅        | Simple. UEFI only. Clean installs.         |
| rEFInd         | ❌        | ✅            | ✅        | Graphical. UEFI only. Auto-detects kernels.|
| EFIStub        | ❌        | ❌            | ✅        | Kernel boots directly via UEFI. No loader. |
| UKI            | ❌        | ❌            | ✅        | Unified Kernel Image. Secure Boot friendly.|

### UKI dependency note
UKI bundles kernel + initramfs + cmdline into a single signed EFI binary.
- mkinitcpio or dracut must be configured to produce a UKI output
- If UKI is selected at Stage 13, Stage 6 must flag this requirement
- State flag: `state.bootloader_uki = True` should influence mkinitcpio config generation

---

## Stage 0 — Implementation Notes (welcome.py)

- `WelcomeScreen` extends `Gtk.Box` directly (predates BaseScreen)
- Three `Gtk.EventBox` cards for Beginner / Intermediate / Advanced
- Card state (hover, selected) driven entirely by CSS classes
- Info panel text lives in `WELCOME_INFO` dict keyed by experience level string
- `_next_called` bool guard prevents double-fire of Continue button
- `self.connect("map", ...)` resets `_next_called` when screen becomes visible again
  (needed for Back → re-select level → Continue to work correctly)
- Right info panel is 300px fixed width with a ScrolledWindow around the text

## Stage 1 — Implementation Notes (network.py + backend/network.py)

### UI (installer/ui/network.py)
- `NetworkScreen` extends `BaseScreen`
- Status card shows live interface info (name, IP, type, SSID) via `get_interface_info()`
- Connectivity check runs in a daemon thread on screen load; updates via `GLib.idle_add`
- WiFi section: Scan button → TreeView list of networks → passphrase entry → Connect
- "📖 Arch Wiki" labeled frame with three wiki link buttons
- Skip button bypasses network requirement (sets `state.network_skipped = True`)
- Next button only enabled when `_connected = True`

### Backend (installer/backend/network.py)
- `check_connectivity()` — DNS resolution → TCP fallback → ping fallback
- `get_interface_info()` — parses `ip addr`/`ip link`, enriches with `iwctl` for WiFi
- `list_wifi_networks()` — `iwctl station <iface> scan` + `get-networks`, returns list of dicts
- `connect_wifi(ssid, passphrase)` — `iwctl --passphrase` flag, polls for IP up to 10s
- `disconnect_wifi()` — clean disconnection

### Wiki viewer (installer/wiki/viewer.py)
- `WikiViewer(Gtk.Window)` — non-modal, ~960×720
- Tries WebKit2 4.1 then falls back to 4.0
- No-network / no-WebKit fallback page with selectable raw URL
- `open_wiki(url, connected)` is the public API used by all screens

---

## CSS Notes (installer/assets/style.css)

GTK CSS has some limitations vs web CSS:
- `text-transform: uppercase` — NOT valid, comment it out
- `line-height` — NOT valid, remove it
- Everything else in the current style.css is valid GTK3 CSS

Key CSS classes defined:
- `.welcome-*` — welcome screen specific
- `.level-card`, `.level-card.selected`, `.level-card.hover` — experience cards
- `.info-panel`, `.info-panel-header`, `.info-panel-text` — right panel
- `.screen-title`, `.screen-subtitle`, `.screen-sep` — BaseScreen title bar
- `.nav-bar`, `.nav-btn`, `.nav-btn-next`, `.nav-btn-back` — navigation
- `.card` — generic bordered card (status card, etc.)
- `.action-button` — Scan / Connect / Refresh buttons
- `.wiki-frame`, `.wiki-frame-title`, `.wiki-link-button` — wiki links section
- `.section-heading` — section labels within content
- `.detail-key`, `.detail-value` — interface info grid
- `.status-ok`, `.status-error`, `.error-label` — status/error text

---

## Current Session Notes

**Session 1 — Project bootstrap**
- Decided on full architecture (see above)
- Created repo skeleton, all placeholder files
- Created CLAUDE.md, README.md, LICENSE, PKGBUILD, .gitignore
- Created installer/main.py (entry point + window scaffold)
- Created installer/state.py (InstallState dataclass)
- Created installer/ui/base_screen.py (base class with info panel)
- Created assets (SVG + PNG icon)

**Session 2 — Stage 0 + architecture refinements**
- Implemented `installer/ui/welcome.py` (WelcomeScreen)
- Implemented `installer/assets/style.css` (dark GitHub theme, full palette)
- Updated `installer/main.py` with Gtk.Stack stage controller and Stage 0 wired in
- Fixed repo file structure (moved files into installer/ package layout)
- Added Arch Wiki viewer feature (webkit2gtk, non-modal, per-screen WIKI_LINKS)
- Added EFIStub + UKI as Advanced-tier bootloader options (Stage 13)
- Moved Network Setup to Stage 1 (required early for wiki viewer)
- Defined WiFi setup via iwd for Stage 1

**Session 3 — Stage 1 (Network Setup) + Wiki Viewer + bug fixes**
- Implemented `installer/ui/network.py` (NetworkScreen extending BaseScreen)
- Implemented `installer/backend/network.py` (connectivity, iwd WiFi wrapper)
- Implemented `installer/wiki/viewer.py` (WikiViewer, non-modal WebKit2 window)
- Created all missing `__init__.py` files for installer, ui, backend, wiki packages
- Fixed `WelcomeScreen` signature to accept `on_back=None` kwarg
- Fixed `main.py` stage controller: `_go_back()`, `GLib.idle_add` for transitions,
  destroy-on-back so screens rebuild fresh with updated state
- Fixed double-fire bug on Continue button (`_next_called` guard + `map` signal reset)
- Fixed `BaseScreen` `_nav_ready` guard (300ms) to prevent spurious Next clicks
- Removed invalid GTK CSS properties (`text-transform`, `line-height`)
- Added wiki links "📖 Arch Wiki" labeled frame with styled buttons
- Made window resizable (default 1024×640, minimum 800×560)
- Reduced welcome screen margins and font sizes for better density on ultrawide

**Next session: Stage 2 — Keyboard Layout**
- File: `installer/ui/keyboard.py`
- Should extend `BaseScreen`
- List available keymaps via `localectl list-keymaps`
- Preview/test keymap
- Store selection in `state.keyboard_layout`

---

## Known Issues / Deferred Decisions

- [ ] Btrfs subvolume layout presets (defer until filesystem screen)
- [ ] LVM support (intermediate/advanced only — defer)
- [ ] Dual-boot / existing partition detection (defer until partition screen)
- [ ] Whether to bundle a default mirrorlist or always fetch live (decide at mirror screen)
- [ ] UKI: mkinitcpio vs dracut decision (defer until filesystem/bootloader screens)
- [ ] Secure Boot key enrollment UI (advanced only — defer until bootloader screen)
- [ ] webkit2gtk must be installed for wiki viewer (add to README prerequisites)

---

## Commit Log Summary

| Session | Commit message                                          |
|---------|---------------------------------------------------------|
| 1       | chore: initial project scaffold and architecture        |
| 2       | feat(stage-0): welcome screen and experience level      |
| 2       | chore: restructure into installer/ package layout       |
| 2       | docs: wiki viewer, EFIStub/UKI, network-early decisions |
| 3       | feat(stage-1): network setup, wiki viewer, bug fixes    |
