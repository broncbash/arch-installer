# CLAUDE.md — Arch Installer Project Context
# Paste this file at the start of every Claude session to restore full context.
# Update this file at the end of every session before committing.

---

## Project Overview

A full-featured, GTK3-based graphical Arch Linux installer built from scratch in Python.
No Calamares. No archinstall. Completely original.

**GitLab repo:** https://gitlab.com/broncbash/arch-installer (private until public release)
**Local repo:**   /home/ronb/nas_data/Git_Projects/arch-installer

### Design Philosophy
- Follows Arch Wiki installation standards exactly
- Experience-level system: Beginner / Intermediate / Advanced
- Every screen has an info/hint panel and wiki links
- GTK3 + Python, dark GitHub-style theme
- Dry-run mode on by default — set dry_run = False in state.py for real installs
- Always provide complete files, never diffs/snippets

---

## Tech Stack

| Component   | Choice                          |
|-------------|---------------------------------|
| Language    | Python 3                        |
| GUI         | GTK3 (python-gobject)           |
| Wiki viewer | WebKit2GTK                      |
| Privilege   | sudo (must run as root)         |
| Disk ops    | parted, sgdisk, mkfs.*          |
| Encryption  | cryptsetup (LUKS2)              |
| Initramfs   | mkinitcpio (default) or dracut  |
| Install     | pacstrap                        |
| ISO build   | archiso (mkarchiso)             |
| VCS         | Git / GitLab (private)          |
| License     | GPLv3                           |

---

## Launching the Installer

```bash
sudo ./arch-installer
# or
sudo python3 -m installer.main
```

On a live ISO the autostart mechanism launches as root directly — no sudo needed.

---

## Stage Order (all choices BEFORE install)
```
 0  Welcome / Experience Level
 1  Network Setup
 2  Keyboard Layout
 3  Locale
 4  Disk Selection
 5  Partition Scheme
 6  Filesystem + Encryption
 7  Mirror Selection
 8  Package Selection
 9  Timezone
10  System Config / Hostname
11  User Setup
12  Review & Confirm
13  Base Install               <- pacstrap runs here
14  Bootloader
15  Complete / Reboot
```

## Status

| #  | Stage                   | Status     | Files                               |
|----|-------------------------|------------|-------------------------------------|
|  0 | Welcome                 | Complete   | ui/welcome.py                       |
|  1 | Network                 | Complete   | ui/network.py, backend/network.py   |
|  2 | Keyboard                | Complete   | ui/keyboard.py                      |
|  3 | Locale                  | Complete   | ui/locale_screen.py                 |
|  4 | Disk Selection          | Complete   | ui/disk_select.py, backend/disk.py  |
|  5 | Partitions              | Complete   | ui/partition.py                     |
|  6 | Filesystem + Encryption | Complete   | ui/filesystem.py                    |
|  7 | Mirrors                 | Complete   | ui/mirrors.py                       |
|  8 | Packages                | Complete   | ui/packages.py                      |
|  9 | Timezone                | Complete   | ui/timezone.py                      |
| 10 | System Config           | Complete   | ui/system_config.py                 |
| 11 | User Setup              | Complete   | ui/users.py                         |
| 12 | Review & Confirm        | Complete   | ui/review.py                        |
| 13 | Base Install            | Complete   | ui/install.py, backend/pacstrap.py  |
| 14 | Bootloader              | Complete   | ui/bootloader.py                    |
| 15 | Complete / Reboot       | Complete   | ui/complete.py                      |

---

## File Structure
```
arch-installer/
├── arch-installer              <- top-level bash launcher
├── CLAUDE.md
├── README.md
├── installer/
│   ├── main.py                 <- entry point, stage controller
│   ├── dev_prefill.py          <- DEV_AUTOFILL test defaults (remove when done)
│   ├── privilege.py            <- root check
│   ├── state.py                <- global install state (DiskPartition, InstallState)
│   ├── ui/
│   │   ├── base_screen.py      <- base class all screens inherit
│   │   ├── welcome.py          <- stage 0
│   │   ├── network.py          <- stage 1
│   │   ├── keyboard.py         <- stage 2
│   │   ├── locale_screen.py    <- stage 3
│   │   ├── disk_select.py      <- stage 4
│   │   ├── partition.py        <- stage 5
│   │   ├── filesystem.py       <- stage 6
│   │   ├── mirrors.py          <- stage 7
│   │   ├── packages.py         <- stage 8
│   │   ├── timezone.py         <- stage 9
│   │   ├── system_config.py    <- stage 10
│   │   ├── users.py            <- stage 11
│   │   ├── review.py           <- stage 12
│   │   ├── install.py          <- stage 13
│   │   ├── bootloader.py       <- stage 14
│   │   └── complete.py         <- stage 15
│   ├── backend/
│   │   ├── runner.py           <- dry-run safe subprocess wrapper
│   │   ├── disk.py
│   │   ├── mirrors.py
│   │   └── pacstrap.py         <- full install sequence (partition->users)
│   ├── wiki/viewer.py
│   └── assets/
│       ├── installer.png / installer.svg
│       └── style.css
├── iso/                        <- archiso profile
│   ├── build.sh                <- sudo ./iso/build.sh
│   ├── profiledef.sh
│   ├── packages.x86_64
│   ├── pacman.conf
│   ├── airootfs/
│   │   ├── etc/
│   │   │   ├── mkinitcpio.conf.d/archiso.conf   <- CRITICAL - archiso hooks
│   │   │   ├── plymouth/plymouthd.conf           <- Theme=arch-installer
│   │   │   └── systemd/system/arch-installer.service
│   │   ├── usr/
│   │   │   ├── local/bin/arch-installer-session
│   │   │   └── share/plymouth/themes/arch-installer/
│   │   │       ├── arch-installer.plymouth
│   │   │       ├── arch-installer.script  <- ISO splash only - NO password dialog
│   │   │       ├── logo.png
│   │   │       └── glow.png
│   │   └── opt/arch-installer/            <- installer copy (rsync'd by build.sh)
│   ├── efiboot/loader/entries/
│   │   ├── arch-installer.conf
│   │   └── arch-installer-debug.conf
│   └── syslinux/syslinux.cfg
└── tests/
```

---

## State Object Key Fields (installer/state.py)

- `experience_level`          — 'beginner'|'intermediate'|'advanced'
- `target_disk`               — e.g. '/dev/sda'
- `boot_mode`                 — 'uefi'|'bios'
- `partition_scheme`          — 'auto'|'manual'
- `partitions`                — list of DiskPartition objects
- `root_filesystem`           — 'ext4'|'btrfs'|'xfs'|'f2fs'
- `luks_passphrase`           — empty string = no encryption
- `luks_block_device`         — raw block device path saved by _step_luks BEFORE
                                p.device is overwritten to /dev/mapper/cryptroot;
                                used by bootloader step to get UUID via blkid
- `initramfs_generator`       — 'mkinitcpio'|'dracut'
- `bootloader`                — 'grub'|'systemd-boot'|'refind'|'efistub'|'uki'
- `bootloader_uki_needs_decrypt` — bool
- `dry_run`                   — bool, default True

User dict: `{username, password, sudo: bool, shell, groups: list}`

---

## BaseScreen Rules

- Set instance variables BEFORE calling `super().__init__()`
- ALL hide/show calls go in a method via `GLib.idle_add()` at end of `build_content()`
- NEVER call hide()/show() during construction — show_all() overrides them
- `_apply_visibility()` must `return False` for one-shot behaviour
- `on_experience_changed()` can call visibility directly

**Content packing - CRITICAL:**
- `build_content()` returns a plain widget (Box, etc.) — NOT a ScrolledWindow
- base_screen already wraps it in a ScrolledWindow with `hexpand=True`
- Returning a nested ScrolledWindow breaks layout on all other screens
- The base packs content with `True, True` (expand+fill) — do not change this

---

## GTK3 Layout - HARD-WON LESSONS (packages.py)

This took an entire session to solve. Read carefully before touching packages.py.

### The core problem
GTK3's ScrolledWindow with hscrollbar-policy=NEVER always allocates its child
the full viewport width, ignoring halign, hexpand=False, and set_size_request
on nested children. There is no clean workaround - you have to work with it.

### What causes the info panel to get pushed off-screen
Any widget inside the content area with an unconstrained natural width will
force GTK to make the content area wider than the window, pushing the info panel
off the right edge. Culprits in packages.py were:
- Gtk.Label with set_line_wrap(True) but NO set_max_width_chars() - GTK
  calculates natural width by rendering the full text on one line first
- Gtk.Grid with inline label children that have no width constraint
- Any hexpand=True set on a container returned from build_content()

### The working solution for packages.py
- DE/WM section frame: set_size_request(660, -1) + set_halign(Gtk.Align.START)
- Cards: set_size_request(230, 110) - 3 per row in plain HBoxes (NOT FlowBox)
- FlowBox was abandoned - it distributes all available width equally among children
  regardless of child size_request, making cards stretch to fill the viewport
- Every wrapping label has set_max_width_chars() set
- _de_desc label: set_max_width_chars(40)
- Extras grid desc_lbl: set_max_width_chars(30) + set_ellipsize(END)
- DO NOT remove the set_size_request / halign=START from the frames -
  this causes the content area to expand and push the info panel off screen
- DO NOT add hexpand=True to root or outer boxes in build_content()

### Remaining cosmetic issue
There is a gap to the right of the DE tile box before the info panel.
This is acceptable for now - all functionality works correctly.
Future fix: increase card width or find a non-destructive way to fill the space.

---

## LUKS Boot Flow (complete.py)

1. `_step_initramfs` - patches HOOKS=(...) in pure Python (no sed):
   - Always inserts plymouth after udev
   - Inserts encrypt after block when LUKS active
   - Runs mkinitcpio -P

2. `_step_bootloader` (GRUB + LUKS):
   - Sets GRUB_ENABLE_CRYPTODISK=y
   - Gets UUID via blkid -o value -s UUID <state.luks_block_device>
   - Sets GRUB_CMDLINE_LINUX="cryptdevice=UUID=<uuid>:cryptroot root=/dev/mapper/cryptroot"
   - Creates 512-byte keyfile at /etc/cryptsetup-keys.d/cryptroot.key,
     adds to LUKS, embeds in initramfs via FILES=() - eliminates second prompt
   - Sets GRUB_CMDLINE_LINUX_DEFAULT="quiet splash" unconditionally

**LUKS mapper naming:** crypt{mountpoint} -> cryptroot, crypthome.
Must match cryptdevice=UUID=<uuid>:cryptroot exactly.

**Critical:** state.luks_block_device is saved in pacstrap.py _step_luks
as original_device = p.device BEFORE p.device is overwritten to the mapper path.

---

## Plymouth - Two Separate Contexts

| Context | File | Password dialog |
|---------|------|-----------------|
| ISO boot splash | iso/airootfs/usr/share/plymouth/themes/arch-installer/arch-installer.script | NO |
| Installed system | Written from _PLYMOUTH_INSTALLED_SCRIPT constant in complete.py | YES |

After copytree copies the theme to the installed system, _step_services
immediately overwrites arch-installer.script with _PLYMOUTH_INSTALLED_SCRIPT.

**CRITICAL:** Plymouth's script language does NOT support dot-property assignment
on plain variables. dialog.box_sprite = Sprite() is INVALID and causes the theme
to crash silently, resulting in a blank screen. Use simple variable names only:
password_box = Sprite() etc.

---

## pacstrap.py Install Steps

| Step       | What it does                                                      |
|------------|-------------------------------------------------------------------|
| partition  | sgdisk/parted                                                     |
| format     | mkfs.* per partition                                              |
| luks       | luksFormat + open; saves state.luks_block_device first            |
| mount      | mount all partitions under /mnt                                   |
| mirrorlist | write mirrorlist                                                   |
| keyring    | pacman-key --init + --populate                                    |
| pacstrap   | writes optimized pacman.conf (ParallelDownloads=10) first,        |
|            | then pacstrap -K -C /mnt/etc/pacman.conf /mnt <packages>         |
| fstab      | genfstab -U                                                       |
| hostname   | /etc/hostname + /etc/hosts                                        |
| users      | useradd + chpasswd + sudoers                                      |

---

## Known Issues (next session)

- **DE tile box gap** — The 660px frame sits left-aligned leaving empty space
  to the right before the info panel. Cosmetic only, everything works.
  DO NOT attempt to remove size_request/halign=START to fix this - see GTK3
  lessons above. Safe approach: increase card/frame width incrementally.

- **LUKS pre-menu passphrase prompt** — Beginner auto layout has no separate
  /boot partition; /boot lives inside the LUKS container. GRUB needs
  GRUB_ENABLE_CRYPTODISK=y to read grub.cfg, which forces a passphrase prompt
  before the boot menu appears.
  Fix: add a separate unencrypted 512MB ext4 /boot partition to
  _build_auto_layout() in partition.py when LUKS is enabled.

- **DEV_AUTOFILL auto-advance race condition** — Multiple screens have
  _dev_auto_advance() via GLib.idle_add() which fires _on_next_cb() rapidly.
  Because each screen rebuild creates a new on_next closure, multiple callbacks
  can fire and corrupt _current_stage. Currently all _dev_auto_advance hooks
  are present in the code but the auto-advance behaviour is unreliable.
  The manual click path works correctly when dry_run=False.
  Fix needed: centralize auto-advance in main.py _go_to_stage() instead of
  per-screen GLib.idle_add() calls.

- **Non-GRUB bootloaders** — systemd-boot, rEFInd, EFIStub, and UKI have all
  been rewritten with correct helper functions (_get_root_partuuid,
  _build_root_options, _get_efi_part_info etc.) but have not been confirmed
  working yet due to the auto-advance debugging work consuming testing time.
  Next session: test each bootloader with DEV_AUTOFILL + manual dry_run toggle.

---

## Custom ISO Build

```bash
sudo mkarchiso -v \
  -w /tmp/archiso-work \
  -o /home/ronb/nas_data/Git_Projects/arch-installer/iso/out \
  /home/ronb/nas_data/Git_Projects/arch-installer/iso
```

### Autostart
```
arch-installer.service -> arch-installer-session
    -> cleans X locks -> GTK_THEME=Adwaita:dark -> Xorg :0 -> python3 -m installer.main
```

### Key archiso lessons
- customize_airootfs.sh is DEPRECATED - use symlinks in airootfs directly
- Service enablement: symlinks in airootfs/etc/systemd/system/multi-user.target.wants/
- Masking: /dev/null symlinks in airootfs/etc/systemd/system/
- mkinitcpio.conf.d/archiso.conf is REQUIRED or boot fails with "Failed to start Switch Root"
- Suppress systemd-firstboot: place locale.conf, hostname, vconsole.conf, localtime in airootfs/etc/
- Work directory MUST be local filesystem - NFS causes realpath errors
- Boot entries use %INSTALL_DIR% and %ARCH% variables

### Troubleshooting

| Symptom | Where to look |
|---------|---------------|
| Installer doesn't start | journalctl -u arch-installer.service |
| X fails to start | /var/log/Xorg.0.log |
| Session script errors | /var/log/arch-installer-session.log |
| Plymouth not showing | Check script for dot-property syntax (invalid) |
| "Failed to start Switch Root" | archiso.conf missing |
| Build realpath error | Work dir is on NFS - use /tmp |

---

## Session Commit Log

| Session | Commit message |
|---------|----------------|
| 1  | chore: initial project scaffold |
| 2  | feat(stage-0): welcome, experience level |
| 2  | chore: restructure into installer/ package |
| 3  | feat(stage-1): network setup, wiki viewer |
| 4  | feat(stages-2-4): keyboard, locale, disk selection |
| 5  | feat(stages-5-6): partitions, filesystem + LUKS |
| 6  | feat(stage-7): mirror selection with reflector |
| 7  | feat(stage-8): package selection, DE/WM picker |
| 7  | feat(stages-9-12): base install, dry-run, runner.py |
| 8  | feat(stage-10): timezone with live clock |
| 8  | feat(stage-11): system config - hostname, root password, NTP |
| 9  | refactor: reorder stages - all choices before pacstrap |
| 9  | feat(stage-11): user setup |
| 10 | feat(stage-13): bootloader selection screen |
| 10 | fix(ui): wiki links collapsible expander |
| 11 | feat(stages-12-15): review, complete/reboot; multi-select DE |
| 12 | feat(privilege): root check + launcher script |
| 12 | feat(stage-10): initramfs generator choice (Advanced) |
| 13 | fix(launcher): auto-install GTK deps and expand cowspace |
| 14 | feat(iso): archiso profile - autostart service, build.sh |
| 15 | fix(iso): archiso.conf, symlinks, firstboot suppression, X session |
| 16 | feat(iso): Plymouth boot splash - Y-axis flip, pulsing glow |
| 16 | fix(iso): partprobe, icon loading, dry-run banner, rsync |
| 17 | fix(main): reconstruct truncated main.py |
| 17 | fix(install): _apply_phase _begin_row crash |
| 18 | fix(packages): DE card sizing - homogeneous=False, fixed 150x95, 3 cols max |
| 18 | fix(packages): remove nested ScrolledWindow from build_content |
| 18 | feat(main): maximize() on startup |
| 18 | fix(pacstrap): ParallelDownloads=10, optimized pacman.conf before pacstrap |
| 18 | fix(pacstrap): save luks_block_device before overwriting p.device |
| 18 | fix(pacstrap): standardize mapper name to cryptroot/crypthome |
| 18 | fix(complete): encrypt hook for all LUKS installs; HOOKS patched in Python |
| 18 | fix(complete): GRUB cryptdevice UUID from blkid on saved block device |
| 18 | fix(complete): LUKS keyfile to eliminate second passphrase prompt |
| 18 | fix(complete): quiet splash unconditional; plymouth hook always added |
| 18 | feat(complete): Plymouth password dialog in installed system only |
| 18 | fix(iso): restore original Plymouth script; password dialog was breaking splash |
| 18 | docs: update CLAUDE.md and README.md - session 18 |
| 19 | fix(packages): replace FlowBox with HBox rows; 230x110px cards; label width constraints |
| 19 | docs: update CLAUDE.md and README.md - session 19 |
| 20 | feat(dev): DEV_AUTOFILL prefill system - state.py flag, dev_prefill.py, per-screen auto-advance |
| 20 | fix(bootloaders): rewrite systemd-boot, rEFInd, EFIStub, UKI with helper functions |
| 20 | fix(dev): confirm field pre-fill in users.py and system_config.py |
| 20 | fix(dev): FALLBACK_MIRRORLIST used in dev_prefill; mirrors screen skips fetch |
| 20 | fix(dev): _build_auto_layout called in dev_prefill to pre-populate state.partitions |
| 20 | debug(dev): base_screen _nav_ready guard identified; auto-advance race condition found |
| 20 | docs: update CLAUDE.md and README.md - session 20 |
