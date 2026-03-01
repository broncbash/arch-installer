"""
installer/backend/network.py
Network backend: connectivity checks, iwd WiFi wrapper, interface info.

All public functions return (success: bool, message: str) or a data structure
as documented. Long-running operations are expected to be called from threads.
"""

import subprocess
import socket
import re
import time
import logging

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a command, capturing stdout/stderr. Never raises on non-zero exit."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        log.warning("Command timed out: %s", " ".join(cmd))
        return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr="Timed out")
    except FileNotFoundError:
        log.warning("Command not found: %s", cmd[0])
        return subprocess.CompletedProcess(cmd, returncode=127, stdout="", stderr=f"Not found: {cmd[0]}")


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------

def check_connectivity() -> tuple[bool, str]:
    """
    Check for an active internet connection.
    First tries a DNS resolution, then a TCP connect to archlinux.org:443.
    Returns (True, "Connected") or (False, reason).
    """
    try:
        socket.setdefaulttimeout(5)
        socket.getaddrinfo("archlinux.org", 443)
        return True, "Connected"
    except socket.gaierror:
        pass

    # Fallback: ping
    result = _run(["ping", "-c", "1", "-W", "3", "8.8.8.8"], timeout=8)
    if result.returncode == 0:
        return True, "Connected (ping)"

    return False, "No internet connection detected"


# ---------------------------------------------------------------------------
# Interface info
# ---------------------------------------------------------------------------

def get_interface_info() -> dict:
    """
    Return info about the active network interface.
    Dict keys: interface, ip, mac, state, type ('ethernet'|'wifi'|'unknown')
    Any missing field is an empty string.
    """
    info = {
        "interface": "",
        "ip": "",
        "mac": "",
        "state": "disconnected",
        "type": "unknown",
        "ssid": "",
        "signal": "",
    }

    # Use 'ip -o addr show' to find the first non-loopback interface with an IP
    result = _run(["ip", "-o", "addr", "show"])
    if result.returncode != 0:
        return info

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        iface = parts[1]
        if iface == "lo":
            continue
        family = parts[2]
        if family not in ("inet", "inet6"):
            continue
        addr = parts[3].split("/")[0]
        info["interface"] = iface
        info["ip"] = addr
        info["state"] = "connected"
        if iface.startswith("e") or iface.startswith("en"):
            info["type"] = "ethernet"
        elif iface.startswith("w"):
            info["type"] = "wifi"
        break

    if not info["interface"]:
        # No IP yet — still show the interface name from 'ip link'
        result2 = _run(["ip", "-o", "link", "show"])
        for line in result2.stdout.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            iface = parts[1].rstrip(":")
            if iface == "lo":
                continue
            info["interface"] = iface
            if iface.startswith("e") or iface.startswith("en"):
                info["type"] = "ethernet"
            elif iface.startswith("w"):
                info["type"] = "wifi"
            break

    # MAC address
    if info["interface"]:
        r = _run(["cat", f"/sys/class/net/{info['interface']}/address"])
        if r.returncode == 0:
            info["mac"] = r.stdout.strip()

    # If WiFi, try to get SSID and signal via iwctl
    if info["type"] == "wifi" and info["interface"]:
        iface = info["interface"]
        r = _run(["iwctl", "station", iface, "show"], timeout=6)
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.startswith("Connected network"):
                    info["ssid"] = line.split(None, 2)[-1].strip()
                elif line.startswith("RSSI"):
                    info["signal"] = line.split(None, 1)[-1].strip()

    return info


# ---------------------------------------------------------------------------
# WiFi — scanning and connecting via iwd / iwctl
# ---------------------------------------------------------------------------

def _detect_wifi_interface() -> str:
    """Return the first wireless interface name, or empty string."""
    result = _run(["ip", "-o", "link", "show"])
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        iface = parts[1].rstrip(":")
        if iface.startswith("w"):
            return iface
    return ""


def list_wifi_networks() -> tuple[bool, list[dict] | str]:
    """
    Scan for WiFi networks using iwctl and return a list of dicts.
    Each dict: { ssid, signal, security, connected }
    Returns (True, [networks]) or (False, error_message).
    """
    iface = _detect_wifi_interface()
    if not iface:
        return False, "No wireless interface found"

    # Trigger a fresh scan (fire-and-forget; ignore result)
    _run(["iwctl", "station", iface, "scan"], timeout=8)
    time.sleep(2)  # give the scan a moment

    result = _run(["iwctl", "station", iface, "get-networks"], timeout=8)
    if result.returncode != 0:
        return False, f"iwctl get-networks failed: {result.stderr.strip()}"

    networks: list[dict] = []
    # Output looks like:
    #                              Available networks
    # Network name          Security  Signal
    # ─────────────────────────────────────────────────
    # MySSID                psk       ****
    # OpenNet               open      ***
    in_table = False
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip header lines
        if "Available networks" in stripped or stripped.startswith("─") or "Network name" in stripped:
            in_table = True
            continue
        if not in_table:
            continue

        # Parse: may have a leading '>' for connected network
        connected = False
        if stripped.startswith(">"):
            connected = True
            stripped = stripped[1:].strip()

        # Split on 2+ spaces to separate SSID (may contain spaces) from security/signal
        parts = re.split(r"\s{2,}", stripped)
        if len(parts) < 2:
            # Treat whole line as SSID with unknown security
            parts = [stripped, "unknown", ""]

        ssid = parts[0].strip()
        security = parts[1].strip() if len(parts) > 1 else "unknown"
        signal_raw = parts[2].strip() if len(parts) > 2 else ""

        # Convert star rating to percentage (4 stars = 100%)
        if signal_raw:
            stars = signal_raw.count("*")
            signal_pct = int((stars / 4) * 100)
            signal = f"{signal_pct}%"
        else:
            signal = "?"

        if ssid:
            networks.append({
                "ssid": ssid,
                "security": security,
                "signal": signal,
                "connected": connected,
            })

    return True, networks


def connect_wifi(ssid: str, passphrase: str = "") -> tuple[bool, str]:
    """
    Connect to a WiFi network via iwctl.
    For open networks pass passphrase="".
    Returns (True, "Connected") or (False, error_message).
    """
    iface = _detect_wifi_interface()
    if not iface:
        return False, "No wireless interface found"

    if passphrase:
        # iwctl can't take a passphrase interactively via a single command easily.
        # Use the --passphrase flag available in iwd >= 1.0.
        result = _run(
            ["iwctl", "--passphrase", passphrase, "station", iface, "connect", ssid],
            timeout=20,
        )
    else:
        result = _run(["iwctl", "station", iface, "connect", ssid], timeout=20)

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        return False, f"Connection failed: {err}"

    # Wait for an IP address (up to 10 seconds)
    for _ in range(10):
        time.sleep(1)
        ok, _ = check_connectivity()
        if ok:
            return True, f"Connected to {ssid}"

    return False, f"Associated with {ssid} but no IP address obtained"


def disconnect_wifi() -> tuple[bool, str]:
    """Disconnect from the current WiFi network."""
    iface = _detect_wifi_interface()
    if not iface:
        return False, "No wireless interface found"
    result = _run(["iwctl", "station", iface, "disconnect"], timeout=8)
    if result.returncode == 0:
        return True, "Disconnected"
    return False, result.stderr.strip() or "Failed to disconnect"
