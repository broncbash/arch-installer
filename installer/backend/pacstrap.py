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
    ("keyring",     "Initialize package keyring"),
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
        "keyring":    _step_keyring,
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
        if step_id in ("pacstrap", "keyring"):
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

    # Tell the kernel to re-read the partition table before format step runs
    run_cmd(["partprobe", disk], state, "Re-read partition table")
    run_cmd(["sleep", "2"], state, "Wait for kernel to register partitions")
    run_cmd(["udevadm", "settle"], state, "Wait for udev to settle device nodes")

    return True, "\n".join(logs)


def _assign_partition_devices(state):
    """Fill in partition device paths based on disk name and index."""
    disk = state.target_disk
    # NVMe disks use p1, p2 notation; others use 1, 2
    sep = "p" if "nvme" in disk or "mmcblk" in disk else ""
    for i, p in enumerate(state.partitions, start=1):
        p.device = f"{disk}{sep}{i}"
    # Also record EFI partition in state
    if state.boot_mode == "uefi":
        for p in state.partitions:
            if p.filesystem == "vfat" and p.mountpoint in ("/boot", "/boot/efi", "/efi"):
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
        # swapon is best-effort — the system will use it via fstab after reboot
        # Failure here is non-fatal (device may need a moment to settle)
        ok2, out2 = run_cmd(
            ["swapon", p.device],
            state, f"Enable swap on {p.device}"
        )
        if not ok2:
            state.add_log(f"[warn] swapon {p.device} failed (non-fatal): {out2}")
        extra = ("\n" + out2) if out2 else ""
        return True, out + extra
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
        # Use consistent mapper names: 'root' for / and 'crypthome' for /home.
        # This ensures rd.luks.name=UUID=root maps correctly to /dev/mapper/root.
        original_device = p.device  # save before p.device is overwritten below
        mp_clean = p.mountpoint.strip("/").replace("/", "_") or "root"
        if mp_clean == "root":
            mapper_name = "root"
        else:
            mapper_name = f"crypt{mp_clean}"
        ok, out = run_cmd(
            ["bash", "-c",
             f"echo -n '{state.luks_passphrase}' | "
             f"cryptsetup open {p.device} {mapper_name}"],
            state, f"Open LUKS container as /dev/mapper/{mapper_name}"
        )
        if not ok:
            return False, out
        logs.append(out)

        # Save the original block device path so the bootloader step
        # can get the LUKS UUID via blkid (p.device gets overwritten next)
        if p.mountpoint in ("/", "/home") and not getattr(state, "luks_block_device", ""):
            state.luks_block_device = original_device  # set just before open

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


def _step_keyring(state, ticker_cb=None) -> tuple:
    """Initialize and populate the pacman keyring before pacstrap.

    On a live ISO the keyring can be stale or incompletely initialized.
    Running pacman-key --init + --populate ensures packages can be verified.
    """
    if state.dry_run:
        state.add_log("[dry run] pacman-key --init && pacman-key --populate archlinux")
        return True, "[dry run] Keyring initialized."

    logs = []

    # Initialize the keyring (generates master key, sets up trust db)
    ok, out = run_cmd(["pacman-key", "--init"], state, "Initialize pacman keyring")
    logs.append(out)
    if not ok:
        return False, f"pacman-key --init failed:\n{out}"

    # Populate with the official Arch Linux keys
    ok, out = run_cmd(
        ["pacman-key", "--populate", "archlinux"],
        state, "Populate Arch Linux keyring"
    )
    logs.append(out)
    if not ok:
        return False, f"pacman-key --populate failed:\n{out}"

    # Refresh the package databases so signatures are current
    ok, out = run_cmd(
        ["pacman", "-Sy", "--noconfirm"],
        state, "Refresh package databases"
    )
    logs.append(out)
    if not ok:
        # Non-fatal — pacstrap will try again
        state.add_log(f"[warn] pacman -Sy failed (non-fatal): {out}")

    return True, "\n".join(logs)


# Optimised pacman.conf written into the new system before pacstrap runs.
# Increases ParallelDownloads for significantly faster package installs.
_PACMAN_CONF = """
[options]
HoldPkg     = pacman glibc
Architecture = auto
Color
CheckSpace
VerbosePkgLists
ParallelDownloads = 10

SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional

[core]
Include = /etc/pacman.d/mirrorlist

[extra]
Include = /etc/pacman.d/mirrorlist

[multilib]
Include = /etc/pacman.d/mirrorlist
""".strip()


def _write_optimized_pacman_conf(state) -> None:
    """Write an optimized pacman.conf to the new system for faster pacstrap."""
    if state.dry_run:
        return
    try:
        os.makedirs(f"{MOUNTPOINT}/etc", exist_ok=True)
        with open(f"{MOUNTPOINT}/etc/pacman.conf", "w") as f:
            f.write(_PACMAN_CONF + "\n")
        state.add_log("Wrote optimized pacman.conf (ParallelDownloads=10)")
    except OSError as e:
        state.add_log(f"[warn] Could not write pacman.conf: {e}")


def _step_pacstrap(state, ticker_cb=None) -> tuple:
    """Run pacstrap to install the base system with live streaming output."""
    packages = build_package_list(state)

    # Write an optimized pacman.conf before pacstrap so parallel downloads
    # take effect. pacstrap -C uses it directly; without -C it copies the
    # live system conf which may have a lower ParallelDownloads setting.
    _write_optimized_pacman_conf(state)

    # Also copy the live system's ranked mirrorlist so pacstrap uses the
    # same fast mirrors without having to re-rank
    if not state.dry_run:
        try:
            live_ml = "/etc/pacman.d/mirrorlist"
            target_ml = f"{MOUNTPOINT}/etc/pacman.d/mirrorlist"
            os.makedirs(f"{MOUNTPOINT}/etc/pacman.d", exist_ok=True)
            # Only use live mirrorlist if it has Server entries
            with open(live_ml) as f:
                live_content = f.read()
            if "Server = " in live_content and not state.mirrorlist:
                with open(target_ml, "w") as f:
                    f.write(live_content)
                state.add_log("Copied live system mirrorlist to new system")
        except OSError:
            pass  # mirrorlist was already written by _step_mirrorlist

    return run_cmd_streaming(
        ["pacstrap", "-K", "-C", f"{MOUNTPOINT}/etc/pacman.conf",
         MOUNTPOINT] + packages,
        state,
        description=f"pacstrap {len(packages)} packages",
        ticker_cb=ticker_cb,
        timeout=3600,  # 60 min — large installs on slow connections
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

        # ── Post-user-creation environment setup ──────────────────────────────
        # Run xdg-user-dirs-update to create standard folders (Downloads, etc.)
        run_chroot(["sudo", "-u", uname, "xdg-user-dirs-update"], state, mountpoint=MOUNTPOINT)

        # Copy default configs for Tiling WMs if selected
        selected_des = (state.desktop_environment or "").split(",")
        extra_pkgs = state.extra_packages

        def _copy_cfg(src, dst_dir, dst_file):
            chroot_dst = f"/home/{uname}/.config/{dst_dir}"
            run_chroot(["mkdir", "-p", chroot_dst], state, mountpoint=MOUNTPOINT)
            # Use cp -f inside chroot
            run_chroot(["cp", "-f", src, f"{chroot_dst}/{dst_file}"], state, mountpoint=MOUNTPOINT)
            run_chroot(["chown", "-R", f"{uname}:{uname}", f"/home/{uname}/.config"], state, mountpoint=MOUNTPOINT)
            run_chroot(["chmod", "+x", f"{chroot_dst}/{dst_file}"], state, mountpoint=MOUNTPOINT)

        if "i3" in selected_des or "i3-wm" in extra_pkgs:
            _copy_cfg("/etc/i3/config", "i3", "config")

        if "bspwm" in selected_des or "bspwm" in extra_pkgs:
            # Arch bspwm package puts examples in /usr/share/doc/bspwm/examples/
            _copy_cfg("/usr/share/doc/bspwm/examples/bspwmrc", "bspwm", "bspwmrc")
            _copy_cfg("/usr/share/doc/bspwm/examples/sxhkdrc", "sxhkd", "sxhkdrc")

        if "polybar" in extra_pkgs:
            # Polybar example config is in /usr/share/doc/polybar/config
            _copy_cfg("/usr/share/doc/polybar/config", "polybar", "config")

        logs.append(f"Created user: {uname} (shell={shell}, sudo={sudo})")

    return True, "\n".join(logs)


def build_package_list(state) -> list:
    """Return the full deduplicated list of packages that will be installed."""
    packages = list(state.base_packages)

    # networkmanager — all lowercase, this is the correct Arch package name
    if state.network_manager and state.network_manager not in packages:
        packages.append(state.network_manager)

    # Standard user directory management
    if "xdg-user-dirs" not in packages:
        packages.append("xdg-user-dirs")

    packages.extend(state.extra_packages)

    # Plymouth — graphical boot splash with LUKS password dialog.
    # The arch-installer theme provides the Fedora-style passphrase prompt.
    if "plymouth" not in packages:
        packages.append("plymouth")

    if state.root_filesystem == "btrfs":
        packages.append("btrfs-progs")
    elif state.root_filesystem == "xfs":
        packages.append("xfsprogs")
    elif state.root_filesystem == "f2fs":
        packages.append("f2fs-tools")

    if state.luks_passphrase:
        packages.append("cryptsetup")

    # Bootloader packages — must be installed into the new system by pacstrap
    bl = state.bootloader
    if bl == "grub":
        packages.extend(["grub", "efibootmgr", "os-prober"])
        if state.boot_mode == "uefi":
            packages.append("dosfstools")
    elif bl == "systemd-boot":
        packages.append("efibootmgr")
    elif bl == "refind":
        packages.append("refind")
    elif bl in ("efistub", "uki"):
        packages.append("efibootmgr")

    # Initramfs generator — dracut is not in base, must be explicitly installed
    if getattr(state, "initramfs_generator", "mkinitcpio") == "dracut":
        packages.append("dracut")

    seen = set()
    result = []
    for p in packages:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result
