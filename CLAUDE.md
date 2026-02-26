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
- Every screen has wiki links that open an in-app wiki viewer
- GTK3 + Python
- Dark GitHub-style theme
- polkit / pkexec for privilege escalation where needed
- **This is a learning project — owner is not a coder. Always provide complete
  files, never diffs or partial snippets. Plain-English explanations alongside code.**

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

| # | Stage                        | Status          | Notes                                                        |
|---|------------------------------|-----------------|--------------------------------------------------------------|
| 0 | Welcome / Experience Level   | ✅ Complete      | welcome.py, main.py, style.css                               |
| 1 | Network Setup                | ✅ Complete      | network.py (UI+backend), wiki viewer                         |
| 2 | Keyboard Layout              | ✅ Complete      | keyboard.py (UI+backend)                                     |
| 3 | Language / Locale            | ✅ Complete      | locale_screen.py, backend/locale.py                          |
| 4 | Disk Selection               | ✅ Complete      | disk_select.py, backend/disk.py (partial)                    |
| 5 | Partition Scheme             | ✅ Complete      | partition.py (auto + manual modes)                           |
| 6 | Filesystem + Encryption      | ✅ Complete      | filesystem.py (ext4/btrfs/xfs/f2fs, LUKS, Btrfs subvols)    |
| 7 | Mirror Selection             | ✅ Complete      | mirrors.py UI + backend/mirrors.py                           |
| 8 | Package Selection            | 🔲 Not started  | base, DE, extras                                             |
| 9 | Base Install (pacstrap)      | 🔲 Not started  | Live progress bar                                            |
|10 | Timezone                     | 🔲 Not started  |                                                              |
|11 | System Config / Hostname     | 🔲 Not started  |                                                              |
|12 | User + Root Setup            | 🔲 Not started  |                                                              |
|13 | Bootloader                   | 🔲 Not started  | GRUB / systemd-boot / rEFInd / EFIStub / UKI                 |
|14 | Review & Confirm             | 🔲 Not started  | Full summary before any writes                               |
|15 | Installation Progress        | 🔲 Not started  | Live log + progress                                          |
|16 | Complete / Reboot            | 🔲 Not started  |                                                              |

---

## Architecture Decisions

### File Structure
```
arch-installer/
├── CLAUDE.md
├── README.md
├── PKGBUILD
├── LICENSE
├── arch-installer.desktop
├── docs/
│   └── design-notes.md
├── installer/
│   ├── __init__.py
│   ├── main.py                 ← Entry point, stage controller ✅
│   ├── state.py                ← Global install state object ✅
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── base_screen.py      ← Base class ✅
│   │   ├── welcome.py          ← Stage 0  ✅
│   │   ├── network.py          ← Stage 1  ✅
│   │   ├── keyboard.py         ← Stage 2  ✅
│   │   ├── locale_screen.py    ← Stage 3  ✅
│   │   ├── disk_select.py      ← Stage 4  ✅
│   │   ├── partition.py        ← Stage 5  ✅
│   │   ├── filesystem.py       ← Stage 6  ✅
│   │   ├── mirrors.py          ← Stage 7  ✅
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
│   │   ├── disk.py             ← lsblk wrapper, boot mode, RAM detection ✅
│   │   ├── mirrors.py          ← reflector wrapper, fallback mirrorlist ✅
│   │   ├── filesystem.py       ← mkfs.*, mount/umount helpers (planned)
│   │   ├── pacstrap.py         ← pacstrap runner (planned)
│   │   ├── chroot.py           ← arch-chroot runner (planned)
│   │   ├── bootloader.py       ← bootloader install logic (planned)
│   │   └── config.py           ← fstab, mkinitcpio, etc. (planned)
│   ├── wiki/
│   │   ├── __init__.py
│   │   └── viewer.py           ← WebKit2GTK wiki viewer ✅
│   └── assets/
│       ├── installer.svg
│       ├── installer.png
│       └── style.css           ← Shared GTK CSS ✅
└── tests/
    └── test_disk.py
```

### State Object (installer/state.py)
All user selections flow through a single `InstallState` dataclass.
No screen writes to disk until Stage 14 (Review & Confirm) is accepted.

Key fields populated so far:
- `experience_level`              — 'beginner' | 'intermediate' | 'advanced'
- `keyboard_layout`               — console keymap e.g. 'us', 'de'
- `locale`                        — e.g. 'en_US.UTF-8'
- `language`                      — same as locale (LANG=)
- `target_disk`                   — e.g. '/dev/sda'
- `boot_mode`                     — 'uefi' | 'bios' (auto-detected Stage 4)
- `partition_table`               — 'gpt' | 'mbr' (defaulted Stage 4)
- `partition_scheme`              — 'auto' | 'manual'
- `partitions`                    — list of DiskPartition objects
- `swap_size_mb`                  — 0 = no swap partition
- `use_swap_file`                 — True if swap file chosen
- `root_filesystem`               — 'ext4' | 'btrfs' | 'xfs' | 'f2fs'
- `btrfs_subvolumes`              — True if standard @ subvolume layout wanted
- `luks_passphrase`               — empty string = no encryption
- `bootloader_uki`                — True if UKI bootloader selected (Stage 13)
- `bootloader_uki_needs_decrypt`  — True if LUKS enabled (affects initramfs)
- `mirror_countries`              — list of reflector country name strings
- `mirrorlist`                    — final mirrorlist file content string
- `network_ok`                    — bool
- `network_skipped`               — bool

### Key Design Rules
1. **Nothing is written to disk until the user confirms on the Review screen.**
2. Every backend function returns `(success: bool, message: str)`.
3. All long operations run in background threads; GTK updates via `GLib.idle_add`.
4. Logging goes to `/tmp/arch-installer.log` during install.
5. The info panel on every screen pulls from `get_hints()` keyed by `experience_level`.
6. Every screen defines a `WIKI_LINKS` class variable rendered automatically by BaseScreen.
7. The wiki viewer is non-modal — users can keep it open while using the installer.
8. **Always provide complete files** — owner is learning to code, no diffs/snippets.

---

## How to Run

```bash
cd ~/arch-installer
python3 -m installer.main
```

---

## BaseScreen Interface (installer/ui/base_screen.py)

All screens extend `BaseScreen(Gtk.Box)`. Constructor signature:
```python
BaseScreen.__init__(self, state, on_back=None, on_next=None)
```

Subclasses set these **class variables**:
```python
title    = "Screen Title"
subtitle = "Optional subtitle"
WIKI_LINKS = [("Label", "https://wiki.archlinux.org/...")]  # optional
```

Subclasses implement these **methods**:
```python
def build_content(self) -> Gtk.Widget:   # return the left-side content widget
def get_hints(self) -> dict:             # keys: 'beginner', 'intermediate', 'advanced'
def validate(self) -> (bool, str):       # (True,'') or (False,'error message')
def on_next(self):                       # save selections to self.state
def on_experience_changed(self):         # optional: react to level changes
```

**IMPORTANT:** Set instance variables BEFORE calling `super().__init__()` because
`super().__init__()` immediately calls `build_content()`.

**IMPORTANT:** GTK's `show_all()` is called after `build_content()` returns and will
override any `.hide()` calls made during construction. To hide widgets on load,
defer visibility calls using `GLib.idle_add(self._apply_visibility)` from inside
`build_content()` — this runs after `show_all()` completes. Widgets that should
never be shown by `show_all()` (e.g. spinners, result panels) use
`widget.set_no_show_all(True)` instead.

Useful methods provided by BaseScreen:
```python
self.set_next_enabled(bool)    # enable/disable the Next button
self.set_next_label(str)       # change Next button text
self.set_back_enabled(bool)    # enable/disable Back button
self.refresh_hints()           # re-read get_hints() and update panel
```

---

## Adding a New Stage

1. Create `installer/ui/<name>.py` extending `BaseScreen`
2. Create `installer/backend/<name>.py` if backend logic is needed
3. In `installer/main.py`:
   - Add import at top
   - Add entry to `STAGE_CLASSES` list
   - Add field to `_show_end_dialog` summary (during development)

---

## CSS Notes (installer/assets/style.css)

GTK CSS limitations vs web CSS:
- `text-transform: uppercase` — NOT valid
- `line-height` — NOT valid

Key CSS classes defined:
- `.welcome-*` — welcome screen specific
- `.level-card`, `.level-card.selected`, `.level-card.hover` — experience cards
- `.info-panel`, `.info-panel-header`, `.info-panel-text` — right panel
- `.screen-title`, `.screen-subtitle`, `.screen-sep` — BaseScreen title bar
- `.nav-bar`, `.nav-btn`, `.nav-btn-next` — navigation
- `.card` — generic bordered card
- `.disk-card`, `.disk-card-selected` — disk selection cards (Stage 4)
- `.action-button` — Scan / Connect / Refresh / Fetch buttons
- `.wiki-frame`, `.wiki-frame-title`, `.wiki-link-button` — wiki links section
- `.section-heading` — section labels within content
- `.detail-key`, `.detail-value` — info grid labels
- `.status-ok`, `.status-error`, `.error-label` — status/error text
- `.passphrase-weak`, `.passphrase-fair`, `.passphrase-good`, `.passphrase-strong`
  — LUKS passphrase entry border/background colours (red→amber→green→blue)

---

## Feature Design: Arch Wiki Viewer

- File: `installer/wiki/viewer.py`
- Public API: `open_wiki(url, connected)` — opens a non-modal `WikiViewer` window
- Tries WebKit2 4.1 then falls back to 4.0
- No-network / no-WebKit fallback page with selectable raw URL
- BaseScreen calls it automatically when wiki link buttons are clicked

---

## Feature Design: Mirror Selection (Stage 7)

- UI: `installer/ui/mirrors.py`
- Backend: `installer/backend/mirrors.py`
- Country list uses `Gtk.ListStore` with `CellRendererToggle` checkboxes
- United States is always first in the list and pre-checked by default
- Locale detection overrides default if country is in LOCALE_TO_COUNTRY dict
- `set_activate_on_single_click(True)` must NOT be used — it double-fires and
  un-checks the pre-selected country. Use `button-press-event` on the name column instead.
- Visibility of options (num mirrors, protocol, sort, age) deferred via
  `GLib.idle_add` so they run after `show_all()` — otherwise show_all overrides hides.
- reflector runs in a background thread; UI updates via `GLib.idle_add`
- Pulse timer ticks every second showing elapsed time while reflector runs
- Falls back to bundled `FALLBACK_MIRRORLIST` if reflector fails or isn't installed
- Saves to `state.mirrorlist` and `state.mirror_countries`

---

## Feature Design: Bootloader Options (Stage 13)

| Bootloader     | Beginner | Intermediate | Advanced | Notes                                      |
|----------------|----------|--------------|----------|--------------------------------------------|
| GRUB           | ✅        | ✅            | ✅        | Default. BIOS + UEFI. Most compatible.     |
| systemd-boot   | ✅        | ✅            | ✅        | Simple. UEFI only. Clean installs.         |
| rEFInd         | ❌        | ✅            | ✅        | Graphical. UEFI only. Auto-detects kernels.|
| EFIStub        | ❌        | ❌            | ✅        | Kernel boots directly via UEFI. No loader. |
| UKI            | ❌        | ❌            | ✅        | Unified Kernel Image. Secure Boot friendly.|

UKI note: if selected, `state.bootloader_uki = True` influences mkinitcpio config.
If LUKS also enabled, `state.bootloader_uki_needs_decrypt = True`.

---

## Implementation Notes by Stage

### Stage 0 — welcome.py
- `WelcomeScreen` extends `Gtk.Box` directly (predates BaseScreen)
- Three `Gtk.EventBox` cards for Beginner / Intermediate / Advanced
- `_next_called` bool guard prevents double-fire of Continue button

### Stage 1 — network.py + backend/network.py
- Connectivity check runs in a daemon thread on screen load
- WiFi: Scan → TreeView list → passphrase entry → Connect via iwd
- Skip button sets `state.network_skipped = True` and advances
- Next only enabled when connected = True

### Stage 2 — keyboard.py + backend/keyboard.py
- `list_keymaps()` calls `localectl list-keymaps`; falls back to built-in list
- `apply_keymap()` calls `loadkeys` for live preview (graceful fail in GUI session)
- Filter model on TreeView for instant search across ~300 keymaps

### Stage 3 — locale_screen.py + backend/locale.py
- `list_locales()` parses `/etc/locale.gen`
- UTF-8 only toggle: hidden/forced on for Beginner; shown for Intermediate/Advanced
- Saves `state.locale` and `state.language`

### Stage 4 — disk_select.py + backend/disk.py
- `detect_boot_mode()` checks `/sys/firmware/efi`
- `list_disks()` calls `lsblk --json`
- Each disk is a clickable EventBox card with `.disk-card-selected` CSS on click
- Sets `state.partition_table` default: 'gpt' for UEFI, 'mbr' for BIOS

### Stage 5 — partition.py + backend/disk.py additions
- Auto mode: EFI (UEFI, 512MB vfat) + optional swap + root (rest)
- Manual mode: editable TreeView; Beginner sees it greyed out
- `get_disk_size_mb()`, `get_ram_mb()`, `suggest_swap_mb()` added to backend/disk.py
- Saves list of `DiskPartition` objects to `state.partitions`

### Stage 6 — filesystem.py
- Root filesystem: ext4 (all), btrfs/xfs (Intermediate+), f2fs (Advanced)
- Btrfs subvolume section shown when btrfs selected and level > Beginner
- LUKS: master toggle → passphrase + confirm; live strength colouring on entry widget
- Sets `state.bootloader_uki_needs_decrypt = True` when encryption enabled
- Updates `p.encrypt` and `p.filesystem` on root partition in state.partitions

### Stage 7 — mirrors.py + backend/mirrors.py
- Country list: checkbox TreeView, United States first and pre-checked
- Beginner: country + Fetch button only
- Intermediate: adds number of mirrors dropdown
- Advanced: adds protocol, sort method, age limit
- Fetch runs reflector in background thread with elapsed-second pulse timer
- Shows exact reflector command that was run (selectable text)
- Falls back to bundled mirrorlist on failure
- Saves `state.mirrorlist` and `state.mirror_countries`

---

## Known Issues / Deferred Decisions

- [ ] LVM support (defer to later)
- [ ] Dual-boot / existing partition preservation (defer)
- [ ] UKI: mkinitcpio vs dracut decision (defer until Stage 13)
- [ ] Secure Boot key enrollment UI (defer until Stage 13)

---

## Session Commit Log

| Session | Commit message                                                        |
|---------|-----------------------------------------------------------------------|
| 1       | chore: initial project scaffold and architecture                      |
| 2       | feat(stage-0): welcome screen and experience level                    |
| 2       | chore: restructure into installer/ package layout                     |
| 2       | docs: wiki viewer, EFIStub/UKI, network-early decisions               |
| 3       | feat(stage-1): network setup, wiki viewer, bug fixes                  |
| 4       | feat(stage-2): keyboard layout screen and backend                     |
| 4       | feat(stage-3): locale selection screen and backend                    |
| 4       | feat(stage-4): disk selection screen and backend                      |
| 4       | docs: update CLAUDE.md and README.md                                  |
| 5       | feat(stage-5): partition scheme (auto + manual)                       |
| 5       | feat(stage-6): filesystem + LUKS encryption                           |
| 5       | fix(style): disk card selection highlight, passphrase colours         |
| 5       | docs: update CLAUDE.md and README.md                                  |
| 6       | feat(stage-7): mirror selection with reflector integration            |
| 6       | fix(mirrors): checkbox pre-selection, US first, visibility timing     |
| 6       | docs: update CLAUDE.md and README.md                                  |

---

## Next Session: Stage 8 — Package Selection

- File: `installer/ui/packages.py`
- Beginner: just a DE picker (None / GNOME / KDE / XFCE) with sane defaults
- Intermediate: DE picker + common extras (e.g. Firefox, VLC, Git, CUPS)
- Advanced: full package list editor — add/remove anything from repos
- Always installs: base, base-devel, linux, linux-firmware, NetworkManager
- DE selection drives `state.desktop_environment` and `state.display_manager`
- Extra packages saved to `state.extra_packages`
- Upload `main.py` and `state.py` at start of next session
