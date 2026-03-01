#!/usr/bin/env bash
# build.sh — Sync installer source into airootfs and build the ISO
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIROOTFS="$REPO_ROOT/iso/airootfs/opt/arch-installer"
WORK_DIR="/tmp/archiso-work"
OUT_DIR="$REPO_ROOT/iso/out"
NAS_DIR="/home/ronb/nas_data/Git_Projects/arch-installer/iso/out"

echo "=== Syncing installer source into airootfs ==="
rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "$REPO_ROOT/installer/" \
  "$AIROOTFS/installer/"

echo "=== Cleaning previous build ==="
rm -rf "$WORK_DIR"
mkdir -p "$OUT_DIR"

echo "=== Building ISO ==="
mkarchiso -v \
  -w "$WORK_DIR" \
  -o "$OUT_DIR" \
  "$REPO_ROOT/iso"

echo ""
echo "=== Copying ISO to NAS ==="
mkdir -p "$NAS_DIR"
rsync -av --progress "$OUT_DIR"/*.iso "$NAS_DIR/"

echo ""
echo "=== Done! ISO saved to NAS: $NAS_DIR ==="
ls -lh "$NAS_DIR"/*.iso
