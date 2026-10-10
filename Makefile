# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

# zerobas — build every deliverable.
#
# Requires pasmo (the assembler C-BIOS uses) and python3. Build from the repo
# root so the `include` paths in basic/main.asm resolve.
#
# `make` (the default `all` goal) builds everything that needs NO EXTERNAL CHECKOUT:
#   - build/disk.rom, build/sub.rom                (the disk-interface and sub ROMs)
#   - tape/zerobas-tape-msx1.ips/.bps              (page-0 cassette patch)
# The .ips/.bps patches need a stock C-BIOS main ROM to stamp/verify against;
# tools/build_patches.py auto-detects openMSX's bundled copy or takes STOCK=<path>.
#
# THE SHIPPED BASIC IS zerobas-main-eu.ips/.bps -- the merged repack main ROM
# (repacked C-BIOS EU + relocated BASIC $2765-$7FFF + tape), tracked at the repo root.
# It is NOT in `all` because REGENERATING it needs a C-BIOS source checkout
# (CBIOS=<path>); `make release` does that, and is the maintainer's step before
# committing the pair. APPLYING it needs no checkout at all -- the pristine ROM the
# patch is diffed against is byte-identical to openMSX's own bundled
# cbios_main_msx1_eu.rom (measured, docs/spec-lean-retire-s2-switch.md §2), so a user
# with openMSX can install straight from the tracked patch.
#
# Until 2026-07-29 the shipped BASIC was zerobas-msx1.ips/.bps, a page-1 splice
# carrying the LEAN 16 KB build. That build is retired (RETIRE THE LEAN 16 KB CART,
# docs/spec-lean-retire-s2-switch.md): it was not a smaller build of the same BASIC but
# one missing seven source files -- no strings, no INPUT, no floats, no arrays, no error
# codes, no KEY traps. Cost of the switch: the repack rewrites C-BIOS's page-0 layout and
# is EU-ONLY, where the lean splice was region-universal (see TODO: regionalise).
#
# `make machines` is separate because openMSX machine configs are not portable
# files — they embed absolute paths to your openMSX ROMs and this repo — so they
# are an INSTALL into your openMSX user dir, not a build output. `make install`
# does `all` then `machines`.

# 🔴 A REFUSAL THAT LEAVES THE BAD ARTIFACT ON DISK IS DEFEATED BY RUNNING `make`
# TWICE. Without this, a recipe step that fails AFTER its target file exists (the
# pad_rom.py assert behind every $(PASMO) line is exactly that shape) leaves the
# broken ROM in build/ with a fresh mtime -- so the next `make` reports it
# "up to date", never re-runs the step that refused, and the whole gate chain
# proceeds on it. Measured twice, D-ROMJUDGE 2026-08-05
# (docs/spec-rom-gate-judge.md §6.3): a 30444-byte truncated sub.rom took
# `make basic-reloc` to rc 0 with every gate OK, and a 0-byte one -- the artifact
# D-P0BASE's empty-input refusal exists to stop -- survived its own refusal the
# same way. GNU make deletes the target of a failed recipe only when asked.
.DELETE_ON_ERROR:

# Build artifacts (ROMs) go under build/ -- a gitignored scratch dir -- so a
# stale copy never lingers in the repo root where tools/probes pick it up. The
# tracked patch deliverables (zerobas-main-eu.ips/.bps) stay at the root.
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
# 🔴 EVERY basic/ SOURCE main.asm INCLUDES BELONGS HERE, AND NINE DID NOT (D-DEPS,
# 2026-09-11). `basic/deffn.asm` was missing, so an edit to it alone rebuilt
# NOTHING: the carve that retired `fn_deep` reported page-1 free UNCHANGED and
# the image byte-identical, which is what a build that did not happen looks like.
# The slice that came before it was saved only by also touching `sysvars.inc`,
# which IS listed -- luck, not a rule. Checked after the fix: a forced rebuild of
# the committed sources reproduces the committed patch bytes exactly, so nothing
# shipped stale; `make deps-check` now proves the list instead of trusting it.
# Same class as the sub-ROM's SUB_PARTS, third occurrence [[makefile-subparts-stale-tenant]].
DEPS  := basic/interp.asm basic/initext.asm basic/islands.asm basic/title.asm basic/repl.asm basic/edctrl.asm \
         basic/vars.asm basic/strvar.asm basic/str-engine.asm basic/expr.asm basic/poke.asm basic/vdpio.asm \
         basic/clear.asm basic/usr.asm basic/time.asm basic/print.asm basic/screen.asm basic/list.asm \
         basic/fat.asm basic/bload.asm basic/cload.asm basic/save.asm basic/files.asm \
         basic/field.asm basic/format.asm basic/printusing.asm basic/program.asm basic/float.asm \
         basic/float-arith.asm basic/subromcall.asm basic/edscreen.asm basic/input.asm \
         basic/arrays.asm basic/sound.asm basic/play.asm basic/graphics.asm basic/traps.asm \
         basic/missing.asm \
         basic/tokenise.inc basic/detok.inc basic/pu-render.inc basic/format-body.inc \
         basic/fat-prim-body.inc basic/fat-delete-body.inc \
         basic/randio-body.inc basic/fld-fill-body.inc \
         basic/casmatch-body.inc basic/cal-refill-body.inc basic/cascap-body.inc \
         basic/fcbname-body.inc basic/bload-body.inc basic/fatio-body.inc \
         basic/sv-bsvdisk.inc basic/sv-bsvcas.inc basic/sv-savdisk.inc basic/sv-tsb.inc \
         basic/sv-tputw.inc basic/sv-tne.inc basic/sv-diskwr.inc \
         basic/fatiocreate-body.inc basic/fatiow-body.inc \
         basic/readdata-body.inc basic/tokskip-body.inc \
         basic/deffn.asm basic/keytrap.asm basic/playsvc.asm basic/subrom-boot.asm \
         basic/pdfcb-body.inc basic/title-body.inc basic/sprtrap-body.inc \
         basic/fiawalked-body.inc basic/kwtable.inc \
         basic/sysvars.inc

# zerobas-disk: a standalone 16 KB disk-interface ROM (not an IPS patch). Lives
# in internal slot 3-1; built with the same pasmo + pad_rom flow as the BASIC image.
DISK_SRC := disk/disk.asm
# disk.asm is an orchestrator that `include`s these parts (assembled with -I disk);
# listed as prerequisites so a change to any part triggers a rebuild.
# D-FATENG Option 2 (Joost, 2026-09-18): disk.rom assembles the SHARED FAT body
# too -- one engine, one source, two ROMs. It must be a prerequisite or an edit to
# it leaves disk.rom quietly stale; `rom-parts-check` refused exactly that.
DISK_PARTS := disk/equates.inc disk/init.asm disk/pageenv.asm disk/driver.asm \
              disk/fat.asm disk/kernel.asm disk/runtime.asm \
              basic/fat-prim-body.inc basic/fat-delete-body.inc basic/fatfits-body.inc \
              basic/fatio-body.inc \
              basic/fatiocreate-body.inc basic/fatiow-body.inc \
              basic/sv-diskwr.inc basic/sv-savdisk.inc
DISK_ROM := $(BUILD)/disk.rom
# D-DISKDEAD: disk.rom needs a symbol table like the other two builds, because
# the dead-code sweep reports a span's ADDRESS and SIZE from it. Without one the
# disk arm could still say WHAT is dead but not WHERE or HOW BIG, which is the
# half that decides whether anyone acts on it.
DISK_SYM := $(BUILD)/disk.sym

# zerobas-sub: the built-in MSX2-style sub-ROM, a standalone 32 KB ROM spanning
# BOTH pages of an internal expanded subslot (slot 3-2 on the merged machine).
# Ships as a plain .rom like disk.rom (no IPS, no C-BIOS interaction). S2a is the
# empty skeleton (CD header + one round-trip ping per page); real tenants arrive
# with the eviction session. See docs/spec-basic-subrom.md.
SUB_SRC   := sub/sub.asm
#
# ⚠️ NAMING NOTE, so the entries below read right: several of them identify a
# shared `.inc` as "the lean cart's inline copy". That is PROVENANCE, not a live
# build fact -- the lean 16 KB cart is RETIRED (2026-07-29, docs/spec-lean-
# retire-s3-gates.md) and every one of those `.inc` files now has exactly ONE
# home. The phrase survives because it is still the clearest way to say WHICH
# body a file was carved out of. The staleness hazard each entry warns about is
# unrelated to the cart and is entirely current: a sub include missing from
# SUB_PARTS silently ships a STALE sub.rom ([[makefile-subparts-stale-tenant]]).
#
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
# reuses fatprim's already-listed primitive bodies sub-locally); until the lean
# cart retired it kept its verb-body copies inline in basic/files.asm -- same
# staleness hazard, same fix.
# sub/randio.asm + basic/randio-body.inc + basic/fld-fill-body.inc (fat_rand_*
# random-access record engine, docs/spec-eviction-g4-space.md §3, carve #1 of
# the G4-space eviction slice): the tenant body + its two shared .inc files
# (the lean cart's inline copies, basic/field.asm) -- same staleness hazard,
# same fix ([[makefile-subparts-stale-tenant]]).
# sub/lineedit.asm + (numbered-line editor TXTTAB-
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
# tenant (no shared .inc; the retired lean cart had kept its own
# differently-shaped inline copy in basic/field.asm) -- same staleness hazard,
# same fix.
# sub/fcbname.asm + basic/fcbname-body.inc (disk 8.3-FCB-name builder
# build_83_name, docs/spec-basic-interrupt-traps.md §10.4, the interrupt-traps
# T1 funding carve): the tenant body + its shared .inc file (the lean cart's
# inline copy, basic/bload.asm) -- same staleness hazard, same fix.
SUB_PARTS := sub/equates.inc sub/deftype.asm sub/tkfloat.asm sub/fp_sqrt.asm sub/fp_atan.asm \
             sub/fp_exp.asm sub/fp_log.asm sub/fp_pow.asm sub/fp_sin.asm \
             sub/fp_rnd.asm sub/arrays.asm sub/strheap.asm sub/detok.asm \
             sub/printusing.asm basic/pu-render.inc sub/punum.asm \
             sub/format.asm basic/format-body.inc \
             sub/errtrap.asm \
             sub/fatprim.asm basic/fat-prim-body.inc basic/fat-delete-body.inc basic/fatfits-body.inc \
             sub/dirverb.asm sub/randio.asm sub/fiawalk.asm basic/fiawalked-body.inc basic/randio-body.inc basic/fld-fill-body.inc \
             sub/lineedit.asm \
             sub/casmatch.asm basic/casmatch-body.inc basic/cal-refill-body.inc \
             sub/fcbname.asm basic/fcbname-body.inc \
             sub/fldlook.asm sub/lrsetst.asm sub/deffn.asm \
             sub/bload.asm basic/bload-body.inc basic/fatio-body.inc basic/pdfcb-body.inc basic/cascap-body.inc \
             sub/save.asm basic/sv-bsvdisk.inc basic/sv-bsvcas.inc \
             basic/sv-tsb.inc basic/sv-tputw.inc basic/sv-tne.inc basic/sv-diskwr.inc \
             basic/fatiocreate-body.inc basic/fatiow-body.inc \
             sub/circleparse.asm sub/errmsg.asm sub/lineno.asm sub/readline.asm sub/cursor.asm \
             sub/readdata.asm basic/readdata-body.inc basic/tokskip-body.inc \
             sub/beep.asm sub/lofu32.asm sub/keystr.asm sub/title.asm basic/title-body.inc \
             sub/playparse.asm sub/graphics.asm \
             sub/math-coeffs.inc basic/sysvars.inc basic/kwtable.inc \
             basic/tokenise.inc basic/detok.inc \
             sub/basic-resident-abi.inc
SUB_ROM   := $(BUILD)/sub.rom

# Tracked patch deliverables (regenerable; live at their committed paths).
# The BASIC pair is $(MAIN_PATCHES) further down -- it needs a C-BIOS checkout to
# regenerate, so it is in `release`, not `all` (see the header).
TAPE_PATCHES := tape/zerobas-tape-msx1.ips tape/zerobas-tape-msx1.bps

# Default goal: everything buildable with pasmo + python3 + openMSX's bundled ROMs.
# The BASIC image itself is $(RELOC_ROM) (a proof/staging target) and $(MAIN_ROM)
# (the shipped merge, needs a C-BIOS checkout), so neither is here.
all: $(DISK_ROM) $(SUB_ROM) $(TAPE_PATCHES)

$(BUILD):
	mkdir -p $(BUILD)

# NOTE: there is no `build/basic.rom` rule any more. It built the lean 16 KB
# page-1-only cartridge, retired in full on 2026-07-29 (RETIRE THE LEAN 16 KB
# CART, docs/spec-lean-retire-s3-gates.md) together with the 284 `IF ROM_BASE`
# gates that selected it. $(SRC) now assembles the one $2765-based image.

$(DISK_ROM): $(DISK_SRC) $(DISK_PARTS) disk/basic-resident-abi.inc | $(BUILD)
	$(PASMO) -I disk --bin $(DISK_SRC) $(DISK_ROM) $(DISK_SYM)
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
RELOC_FULL := $(BUILD)/basic-full.bin
ISLANDS    := $(BUILD)/basic-islands.bin
$(RELOC_SYM): $(SRC) $(DEPS) tools/split_islands.py | $(BUILD)
	$(PASMO) --bin $(SRC) $(RELOC_FULL) $(RELOC_SYM)
	python3 tools/split_islands.py $(RELOC_FULL) $(RELOC_ROM) $(ISLANDS)
# Grouped-target workaround (GNU make 3.81 has no `&:`): $(RELOC_SYM)'s recipe
# above produces BOTH files; this is a no-op follower, same pattern as the
# zerobas-main-eu.ips/.bps pair below.
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

# --- the DISK ROM's own resident-ABI import (D-DISKABI) ---------------------
# disk.rom is a PAGE-1 ROM, so main's LOW REGION is callable from it by absolute
# address while main page 1 is not -- the same rule the sub-ROM page-1 tenants
# live under. Until 2026-09-03 it had NO bridge, which is exactly why the disk
# verbs' bodies could not follow their hooks into it (docs/spec-basic-nodisk.md
# §12.1). Generated from the same sym file by the same tool, so a low-region
# shift cannot leave disk.rom calling stale addresses.
disk/basic-resident-abi.inc: $(RELOC_SYM) tools/gen_resident_abi.py
	python3 tools/gen_resident_abi.py $(RELOC_SYM) disk/basic-resident-abi.inc

diskrom-abi-check: disk/basic-resident-abi.inc $(RELOC_SYM)
	python3 tools/check_resident_abi.py $(RELOC_SYM) disk/basic-resident-abi.inc

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
# --- every file a ROM INCLUDES must be a prerequisite of that ROM -----------
# 🔴 WRITTEN BECAUSE IT HAPPENED (D-PUDOT): sub/punum.asm was added as a tenant
# and never put in SUB_PARTS, so `make sub` said "nothing to be done" after a
# full rewrite of it. The Makefile already carried [[makefile-subparts-stale-
# tenant]] from a PREVIOUS occurrence and there was still no check -- a lesson
# with no gate is a lesson that gets re-learned. Its first run found three more.
rom-parts-check:
	python3 tools/check_rom_parts.py

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
# ($2765-$3FFF), the BIOS, or the sub's own page 1. PAGE-1 TENANT WALK
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

# Assemble the $2765-based image ($(SRC)) and prove it lands the "AB" header at
# $4000 and spans the region it claims. This is a proof/staging target only --
# deliberately NOT in `all`; the merged main-ROM splice that ships it is WS-3 (S4).
# See docs/cbios-repack-ws2-audit.md.
# NOTE: this used to also build the lean basic.rom, for check_reloc.py's 4th check
# (a frozen-baseline pin, the ONLY reader of that argument). S2 deleted the check;
# S3 deleted the build. Checks 1-3 read only $(RELOC_ROM), the wall readout only
# $(RELOC_SYM).
basic-reloc: $(RELOC_SYM) $(RELOC_ROM) $(SUB_ROM) $(DISK_ROM)
	python3 tools/check_reloc.py $(RELOC_ROM) $(RELOC_SYM)
	python3 tools/check_sub_walls.py $(SUB_ROM) $(SUB_SYM)
	python3 tools/check_disk_walls.py $(DISK_ROM)
	python3 tools/check_kwtable_identity.py $(RELOC_ROM) $(RELOC_SYM) $(SUB_ROM) $(SUB_SYM)
	python3 tools/check_resident_abi.py $(RELOC_SYM) sub/basic-resident-abi.inc
	python3 tools/check_resident_abi.py $(RELOC_SYM) disk/basic-resident-abi.inc
	python3 tools/check_tenant_closure.py $(RELOC_SYM) sub/basic-resident-abi.inc
	python3 tools/check_tenant_closure.py --page0 $(SUB_SYM) sub/sub.asm
	python3 tools/check_tenant_closure.py --page1 $(SUB_SYM) sub/sub.asm
	python3 tools/check_dead_code.py $(RELOC_SYM) $(SUB_SYM) $(DISK_SYM)
	python3 tools/audit_citations.py
	python3 tools/check_citation_paths.py

# Transitive dead-code sweep, BOTH builds (docs/spec-deadcode-gate.md). A step of
# `basic-reloc` above, since unreachable code is exactly the finding that goes
# unread when it is only advisory: the carve the ROM REGION STRUCTURE REVIEW took
# had been printing in pasmo's warning noise for months (and pasmo could only see
# two thirds of it -- `Var never used` is per-symbol, so it cannot see a routine
# reached only from OTHER dead code).
#
# ⚠️ IT HANGS OFF THE `basic-reloc` PHONY TARGET, NEVER OFF THE $(RELOC_SYM) FILE
# RULE. It needs BOTH .sym files, and $(SUB_ROM) already depends on $(RELOC_SYM)
# through sub/basic-resident-abi.inc -- so making $(RELOC_SYM) depend back on
# $(SUB_SYM) would close the build-graph cycle this Makefile is shaped to avoid
# (see the $(RELOC_ROM) rule's note above).
#
# `make deadcode` is the same sweep in --report mode: it prints the allowlisted
# spans too and always exits 0, for use while writing a routine ahead of its
# caller. tools/deadcode-allow.txt is the escape valve -- and a CONTROL, not a
# suppression list: the gate asserts every entry is still detected as dead, which
# is the only warning available for this tool going blind and reporting a clean
# tree while measuring nothing.
deadcode: $(RELOC_SYM) $(SUB_ROM) $(DISK_ROM)
	python3 tools/check_dead_code.py --report $(RELOC_SYM) $(SUB_SYM) $(DISK_SYM)

# --- D-ALIASGATE: an `equ` emits no bytes, so `deadcode` above cannot see an
# unreferenced ALIAS of a code label. This is that arm. Source-only: no ROM, no
# symbol table, no build dependency.
dead-alias-check:
	python3 tools/check_dead_aliases.py --selftest
	python3 tools/check_dead_aliases.py

# --- Layout invariant (D-LAYOUTINV) -------------------------------------------
# The property a LAYOUT PASS is allowed to preserve: every routine keeps its
# ORDERED INSTRUCTION SEQUENCE, and only its address and the FORM of its branches
# may move. Strictly stronger than "the battery is green" -- a battery samples
# behaviour, this asserts the code is the same code.
#
# 🔴 DELIBERATELY NOT COLLECTED INTO `make gates`. It is vacuous without a
# recorded baseline, and the baseline is meaningful only for the duration of a
# pass: ordinary work CHANGES routine bodies, which is exactly what this refuses.
# Collected, it would be red on every normal commit and would teach its readers
# to ignore it. Record before a pass, check after each step, delete when done.
layout-invariant:
	python3 tools/check_layout_invariant.py

layout-invariant-record:
	python3 tools/check_layout_invariant.py --record

layout-invariant-selftest:
	python3 tools/check_layout_invariant.py --selftest

# --- Redundant-load sweep (D-LOADSWEEP) ---------------------------------------
# The gate D-RETLN asked for on 2026-08-02 and did not get: it carved 160 dead
# bytes of one shape (`call skip_spaces` / `ld a,(hl)`, where the callee already
# returns with A = (hl)) and filed the SHAPE, noting "a redundant-load sweep is a
# two-line matcher". Seventeen days later D-EVSPDUP found the identical idiom at
# `ev_sp` BY HAND while scouting 5 B for something else, carved 72 B from
# expr.asm, and left NINE MORE SITES in two other files -- which this sweep found
# on its first run, for a further 27 B. That is why it FAILS rather than reports.
#
# It PROVES only the tight-skip-loop shape (`ld a,(PTR) / cp / ret cc / inc PTR /
# jr back`) and flags everything else as a CANDIDATE for a human to read; it
# resolves each site to its ENCLOSING LABEL's region rather than to its file,
# because str-engine.asm spans both and pricing it by file got 18 B of low region
# wrong. Needs $(RELOC_SYM) for that resolution -- it degrades to "region
# UNRESOLVED" without one rather than guessing.
redundant-load-check: $(RELOC_SYM)
	python3 tools/redundant_load_sweep.py

# --- Inline-index tenant calls (D-STUBINL, space plan B-11) --------------------
# basic/subromcall.asm's sc_inl0/sc_inl1/sr_inl0/sr_inl1 read the byte AFTER their
# `call` as the tenant's entry. A site that forgets that `db` runs the next opcode
# as the index and calls some other tenant -- no emulator gate can name which.
# Reads the source only: every reference is an unconditional `call` followed by
# its own table's `db low (...)`, and never inside a body sub/ or disk/ assembles.
stubinl-check:
	python3 tools/check_stub_inline.py

# --- Wall-assertion check (D-WALLDATE) ----------------------------------------
# D-REPRICE found FOUR open TODO items asserting a CURRENT free-space figure in
# prose, all four wrong, three of them UNDERSTATING the wall -- so each read as
# LESS affordable than it was. Deciding "is this sentence stale?" needs English
# tense; this asks the mechanical question instead: a free-space figure must
# carry a DATE or a COMMIT, and must not be phrased in the present tense. A
# dated reading then STANDS AS TAKEN and is never second-guessed.
# Calibrated against the pre-D-REPRICE TODO.md, where all four were live: it
# catches 4/4. Its first two drafts caught 0/4 and 3/4 -- see the header.
wall-assertion-check:
	python3 tools/wall_assertion_check.py

# --- D-PERFPIN: the standing ASYMMETRIC performance check ---------------------
# Joost's policy is "faster or comparable is not a worry; significantly SLOWER
# is", and the PAINT item proposed a standing check for it. 🔴 BUT "slower than
# both references" cannot be the gate: PAINT is 2x slower today and that is a
# filed, open on-par-speed item, so such a gate would be RED on arrival and teach
# nobody anything. This fires on DRIFT AGAINST A PIN instead -- it cannot go red
# for being slow, only for getting SLOWER -- and the reference columns are
# reported for context. It exists because the drift ALREADY happened unnoticed:
# the flood went 29.742824 (2026-08-25) -> 30.922748, +4.0%, with nothing
# watching. ~13 s; the mark stopwatch is exact and repeats bit-identically, which
# is what makes a 3% margin legitimate rather than optimistic.
perf-pin-check: repack-machine
	python3 tools/check_perf_pins.py

# --- D-RAMCLAIM: a RAM free-space claim may not contain a NAME ----------------
# `wall-assertion-check` above polices ROM figures and dates them; RAM figures
# had NO gate, so they rot silently -- sysvars.inc advertised "376 B spare" where
# 10 were, for three slices, and the ASSEMBLER caught it rather than any reading.
# 🎯 The class bit again the day this was written: D-CTLPOOL added
# `CTLLIM equ $E056` and left a neighbour claiming `$E056..$E080 is FREE`.
# ⚠️ A CLAIM IS DECLARED (`; FREE-RAM $A..$B`), NOT PROSE-MATCHED. The first cut
# matched prose and reported 7 violations of which most were its own misreading
# -- a cell's own extent read as a claim, a layout table's "FREE" describing the
# named cell, a comment QUOTING a claim it had already corrected. Prose that
# still looks free-shaped is listed ADVISORY so the set can be migrated
# deliberately instead of hiding behind a tighter regex.
# 🔴 NAME-LEVEL ONLY, AND IT SAYS SO: an address is where a cell STARTS, never
# how long it is, so a cell can extend up into a claim from below (TOKBUF's
# 612 B delta is 36 B free). Extent needs the machine -- scratchpad/ramfree_probe.py.
ram-claim-check:
	python3 tools/check_ram_claims.py --selftest
	python3 tools/check_ram_claims.py

# --- ram-map-check: the EXTENT half `ram-claim-check` says it cannot do -------
# 🔴 THE OTHER GATE'S OWN HEADER NAMES THIS GAP: *"an address is where a cell
# STARTS, never how long it is ... promoting the sweeper to a gate on deltas
# alone would have encoded exactly the error the filing warned about."* That is
# still true, so this gate does NOT police the runs. What it polices is the
# PRECONDITION for ever being able to: every cell whose extent is not
# machine-readable is pinned in tools/ram-width-allow.txt, the list may SHRINK
# and may never grow, and a pin that stops matching is equally an error.
# 🙋 FILED BY JOOST, 2026-09-21: *"I'm a bit worried that it takes you so much
# time to figure out ram usage. Don't you have a single RAM map?"* -- no, and
# this is the start of one. It also prints the CROSS-ROM OVERLAY table, which is
# the question a per-component map cannot answer: which of main's cells does
# disk.rom's sector buffer sit on top of (spec-diskcode-eviction.md §6.6aq).
ram-map-check:
	python3 tools/ram_map.py --selftest
	python3 tools/ram_map.py --check

# --- rigstick: the host joystick openMSX does not have (ruling 4's rig) -------
# D-RIGBLOCK: openMSX 21.0 has NO key-joystick pluggable (0 occurrences of
# `keyjoystick` in its binary) and builds `joystick1` from SDL's HOST
# enumeration, so the only route to STICK/STRIG is a device the host reports.
# 🔴 DELIBERATELY NOT IN THE BATTERY, AND THIS IS THE REASON. It cannot create
# its device without the RESTRICTED entitlement
# com.apple.developer.hid.virtual.device, so every emulator-facing arm would be
# inert -- and a gate that cannot fail is worse than no gate. It also needs
# swiftc, which nothing else in this tree does. `rigstick-selftest` covers the
# parser and the report encoder, which is the part a probe's verdict rests on;
# run it by hand. When a provisioning profile exists, wire it in then and say so.
rigstick: | $(BUILD)
	swiftc -O -parse-as-library -o $(BUILD)/rigstick tools/rigstick.swift

rigstick-selftest: rigstick
	$(BUILD)/rigstick --selftest

# `--probe` reports which of the two refusals this machine gives: nil (the
# entitlement is absent) or a SIGKILL before main (it was claimed unsigned).
rigstick-probe: rigstick
	$(BUILD)/rigstick --probe

# --- ram-map-doc: regenerate docs/ram-map.md ----------------------------------
# 🙋 JOOST, 2026-09-21: *"what I was expecting is a table that says for each RAM
# address what its purpose(es) is (are)."* That is docs/ram-map.md -- one row per
# ADDRESS, the cell's own comment as its purpose, and the column that says which
# of the OTHER component's buffers the address falls inside. `ram-map-check`
# above refuses when the file has drifted from this generator, the same
# discipline docs/tier-status.md already runs under.
ram-map-doc:
	python3 tools/ram_map.py --doc

# --- D-DEFFN §4.5: an ALIGNMENT assert over a MOVING symbol is a landmine ------
# `wall-assertion-check` and `ram-claim-check` police FIGURES; this polices the
# `IF <cond> / db UNDEFINED_SYMBOL / ENDIF` asserts themselves. Two shapes look
# identical and behave completely differently: a BUDGET assert (`IF $ > $4000`)
# is tripped by your own edit with the usual remedy, while an ALIGNMENT assert
# (`high X != high (X+n)`) is tripped by a STRANGER's unrelated edit upstream and
# its diagnostic names no remedy. `sub/deftype.asm`'s `edt_codes` guard fired
# exactly that way -- a 40 B routine added to a file included AHEAD of it.
# 🎯 The rule is the CONJUNCTION: alignment-shaped AND an operand that can move.
# Three of this tree's four alignment asserts are over symbols that cannot
# (USRTAB is the published $F39A, SUBROM_ENTRY_BASE_P1 is `equ $4010`, FN_BASE is
# separately pinned), and an assert over a pinned literal is a PROOF.
# ⚠️ ENFORCEMENT IS DETECTED IN THE SOURCE, not acknowledged in a list: the check
# looks for the `IF (low $) > n / ds` pad before the label, so deleting the pad
# turns the row red by itself instead of an allowlist entry quietly going stale.
build-assert-check:
	python3 tools/check_build_asserts.py --selftest
	python3 tools/check_build_asserts.py

# --- D-MSGEXACT §6b: a capitalised needle in a CASE-FOLDED table never matches -
# That slice broke 30 comparisons across 9 files and every one failed BY
# AGREEING -- a needle tested against an already-`.lower()`-ed screen string
# cannot match if it is capitalised, so the row reclassifies instead of going
# red. `diskbasic_probe_badfnum.py` survived TWO audits: it has no `.lower()` of
# its own, it `setdefault`s needles into `ERR_CLASSES` imported from
# `diskbasic_probe_lof`. The GATE caught it, not the audit.
# 🎯 The tables are DISCOVERED, not listed -- a hand-kept list is the thing that
# already failed. Pass 1 finds every table consumed case-folded; pass 2 flags a
# capitalised string written into one ANYWHERE, which is what crosses the module
# boundary.
needle-case-check:
	python3 tools/check_needle_case.py --selftest
	python3 tools/check_needle_case.py

# --- D-RAMFREE: ...and is a declared window ACTUALLY free? Ask the machine -----
# `ram-claim-check` above is the NAME half and refuses to claim more. This is the
# EXTENT half, and the only thing that can settle it: fill every declared span
# with a pattern, run one subsystem hard, read every byte back, report changes
# PER SPAN. Generalised 2026-09-04 from scratchpad/ramfree_probe.py, which
# watched one hardcoded window.
# 🎯 THE SPANS COME FROM sysvars.inc VIA check_ram_claims.py'S OWN REGEX, so a
# span that is declared and name-checked but never extent-checked cannot exist.
# ⚠️ Two controls, both asserting: ctl.poke writes one byte into EACH span and
# every counter must read 1; ctl.pool requires a deep GOSUB nest to move the
# control pool while no declared span moves. Repack-only, no oracle (this is a
# claim about zerobas's own map). ~3 min.
# ⚠️ NEEDS $(DISK_TEST_DSK): the `s.files` row mounts a WRITABLE COPY of the
# test image, and `diskdep-check` refuses a target that names it without
# declaring it -- the image is generated, not tracked.
ramfree-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_ramfree.py --gate $(if $(ONLY),--only '$(ONLY)',)

# --- D-TXTCEIL: a line store may not grow past the string-pool floor ----------
# The store used to compare against the CONSTANT TXTMAX ($$DB00), so
# `CLEAR n,himem` never reached it and the program grew PAST HIMEM into the
# string and variable area, silently. dl_store now publishes the live ceiling in
# SL_CEIL and the lineedit tenant bounds against it; this row went -225 B -> +71 B
# across the fix.
# 🎯 ZEROBAS-ONLY ON PURPOSE. `PRGEND <= HIMEM - POOLSIZE` is a claim about this
# machine's own map and needs no oracle. lnblank's crf-oom* rows compare FRE(0)
# against references that reserve 293 + 267*MAXFILES below HIMEM where zerobas
# reserves 12 + 50*MAXFILES (D-HIMEMRES), because D-FCH's per-channel block is
# "state ONLY (no buffer)" -- they can never agree and are the wrong instrument.
# 🔴 c.fits IS NOT DECORATION: a one-sided invariant is trivially satisfied by a
# machine that stores NOTHING, so a bound that over-refused would read green
# without it. ~4 boots.
txtceil-acceptance: repack-machine
	python3 probes/basic/basic_probe_txtceil.py --gate $(if $(ONLY),--only '$(ONLY)',)

# --- WALL LITERALS OUTSIDE TODO.md (docs/spec-wall-literals.md, D-WALLIT) -----
# `wall-assertion-check` above scopes itself to TODO.md's `- [ ]` items BY DESIGN.
# A stale figure inside a GATE, a PROBE or a source comment misleads the gate
# instead, and nobody reads it -- that is how `LOW_CEILING = 0x3FE5` sat 65 B
# stale under a comment naming the label the build measures (D-DUPSPAN2 §5.2).
# Needs the sym files, so it depends on the build; without them it SKIPS loudly.
wall-literal-check: repack-machine
	python3 tools/check_wall_literals.py

# --- HOOK-EQUATE AGREEMENT gate (D-DSKOHOOK) ---------------------------------
# The MSX hook equates live in TWO files: basic/sysvars.inc (the side that
# CONSULTS a cell) and disk/equates.inc (the side that CLAIMS it). `H_DSKO` was
# wrong in BOTH and therefore invisible -- our disk ROM claimed the address our
# BASIC consulted, so every gate read `ok`; only a FOREIGN disk ROM would have
# shown it. Fixing one file alone would be worse than the bug.
hook-equate-check:
	python3 tools/check_hook_equates.py

# --- GENERATED-FIXTURE DEPENDENCY gate (docs/spec-probe-diskdep.md) -----------
# `disk/test720.dsk` is GENERATED by `make test-dsk`, not tracked -- `git ls-files`
# does not list it. A target that runs a probe needing it and does not depend on it
# works only because some earlier target happened to build it. Four slices found one
# each, one at a time (D-ARYSITE `inputary`, D-FILESIDE `namspc`, D-COLDROW
# `stmtpend`, D-DISKDEP the remaining 48), which is what a class looks like when
# nobody has written its enumerator.
#
# 🔴 THE FILED SPLIT WAS WRONG AND THE MEASUREMENT SAYS SO. D-COLDROW filed a static
# 19-LOUD / 16-SILENT classification and warned that the silent half could AGREE
# while measuring nothing. D-DISKDEP moved the image aside and ran all seventeen
# candidates: EVERY ONE REFUSED -- `omsx_preflight` rc 2 (6), an own guard rc 2 (3),
# a `shutil.copy` traceback rc 1 (5), the `<NO DISK FIXTURE>` sentinel rc 1 (1), and
# a child probe's own guard through the acceptance runner rc 1 (1). The regex behind
# the split keyed on the VARIABLE NAME (`TEST_DSK`), so every probe that spells it
# `SRC_DSK` or copies through a local read as silent. There is no silent half.
# `make diskdep-selftest` is the calibration; a green run of this gate is not
# believed without it ([[a-prediction-and-its-reason-are-two-claims]]).
diskdep-check:
	python3 tools/check_disk_deps.py $(if $(LIST),--list,)

diskdep-selftest:
	python3 tools/check_disk_deps.py --selftest

# --- Merged repack main ROM (WS-3 / D4) ---------------------------------------
# The 32 KB slot-0 "main ROM": repacked C-BIOS + relocated BASIC ($2765-$7FFF) +
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
# C3 (2026-10-04): the C-BIOS repack patches are prerequisites too -- a patch
# edited alone used to leave the merged ROM (and the shipped .ips/.bps) stale.
$(MAIN_ROM): $(SRC) $(DEPS) tape/tape.asm $(wildcard cbios-repack/*.patch) \
             tools/build_patches.py tools/build_mainrom.py tools/build_repacked_cbios.py | $(BUILD)
	python3 tools/build_patches.py --main --cbios $(CBIOS)
repack-main: $(MAIN_ROM)
repack-boot: repack-main $(SUB_ROM)
	python3 probes/basic/basic_probe_repack_boot.py

# --- RETIRED: the slot-0 page-1 BASIC patch (lean build/basic.rom into stock C-BIOS) ---
# zerobas-msx1.ips/.bps were the shipped BASIC deliverable until 2026-07-29. They carried
# the LEAN 16 KB build, which is retired (RETIRE THE LEAN 16 KB CART, S2 --
# docs/spec-lean-retire-s2-switch.md); the shipped pair is now $(MAIN_PATCHES), the merged
# repack main ROM. Both files are deleted from the tree. If a lean build is ever wanted
# again it gets CHERRY-PICKED from the finished zerobas build rather than co-maintained
# here (user direction, 2026-07-29), so there is nothing to keep alive.

# --- The shipped BASIC patch pair (merged repack main ROM) ---------------------
# build_patches.py --main emits BOTH .ips and .bps in one run, as a side effect of the
# $(MAIN_ROM) rule above; express that with no-op followers (GNU make 3.81 has no grouped
# targets), same pattern as $(RELOC_ROM). Regenerating needs CBIOS=<checkout>.
zerobas-main-eu.ips: $(MAIN_ROM)
	@: # produced by the build_patches.py --main run above
zerobas-main-eu.bps: $(MAIN_ROM)
	@: # produced by the build_patches.py --main run above

# Regenerate the tracked shipped pair from source. The maintainer's step before
# committing a basic/ change -- NOT a prerequisite of `machines`, which must stay
# usable without a C-BIOS checkout (docs/spec-lean-retire-s2-switch.md §4.4).
release: all $(MAIN_PATCHES)

patches: $(MAIN_PATCHES)

# The shipped pair must match the sources committed beside it. D-EVFERR shipped
# two ROM-moving commits without regenerating it and `make gates` went 38/38
# green BOTH times -- `git add <paths>` instead of `git add -A` is all it takes.
# ⚠️ IT REGENERATES; it does not look at the tree. $(MAIN_ROM)'s file rule
# rewrites the pair IN PLACE, so by the time any battery finishes the WORKING
# COPY is already fresh and the defect only survives in what was COMMITTED.
# Hermetic (its own temp dir -- no build/ writes, so it is parallel-battery safe)
# and SKIPS, never passes, with no C-BIOS checkout: run_gates.py reads the
# GATE-SKIPPED sentinel and counts the unit as skipped.
# ~5 s. Spec: docs/spec-patch-freshness-gate.md.
patch-freshness-check:
	python3 tools/check_patch_freshness.py --cbios $(CBIOS)

# --- Page-0 cassette patch (assembled from tape/tape.asm; its own sub-make) ----
tape/zerobas-tape-msx1.ips: tape/tape.asm tools/build_patches.py tools/openmsx_paths.py \
                            tools/rom_patch.py
	$(MAKE) -C tape patches STOCK=$(STOCK)
tape/zerobas-tape-msx1.bps: tape/zerobas-tape-msx1.ips
	@: # produced by the tape sub-make above

tape-patches: $(TAPE_PATCHES)

# --- openMSX machine configs (INSTALL, not a portable build output) ------------
# Generate the release machines into your openMSX user dir: an EU _BASIC (the merged
# repack main ROM as an IPS on openMSX's own stock C-BIOS) and _BASIC_DISK (+ zerobas-disk
# in slot 3-1), each with zerobas-sub in slot 3-2. Plus a region-universal _TAPE per C-BIOS
# MSX1 region (stock C-BIOS + the cassette patch only; no zerobas BASIC).
# The _ZEROBASDISK provider-oracle is a TEST machine, kept out of the release set
# (see machines-oracle). Configs embed absolute paths, so this is install-local.
#
# ⚠️ DELIBERATELY NOT a prerequisite on $(MAIN_PATCHES): that would drag in $(MAIN_ROM),
# and with it CBIOS=<checkout> -- destroying the property that makes the repack pair
# shippable at all, that APPLYING it needs no C-BIOS checkout
# (docs/spec-lean-retire-s2-switch.md §2, §4.4 refinement 2). The installer instead dies
# loudly if the tracked patch is absent. Regenerating it is `make release`.
# The gates' freshness is covered separately, by $(MAIN_ROM)'s real file rule via
# `repack-machine` ([[ips-rebuild-after-basic-change]]) -- `machines` is the
# RELEASE-INSTALL path, not a gate path.
machines: $(TAPE_PATCHES) $(DISK_ROM) $(SUB_ROM)
	python3 tools/install-openmsx-machine.py --disk-rom $(DISK_ROM) --sub-rom $(SUB_ROM)

# Test-only: also write the Tier-1 provider-oracle machine (real CF-3300 BIOS +
# zerobas-disk swapped into slot 3-1). Not a user-facing release config.
machines-oracle: $(TAPE_PATCHES) $(DISK_ROM) $(SUB_ROM)
	python3 tools/install-openmsx-machine.py --disk-rom $(DISK_ROM) --sub-rom $(SUB_ROM) \
	  --real-bios-disk

# Build everything portable, then install the openMSX machine configs.
install: all machines

# A 720 KB FAT12 test image with deterministic content, for disk integration
# tests (see disk/TODO.md). Reproducible from the Microsoft FAT spec generator.
DISK_TEST_DSK := disk/test720.dsk

$(DISK_TEST_DSK): tools/make_test_dsk.py
	python3 tools/make_test_dsk.py $(DISK_TEST_DSK)

# The EMPTY-directory fixture (D-DSKMSG, docs/spec-basic-dskmsg.md §3): the same
# geometry with NO files, so a bare `FILES`/`LFILES` walk ends on its first
# directory entry. It is a MOUNTABLE, WRITABLE volume -- which is the whole point,
# because "the directory is empty", "no file matches the filespec" and "there is
# no disk" are three dispositions that all print nothing or an error and are
# otherwise indistinguishable ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).
DISK_EMPTY_DSK := disk/empty720.dsk

$(DISK_EMPTY_DSK): tools/make_test_dsk.py
	python3 tools/make_test_dsk.py --empty $(DISK_EMPTY_DSK)

test-dsk: $(DISK_TEST_DSK) $(DISK_EMPTY_DSK)

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
# Both zerobas-side probes name their machine here rather than defaulting to one: no probe
# picks the build under test any more (docs/spec-lean-retire-s1-explicit-machine.md).
#
# ⚠️ basic_probe_print.py used to run zerobas as `--cart build/basic.rom` on the SAME
# Philips VG-8020 as the reference, so the two sides differed only in the inserted
# cartridge. The repack build is a slot-0 32 KB main ROM, not a cartridge, so retiring
# lean (S2, docs/spec-lean-retire-s2-switch.md) makes this a machine-to-machine
# comparison -- C-BIOS + TMS9929A vs the VG-8020 -- which is the same footing the other
# 61 probes in probes/basic/ already stand on, but IS a real reduction in control. This
# is a smoke target; the verb's locked coverage lives in tests/ and the acceptance gates.
probe: $(DISK_ROM) $(DISK_TEST_DSK) repack-machine
	cp $(DISK_TEST_DSK) /tmp/zerobas-probe.dsk
	python3 probes/disk/disk_probe_dskio.py --dsk /tmp/zerobas-probe.dsk \
	        --our-machine $(REPACK_MACHINE)
	python3 probes/basic/basic_probe_print.py --zb-machine $(REPACK_MACHINE)
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
#
# ⚠️ THE MACHINE IS NAMED HERE, NOT IN THE PROBES (S1 of RETIRE THE LEAN 16 KB CART,
# docs/spec-lean-retire-s1-explicit-machine.md). This target used to set NO env var and
# ride 33 probes' hardcoded lean literals — so what it measured was decided by 33 files
# rather than by the caller. Now the gate states its subject, and --expect-build makes
# the runner REFUSE to run if the named machine is not that build.
#
# ⚠️ THIS GATE MEASURES THE REPACK BUILD since 2026-07-29 (S2 of RETIRE THE LEAN 16 KB
# CART, docs/spec-lean-retire-s2-switch.md). It used to run the SAME 34-probe corpus on
# the lean 16 KB basic.rom, with `diskbasic-acceptance-repack` as its repack twin; zerobas
# no longer builds or ships lean, so the twin IS the gate now and the lean column is gone.
# No coverage was lost -- all 34 already passed on repack (S1 §5). The alias below keeps
# the old target name working for one arc.
#
# The merged repack ROM (build/zerobas-main-eu.rom — relocated BASIC $2765-$7FFF,
# STRMAX=64, concat-aware str_eval, relocated kwtable) runs against the SAME CF-3300
# oracle. Mechanism: an EXTRA machine file (repack-machine) plus the probes' MANDATORY
# machine name — every probe's zerobas-BASIC machine reads $ZEROBAS_BASIC_MACHINE and has
# no fallback, so naming it here points the whole corpus at the repack machine while the
# CF-3300 oracle side is untouched. The runner refuses to start (vacuity guards
# §3.1.3-§3.1.6) if the machine does not resolve, is not a zerobas machine, is not the
# --expect-build named here, or if any registry probe fails to honour the env var.
#
# ⚠️ `--expect-build lean` and the runner's `lean` classification are DELIBERATELY KEPT
# (probes/disk/diskbasic_acceptance.py §3.1.4/§3.1.5) even though nothing passes them any
# more. They are what makes "this gate got pointed back at a lean machine" a loud death.
# Deleting the classification because lean retired would delete the guard that PROVES it
# retired -- and a machine named *_BASIC_DISK still resolves on any dev box that ran
# `make machines` before this change.
#
# `repack-machine` is a prerequisite so a basic/ edit rebuilds the merged ROM and
# reinstalls the config first ([[ips-rebuild-after-basic-change]]).
#
# There is deliberately NO bdos-acceptance-repack: the BDOS gate exercises the disk ROM
# (build/disk.rom) under the real CF-3300 BIOS — the string-engine arc does not touch the
# disk ROM, so BDOS behaviour was identical across the lean and repack BASIC builds.
REPACK_MACHINE  := C-BIOS_MSX1_EU_REPACK_DISK
repack-machine: $(MAIN_ROM) $(DISK_ROM) $(SUB_ROM)
	python3 tools/install-repack-machine.py --merged $(MAIN_ROM) --disk-rom $(DISK_ROM) \
	  --sub-rom $(SUB_ROM)
	python3 tools/install-repack-machine.py --merged $(MAIN_ROM) --sub-rom $(SUB_ROM) \
	  --no-disk

# --- the DISKLESS target (Joost, 2026-09-03) --------------------------------
# "it should also be possible to ship zerobas without a disk ROM ... any disk
# related thing should be validated on both". C-BIOS_MSX1_EU_REPACK_NODISK is the
# same merged main ROM and sub-ROM with slot 3-1 EMPTY -- the hardware shape of
# the Philips VG-8020 oracle -- so `nodisk-acceptance` can score a diskless
# zerobas against the machine it is meant to be faithful to. It is installed by
# `repack-machine` above so no probe can ever run against a stale copy of it.
# D-PUGATE: the PRINT USING format-specifier surface, 67 rows with an oracle.
# ⚠️ THIS ONE SCORES ZEROBAS AGAINST PINNED REFERENCE ANSWERS rather than
# re-booting both references: with the refcache off that would be ~140 extra
# boots. `--refresh` re-measures and rewrites the pins, and the plain run still
# boots all three sides. docs/spec-basic-pufloat.md §18.
# D-CATGATE: the concatenation / first-error-wins rows. BOTH of these already
# exited non-zero on DIFF -- they were never the "prints divergences and exits 0"
# class. They were the OTHER one: an honest rc that no battery collects, which is
# not an oracle. D-CATFIX (2026-09-01) is the fix they guard, and nothing in
# probes/ carries `"AB"+(0*(1/0)+1)` at all.
# D-NAMEORD's diskless side. The reorder moved DISKSLOT_OK ahead of the new-name
# evaluation, so the driveless build could have answered the no-disk error where a
# type error is due. It does not -- and this gate is what keeps that true, on the
# target whose oracle (VG-8020) has no drive either.
# D-NAMEGATE: the NAME operand rows, with their FACES pinned. $(DISK_TEST_DSK)
# because it drives a scratch copy of test720.dsk.
namegate-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_namegate.py

nameord-acceptance: repack-machine
	python3 probes/basic/basic_probe_namend.py

# --- D-ASCIIDIGIT: the ASCII-digit evaluator gap, held on TWO verbs -----------
# A numeric constant after an ASCII-parsed `AS` survives the crunch as ASCII on
# BOTH machines (D-CRUNCHBYTES read the stored program bytes off each), the
# reference evaluates it, and zerobas's `eval` has no ASCII-digit factor path --
# so it answers Syntax error. `OPEN "TS.DAT" AS 1` is the member that matters:
# the `#` is OPTIONAL after OPEN's `AS` (our own oo_parse_as_chan says so), so
# this is idiomatic BASIC that works on the reference and fails here.
#
# 🎯 THE CONTROLS ARE WHAT MAKE THE FAILING COLUMN THE ASCII DIGIT AND NOTHING
# ELSE ABOUT OPEN: the same open with `#`, and the same open with a VARIABLE in
# that position, both agree. `FIELD`'s number comes BEFORE its `AS`, so it is
# predicted OUT of the class and carried as a row rather than as an argument.
#
# Both divergences are PINNED BY FACE: a fix that lands makes this gate RED and
# tells you to delete the pin, which is the only way a closed divergence cannot
# rot into a silently-carried one. ONE REFERENCE (Disk BASIC; a diskless VG-8020
# cannot express these verbs). Repack-only; oracle-dependent.
asciidigit-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_asciidigit.py --gate

catterm-acceptance: repack-machine
	python3 probes/basic/basic_probe_catterm.py

# ⚠️ $(DISK_TEST_DSK): catusr imports basic_probe_runtail, which names the image.
# diskdep-check found this the moment the probe became a make target -- as a
# scratchpad file the dependency was real and invisible.
catusr-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_catusr.py

pusing-acceptance: repack-machine
	python3 probes/basic/basic_probe_pusing.py --gate

nodisk-acceptance: repack-machine
	python3 probes/basic/basic_probe_nodisk.py --gate

diskbasic-acceptance: $(DISK_ROM) $(DISK_TEST_DSK) repack-machine
	python3 probes/disk/diskbasic_acceptance.py \
	        --machine $(REPACK_MACHINE) --expect-build repack $(if $(ONLY),--only '$(ONLY)',)

# Deprecated alias, kept for one arc so existing docs/muscle memory keep working.
# The lean column it used to be distinguished from no longer exists.
diskbasic-acceptance-repack: diskbasic-acceptance

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
fat-error-acceptance: $(DISK_ROM) repack-machine $(DISK_TEST_DSK)
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
# --- One temp root, statically enforced --------------------------------------
# `probes/lib/probe_tmp.py` owns `/tmp/zerobas` and points `tempfile.tempdir` at
# it, so every bare `tempfile.*` in the tree lands under ONE directory and
# "clean up everything this project wrote" is `rm -rf /tmp/zerobas`. This gates
# the three rules that keep it true: a bare tempfile call must reach the root,
# only probe_tmp may set it, and the hardcoded `/tmp/...` literals that predate
# it are PINNED (tools/temp-root-allow.txt) so the set can shrink but not grow.
# 🔴 The tree already lost this once: `tests/_tmp.py` solved it for the unit
# tests and nobody carried it to the probes, which cost 1.1 GB of orphans and a
# stochastic gate flake. Emulator-free, <1 s.
temp-root-check:
	python3 tools/check_temp_root.py --selftest
	python3 tools/check_temp_root.py

# --- shared-body-check: every `.inc` under basic/ and sub/ must be ASSEMBLED --
# D-TRUNCLOAD's follow-up sweep. `deadcode-check` reasons about labels in an
# assembled image, so an UNASSEMBLED source contributes none and is invisible to
# it -- and a dead COPY of a live routine is worse than dead code, because it
# reads as the live one while being free to drift from it. Which is exactly what
# `basic/lineedit-body.inc` did -- it was DELETED 2026-08-31 once this gate had
# surfaced it and its relink copy had DIVERGED from the live one; commit 136aee8
# keeps the historical content.
shared-body-check:
	python3 tools/check_shared_bodies.py

# --- probe-reach-check: which probes does no `make` target ever run? ---------
# D-WALLIT §3.1 asked for the COUNT and nobody had it: 204 probes, 89 invoked,
# 11 imported by an invoked one, 104 unreached. `basic_probe_cas_verbs` returned
# an honest rc=1 for MONTHS because nothing collected it. The 104 are PINNED as a
# ratchet (tools/probe-reach-allow.txt) so the number can only go down; which of
# them earn a battery slot is the runtime-budget call TODO.md marks NEEDS-JOOST.
probe-reach-check:
	python3 tools/check_probe_reach.py

# --- D-UNCOLLECTED (docs/spec-uncollected.md): the battery's MEMBERSHIP -------
# `probe-reach-check` above asks whether SOME make target runs a probe. That is
# weaker than whether the BATTERY does, and the gap is where three RED suites sat:
# `make gates` collects 22 of 68 `*-acceptance` targets, nothing recorded why, and
# running the other 46 by hand found cursor/namspc/time red. Excluding a suite is
# fine; excluding it SILENTLY is not.
battery-membership-check:
	python3 tools/check_battery_membership.py --selftest
	python3 tools/check_battery_membership.py

# --- hostkill-check: no battery unit kills what it did not start (D-PKILLGATE) --
# 🔴 2026-09-30: a gate built from a scratchpad rig ran `pkill -9 openmsx` and
# killed the pool's other emulators; kwtime read 32-51 rows HANG two units away.
hostkill-check:
	python3 tools/check_no_hostkill.py --selftest
	python3 tools/check_no_hostkill.py

# --- D-FIXTUREPOLL (docs/spec-fixturepoll.md): the generated disk images -------
# disk/test720.dsk is UNTRACKED and generated. A probe wrote TS.DAT into the
# local copy; namspc-acceptance refused (nobody collected it) and D-FILESROT then
# re-measured two frozen constants against the polluted disk. `make test-dsk`
# cannot catch it -- make is timestamp-driven and a polluted image is NEWER than
# its generator, so the rule is satisfied. Regenerate and compare instead.
fixture-integrity-check:
	python3 tools/check_fixture_integrity.py --selftest
	python3 tools/check_fixture_integrity.py

# --- the disk ROM's free space (docs/disk-rom-layout.md) ---------------------
# A COVERAGE REPORT, not a gate: prints where the pinned-address pads are and how
# much room each holds. The disk ROM's APPENDABLE tail is 2 B -- every usable
# byte is interior, and the only way to find it was to diff the image by hand,
# which produced two wrong answers in one session.
diskmap:
	python3 tools/disk_rom_map.py

# --- D-REFCACHE (docs/spec-refcache.md): the reference-column store ---------
# 🔴 A CACHE IS ONE SLIP AWAY FROM "A PREDICTION COPIED INTO THE RESULT COLUMN",
# so its falsification suite is a GATE, not a script somebody remembers to run.
# 23 arms: every way a wrong hit could happen, planted and shown to miss, plus a
# green control for each and an end-to-end `verify` arm that tampers with a
# stored entry and requires the mismatch to be caught against a real machine.
refcache-check:
	python3 probes/lib/probe_refcache.py --selftest
	python3 probes/lib/probe_refcache.py --maintain

# --- D-KNIFEROM (docs/spec-kniferom.md): a knife must prove its cut landed ----
# A knife writes a source file and rebuilds. If the rebuild does not happen, the
# probe measures the PREVIOUS machine and the runner reports "moved 0 row(s)" --
# indistinguishable from an arm that legitimately found nothing, which is the
# verdict specs quote as EVIDENCE. 36 of 41 runners already hashed the built
# images; this gate says so and refuses the next one that omits it.
knife-guard-check:
	python3 tools/check_knife_guard.py --selftest
	python3 tools/check_knife_guard.py

# --- D-KNIFEROM2 (docs/spec-basic-kniferom2.md): every knife runner must ACT on
# its ROM hash, or say why it has none. A knife can be silently inert because the
# build did not happen, and it reports as "moved 0 rows" -- indistinguishable
# from an arm that legitimately found nothing.
.PHONY: knife-rom-guard-check
knife-rom-guard-check:
	python3 tools/check_knife_rom_guard.py --selftest
	python3 tools/check_knife_rom_guard.py

# --- D-SELFTEST (docs/spec-selftest.md): collect the exit codes nobody read --
# A script outside the battery can be RED FOR MONTHS and nobody learns. Measured
# 2026-08-28: of 15 scripts advertising `--selftest`, THREE were red -- two
# genuinely (a known-answer set invalidated by the slice's own fix; a frozen
# `jp $429A` literal that every carve since had moved) and one a false positive
# of the first sweep. Same shape as D-WALLIT.
selftest-check:
	python3 tools/check_selftests.py --selftest
	python3 tools/check_selftests.py

# --- The missing-capture diagnosis, falsified (docs/spec-probe-mark.md is not
# its home -- see probes/lib/omsx_missing_teeth.py). ⛔ DELIBERATELY NOT IN
# `make gates`: two of its cases SIGKILL/SIGTERM `openmsx` BY NAME, which in a
# parallel battery would hit a neighbour, so it refuses to start while any
# openmsx is running. `omsx_repl._why_missing` is a failure-formatting branch --
# no healthy run ever executes it, so nothing else in the tree can notice it rot.
# Five cases: a GREEN control that must print NOTHING, and four forced failures
# (stall watchdog, abscap backstop, a CRASH, a graceful SIGTERM) that must each
# be named DIFFERENTLY. ~40 s, needs a quiet host.
omsx-diag-teeth: repack-machine
	python3 probes/lib/omsx_missing_teeth.py

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

# --- dexp==5 bound-table acceptance (D-PINDATA) --------------------------------
# The three 5-byte unpacked-digit bound tables in basic/float.asm (tkf_ref32767 /
# tkf_ref65535 / tkf_ref32768) had NO gate: graphics-acceptance's CIRCLE corpus
# tops out at coordinate 80 (dexp 2), and intarg-acceptance covers the POKE/VPOKE/
# OUT domains but not the graphics reader. This walks the dexp==5 arm of
# domain_convert_core through every reader that reaches it -- CIRCLE coords/radius,
# POKE/VPOKE/OUT, and the sub-ROM tenant's aspect path -- as a VG-8020 differential.
# Falsified: a five-byte edit to tkf_ref32767 (3,2,7,6,7 -> 9,9,9,9,9) moves five
# rows, so it is a gate that has been shown to MOVE.
# docs/spec-rom-region-promote-input.md §5.
dexp5-pin: repack-machine
	python3 probes/basic/basic_probe_dexp5_pin.py

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
# ⚠️ NEEDS $(DISK_TEST_DSK) since D-KWDISK (2026-09-12): the Disk-BASIC rows mount
# a WRITABLE PRIVATE COPY of the test image on BOTH sides, and `diskdep-check`
# refuses a target that names the image without declaring it -- it is generated,
# not tracked. Without it every disk verb measured an EMPTY drive, which is how
# `DSKF(0)` came to be filed as reading 0 "exactly like a stub".
kwsweep: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_kwsweep.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- kwtime: the T2/T5 row type (D-KWPROVEN, Joost 2026-09-24) -----------------
# Each keyword's kwsweep test program, TIMED on the VG-8020 and here between two
# program-written marks (emulated time, deterministic). T2 = completes within 10x
# the reference; T5 = the ratio, shown and never ticked. Writes build/kwtime.json,
# which tools/tier_table.py joins with kwsweep's pin. ~30 s. The --negative run
# FIRST pads zerobas's side with a delay loop and must read every row SLOW -- a
# live control that the ratio and the bar do what the sheet will claim.
kwtime: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_kwtime.py --negative --zb-machine $(REPACK_MACHINE)
	python3 probes/basic/basic_probe_kwtime.py --zb-machine $(REPACK_MACHINE)

# --- kwram: the T4 row type (D-KWPROVEN; row type ruled by Joost 2026-09-30) -----
# Each keyword's kwsweep test program run inside a RAM write-watch window on the
# VG-8020 (the CF-3300 for disk-only rows) and here -- D-RAMFOOT's instrument.
# (a) FRE(0)/FRE("") move by the same amount; (b) the same set of documented
# work-area cells ($F380..) written, each ending on the same value; (c) cells
# written zerobas / reference, shown and never ticked. Writes build/kwram.json,
# which tools/tier_table.py joins with kwsweep's pin. The selftest, then the
# --negative run (a documented cell planted on zerobas's side of every row must
# FAIL (b)) come first. The reference side is replayed from the probe cache when
# the same group was measured before (Joost 2026-09-30).
kwram: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_kwram.py --selftest
	python3 probes/basic/basic_probe_kwram.py --negative --zb-machine $(REPACK_MACHINE)
	python3 probes/basic/basic_probe_kwram.py --zb-machine $(REPACK_MACHINE)

# --- System-variable SWEEP (the MSX work-area denominator, NOT a pass/fail gate) ---
# The same shape as `kwsweep`, for the other surface that had no denominator: every
# byte of the published work area $F380..$FFFE, on all three sides, in a baseline
# state and after each stimulus -- docs/sysvar-msx1-coverage.md, spec
# docs/spec-basic-sysvar-denominator.md.
# It exists because zerobas keeps the last error code at $E1C5 and MSX's ERRFLG at
# $F414 appears NOWHERE in this repo -- the standard address was never considered,
# and that was found BY ACCIDENT while asking an unrelated question. There was no
# list against which the question could have been asked.
# Deliberately NOT a gate: its expected state is "N addresses diverge", so it exits
# 0 with findings. Non-zero means the APPARATUS failed -- the echo guard (a stimulus
# that never arrived reads as a three-way agreement and fails TOWARD "pass"),
# C-INSTR (read_block disagreeing with a real PEEK), or C-REPRO (the sweep failing
# to re-find the known $F414 row it was not told about).
# ⚠️ --repeat is REFUSED below 2: it IS the volatility control, and the repeats are
# JITTERED because openMSX is deterministic -- an unjittered repeat reports ZERO
# volatile bytes in the whole work area, JIFFY included.
# The denominator is generated from the pinned C-BIOS checkout's systemvars.asm
# (CBIOS=<path>, default ~/projects/cbios), admissible for published sysvar
# addresses per docs/allowed-sources.md:121 -- a GENERATOR ONLY; every verdict comes
# from measurement. Repack-only + oracle-dependent (boots openMSX; needs your
# VG-8020 and CF-3300 reference ROMs); NOT part of the emulator-free `unit-test`.
sysvarsweep: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_sysvarsweep.py \
	        --zb-machine $(REPACK_MACHINE) --cbios $(CBIOS)/src/systemvars.asm \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(SIDES),--sides '$(SIDES)',)

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
# Oracle-dependent (boots
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
# The ?redo/?extra wording is now the reference's verbatim `?Redo from start` /
# `?Extra ignored` (D-MSGEXACT withdrew the D-2 own-lowercase convention); these cases
# still differential the final VALUE rather than the message, which is what makes them
# robust -- basic_probe_msgexact.py is where the TEXT is asserted. Console INPUT is repack-only, so this boots
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

# --- THE CONTROL-FRAME POOL: three gates for one arc --------------------------
# TODO.md "ARC: CONTROL FRAMES BELONG IN ONE HIMEM-BOUNDED POOL, NOT THREE FIXED
# ARRAYS", out of D-TRAPSVC / D-TRAPDEPTH / D-STACKPOOL
# (docs/spec-basic-trapsvc.md §10-§12). All three were scratchpad probes with NO
# GATE until 2026-09-04 -- the D-CATGATE lesson: an honest rc no battery collects
# is not an oracle. Promoted together, and PINNED BY FACE rather than by row name
# (D-NAMEGATE: a row that still diverges, but to a DIFFERENT face, adjudicates as
# `known` and reads green).
#
# stackpool-acceptance  the ALLOCATION MODEL. A `CLEAR` ladder + a pinned-HIMEM
#   row. ⚠️ IT GATES A RELATION, NEVER AN ABSOLUTE DEPTH: the two machines have
#   different memory maps by construction, so what is asserted is sensitivity,
#   linearity, the ERR, and -- between the two REFERENCES, where it means
#   something -- that pinning HIMEM makes them agree exactly.
# trapdepth-acceptance  the LEAK RATE, plus the `d.selfarm` GUARD (a handler that
#   re-arms its own trap and RETURNs; spec §6 warns a fix must not break it).
# ctlcross-acceptance   the INTERLEAVE semantics -- what a `NEXT` does when a
#   GOSUB frame is in the way. 🔴 THREE ROWS DIVERGE TODAY and are pinned; a
#   single pool whose NEXT search stops at the first non-FOR frame closes all
#   three, so they are the arc's behavioural acceptance.
#
# Repack-only; oracle-dependent. `make stackpool-acceptance ONLY=himem` to scope.
stackpool-acceptance: repack-machine
	python3 probes/basic/basic_probe_stackpool.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

trapdepth-acceptance: repack-machine
	python3 probes/basic/basic_probe_trapdepth.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

ctlcross-acceptance: repack-machine
	python3 probes/basic/basic_probe_ctlcross.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- D-TRAPSVC: the trap-abandonment semantics, gated at last -----------------
# "Does leaving a trap handler WITHOUT its RETURN kill that trap?" -- YES, on all
# three machines, and that is FAITHFUL (docs/spec-basic-trapsvc.md §4).
# `int.resnext` is what makes it a mechanism: the same program, same fault, same
# trap, ONE KEYWORD apart, and it keeps the trap alive on all three.
#
# 🔴 THIS SET HAD TWO DIVERGENT ROWS UNTIL D-CTLPOOL CLOSED THEM BY ACCIDENT.
# `int.six` read `6 18` and `gos.leak` `8 7` because zerobas had two fixed arrays
# (TRAPSTK_MAX = 6, GOSUB_DEPTH = 8) where the references have one HIMEM-bounded
# pool; §17 retired TRAPSTK outright and both caps went with it. Nothing was
# aiming at these rows, nothing was holding them, and the spec's §6 went on
# declining a fix for a data structure that no longer existed. Seven rows made
# green by a side effect are seven rows a gate has to own.
#
# The two references AGREE on every row, so ONE pin serves both and a side that
# leaves it is an ORACLE DRIFT, reported as such and never as a zerobas finding.
# ⚠️ The FIRST number of every two-window row is the arming guard, checked before
# any verdict: a row reading 0 because the trap never armed is a different fact
# from one reading 0 because the trap DIED. `--selftest` drives that arm, the
# typed-echo fence trap and the drift split with no emulator.
# Repack-only; oracle-dependent. `make trapsvc-acceptance ONLY=resume` to scope.
trapsvc-acceptance: repack-machine
	python3 probes/basic/basic_probe_trapsvc.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

# --- D-CTLLIM: the pool's collision floor is a STORED derivation ---------------
# spec-basic-trapsvc.md §17 shipped `CTLLIM` (= ARYEND+2) as a CACHE, against
# strheap_floor's own "DERIVED, NEVER STORED" rule, because deriving it needs an
# array-chain walk and a subrom_call per PUSH is not affordable. Its failure mode
# is SILENT: a path that grows the variable region without refreshing leaves the
# floor stale-LOW and control frames land inside live variables.
#
# 🎯 THE ROWS TEST THE CORRUPTION, NOT THE POINTER -- reading CTLLIM back would
# assert the implementation against itself. Each row fills memory with a known
# pattern, drives the pool to its floor by recursing to `Out of memory`, and
# counts cells that changed; it must be 0, and the allocation must COST depth.
# ⚠️ BOTH ALLOCATORS ARE EXERCISED: scv_alloc (scalars) and ary_alloc (arrays)
# have SEPARATE refresh hooks, and a gate that only DIMmed would leave one of
# them completely untested.
# ⚠️ Slower than its siblings by design (~150 s): every A() element crosses a
# slot here, so the budget is 180 emulated seconds -- at 45 both bulk rows read
# blank on zerobas only, which looks exactly like the corruption this hunts.
ctllim-acceptance: repack-machine
	python3 probes/basic/basic_probe_ctllim.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',)

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

# --- WIDTH valid-domain gate (docs/spec-basic-width-domain.md, D-WID; -----------
# --- docs/spec-basic-evalchk.md, D-EVALCHK) -----------------------------------
# THREE-SIDED differential (VG-8020 + CF-3300 + zb) over `WIDTH n`'s DOMAIN:
# which n each screen mode accepts, which of four errors it raises otherwise, and
# which per-mode default it records. The last residue of the abort-depth slice --
# 4d35b6d fixed how `WIDTH 300` FAILS and left open what `WIDTH` should ACCEPT
# (spec-basic-abort-depth.md §7). Five divergences, every one of them a SILENT
# screen-destroyer: no bound at all (`WIDTH 0` and `WIDTH 41..255` accepted in
# every mode), the wrong per-mode slot in graphics modes, and no Type-mismatch /
# Missing-operand check.
#
# 🔴 D-EVALCHK ADDED THE SECOND REFERENCE AND THE `dfe`/`cl` BATTERIES. `WIDTH`
# is not Disk BASIC, so the CF-3300 can express every row here and a row the two
# machines answer DIFFERENTLY has NO ORACLE (printed, never scored). The new rows
# ask which of TWO PENDING errors the reference reports when the argument
# expression has already faulted AND the value it left is also out of int16 --
# the ordering the shared `eval_byte_checked`/`eval_int16_checked` helper has to
# keep. `cl-*` measure the SAME rule at `CLEAR`, the third verbatim copy of the
# same five instructions; `CLEAR`'s own DOMAIN stays with D-CLP.
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
# ⚠️ THE INSTRUMENT IS PINNED ON EVERY ROW (lines 10-20 of the program). The
# machines boot at different text widths (VG-8020 37, zerobas 39); unpinned,
# three control rows that execute no WIDTH at all diverged on width alone while
# their ERR codes agreed. The pin also gives every reject row a KNOWN prior
# LINLEN, which is what makes "did the reject write anything anyway?" answerable.
#
# ⚠️ `CLEAR` CANNOT USE THAT FIXTURE: a CLEAR that SUCCEEDS wipes every variable,
# so the four captured numbers would read back as zeros. The `cl` rows use a
# trapped-ERR-only program, which is sound because CLEAR touches none of the
# three width sysvars. The `unt` battery stays VG-8020 + zb: it reads the raw
# screen tail, the one place the CF-3300's disk-boot banner is not pinned away.
#
# ⚠️ THESE BATTERIES ARM `ON ERROR` ON PURPOSE -- the opposite of the rule in
# abort-acceptance / str-domain-acceptance. Those measure the UNWIND, which a
# handler hides; this measures the DOMAIN, and a trapped ERR read is the only
# readout that survives a statement which has just destroyed the screen. The
# unwind stays gated by abort-acceptance; the `unt` battery is the seam.
#
# ⚠️ The in-domain rows are NOT padding, for the same reason str-domain's are not.
#
# Repack-only; oracle-dependent. `make width-acceptance ONLY=dfe-` to scope one
# battery, `SIDES=cf3300,zb` to scope the machines. Boot-per-case always (a WIDTH
# row leaves the machine unusable by construction).
width-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_width.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(SIDES),--sides '$(SIDES)',)

width-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_width.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(SIDES),--sides '$(SIDES)',)

# --- CLEAR string-pool partition (docs/spec-basic-clearpool.md, D-CLP) --------
# VG-8020 differential over the two-pool model. ✅ LANDED: `clearpool-acceptance`
# is the standing gate (52/52 gated rows, 5 reported-never-gated);
# `clearpool-characterize` is the same probe without --gate, for re-measuring.
# Before the slice this read 6/51 -- zerobas had ONE free gap where the reference
# has TWO POOLS, and CLEAR's <string-space> argument was evaluated and DISCARDED,
# so `CLEAR 500:PRINT FRE("")` answered ~15867 instead of 500.
#
# ⚠️ THE FIVE UNGATED ROWS ARE UNGATED FOR TWO DIFFERENT REASONS, and the
# batteries say which: `rep` (2) are FRE(0) absolutes, a property of each
# machine's memory map; `share` (3) are the body-OWNERSHIP divergence
# (S-CLP-5, signed off out of scope -- zerobas owns a body per variable, the
# reference decides per source). Neither is a silenced failure:
# oos-vs-oom, which used to carry the `arr` case as well, was SPLIT so the
# claim it makes ("out of string space is distinct from out of memory") is
# gated on a DIM both machines call an OOM.
#
# 🔴 THIS HEADER SAID 51/51 AND SIX-NEVER-GATED FOR TWO MONTHS, AND IT WAS A
# PREDICTION COPIED FORWARD, NOT A READING. The sixth was `arr` (1), the
# ARRAYS-arc `DIM Q(20000)` divergence this probe found in passing -- and it
# GRADUATED at 9a9a4c7, when zerobas learned to bound a dimension before it
# allocates. `oos-dim-huge` has been a scored, PASSING row ever since (both
# references and zerobas answer `Subscript out of range`), so the gate has read
# 52/52 with FIVE reported and never gated. Corrected 2026-08-09 by the TODO
# staleness sweep, which re-measured the same fact from the other end -- see
# docs/todo-staleness-sweep-2026-08.md sections 3.5 and 7. Run the gate; do not
# grep this comment.
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

# --- D-ARR-B: where the reference BOUNDS A DIMENSION (arrays arc, reopened) ----
# `CLEAR 100 : DIM Q(20000)` answers `Subscript out of range` on the reference and
# `Out of memory` here: the reference bounds a dimension BEFORE allocating,
# zerobas allocates until it runs out, so its error is right only by accident of
# size. Found as a D-CLP calibration row aimed at something else and kept there as
# `oos-dim-huge` (reported, never gated) so it could not be "discovered" later by
# a red gate.
#
# ⚠️ THE ARRAYS ARC ASKED THIS AND NEVER ANSWERED IT: spec-basic-arrays.md §4
# target #9 ("`Out of memory` onset") has no row in the §4.1 results table, while
# the other nine targets were all measured and pinned.
#
# ⚠️ EVERY ROW IS AN ERROR-CLASS ROW, NEVER A THRESHOLD. The two machines have
# different memory maps (~28.8 KB free vs ~15.7 KB) so the RAM-exhaustion point
# can never agree; each row is sized past BOTH machines' free space, and the only
# thing measured is WHICH error the machine picks.
#
# ⚠️ NO LINE MAY REACH 40 CHARACTERS (the wrapped-echo fault); the probe enforces
# it before an emulator boots.
#
# Repack-only; oracle-dependent. Boot-per-case by default: a case that succeeds in
# dimensioning leaves the array behind, and a follower's own DIM then reports
# `Redimensioned array` instead of what it measures.
arrdim-characterize: repack-machine
	python3 probes/basic/basic_probe_arrdim.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BATCH),--batch,)

arrdim-acceptance: repack-machine
	python3 probes/basic/basic_probe_arrdim.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(BATCH),--batch,)

# --- D-LINEMAX: the input line AND the crunched line -------------------------
# docs/spec-basic-linemax.md, measurement docs/linemax-vg8020-characterization.md.
# Seven batteries: rem (input-line ceiling, byte-counted from the stored line),
# tok / lnum (crunch expansion, byte-for-byte), tokx / bnd (the refusal boundary,
# read off the screen and walked a byte at a time), corrupt + code (the DAMAGE).
# Scope with ONLY=rem,tok,...; --cas adds the 3 cassette rows (R-3, one tape and
# one boot each).
#
# ⚠️ THE tok AND lnum BATTERIES CANNOT GATE THIS ALONE, and a green run of them
# means less than it looks. Their verdict is "the two machines produced the same
# bytes", and every lnum row PASSED even when the defect was live -- both machines
# crunch an identical 174 bytes and only the one with a 96-byte buffer is harmed
# (characterization §2.2). AGREEMENT ON WHAT WAS PRODUCED IS NOT AGREEMENT ON
# WHETHER IT FIT. The `corrupt` rows, which read the damage rather than the output,
# are the ones with teeth; the byte batteries pin WHERE the boundary is.
#
# ⚠️ NO LINE MAY REACH THE MACHINE'S OWN LINLEN (37), not the screen's 40 -- an
# echo at or past it WRAPS and can never be matched, and both sides then read
# `<none>` and score PASS. The probe enforces this before an emulator boots.
#
# Repack-only; oracle-dependent. Boot-per-case: the `corrupt` battery deliberately
# damages RAM, so a shared boot would carry that damage into every later row.
linemax-characterize: repack-machine
	python3 probes/basic/basic_probe_linemax.py \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(CAS),--cas,)

linemax-acceptance: repack-machine
	python3 probes/basic/basic_probe_linemax.py --gate \
	        --zb-machine $(REPACK_MACHINE) $(if $(ONLY),--only '$(ONLY)',) \
	        $(if $(CAS),--cas,)

# --- D-LNBLANK: a blank INSIDE a line number ---------------------------------
# docs/spec-basic-lnblank.md, measurement docs/lnblank-msx1-characterization.md.
# Four batteries: num (the leading line number, program.asm parse_lineno), ref
# (a line-number REFERENCE inside a statement, tokenise.inc branch_lineno -- a
# DIFFERENT code path), lit (is the rule the line-number scan's, or the number
# scanner's?) and dec (D-DECBLANK, docs/spec-basic-decblank.md: the DENOMINATOR
# of the decimal-literal scanner -- every internal seam of a literal, both other
# radices, and the rows that say a blank run which merely TRAILS a number is
# KEPT), exp (D-EXPBAD, a MALFORMED exponent marker) and nam (D-NAMBLANK,
# docs/spec-basic-nameblank.md: a blank is COPIED but changes NO tokeniser state,
# so `20 A=B1 1` is the single identifier B11 -- the `&` the TODO filed this
# under turned out to be inert on every side) and dot (D-NAMDOT,
# docs/spec-basic-namedot.md: a '.' behind a LIVE name state CONTINUES the
# identifier, and a '.' with the state DEAD leads a numeric constant WITHOUT
# needing a digit -- a bare '.' is the literal 0).
# Scope with ONLY=num,ref,lit,dec,exp,nam,dot.
#
# ⚠️ `nam` is a SUBSTRING of `lit-varname`, so ONLY=nam pulls that bounding
# control in for free; ONLY=nam,lit is what a knife on the blank rule wants,
# because `lit` carries the must-not-move cells (`lit-assign`: `20 A=1 0` is the
# SINGLE literal 10, D-DECBLANK).
#
# ⚠️ Likewise ONLY=dot selects the whole `dec-dot*` cohort and both `nam-dot`
# rows for free -- exactly the must-not-move cells of a '.'-led literal. A knife
# on the dot rule wants ONLY=dot,nam,lit,dec-dotlead; use SIDES=vg8020,zb to
# halve it (the two references agree on every row in this probe).
#
# ⚠️ --say rows are FILTERED OUT of this gate. Their payloads must PRINT BRACKETS
# (`result_span_after_echo` returns the span between the last '[' and its ']'):
# a bracketless payload reads `<none>` on every side and those compare EQUAL.
#
# ⚠️ TWO ORACLES. Every row is asked of the VG-8020 AND the CF-3300, because the
# whole slice rests on one filed row from one machine and a rule only one ROM
# shows is not a rule MSX-BASIC has. Affordable only because the readout is
# MEMORY (`("stored_line", TXTTAB)`), not the screen -- the CF-3300 boots Disk
# BASIC in SCREEN 1 and a screen readout would need chancost's geometry dance.
# SIDES= overrides the machine list; the characterize target defaults to the two
# references alone, which is what an ORACLE-LOCK pass is.
#
# ⚠️ REPEAT=2 IS MANDATORY ON A REFERENCE PASS and the reason is asymmetric: a
# dropped keystroke changes the stored bytes and looks exactly like a semantic
# divergence. In the differential direction that is a loud false FAIL; in the
# oracle-lock direction it is a false PASS FOREVER. Any row whose two boots
# disagree is UNSTABLE and fatal.
#
# `make lnblank-echo` runs the echo guard instead of the measurement. It does NOT
# squeeze whitespace the way the other probes' guards do -- blanks are the
# subject here -- so it measures the screen's left margin per capture instead.
#
# ⚠️ IT GOT SLOWER IN D-KWGAP4, ON PURPOSE, AND THE COST IS THE POINT. Until then
# `--echo` shared the measurement pass's SAY_ONLY filter, so it silently skipped
# every `--say` payload in the probe -- `err`/`dir`/`dotd`/`lnld`/`cnmd`/`lnrd`
# had NEVER been echo-guarded at all. They are guarded now, and say rows must
# boot per case (`err-ctl` reads ERRCODE state `err-over` leaves behind), so this
# target now pays ~40 extra boots per side. `run_side` splits the selection so
# only the say rows pay it; the other 518 stay batched.
lnblank-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lnblank.py \
	        $(if $(SIDES),--sides '$(SIDES)',) \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(REPEAT),--repeat $(REPEAT),)

lnblank-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lnblank.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) --repeat $(if $(REPEAT),$(REPEAT),1)

lnblank-echo: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lnblank.py --echo --repeat 1 \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',)

# --- the SAY surface, GATED (D-LNREF, docs/spec-basic-lnref.md §6) -----------
#
# 🔴 `lnblank-acceptance` CANNOT SEE A SAY-MODE ROW. The probe drops every
# SAY_ONLY row from any non---say run, so the `lnrd` battery -- which carries
# `lnrd-erl`, the control that says arming ERL did not break `IF ERL=<n>`, and
# the `lnrd-return` pin -- would be measured by hand and gated by NOTHING. That
# is the shape TODO.md files under `dir-name` as "the row has never gated
# anything", and D-LNREF's load-bearing control was sitting in it.
#
# ⚠️ SCOPED TO `lnrd-,kwgd-` BY DEFAULT, AND THAT IS NOT TIMIDITY. The rest of
# the say surface (`err`/`dir`/`dotd`/`lnld`/`cnmd`) carries `dir-name`'s KNOWN,
# FILED divergence, so a whole-surface default would ship a red target. Widening
# the default is the fix for THAT item; `ONLY=` selects any subset today.
#
# D-KWGAP4 widened it once, from `lnrd-` to `lnrd-,kwgd-`: the two new pins
# (`kwgd-delete`, `kwgd-renum`) record that the four editor verbs still do
# NOTHING at run time now that their crunch is byte-exact, and a pin nobody runs
# is the `dir-name` defect itself.
#
# D-RETLN widened it again, to `lnrd-,kwgd-,lnrt-`: the 25-row `lnrt` battery is
# what `RETURN <line>` is gated by, and six of those rows gate the IMPLEMENTATION
# rather than the outcome -- `lnrt-nogosbad`/`lnrt-nogosund` pin that the
# empty-stack check runs BEFORE the argument, `lnrt-undefp`/`lnrt-varp` that both
# failure modes pop the frame first, and `lnrt-erlund`/`lnrt-erlvar` that the
# error is filed against the RETURN's own line. None of those can be seen by a
# row reading only where control went. It carries NO pins: D-RETLN retired the
# one it inherited (`lnrd-return`) instead of adding any.
#
# D-DELETE widened it to `lnrd-,kwgd-,lnrt-,dlt-`: the 33-row `dlt` walk is what
# `DELETE <range>` is gated by, and its two ROUND-2 cohorts are rows round 1
# could not have carried -- `dlt-hipast`/`dlt-hitop` separate "a line numbered
# exactly hi must EXIST" from the far weaker "hi must not be past the last line"
# (every round-1 failure agreed with both), and `dlt-varsbad`/`dlt-contbad` see
# the FAILURE path's reset, which every round-1 failure row hid behind its own
# RUN. It retires `kwgd-delete`'s pin and adds two: `dlt-dot`/`dlt-dotedit`, for
# the current-line `.` this slice measured and DECLINED (spec-basic-delete.md §6).
#
# D-DOTLINE widened it to add `cln-,cle-,clp-`: the 71-row `.` walk, which is
# what the current-line pseudo-line-number is gated by. 108 -> 179 rows, and it
# RETIRES FOUR PINS (`dlt-dot`, `dlt-dotedit`, `lst-dot`, `lse-dotedit`) while
# adding NONE -- the first cohort here to shrink the pin set rather than grow it.
# 🔴 The `clp-` third of it reads the PUBLISHED CELL (`DOT $F6B5`) by PEEK rather
# than reading `.`'s behaviour, and it is not redundant with the other two: on a
# cold machine, and after a `NEW`, the program is EMPTY, so `LIST .` prints
# nothing whatever the cell holds and the behavioural rows are STRUCTURALLY BLIND
# to both questions. Every `clp` row has a `cln`/`cle` twin, and the twins
# agreeing is what makes the PEEK evidence about `.` and not about a byte.
#
# ⚠️ `kwgz-` IS DELIBERATELY NOT HERE. Those rows are SIDE_LOCKed to zerobas
# (AUTO is interactive, LLIST drives an unplugged LPTOUT -- both hang a
# reference), so they carry no oracle lock and gate nothing. Read them with
#   python3 probes/basic/basic_probe_lnblank.py --say --only kwgz- --sides zb
# D-DOTGAPS widened it again, to add `cld-,csv-,dsk-,crf-`: the 23 rows that
# close the three questions D-DOTLINE answered by reasoning (an ASCII LOAD/MERGE
# writes `.`; the ASCII-SAVE reading on a SECOND reference and a second device; a
# REFUSED store writes it). 181 -> 204 rows, and it is the first cohort here to
# need HARDWARE: `cld`/`csv` mount or record a cassette, `dsk` needs a disk.
#
# 🔴 THE "~1.5-2 h ON TOP OF ~2 h" THAT USED TO BE WRITTEN HERE WAS WRONG BY ~25x.
# MEASURED 2026-08-04 (D-LASTINJ): the whole 204-row three-side walk, `repack-machine`
# included, takes **8 min 58 s** -- 612 boot-per-case runs at ~0.9 s each, which is
# what an unthrottled `renderer none` openMSX costs ([[emulator-gates-are-fast-dont-
# sleep-poll]]). The old figure predates the harness dropping sleep-polling, and it
# was never re-measured. That is not harmless documentation: it is a standing
# argument for not running a gate, and it won that argument in D-LATCH, which
# skipped this suite on cost and filed the gap. Scope with ONLY= when iterating,
# but do not skip it -- it is nine minutes.
#
# 🔴 THE `dsk-` ROWS ARE CAPABILITY-LOCKED, NOT DROPPED. The VG-8020 has no disk,
# so those five rows are measured on cf3300 + zb and gate ACROSS THOSE, while the
# older `kwgz-` lock (AUTO/LLIST HANG a reference) still removes its rows from
# the run entirely. Two kinds, per row, with per-row reasons -- before D-DOTGAPS
# SIDE_LOCK held one global string, which is precisely why a cf3300-only reading
# had to live in a document instead of in a gate.
lnblank-say-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lnblank.py --gate --say \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        --only $(if $(ONLY),'$(ONLY)',lnrd-,kwgd-,lnrt-,dlt-,lst-,lse-,cln-,cle-,clp-,cld-,csv-,dsk-,crf-) --repeat $(if $(REPEAT),$(REPEAT),1)

# --- D-EDITVERB: RENUM / AUTO / LLIST (docs/spec-basic-editverb.md) ----------
#
# The three editor verbs whose STATEMENT half TODO.md carried as open. 60 rows,
# three sides, three DIFFERENT readouts -- which is why this is its own probe
# and not more rows in basic_probe_lnblank.py:
#
#   `rnm-`  the screen, anchored on the RENUM command itself and NOT on the
#           trailing LIST. Anchoring on the LIST made the reading the listing
#           only, so `Undefined line N in M`, `Illegal function call` vs
#           `Syntax error`, and AUTO's whole session were outside the window --
#           a machine that printed no message at all would have passed.
#   `aut-`  the same readout, but the case presses Ctrl-STOP mid-way (`@BREAK`,
#           omsx_repl): an AUTO session cannot be left by typing, because
#           Ctrl-STOP is not a character and never rides KEYBUF.
#   `llt-`  🔴 the PRINTER LOG. `plug printerport logger` reports READY
#           unconditionally, so LLIST cannot block -- which is what refutes
#           D-KWGAP4's filed "LLIST hangs an unplugged LPTOUT, so SIDE_LOCK
#           refuses a reference". The reading is the byte stream the program
#           sent, CR/LF included.
#
# ⚠️ THE `aut-` AND `llt-` BATTERIES RUN BOOT-PER-CASE, FOR TWO DIFFERENT
# REASONS, AND BOTH WERE MEASURED RATHER THAN ASSUMED. AUTO is MODAL: batched,
# `aut-nocomma` read `0` on BOTH references (an AUTO prompt left over from the
# case before) and `aut-plain` read `<NO ECHO>`; alone, `aut-nocomma` is
# `Illegal function call` on all three sides. The printer log is TRUNCATED once
# per boot and accumulates within one, so a batched case's output is a delta --
# correct right up until run_differential self-heals one case boot-per-case,
# after which every later delta is silently wrong.
#
# ⚠️ AND THE RESET HAS TO BE CARRIED INTO EACH CASE on that path: run_cases
# IGNORES `reset` when batch=False, and the CF-3300's reset answers its boot
# date prompt and sets SCREEN 0. Without it every CF-3300 row read `<NO ECHO>`
# while the other two sides agreed -- an apparatus failure shaped exactly like
# one machine disagreeing.
editverb-acceptance: repack-machine
	python3 probes/basic/basic_probe_editverb.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) --repeat $(if $(REPEAT),$(REPEAT),1)

# --- D-LPTVERB: the REST of the printer surface (LPRINT / LPOS / LFILES) -------
# docs/lptverb-msx1-characterization.md. 38 rows in four batteries, and they do
# NOT share a readout or even a SIDE SET:
#   lpr-  the printer log      LPRINT   vg8020 + cf3300 + zb
#   lps-  the screen           LPOS     vg8020 + cf3300 + zb
#   scr-  the screen           the halves a printer-log row CANNOT see
#   lfl-  the printer log      LFILES   🔴 cf3300 + zb ONLY
#
# 🔴 LFILES IS TWO-SIDED BY CONSTRUCTION, NOT BY OMISSION. It is a Disk-BASIC
# word and the VG-8020 has no disk ROM, so that side would measure the absence of
# a disk interface rather than of a language feature. This is the half of the
# filed printer reason D-EDITVERB did NOT refute: basic_probe_kwsweep.py's
# `lfiles` row carries NEEDS-DISK *and* printer-bound, and only the second fell.
# The probe prints the side set rather than letting a reader infer it.
#
# ⚠️ EVERY BATTERY PLUGS A PRINTER, INCLUDING THE SCREEN ONES -- with none
# plugged the VG-8020's LSTOUT tight-polls port $90 forever and the machine hangs
# (D-EDITVERB hung a screen row on an LLIST exactly that way). A `logger`
# pluggable is READY unconditionally and changes no screen output.
#
# ⚠️ AND EVERY BATTERY BOOTS PER CASE. The printer log is truncated once per BOOT,
# so a batch makes each capture a delta -- fine until one case is re-run
# boot-per-case, after which every later delta is silently wrong. And the printer
# COLUMN survives a case, so a batched `lps-init` ("a fresh head is at 0") reads
# whatever the previous case left. Deterministic, so --repeat cannot catch it.
lptverb-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lptverb.py \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) --repeat $(if $(REPEAT),$(REPEAT),1)

# The GATED form. ✅ ALL FOUR BATTERIES, 39 ROWS, SINCE D-LFILES (2026-08-06,
# docs/spec-basic-lfiles.md). This target used to carry `--only lpr-,lps-,scr-`
# because LFILES had a token equate and nothing else -- page 1 ended D-LPTVERB at
# 7 B and the verb did not fit -- and the probe PRINTED `NOT GATED: lfl- (LFILES)`
# with the reason on every run rather than dropping the battery silently, on the
# ground that a permanently red gate is one that gets ignored but a printed hole is
# not. The hole is closed: the walk moved to the sub-ROM dirverb tenant, which paid
# for the verb (page 1 7 -> 194 B), so the default `ONLY` is gone with it.
#
# ⚠️ THE `lfl-` BATTERY IS STILL TWO-SIDED, and that is scored per row, not by
# dropping it: a row is judged over the sides that CAN measure it, so LFILES's
# missing VG-8020 column prints `[not measurable on: vg8020]` instead of DIFF.
#
# ⚠️ BOTH DISK FIXTURES ARE PREREQUISITES SINCE D-DSKMSG. The `lfl-` battery
# mounts test720.dsk, and its empty-directory rows mount empty720.dsk; the probe
# answers `<NO DISK FIXTURE>` for a missing one, which the gate scores as a
# divergence rather than as agreement -- loud, but the loudness is a fallback,
# not the plan. `lptverb-acceptance` used to name neither.
lptverb-acceptance: repack-machine $(DISK_TEST_DSK) $(DISK_EMPTY_DSK)
	python3 probes/basic/basic_probe_lptverb.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) \
	        --repeat $(if $(REPEAT),$(REPEAT),1)

# --- KILL's and NAME's no-match MESSAGE ---------------------------------------
# docs/spec-basic-dskmsg.md (KILL, R-DK1) + docs/spec-basic-dkname.md (NAME,
# R-DK2). The oracle differential D-LFILES's residual was blocked on. Two-sided
# by construction (cf3300, zb): KILL/NAME/FILES are Disk-BASIC words and a
# diskless MSX1 answers `Syntax error` to all three, so the VG-8020 would measure
# the absence of a disk interface. HEAVY + oracle-dependent (needs your CF-3300
# reference ROMs); NOT part of the emulator-free `unit-test`.
#
# ⚠️ Its subject rows all expect an ERROR MESSAGE, the disposition that passes a
# totally dead subject, so the probe runs a positive control PER GATED VERB in
# the same invocation and exits 2 -- not 1 -- when one fails: `dsk-ctl` (a named
# file is FOUND), `dsk-killhit` (a KILL that must SUCCEED) and `dsk-namehit` (a
# NAME that must SUCCEED), each asserted on the SURVIVORS as well as the
# casualty. One per verb is not belt-and-braces: knife K-NAMECTL measured a NAME
# that renames nothing scoring GREEN on both other controls, on `dsk-namenone`
# itself, and on all 8 rows of `fat-error-acceptance`
# (docs/spec-basic-dkname.md §6.4).
dskmsg-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_dskmsg.py \
	        --sides $(if $(SIDES),'$(SIDES)',cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',)

dskmsg-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_dskmsg.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) \
	        --repeat $(if $(REPEAT),$(REPEAT),1)

# --- what a machine prints AFTER RUN"file" / LOAD"file",R ---------------------
# D-RUNTAIL: docs/spec-basic-runtail.md, measured in
# docs/runtail-msx1-characterization.md. Closes
# docs/spec-fat-error-verb-control.md §8.6 -- `run-missing`'s SECOND screen row.
# Two-sided by construction (cf3300, zb): RUN"A:name" needs a disk interface and
# a diskless MSX1 answers `Syntax error`, so the probe REFUSES a vg8020 side
# rather than dropping it. HEAVY + oracle-dependent (needs your CF-3300 reference
# ROMs); NOT part of the emulator-free `unit-test`.
#
# ⚠️ Every row is a WHOLE-TAIL match, never a substring -- the subject IS an
# extra screen row, and a substring `want` is exactly why the divergence survived
# in `fat-error-acceptance` for the whole life of that battery. THREE rows expect
# `<nothing>` and TWO expect an error message, both of which a machine that runs
# no program at all produces for free, so three POSITIVE controls (`run-hit`,
# `bare-run`, `load-plain:listing`) require program output / a listing in the
# agreed reading and the probe exits 2 -- not 1 -- when one fails. Knife K-DONE
# (spec §5) is the build that proves they are load-bearing.
runtail-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_runtail.py \
	        --sides $(if $(SIDES),'$(SIDES)',cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',)

runtail-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_runtail.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) \
	        --repeat $(if $(REPEAT),$(REPEAT),1)

# --- `RUN <lineno>` AT THE PROMPT (D-RUNLINE2) --------------------------------
# `dispatch_line`'s fast path for the REPL's own bare RUN used `is_cmd`, which
# matches on a DELIMITER -- right for telling RUN from RUNNER, wrong as a "takes
# no argument" test. Before D-RUNARG, `RUN 20` typed at the prompt ran from the
# TOP: a SILENT WRONG PROGRAM RUN, the class this project ranks worst.
# 🔴 THAT FIX WAS UNROWED until 2026-09-10. TODO.md's R2 still carried the defect
# as open and ⛔ BLOCKED; measuring it found all five rows already agreeing on
# all three machines. `namspc`'s denominator names DIRECT MODE as not covered, so
# no other battery would have caught a regression either.
# 🎯 The LETTERS are the reading (`ABC` / `BC` / `C`): an ERR column cannot tell
# "started at the top" from "started where it was asked".
# NO DISK, no cassette — five boots of the plain machine.
runline-acceptance: repack-machine
	python3 probes/basic/basic_probe_runline.py

# --- KEY n,"str" / KEY LIST / the function-key defaults (D-KEYSTR) -------------
# Ten rows on the plain machine: the n domain (1..10, ERR 5 outside), the empty
# string, and KEY LIST after a cold boot / a plant / a 20-char store / an empty
# store. Expectations are the two references' measured faces (they agree on
# every row; F6 ships the VG-8020 value by the standing style ruling).
keystr-acceptance: repack-machine
	python3 probes/basic/basic_probe_keystr.py

# --- what a machine prints AFTER RUN"CAS:x" / LOAD"CAS:x",R -------------------
# D-CASTAIL: docs/spec-basic-castail.md, measured in
# docs/castail-msx1-characterization.md. Closes docs/spec-basic-runtail.md §9 --
# the TAPE TWINS of D-RUNTAIL's two defects, which that slice left unscored
# because it had no cassette instrument.
#
# 🟢 THREE-SIDED, and the VG-8020 is a full side here BY MEASUREMENT, not by
# habit: RUN"A:name" needs a disk interface (which is why runtail-acceptance
# REFUSES a vg8020 run), but RUN"CAS:x" needs a CASSETTE PORT, which every MSX1
# has. The two references agree row for row, which is what says these readings
# are the MSX1 rule rather than a property of one machine's Disk BASIC.
#
# ⚠️ Every row is a WHOLE-TAIL match, never a substring -- the subject IS an
# extra screen row. ONE row expects `<nothing>` and THREE expect an error
# message, all of which a machine that runs no program at all produces for free,
# so three POSITIVE controls (`cas-run-hit`, `bare-run`,
# `cas-load-plain:listing`) require program output / a listing in the agreed
# reading and the probe exits 2 -- not 1 -- when one fails. Knife K-ASC (spec §5)
# is the build that proves they are load-bearing.
#
# 📌 The tape-search progress rows (`Found:`/`Skip :`) are dropped from the six
# D-CASTAIL tails, where they are not the subject, and read UNFILTERED by the
# cas2-* rows, where they are. zerobas printed NEITHER until D-CASSEARCH
# (docs/spec-basic-cassearch.md): it now prints both, for 57 B in SUB page 1, and
# `cas-load-plain:search` is RE-MEASURED and re-pinned rather than loosened. ONE
# pin remains and it is that one. A pin that moves FAILS the gate.
#
# ✅ D-CASOPEN (docs/spec-basic-casopen.md) closed the other two, for 7 B in MAIN
# page 1: OPEN"CAS:name" FOR INPUT name-matches on both references and zerobas
# did not, so it opened the NEXT file and returned the WRONG FILE'S BYTES. All
# three sides now agree, so `cas2-open` / `cas2-open:echo` are RECLASSIFIED to
# scored rows with a ZQ9 control rather than re-pinned at a value all three share.
# That slice also adds the OPEN verb's own readings: the bare form (takes the next
# file), CASE SENSITIVITY (`OPEN"CAS:rt"` does not find `RT`), and — read off the
# TAPE THE MACHINE WROTE, because the screen cannot answer it — what FOR OUTPUT
# records in its $EA header. Those two rows use a `cassetteplayer new` recording
# and probes/lib/cas_decode.py; each needs its OWN boot, since `cassetteplayer
# new` is a prologue and truncates the file at every boot.
#
# ⚠️ Three fixtures, and the reference forces each one. LOAD/RUN/MERGE/OPEN get
# $EA ASCII tapes: those verbs search for an ASCII file and skip a tokenised
# ($D3) one past the end of the tape, where they wait forever
# (docs/dotgaps-msx1-characterization.md §1.2), so a $D3 fixture would hang them
# and gate nothing. CLOAD is the exception and gets a $D3 tape, because it
# searches for a tokenised file and an ASCII tape would hang it instead. Two of
# the three hold TWO files, so the SKIP arm has something to step over -- a
# one-file tape can only ever produce a `Found:`. HEAVY + oracle-dependent (needs
# your CF-3300 reference ROMs); NOT part of the emulator-free `unit-test`.
# D-CASSAVE: docs/spec-basic-cassave.md, measured in
# docs/cassave-msx1-characterization.md. Closes the residual D-DOTGAPS filed
# (docs/dotgaps-msx1-characterization.md §3.2) and pinned as `csv-tok`.
#
# 🔴 THE SCREEN IS NOT A WITNESS. Every cassette SAVE verb prints NOTHING,
# whatever format it writes -- which is why the divergence was found sideways, by
# a `.` reading, and had to be confirmed by decoding a tape. Each row here runs on
# a FRESH RECORDING TAPE (`cassetteplayer new`) and probes/lib/cas_decode.py turns
# the WAV back into bytes: the ten-byte id run, the 6-char name, and the printable
# runs of the data block.
#
# 🟢 THREE-SIDED, and `csave` is the CONTROL that keeps the claim narrow:
# SAVE"CAS:name" is the ASCII ($EA) write on an MSX1 -- `,A` or not -- and CSAVE
# is the tokenised ($D3) one. Without that row, "SAVE"CAS:" is ASCII" reads as
# "every cassette save is ASCII", which is measurably false.
#
# ⚠️ ONE ROW PER BOOT, one recording each: `cassetteplayer new` is a prologue and
# TRUNCATES the file at every boot, so two rows sharing a run would both read one
# recording. HEAVY + oracle-dependent (needs your CF-3300 reference ROMs); NOT
# part of the emulator-free `unit-test`.
cassave-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_cassave.py \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',)

cassave-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_cassave.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) \
	        --repeat $(if $(REPEAT),$(REPEAT),1)

castail-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_castail.py \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',)

# --- cas-ascii-acceptance: LOAD"CAS:" of ASCII tapes, 1 to 4 blocks (D-CAS4BLK) --
# 🔴 This probe existed since 2026-08-18 in NO make target, and its 4-block
# assertion went red unseen: the tape PLAYED ON while BASIC tokenised, until a
# block took longer than the next leader (cal_refill never stopped the motor).
# A gate is what keeps a fixed timing bug fixed.
cas-ascii-acceptance: repack-machine
	python3 probes/basic/basic_probe_cas_ascii.py

# --- eofcas-acceptance: EOF() on a tape channel (D-EOFCAS, 2026-09-30) --------
# A CAS: channel opened FOR INPUT answers EOF on the CF-3300 (0 while data
# remains, -1 after the last line) and was ERR 5 here. Same program on both
# machines (AUTOEXEC.BAS + an $EA tape), RAM read back; three tapes, two of them
# putting the last LF on the tape buffer's LAST byte.
eofcas-acceptance: repack-machine
	python3 probes/basic/basic_probe_eofcas.py

# --- casprdir-acceptance: a tape channel used against its direction (D-CASPRDIR) --
# PRINT# to a CAS: channel open FOR INPUT, INPUT# from one open FOR OUTPUT, and
# a LINE INPUT# control, under ON ERROR: the VG-8020 raises 52 in the line; ours
# printed `load error` (untrappable) for the first. Tape built by cas_encode.
casprdir-acceptance: repack-machine
	python3 probes/basic/basic_probe_casprdir.py

# --- casbrk-acceptance: a tape search broken with Ctrl-STOP is 19 (D-CASBRK) -----
# LOAD typed (the message), and LOAD / CLOAD / RUN / OPEN FOR INPUT / MERGE "CAS:"
# under ON ERROR (19 in 20 on the VG-8020; ours ran on, or raised a stale 255).
casbrk-acceptance: repack-machine
	python3 probes/basic/basic_probe_casbrk.py

# --- castype-acceptance: a tape search filters by file type (D-CASTYPE) ---------
# Tapes holding X twice (tokenised + ASCII, both orders, CSAVE-faithful): LOAD /
# RUN / MERGE / OPEN "CAS:" take the ASCII X, CLOAD the tokenised one, the other
# type stepped over silently; MERGE / OPEN of a lone tokenised X search on (19).
castype-acceptance: repack-machine
	python3 probes/basic/basic_probe_castype.py

# --- casbin-acceptance: binary files in a tape search (D-CASBIN) ----------------
# BLOAD"CAS:X" searches by name and type (it took the FIRST file: a binary Y was
# loaded for X); LOAD / CLOAD step over a binary file; the diskless BLOAD"X".
casbin-acceptance: repack-machine
	python3 probes/basic/basic_probe_casbin.py

# --- fcbhdr-acceptance: the FCB header a program PEEKs through VARPTR(#n) -------
# Mode +0, device +4, position +6 after OPEN, for CRT: / LPT: / CAS: (VG-8020)
# and disk OUTPUT / INPUT / APPEND / RANDOM (CF-3300) -- D-FCBHDR.
fcbhdr-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_fcbhdr.py

# --- readflt-acceptance: READ of a numeric DATA item (D-READFLT) --------------
# `DATA 1.5` / `2E3` / `40000` read as on the VG-8020 (they were Syntax error /
# -25536); Overflow, Syntax error, &H/&B, blanks, a refused item stays unread.
readflt-acceptance: repack-machine
	python3 probes/basic/basic_probe_readflt.py

# --- recauto-acceptance: GET # / PUT # with no record number (D-RECAUTO) ------
# A bare GET/PUT takes the NEXT record (LOC + 1) on the CF-3300; zerobas always
# used record 1, so records written in order kept only the last.
recauto-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/disk/disk_probe_recauto.py

# --- ampb-acceptance: `&B` binary numbers read when the line runs (D-AMPB) ----
# `PRINT &B101` is 5 on the VG-8020 (the crunch keeps `&B…` as text there too);
# it was Syntax error here. Value, bare `&B`, stop at a non-binary byte, Overflow.
ampb-acceptance: repack-machine
	python3 probes/basic/basic_probe_ampb.py

# --- filesnl-acceptance: the cursor after FILES (D-FILESNL) --------------------
# The CF-3300 ends a FULL row of the listing at once, so a PRINT after FILES
# starts on its own row; a partly filled row keeps the cursor on it, on both.
filesnl-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/disk/disk_probe_filesnl.py

# --- filesbare-acceptance: FILES with a blank or drive-only pattern (D-FILESBARE)
# `FILES " "` / `"A:"` / `"a:"` / `"A: "` list the disk on the CF-3300; `""` is
# 56 and `"Q:"` 62 there too.
filesbare-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/disk/disk_probe_filesbare.py

# --- callsystem-acceptance: CALL SYSTEM, back to MSX-DOS (D-CALLSYSTEM) -------
# Illegal function call after a data-disk boot; after a DOS boot a WARM return to
# A> with the open files closed. Uses the BDOS gates' MSX-DOS disk (refuses
# without it, like bdos-acceptance).
callsystem-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/disk/disk_probe_callsystem.py

# --- resnext-acceptance: RESUME NEXT past a statement holding numbers (D-RESNEXTOVF)
# The next-statement scan read a constant's value bytes as text ($00 = end of
# line, $3A = ':'); after `PRINT 1E62*9:PRINT "A"` it skipped A.
resnext-acceptance: repack-machine
	python3 probes/basic/basic_probe_resnext.py

# --- readerl-acceptance: a refused DATA item's error names the DATA line (D-READERL)
# ERL, `Syntax error in <line>` and LIST . all name it on the VG-8020, in a program
# and from a READ typed at the prompt; RESUME NEXT still resumes after the READ.
readerl-acceptance: repack-machine
	python3 probes/basic/basic_probe_readerl.py

# --- dosmode-acceptance: MODE 40 / MODE 32 at MSX-DOS's A> (D-DOSMODE40) ----
# COMMAND.COM calls INITXT/INIT32 through CALSLT; page 0 is DOS's RAM, so the
# call must page the BIOS in. Uses the BDOS gates' MSX-DOS disk.
dosmode-acceptance: repack-machine
	python3 probes/disk/disk_probe_dosmode.py

# --- bootkeys-acceptance: SHIFT held at power-on keeps Disk BASIC out (D-BOOTKEYS)
# The key is pressed from power-on in a Tcl prologue; DSKF(0) answers or is ERR 5.
bootkeys-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/disk/disk_probe_bootkeys.py

# --- fcb0-acceptance: channel 0's FCB and the blocks' order (D-FCBSHAPE) -----
# VARPTR(#0) answers at every MAXFILES; the blocks sit table-#0-#1.. bottom-up,
# 265 apart. Every row is a RELATION: the machines' bases differ.
fcb0-acceptance: repack-machine
	python3 probes/basic/basic_probe_fcb0.py

# --- prec-acceptance: arithmetic precedence and associativity (D-DIMRESERVE S2)
# The arithmetic levels are a precedence climber since 2026-10-10; same-level
# chains, ^ chains and mixed levels against the VG-8020.
prec-acceptance: repack-machine
	python3 probes/basic/basic_probe_prec.py

# --- dimedge-acceptance: how close to the end of memory DIM and the line store
# reach (D-DIMRESERVE S3). STK_STORE_RESERVE puts the store's edge on the
# VG-8020's to the byte (store-13 stored, store-14 refused, both machines); the
# DIM edge is STK_EDGE_RESERVE, the floor zerobas's own stack sets, and its ~30 B
# residual against the reference is pinned (dim-120, dim-136 KNOWN_DIVERGE).
dimedge-acceptance: repack-machine
	python3 probes/basic/basic_probe_dimedge.py

# --- loaddi-acceptance: the clock runs while LOAD reads the disk (D-LOADDI)
# disk.rom's LOAD hook arrives through CALSLT (which returns DI) and the FDC
# driver keeps the caller's state per sector, so the whole load ran masked:
# TIME stood still and the keyboard was not scanned. The CF-3300 keeps ~50 %.
loaddi-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/disk/disk_probe_loaddi.py

# --- bootkey-acceptance: the first key after power-on is taken at once (D-BOOTSCAN)
# C-BIOS leaves the key-scan countdown SCNCNT at $FF; zerobas took its first key
# 2.5 s after the prompt. The VG-8020 row is the control.
bootkey-acceptance: repack-machine
	python3 probes/basic/basic_probe_bootkey.py

# --- putdir-acceptance: a RANDOM file's entry changes at CLOSE, not per PUT ----
# PUT then no CLOSE leaves the on-disk entry at 0 on the CF-3300 (D-LOF §4c);
# ours stamped it at every PUT (D-PUTDIR). Read from the image.
putdir-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_putdir.py

# --- dosbasic-acceptance: A>BASIC reaches disk BASIC, the DOS date with it (D-DOSBASIC) ------
# zerobas had its own banner at $4022, the standard BASENT entry MSX-DOS's BASIC calls.
dosbasic-acceptance: repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_dosbasic.py

# --- strout-acceptance: BDOS $09 STROUT prints, as on the CF-3300 (D-STROUT) ----------
# RES_PRINT ($F1C9) lived below the RAMAD $FF gate, so the C-BIOS target never had it.
strout-acceptance: repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_strout.py

# --- dosdate-acceptance: DOS dates as the CF-3300 (D-CLOSESTAMP, D-DOSDATE) -----
# FCLOSE re-dating a WRRND-written file, and SDATE moving GDATE and the file stamp.
# In the battery since both landed (2026-10-01).
dosdate-acceptance: repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_dosdate.py

# --- savedate-acceptance: disk BASIC stamps the directory as the CF-3300 (D-WRBLKSEEK (b))
# Joost 2026-10-01 "Stamp as 3300": SAVE, SAVE ,A and OPEN FOR OUTPUT each stamp
# date 0821h (1984-01-01), time 0, at the same directory index as the CF-3300.
savedate-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_savedate.py

# --- diskfull-acceptance: a full disk is Disk full (ERR 66), as the CF-3300 (D-DISKFULL)
# CLOSE (the channel stays open, a second CLOSE frees it), SAVE and PRINT#, each
# on a fresh test720 copy with every free cluster marked used. PRINT# HUNG
# before the fix; the verdict is a summary line, so a hang fails by the window.
# PRINT#'s I is a pinned divergence (12 on the CF-3300's 256 B record, 24 on our
# 512 B sector) that S10.B is expected to move.
diskfull-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_diskfull.py

# --- asavechan-acceptance: a disk write beside an open OUTPUT channel (D-ASAVECHAN)
# SAVE ,A / BSAVE / SAVE between two PRINT#1s: P1.TXT must come back whole, as on the
# CF-3300. Main's SAVE ,A and the BSAVE tenant used to stream through the live
# channel's engine globals and silently emptied it.
asavechan-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_asavechan.py

# --- nohash-acceptance: the optional `#` of a file number (D-INPUTDNOHASH) ------
# INPUT$(n,1), INPUT$(n, #1), CLOSE 1, FIELD/GET/PUT 1, OPEN ... AS 1 (+ AS 1+1,
# AS 12 -> 52, AS 1 LEN=8): each against the CF-3300. `AS 1` stores the 1 as an
# ASCII digit, so its rows also gate the evaluator's ASCII-number arm (D-ASCIINUM).
nohash-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_nohash.py

# --- dout-acceptance: a disk file open FOR OUTPUT is disk.rom's (S10.B) ---------
# LOF/LOC across 256 B records, two OUTPUT channels alternating, OUTPUT beside
# APPEND and beside INPUT, OPEN/KILL/NAME of an open file (54/64/64), an empty
# file, exactly 256 B, truncation: each against the CF-3300.
dout-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_dout.py

# --- asavedev-acceptance: SAVE ,A's file is disk.rom's (S10 increment 3) -------
# SAVE"Q.BAS",A read back from the image, every byte against the CF-3300: a
# one-line program, ~2 KB over two clusters, and the save after a PRINT# to a
# CRT: channel (D-ASAVEDEV: the listing went to the screen, Q.BAS 0 B).
asavedev-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_asavedev.py

# --- savetail-acceptance: SAVE's bad option tail is a trappable 2 (D-SAVETAIL) --
# `SAVE "X.BAS",B` / `,A,1` (CF-3300) and `SAVE "CAS:X",B` / `,A,1` (VG-8020)
# read `2 in 30` under ON ERROR; ours aborted with `load error`. Plus the
# `,A` control (a SAVE inside a program returns to the prompt on both).
savetail-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_savetail.py

# --- loadtail-acceptance: LOAD / RUN's bad option tail is a trappable 2 (D-LOADTAIL)
# `LOAD "X.BAS",Q` / `,S` / `RUN "A",5` (CF-3300) and `LOAD "CAS:X",Q` /
# `RUN "CAS:X",5` (VG-8020) read `2 in 30` under ON ERROR; ours printed `load
# error` and ran on (and took `,S` as an option). Plus the `,R` 53 control.
loadtail-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_loadtail.py

# --- inputdn-acceptance: INPUT$'s count outside 1..255 is 5, at the read (D-INPUTDN)
# INPUT$(0) / (256) / (-1) on the console, (0,#1) / (256,#1) on an OPEN channel
# (CF-3300) and INPUT$(0) on the diskless VG-8020 read `5 in 30`; a CLOSED
# channel is 59 first, and INPUT$(2,#1) reads `AB` -- the two controls.
inputdn-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_inputdn.py

# --- bloadofs-acceptance: BLOAD's `,offset` (D-BLOADOFS) -----------------------
# A RAM load relocated by &H1000, `,R,&H1000` running the relocated exec, a 16-bit
# wrap, `,S,&H100` into VRAM, a decimal 61440 (an ADDRESS, not an int16), 70000
# (6), "A" (13), a missing file with a string offset (13: parsed first), `,Q`=0.
bloadofs-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_bloadofs.py

# --- nodiskopen-acceptance: a diskless OPEN is the cassette's (D-NODISKOPEN) -----
# On the VG-8020 with no disk a device-less name opens the cassette (a second
# cassette OPEN beside it is 52, as for "CAS:"), a drive name is 56, and the
# cassette refuses RANDOM and APPEND with 56 -- the last two on the CF-3300 too.
nodiskopen-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/basic/basic_probe_nodiskopen.py

# --- bsavevar-acceptance: BSAVE's exec is an expression (D-BSAVEVAR) -----------
# A variable exec (`,Q`) is its value on the CF-3300 and, to tape, on the
# diskless VG-8020; `,SX` is 2 -- an S there is always the VRAM flag -- and
# creates nothing; a literal exec is the control.
bsavevar-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_bsavevar.py

# --- tapetail-acceptance: the cassette save verbs' bad tails (D-TAPETAIL) ------
# On the diskless VG-8020: `SAVE "CAS:X" Q` 2, `CSAVE "X",3` 5, `CSAVE "X",1,2` 2;
# a tape BSAVE's 4th argument is the exec VARIABLE even when it is S (S=70000 is
# 6 on the VG-8020 and the CF-3300); a disk BSAVE's exec is typed (70000 6, "A"
# 13, the file not created). Ours printed `load error` for the tape ones.
tapetail-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/basic/basic_probe_tapetail.py

# --- nodiskverbs-acceptance: the file verbs on the diskless target (D-NODISKVERBS)
# VG-8020 with no disk: `SAVE "X"` / `SAVE "CAS:X"` save to tape and END the run,
# `BSAVE "X",..` saves; LOAD / MERGE / BLOAD / RUN / SAVE / BSAVE of `"A:X"` are 56;
# `KILL "A:X"` 5. Ours printed `load error` / 5 and ran on after a tape SAVE.
nodiskverbs-acceptance: repack-machine
	python3 probes/basic/basic_probe_nodiskverbs.py

# --- readref-acceptance: a READ string points at the program text (D-READREF) ---
# 9 x 40-char DATA rows READ into A$() / a scalar leave FRE("") at 200 (ours ran
# out of string space); MID$ copies such a string out before writing (the program
# is untouched, LIST shows it); its copy-out's no-room is 14 on the MID$ line;
# LSET/RSET on one are 5; an edit clears the variables. VG-8020, diskless.
readref-acceptance: repack-machine
	python3 probes/basic/basic_probe_readref.py

# --- litref-acceptance: a program literal points at the program text (D-LITREF)
# 9 x 40-char literals into A$() / one into a scalar / A$=B$ with B$ READ from
# DATA leave FRE("") at 200; a DIRECT-mode literal and a computed string are still
# copied (197); MID$ on a literal-assigned string leaves the program line alone.
litref-acceptance: repack-machine
	python3 probes/basic/basic_probe_litref.py

# --- clearclose-acceptance: an accepted CLEAR closes every file (D-CLEARCLOSE) --
# CLEAR 500 / bare CLEAR / CLEAR 200,&HE000 -> the next PRINT# is 59 and the file
# holds what was written plus its Ctrl-Z; a REJECTED CLEAR (ERR 5 / 7) leaves it
# open; a PARKED second channel closes whole. Each against the CF-3300.
clearclose-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_clearclose.py

# --- wrblkalt-acceptance: two FCBs, RS = 1, alternating WRBLK (D-WRBLKRS) ------
# The BDOSX RAM gate is BLIND to disk writes; this reads the persisted artifact.
# Our WRBLK positioned as if every record were 128 B, so RS = 1 -- MSX-DOS1's
# block-I/O idiom and step 10's channel shape -- built a 32-cluster chain for
# 256 B. Both files must come out byte-exact on ours AND the CF-3300.
# --read adds the READ side (D-RDBLKMULTI): both files reopened and read in turn
# with RS = 1 RDBLK, copied onto OUT.BIN -- ours read the last-FOUND file.
# --rnd adds RDRND (D-RDRNDMULTI), the same defect: record 2k of each, alternately.
# --seek adds a 32 KB file read whole in 256 B RDBLKs (D-RDBLKSEEK): 0 wrong blocks
# on both, and ours within T2's 10x of the CF-3300 (it was 147x, now ~3x), plus
# the FCB dumps compared byte for byte outside the named open set.
# --wseek adds a 32 KB file WRITTEN in 256 B WRBLKs (D-WRBLKSEEK): byte-exact on
# both, ours within 10x (it was 59x, now ~9x), its FCB compared outside the named set.
# --end 600: ours takes ~390 emulated s for the five phases, plus boot.
wrblkalt-acceptance: repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/disk_probe_wrblk_alt.py --read --rnd --seek --wseek --end 600

# --- wprotect-acceptance: disk WRITE errors reach BASIC (D-WPROTECT, D-SAVEOPEN) --
# 🔴 zerobas reported NO disk write error at all until 2026-09-28: the driver's
# `cp 0` cleared the carry on every failed write, so a write-protected disk
# answered OK where the CF-3300 raises 68 -- and SAVE with a file open wrote
# nothing and answered OK (its selector was overwritten by the gate's flush).
# kwsweep cannot hold these rows: it runs on ONE writable image, and write
# protect needs a read-only one per case. The probe makes a private read-only copy.
wprotect-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 -u probes/basic/basic_probe_wprotect.py

castail-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_castail.py --gate \
	        --sides $(if $(SIDES),'$(SIDES)',vg8020,cf3300,zb) \
	        $(if $(ONLY),--only '$(ONLY)',) \
	        --repeat $(if $(REPEAT),$(REPEAT),1)

# --- FILE-CHANNEL COST characterization (docs/chancost-cf3300-characterization.md)
#
# What one open channel costs on a real disk-capable MSX1, measured out of the same
# FRE(0) pool programs live in. Oracle-dependent: needs your CF-3300 reference ROMs.
#
# ⚠️ This probe does NOT use omsx_repl, on purpose. omsx_repl scrapes the SCREEN 0
# name table ($0000/40col) and CF-3300 Disk BASIC boots to SCREEN 1 ($1800/32col) --
# that mismatch, not the machine, is why an earlier attempt read `<none>` on every
# row. This probe MEASURES scrmod out of RAM and picks the name table from it.
#
# ⚠️ FRE(0) is impure (counts down to SP, +6 per nesting level), so every row asks
# the byte-identical `PRINT FRE(0)` at identical depth. Boot-per-case both sides.
#
# ⚠️ EVERY ROW IS ECHO-GUARDED (docs/chancost-cf3300-characterization.md §0.1). A
# typed line that is not on screen returns MANGLED, which is fatal and which
# SUPPRESSES the derived slope/ceiling/headline. A mangled line earns a
# COMPLETELY REAL `Syntax error` -- which is what `ctl_syntax` EXPECTS, so this
# probe's own harness control fails toward "pass" without the guard.
# `--line-delay` (default 4.5) exists so the guard can be shown to CUT: at 3.1 the
# CF-3300 turns `PRINT LOF(1)` into `RIT OF1)`, on BOTH machines at once.
chancost-characterize: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) \
	  python3 probes/disk/diskbasic_probe_chancost.py \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(SIDE),--side $(SIDE),) \
	        $(if $(V),-v,)

# --- LOF(#n) SIZE-FIELD characterization + gate (D-LOF) -----------------------
# docs/spec-basic-lof-size-field.md, docs/lof-cf3300-characterization.md.
#
# What LOF reports for EVERY way a channel can be opened -- INPUT / OUTPUT /
# APPEND / RANDOM, on an existing file and on a missing one -- because the filed
# TODO row walked ONE of those paths and three of them were broken. Oracle-
# dependent: needs your CF-3300 reference ROMs.
#
# TWO INSTRUMENTS: the LOF reading off the screen, and the on-disk FAT12
# DIRECTORY of the machine's own scratch image. Only the second could separate
# "the size field is zeroed at OPEN" from "LOF computes from the directory" --
# the reference prints 256 after a RANDOM PUT while its directory still holds 0.
#
# ⚠️ TYPED LINES GET MANGLED HERE and a mangled line earns a completely REAL
# `Syntax error`. At chancost's 4.5 s cadence the CF-3300 dropped whole chunks
# after any disk-busy line; at 9.0 zerobas doubled the first character instead.
# The cadence is 14.0 s AND every row is echo-guarded: a typed line that is not
# on screen returns MANGLED, which is fatal with or without --gate (two mangled
# sides would otherwise compare equal and print `agree`).
lof-characterize: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) \
	  python3 probes/disk/diskbasic_probe_lof.py \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(SIDE),--side $(SIDE),) \
	        $(if $(V),-v,)

# `lof-acceptance` adds --gate: oracle drift on the reference column, or any
# divergence not in the probe's KNOWN_DIVERGE allowlist, fails the run.
lof-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) \
	  python3 probes/disk/diskbasic_probe_lof.py --gate \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(V),-v,)

# --- LOC(#n): record number on a RANDOM channel, file size on a sequential one,
# PER CHANNEL (D-LOC). The rows are D-LOCSEM's CF-3300 measurements plus the
# two-channel row the shape exists for. Each row mounts its own fixture copy.
loc-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/diskbasic_probe_loc.py

# --- D-DSKIO: DSKI$ / DSKO$ direct sector access (docs/spec-basic-dskio.md) ----
dskio-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/diskbasic_probe_dskio.py

# --- D-COPY: COPY "src" TO "dst" (docs/spec-basic-copy.md) ------------------------
copy-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/diskbasic_probe_copy.py

# --- diskascii-acceptance: MERGE + ASCII LOAD + ASCII SAVE, the three verbs the
# --- battery could not see (D-MERGEPORT, spec-diskcode-eviction.md §6.6at) -----
# 🔴 WHY THIS EXISTS. `diskbasic-acceptance` says 34/34 and has NO `MERGE` row --
# nor one for ASCII `LOAD` or `SAVE",A"`. The three probes that do cover them sat
# in NO make target at all, excused in tools/probe-reach-allow.txt as "archived
# and still re-provable when the code changes". That was a fair call while these
# paths lived entirely in main.
# 🔴 STEP 11 ENDED IT: since §6.6at, `MERGE` and ASCII `LOAD` open the file and
# read every byte of it THROUGH THE SLOT, so a disk.rom edit can break them and
# nothing says so -- and the re-proof only happens if whoever edits disk.rom
# remembers three probes no target runs. A suite's N/N is a claim about the rows
# it HAS.
# 🎯 ALL THREE RUN EVEN WHEN ONE IS RED, on purpose: `make` would stop at the
# first, and one failure hiding the other two is how a denominator goes missing.
# Each is a CF-3300 differential; D-REFCACHE keys on the ROM bytes, so the
# reference side is served from cache and a zerobas rebuild always misses.
# 🔴 THE PATHS ARE SPELLED OUT IN THE LOOP LIST ON PURPOSE. The first cut looped
# over bare NAMES and built `probes/disk/$$p.py` at runtime -- and
# `check_probe_reach.py` scans this file TEXTUALLY for `probes/.../name.py`, so
# it still reported all three as "no make target runs it". The target worked and
# the gate could not see it. A path a gate has to EXECUTE the Makefile to learn
# is a path that gate does not know about.
diskascii-acceptance: repack-machine $(DISK_TEST_DSK)
	@rc=0; for p in probes/disk/disk_probe_merge.py \
	                probes/disk/disk_probe_load_ascii.py \
	                probes/disk/disk_probe_save_ascii.py; do \
	  echo "=== $$p ==="; \
	  ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 $$p || rc=1; \
	done; \
	if [ $$rc -ne 0 ]; then \
	  echo "🔴 diskascii-acceptance: at least one of MERGE / ASCII LOAD / ASCII SAVE is RED"; \
	else \
	  echo "✅ diskascii-acceptance: MERGE + ASCII LOAD + ASCII SAVE all converged with the CF-3300"; \
	fi; \
	exit $$rc

# --- ctrlkeys-acceptance: a CTRL key reads as its control code (D-CTRLKEYS) -------
# cbios-repack/ctrl-keys.patch: CTRL-E read 101 (`e`) where the VG-8020 reads 5.
# Ten keys through INPUT$, plus CTRL over all 48 keys of matrix rows 0-5, against
# the VG-8020. Runs the DISKLESS machine (the keyboard is the same main ROM).
ctrlkeys-acceptance: repack-machine
	python3 probes/basic/basic_probe_ctrlkeys.py

# --- prnumwrap-acceptance: a PRINT number that does not fit moves whole (D-PRNUMWRAP)
# basic/print.asm pnum_fit: ours split ` 601` at the line edge (`6`|`01`) where
# the VG-8020 moves it to the next line whole. Seven rows (n33 fits exactly; a
# string does NOT move), against the VG-8020, on the DISKLESS machine.
prnumwrap-acceptance: repack-machine
	python3 probes/basic/basic_probe_prnumwrap.py

# --- D-SCREDIT: the screen editor's happy path (docs/spec-basic-screditor.md) ------
screditor-acceptance: repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/basic/basic_probe_screditor.py

# --- D-PARENNEST: how deep may an ordinary expression nest? The TIER 1 stack
# defect's own gate -- green with nine faces PINNED, and D-SPMERGE flips them.
parennest-acceptance: repack-machine
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/basic/basic_probe_parennest.py

# --- D-DISKERR: an empty drive is ERR 70 (docs/spec-basic-diskerr.md) ---------------
nodiskerr-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) python3 probes/disk/diskbasic_probe_nodiskerr.py

# --- D-BADFNUM: the REJECTED-channel-number grid ------------------------------
# docs/spec-basic-badfnum-channel-class.md. 12 channel-taking verbs x 5 channel
# classes, SWEPT rather than sampled, plus 4 controls, 8 trappability rows and 10
# edge cells: 82 cases. The filed item named THREE of them.
# ⚠️ The sweep is the point. A first battery sampled the last three classes on
# three verbs, read a uniform rule, and would have shipped `OPEN … AS #256` wrong
# -- OPEN being the one verb that already followed a different rule at channel 0.
# Scope with `make badfnum-characterize ONLY=clo_c2,opn_c256`.
badfnum-characterize: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) \
	  python3 probes/disk/diskbasic_probe_badfnum.py \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(SIDE),--side $(SIDE),) \
	        $(if $(V),-v,)

# `--gate`: oracle drift on the reference column, any divergence not in the
# probe's (currently EMPTY, and asserted so) KNOWN_DIVERGE, a mangled row, or a
# case with no oracle lock at all -- any of them fails the run.
badfnum-acceptance: repack-machine $(DISK_TEST_DSK)
	ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE) \
	  python3 probes/disk/diskbasic_probe_badfnum.py --gate \
	        $(if $(ONLY),--only '$(ONLY)',) $(if $(V),-v,)

# --- ERROR-MESSAGE reference-exactness gate (docs/spec-basic-msgexact.md) -----
# 55 rows: every error code the machine can reach, read back VERBATIM from all
# three sides. `--relock` re-measures the two references and rewrites the
# embedded REF_TEXT lock.
#
# 🔴 THIS TARGET EXISTS BECAUSE THE PROBE HAD NONE, AND THAT IS HOW D-DOTGAPS
# MEASURED A MACHINE WITH NO ROM BEHIND IT. `basic_probe_msgexact.py` is a named
# corpus member and was one of the 94 probes with no make target, so the corpus
# script ran it BY HAND after `rm -rf build && make basic-reloc` -- which builds
# build/basic-reloc.rom but NOT build/zerobas-main-eu.rom, the merged ROM the
# machine XML's absolute paths point at. All 55 rows read `<none>` and the gate
# reported 55 red INCLUDING ITS OWN CONTROLS (docs/spec-basic-dotgaps.md §9.2).
# Depending on `repack-machine` makes that ordering inexpressible here.
# ⚠️ A make target only fixes the path someone remembers to use; the preflight in
# probes/lib/omsx_preflight.py covers the one they type by hand.
msgexact-gate: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_msgexact.py --gate $(if $(V),--verify,)

msgexact-relock: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_msgexact.py --relock

# --- COVERAGE of the openMSX preflight (docs/spec-probe-preflight.md §3.5) -----
# The denominator, not a smoke test: every subprocess spawn site in probes/,
# tools/ and tests/ is classified, and the only exemption is STRUCTURAL (a list
# literal that provably carries no `-machine`). Anything else -- a literal with
# `-machine`, a variable this checker cannot prove `-machine`-free, an expression
# it cannot see into -- must spawn `omsx_preflight.guarded(...)`.
# A new probe that builds its own openMSX command line fails this gate.
# `make preflight-check LIST=1` prints every site and its verdict.
preflight-check:
	python3 tools/check_probe_preflight.py $(if $(LIST),--list,)

# --- REPORT-ROW GRAMMAR gate (docs/spec-probe-rowshape.md) --------------------
# A knife runner parses a probe's report to decide whether a cut reddened
# anything, and twice in one session (D-CASOPEN, 2026-08-07) it was defeated by
# the report's SHAPE: an `^`-anchored row regex matched every green run and NO
# knifed one (the exit-2 rows are indented two spaces), and a runner diffing
# report LINES scored every row as moved (the same reading prints as
# `ok  label  'value'` when the sides agree and `....  label  a='..'  b='..'`
# when nothing is scored). Both cost real re-measures.
#
# ⚠️ THIS GATE IS STATIC BECAUSE ITS SUBJECT IS UNREACHABLE AT RUNTIME. A probe's
# failure-formatting branch only ever executes under a KNIFE -- no acceptance
# gate has printed the `....` shape, ever -- so four probes carried the fault for
# months underneath a fully green corpus, and a behavioural gate would have to
# fail a positive control to see it at all.
#
# In contract: a probe printing report rows on an exit-2 path AND another path,
# computed structurally over probes/**/*.py -- never a name list. Five today.
# `make rowshape-check LIST=1` prints every site and its verdict.
rowshape-check:
	python3 tools/check_report_shape.py $(if $(LIST),--list,)

# --- READ target surface, CHARACTERIZATION (docs/spec-basic-readvar.md) -------
# 24 rows on three sides. `TODO.md` filed ONE face -- "zerobas has no string
# READ" -- but `ex_read` consumes a bare letter and stores through the
# SINGLE-LETTER int16 shim, while every other variable reference in the tree uses
# var_name_key (whole name + type suffix). Measured 2026-08-07: both references
# agree on all 24 rows, zerobas agrees on 2, so 22 divergences -- 21 refusals and
# ONE OVER-ACCEPTANCE (`DATA HELLO` / `READ A` is a Syntax error on both
# references; zerobas silently stores 0).
#
# ⚠️ THIS IS DELIBERATELY *NOT* AN ACCEPTANCE GATE YET. 22 of its 24 rows are red
# until the fix lands, and a row that can only ever be red is doc debt, not a
# gate. `readvar-acceptance` (the --gate form) ships WITH the fix; until then
# this target characterises and the table lives in
# docs/readvar-msx1-characterization.md.
#   make readvar-characterize ONLY=b.trailsp,b.qspace   # scope to rows
readvar-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_readvar.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- READ target surface, ACCEPTANCE (docs/spec-basic-readvar.md §7) ----------
# The same 24 rows, gated. Ships WITH the fix, which took 22 of them: `ex_read`
# now parses its target with var_str_type/var_name_key and stores through
# var_store_fac / strscr_desc+str_set_key -- ex_input's shape, routine for routine.
#
# 22 OF 24, AND THE OTHER TWO ARE PRINTED. `a.ary` / `a.arystr` need ex_let's array
# lvalue path (ary_op0_resolve / ary_store_write), which basic/input.asm has no twin
# for, so they are DEFERRED: measured, printed as `....` with their reason, and
# excluded from the tally in BOTH directions. A row that can only ever be red is doc
# debt, not a gate (spec §9).
#
# 🟢 `a.one` (`READ A` <- `DATA 7`) is the POSITIVE CONTROL and its failure exits 2,
# not 1: every row here answers with a short bracketed span, and a machine that ran
# no program prints no bracket on ANY side -- three sides agreeing on nothing is
# perfect agreement about nothing (`make fat-error-acceptance` once scored 8/8
# against an all-$00 disk.rom). 24 cases x 3 sides.
readvar-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_readvar.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- Does INPUT take an ARRAY ELEMENT target? (D-READVAR follow-up) -----------
# D-READVAR deferred `READ A(1)` / `READ A$(1)` and said in as many words that
# their PRICE depended on an unmeasured question: does `INPUT A(1)` diverge too?
# Measured 2026-08-08, 7 rows x 3 sides, both references agreeing on all 7:
# IT DOES, on all THREE of INPUT's target-parse arms -- `INPUT A(1)`,
# `INPUT A$(1)` and `LINE INPUT A$(1)` all read the value on both references and
# are Syntax error here. The unDIMmed row (`i.arynodim`) is what says the refusal
# is in the PARSE and not a complaint about a missing array: an MSX
# auto-dimensions to 10 on first reference, and both references read ` 7 ` there.
# Table: docs/inputary-msx1-characterization.md.
#
# ✅ PROMOTED TO AN ACCEPTANCE GATE 2026-08-08 BY D-ARYLV. It was deliberately
# characterization-only while 4 of its 7 rows could only ever be red -- "a row
# that can only ever be red is doc debt, not a gate". The array-lvalue work
# landed (docs/spec-basic-arylv.md) and all 7 now agree, so the condition that
# blocked the promotion is gone and the rows become a REGRESSION gate: they are
# the only ones in the tree that score `INPUT`'s three arms against an array
# target, and the unDIMmed row is the only one anywhere that scores auto-dim
# through a target parse.
# The 3 controls stay gating in the sense that matters -- their failure exits 2,
# because every row here needs a typed response to reach a blocked INPUT, and a
# response that never arrives makes all three sides agree about nothing.
#   make inputary-characterize ONLY=i.lineary   # scope to rows
# ⚠️ $(DISK_TEST_DSK) IS A REAL DEPENDENCY SINCE D-ARYSITE, not decoration: the
# four `i.oos*file*` rows read HI.TXT off it, and without the image they would
# read `<NO OUTPUT>` on every side and AGREE.
inputary-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_inputary.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

inputary-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_inputary.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-ARYLV CARVE SCOUT: how WIDE is the array-lvalue target surface? --------
# inputary-characterize established the CLASS (6 divergent rows, two verbs, four
# parse sites). Every one of those rows is the literal form `A(1)`, so they say
# nothing about the subscript FORM (`A(I)`, `A(1+1)`), the RANK (`A(1,2)`), the
# POSITION in the variable list (`READ A(1),B` vs `READ B,A(1)`), or the one row
# whose reference answer should be an ERROR rather than a value (`A(9)` against
# `DIM A(3)`) -- and a fix scoped to the rows that happened to be measured is a
# fix scoped to a hand-picked denominator.
#
# 🔴 IT ALSO ASKS ABOUT `FOR`, which no row in the class ever did. `ex_for`
# (basic/program.asm) still parses its loop variable with the SINGLE-LETTER shim
# `ex_read` stopped using at D-READVAR, so `FOR A(1)=`, `FOR AB=` and `FOR A%=`
# all fail to parse here. Whether they DIVERGE decides whether the array work has
# four parse sites or five -- and whether `FOR` is an array residual at all, or a
# re-run of D-READVAR's own name class in a verb nobody re-checked.
#
# ✅ IMPLEMENTED 2026-08-08 (docs/spec-basic-arylv.md), so this now has an
# ACCEPTANCE form as well: 16 rows scored, 2 DEFERRED. The two deferrals are
# `f.two`/`f.pct` -- `ex_for`'s single-letter NAME shim, a different residual --
# and they are printed with their readings rather than deleted, because a
# deferral has to carry its evidence.
# 🔴 `f.ary` IS SCORED, as a NEGATIVE control: `FOR A(1)=1 TO 3` is Syntax error
# on BOTH references, so neither this slice nor the ex_for slice that clears the
# two deferrals may make it work.
# The 3 positive controls exit 2 on failure -- c.let (`A(1)=7`) in particular,
# because it is what says the element-address MACHINERY is present, so a red row
# is a missing PARSE and not a missing store.
# Table: docs/arylv-msx1-scout.md.
#   make arylv-characterize ONLY=f.ary            # scope to rows
arylv-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_arylv.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

arylv-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_arylv.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- The four lvalue parse sites D-ARYLV did NOT measure ----------------------
# D-ARYLV closed READ/INPUT/LINE INPUT against an array-element target and
# recorded that its own "four parse sites" figure was a HAND-LIST: the count of
# sites MEASURED to diverge, not of sites that parse an lvalue. Walking
# var_name_key's callers outside vars.asm finds four more -- `INPUT #n`
# (files.asm), `FIELD` and `LSET`/`RSET` (field.asm), `MID$(...)=`
# (str-engine.asm, whose own header already says "array lvalues deferred").
#
# 🔴 SIX OF THE EIGHT ROWS HAVE ONE REFERENCE, NOT TWO. INPUT #n / FIELD / LSET
# are Disk BASIC, and a diskless VG-8020 answers Syntax error to all of them --
# it cannot express the question, so recording its answer would manufacture an
# agreement out of an absent disk controller. Those rows rest on the CF-3300
# alone, which is a WEAKER oracle than every row D-ARYLV measured, and the probe
# prints that per row rather than saying "both references agree".
#
# ⚠️ MEASUREMENT ONLY, not an acceptance gate: nothing is implemented for these
# four sites. Each site carries its own SCALAR positive control on the same
# fixture, because a red array row otherwise has two candidate causes -- the
# target parse, or a fixture that never mounted/opened/wrote. Controls exit 2.
# Table: docs/lvsites-msx1-characterization.md.
#   make lvsites-characterize ONLY=d.ary          # scope to rows
lvsites-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lvsites.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-LVFIX: an ARRAY ELEMENT as a MID$(...)= / INPUT #n target --------------
# docs/spec-basic-lvsites.md. The slice that ACTS on the measurement above --
# and it ships TWO of its four sites. `ex_mid_stmt` (str-engine.asm, the LOW
# region) and `inp_readvar` (files.asm, page 1) are +31 B of main page 1 and
# +3 B of the low region; `ex_field` and `lrset_common` are DECLINED WITH
# NUMBERS (spec §7) -- they need FLD_TAB to identify an ELEMENT and a
# FIELDed-READ hook on str_eval_arr, a third site nobody had listed, for ~+80 B
# against the 18 B that is left. Their two rows ride here as DEFERRED so a
# priced decline stays visible in a GATE, not only in a document.
#
# 🔴 THE ORACLE IS NOT UNIFORM. Only the MID$ rows have TWO references; INPUT #n
# / FIELD / LSET are Disk BASIC and a diskless VG-8020 cannot express them, so
# those rows rest on the CF-3300 alone. Carried forward, not upgraded.
# 🎯 m.arydrift / m.ctldrift exist because K-LV5 was DRAFTED BEFORE the row set
# was frozen: cutting the arrays-§13a correction reddens NO row without them.
#   make lvfix-characterize ONLY=m.ary SIDES=zb      # scope rows / sides
lvfix-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lvfix.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

lvfix-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lvfix.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-FLDARY: an ARRAY ELEMENT as a FIELD / LSET / RSET target ---------------
# docs/spec-basic-fldary.md. The half D-LVFIX declined, re-priced against a
# design: THREE of its four reasons did not survive. FLD_TAB does NOT grow (the
# discriminator does not sit beside the name key -- it IS the key, and the two
# key spaces are disjoint by construction, spec §4.2), the price is +38 B of
# main page 1 rather than ~+80, and a carve IS available -- lrset_store moves
# whole to a page-0 sub-ROM tenant and returns 57 B. What survived is that 38
# does not fit 18, which is why this slice is FUNDED rather than free.
#
# 🔴 THREE SITES, and the third is the one nobody had listed: str_eval_arr's
# FIELDed-READ hook. Teaching only the two PARSE sites about subscripts turns
# `d.ary` green FOR THE WRONG REASON and leaves `s.fldary` red.
# 🔴 EVERY ROW HAS ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express
# the question). Weaker than anything D-ARYLV rested on; not upgraded.
# 🎯 s.fldary2 / s.fldarymix exist because K-FA1 was DRAFTED BEFORE the row set
# was frozen: with ONE fielded element, a FIELD and an LSET that agree on the
# WRONG key still agree with each other, so the discriminator reddens no row.
# ⚠️ A CONTROL PER ARM (d.ctl for FIELD, s.fld for FIELDed LSET), not per site.
#   make fldary-characterize ONLY=s.fldary2 SIDES=zb    # scope rows / sides
fldary-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_fldary.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

fldary-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_fldary.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-LRVAR: LSET / RSET on a NON-FIELDed variable ---------------------------
# docs/spec-basic-lrvar.md. The last open item of the lvalue/FIELD surface --
# lrset_notfld was a bare `jp stmt_error` commented "slice-1 limit", and the two
# rows it owned (s.ctl / s.ary) were the only ones still red in
# docs/lvsites-msx1-characterization.md.
#
# 🔴 ONE DATA POINT IS NOT A RULE, and the filed residual had exactly one. The
# rule was MEASURED FIRST, over 21 rows: the target's CURRENT bytes are
# overwritten IN PLACE, its LENGTH never changes, an UNSET or EMPTY target is a
# NO-OP, and a longer source keeps its FIRST len(target) bytes for BOTH verbs --
# `RSET A$="HELLO"` on `A$="AB"` reads `HE`, not `LO`.
# 🎯 NO STORE ENGINE WAS WRITTEN: that rule is exactly what lrset_store_tenant
# already did, with the width set to the target's length and the destination to
# its own heap body. The slice is a destination generalisation, not a store.
# 🎯 n.fld2 / n.mix / n.arysep exist because K-LV2/K-LV1/K-LV6 were DRAFTED
# BEFORE the row set was frozen -- each of those three cuts reddened NO row
# against the obvious row set.
# 🔴 THE ERASE RESIDUAL IS CLOSED HERE AND IT WAS FORCED: this slice turns a
# stale element key from a LOUD `Syntax error` into a SILENT no-op, and the
# oracle (e.erase) says the reference KEEPS the field across ERASE -- which
# REFUTES the `fld_clear_ary` sweep D-FLDARY priced for it.
# 🔴 EVERY ROW HAS ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express
# the question). Not upgraded.
# ⚠️ A CONTROL PER ARM: n.fldctl (FIELDed), n.ctl (non-FIELDed), e.ctl (ERASE).
#   make lrvar-characterize ONLY=n.arysep SIDES=zb      # scope rows / sides
lrvar-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lrvar.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-IFSEM: `IF`'s EXECUTION semantics (docs/spec-basic-ifsem.md) ----------
# 🔴 THIS GATE EXISTS BECAUSE THE ARC NAME LIED. `IF` was listed as covered by
# "interp.asm core: lineerr + unit tests" -- but lineerr is LINE ENTRY, lnblank's
# ELSE rows are about CRUNCHING, and `IF` appears across dozens of probes as
# FIXTURE SCAFFOLDING. Its whole execution surface was ONE row in direct_ctrl,
# and the review found a real defect there (a false outer IF caught by a nested
# IF's ELSE). Rows: nesting depth 0/1/2, ELSE binding, the GOTO form, REM and `'`
# swallowing an ELSE, string-condition type errors, float truthiness.
ifsem-characterize: repack-machine
	python3 probes/basic/basic_probe_ifsem.py $(if $(SIDES),$(SIDES),)

ifsem-acceptance: repack-machine
	python3 probes/basic/basic_probe_ifsem.py --gate $(if $(SIDES),$(SIDES),)

# --- D-GICINI: the abort seam must STOP THE MUSIC (docs/spec-basic-gicini.md) --
# Two halves, and the second is not belt-and-braces. Knife K-GI4 deleted the
# amplitude loop while keeping `ld (MUSICF),a` and moved ZERO of the 36 rows --
# the machine sustains the note forever and every row stays green, because every
# row reads MUSICF. `--gate` scores the rows AND the PSG amplitude trace, whose
# own control (a program that never aborts) must read NON-ZERO or the trace is
# not looking at music and its verdict says nothing.
gicini-acceptance: repack-machine
	python3 probes/basic/basic_probe_gicini.py --gate $(if $(SIDES),--sides $(SIDES),)

lrvar-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lrvar.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-FORVAR: what a FOR/NEXT LOOP VARIABLE may be (docs/spec-basic-forvar.md)
# `ex_for` parses its loop variable with the SINGLE-LETTER shim `ex_read`
# stopped using at D-READVAR, so `FOR AB=` / `FOR A%=` are Syntax error where
# both references read the loop. D-ARYLV measured three rows of that; three
# readings are not a rule, and FOR differs from READ in the one way that
# matters -- NEXT MATCHES ON THE STORED NAME, so widening the name moves the
# MATCH, the frame layout and the nesting DEPTH with it.
# 🔴 f.ary is a NEGATIVE control: `FOR A(1)=` is Syntax error on BOTH
# references and must STAY that way -- this is a NAME residual, not an array
# one.
# ⚠️ THREE positive controls, and each names a different thing that could
# break: c.for (the shape ex_for handles), c.next (the NAMED match, a separate
# parse), c.let (the 2-char name STORE a fix reuses).
#   make forvar-characterize ONLY=n.xtype SIDES=zb      # scope rows / sides
forvar-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_forvar.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

forvar-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_forvar.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-NXLIST: NEXT takes a LIST of loop variables (docs/spec-basic-nxlist.md)
# `nx_end` runs `jp exec_stmt` once its frame is closed, so the `,` of
# `NEXT B,A` arrives in statement position and is Syntax error where both
# references read ` 3  3 `. D-FORVAR measured it and DEFERRED it, because
# `n.multi1` -- the same comma with the single-letter names `ex_for` already
# parsed -- proves it is a LIST rule and not a NAME rule.
# 🎯 m.count is the row for the path a fix is most likely to break: the
# loop-CONTINUES path (`nx_again`) must NOT see the comma, and only an inner
# body COUNT can say so.
# 🔴 n.nofor / n.barenofor are the CARVE's rows -- the funding merges
# nx_find's empty-stack test with nx_miss's, and no forvar row enters through
# nx_find's.
# 🔴 n.num is a NEGATIVE control: `NEXT 1` is Syntax error on BOTH references
# and must STAY so.
#   make nxlist-characterize ONLY=m.count SIDES=zb      # scope rows / sides
nxlist-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_nxlist.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

nxlist-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_nxlist.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-NXARY: a NEXT operand is a full variable REFERENCE (spec-basic-nxary.md)
# D-NXLIST measured three rows and DECLINED the fix with a price: `NEXT A(1)`
# is NEXT without FOR but `NEXT A(99)` is Subscript out of range, so the
# reference EVALUATES the subscript before matching anything and the cheap
# "a `(` makes the key unmatchable" fix answers the wrong error.
# 🎯 a.autodim is the row no DIRECT reading can take: whether the resolve
# creates an array is a side effect on a row that ERRORS, so it traps the error
# and then DIMs -- a created array reads `Redimensioned array`.
# 🎯 a.str / a.pct are the TWO-NAMESPACE rows: tgt_parse takes a MODE and
# for_name returns a TYPE CODE, and they are not the same number.
# 🔴 f.ary is a NEGATIVE control: `FOR A(1)=` is Syntax error on BOTH
# references, and the danger of teaching ex_next to resolve a subscript is that
# the same reach lands in ex_for.
#   make nxary-characterize ONLY=a.autodim SIDES=zb      # scope rows / sides
nxary-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_nxary.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

nxary-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_nxary.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-TGTSPC: a SPACE before the `(` (docs/spec-basic-tgtspc.md) -------------
# D-NXARY measured ONE row (`NEXT A (1)`) and DEFERRED it -- NOT for space. The
# fix is one instruction in `tgt_parse`, which is the lvalue family's SHARED
# target parse, so it decides what a target MEANS at NINE statement surfaces:
# NEXT, READ, console INPUT (both arms), LINE INPUT, MID$()=, INPUT #n, FIELD
# and LSET/RSET. All nine are measured here, each with the CONTIGUOUS form of
# its own statement as its own positive control, on its own fixture.
# 🎯 t.ctl/t.spc read the STORED LINE BYTES through TXTTAB, not the screen: if
# the reference's CRUNCH stripped the space, a parser-side fix would spend every
# byte in the wrong file -- and both cases look identical on screen.
# 🎯 m.trail is the SCALAR path: `MID$(A$ ,1,2)="XY"` is XYLLO on both
# references, so the trailing-space consumption is a second FIX, not a caveat.
# 🔴 x.dollar / x.name are DEFERRED: a space inside the NAME or before the `$`
# suffix is var_name_key's rule, not tgt_parse's, and it is far wider.
# 🔴 z.for is a NEGATIVE control: `FOR A (1)=` is Syntax error on BOTH
# references and ex_for must not gain tgt_parse's reach.
# ⚠️ ORACLE STRENGTH IS NOT UNIFORM: the INPUT#n / FIELD / LSET rows are Disk
# BASIC and rest on the CF-3300 alone. The probe says so per row.
#   make tgtspc-characterize ONLY=m.trail SIDES=zb      # scope rows / sides
tgtspc-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_tgtspc.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

tgtspc-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_tgtspc.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-NAMSPC: a SPACE inside a variable NAME (docs/spec-basic-namspc.md) -----
# D-TGTSPC closed the `(` position and DEFERRED two rows it could not reach.
# 🎯 THE RULE IS UNIVERSAL, NOT AN LVALUE ONE, AND `r.name` IS WHAT SAYS SO:
# `AB=7 : PRINT A B` reads ` 7 ` -- ONE value, the variable AB -- on BOTH
# references, and `PRINT` never touches tgt_parse. So the fix is one instruction
# in `is_ident_cont` (basic/vars.asm), the routine all three name-scan read
# points share, and it reaches all 11 var_name_key + 16 var_str_type call sites.
# 🎯 t.* read the STORED LINE BYTES: the $20 survives the crunch in every
# position INCLUDING before a digit (`1 A 1=1` -> 41 20 31 ...), which is what
# says the fix is the parser's and not the tokeniser's -- and the TKNAME hazard
# that could have moved this whole slice into basic/interp.asm is refuted there.
# 🔴 THE KEYWORD CONSTRAINT prices the design: this tokeniser matches keywords at
# every position mid-identifier, so `SC ORE` carries an `OR` token (t.kw) and
# `z.kw` is the negative control that says such a name must STAY refused.
# 🔴 z.miss is the other negative control: `FOR A=1 TO 2 : NEXT A B` is NEXT
# without FOR, because the joined name is a DIFFERENT variable, not junk.
# 🟢 w.* are green BEFORE and must stay green: the scan now eats a name's
# TRAILING spaces, and they are the only rows that can catch one delimiter too
# many. ⚠️ z.fldvar / z.fldstr are DEFERRED -- `ex_field` never type-checks its
# width, which z.fldstr measures with NO SPACE IN IT AT ALL.
#   make namspc-characterize ONLY=r.name SIDES=zb      # scope rows / sides
namspc-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_namspc.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# ⚠️ $(DISK_TEST_DSK) IS A REAL DEPENDENCY AND WAS MISSING UNTIL D-FILESIDE
# (2026-08-21). Every `f.*` row of kind `dsk`/`dskerr`/`dsklist` copies that image
# per case. The gap predates the listing rows -- it is the fourteen D-FNARG rows'
# dependency too -- and was fixed here because that slice is the one that noticed.
# 🔴 THE REASON D-FILESIDE GAVE FOR IT WAS WRONG AND IS CORRECTED HERE
# (D-COLDROW, 2026-08-21). It said the rows "would read `<NO OUTPUT>` on both
# disk sides and AGREE". They would not: this probe COPIES the image per case,
# so a missing image raises FileNotFoundError before openMSX is launched --
# measured by moving the file aside and running one row (rc 1, a traceback).
# The dependency is still right and still real; what is wrong is only the
# consequence claimed for its absence. The SILENT-agreement failure is real but
# belongs to the OTHER kind of probe, the kind that hands the path straight to
# openMSX (`inputary` is one, and its note is accurate). See TODO.md for the
# machine-produced split of all 35 probes that name that image.
namspc-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_namspc.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-STRPAREN: `(A$)` in every string context (docs/spec-basic-strparen.md) --
# 🔴 THE RESIDUAL CAME WITH TWO DATA POINTS AND THIS IS THE DENOMINATOR.
# D-FNEXPR filed "`(A$)` is refused in EVERY string context" off `B$=(A$)` and
# `PRINT (A$)`, measured ad hoc and never committed. Eleven contexts + three
# controls, and NO DISK ANYWHERE -- so unlike the filename battery it grew out
# of, every row here has TWO references.
# ⚠️ The eleven divergent rows are DEFERRED (printed, never scored): a known
# divergence that gates turns the battery red forever instead of measuring. The
# three CONTROLS are gated, which is what makes the eleven a reading.
strparen-acceptance: repack-machine
	python3 probes/basic/basic_probe_strparen.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-FLDWIDTH: a FIELD width is a BYTE ARGUMENT (docs/spec-basic-fldwidth.md)
# D-NAMSPC deferred two rows and filed them as a residual: `ex_field` never
# type-checked its width, so `FIELD#1,B$ AS A$` -- NO SPACE IN IT -- was `OK`
# here and `Type mismatch` on the CF-3300.
# 🎯 THE READING IS `LEN(A$)`, NOT `OK`: the whole subject lives between
# "accepted as 10" and "accepted as 0", and an [OK] fixture cannot tell those
# apart. Every accepting row reads the width BACK out of the field table.
# 🎯 d.big vs d.neg/d.256/d.257 NAME THE RULE: 70000 is `Overflow` and
# -1/256/257 are `Illegal function call`, which is exactly get_byte_arg's TWO
# STAGES -- code that already ships and is already the reference's rule -- so
# the whole domain fix is 3 bytes of `call`. And d.zero says 0 IS LEGAL,
# against this file's own header claim of "1..255".
# 🎯 m.trap says the check is PER ITEM with NO ROLLBACK (` 13  5 `: ERR 13, and
# the first field is still 5 wide), and o.dt ORDERS the checks (a bad-DOMAIN
# width with a numeric target is ERR 5, not ERR 13 -- o.wt CANNOT say that,
# both its faults are ERR 13).
# 🔴 t.noas / t.nonm are the NEGATIVE controls that bound the ERR-13 change:
# only ONE of ex_field's four exf_syn arms moves.
# ⏸ d.sum / d.sum1 are DEFERRED -- the RECORD-LENGTH rule (ERR 50) is a
# separate rule, priced at ~27 B against a 6 B wall and declined with numbers.
#   make fldwidth-characterize ONLY=d.big SIDES=zb      # scope rows / sides
fldwidth-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_fldwidth.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

fldwidth-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_fldwidth.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-ONERR0: ON ERROR GOTO 0 inside a handler RE-RAISES ---------------------
# (docs/spec-basic-onerr0.md, measured in docs/onerr0-msx1-characterization.md)
# D-NXARY filed this from ONE row that was measuring something else, and by the
# time anyone came back the row had ROTTED without the rule moving (D-NXARY's own
# auto-DIM turned its `[OK]` into `Redimensioned array`). So every program here
# is ARRAY-FREE: the error comes from `ERROR n`.
# 🎯 r.rearm is the SCOPE row and a negative control: `ON ERROR GOTO <n>` inside
# a handler RE-ARMS and runs on, all three sides. Disarming is special, so the
# fix is one test on the GOTO-0 arm and not a change to `ON ERROR`.
# 🎯 r.reexec is the row that REFUTED the 7-byte design. `PRINT"[X]";ASC("")`
# prints `[X]` ONCE on both references, so the reference restores context and
# aborts rather than handing the statement back to the run loop. Every OTHER row
# in the battery answers both designs identically.
# 🔴 r.line agrees on its error TEXT for the wrong reason -- zerobas used to run
# on and raise a FRESH error at the same line -- and only the `[RANON]` prefix
# separates them. Keep the reading as the screen TAIL, never a `[...]` span.
# ✅ d.instop / d.dirtrap WERE DEFERRED and priced at +7 B against a 0 B wall;
# D-LOCARG carved -29 B out of `loc_next` and spent 7 of it on `derive_directf`
# (basic/program.asm), so this gate is 24 rows / 24 SCORED and its DEFERRED dict
# is EMPTY. They failed in OPPOSITE directions, which is what said a constant
# would not do -- knife K-LA3 falsifies the constant live.
#   make onerr0-characterize ONLY=r.reexec SIDES=zb      # scope rows / sides
onerr0-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_onerr0.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

onerr0-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_onerr0.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-LOCARG: LOCATE's three arguments are CHECKED COERCIONS -----------------
# (docs/spec-basic-locarg.md, measured in docs/locarg-msx1-characterization.md)
# The denominator for the -29 B `loc_next` carve D-EVALCHK declined at
# docs/spec-basic-evalchk.md §6.6 with four rows and no denominator.
# 🔴 THE OTHER HALF OF THAT DENOMINATOR ALREADY EXISTED: `missing-acceptance`
# (batteries locate/locerr/locrow/xchk, 214 recorded rows) covers every axis
# §6.6 listed as missing -- row/column, omitted arguments, the CON_LASTROW and
# LINLEN clamps, the CSRLIN/POS read-back. It is this gate's GREEN control set
# and is deliberately NOT duplicated here; run BOTH after touching LOCATE.
# 🎯 The subject is RANK: `70000+0*(1/0)` both faults (11) and overflows (6),
# and `70000+0*SQR(-1)` faults with a DIFFERENT code (5) and overflows the same
# way -- two codes, one shape, which is what makes it a rule about rank rather
# than about division. `256+0*(1/0)` is the negative control: a fault that does
# NOT overflow was already reported correctly and must stay so.
# 🎯 EVERY t.* row reads the CURSOR as well as ERR, because "the abort left the
# cursor alone" is exactly what `loc_next`'s parked-frame apparatus is for, and
# an error code alone is blind to it. The u.* battery is the apparatus test
# proper: untrapped, whole screen tail, so a SECOND message is visible.
# 💰 t.tmfp is DEFERRED: `LOCATE STR$(1/0),3` leaves a numeric AND a type fault
# pending, references report the numeric one, zerobas the type one -- before and
# after the carve alike. The order is `check_expr_errors`', shared with four
# other callers, and it does not move until each has a row of its own.
#   make locarg-characterize ONLY=t.c.ovdiv SIDES=zb     # scope rows / sides
locarg-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_locarg.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

locarg-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_locarg.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-TMFP: of two pending faults, the one that happened FIRST is reported ---
# (docs/spec-basic-tmfp.md, docs/tmfp-msx1-characterization.md.)
# A type fault (TMISMATCH) and a numeric fault (FPERR) can BOTH be pending at the
# statement boundary. Which one the reference reports is decided by nothing but
# WHICH HAPPENED FIRST -- because the reference raises EAGERLY, so the first
# fault aborts on the spot and the second never occurs:
#   WIDTH (A$<5)+0*(1/0)    type first     -> ERR 13
#   WIDTH 0*(1/0)+(A$<5)    numeric first  -> ERR 11
#   WIDTH 0*SQR(-1)+(A$<5)  numeric first  -> ERR  5
# 🎯 THE SQR PAIR IS WHAT MAKES IT ORDER AND NOT RANK: the winning code changes
# with the OPERAND, not the operator. D-EVALCHK §5.1 froze TMISMATCH-first on the
# first row and D-LOCARG measured the second; no STATIC test order satisfies
# both, which is why the filed `check_expr_errors` reorder is declined here.
# 🎯 The order is recorded where it is KNOWN -- type_mismatch_set is TMISMATCH's
# only writer and exec_stmt clears both flags together, so a non-zero FPERR at
# arming time means the numeric fault came first. One site, +5 B, and it moves
# all fourteen readers including the two hand-rolled copies of the ordering
# (check_expr_errors_popbc, ex_let_arr) that a check_expr_errors fix cannot
# reach, and the four readers that test TMISMATCH and never test FPERR.
# 💰 r.hex is DEFERRED: `Q2$=HEX$(0*(1/0)+(Q$<5))` was wrong before (13) and is
# wrong differently now (2). It EXPOSED two pre-existing defects TMISMATCH was
# masking -- the cursor does not reach `)`, and str_arg_empty then overwrites the
# pending FPERR with the deferred syntax error. +6 B for half of it, which is the
# low region's entire remaining budget; its own slice. See TODO.md.
#   make tmfp-characterize ONLY=o.w.fp SIDES=zb          # scope rows / sides
tmfp-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_tmfp.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

tmfp-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_tmfp.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-PENDERR: first-error-wins as a property of the WRITE -------------------
# (docs/spec-basic-penderr.md.) D-TMFP kept the type fault safe from twenty bare
# `ld (FPERR),a` clobbers by giving it a CELL of its own that every reader tested
# first. This slice collapses the two cells into one pending-error CODE and pays
# for that by routing every writer through `penderr_set` (basic/str-engine.asm),
# a set-if-empty store that is byte-for-byte the size of the bare one it
# replaces. -48 B (low 6 -> 14, page 1 22 -> 62).
#
# What this gate holds that `tmfp-acceptance` cannot: NUMERIC-vs-NUMERIC order
# (the same rule, generalised past the type/numeric pair), the two SUB-ROM
# tenants that raise into the cell through the resident ABI, the three readers
# widened from "is a TYPE fault pending" to "is anything pending", and the
# `r.hex` family that D-TMFP deferred. 61 rows x 3 sides, ~9 min.
penderr-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_penderr.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-STMTPEND: a fault that already happened outranks the rest of the -------
# statement (docs/spec-basic-stmtpend.md). D-PENDERR made every WRITER into the
# pending-error cell set-if-empty, so the FIRST fault is the one recorded. It did
# not make anything read the cell that was not already reading it -- and TWO
# places drop the recorded code on the floor:
#   exec_stmt   clears the cell unconditionally at the top of every statement,
#               so a fault raised by a driver that never calls
#               check_expr_errors is FORGOTTEN. `SCREEN 0*(1/0)` and
#               `DEFUSR=0*(1/0)` print nothing at all here and
#               `Division by zero` on both references.
#   stmt_error  raises ERR 2 over a live code, so a statement whose own
#               delimiter check fails reports `Syntax error` instead of the
#               fault that already happened.
# 🎯 The slice that found it was chasing D-TMFP's "defect 1", the token cursor
# stranded on the RHS operand after a string compare -- which is one ROUTE into
# both holes and not the rule. The cursor is measured (by freezing the machine
# and reading IX, docs/stmtpend-msx1-characterization.md §3) and left alone.
# 🔴 THE b.* PAIR (D-COLDROW, 2026-08-21) IS THE ONLY THING IN THE TREE THAT
# BOOTS AND RUNS A PROGRAM WITHOUT TYPING `CLS` FIRST. Every other row in every
# battery resets through `CLS`, `CLS` is a statement, and a statement runs
# exec_stmt -- which READS the pending-error cell. So the cold-boot
# `ld (FPERR),a` in basic/interp.asm was covered by nothing at all, despite
# being loudly observable (knife K-VT1: `Unprintable error in 10`).
# `b.cold` resets with `NEW` only; `b.warm` is the same program off the normal
# reset and is a POSITIVE CONTROL.
# ⚠️ $(DISK_TEST_DSK) IS A REAL DEPENDENCY AND WAS MISSING UNTIL D-COLDROW: the
# cf3300 and zb sides both run `diska=True`, so EVERY row here copies that image
# per case. Absence is LOUD in this probe (`shutil.copy` raises) -- measured, not
# assumed, 2026-08-21 -- but a target that only builds its fixture by luck is a
# fixture that is not built.
# 60 rows x 3 sides (58 before D-COLDROW), ~15 min.
stmtpend-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_stmtpend.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

stmtpend-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_stmtpend.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-SCRERR: SCREEN's mode is a CHECKED BYTE, checked BEFORE it is applied --
# (docs/spec-basic-screenerr.md.) D-STMTPEND filed two ex_screen divergences and
# could close neither, because SCREEN's ERROR surface had never been measured --
# `make missing-acceptance` and the graphics gates cover the MODES, not the
# REJECTS. This is that denominator, and it found four more:
#   the mode was `call eval` + two hand-rolled range rejects that `jp
#   stmt_error`, so `SCREEN -1` / `SCREEN 256` / `SCREEN (1<5)` answered Syntax
#   error for a DOMAIN fault, and `SCREEN 70000` answered nothing at all --
#   eval's silent flt_to_int16 zeroed DE, so an out-of-int16 mode SET SCREEN 0
#   where both references answer Overflow;
#   the range tests passed BEFORE CHGMOD but the pending-error read happened
#   after it, so `SCREEN 0*(1/0)` applied the mode and then reported;
#   an argument list that ENDS where a value was required is Missing operand
#   (ERR 24) on both references at all four of ex_screen's such slots, and was
#   a silent no-op here;
#   the sprite size has its own 0..3 domain (`SCREEN 1,99` -> ERR 5) where an
#   `and $03` silently accepted it, and every trailing argument is a checked
#   byte (`SCREEN 1,,300` -> ERR 5, `SCREEN 1,,70000` -> ERR 6).
# 🎯 THE SCREEN IS THE INSTRUMENT HERE, so trapped rows read `[ ERR , SCRMOD ]`
# -- the code AND the mode the statement left behind, captured in the handler
# over a `SCREEN 1` seed. Scraping the screen for a row whose subject IS the
# screen mode is how `u.scr.dz` came to be deferred rather than scored.
# 59 rows x 3 sides, ~17 min.
screenerr-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_screenerr.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

screenerr-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_screenerr.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-LINERR: WHERE in a graphics statement the wrong-mode refusal happens ---
# (docs/spec-basic-lineerr.md.) D-STMTPEND filed `c.line.tm` as "LINE raises its
# OWN Illegal function call eagerly from inside its coordinate parse".
# 🔴 THAT DIAGNOSIS IS WRONG AND READING THE SITE REFUTES IT: there is no ERR 5
# anywhere in parse_coord. The refusal was `ex_line_gfx`'s own opening `cp 2`,
# three instructions in, and the filed row runs in the boot default SCREEN 0 --
# so zerobas answered ERR 5 to a statement whose coordinates it never looked at.
# The rule the 142 rows here measure is an ORDERING one, and it is not LINE's:
#   a graphics statement moves the WORK AREA to the point its MANDATORY
#   arguments resolve to, and refuses a wrong SCREEN mode IMMEDIATELY AFTER
#   THAT -- after every fault the mandatory arguments can raise, and BEFORE the
#   first OPTIONAL argument is looked at.
# 🔴 IT IS ONE RULE AT FIVE VERBS, and a NEGATIVE CONTROL is what said so:
# `n.pset0` was written as "the same question at a verb this slice claims
# nothing about" and diverged identically, so it became the v.* class and the
# fix became one shared leaf (gfx_point_gate) across PSET/PRESET/LINE/CIRCLE/
# PAINT rather than one edit at LINE. Two corollaries fell out, each refuting a
# shipped doc claim: a LINE/PSET colour is a 0..15 RANGE CHECK (`PSET(20,21),16`
# -> ERR 5 on both references), not spec-basic-graphics-g2.md §11.9's silent
# nibble mask; and PAINT's work-area write is NOT deferred past every field, as
# spec-basic-graphics-g5.md §6 had it.
# 🎯 THE WORK AREA IS THE INSTRUMENT, so trapped rows read `[ ERR , X , Y ]`
# over a `PSET(7,4)` seed -- the code AND how far the statement got: (7,4) = it
# moved nothing, (11,12) = the first endpoint was staged and it then died,
# (20,21) = it ran to completion. Every row changes the SCREEN mode, so a screen
# scrape would be blind to its own subject. The w.* rows read GXPOS/GYPOS
# instead of GRPACX/GRPACY and earned their place: after the first fix `m.s0.tm`
# was green while its GXPOS twin `w.s0.tm` was still red on the identical
# statement, because LINE's p1 staging wrote only the last-referenced point.
# 🎯 D-PAINTSEED (2026-08-11) closed the residual D-LINERR filed against this
# same gate: the p.* class (14 rows + 2 GXPOS twins) asks where PAINT's
# OFF-SCREEN-SEED ERR 5 stands relative to the work-area write, since it and the
# wrong-mode ERR 5 are the same code. The references write the work area FIRST
# -- `PAINT(300,100)` leaves GRPAC on the raw unclipped (300,100) before raising
# -- so the seed test moved BELOW `gfx_point_gate`. Net zero bytes; 13 of the 16
# new rows were red before it.
# 🎯 D-GIRDOM then measured the SAME LEAF at its two SILENT callers, which is
# where D-PAINTSEED's own residual pointed: the domain (0..255 x 0..191, edge
# (255,191) accepted) agrees at PSET/PRESET and POINT too -- but two rows nobody
# had ever read did not. `ev_f_point` marshalled POINT's target to the tenant
# through GXPOS/GYPOS, a BASIC-VISIBLE cell, so `V=POINT(20,21)` MOVED half the
# work area where both references move neither half. 🔴 `v.point0` could never
# have caught it: that row reads GRPAC, which POINT does not touch on any side.
# POINT now marshals through its own GFX_PTX/GFX_PTY; net zero bytes on BOTH
# sides of the slot boundary (rows g.* / w.pt.*, knives K-GD1..K-GD3).
# ⚠️ `c.32767`/`c.m32768` need a WIDER WINDOW, not a bug report: zerobas
# rasterises the true int16 span and masks per pixel (spec-basic-graphics-g3.md
# §3.4/§4.4) where the references clip first, so a 32767-pixel span really is
# walked. At step=12 it answers exactly what both references answer.
# 🎯 D-DRAWERR (2026-08-11) then closed D-LINERR's LAST residual, and the answer
# is a NEGATIVE one: `DRAW` refuses the mode BEFORE evaluating its string
# expression, so the five-verb rule does NOT extend to it and `ex_draw`'s
# opening `cp 2` was right all along. `DRAW 5` is ERR 5 in SCREEN 0 and ERR 13
# in SCREEN 2 on both references (d.tm0 / d.tm2). 🔴 The row DRAW had been
# excluded on could never have said so: `v.draw0` uses a string LITERAL, whose
# evaluation raises nothing, so it reads ERR 5 whichever side of `str_eval` the
# gate is on -- and the WORK-AREA half of the rule is vacuous at a verb whose
# mandatory argument is a string. 🔴 THE SWEEP FOUND TWO DEFECTS THE RESIDUAL
# WAS NOT ABOUT, both caught by rows written as CONTROLS: `ex_draw` had no
# `skip_spaces`, so `DRAW A$` was Type mismatch and DRAW took a string LITERAL
# and nothing else (n.drawvar); and the tenant ignored whitespace only BETWEEN
# commands, so `DRAW"R 10"` and every STR$ -- which emits a leading blank --
# refused (d.spc2 / d.sp.num). +3 B page 1, -3 B sub p0.
# ⚠️ d.lit2/d.def32k were DEFERRED here at D-DRAWERR and are UNDEFERRED and
# GREEN since D-DSCALE (2026-08-11, spec-basic-lineerr.md §12): DRAW's scale
# state has THREE values, not two -- never-set, explicit S4, explicit Sn -- and
# GFX_DSCALE now boots at the sentinel 0, which gdo_s can never write because it
# maps S0 to 4. 🔴 THAT SWEEP FOUND A SECOND DEFECT, in the arithmetic the
# residual called correct, and a row written as a CONTROL found it: the 16-bit
# product $8000 is +32768 on both references and was -32768 in gdrw_scale, so
# the sign boundary is $8001. Pinned at five (n,S) pairs reaching that product
# plus the $7FFC/$8004 neighbours. 🔴 And d.def8k, written as "the smallest
# count that separates the two states", lands on the ONE count where they
# COINCIDE -- the minimum is 8193.
# 210 rows x 3 sides. MEASURED 358 s (2026-08-11, D-DSCALE). The lineage,
# stated because the FIRST of these figures was carried forward unmeasured when
# the row set grew: 108 rows / 168 s at D-LINERR, 124 / 205 at D-PAINTSEED,
# 142 / 236 at D-GIRDOM, 189 / 309 at D-DRAWERR, 210 / 358 here -- real host
# wall time for three unthrottled boots, not emulated MSX time, and not
# reproducible to the second on a loaded machine.
# ⚠️ This comment previously read "~35 min", a figure NOBODY EVER MEASURED: it
# is the wall time of the WHOLE 52-target corpus (2014 s), inherited from an
# earlier session's estimate and misattributed to this one gate. An estimate
# copied forward is indistinguishable from a reading once it is in the tree --
# the same fault as a prediction copied into the result column.
lineerr-characterize: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lineerr.py \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-DEFFN: the last missing MSX1 reserved word ---------------------------
# 🔴 RED BY DESIGN UNTIL THE VERB SHIPS. `deffn-acceptance` gates the EIGHT
# POSITIVE CONTROLS (rows with no DEF FN in them) and the address CLAIMS, and
# reports the 69 subject rows as a recorded baseline -- so it is runnable in CI
# today and says something true. `deffn-strict` is the same run with the subject
# rows required to match: that is the target that flips when DEF FN lands.
# `SIDES=vg8020,cf3300` re-measures the reference column instead of trusting the
# banked one (docs/deffn-design-2026-08-22.md).
deffn-acceptance: repack-machine
	python3 probes/basic/basic_probe_deffn.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# 🔬 MUTATION-TEST THE GATE. DEF FN is missing, so 67 of 69 rows are red no
# matter what the instrument does and a real run cannot show it would detect
# anything. This plants face tables instead -- a correct implementation, eight
# subtly wrong ones, a blank, a broken control -- and needs no emulator.
deffn-selftest:
	python3 probes/basic/basic_probe_deffn.py --selftest

# probe-sides-selftest: the machine facts must keep matching the arms that use them.
# ONE fact -- the VG-8020 has no disk drive -- produced three separate probe
# failures (compare against it, score it, mount to it), so it now lives in one
# module and the module is gated.
probe-sides-selftest:
	python3 probes/lib/probe_sides.py

deffn-strict: repack-machine
	python3 probes/basic/basic_probe_deffn.py --gate --strict \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- D-DEFFNKNIFE: EVERY BUILD SWITCH, FLIPPED ------------------------------
# 🔴 NOTHING IN THIS TREE EVER RAN WITH A SWITCH OFF, SO THE SWITCHES DECAYED.
# D-DUPSPAN2's `loc_missing equ g8_missing` -- an always-assembled alias to a
# symbol that exists only under `IF G8_RESIDENT` -- had made `G8_RESIDENT equ 0`
# unbuildable from the day that carve landed, and the only thing that ever
# noticed was a SCAFFOLD, mid-slice, where a broken switch is indistinguishable
# from a broken edit (docs/spec-basic-deffnland.md §3.3). This assembles the
# main image with each switch off in turn and asks ONLY that it BUILDS -- not
# that it fits, not that it is correct: a disabled feature's stub moves the
# walls, and gating a wall here would fail for reasons that are not the switch.
# It writes into build/switchcheck/ and never touches the shipping artefacts.
switch-build-check:
	python3 tools/check_switch_builds.py

lineerr-acceptance: repack-machine $(DISK_TEST_DSK)
	python3 probes/basic/basic_probe_lineerr.py --gate \
	        $(if $(ONLY),--only $(ONLY),) $(if $(SIDES),--sides $(SIDES),)

# --- DELIVERY-RACE trigger gate (docs/spec-probe-latch.md §5) -----------------
# Forces the batched-injection race onto its own trigger -- a CPU breakpoint on
# the ONE instruction boundary inside C-BIOS `chget` where a backwards GETPNT
# write is invisible to the machine -- and scores both injectors there.
#   row A  the frozen pre-D-LATCH injector -> must still MANGLE (the control)
#   row B  omsx_repl.key_proc              -> must DELIVER (the fix)
#   row C  key_proc on the three neighbouring, never-fatal boundaries
# Row A is why this cannot pass vacuously: once the race is fixed, the two
# delivery oracles have no live subject left, and cross-oracle disagreement --
# D-ECHO's only positive control -- goes silent forever. Nine boots, ~40 s.
# SUBJECT-ONLY (the reference is not driven, see the module docstring). Exits
# NON-ZERO if it cannot identify the trigger.
# 🔴 `repack-machine` IS A PREREQUISITE, NOT A SENTENCE. This line used to read
# "Needs `make repack-machine`" in prose with an EMPTY prerequisite list -- so a
# hand-rolled battery running it straight after `rm -rf build` got the preflight
# refusal ("a probe booted against this machine would report the absence of the
# ROM as the absence of the FEATURE") and `make` exited 2. Every other
# emulator-driving target self-heals through its own prerequisite; this was the
# only one where the rule lived in a comment. `run_gates.py` builds
# repack-machine in its WARM set, so this adds no work to the battery and
# cannot rebuild mid-run.
latch-check: repack-machine
	python3 probes/lib/latch_check.py

# --- ONE type-ahead injector in the tree (docs/spec-probe-lastinj.md §3.4) ----
# The DENOMINATOR behind latch-check, not a duplicate of it. `latch-check` proves
# the SHIPPED injector is race-free; this proves nothing else in the tree ships a
# copy of the one that is not. SIX probe files had composed their own pre-D-LATCH
# body -- write at KEYBUF, reset GETPNT -- and fixing `omsx_repl.key_proc()` did
# nothing for any of them. D-ECHO filed the class as a coverage limit, D-LATCH
# promoted it to a correctness limit, and both times it was closed by hand from a
# list nobody generated. This is the generator.
#
# TWO rules. (a) COMPOSES: a `.py` under probes/, tools/, tests/ whose STRING
# LITERALS emit `debug write memory` AND which names a type-ahead cursor. AST,
# not grep -- this tree explains the mechanism in prose constantly, and prose is
# not a subject. (b) HANDLES (D-INJSINK, docs/spec-probe-injsink.md): it names a
# FROZEN-BODY symbol defined in another module. `import latch_check; return
# latch_check.OLD_KEY` shipped the whole pre-D-LATCH injector past rule (a) with
# no literal of its own, and this gate reported ALL PASS over it. Rule (b)'s
# registry is GENERATED and PINNED: an empty registry is CANNOT JUDGE.
# Four structural exemptions, each stating a CLASS -- SHIPS / HOLDS / HANDLES --
# and a HANDLES claim is machine-checked (no write literal of its own). Fails
# CLOSED.
#
# 🔴 IT SCORES ITSELF FIRST, and that is the whole design. After the last copy
# was re-pointed this walk has ZERO offenders, so a gutted classifier would
# certify a clean tree exactly the way fixing the D-LATCH race silenced the only
# live subject the delivery oracles had. Two frozen bodies are classified on
# every run -- the pre-D-LATCH injector (must be COMPOSES) and a probe that pokes
# RAM without touching the cursors (must be CLEAN) -- so "flag nothing" and "flag
# everything" both REFUSE TO JUDGE instead of reporting a tally. Emulator-free.
# `make injector-check LIST=1` prints every file and its verdict.
injector-check:
	python3 tools/check_probe_injectors.py $(if $(LIST),--list,)

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
# + per-file attestation + decoded-listing sweep (gating) and disk
# section-citation presence (advisory).
# Cheap (0.8 s), read-only, no emulator, no reference ROMs. It does NOT replace
# the human paper trail (the "is each probe black-box?" judgement); see
# docs/clean-room-audit.md. `make audit-citations TARGET="disk"` scopes it.
#
# ⚠️ WHERE IT RUNS, AND WHY THAT IS WIRED RATHER THAN WRITTEN DOWN. This comment
# used to say "run it on demand / in CI", and D-CITEJUDGE (2026-08-06) measured
# both clauses false: ci.yml did not run it, and "on demand" left the gate RED for
# 268 of its first 761 commits -- including one unbroken 144-commit stretch --
# with every green return coming from a human happening to run it. A cadence
# written in a comment is a habit, and a habit is not a control. It is now a step
# of `basic-reloc` above (the target every slice runs, beside check_dead_code.py)
# and a step of .github/workflows/ci.yml. Spec: docs/spec-audit-citations-gate.md.
#
# ⚠️ CHECK 5 IS REPO-WIDE AND IGNORES $(TARGET). D-DOCJUDGE (2026-08-06) measured
# that the forbidden-VOCABULARY scan is structurally blind to decoded-instruction
# listings -- 0 recall on every breach in the project's record -- and that the
# class lives in shipped asm comments as much as in prose. So the listing sweep
# runs over every first-party text file on every invocation, scoped or not.
# Allowlist: tools/citations-listing-allow.txt (digest-anchored; entries must KEEP
# matching, so a stale entry and a blind sweep are both exit 2).
# Spec: docs/spec-audit-citations-docs.md.
audit-citations:
	python3 tools/audit_citations.py $(TARGET)

# A committed doc may not cite a `scratchpad/` path the repo does not contain --
# `scratchpad/` is tracked on purpose (knives, probes, characterisations), so a
# citation that dead-ends means that spec's evidence cannot be re-run by anybody.
# Same family as audit_citations.py check 4 (a citation dead-ending in the
# private workbench); where it dead-ends only changes the remedy, which is why
# the report splits GONE / IGNORED / UNTRACKED.
# ⚠️ LIKE audit-citations, IT RUNS AS A STEP OF `basic-reloc`, NOT ON DEMAND: a
# cadence written in a comment is a habit, and a habit is not a control
# (D-CITEJUDGE left audit-citations RED for 268 of its first 761 commits that
# way). This target is the standalone alias. <1 s, read-only, no emulator.
# Spec: docs/spec-citation-paths-gate.md.
citation-check:
	python3 tools/check_citation_paths.py

# A `TODO.md:NNN` citation rots the moment TODO.md is edited, and the 2026-08-26
# archive split moved 8829 lines at once. Every citation now carries the block's
# CONTENT-DERIVED id beside the line, so the line is for a human's click and the
# id is what this check trusts; `--fix` repairs a drifted line from the id and
# `--annotate` attaches an id to a citation that lacks one. Also catches a
# markdown link whose two halves disagree -- the exact defect the split's first
# repointing pass introduced.
# ⚠️ DELIBERATELY *NOT* A STEP OF `basic-reloc`, unlike citation-check: that
# target is a prerequisite of 112 others, and a stale line number in a doc does
# not gate ROM correctness. One unit of `make gates` is the right weight.
# <1 s, read-only, no emulator.
# Spec: docs/spec-todo-archive-split.md.
todo-citation-check:
	python3 tools/check_todo_citations.py

# tiers: Joost's priority-tier table, compactly, whenever he asks (D-TIERS,
# 2026-09-10). Reads the 🎚️ tag on every open TODO item and the keyword
# denominator in basic/kwtable.inc plus the keywords filed as missing.
# `ARGS=--keywords` for the per-keyword view, `ARGS=--all` to include
# APPARATUS/BUDGET/STANDING/OTHER, `ARGS=--markdown` for the same table as a
# status page (the go-public form, Joost 2026-09-10). The per-keyword
# SCORED column is step (c) of that item and does not exist yet -- the tool
# says so in its footer rather than letting a blank read as verified.
tiers:
	python3 tools/tier_table.py $(ARGS)

# The same table as a FILE -- docs/tier-status.md, the page to open (or publish).
# Generated; regenerate after any TODO.md edit, never hand-edit.
# D-DEPS: the DEPS list above, proved rather than trusted -- every basic/ file
# main.asm includes must be a prerequisite, or an edit to it rebuilds nothing.
deps-check:
	@python3 -c "import re,sys;\
inc=set(re.findall(r'include\s+\"(basic/[^\"]+)\"', open('basic/main.asm').read()));\
mk=open('Makefile').read();\
dep=set(re.findall(r'(basic/[A-Za-z0-9_.-]+)', mk[mk.index('DEPS  :='):mk.index('DEPS  :=')+4000]));\
miss=sorted(inc-dep-{'basic/main.asm'});\
print('deps-check: %d include(s) in basic/main.asm, %d listed' % (len(inc), len(inc)-len(miss)));\
print('\n'.join('  MISSING FROM DEPS: '+m for m in miss)) if miss else print('  every included source is a prerequisite');\
sys.exit(1 if miss else 0)"

tiers-md:
# 🔴 WRITE TO A TEMP AND MOVE ON SUCCESS. `> docs/tier-status.md` truncates the
# target BEFORE the generator runs, so a non-zero exit leaves an EMPTY file and
# the failure is discovered later, as missing content rather than as an error.
# Not hypothetical: `tier_table.py` REFUSES while the knife pin is stale (which
# is correct of it, and happens on every ROM change), and that refusal emptied
# this file twice -- once to 2 lines, once to 0 -- each time needing a
# `git checkout` to notice and undo. The temp file is in the same directory so
# the move is atomic on the same filesystem.
	python3 tools/tier_table.py --keywords --markdown > docs/.tier-status.md.tmp \
	  && mv docs/.tier-status.md.tmp docs/tier-status.md \
	  || (rm -f docs/.tier-status.md.tmp; \
	      echo "tiers-md: generator FAILED -- docs/tier-status.md left UNCHANGED"; \
	      exit 1)

# D-TIERDOC (Joost, 2026-09-14: "maybe generate the updated tier markdown after
# each iteration before you run the suite?"). docs/tier-status.md is GENERATED and
# NOTHING NOTICED WHEN IT DRIFTED FROM ITS GENERATOR -- 128 green gates said
# nothing while its own header advertised a regenerate command that writes to
# stdout and therefore writes nothing at all. Same class as a fix that falsifies
# the paragraph above the code it adds: no gate reads prose.
# 🔴 IT PROVES THE DOC MATCHES THE GENERATOR, NOT THAT THE PIN IS CURRENT. The
# evidence columns come from build/kwsweep-verdicts.json, which only a kwsweep run
# refreshes; this check would pass on a doc generated from a month-old pin. Making
# the pin current is the WORKFLOW step -- `make kwsweep && make tiers-md` before
# staging -- and that is deliberately not a gate, because a gate that ran kwsweep
# would cost 120 s on every battery to re-derive what the battery already writes.
# ⚠️ IT IS IN `run_gates.POSTCHECKS` AND MUST STAY THERE — it runs SERIALLY AFTER
# THE POOL. The first version put it in MUTATORS (before the pool), to keep it
# from reading the pin while the pool's `kwsweep` rewrote it. It went red every
# run, and its own refusal named why: `run_gates.main()` OPENS WITH
# `rm -rf {OUT} build`, so the pin does not exist at all until the pool's kwsweep
# writes it. There is no "before the pool" to read it in.
# 🎯 After the pool is also the STRONGER invariant: the doc is compared against the
# pin THIS battery just measured, not whatever was on disk when it started.
tiers-md-check:
	@python3 tools/tier_table.py --keywords --markdown > build/tier-status.check.md
	@if diff -u docs/tier-status.md build/tier-status.check.md; then \
	  echo "tiers-md-check: docs/tier-status.md matches its generator"; \
	else \
	  echo "🔴 tiers-md-check: docs/tier-status.md DIFFERS from its generator -- run \`make tiers-md\` (and \`make kwsweep kwtime\` first if the evidence columns are stale)"; \
	  exit 1; \
	fi

# D-KWCOVER: which of the 159 keywords does the collected battery actually TYPE?
# The capture rides on a normal battery run -- `omsx_repl.run_cases` appends every
# typed line, tagged with its suite -- and the report refuses without one, because
# three scans of the probe sources each returned a plausible wrong answer first.
# 🔴 gates-FULL, not gates (D-KWCOVERFLOOR 2026-09-13): a normal battery SKIPS its
# emulator tier when the ROMs and probe sources are byte-identical to the last
# green run, and the capture only exists while those 88 targets execute. Riding a
# skipped battery collected 754 lines from 3 suites and the report printed a
# plausible "6 UNEXERCISED" table from it.
kwcover:
	ZEROBAS_KWCOVER=$(PWD)/build/kwcover.tsv $(MAKE) gates-full
	python3 tools/kwcover.py

kwcover-report:
	python3 tools/kwcover.py $(ARGS)

# D-MARKGATE. TODO.md's header states "EVERY OPEN ITEM CARRIES A PICK-UP MARKER"
# and until 2026-09-05 the only thing that could check it lived in scratchpad and
# NOTHING RAN IT -- so it had failed silently on 2026-08-27, on 2026-09-01 and
# again the day this target was written. 🔴 And the readout that caught those saw
# HALF of the last set: its rule was "a line in the block STARTS with a marker
# emoji", which scores prose ("🙋 NEEDS A DECISION -- the mechanism is Joost's
# call") as a marker and had put an unmarked item INSIDE the 🤖 tally the /loop
# picks from. This target requires the bucket NAME, correctly paired with its
# emoji; the 8 arms include two that go green under the old loose rule.
# <1 s, read-only, no emulator. Same weight and the same non-prerequisite
# reasoning as todo-citation-check above.
todo-marker-check:
	python3 tools/check_todo_markers.py --selftest
	python3 tools/check_todo_markers.py

# D-DEFERPIN. A DEFERRED row is measured, printed and never scored -- so its
# stated REASON is the only thing saying why, and a reason is prose that nothing
# checks. 🔴 Five times now a filed FACE rotted while the row went on diverging,
# invisible to filed-row adjudication (which asks known/unfiled/no-longer-
# diverging, and a row that diverges to a DIFFERENT face is `known`). The face
# now lives in the probe as probe_report.Deferral(reason, side=face, ...), red on
# drift in either direction; this static gate is what stops the next deferral
# being added as a bare string again.
# <1 s, read-only, no emulator.
deferral-pin-check:
	python3 tools/check_deferral_pins.py

# D-PINGATE. `tools/filed-row-known.txt` -- the filed-row adjudication set -- had
# NO GATE, and the entry that owns it said so: "the rule is not carried by
# anything that runs: closing an item does not touch tools/filed-row-known.txt,
# and only --check-orphans notices, and only when someone runs it." It recorded
# that failing three times, once leaving `reqcomma_probe` pinned as outstanding
# correctness debt for a day after its rows had stopped diverging.
# 🎯 The CHECK is not new -- it is filed_row_sweep.check_orphans(), which found
# all three. What was missing was a caller in the battery, and this is it. The
# gate IMPORTS the sweep rather than reimplementing it, so there is one
# definition of "the corpus" and not two free to drift.
# ⚠️ It reads files only; it cannot tell a pin whose rows STOPPED diverging from
# one whose rows still diverge -- that is the sweep's own arm and costs a full
# serial run with the refcache off.
# <1 s, read-only, no emulator.
filed-pin-check:
	python3 tools/check_filed_pins.py

# D-DISKMOUNT. Booting a DISK machine without `diska=` makes
# `OPEN"TS.TXT"FOR OUTPUT AS #1` answer ERR 59 -- which is exactly what a
# channel-ceiling violation looks like, so THE APPARATUS FAULT READS AS A
# LANGUAGE RULE and the probe reports a BASIC finding that does not exist.
# 🎯 The library half was already built (`probe_sides.diska()` /
# `require_disk()`); what was missing was the DENOMINATOR. Measured 2026-09-10:
# of 558 scratch probes, 509 type no drive verb, 46 type one AND mount, 3 are
# excused with a reason, and **0 are unmounted**. The class is empty; this keeps
# it that way for the next probe written at 3am.
# ⚠️ It is a TEXTUAL shortlist and says so on every run: it parses with `ast` so
# docstring prose cannot trip it, and follows one level of imports so a probe
# that mounts through `basic_probe_fldwidth` is not a false hit -- both of which
# were false positives it actually produced before they were fixed.
# <1 s, read-only, no emulator.
disk-mount-check:
	python3 tools/check_disk_mount.py --selftest
	python3 tools/check_disk_mount.py

# D-ALPHAGATE. A probe classifies error text against a literal alphabet, and
# anything absent used to fall through to `<NO OUTPUT>` -- which routes the row to
# "without a reference", a sentence about the MACHINE for a fault in the PROBE.
# `Missing operand` was missing from three separate alphabets and cost real
# readings each time. 🎯 This does NOT demand a complete alphabet (a probe names
# only the faces its rows produce, and the REFERENCES print messages zerobas has
# no string for): it demands the property that makes an omission LOUD -- an
# UNREADABLE arm carrying the text. Spelling drift against the ROM's own tables
# is reported ADVISORY, because two probes case-fold ON PURPOSE (D-MSGEXACT).
# The alphabet is DERIVED from sub/errmsg.asm + the escape-encoded main strings
# by probes/lib/errmsg_alphabet.py, whose own known-answer arms run from here.
# <1 s, read-only, no emulator.
error-alphabet-check:
	python3 tools/check_error_alphabet.py

# Three items filed "and nothing checks it" and each proposed its own cheap
# checker. They are ONE property, not three subjects: a shared helper exists
# BECAUSE the obvious hand-written version was measured wrong, so writing the
# obvious version again re-introduces a defect that has a number attached.
#   PUBLISH  openmsx_paths.publish()      412/1200 concurrent reads torn
#   ROOT     dirname(dirname(__file__))   the tree had voted 190 to 25
#   READER   the echo fence               separated on 4/4 cases
# Every rule states its own denominator; exceptions are pinned WITH a reason in
# tools/chokepoint-allow.txt and may shrink, never grow (a stale pin is RED).
# Like todo-citation-check and unlike citation-check, NOT a `basic-reloc` step:
# none of this gates ROM correctness, and 112 targets depend on that path.
# <1 s, read-only, no emulator. Spec: docs/spec-chokepoint-gate.md.
chokepoint-check:
	python3 tools/check_chokepoints.py

# The boot banner is the one thing no other gate can see: every probe program in
# this tree opens with CLS, which wipes the startup header, so `show_title` could
# stop printing entirely and all 41 gates would stay green. D-MISSOP funded a 5 B
# fix by PROMOTING basic/title.asm out of page 1 -- the one thing that could
# plausibly break was the one thing nothing read. Runs no CLS and asserts the
# header is above the prompt, with the program's own marker as the control that
# separates "header gone" (RED) from "never booted" (rc 2).
# Knife: scratchpad/banner_knife.py. One boot, ~15 s.
banner-acceptance: repack-machine
	python3 probes/basic/basic_probe_banner.py --gate

# clean removes the gitignored build artifacts only. The tracked patch
# deliverables are left in place (use `make patches` to regenerate them).
clean:
	rm -rf $(BUILD)

.PHONY: all disk sub patches tape-patches machines machines-oracle install tiers \
        test-dsk unit-test coverage probe bdos-acceptance diskbasic-acceptance \
        bdos-cbios-selfcheck audit-citations basic-reloc deadcode repack-main repack-boot \
        repack-machine diskbasic-acceptance-repack string-acceptance time-acceptance \
        battery-membership-check fixture-integrity-check diskmap ram-claim-check \
        ram-map-check ram-map-doc \
        rigstick rigstick-selftest rigstick-probe \
        asciidigit-acceptance \
        build-assert-check \
        interval-trap-acceptance \
        stackpool-acceptance trapdepth-acceptance trapsvc-acceptance ctlcross-acceptance ctllim-acceptance \
        ramfree-acceptance txtceil-acceptance \
        input-acceptance error-acceptance error-trap-acceptance stop-trap-acceptance strig-trap-acceptance key-trap-acceptance sprite-trap-acceptance intarg-acceptance abort-acceptance direct-ctrl-acceptance sound-acceptance play-acceptance play-trace-acceptance beep-acceptance float-acceptance math-acceptance subrom-acceptance \
        subrom-inttest subrom-abi-check subrom-closure-check \
        graphics-floor-acceptance graphics-floor-teeth graphics-acceptance kwsweep kwtime kwram sysvarsweep fat-error-acceptance \
        logicops-characterize cursor-characterize cursor-acceptance \
        binfre-characterize binfre-acceptance \
        missing-characterize missing-acceptance \
        str-domain-characterize str-domain-acceptance \
        clearpool-characterize clearpool-acceptance \
        width-characterize width-acceptance \
        arrdim-characterize arrdim-acceptance \
        linemax-characterize linemax-acceptance chancost-characterize \
        lnblank-characterize lnblank-acceptance lnblank-echo lnblank-say-acceptance \
        editverb-acceptance lptverb-characterize lptverb-acceptance \
        dskmsg-characterize dskmsg-acceptance \
        runtail-characterize runtail-acceptance runline-acceptance \
        castail-characterize castail-acceptance cas-ascii-acceptance wprotect-acceptance \
        cassave-characterize cassave-acceptance \
        readvar-characterize readvar-acceptance \
        inputary-characterize inputary-acceptance \
        arylv-characterize arylv-acceptance lvsites-characterize \
        lvfix-characterize lvfix-acceptance \
        fldary-characterize fldary-acceptance \
        lrvar-characterize lrvar-acceptance \
        forvar-characterize forvar-acceptance \
        nxlist-characterize nxlist-acceptance \
        nxary-characterize nxary-acceptance \
        tgtspc-characterize tgtspc-acceptance \
        namspc-characterize namspc-acceptance \
        fldwidth-characterize fldwidth-acceptance \
        onerr0-characterize onerr0-acceptance \
        locarg-characterize locarg-acceptance \
        tmfp-characterize tmfp-acceptance \
        penderr-acceptance \
        stmtpend-characterize stmtpend-acceptance \
        screenerr-characterize screenerr-acceptance \
        lineerr-characterize lineerr-acceptance \
        lof-characterize lof-acceptance \
        badfnum-characterize badfnum-acceptance \
        deffn-acceptance deffn-selftest probe-sides-selftest deffn-strict switch-build-check \
        msgexact-gate msgexact-relock preflight-check latch-check injector-check \
        omsx-diag-teeth temp-root-check shared-body-check probe-reach-check citation-check todo-citation-check todo-marker-check deferral-pin-check error-alphabet-check filed-pin-check disk-mount-check \
        chokepoint-check banner-acceptance wall-literal-check hook-equate-check \
        patch-freshness-check tiers-md tiers-md-check gates clean

# --- gates: the acceptance-gate battery, run in PARALLEL ----------------------
# Build the shared artifacts once, then fan the per-gate probes out across worker
# slots (docs/spec-probe-emutime-watchdog.md). ~2.5-2.8x faster than running them
# serially, and reliable because the harness is parallel-safe (emulated-time
# watchdog + temp-path isolation). `make gates` picks the worker count from the
# CPU; tools/run_gates.py --serial falls back to one-at-a-time. NOT a substitute
# for a targeted `make <gate>` while iterating -- it is the full-suite sweep.
gates:
	python3 tools/run_gates.py $(GATE_ARGS)

# --- D-GATESKIP (docs/spec-gateskip.md): the two tiers ----------------------
# Measured 2026-08-28 over a full battery: the STATIC tier is 65 serial-seconds
# and the EMULATOR tier is 2870. Nearly the whole cost of a battery is the
# emulator half -- and both of that day's real reds came out of the static half.
#
# `gates-fast` is the iteration loop: ~20s, run it after every edit instead of
# guessing. It NEVER records a green baseline, and its report says
# [STATIC TIER ONLY] so it can never be mistaken for a full battery.
#
# `gates` skips the emulator tier only when it can PROVE it cannot move: the four
# ROM images AND every probe/test/tool source AND the Makefile byte-identical to
# a full battery that was itself fully green. That is a proof, not a judgement
# about what a diff can affect -- judgement is what failed 3x on 2026-08-26.
# `gates-full` forces the emulator tier regardless.
gates-fast:
	python3 tools/run_gates.py --static $(GATE_ARGS)

gates-full:
	python3 tools/run_gates.py --full $(GATE_ARGS)

# --- D-GATESCOPE (Joost, 2026-09-24): scoped batteries, FULL only on risk ------
# `gates-plan` prints which tier THIS change needs and why; `gates-scoped` runs
# it. STATIC for docs; SCOPED (static + the emulator suites a changed file or a
# changed handler's keyword reaches, + a canary set) for a probe/tool or a
# handler-local ROM change; FULL for shared code, an unknown blast radius, every
# 5th commit since the last full green, and every hand-off (`HANDOFF=1`).
# Every commit message states the tier that ran (`GATE TIER RAN:` line).
gates-plan:
	python3 tools/pick_gates.py $(if $(HANDOFF),--handoff,)

gates-scoped:
	python3 tools/pick_gates.py --run $(if $(HANDOFF),--handoff,)
