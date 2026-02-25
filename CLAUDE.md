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
| 2 | Keyboard Layout              | ✅ Complete     | keyboard.py (UI+backend)                                |
| 3 | Language / Locale            | ✅ Complete     | locale_screen.py (UI+backend)                           |
| 4 | Disk Selection               | ✅ Complete     | disk_select.py (UI), disk.py (backend, partial)         |
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
│   │   ├── keyboard.py         ← Stage 2  ✅
│   │   ├── locale_screen.py    ← Stage 3  ✅
│   │   ├── disk_select.py      ← Stage 4  ✅
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
│   │   ├── keyboard.py         ← localectl / loadkeys wrappers ✅
│   │   ├── locale.py           ← locale.gen parser ✅
│   │   ├── disk.py             ← lsblk wrapper, boot mode detection ✅ (partial — partitioning logic to be added)
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
   a labeled "📖 Arch Wiki" frame in the info panel. Clicking opens the wiki viewer window.
7. The wiki viewer is non-modal — users can keep it open while using the installer.
8. The wiki viewer gracefully handles no network connection (shows friendly message + raw URL).

---

## How to Run

```bash
cd ~/arch-installer
python3 -m installer.main
```

---

## BaseScreen Interface (installer/ui/base_screen.py)

All stage screens extend `BaseScreen`. Key points for new screens:

### Class variables (set at class level, not in __init__)
```python
class MyScreen(BaseScreen):
    title    = "Screen Title"
    subtitle = "Optional subtitle shown below the title"
    WIKI_LINKS = [
        ("Link Label", "https://wiki.archlinux.org/title/..."),
    ]
```

### Methods to implement
```python
def get_hints(self) -> dict:
    # Return hints keyed by 'beginner', 'intermediate', 'advanced'
    return {"beginner": "...", "intermediate": "...", "advanced": "..."}

def build_content(self) -> Gtk.Widget:
    # Build and return the left-side content widget
    # Called automatically by BaseScreen.__init__
    ...
    return root_widget

def validate(self) -> tuple:
    # Return (True, '') to allow Next, or (False, 'message') to block
    return True, ""

def on_next(self):
    # Save selections to self.state before navigating away
    self.state.some_field = self._selected_value
```

### Optional override
```python
def on_experience_changed(self):
    # Called when user changes experience level dropdown
    # Use to show/hide advanced options
    pass
```

### Useful BaseScreen methods
```python
self.set_next_enabled(bool)   # enable/disable the Next button
self.set_next_label(str)      # change Next button text
self.set_back_enabled(bool)   # enable/disable Back button
self.error_label.set_text(str) # show an error message in the nav bar
```

### __init__ signature
```python
def __init__(self, state, on_next, on_back):
    # Set instance variables BEFORE calling super().__init__
    # because super().__init__ calls build_content() immediately
    self._my_var = some_default
    super().__init__(state=state, on_next=on_next, on_back=on_back)
```

---

## Feature Design: Arch Wiki Viewer

### Overview
Every installer screen has a `WIKI_LINKS` class variable — a list of `(label, url)` tuples.
`BaseScreen` automatically renders these as buttons inside a "📖 Arch Wiki" frame in the
info panel. Clicking opens a non-modal `WikiViewer` window.

### Implementation
- File: `installer/wiki/viewer.py`
- Public API: `open_wiki(url, connected)` — opens a new viewer window
- `BaseScreen._open_wiki(url)` calls this, passing `state.network_ok` for the connected flag
- Tries WebKit2 4.1, falls back to 4.0
- If no network or no WebKit: shows friendly fallback page with selectable raw URL
- Non-modal: multiple wiki windows can be open simultaneously

---

## Stage Controller (installer/main.py)

### Adding a new stage
1. Import the screen class at the top of main.py
2. Add to STAGE_CLASSES list:
```python
STAGE_CLASSES = [
    ("Welcome",       lambda: WelcomeScreen),
    ("Network Setup", lambda: NetworkScreen),
    ("Keyboard",      lambda: KeyboardScreen),
    ("Locale",        lambda: LocaleScreen),
    ("Disk",          lambda: DiskSelectScreen),
    ("Partition",     lambda: PartitionScreen),   # ← add like this
]
```

### Navigation behaviour
- `_advance()` moves forward, rebuilding the next screen fresh
- `_go_back()` slides back, destroys the current screen (so it rebuilds fresh if revisited)
- All screens receive `on_next=self._advance` and `on_back=self._go_back` (or `None` for Stage 0)

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

## Implementation Notes by Stage

### Stage 0 — welcome.py
- `WelcomeScreen` extends `Gtk.Box` directly (predates BaseScreen)
- Three `Gtk.EventBox` cards for Beginner / Intermediate / Advanced
- `_next_called` bool guard prevents double-fire of Continue button

### Stage 1 — network.py + backend/network.py
- Status card shows live interface info via `get_interface_info()`
- Connectivity check runs in a daemon thread on screen load
- WiFi: Scan → TreeView list → passphrase entry → Connect via iwd
- Skip button sets `state.network_skipped = True` and advances
- Next button only enabled when `_connected = True`

### Stage 2 — keyboard.py + backend/keyboard.py
- `list_keymaps()` calls `localectl list-keymaps`; falls back to built-in list
- `apply_keymap()` calls `loadkeys` for live preview
- When running in a graphical session (not TTY), loadkeys fails gracefully with
  a friendly message — works correctly on the real Arch live ISO TTY
- `get_current_keymap()` pre-selects the active keymap on load
- Filter model on TreeView for instant search across ~300 keymaps

### Stage 3 — locale_screen.py + backend/locale.py
- `list_locales()` parses `/etc/locale.gen` (all lines, commented or not)
- UTF-8 only toggle: hidden and forced on for Beginner; shown for Intermediate/Advanced
- Pre-selects `state.locale` if returning from a later stage
- Saves `state.locale` and `state.language` on Next

### Stage 4 — disk_select.py + backend/disk.py
- `detect_boot_mode()` checks `/sys/firmware/efi` → 'uefi' or 'bios'
- `list_disks()` calls `lsblk --json` and parses output
- Each disk rendered as a clickable card (not a tree row) for clarity
- Shows model, size, type (NVMe/SSD/HDD/USB/Virtual), existing partitions
- Red warning shown if selected disk has existing partitions
- Sets `state.partition_table` default: 'gpt' for UEFI, 'mbr' for BIOS
- Refresh button re-scans drives

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
- `.card` — generic bordered card (status card, disk cards, etc.)
- `.disk-card`, `.disk-card-selected` — disk selection cards (Stage 4)
- `.action-button` — Scan / Connect / Refresh / Apply buttons
- `.wiki-frame`, `.wiki-frame-title`, `.wiki-link-button` — wiki links section
- `.section-heading` — section labels within content
- `.detail-key`, `.detail-value` — key/value info pairs
- `.status-ok`, `.status-error`, `.error-label` — status/error text

---

## Known Issues / Deferred Decisions

- [ ] Btrfs subvolume layout presets (defer until filesystem screen)
- [ ] LVM support (intermediate/advanced only — defer)
- [ ] Dual-boot / existing partition detection (defer until partition screen)
- [ ] Whether to bundle a default mirrorlist or always fetch live (decide at mirror screen)
- [ ] UKI: mkinitcpio vs dracut decision (defer until filesystem/bootloader screens)
- [ ] Secure Boot key enrollment UI (advanced only — defer until bootloader screen)
- [ ] webkit2gtk must be installed for wiki viewer (add to README prerequisites)
- [ ] disk-card-selected CSS class needs adding to style.css (highlighted disk card)

---

## Session Commit Log

| Session | Commit message                                          |
|---------|---------------------------------------------------------|
| 1       | chore: initial project scaffold and architecture        |
| 2       | feat(stage-0): welcome screen and experience level      |
| 2       | chore: restructure into installer/ package layout       |
| 2       | docs: wiki viewer, EFIStub/UKI, network-early decisions |
| 3       | feat(stage-1): network setup, wiki viewer, bug fixes    |
| 4       | feat(stage-2): keyboard layout screen and backend       |
| 4       | feat(stage-3): locale selection screen and backend      |
| 4       | feat(stage-4): disk selection screen and backend        |
| 4       | docs: update CLAUDE.md and README.md                    |
