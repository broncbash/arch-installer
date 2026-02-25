"""
installer/backend/disk.py
--------------------------
Backend functions for disk detection and later disk operations.

Stage 4 uses:
    list_disks()        — returns info about all physical block devices
    detect_boot_mode()  — UEFI or BIOS

Stage 5 uses:
    get_disk_size_mb()  — returns the size of a specific disk in MB
    get_ram_mb()        — returns total system RAM in MB (for swap suggestions)

Later stages (6+) will use the partitioning and filesystem functions
that will be added here when we reach those stages.

IMPORTANT: Nothing in this file writes to disk. All detection functions
are completely safe to run at any time.
"""

import subprocess
import json
import os
import logging

log = logging.getLogger(__name__)


def detect_boot_mode() -> str:
    """
    Detect whether the system was booted in UEFI or BIOS (legacy) mode.
    UEFI systems have /sys/firmware/efi present. BIOS systems do not.
    Returns 'uefi' or 'bios'.
    """
    if os.path.exists("/sys/firmware/efi"):
        return "uefi"
    return "bios"


def get_disk_size_mb(disk_path: str) -> int:
    """
    Return the total size of a disk in megabytes.
    e.g. get_disk_size_mb('/dev/sda') → 476940

    Uses lsblk to read the size. Returns 0 if the disk can't be found.
    """
    try:
        result = subprocess.run(
            ["lsblk", "--bytes", "--nodeps", "--output", "SIZE", "--noheadings",
             disk_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            size_bytes = int(result.stdout.strip())
            return size_bytes // (1024 * 1024)  # bytes → MB
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired) as e:
        log.warning("Could not get disk size for %s: %s", disk_path, e)
    return 0


def get_ram_mb() -> int:
    """
    Return total system RAM in megabytes.
    Reads /proc/meminfo which is always available on Linux.
    Returns 0 if it can't be read (shouldn't happen).
    """
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    # Line looks like: "MemTotal:       16384000 kB"
                    kb = int(line.split()[1])
                    return kb // 1024   # kB → MB
    except (OSError, ValueError, IndexError) as e:
        log.warning("Could not read /proc/meminfo: %s", e)
    return 0


def suggest_swap_mb(ram_mb: int) -> int:
    """
    Return a sensible swap partition size in MB based on system RAM.
    Follows common Arch/Linux conventions:
      RAM ≤ 2GB  → swap = RAM × 2
      RAM ≤ 8GB  → swap = RAM
      RAM ≤ 64GB → swap = RAM / 2  (rounded to nearest 512MB)
      RAM > 64GB → swap = 4096MB (4GB is plenty)
    Returns 0 if RAM is 0 (unknown).
    """
    if ram_mb <= 0:
        return 2048   # safe fallback
    if ram_mb <= 2048:
        return ram_mb * 2
    if ram_mb <= 8192:
        return ram_mb
    if ram_mb <= 65536:
        raw = ram_mb // 2
        # Round to nearest 512MB for tidiness
        return (raw // 512) * 512
    return 4096


def list_disks() -> list:
    """
    Return a list of physical block devices (whole drives, not partitions).

    Each entry in the list is a dict with these keys:
        name        str   e.g. 'sda', 'nvme0n1', 'vda'
        path        str   e.g. '/dev/sda'
        size_bytes  int   total size in bytes
        size_human  str   human-readable size e.g. '500G', '1T'
        model       str   drive model name, or '' if unknown
        transport   str   'sata', 'nvme', 'usb', 'virtio', or 'unknown'
        disk_type   str   'SSD', 'NVMe', 'HDD', 'USB', or 'Virtual'
        removable   bool  True for USB drives etc.
        partitions  list  list of partition dicts (see below)
        has_data    bool  True if the disk has any existing partitions

    Each partition dict has:
        name        str   e.g. 'sda1'
        path        str   e.g. '/dev/sda1'
        size_human  str   e.g. '100G'
        fstype      str   filesystem type or '' if unknown
        label       str   partition label or ''
        mountpoint  str   current mountpoint or ''

    Falls back to a safe empty list if lsblk is unavailable.
    """
    try:
        result = subprocess.run(
            [
                "lsblk", "--json", "--bytes",
                "--output",
                "NAME,SIZE,MODEL,TRAN,ROTA,RM,TYPE,FSTYPE,LABEL,MOUNTPOINT",
            ],
            capture_output=True, text=True, timeout=10,
        )

        if result.returncode != 0:
            log.warning("lsblk failed: %s", result.stderr.strip())
            return []

        data = json.loads(result.stdout)
        devices = data.get("blockdevices", [])

        disks = []
        for dev in devices:
            if dev.get("type") not in ("disk",):
                continue

            name       = dev.get("name", "")
            size_bytes = int(dev.get("size") or 0)
            model      = (dev.get("model") or "").strip()
            transport  = (dev.get("tran") or "").lower()
            rotational = dev.get("rota")
            removable  = dev.get("rm") in (True, "1", 1)

            if transport == "nvme":
                disk_type = "NVMe SSD"
            elif removable or transport == "usb":
                disk_type = "USB"
            elif transport in ("sata", "ata", "scsi"):
                disk_type = "HDD" if rotational in (True, "1", 1) else "SSD"
            elif transport in ("virtio", ""):
                disk_type = "Virtual"
            else:
                disk_type = "Unknown"

            partitions = []
            for child in dev.get("children", []):
                if child.get("type") not in ("part", "md"):
                    continue
                partitions.append({
                    "name":       child.get("name", ""),
                    "path":       f"/dev/{child.get('name', '')}",
                    "size_human": _bytes_to_human(int(child.get("size") or 0)),
                    "fstype":     child.get("fstype") or "",
                    "label":      child.get("label") or "",
                    "mountpoint": child.get("mountpoint") or "",
                })

            disks.append({
                "name":       name,
                "path":       f"/dev/{name}",
                "size_bytes": size_bytes,
                "size_human": _bytes_to_human(size_bytes),
                "model":      model,
                "transport":  transport,
                "disk_type":  disk_type,
                "removable":  removable,
                "partitions": partitions,
                "has_data":   len(partitions) > 0,
            })

        return disks

    except FileNotFoundError:
        log.error("lsblk not found")
        return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
        log.error("Error listing disks: %s", e)
        return []


def _bytes_to_human(n: int) -> str:
    """
    Convert a byte count to a short human-readable string.
    e.g. 500107862016 → '465.8G'
    Uses GiB/MiB (powers of 1024) to match lsblk's display.
    """
    if n <= 0:
        return "0B"
    for unit in ("B", "K", "M", "G", "T", "P"):
        if n < 1024:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}{unit}"
        n /= 1024
    return f"{n:.1f}P"
