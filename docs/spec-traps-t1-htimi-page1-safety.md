# spec — H.TIMI page-1-safety guard (interrupt-traps T1 unblock)

Status: **DRAFT for sign-off** (2026-07-24). Prereq for wiring `basic/traps.asm` (slice T1).
Root cause + repro: [traps-t1-wiring-blocker.md](traps-t1-wiring-blocker.md).

## 1. Problem (proven)

`play_install` (playsvc.asm) points the **H.TIMI** hook ($FD9F) at `jp play_service`, and
`play_service` is **main-ROM PAGE-1 resident**. That placement (audio §4a) rests on a stated
invariant — *"subrom_call runs every page-1 tenant under DI … no page-1 tenant opts into EI,
so a VBLANK never fires while main page 1 is switched out"* (playsvc.asm:15-23).

**The invariant is false.** The **FATPRIM** page-1 tenant (`SUBROM_IDX_FATPRIM=12`) runs
`dskio_calslt` → `call CALSLT` to the disk ROM's **DSKIO**, with no DI guard; **DSKIO enables
interrupts**. So a VBLANK *can* fire while main page-1 is paged out to the sub-ROM. When it
does, the BIOS ISR runs H.TIMI → jumps to `play_service`'s address in the **paged-out page-1**
→ executes sub-ROM bytes → wild jump / garbage boot. Because `play_service`'s address moves
with any page-1 growth, the failure is a **bounded band** (survivable vs fatal sub-ROM landing);
the T1 carve happened to shift it onto fatal bytes. This is a **pre-existing latent flaw in the
audio seam**, independent of traps — traps just exposed it.

First hit at boot: `autoexec_run` → `fat_mount`/`fat_find` → FATPRIM, before the REPL.

## 2. Goal

Make the H.TIMI → `play_service` path **safe regardless of the page-1 slot mapping**, so a VBLANK
landing mid page-1-tenant is harmless. Must:

- G1. Never jump into `play_service` while main-ROM page-1 is paged out.
- G2. Stay **register-transparent** (H.TIMI contract) and **DI-only** (never EI).
- G3. Cost ≤ a few bytes; not reintroduce the page-1 pressure the arc just relieved.
- G4. Also cover the future traps seam (`htimi_service` replaces `play_service` at the SAME
      H.TIMI hook), i.e. fix the *class*, not just PLAY.
- G5. No behavioural change to PLAY in the common case (main page-1 mapped): byte-identical drain.

Non-goal: making FATPRIM/DSKIO run DI (would need a disk-ROM change, only covers DSKIO, and
risks real-hardware disk timing/faithfulness). We fix the seam, not every possible EI leak.

## 3. Design — an H.TIMI guard stub

Insert a tiny guard between H.TIMI and `play_service`: `H.TIMI = jp htimi_guard`; the guard reads
the **page-1 primary-slot field** and only falls through to `play_service` when main-ROM page-1 is
actually mapped; otherwise it returns immediately (PLAY simply drains that one frame on the next
VBLANK — an inaudible ≤1-frame skip during the rare tenant window).

```
htimi_guard:            ; entered from the BIOS ISR's `call H_TIMI`, DI, all regs live
        push    af
        push    hl
        in      a,(PSLTREG)     ; port $A8 current slot config
        rrca
        rrca
        and     %00000011       ; A = page-1 primary field (bits 3-2 -> bits 1-0)
        ld      hl,INT_MAIN_PRIM ; primary of the main-ROM (slot-0) — recorded at boot
        cp      (hl)
        pop     hl
        jr      nz,hg_skip      ; page-1 != main-ROM -> a page-1 tenant is running -> skip
        pop     af
        jp      play_service    ; safe: main page-1 mapped; its own `ret` returns to the ISR
hg_skip:
        pop     af
        ret                     ; skip PLAY this frame; return to the ISR
```

~14 bytes. Preserves AF/HL (the only regs it touches before the decision); `play_service` already
preserves the rest. For the traps seam, `htimi_guard` falls through to `htimi_service` instead —
same guard, one label change (§6).

### 3.1 Slot detection — reuse `INT_MAIN_PRIM`

`INT_MAIN_PRIM` ($F14A, set by `sub_int_install`) is the main/BIOS slot primary (=0). The merged
main ROM is a single 32 KB slot-0 ROM spanning pages 0 **and** 1, so its page-1 primary == its
page-0 primary == `INT_MAIN_PRIM`. During a page-1 tenant the field reads the sub-ROM primary
(=3, slot 3-x) ≠ `INT_MAIN_PRIM`. Comparing the primary field is sufficient on this machine
(main=slot0 vs sub/disk=slot3). *Sign-off check:* confirm no supported config puts the sub-ROM in
main's own primary but a different subslot (would need a subslot compare too — not the case for the
slot-0-main / slot-3-2-sub layout; documented limitation, same class as init_ext_roms' own).

### 3.2 Where the guard lives — two options (DECISION)

The guard must be mapped **at H.TIMI-execution time in every context**:

- **Option A — PAGE-0 low region (recommended if it fits).** During a page-1 tenant, page-0 is
  untouched (still main ROM), so a page-0-resident guard is mapped. During a page-0 tenant, the
  `$0038` sub-ROM trampoline (`SUB_INT_RAM`) has already mapped main/BIOS **back into page-0**
  before its `call $0038`, so a page-0-resident guard is *also* mapped when H.TIMI runs there.
  ⇒ page-0 residence is always-mapped at H.TIMI time. **No RAM copy, no new RAM cell.** Cost: ~14 B
  of the page-0 low region (playsvc header notes ~19 B free — **must be re-measured**, §7).
- **Option B — RAM-resident (copied by `play_install`, mirrors `sub_int_template`).** Always mapped
  unconditionally. Needs a ~14 B always-mapped RAM home + a boot-time copy. The `SUB_INT_RAM`
  reservation ($F10A..$F149) is nearly full (stub 47 B, `RND_SEED` at $F142); a fresh free-RAM
  window must be found + write-watchpoint-proven boot-safe (candidates from the earlier audit:
  the $E3E8..$E560 gap, or above `FCH_CTX` $EA00).

Recommendation: **Option A** if ≥14 B is genuinely free in page-0; it is simpler and spends no
RAM. Fall back to Option B if page-0 is too tight.

## 4. What does NOT change

- `play_service` itself: byte-identical, stays page-1 resident, still DI-only.
- The `$0038` sub-ROM trampoline (`sub_int_template`): unrelated (page-0-tenant path).
- ZTRAP RAM home ($E1D1): fine — never was the problem (superseded theory).
- The audio §4a page-1 placement rationale: **amend** the header to record that the DI invariant is
  guaranteed by this guard, not by an (untrue) "no page-1 tenant EIs" claim.

## 5. Test plan (Definition of Done)

1. **The clean repro sweep goes GREEN across the whole band.** Repack-only `defs N,0` at `ier_done`
   (inside `IF ROM_BASE < $4000`), oracle `make diskbasic-acceptance-repack ONLY=FILES`. Pre-fix:
   N∈[4,135] FAIL. Post-fix: **all N (0…150) PASS**. This is the load-bearing gate — a green build
   at N=0 alone is NOT sufficient (the whole arc's recurring lesson).
2. `make diskbasic-acceptance-repack` (full 34) and `make string-acceptance` GREEN at N=0 **and** at
   a mid-band N (e.g. 74) — proving the guard, not luck, fixes it.
3. `make unit-test` GREEN (host Z80 layer).
4. **PLAY still works:** an audio trace case (existing `play-trace-acceptance`) confirms byte-identical
   drain — the guard never skips when main page-1 is mapped.
5. Boot the merged machine (no input): clean banner + `zb>` prompt, no garbage, at the mid-band N.

## 6. Follow-on — wiring traps (the actual T1 goal), after this lands

With the seam safe, `play_install` points H.TIMI at `htimi_guard` → (main mapped) → `htimi_service`
→ `event_poll` → `play_service`. `trap_init` (ZTRAP zero-fill at $E1D1) goes in `ier_done` +
`run_prog` as originally planned. Re-run the §5 gates with `traps.asm` wired.

## 7. Open decisions for sign-off

- **D1. Guard home:** Option A (page-0, ~14 B) vs Option B (RAM copy). Needs a page-0 free-space
  re-measurement. *Recommend A if it fits.*
- **D2. Slot compare depth:** primary-only (sufficient for slot-0-main / slot-3-2-sub) vs
  primary+subslot (fully general). *Recommend primary-only + documented limitation.*
- **D3. Skip vs swap on a tenant window:** guard **skips** PLAY that frame (recommended, trivial,
  inaudible) vs the guard **maps main page-1 in, calls play_service, restores** (faithful every
  frame but heavier + must restore the tenant's exact page-1 mapping). *Recommend skip.*

## 8. Clean-room / provenance

Own-design guard. Inputs are published contracts already used in-tree: port $A8 primary-slot field
(MSX2 TH slot architecture), H.TIMI $FD9F 5-byte hook (BIOS work-area appendix), the `INT_MAIN_PRIM`
cell (our own `sub_int_install`). No reference-ROM disassembly. Same clean-room basis as
`sub_int_template`.
