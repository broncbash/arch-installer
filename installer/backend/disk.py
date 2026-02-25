"""
installer/backend/disk.py
--------------------------
Backend functions for disk detection and later disk operations.

Stage 4 uses:
    list_disks()      — returns info about all physical block devices
    detect_boot_mode() — UEFI or BIOS

Later stages (5, 6) will use the partitioning and filesystem functions
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

    UEFI systems have /sys/firmware/efi present.
    BIOS systems do not.

    Returns 'uefi' or 'bios'.
    """
    if os.path.exists("/sys/firmware/efi"):
        return "uefi"
    return "bios"


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
                "lsblk",
                "--json",
                "--bytes",          # sizes in bytes (easier to work with)
                "--output",
                "NAME,SIZE,MODEL,TRAN,ROTA,RM,TYPE,FSTYPE,LABEL,MOUNTPOINT",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            log.warning("lsblk failed: %s", result.stderr.strip())
            return []

        data = json.loads(result.stdout)
        devices = data.get("blockdevices", [])

        disks = []
        for dev in devices:
            # Only process whole disks, not partitions or loop devices
            if dev.get("type") not in ("disk",):
                continue

            name      = dev.get("name", "")
            size_bytes = int(dev.get("size") or 0)
            model     = (dev.get("model") or "").strip()
            transport = (dev.get("tran") or "").lower()
            rotational = dev.get("rota")   # "1" = HDD, "0" = SSD/NVMe
            removable  = dev.get("rm") in (True, "1", 1)

            # Work out a friendly disk type label
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

            # Parse child partitions
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
                "name":        name,
                "path":        f"/dev/{name}",
                "size_bytes":  size_bytes,
                "size_human":  _bytes_to_human(size_bytes),
                "model":       model,
                "transport":   transport,
                "disk_type":   disk_type,
                "removable":   removable,
                "partitions":  partitions,
                "has_data":    len(partitions) > 0,
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
    Uses GiB/MiB (powers of 1024) which matches how lsblk normally displays sizes.
    """
    if n <= 0:
        return "0B"
    for unit in ("B", "K", "M", "G", "T", "P"):
        if n < 1024:
            # Show one decimal place for tidiness
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}{unit}"
        n /= 1024
    return f"{n:.1f}P"
