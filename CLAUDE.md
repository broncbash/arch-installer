# CLAUDE.md — Arch Installer Project Context
# Paste this file at the start of every Claude session to restore full context.
# Update this file at the end of every session before committing.

---

## Project Overview

A full-featured, GTK3-based graphical Arch Linux installer built from scratch in Python.
No Calamares. No archinstall. Completely original.

**GitLab repo:** https://gitlab.com/broncbash/arch-installer (private until public release)
**Local repo:**   /path/to/nas/arch-installer  ← moved from ~/arch-installer to NAS

### Design Philosophy
- Follows Arch Wiki installation standards exactly
- Experience-level system: Beginner / Intermediate / Advanced
- Every screen has an info/hint panel and wiki links
- GTK3 + Python, dark GitHub-style theme
- Dry-run mode on by default — set dry_run = False in state.py for real installs
- This is a learning project — always provide complete files, never diffs/snippets

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

The installer must be run as root. It will exit immediately with a clear
error message if launched without root privileges.
```bash
# From repo root — simplest
sudo ./arch-installer

# Alternatively
sudo python3 -m installer.main
```

`arch-installer` is a top-level bash launcher script in the repo root.
`installer/privilege.py` contains the root check called at startup.

On a live ISO, the autostart mechanism launches the installer as root directly
so no sudo prompt is needed.

---

## Stage Order (all choices BEFORE install — critical)
```
 0  Welcome / Experience Level
 1  Network Setup
 2  Keyboard Layout
 3  Locale
 4  Disk Selection
 5  Partition Scheme
 6  Filesystem + Encryption
 7  Mirror Selection
 8  Package Selection          ← DE/WM multi-select + extras chosen here
 9  Timezone
10  System Config / Hostname   ← includes initramfs generator choice (Advanced)
11  User Setup
12  Review & Confirm           ← confirm everything BEFORE install
13  Base Install               ← pacstrap runs here
14  Bootloader                 ← post-install config
15  Complete / Reboot          ← locale, initramfs, services, reboot
```

## Status

| #  | Stage                  | Status     | Files                                    |
|----|------------------------|------------|------------------------------------------|
|  0 | Welcome                | ✅ Complete | ui/welcome.py                            |
|  1 | Network                | ✅ Complete | ui/network.py, backend/network.py        |
|  2 | Keyboard               | ✅ Complete | ui/keyboard.py, backend/keyboard.py      |
|  3 | Locale                 | ✅ Complete | ui/locale_screen.py, backend/locale.py   |
|  4 | Disk Selection         | ✅ Complete | ui/disk_select.py, backend/disk.py       |
|  5 | Partitions             | ✅ Complete | ui/partition.py                          |
|  6 | Filesystem + Encryption| ✅ Complete | ui/filesystem.py                         |
|  7 | Mirrors                | ✅ Complete | ui/mirrors.py, backend/mirrors.py        |
|  8 | Packages               | ✅ Complete | ui/packages.py                           |
|  9 | Timezone               | ✅ Complete | ui/timezone.py                           |
| 10 | System Config          | ✅ Complete | ui/system_config.py                      |
| 11 | User Setup             | ✅ Complete | ui/users.py                              |
| 12 | Review & Confirm       | ✅ Complete | ui/review.py                             |
| 13 | Base Install           | ✅ Complete | ui/install.py, backend/pacstrap.py       |
| 14 | Bootloader             | ✅ Complete | ui/bootloader.py                         |
| 15 | Complete / Reboot      | ✅ Complete | ui/complete.py                           |

---

## File Structure
```
arch-installer/
├── arch-installer          ← top-level bash launcher (sudo ./arch-installer)
├── CLAUDE.md
├── README.md
├── installer/
│   ├── main.py             ← entry point, stage controller, dry-run banner
│   ├── privilege.py        ← root check — exits with clear message if not root
│   ├── state.py            ← global install state
│   ├── ui/
│   │   ├── base_screen.py      ← base class all screens inherit
│   │   ├── welcome.py          ← stage 0
│   │   ├── network.py          ← stage 1
│   │   ├── keyboard.py         ← stage 2
│   │   ├── locale_screen.py    ← stage 3
│   │   ├── disk_select.py      ← stage 4
│   │   ├── partition.py        ← stage 5
│   │   ├── filesystem.py       ← stage 6
│   │   ├── mirrors.py          ← stage 7
│   │   ├── packages.py         ← stage 8
│   │   ├── timezone.py         ← stage 9
│   │   ├── system_config.py    ← stage 10
│   │   ├── users.py            ← stage 11
│   │   ├── review.py           ← stage 12
│   │   ├── install.py          ← stage 13
│   │   ├── bootloader.py       ← stage 14
│   │   └── complete.py         ← stage 15
│   ├── backend/
│   │   ├── runner.py           ← dry-run safe subprocess wrapper
│   │   ├── network.py
│   │   ├── keyboard.py
│   │   ├── locale.py
│   │   ├── disk.py
│   │   ├── mirrors.py
│   │   └── pacstrap.py         ← full 9-step install sequence
│   ├── wiki/
│   │   └── viewer.py
│   └── assets/
│       ├── installer.png
│       ├── installer.svg
│       └── style.css
├── iso/                    ← archiso profile — builds the live ISO
│   ├── build.sh                ← main build script (sudo ./iso/build.sh)
│   ├── profiledef.sh           ← ISO metadata, bootmodes, compression
│   ├── packages.x86_64         ← all packages baked into the ISO
│   ├── pacman.conf
│   ├── README.md
│   ├── airootfs/
│   │   ├── etc/
│   │   │   ├── customize_airootfs.sh   ← runs in chroot at build time
│   │   │   ├── X11/xorg.conf.d/10-arch-installer.conf
│   │   │   └── systemd/system/arch-installer.service
│   │   ├── usr/local/bin/
│   │   │   ├── arch-installer-session  ← starts X + installer
│   │   │   └── start-installer         ← thin shim
│   │   └── opt/arch-installer/         ← installer repo (copied in by build.sh)
│   ├── efiboot/loader/
│   │   ├── loader.conf
│   │   └── entries/
│   │       ├── arch-installer.conf
│   │       └── arch-installer-debug.conf
│   └── syslinux/
│       └── syslinux.cfg
└── tests/
```

---

## State Object (installer/state.py)

Key fields:
- `experience_level`      — 'beginner'|'intermediate'|'advanced'
- `keyboard_layout`       — e.g. 'us'
- `locale`                — e.g. 'en_US.UTF-8'
- `timezone`              — e.g. 'America/Los_Angeles'
- `target_disk`           — e.g. '/dev/sda'
- `boot_mode`             — 'uefi'|'bios'
- `partition_table`       — 'gpt'|'mbr'
- `partition_scheme`      — 'auto'|'manual'
- `partitions`            — list of DiskPartition objects
- `root_filesystem`       — 'ext4'|'btrfs'|'xfs'|'f2fs'
- `btrfs_subvolumes`      — bool
- `luks_passphrase`       — empty = no encryption
- `mirrorlist`            — final mirrorlist content string
- `desktop_environment`   — comma-separated selected DE ids, e.g. 'gnome,i3' or ''
- `display_manager`       — dm of first full DE selected, or ''
- `base_packages`         — ['base','base-devel','linux','linux-firmware']
- `extra_packages`        — selected extras + all DE pkgs + shell if non-bash
- `hostname`              — e.g. 'my-arch-pc'
- `root_password`         — string
- `enable_ntp`            — bool, default True
- `initramfs_generator`   — 'mkinitcpio'|'dracut', default 'mkinitcpio'
- `users`                 — list of user dicts (see below)
- `bootloader`            — 'grub'|'systemd-boot'|'refind'|'efistub'|'uki'
- `bootloader_uki`        — bool, True if UKI selected
- `bootloader_uki_needs_decrypt` — bool, True if UKI + LUKS enabled
- `dry_run`               — bool, default True

User dict format:
```python
{
    "username": str,
    "password": str,
    "sudo":     bool,
    "shell":    str,    # '/bin/bash'|'/bin/zsh'|'/bin/fish'
    "groups":   list,   # e.g. ['audio','video','storage','input']
}
```

---

## BaseScreen Rules

Set instance variables BEFORE calling `super().__init__()`.

**CRITICAL — GTK visibility timing:**
- ALL hide/show calls must go in a method called via `GLib.idle_add()` at the
  END of `build_content()` — this runs AFTER `show_all()`.
- NEVER call hide()/show() directly during construction — show_all() overrides them.
- NEVER add a second idle_add for visibility in `__init__()`.
- `_apply_visibility()` must `return False` for one-shot behaviour.
- `on_experience_changed()` can call visibility directly (show_all not re-run).

**CRITICAL — set_next_enabled() timing:**
- Requires `self.next_btn` which is built by BaseScreen after `build_content()`.
- Guard any call made during `build_content()`:
  `if hasattr(self, 'next_btn'): self.set_next_enabled(...)`

**CRITICAL — optional widgets:**
- Any widget built conditionally (e.g. only in Advanced mode) must be guarded
  before access: `if hasattr(self, '_my_widget'): ...`
- Example: `_hosts_preview` in system_config.py is built inside
  `_build_advanced_card()` — `_update_hosts_preview()` guards with
  `if not hasattr(self, '_hosts_preview'): return`

**Wiki links:**
- Define `WIKI_LINKS = [("Label", "https://..."), ...]` as a class variable.
- BaseScreen renders them automatically in a `Gtk.Expander` ("📖 Arch Wiki")
  in the hints panel — collapsed by default so hint text gets full height.
- NEVER build wiki link widgets manually in `build_content()`.
- `_open_wiki(url)` is provided by BaseScreen; override only if you need to
  pass extra context (e.g. NetworkScreen passes `connected=self._connected`).
  Override signature must be `_open_wiki(self, url: str)` — one argument.

---

## System Config Screen (Stage 10)

- File: `installer/ui/system_config.py`
- Beginner: hostname + root password only
- Intermediate: adds NTP toggle + hardware clock note
- Advanced: adds hosts file preview + initramfs generator choice

**Initramfs generator (Advanced only):**
- Radio buttons: mkinitcpio (default, recommended) / dracut
- Saved to `state.initramfs_generator`
- Beginner and Intermediate always get mkinitcpio silently
- Wiki links for both options shown in the hints panel expander

---

## Review Screen (Stage 12)

- File: `installer/ui/review.py`
- Read-only summary of all state — nothing is saved here
- Five categorised cards: System, Disk & Partitions, Packages, Users,
  and an "After Confirmation" info card showing the remaining stages
- Each card has an ✏ Edit button that jumps directly back to that stage
- A confirmation checkbox must be ticked before Next is enabled
- Next button label: "🧪 Begin Dry Run" or "🚀 Begin Installation"
- Validates: target disk set, partitions defined, root password set, users defined
- System card shows: Hostname, Root pwd, Locale, Keyboard, Timezone, NTP,
  Initramfs generator, Network

**Edit button jump-back flow (main.py):**
- `ReviewScreen.__init__` accepts `on_jump` callback
- `on_jump(stage_index)` calls `InstallerWindow._jump_to_stage()`
- `_jump_to_stage()` sets `_return_to_review = True`, clears the target stage
  card, and slides back to it
- `_advance()` checks `_return_to_review` — if set and current stage < Review,
  clears the flag, destroys the stale Review card, and jumps straight back to
  Review instead of stepping forward one at a time

---

## Complete Screen (Stage 15)

- File: `installer/ui/complete.py`
- Three-phase screen: ready → running → done (same pattern as install.py)
- 7 post-install steps run in a background thread:
  1. locale — locale-gen + locale.conf
  2. vconsole — vconsole.conf (keyboard layout)
  3. timezone — /etc/localtime symlink + hwclock --systohc
  4. initramfs — mkinitcpio -P or dracut --force (reads state.initramfs_generator)
     - mkinitcpio: injects encrypt hook first if LUKS+UKI, then mkinitcpio -P
     - dracut: runs dracut --force (auto-detects hardware, no hook config needed)
  5. bootloader — GRUB / systemd-boot / rEFInd / EFIStub / UKI install
  6. services — systemctl enable for NetworkManager, timesyncd, display manager
  7. unmount — umount -R /mnt
- Step label for initramfs is dynamic — shows actual generator command at runtime
- Done page: dry run → "Close" button; real install → "🔁 Reboot Now" button
  (calls `systemctl reboot` or falls back to `subprocess.run(["reboot"])`)
- Back button disabled — no going back once post-install config starts
- Retry button appears on step failure (resumes from failed step)

---

## runner.py API
```python
from installer.backend.runner import run_cmd, run_chroot, run_script

ok, out = run_cmd(["mkfs.ext4", "/dev/sda2"], state, "Format root")
ok, out = run_chroot(["locale-gen"], state, "Generate locales")
ok, out = run_script("echo foo > /mnt/bar", state, "Write bar")
```
Dry-run: logs command, returns (True, "[dry run] ...") without executing.

---

## pacstrap.py — 9 Install Steps

| Step       | What it does                                        |
|------------|-----------------------------------------------------|
| partition  | sgdisk/parted — create partition table              |
| format     | mkfs.* for each partition                           |
| luks       | cryptsetup luksFormat + open (skipped if no LUKS)   |
| mount      | mount all partitions under /mnt                     |
| mirrorlist | write mirrorlist to /mnt/etc/pacman.d/mirrorlist    |
| pacstrap   | pacstrap -K /mnt <packages> (30 min timeout)        |
| fstab      | genfstab -U >> /mnt/etc/fstab                       |
| hostname   | write /etc/hostname and /etc/hosts                  |
| users      | useradd + chpasswd + sudoers for each user          |

---

## CSS Notes

- No `text-transform` or `line-height` in GTK CSS
- Progress bar color: use `override_background_color()` in Python, not CSS classes
- TreeView selection: `treeview:selected` (GTK3) NOT `treeview row:selected` (GTK4)
- Disk cards need `.disk-card` and `.disk-card-selected` explicitly in CSS

Key classes: `.card`, `.level-card`, `.level-card.selected`, `.disk-card`,
`.disk-card-selected`, `.info-panel`, `.screen-title`, `.nav-btn`, `.nav-btn-next`,
`.action-button`, `.section-heading`, `.detail-key`, `.detail-value`,
`.status-ok`, `.status-error`, `.error-label`, `.passphrase-weak/fair/good/strong`,
`.dry-run-banner`, `.dry-run-text`, `.wiki-expander`, `.wiki-frame-title`,
`.wiki-link-button`

---

## Bootloader Options (Stage 14)

| Bootloader   | Beginner | Intermediate | Advanced |
|--------------|----------|--------------|----------|
| GRUB         | ✅        | ✅            | ✅        |
| systemd-boot | ✅        | ✅            | ✅        |
| rEFInd       | ❌        | ✅            | ✅        |
| EFIStub      | ❌        | ❌            | ✅        |
| UKI          | ❌        | ❌            | ✅        |

- Cards rebuild live when experience level changes (`on_experience_changed()`)
- BIOS mode: only GRUB allowed; Next is blocked for any other choice
- UKI + LUKS: shows decrypt hook warning; sets `bootloader_uki_needs_decrypt = True`

---

## arch-installer Launcher Script

The launcher script auto-installs GTK dependencies and expands cowspace before
launching. It is a fallback for running on the stock Arch ISO without a custom build.

Key things the launcher does:
- Checks for root, exits cleanly if not
- Checks it's running on Arch Linux
- Expands cowspace to 2G on live ISO before installing packages
- Detects and installs only missing dependencies via pacman
- Verifies `gi` is importable before launching
- Changes to repo directory so module paths are correct

---

## Custom ISO — archiso Profile

**Status:** ✅ Profile complete. Boot-tested in VM — installer launches automatically.

**Location:** `iso/` directory in repo root.

**Goal:** A custom Arch ISO that boots directly into the GTK installer with all
dependencies pre-installed. No manual pacman installs, no cowspace hacks, no
Python version mismatches. Boot → installer starts automatically.

### Autostart mechanism (implemented: Option A)
```
systemd multi-user.target
    └── arch-installer.service       (iso/airootfs/etc/systemd/system/)
            └── arch-installer-session   (iso/airootfs/usr/local/bin/)
                    ├── cleans up stale X locks
                    ├── sets GTK_THEME=Adwaita:dark
                    ├── starts Xorg :0 on tty1
                    ├── waits up to 20s for /tmp/.X11-unix/X0 socket
                    ├── sets background + mouse cursor via xsetroot
                    └── python3 -m installer.main  (from /opt/arch-installer/)
```
On clean exit (reboot triggered by installer): service exits normally.
On crash: systemd restarts after 3 seconds.
getty@tty1.service is masked via /dev/null symlink in airootfs.

### Critical archiso lessons learned (session 15)
- `customize_airootfs.sh` is DEPRECATED in current archiso — not called automatically
- Service enablement must use symlinks directly in `airootfs/etc/systemd/system/multi-user.target.wants/`
- Masking services must use `/dev/null` symlinks in `airootfs/etc/systemd/system/`
- `systemd-firstboot` is suppressed by placing `locale.conf`, `hostname`, `vconsole.conf`,
  and `localtime` symlink directly in `airootfs/etc/` — firstboot skips if these exist
- `mkinitcpio.conf.d/archiso.conf` is REQUIRED — without it initramfs has no archiso hooks
  and boot fails with "Failed to start Switch Root"
- `xdpyinfo` not needed — use `[[ -e /tmp/.X11-unix/X0 ]]` to detect Xorg readiness
- `GTK_THEME=Adwaita:dark` must be exported or text colors are invisible (white on white)
- `xorg-xsetroot` must be in packages for cursor and background color
- efiboot entries must use `%INSTALL_DIR%` and `%ARCH%` variables, not hardcoded paths
- `archisosearchuuid` not `archisodevice=UUID=` in boot entry options
- Work directory MUST be on local filesystem — NFS/bind mount causes `realpath` errors
- `networkmanager` package name is all lowercase — `NetworkManager` causes pacstrap failure

### Build instructions
```bash
# One-time: install archiso on your Arch build machine
sudo pacman -S archiso

# Build — work dir must be local, output can be on NAS
sudo mkarchiso -v \
  -w /tmp/archiso-work \
  -o /home/ronb/nas_data/Git_Projects/arch-installer/iso/out \
  /home/ronb/nas_data/Git_Projects/arch-installer/iso

# Clean rebuild
sudo rm -rf /tmp/archiso-work
sudo mkarchiso -v \
  -w /tmp/archiso-work \
  -o /home/ronb/nas_data/Git_Projects/arch-installer/iso/out \
  /home/ronb/nas_data/Git_Projects/arch-installer/iso
```

Output ISO: `iso/out/arch-installer-YYYY.MM-x86_64.iso`

### Required airootfs static files (prevent systemd-firstboot)
These files must exist in `iso/airootfs/etc/` before building:
- `locale.conf` → `LANG=en_US.UTF-8`
- `hostname` → `arch-installer`
- `vconsole.conf` → `KEYMAP=us`
- `localtime` → symlink to `/usr/share/zoneinfo/UTC`
- `shadow` → copied from releng profile (passwordless root)
- `mkinitcpio.conf.d/archiso.conf` → archiso initramfs hooks (CRITICAL)

### Required airootfs symlinks
```
iso/airootfs/etc/systemd/system/
├── multi-user.target.wants/
│   └── arch-installer.service -> /etc/systemd/system/arch-installer.service
├── getty@tty1.service -> /dev/null          (masked)
└── systemd-firstboot.service -> /dev/null   (masked)
```

### Key ISO files

| File | Purpose |
|------|---------|
| `iso/profiledef.sh` | ISO metadata, bootmodes (BIOS+UEFI), squashfs compression, file permissions |
| `iso/packages.x86_64` | All packages baked in: Python, GTK3, WebKit2GTK, Xorg, fonts, disk tools |
| `iso/pacman.conf` | Pacman config used during ISO build |
| `iso/airootfs/etc/mkinitcpio.conf.d/archiso.conf` | CRITICAL — archiso hooks for initramfs |
| `iso/airootfs/etc/systemd/system/arch-installer.service` | Systemd unit that starts the installer session |
| `iso/airootfs/usr/local/bin/arch-installer-session` | Session script: cleans locks, sets GTK theme, starts X, launches installer |
| `iso/airootfs/etc/X11/xorg.conf.d/10-arch-installer.conf` | Minimal Xorg config |
| `iso/efiboot/loader/entries/arch-installer.conf` | UEFI boot entry (systemd-boot) |
| `iso/efiboot/loader/entries/arch-installer-debug.conf` | UEFI debug entry |
| `iso/syslinux/syslinux.cfg` | BIOS boot menu |

### Boot entries
- **Normal** — quiet boot, autostart installer
- **Debug** — `systemd.unit=multi-user.target`, drops to TTY for troubleshooting

### cow_spacesize
Both boot entries pass `cow_spacesize=2G` — overlayfs write layer.
Sufficient for downloading extra packages at runtime if needed.

### Troubleshooting the live ISO

| Symptom | Where to look |
|---------|---------------|
| Installer doesn't start | `journalctl -u arch-installer.service` |
| X fails to start | `/var/log/Xorg.0.log` |
| Session script errors | `/var/log/arch-installer-session.log` |
| Text invisible in installer | `GTK_THEME=Adwaita:dark` missing from session script |
| "Failed to start Switch Root" | `airootfs/etc/mkinitcpio.conf.d/archiso.conf` missing |
| "systemd-firstboot" intercepts | Static config files missing from `airootfs/etc/` |
| Build `realpath` error | Work dir is on NFS — use `/tmp/archiso-work` instead |
| Build fails (mount errors) | `sudo umount -R /tmp/archiso-work` then retry |

---

## Known Issues / Deferred

- [ ] LVM support
- [ ] Dual-boot / existing partition preservation
- [ ] Secure Boot key enrollment — deferred post-bootloader
- [ ] Full end-to-end install test — pacstrap downloads and installs successfully.
      Remaining known issues:
      - `partprobe` + sleep needed after sgdisk so kernel registers new partitions
        before format step runs — fix applied in session 16
      - Mirror reliability: kernel.org drops connections under load — use
        rackspace/osuosl/arizona mirrors instead
- [ ] Plymouth Y-axis flip animation — logo flips on Y axis using X-scale trick.
      Circle background removed from logo.png via pixel masking. Working in ISO.
- [ ] Installer icon not showing in window title bar — fixed in session 16 via
      absolute ASSETS_DIR path and GdkPixbuf loading in main.py
- [ ] NAS→ISO sync — airootfs/opt/arch-installer is a separate copy of the repo.
      build.sh now runs rsync before mkarchiso to keep them in sync automatically.

---

## Session Commit Log

| Session | Commit message                                                               |
|---------|------------------------------------------------------------------------------|
| 1       | chore: initial project scaffold                                              |
| 2       | feat(stage-0): welcome, experience level                                     |
| 2       | chore: restructure into installer/ package                                   |
| 3       | feat(stage-1): network setup, wiki viewer                                    |
| 4       | feat(stages-2-4): keyboard, locale, disk selection                           |
| 4       | docs: update CLAUDE.md and README.md                                         |
| 5       | feat(stages-5-6): partitions, filesystem + LUKS                              |
| 5       | docs: update CLAUDE.md and README.md                                         |
| 6       | feat(stage-7): mirror selection with reflector                               |
| 6       | fix(mirrors): checkbox pre-selection, visibility timing                       |
| 6       | docs: update CLAUDE.md and README.md                                         |
| 7       | feat(stage-8): package selection, DE/WM picker                               |
| 7       | feat(stages-9-12): base install, dry-run, runner.py                          |
| 7       | fix(style): disk-card CSS, treeview selection, dry-run banner                |
| 7       | docs: update CLAUDE.md and README.md                                         |
| 8       | feat(stage-10): timezone with live clock                                     |
| 8       | feat(stage-11): system config — hostname, root password, NTP                 |
| 8       | fix: password strength colors, NTP checkbox visibility                       |
| 8       | docs: update CLAUDE.md and README.md                                         |
| 9       | refactor: reorder stages — all choices before pacstrap                       |
| 9       | feat(stage-11): user setup — username, password, sudo, shell, groups         |
| 9       | fix(filesystem): visibility timing bug on beginner level                     |
| 9       | fix(install): hostname + users in summary and install log                    |
| 9       | docs: update CLAUDE.md and README.md                                         |
| 10      | feat(stage-13): bootloader selection screen                                  |
| 10      | fix(ui): wiki links collapsible expander in hints panel                      |
| 10      | fix(network): move wiki links to panel, remove inline widget                 |
| 10      | docs: update CLAUDE.md and README.md                                         |
| 11      | feat(stages-12-15): review, complete/reboot; fix stage order; multi-select DE|
| 12      | feat(privilege): root check + arch-installer launcher script                 |
| 12      | feat(stage-10): initramfs generator choice — mkinitcpio/dracut (Advanced)    |
| 12      | feat(complete): branch initramfs step on state.initramfs_generator           |
| 12      | docs: update CLAUDE.md and README.md                                         |
| 13      | fix(launcher): auto-install GTK deps and expand cowspace on live ISO         |
| 13      | chore: move repo from ~/arch-installer to NAS                                |
| 13      | docs: update CLAUDE.md — custom ISO plan, Python version issue, next phase   |
| 14      | feat(iso): archiso profile — build.sh, profiledef, packages, autostart service|
| 14      | fix(iso): correct efiboot entry paths to use %INSTALL_DIR%/%ARCH% variables  |
| 14      | docs: update CLAUDE.md — Plymouth splash deferred, ISO boot entry fix noted  |
| 15      | fix(iso): add mkinitcpio.conf.d/archiso.conf — fixes "Failed to start Switch Root"|
| 15      | fix(iso): replace customize_airootfs.sh with direct airootfs symlinks        |
| 15      | fix(iso): add static locale/hostname/vconsole/localtime to suppress firstboot |
| 15      | fix(iso): session script — socket-based X check, GTK_THEME, stale lock cleanup|
| 15      | fix(iso): packages — add xorg-xsetroot, fonts, xorg-xset, xf86-input-libinput|
| 15      | fix(iso): bake default mirrorlist into airootfs                              |
| 15      | fix(state): networkmanager package name lowercase                             |
| 15      | fix(pacstrap): run_chroot calls use keyword args — fixes user creation chroot |
| 15      | feat(install): Begin button fixed outside scroll area                        |
| 15      | feat(install): live status ticker during pacstrap using run_cmd_streaming    |
| 15      | docs: update CLAUDE.md — all session 15 ISO lessons, troubleshooting table   |
| 16      | fix(iso): profiledef.sh — remove declare -A from file_permissions            |
| 16      | fix(iso): NetworkManager-wait-online dependency in arch-installer.service    |
| 16      | fix(iso): Xorg -quiet flag — suppress console output during X startup        |
| 16      | fix(iso): add partprobe + sleep after sgdisk — kernel partition registration |
| 16      | fix(main): icon loading via GdkPixbuf with absolute ASSETS_DIR path          |
| 16      | fix(main): dry-run banner now dynamic — hides when toggle turns off dry_run  |
| 16      | feat(welcome): dry_run toggle switch with live warning box                   |
| 16      | feat(iso): Plymouth boot splash — Y-axis flip animation, pulsing cyan glow   |
| 16      | feat(iso): build.sh — rsync installer into airootfs before mkarchiso         |
| 16      | feat(iso): generate_glow.py — generates Plymouth glow.png asset              |
| 16      | fix(iso): Plymouth logo — circle background removed, just the Arch "A"       |
| 16      | docs: update CLAUDE.md and README.md — session 16 complete                   |
