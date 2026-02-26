<div align="center">
  <img src="installer/assets/installer.png" width="96" alt="arch-installer icon"/>
  <h1>Arch Installer</h1>
  <p>A full-featured, GTK3 graphical installer for Arch Linux — built from scratch.</p>

  ![Python](https://img.shields.io/badge/python-3.x-blue?logo=python&logoColor=white)
  ![GTK](https://img.shields.io/badge/GTK-3-blueviolet?logo=gtk)
  ![License](https://img.shields.io/badge/license-GPLv3-green)
  ![Status](https://img.shields.io/badge/status-in_development-orange)
  ![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white)
</div>

---

> ⚠️ **This project is in active development and not yet ready for use on real hardware.**
> Testing is currently done in VMs only.

---

## What is this?

A clean-room graphical Arch Linux installer — no Calamares, no archinstall.
Built with GTK3 and Python, following Arch Wiki installation standards exactly.

### Key Features

- **Experience levels** — Beginner, Intermediate, and Advanced modes that adjust
  available options and explanations on every screen
- **Contextual hints** — every screen has an info panel with suggestions tailored
  to your experience level
- **Integrated Arch Wiki viewer** — wiki links on every screen open an in-app
  WebKit2GTK browser window, with a graceful fallback if offline
- **Full partitioning support** — MBR/GPT, automatic layouts, manual partitioning,
  LUKS encryption, Btrfs subvolumes
- **Mirror selection** — reflector integration with country picker, live command
  display, elapsed timer, and bundled fallback mirrorlist
- **Bootloader choice** — GRUB, systemd-boot, rEFInd, EFIStub, UKI *(coming soon)*
- **Desktop environment selection** — choose your DE/WM at install time *(coming soon)*
- **Nothing written to disk** until you confirm the final review screen
- **Full install log** at `/tmp/arch-installer.log`

---

## Installation Stages

| # | Stage | Status |
|---|-------|--------|
| 0 | Welcome / Experience Level | ✅ Complete |
| 1 | Network Setup | ✅ Complete |
| 2 | Keyboard Layout | ✅ Complete |
| 3 | Language / Locale | ✅ Complete |
| 4 | Disk Selection | ✅ Complete |
| 5 | Partition Scheme | ✅ Complete |
| 6 | Filesystem + Encryption | ✅ Complete |
| 7 | Mirror Selection | ✅ Complete |
| 8 | Package Selection | 🔲 Planned |
| 9 | Base Install (pacstrap) | 🔲 Planned |
| 10 | Timezone | 🔲 Planned |
| 11 | System Config / Hostname | 🔲 Planned |
| 12 | User + Root Setup | 🔲 Planned |
| 13 | Bootloader | 🔲 Planned |
| 14 | Review & Confirm | 🔲 Planned |
| 15 | Installation Progress | 🔲 Planned |
| 16 | Complete / Reboot | 🔲 Planned |

---

## Dependencies

```bash
sudo pacman -S python python-gobject gtk3 webkit2gtk polkit parted reflector
```

> **Note:** `webkit2gtk` is required for the integrated Arch Wiki viewer.
> Without it the viewer falls back to displaying the raw URL.
> `reflector` is required for the mirror selection screen.
> Without it the bundled fallback mirrorlist is used automatically.

---

## Running (development)

```bash
git clone git@gitlab.com:broncbash/arch-installer.git
cd arch-installer
python3 -m installer.main
```

> You do not need `sudo` to run the installer UI during development.
> Privilege escalation (via polkit/pkexec) will be used only when
> actual disk operations begin in a later stage.

---

## Project Structure

```
arch-installer/
├── installer/
│   ├── main.py              # Entry point, stage controller
│   ├── state.py             # Shared install state (passed between all screens)
│   ├── ui/
│   │   ├── base_screen.py   # Base class all screens inherit from
│   │   ├── welcome.py       # Stage 0 — Welcome / Experience Level
│   │   ├── network.py       # Stage 1 — Network Setup
│   │   ├── keyboard.py      # Stage 2 — Keyboard Layout
│   │   ├── locale_screen.py # Stage 3 — Language / Locale
│   │   ├── disk_select.py   # Stage 4 — Disk Selection
│   │   ├── partition.py     # Stage 5 — Partition Scheme
│   │   ├── filesystem.py    # Stage 6 — Filesystem + Encryption
│   │   ├── mirrors.py       # Stage 7 — Mirror Selection
│   │   └── ...              # Remaining stages (in progress)
│   ├── backend/
│   │   ├── network.py       # Connectivity checks, iwd WiFi wrapper
│   │   ├── keyboard.py      # localectl / loadkeys wrappers
│   │   ├── locale.py        # locale.gen parser
│   │   ├── disk.py          # lsblk wrapper, boot mode detection, RAM detection
│   │   ├── mirrors.py       # reflector wrapper, fallback mirrorlist
│   │   └── ...              # Disk ops, pacstrap, chroot, config (planned)
│   ├── wiki/
│   │   └── viewer.py        # In-app WebKit2GTK wiki viewer
│   └── assets/
│       ├── installer.png
│       ├── installer.svg
│       └── style.css        # Dark GitHub-style GTK theme
├── tests/
├── docs/
├── PKGBUILD
└── CLAUDE.md                # AI session continuity file
```

---

## Design Philosophy

This installer is built as a learning project with the goal of understanding
both the Arch Linux installation process and GTK3 application development deeply.
Every design decision follows the Arch Wiki, and every screen is built to be
understandable at the Beginner level while exposing full control at the Advanced level.

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
