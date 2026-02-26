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

Usage:
    from installer.backend.runner import run_cmd

    ok, output = run_cmd(
        ["mkfs.ext4", "-L", "root", "/dev/sda2"],
        state,
        description="Format root partition as ext4",
    )
    if not ok:
        # handle failure
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
        output is stdout+stderr on real runs, or a dry-run message.
    """
    cmd_str = " ".join(shlex.quote(str(c)) for c in cmd)
    label   = description or cmd_str

    if state.dry_run:
        msg = f"[DRY RUN] {label}\n  $ {cmd_str}"
        log.info(msg)
        state.add_log(msg)
        return True, f"[dry run] {label}"

    # Live run
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


def run_chroot(
    cmd: list,
    state,
    mountpoint: str = "/mnt",
    description: str = "",
    timeout: int = 300,
) -> tuple:
    """
    Run a command inside arch-chroot.

    Equivalent to: arch-chroot <mountpoint> <cmd...>

    Args:
        cmd:        Command to run inside chroot
        state:      InstallState
        mountpoint: Chroot target (default /mnt)
        description: Human-readable description
        timeout:    Seconds before timeout

    Returns:
        (success: bool, output: str)
    """
    full_cmd     = ["arch-chroot", mountpoint] + cmd
    desc         = description or f"chroot: {' '.join(cmd)}"
    return run_cmd(full_cmd, state, description=desc, timeout=timeout)


def run_script(
    script: str,
    state,
    description: str = "",
    timeout: int = 300,
) -> tuple:
    """
    Run a shell script string via bash -c.

    Useful for multi-step shell operations that are easier as one-liners.

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
