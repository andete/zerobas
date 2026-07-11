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
DEPS  := basic/interp.asm basic/initext.asm basic/title.asm basic/repl.asm \
         basic/vars.asm basic/strvar.asm basic/expr.asm basic/poke.asm basic/vdpio.asm \
         basic/clear.asm basic/usr.asm basic/print.asm basic/screen.asm basic/list.asm \
         basic/fat.asm basic/bload.asm basic/cload.asm basic/save.asm basic/files.asm \
         basic/field.asm basic/format.asm basic/printusing.asm basic/program.asm basic/float.asm \
         basic/float-arith.asm \
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
SUB_PARTS := sub/equates.inc sub/fltout.asm basic/sysvars.inc
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
$(SUB_ROM): $(SUB_SRC) $(SUB_PARTS) | $(BUILD)
	$(PASMO) -I sub --bin $(SUB_SRC) $(SUB_ROM)
	python3 tools/pad_rom.py $(SUB_ROM) 32768

sub: $(SUB_ROM)

# --- Relocated BASIC proof (cbios-repack arc, WS-2 / S3) -----------------------
# Assemble the $2812-based variant (basic/main-reloc.asm) and prove it lands the
# "AB" header at $4000 and matches the shipping page-1 body byte-for-byte. This is
# a proof/staging target only -- deliberately NOT in `all`; the merged main-ROM
# splice that ships it is WS-3 (S4). See docs/cbios-repack-ws2-audit.md.
RELOC_ROM := $(BUILD)/basic-reloc.rom
basic-reloc: $(ROM) basic/main-reloc.asm basic/main.asm $(DEPS) | $(BUILD)
	$(PASMO) --bin basic/main-reloc.asm $(RELOC_ROM)
	python3 tools/check_reloc.py $(RELOC_ROM) $(ROM)

# --- Merged repack main ROM (WS-3 / D4) ---------------------------------------
# The 32 KB slot-0 "main ROM": repacked C-BIOS + relocated BASIC ($2812-$7FFF) +
# tape, built reproducibly from the user's C-BIOS checkout (CBIOS=<path>; no
# C-BIOS bytes in-repo). NOT in `all` -- it needs that external checkout. The
# patch pair diffs the merged image vs the pristine stock from the same pinned tag.
CBIOS ?= ~/projects/cbios
MAIN_ROM   := $(BUILD)/zerobas-main-eu.rom
MAIN_PATCHES := zerobas-main-eu.ips zerobas-main-eu.bps
repack-main: basic/main-reloc.asm basic/main.asm $(DEPS) tape/tape.asm | $(BUILD)
	python3 tools/build_patches.py --main --cbios $(CBIOS)
repack-boot: repack-main
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
	python3 probes/disk/disk_bdos_acceptance.py $(if $(ONLY),--only $(ONLY),)

# Standing Disk-BASIC acceptance gate: the BASIC-side counterpart of bdos-acceptance.
# Replays the self-asserting disk_probe_* differentials over the Disk-BASIC verb
# surface (FILES/OPEN/FIELD/GET/PUT/SAVE/LOAD/...) and asserts each still converges to
# the oracle. HEAVY + oracle-dependent (needs `make machines-oracle` + the seed image
# + your CF-3300 reference ROMs); NOT part of the emulator-free `unit-test`. Scope with
# `make diskbasic-acceptance ONLY=FIELD`. See disk/docs/diskbasic-acceptance-spec.md.
diskbasic-acceptance: $(DISK_ROM) $(DISK_TEST_DSK)
	python3 probes/disk/diskbasic_acceptance.py $(if $(ONLY),--only $(ONLY),)

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
	  python3 probes/disk/diskbasic_acceptance.py $(if $(ONLY),--only $(ONLY),)

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
	python3 probes/basic/basic_probe_input.py $(if $(ONLY),--only $(ONLY),)

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
	python3 probes/basic/basic_probe_floatlit.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only $(ONLY),)
	python3 probes/basic/basic_probe_float_fmt.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only $(ONLY),)
	python3 probes/basic/basic_probe_float_arith.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK $(if $(ONLY),--only $(ONLY),)

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
	python3 probes/disk/disk_bdos_cbios_selfcheck.py $(if $(ONLY),--only $(ONLY),)

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
        repack-machine diskbasic-acceptance-repack string-acceptance \
        input-acceptance float-acceptance subrom-acceptance clean
