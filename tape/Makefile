# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

# cbios-tape -- build the IPS/BPS cassette-BIOS patches.
#
# Requires pasmo (the assembler C-BIOS uses) and python3. No C-BIOS tree is
# needed: the patch is assembled from src/tape.asm alone. A stock C-BIOS v0.29
# ROM is used only to stamp the BPS CRC32 + verify; override its path with STOCK=.

IPS := cbios-tape-msx1.ips
BPS := cbios-tape-msx1.bps
SRC := src/tape.asm
STOCK ?=

patches: $(SRC) tools/rom_patch.py build-patches.sh
	sh build-patches.sh $(STOCK)

test: patches
	python3 tools/run_tape_regression.py \
	    $(if $(MSX_PRESERVATION),--msx-preservation $(MSX_PRESERVATION),) \
	    $(if $(ZEROBAS),--zerobas $(ZEROBAS),)

clean:
	rm -f $(IPS) $(BPS)

.PHONY: patches test clean
