<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M22b slice 2 — above-the-FDC-hole relocation plan (for sign-off)

**Status: SPEC / SCOPE ONLY — no asm touched. STOP for sign-off** before building
([[spec-before-implementation]]). The slice-2 *logic* is already characterised +
written (spec [tier2-m22b-conout53a7-spec.md](tier2-m22b-conout53a7-spec.md)
§5.3–§5.5/§6; saved impl `scratchpad/m22b-slice2-conout.patch`); this spec is ONLY
about *where the bytes go* so it doesn't crash the DOS boot. Blocker background:
[tier2-lstout-characterisation.md](tier2-lstout-characterisation.md) sibling; FDC
hole [[disk-hardware-target-variants]].

## 1. What slice 2 does (recap — unchanged, already signed off in principle)

In the shared CONOUT bottleneck: expand TAB (`$09`) to 8-column stops
(`do{ emit ' '; col++ }while(col&7)`), maintain the logical column at page-1 cell
`$F237` (printable → `col++`, CR → `col:=0`, LF → unchanged), seeded `$00` in
`dos_handoff`. Exit `A` after a TAB = `$00` (§8.1 RESOLVED — the saved impl already
captured stock `AF=$0054`, `$F237=$08` after a col-1 tab). Full contract + clean-room
provenance: the referenced spec §5. **None of that changes here.**

## 2. Why it can't just grow in place (the blocker)

The WD2793 FDC registers are memory-mapped at **`$7FB8–$7FBF`** inside the ROM page.
The disk ROM is **full right up against the hole**: executable bodies end at `$7FB7`
(`p0_env_tab` start), the only free space is the 47-byte pad `$7FD1–$7FFF` (all
*above* the hole), and `conout_body` lives far below at `$7D5C`. Growing `conout_body`
in place by slice-2's ~40 bytes shoves the `fat_find`/`fdc_*` bodies (`$7F4F–$7FB6`,
executable) UP *through* the hole → an instruction fetched from `$7FB8–$7FBF` during
the FDC-active MSXDOS.SYS load reads register bytes, not opcodes → silent boot crash.
(This is exactly what the FDC-window guard now catches at build time.)

## 3. The relocation — split conout across the hole

Code at `$7FC0+` is entirely above the hole and is reached by an **absolute
`call`/`jp`** from below (the `call` opcode is fetched below the hole; execution then
jumps over the hole — the hole is never fetched as code). So:

- **BELOW the hole (byte-stable preamble + a SHRUNK branch stub):**
  `conout_body`'s dispatch preamble (`$7D5C`, the stack-peek DIRIO detector) stays
  **byte-for-byte unchanged**. Its emit tail `conout_not_dispatch` shrinks from the
  current 32-byte inline CHPUT to a **13-byte stub** that branches to the above-hole
  bodies:
  ```
  conout_not_dispatch:
        pop  hl                 ; caller AF stays on the stack
        ld   a, e
        cp   $09
        jp   z, conout_tab      ; jp (not jr): target is ~580 B away, above the hole
        call conout_emit_e      ; absolute call up over the hole
        pop  af
        ld   a, e               ; A := E (return contract, §5.1)
        ret
  ```
  Net: `conout_body` **shrinks ~19 B** → everything after it (incl. the `fdc_*`
  bodies and `p0_env_tab`) moves **DOWN**, never up through the hole. `dos_handoff`
  gains the 3-byte `$F237` seed (`ld ($F237),a`), so the net below-hole change is
  ~−16 B — still a shrink.

- **ABOVE the hole (the relocated body, pinned):** `conout_tab` (15 B) +
  `conout_emit_e` (45 B) = **60 B**, verbatim from the saved impl, placed after
  `p0_env_tab` and **pinned above the hole**:
  ```
                  IF ($ > $7FC0)                 ; NEW loud guard (see §4)
  ABOVE_HOLE_OVERRUN: equ p0_env_tab_overran_the_above_hole_routine_slot
                  ENDIF
                  ds   $7FC0 - $, $00            ; pin start at $7FC0 (data pad ACROSS
                                                 ; the hole tail — never executed)
  conout_tab:     ...                            ; $7FC0.. (60 B -> ~$7FFB); 64 B avail
  conout_emit_e:  ...
                  ds   $8000 - $, $00            ; final pad (≈4 B slack)
  ```
  `conout_emit_e` / `conout_tab` are reached ONLY by absolute `call` (from the stub
  and from each other) — no fall-through across the hole. They do console CHPUT
  (FDC idle) and live at `$7FC0+` (above the hole) regardless of FDC state, so their
  own fetches never hit the register window.

## 4. Byte budget + why it's safe (guarded, not hand-counted)

- Total: slice-2 net ≈ +40 B; the only free space is the 47-B pad → fits with a few
  B slack (matches the saved impl's "16384 / 4-B-slack" build).
- Above-hole routine 60 B fits `$7FC0–$7FFF` (64 B).
- `p0_env_tab` (26 B, DATA) may straddle the hole as it does today; it must end
  `≤ $7FC0` so the `ds $7FC0-$` is non-negative.
- **Three guards make every failure mode a LOUD build error, never a silent boot
  crash** (the M15 "no hand-guessed addresses" + the FDC-guard lesson):
  1. **existing** `IF ($ > $7FB8)` before `p0_env_tab` — fires if the below-hole
     change accidentally *grows* (executable code reaching the hole).
  2. **new** `IF ($ > $7FC0)` before the `ds $7FC0-$` — fires if `p0_env_tab`
     overruns the pinned routine slot (a plain `ds` negative only *warns* → silent
     empty object; this IF makes it fail).
  3. **existing** `ds $8000 - $` + the 16384-B size assert — total-overflow backstop.
- If guard #2 fires by a byte or two at build (the arithmetic lands `p0_env_tab`'s
  end within ~1 B of `$7FC0`), reclaim trivially from conout (e.g. `xor a` for the
  post-TAB `A:=0`, −1 B, F not load-bearing per §5.1/§8.1) or nudge the pin to
  `$7FC1`; the design carries ~4 B of slack. Final addresses come from the `.sym`
  at build, not from this doc.

## 5. Build / falsify-first order

1. Land the below-hole stub + the above-hole pinned bodies + the `$F237` seed
   together (they're one indivisible restructure). Build → **the two IF guards +
   16384-B check must pass**; regenerate `.sym`, confirm `conout_tab`/`conout_emit_e`
   start `≥ $7FC0` and `p0_env_tab` ends `≤ $7FC0`.
2. **Boot regression FIRST** (the crash the hole caused): `callseq --log 0x0005`
   boot+DIR aligned ours==stock (the deterministic boot-success oracle,
   [[openmsx-probing-toolbox]]); `make machines-oracle` then a `screen` DIR frame.
3. Then the slice-2 acceptance (§6).

## 6. Acceptance criteria (from conout53a7-spec §7, + the hole guard)

1. **Screen arbiter:** `screen --machine both` for (a) `--keys '\r'` (date + `A>`),
   (b) `'\rDIR\r'` (listing + footer + `A>`) — byte-identical frames ours==stock.
2. **No regression:** boot+DIR `callseq` aligned; BDOSX2 14-record capture zero-diff
   (keys2 echo now VISIBLE both screens); BDOSX 47/47; `make unit-test` 19/19;
   `make probe`; `disk.rom` == 16384 B; **both FDC/above-hole guards pass**.
3. **TAB oracle (slice 2):** inject `TABTEST.TXT`/`TABTEST2.TXT`
   (`scratchpad/make_tabtest_disk.py`), `TYPE` them: CHPUT stream
   (`callseq --log 0x00A2`) + `screen` byte-identical ours==stock — cols 1/2/8/34
   incl. at-stop and post-wrap cases.
4. **`$F237` parity:** `capture --mem 0xF237:0x1` at a late anchor, ours==stock.
5. **Docs:** [tier2-bdos-coverage.md](tier2-bdos-coverage.md) `$02` row notes the
   tab/column bookkeeping; conout53a7-spec §6 slice-2 marked landed; STATE.md
   residual cleared.

## 7. Clean-room status
Unchanged from conout53a7-spec §9 — this is a *placement* change, not new behaviour.
The tab/column semantics come from OUR OWN injected TABTEST files' observable output
+ the published `_CONOUT` contract; `$F237` is a pinned page-1 kernel-ABI DATA cell;
no stock code decoded. The relocation itself touches only OUR ROM's layout.

## 8. Risk / rollback
LOW. Pure layout + a byte-stable-preamble restructure of code that already exists and
was verified correct; three build guards convert any mis-placement into a loud error;
boot regression is the first gate. Rollback = revert the one commit (no cross-file
ABI change; the `$5454`/`$53A7` veneers still just `jp conout_body`).

## 9. IMPLEMENTATION OUTCOME — LANDED, with a deeper root cause found (2026-07-04)

The §3 plan (pin the *routine* at `$7FC0`, let the below-hole shrink move `p0_env_tab`
down) built cleanly but **crashed the DOS boot** — and root-causing that revealed the
§2 blocker was only HALF the story. **The FDC hole has TWO hazards, not one:**

1. (known) executable code fetched from `$7FB8-$7FBF` reads register bytes, not opcodes.
2. **(NEW) `p0_env_tab` is DATA, but `lay_page0_env` reads it THROUGH the ROM page to
   build the page-0 RST/CALLF/INT vectors — and those reads ALSO hit the register
   window.** The old FDC-guard comment's claim that the straddle is "transparent ROM
   reads while the FDC is idle" was **FALSE**. Proven: with the §3 plan, `p0_env_tab`
   shifted down so its `$0038`/INT_H_HIRAM entry landed at `$7FB8` (in the hole);
   `lay_page0_env` read it as FDC register garbage and wrote a **corrupt page-0 `$0038`
   vector** (`00 39…` vs stock's `C3 AE DD`); the first maskable interrupt then jumped
   into garbage → crash in MSXDOS.SYS init, *before* any console output (`conout_body`
   never even reached — which is what disproved the "it's my emit logic" theory).

**Why HEAD tolerates the straddle** (and the §3 plan didn't): at HEAD `p0_env_tab` sits
at `$7FB7`, so the hole covers only the **RDSLT/WRSLT** entries (offsets 1-8), whose
page-0 hooks the DOS boot tolerates as garbage; the load-bearing **`$0030` CALLF (DSKIO)
and `$0038` INT** entries sit *above* the hole and read correctly. Moving `p0_env_tab`
by ANY amount slides a critical entry into the window.

**The fix that landed:** **pin `p0_env_tab` at its exact HEAD address `$7FB7`** (a
`ds $7FB7-$` + `IF ($ > $7FB7)` guard), independent of below-hole size — reproducing
HEAD's proven-safe straddle. The 60 B of slice-2 code splits around the hole:
`conout_tab` (15 B) stays **below** (right after the branch stub, jr-reachable),
`conout_emit_e` (45 B) goes **above** the hole at `$7FD1` (right after `p0_env_tab`,
which ends `$7FD0`; a `IF ($ <= $7FBF)` guard asserts it clears the window). The
`$F237` seed is safe because the pin absorbs its +3 B.

**Verified (National_CF-3300_ZEROBASDISK oracle):** boot+DIR BDOS parity 260/260
aligned; page-0 `$0038` = `C3 AE DD` (valid); TAB expansion byte-identical ours==stock
on TABTEST.TXT (cols 1/2/8) AND TABTEST2.TXT (col-34 post-wrap); `$F237` parity 0-diff;
DIR screen byte-identical; BDOSX2 60/60 aligned; unit-test 19/19; probe smoke green;
ROM 16384 B; all three build guards pass. **The FDC-hole understanding is corrected in
the `p0_env_tab` code comment and [[disk-hardware-target-variants]].**
