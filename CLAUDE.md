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
**Network is now Stage 1** (moved early — required for wiki viewer and later for reflector/pacstrap).

| # | Stage                        | Status         | Notes                                                   |
|---|------------------------------|----------------|---------------------------------------------------------|
| 0 | Welcome / Experience Level   | ✅ Complete     | welcome.py, main.py, style.css done                     |
| 1 | Network Setup                | 🔲 Not started | **Moved early.** Ethernet auto + WiFi via iwd. Required for wiki viewer. |
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
│   ├── main.py                 ← Entry point, stage controller, window manager
│   ├── state.py                ← Global install state object (passed between stages)
│   ├── ui/
│   │   ├── base_screen.py      ← Base class all screens inherit from
│   │   ├── welcome.py          ← Stage 0  ✅
│   │   ├── network.py          ← Stage 1  (was Stage 3 — moved early)
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
│   │   ├── disk.py             ← parted/sgdisk wrappers, partition logic
│   │   ├── filesystem.py       ← mkfs.*, mount/umount helpers
│   │   ├── pacstrap.py         ← pacstrap runner with progress parsing
│   │   ├── chroot.py           ← arch-chroot command runner
│   │   ├── bootloader.py       ← GRUB/systemd-boot/rEFInd/EFIStub/UKI install logic
│   │   ├── network.py          ← connectivity checks, iwd wrapper, mirror fetching
│   │   └── config.py           ← fstab, locale.gen, mkinitcpio, etc.
│   ├── wiki/
│   │   └── viewer.py           ← Gtk.Window + WebKit2.WebView wiki viewer
│   └── assets/
│       ├── installer.svg
│       ├── installer.png
│       └── style.css           ← Shared GTK CSS
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
5. The info panel on every screen pulls from a dict keyed by `(stage, experience_level)`.
6. Every screen defines a `WIKI_LINKS` list of `(label, url)` tuples rendered as
   "Learn: <label>" buttons in the info panel. Clicking opens the wiki viewer window.
7. The wiki viewer is non-modal — users can keep it open while using the installer.
8. The wiki viewer gracefully handles no network connection (shows friendly message + raw URL).

---

## Feature Design: Arch Wiki Viewer

### Overview
Every installer screen has a `WIKI_LINKS` list of `(label, url)` tuples. These render
as clickable "Learn: <label>" links in the info panel. Clicking opens a separate
non-modal `Gtk.Window` containing a `WebKit2.WebView` pointed at that wiki page.

### Implementation
- New file: `installer/wiki/viewer.py`
- Class: `WikiViewer(Gtk.Window)`
  - Takes a URL, opens a ~900×700 non-modal window
  - Has a simple toolbar: Back, Forward, Reload, URL bar (read-only), Close
  - Themed to match the dark installer aesthetic
- Called from `base_screen.py` so all screens get it for free
- Multiple viewer windows can be open simultaneously (one per link clicked)

### Network dependency
- Wiki viewer requires an active network connection to load pages
- If no connection is detected, viewer shows:
  *"No network connection yet. Connect in Stage 1 (Network Setup) to browse the wiki."*
  with the raw URL displayed for manual reference
- This is a safety net — normal flow has network established at Stage 1

### Dependency
- Requires `webkit2gtk` package (add to PKGBUILD and README prerequisites)
- Python binding via `gi.repository`: `gi.require_version("WebKit2", "4.1")`

### Example WIKI_LINKS usage (per screen)
```python
WIKI_LINKS = [
    ("Installation Guide",  "https://wiki.archlinux.org/title/Installation_guide"),
    ("Partitioning",        "https://wiki.archlinux.org/title/Partitioning"),
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
This has implications for Stage 6 (Filesystem + Encryption):
- mkinitcpio or dracut must be configured to produce a UKI output
- If UKI is selected at Stage 13, Stage 6 must flag this requirement
- State flag: `state.bootloader_uki = True` should influence mkinitcpio config generation

### Wiki links for Stage 13
```python
WIKI_LINKS = [
    ("GRUB",                 "https://wiki.archlinux.org/title/GRUB"),
    ("systemd-boot",         "https://wiki.archlinux.org/title/Systemd-boot"),
    ("rEFInd",               "https://wiki.archlinux.org/title/REFInd"),
    ("EFIStub",              "https://wiki.archlinux.org/title/EFISTUB"),
    ("Unified Kernel Image", "https://wiki.archlinux.org/title/Unified_kernel_image"),
    ("Secure Boot",          "https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot"),
]
```

---

## Feature Design: Network Setup (Stage 1)

### Why moved early
- Wiki viewer requires network to load pages (available from Stage 0 onward)
- reflector (Stage 7) requires network
- pacstrap (Stage 9) requires network
- Getting network established first removes all downstream dependencies

### What Stage 1 handles
- **Ethernet**: auto-detect, show status. Usually just works with DHCP — no user action needed.
- **WiFi**: scan for networks via `iwd` (ships on Arch ISO), list SSIDs, connect with passphrase
- **Status display**: show current IP, interface, connection quality
- **Skip option**: allow skipping (user may be on ethernet that auto-connected, or want to proceed without wiki)

### Backend: installer/backend/network.py
- `check_connectivity() -> (bool, str)` — ping-based or DNS check
- `list_wifi_networks() -> list[dict]` — via `iwctl station wlan0 scan` + `get-networks`
- `connect_wifi(ssid, passphrase) -> (bool, str)` — via `iwctl station wlan0 connect`
- `get_interface_info() -> dict` — current IP, interface name, signal strength

### Wiki links for Stage 1
```python
WIKI_LINKS = [
    ("Network configuration", "https://wiki.archlinux.org/title/Network_configuration"),
    ("iwd",                   "https://wiki.archlinux.org/title/Iwd"),
    ("Installation guide: Connect to internet", "https://wiki.archlinux.org/title/Installation_guide#Connect_to_the_internet"),
]
```

---

## Stage 0 — Implementation Notes (welcome.py)

- `WelcomeScreen` extends `Gtk.Box` (horizontal split: left content + right info panel)
- Three `Gtk.EventBox` cards for Beginner / Intermediate / Advanced
- Card state (hover, selected) driven entirely by CSS classes — no inline styling
- Info panel text lives in `WELCOME_INFO` dict keyed by experience level string
- `on_next` callback writes `state.experience_level` before handing off to the stage controller
- `main.py` uses a `Gtk.Stack` with `SLIDE_LEFT` transitions (220ms); new stages are registered in the `STAGE_CLASSES` list

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
- Next session: **Stage 1 — Network Setup + Wiki Viewer** (`installer/ui/network.py`, `installer/wiki/viewer.py`, `installer/backend/network.py`)

**What to tell Claude next session:**
> "We're building an Arch Linux GTK3 installer in Python. Here's the full context: [paste this file].
>  Today I want to work on Stage 1 — Network Setup and the Wiki Viewer."

---

## Known Issues / Deferred Decisions

- [ ] Btrfs subvolume layout presets (defer until filesystem screen)
- [ ] LVM support (intermediate/advanced only — defer)
- [ ] Dual-boot / existing partition detection (defer until partition screen)
- [ ] Whether to bundle a default mirrorlist or always fetch live (decide at mirror screen)
- [ ] UKI: mkinitcpio vs dracut decision (defer until filesystem/bootloader screens)
- [ ] Secure Boot key enrollment UI (advanced only — defer until bootloader screen)

---

## Commit Log Summary

| Session | Commit message                                          |
|---------|---------------------------------------------------------|
| 1       | chore: initial project scaffold and architecture        |
| 2       | feat(stage-0): welcome screen and experience level      |
| 2       | chore: restructure into installer/ package layout       |
| 2       | docs: wiki viewer, EFIStub/UKI, network-early decisions |
