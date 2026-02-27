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
- **Integrated Arch Wiki viewer** — wiki links open an in-app WebKit2GTK browser,
  accessible via a collapsible "📖 Arch Wiki" expander in the hints panel
- **Full partitioning** — MBR/GPT, auto/manual layouts, LUKS2, Btrfs subvolumes
- **Mirror selection** — reflector with checkbox country picker and live log
- **Package selection** — 9 DE/WM options with multi-select (tick as many as you
  want), curated extras checklist, and free-form package entry
- **Timezone** — searchable list with live clock preview, auto-detected default
- **System config** — hostname validation, root password with strength indicator,
  NTP toggle, and initramfs generator choice (mkinitcpio / dracut) for Advanced users
- **User setup** — username, password, sudo, shell picker, group checkboxes
- **Review & Confirm** — full summary of every selection before anything touches
  disk; ✏ Edit buttons jump directly back to any stage and return automatically
- **Base system install** — pacstrap with live log, per-step progress, retry on error
- **Bootloader selection** — GRUB, systemd-boot, rEFInd, EFIStub, UKI; options
  filtered by experience level with live card switching
- **Complete / Reboot** — post-install chroot config: locale, keyboard, timezone,
  initramfs (mkinitcpio or dracut), bootloader install, service enablement,
  unmount, reboot
- **Dry-run mode** — yellow banner + full simulation so you can test safely anywhere

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
| 12 | Review & Confirm | ✅ Complete |
| 13 | Base Install (pacstrap) | ✅ Complete |
| 14 | Bootloader | ✅ Complete |
| 15 | Complete / Reboot | ✅ Complete |

All 16 stages complete. 🎉

---

## Dependencies

```bash
sudo pacman -S python python-gobject gtk3 webkit2gtk parted \
               reflector sgdisk cryptsetup btrfs-progs dracut
```

> `dracut` is optional — only needed if you select it as your initramfs generator
> on the System Config screen (Advanced mode). mkinitcpio is installed as part of
> the base Arch system automatically.

---

## Running (development)

```bash
git clone git@gitlab.com:broncbash/arch-installer.git
cd arch-installer
sudo ./arch-installer
```

The installer must be run as root. It will exit with a clear error message if
launched without `sudo`. On a live ISO, root is already the active user so no
`sudo` is needed.

The installer starts in **dry-run mode** by default — a yellow banner is shown and
no disk operations are performed. To perform a real install, set
`dry_run = False` in `installer/state.py`.

---

## Safety: Dry-Run Mode

- A **yellow warning banner** is shown at the top of every screen
- All disk operations are **logged but never executed**
- The install screen shows "🧪 Begin Dry Run" instead of "Begin Installation"
- The complete screen shows "🧪 Begin Dry Run" and closes instead of rebooting
- The full UI flow works identically — progress bars, logs, step indicators

To perform a real install:
```python
# installer/state.py
dry_run: bool = False
```

---

## Design Notes

**All choices come before the install.** Packages, timezone, hostname, users —
everything is configured first on the Review & Confirm screen. Pacstrap runs
after confirmation with the complete picture. This means the shell you pick
for your user (zsh, fish) is automatically included in the pacstrap package list.

**Experience levels** control what's visible on every screen:
- Beginner sees only the safest options with plain-language explanations
- Intermediate unlocks more choices with brief technical context
- Advanced exposes everything with full technical detail

**Initramfs generator** is an Advanced-only choice on the System Config screen.
Beginner and Intermediate users always get mkinitcpio (the Arch default) silently.
Advanced users can switch to dracut via radio buttons. The choice is reflected in
the Review summary and drives the actual command run in Stage 15.

**Arch Wiki links** are available on every screen via a collapsible expander
at the bottom of the hints panel. Collapsed by default so the hint text always
has room to breathe — one click to expand when you need a reference.

**Review & Confirm** is a read-only summary of every selection made across all
prior stages. Each section has an ✏ Edit button that jumps directly back to that
stage. After editing, clicking Next on the edited screen returns automatically to
Review — no need to step through intermediate screens.

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
