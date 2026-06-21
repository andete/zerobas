# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

# zerobas — build the 16 KB cartridge ROM.
#
# Requires pasmo (the assembler C-BIOS uses). Build from the repo root so the
# `include` paths in basic/main.asm resolve.

PASMO ?= pasmo
SRC   := basic/main.asm
DEPS  := basic/interp.asm basic/initext.asm basic/title.asm basic/repl.asm \
         basic/vars.asm basic/strvar.asm basic/expr.asm basic/poke.asm basic/vdpio.asm \
         basic/clear.asm basic/usr.asm basic/print.asm basic/screen.asm basic/list.asm \
         basic/fat.asm basic/bload.asm basic/cload.asm basic/save.asm basic/program.asm \
         basic/sysvars.inc
ROM   := basic.rom

# zerobas-disk: a standalone 16 KB disk-interface ROM (not an IPS patch). Lives
# in internal slot 3-1; built with the same pasmo + pad_rom flow as basic.rom.
DISK_SRC := disk/disk.asm
DISK_ROM := disk.rom

$(ROM): $(SRC) $(DEPS)
	$(PASMO) --bin $(SRC) $(ROM)
	python3 tools/pad_rom.py $(ROM) 16384

$(DISK_ROM): $(DISK_SRC)
	$(PASMO) --bin $(DISK_SRC) $(DISK_ROM)
	python3 tools/pad_rom.py $(DISK_ROM) 16384

disk: $(DISK_ROM)

# A 720 KB FAT12 test image with deterministic content, for disk integration
# tests (see disk/TODO.md). Reproducible from the Microsoft FAT spec generator.
DISK_TEST_DSK := disk/test720.dsk

$(DISK_TEST_DSK): tools/make_test_dsk.py
	python3 tools/make_test_dsk.py $(DISK_TEST_DSK)

test-dsk: $(DISK_TEST_DSK)

# Host-side unit tests: execute the real assembled Z80 against an embedded Z80
# core — no emulator. Each test assembles to /tmp itself, so this needs no other
# target. tests/run.py auto-discovers every tests/test_*.py. See tests/README.md.
unit-test:
	python3 tests/run.py

# Code-coverage report for the unit tests: monkeypatches the Z80 core's step()
# to log executed opcode addresses (no production change), then buckets them
# against the symbol table to report per-routine entry coverage. See
# tests/coverage.py.
coverage:
	python3 tests/coverage.py

clean:
	rm -f $(ROM) $(DISK_ROM)

# Slot-0 page-1 patches: ship zerobas patched into a stock C-BIOS main ROM, the
# real-hardware layout (BASIC next to the BIOS) instead of an external cartridge.
# Pass a stock ROM as STOCK=... or let build-patches.sh auto-detect openMSX's.
patches: $(ROM) build-patches.sh tools/rom_patch.py tools/overlay_page1.py
	sh build-patches.sh $(STOCK)

.PHONY: clean patches disk test-dsk unit-test coverage
