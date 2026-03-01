#!/usr/bin/env bash
# build.sh — Sync installer source into airootfs and build the ISO
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIROOTFS="$REPO_ROOT/iso/airootfs/opt/arch-installer"
WORK_DIR="/tmp/archiso-work"
OUT_DIR="/tmp/archiso-out"

echo "=== Syncing installer source into airootfs ==="
rsync -av --delete \
  "$REPO_ROOT/installer/" \
  "$AIROOTFS/installer/"

echo "=== Cleaning previous build ==="
rm -rf "$WORK_DIR" "$OUT_DIR"

echo "=== Building ISO ==="
mkarchiso -v \
  -w "$WORK_DIR" \
  -o "$OUT_DIR" \
  "$REPO_ROOT/iso"

echo ""
echo "=== Done! ISO is at: $OUT_DIR ==="
ls -lh "$OUT_DIR"/*.iso
