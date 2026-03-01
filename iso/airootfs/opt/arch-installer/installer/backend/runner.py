"""
installer/backend/runner.py
----------------------------
Safe subprocess wrapper for all disk-touching operations.

Every backend function that would modify the system (mkfs, mount,
pacstrap, arch-chroot, etc.) MUST use run_cmd() instead of calling
subprocess directly.

In dry_run mode (state.dry_run = True):
  - The command is logged but never executed
  - A success result is returned so the UI behaves normally
  - The dry-run action is appended to state.install_log

In live mode (state.dry_run = False):
  - The command runs for real via subprocess
  - stdout + stderr are captured and returned
  - Non-zero exit codes are treated as failures

For long-running commands (e.g. pacstrap) use run_cmd_streaming()
to get live output fed to a ticker callback as lines arrive.
"""

import subprocess
import logging
import shlex

log = logging.getLogger(__name__)


def run_cmd(
    cmd: list,
    state,
    description: str = "",
    timeout: int = 300,
    cwd: str = None,
    env: dict = None,
) -> tuple:
    """
    Run a system command, or simulate it in dry-run mode.

    Args:
        cmd:         Command as a list, e.g. ["mkfs.ext4", "/dev/sda2"]
        state:       InstallState — checked for dry_run flag
        description: Human-readable description shown in dry-run log
        timeout:     Seconds before subprocess.TimeoutExpired (default 300)
        cwd:         Working directory for the subprocess
        env:         Optional environment dict override

    Returns:
        (success: bool, output: str)
    """
    cmd_str = " ".join(shlex.quote(str(c)) for c in cmd)
    label   = description or cmd_str

    if state.dry_run:
        msg = f"[DRY RUN] {label}\n  $ {cmd_str}"
        log.info(msg)
        state.add_log(msg)
        return True, f"[dry run] {label}"

    log.info("Running: %s", cmd_str)
    state.add_log(f"$ {cmd_str}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
        output = (result.stdout + result.stderr).strip()

        if result.returncode == 0:
            log.info("Success: %s", label)
            if output:
                state.add_log(output)
            return True, output

        log.error("Failed (exit %d): %s\n%s", result.returncode, label, output)
        state.add_log(f"ERROR (exit {result.returncode}): {output}")
        return False, output

    except FileNotFoundError:
        msg = f"Command not found: {cmd[0]}"
        log.error(msg)
        state.add_log(f"ERROR: {msg}")
        return False, msg

    except subprocess.TimeoutExpired:
        msg = f"Timed out after {timeout}s: {label}"
        log.error(msg)
        state.add_log(f"ERROR: {msg}")
        return False, msg

    except Exception as exc:
        msg = f"Unexpected error running {label}: {exc}"
        log.error(msg)
        state.add_log(f"ERROR: {msg}")
        return False, msg


def run_cmd_streaming(
    cmd: list,
    state,
    description: str = "",
    ticker_cb=None,
    timeout: int = 1800,
    cwd: str = None,
    env: dict = None,
) -> tuple:
    """
    Run a long-running command with live output streaming.

    Like run_cmd() but uses Popen to stream stdout/stderr line by line.
    Each line is passed to ticker_cb (if provided) so the UI can show
    live status without blocking.

    Args:
        cmd:         Command as a list
        state:       InstallState — checked for dry_run flag
        description: Human-readable description
        ticker_cb:   Optional callable(str) called for each output line
        timeout:     Total seconds before giving up (default 1800 = 30 min)
        cwd:         Working directory
        env:         Optional environment dict override

    Returns:
        (success: bool, output: str)
    """
    cmd_str = " ".join(shlex.quote(str(c)) for c in cmd)
    label   = description or cmd_str

    if state.dry_run:
        msg = f"[DRY RUN] {label}\n  $ {cmd_str}"
        log.info(msg)
        state.add_log(msg)
        return True, f"[dry run] {label}"

    log.info("Running (streaming): %s", cmd_str)
    state.add_log(f"$ {cmd_str}")

    lines = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            env=env,
        )

        import threading
        import time

        timed_out = [False]
        start = time.monotonic()

        def _watchdog():
            while proc.poll() is None:
                if time.monotonic() - start > timeout:
                    timed_out[0] = True
                    proc.kill()
                    break
                time.sleep(1)

        watchdog = threading.Thread(target=_watchdog, daemon=True)
        watchdog.start()

        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            if not line:
                continue
            lines.append(line)
            state.add_log(line)
            log.debug(line)
            if ticker_cb:
                display = _extract_ticker_text(line)
                if display:
                    ticker_cb(display)

        proc.wait()
        watchdog.join(timeout=2)

        if timed_out[0]:
            msg = f"Timed out after {timeout}s: {label}"
            log.error(msg)
            state.add_log(f"ERROR: {msg}")
            return False, msg

        output = "\n".join(lines)
        if proc.returncode == 0:
            log.info("Success: %s", label)
            return True, output

        log.error("Failed (exit %d): %s", proc.returncode, label)
        state.add_log(f"ERROR (exit {proc.returncode})")
        return False, output

    except FileNotFoundError:
        msg = f"Command not found: {cmd[0]}"
        log.error(msg)
        state.add_log(f"ERROR: {msg}")
        return False, msg

    except Exception as exc:
        msg = f"Unexpected error running {label}: {exc}"
        log.error(msg, exc_info=True)
        state.add_log(f"ERROR: {msg}")
        return False, msg


def _extract_ticker_text(line: str) -> str:
    """
    Extract a short human-readable status string from a pacstrap output line.

    pacstrap / pacman output looks like:
      ":: Synchronizing package databases..."
      "core downloading..."
      "(1/120) installing base..."
      "downloading linux 6.x..."
      "==> Creating install root at /mnt"
      "==> Generating pacman master key..."
    """
    import re
    line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()

    if not line:
        return ""

    # pacman progress: "(N/M) installing packagename..."
    m = re.match(r'\((\d+/\d+)\)\s+(.*)', line)
    if m:
        return f"{m.group(1)}  {m.group(2)}"

    if "downloading" in line.lower() or "installing" in line.lower():
        return line

    if line.startswith("==>") or line.startswith("::"):
        return line

    return ""


def run_chroot(
    cmd: list,
    state,
    mountpoint: str = "/mnt",
    description: str = "",
    timeout: int = 300,
) -> tuple:
    """
    Run a command inside arch-chroot.

    Args:
        cmd:         Command to run inside chroot
        state:       InstallState
        mountpoint:  Chroot target (default /mnt)
        description: Human-readable description
        timeout:     Seconds before timeout

    Returns:
        (success: bool, output: str)
    """
    full_cmd = ["arch-chroot", mountpoint] + cmd
    desc     = description or f"chroot: {' '.join(cmd)}"
    return run_cmd(full_cmd, state, description=desc, timeout=timeout)


def run_script(
    script: str,
    state,
    description: str = "",
    timeout: int = 300,
) -> tuple:
    """
    Run a shell script string via bash -c.

    Args:
        script:      Shell script string
        state:       InstallState
        description: Human-readable description
        timeout:     Seconds before timeout

    Returns:
        (success: bool, output: str)
    """
    return run_cmd(
        ["bash", "-c", script],
        state,
        description=description or script,
        timeout=timeout,
    )
