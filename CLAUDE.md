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
- Every screen has one or more wiki links that open an in-app wiki viewer
- GTK3 + Python (same stack as the systemd-manager project)
- Dark GitHub-style theme (matching systemd-manager aesthetic)
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
| 7 | Mirror Selection             | 🔲 Not started  | reflector integration                                        |
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
├── CLAUDE.md                   ← YOU ARE HERE — paste to resume sessions
├── README.md
├── PKGBUILD
├── LICENSE                     ← GPLv3
├── arch-installer.desktop
├── docs/
│   └── design-notes.md
├── installer/
│   ├── __init__.py
│   ├── main.py                 ← Entry point, stage controller, window manager ✅
│   ├── state.py                ← Global install state object ✅
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── base_screen.py      ← Base class all screens inherit from ✅
│   │   ├── welcome.py          ← Stage 0  ✅
│   │   ├── network.py          ← Stage 1  ✅
│   │   ├── keyboard.py         ← Stage 2  ✅
│   │   ├── locale_screen.py    ← Stage 3  ✅
│   │   ├── disk_select.py      ← Stage 4  ✅
│   │   ├── partition.py        ← Stage 5  ✅
│   │   ├── filesystem.py       ← Stage 6  ✅
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
│   │   ├── disk.py             ← lsblk wrapper, boot mode, RAM detection ✅
│   │   ├── filesystem.py       ← mkfs.*, mount/umount helpers (planned)
│   │   ├── pacstrap.py         ← pacstrap runner with progress parsing (planned)
│   │   ├── chroot.py           ← arch-chroot command runner (planned)
│   │   ├── bootloader.py       ← GRUB/systemd-boot/rEFInd/EFIStub/UKI (planned)
│   │   └── config.py           ← fstab, locale.gen, mkinitcpio, etc. (planned)
│   ├── wiki/
│   │   ├── __init__.py
│   │   └── viewer.py           ← Gtk.Window + WebKit2.WebView wiki viewer ✅
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
- `network_ok`                    — bool
- `network_skipped`               — bool

### Key Design Rules
1. **Nothing is written to disk until the user confirms on the Review screen.**
2. Every backend function returns `(success: bool, message: str)`.
3. All long operations run in background threads; GTK updates via `GLib.idle_add`.
4. Logging goes to `/tmp/arch-installer.log` during install.
5. The info panel on every screen pulls from `get_hints()` keyed by `experience_level`.
6. Every screen defines a `WIKI_LINKS` class variable: list of `(label, url)` tuples.
   BaseScreen renders these automatically in the info panel.
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
- `.nav-bar`, `.nav-btn`, `.nav-btn-next`, `.nav-btn-back` — navigation
- `.card` — generic bordered card
- `.disk-card`, `.disk-card-selected` — disk selection cards (Stage 4)
- `.action-button` — Scan / Connect / Refresh / Apply buttons
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
- `connected` is read from `state.network_ok`

---

## Feature Design: Bootloader Options (Stage 13)

Five bootloader options, visibility gated by experience level:

| Bootloader     | Beginner | Intermediate | Advanced | Notes                                      |
|----------------|----------|--------------|----------|--------------------------------------------|
| GRUB           | ✅        | ✅            | ✅        | Default. BIOS + UEFI. Most compatible.     |
| systemd-boot   | ✅        | ✅            | ✅        | Simple. UEFI only. Clean installs.         |
| rEFInd         | ❌        | ✅            | ✅        | Graphical. UEFI only. Auto-detects kernels.|
| EFIStub        | ❌        | ❌            | ✅        | Kernel boots directly via UEFI. No loader. |
| UKI            | ❌        | ❌            | ✅        | Unified Kernel Image. Secure Boot friendly.|

UKI note: if selected at Stage 13, `state.bootloader_uki = True` influences
mkinitcpio config generation. If LUKS is also enabled,
`state.bootloader_uki_needs_decrypt = True` ensures the decrypt hook is included.

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
- Next button only enabled when connected = True

### Stage 2 — keyboard.py + backend/keyboard.py
- `list_keymaps()` calls `localectl list-keymaps`; falls back to built-in list
- `apply_keymap()` calls `loadkeys` for live preview
- When running in a graphical session (not TTY), loadkeys fails gracefully
- `get_current_keymap()` pre-selects the active keymap on load
- Filter model on TreeView for instant search across ~300 keymaps

### Stage 3 — locale_screen.py + backend/locale.py
- `list_locales()` parses `/etc/locale.gen` (all lines, commented or not)
- UTF-8 only toggle: hidden/forced on for Beginner; shown for Intermediate/Advanced
- Saves `state.locale` and `state.language` on Next

### Stage 4 — disk_select.py + backend/disk.py
- `detect_boot_mode()` checks `/sys/firmware/efi` → 'uefi' or 'bios'
- `list_disks()` calls `lsblk --json` and parses output
- Each disk rendered as a clickable EventBox card
- `.disk-card-selected` CSS class applied on click (blue border + dark bg)
- Red warning shown if selected disk has existing partitions
- Sets `state.partition_table` default: 'gpt' for UEFI, 'mbr' for BIOS

### Stage 5 — partition.py + backend/disk.py additions
- Auto mode: EFI (UEFI only, 512MB vfat) + optional swap + root (rest)
- Manual mode: editable TreeView with Add/Edit/Delete; dialog for each partition
- Intermediate/Advanced only for Manual; Beginners see it greyed out with note
- `get_disk_size_mb()` and `get_ram_mb()` added to backend/disk.py
- `suggest_swap_mb()` calculates sensible swap size from RAM
- Validates: root partition required; UEFI requires vfat EFI partition
- Saves list of `DiskPartition` objects to `state.partitions`

### Stage 6 — filesystem.py
- Root filesystem choice: ext4 (all), btrfs/xfs (Intermediate+), f2fs (Advanced)
- Btrfs subvolume section shown only when btrfs selected and level > Beginner
- Standard subvolume layout: @, @home, @snapshots, @log, @cache
- LUKS encryption: master toggle → passphrase + confirm entries
- Passphrase entry border/bg changes colour live: red=Weak, amber=Fair, green=Good, blue=Strong
- Confirm entry matches strength colour when passphrases match, red when mismatch
- Eye button (ToggleButton) shows/hides passphrase text
- Sets `state.bootloader_uki_needs_decrypt = True` when encryption enabled
- Updates `p.encrypt = True` on root (and /home if present) partitions in state
- Updates `p.filesystem` on the root partition to the chosen filesystem

---

## Known Issues / Deferred Decisions

- [ ] LVM support (intermediate/advanced only — defer)
- [ ] Dual-boot / existing partition preservation (defer until partition screen V2)
- [ ] Whether to bundle a default mirrorlist or always fetch live (decide at Stage 7)
- [ ] UKI: mkinitcpio vs dracut decision (defer until Stage 13)
- [ ] Secure Boot key enrollment UI (advanced only — defer until Stage 13)
- [ ] HDD icon 🖴 may not render on all systems (monitor for reports)

---

## Session Commit Log

| Session | Commit message                                                    |
|---------|-------------------------------------------------------------------|
| 1       | chore: initial project scaffold and architecture                  |
| 2       | feat(stage-0): welcome screen and experience level                |
| 2       | chore: restructure into installer/ package layout                 |
| 2       | docs: wiki viewer, EFIStub/UKI, network-early decisions           |
| 3       | feat(stage-1): network setup, wiki viewer, bug fixes              |
| 4       | feat(stage-2): keyboard layout screen and backend                 |
| 4       | feat(stage-3): locale selection screen and backend                |
| 4       | feat(stage-4): disk selection screen and backend                  |
| 4       | docs: update CLAUDE.md and README.md                              |
| 5       | feat(stage-5): partition scheme (auto + manual)                   |
| 5       | feat(stage-6): filesystem + LUKS encryption                       |
| 5       | fix(style): disk card selection highlight, passphrase colours     |
| 5       | docs: update CLAUDE.md and README.md                              |

---

## Next Session: Stage 7 — Mirror Selection

- File: `installer/ui/mirrors.py`
- Backend: `installer/backend/mirrors.py`
- Uses `reflector` to fetch and rank mirrors by country/speed
- Country selection (multi-select list, pre-selects based on locale)
- Shows ranked mirror list with protocol, country, speed
- Beginner: auto-select top 5 mirrors for detected country, no further config
- Intermediate: choose countries, number of mirrors
- Advanced: full reflector flags (protocol, age, sort method etc.)
- Falls back to bundled mirrorlist if network unavailable
- Saves to `state.mirrorlist` (the actual mirrorlist content) and `state.mirror_countries`
- Upload current `main.py`, `state.py`, `base_screen.py` at start of next session
