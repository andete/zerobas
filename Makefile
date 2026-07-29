# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

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
# tools/build_patches.py auto-detects openMSX's bundled copy or takes STOCK=<path>.
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
# basic/tokenise.inc + basic/detok.inc: include'd by interp.asm/list.asm (and
# by sub/sub.asm/sub/detok.asm for the sub-ROM's own copies, SUB_PARTS below)
# but were NOT tracked as prerequisites -- the same staleness class as the
# str-engine.asm/input.asm gap the empty-expr slice fixed (ba652b7). Caught
# here (math pack slice 2c, docs/spec-basic-mathpack-slice2.md §13.3) because
# `^` is the first math-pack change to touch the tokeniser/detokeniser at all
# (SQR/ATN/EXP/LOG are $FF-prefixed function tokens, reached via kwtable, not
# tk_notkw's single-char operator chain) -- without this, an edit to either
# file could silently ship a stale basic.rom/sub.rom.
DEPS  := basic/interp.asm basic/initext.asm basic/title.asm basic/repl.asm \
         basic/vars.asm basic/strvar.asm basic/str-engine.asm basic/expr.asm basic/poke.asm basic/vdpio.asm \
         basic/clear.asm basic/usr.asm basic/time.asm basic/print.asm basic/screen.asm basic/list.asm \
         basic/fat.asm basic/bload.asm basic/cload.asm basic/save.asm basic/files.asm \
         basic/field.asm basic/format.asm basic/printusing.asm basic/program.asm basic/float.asm \
         basic/float-arith.asm basic/subromcall.asm basic/input.asm \
         basic/arrays.asm basic/sound.asm basic/play.asm basic/graphics.asm basic/traps.asm \
         basic/missing.asm \
         basic/tokenise.inc basic/detok.inc basic/pu-render.inc basic/format-body.inc \
         basic/fat-prim-body.inc basic/fat-delete-body.inc \
         basic/randio-body.inc basic/fld-fill-body.inc \
         basic/lineedit-body.inc \
         basic/casmatch-body.inc basic/cal-refill-body.inc \
         basic/fcbname-body.inc basic/bload-body.inc basic/fatio-body.inc \
         basic/sv-bsvdisk.inc basic/sv-bsvcas.inc basic/sv-savdisk.inc basic/sv-tsb.inc \
         basic/sv-tputw.inc basic/sv-tne.inc basic/sv-diskwr.inc \
         basic/fatiocreate-body.inc basic/fatiow-body.inc \
         basic/readdata-body.inc basic/tokskip-body.inc \
         basic/sysvars.inc
ROM   := $(BUILD)/basic.rom

# zerobas-disk: a standalone 16 KB disk-interface ROM (not an IPS patch). Lives
# in internal slot 3-1; built with the same pasmo + pad_rom flow as basic.rom.
DISK_SRC := disk/disk.asm
# disk.asm is an orchestrator that `include`s these parts (assembled with -I disk);
# listed as prerequisites so a change to any part triggers a rebuild.
DISK_PARTS := disk/equates.inc disk/init.asm disk/pageenv.asm disk/driver.asm \
              disk/fat.asm disk/kernel.asm disk/runtime.asm
DISK_ROM := $(BUILD)/disk.rom

# zerobas-sub: the built-in MSX2-style sub-ROM, a standalone 32 KB ROM spanning
# BOTH pages of an internal expanded subslot (slot 3-2 on the merged machine).
# Ships as a plain .rom like disk.rom (no IPS, no C-BIOS interaction). S2a is the
# empty skeleton (CD header + one round-trip ping per page); real tenants arrive
# with the eviction session. See docs/spec-basic-subrom.md.
SUB_SRC   := sub/sub.asm
# basic/kwtable.inc: sub/sub.asm includes it (the sole resident copy, wave 3 --
# see check_kwtable_identity.py); missing this prerequisite let a kwtable-only
# edit silently ship a STALE sub.rom (caught 2026-07-12, math pack slice 1a: a
# new keyword crunched fine on the reference but parsed as a bare variable on
# zerobas because sub.rom hadn't picked up the new kwtable.inc entries).
# sub/fp_sqrt.asm + sub/basic-resident-abi.inc (subrom-mathpack arc): the SQR
# tenant body + its GENERATED resident-ABI import (tools/gen_resident_abi.py,
# rule below) -- same staleness hazard as kwtable.inc above, same fix (a real
# prerequisite so a stale sub.rom cannot silently ship).
# sub/fp_atan.asm + sub/math-coeffs.inc (math pack slice 2a, docs/spec-basic-
# mathpack-slice2.md §11): the ATN tenant body + its GENERATED FPNUM coefficient
# table (tools/gen_math_coeffs.py, rule below) -- same staleness hazard, same fix.
# sub/fp_exp.asm + sub/fp_log.asm (math pack slice 2b, docs/spec-basic-mathpack-
# slice2.md §12): the EXP/LOG tenant bodies -- same staleness hazard, same fix
# (math-coeffs.inc already listed above covers their shared coefficient tables).
# sub/fp_pow.asm (math pack slice 2c, docs/spec-basic-mathpack-slice2.md §13):
# the `^` tenant body -- same staleness hazard, same fix. Also adds
# basic/tokenise.inc + basic/detok.inc (the sub-ROM's own tokeniser/detok
# copies, sub/sub.asm/sub/detok.asm) -- see the DEPS comment above for why.
# sub/fp_sin.asm (math pack slice 2d, docs/spec-basic-mathpack-slice2.md §14):
# the SIN/COS/TAN tenant body (shared sincos_kernel) -- same staleness hazard,
# same fix.
# sub/fp_rnd.asm (math pack slice 2e, docs/spec-basic-mathpack-slice2.md §15):
# the LAST page-1 tenant, RND(x) -- same staleness hazard, same fix.
# sub/arrays.asm (arrays slice-1 SPLIT design, docs/spec-basic-arrays.md §10):
# the numeric-array engine tenant (page-0, SUBROM_IDX_ARY) -- same staleness
# hazard, same fix.
# sub/strheap.asm (arrays slice-4a string-heap tenant) + sub/detok.asm (the
# wave-3 detokeniser tenant body): BOTH were MISSING here since their
# introduction -- an edit to either silently shipped a STALE sub.rom (caught
# 2026-07-17, slice-4c adversarial review: a revert-and-observe experiment on
# sub/strheap.asm did not rebuild sub.rom, so the machine probes ran the
# reverted GC walk after the source was restored). Same staleness hazard as
# kwtable.inc above, same fix (real prerequisites).
# sub/format.asm + basic/format-body.inc (CALL FORMAT eviction, docs/spec-
# evict-call-format.md): the build/write-engine tenant body + its shared
# .inc with the lean cart's inline copy -- same staleness hazard, same fix.
# sub/errtrap.asm (scan_stmt_end, error-handling S2b RESUME NEXT, docs/spec-
# basic-error-handling-s2b-packet.md §5.5): same staleness hazard, same fix
# ([[makefile-subparts-stale-tenant]] -- a sub include missing from SUB_PARTS
# silently ships a STALE sub.rom).
# sub/fatprim.asm + basic/fat-prim-body.inc + basic/fat-delete-body.inc
# (FAT12 primitive/sector-layer eviction, docs/spec-evict-diskfile-cluster.md
# §11, Phase 1): the tenant body + its two shared .inc files (the lean cart's
# inline copies) -- same staleness hazard, same fix.
# sub/dirverb.asm (KILL/NAME directory-verb I/O bodies, docs/spec-evict-
# diskfile-cluster.md §12, Phase 2): a self-contained tenant (no new .inc -- it
# reuses fatprim's already-listed primitive bodies sub-locally); the lean cart
# keeps its verb-body copies inline in basic/files.asm -- same staleness hazard,
# same fix.
# sub/randio.asm + basic/randio-body.inc + basic/fld-fill-body.inc (fat_rand_*
# random-access record engine, docs/spec-eviction-g4-space.md §3, carve #1 of
# the G4-space eviction slice): the tenant body + its two shared .inc files
# (the lean cart's inline copies, basic/field.asm) -- same staleness hazard,
# same fix ([[makefile-subparts-stale-tenant]]).
# sub/lineedit.asm + basic/lineedit-body.inc (numbered-line editor TXTTAB-
# memmove engine, docs/spec-eviction-g4-space.md §4, carve #2 of the
# G4-space eviction slice): the tenant body + its shared .inc file (the lean
# cart's inline copy, basic/program.asm) -- same staleness hazard, same fix.
# sub/casmatch.asm + basic/casmatch-body.inc + basic/cal-refill-body.inc
# (cassette Tier-3 name-match/data-skip engine, docs/spec-eviction-g5-
# space.md, the G5-space eviction slice): the tenant body + its two shared
# .inc files (the lean cart's inline copies, basic/cload.asm) -- same
# staleness hazard, same fix ([[makefile-subparts-stale-tenant]]).
# sub/save.asm + basic/sv-*.inc + basic/fatiocreate-body.inc + basic/fatiow-body.inc
# (the SAVE/BSAVE/CSAVE WRITE engines, docs/decision-fund-time-and-t5.md
# D-FUND-1, the TIME+T5 funding carve): the tenant body, its five carved engine
# bodies (the lean cart's inline copies, basic/save.asm) and the two shared
# copies the tenant needs sub-locally -- same staleness hazard, same fix.
# sub/fldlook.asm (the FIELDed-variable READ hook's pure-RAM half, docs/
# decision-clearpool-funding.md -- the D-CLP funding carve): a self-contained
# tenant (no shared .inc; the lean cart keeps its own differently-shaped inline
# copy in basic/field.asm) -- same staleness hazard, same fix.
# sub/fcbname.asm + basic/fcbname-body.inc (disk 8.3-FCB-name builder
# build_83_name, docs/spec-basic-interrupt-traps.md §10.4, the interrupt-traps
# T1 funding carve): the tenant body + its shared .inc file (the lean cart's
# inline copy, basic/bload.asm) -- same staleness hazard, same fix.
SUB_PARTS := sub/equates.inc sub/deftype.asm sub/tkfloat.asm sub/fp_sqrt.asm sub/fp_atan.asm \
             sub/fp_exp.asm sub/fp_log.asm sub/fp_pow.asm sub/fp_sin.asm \
             sub/fp_rnd.asm sub/arrays.asm sub/strheap.asm sub/detok.asm \
             sub/printusing.asm basic/pu-render.inc \
             sub/format.asm basic/format-body.inc \
             sub/errtrap.asm \
             sub/fatprim.asm basic/fat-prim-body.inc basic/fat-delete-body.inc \
             sub/dirverb.asm sub/randio.asm sub/fiawalk.asm basic/fiawalked-body.inc basic/randio-body.inc basic/fld-fill-body.inc \
             sub/lineedit.asm basic/lineedit-body.inc \
             sub/casmatch.asm basic/casmatch-body.inc basic/cal-refill-body.inc \
             sub/fcbname.asm basic/fcbname-body.inc \
             sub/fldlook.asm \
             sub/bload.asm basic/bload-body.inc basic/fatio-body.inc \
             sub/save.asm basic/sv-bsvdisk.inc basic/sv-bsvcas.inc basic/sv-savdisk.inc \
             basic/sv-tsb.inc basic/sv-tputw.inc basic/sv-tne.inc basic/sv-diskwr.inc \
             basic/fatiocreate-body.inc basic/fatiow-body.inc \
             sub/circleparse.asm \
             sub/readdata.asm basic/readdata-body.inc basic/tokskip-body.inc \
             sub/beep.asm sub/title.asm basic/title-body.inc \
             sub/playparse.asm sub/graphics.asm \
             sub/math-coeffs.inc basic/sysvars.inc basic/kwtable.inc \
             basic/tokenise.inc basic/detok.inc \
             sub/basic-resident-abi.inc
SUB_ROM   := $(BUILD)/sub.rom

# Tracked patch deliverables (regenerable; live at their committed paths).
PATCHES      := zerobas-msx1.ips zerobas-msx1.bps
TAPE_PATCHES := tape/zerobas-tape-msx1.ips tape/zerobas-tape-msx1.bps

# Default goal: every portable deliverable (ROMs + both patch pairs).
all: $(ROM) $(DISK_ROM) $(SUB_ROM) $(PATCHES) $(TAPE_PATCHES)

$(BUILD):
	mkdir -p $(BUILD)

$(ROM): $(SRC) $(DEPS) | $(BUILD)
	$(PASMO) --bin $(SRC) $(ROM)
	python3 tools/pad_rom.py $(ROM) 16384

$(DISK_ROM): $(DISK_SRC) $(DISK_PARTS) | $(BUILD)
	$(PASMO) -I disk --bin $(DISK_SRC) $(DISK_ROM)
	python3 tools/pad_rom.py $(DISK_ROM) 16384

disk: $(DISK_ROM)

# zerobas-sub: assembled with `pasmo -I sub` (its includes resolve under sub/);
# the source spans $0000-$7FFF so pad_rom just asserts the 32 KB size.
SUB_SYM   := $(BUILD)/sub.sym
$(SUB_ROM): $(SUB_SRC) $(SUB_PARTS) | $(BUILD)
	$(PASMO) -I sub --bin $(SUB_SRC) $(SUB_ROM) $(SUB_SYM)
	python3 tools/pad_rom.py $(SUB_ROM) 32768

sub: $(SUB_ROM)

# --- Relocated BASIC proof (cbios-repack arc, WS-2 / S3) -----------------------
# $(RELOC_SYM)/$(RELOC_ROM) get their OWN file rule here (depending ONLY on the
# BASIC sources, NEVER on $(SUB_ROM)) so sub/basic-resident-abi.inc below can
# depend on $(RELOC_SYM) without creating a BUILD-GRAPH CYCLE: $(SUB_ROM)
# depends on the .inc (via SUB_PARTS), the .inc depends on $(RELOC_SYM) -- so
# $(RELOC_SYM) must never depend back on $(SUB_ROM), directly or through the
# old phony `basic-reloc` (which used to build RELOC_SYM itself while ALSO
# depending on $(SUB_ROM) for its own cross-checks -- that shape is exactly
# the cycle this split avoids; same class of fix as the earlier $(MAIN_ROM)
# real-file-rule change). The `basic-reloc` PHONY target (further down) still
# depends on $(RELOC_SYM)/$(SUB_ROM) for ITS OWN cross-checks, which is fine --
# phony targets are never anyone else's prerequisite.
RELOC_ROM := $(BUILD)/basic-reloc.rom
RELOC_SYM := $(BUILD)/basic-reloc.sym
$(RELOC_SYM): basic/main-reloc.asm basic/main.asm $(DEPS) | $(BUILD)
	$(PASMO) --bin basic/main-reloc.asm $(RELOC_ROM) $(RELOC_SYM)
# Grouped-target workaround (GNU make 3.81 has no `&:`): $(RELOC_SYM)'s recipe
# above produces BOTH files; this is a no-op follower, same pattern as the
# zerobas-msx1.ips/.bps pair below.
$(RELOC_ROM): $(RELOC_SYM)
	@: # produced by the pasmo run above

# --- Resident-ABI import (subrom-mathpack arc, spec §4) ------------------------
# fp_sqrt (sub/fp_sqrt.asm, the first page-1 tenant) calls back into 9 main-ROM
# page-0-resident routines; their absolute addresses live in $(RELOC_SYM) and
# shift whenever the page-0 low region changes. This generated .inc is a real
# prerequisite of $(SUB_ROM) (via SUB_PARTS below) — depends on $(RELOC_SYM)
# only (never $(SUB_ROM) -- see the cycle note above).
sub/basic-resident-abi.inc: $(RELOC_SYM) tools/gen_resident_abi.py
	python3 tools/gen_resident_abi.py $(RELOC_SYM) sub/basic-resident-abi.inc

# --- Math-pack coefficient generator (math pack slice 2a, spec §11.3 point 3) --
# fp_atan's ATAN_COEF/PI_2/PI_6/SQRT3/BREAK FPNUM records are a deterministic own
# decimal-minimax fit (tools/gen_math_coeffs.py; no reloc-sym dependency, unlike
# the resident-ABI import above -- it needs no build artifact, just the tool
# itself), so a real prerequisite here (mirroring the resident-ABI rule) means an
# edit to the generator can never leave a stale sub/math-coeffs.inc silently
# shipping in $(SUB_ROM) (same staleness class as the kwtable.inc/resident-ABI
# fixes above).
sub/math-coeffs.inc: tools/gen_math_coeffs.py
	python3 tools/gen_math_coeffs.py --emit

# --- Standing resident-ABI consistency gate (spec §4.3/§8 sign-off) ------------
# STRONG assert: re-runs the SAME generator against the CURRENT basic-reloc.sym
# and diffs the result against the on-disk sub/basic-resident-abi.inc, catching
# a stale .inc (and therefore a stale sub.rom calling wrong addresses) that the
# build-order dependency above should prevent but a partial/interrupted build
# or a hand-edit might not. Also run as a step of `basic-reloc` below.
subrom-abi-check: sub/basic-resident-abi.inc $(RELOC_SYM)
	python3 tools/check_resident_abi.py $(RELOC_SYM) sub/basic-resident-abi.inc

# --- Standing closure gates for sub-ROM tenants (both page directions) ---------
# CALSLT switches only the called page, so the two flavours have OPPOSITE
# visibility. PAGE-1: a page-1 tenant runs with main page 1 switched OUT, so the
# transitive closure of the resident-ABI surface it calls must be page-0-resident
# (< $4000) -- two escapes (cmp16_bits, div10) hung the tenant before this gate.
# PAGE-0 (--page0): a page-0 tenant (detok/arrays/strheap/printusing) runs with
# slot-0 page 0 (BIOS + low region + ISR) switched OUT, so it must reach only
# sub-local page-0 code / main page-1 / RAM -- never the main low region
# ($2812-$3FFF), the BIOS, or the sub's own page 1. PAGE-1 TENANT WALK
# (--page1, added for the CALL FORMAT eviction, docs/spec-evict-call-format.md
# §6): the mirror of --page0 -- walks the SUB call graph from sub_p1_table
# (fp_sqrt..fp_rnd, format_tenant) and fails on a callee that is main-BASIC
# page-1 (switched out) or the sub's own page-0 island (also unmapped). This
# is DISTINCT from the unflagged default above, which only audits the
# resident-ABI IMPORT LIST and never walks a tenant that imports nothing from
# it (format_tenant is a pure RAM+BIOS leaf). All three are steps of
# `basic-reloc`.
subrom-closure-check: sub/basic-resident-abi.inc $(RELOC_SYM) $(SUB_ROM)
	python3 tools/check_tenant_closure.py $(RELOC_SYM) sub/basic-resident-abi.inc
	python3 tools/check_tenant_closure.py --page0 $(SUB_SYM) sub/sub.asm
	python3 tools/check_tenant_closure.py --page1 $(SUB_SYM) sub/sub.asm

# Assemble the $2812-based variant (basic/main-reloc.asm) and prove it lands the
# "AB" header at $4000 and matches the shipping page-1 body byte-for-byte. This is
# a proof/staging target only -- deliberately NOT in `all`; the merged main-ROM
# splice that ships it is WS-3 (S4). See docs/cbios-repack-ws2-audit.md.
basic-reloc: $(ROM) $(RELOC_SYM) $(RELOC_ROM) $(SUB_ROM)
	python3 tools/check_reloc.py $(RELOC_ROM) $(ROM) $(RELOC_SYM)
	python3 tools/check_kwtable_identity.py $(RELOC_ROM) $(RELOC_SYM) $(SUB_ROM) $(SUB_SYM)
	python3 tools/check_resident_abi.py $(RELOC_SYM) sub/basic-resident-abi.inc
	python3 tools/check_tenant_closure.py $(RELOC_SYM) sub/basic-resident-abi.inc
	python3 tools/check_tenant_closure.py --page0 $(SUB_SYM) sub/sub.asm
	python3 tools/check_tenant_closure.py --page1 $(SUB_SYM) sub/sub.asm

# --- Merged repack main ROM (WS-3 / D4) ---------------------------------------
# The 32 KB slot-0 "main ROM": repacked C-BIOS + relocated BASIC ($2812-$7FFF) +
# tape, built reproducibly from the user's C-BIOS checkout (CBIOS=<path>; no
# C-BIOS bytes in-repo). NOT in `all` -- it needs that external checkout. The
# patch pair diffs the merged image vs the pristine stock from the same pinned tag.
CBIOS ?= ~/projects/cbios
MAIN_ROM   := $(BUILD)/zerobas-main-eu.rom
MAIN_PATCHES := zerobas-main-eu.ips zerobas-main-eu.bps
# Real file rule so `repack-machine` (and every *-acceptance gate that depends on
# it) rebuilds the merged main ROM when any BASIC source changes — previously
# $(MAIN_ROM) had no rule, so a stale zerobas-main-eu.rom was silently reinstalled
# after a basic/*.asm edit and gates tested STALE BASIC ([[ips-rebuild-after-basic-change]]).
# $(DEPS) already lists float-arith.asm/expr.asm/sysvars.inc, so float/math slices
# now retrigger correctly. `repack-main` stays a phony alias for existing callers.
$(MAIN_ROM): basic/main-reloc.asm basic/main.asm $(DEPS) tape/tape.asm \
             tools/build_patches.py tools/build_mainrom.py tools/build_repacked_cbios.py | $(BUILD)
	python3 tools/build_patches.py --main --cbios $(CBIOS)
repack-main: $(MAIN_ROM)
repack-boot: repack-main $(SUB_ROM)
	python3 probes/basic/basic_probe_repack_boot.py

# --- Slot-0 page-1 BASIC patch (build/basic.rom spliced into a stock C-BIOS) ---
# build_patches.py emits BOTH .ips and .bps in one run; express that with a
# single-recipe target plus a no-op follower (GNU make 3.81 has no grouped
# targets). Pass STOCK=<rom> or let the tool auto-detect openMSX's copy.
zerobas-msx1.ips: $(ROM) tools/build_patches.py tools/openmsx_paths.py \
                  tools/rom_patch.py tools/overlay_page1.py
	python3 tools/build_patches.py $(STOCK)
zerobas-msx1.bps: zerobas-msx1.ips
	@: # produced by the build_patches.py run above

patches: $(PATCHES)

# --- Page-0 cassette patch (assembled from tape/tape.asm; its own sub-make) ----
tape/zerobas-tape-msx1.ips: tape/tape.asm tools/build_patches.py tools/openmsx_paths.py \
                            tools/rom_patch.py
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

# Heavy openMSX oracle probes (the reproduction half of the mission; see
# probes/README.md). Unlike unit-test these BOOT openMSX and need the installed
# machines (`make machines-oracle`) plus YOUR own reference ROMs (VG-8020,
# CF-3300) — those are never shipped. `probe` smoke-runs one probe per component.
probe: $(ROM) $(DISK_ROM) $(DISK_TEST_DSK)
	cp $(DISK_TEST_DSK) /tmp/zerobas-probe.dsk
	python3 probes/disk/disk_probe_dskio.py --dsk /tmp/zerobas-probe.dsk
	python3 probes/basic/basic_probe_print.py --cart $(ROM)
	python3 probes/tape/bios_probe_tapwrite.py --out /tmp/zerobas-tapwrite.rom
	@echo "probe smoke OK (disk + basic + tape)"

# Standing BDOS acceptance gate: replays the BDOSX/2/3/0 exercisers and asserts
# each still converges 0-byte-identical to the stock oracle (turns the one-shot
# M19-M26 differentials into a re-runnable regression gate). HEAVY + oracle-
# dependent like `probe` (needs `make machines-oracle` + your CF-3300 reference
# ROMs); NOT part of the emulator-free `unit-test`. `make bdos-acceptance ONLY=BDOSX3`
# scopes it to one exerciser.
bdos-acceptance: $(DISK_ROM)
	python3 probes/disk/disk_bdos_acceptance.py $(if $(ONLY),--only '$(ONLY)',)

# Standing Disk-BASIC acceptance gate: the BASIC-side counterpart of bdos-acceptance.
# Replays the self-asserting disk_probe_* differentials over the Disk-BASIC verb
# surface (FILES/OPEN/FIELD/GET/PUT/SAVE/LOAD/...) and asserts each still converges to
# the oracle. HEAVY + oracle-dependent (needs `make machines-oracle` + the seed image
# + your CF-3300 reference ROMs); NOT part of the emulator-free `unit-test`. Scope with
# `make diskbasic-acceptance ONLY=FIELD`. See disk/docs/diskbasic-acceptance-spec.md.
diskbasic-acceptance: $(DISK_ROM) $(DISK_TEST_DSK)
	python3 probes/disk/diskbasic_acceptance.py $(if $(ONLY),--only '$(ONLY)',)

# --- REPACK acceptance: the SAME Disk-BASIC corpus on the relocated BASIC build ----
# (string-engine arc.) The lean gate above proves the 16 KB basic.rom; this proves the
# merged repack ROM (build/zerobas-main-eu.rom — relocated BASIC $2812-$7FFF, STRMAX=64,
# concat-aware str_eval, relocated kwtable) against the SAME CF-3300 oracle. The disk
# verbs flow through the changed str_eval / newly-tokenised keywords, so lean-converges
# does NOT imply repack-converges. Mechanism: an EXTRA machine file (repack-machine) plus
# the probes' now-optional machine name — each probe's zerobas-BASIC machine default reads
# $ZEROBAS_BASIC_MACHINE (falling back to its lean literal), so setting it here points the
# whole corpus at the repack machine while the CF-3300 oracle side is untouched. The runner
# refuses to start (vacuity guard) if any registry probe fails to honour the env var. Same
# deps as the lean gate (machines-oracle + seed + CF-3300).
#
# There is deliberately NO bdos-acceptance-repack: the BDOS gate exercises the disk ROM
# (build/disk.rom) under the real CF-3300 BIOS — the string-engine arc does not touch the
# disk ROM, so BDOS behaviour is identical across the lean and repack BASIC builds.
REPACK_MACHINE  := C-BIOS_MSX1_EU_REPACK_DISK
repack-machine: $(MAIN_ROM) $(DISK_ROM) $(SUB_ROM)
	python3 tools/install-repack-machine.py --merged $(MAIN_ROM) --disk-rom $(DISK_ROM) \
	  --sub-rom $(SUB_ROM)

diskbasic-acceptance-repack: $(DISK_ROM) $(DISK_TEST_DSK) repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) \
	  python3 probes/disk/diskbasic_acceptance.py $(if $(ONLY),--only '$(ONLY)',)

# --- FAT-primitive ERROR-disposition gate (the half diskbasic-acceptance misses) --
# The 34 verbs above are oracle differentials over the SUCCESS path. They stay
# 34/34 GREEN with the repack shim layer's error tail deliberately neutered
# (`scf` -> `or a` in fatprim_bounce, basic/fat.asm) -- proved by experiment on
# 2026-07-27 during the shim collapse. This gate measures the other disposition:
# seven verbs at a nonexistent filename, each of which must reach STATUS != 0 in
# the tenant and come back Cy=1. With the tail neutered, FOUR of the seven report
# NOTHING AT ALL, which is what makes them a real instrument rather than a
# restatement of the success path. Self-check against zerobas's own lowercase
# `load error` on purpose: that wording is a DOCUMENTED divergence from the
# reference's "File not found", so an oracle differential here would fail on the
# divergence instead of on the disposition under test.
fat-error-acceptance: $(DISK_ROM) repack-machine
	python3 probes/disk/disk_probe_fat_error_disposition.py \
	        --machine $(REPACK_MACHINE)

# --- Standing sub-ROM boot gate (zerobas-sub arc, S2a) -------------------------
# Proves the built-in sub-ROM's discovery + two-page CALSLT ABI end-to-end with
# NO main-ROM change (the main-ROM boot-scan + dispatch land in the eviction
# session, S2b). Boots a minimal C-BIOS MSX1 with slot 3 expanded (3-0 = RAM,
# 3-2 = build/sub.rom), injects a 44-byte stub, and CALSLTs each page's entry
# ($0010 page 0 -> tag $C0, $4010 page 1 -> tag $C1). HEAVY (boots openMSX) but
# needs only openMSX's bundled C-BIOS ROMs -- NOT the merged main ROM, reference
# ROMs, or a disk image. NOT part of the emulator-free `unit-test`.
subrom-acceptance: $(SUB_ROM)
	python3 probes/basic/basic_probe_subrom_boot.py

# --- Interrupt-trampoline gate (subrom trampoline slice) -----------------------
# Proves a page-0 sub-ROM tenant can run EI: the shipped merged machine installs
# the RAM interrupt trampoline at boot (init_ext_roms -> sub_int_install), then the
# probe CALSLTs the self-test tenant (index 3), which spins under EI and returns the
# JIFFY delta serviced through the sub-ROM's own $0038. Asserts delta >= 1. Depends
# on repack-machine (the C-BIOS_MSX1_EU_REPACK_DISK machine with the sub-ROM in 3-2).
# docs/spec-basic-subrom-trampoline.md.
subrom-inttest: repack-machine
	python3 probes/basic/basic_probe_subrom_inttest.py

# --- Graphics G1 floor gate (graphics arc, docs/spec-basic-graphics-g1.md) -----
# Proves the SCREEN-2 geometry engine's architectural floor on the shipped merged
# machine: the probe CALSLTs the page-0 graphics self-test (index 8), which writes
# an 8 KB VRAM block via the di-guarded direct-port primitives while running EI,
# reads it all back, and reports the JIFFY delta + mismatch count. Asserts delta>=1
# (interrupts serviced mid-draw) AND mismatch=0 (the address-latch race is closed).
# The teeth check `make graphics-floor-teeth` rebuilds the sub-ROM with the guard
# stripped (pasmo --equ GFX_UNGUARDED=1) and asserts the gate then FAILs.
graphics-floor-acceptance: repack-machine
	python3 probes/basic/basic_probe_graphics_floor.py

# WIRING FIX (G7, 2026-07-22): this rule used to export ZB_GFX_UNGUARDED=1 and
# run the probe -- but NOTHING read that variable, so it ran the ordinary GUARDED
# sub-ROM and could only ever report FAIL. The teeth check now actually builds an
# unguarded sub.rom, installs it, runs the probe, and puts the real machine back
# whatever the outcome.
graphics-floor-teeth: $(MAIN_ROM) $(DISK_ROM) $(SUB_ROM)
	$(PASMO) -I sub --equ GFX_UNGUARDED=1 --bin $(SUB_SRC) $(BUILD)/sub-unguarded.rom
	python3 tools/pad_rom.py $(BUILD)/sub-unguarded.rom 32768
	python3 tools/install-repack-machine.py --merged $(MAIN_ROM) --disk-rom $(DISK_ROM) \
	  --sub-rom $(BUILD)/sub-unguarded.rom
	python3 probes/basic/basic_probe_graphics_floor.py --expect-fail; st=$$?; \
	  $(MAKE) --no-print-directory repack-machine >/dev/null; exit $$st

# --- Graphics G2 acceptance (PSET/PRESET/POINT VG-8020 differential) ----------
# The load-bearing gate for the pixel op (docs/spec-basic-graphics-g2.md §8): draws
# PSET/PRESET on BOTH the VG-8020 reference and the merged zerobas build, reads the
# pattern AND colour planes back, and asserts byte-identical results -- the colour
# plane is where the 8-pixel colour clash lives (a pattern-only check would pass a
# wrong-attribute plot). Phase B differentials the clip/error/POINT/STEP behaviour.
# Repack-only + oracle-dependent (boots openMSX; needs your VG-8020 reference ROM);
# NOT part of the emulator-free `unit-test`.
graphics-acceptance: repack-machine
	python3 probes/basic/basic_probe_graphics.py

# --- Keyword-completeness SWEEP (the coverage denominator, NOT a pass/fail gate) ---
# Sweeps the whole MSX1 reserved-word set in two layers and reports which words are
# absent and what a program actually observes -- docs/kwsweep-msx1-coverage.md.
# Deliberately NOT wired into any acceptance gate: its expected state is "34 words
# absent", so it exits 0 with findings rather than failing. What it IS good for is
# re-running after a keyword lands, to confirm the word moved out of the gap list on
# its own (TIME did exactly that between the 2026-07-26 runs).
# Two layers because neither is sufficient alone, and this repo owns both counter-
# examples: crunch-only would call INTERVAL missing (it is the compound INT+"ER"+VAL,
# and it works), while a carelessly written execute-only case called TAB( present --
# `PRINT TAB(99999)` raises ERR 6 on BOTH sides, for structurally different reasons.
# Non-zero exit means the APPARATUS failed (control group, or the ROMs changed
# mid-run), not that coverage regressed. Repack-only + oracle-dependent (boots
# openMSX; needs your VG-8020 reference ROM); NOT part of `unit-test`.
kwsweep: repack-machine
	python3 probes/basic/basic_probe_kwsweep.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- Logical-operator characterization + gate (AND/OR/XOR/EQV/IMP/NOT) ------------
# `logicops-characterize` is the MEASUREMENT run behind
# docs/logicops-vg8020-characterization.md: semantics, precedence (every ordered
# pair, three measured lines each), associativity, the int16 operand domain, and the
# boundaries with the relational/arithmetic/NOT layers. Rows built only from the
# operators zerobas already implements run on BOTH machines as a CALIBRATION battery
# -- if that is red the apparatus is what is broken and no reading from the run is
# trustworthy.
#
# `logicops-acceptance` adds --gate, which promotes EQV/IMP to "implemented" and so
# turns EVERY row into a two-sided differential. That is the standing gate for the
# slice. It is falsifiable by construction: deleting the `cpl` from lg_eqv takes it
# from 156/156 to 115/156.
#
# Repack-only (the lean cart ships without EQV/IMP) + oracle-dependent (boots
# openMSX; needs your VG-8020 reference ROM); NOT part of `unit-test`.
logicops-characterize: repack-machine
	python3 probes/basic/basic_probe_logicops.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

logicops-acceptance: repack-machine
	python3 probes/basic/basic_probe_logicops.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- Cursor / PRINT-positioning characterization (CSRLIN, POS, TAB(, SPC() -------
# The measurement behind docs/cursor-vg8020-characterization.md. Values via the
# bracket convention, POSITIONS via the SCREEN 0 grid (whitespace is invisible to
# a value readout), errors via the text after the echo. Every positional row pins
# `WIDTH 40` first: the two machines BOOT AT DIFFERENT WIDTHS (reference 37,
# zerobas 39, D-CUR-2), and comparing absolute columns across two text widths
# measures that instead of TAB(/SPC(.
#
# Repack-only + oracle-dependent (boots openMSX; needs your VG-8020 reference
# ROM); NOT part of `unit-test`.
cursor-characterize: repack-machine
	python3 probes/basic/basic_probe_cursor.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

cursor-acceptance: repack-machine
	python3 probes/basic/basic_probe_cursor.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- BIN$ / FRE characterization (the last two SILENT-GAP words) ---------------
# The measurement behind docs/binfre-vg8020-characterization.md. BIN$ is a pure
# function, so it is calibrated against HEX$/OCT$ -- the family members already
# implemented on BOTH sides, which pin its whole argument and error contract with
# code that is not under test (and which turned up D-BF-1/D-BF-2 doing it).
#
# FRE reports MEMORY, and the two machines do not have the same memory. It is
# measured through RELATIONS, plus the one absolute `CLEAR n` makes comparable by
# PINNING the string pool -- the same move `WIDTH 40` is for the cursor cluster.
# Rows that measure the reference evaluator's own 6-byte-per-level stack frame,
# and absolute FRE values, are reported but NEVER gated.
#
# Repack-only + oracle-dependent (boots openMSX; needs your VG-8020 reference
# ROM); NOT part of `unit-test`.
binfre-characterize: repack-machine
	python3 probes/basic/basic_probe_binfre.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

binfre-acceptance: repack-machine
	python3 probes/basic/basic_probe_binfre.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- MISSING class: LOCATE / SWAP / TRON / TROFF / MOTOR ----------------------
# The measurement behind docs/missing-vg8020-characterization.md. With the
# SILENT-GAP class empty (2facfc0), these five statements are the whole of what
# remains of the keyword arc that is a SLICE rather than an arc -- `DEF FN`/`FN`
# is deliberately out of scope.
#
# The risk here is the INVERSE of the SILENT-GAP slices: zerobas raises an honest
# `syntax error`, so nothing is silently wrong; what is unknown is what the
# REFERENCE does. Four of the five have surfaces that are easy to guess wrong --
# LOCATE's omittable arguments and WIDTH-relative bound, SWAP's type-equality
# granularity, TRON's decoration format and scope, and MOTOR's accepted forms.
#
# TWO readouts are deliberately NOT the usual bracket span: trace rows read the
# WHOLE SCREEN (the reference's own TRON decoration is bracketed, so result_span
# would return a slice of the trace and call it the answer), and LOCATE rows read
# the screen GRID (CSRLIN/POS are the READ side of the state LOCATE WRITES, so a
# wrong pair could cancel -- they appear only in the declared `xchk` battery).
#
# MOTOR's effect is the cassette RELAY, which a name-table scrape cannot see: the
# `motor` battery measures the LANGUAGE SURFACE only and says so on every row.
#
# Repack-only + oracle-dependent (boots openMSX; needs your VG-8020 reference
# ROM); NOT part of `unit-test`.
# BOOTPC=1 forces boot-per-case. The reference-only rows are the ones that need
# it: run_differential SELF-HEALS a disagreeing two-sided row by re-running it
# boot-per-case, so calibration verdicts already equal a boot-per-case run -- but
# a reference-only row is delivered BATCHED and nothing re-checks it. Every
# number the spec is built on was confirmed with BOOTPC=1.
missing-characterize: repack-machine
	python3 probes/basic/basic_probe_missing.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BOOTPC),--boot-per-case,)

missing-acceptance: repack-machine
	python3 probes/basic/basic_probe_missing.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BOOTPC),--boot-per-case,)

# --- Standing string-engine acceptance gate (string-engine arc S5; compare S3) -----
# The three-part proof of the Phase-3 string engine on the merged repack build. CRUNCH:
# the 8 string keywords (LEN/LEFT$/RIGHT$/MID$/CHR$/ASC/STR$/VAL) tokenise byte-for-byte
# like the VG-8020 reference AND match the §4 captured $FF-suffixes. EXECUTE: the verbs
# and `+` concatenation produce the right screen output live on the relocated build.
# COMPARE: the six relational operators on string operands (=/<>/</>/<=/>=) match the
# VG-8020 reference (reference-lock + zerobas==reference; spec-basic-string-compare.md).
# The lean build never tokenises these keywords (verbatim ASCII) and has no engine, so
# this gate is repack-only -- it boots C-BIOS_MSX1_EU_REPACK_DISK (from repack-machine).
# HEAVY + oracle-dependent like the other acceptance gates (boots openMSX; needs your
# VG-8020 reference ROM); NOT part of the emulator-free `unit-test`. `make string-acceptance
# FULL=1` also re-runs the whole crunch corpus on the repack build (relocated-kwtable proof).
string-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/string_acceptance.py $(if $(FULL),--full,)

# --- Standing console-INPUT acceptance gate (input slice S3) ------------------------
# Console INPUT / LINE INPUT (docs/spec-basic-input.md). Its own gate rather than a half
# of string-acceptance: INPUT is I/O, not the string engine (spec §8 Q2). DRIVES THE
# KEYBOARD -- types a small program, RUNs it, then delivers the INPUT *response* as a
# separate keystroke burst after the prompt appears (spec §6 harness wrinkle). Two
# halves: reference-lock each case on the VG-8020 (numeric/string/multi-var/LINE INPUT/
# prompt separator/?redo/?extra), then assert zerobas==reference on the repack build.
# The ?redo/?extra WORDING is zerobas's own lowercase (D-2), so those cases differential
# the final VALUE, not the message. Console INPUT is repack-only, so this boots
# C-BIOS_MSX1_EU_REPACK_DISK. HEAVY + oracle-dependent (needs your VG-8020 reference
# ROM); NOT part of the emulator-free `unit-test`. Scope with `make input-acceptance
# ONLY=numeric`.
input-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_input.py $(if $(ONLY),--only '$(ONLY)',)

# --- Input-devices acceptance gate (input devices, slice I1) ------------------
# STICK/STRIG differential vs the VG-8020 (docs/spec-basic-input-devices.md §8):
# PHASE A grammar + error surface + the truncate-vs-round coercion
# discriminators, PHASE B idle values, PHASE C the LIVE key matrix -- the only
# phase with teeth, since with nothing plugged an idle read and a stubbed
# constant 0 are indistinguishable. Phase C drives openMSX's keymatrixdown (the
# REPL driver's KEYBUF injection bypasses the matrix that STICK/STRIG scan) and
# runs boot-per-case. Repack-only; HEAVY + oracle-dependent (needs your VG-8020
# reference ROM); NOT part of the emulator-free `unit-test`.
input-devices-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_input_devices.py $(if $(ONLY),--only '$(ONLY)',)

# --- Error-handling acceptance gate (error-handling arc, S1) -------------------
# Two differential families against the VG-8020 reference (docs/
# spec-basic-error-handling.md): FAMILY A -- untrapped-error ABORT semantics
# (the D-1 fix), observable-variable (10 A=1 / 20 <error> / 30 A=2 / RUN /
# PRINT A: A==1 iff the run aborted, ==2 iff it wrongly continued) across all ten
# fatal error types; FAMILY B -- run-mode " in <line>" reporting (the D-2 fix),
# structure asserted on both machines (wording stays house-style, D-2, so the
# text itself is NOT compared). Repack-only; HEAVY + oracle-dependent (boots
# openMSX per case; needs your VG-8020 reference ROM); NOT part of the
# emulator-free `unit-test`. Scope one case with `make error-acceptance ONLY=divzero`.
error-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/error_acceptance.py $(if $(ONLY),--only '$(ONLY)',)

# --- Error-handling trap/RESUME acceptance gate (error-handling arc, S2b) -----
# The RESUME-family DoD gate (docs/spec-basic-error-handling-s2b-packet.md §10):
# trap fires + ERR/ERL; RESUME/RESUME 0/RESUME NEXT (incl. the scan_stmt_end
# quote-awareness case, a mid-':'-line error inside a string literal)/RESUME
# <line>; nested-error forced abort (inner message); ON ERROR GOTO 0 disable;
# ON ERROR GOTO <undefined>; RESUME without error (ERR 22); ERROR n regression;
# and the §7 reset-scope cases (UNVERIFIED pin -- straight differential, no
# hardcoded expectation). Repack-only; HEAVY + oracle-dependent, same shape as
# error-acceptance above. Scope one case with `make error-trap-acceptance
# ONLY=resume_next`.
error-trap-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_error_trap.py $(if $(ONLY),--only '$(ONLY)',)

# --- STOP interrupt-trap gate (interrupt-traps T1 -- docs/spec-traps-t1-stop-
# reslice.md §9.2/§12). VG-8020 differential of ON STOP GOSUB / STOP ON|OFF|STOP:
# a Ctrl-STOP TAP during a FOR delay must FIRE the handler (A), an armed-but-not-
# enabled or STOP-OFF trap must NOT (B/B2), all matching the reference bit-for-bit.
# The discriminating regime is a released TAP during a delay, not a held key in a
# tight loop (both break there). Repack-only; HEAVY + oracle-dependent (boots
# openMSX per case; needs the VG-8020 reference machine). The emulator-free fast
# layer is tests/test_traps.py under `unit-test`. Scope with `make stop-trap-
# acceptance ONLY=B2_stop_off`; `TRIALS=n` sets the robustness repeat count.
stop-trap-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_stop_trap.py $(if $(ONLY),--only '$(ONLY)',) \
	  $(if $(TRIALS),--trials $(TRIALS),)

# --- STRIG interrupt-trap gate, slice T2 (docs/spec-traps-t2-strig.md) --------
# VG-8020 differential for `ON STRIG GOSUB` / `STRIG(n) ON|OFF|STOP`. Trigger 0 is
# pressed through the keyboard matrix (row 8 bit 0 IS trigger 0); triggers 1..4 are
# driven by the PSG port-A-output + R14-latch injection (spec §7.3), which needs the
# repack machine's <ignorePortDirections>false</> (D-T2-6) -- so this target depends
# on repack-machine like the rest. Scope with `make strig-trap-acceptance ONLY=B_`.
strig-trap-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_strig_trap.py $(if $(ONLY),--only '$(ONLY)',)

# --- KEY interrupt-trap gate, slice T3 (docs/spec-traps-t3-key.md §8) ---------
# VG-8020 differential for `ON KEY GOSUB` / `KEY(n) ON|OFF|STOP`. Function keys are
# pressed straight through the matrix (row 6 bits 5/6/7 = F1..F3, row 7 bits 0/1 =
# F4/F5, + row 6 bit 0 SHIFT for F6..F10). Needs the repack machine because the
# event source is a C-BIOS hook (H_ZKEY, cbios-repack/key-trap-hook.patch), so an
# unrepacked ROM cannot fire it at all. Scope with `make key-trap-acceptance ONLY=A_`.
# `make key-trap-acceptance CALIBRATE=1` re-measures the two machines' loop rates,
# which is what the iteration-count observation windows are sized from -- the spec
# requires calibrating them rather than assuming (§1.0).
key-trap-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_key_trap.py $(if $(ONLY),--only '$(ONLY)',) \
	  $(if $(CALIBRATE),--calibrate,)

# --- SPRITE interrupt-trap gate, slice T4 (docs/spec-traps-t4-sprite.md §8) ---
# VG-8020 differential for `ON SPRITE GOSUB` / `SPRITE ON|OFF|STOP`, the last slice
# of the trap arc. THE ONLY GATE IN THE ARC THAT DRIVES NO INPUT DEVICE: the event
# is a VDP sprite collision the BASIC program causes itself, so every case is just
# `-machine <name>` plus a program -- no key matrix (T1/T3), no PSG injection (T2),
# no C-BIOS hook (T3). Repack-only (the poll is low-region repack code).
# Fire COUNTS are asserted per machine, never across the two: a count is a function
# of how many frames fit in the window and the machines run BASIC ~7x apart. The
# cross-machine assertions are the error surface, the STATFL readings, and the
# emulator-counted cadence windows (spec 1.2.1: those windows are exactly as long on
# both machines BY CONSTRUCTION -- the emulator closes them after N ISR ticks -- so
# there the counts ARE comparable, and F_cadence_off's zero is asserted as an
# equality).
# Scope with `make sprite-trap-acceptance ONLY=cadence` (all three cadence cases);
# `REPORT=1` prints the raw
# readings without asserting (characterization mode). FRAMES=n sets the ISR ticks
# per cadence window (default 300; measured identical at 120/300/600).
sprite-trap-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_sprite_trap.py $(if $(ONLY),--only '$(ONLY)',) \
	  $(if $(REPORT),--report,) $(if $(FRAMES),--frames $(FRAMES),)

# --- INTERVAL trap acceptance gate (traps T5, docs/spec-traps-t5-interval.md) --
# VG-8020 differential. The arc's fifth and last trap slice, and the one whose
# every observable is a JIFFY COUNT -- so the PERIOD is measured BETWEEN TWO
# FIRES (the handler stamps JIFFY at fire #1 and fire #1+span) rather than counted
# over a window, which would carry +-1 frame of pure phase noise. Error codes,
# no-fire cases and latch-release counts are equality differentials; anything that
# is a period is a per-machine predicate with the span's own jitter as tolerance.
# `REPORT=1` prints readings without asserting; scope with ONLY=<substring>.
interval-trap-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_interval_trap.py \
	  $(if $(ONLY),--only '$(ONLY)',) $(if $(REPORT),--report,)

# --- TIME / TIME=n acceptance gate (docs/spec-basic-time.md) -------------------
# VG-8020 differential, BOTH sides asserted against the SAME pinned reference
# values (spec §1 is all measurement, so those values ARE the comparison and the
# reference run re-validates the oracle in the same pass). Five groups: crunch
# ($CB + the TIMES/TIME$/ATIME/TI shadow cases), read, write (the address-domain
# conversion table), the error surface, and the clock.
#
# THE CLOCK GROUP IS A PER-MACHINE PROPERTY, NEVER AN EQUALITY: the tick rate
# belongs to the host BIOS/VDP and BASIC runs ~3x apart on the two machines
# (measured: 789 jiffies per 3000 iterations on the repack build vs 240 on the
# VG-8020). It asserts advances / monotonic / wraps, per machine.
#
# EVERY TIME-READING CASE IS PHASE-SHIFTED AND REDUCED. A single reading of TIME
# after an assignment is not a measurement: JIFFY ticks in between, and in a
# BATCHED run that phase is DETERMINISTIC, so repetition does not average it out.
# Scope with `make time-acceptance ONLY=w` (crwek groups); PHASES=n to widen.
time-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_time.py --mode differential \
	  $(if $(ONLY),--groups $(ONLY),) $(if $(PHASES),--phases $(PHASES),)

# --- D-F2-2 int-argument coercion gate (docs/spec-basic-df2-2-intarg-coercion.md)
# VG-8020 differential: out-of-domain int args must raise the reference's Overflow
# (ERR 6) / Illegal function call (ERR 5), not silently coerce. ASSERTED cases gate
# the landed stages (A1 = OUT + address-domain regression guards); PENDING cases are
# reported as a straight differential until their stage (A2 PEEK/INP, B STRING$/
# SPACE$/ON/WIDTH/VPOKE-VRAM) lands. Repack-only; oracle-dependent.
intarg-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_intarg.py $(if $(ONLY),--only '$(ONLY)',)

# --- D-CUR-D UNTRAPPED-abort gate (docs/spec-basic-abort-depth.md §6) ---------
# The half `intarg-acceptance` above structurally cannot measure. raise_error has
# two branches: the TRAP branch resets SP and jumps to the handler, the ABORT
# branch prints and returns. All 36 asserted intarg rows arm `ON ERROR GOTO` and
# read ERR -- which selects the TRAP branch, i.e. the one that was always
# correct. They were ALL PASS on the build where `WIDTH 99999` typed at the
# prompt printed NO error at all and left the screen unusable.
#
# So: not one row here may arm a handler, every value row is bracket-delimited
# (the junk an aborted statement leaves can be WHITESPACE -- SPACE$(-1) built a
# five-space string and a right-stripped scrape read it as clean), and the whole
# matrix runs boot-per-case (the WIDTH rows leave the machine unusable). The
# probe's own docstring carries these rules; they are not style.
#
# FALSIFIED 2026-07-28, not asserted: commenting out `ld sp,(SAVSTK)` in
# fre_abort_low (basic/arrays.asm), rebuilding from clean and re-running takes it
# from 23/23 to 6/23. The 6 survivors are the right ones -- ctl_value, ctl_abort,
# boot_first, tenant_ary, tenant_after and run_suffix all raise at the STATEMENT
# HANDLER's own depth, where the abort was always correct. Repack-only;
# oracle-dependent.
abort-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_abort_depth.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- D-MISS-2 string-ARGUMENT-DOMAIN gate (docs/spec-basic-str-domain.md §6) --
# CHR$/LEFT$/RIGHT$/MID$/INSTR accept out-of-range arguments silently and compute
# a wrong answer where the reference raises. 89 rows, six batteries.
#
# `ctl` is read FIRST and separately: LEN(A$) proves the readout, ASC("") proves
# an abort is reachable at EVALUATOR depth (far below statement-handler depth),
# and STRING$/SPACE$ are the family members that already check -- the working
# reference implementation of the two-stage rule. If a control diverges the probe
# exits non-zero and says so, because no other row is then readable as a finding.
#
# ⚠️ The 34 `in` rows are NOT padding. A domain check's failure mode is rejecting
# what it should ACCEPT, and a matrix of only out-of-range rows goes green on an
# implementation that raises `Illegal function call` for everything.
#
# ⚠️ NO ROW MAY ARM `ON ERROR` (same reason as abort-acceptance above), every
# value row is bracket-delimited, and `WIDTH 40` is pinned with the subject
# carried in A$ -- the two machines boot at different widths and a wrapped echo
# breaks the screen_tail readout SILENTLY. The probe's docstring carries these.
#
# Repack-only; oracle-dependent. `make str-domain-acceptance ONLY=mid` to scope;
# BOOTPC=1 forces boot-per-case (the default already self-heals any disagreeing
# row boot-per-case, so the verdicts already equal a boot-per-case run).
str-domain-characterize: repack-machine
	python3 probes/basic/basic_probe_str_domain.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BOOTPC),--boot-per-case,)

str-domain-acceptance: repack-machine
	python3 probes/basic/basic_probe_str_domain.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BOOTPC),--boot-per-case,)

# --- WIDTH valid-domain gate (docs/spec-basic-width-domain.md, D-WID) ---------
# VG-8020 differential over `WIDTH n`'s DOMAIN: which n each screen mode accepts,
# which of four errors it raises otherwise, and which per-mode default it records.
# The last residue of the abort-depth slice -- 4d35b6d fixed how `WIDTH 300`
# FAILS and left open what `WIDTH` should ACCEPT (spec-basic-abort-depth.md §7).
# Five divergences, every one of them a SILENT screen-destroyer: no bound at all
# (`WIDTH 0` and `WIDTH 41..255` accepted in every mode), the wrong per-mode slot
# in graphics modes, and no Type-mismatch / Missing-operand check.
#
# ⚠️ THE SUBJECT UNDER TEST MOVES THE INSTRUMENT. Every other probe here reads
# the SCREEN-0 name table at a fixed 40-byte stride; `WIDTH`'s whole job is to
# change that stride, after which the scrape shears and every readout -- echo
# anchor included -- silently stops meaning anything. So the subject runs inside
# a stored program, the outcome is captured into NUMERIC variables (trapped ERR
# plus LINLEN/LINL40/LINL32) while the screen is still wrong, the program then
# RESTORES SCREEN 0 + WIDTH 40, and only then prints. Readout is
# `[ ERR LINLEN LINL40 LINL32 ]`, width-independent by construction.
#
# ⚠️ THE INSTRUMENT IS PINNED ON EVERY ROW (lines 10-20 of the program). The two
# machines boot at different text widths (reference 37, zerobas 39); unpinned,
# three control rows that execute no WIDTH at all diverged on width alone while
# their ERR codes agreed. The pin also gives every reject row a KNOWN prior
# LINLEN, which is what makes "did the reject write anything anyway?" answerable.
#
# ⚠️ THESE BATTERIES ARM `ON ERROR` ON PURPOSE -- the opposite of the rule in
# abort-acceptance / str-domain-acceptance. Those measure the UNWIND, which a
# handler hides; this measures the DOMAIN, and a trapped ERR read is the only
# readout that survives a statement which has just destroyed the screen. The
# unwind stays gated by abort-acceptance; the `unt` battery is the seam.
#
# ⚠️ The in-domain rows are NOT padding, for the same reason str-domain's are not.
#
# Repack-only; oracle-dependent. `make width-acceptance ONLY=s1-` to scope one
# battery. Boot-per-case by default (a WIDTH row leaves the machine unusable by
# construction); BATCH=1 shares one boot, which is sound only because every
# trapped row restores SCREEN 0/WIDTH 40 itself.
width-characterize: repack-machine
	python3 probes/basic/basic_probe_width.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BATCH),--batch,)

width-acceptance: repack-machine
	python3 probes/basic/basic_probe_width.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BATCH),--batch,)

# --- CLEAR string-pool partition (docs/spec-basic-clearpool.md, D-CLP) --------
# VG-8020 differential over the two-pool model. ✅ LANDED: `clearpool-acceptance`
# is the standing gate (51/51 gated rows, 6 reported-never-gated);
# `clearpool-characterize` is the same probe without --gate, for re-measuring.
# Before the slice this read 6/51 -- zerobas had ONE free gap where the reference
# has TWO POOLS, and CLEAR's <string-space> argument was evaluated and DISCARDED,
# so `CLEAR 500:PRINT FRE("")` answered ~15867 instead of 500.
#
# ⚠️ THE SIX UNGATED ROWS ARE UNGATED FOR THREE DIFFERENT REASONS, and the
# batteries say which: `rep` (2) are FRE(0) absolutes, a property of each
# machine's memory map; `share` (3) are the body-OWNERSHIP divergence
# (S-CLP-5, signed off out of scope -- zerobas owns a body per variable, the
# reference decides per source); `arr` (1) is the ARRAYS-arc `DIM Q(20000)`
# divergence this probe found in passing. None of them is a silenced failure:
# oos-vs-oom, which used to carry the `arr` case as well, was SPLIT so the
# claim it makes ("out of string space is distinct from out of memory") is
# gated on a DIM both machines call an OOM.
#
# ⚠️ `FRE("")` IS THE ONE MACHINE-INDEPENDENT MEMORY READOUT, which is what makes
# absolute rows legitimate here and nowhere else in this tree: FRE(0) answers
# with free VARIABLE space (a property of each machine's memory map, gateable
# only as a relation), but a pool sized by `CLEAR n` answers with a number the
# USER chose. The two `rep` rows are FRE(0) readings and are never gated.
#
# ⚠️ THE ORACLE IS CHECKED AGAINST ITS OWN RECORDED ANSWERS FIRST. Four rows are
# verbatim from docs/binfre-vg8020-characterization.md §1; REPRO_EXPECT asserts
# them against the REFERENCE COLUMN ALONE, before any verdict is read as a
# finding. They are deliberately not controls: a control must be a row both
# machines are expected to pass today, and these are what zerobas must FAIL.
#
# ⚠️ NO LINE MAY REACH 40 CHARACTERS, and the probe enforces it BEFORE booting an
# emulator. Both readouts are echo-anchored and a longer echo WRAPS, after which
# it can never be matched -- the first run of this matrix had ELEVEN rows read
# <none> ON THE REFERENCE, several then scoring PASS against a zerobas <none>.
# Every case is a list of short lines with the PRINT last.
#
# Repack-only; oracle-dependent. Boot-per-case by default: a case's CLEAR
# resizes the pool PERSISTENTLY, so it leaks into every follower, and the reset
# that would undo it is the very thing under measurement.
clearpool-characterize: repack-machine
	python3 probes/basic/basic_probe_clearpool.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BATCH),--batch,)

clearpool-acceptance: repack-machine
	python3 probes/basic/basic_probe_clearpool.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BATCH),--batch,)

# --- DIRECT-MODE control-flow gate (docs/spec-basic-direct-ctrl.md §8) --------
# VG-8020 differential for FOR/NEXT, GOSUB/RETURN, GOTO, IF-THEN-<line> and
# ON-GOTO typed AT THE PROMPT -- an execution mode that had zero coverage until
# 2026-07-26 (every earlier loop/trap/graphics gate runs its BASIC as a stored
# program + RUN). Six groups, 40 cases: direct / cross / stored / xfer / break /
# reset. Scope with `make direct-ctrl-acceptance ONLY=xfer,break`.
#
# THE PROBE IS BOOT-PER-CASE AND MUST STAY THAT WAY: half the defect it gates is
# COLD-BOOT STATE (FSP/GSP were initialised only by run_prog), so in a batched
# run the first case that RUNs a stored program initialises them for the whole
# boot and every later direct-mode case passes -- a green gate over a live bug.
# Consequently this target is SLOW (80 openMSX boots). Repack-only;
# oracle-dependent (needs the VG-8020 reference machine).
direct-ctrl-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_direct_ctrl.py $(if $(ONLY),--groups $(ONLY),)

# --- SOUND acceptance gate (audio arc, Slice 1 — docs/spec-basic-audio-play.md)
# VG-8020 differential, two halves: (1) the ERROR SURFACE — SOUND's register 0..13
# range + the D-F2-2 byte coercion (14..255 -> ERR 5, >int16 -> ERR 6); (2) the PSG
# REGISTER WRITE — `SOUND reg,value` then read the openMSX "PSG regs" debuggable and
# compare the written register's byte (register 7's top-2-bit I/O mask included).
# Repack-only; HEAVY + oracle-dependent (boots openMSX per case; needs your VG-8020
# reference ROM). The emulator-free fast layer is tests/test_sound.py under
# `unit-test`. Scope one case with `make sound-acceptance ONLY=r7_ff`.
sound-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_sound.py $(if $(ONLY),--only '$(ONLY)',)

# --- Standing PLAY acceptance gate (audio arc, Slice 2a) ----------------------
# docs/spec-basic-audio-play-slice2a.md §8. Two halves: ERROR SURFACE (differential
# vs the VG-8020 -- exercises the full ex_play -> str_eval -> marshal -> subrom_call
# -> parser-tenant path the host layer cannot, and locked the '&'-unsupported /
# bare-comma-Syntax-error / numeric-Type-mismatch facts against the reference) plus a
# zerobas MUSICF integration self-check (present voices marked active, PLAY returns).
# Repack-only; HEAVY + oracle-dependent (boots openMSX per case; the differential half
# needs your VG-8020 reference ROM). The emulator-free fast layer is
# tests/test_play_parse.py under `unit-test`. Scope one case with `make play-acceptance
# ONLY=badcmd`; pass `--no-ref` (edit the recipe) for the zerobas-only self-check.
play-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_play.py $(if $(ONLY),--only '$(ONLY)',)

# --- Standing PLAY live-servicer trace gate (audio arc, Slice 3) ---------------
# docs/audio-slice3-characterization.md. Per-VBLANK PSG register trace differential
# vs the VG-8020 -- proves play_service (reached from the $0038 ISR via the H.TIMI
# seam) reproduces the reference's live drain: note tone periods (the black-box
# 96-note table), frame durations (12000//tl floor), rests (amp 0, period kept),
# dots, envelope (R11/12/13 + amp $10|vol), 3-voice independent drain, R7 never
# touched, and a DI-safety liveness case (PLAY then a tight SIN loop). Repack-only;
# HEAVY + oracle-dependent (boots openMSX twice per case; needs your VG-8020 ROM).
# The emulator-free fast layer is tests/test_play_frame_sim.py under `unit-test`.
# Scope one case with `make play-trace-acceptance ONLY=env`.
play-trace-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_playtrace.py $(if $(ONLY),--only '$(ONLY)',)

# --- Standing BEEP acceptance gate (audio arc, close-out) ---------------------
# docs/spec-basic-audio-beep.md §5. Per-VBLANK PSG-register trace differential vs the
# VG-8020: for `beep` and its edge cases, assert the (R0,R1,R7,R8) transient is
# byte-identical to the reference -- ON = tone-A period 85 / mixer $be / vol 7, OFF =
# amp 0 / mixer wiped to the default $b8. The `sound 7,190:beep` / `sound 8,10:beep`
# cases prove the restore is dynamic (not a hardcoded $b8) and R8 is zeroed not
# restored. Repack-only; HEAVY + oracle-dependent (boots openMSX per case; needs your
# VG-8020 reference ROM). The emulator-free fast layer is tests/test_beep.py under
# `unit-test`. Scope one case with `make beep-acceptance ONLY=r7dyn`.
beep-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_beep.py $(if $(ONLY),--only '$(ONLY)',)

# --- Standing float-pack acceptance gate (float arc, F1 S3 + F2 S2) -----------
# Three differential halves against the VG-8020 reference (docs/
# spec-basic-float-core.md §9-§10): LITERALS (basic_probe_floatlit.py -- the
# crunched $1D/$1F token bytes ARE the stored BCD representation, so this is
# both the classification and the encoder proof), FORMAT
# (basic_probe_float_fmt.py -- PRINT's fixed/E-notation output, spaces exact),
# and ARITH (basic_probe_float_arith.py -- + - * / relationals, promotion,
# rounding ties, overflow/underflow walls, signed \/MOD, the two float->int
# conversion domains, IF truthiness; ~150 cases, the F2 slice's gate).
# Grows a half per slice (F3 vars next). Repack-only; HEAVY +
# oracle-dependent (boots openMSX per case; needs your VG-8020 reference ROM);
# NOT part of the emulator-free `unit-test` (tests/test_float.py is the fast
# layer under it). Scope one case with `make float-acceptance ONLY=9999995`.
float-acceptance: $(DISK_ROM) repack-machine
	python3 probes/basic/basic_probe_floatlit.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only '$(ONLY)',)
	python3 probes/basic/basic_probe_float_fmt.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only '$(ONLY)',)
	python3 probes/basic/basic_probe_float_arith.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only '$(ONLY)',)
	python3 probes/basic/basic_probe_float_vars.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only '$(ONLY)',)
	python3 probes/basic/basic_probe_var_reset.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only '$(ONLY)',)

# --- Standing math-pack acceptance gate (math pack slice 1a + SQR/1b) ----------
# ABS/SGN/INT/FIX/CINT/CSNG/CDBL/SQR (docs/spec-basic-math-pack.md §9.4/§10.4):
# token crunch-byte-identity (vs MSX2 TH Table 2.20) + the value differential vs
# the VG-8020 reference (INT/FIX negative-operand divergence, CINT rounding +
# domain-overflow edges, FACTYP-leak, the ABS(-32768%) int-domain escape, SQR's
# correctly-rounded battery). SQR's body is now a sub-ROM page-1 tenant
# (docs/spec-basic-subrom-mathpack.md) -- this gate's byte-identical SQR outputs
# are the PROOF the tenant migration is correct (algorithm unchanged, only its
# home moved), so `subrom-abi-check` runs first: a stale resident-ABI import
# would otherwise surface as a confusing SQR value mismatch instead of a clear
# staleness error. Repack-only; HEAVY + oracle-dependent (boots openMSX; needs
# your VG-8020 reference ROM); NOT part of the emulator-free `unit-test`. Scope
# with `make math-acceptance ONLY=cint`.
math-acceptance: $(DISK_ROM) repack-machine subrom-abi-check
	python3 probes/basic/basic_probe_math_conv.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only '$(ONLY)',)

# --- Standing arrays acceptance gate (arrays arc, slice 1 -- numeric arrays) ---
# DIM + subscript rvalue/lvalue for numeric arrays (docs/spec-basic-arrays.md
# §9/§10). Differential vs the VG-8020 across the §4.1 semantics matrix PLUS the
# adversarial regression the literal-only first cut missed (variable/nested/FOR-
# loop subscripts -- the showstopper the review caught). The array *engine* is a
# page-0 sub-ROM tenant (sub/arrays.asm), so these byte-identical outputs also
# prove the split's ABI wiring. Repack-only; HEAVY + oracle-dependent (boots
# openMSX; needs your VG-8020 reference ROM, reachable via OPENMSX=); NOT part of
# the emulator-free `unit-test` (tests/test_arrays.py is the fast layer under it).
array-acceptance: $(DISK_ROM) $(SUB_ROM) repack-machine
	python3 probes/basic/basic_probe_arrays.py

# Standing C-BIOS self-consistency gate: closes the coverage gap that `bdos-acceptance`
# structurally can't reach. That gate is a DIFFERENTIAL, so it only runs on the CF-3300
# oracle (the only host with a stock disk ROM + MSX-DOS to diff against); the shipped
# C-BIOS DOS-boot path went unexercised until the $F340 cold-boot bug surfaced it. This
# re-captures the SAME BDOSX anchors on BOTH the CF-3300 and the C-BIOS target and asserts
# the buffers are byte-identical, proving the BDOS surface is BIOS-independent (so what
# bdos-acceptance proved against stock also holds on C-BIOS). HEAVY + oracle-dependent
# (boots openMSX on both hosts; needs `make machines-oracle` + the installed C-BIOS+disk
# machine). Scope with `make bdos-cbios-selfcheck ONLY=BDOSX3`. Spec:
# disk/docs/tier2-cbios-bdos-selfcheck-spec.md.
bdos-cbios-selfcheck: $(DISK_ROM)
	python3 probes/disk/disk_bdos_cbios_selfcheck.py $(if $(ONLY),--only '$(ONLY)',)

# The mechanical half of the clean-room paper-trail audit: forbidden-source scan
# + per-file attestation (gating) and disk section-citation presence (advisory).
# Cheap, read-only, no emulator -- run it on demand / in CI so the citation
# scaffolding cannot silently lapse between the manual paper-trail passes. It does
# NOT replace the human paper trail (the "is each probe black-box?" judgement);
# see docs/clean-room-audit.md. `make audit-citations TARGET="disk"` scopes it.
audit-citations:
	python3 tools/audit_citations.py $(TARGET)

# clean removes the gitignored build artifacts only. The tracked patch
# deliverables are left in place (use `make patches` to regenerate them).
clean:
	rm -rf $(BUILD)

.PHONY: all disk sub patches tape-patches machines machines-oracle install \
        test-dsk unit-test coverage probe bdos-acceptance diskbasic-acceptance \
        bdos-cbios-selfcheck audit-citations basic-reloc repack-main repack-boot \
        repack-machine diskbasic-acceptance-repack string-acceptance time-acceptance \
        interval-trap-acceptance \
        input-acceptance error-acceptance error-trap-acceptance stop-trap-acceptance strig-trap-acceptance key-trap-acceptance sprite-trap-acceptance intarg-acceptance abort-acceptance direct-ctrl-acceptance sound-acceptance play-acceptance play-trace-acceptance beep-acceptance float-acceptance math-acceptance subrom-acceptance \
        subrom-inttest subrom-abi-check subrom-closure-check \
        graphics-floor-acceptance graphics-floor-teeth graphics-acceptance kwsweep fat-error-acceptance \
        logicops-characterize cursor-characterize cursor-acceptance \
        binfre-characterize binfre-acceptance \
        missing-characterize missing-acceptance \
        str-domain-characterize str-domain-acceptance clean
