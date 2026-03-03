<div align="center">
  <img src="installer/assets/installer.png" width="96" alt="arch-installer icon"/>
  <h1>Arch Installer</h1>
  <p>A full-featured, GTK3 graphical installer for Arch Linux — built from scratch.</p>

  ![Python](https://img.shields.io/badge/python-3.x-blue?logo=python&logoColor=white)
  ![GTK](https://img.shields.io/badge/GTK-3-blueviolet?logo=gtk)
  ![License](https://img.shields.io/badge/license-GPLv3-green)
  ![Status](https://img.shields.io/badge/status-VM_testing-yellow)
  ![Arch Linux](https://img.shields.io/badge/Arch_Linux-1793D1?logo=arch-linux&logoColor=white)
</div>

---

> ⚠️ **This project is in active development and not yet ready for use on real hardware.**
> End-to-end VM installs are working. LUKS encryption, Plymouth boot splash, and
> post-install configuration are functional. A developer autofill system has been
> added to speed up bootloader testing. A small number of known issues remain
> (see below).

---

## What is this?

A clean-room graphical Arch Linux installer — no Calamares, no archinstall.
Built with GTK3 and Python, following Arch Wiki installation standards exactly.

### Key Features

- **Experience levels** — Beginner, Intermediate, and Advanced modes that adjust
  available options and explanations on every screen
- **Contextual hints** — every screen has an info panel tailored to your level
- **Integrated Arch Wiki viewer** — wiki links open an in-app WebKit2GTK browser
  via a collapsible expander in the hints panel
- **Full partitioning** — MBR/GPT, auto/manual layouts, LUKS2 encryption, Btrfs subvolumes
- **Mirror selection** — reflector with checkbox country picker and live log
- **Package selection** — 9 DE/WM options with multi-select, curated extras checklist,
  and free-form package entry
- **Timezone** — searchable list with live clock preview
- **System config** — hostname, root password with strength indicator, NTP toggle,
  initramfs generator choice (mkinitcpio / dracut) for Advanced users
- **User setup** — username, password, sudo, shell picker, group checkboxes
- **Review & Confirm** — full summary of every selection before anything touches disk;
  Edit buttons jump directly back to any stage and return automatically
- **Base system install** — pacstrap with live streaming status, per-step progress,
  retry on error; optimized pacman.conf (ParallelDownloads=10) for faster downloads
- **LUKS encryption** — full dm-crypt/LUKS2 with correct initramfs hooks,
  cryptdevice kernel params, GRUB integration, and a keyfile to avoid double prompts
- **Bootloader** — GRUB, systemd-boot, rEFInd, EFIStub, UKI; filtered by experience level
- **Post-install config** — locale, keyboard, timezone, initramfs, bootloader,
  service enablement, unmount, reboot — all automated
- **Plymouth boot splash** — animated logo (Y-axis flip + pulsing cyan glow) on ISO boot;
  styled LUKS passphrase dialog on the installed system
- **Dry-run mode** — toggle on the welcome screen, enabled by default; all disk
  operations are logged but never executed

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

All 16 stages complete. VM end-to-end testing in progress. 🚧

---

## Known Issues

- **Package selection screen gap** — The DE/WM card container is fixed-width and
  sits left-aligned, leaving empty space before the hints panel. Cosmetic only —
  all functionality works correctly.
- **LUKS pre-menu passphrase prompt** — when using Beginner auto-partitioning with
  LUKS, GRUB asks for the passphrase before showing the boot menu because `/boot`
  lives inside the encrypted root partition. A separate `/boot` partition in the
  auto layout will fix this in a future session.
- **DEV_AUTOFILL auto-advance** — per-screen auto-advance hooks are in place but
  have a race condition due to multiple GLib closure callbacks firing on rapid
  screen transitions. Manual click-through works correctly. Fix planned for next
  session.
- **Non-GRUB bootloaders** — rewritten with correct helper functions but not yet
  confirmed working. Testing in progress.

---

## Custom ISO

Includes a full archiso profile that builds a bootable ISO with the GTK installer
launching automatically on boot.

### Build

```bash
sudo mkarchiso -v \
  -w /tmp/archiso-work \
  -o /path/to/arch-installer/iso/out \
  /path/to/arch-installer/iso
```

`build.sh` syncs the installer source into the ISO airootfs automatically before building.

### Boot sequence

1. Plymouth displays the animated boot splash (spinning Arch logo + pulsing cyan glow)
2. systemd starts `arch-installer.service` after NetworkManager is online
3. Service runs `/usr/local/bin/arch-installer-session` as root on tty1
4. Session script starts a minimal Xorg server
5. GTK3 installer launches fullscreen automatically
6. User installs Arch Linux through the GUI
7. On reboot: Plymouth shows a styled passphrase dialog if LUKS was enabled

### Boot entries

- **Normal** — quiet boot with Plymouth splash, autostart installer
- **Debug** — `systemd.unit=multi-user.target`, drops to TTY for troubleshooting

---

## Dependencies

```bash
sudo pacman -S python python-gobject gtk3 webkit2gtk parted \
               reflector sgdisk cryptsetup btrfs-progs
```

---

## Running (development)

```bash
git clone git@gitlab.com:broncbash/arch-installer.git
cd arch-installer
sudo ./arch-installer
```

Must be run as root. On the live ISO, root is already the active user.

---

## Safety: Dry-Run Mode

The welcome screen has a **Dry Run Mode toggle** — enabled by default.

- **On**: banner shown at top of every screen, disk operations logged but not executed
- **Off**: red warning shown, real disk operations will be performed

---

## Design Notes

**All choices come before the install.** Everything is configured on the Review &
Confirm screen. Pacstrap runs after confirmation with the complete picture.

**Experience levels** control what's visible on every screen — Beginner sees only
safe options with plain-language explanations; Advanced exposes everything.

**Arch Wiki links** are available on every screen via a collapsible expander at
the bottom of the hints panel.

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
