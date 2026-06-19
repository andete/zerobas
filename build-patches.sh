#!/bin/sh
# Build the zerobas slot-0 page-1 patches (IPS + BPS) against a stock C-BIOS.
#
# zerobas is normally an "AB" cartridge. But on a real MSX, BASIC lives in slot 0
# page 1 ($4000-$7FFF), right next to the BIOS in page 0 -- not in a cartridge
# slot. This produces patches that put zerobas there: apply one to a stock C-BIOS
# main ROM and you get a single 32 KB BIOS+BASIC image, the real-hardware layout.
# C-BIOS's cold-boot cartridge scan reaches its own slot-0 page 1, finds zerobas's
# "AB" header, and calls INIT -- so no extra boot-vector patch is needed.
#
#   sh build-patches.sh [/path/to/cbios_main_msx1*.rom]
#
# The stock ROM is the patch *target* (and the BPS source for its CRC32). Pass
# yours, or it auto-detects openMSX's bundled copy. Output:
#   zerobas-msx1.ips   -- universal, no checksum (used by the openMSX installer)
#   zerobas-msx1.bps   -- CRC32-locked to the stock ROM below; fails cleanly on a
#                         mismatch (use it to forge a standalone patched ROM)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PATCH="$HERE/tools/rom_patch.py"
OVERLAY="$HERE/tools/overlay_page1.py"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Canonical target. Override with $1. (The IPS applies to any MSX1 C-BIOS variant;
# the BPS is CRC-locked to this exact ROM.)
STOCK="${1:-/Applications/openMSX.app/Contents/Resources/share/machines/cbios_main_msx1.rom}"

echo "building zerobas (basic.rom)..."
make -C "$HERE" >/dev/null

if [ ! -f "$STOCK" ]; then
    echo "error: stock C-BIOS main ROM not found: $STOCK" >&2
    echo "       pass it: sh build-patches.sh /path/to/cbios_main_msx1.rom" >&2
    exit 1
fi

echo "splicing zerobas into C-BIOS page 1..."
python3 "$OVERLAY" "$STOCK" "$HERE/basic.rom" "$WORK/combined.rom"

echo "making patches..."
python3 "$PATCH" make "$STOCK" "$WORK/combined.rom" "$HERE/zerobas-msx1.ips"
python3 "$PATCH" make "$STOCK" "$WORK/combined.rom" "$HERE/zerobas-msx1.bps"
echo "done."
