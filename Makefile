# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

# zerobas — build every deliverable.
#
# Requires pasmo (the assembler C-BIOS uses) and python3. Build from the repo
# root so the `include` paths in basic/main.asm resolve.
#
# `make` (the default `all` goal) builds every PORTABLE deliverable:
#   - build/basic.rom, build/disk.rom              (the ROMs)
#   - zerobas-msx1.ips/.bps                         (slot-0 page-1 BASIC patch)
#   - tape/zerobas-tape-msx1.ips/.bps              (page-0 cassette patch)
# The .ips/.bps patches need a stock C-BIOS main ROM to stamp/verify against;
# build-patches.sh auto-detects openMSX's bundled copy or takes STOCK=<path>.
#
# `make machines` is separate because openMSX machine configs are not portable
# files — they embed absolute paths to your openMSX ROMs and this repo — so they
# are an INSTALL into your openMSX user dir, not a build output. `make install`
# does `all` then `machines`.

# Build artifacts (ROMs) go under build/ -- a gitignored scratch dir -- so a
# stale copy never lingers in the repo root where tools/probes pick it up. The
# tracked patch deliverables (zerobas-msx1.ips/.bps) stay at the root.
BUILD := build

PASMO ?= pasmo
SRC   := basic/main.asm
DEPS  := basic/interp.asm basic/initext.asm basic/title.asm basic/repl.asm \
         basic/vars.asm basic/strvar.asm basic/expr.asm basic/poke.asm basic/vdpio.asm \
         basic/clear.asm basic/usr.asm basic/print.asm basic/screen.asm basic/list.asm \
         basic/fat.asm basic/bload.asm basic/cload.asm basic/save.asm basic/files.asm \
         basic/field.asm basic/printusing.asm basic/program.asm basic/sysvars.inc
ROM   := $(BUILD)/basic.rom

# zerobas-disk: a standalone 16 KB disk-interface ROM (not an IPS patch). Lives
# in internal slot 3-1; built with the same pasmo + pad_rom flow as basic.rom.
DISK_SRC := disk/disk.asm
DISK_ROM := $(BUILD)/disk.rom

# Tracked patch deliverables (regenerable; live at their committed paths).
PATCHES      := zerobas-msx1.ips zerobas-msx1.bps
TAPE_PATCHES := tape/zerobas-tape-msx1.ips tape/zerobas-tape-msx1.bps

# Default goal: every portable deliverable (ROMs + both patch pairs).
all: $(ROM) $(DISK_ROM) $(PATCHES) $(TAPE_PATCHES)

$(BUILD):
	mkdir -p $(BUILD)

$(ROM): $(SRC) $(DEPS) | $(BUILD)
	$(PASMO) --bin $(SRC) $(ROM)
	python3 tools/pad_rom.py $(ROM) 16384

$(DISK_ROM): $(DISK_SRC) | $(BUILD)
	$(PASMO) --bin $(DISK_SRC) $(DISK_ROM)
	python3 tools/pad_rom.py $(DISK_ROM) 16384

disk: $(DISK_ROM)

# --- Slot-0 page-1 BASIC patch (build/basic.rom spliced into a stock C-BIOS) ---
# build-patches.sh emits BOTH .ips and .bps in one run; express that with a
# single-recipe target plus a no-op follower (GNU make 3.81 has no grouped
# targets). Pass STOCK=<rom> or let the script auto-detect openMSX's copy.
zerobas-msx1.ips: $(ROM) build-patches.sh tools/rom_patch.py tools/overlay_page1.py
	sh build-patches.sh $(STOCK)
zerobas-msx1.bps: zerobas-msx1.ips
	@: # produced by the build-patches.sh run above

patches: $(PATCHES)

# --- Page-0 cassette patch (assembled from tape/tape.asm; its own sub-make) ----
tape/zerobas-tape-msx1.ips: tape/tape.asm tape/build-patches.sh tools/rom_patch.py
	$(MAKE) -C tape patches STOCK=$(STOCK)
tape/zerobas-tape-msx1.bps: tape/zerobas-tape-msx1.ips
	@: # produced by the tape sub-make above

tape-patches: $(TAPE_PATCHES)

# --- openMSX machine configs (INSTALL, not a portable build output) ------------
# Generate the release machines into your openMSX user dir: per C-BIOS MSX1
# region, a _BASIC (zerobas+tape) and a _BASIC_DISK (+ zerobas-disk in slot 3-1).
# The _ZEROBASDISK provider-oracle is a TEST machine, kept out of the release set
# (see machines-oracle). Configs embed absolute paths, so this is install-local.
machines: $(PATCHES) $(TAPE_PATCHES) $(DISK_ROM)
	python3 tools/install-openmsx-machine.py --disk-rom $(DISK_ROM)

# Test-only: also write the Tier-1 provider-oracle machine (real CF-3300 BIOS +
# zerobas-disk swapped into slot 3-1). Not a user-facing release config.
machines-oracle: $(PATCHES) $(TAPE_PATCHES) $(DISK_ROM)
	python3 tools/install-openmsx-machine.py --disk-rom $(DISK_ROM) --real-bios-disk

# Build everything portable, then install the openMSX machine configs.
install: all machines

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

# clean removes the gitignored build artifacts only. The tracked patch
# deliverables are left in place (use `make patches` to regenerate them).
clean:
	rm -rf $(BUILD)

.PHONY: all disk patches tape-patches machines machines-oracle install \
        test-dsk unit-test coverage clean
