# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

# zerobas — build the 16 KB cartridge ROM.
#
# Requires pasmo (the assembler C-BIOS uses). Build from the repo root so the
# `include` paths in basic/main.asm resolve.

PASMO ?= pasmo
SRC   := basic/main.asm
DEPS  := basic/interp.asm basic/title.asm basic/repl.asm basic/vars.asm basic/expr.asm \
         basic/poke.asm basic/clear.asm basic/usr.asm basic/print.asm basic/bload.asm \
         basic/program.asm basic/sysvars.inc
ROM   := basic.rom

$(ROM): $(SRC) $(DEPS)
	$(PASMO) --bin $(SRC) $(ROM)
	python3 tools/pad_rom.py $(ROM) 16384

clean:
	rm -f $(ROM)

# Slot-0 page-1 patches: ship zerobas patched into a stock C-BIOS main ROM, the
# real-hardware layout (BASIC next to the BIOS) instead of an external cartridge.
# Pass a stock ROM as STOCK=... or let build-patches.sh auto-detect openMSX's.
patches: $(ROM) build-patches.sh tools/rom_patch.py tools/overlay_page1.py
	sh build-patches.sh $(STOCK)

.PHONY: clean patches
