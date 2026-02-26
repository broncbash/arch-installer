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
|10 | Timezone                     | ✅ Complete      | ui/timezone.py                                               |
|11 | System Config / Hostname     | ✅ Complete      | ui/system_config.py                                          |
|12 | User + Root Setup            | 🔲 Not started  |                                                              |
|13 | Bootloader                   | 🔲 Not started  | GRUB / systemd-boot / rEFInd / EFIStub / UKI                 |
|14 | Review & Confirm             | 🔲 Not started  | Full summary before any writes                               |
|15 | Complete / Reboot            | 🔲 Not started  |                                                              |

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
│   │   ├── timezone.py         ← Stage 10 ✅
│   │   ├── system_config.py    ← Stage 11 ✅
│   │   ├── users.py            ← Stage 12
│   │   ├── bootloader.py       ← Stage 13
│   │   ├── review.py           ← Stage 14
│   │   └── complete.py         ← Stage 15
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
Key fields populated so far:
- `experience_level`              — 'beginner' | 'intermediate' | 'advanced'
- `keyboard_layout`               — e.g. 'us', 'de'
- `locale`                        — e.g. 'en_US.UTF-8'
- `timezone`                      — e.g. 'America/Los_Angeles'
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
- `hostname`                      — e.g. 'my-arch-pc'
- `root_password`                 — root account password string
- `enable_ntp`                    — bool, default True (systemd-timesyncd)
- `install_log`                   — running list of log lines
- `install_complete`              — True once Stage 9 finishes
- `dry_run`                       — **True by default** — flip to False for real installs

### Key Design Rules
1. **Nothing is written to disk until the user confirms on the Review screen.**
2. **`dry_run = True` by default** — all disk ops are simulated via runner.py.
3. Every backend function that touches disk uses `runner.run_cmd()`.
4. Every backend function returns `(success: bool, message: str)`.
5. All long operations run in background threads; GTK updates via `GLib.idle_add`.
6. The info panel on every screen pulls from `get_hints()` keyed by `experience_level`.
7. Every screen defines a `WIKI_LINKS` class variable rendered automatically by BaseScreen.
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

Subclasses implement:
```python
def build_content(self) -> Gtk.Widget   # return the left-side content widget
def get_hints(self) -> dict             # keys: 'beginner', 'intermediate', 'advanced'
def validate(self) -> (bool, str)       # (True,'') or (False,'error message')
def on_next(self)                       # save selections to self.state
def on_experience_changed(self)         # optional: react to level changes
```

**IMPORTANT:** Set instance variables BEFORE calling `super().__init__()`.

**IMPORTANT — GTK show_all() visibility pattern:**
- Queue visibility calls via `GLib.idle_add(self._apply_level_visibility)` at
  the END of `build_content()` — runs after `show_all()` completes.
- Do NOT add a second `GLib.idle_add` for the same function in `__init__()` —
  it fires before `show_all()` and gets overridden, and can also fire before
  widgets are created if `super().__init__()` hasn't been called yet.
- Do NOT use `set_no_show_all(True)` on containers whose children need showing
  later — blocks GTK from descending into them, children never realize.
- `_apply_level_visibility()` must `return False` for GLib one-shot.

---

## runner.py — Dry-Run Safe Subprocess Wrapper

```python
from installer.backend.runner import run_cmd, run_chroot, run_script

ok, output = run_cmd(["mkfs.ext4", "/dev/sda2"], state, "Format root partition")
ok, output = run_chroot(["locale-gen"], state, description="Generate locales")
ok, output = run_script("echo 'archlinux' > /mnt/etc/hostname", state, "Set hostname")
```

In dry_run mode: logs `[DRY RUN]` and returns `(True, "[dry run] ...")`.

---

## CSS Notes (installer/assets/style.css)

GTK CSS limitations: no `text-transform`, no `line-height`, no descendant
class matching on widget children (e.g. `progressbar.foo progress` doesn't work).

For progress bar colors, use `override_background_color()` in Python directly:
```python
from gi.repository import Gdk
color = Gdk.RGBA(0.247, 0.722, 0.314, 1)  # green
self._bar.override_background_color(Gtk.StateFlags.NORMAL, color)
```

TreeView row selection — use `treeview:selected` (GTK3), NOT `treeview row:selected`
(GTK4 syntax). Low-opacity rgba keeps text readable:
```css
treeview:selected       { background-color: rgba(88, 166, 255, 0.18); }
treeview:selected:focus { background-color: rgba(88, 166, 255, 0.25); }
```

Key CSS classes:
- `.level-card`, `.level-card.selected`, `.level-card.hover` — experience + DE/WM cards
- `.disk-card`, `.disk-card-selected` — disk selection cards (Stage 4)
- `.card` — generic bordered card
- `.info-panel`, `.info-panel-header`, `.info-panel-text` — right panel
- `.screen-title`, `.screen-subtitle`, `.screen-sep` — BaseScreen title bar
- `.nav-bar`, `.nav-btn`, `.nav-btn-next` — navigation
- `.action-button` — Fetch / Connect / Retry etc buttons
- `.wiki-frame`, `.wiki-link-button` — wiki links section
- `.section-heading`, `.detail-key`, `.detail-value` — content labels
- `.status-ok`, `.status-error`, `.error-label` — status/error text
- `.passphrase-weak/fair/good/strong` — entry border colours (LUKS + root pw)
- `.dry-run-banner`, `.dry-run-text` — red dry-run warning banner

---

## Feature Design Notes

### Dry-Run Mode
- `state.dry_run = True` by default
- Red banner at top of window when active
- Install screen begin button reads "🧪 Begin Dry Run"
- All `run_cmd()` calls return success without executing

### Package Selection (Stage 8)
- 9 DE/WM options in FlowBox: None, GNOME, KDE, XFCE, Sway, Hyprland, Niri, i3, bspwm
- Each DE sets state.display_manager automatically
- Curated extras: 7 groups ~45 options; Advanced adds free-form package entry

### Base Install (Stage 9)
- Two-phase: summary page → live install (Gtk.Stack crossfade)
- 7 steps: partition → format → luks → mount → mirrorlist → pacstrap → fstab
- Background thread, per-step icons ○→⏳→✅/❌, retry on error

### Disk Selection (Stage 4)
- `.disk-card` and `.disk-card-selected` MUST be defined in style.css explicitly

### Timezone (Stage 10)
- Loads zones from /usr/share/zoneinfo, falls back to built-in list
- Auto-detects default from state.locale via LOCALE_TO_TZ map
- Live clock preview updates every second via GLib.timeout_add(1000)
- Clock timer cleaned up in destroy() to prevent leaks
- Intermediate+: shows zoneinfo path and UTC offset detail row

### System Config (Stage 11)
- Hostname: RFC 1123 validated live, ✓/✗ inline indicator
- Root password: strength bar with override_background_color() colors
  (red=weak, yellow=fair, green=good, blue=strong), show/hide toggle
- NTP checkbox: shown for Intermediate and Advanced only
- Advanced: live /etc/hostname + /etc/hosts file preview
- state.enable_ntp added to state.py (default True)

### Bootloader Options (Stage 13, planned)
| Bootloader     | Beginner | Intermediate | Advanced |
|----------------|----------|--------------|----------|
| GRUB           | ✅        | ✅            | ✅        |
| systemd-boot   | ✅        | ✅            | ✅        |
| rEFInd         | ❌        | ✅            | ✅        |
| EFIStub        | ❌        | ❌            | ✅        |
| UKI            | ❌        | ❌            | ✅        |

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
| 7       | feat(safety): dry-run mode, runner.py, amber→red banner               |
| 7       | fix(style): disk-card CSS, treeview selection, dry-run banner         |
| 7       | docs: update CLAUDE.md and README.md                                  |
| 8       | feat(stage-10): timezone selection with live clock preview            |
| 8       | feat(stage-11): system config — hostname, root password, NTP          |
| 8       | fix(system-config): password strength bar colors, NTP checkbox        |
| 8       | docs: update CLAUDE.md and README.md                                  |

---

## Next Session: Stage 12 — User Setup

- File: `installer/ui/users.py`
- Beginner: single user — username, password + confirm, sudo toggle
- Intermediate: same + shell picker (bash/zsh/fish)
- Advanced: same + ability to add multiple users, each with own settings
- Saves to `state.users` list of dicts
- Upload `main.py` and `state.py` at start of next session
