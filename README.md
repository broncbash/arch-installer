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
- **Contextual hints** — every screen has an info panel tailored to your experience level
- **Integrated Arch Wiki viewer** — wiki links on every screen open an in-app
  WebKit2GTK browser, with graceful fallback if offline
- **Full partitioning support** — MBR/GPT, automatic layouts, manual partitioning,
  LUKS2 encryption, Btrfs subvolumes
- **Mirror selection** — reflector integration with checkbox country picker,
  live command display, elapsed timer, and bundled fallback mirrorlist
- **Package selection** — DE/WM picker (GNOME, KDE, XFCE, Sway, Hyprland, Niri,
  i3, bspwm) plus curated extras and free-form package entry
- **Base system install** — pacstrap with live log, per-step progress, retry on error
- **Dry-run mode** — a prominent amber banner and full simulation of all disk
  operations so you can test safely on any machine
- **Nothing written to disk** until you confirm — and never in dry-run mode
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
| 8 | Package Selection | ✅ Complete |
| 9 | Base Install (pacstrap) | ✅ Complete |
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
sudo pacman -S python python-gobject gtk3 webkit2gtk polkit parted \
               reflector sgdisk cryptsetup btrfs-progs
```

> **reflector** is required for mirror fetching — the bundled fallback mirrorlist
> is used automatically if it isn't installed or the network is down.
>
> **webkit2gtk** enables the integrated Arch Wiki viewer. Without it the viewer
> falls back to displaying the raw URL.

---

## Running (development)

```bash
git clone git@gitlab.com:broncbash/arch-installer.git
cd arch-installer
python3 -m installer.main
```

The installer starts in **dry-run mode** by default — a yellow banner is shown
at the top of the window and no disk operations are performed. To perform a real
install, set `dry_run = False` in `installer/state.py`.

> You do not need `sudo` to run the UI during development. Privilege escalation
> (via polkit/pkexec) will be added when real disk operations are wired up.

---

## Project Structure

```
arch-installer/
├── installer/
│   ├── main.py                  # Entry point, stage controller, dry-run banner
│   ├── state.py                 # Shared install state (passed between all screens)
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
│   │   └── ...                  # Remaining stages (planned)
│   ├── backend/
│   │   ├── runner.py            # safe_run() — dry-run aware subprocess wrapper
│   │   ├── network.py           # Connectivity checks, iwd WiFi wrapper
│   │   ├── keyboard.py          # localectl / loadkeys wrappers
│   │   ├── locale.py            # locale.gen parser
│   │   ├── disk.py              # lsblk wrapper, boot mode detection, RAM detection
│   │   ├── mirrors.py           # reflector wrapper, fallback mirrorlist
│   │   └── pacstrap.py          # Full install sequence (partition→format→pacstrap→fstab)
│   ├── wiki/
│   │   └── viewer.py            # In-app WebKit2GTK wiki viewer
│   └── assets/
│       ├── installer.png
│       ├── installer.svg
│       └── style.css            # Dark GitHub-style GTK theme
├── tests/
├── docs/
├── PKGBUILD
└── CLAUDE.md                    # AI session continuity file
```

---

## Safety: Dry-Run Mode

The installer ships with `dry_run = True` in `installer/state.py`. In this mode:

- A **amber warning banner** is shown at the top of every screen
- The install screen begin button reads **"🧪 Begin Dry Run"**
- All disk operations (parted, mkfs, cryptsetup, mount, pacstrap, etc.) are
  **logged but never executed**
- The UI behaves exactly as it would in a real install — progress bars fill,
  logs scroll, steps complete — so you can test the full flow safely

To perform a real install, change one line in `installer/state.py`:
```python
dry_run: bool = False   # was True
```

---

## Design Philosophy

Built as a learning project with the goal of understanding both the Arch Linux
installation process and GTK3 application development deeply. Every design
decision follows the Arch Wiki, and every screen is built to be understandable
at the Beginner level while exposing full control at the Advanced level.

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
