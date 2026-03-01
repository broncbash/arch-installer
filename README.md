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
> The installer boots and runs from a custom ISO in a VM. End-to-end install testing
> is in progress — base system install nearly complete.

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
- **Base system install** — pacstrap with live streaming status ticker, per-step
  progress, retry on error; Begin button fixed at bottom outside scroll area
- **Bootloader selection** — GRUB, systemd-boot, rEFInd, EFIStub, UKI; options
  filtered by experience level with live card switching
- **Complete / Reboot** — post-install chroot config: locale, keyboard, timezone,
  initramfs (mkinitcpio or dracut), bootloader install, service enablement,
  unmount, reboot
- **Dry-run toggle** — toggle switch on the welcome screen; defaults to safe
  dry-run mode with a live banner that hides when disabled
- **Custom bootable ISO** — archiso profile boots directly into the GTK installer;
  Plymouth boot splash with animated logo (Y-axis flip + pulsing cyan glow)

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

All 16 stages complete. End-to-end VM install testing in progress. 🚧

---

## Custom ISO

The project includes a full archiso profile that builds a bootable ISO with the
GTK installer launching automatically on boot — no desktop environment, no login
prompt.

### Build the ISO

```bash
sudo ./build.sh
```

`build.sh` automatically syncs the installer source into the ISO airootfs, cleans
previous build artifacts, and runs `mkarchiso`. The ISO is output to `/tmp/archiso-out/`.

### What the ISO does on boot

1. Plymouth displays the animated boot splash (spinning logo + pulsing glow)
2. systemd starts `arch-installer.service` after NetworkManager is online
3. Service runs `/usr/local/bin/arch-installer-session` as root on tty1
4. Session script quits Plymouth, starts a minimal Xorg server
5. GTK3 installer launches fullscreen automatically
6. User goes through all stages and installs Arch Linux

### Boot entries

- **Normal** — quiet boot with Plymouth splash, autostart installer
- **Debug** — `systemd.unit=multi-user.target`, drops to TTY for troubleshooting

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

---

## Safety: Dry-Run Mode

The welcome screen has a **Dry Run Mode toggle switch** — enabled by default.

- When **on**: a banner is shown at the top of every screen, all disk operations
  are logged but never executed, the install screen shows "🧪 Begin Dry Run"
- When **off**: a red warning box appears on the welcome screen, the banner
  disappears, and real disk operations will be performed

The toggle updates `state.dry_run` live — no need to edit any source files.

---

## Design Notes

**All choices come before the install.** Packages, timezone, hostname, users —
everything is configured first on the Review & Confirm screen. Pacstrap runs
after confirmation with the complete picture.

**Experience levels** control what's visible on every screen:
- Beginner sees only the safest options with plain-language explanations
- Intermediate unlocks more choices with brief technical context
- Advanced exposes everything with full technical detail

**Arch Wiki links** are available on every screen via a collapsible expander
at the bottom of the hints panel.

**Review & Confirm** is a read-only summary of every selection. Each section
has an ✏ Edit button that jumps directly back to that stage and returns
automatically after editing.

**Live install status ticker** — during pacstrap, a spinner and status line show
the current package being downloaded or installed in real time.

---

## License

[GPLv3](LICENSE) — © 2025 broncbash
