<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M18 spec — the missing `$50C4` CURDRV-time kernel entry (current-drive read)

**Status: CHARACTERISED (2026-07-03, Opus session), root cause pinned clean-room-safe;
falsify-first build validated (see §5). Same well-established un-wired-`$50xx`-entry +
un-built-work-area-cell class as M13 (`$50E0`) / M15 (`res_print_tmpl`) / M17 (`$50D5`).**
Resume board: [tier2-STATE.md](tier2-STATE.md). Fix-shape template:
[tier2-m17-spec.md](tier2-m17-spec.md) (the immediately-preceding, identical-shape fix).

## 1. Goal
Drive the boot prompt to print the **correct drive letter** `A>` (not `C>`). Concretely:
after the date-prompt Enter, at BDOS call n=25 (the drive-letter CONOUT) ours must emit
`A=$41`='A' matching stock, not `$43`='C'; the current-drive value CURDRV computes must be
**0** (drive A:) on ours as it is on stock. Tier-1 green, `disk.rom`==16384 B.

## 2. Root cause (pinned, all clean-room-safe — no stock/kernel code decoded)
With M17 landed, ours reaches **full 27-call BDOS parity with stock through BUFIN**; the
first (and only) divergence is at **n=25**: stock CONOUTs `A=$41`='A', ours `A=$43`='C'.
The letter is computed by the kernel as `'A' + current_drive` (`HL = $C400 + drive`;
`capture --nth 25`: stock `HL=C400`, ours `HL=C402` — i.e. drive 0 vs 2).

The current-drive value comes from **BDOS CURDRV (func `$19`, n=24)**. During CURDRV the
loaded MSXDOS.SYS kernel **CALLs a page-1 disk-ROM routine at `$50C4`**. On ours that
address is `$00` NOP-padding (our active `$50xx` code ends at the `$50A9` routine's `ret`
@ `$50B7`; `$50B8–$50D4` is our own `$00` fill, up to the M17 `$50D5` veneer), so the CALL
NOP-slides and never does CURDRV's current-drive read — the **exact same class of bug** as
M13's `$50E0`, M15's `res_print_tmpl`, and M17's `$50D5`: another un-wired entry in the
`$50xx` relocated-kernel block.

### 2.1 Evidence (all `disk_probe_diff.py`, test.dsk, keyed `--keys '\r' --keys-at 20`)
- **`callwatch --in-func 0x19` (CURDRV):** during CURDRV, STOCK executes page-1 PCs
  `$50C4` **then** `$50C7` (its real 2-block routine); OURS executes `$50C4` then
  NOP-slides away (only 1 entry, no `$50C7`).
- **`callseq --log 0x50C4`:** both machines hit `$50C4` **exactly once**, and
  **register-identical** at entry (`capture --at 0x50C4 --nth 1`, one-sided each):
  `AF=0044 BC=C419 DE=D3FF HL=D502 SP=DBFE IY=DC5B` on BOTH; only `IX` differs
  (`F459` stock / `F195` ours — the long-standing benign IX delta). Return address on the
  stack `[SP=DBFE] = $D88A` — the same trampoline return as M17's `$50D5`. A genuine CALL
  boundary, not a mid-slide.
- **CAUSAL read pin (`readwatch --machine stock --in-func 0x19`):** during CURDRV, reader
  PC **`$50C4` reads exactly ONE cell — `$F247`, value `$00`** — and nothing else in the
  swept `$F200–F2BF` / `$F340–F34B` windows. So `$50C4` ≈ `ld a,($F247); ret`, returning
  the current-drive index (`$00` = drive A:). Passes the §8.65/M15 causality guard (the
  routine demonstrably READS the specific cell on its live path).
- **`HL` corroboration:** at n=25 stock `HL=$C400` (=`$C400 + 0`), ours `HL=$C402`
  (=`$C400 + 2`) — the +2 is exactly our bogus drive value 2, and the printed char
  `$41 + 2 = $43`='C'.

### 2.2 The second half of the gap — `$F247` is unbuilt on ours
Stock's `$F247` = `$00`; **ours' `$F247` = `$FF` (unbuilt)** (`capture --nth 24
--mem 0xF244:0x08`: stock `F1 04 00 00 01 01 04 00`, ours all `$FF`). `$F247` is BELOW our
`RES_STUBS` fill (`$F24E–$F2B7`) and below `DRVCNT` (`$F347`), so nothing in our init writes
it. The MSX-DOS-1 current drive at boot is **A: = `$00`** (the published boot state — the
system logs in drive A:), so the clean-room value is `$00`.

**⇒ Even a correct `$50C4` veneer returns the WRONG value unless `$F247`=$00 is also built.
The fix has two parts: (a) the veneer, (b) the `$F247` build.** (`$F247` happens to be `$FF`
= a large index; the kernel's `'A'+drive` masks it to `'A'+2` in practice, but the correct
model is a definite `$00`.)

## 3. Fix (approach IDENTICAL to M17 — a `$50xx` veneer + a work-area cell)
**(a) `$50C4` veneer.** `$50B8–$50D4` is free `$00` padding (active code ends `$50B7`; the
M17 `$50D5` veneer starts `$50D5`). Place a 3-byte `jp curdrv_body` at `$50C4`, consuming
existing pad `$50C4–$50C6`; the remaining `$50C7–$50D4` stays `$00` up to the `ds $50D5 - $`
M17 fill — **net-zero, no address shift**. Body in the free tail (next to
`seldsk_drv_body`):

```
; curdrv_body — the $50C4 kernel CURDRV-time entry: return the current-drive index.
; Black-box contract (M18 §2.1): reads $F247 (=current drive) into A, preserves BC/DE/HL/IX/IY.
;   in: -    ; out: A = ($F247) ; BC/DE/HL/IX/IY preserved
curdrv_body:
                ld      a, (CURDRV_CELL)   ; CURDRV_CELL = $F247 = current-drive index ($00)
                ret
```

**(b) build `$F247` = `$00`.** In `build_drvtbl` (init.asm), alongside the M17 `DRVCNT`
write, add `xor a / ld (CURDRV_CELL),a` (define `CURDRV_CELL equ $F247`). ~4 bytes. This is
the cramped pre-`$41FD` region — **verify object-file size under 3-pass `--sym` after the
change** (§7.3 lesson: a 2-arg `pasmo` hides an overflow by silently emitting an empty
object). If it doesn't fit, the `xor a` can be shared with a nearby zero if measured.

**Clean-room:** `$50C4` is a de-facto page-1 kernel ABI entry (same class as
`$50D5`/`$50E0`/`$5454`); the body derives from the black-box read contract
(`return [$F247]`) + our own code. `$F247`=$00 derives from the published MSX-DOS boot
state (current drive = A:), NOT from any stock byte. No kernel/ROM code was decoded (only
entry/exit registers, a DATA-cell read-watch of `$F247`, and our own RAM).

## 4. Open sub-question (does NOT block the falsify-first build)
Like M17's `$50D5`, `$50C4` may set flags via an ALU op (stock's return F not yet pinned).
The falsify-first build (§5) tests the simplest hypothesis (return A only, flags don't
matter). If ours reaches a correct visible `A>` / n=25 parity, F is proven irrelevant and
we stop. If it stalls one step later on a flag-dependent branch, re-pin F via a black-box
`capture` and add the matching flag op (still clean-room: our own op).

## 5. Falsify-first build + validation
Same signed-off falsify-first build class as M13/M15/M16/M17. Acceptance:
- `callseq --log 0x0005 --keys '\r' --keys-at 20`: n=25 CONOUT now `A=$41`='A' matching
  stock; full 27-call parity with NO divergence (or divergence pushed strictly later).
- `callseq --log 0x50C4`: ours returns A=$00 and lands back at `$D88A`.
- Tier-1 `make unit-test` 19/19; `disk.rom` == 16384 B; no canonical shift.
- (Regression) M13 `--log 0x009F` 1 idle call; M15 `--log 0x00A2` stream; M17 27-call parity.
- `screen --machine ours --keys '\r' --keys-at 20`: assess the drive letter + OI-3 banner.

## 6. Invariants
- Net-zero: `$50C4` veneer uses existing `$00` pad; body + `$F247` build add to the free
  tail / the existing build routine. `disk.rom` == 16384 B, no address shift.
- BIOS-agnostic + DOS-path only (work-area construction runs on the DOS boot path).
- Clean-room per §3.
