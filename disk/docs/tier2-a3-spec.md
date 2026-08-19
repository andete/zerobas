<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 A-3 spec — relocate int_h to always-mapped high RAM

**Status:** spec, awaiting sign-off (no asm yet).
**Genre:** Interface-B boot fix. **This one IS the boot fix for the COMMAND.COM storm.**
Supersedes the A-2b *placement* (A-2b's handler logic is reused; only its location moves).

## Why (located root cause, §8.77 + 2026-06-26 stock comparison)

The COMMAND.COM-handoff storm is now located and confirmed with the reverse/probe
harness, and the fix is named by direct ours-vs-stock measurement:

| | `$0038` vector | int handler lives in | installed by |
|---|---|---|---|
| **Ours**  | `C3 51 42` = `jp $4251` | **page-1 disk ROM** (`int_h $4251 → int_h_body $792B`) | our disk ROM `$41C7`/`lay_page0_env`, t≈3.14s |
| **Stock** | `C3 AE DD` = `jp $DDAE` | **high RAM $DDAE** (stock's always-mapped int handler; full register-save, chains KEYINT) | stock disk ROM `$5ABC`, t≈9.65s |

At the COMMAND.COM handoff, `wa_seg_ram` (M5.6) correctly swaps page 1 from the disk
ROM (slot3-sub1) to RAM (slot3-sub0) so the TPA owns `$4000-$7FFF`. COMMAND.COM then
runs (`$0100→$0500` self-relocate). On the **first interrupt**, `$0038 → jp $4251`, but
`$4251` is now unmapped RAM (`$FF` = `rst 38h`) → `$0038→$4251→$FF→$0038…` recursion,
each `rst` marching SP down: the storm. **`int_h` (and `int_h_body`, and the
`pg0_mainrom_*` helpers) all live in page 1, which the TPA legitimately reclaims — so
the entire handler chain vanishes exactly when COMMAND.COM needs it.** A-2b's private
stack could never help: `$792B` is in page 1 too.

Stock avoids this by putting the handler in **high RAM (page 3), which is always
mapped**, and pointing `$0038` there. On ours `$DDAE` reads `FF FF FF…` — the
always-mapped handler **does not exist; we must build it** (it is the disk ROM's job,
not MSXDOS.SYS's — `$DDAE` is `$FF` on ours through the whole boot).

This is exactly the Interface-B class from the architecture audit (§8.69): the disk
ROM↔main-BIOS interrupt path must be BIOS-agnostic AND survive DOS paging. The handler
*logic* (A-2 KEYINT chain + A-2b private stack) is correct and unchanged; only its
**memory placement** is wrong.

## Goal / non-goal

- **Goal:** the maskable-interrupt handler survives the page-1→RAM swap, so the first
  post-handoff interrupt is serviced (KEYINT chain) instead of storming. Success =
  the harness shows ours' `$0038` chain landing on an always-mapped handler and **no
  `paging-p1`/`sp-rompage` storm** at the handoff.
- **Non-goal / honest scope:** reaching `A>`. This removes *this* blocker (the storm).
  COMMAND.COM may surface a further blocker downstream; that is the next milestone,
  found with the same harness. (We have been here before — fix the proximate cause,
  re-probe for the next.)

## The invariant to restore

> The maskable-interrupt entry **and** its body **and** every routine it calls before
> it can restore paging must reside in memory that stays mapped across the DOS page-1
> swap — i.e. page 3 high RAM (or page 0, but page 0 is the TPA). Pointing `$0038` at a
> page-1 (`$4000-$7FFF`) address is the bug.

## Design

Two approaches; **(B) is recommended** (faithful to stock, no per-interrupt page-1
juggling). (A) is a lower-churn fallback.

### (B) Self-contained high-RAM handler  — RECOMMENDED

1. **A new high-RAM handler `int_h_hiram`** — the A-2/A-2b body, made self-contained so
   it touches only page 0 (for the KEYINT chain) and never page 1:
   - save regs + switch to the A-2b private interrupt stack (`INT_STK_TOP`, page 3);
   - `pg0_mainrom_in` → `call $0038` (main-ROM KEYINT: VDP ack + H.KEYI/H.TIMI/kb/JIFFY,
     BIOS-agnostic via EXPTBL[0]) → `di` → `pg0_mainrom_out`;
   - restore regs + caller SP, `ei`, `ret`.
   The `pg0_mainrom_in/out` helpers must be **verified self-contained** (they page the
   main ROM into page 0 via EXPTBL[0] + slot writes; no page-1 calls). If self-contained
   they relocate as one contiguous block with the body; if not, inline their bodies.

2. **Install it in high RAM during init.** Add a ROM template (free tail) and `LDIR` it
   to `INT_H_HIRAM` during disk-ROM init — the same mechanism as `wa_seg_*`/the work-area
   builders (`build_wa_table`). Install **before** `lay_page0_env` points `$0038` at it,
   and at an address above MSXDOS.SYS's self-relocation landing so the DOS load cannot
   clobber it (see address choice below).

3. **Repoint `$0038`.** Change the page-0 vector table entry
   `pageenv.asm:56  dw $0038, int_h`  →  `dw $0038, INT_H_HIRAM`. `lay_page0_env` then
   writes `jp INT_H_HIRAM` at `$0038`. The page-1 `int_h`/`int_h_body` become dead and
   are removed (recovering their bytes / restoring net-zero).

### (A) Minimal high-RAM page-in trampoline — FALLBACK

Keep `int_h_body` in page 1; add a small always-mapped stub at `INT_H_HIRAM`:
save the live page-1 subslot, map the disk ROM into page 1 (reuse `wa_seg_rom` logic),
`call int_h_body`, restore COMMAND.COM's page-1 subslot, `ei`, `ret`. Requires
`int_h_body` to end in a bare `ret` (move its `ei` to the stub). Smaller (~30 B) but
does a subslot read-modify-write inside every interrupt and must restore the TPA mapping
exactly — more failure surface than (B).

## Concrete changes (approach B)

- **`disk/runtime.asm`** — add `int_h_hiram_template:` (self-contained handler) in the
  free tail (which has `ds $8000-$,$00` slack); confirm/relocate `pg0_mainrom_in/out`
  into the template block. Remove the now-dead page-1 `int_h_body`.
- **`disk/pageenv.asm`** — `int_h: jp int_h_body` trampoline removed; `p0_env_tab` entry
  `dw $0038, int_h` → `dw $0038, INT_H_HIRAM`.
- **`disk/init.asm`** — add the `LDIR` install of the template to `INT_H_HIRAM`, wired
  into the existing init sequence (near `build_wa_table`); add the `INT_H_HIRAM` equate
  and `INT_H_LEN`. Update the stale comment at `init.asm:463` ("page 1 stays mapped").
- **`disk/equates.inc`/`init.asm`** — `INT_H_HIRAM equ $DDAE` (proposed; see below).

## High-RAM address choice

Propose **`INT_H_HIRAM = $DDAE`** — exactly stock's address (maximally faithful;
known-good on the oracle), and `$DD..` is above MSXDOS.SYS's ~`$D300-$DC7F` landing and
above COMMAND.COM's stack (SP≈`$DBFA` at the handoff). **Pending a harness validation**
that the chosen cell stays untouched through the whole boot on ours:
`OmsxRun.read_block($DDAE, 16, settle=…)` at several settles + a `write_watch($DDAE)`
must show no foreign writer. If `$DDAE` is ever touched on ours, pick a free cell in the
`$DD00-$DFFF` window the same way. (Our own address, our own bytes — clean-room: we
mirror stock's *structure*, never its handler bytes.)

## Net-zero / size accounting

Approach B nets roughly even: the page-1 `int_h` trampoline (3 B + `ds` pad) and
`int_h_body` (~30 B) are **removed** from page 1; the template (~same size) is **added**
to the free tail and consumes free-tail `ds $8000-$,$00` slack; the high-RAM image is
built at runtime (no ROM page cost beyond the template + a short LDIR install). Show the
exact ledger delta at implementation; keep canonical addresses fixed (net-zero veneer
discipline) for any displaced page-1 code.

## Validation plan (all via the harness)

1. **Build + unit/regression:** `make unit-test` 18/18; DSKIO/FILES == CF-3300; BLOAD ok.
2. **Vector relocated:** `OmsxRun.irq_chain()` on ours must show `$0038 → jp $DDAE` (not
   `$4251`) and the handler bytes present at `$DDAE`.
3. **Storm gone:** `disk_derail_locate.py --preset paging-p1` and `--preset sp-rompage`
   must NOT find the `$0038⇄$4251` storm at the handoff (expect `STUCK`/no-failure there,
   or a *new, further-downstream* state — which is progress, not regression).
4. **Interrupt serviced:** forward-trace the first post-handoff `z80.acceptIRQ` — it must
   enter `$DDAE`, run the KEYINT chain, and `ret` cleanly (SP restored), like stock.
5. **Address safe:** the `$DDAE` read_block/write_watch check above.

## Risks / open items

- **`pg0_mainrom_*` self-containment** (B): must confirm they make no page-1 calls before
  relocating; if they do, inline. — verify first.
- **Install timing vs MSXDOS.SYS:** the template must be installed and `$0038` repointed
  before the first post-handoff interrupt, and the image must not be overwritten by the
  DOS load. `$DD..` above the DOS landing addresses both; validate (step 5).
- **A vs B:** if (B)'s relocation proves fiddly, (A) is the smaller fallback at the cost
  of per-interrupt page-1 juggling.
- **Downstream blocker:** the storm may be masking a later issue; success criterion is
  "storm gone + interrupt serviced", not "A>".

## Clean-room note

Faithful-relocation fork (a): we mirror stock's **structure** (handler in always-mapped
high RAM, `$0038` pointed there) and reuse our OWN handler logic (A-2/A-2b) at our OWN
address with our OWN bytes. Stock's `$DDAE` bytes are an oracle data point (where/that,
not how); `MSXDOS.SYS`/`COMMAND.COM` stay pure oracles.
