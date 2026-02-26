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
- GTK3 + Python, dark GitHub-style theme
- polkit / pkexec for privilege escalation where needed
- **Dry-run mode on by default** — set `dry_run = False` in state.py for real installs
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
| Encryption       | cryptsetup (LUKS2)            |
| Install engine   | pacstrap                      |
| Chroot ops       | arch-chroot subprocess calls  |
| VCS              | Git → GitLab (private)        |
| License          | GPLv3                         |

---

## Installer Stage Map

| # | Stage                        | Status          | Files                                                        |
|---|------------------------------|-----------------|--------------------------------------------------------------|
| 0 | Welcome / Experience Level   | ✅ Complete      | ui/welcome.py                                                |
| 1 | Network Setup                | ✅ Complete      | ui/network.py, backend/network.py                            |
| 2 | Keyboard Layout              | ✅ Complete      | ui/keyboard.py, backend/keyboard.py                          |
| 3 | Language / Locale            | ✅ Complete      | ui/locale_screen.py, backend/locale.py                       |
| 4 | Disk Selection               | ✅ Complete      | ui/disk_select.py, backend/disk.py                           |
| 5 | Partition Scheme             | ✅ Complete      | ui/partition.py                                              |
| 6 | Filesystem + Encryption      | ✅ Complete      | ui/filesystem.py                                             |
| 7 | Mirror Selection             | ✅ Complete      | ui/mirrors.py, backend/mirrors.py                            |
| 8 | Package Selection            | ✅ Complete      | ui/packages.py                                               |
| 9 | Base Install (pacstrap)      | ✅ Complete      | ui/install.py, backend/pacstrap.py                           |
|10 | Timezone                     | 🔲 Not started  |                                                              |
|11 | System Config / Hostname     | 🔲 Not started  |                                                              |
|12 | User + Root Setup            | 🔲 Not started  |                                                              |
|13 | Bootloader                   | 🔲 Not started  | GRUB / systemd-boot / rEFInd / EFIStub / UKI                 |
|14 | Review & Confirm             | 🔲 Not started  | Full summary before any writes                               |
|15 | Installation Progress        | 🔲 Not started  | (may merge with Stage 9)                                     |
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
├── installer/
│   ├── __init__.py
│   ├── main.py                 ← Entry point, stage controller, dry-run banner ✅
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
│   │   ├── packages.py         ← Stage 8  ✅
│   │   ├── install.py          ← Stage 9  ✅
│   │   ├── timezone.py         ← Stage 10
│   │   ├── system_config.py    ← Stage 11
│   │   ├── users.py            ← Stage 12
│   │   ├── bootloader.py       ← Stage 13
│   │   ├── review.py           ← Stage 14
│   │   └── complete.py         ← Stage 16
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── runner.py           ← safe_run() dry-run wrapper ✅
│   │   ├── network.py          ← connectivity checks, iwd wrapper ✅
│   │   ├── keyboard.py         ← localectl / loadkeys wrappers ✅
│   │   ├── locale.py           ← locale.gen parser ✅
│   │   ├── disk.py             ← lsblk wrapper, boot mode, RAM detection ✅
│   │   ├── mirrors.py          ← reflector wrapper, fallback mirrorlist ✅
│   │   ├── pacstrap.py         ← full install sequence ✅
│   │   ├── chroot.py           ← arch-chroot runner (planned)
│   │   ├── bootloader.py       ← bootloader install logic (planned)
│   │   └── config.py           ← fstab, mkinitcpio, etc. (planned)
│   ├── wiki/
│   │   └── viewer.py           ← WebKit2GTK wiki viewer ✅
│   └── assets/
│       ├── installer.svg
│       ├── installer.png
│       └── style.css           ← Shared GTK CSS ✅
└── tests/
```

### State Object (installer/state.py)
All user selections flow through a single `InstallState` dataclass.

Key fields populated so far:
- `experience_level`              — 'beginner' | 'intermediate' | 'advanced'
- `keyboard_layout`               — e.g. 'us', 'de'
- `locale`                        — e.g. 'en_US.UTF-8'
- `target_disk`                   — e.g. '/dev/sda'
- `boot_mode`                     — 'uefi' | 'bios'
- `partition_table`               — 'gpt' | 'mbr'
- `partition_scheme`              — 'auto' | 'manual'
- `partitions`                    — list of DiskPartition objects
- `root_filesystem`               — 'ext4' | 'btrfs' | 'xfs' | 'f2fs'
- `btrfs_subvolumes`              — True if standard @ subvolume layout wanted
- `luks_passphrase`               — empty string = no encryption
- `mirror_countries`              — list of reflector country name strings
- `mirrorlist`                    — final mirrorlist file content string
- `desktop_environment`           — 'gnome'|'kde'|'xfce'|'sway'|'hyprland'|'niri'|'i3'|'bspwm'|''
- `display_manager`               — 'gdm'|'sddm'|'lightdm'|''
- `base_packages`                 — always ['base','base-devel','linux','linux-firmware']
- `extra_packages`                — user-selected extras + DE packages
- `install_log`                   — running list of log lines
- `install_complete`              — True once Stage 9 finishes
- `dry_run`                       — **True by default** — flip to False for real installs

### Key Design Rules
1. **Nothing is written to disk until the user confirms on the Review screen.**
2. **`dry_run = True` by default** — all disk ops are simulated via runner.py.
3. Every backend function that touches disk uses `runner.run_cmd()`.
4. Every backend function returns `(success: bool, message: str)`.
5. All long operations run in background threads; GTK updates via `GLib.idle_add`.
6. Logging goes to `/tmp/arch-installer.log` during install.
7. The info panel on every screen pulls from `get_hints()` keyed by `experience_level`.
8. Every screen defines a `WIKI_LINKS` class variable rendered automatically by BaseScreen.
9. The wiki viewer is non-modal — users can keep it open while using the installer.
10. **Always provide complete files** — owner is learning to code, no diffs/snippets.

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

**IMPORTANT — GTK show_all() visibility pattern:**
GTK's `show_all()` is called after `build_content()` returns and will override
any `.hide()` calls made during construction. To hide widgets conditionally:
- Queue visibility calls via `GLib.idle_add(self._apply_level_visibility)` at
  the END of `build_content()` — this runs after `show_all()` completes.
- Do NOT use `set_no_show_all(True)` on containers whose children need to be
  shown later — it blocks GTK from descending into them during `show_all()`,
  so children are never realized and `.show_all()` on the container won't work.
- `set_no_show_all(True)` is fine for widgets that are NEVER shown by default
  and are only shown programmatically later (e.g. spinners, error panels).
- `_apply_level_visibility()` must `return False` when called via `GLib.idle_add`.

Useful methods provided by BaseScreen:
```python
self.set_next_enabled(bool)    # enable/disable the Next button
self.set_next_label(str)       # change Next button text
self.set_back_enabled(bool)    # enable/disable Back button
self.refresh_hints()           # re-read get_hints() and update panel
```

---

## runner.py — Dry-Run Safe Subprocess Wrapper

**File:** `installer/backend/runner.py`

All disk-touching commands MUST go through this module. Never call `subprocess`
directly from backend code.

```python
from installer.backend.runner import run_cmd, run_chroot, run_script

# Run any shell command
ok, output = run_cmd(["mkfs.ext4", "/dev/sda2"], state, "Format root partition")

# Run inside arch-chroot /mnt
ok, output = run_chroot(["locale-gen"], state, description="Generate locales")

# Run a bash one-liner
ok, output = run_script("echo 'archlinux' > /mnt/etc/hostname", state, "Set hostname")
```

In dry_run mode: logs `[DRY RUN] <description> — $ <command>`, returns `(True, "[dry run] ...")`.
In live mode: runs for real, captures stdout+stderr, returns `(success, output)`.

---

## pacstrap.py — Install Sequence (Stage 9)

**File:** `installer/backend/pacstrap.py`

Seven steps executed in order by `InstallScreen`:

| Step ID      | What it does                                              |
|--------------|-----------------------------------------------------------|
| partition    | sgdisk (GPT) or parted (MBR) — create partition table     |
| format       | mkfs.vfat / mkfs.ext4 / mkfs.btrfs / mkfs.xfs / mkswap   |
| luks         | cryptsetup luksFormat + open (skipped if no passphrase)   |
| mount        | mount all partitions under /mnt (btrfs subvols if needed) |
| mirrorlist   | write state.mirrorlist to /mnt/etc/pacman.d/mirrorlist    |
| pacstrap     | pacstrap -K /mnt <all packages> (30 min timeout)          |
| fstab        | genfstab -U /mnt >> /mnt/etc/fstab                        |

API: `run_step(step_id, state) → (success, output)`
Also: `build_package_list(state) → list` — used by summary page to show packages.

---

## Feature Design Notes

### Dry-Run Mode
- `state.dry_run = True` by default in state.py
- Amber banner shown at top of window via main.py when dry_run is active
- Install screen begin button reads "🧪 Begin Dry Run"
- All `run_cmd()` calls return success without executing
- Safe to run on any machine including the development machine

### Mirror Selection (Stage 7)
- Country list: checkbox TreeView, United States first and pre-checked
- `set_activate_on_single_click(True)` must NOT be used — double-fires and
  un-checks the pre-selected country. Use `button-press-event` on name column.
- Visibility of advanced options deferred via `GLib.idle_add` (see pattern above)
- reflector runs in background thread, pulse timer ticks elapsed seconds
- Falls back to bundled FALLBACK_MIRRORLIST if reflector fails

### Package Selection (Stage 8)
- 9 DE/WM options in a FlowBox (wraps automatically): None, GNOME, KDE Plasma,
  XFCE, Sway, Hyprland, Niri, i3, bspwm
- Each DE sets state.display_manager automatically (gdm/sddm/lightdm/'')
- Curated extras: 7 groups, ~45 options (Web, Media, Office, Dev, System, Gaming, Fonts)
- Advanced: free-form package entry with removable chip tags
- Extras section is scrollable (200-260px height) to avoid overflow

### Base Install (Stage 9)
- Two-phase screen: summary → live install (Gtk.Stack crossfade)
- Summary shows: steps list, config recap, full package list, dry-run notice
- Install page: per-step icons (○→⏳→✅/❌), progress bar, scrolling monospace log
- Background thread calls run_step() for each of 7 steps
- On error: Retry (resume from failed step) and Abort (back to summary) buttons
- On complete: state.install_complete = True, Next enabled

### Disk Selection (Stage 4)
- Cards use `.disk-card` and `.disk-card-selected` CSS classes
- Both MUST be defined in style.css — they are not aliases of `.card`
- `.disk-card-selected` uses blue border (#58a6ff) matching level-card.selected

### Bootloader Options (Stage 13, planned)
| Bootloader     | Beginner | Intermediate | Advanced |
|----------------|----------|--------------|----------|
| GRUB           | ✅        | ✅            | ✅        |
| systemd-boot   | ✅        | ✅            | ✅        |
| rEFInd         | ❌        | ✅            | ✅        |
| EFIStub        | ❌        | ❌            | ✅        |
| UKI            | ❌        | ❌            | ✅        |

---

## CSS Notes (installer/assets/style.css)

GTK CSS limitations vs web CSS:
- `text-transform: uppercase` — NOT valid
- `line-height` — NOT valid

Key CSS classes:
- `.level-card`, `.level-card.selected`, `.level-card.hover` — experience + DE/WM cards
- `.disk-card`, `.disk-card-selected` — disk selection cards (Stage 4)
- `.card` — generic bordered card
- `.info-panel`, `.info-panel-header`, `.info-panel-text` — right panel
- `.screen-title`, `.screen-subtitle`, `.screen-sep` — BaseScreen title bar
- `.nav-bar`, `.nav-btn`, `.nav-btn-next` — navigation
- `.action-button` — Fetch / Connect / Retry etc buttons
- `.wiki-frame`, `.wiki-link-button` — wiki links section
- `.section-heading` — section labels within content
- `.detail-key`, `.detail-value` — info grid labels
- `.status-ok`, `.status-error`, `.error-label` — status/error text
- `.passphrase-weak/fair/good/strong` — LUKS passphrase strength colours
- `.dry-run-banner`, `.dry-run-text` — amber dry-run warning banner

---

## Known Issues / Deferred Decisions

- [ ] LVM support (defer to later)
- [ ] Dual-boot / existing partition preservation (defer)
- [ ] UKI: mkinitcpio vs dracut decision (defer until Stage 13)
- [ ] Secure Boot key enrollment UI (defer until Stage 13)
- [ ] pkexec privilege escalation not yet wired up (safe in dry-run)

---

## Session Commit Log

| Session | Commit message                                                        |
|---------|-----------------------------------------------------------------------|
| 1       | chore: initial project scaffold and architecture                      |
| 2       | feat(stage-0): welcome screen and experience level                    |
| 2       | chore: restructure into installer/ package layout                     |
| 3       | feat(stage-1): network setup, wiki viewer                             |
| 4       | feat(stages-2-4): keyboard, locale, disk selection                    |
| 4       | docs: update CLAUDE.md and README.md                                  |
| 5       | feat(stages-5-6): partition scheme, filesystem + LUKS encryption      |
| 5       | docs: update CLAUDE.md and README.md                                  |
| 6       | feat(stage-7): mirror selection with reflector integration            |
| 6       | fix(mirrors): checkbox pre-selection, US first, visibility timing     |
| 6       | docs: update CLAUDE.md and README.md                                  |
| 7       | feat(stage-8): package selection — DE/WM picker + curated extras      |
| 7       | feat(stage-9): base system install with dry-run safety mode           |
| 7       | feat(safety): dry-run mode, runner.py, amber banner                   |
| 7       | fix(style): add disk-card CSS classes, dry-run banner styles          |
| 7       | docs: update CLAUDE.md and README.md                                  |

---

## Next Session: Stage 10 — Timezone

- File: `installer/ui/timezone.py`
- Interactive map or scrollable list to pick timezone
- Auto-detect from locale/IP as default suggestion
- Sets `state.timezone` (e.g. 'America/Los_Angeles')
- Backend: `run_chroot(["ln", "-sf", ...], state)` to set /etc/localtime
- Upload `main.py` and `state.py` at start of next session
