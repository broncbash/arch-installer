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
> Testing is currently done in VMs and dry-run mode only.

---

## What is this?

A clean-room graphical Arch Linux installer — no Calamares, no archinstall.
Built with GTK3 and Python, following Arch Wiki installation standards exactly.

### Key Features

- **Experience levels** — Beginner, Intermediate, and Advanced modes that adjust
  available options and explanations on every screen
- **Contextual hints** — every screen has an info panel tailored to your level
- **Integrated Arch Wiki viewer** — wiki links open an in-app WebKit2GTK browser
- **Full partitioning support** — MBR/GPT, auto/manual layouts, LUKS2, Btrfs subvols
- **Mirror selection** — reflector with checkbox country picker and live log
- **Package selection** — 9 DE/WM options plus curated extras and free-form entry
- **Base system install** — pacstrap with live log, per-step progress, retry on error
- **Timezone** — searchable list with live clock preview, auto-detected default
- **System config** — hostname validation, root password with strength indicator, NTP
- **Dry-run mode** — red banner + full simulation so you can test safely anywhere
- **Nothing written to disk** until confirmed — and never in dry-run mode

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
| 8 | Package Selection | ✅ Complete |
| 9 | Base Install (pacstrap) | ✅ Complete |
| 10 | Timezone | ✅ Complete |
| 11 | System Config / Hostname | ✅ Complete |
| 12 | User + Root Setup | 🔲 Planned |
| 13 | Bootloader | 🔲 Planned |
| 14 | Review & Confirm | 🔲 Planned |
| 15 | Complete / Reboot | 🔲 Planned |

---

## Dependencies

```bash
sudo pacman -S python python-gobject gtk3 webkit2gtk polkit parted \
               reflector sgdisk cryptsetup btrfs-progs
```

---

## Running (development)

```bash
git clone git@gitlab.com:broncbash/arch-installer.git
cd arch-installer
python3 -m installer.main
```

The installer starts in **dry-run mode** by default — a red banner is shown and
no disk operations are performed. To perform a real install, set
`dry_run = False` in `installer/state.py`.

---

## Safety: Dry-Run Mode

The installer ships with `dry_run = True` in `installer/state.py`. In this mode:

- A **red warning banner** is shown at the top of every screen
- All disk operations are **logged but never executed**
- The UI behaves exactly as in a real install — progress bars fill, logs scroll

To perform a real install:
```python
# installer/state.py
dry_run: bool = False   # was True
```

---

## Project Structure

```
arch-installer/
├── installer/
│   ├── main.py                  # Entry point, stage controller, dry-run banner
│   ├── state.py                 # Shared install state
│   ├── ui/
│   │   ├── base_screen.py       # Base class all screens inherit from
│   │   ├── welcome.py           # Stage 0  — Welcome / Experience Level
│   │   ├── network.py           # Stage 1  — Network Setup
│   │   ├── keyboard.py          # Stage 2  — Keyboard Layout
│   │   ├── locale_screen.py     # Stage 3  — Language / Locale
│   │   ├── disk_select.py       # Stage 4  — Disk Selection
│   │   ├── partition.py         # Stage 5  — Partition Scheme
│   │   ├── filesystem.py        # Stage 6  — Filesystem + Encryption
│   │   ├── mirrors.py           # Stage 7  — Mirror Selection
│   │   ├── packages.py          # Stage 8  — Package Selection
│   │   ├── install.py           # Stage 9  — Base System Install
│   │   ├── timezone.py          # Stage 10 — Timezone
│   │   ├── system_config.py     # Stage 11 — System Config / Hostname
│   │   └── ...                  # Remaining stages (planned)
│   ├── backend/
│   │   ├── runner.py            # Dry-run aware subprocess wrapper
│   │   ├── network.py           # Connectivity, iwd WiFi
│   │   ├── keyboard.py          # localectl / loadkeys
│   │   ├── locale.py            # locale.gen parser
│   │   ├── disk.py              # lsblk, boot mode, RAM detection
│   │   ├── mirrors.py           # reflector, fallback mirrorlist
│   │   └── pacstrap.py          # Full install sequence
│   ├── wiki/
│   │   └── viewer.py            # In-app WebKit2GTK wiki viewer
│   └── assets/
│       ├── installer.png
│       ├── installer.svg
│       └── style.css            # Dark GitHub-style GTK theme
├── CLAUDE.md
└── README.md
```

---

## Design Philosophy

Built as a learning project to understand both the Arch Linux installation
process and GTK3 development deeply. Every screen works at the Beginner level
while exposing full control at Advanced.

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
