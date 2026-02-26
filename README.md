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
- **Full partitioning** — MBR/GPT, auto/manual layouts, LUKS2, Btrfs subvolumes
- **Mirror selection** — reflector with checkbox country picker and live log
- **Package selection** — 9 DE/WM options plus curated extras and free-form entry
- **Timezone** — searchable list with live clock preview, auto-detected default
- **System config** — hostname validation, root password with strength indicator, NTP
- **User setup** — username, password, sudo, shell picker, group checkboxes
- **Base system install** — pacstrap with live log, per-step progress, retry on error
- **Dry-run mode** — red banner + full simulation so you can test safely anywhere

---

## Installation Stages

| #  | Stage | Status |
|----|-------|--------|
|  0 | Welcome / Experience Level | ✅ Complete |
|  1 | Network Setup | ✅ Complete |
|  2 | Keyboard Layout | ✅ Complete |
|  3 | Language / Locale | ✅ Complete |
|  4 | Disk Selection | ✅ Complete |
|  5 | Partition Scheme | ✅ Complete |
|  6 | Filesystem + Encryption | ✅ Complete |
|  7 | Mirror Selection | ✅ Complete |
|  8 | Package Selection | ✅ Complete |
|  9 | Timezone | ✅ Complete |
| 10 | System Config / Hostname | ✅ Complete |
| 11 | User Setup | ✅ Complete |
| 12 | Base Install (pacstrap) | ✅ Complete |
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

- A **red warning banner** is shown at the top of every screen
- All disk operations are **logged but never executed**
- The install screen shows "🧪 Begin Dry Run" instead of "Begin Installation"
- The full UI flow works identically — progress bars, logs, step indicators

To perform a real install:
```python
# installer/state.py
dry_run: bool = False
```

---

## Design Notes

**All choices come before the install.** Packages, timezone, hostname, users —
everything is configured first. Pacstrap runs last with the complete picture.
This means the shell you pick for your user (zsh, fish) is automatically
included in the pacstrap package list.

**Experience levels** control what's visible on every screen:
- Beginner sees only the safest options with plain-language explanations
- Intermediate unlocks more choices with brief technical context
- Advanced exposes everything with full technical detail

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
