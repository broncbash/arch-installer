"""
installer/ui/complete.py
------------------------
Stage 15 — Complete / Reboot

Runs the final post-install configuration steps inside the chroot, then
offers a reboot button.

Steps handled here (everything pacstrap did NOT cover):
  1.  locale-gen              — generate locale
  2.  locale.conf             — write LANG= to /etc/locale.conf
  3.  vconsole.conf           — write KEYMAP= to /etc/vconsole.conf
  4.  timezone                — symlink /etc/localtime, hwclock --systohc
  5.  initramfs               — generate initramfs (mkinitcpio -P or dracut)
  6.  bootloader              — install GRUB / systemd-boot / rEFInd
  7.  enable services         — NetworkManager, NTP, display manager
  8.  unmount                 — umount -R /mnt

Then shows a success screen with a Reboot Now button.

All steps go through runner.run_cmd / run_chroot so dry_run is respected.
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from installer.ui.base_screen import BaseScreen
from installer.backend.runner import run_cmd, run_chroot, run_script


MOUNTPOINT = "/mnt"

# Plymouth script written into the INSTALLED system (not the ISO).
# The ISO boot splash uses the plain version without a password dialog.
# This version adds the LUKS passphrase callback for the installed system's boot.
_PLYMOUTH_INSTALLED_SCRIPT = r"""
// arch-installer Plymouth theme — installed system
// Y-axis flip effect with pulsing cyan glow + LUKS password dialog

Window.SetBackgroundTopColor(0.07, 0.07, 0.12);
Window.SetBackgroundBottomColor(0.05, 0.05, 0.09);

logo.image  = Image("logo.png");
glow.image  = Image("glow.png");

glow.sprite = Sprite();
glow.sprite.SetImage(glow.image);
glow.sprite.SetZ(1);

logo.sprite = Sprite();
logo.sprite.SetImage(logo.image);
logo.sprite.SetZ(2);

logo.w = logo.image.GetWidth();
logo.h = logo.image.GetHeight();
glow.w = glow.image.GetWidth();
glow.h = glow.image.GetHeight();

glow.sprite.SetX(Window.GetWidth()  / 2 - glow.w / 2);
glow.sprite.SetY(Window.GetHeight() / 2 - glow.h / 2);

flip_angle = 0.0;
flip_speed = 0.04;
glow_alpha = 0.3;
glow_dir   = 1;

progress_bar.image  = Image.New(1, 3);
progress_bar.sprite = Sprite(progress_bar.image);
progress_bar.sprite.SetX(0);
progress_bar.sprite.SetY(Window.GetHeight() - 4);
progress_bar.sprite.SetZ(4);

fun refresh_callback()
{
    flip_angle = flip_angle + flip_speed;
    if (flip_angle > 6.2832) flip_angle = 0.0;
    scale_x = Math.Abs(Math.Cos(flip_angle));
    if (scale_x < 0.02) scale_x = 0.02;
    scaled_w = Math.Int(logo.w * scale_x);
    if (scaled_w < 1) scaled_w = 1;
    scaled = logo.image.Scale(scaled_w, logo.h);
    logo.sprite.SetImage(scaled);
    logo.sprite.SetX(Window.GetWidth()  / 2 - scaled_w / 2);
    logo.sprite.SetY(Window.GetHeight() / 2 - logo.h   / 2);
    glow_alpha = glow_alpha + (glow_dir * 0.015);
    if (glow_alpha >= 0.85) { glow_alpha = 0.85; glow_dir = -1; }
    if (glow_alpha <= 0.15) { glow_alpha = 0.15; glow_dir =  1; }
    glow.sprite.SetOpacity(glow_alpha);
}
Plymouth.SetRefreshFunction(refresh_callback);

fun progress_callback(duration, progress)
{
    if (progress > 1.0) progress = 1.0;
    bar_width = Math.Int(Window.GetWidth() * progress);
    if (bar_width < 1) bar_width = 1;
    bar_img = Image.New(bar_width, 3);
    bar_img.Rectangle(0, 0, bar_width, 3, 0.36, 0.78, 0.94, 1.0);
    progress_bar.sprite.SetImage(bar_img);
}
Plymouth.SetBootProgressFunction(progress_callback);

message_sprite = Sprite();
message_sprite.SetZ(5);
fun display_message_callback(text)
{
    my_image = Image.Text(text, 0.8, 0.8, 0.8, 1.0);
    message_sprite.SetImage(my_image);
    message_sprite.SetX(Window.GetWidth()  / 2 - my_image.GetWidth()  / 2);
    message_sprite.SetY(Window.GetHeight() - 40);
}
Plymouth.SetDisplayMessageFunction(display_message_callback);
fun hide_message_callback(text)
{
    message_sprite.SetImage(Image.New(1,1));
}
Plymouth.SetHideMessageFunction(hide_message_callback);

// ── LUKS passphrase dialog ────────────────────────────────────────────────────
password_label  = Sprite();
password_label.SetZ(10);
password_box    = Sprite();
password_box.SetZ(10);
password_text   = Sprite();
password_text.SetZ(11);

fun display_password_callback(prompt, bullets)
{
    screen_w = Window.GetWidth();
    screen_h = Window.GetHeight();

    label_img = Image.Text(prompt, 0.88, 0.88, 0.88);

    // Auto-size box based on prompt width, but with a minimum
    box_w = label_img.GetWidth() + 32;
    if (box_w < 400) box_w = 400;
    if (box_w > screen_w - 40) box_w = screen_w - 40;

    box_h = 90;
    box_x = screen_w / 2 - box_w / 2;
    box_y = Math.Int(screen_h * 0.62);

    password_label.SetImage(label_img);
    password_label.SetX(screen_w / 2 - label_img.GetWidth() / 2);
    password_label.SetY(box_y - label_img.GetHeight() - 12);
    password_label.SetOpacity(1);

    box_img = Image.New(box_w, box_h);
    box_img.Rectangle(0,       0,       box_w,   box_h,   0.07, 0.07, 0.12, 0.95);
    box_img.Rectangle(0,       0,       box_w,   2,       0.22, 0.82, 0.95, 1.0);
    box_img.Rectangle(0,       box_h-2, box_w,   2,       0.22, 0.82, 0.95, 1.0);
    box_img.Rectangle(0,       0,       2,       box_h,   0.22, 0.82, 0.95, 1.0);
    box_img.Rectangle(box_w-2, 0,       2,       box_h,   0.22, 0.82, 0.95, 1.0);
    password_box.SetImage(box_img);
    password_box.SetX(box_x);
    password_box.SetY(box_y);
    password_box.SetOpacity(1);

    bullet_str = "";
    i = 0;
    while (i < bullets) { bullet_str = bullet_str + "* "; i = i + 1; }
    if (bullets == 0) { bullet_str = "Enter passphrase..."; }
    bullet_img = Image.Text(bullet_str, 0.36, 0.78, 0.94);
    password_text.SetImage(bullet_img);

    // Center bullets if they are short, or left-align if they get long
    bullet_w = bullet_img.GetWidth();
    if (bullet_w < box_w - 32) {
        password_text.SetX(screen_w / 2 - bullet_w / 2);
    } else {
        password_text.SetX(box_x + 16);
    }

    password_text.SetY(box_y + box_h / 2 - bullet_img.GetHeight() / 2);
    password_text.SetOpacity(1);
}
Plymouth.SetDisplayPasswordFunction(display_password_callback);
"""


# ── Step definitions ──────────────────────────────────────────────────────────
# Note: the initramfs label is updated at runtime in _build_ready_page() and
# _build_running_page() to reflect the chosen generator.

COMPLETE_STEPS = [
    ("locale",      "Generate locale"),
    ("vconsole",    "Set keyboard layout"),
    ("timezone",    "Configure timezone"),
    ("initramfs",   "Generate initramfs"),   # label refined at runtime
    ("bootloader",  "Install bootloader"),
    ("services",    "Enable system services"),
    ("unmount",     "Unmount filesystems"),
]


def _initramfs_label(state) -> str:
    """Return a human-readable label for the initramfs step."""
    gen = getattr(state, "initramfs_generator", "mkinitcpio")
    if gen == "dracut":
        return "Generate initramfs  (dracut --force)"
    return "Generate initramfs  (mkinitcpio -P)"


# ── Backend step functions ────────────────────────────────────────────────────

def _step_locale(state) -> tuple:
    """Generate locale and write locale.conf."""
    logs = []

    # Ensure the locale is uncommented in /etc/locale.gen
    locale = state.locale or "en_US.UTF-8"
    ok, out = run_chroot(
        ["sed", "-i", f"s/^#{locale}/{locale}/", "/etc/locale.gen"],
        state, description=f"Uncomment {locale} in locale.gen"
    )
    if not ok:
        return False, out
    logs.append(out)

    ok, out = run_chroot(["locale-gen"], state, description="Run locale-gen")
    if not ok:
        return False, out
    logs.append(out)

    # Write /etc/locale.conf
    locale = state.locale or "en_US.UTF-8"
    ok, out = run_script(
        f"echo 'LANG={locale}' > {MOUNTPOINT}/etc/locale.conf",
        state, "Write /etc/locale.conf"
    )
    if not ok:
        return False, out
    logs.append(out)

    return True, "\n".join(logs)


def _step_vconsole(state) -> tuple:
    """Write /etc/vconsole.conf with the chosen keyboard layout."""
    keymap = state.keyboard_layout or "us"
    ok, out = run_script(
        f"echo 'KEYMAP={keymap}' > {MOUNTPOINT}/etc/vconsole.conf",
        state, f"Write /etc/vconsole.conf (KEYMAP={keymap})"
    )
    return ok, out


def _step_timezone(state) -> tuple:
    """Symlink /etc/localtime and sync hardware clock."""
    logs = []
    tz = state.timezone or "UTC"

    ok, out = run_chroot(
        ["ln", "-sf", f"/usr/share/zoneinfo/{tz}", "/etc/localtime"],
        state, description=f"Link /etc/localtime → {tz}"
    )
    if not ok:
        return False, out
    logs.append(out)

    ok, out = run_chroot(
        ["hwclock", "--systohc"],
        state, description="Sync hardware clock (hwclock --systohc)"
    )
    if not ok:
        return False, out
    logs.append(out)

    return True, "\n".join(logs)


def _step_initramfs(state) -> tuple:
    """Generate the initramfs using mkinitcpio or dracut."""
    logs = []
    gen = getattr(state, "initramfs_generator", "mkinitcpio")
    has_luks = bool(state.luks_passphrase)

    if gen == "dracut":
        # dracut auto-detects LUKS — no extra config needed
        ok, out = run_chroot(
            ["dracut", "--force"],
            state, description="Generate initramfs (dracut --force)"
        )
        if not ok:
            return False, out
        logs.append(out)

    else:
        # mkinitcpio path — edit mkinitcpio.conf directly in Python
        # so we don't rely on fragile sed backreferences.
        # Standard default HOOKS line on a fresh Arch install:
        #   HOOKS=(base udev autodetect modconf kms block filesystems keyboard fsck)
        # With LUKS we need 'encrypt' after 'block'.
        # With Plymouth we need 'plymouth' after 'udev'.
        if not state.dry_run:
            conf_path = f"{MOUNTPOINT}/etc/mkinitcpio.conf"
            try:
                with open(conf_path) as f:
                    conf = f.read()

                import re as _re

                def _patch_hooks(line):
                    """Add encrypt and/or plymouth hooks to a HOOKS=(...) line."""
                    m = _re.match(r"(HOOKS=\()([^)]+)(\))", line.strip())
                    if not m:
                        return line
                    hooks = m.group(2).split()

                    # Always add 'plymouth' after 'udev' for boot splash
                    if "plymouth" not in hooks and "udev" in hooks:
                        idx = hooks.index("udev")
                        hooks.insert(idx + 1, "plymouth")

                    # LUKS hooks
                    if has_luks and "encrypt" not in hooks and "sd-encrypt" not in hooks:
                        # Use systemd-based sd-encrypt if the 'systemd' hook is present
                        enc_hook = "sd-encrypt" if "systemd" in hooks else "encrypt"

                        # Move keymap/keyboard early so they work for passphrase input
                        for h in ["keymap", "keyboard"]:
                            if h in hooks:
                                hooks.remove(h)

                        # Standard mkinitcpio setup needs keyboard/keymap before encrypt
                        # so the user can type their passphrase!
                        base_idx = hooks.index("autodetect") if "autodetect" in hooks else 0
                        hooks.insert(base_idx + 1, "keymap")
                        hooks.insert(base_idx + 2, "keyboard")

                        # Place encryption hook before filesystems (crucial for mounting root)
                        if "filesystems" in hooks:
                            hooks.insert(hooks.index("filesystems"), enc_hook)
                        else:
                            hooks.append(enc_hook)

                    return f"HOOKS=({' '.join(hooks)})"

                patched = []
                for line in conf.splitlines():
                    if line.strip().startswith("HOOKS="):
                        patched.append(_patch_hooks(line))
                    else:
                        patched.append(line)
                conf = "\n".join(patched) + "\n"

                with open(conf_path, "w") as f:
                    f.write(conf)
                hook_msg = "plymouth" + (" + encrypt" if has_luks else "")
                logs.append(f"Patched mkinitcpio.conf HOOKS: added {hook_msg}")
            except OSError as e:
                return False, f"Could not patch mkinitcpio.conf: {e}"

        ok, out = run_chroot(
            ["mkinitcpio", "-P"],
            state, description="Generate initramfs (mkinitcpio -P)"
        )
        if not ok:
            return False, out
        logs.append(out)

    return True, "\n".join(logs)


def _get_efi_dir(state) -> str:
    """Return the ESP mountpoint as seen inside the chroot (e.g. /boot)."""
    for p in state.partitions:
        if p.filesystem == "vfat" and p.mountpoint in ("/boot", "/boot/efi", "/efi"):
            return p.mountpoint
    return "/boot"


def _get_root_partuuid(state) -> str:
    """Return the PARTUUID of the root partition, or empty string on failure."""
    import subprocess as _sp
    for p in state.partitions:
        if p.mountpoint == "/":
            try:
                r = _sp.run(
                    ["blkid", "-o", "value", "-s", "PARTUUID", p.device],
                    capture_output=True, text=True, timeout=10
                )
                return r.stdout.strip()
            except Exception:
                return ""
    return ""


def _get_luks_uuid(state) -> str:
    """Return the UUID of the LUKS block device, or empty string on failure."""
    import subprocess as _sp
    luks_block = getattr(state, "luks_block_device", "")
    if not luks_block:
        return ""
    try:
        r = _sp.run(
            ["blkid", "-o", "value", "-s", "UUID", luks_block],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _build_root_options(state) -> str:
    """
    Build kernel command-line root= options.
    Uses PARTUUID for reliability. Adds cryptdevice= and rd.luks.uuid= when LUKS is active.
    """
    if state.dry_run:
        return "root=PARTUUID=<dry-run> rw quiet splash"

    if state.luks_passphrase:
        luks_uuid = _get_luks_uuid(state)
        if luks_uuid:
            # We add both cryptdevice (for 'encrypt' hook) and rd.luks.name (for 'sd-encrypt' or dracut)
            # to be safe across different initramfs generators.
            # rd.luks.name=<UUID>=<name> ensures the mapper device is named 'cryptroot'
            # which matches our root= parameter and fstab.
            return (
                f"cryptdevice=UUID={luks_uuid}:cryptroot "
                f"rd.luks.name={luks_uuid}=cryptroot "
                f"root=/dev/mapper/cryptroot rw quiet splash"
            )
        return "root=/dev/mapper/cryptroot rw quiet splash"

    partuuid = _get_root_partuuid(state)
    if partuuid:
        return f"root=PARTUUID={partuuid} rw quiet splash"
    return "root=LABEL=root rw quiet splash"


def _get_efi_part_info(state) -> tuple:
    """
    Return (disk, part_num_str, efi_dev) for the EFI partition.
    e.g. ("/dev/sda", "1", "/dev/sda1")
    """
    import re as _re
    efi_dev = getattr(state, "efi_partition", "")
    if not efi_dev:
        for p in state.partitions:
            if p.filesystem == "vfat" and p.mountpoint in ("/boot", "/boot/efi", "/efi"):
                efi_dev = p.device
                break
    disk = state.target_disk or ""
    m = _re.search(r"(\d+)$", efi_dev)
    part_num = m.group(1) if m else "1"
    return disk, part_num, efi_dev


def _step_bootloader(state) -> tuple:
    """Install the chosen bootloader."""
    bl = state.bootloader or "grub"
    logs = []

    if bl == "grub":
        # ── LUKS: configure /etc/default/grub for encrypted boot ─────────────
        if state.luks_passphrase:
            grub_default = f"{MOUNTPOINT}/etc/default/grub"
            if not state.dry_run:
                try:
                    import os as _os, re as _re, subprocess as _sp
                    _os.makedirs(f"{MOUNTPOINT}/etc/default", exist_ok=True)
                    try:
                        with open(grub_default) as f:
                            grub_txt = f.read()
                    except FileNotFoundError:
                        grub_txt = ""

                    # 1. GRUB_ENABLE_CRYPTODISK=y — lets GRUB decrypt its own partition
                    if "GRUB_ENABLE_CRYPTODISK" in grub_txt:
                        grub_txt = _re.sub(
                            r"#?GRUB_ENABLE_CRYPTODISK=.*",
                            "GRUB_ENABLE_CRYPTODISK=y", grub_txt
                        )
                    else:
                        grub_txt += "\nGRUB_ENABLE_CRYPTODISK=y\n"

                    # 2. Get the LUKS partition UUID via blkid
                    # Use the original block device path saved by _step_luks
                    # (p.device has been overwritten to /dev/mapper/cryptroot)
                    luks_uuid = ""
                    luks_block = getattr(state, "luks_block_device", "")
                    if not luks_block:
                        # Fallback: scan all block devices for crypto_LUKS type
                        try:
                            result = _sp.run(
                                ["blkid", "-t", "TYPE=crypto_LUKS",
                                 "-o", "value", "-s", "UUID"],
                                capture_output=True, text=True, timeout=10
                            )
                            uuids = result.stdout.strip().splitlines()
                            if uuids:
                                luks_uuid = uuids[0].strip()
                        except Exception:
                            pass
                    else:
                        # Direct blkid on the known LUKS block device — reliable
                        try:
                            result = _sp.run(
                                ["blkid", "-o", "value", "-s", "UUID", luks_block],
                                capture_output=True, text=True, timeout=10
                            )
                            luks_uuid = result.stdout.strip()
                        except Exception:
                            pass

                    # 3. Set cryptdevice= and root= kernel parameters
                    if luks_uuid:
                        # Ensure we use the SAME options as systemd-boot for consistency
                        crypt_param = (
                            f"cryptdevice=UUID={luks_uuid}:cryptroot "
                            f"rd.luks.name={luks_uuid}=cryptroot "
                            f"root=/dev/mapper/cryptroot"
                        )
                        if "GRUB_CMDLINE_LINUX=" in grub_txt:
                            grub_txt = _re.sub(
                                r'GRUB_CMDLINE_LINUX="[^"]*"',
                                f'GRUB_CMDLINE_LINUX="{crypt_param}"',
                                grub_txt
                            )
                        else:
                            grub_txt += f'\nGRUB_CMDLINE_LINUX="{crypt_param}"\n'
                        logs.append(f"Set cryptdevice=UUID={luks_uuid}:cryptroot")

                    # 4. Create a keyfile so GRUB only asks once (not twice).
                    #    GRUB_ENABLE_CRYPTODISK=y makes GRUB ask for passphrase
                    #    to decrypt its own files, then the initramfs asks again.
                    #    A keyfile embedded in the initramfs lets cryptsetup
                    #    auto-unlock at boot without a second prompt.
                    if luks_uuid and luks_block:
                        try:
                            keyfile_path = f"{MOUNTPOINT}/etc/cryptsetup-keys.d/cryptroot.key"
                            _os.makedirs(f"{MOUNTPOINT}/etc/cryptsetup-keys.d", exist_ok=True)
                            # Generate 512-byte random keyfile
                            key_bytes = _os.urandom(512)
                            with open(keyfile_path, "wb") as kf:
                                kf.write(key_bytes)
                            _os.chmod(keyfile_path, 0o400)
                            safe_pass = state.luks_passphrase.replace("'", "'\\''")
                            # Add the keyfile to LUKS using existing passphrase
                            result = _sp.run(
                                ["bash", "-c",
                                 f"echo -n '{safe_pass}' | "
                                 f"cryptsetup luksAddKey {luks_block} {keyfile_path}"],
                                capture_output=True, text=True, timeout=30
                            )
                            if result.returncode == 0:
                                # Tell mkinitcpio to include the keyfile
                                conf_path = f"{MOUNTPOINT}/etc/mkinitcpio.conf"
                                try:
                                    with open(conf_path) as f:
                                        mkinit = f.read()
                                    if "FILES=()" in mkinit:
                                        mkinit = mkinit.replace(
                                            "FILES=()",
                                            "FILES=(/etc/cryptsetup-keys.d/cryptroot.key)"
                                        )
                                    elif "FILES=(" in mkinit and "/cryptroot.key" not in mkinit:
                                        mkinit = _re.sub(
                                            r"FILES=\(([^)]*)\)",
                                            r"FILES=(\1 /etc/cryptsetup-keys.d/cryptroot.key)",
                                            mkinit
                                        )
                                    with open(conf_path, "w") as f:
                                        f.write(mkinit)
                                except OSError:
                                    pass
                                # Add rd.luks.key to kernel params for systemd path
                                crypt_param += f" rd.luks.key={luks_uuid}=/etc/cryptsetup-keys.d/cryptroot.key"
                                logs.append("Created LUKS keyfile — single passphrase prompt at boot")
                            else:
                                state.add_log(f"[warn] Could not add keyfile to LUKS: {result.stderr}")
                        except Exception as e:
                            state.add_log(f"[warn] Keyfile setup failed (non-fatal): {e}")

                    # Add quiet splash for Plymouth (non-destructive — won't
                    # override if user already has GRUB_CMDLINE_LINUX_DEFAULT)
                    if "GRUB_CMDLINE_LINUX_DEFAULT=" not in grub_txt:
                        grub_txt += 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n'
                    else:
                        # Inject quiet splash into existing default cmdline
                        import re as _re2
                        def _add_quiet(m):
                            v = m.group(1)
                            if "quiet" not in v:
                                v += " quiet"
                            if "splash" not in v:
                                v += " splash"
                            return f'GRUB_CMDLINE_LINUX_DEFAULT="{v.strip()}"'
                        grub_txt = _re2.sub(
                            r'GRUB_CMDLINE_LINUX_DEFAULT="([^"]*)"'
                            , _add_quiet, grub_txt)

                    with open(grub_default, "w") as f:
                        f.write(grub_txt)
                    logs.append("Set GRUB_ENABLE_CRYPTODISK=y in /etc/default/grub")
                except OSError as e:
                    state.add_log(f"[warn] Could not update /etc/default/grub: {e}")
            else:
                state.add_log("[dry run] Would set GRUB_ENABLE_CRYPTODISK=y and cryptdevice=")

        # ── quiet splash — always needed for Plymouth boot splash ────────────
        if not state.dry_run:
            try:
                import os as _os, re as _re3
                grub_default = f"{MOUNTPOINT}/etc/default/grub"
                _os.makedirs(f"{MOUNTPOINT}/etc/default", exist_ok=True)
                try:
                    with open(grub_default) as f:
                        grub_txt2 = f.read()
                except FileNotFoundError:
                    grub_txt2 = ""
                if "GRUB_CMDLINE_LINUX_DEFAULT=" not in grub_txt2:
                    grub_txt2 += 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n'
                else:
                    def _qs(m):
                        v = m.group(1)
                        if "quiet" not in v: v += " quiet"
                        if "splash" not in v: v += " splash"
                        return f'GRUB_CMDLINE_LINUX_DEFAULT="{v.strip()}"'
                    grub_txt2 = _re3.sub(
                        r'GRUB_CMDLINE_LINUX_DEFAULT="([^"]*)"'
                        , _qs, grub_txt2)
                with open(grub_default, "w") as f:
                    f.write(grub_txt2)
                logs.append("Set GRUB_CMDLINE_LINUX_DEFAULT=\"quiet splash\"")
            except OSError as e:
                state.add_log(f"[warn] Could not set quiet splash: {e}")

        # ── grub-install ──────────────────────────────────────────────────────
        if state.boot_mode == "uefi":
            # Determine where the ESP is actually mounted (auto = /boot/efi,
            # manual may use /boot or /efi — read from state.partitions)
            efi_dir = "/boot/efi"  # safe default matching auto partition scheme
            for p in state.partitions:
                if p.filesystem == "vfat" and p.mountpoint in ("/boot", "/boot/efi", "/efi"):
                    efi_dir = p.mountpoint
                    break
            ok, out = run_chroot(
                ["grub-install",
                 "--target=x86_64-efi",
                 f"--efi-directory={efi_dir}",
                 "--bootloader-id=GRUB",
                 "--recheck"],
                state, description="grub-install (UEFI)"
            )
        else:
            ok, out = run_chroot(
                ["grub-install",
                 "--target=i386-pc",
                 state.target_disk],
                state, description="grub-install (BIOS)"
            )
        if not ok:
            return False, out
        logs.append(out)

        ok, out = run_chroot(
            ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
            state, description="Generate grub.cfg"
        )
        if not ok:
            return False, out
        logs.append(out)

    elif bl == "systemd-boot":
        efi_dir = _get_efi_dir(state)
        esp_host = f"{MOUNTPOINT}{efi_dir}"   # e.g. /mnt/boot

        # bootctl install runs inside the chroot so it can write EFI vars.
        # --esp-path is the correct modern flag (not the deprecated --path alias).
        ok, out = run_chroot(
            ["bootctl", f"--esp-path={efi_dir}", "install"],
            state, description="bootctl install"
        )
        if not ok:
            return False, out
        logs.append(out)

        root_opts = _build_root_options(state)

        # Detect installed microcode
        microcode_line = ""
        if not state.dry_run:
            import os as _os
            for uc in ("intel-ucode.img", "amd-ucode.img"):
                if _os.path.exists(f"{MOUNTPOINT}/boot/{uc}"):
                    microcode_line = f"initrd  /{uc}\n"
                    break

        # Write config files directly in Python to avoid shell escaping issues.
        # loader.conf: 'default' must be the entry filename WITH .conf extension.
        # Entry paths are relative to the ESP root; Beginner layout puts ESP at
        # /boot so /vmlinuz-linux, /initramfs-linux.img are correct as-is.
        if not state.dry_run:
            import os as _os2
            try:
                _os2.makedirs(f"{esp_host}/loader/entries", exist_ok=True)

                with open(f"{esp_host}/loader/loader.conf", "w") as f:
                    f.write("default arch.conf\ntimeout 4\nconsole-mode max\n")
                logs.append("Wrote loader.conf")

                entry = (
                    "title   Arch Linux\n"
                    "linux   /vmlinuz-linux\n"
                    + microcode_line +
                    "initrd  /initramfs-linux.img\n"
                    f"options {root_opts}\n"
                )
                with open(f"{esp_host}/loader/entries/arch.conf", "w") as f:
                    f.write(entry)
                logs.append(f"Wrote arch.conf (options: {root_opts})")
            except OSError as e:
                return False, f"Could not write systemd-boot config: {e}"
        else:
            logs.append("[dry run] Would write loader.conf and arch.conf")

    elif bl == "refind":
        # refind-install is a bash script that breaks when run inside arch-chroot
        # because it sources helper scripts relative to its own path using process
        # substitution that arch-chroot doesn't handle well.
        # Correct approach: run it from the LIVE system with --root /mnt so it
        # installs rEFInd into the target ESP without trying to chroot itself.
        # The binary lives at /usr/bin/refind-install inside the new system.
        ok, out = run_cmd(
            [f"{MOUNTPOINT}/usr/bin/refind-install", "--root", MOUNTPOINT],
            state, description="refind-install --root /mnt"
        )
        if not ok:
            return False, out
        logs.append(out)

        # refind-install populates /boot/refind_linux.conf with kernel options
        # from the LIVE system, not the installed system. Overwrite it with the
        # correct options for the installed system.
        root_opts = _build_root_options(state)
        refind_conf = f"{MOUNTPOINT}/boot/refind_linux.conf"
        if not state.dry_run:
            import os as _os3
            try:
                with open(refind_conf, "w") as f:
                    f.write(f'"Boot with standard options"  "{root_opts}"\n')
                logs.append(f"Wrote refind_linux.conf (options: {root_opts})")
            except OSError as e:
                state.add_log(f"[warn] Could not write refind_linux.conf: {e}")

    elif bl == "efistub":
        # efibootmgr is installed into the NEW system by pacstrap.
        # It must run via arch-chroot so it's found in /usr/bin/.
        # EFI loader paths must use backslashes and be relative to the ESP root.
        disk, part_num, _ = _get_efi_part_info(state)
        if not disk:
            return False, "Cannot determine target disk for EFIStub registration."

        root_opts = _build_root_options(state)

        # Detect microcode for initrd chain
        microcode_initrd = ""
        if not state.dry_run:
            import os as _os4
            for uc in ("intel-ucode.img", "amd-ucode.img"):
                if _os4.path.exists(f"{MOUNTPOINT}/boot/{uc}"):
                    microcode_initrd = f"initrd=\\{uc} "
                    break

        # --loader path uses backslashes and is relative to the ESP root.
        # --unicode carries the full kernel command line including initrd= params.
        unicode_opts = f"{root_opts} {microcode_initrd}initrd=\\initramfs-linux.img".strip()

        ok, out = run_chroot(
            ["efibootmgr",
             "--disk", disk,
             "--part", part_num,
             "--create",
             "--label", "Arch Linux",
             "--loader", "\\vmlinuz-linux",
             "--unicode", unicode_opts],
            state, description="Register EFIStub entry via efibootmgr"
        )
        if not ok:
            return False, out
        logs.append(out)

    elif bl == "uki":
        # Build a Unified Kernel Image: kernel + initramfs + cmdline in one .efi.
        # Steps:
        #   1. Create the output directory (mkinitcpio won't create it itself)
        #   2. Write /etc/kernel/cmdline (mkinitcpio reads this for UKI cmdline)
        #   3. Patch linux.preset to set default_uki= output path
        #   4. Run mkinitcpio -p linux inside chroot
        #   5. Register the .efi with efibootmgr inside chroot

        import os as _os5

        uki_efi_path = "/boot/EFI/Linux/arch-linux.efi"   # inside chroot
        uki_host_dir = f"{MOUNTPOINT}/boot/EFI/Linux"

        # 1. Create output directory
        if not state.dry_run:
            try:
                _os5.makedirs(uki_host_dir, exist_ok=True)
                logs.append(f"Created {uki_host_dir}")
            except OSError as e:
                return False, f"Could not create UKI output directory: {e}"

        root_opts = _build_root_options(state)

        # 2. Write /etc/kernel/cmdline — embedded into the UKI by mkinitcpio
        if not state.dry_run:
            try:
                _os5.makedirs(f"{MOUNTPOINT}/etc/kernel", exist_ok=True)
                with open(f"{MOUNTPOINT}/etc/kernel/cmdline", "w") as f:
                    f.write(root_opts + "\n")
                logs.append(f"Wrote /etc/kernel/cmdline: {root_opts}")
            except OSError as e:
                return False, f"Could not write /etc/kernel/cmdline: {e}"

        # 3. Patch linux.preset to enable UKI output
        if not state.dry_run:
            preset_path = f"{MOUNTPOINT}/etc/mkinitcpio.d/linux.preset"
            try:
                with open(preset_path) as f:
                    preset = f.read()
                import re as _re2
                # Ensure ALL_kver points to the kernel
                if "ALL_kver=" not in preset:
                    preset += "\nALL_kver=/boot/vmlinuz-linux\n"
                # Set default_uki= output path (add or replace/uncomment)
                uki_line = f'default_uki="{uki_efi_path}"'
                if "default_uki=" in preset:
                    preset = _re2.sub(r'#?\s*default_uki=.*', uki_line, preset)
                else:
                    preset += f"\n{uki_line}\n"
                with open(preset_path, "w") as f:
                    f.write(preset)
                logs.append("Patched linux.preset for UKI output")
            except OSError as e:
                return False, f"Could not patch linux.preset: {e}"

        # 4. Build the UKI
        ok, out = run_chroot(
            ["mkinitcpio", "-p", "linux"],
            state, description="Build Unified Kernel Image (mkinitcpio -p linux)"
        )
        if not ok:
            return False, out
        logs.append(out)

        # 5. Register with efibootmgr (inside chroot — efibootmgr is in new system)
        disk, part_num, _ = _get_efi_part_info(state)
        if disk:
            ok2, out2 = run_chroot(
                ["efibootmgr",
                 "--disk", disk,
                 "--part", part_num,
                 "--create",
                 "--label", "Arch Linux (UKI)",
                 "--loader", "\\EFI\\Linux\\arch-linux.efi"],
                state, description="Register UKI with efibootmgr"
            )
            if out2:
                logs.append(out2)

    else:
        return False, f"Unknown bootloader: {bl}"

    return True, "\n".join(logs)


def _step_services(state) -> tuple:
    """Enable essential systemd services."""
    logs = []
    services = []

    # ── Plymouth: install theme + set it as default ───────────────────────────
    # Plymouth gives the Fedora-style graphical password entry at boot.
    # The arch-installer theme is bundled in the ISO and pacstrap copies it.
    if state.luks_passphrase or True:  # always nice to have a boot splash
        # Install theme files into new system
        if not state.dry_run:
            import os as _os, shutil as _sh
            theme_src = "/usr/share/plymouth/themes/arch-installer"
            theme_dst = f"{MOUNTPOINT}/usr/share/plymouth/themes/arch-installer"
            if _os.path.exists(theme_src):
                try:
                    _sh.copytree(theme_src, theme_dst, dirs_exist_ok=True)
                    logs.append("Copied arch-installer Plymouth theme to new system")

                    # The ISO script has no password dialog (it's just a boot splash).
                    # Overwrite the installed copy with a version that adds the
                    # LUKS passphrase callback — only needed on the installed system.
                    installed_script = f"{theme_dst}/arch-installer.script"
                    with open(installed_script, "w") as _sf:
                        _sf.write(_PLYMOUTH_INSTALLED_SCRIPT)
                    logs.append("Wrote LUKS-capable Plymouth script to installed system")
                except Exception as e:
                    state.add_log(f"[warn] Plymouth theme copy failed: {e}")

        # Write plymouthd.conf to new system
        if not state.dry_run:
            try:
                import os as _os
                _os.makedirs(f"{MOUNTPOINT}/etc/plymouth", exist_ok=True)
                with open(f"{MOUNTPOINT}/etc/plymouth/plymouthd.conf", "w") as f:
                    f.write("[Daemon]\nTheme=arch-installer\nShowDelay=0\n")
                logs.append("Configured Plymouth theme: arch-installer")
            except OSError as e:
                state.add_log(f"[warn] Could not write plymouthd.conf: {e}")

        services.append("plymouth")

    # Network manager — package name is lowercase but service name is mixed case
    nm = (state.network_manager or "").lower()
    if nm == "networkmanager":
        services.append("NetworkManager")
    elif nm == "systemd-networkd":
        services.append("systemd-networkd")
        services.append("systemd-resolved")
    elif nm == "iwd":
        services.append("iwd")

    # NTP
    if state.enable_ntp:
        services.append("systemd-timesyncd")

    # Display manager
    dm = state.display_manager or ""
    if dm in ("gdm", "sddm", "lightdm"):
        services.append(dm)

    if not services:
        return True, "No services to enable."

    # Configure LightDM GTK greeter to use Adwaita dark — matches installer theme.
    # Write the config file directly from Python to avoid shell quoting issues.
    if dm == "lightdm":
        greeter_conf_path = f"{MOUNTPOINT}/etc/lightdm/lightdm-gtk-greeter.conf"
        greeter_conf = (
            "[greeter]\n"
            "theme-name = Adwaita\n"
            "prefer-dark-theme = true\n"
            "icon-theme-name = Adwaita\n"
            "font-name = Sans 11\n"
            "xft-antialias = true\n"
            "xft-hintstyle = hintslight\n"
            "xft-rgba = rgb\n"
            "background = #1e1e2e\n"
            "user-background = false\n"
        )
        if not state.dry_run:
            try:
                import os as _os
                _os.makedirs(f"{MOUNTPOINT}/etc/lightdm", exist_ok=True)
                with open(greeter_conf_path, "w") as f:
                    f.write(greeter_conf)
                logs.append("LightDM greeter configured with Adwaita dark theme.")
            except OSError as e:
                state.add_log(f"[warn] Could not write LightDM greeter config: {e}")
        else:
            state.add_log(f"[dry run] Would write LightDM greeter config to {greeter_conf_path}")
            logs.append("[dry run] LightDM greeter config skipped.")

    for svc in services:
        ok, out = run_chroot(
            ["systemctl", "enable", svc],
            state, description=f"Enable {svc}"
        )
        if not ok:
            # Non-fatal: service may not be installed (e.g. no DE selected)
            # Log the warning but keep going
            logs.append(f"[warn] Could not enable {svc}: {out}")
            state.add_log(f"[warn] systemctl enable {svc} failed: {out}")
        else:
            logs.append(out)

    return True, "\n".join(logs)


def _step_unmount(state) -> tuple:
    """Unmount all filesystems under /mnt."""
    return run_cmd(
        ["umount", "-R", MOUNTPOINT],
        state, "Unmount all filesystems (umount -R /mnt)"
    )


def run_complete_step(step_id: str, state) -> tuple:
    """Dispatch a complete step by id."""
    fn = {
        "locale":     _step_locale,
        "vconsole":   _step_vconsole,
        "timezone":   _step_timezone,
        "initramfs":  _step_initramfs,
        "bootloader": _step_bootloader,
        "services":   _step_services,
        "unmount":    _step_unmount,
    }.get(step_id)

    if fn is None:
        return False, f"Unknown step: {step_id}"

    try:
        return fn(state)
    except Exception as exc:
        return False, f"Unexpected error in '{step_id}': {exc}"


# ── Screen ────────────────────────────────────────────────────────────────────

class CompleteScreen(BaseScreen):
    """Stage 15 — Complete / Reboot."""

    title    = "Complete Installation"
    subtitle = "Final configuration and reboot"

    WIKI_LINKS = [
        ("Installation guide — chroot", "https://wiki.archlinux.org/title/Installation_guide#Configure_the_system"),
        ("mkinitcpio",                  "https://wiki.archlinux.org/title/Mkinitcpio"),
        ("dracut",                      "https://wiki.archlinux.org/title/Dracut"),
        ("GRUB",                        "https://wiki.archlinux.org/title/GRUB"),
        ("systemd-boot",                "https://wiki.archlinux.org/title/Systemd-boot"),
    ]

    def __init__(self, state, on_next, on_back=None):
        self._phase        = "ready"   # 'ready' | 'running' | 'done' | 'error'
        self._failed_step  = None
        self._step_icons   = {}

        super().__init__(state=state, on_next=on_next, on_back=on_back)

        self.set_next_enabled(False)
        self.set_next_label("🔁  Finish")
        self.set_back_enabled(False)   # no going back once we're here
        GLib.idle_add(self._apply_phase)

    # ── Hints ─────────────────────────────────────────────────────────────────

    def get_hints(self) -> dict:
        dry = "  [DRY RUN]" if self.state.dry_run else ""
        gen = getattr(self.state, "initramfs_generator", "mkinitcpio")
        return {
            "beginner": (
                f"🎉  Almost done!{dry}\n\n"
                "This final stage sets up the last few things your system "
                "needs before it can boot on its own:\n\n"
                "• Locale — your language settings\n"
                "• Keyboard layout in the console\n"
                "• Timezone and hardware clock\n"
                "• Initramfs — the mini-system that starts your kernel\n"
                "• Bootloader — what starts Arch at power-on\n"
                "• System services (network, time sync)\n\n"
                "When it's done, click Reboot to start your new system."
            ),
            "intermediate": (
                f"🎉  Final configuration{dry}\n\n"
                f"Steps: locale-gen → locale.conf → vconsole.conf → "
                f"localtime symlink → hwclock → {gen} → "
                f"bootloader install → systemctl enable → umount -R /mnt\n\n"
                "After rebooting, remove the installation media so the "
                "system boots from the installed disk."
            ),
            "advanced": (
                f"🎉  Post-install chroot config{dry}\n\n"
                "locale-gen reads /etc/locale.gen; LANG is written to "
                "/etc/locale.conf. KEYMAP to /etc/vconsole.conf.\n\n"
                f"Initramfs generator: {gen}. "
                + (
                    "mkinitcpio -P regenerates all presets. If LUKS + UKI is "
                    "selected the encrypt hook is injected into "
                    "/etc/mkinitcpio.conf first."
                    if gen == "mkinitcpio" else
                    "dracut --force regenerates the initramfs image. "
                    "dracut auto-detects hardware — no manual hook configuration needed."
                ) +
                "\n\nBootloader: GRUB (grub-install + grub-mkconfig), "
                "systemd-boot (bootctl install + loader entries), "
                "rEFInd (refind-install), EFIStub (efibootmgr), "
                "UKI (mkinitcpio --uki).\n\n"
                "Finally: umount -R /mnt and reboot."
            ),
        }

    # ── Content ───────────────────────────────────────────────────────────────

    def build_content(self) -> Gtk.Widget:
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)

        self._stack.add_named(self._build_ready_page(),   "ready")
        self._stack.add_named(self._build_running_page(), "running")
        self._stack.add_named(self._build_done_page(),    "done")

        return self._stack

    # ── Ready page ────────────────────────────────────────────────────────────

    def _build_ready_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)

        # What will happen card
        frame = Gtk.Frame()
        frame.get_style_context().add_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)

        heading = Gtk.Label(label="Final steps:")
        heading.get_style_context().add_class("section-heading")
        heading.set_xalign(0)
        inner.pack_start(heading, False, False, 0)

        for step_id, label in COMPLETE_STEPS:
            # Use the runtime-refined label for the initramfs step
            display_label = _initramfs_label(self.state) if step_id == "initramfs" else label
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            dot = Gtk.Label(label="◦")
            dot.get_style_context().add_class("detail-key")
            row.pack_start(dot, False, False, 0)
            lbl = Gtk.Label(label=display_label)
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            row.pack_start(lbl, True, True, 0)
            inner.pack_start(row, False, False, 0)

        frame.add(inner)
        box.pack_start(frame, False, False, 0)

        # Config summary card
        s = self.state
        summary_frame = Gtk.Frame()
        summary_frame.get_style_context().add_class("card")
        summary_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        summary_inner.set_margin_start(16)
        summary_inner.set_margin_end(16)
        summary_inner.set_margin_top(12)
        summary_inner.set_margin_bottom(12)

        sum_heading = Gtk.Label(label="Configuration:")
        sum_heading.get_style_context().add_class("section-heading")
        sum_heading.set_xalign(0)
        summary_inner.pack_start(sum_heading, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_spacing(4)

        rows = [
            ("Locale",      s.locale),
            ("Keyboard",    s.keyboard_layout),
            ("Timezone",    s.timezone),
            ("Initramfs",   getattr(s, "initramfs_generator", "mkinitcpio")),
            ("Bootloader",  s.bootloader),
            ("Services",    self._services_summary()),
        ]
        for r, (key, val) in enumerate(rows):
            k = Gtk.Label(label=key)
            k.get_style_context().add_class("detail-key")
            k.set_xalign(1)
            grid.attach(k, 0, r, 1, 1)
            v = Gtk.Label(label=val)
            v.get_style_context().add_class("detail-value")
            v.set_xalign(0)
            grid.attach(v, 1, r, 1, 1)

        summary_inner.pack_start(grid, False, False, 0)
        summary_frame.add(summary_inner)
        box.pack_start(summary_frame, False, False, 0)

        # Begin button
        begin_label = (
            "🧪  Begin Dry Run" if s.dry_run else "🚀  Finalise Installation"
        )
        begin_btn = Gtk.Button(label=begin_label)
        begin_btn.get_style_context().add_class("nav-btn")
        begin_btn.get_style_context().add_class("nav-btn-next")
        begin_btn.set_halign(Gtk.Align.START)
        begin_btn.connect("clicked", self._on_begin_clicked)
        box.pack_start(begin_btn, False, False, 0)

        return box

    # ── Running page ──────────────────────────────────────────────────────────

    def _build_running_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Step indicators
        steps_frame = Gtk.Frame()
        steps_frame.get_style_context().add_class("card")
        steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        steps_box.set_margin_start(16)
        steps_box.set_margin_end(16)
        steps_box.set_margin_top(10)
        steps_box.set_margin_bottom(10)

        for step_id, label in COMPLETE_STEPS:
            display_label = _initramfs_label(self.state) if step_id == "initramfs" else label
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = Gtk.Label(label="○")
            icon.set_width_chars(2)
            self._step_icons[step_id] = icon
            row.pack_start(icon, False, False, 0)
            lbl = Gtk.Label(label=display_label)
            lbl.get_style_context().add_class("detail-value")
            lbl.set_xalign(0)
            row.pack_start(lbl, True, True, 0)
            steps_box.pack_start(row, False, False, 0)

        steps_frame.add(steps_box)
        box.pack_start(steps_frame, False, False, 0)

        # Progress bar
        self._progress = Gtk.ProgressBar()
        self._progress.set_show_text(True)
        self._progress.set_text("Starting…")
        box.pack_start(self._progress, False, False, 0)

        # Log view
        log_frame = Gtk.Frame()
        log_frame.get_style_context().add_class("card")
        log_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        log_inner.set_margin_start(2)
        log_inner.set_margin_end(2)
        log_inner.set_margin_top(2)
        log_inner.set_margin_bottom(2)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        log_scroll.set_min_content_height(180)
        log_scroll.set_vexpand(True)

        self._log_view = Gtk.TextView()
        self._log_view.set_editable(False)
        self._log_view.set_cursor_visible(False)
        self._log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._log_view.override_font(Pango.FontDescription("Monospace 9"))
        self._log_view.get_style_context().add_class("detail-value")
        self._log_buffer = self._log_view.get_buffer()

        log_scroll.add(self._log_view)
        log_inner.pack_start(log_scroll, True, True, 0)
        log_frame.add(log_inner)
        box.pack_start(log_frame, True, True, 0)

        # Status label
        self._status_label = Gtk.Label(label="")
        self._status_label.get_style_context().add_class("detail-value")
        self._status_label.set_xalign(0)
        self._status_label.set_line_wrap(True)
        box.pack_start(self._status_label, False, False, 0)

        # Retry / Abort row (hidden until error)
        self._error_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._retry_btn = Gtk.Button(label="🔄  Retry failed step")
        self._retry_btn.get_style_context().add_class("action-button")
        self._retry_btn.connect("clicked", self._on_retry_clicked)
        self._error_row.pack_start(self._retry_btn, False, False, 0)
        self._error_row.set_no_show_all(True)
        box.pack_start(self._error_row, False, False, 0)

        return box

    # ── Done page ─────────────────────────────────────────────────────────────

    def _build_done_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        if self.state.dry_run:
            icon_text = "🧪"
            title_text = "Dry Run Complete"
            body_text = (
                "All steps were simulated successfully.\n"
                "No changes were made to your disk.\n\n"
                "Set  dry_run = False  in state.py to perform a real install."
            )
            btn_text = "✓  Close"
        else:
            icon_text = "🎉"
            title_text = "Installation Complete!"
            body_text = (
                f"Arch Linux has been installed successfully.\n\n"
                f"Hostname  :  {self.state.hostname}\n"
                f"Users     :  {', '.join(u['username'] for u in self.state.users)}\n"
                f"Bootloader:  {self.state.bootloader}\n\n"
                "Remove your installation media, then reboot."
            )
            btn_text = "🔁  Reboot Now"

        icon = Gtk.Label(label=icon_text)
        icon.get_style_context().add_class("screen-title")
        box.pack_start(icon, False, False, 0)

        title = Gtk.Label(label=title_text)
        title.get_style_context().add_class("screen-title")
        box.pack_start(title, False, False, 0)

        body = Gtk.Label(label=body_text)
        body.get_style_context().add_class("detail-value")
        body.set_justify(Gtk.Justification.CENTER)
        body.set_line_wrap(True)
        box.pack_start(body, False, False, 0)

        self._reboot_btn = Gtk.Button(label=btn_text)
        self._reboot_btn.get_style_context().add_class("nav-btn")
        self._reboot_btn.get_style_context().add_class("nav-btn-next")
        self._reboot_btn.connect("clicked", self._on_reboot_clicked)
        box.pack_start(self._reboot_btn, False, False, 0)

        return box

    # ── Phase management ──────────────────────────────────────────────────────

    def _apply_phase(self):
        if self._phase == "ready":
            self._stack.set_visible_child_name("ready")
        elif self._phase in ("running", "error"):
            self._stack.set_visible_child_name("running")
        elif self._phase == "done":
            self._stack.set_visible_child_name("done")
        return False

    # ── Install flow ──────────────────────────────────────────────────────────

    def _on_begin_clicked(self, _btn):
        self._phase = "running"
        self._apply_phase()
        self._reset_step_icons()
        self._append_log(
            "🧪 DRY RUN — no changes will be made\n\n"
            if self.state.dry_run
            else "Starting final configuration…\n\n"
        )
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        total = len(COMPLETE_STEPS)
        for i, (step_id, label) in enumerate(COMPLETE_STEPS):
            display_label = _initramfs_label(self.state) if step_id == "initramfs" else label
            GLib.idle_add(self._set_step_running, step_id, i, total, display_label)
            ok, output = run_complete_step(step_id, self.state)
            if output:
                GLib.idle_add(self._append_log, output + "\n")
            if ok:
                GLib.idle_add(self._set_step_done, step_id, i + 1, total)
            else:
                GLib.idle_add(self._set_step_failed, step_id, output)
                return
        GLib.idle_add(self._on_complete)

    def _set_step_running(self, step_id, idx, total, label):
        if step_id in self._step_icons:
            self._step_icons[step_id].set_text("⏳")
        self._progress.set_fraction(idx / total)
        self._progress.set_text(f"Step {idx + 1}/{total}: {label}")
        self._append_log(f"\n▶  {label}\n")

    def _set_step_done(self, step_id, done, total):
        if step_id in self._step_icons:
            self._step_icons[step_id].set_text("✅")
        self._progress.set_fraction(done / total)

    def _set_step_failed(self, step_id, error_msg):
        if step_id in self._step_icons:
            self._step_icons[step_id].set_text("❌")
        self._phase = "error"
        self._failed_step = step_id
        self._progress.set_text("Step failed")
        self._status_label.set_text(
            f"❌  Failed: {dict(COMPLETE_STEPS).get(step_id, step_id)}\n"
            f"    {error_msg}"
        )
        self._status_label.get_style_context().add_class("error-label")
        self._error_row.show_all()

    def _on_complete(self):
        self._phase = "done"
        self._progress.set_fraction(1.0)
        self._progress.set_text(
            "✅  Dry run complete" if self.state.dry_run
            else "✅  Installation complete"
        )
        self.state.install_complete = True
        self._apply_phase()

    def _on_retry_clicked(self, _btn):
        if not self._failed_step:
            return
        self._error_row.hide()
        self._status_label.set_text("")
        self._phase = "running"

        failed = self._failed_step
        self._failed_step = None

        step_ids = [s[0] for s in COMPLETE_STEPS]
        start_idx = step_ids.index(failed) if failed in step_ids else 0
        total = len(COMPLETE_STEPS)

        def _retry():
            for i in range(start_idx, total):
                step_id, label = COMPLETE_STEPS[i]
                display_label = _initramfs_label(self.state) if step_id == "initramfs" else label
                GLib.idle_add(self._set_step_running, step_id, i, total, display_label)
                ok, output = run_complete_step(step_id, self.state)
                if output:
                    GLib.idle_add(self._append_log, output + "\n")
                if ok:
                    GLib.idle_add(self._set_step_done, step_id, i + 1, total)
                else:
                    GLib.idle_add(self._set_step_failed, step_id, output)
                    return
            GLib.idle_add(self._on_complete)

        threading.Thread(target=_retry, daemon=True).start()

    def _on_reboot_clicked(self, _btn):
        if self.state.dry_run:
            Gtk.main_quit()
            return
        import subprocess
        try:
            subprocess.run(["reboot"], check=True)
        except Exception:
            run_cmd(["systemctl", "reboot"], self.state, "Reboot")

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _append_log(self, text: str):
        end = self._log_buffer.get_end_iter()
        self._log_buffer.insert(end, text)
        adj = self._log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper())

    def _reset_step_icons(self):
        for step_id, _ in COMPLETE_STEPS:
            if step_id in self._step_icons:
                self._step_icons[step_id].set_text("○")

    # ── Validate and save ─────────────────────────────────────────────────────

    def validate(self):
        return True, ""   # Next button is never shown; reboot btn handles exit

    def on_next(self):
        pass

    # ── Services summary helper ───────────────────────────────────────────────

    def _services_summary(self) -> str:
        svcs = []
        nm = self.state.network_manager or ""
        if nm:
            svcs.append(nm)
        if self.state.enable_ntp:
            svcs.append("systemd-timesyncd")
        if self.state.display_manager:
            svcs.append(self.state.display_manager)
        return ", ".join(svcs) if svcs else "None"
