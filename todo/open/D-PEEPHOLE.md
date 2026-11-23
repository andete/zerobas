- [ ] 💰 **D-PEEPHOLE: THE CLASSIC Z80 SIZE IDIOMS, COUNTED — SAFE CLASS TAKEN,
      FLAG-CHANGING CLASS STILL OPEN (20 B).** Pattern list from the WikiTI
      "Z80 Optimization" page (Joost, 2026-08-28);
      `scratchpad/peephole_sweep.py --sites` counts each against basic/ + sub/
      (76 files, 20579 instructions). Two entries were ALREADY CLOSED and are
      reported rather than re-counted: ~~`jp`→`jr` (D-JRSLICE/2, banked
      2026-08-24)~~ and `call X`/`ld a,(hl)` (D-RETLN/D-EVSPDUP, gated).
      🔴 **`jp`→`jr` IS NOT CLOSED, MEASURED 2026-09-05.** D-UPSTR ran
      `scratchpad/jr_mapper.py` because it was 1 B short and found **19
      convertible sites, 14 in main page 1** — a class this entry had been
      reporting as banked since 2026-08-24. Code moves, and every insertion since
      (D-CTLPOOL moved a great deal) pulls fresh targets into `jr` range, so this
      is not a one-off sweep but a RENEWABLE seam. D-UPSTR spent 8 of them; **13
      remain in page 1**. The tool's own note is why it is safe to spend blind:
      shrinking only TIGHTENS displacements, and `jr`/`jp` are flag- and
      control-flow-identical, so *"it assembles"* == *"it is correct"*.
      ⚠️ A count from this paragraph rots the same way the last one did — run the
      mapper, do not quote it.
      🎯 **REGION IS WHAT THE BYTES ARE WORTH**: of a 106 B ceiling only **47 B
      is in MAIN** (35 page 1, 12 low, measured 2026-08-28) — the rest is sub,
      which had thousands of bytes free and is not a carve.
      ✅ **SAFE CLASS SHIPPED 2026-08-28: 14 B** — 12 `call X / ret` → `jp X`
      tail calls (each read individually first) + 2 `ld r,n / ld r',n` →
      `ld rr,nn`. Low region read 38 → 44 B, page 1 124 → 132 B on 2026-08-28.
      ✅ **THE FLAG-CHANGING RULES ARE A MEASURED NEGATIVE, 2026-08-28 — the
      ~20 B ceiling is really 1 B, and sweeping it would have shipped SIX
      REGRESSIONS.** Every one of the six main-region `ld a,0` sites is
      LOAD-BEARING: `cload.asm:777`/`:850` are `call cal_refill / ld a,0 /
      jr nc` (xor clears the carry the branch tests), `float.asm:308`/`:351` are
      16-bit NEGATES where the borrow from `sub l`/`sub e` must reach the
      following `sbc` — and `program.asm:555`/`:1994` already said so in a
      comment. Only the `djnz` at `cload.asm:376` converts: **1 B, taken**
      (nothing reads `dec b`'s flags — `ccn_flag` opens `ld a,c / or a`).
      🔴 **AND THE SWEEP WAS REPORTING A DISHONEST 18.** It counted every
      `ld a,0` as a candidate. It now walks forward and rejects the site if any
      instruction CONSUMES a flag before the flags are redefined, treating a
      label / a call / the end of the window as LIVE. It reports **1** tree-wide
      and independently rejects exactly the six rejected by hand.
      🎯 **FOUR OF THE SIX HAD NO COMMENT SAYING WHY** — annotated in place
      (0 B; comments do not assemble), because that is where the next person
      running a peephole sweep will land, not in a spec file.
      ➡️ ~~Also open: `ld a,(v)/inc a/ld (v),a` → `ld hl,v / inc (hl)`, 29 sites,
      58 B ceiling — needs HL free AND A dead at each, unmeasured.~~
      ✅ **MEASURED 2026-09-05 (D-PEEPINC), AND THE MAIN REGION YIELDS EXACTLY
      3 B — WHICH WERE TAKEN.** Main page 1 read **0 → 3 B free** (and sub page 1
      917 → 920). The census's own *"MAIN p1 12 B ceiling"* is 0 in practice:
      all four sites it attributes there — [`basic/screen.asm`](basic/screen.asm:134)
      and [`basic/traps.asm`](basic/traps.asm:272) ×3 — were ALREADY read and
      rejected, each carrying a 🔴 comment saying HL is live (the parse cursor in
      one, the entry byte `ss_write` stores to in the others).
      🔴 **AND THE CENSUS MIS-ATTRIBUTED THE ONE SITE THAT PAID.** A direct scan
      finds **17** sites in the main tree, not 4: twelve are in `.inc` bodies
      included ONLY into sub tenants (not a carve), and one —
      [`basic/sv-tne.inc`](basic/sv-tne.inc:36) — is a SHARED body included into
      `sub/save.asm` **and** `basic/save.asm`, so its bytes are in main page 1
      too. The by-region table saw the sub include and filed it there. **The
      region of an `.inc` is its INCLUDE SITE, and a body can have two** — the
      same shared-`*-body.inc` blindness [[jrslice-slice]] hit from the other
      direction. Recorded in the sweep's own header.
      🔬 **HL IS DEAD THERE, READ RATHER THAN ASSUMED**: `ld (TSV_PTR),hl` two
      instructions up has already stored it and the loop top reloads it. The
      hazard is that the after-form changes **A and Zf on return** where the
      contract documents only CF — all three callers (`basic/save.asm:354`,
      `basic/sv-tsb.inc:37`, `basic/sv-bsvcas.inc:43`) test CF alone and go
      straight into `call TAPOOF`. `unit-test` 59/59, `cassave-acceptance` green,
      battery 114/114.
      ⚠️ The remaining twelve are sub-only and stay unconverted: a sub byte is a
      rounding error against ~1350 B free, and each would still need its own
      HL/A read.
      🔴 **THE SWEEP'S FIRST RUN REPORTED 54 HITS FOR THE PAIR-LOAD RULE AND THE
      TRUE COUNT IS 9**: `a b c d e` are all valid HEX DIGITS, so `is_imm()`
      accepted a bare register name and counted `ld d,a / ld e,b` — a register
      MOVE — as a constant pair.
      🎚️ BUDGET — ROM carve
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended.
      ✂️ **`jp`→`jr` RENEWED AGAIN, 2026-10-10 (loop, after D-READERL / D-DOSMODE40
      brought main page 1 to 8 B):** `scratchpad/jr_mapper.py` found 6 convertible
      sites, all page 1 (`save.asm` sv_tenant; `files.asm` oo_hdr_tail, oo_fail_e,
      oo_fail_syn, oo_fail_bfname ×2) — converted, page 1 **8 → 14 B** (predicted
      +6: hit); a re-run finds 0, so the route is spent until code moves again
      ([`carve_jrmap.out`](scratchpad/carve_jrmap.out) →
      [`carve_jrmap2.out`](scratchpad/carve_jrmap2.out)).
