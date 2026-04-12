#!/usr/bin/env bash
# build.sh — arch-installer ISO build script
#
# Usage:
#   sudo ./build.sh                   # build the ISO
#   sudo ./build.sh --clean           # wipe work/ and out/ first
#   sudo ./build.sh --vm-test         # build then launch in QEMU for quick testing
#
# Output: out/arch-installer-YYYY.MM.DD-x86_64.iso
#
# Requirements (install on your Arch build machine):
#   sudo pacman -S archiso qemu-desktop libvirt (last two only for --vm-test)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"          # arch-installer repo root
PROFILE_DIR="$SCRIPT_DIR"                          # this directory IS the profile
WORK_DIR="$SCRIPT_DIR/work"
OUT_DIR="$SCRIPT_DIR/out"
INSTALLER_DEST="$WORK_DIR/x86_64/airootfs/opt/arch-installer"

# NFS output path — copy finished ISO here automatically if it exists
NFS_OUTPUT_DIR="${NFS_OUTPUT_DIR:-}"               # set in environment or leave blank

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[build]${NC} $*"; }
success() { echo -e "${GREEN}[build]${NC} $*"; }
warn()    { echo -e "${YELLOW}[build]${NC} $*"; }
error()   { echo -e "${RED}[build]${NC} $*" >&2; }

# ── Root check ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root: sudo ./build.sh"
    exit 1
fi

# ── Parse args ────────────────────────────────────────────────────────────────
DO_CLEAN=false
DO_VM_TEST=false
for arg in "$@"; do
    case "$arg" in
        --clean)    DO_CLEAN=true ;;
        --vm-test)  DO_VM_TEST=true ;;
        --help|-h)
            echo "Usage: sudo ./build.sh [--clean] [--vm-test]"
            echo "  --clean     Remove work/ and out/ before building"
            echo "  --vm-test   Launch the finished ISO in QEMU after build"
            exit 0
            ;;
        *) error "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ── Dependency check ─────────────────────────────────────────────────────────
info "Checking build dependencies..."
missing=()
for cmd in mkarchiso mksquashfs xorriso; do
    if ! command -v "$cmd" &>/dev/null; then
        missing+=("$cmd")
    fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
    error "Missing required tools: ${missing[*]}"
    error "Install with: sudo pacman -S archiso"
    exit 1
fi

if $DO_VM_TEST && ! command -v qemu-system-x86_64 &>/dev/null; then
    error "--vm-test requires qemu: sudo pacman -S qemu-desktop"
    exit 1
fi

# ── Clean ─────────────────────────────────────────────────────────────────────
if $DO_CLEAN; then
    warn "Cleaning work/ and out/ directories..."
    # Safety check: make sure nothing is still mounted from a previous interrupted build
    if findmnt --target "$WORK_DIR" &>/dev/null; then
        error "Mounts detected under $WORK_DIR — run 'sudo umount -R $WORK_DIR' first"
        exit 1
    fi
    rm -rf "$WORK_DIR" "$OUT_DIR"
    success "Cleaned."
fi

mkdir -p "$WORK_DIR" "$OUT_DIR"

# ── Copy installer repo into airootfs ─────────────────────────────────────────
# mkarchiso copies airootfs/ into the squashfs root at build time.
# We overlay our installer at /opt/arch-installer inside the ISO.
info "Copying installer repo into airootfs/opt/arch-installer..."

AIROOTFS_INSTALLER="$PROFILE_DIR/airootfs/opt/arch-installer"
rm -rf "$AIROOTFS_INSTALLER"
mkdir -p "$AIROOTFS_INSTALLER"

rsync -a --exclude='.git' \
         --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='*.pyo' \
         --exclude='.mypy_cache' \
         --exclude='iso/'          \
         --exclude='work/'         \
         --exclude='out/'          \
         "$REPO_ROOT/" "$AIROOTFS_INSTALLER/"

success "Installer repo copied to airootfs."

# ── Make customize_airootfs.sh executable ─────────────────────────────────────
chmod +x "$PROFILE_DIR/airootfs/etc/customize_airootfs.sh" 2>/dev/null || true

# ── Build the ISO ─────────────────────────────────────────────────────────────
info "Starting mkarchiso build..."
info "  Profile : $PROFILE_DIR"
info "  Work dir: $WORK_DIR"
info "  Out dir : $OUT_DIR"
echo ""

# Record build start time to find the resulting ISO later
BUILD_START_TIME=$(date +%s)

if ! mkarchiso -v -w "$WORK_DIR" -o "$OUT_DIR" "$PROFILE_DIR"; then
    error "mkarchiso failed."
    warn "Try running with --clean if you're seeing unexpected errors."
    exit 1
fi

# ── Find the output ISO ────────────────────────────────────────────────────────
# Find the newest .iso file in OUT_DIR that was created during or after this build
ISO_FILE=$(find "$OUT_DIR" -name "*.iso" -type f -printf "%T@ %p\n" | sort -rn | head -1 | cut -d' ' -f2-)

# Sanity check: is it actually a new file?
if [[ -n "$ISO_FILE" ]]; then
    FILE_TIME=$(date -r "$ISO_FILE" +%s)
    if (( FILE_TIME < BUILD_START_TIME )); then
        ISO_FILE=""
    fi
fi

if [[ -z "$ISO_FILE" ]]; then
    error "mkarchiso reported success but no NEW ISO was found in $OUT_DIR"
    warn "This often happens if mkarchiso skipped steps because the work directory was already populated."
    warn "Try building with --clean: sudo ./build.sh --clean"
    exit 1
fi

success "ISO built successfully:"
success "  → $ISO_FILE"
echo ""
ls -lh "$ISO_FILE"

# ── Copy to NFS share (if configured) ─────────────────────────────────────────
if [[ -n "$NFS_OUTPUT_DIR" ]]; then
    if [[ -d "$NFS_OUTPUT_DIR" ]]; then
        info "Copying ISO to NFS share: $NFS_OUTPUT_DIR"
        cp "$ISO_FILE" "$NFS_OUTPUT_DIR/"
        success "Copied to $NFS_OUTPUT_DIR/$(basename "$ISO_FILE")"
    else
        warn "NFS_OUTPUT_DIR=$NFS_OUTPUT_DIR does not exist — skipping NFS copy"
    fi
fi

# ── VM test ────────────────────────────────────────────────────────────────────
if $DO_VM_TEST; then
    echo ""
    info "Launching ISO in QEMU (UEFI, 4GB RAM, 60GB virtual disk)..."
    info "Close the QEMU window or press Ctrl-C to stop."
    echo ""

    # Create a throw-away virtual disk for testing the installer
    VDISK="/tmp/arch-installer-test.qcow2"
    if [[ ! -f "$VDISK" ]]; then
        info "Creating test disk image: $VDISK (60G)"
        qemu-img create -f qcow2 "$VDISK" 60G
    fi

    # OVMF (UEFI firmware) — try common paths
    OVMF_CODE=""
    for path in \
        /usr/share/edk2/x64/OVMF_CODE.4m.fd \
        /usr/share/edk2/x64/OVMF_CODE.fd \
        /usr/share/ovmf/x64/OVMF_CODE.fd \
        /usr/share/OVMF/OVMF_CODE.fd; do
        if [[ -f "$path" ]]; then
            OVMF_CODE="$path"
            break
        fi
    done

    if [[ -z "$OVMF_CODE" ]]; then
        warn "OVMF firmware not found — booting in BIOS mode instead."
        warn "For UEFI testing: sudo pacman -S edk2-ovmf"
        qemu-system-x86_64 \
            -m 4096 \
            -smp 2 \
            -boot d \
            -cdrom "$ISO_FILE" \
            -drive file="$VDISK",format=qcow2 \
            -vga virtio \
            -display gtk \
            -netdev user,id=net0 \
            -device virtio-net-pci,netdev=net0
    else
        info "Using UEFI firmware: $OVMF_CODE"
        qemu-system-x86_64 \
            -m 4096 \
            -smp 2 \
            -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
            -boot d \
            -cdrom "$ISO_FILE" \
            -drive file="$VDISK",format=qcow2 \
            -vga virtio \
            -display gtk \
            -netdev user,id=net0 \
            -device virtio-net-pci,netdev=net0
    fi
fi

echo ""
success "All done."
