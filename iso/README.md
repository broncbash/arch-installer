# arch-installer ISO profile

This directory is an [archiso](https://wiki.archlinux.org/title/Archiso) profile
that builds a custom Arch Linux live ISO with the GTK installer pre-installed and
auto-starting on boot.

## Directory layout

```
iso/
├── build.sh                        ← main build + test script (run as root)
├── profiledef.sh                   ← ISO metadata, bootmodes, compression
├── packages.x86_64                 ← packages baked into the ISO
├── pacman.conf                     ← pacman config used during build
├── airootfs/                       ← overlaid directly onto the ISO root fs
│   ├── etc/
│   │   ├── customize_airootfs.sh   ← runs in chroot at build time
│   │   ├── X11/xorg.conf.d/        ← minimal Xorg config
│   │   └── systemd/system/
│   │       └── arch-installer.service
│   ├── usr/local/bin/
│   │   ├── arch-installer-session  ← starts X + installer (called by service)
│   │   └── start-installer         ← thin shim
│   └── opt/arch-installer/         ← installer repo (copied in by build.sh)
├── efiboot/loader/                 ← systemd-boot UEFI config
│   ├── loader.conf
│   └── entries/
│       ├── arch-installer.conf
│       └── arch-installer-debug.conf
└── syslinux/
    └── syslinux.cfg                ← BIOS boot config
```

## Prerequisites

Build machine must be running **Arch Linux**. Install archiso:

```bash
sudo pacman -S archiso
# For VM testing:
sudo pacman -S qemu-desktop edk2-ovmf
```

## Building

The `iso/` directory must live inside the `arch-installer` repo root so that
`build.sh` can find the installer source at `../`.

```bash
# First build
sudo ./iso/build.sh

# Clean rebuild (highly recommended if build fails or output is missing)
sudo ./iso/build.sh --clean

# Build and immediately test in QEMU
sudo ./iso/build.sh --vm-test

# Build and copy to NFS share automatically
sudo NFS_OUTPUT_DIR=/mnt/nas/isos ./iso/build.sh
```

Output ISO lands in `iso/out/arch-installer-YYYY.MM.DD-x86_64.iso`.

> **Note on Build Cache**: `mkarchiso` uses a work directory (`iso/work/`) to
> cache build steps. If you modify files but don't see changes in the ISO, or
> if the build script says "Done!" immediately without creating a new file,
> you **must** use the `--clean` flag to clear the cache.

## How the autostart works

```
systemd multi-user.target
    └── arch-installer.service
            └── /usr/local/bin/arch-installer-session
                    ├── starts Xorg :0 on tty1
                    ├── waits for X to be ready
                    └── python3 -m installer.main
                            └── GTK installer window fills the screen
```

On a clean exit (installer calls `systemctl reboot`), the service exits normally.
On a crash, systemd restarts it after 3 seconds.

## Boot menu entries

| Entry | Description |
|---|---|
| `Arch Linux Installer` | Normal boot — quiet, starts installer |
| `Arch Linux Installer (debug)` | Verbose, drops to TTY instead of auto-starting |

## Troubleshooting

| Symptom | Check |
|---|---|
| X fails to start | `/var/log/Xorg.0.log` on the live system |
| Installer doesn't launch | `journalctl -u arch-installer.service` |
| Session script errors | `/var/log/arch-installer-session.log` |
| Build fails with mount errors | Run `sudo findmnt \| grep work` then `sudo umount -R iso/work` |
