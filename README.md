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

### Key Features (planned)

- **Experience levels** — Beginner, Intermediate, and Advanced modes that adjust
  available options and explanations on every screen
- **Contextual hints** — every screen has an info panel with suggestions tailored
  to your experience level
- **Full partitioning support** — MBR/GPT, automatic layouts, manual partitioning,
  LUKS encryption, Btrfs subvolumes
- **Bootloader choice** — GRUB, systemd-boot, or rEFInd
- **Desktop environment selection** — choose your DE/WM at install time
- **Nothing written to disk** until you confirm the final review screen
- **Full install log** at `/tmp/arch-installer.log`

---

## Installation Stages

| # | Stage | Status |
|---|-------|--------|
| 0 | Welcome / Experience Level | 🔲 Planned |
| 1 | Keyboard Layout | 🔲 Planned |
| 2 | Language / Locale | 🔲 Planned |
| 3 | Network Check | 🔲 Planned |
| 4 | Disk Selection | 🔲 Planned |
| 5 | Partition Scheme | 🔲 Planned |
| 6 | Filesystem + Encryption | 🔲 Planned |
| 7 | Mirror Selection | 🔲 Planned |
| 8 | Package Selection | 🔲 Planned |
| 9 | Base Install (pacstrap) | 🔲 Planned |
| 10 | Timezone | 🔲 Planned |
| 11 | Locale / Hostname | 🔲 Planned |
| 12 | User + Root Setup | 🔲 Planned |
| 13 | Bootloader | 🔲 Planned |
| 14 | Review & Confirm | 🔲 Planned |
| 15 | Installation Progress | 🔲 Planned |
| 16 | Complete / Reboot | 🔲 Planned |

---

## Dependencies

```bash
sudo pacman -S python python-gobject gtk3 polkit parted
```

## Running (development)

```bash
git clone git@gitlab.com:broncbash/arch-installer.git
cd arch-installer
sudo python installer/main.py
```

---

## Project Structure

```
arch-installer/
├── installer/
│   ├── main.py          # Entry point
│   ├── state.py         # Shared install state
│   ├── ui/              # One file per installer screen
│   ├── backend/         # Disk, pacstrap, chroot, config logic
│   └── assets/          # Icons, CSS
├── tests/
├── docs/
├── PKGBUILD
└── CLAUDE.md            # Developer session continuity file
```

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
