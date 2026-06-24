<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 milestone M5.6 — implement the `$F368`/`$F36B` segment-switch hooks

**Status: APPROVED + LANDED (§8.59). Both default decisions (DI-only, read-modify-
write) confirmed by the user. Outcome: the `$D87F` retry loop collapsed; boot
advanced to a new slow-crawl blocker `$D7B0-$DC00` (M5.7). See §8.59 for results.**
Genre: implementation spec (spec-before-code discipline). Evidence: notebook
§8.57 (the blocker is the `$F365` jump table) + §8.58 (per-vector contract).

## 1. Problem (recap)

After the `k_47B2` loader (M5.4) COMMAND.COM is in the TPA, but the relocated
kernel spins ~14 k× in a retry loop at `$D87F-$D8A7` (§8.56). The `$D87F`
differential (§8.57) localised it to the seven-slot work-area jump table at
`$F368-$F37C`: stock fills the slots with distinct resident routines, ours fills
**every** slot with one catch-all `JP wa_stub` (a bare `RET`, `disk.asm:742`). The
write-watch proved the **disk ROM** owns the table (no hiRAM writer), so those
bodies are part of the ROM we reimplement — clean-room from contract, never bytes.

## 2. Contract to satisfy (§8.58, measured on stock `National_CF-3300`)

Only two slots are ever called during the COMMAND.COM-load → `A>` boot:

| slot | calls | role | persistent effect | regs |
|------|------:|------|-------------------|------|
| `$F368` | 81 | **map disk-ROM into page 1** | slot-3 subslot ← `$04` (page 1 = subslot 1) | entry == exit (transparent) |
| `$F36B` | 80 | **map RAM into page 1**      | slot-3 subslot ← `$00` (page 1 = subslot 0) | entry == exit (transparent) |

`$F36E/$F371/$F374` are never called in this phase (`ncalls 0`) and stay
`wa_stub`; `$F377/$F37A` are null (`JP $0000`) on stock too. The "persistent
effect" is two stores: the real secondary-slot register `$FFFF` **and** its RAM
mirror `SLTTBL[3]` = `$FCC8`. All other writes are transient stack traffic.

Machine grounding (`National_CF-3300_ZEROBASDISK.xml`): slot 3 is expanded,
subslot 0 = 64 K RAM, subslot 1 = our disk ROM (`$4000-$BFFF`). On this machine
pages 0/2/3 are subslot 0 throughout DOS, so writing the whole subslot byte
(`$04` / `$00`) reproduces stock without disturbing the other pages. We will
nonetheless **read-modify-write only the page-1 bits** for robustness (see §3).

## 3. Design

Two new clean-room resident routines, installed into always-mapped page-3 high
RAM by `build_resident` (same mechanism as `p1_blit`, §8.35), then wired into the
jump table by `build_wa_table`:

```
; wa_seg_rom  ($F368 body) — page 1 -> slot-3 subslot 1 (disk ROM)
; wa_seg_ram  ($F36B body) — page 1 -> slot-3 subslot 0 (RAM)
; Contract: preserve ALL registers (AF BC DE HL IX IY); only effect = page-1
; subslot of slot 3, mirrored in SLTTBL[3]. Bodies run from page-3 RAM so the
; page-1 flip never unmaps the running code.
wa_seg_rom:     push    af
                ld      a, %00000100        ; page-1 bits = subslot 1
                jr      wa_seg_set
wa_seg_ram:     push    af
                ld      a, %00000000        ; page-1 bits = subslot 0
wa_seg_set:     di
                ld      b, a                ; B = desired page-1 subslot bits ($04/$00)
                ld      a, (SLTTBL3)        ; current slot-3 subslot mirror ($FCC8)
                and     %11110011           ; clear page-1 bits, keep pages 0/2/3
                or      b                   ; merge new page-1 bits
                ld      (SLTTBL3), a        ; update RAM mirror first
                ld      ($FFFF), a          ; ...then the real secondary-slot register
                pop     af                  ; (no EI: faithful — stock leaves IFF as found;
                ret                         ;  callers run with DI here, confirmed by trace)
SLTTBL3         equ     $FCC8
```

Notes / decisions to confirm:

- **DI but no EI.** The contract is register-transparent; the trace shows the
  kernel calls these with interrupts already disabled (the body is in the int-safe
  relocation band). We restore nothing re IFF — matching "leave as found". If
  review prefers a save/restore of IFF, we add `ld a,i / push af` … but that
  perturbs flags, so the minimal DI-only form is preferred unless an interrupt
  reaches here (it does not in the trace).
- **read-modify-write** of only page-1 bits (`and %11110011 / or B`) rather than a
  blind `ld $04`/`$00`, so the routine is correct even if another page's subslot
  is non-zero. Reproduces the observed `$04`/`$00` on this machine.
- Write order **mirror-then-register** ( `$FCC8` then `$FFFF` ): once `$FFFF` is
  live the page-1 map has changed; the body is in page 3 so it survives, and the
  next instruction is `pop af/ret` from page-3 — no page-1 fetch in between.
- `$FFFF` readback is inverted by hardware; we never read it (we keep the mirror
  in `$FCC8`), so inversion is irrelevant.

### Wiring (`build_wa_table`, `disk.asm:607`)

Currently the loop writes `JP wa_stub` into all 7 slots. Change to: keep the
uniform `wa_stub` fill (covers `$F36E/$F371/$F374/$F377/$F37A` — still no-ops /
unused), then **overwrite slots 0 and 1** with the real targets:

```
                ; after the existing 7×(JP wa_stub) fill:
                ld      hl, WA_JMPTAB + 0   ; $F368
                ld      (hl), $C3
                inc hl : ld (hl), low wa_seg_rom  : inc hl : ld (hl), high wa_seg_rom
                ld      hl, WA_JMPTAB + 3   ; $F36B
                ld      (hl), $C3
                inc hl : ld (hl), low wa_seg_ram  : inc hl : ld (hl), high wa_seg_ram
```

(`$F365` stays as-is — stock has a tiny `in a,($A8);ret` there; it is not a
jump-table slot and is never CALLed in the trace, so out of scope for M5.6.)

## 4. Placement / sizing

- `wa_seg_rom`/`wa_seg_ram`/`wa_seg_set`: ~22 bytes, page-1 ROM source (the
  template), relocated into free page-3 RAM next to `p1_blit` (`$E77A` region) by
  an `ldir` in `build_resident`. Pick the next free page-3 slot after the existing
  resident routines; confirm no overlap with `P1_BLIT`, `RES_PRINT`, the DPB, or
  the CALSLT table.
- Net new ROM ≈ template (~22 B) + table-rewire (~18 B) ≈ **~40 B** added in the
  free tail — additive, no address shift (regression-safe like M5.4).

## 5. Risks

1. **IFF handling** — minimal DI-only form assumes callers are already DI (true in
   trace). Mitigation: if re-probe shows a derail, switch to save/restore IFF.
2. **Downstream blockers** — unblocking `$F368/$F36B` may expose the *next* stall
   (e.g. `$F36E` then becomes reachable, or a different kernel poll). Expected and
   fine: incremental milestones. Success here = the `$D87F` retry loop collapses
   and the boot advances past it (new end-PC), not necessarily `A>` yet.
3. **Subslot value assumption** — read-modify-write removes the "other pages are
   0" assumption; verified `$04`/`$00` reproduce stock.

## 6. Validation plan (after asm)

1. `make` the ROM; **regression**: `make unit-test` (expect 18/18), FILES vs
   CF-3300 byte-identical, BLOAD `,R`/plain (additive change → must stay green).
2. Re-run `disk_probe_dosboot_wacontract.py --slot 0xF368` / `0xF36B` on **ours**
   and diff against stock: entry/exit regs transparent, `$FCC8`/`$FFFF` writes
   present with `$04`/`$00`.
3. `disk_probe_dosboot_loop.py` / `disk_probe_dosboot_path.py`: confirm the
   `$D87F-$D8A7` retry loop collapses (top-PC counts drop) and the end-PC advances.
4. Update the ledger (these bodies flip `$F368/$F36B` work from 🟨/⬜ toward ✅)
   and the notebook (§8.59 result).

## 7. Clean-room

Bodies are our own standard expanded-slot switch idiom (public MSX slot-select
spec: `$FFFF` secondary register + `SLTTBL`). `MSXDOS.SYS`/`COMMAND.COM` and the
stock disk ROM's `$DF57/$DF59` bytes are never read or copied — only the
black-box contract (which subslot byte, which two cells) is reproduced.
