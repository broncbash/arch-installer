"""
installer/backend/pacstrap.py
------------------------------
Backend logic for Stage 9 — Base System Install.

Handles the full install sequence:
  1. Partition the disk (parted/sgdisk)
  2. Format filesystems (mkfs.*)
  3. Set up LUKS encryption if requested
  4. Mount partitions
  5. Write mirrorlist
  6. pacstrap base system
  7. genfstab

All operations go through runner.run_cmd() so dry_run mode is
respected automatically — nothing touches the disk in dry_run mode.

The pacstrap step uses run_cmd_streaming() so live output is fed
to the UI ticker callback as packages download and install.
"""

import logging
import os

from installer.backend.runner import run_cmd, run_chroot, run_script, run_cmd_streaming

log = logging.getLogger(__name__)

MOUNTPOINT = "/mnt"


# ── Step definitions ──────────────────────────────────────────────────────────
# Each step has an id and label.
# The install screen iterates these in order, updating the UI between each.

INSTALL_STEPS = [
    ("partition",   "Partition disk"),
    ("format",      "Format filesystems"),
    ("luks",        "Set up encryption"),
    ("mount",       "Mount partitions"),
    ("mirrorlist",  "Write mirrorlist"),
    ("pacstrap",    "Install base system  (this takes a while)"),
    ("fstab",       "Generate fstab"),
    ("hostname",    "Set hostname"),
    ("users",       "Create user accounts"),
]


def run_step(step_id: str, state, ticker_cb=None) -> tuple:
    """
    Execute a single install step.

    Args:
        step_id:   One of the step ids from INSTALL_STEPS
        state:     InstallState
        ticker_cb: Optional callable(str) passed to streaming steps
                   to update the UI live status ticker

    Returns:
        (success: bool, output: str)
    """
    fn = {
        "partition":  _step_partition,
        "format":     _step_format,
        "luks":       _step_luks,
        "mount":      _step_mount,
        "mirrorlist": _step_mirrorlist,
        "pacstrap":   _step_pacstrap,
        "fstab":      _step_fstab,
        "hostname":   _step_hostname,
        "users":      _step_users,
    }.get(step_id)

    if fn is None:
        return False, f"Unknown step: {step_id}"

    # Skip LUKS step if no encryption was requested
    if step_id == "luks" and not state.luks_passphrase:
        return True, "No encryption requested — skipping."

    try:
        # Pass ticker_cb to steps that support it (pacstrap)
        if step_id == "pacstrap":
            return fn(state, ticker_cb=ticker_cb)
        return fn(state)
    except Exception as exc:
        msg = f"Unexpected error in step '{step_id}': {exc}"
        log.error(msg, exc_info=True)
        state.add_log(f"ERROR: {msg}")
        return False, msg


# ── Step implementations ──────────────────────────────────────────────────────

def _step_partition(state) -> tuple:
    """Create partition table and partitions on the target disk."""
    disk = state.target_disk
    if not disk:
        return False, "No target disk selected."

    logs = []

    if state.partition_table == "gpt":
        ok, out = run_cmd(
            ["sgdisk", "--zap-all", disk],
            state, "Wipe existing partition table"
        )
        if not ok:
            return False, out
        logs.append(out)

        # Create partitions from state.partitions
        for i, p in enumerate(state.partitions, start=1):
            if p.mountpoint in ("/boot", "/boot/efi"):
                type_code = "ef00"  # EFI System Partition
            elif p.filesystem == "swap":
                type_code = "8200"  # Linux swap
            else:
                type_code = "8300"  # Linux filesystem

            size_arg = (f"+{p.size_mb}M" if p.size_mb > 0 else "0")
            ok, out = run_cmd(
                ["sgdisk", "-n", f"{i}:0:{size_arg}",
                 "-t", f"{i}:{type_code}", disk],
                state, f"Create partition {i} ({p.mountpoint})"
            )
            if not ok:
                return False, out
            logs.append(out)

    else:  # MBR
        ok, out = run_cmd(
            ["parted", "-s", disk, "mklabel", "msdos"],
            state, "Create MBR partition table"
        )
        if not ok:
            return False, out
        logs.append(out)

        start_mb = 1
        for i, p in enumerate(state.partitions, start=1):
            end_mb = (start_mb + p.size_mb) if p.size_mb > 0 else -1
            end_arg = f"{end_mb}MiB" if end_mb > 0 else "100%"
            fs_type = "linux-swap" if p.filesystem == "swap" else "ext2"
            ok, out = run_cmd(
                ["parted", "-s", disk, "mkpart", "primary",
                 fs_type, f"{start_mb}MiB", end_arg],
                state, f"Create partition {i} ({p.mountpoint})"
            )
            if not ok:
                return False, out
            logs.append(out)
            if p.size_mb > 0:
                start_mb += p.size_mb

    # Update partition device paths in state
    _assign_partition_devices(state)

    return True, "\n".join(logs)


def _assign_partition_devices(state):
    """Fill in partition device paths based on disk name and index."""
    disk = state.target_disk
    # NVMe disks use p1, p2 notation; others use 1, 2
    sep = "p" if "nvme" in disk or "mmcblk" in disk else ""
    for i, p in enumerate(state.partitions, start=1):
        p.device = f"{disk}{sep}{i}"
    # Also record EFI partition in state
    for p in state.partitions:
        if p.mountpoint in ("/boot", "/boot/efi"):
            state.efi_partition = p.device
            break


def _step_format(state) -> tuple:
    """Format each partition with the appropriate filesystem."""
    logs = []
    for p in state.partitions:
        if p.encrypt:
            # Encrypted partitions are formatted after LUKS is opened
            continue

        ok, out = _format_partition(p, state)
        if not ok:
            return False, out
        logs.append(out)

    return True, "\n".join(logs)


def _format_partition(p, state) -> tuple:
    """Format a single partition."""
    if p.filesystem == "vfat":
        return run_cmd(
            ["mkfs.fat", "-F32", "-n", "EFI", p.device],
            state, f"Format {p.device} as FAT32 (EFI)"
        )
    elif p.filesystem == "ext4":
        return run_cmd(
            ["mkfs.ext4", "-L", _label(p), p.device],
            state, f"Format {p.device} as ext4"
        )
    elif p.filesystem == "btrfs":
        return run_cmd(
            ["mkfs.btrfs", "-L", _label(p), "-f", p.device],
            state, f"Format {p.device} as btrfs"
        )
    elif p.filesystem == "xfs":
        return run_cmd(
            ["mkfs.xfs", "-L", _label(p), "-f", p.device],
            state, f"Format {p.device} as XFS"
        )
    elif p.filesystem == "f2fs":
        return run_cmd(
            ["mkfs.f2fs", "-l", _label(p), "-f", p.device],
            state, f"Format {p.device} as F2FS"
        )
    elif p.filesystem == "swap":
        ok, out = run_cmd(
            ["mkswap", "-L", "swap", p.device],
            state, f"Create swap on {p.device}"
        )
        if not ok:
            return False, out
        return run_cmd(
            ["swapon", p.device],
            state, f"Enable swap on {p.device}"
        )
    else:
        return False, f"Unknown filesystem: {p.filesystem}"


def _label(p) -> str:
    """Return a filesystem label for a partition."""
    if p.label:
        return p.label
    return {
        "/":          "root",
        "/boot":      "boot",
        "/boot/efi":  "EFI",
        "/home":      "home",
        "swap":       "swap",
    }.get(p.mountpoint, "arch")


def _step_luks(state) -> tuple:
    """Set up LUKS encryption on partitions that have encrypt=True."""
    logs = []
    for p in state.partitions:
        if not p.encrypt:
            continue

        safe_pass = state.luks_passphrase.replace("'", "'\\''")
        ok, out = run_cmd(
            ["bash", "-c",
             f"echo -n '{safe_pass}' | cryptsetup luksFormat "
             f"--type luks2 --batch-mode {p.device}"],
            state, f"LUKS format {p.device}"
        )
        if not ok:
            return False, out
        logs.append(out)

        # Open the LUKS container
        mapper_name = f"crypt_{p.mountpoint.strip('/').replace('/', '_') or 'root'}"
        ok, out = run_cmd(
            ["bash", "-c",
             f"echo -n '{state.luks_passphrase}' | "
             f"cryptsetup open {p.device} {mapper_name}"],
            state, f"Open LUKS container as /dev/mapper/{mapper_name}"
        )
        if not ok:
            return False, out
        logs.append(out)

        # Update the partition device to point to the mapper
        p.device = f"/dev/mapper/{mapper_name}"

        # Now format the opened container
        ok, out = _format_partition(p, state)
        if not ok:
            return False, out
        logs.append(out)

    return True, "\n".join(logs)


def _step_mount(state) -> tuple:
    """Mount all partitions under /mnt in the correct order."""
    logs = []

    # Sort: root first, then by mountpoint depth (shorter = higher)
    def mount_order(p):
        if p.mountpoint == "/":
            return 0
        return p.mountpoint.count("/")

    sorted_parts = sorted(
        [p for p in state.partitions if p.filesystem != "swap"],
        key=mount_order
    )

    for p in sorted_parts:
        target = f"{MOUNTPOINT}{p.mountpoint}"

        ok, out = run_cmd(
            ["mkdir", "-p", target],
            state, f"Create mountpoint {target}"
        )
        if not ok:
            return False, out

        if p.filesystem == "btrfs" and p.mountpoint == "/" and state.btrfs_subvolumes:
            ok, out = _mount_btrfs_subvolumes(p, state)
            if not ok:
                return False, out
            logs.append(out)
            continue

        ok, out = run_cmd(
            ["mount", p.device, target],
            state, f"Mount {p.device} → {target}"
        )
        if not ok:
            return False, out
        logs.append(out)

    return True, "\n".join(logs)


def _mount_btrfs_subvolumes(p, state) -> tuple:
    """Create and mount standard btrfs subvolumes: @, @home, @snapshots."""
    logs = []

    ok, out = run_cmd(
        ["mount", p.device, "/mnt"],
        state, "Mount btrfs root temporarily"
    )
    if not ok:
        return False, out

    for subvol in ["@", "@home", "@snapshots"]:
        ok, out = run_cmd(
            ["btrfs", "subvolume", "create", f"/mnt/{subvol}"],
            state, f"Create btrfs subvolume {subvol}"
        )
        if not ok:
            return False, out
        logs.append(out)

    ok, out = run_cmd(["umount", "/mnt"], state, "Unmount btrfs temp mount")
    if not ok:
        return False, out

    mnt_opts = "noatime,compress=zstd,space_cache=v2,subvol=@"
    ok, out = run_cmd(
        ["mount", "-o", mnt_opts, p.device, "/mnt"],
        state, "Mount @ subvolume as root"
    )
    if not ok:
        return False, out
    logs.append(out)

    ok, out = run_cmd(["mkdir", "-p", "/mnt/home"], state, "Create /mnt/home")
    if not ok:
        return False, out

    home_opts = "noatime,compress=zstd,space_cache=v2,subvol=@home"
    ok, out = run_cmd(
        ["mount", "-o", home_opts, p.device, "/mnt/home"],
        state, "Mount @home subvolume"
    )
    if not ok:
        return False, out
    logs.append(out)

    return True, "\n".join(logs)


def _step_mirrorlist(state) -> tuple:
    """Write the mirrorlist to /mnt/etc/pacman.d/mirrorlist."""
    if not state.mirrorlist:
        return False, "No mirrorlist available. Go back to the Mirror Selection stage."

    if state.dry_run:
        return run_cmd(
            ["tee", f"{MOUNTPOINT}/etc/pacman.d/mirrorlist"],
            state, "Write mirrorlist"
        )

    try:
        os.makedirs(f"{MOUNTPOINT}/etc/pacman.d", exist_ok=True)
        with open(f"{MOUNTPOINT}/etc/pacman.d/mirrorlist", "w") as f:
            f.write(state.mirrorlist)
        state.add_log(f"Wrote mirrorlist ({len(state.mirrorlist)} bytes)")
        return True, "Mirrorlist written."
    except OSError as e:
        return False, f"Failed to write mirrorlist: {e}"


def _step_pacstrap(state, ticker_cb=None) -> tuple:
    """Run pacstrap to install the base system with live streaming output."""
    packages = build_package_list(state)

    return run_cmd_streaming(
        ["pacstrap", "-K", MOUNTPOINT] + packages,
        state,
        description=f"pacstrap {len(packages)} packages",
        ticker_cb=ticker_cb,
        timeout=1800,  # 30 min — large installs take time
    )


def _step_fstab(state) -> tuple:
    """Generate /etc/fstab using genfstab."""
    if state.dry_run:
        return run_cmd(
            ["genfstab", "-U", MOUNTPOINT],
            state, "Generate fstab"
        )

    ok, out = run_cmd(
        ["bash", "-c", f"genfstab -U {MOUNTPOINT} >> {MOUNTPOINT}/etc/fstab"],
        state, "Generate and write fstab"
    )
    return ok, out


def _step_hostname(state) -> tuple:
    """Write /etc/hostname and /etc/hosts inside the chroot."""
    logs = []
    hostname = state.hostname or "archlinux"

    if state.dry_run:
        ok, out = run_cmd(
            ["bash", "-c", f"echo '{hostname}' > {MOUNTPOINT}/etc/hostname"],
            state, f"Write /etc/hostname ({hostname})"
        )
    else:
        try:
            with open(f"{MOUNTPOINT}/etc/hostname", "w") as f:
                f.write(hostname + "\n")
            state.add_log(f"Wrote /etc/hostname: {hostname}")
            ok, out = True, f"Hostname set to: {hostname}"
        except OSError as e:
            return False, f"Failed to write /etc/hostname: {e}"
    if not ok:
        return False, out
    logs.append(out)

    hosts_content = (
        "127.0.0.1   localhost\n"
        "::1         localhost\n"
        f"127.0.1.1   {hostname}.localdomain  {hostname}\n"
    )
    if state.dry_run:
        ok, out = run_cmd(
            ["bash", "-c", f"cat > {MOUNTPOINT}/etc/hosts"],
            state, "Write /etc/hosts"
        )
    else:
        try:
            with open(f"{MOUNTPOINT}/etc/hosts", "w") as f:
                f.write(hosts_content)
            state.add_log("Wrote /etc/hosts")
            ok, out = True, "Wrote /etc/hosts"
        except OSError as e:
            return False, f"Failed to write /etc/hosts: {e}"
    if not ok:
        return False, out
    logs.append(out)

    return True, "\n".join(logs)


def _step_users(state) -> tuple:
    """Set root password and create user accounts inside the chroot."""
    logs = []

    if state.root_password:
        safe = state.root_password.replace("'", "'\\''")
        ok, out = run_cmd(
            ["bash", "-c",
             f"echo 'root:{safe}' | arch-chroot {MOUNTPOINT} chpasswd"],
            state, "Set root password"
        )
        if not ok:
            return False, out
        logs.append(out)

    for user in state.users:
        uname = user["username"]
        pw    = user["password"]
        shell = user.get("shell", "/bin/bash")
        sudo  = user.get("sudo", True)

        group_list = []
        if sudo:
            group_list.append("wheel")
        extra = user.get("groups", [])
        group_list.extend(extra)
        if not group_list:
            group_list.append("users")
        groups_str = ",".join(group_list)

        ok, out = run_chroot(
            ["useradd", "-m", "-G", groups_str, "-s", shell, uname],
            state,
            mountpoint=MOUNTPOINT,
            description=f"Create user: {uname} (groups: {groups_str})"
        )
        if not ok:
            return False, out
        logs.append(out)

        safe_pw = pw.replace("'", "'\\''")
        ok, out = run_cmd(
            ["bash", "-c",
             f"echo '{uname}:{safe_pw}' | arch-chroot {MOUNTPOINT} chpasswd"],
            state, f"Set password for {uname}"
        )
        if not ok:
            return False, out
        logs.append(out)

        if sudo:
            ok, out = run_chroot(
                ["sed", "-i",
                 "s/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/",
                 "/etc/sudoers"],
                state,
                mountpoint=MOUNTPOINT,
                description="Enable wheel group in sudoers"
            )
            if not ok:
                return False, out
            logs.append(out)

        logs.append(f"Created user: {uname} (shell={shell}, sudo={sudo})")

    return True, "\n".join(logs)


def build_package_list(state) -> list:
    """Return the full deduplicated list of packages that will be installed."""
    packages = list(state.base_packages)

    # networkmanager — all lowercase, this is the correct Arch package name
    if state.network_manager and state.network_manager not in packages:
        packages.append(state.network_manager)

    packages.extend(state.extra_packages)

    if state.root_filesystem == "btrfs":
        packages.append("btrfs-progs")
    elif state.root_filesystem == "xfs":
        packages.append("xfsprogs")
    elif state.root_filesystem == "f2fs":
        packages.append("f2fs-tools")

    if state.luks_passphrase:
        packages.append("cryptsetup")

    seen = set()
    result = []
    for p in packages:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result
