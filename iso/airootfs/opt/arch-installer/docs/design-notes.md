# Design Notes — Arch Installer

## Core Principles

1. **Nothing writes to disk until the Review screen is confirmed.**
   All selections are held in `InstallState`. This means the user can freely
   navigate back and change options at any point without side effects.

2. **Experience levels gate complexity, not capability.**
   A beginner can still install with Btrfs or LUKS — they just won't be shown
   those options by default. The info panel explains what they're missing and
   how to access it by switching level.

3. **Every long-running operation is threaded.**
   pacstrap, reflector, mkfs, etc. all run in background threads.
   GTK updates only happen via `GLib.idle_add()` to stay on the main thread.

4. **Every backend function returns `(bool, str)`.**
   `(True, "")` = success. `(False, "reason")` = failure with a human-readable
   message. No backend function raises exceptions into the UI layer.

5. **Full logging from day one.**
   Everything goes to `/tmp/arch-installer.log`. This is invaluable for
   diagnosing failures on real hardware.

---

## Partitioning Strategy

This is the most complex part of the installer. The plan:

### Auto mode (Beginner/Intermediate)
Offer pre-set layouts the user picks from:
- **Simple** — one root partition + EFI (no swap)
- **Recommended** — EFI + swap + root
- **With /home** — EFI + swap + root + /home

### Manual mode (Advanced)
Show a partition table editor. User can:
- Add/delete/resize partitions
- Set filesystem and mountpoint per partition
- Enable LUKS on any partition
- Set Btrfs subvolume layout

### Tools used
- `lsblk` — enumerate disks
- `sgdisk` — GPT operations
- `fdisk` / `parted` — MBR operations
- `mkfs.ext4`, `mkfs.btrfs`, `mkfs.xfs`, `mkswap`, `mkfs.vfat` — format
- `cryptsetup luksFormat` + `cryptsetup open` — encryption
- `mount` / `umount` — mount management
- `genfstab` — fstab generation

---

## Bootloader Decision Tree

```
Is boot mode UEFI?
├── Yes → Offer: systemd-boot (default), GRUB, rEFInd
│         Beginner default: systemd-boot (simpler, built-in)
│         GRUB: needed for LUKS full-disk encryption on some setups
└── No  → GRUB only (BIOS/MBR)
```

---

## Desktop Environment Package Groups

| DE/WM    | Packages                                    | Display Manager |
|----------|---------------------------------------------|-----------------|
| GNOME    | gnome gnome-extra                           | gdm             |
| KDE      | plasma kde-applications                     | sddm            |
| XFCE     | xfce4 xfce4-goodies                         | lightdm         |
| MATE     | mate mate-extra                             | lightdm         |
| Cinnamon | cinnamon                                    | lightdm         |
| i3       | i3-wm i3status i3lock dmenu xterm           | None            |
| Sway     | sway swaybar swaybg swaylock waybar         | None            |
| None     | (base only)                                 | None            |

---

## mkinitcpio hooks for LUKS

When any partition is encrypted, add `encrypt` to HOOKS in mkinitcpio.conf:
```
HOOKS=(base udev autodetect modconf block encrypt filesystems keyboard fsck)
```
And add `cryptdevice=UUID=<uuid>:cryptroot root=/dev/mapper/cryptroot`
to the kernel command line.

---

## Session Continuity

See `CLAUDE.md` in the repo root. Paste its contents at the start of every
new Claude session to restore full project context instantly.
