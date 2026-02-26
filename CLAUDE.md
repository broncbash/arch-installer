# CLAUDE.md — Arch Installer Project Context
# Paste this file at the start of every Claude session to restore full context.
# Update this file at the end of every session before committing.

---

## Project Overview

A full-featured, GTK3-based graphical Arch Linux installer built from scratch in Python.
No Calamares. No archinstall. Completely original.

**GitLab repo:** https://gitlab.com/broncbash/arch-installer (private until public release)
**Local repo:**   ~/arch-installer

### Design Philosophy
- Follows Arch Wiki installation standards exactly
- Experience-level system: Beginner / Intermediate / Advanced
- Every screen has an info/hint panel and wiki links
- GTK3 + Python, dark GitHub-style theme
- Dry-run mode on by default — set dry_run = False in state.py for real installs
- This is a learning project — always provide complete files, never diffs/snippets

---

## Tech Stack

| Component   | Choice                  |
|-------------|-------------------------|
| Language    | Python 3                |
| GUI         | GTK3 (python-gobject)   |
| Wiki viewer | WebKit2GTK              |
| Privilege   | pkexec (polkit)         |
| Disk ops    | parted, sgdisk, mkfs.*  |
| Encryption  | cryptsetup (LUKS2)      |
| Install     | pacstrap                |
| VCS         | Git / GitLab (private)  |
| License     | GPLv3                   |

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
 8  Package Selection          ← DE/WM + extras chosen here
 9  Timezone
10  System Config / Hostname
11  User Setup                 ← shell adds zsh/fish to extra_packages
12  Base Install               ← pacstrap runs with complete package list
13  Bootloader                 ✅ complete
14  Review & Confirm           (planned)
15  Complete / Reboot          (planned)
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
| 12 | Base Install           | ✅ Complete | ui/install.py, backend/pacstrap.py       |
| 13 | Bootloader             | ✅ Complete | ui/bootloader.py                         |
| 14 | Review & Confirm       | 🔲 Planned  |                                          |
| 15 | Complete / Reboot      | 🔲 Planned  |                                          |

---

## File Structure

```
arch-installer/
├── CLAUDE.md
├── README.md
├── installer/
│   ├── main.py                 ← entry point, stage controller, dry-run banner
│   ├── state.py                ← global install state
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
│   │   ├── install.py          ← stage 12
│   │   └── bootloader.py       ← stage 13
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
- `experience_level`    — 'beginner'|'intermediate'|'advanced'
- `keyboard_layout`     — e.g. 'us'
- `locale`              — e.g. 'en_US.UTF-8'
- `timezone`            — e.g. 'America/Los_Angeles'
- `target_disk`         — e.g. '/dev/sda'
- `boot_mode`           — 'uefi'|'bios'
- `partition_table`     — 'gpt'|'mbr'
- `partition_scheme`    — 'auto'|'manual'
- `partitions`          — list of DiskPartition objects
- `root_filesystem`     — 'ext4'|'btrfs'|'xfs'|'f2fs'
- `btrfs_subvolumes`    — bool
- `luks_passphrase`     — empty = no encryption
- `mirrorlist`          — final mirrorlist content string
- `desktop_environment` — 'gnome'|'kde'|'xfce'|'sway'|'hyprland'|'niri'|'i3'|'bspwm'|''
- `display_manager`     — 'gdm'|'sddm'|'lightdm'|''
- `base_packages`       — ['base','base-devel','linux','linux-firmware']
- `extra_packages`      — selected extras + DE pkgs + shell if non-bash
- `hostname`            — e.g. 'my-arch-pc'
- `root_password`       — string
- `enable_ntp`          — bool, default True
- `users`               — list of user dicts (see below)
- `bootloader`          — 'grub'|'systemd-boot'|'refind'|'efistub'|'uki'
- `bootloader_uki`      — bool, True if UKI selected
- `bootloader_uki_needs_decrypt` — bool, True if UKI + LUKS enabled
- `dry_run`             — bool, default True

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

**Wiki links:**
- Define `WIKI_LINKS = [("Label", "https://..."), ...]` as a class variable.
- BaseScreen renders them automatically in a `Gtk.Expander` ("📖 Arch Wiki")
  in the hints panel — collapsed by default so hint text gets full height.
- NEVER build wiki link widgets manually in `build_content()`.
- `_open_wiki(url)` is provided by BaseScreen; override only if you need to
  pass extra context (e.g. NetworkScreen passes `connected=self._connected`).
  Override signature must be `_open_wiki(self, url: str)` — one argument.

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

## Bootloader Options (Stage 13)

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

## Known Issues / Deferred

- [ ] LVM support
- [ ] Dual-boot / existing partition preservation
- [ ] UKI: mkinitcpio vs dracut — backend not yet wired (Stage 13 UI complete)
- [ ] Secure Boot key enrollment — deferred post-bootloader
- [ ] pkexec privilege escalation not yet wired up

---

## Session Commit Log

| Session | Commit message                                                          |
|---------|-------------------------------------------------------------------------|
| 1       | chore: initial project scaffold                                         |
| 2       | feat(stage-0): welcome, experience level                                |
| 2       | chore: restructure into installer/ package                              |
| 3       | feat(stage-1): network setup, wiki viewer                               |
| 4       | feat(stages-2-4): keyboard, locale, disk selection                      |
| 4       | docs: update CLAUDE.md and README.md                                    |
| 5       | feat(stages-5-6): partitions, filesystem + LUKS                         |
| 5       | docs: update CLAUDE.md and README.md                                    |
| 6       | feat(stage-7): mirror selection with reflector                          |
| 6       | fix(mirrors): checkbox pre-selection, visibility timing                  |
| 6       | docs: update CLAUDE.md and README.md                                    |
| 7       | feat(stage-8): package selection, DE/WM picker                          |
| 7       | feat(stages-9-12): base install, dry-run, runner.py                     |
| 7       | fix(style): disk-card CSS, treeview selection, dry-run banner           |
| 7       | docs: update CLAUDE.md and README.md                                    |
| 8       | feat(stage-10): timezone with live clock                                |
| 8       | feat(stage-11): system config — hostname, root password, NTP            |
| 8       | fix: password strength colors, NTP checkbox visibility                  |
| 8       | docs: update CLAUDE.md and README.md                                    |
| 9       | refactor: reorder stages — all choices before pacstrap                  |
| 9       | feat(stage-11): user setup — username, password, sudo, shell, groups    |
| 9       | fix(filesystem): visibility timing bug on beginner level                |
| 9       | fix(install): hostname + users in summary and install log               |
| 9       | docs: update CLAUDE.md and README.md                                    |
| 10      | feat(stage-13): bootloader selection screen                             |
| 10      | fix(ui): wiki links collapsible expander in hints panel                 |
| 10      | fix(network): move wiki links to panel, remove inline widget            |
| 10      | docs: update CLAUDE.md and README.md                                    |

---

## Next Session: Stage 14 — Review & Confirm

- File: `installer/ui/review.py`
- Show a complete human-readable summary of every selection made
- Use `state.summary()` as a starting point but render it properly in the UI
- Group by category: Disk, System, Packages, Users, Bootloader
- A final "Begin Installation" / "Begin Dry Run" confirm button
- Consider a "Go back to stage X" quick-jump for each section
- Upload `main.py` and `state.py` at start of next session
