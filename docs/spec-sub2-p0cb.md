<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# zerobas-sub2 page-0 call-back (`p0cb`): moving cold statements out of main

Status: **slices A and B BUILT 2026-10-21** (D-P0CB): `p0cb`, sub2's RST 10h / 18h
and a self-test (`make sub2-acceptance`, both repack machines), then the event-trap
statements moved (main page 1 +255 B). Slice C1 (OPEN / CLOSE / MERGE / MAXFILES,
sub2/filestmt.asm) is DRAFTED 2026-10-21: ~800 B of main page 1, all of it pad in
front of the $6CF3 and $72D4 pins. Slice C2 (SAVE / CSAVE / BSAVE / LOAD / CLOAD /
BLOAD / RUN <name>, sub2/loadsave.asm) is DRAFTED 2026-10-21: ~780 B of main page 1
(pad in front of $6CF3) and 5 B of the low region; the loaders and writers stay in
main (do_tape_prog's real-time TAPIN loop runs whole inside one p0cb). D is not built.

## 1. Why

Main page 1 and the low region are one budget, and it is the binding one: after
D-DISKREST (2026-10-20) page 1 has 36 B free at its tail and 153 B in pin pads, the
low region 6 B + 31 B. Joost, 2026-10-20/21: ROM space first; free MAIN — sub-ROM
bytes are not the budget while the sub ROM exists. zerobas-sub2's page 0 has ~16 KB
free.

A read-only study (2026-10-21, from `build/basic-reloc.sym` and the call graph of
`tools/check_tenant_closure.py`) found that **no statement can move there under
today's rules**. While a page-0 tenant runs, slot-0 page 0 — the BIOS, main's low
region, the `$0038` interrupt entry — is switched out, and only main page 1 stays
mapped. Every statement parser uses `rst $10` (CHRGTR), and `raise_error`, `eval`
and the print path all reach the low region or the BIOS. Of 1278 page-1 labels only
324 (~3 KB of scattered leaves) are "clean". The ROM-1 page-0 tenants are pure
RAM / port leaves for exactly this reason (`sub/deffn.asm`'s header).

So moving a statement needs a way **back** into main with main's page 0 mapped: the
mirror of disk.rom's `calbak`, which a disk-ROM handler already uses to evaluate,
raise and print.

## 2. The mechanism — C-BIOS's own CLPRIM, no new RAM

🏗️ Joost, 2026-10-21: *"Yes, but no new RAM"*. So no private RAM stub: the call
goes through the BIOS's RAM-resident inter-slot primitive at **`$F38C` (CLPRIM)**,
which C-BIOS copies to the work area at boot with RDPRIM / WRPRIM (C-BIOS
`src/slot.asm` `m_clprim`; its own CALSLT jumps to it). Its contract, read from that
source:

```
  in   A  = the new primary-slot register value      (out to port $A8)
       IX = the address to call
       stack: [old $A8 value, as AF] above [the return address]
       AF' = the caller's AF, which the callee receives (one `ex af,af'`)
  does out ($A8),A / ex af,af' / call (IX) / ex af,af' / pop af /
       out ($A8),A / ex af,af' / ret
  out  the callee's AF, HL, DE, BC come back; IX is the callee's
```

`p0cb` (sub2 page 0) wraps it: park the caller's AF in AF', push its own return
address and the current `$A8`, clear the page-0 field (main is slot 0), `jp $F38C`.
HL / DE / BC / A / F cross in BOTH directions; IX is consumed (the target).

⚠️ zerobas never writes `$F380..$F39x` (grep, 2026-10-21); `basic/fat.asm` already
relies on CLPRIM restoring AF. The **probe** of slice A (§5) is what establishes the
contract on the machines; this section is what to expect from it.

## 3. What runs where, and the rules

- **Interrupts.** While the callee runs, page 0 is main's: an interrupt takes main's
  own `$0038`. Back in sub2's page 0, an interrupt takes sub2's `jp SUB_INT_RAM`
  trampoline, which restores the interrupted tenant's live slot (D-SUB2 (a)).
  D-SUB2EI's inttest twin for ROM 2 page 0 lands WITH the first tenant.
- **`rst`.** sub2 page 0's `$0010` and `$0018` become `jp s2_chrgtr` / `jp s2_outdo`:
  each saves IX, `p0cb`s to main's CHRGTR / OUTDO, restores IX. Moved code keeps its
  `rst`s byte for byte. Every other `rst` (`$30` CALLF among them) stays `$FF` and is
  refused in the sub2 build, as `check_tenant_closure.py --page0` refuses it in ROM 1.
  A hook call (`call H_xxxx`) from moved code goes through `p0cb` too.
- **Raise.** A callee that raises never returns: `raise_error` resets SP and runs
  main's error path with main's page 0 already mapped by CLPRIM. The CALSLT frame
  that entered the tenant is abandoned, as a raise from disk.rom's `calbak` abandons
  the hook's; slot 3's secondary page-0 field is left on sub2, harmless because the
  primary register points page 0 at slot 0 and the next ROM-1 CALSLT sets its own.
- **Nesting.** A callee that CALSLTs a ROM-1 tenant (3-2) gets slot 3's secondary
  register restored by C-BIOS's CALSLT on return; CLPRIM then restores the primary.
- **Cost.** One CALSLT round trip per statement (main -> tenant), plus one CLPRIM
  round trip (~100 T) per call-back. Cold statements only; a statement games run per
  frame stays in main unless a stopwatch says otherwise.

## 4. The main side

One shared entry `ex_sub2` (~12 B, once): `ld ix,SUBROM_ENTRY_BASE_P0+3*SUB2_IDX_STMT`
/ `call subrom2_call` / `jp c,subrom_absent_error` / `push de` / `ret` — the tenant
dispatches on the token at `(HL)` and returns DE = the main continuation
(`exec_stmt`, `pop_exec`, `end_line_end`, ...) and HL = the cursor. `stmt_table` rows
are retargeted to `ex_sub2`: 0 B per statement. The generated sub2 ABI include and a
sub2 closure-check mode follow the ROM-1 pattern (`Makefile`, `sub/basic-resident-abi.inc`).

## 5. Slices

- **A — the mechanism, 0 B of main.** `p0cb`, the two `rst` vectors, a sub2 page-0
  SELFTEST tenant (calls a low-region routine, a page-1 routine, CHRGTR through
  `rst $10`, a nested ROM-1 tenant; checks HL / DE / BC / A / F both ways), probed by
  injection on BOTH repack machines like `sub2-acceptance`; D-SUB2EI's ROM-2 inttest
  twin; knives: CLPRIM entered with page 0 NOT switched (must go red), the IX save in
  `s2_chrgtr` removed.
- **B — the trap statements** (`ON KEY / STRIG / INTERVAL / STOP / SPRITE GOSUB`,
  `KEY(n) / STRIG(n) / INTERVAL ON / OFF / STOP`; basic/program.asm from `ex_on_stop`),
  ~300 B past the last pin. `ex_on` itself stays (ON GOTO is hot).
- **C — the file family** (OPEN / CLOSE / MERGE / MAXFILES, SAVE, LOAD), ~1.4-1.6 KB,
  keeping the pin targets and disk.rom's call-back targets in main. **C1** (the first
  four) reuses slice B's entry: their stmt_table rows share ONE byte, `ld c,a` in
  front of `ex_sub2`, and trap_tenant forwards C >= 8 (a token) to file_tenant.
  Their continuations are exec_stmt, clr_wipe, end_line_end -- and disk_error /
  load_error, which PRINT AND RETURN, so they too go back in DE, never through p0cb.
  **C2** (SAVE / CSAVE / BSAVE / LOAD / CLOAD / BLOAD, and RUN's name arm, which
  main's do_run sends with C = RUN_TOKEN) shares the same byte; file_tenant forwards
  to ls_tenant. New continuations: run_prog_top (LOAD ,R / RUN <name>), load_handoff
  (BLOAD: ,R calls the loaded code) and bp_ret (a handler's own `ret` / `ret c`).
  The loaders and writers stay main's and are p0cb targets; sv_tenant and bload_sub
  keep main wrappers because their sub-ROM call carries an INLINE byte.
- **D — SCREEN / COLOR / WIDTH / KEY**, ~450 B. Graphics (~800 B) only after a
  stopwatch on PSET / LINE / PUT SPRITE.

Estimates are the 2026-10-21 study's (label spans, ±10%); each slice re-measures.
