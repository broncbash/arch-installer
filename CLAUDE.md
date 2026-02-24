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
- GTK3 + Python (same stack as the systemd-manager project)
- Dark GitHub-style theme (matching systemd-manager aesthetic)
- polkit / pkexec for privilege escalation where needed

---

## Tech Stack

| Component        | Choice                        |
|------------------|-------------------------------|
| Language         | Python 3                      |
| GUI toolkit      | GTK3 (python-gobject)         |
| Privilege        | pkexec (polkit)               |
| Disk ops         | parted, sgdisk, mkfs.* tools  |
| Install engine   | pacstrap                      |
| Chroot ops       | arch-chroot subprocess calls  |
| VCS              | Git → GitLab (private)        |
| License          | GPLv3                         |

---

## Installer Stage Map

Each stage is a separate GTK screen. Completed stages are marked ✅.

| # | Stage                        | Status      | Notes                                 |
|---|------------------------------|-------------|---------------------------------------|
| 0 | Welcome / Experience Level   | 🔲 Not started |                                    |
| 1 | Keyboard Layout              | 🔲 Not started |                                    |
| 2 | Language / Locale            | 🔲 Not started |                                    |
| 3 | Network Check                | 🔲 Not started |                                    |
| 4 | Disk Selection               | 🔲 Not started | Most critical — do early             |
| 5 | Partition Scheme             | 🔲 Not started | MBR/GPT, auto vs manual              |
| 6 | Filesystem + Encryption      | 🔲 Not started | ext4/btrfs/xfs, LUKS optional        |
| 7 | Mirror Selection             | 🔲 Not started | reflector integration                |
| 8 | Package Selection            | 🔲 Not started | base, DE, extras                     |
| 9 | Base Install (pacstrap)      | 🔲 Not started | Live progress bar                    |
|10 | Timezone                     | 🔲 Not started |                                      |
|11 | Locale / Hostname            | 🔲 Not started |                                      |
|12 | User + Root Setup            | 🔲 Not started |                                      |
|13 | Bootloader                   | 🔲 Not started | GRUB / systemd-boot / rEFInd         |
|14 | Review & Confirm             | 🔲 Not started | Full summary before any writes       |
|15 | Installation Progress        | 🔲 Not started | Live log + progress                  |
|16 | Complete / Reboot            | 🔲 Not started |                                      |

---

## Architecture Decisions

### File Structure
```
arch-installer/
├── CLAUDE.md                   ← YOU ARE HERE — paste to resume sessions
├── README.md                   ← GitHub/GitLab public readme
├── PKGBUILD                    ← Arch package build
├── LICENSE                     ← GPLv3
├── installer/
│   ├── main.py                 ← Entry point, stage controller, window manager
│   ├── state.py                ← Global install state object (passed between stages)
│   ├── ui/
│   │   ├── base_screen.py      ← Base class all screens inherit from
│   │   ├── welcome.py          ← Stage 0
│   │   ├── keyboard.py         ← Stage 1
│   │   ├── locale_screen.py    ← Stage 2
│   │   ├── network.py          ← Stage 3
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
│   │   ├── disk.py             ← parted/sgdisk wrappers, partition logic
│   │   ├── filesystem.py       ← mkfs.*, mount/umount helpers
│   │   ├── pacstrap.py         ← pacstrap runner with progress parsing
│   │   ├── chroot.py           ← arch-chroot command runner
│   │   ├── bootloader.py       ← GRUB/systemd-boot/rEFInd install logic
│   │   ├── network.py          ← connectivity checks, mirror fetching
│   │   └── config.py           ← fstab, locale.gen, mkinitcpio, etc.
│   └── assets/
│       ├── installer.svg
│       ├── installer.png
│       └── style.css           ← Shared GTK CSS (extracted from inline)
├── tests/
│   └── test_disk.py            ← Unit tests for disk backend (safe, no writes)
├── docs/
│   └── design-notes.md        ← Longer design decisions and research notes
└── .gitignore
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
5. The info panel on every screen pulls from a dict keyed by `(stage, experience_level)`.

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
- Next session: Start Stage 0 (Welcome screen) and Stage 1 (Keyboard)

**What to tell Claude next session:**
> "We're building an Arch Linux GTK3 installer in Python. Here's the full context: [paste this file].
>  Today I want to work on [STAGE NAME]."

---

## Known Issues / Deferred Decisions

- [ ] Btrfs subvolume layout presets (defer until filesystem screen)
- [ ] LVM support (intermediate/advanced only — defer)
- [ ] Dual-boot / existing partition detection (defer until partition screen)
- [ ] Wireless network setup UI (defer until network screen)
- [ ] Whether to bundle a default mirrorlist or always fetch live (decide at mirror screen)

---

## Commit Log Summary

| Session | Commit message                                      |
|---------|-----------------------------------------------------|
| 1       | chore: initial project scaffold and architecture    |
