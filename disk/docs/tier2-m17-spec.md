<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M17 spec — the missing `$50D5` SELDSK-time kernel entry (drive-count read)

**Status: CHARACTERISED (2026-07-03, Opus session), root cause pinned clean-room-safe;
falsify-first build validated (see §5). Needs the same quick sign-off M13/M15/M16 got
before the fix is declared final.** Resume board: [tier2-STATE.md](tier2-STATE.md).
Template for the fix shape: [tier2-m15-spec.md](tier2-m15-spec.md) §9, [tier2-conin-spec.md](tier2-conin-spec.md) §3.

## 1. Goal
Drive MSX-DOS past the SELDSK-time stall to a **visible `A>`**. Concretely: after the
date-prompt Enter, ours' BDOS call sequence must continue past `SELDSK` (n=21) to
`CONOUT`(CR/LF)/`CURDRV`/print `A>`/`BUFIN` (stock's n=22–27), and `screen --machine ours
--keys '\r' --keys-at 20 --settle 25` must render `A>`. Tier-1 green, `disk.rom`==16384 B.

## 2. Root cause (pinned, all clean-room-safe — no stock/kernel code decoded)
The loaded MSXDOS.SYS kernel, while processing BDOS `SELDSK` (func `$0E`), **CALLs a
page-1 disk-ROM routine at `$50D5`**. On ours that address is `$00` NOP-padding (our
active code in the `$50xx` block ends at the `$50A9` routine's `ret` @ `$50B7`; the region
`$50B8–$5453` is our own `$00` fill), so the CALL **NOP-slides `$50D5→$5453` into the
`$5454` `jp conout_body` CONOUT veneer** and never does SELDSK's drive-select work — the
exact same class of bug as the M13 CONIN `$50E0` gap and the M15 `res_print_tmpl` stub:
another un-wired entry in the `$50xx` relocated-kernel block.

### 2.1 Evidence (all `disk_probe_diff.py`, test.dsk, keyed `--keys '\r' --keys-at 20`)
- **`callwatch --in-func 0x0E` (new gate generalisation):** during SELDSK, STOCK executes
  only page-1 PCs `$50D5`/`$50D8` (its real 2-block routine); OURS executes `$50D5` then
  jumps into the `$78xx`/`$79xx` CONOUT/inter-slot veneer (the NOP-slide → `conout_body`).
- **`callseq --log 0x50D5`:** both machines hit `$50D5` **exactly once**, **register-
  identical** at entry: `AF=0044 BC=D50E DE=D3FF HL=D349 IX=F459 IY=DC5B SP=DBFE ret=D88A`.
  A genuine CALL boundary (same clean PIN shape as `$50E0`'s PIN A; same trampoline caller
  `$D88A`), NOT a mid-slide — so `$50D5` is a real kernel CALL target.
- **`callseq --log 0xD88A` (the trampoline return):** stock returns to `$D88A` 26× and
  proceeds (CURDRV, `A>`); **ours reaches `$D88A` only 20× — the `$50D5` NOP-slide path
  never cleanly returns to the trampoline**, so the kernel's post-SELDSK sequence never runs.
- **`$50D5`'s black-box contract** (`capture --machine ours/stock`, one-sided): entry
  `AF=0044`, return (at `$D88A` #21) `AF=023B`; **BC/DE/HL/IX/IY all preserved**. Only AF
  changes: **A returns `$02`.**
- **CAUSAL read pin (`readwatch --machine stock --in-func 0x0E --range 0xF344:0x08`, and
  three wider sweeps `$F1C0/$F340/$F380:0x40`):** during SELDSK, reader PC **`$50D5` reads
  exactly ONE cell — `$F347`, value `$02`** — and nothing else anywhere in `$F1C0–$F3BF`.
  So `$50D5` ≈ `ld a,($F347); ret` (plus a flag-setting op — return `F=$3B`; the exact F is
  not yet shown to matter, see §4). This passes the §8.65/M15 causality guard: the routine
  demonstrably READS the specific cell on its live path, not merely "the work area is
  unbuilt."

### 2.2 The second half of the gap — `$F347` is unbuilt on ours
Stock's `$F347` = `$02`; **ours' `$F347` = `$FF` (unbuilt)** (`capture --mem 0xF340:0x30`).
`$F347` is `DRVTBL-1` (our `DRVTBL` = `$F348`), the byte immediately before the disk-driver
table — the **number of logical drives** the interface exposes. Our `build_drvtbl`
(init.asm ~490) writes `DRVTBL+0..+15` but **never `DRVTBL-1`**. The MSX-DOS-1 single-drive
model exposes **2 logical drives (A: and B:) on one physical drive** ([[dual-drive-decision]]),
so the published/clean-room value is `$02`. (Stock's neighbouring `$F345`=07, `$F346`=FF are
NOT read by `$50D5` — irrelevant to this fix.)

**⇒ Even a correct `$50D5` veneer returns the WRONG value (A=$FF) unless `$F347`=$02 is
also built. The fix has two parts: (a) the veneer, (b) the `$F347` build.**

## 3. Fix (approach mirrors M13/M15 — a `$50xx` veneer + a work-area cell)
**(a) `$50D5` veneer.** `$50D5–$50D7` is free `$00` padding (active code ends `$50B7`;
conin veneer starts `$50E0`). Place a 3-byte `jp seldsk_drv_body` at `$50D5` (like the
`$50E0` conin / `$5454` conout veneers), consuming existing pad — **net-zero, no address
shift** (`$50D8–$50DF` stay `$00` up to the `ds $50E0 - $` conin fill). Body in the free
tail:

```
; seldsk_drv_body — the $50D5 kernel SELDSK-time entry: return the logical-drive count.
; Black-box contract (M17 §2.1): reads $F347 (=drive count) into A, preserves BC/DE/HL/IX/IY.
;   in: -    ; out: A = ($F347) ; BC/DE/HL/IX/IY preserved
seldsk_drv_body:
                ld      a, (DRVCNT)     ; DRVCNT = $F347 = logical-drive count ($02)
                ret
```
Install via a fixed `jp` at `$50D5` in kernel.asm (no LDIR needed — it's a 3-byte veneer at
a canonical address, exactly like `conin`/`conout`).

**(b) build `$F347` = `$02`.** In `build_drvtbl` (init.asm), alongside the `DRVTBL+n`
writes, add `ld a,$02 / ld (DRVTBL-1),a` (define `DRVCNT equ $F347`). ~5 bytes. This region
is the pre-`$41FD` cramped area — **verify object-file size under 3-pass `--sym` after the
change** (§7.3 lesson: 2-arg pasmo hides an overflow). If it doesn't fit, move the two
stores just after the existing `DRVTBL+15` sentinel write which is already in this routine
(measure first).

**Clean-room:** `$50D5` is a de-facto page-1 kernel ABI entry (same class as `$50E0`/`$5454`);
the body derives from the black-box read contract (`return [$F347]`) + our own code. `$F347`=$02
derives from the published MSX-DOS single-drive-exposes-2-logical-drives convention, NOT from
any stock byte. No kernel/ROM code was decoded (only entry/exit registers, a DATA-cell read
watch, and our own RAM).

## 4. Open sub-question (does NOT block the falsify-first build)
The return `F=$3B` (flags modified) shows `$50D5` does more than a transparent value
fetch — its routine performs a flag-affecting operation (some ALU step) on the way, not
a pure load-and-return. Whether the kernel branches on that F is **not yet shown**. The falsify-
first build (§5) tests the simplest hypothesis (return A only, flags don't matter); if it
unblocks to `A>`, F is proven irrelevant and we stop there. If it stalls again one step
later on a flag-dependent branch, re-pin F via a black-box `capture` of the kernel's
post-`$50D5` branch input and add the matching flag op (still clean-room: our own op, chosen
to reproduce the observed F, not copied).

## 5. Falsify-first build + validation
Signed-off falsify-first build class (as M13/M15/M16). Acceptance:
- `callseq --at 0x0100 --log 0x0005 --keys '\r' --keys-at 20`: ours continues past n=21
  SELDSK to n=22–27 matching stock (CONOUT/CONOUT/CURDRV/CONOUT/CONOUT/BUFIN).
- `callseq --log 0x50D5`: ours returns A=$02 and lands back at `$D88A` (26 trampoline
  returns, matching stock).
- `screen --machine ours --keys '\r' --keys-at 20 --settle 25`: **visible `A>`**.
- Tier-1 `make unit-test` 19/19; `disk.rom` == 16384 B; no canonical shift.
- (Regression) M13 `--log 0x009F` 1 idle call; M15 `--log 0x00A2` full stream still render.

## 6. Invariants
- Net-zero: `$50D5` veneer uses existing `$00` pad; body + `$F347` build add to the free
  tail / the existing build routine. `disk.rom` == 16384 B, no address shift.
- BIOS-agnostic + DOS-path only (work-area construction runs on the DOS boot path).
- Clean-room per §3.
