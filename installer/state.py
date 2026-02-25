"""
installer/state.py
------------------
Single source of truth for all user selections during the install process.
This object is created once in main.py and passed to every screen.
Nothing is written to disk until the user confirms on the Review screen.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class DiskPartition:
    """Represents a single partition to be created or used."""
    device: str          # e.g. /dev/sda1
    mountpoint: str      # e.g. /, /boot, /home, swap
    filesystem: str      # e.g. ext4, btrfs, vfat, swap
    size_mb: int         # 0 = use remaining space
    encrypt: bool = False
    label: str = ""


@dataclass
class InstallState:
    """
    All installer selections live here.
    Screens read from and write to this object.
    Backend functions consume it during the actual install.
    """

    # ── Experience level ──────────────────────────────────────────────────────
    # 'beginner' | 'intermediate' | 'advanced'
    experience_level: str = "beginner"

    # ── Locale / keyboard ─────────────────────────────────────────────────────
    keyboard_layout: str = "us"      # console keymap, e.g. 'us', 'de', 'fr'
    language: str = "en_US"
    locale: str = "en_US.UTF-8"
    timezone: str = "UTC"

    # ── Network ───────────────────────────────────────────────────────────────
    network_ok: bool = False            # True once connectivity confirmed
    network_connected: bool = False     # alias kept in sync by NetworkScreen
    network_skipped: bool = False       # True if user clicked Skip
    network_interface_info: dict = field(default_factory=dict)

    # ── Disk / partitions ─────────────────────────────────────────────────────
    target_disk: str = ""            # e.g. /dev/sda
    partition_table: str = "gpt"     # 'gpt' | 'mbr'
    partition_scheme: str = "auto"   # 'auto' | 'manual'
    partitions: List[DiskPartition] = field(default_factory=list)
    swap_size_mb: int = 0            # 0 = no swap partition
    use_swap_file: bool = False
    luks_passphrase: str = ""        # only set if any partition has encrypt=True
    btrfs_subvolumes: bool = False   # create standard Btrfs subvolume layout

    # ── Filesystem ────────────────────────────────────────────────────────────
    root_filesystem: str = "ext4"    # 'ext4' | 'btrfs' | 'xfs' | 'f2fs'

    # ── Mirrors ───────────────────────────────────────────────────────────────
    mirror_countries: List[str] = field(default_factory=lambda: ["US"])
    mirrorlist: str = ""             # final /etc/pacman.d/mirrorlist content

    # ── Packages ──────────────────────────────────────────────────────────────
    # Always installed
    base_packages: List[str] = field(default_factory=lambda: [
        "base", "base-devel", "linux", "linux-firmware"
    ])
    # User-selected extras
    extra_packages: List[str] = field(default_factory=list)
    desktop_environment: str = ""    # 'gnome'|'kde'|'xfce'|'sway'|'' etc.
    display_manager: str = ""        # 'gdm'|'sddm'|'lightdm'|'' etc.
    network_manager: str = "NetworkManager"

    # ── System config ─────────────────────────────────────────────────────────
    hostname: str = "archlinux"
    root_password: str = ""

    # ── Users ─────────────────────────────────────────────────────────────────
    users: List[Dict] = field(default_factory=list)
    # Each user dict: {"username": str, "password": str, "sudo": bool, "shell": str}

    # ── Bootloader ────────────────────────────────────────────────────────────
    bootloader: str = "grub"         # 'grub' | 'systemd-boot' | 'refind'
    bootloader_uki: bool = False     # True if UKI bootloader selected (Stage 13)
    bootloader_uki_needs_decrypt: bool = False  # True if LUKS encryption enabled
    boot_mode: str = "uefi"          # 'uefi' | 'bios'  (auto-detected)
    efi_partition: str = ""          # e.g. /dev/sda1

    # ── Install progress tracking ─────────────────────────────────────────────
    install_log: List[str] = field(default_factory=list)
    current_stage: int = 0
    install_complete: bool = False

    # ── Runtime flags ─────────────────────────────────────────────────────────
    dry_run: bool = False            # If True, simulate all disk ops (for testing)

    def add_log(self, message: str):
        """Append a line to the install log."""
        self.install_log.append(message)

    def add_user(self, username: str, password: str, sudo: bool = True,
                 shell: str = "/bin/bash"):
        self.users.append({
            "username": username,
            "password": password,
            "sudo": sudo,
            "shell": shell,
        })

    def summary(self) -> str:
        """Return a human-readable summary of all selections (for Review screen)."""
        lines = [
            f"Experience Level : {self.experience_level}",
            f"Keyboard         : {self.keyboard_layout}",
            f"Locale           : {self.locale}",
            f"Timezone         : {self.timezone}",
            f"Target Disk      : {self.target_disk}",
            f"Partition Table  : {self.partition_table.upper()}",
            f"Partition Scheme : {self.partition_scheme}",
            f"Root Filesystem  : {self.root_filesystem}",
            f"Bootloader       : {self.bootloader}",
            f"Boot Mode        : {self.boot_mode.upper()}",
            f"Hostname         : {self.hostname}",
            f"Desktop          : {self.desktop_environment or 'None (base only)'}",
            f"Network Manager  : {self.network_manager}",
            f"Users            : {', '.join(u['username'] for u in self.users)}",
            f"Extra Packages   : {', '.join(self.extra_packages) or 'None'}",
        ]
        return "\n".join(lines)
