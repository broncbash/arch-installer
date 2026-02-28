#!/usr/bin/env bash
# customize_airootfs.sh
# NOTE: Newer archiso versions do NOT run this automatically.
# Service enablement is handled via symlinks in
# airootfs/etc/systemd/system/multi-user.target.wants/ instead.
# Static config files prevent systemd-firstboot from intercepting.

set -euo pipefail
echo "=== customize_airootfs.sh: nothing to do in this archiso version ==="
