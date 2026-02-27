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
launching. However, the correct long-term solution is a custom ISO (see Next Phase
below) so this is only needed as a fallback.

Key things the launcher does:
- Checks for root, exits cleanly if not
- Checks it's running on Arch Linux
- Expands cowspace to 2G on live ISO before installing packages
- Detects and installs only missing dependencies via pacman
- Verifies `gi` is importable before launching
- Changes to repo directory so module paths are correct

---

## Known Issues / Deferred

- [ ] LVM support
- [ ] Dual-boot / existing partition preservation
- [ ] Secure Boot key enrollment — deferred post-bootloader
- [ ] VM smoke test with dry_run = False not yet completed — blocked by live ISO
      Python version mismatch (ISO ships Python 3.14, packages built for 3.13)
- [ ] Full end-to-end install test not yet performed

---

## Next Phase — Custom ISO with archiso

**Goal:** A custom Arch ISO that boots directly into the GTK installer with all
dependencies pre-installed. No manual pacman installs, no cowspace hacks, no
Python version mismatches. Boot and the installer starts automatically.

**Why:** The standard Arch live ISO is a moving target — Python version on the ISO
frequently mismatches the python-gobject package on the mirrors, making it
impossible to reliably install GTK deps at runtime. Baking everything into a
custom ISO solves this permanently.

**Plan:**
1. Install `archiso` on dev machine: `pacman -S archiso`
2. Copy the baseline profile: `cp -r /usr/share/archiso/configs/releng/ ~/arch-iso-profile`
3. Add deps to `packages.x86_64`:
   - python
   - python-gobject
   - python-cairo
   - gtk3
   - webkit2gtk
   - gobject-introspection
4. Copy installer repo into the ISO filesystem via `airootfs/`
5. Add a systemd service or getty autologin + xinit to autostart the installer as root on boot
6. Build: `mkarchiso -v -o ~/iso-out ~/arch-iso-profile`
7. Test in VM

**Autostart mechanism** (to be designed):
- Option A: systemd service that runs `./arch-installer` after graphical target
- Option B: getty autologin as root → `.bash_profile` launches installer
- Option C: `.desktop` autostart entry if a minimal WM is included

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
| 8       : docs: update CLAUDE.md and README.md                                         |
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
