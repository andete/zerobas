#!/bin/sh
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

# Build the cbios-tape ROM patches (IPS + BPS) from tape.asm alone.
#
# No C-BIOS is compiled. pasmo assembles the self-contained cassette source into
# just the bytes the patch adds, and ../tools/rom_patch.py slices the two changed
# regions straight out of it:
#
#   * 0x00E2-0x00F5  -- the seven repointed cassette jump vectors (incl. STMOTR)
#   * 0x3A72-...     -- the routine bodies, in spare page-0 ROM (ends at tape_end)
#
# A stock C-BIOS v0.29 ROM is the patch *target*, not a build input: it is used
# only to stamp the BPS source/target CRC32 and to verify the result end-to-end.
# Pass yours as the first argument, or it auto-detects openMSX's bundled copy.
#
#   sh build-patches.sh [/path/to/cbios_main_msx1_eu.rom]
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SRC="$HERE/tape.asm"
PATCH="$HERE/../tools/rom_patch.py"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Stock ROM (binary target), for BPS CRCs + verification. Override with $1.
STOCK="${1:-/Applications/openMSX.app/Contents/Resources/share/machines/cbios_main_msx1_eu.rom}"

echo "assembling tape.asm (our code only)..."
pasmo --bin "$SRC" "$WORK/tape.bin" "$WORK/tape.sym"

forge() {   # forge OUT [--source ROM]
    python3 "$PATCH" forge "$1" \
        --bin "$WORK/tape.bin" --sym "$WORK/tape.sym" --base 0xE1 \
        --region 0xE2:0xF6 --region 0x3A72:tape_end "$2" "$3"
}

if [ -f "$STOCK" ]; then
    forge "$HERE/cbios-tape-msx1.ips" --source "$STOCK"
    forge "$HERE/cbios-tape-msx1.bps" --source "$STOCK"
else
    echo "note: stock ROM not found ($STOCK)"
    echo "      building IPS only (BPS needs the stock ROM for its CRC32)."
    echo "      pass it: sh build-patches.sh /path/to/cbios_main_msx1_eu.rom"
    forge "$HERE/cbios-tape-msx1.ips"
fi
