"""
installer/dev_prefill.py
------------------------
Developer test helper — pre-fills InstallState with sensible defaults so
you can skip through all screens without manually entering anything.

USAGE:
  1. Set  DEV_AUTOFILL = True   in installer/state.py
  2. Run the installer normally
  3. All screens will be pre-populated; just click Next through each one

TO REMOVE when done testing:
  1. Set  DEV_AUTOFILL = False  in installer/state.py  (or delete the flag)
  2. Delete this file

The disk is set to /dev/sda — the typical first disk in a VirtualBox VM.
Change DEV_DISK below if your test VM uses a different device.
"""

from installer.state import InstallState, DiskPartition
from installer.backend.mirrors import FALLBACK_MIRRORLIST
from installer.backend.pacstrap import build_package_list
from installer.ui.partition import _build_auto_layout, get_disk_size_mb, suggest_swap_mb, get_ram_mb

# ── Tweak these to match your test VM ────────────────────────────────────────
DEV_DISK       = "/dev/vda"
DEV_BOOTLOADER = "refind"          # change to whichever bootloader you're testing
DEV_PASSWORD   = "testpass123"   # used for root, user, and LUKS (if enabled)
DEV_LUKS       = False           # set True to test LUKS installs
# ─────────────────────────────────────────────────────────────────────────────


def apply(state: InstallState) -> None:
    """
    Populate state with test defaults.
    Called from main.py before the window is shown.
    """

    # ── Experience level ──────────────────────────────────────────────────────
    state.experience_level = "beginner"

    # ── Network — mark as connected so the screen passes immediately ──────────
    state.network_ok        = True
    state.network_connected = True

    # ── Keyboard / Locale / Timezone ─────────────────────────────────────────
    state.keyboard_layout = "us"
    state.language        = "en_US"
    state.locale          = "en_US.UTF-8"
    state.timezone        = "America/New_York"

    # ── Disk ─────────────────────────────────────────────────────────────────
    state.target_disk      = DEV_DISK
    state.partition_table  = "gpt"
    state.partition_scheme = "auto"
    state.boot_mode        = "uefi"

    # ── Auto partition layout — use the same function partition.py uses ───────
    # This ensures state.partitions is populated before the filesystem screen
    # runs its validation, even if the partition screen auto-advances quickly.
    disk_mb  = get_disk_size_mb(DEV_DISK) if DEV_DISK else 20480
    ram_mb   = get_ram_mb()
    swap_mb  = suggest_swap_mb(ram_mb)

    state.partitions = _build_auto_layout(
        disk_mb   = disk_mb,
        boot_mode = "uefi",
        swap_type = "none",   # no swap for testing — keeps layout simple
        swap_mb   = 0,
    )

    # Assign device paths and record the EFI partition
    sep = "p" if "nvme" in DEV_DISK or "mmcblk" in DEV_DISK else ""
    for i, p in enumerate(state.partitions, start=1):
        p.device = f"{DEV_DISK}{sep}{i}"
        if DEV_LUKS and p.mountpoint in ("/", "/home"):
            p.encrypt = True
    for p in state.partitions:
        if p.mountpoint in ("/boot", "/boot/efi"):
            state.efi_partition = p.device
            break

    # ── Filesystem / Encryption ───────────────────────────────────────────────
    state.root_filesystem  = "ext4"
    state.luks_passphrase  = DEV_PASSWORD if DEV_LUKS else ""

    # ── Mirrors — use the bundled fallback so no fetch is needed ────────────
    state.mirror_countries = ["US"]
    state.mirrorlist       = FALLBACK_MIRRORLIST

    # ── Packages — base only, no DE ──────────────────────────────────────────
    state.desktop_environment = ""
    state.display_manager     = ""
    state.network_manager     = "networkmanager"
    state.extra_packages      = []

    # ── System config ─────────────────────────────────────────────────────────
    state.hostname             = "archtest"
    state.root_password        = DEV_PASSWORD
    state.enable_ntp           = True
    state.initramfs_generator  = "mkinitcpio"

    # ── User ─────────────────────────────────────────────────────────────────
    state.users = []
    state.add_user(
        username = "testuser",
        password = DEV_PASSWORD,
        sudo     = True,
        shell    = "/bin/bash",
    )

    # ── Bootloader ────────────────────────────────────────────────────────────
    state.bootloader                   = DEV_BOOTLOADER
    state.bootloader_uki               = (DEV_BOOTLOADER == "uki")
    state.bootloader_uki_needs_decrypt = (DEV_BOOTLOADER == "uki" and DEV_LUKS)
