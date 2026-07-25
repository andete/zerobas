<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 review queue — decisions taken without per-step sign-off

Running log for the **autonomous-span** working mode (2026-06-25). During a span I
chain `characterise → spec → implement → validate → commit` across milestones
without bouncing back; every judgment call I'd normally have asked about lands here.
When the user is back we do **one batched review** of the open entries, then I
archive them (move the resolved block under "Archived").

**Hard-stops (I pause the span and wait):** a design fork that hinges on user taste;
a clean-room legitimacy call I'm unsure of; anything irreversible/outward-facing;
a regression I can't get green or a blocker I can't crack; a scope surprise that
changes a signed-off plan.

Entry format: **[Mx.y / §8.zz]** what I decided · why · alternative · confidence ·
undo. Newest first.

**RESOLUTION 2026-07-05 — Tier-C cases 3/4/5 DONE (user: "finish up Tier-C"; both
forks "fix to byte-identity").** Signed-off spec
[tier2-m35-m36-tierc-fixes-spec.md](tier2-m35-m36-tierc-fixes-spec.md). Three new
BDOSX-family exercisers authored (bdosx5/6/7), characterised vs the CF-3300:
- **Case 3 (dir-full): byte-identical, no fix.** FMAKE on a root-dir-full fixture =
  stock (A=FF); folded into the gate (1 allowlisted FOPEN-miss L). Committed first.
- **Case 5 (FREN collision) → M35:** ours renamed onto an existing name (A=00,
  namespace corruption); stock refuses (A=FF). Fix = `fren_body` `fat_find`s the new
  name first → `fren_miss` (A=FF, kernel mirrors L=FF). ~12 B in-place.
- **Case 4 (WRRND past-EOF) → M36:** ours' random write past EOF returned success but
  didn't grow the file. **SCOPE JUDGMENT CALL (surfaced + approved):** a read-only
  artifact-oracle check found stock **persists** the extended size to the on-disk
  DIRENT (256→768), so an FCB-only bump would be VACUOUS — I flagged the scope growth
  and the user approved the full fix (FCB + dirent). `wrrnd_extend` grows FCB+16..19
  AND patches dirent+28..31 (fren_body idiom, not fat_dir_update); bdosx6 re-FOPENs to
  prove persistence.
- **Verified:** bdosx6/bdosx7 differentials byte-identical (bar documented date/dirloc
  + FREN/RDRND undefined-register classes); direct ours-run dirent read = 768 = stock
  (anti-vacuity). Gate **11/11** (BDOSX6+7 folded in). Unit **34/34** (2 new host
  tests). Tier-1 16384 B, 0 `k_*` moved, FDC window clean, md5 unchanged.
- **Sonnet self-caught bug (logged):** M36's first draft leaked the size-compare Cy=1
  as a false I/O error on every within-file WRRND; its new host test caught it before
  my differential. Fixed via a Cy-clearing `wre_noext` early-out.
- **Tier-C (the adversarial/boundary suite) is now COMPLETE** — all 5 cases landed
  byte-identical; the disk-full/dir-full/past-EOF-random/rename-collision corners are
  standing gate guards.

**RESOLUTION 2026-07-05 — M34 WRSEQ disk-full onset parity DONE (user chose "fix to
byte-identity" + "fold BDOSX4 into the gate").** Signed-off spec
[tier2-m34-wrseq-diskfull-spec.md](tier2-m34-wrseq-diskfull-spec.md).
- **Clean re-characterisation** (IX-fixed bdosx4) found TWO coupled divergences, and
  corrected the old contaminated numbers: **D1 onset lag** stock A=01 at WRSEQ **#1**
  (not #2), ours at **#4**; **D2 FCLOSE** stock 00 / ours FF. The old "stock
  terminates the program" reading was the since-fixed IX-walk artifact (control-flow
  is identical).
- **Root cause (our source):** `bdos_seqwrite_body` buffers records and only
  allocates a cluster at the 512-B sector-flush (record #4); stock allocates the
  fresh file's first cluster eagerly at #1. D2 is DOWNSTREAM of D1 — ours buffered
  384 B that FCLOSE then fails to flush (driver.asm `bdos_close_write`).
- **Fix (Sonnet 5, Opus-verified):** one eager free-cluster *availability* pre-check
  at the top of `bdos_seqwrite_body` (mirrors `ffds_nopad_body`'s alloc condition,
  fires at WRBUFLEN==0) + new scan-only `fat_have_free_cluster` @ $66F6 (mirrors the
  proven `fac_loop_body` scan, no claim, hint untouched). The real allocation stays
  at flush → **happy path provably unchanged** (falls through to byte-identical body).
- **D2 auto-fixed (prediction CONFIRMED, no FCLOSE change):** with nothing buffered,
  FCLOSE skips the failing flush → clean 0-cluster dir update → A=00. Same "fix the
  derail, the downstream symptom resolves" shape.
- **JUDGMENT CALL (log):** chose the **availability-check** design over true-eager
  (§4) — observationally byte-identical (registers + final disk artifact), lower
  risk; the only residual is the FAT's *intermediate* reservation timing, which is
  unobservable through any BDOS call (single-tasking) and leaves ours cleaner on a
  crash. User approved this design at sign-off.
- **Verified:** bdosx4 differential **0-byte-diff both machines** (onset #1, all-01,
  FCLOSE 00); the live-AF delta decodes to A=$00 on both, only the non-contractual F
  flag differs (benign, gate-classed). Gate **7/7** (BDOSX4 folded in, no allowlist);
  WRBLK/RDBLK round-trips only the pre-existing accepted divergences; unit **32/32**;
  Tier-1 16384 B, 0 `k_*` moved; md5 unchanged.
- **Tier-C case 2 CLOSED byte-identical.** The disk-full corner is now a standing
  regression guard in `make bdos-acceptance`.

---

## Open (awaiting next sync)

**[JUDGMENT CALL — traps T2 harness, 2026-07-25] The acceptance machine now models
PSG port directions like the VG-8020, and joystick triggers 1..4 are driven by a
PSG-latch injection with one residual blind spot.** `tools/install-repack-machine.py`
now emits `<ignorePortDirections>false</ignorePortDirections>` (openMSX defaults it to
`true`; `Philips_VG_8020.xml` sets it `false`). *Why:* the two sides of every PSG
differential were structurally different for a reason unrelated to our ROM, and the
default silently discarded the R7 write that the only scriptable joystick-button
mechanism depends on. zerobas's ROM never writes R7's direction bits (`SOUND` merges
`(curR7 & $C0) | (val & $3F)`, and `play-trace-acceptance` asserts R7 stays `$B8`), so
shipping behaviour is unaffected; `input-devices-acceptance` 50/50 and
`play-trace-acceptance` were re-run green after the change. *The mechanism* (spec
[spec-traps-t2-strig.md](../../docs/spec-traps-t2-strig.md) §7.3): put PSG port A in
output mode, then write R14 — verified byte-identical on both machines, and a
press/release/press sequence counts exactly 2 rising edges on both. **Residual:** the
injected latch sits *behind* the port-A/port-B multiplexer, so `STRIG(1)`/`STRIG(2)`
cannot be told apart, nor `STRIG(3)`/`STRIG(4)`. Every trigger is pressable and
edge-detectable; only "which physical port" stays untested. Flagged rather than solved —
no openMSX facility for it was found (dead ends recorded in the spec so they are not
re-derived).

**[RESOLVED — malformed-call fix D-F2-4, 2026-07-14] The slice-2e RND Finding 1
(malformed-call seed mutation) is FIXED as the family-wide slice it was deferred
to.** `ev_mc_arg`'s two error exits now raise the deferred FPERR=4 syntax error,
and a shared `ev_mc_arg_checked` gate makes all 15 ev_mc_arg-family functions
bail (no body run) whenever a deferred FPERR/TMISMATCH is pending -> clean
`syntax error` for bare/extra/unclosed/empty forms in PRINT/LET/IF, RND seed
provably untouched, AND fixes a transcendentals-era regression (LOG()/CINT()
were misreporting illegal/overflow). Fable review = SHIP; it caught a real
first-error-wins regression in my first cut (unconditional FPERR=4 clobbered an
erroring arg's div0/overflow) -> fixed (ev_f_empty conditional), which also
repaired the pre-existing D-F2-3 sibling `(1/0)+()`. Spec
docs/spec-basic-malformed-call-syntax-error.md; commits 2929365 + review-fix.
Two PRE-EXISTING gaps surfaced (below) remain the natural next steps.

**[JUDGMENT CALL — malformed-call review, 2026-07-14] Deferred-error DRIVER
COVERAGE + stored-mode RUN halt: two pre-existing architectural gaps, LOGGED not
fixed.** (1) Only PRINT (num+str items), LET, IF, POKE, VPOKE call
`check_expr_errors` after their eval, so a deferred FPERR/TMISMATCH is only
surfaced there. `FOR I=SIN TO 3` -> zb `out of memory` (vs ref `Syntax error`);
`SCREEN SIN` -> zb silent (executes SCREEN 0). Same class: COLOR/WIDTH/OUT/
ON..GOTO/GOSUB/PRINT USING/CLEAR/file-channel evals (OPEN/CLOSE/PRINT#/FIELD/
GET/PUT)/MID$-stmt counts/USR/SAVE/BSAVE args -- none check the deferred flags.
**Pre-existing** (identical before the D-F2-4 commit; the commit only upgrades
the stale value to 0). (2) Stored-mode `10 PRINT SIN`/`RUN` prints the error but
**continues** to line 20 (reference halts with `Syntax error in 10`); control
`10 PRINT 1/0` behaves the same -> it's the D-F2-1 statement-abort model (the RUN
loop proceeds past a per-line abort), the single largest divergence in the whole
deferred-error architecture. **Call made:** DEFER both -- they are one coherent
"propagate deferred errors through every statement driver + make RUN halt on
abort" slice, orthogonal to malformed-CALL handling, and regression-sensitive
(must audit every numeric-expr driver). No reference-legal program observes
them (all inputs are themselves illegal). Confidence high; undo = a follow-up
slice. Full record spec-basic-malformed-call-syntax-error.md §4/§6.

**[JUDGMENT CALL — mathpack slice 2e, 2026-07-14] `RND` SHIPPED reference-IDENTICAL; a
malformed-`RND`-call seed-mutation deviation DEFERRED to a family-wide fix (not bolted onto
2e).** `RND` (spec §15, commit d68426a) is the last slice-2 function and the FIRST to hit
bit-for-bit reference-identity as its native target (exact decimal LCG mod 1e14, A/C/S0
black-box-recovered per §4.2). Fable review = SHIP; its one matrix-invisible finding: a
**malformed** `RND` call the reference rejects with `Syntax error` (extra arg `RND(1.5,2)`,
or bare `RND` with no parens — reference aborts the line, seed untouched) is silently run by
zerobas on the stale FAC operand (`ev_mc_arg`'s `ev_f_err` sets the `$DD` ERRMARK landmark but
does NOT abort these evmc paths), which **mutates the persistent seed** (reseed/advance;
bare `RND`→`RND(0)`) and diverges the sequence until the next NEW/CLEAR/RUN. **Call made:**
DEFER, not fix in 2e — (1) it is a **pre-existing evmc-family gap** (bare `SIN` also returns
`0` vs reference `Syntax error`), not a 2e regression; RND only escalates its *visibility*
(persistent-state mutation vs a transient wrong value); (2) the correct fix is a **dedicated
family-wide "malformed function-call → `Syntax error`" slice** — the sibling of the empty-parens
slice (`spec-basic-empty-expr-syntax-error.md`, which itself deferred the adjacent EOL
`Missing operand` case), so this matches precedent exactly; (3) an RND-only guard would be
inconsistent with the six other evmc math functions and STILL wouldn't emit `Syntax error`
without the family plumbing; (4) **no reference-legal program can observe it** (the reference
aborts the RUN at the syntax error). Flagged as the family's **worst member** (only one that
mutates persistent state) → highest priority when that family-wide effort is taken up.
Confidence high; undo = trivial (a follow-up slice, nothing to revert). Full record spec §15.7.
Alternative considered + rejected: a cheap RND-local `evmc_rnd` guard (prevents the mutation
but not the missing `Syntax error`, and breaks family symmetry).

**[JUDGMENT CALL — mathpack slice 2c, 2026-07-14] `^`'s spurious-overflow surface kept
bug-for-bug; positive-y int path asserted BIT-IDENTICAL (stronger than the signed
ATN-shape bar).** Characterization (spec §13.1) revealed the reference's integer `^`
overflows on inputs whose RESULT fits (`10^62`→Overflow though 1E62 is representable;
`1D62^1`→Overflow) — an emergent artifact of its LSB-first square-and-multiply feeding
its multiply's own E1+E2≥64 pre-normalisation gate, which our fp_mul already carries
IDENTICALLY (probed 6/6 on plain `*`, both machines). Two calls made under
[[bug-for-bug-compat-over-accuracy]] without an interim sync: (1) we REPRODUCE that
surface (a user typing `10^62` gets Overflow like the reference, though the value is
representable — the alternative, a "better" loop shape, would break the bit-identity
and diverge the error surface); (2) since the composition is then bit-exact for free,
the gate ASSERTS positive-y int-path bit-identity differentially (exceeds the ratified
documented-deviation bar; neg-y/frac stay truth-bound: our correctly-rounded div beats
the reference's low-biased one by ≤1 ulp, and the frac path inherits our own EXP/LOG).
Also: our `10^-70.5`=0 where the reference throws its own EXP(-162) disposition-bug
Overflow (the §12.9 reference bug, inherited by its `^`) — kept OURS-correct, captured
informationally. Flag if either call should flip. Full record spec §13.1/§13.2/§13.8.

**[JUDGMENT CALL — mathpack slice 2b, 2026-07-13] Never-worse invariant shape for
EXP/LOG = the ATN bounded-deviation form, not per-input strict.** §11.10 asserted "the
other five functions (references 4–20 ulp off) keep the strict [per-input never-worse]
invariant trivially at 14 digits." Writing the 2b contract against the pre-proven chain
sim showed that claim was optimistic *in per-input form*: the reference EXP/LOG are
correctly-rounded on scattered inputs (~15 %/~30 % of the characterization battery), and
our 14-digit chains land 1–2 ulp off on SOME inputs (EXP worst 1 ulp/92 % exact; LOG
worst 4 ulp/87 % exact, all >2-ulp cases in the fold path's den-15-digit +
∂r/∂s=2 wall) — so on an unlucky overlap the reference can win per-input. Applied the
framework the user already ratified for ATN (§2/§11.10, the more demanding case):
gate = truth-bound (EXP ≤ 2, LOG ≤ 4) + exact-count floor, reference captured
informationally. Aggregate superiority is overwhelming (reference EXP worst −45 ulp
@x=88 — measured this slice; ours exact there). Full rationale spec §12.1. Flag if the
per-input form should instead be escalated (would need the extended-precision layer
already declined for ATN).

**RESOLUTION 2026-07-07 — BDOS harness AUTOEXEC.BAT auto-run DONE (user: "all 8 now",
one commit per script, --settle left untouched).** Signed-off spec
[tier2-autoexec-bat-harness-spec.md](tier2-autoexec-bat-harness-spec.md). Verify-first
(black-box, both machines): a disk with `AUTOEXEC.BAT`="BDOSX" reaches BDOSX's resident-arm
anchor with ZERO typed keys on both the CF-3300 oracle and ours (t~18s); a control disk
without `AUTOEXEC.BAT` never reaches it under an identical zero-keys capture — confirming
MSX-DOS 1 auto-runs `AUTOEXEC.BAT` and skips the date prompt on both. All 8
`build_bdosx*_disk.py` scripts now inject `AUTOEXEC.BAT` and drop `--keys`/`--keys-at`
(7 mechanical; `build_bdosx2_disk.py`'s `--keys2-at 32` timing for its staged CONIN/DIRIN/
INNOE input was left unchanged and re-verified, since record 7's `const_poll` busy-waits for
it — only needs to land after the COM's own disk load, which `AUTOEXEC.BAT` only makes
earlier, never later). Fixture-shape gotchas handled: BDOSX4 (100%-disk-full) and BDOSX5
(dir-full) inject `AUTOEXEC.BAT` BEFORE their filler/saturation step so the fixture invariant
(exactly 0 free clusters / exactly 0 free root-dir slots) still holds. Re-verified per script
+ full gate: `make bdos-acceptance` **11/11** (unchanged), `make unit-test` 34/34, working
tree clean (harness-only, zero assembly touched). The former parked note is preserved below
for context:

**[FUTURE IMPROVEMENT — parked 2026-07-05, DONE 2026-07-07] BDOS harness: replace the typed
`.COM` launch with `AUTOEXEC.BAT` auto-run (zero typing).** The `make bdos-acceptance` gate
(the primary 11/11 standing guard) launches each exerciser by TYPING it: `build_bdosx*_disk.py`
pass `--keys '\rBDOSX\r' --keys-at 20` to `disk_probe_diff.py` (the leading `\r` answers the
MSX-DOS date prompt; `BDOSX\r` runs the COM). That is the SAME openMSX key-injection class that
caused the SAVE/BSAVE false-positive (first-keypress doubling in narrow emutime windows,
[openmsx-probing-toolbox.md](openmsx-probing-toolbox.md) §8) — a latent flakiness sitting in our
most important gate. **Improvement (idea from the user):** inject an `AUTOEXEC.BAT` (contents
`BDOSX`) onto the throwaway DOS disk next to `BDOSX.COM` and drop the typed keys. **No ROM change**
— `AUTOEXEC.BAT` is `COMMAND.COM`'s job, and `COMMAND.COM` is stock MSX-DOS 1.03 loaded from the
disk (identical on ours + CF-3300, disk-resident), unlike `AUTOEXEC.BAS` which we had to implement
in our Disk-BASIC ROM. Standard MSX-DOS also **skips the date prompt** when `AUTOEXEC.BAT` exists,
so the leading `\r` goes away too → zero typed input. Bonus: exercises a bit more of the DOS path.
**Verify-first (black-box, like the AUTOEXEC.BAS experiment `scratchpad/autoexec_probe.py`):**
confirm MSX-DOS 1 (a) auto-runs `AUTOEXEC.BAT` and (b) skips the date prompt, on the CF-3300 AND
ours. **Scope:** ~8 `build_bdosx*_disk.py` + re-anchor the `disk_probe_diff` capture timing (the
COM now runs at boot, not t=20). Spec + sign-off before touching all 8 (primary gate). See
[[diskbasic-acceptance-gate]] for the parallel `AUTOEXEC.BAS` precedent.

**2026-07-05 — Disk-BASIC acceptance gate built; two items for review:**
- **[JUDGMENT CALL, deviated from sign-off] Smoke probes KEPT, not retired.** Sign-off (decision 2)
  said retire `diskbasic_probe_filechannel/files/format`. On execution I found they are **cited
  provenance anchors** (the Phase-2 spikes that first recorded the file-channel contract / FILES
  format / CALL FORMAT dispatch, cited in [file-channel-protocol.md](file-channel-protocol.md) +
  [basic/PROVENANCE.md](../../basic/PROVENANCE.md)). Deleting them breaks the provenance trail
  (dual-mission), so I took the conservative reversible path: **kept them + added a header banner**
  marking each "provenance-capture, NOT part of the gate." Achieves decision 2's intent (no
  false-coverage) without the citation loss. **Flag if you'd still prefer deletion.**
- **[RESOLVED 2026-07-05 — NOT a ROM bug; flaky-probe false positive.] "Binary BSAVE-to-disk"
  red cell.** The gate's first run reported 22/23 with `disk_probe_save.py` red; I initially
  (wrongly) called it a real pre-existing ROM bug. **Investigation (Fable-solo) proved the ROM
  innocent — the red was an openMSX test-harness artifact:** the probe typed its `bload` command
  via keyboard injection at emutime t≈26, where `type`'s first keypress **doubles** on
  `C-BIOS_MSX1_BASIC_DISK`-with-disk (~t=26–27 window) → `bbload"…"` → syntax error → BLOAD never
  ran → the region kept the probe's wipe byte, which was `0x00` and so masqueraded as "loaded
  zeros." Proof: (1) offline FAT12 dump of the BSAVE'd file = exact 17-byte pattern on disk (write
  path byte-perfect); (2) nonzero-sentinel re-run reads `a5a5…`, not `00` (BLOAD demonstrably never
  executed); (3) same sequence at t=36 round-trips byte-identical. **Fix = probe-only** (leading
  space on all typed commands so a doubled first key becomes a doubled space eaten by `skip_spaces`;
  nonzero `BIN_SENTINEL`). → SAVE/BSAVE green, **gate now 23/23, ROM clean**. TODO.md L148/167 was
  NOT an overclaim after all. **Follow-up (in progress):** replace this type-injection probe for
  SAVE/BSAVE with a **`.bas`-on-disk / boot-auto-run** test (zero keyboard typing) — the robust
  methodology that eliminates this whole failure class; pilot signed off (RAM-sentinel + on-disk
  artifact capture). Gotcha recorded in
  [openmsx-probing-toolbox.md](openmsx-probing-toolbox.md).

**RESOLUTION 2026-07-05 — M33+M32 DONE (signed-off spec
[tier2-m33-m32-fcb-position-spec.md](tier2-m33-m32-fcb-position-spec.md); user chose "full
byte-identity" for CR-bookkeeping + "implement correctly" for `$24`).** Sonnet-5 impl, Opus-verified:
- **M33** RDSEQ FCB position write-back — `wrseq_body`'s read branch (NOT the shared `bdos_seqread_body`
  — that would corrupt RRND/boot; a hazard I caught in my own spec before dispatch) mirrors
  CR/EX/current-cluster/index into the `$DA40` FCB copy; new `BDOS_SEQREC` ($E814) seeded by FOPEN.
  **Byte-identical to CF-3300** across a read sweep + extent roll (bar `+25` dirloc).
- **M32** correct `$24` SETRND at the pinned `$50C8` (`C3` veneer, net-zero): `rr=cr+ex*128+s2*4096`,
  an intended documented divergence from stock's `RR:=1` stub. Positive test K=3→3/K=129→129. **Exit
  regs pinned to stock** (A=`$25`, HL=`$0025`) — only the rr value diverges.
- **Two honest corrections during verify:** (a) my first `setrnd_body` exited A=`$00`/HL=`$0000`; the
  BDOSX snap showed stock exits A=`$25`/HL=`$0025` (dispatcher passthrough) — fixed to match. (b) My
  spec §5 predicted "correct `$24` does NOT green the gate"; WRONG — implementing §4's intent (don't
  gate the `$24`-chained path; test `$27` with an explicit record) I broke the chain in `bdosx.asm`
  (FCB+33..35:=1 before `$27`) so the DTA converges → `make bdos-acceptance` now **6/6 ALL CONVERGED**
  (was 4/6, BDOSX RED). Gate got greener AND stricter (no byte hidden; only date+M22a-cosmetic excused,
  same as BDOSX3). `$24` verified standalone; `$27` still 3/3 via M31's dedicated probe.
- **JUDGMENT CALL (log):** breaking the `bdosx.asm` `$24`→`$27` chain + adding a BDOSX allowlist entry
  is a gate-exerciser change realizing signed-off §4 ("the dedicated probe" tests `$27`). It flips the
  earlier "stays RED" expectation to green. Flagged in my report for veto; alternative = leave BDOSX RED
  on the intended cascade (noisier CI, hides future regressions behind a known failure).
- **No regression:** unit 31/31; `bdos_seqread_body`/`driver.asm` byte-unchanged; Tier-1 16384 net-zero;
  oracle md5 unchanged.

**CHARACTERISED 2026-07-05 — M33 RDSEQ FCB write-back ("CR bookkeeping") DONE; fix is a scope fork
(surfaced to user).** Doc [tier2-m33-crbookkeeping-char.md](tier2-m33-crbookkeeping-char.md) (user
chose "characterize it next"). Stock steps the user FCB every read (`+32` CR = K mod 128, `+12` EX =
K div 128, `+28/30` internal FAT current-cluster/index once clusters cross); **ours never advances
any** — at K=0 ours==stock bar dirloc, so FOPEN is faithful and the ONLY growing divergence is the
missing write-back. Root cause (our source): the shared `$477D` worker's read side
`bdos_seqread_body` (kernel.asm:346) tracks position in GLOBAL cells and never writes the FCB copy at
`DE=$DA40` (pointer already live at entry); it also lacks an absolute record counter. **Coupling:**
the M32 "correct `$24`" reads EX/CR *from the FCB*, which stay 0 without this fix → a correct `$24`
is useless unless CR-bookkeeping is fixed OR `$24` reads our internal state instead. **⇒ decide this
scope BEFORE speccing `$24`.** Fork: (A) documented fields EX/CR only + allowlist `+16..31` internal
divergence · (B) full byte-identity incl. `+28/30` · (C) defer. NOT fixed pending the answer.

**CHARACTERISED 2026-07-05 — M32 `$24` SETRND black-box characterisation DONE; implementation is a
HARD-STOP design fork (surfaced to user).** Spec/evidence
[tier2-m32-setrnd-char.md](tier2-m32-setrnd-char.md); tooling `setrnd_char.asm` +
`disk_probe_setrnd_char.py` (committed). Interpreted the post-M31 "continue" as authorising the
read-only characterisation step I'd offered (no code). Result **pins the anomaly precisely**: stock
`$24` is a **broken/stub** function — its entire effect is `FCB+33:=1, FCB+34:=0, FCB+35:=FCB+14>>1`,
**independent of EX/CR** (proven across CR 0→127 + an extent roll to EX=1). Under normal conditions
(FCB+14=0 post-open) it collapses to **`RR:=1` constant**. A "correct" CP/M `EX×128+CR` impl would
therefore *diverge* from the oracle — which is exactly why characterise-first mattered. Isolation
(with/without `$24`) proves `$24` is the writer (`+33: 00→01`), not FOPEN/RDSEQ. Two more findings:
(a) BDOSX calls `$24` *before* setting record size, so the gate needs only `FCB+33:=1`; (b) a
**separate** gap surfaced — ours' RDSEQ never advances the user FCB position (EX/CR/pointers stay 0
where stock steps them) = the "CR bookkeeping" item, real and likely the bigger gate contributor.
**HARD-STOP fork for the user (faithfulness taste, no default):** (A) reproduce the quirk `RR:=1`
[byte-identical, greens gate] · (B) implement SETRND correctly [documented divergence, doesn't green]
· (C) defer. Plus whether to bundle the CR-bookkeeping fix. NOT implemented pending the answer.

**RESOLUTION 2026-07-05 — M31 `$27` RDBLK un-simplification DONE (user chose "$27 only, as
M31" after the investigation revealed gate-green is 3-part).** Signed-off spec
[tier2-m31-rdblk-randrecord-spec.md](tier2-m31-rdblk-randrecord-spec.md). A read-only Fable
investigation first settled: (Q1) a running program's `$27` enters **`k_47B2`** (kernel.asm),
NOT `bdos_rdblk` (driver.asm, boot-only) — so the fix touches k_47B2 alone; (Q2) both boot/TPA
loaders pass RR=0/RS=1 (positioning is a boot no-op, but RS≠128 must be honored); (Q3) the stock
A/HL/RR-advance/zero-pad contract (matches grauw `_RDBLK`). Sonnet-5 impl, Opus-verified:
- **`k_47B2` rewritten** to a faithful RDBLK: position to `FCB+33..35`, transfer ≤HL records of
  `FCB+14..15` size (0→128), zero-pad a final partial record, `RR := RR + HL` write-back, unified
  return (A=0 all-read / 1 EOF-first; HL=BC=records; IX=DRVA_DPB; IY=entry-DE; `$F306` clear).
  3b-relocation (veneer `jp k47b2_body` at `$47B2`, body in the `$75A5` free corridor).
  `bdos_rdblk`/`rdb_recloop_body` (boot MSXDOS.SYS path) **byte-identical** (driver.asm 0-diff).
- **Live-oracle round-trip PASS** (new `disk_probe_rdblk_roundtrip.py` + `rdblk_rt.asm`):
  cases mid-file(RR=1)/EOF-zero-pad(300B)/at-EOF all **byte-identical to National_CF-3300** (DTA +
  return snapshot). Host test `test_rdblk_randrecord.py` (31/31). Boot regression PASS (BDOSX ran
  → both k_47B2 paths). Tier-1: 16384 B, 28 ds-anchors identical (jp-operand relocation only).
- **My gate-prediction was WRONG (honest correction):** I predicted the gate stays byte-for-byte
  RED. It **converged** — BDOSX `0x0300` 11→8 unexcused (RR write-back makes BDOSX partly match
  stock even at RR=0). Good direction, no regression, still 4/6 (BDOSX RED pending the deferred
  pieces). **Exerciser lesson:** a bare FOPEN→`$27` reads zeros/EOF on BOTH machines — the FCB
  must be name-filled AND `$27` needs the BDOSX-style FOPEN→RDSEQ×2→SETRND preamble to establish
  extent state; capture must exclude FCB+32 (CR) / FCB+25 (dirloc).
- **Still open (unchanged, none forced):** to GREEN BDOSX still needs (i) `$24` SETRND real
  `$50C8` — but its stock contract is anomalous (leaves RR=1 *constant*, ≠ the DOS-2 formula), so
  it needs its OWN black-box characterisation first; (ii) FCB-copy **CR bookkeeping** in the
  sequential worker (stock advances copy+32 per record; ours doesn't). Plus (iii) WRSEQ disk-full
  onset lag (P2).

**[Tier-C → BIGGER] HARD-STOP: the case-2 dig uncovered a vacuous acceptance gate + a live
create-file regression in `main`. Surfaced to user 2026-07-04 (2nd time this thread).**
The Fable-solo root-cause investigation (dispatched after the user chose "investigate root
cause first") returned a much larger result. Two claims INDEPENDENTLY VERIFIED here (own reruns,
not the agent's word):
- **VACUOUS GATE (verified):** the committed BDOSX3 capture (`--at 0x0333`, un-armed) fires
  occurrence #1 during BOOT at **t=0.31 s** — ~20 s before the `\rBDOSX3\r` keys (t=20) load the
  program. "0/293 bytes differ" is a hollow PASS comparing COMMAND.COM idle state, not the
  exercised BDOS surface. The Tier-B "6/6 converged" baseline included these. The arm-gate that
  fixes it (`_capture_arm`, disk_probe_diff.py:227-235) is opt-in and NO builder emits it.
- **LIVE create-file DIVERGENCE (verified):** same BDOSX3 capture, HONESTLY armed
  (`--arm-check-val 0x03`, anchor now at t≈31–38 s AFTER the program runs) → **17/293 bytes
  differ, `ours=FF` where `stock=00`** at the FOPEN/RDSEQ results: ours fails to REOPEN a file it
  just FMAKE-created. A real regression in the M24–M26 mutation block, hidden by the vacuous anchor.
- **CORRECTION to the earlier case-2 note:** the "stock terminates the program on disk-full"
  reading was an ARTIFACT of a bug in our OWN exerciser — `bdosx4.asm` walks `IX` across BDOS
  calls without reloading (bdosx3.asm reloads before each `snap`); the kernel returns FCB calls
  with IX clobbered, so our post-call `ld (ix+0),$15` corrupted stock's page-3 RAM and killed it.
  A scratchpad exerciser that reloads IX runs to completion on BOTH machines. The WRSEQ disk-full
  ONSET lag is still real (ours defers allocation to the 512-B flush boundary; stock detects at
  the first unwritable record) — but it is now the LEAST severe of the findings.
- **Agent's root-cause DIAGNOSIS (symptom verified, mechanism NOT yet independently checked):**
  the National FDC register window is $7F80–$7FBF (mirrored ×8), not just $7FB8–$7FBF as the
  guard assumes (runtime.asm:706-726); `fdc_useslot_body` (create's dir-slot claim, ~$7F8E–$7FB5)
  sits IN it → FMAKE stops persisting the dirent; regression landed ~M27. NEEDS a targeted
  independent check before it's trusted as the fix target.
- **Decision PENDING user:** this is now a P0-in-`main` + verification-gap situation, far beyond
  the Tier-C scope the user greenlit. No source touched; nothing committed for case 2; BDOSX4
  stays OUT of the gate. · confidence: gate-vacuity + live-divergence HIGH (reproduced here);
  FDC-window mechanism MEDIUM (agent-only).

**RESOLUTION 2026-07-04 — FDC-window P0 FIXED (commit 2047822) + write-path residual root-caused:**
- **FDC-window mechanism CONFIRMED + FIXED.** True window is $7F80–$7FBF (×8 mirror); the three
  position-free tail blocks (fdc_entloop_body/fdc_useslot_body/p0_env_tab) relocated OUT into the
  kernel free-region corridor. PROVEN byte-pure (old-vs-new ROM = 5 clusters: 2 veneer jp operands
  + 1 `ld hl,p0_env_tab` operand + bodies moved verbatim $7F5F→$607E). Window now dead $00 pad;
  guard corrected to $7F80 with a tamper-tested `FDC_WINDOW_INTRUSION` build assert. BDOSX3
  create→reopen→read region converged 17→0 B. Net-zero canonical; disk.rom=16384; unit-test green.
- **De-vacuumed gate residuals ROOT-CAUSED (Fable, 2026-07-04; relocation EXONERATED — all
  reproduce fresh-vs-fresh).** Breakdown: **(c) documented/accepted divergences the gate has no
  allowlist for** — date-stamp (we intentionally don't stamp; fat.asm:16) + dirloc/devid cosmetic;
  **(b) exerciser out-of-contract** — bdosx.asm drives $24/$26/$27 without setting FCB record-size,
  so it compares implementation-defined garbage; **(a) real ROM items** — $23 FSIZE returns A=$03
  not A=0 (return-contract nit); $27 RDBLK (k_47B2) is a documented stream-from-0 simplification;
  $26 WRBLK is UNIMPLEMENTED (feature gap, not a regression).
- **NEW CONFIRMED P1 (independently verified in source):** RDRND/WRRND ($21/$22) position to the
  WRONG record. `rrnd_recsector` ($7C83) and `rrnd_clussec_tmp` ($7CAD) are `db` scratch cells
  INSIDE the ROM (kernel.asm:1699/1729), written at runtime (`ld (…),a`, :1655/:1709) → the stores
  no-op (ROM is read-only), reads always return 0 → BDOS_RECIDX≡0 and the WRRND absolute sector is
  wrong. **Same CLASS as the FDC-window P0** (silent store into ROM address space); NOT in the FDC
  window; latent since M26. Invisible to the RAM-only gate — caught only by disk-artifact inspection
  (ours wrote wrpat to BDOSX.BIN record 0, stock to record 1). Fix = move the 2 cells to RAM.
- **Harness landmines to fix (Fable):** (1) disk_probe_diff.py copies `--diska` ONCE and runs OURS
  then STOCK on that same image (:324/:1246) → unsound for write-exercisers (stock boots an
  ours-mutated disk); didn't drive today's diffs but is a landmine. (2) the BDOS name table
  mislabels $25/$26/$27 ($26=WRBLK, $27=RDBLK). (3) gate needs an allowlist for documented
  divergences + on-disk evidence (RAM capture is blind to wrong-record writes); the exerciser
  fixture ramp has period 256, so buffer bytes cannot prove positional correctness.
- **RESOLVED 2026-07-04 (user chose "spec + fix P1 now" + follow-ons).** Signed-off spec
  [tier2-writepath-remediation-spec.md](tier2-writepath-remediation-spec.md):
  - **F1 DONE (c557628):** RDRND/WRRND P1 fixed (scratch cells ROM→RAM $E760/$E761, net-zero);
    disk-artifact round-trip PASS (WRRND r0=1 → BDOSX.BIN record 1 == CF-3300).
  - **F4 DONE:** disk_probe_diff.py copies per-machine (write-exerciser soundness); BDOS name
    table $26=WRBLK/$27=RDBLK.
  - **F3 DONE:** exact-address anti-vacuous allowlist; BDOSX3 GREEN (documented date/dirloc +
    undefined-return regs cited), gate 4/6. Coverage doc's vacuous $23/$26/$27 claims corrected.
  - **F2 DEFERRED:** $23 FSIZE is a kernel shared call (no disk-ROM handler); A=3 may be a valid
    CP/M dir code — needs its own contract characterisation, not a forced edit.
  - **OPEN tracked follow-ons (next syncs):** (1) implement $26 WRBLK (unimplemented feature);
    (2) fix bdosx.asm to set FCB record-size before block ops so BDOSX is validly gatable;
    (3) characterise the true $23 F_SIZE return-in-A; (4) adjudicate the WRSEQ disk-full onset
    lag (P2, least severe). BDOSX stays honestly RED in the gate until (1)+(2).

**RESOLUTION 2026-07-04 (follow-ons (2) DONE + (3) dispatched):**
- **F5 DONE (follow-on (2)) — bdosx.asm out-of-contract fixed.** `bdosx.asm` now sets FCB+14..15=128
  (word) immediately BEFORE the `$27 RDBLK`/`$26 WRBLK` block ops (NOT after FOPEN — an earlier
  placement corrupts position state the sequential path relies on and breaks stock's RDSEQ; measured
  both ways). Result: the block-op differential is now WELL-FORMED — both machines transfer a defined
  128-B record; the residual is exactly one record's positional offset (`$27` stream-from-0 vs stock's
  random-record position) + the `$26` gap + the `$23` A=3 nit. **Characterisation bonus:** setting
  FCB+14=128 made STOCK read a real block (was `00`), confirming stock MSX-DOS-1 uses FCB+14..15 as
  record size = our `driver.asm:578` interpretation (retires a latent divergence worry). **BDOSX
  still cannot go green from this fix alone** — the premise that the record-size fix "unblocks BDOSX
  to green" was optimistic; green needs the `$26` implementation (explicitly excluded by the user)
  AND the `$27` un-simplification. Gate unchanged at 4/6; BDOSX RED is now diagnostic, not garbage.
- **Follow-on (3) $23 F_SIZE — CHARACTERISED, verdict CONFIRMED BUG (Fable-solo + re-verified here).**
  Ours' `$23` is a found-BLIND stub: constant `A=L=$03`, random-record field (fcb+33..35) never set.
  Refutes the "valid CP/M dir code" theory — stock returns `A=L=0`+r0=ceil(size/128) on found,
  `A=L=$FF` on not-found (map.grauw.nl `_FSIZE`); ours returns `$03` for found, not-found (re-ran:
  absent file → stock `$FF` / ours `$03`), any slot, any size. A is not a dir code (dir codes are
  F_OPEN/CLOSE/SFIRST/SNEXT per seasip). **Fix is FEATURE-SCALE** (real dir-search + record-count),
  same class as the user-excluded `$26` — needs its own spec + sign-off, not net-zero. HARD-STOP:
  surfaced to the user as a scope decision (do NOT implement unilaterally). Docs (coverage row +
  summary, writepath-spec F2) corrected to the characterised truth.
- **Still open:** (1) implement `$26` WRBLK (user-excluded feature); (3-fix) implement a real `$23`
  FSIZE (feature-scale, pending user decision); (4) WRSEQ disk-full onset lag (P2).

**RESOLUTION 2026-07-04 — M28 block/random pass DONE (real `$23` FSIZE + `$26` WRBLK; user chose
"bundle $23 + $26").** Signed-off spec [tier2-m28-blockrandom-spec.md](tier2-m28-blockrandom-spec.md)
(APPROVED: defer `$27`, full past-EOF extend, sane shrink, Sonnet 5 impl). Implemented + Opus-verified:
- **`$23` FSIZE** — `fsize_body`@`$501E` (dead-pad wire). Gate-converged (BDOSX `$0300` 15→11 diffs;
  the 4 removed are all FSIZE stub artifacts). RAM-visible result, so the gate is its oracle.
- **`$26` WRBLK** — `wrblk_body`@`$47BE`. **The trace agent's "repoint the `$D8BE` table" advice was
  CORRECTED in the Opus verification pass** to a **3b relocation** of `ff_secloop` (the `$D8BE` table
  is the fixed shared-kernel ABI, not ours; `$47BE` collided with live `ff_secloop`) — committed
  5fe8d41 before any code. **Verified byte-identical to the CF-3300 by disk-artifact round-trip**
  (probes/disk/disk_probe_wrblk_roundtrip.py + wrblk_rt.asm — the RAM gate is BLIND to disk writes):
  within-EOF, past-EOF extend, and a 24-bit-RR 33-cluster extend all match stock (size/FAT/data).
- **Sane-shrink divergence (signed off §6 Q3):** ours frees the tail + EOC-marks (FCLOSE succeeds,
  1-cluster consistent chain); stock leaks the tail (verified: 4 clusters under size=384). Documented
  in tier2-bdos-coverage.md — INTENTIONAL, correct-where-stock-is-broken, not a regression.
- **Tier-1 green:** disk.rom=16384; net-zero canonical (baseline sym diff: 0 `k_*` moved); veneers
  correct; FDC window clean; unit-test 28/28 (3 new: test_wrblk_fsize/extend/body_e2e).
- **Two honest edge-case notes (NON-blocking):** (a) `fat_alloc_cluster` is O(n²) so large
  multi-cluster extends are slow but correct (§4 non-goal tradeoff — a 33-cluster extend needed
  >46 s emulated; NOT a bug — initially mistaken for one until re-run with budget); (b) the mod-64K
  `(HL×RS)` transfer-byte wrap on pathological HL (e.g. 513 records/call) is host-multiply-tested
  but not separately round-tripped (ours writes HL records literally; extreme/unrealistic input).
- **Still open (unchanged):** (A) `$27` RDBLK stream-from-0 un-simplification — now the ONLY thing
  keeping BDOSX RED in the gate; deferred with its own COMMAND.COM-boot regression check. (B) WRSEQ
  disk-full onset lag (P2). Neither forced.

**RESOLUTION 2026-07-04 — M29 WRBLK position cursor DONE (perf; user directive "the O(n²) should
be investigated for improvement").** [tier2-m29-wrblk-position-cursor-spec.md](tier2-m29-wrblk-position-cursor-spec.md),
signed off after TWO scope rounds (C+P → narrowed to **P only**). Investigation found the M28
"O(n²)" was actually THREE costs; scope resolved after measuring each:
- **P — positioning re-walk (FIXED):** `wrblk_position_ext` re-`fat_open`'d + re-walked from the head
  every record. Now keeps an incremental cursor (`WRBLK_CURVALID`/`WRBLK_CURSEC`, 3 B in the free
  `$E7F8` tail); same-sector records (¾) do ZERO positioning I/O (`wpe_same`), next-sector = one step
  (`wpe_adv`). `fat.asm`/shared kernel untouched. Measured: K=32 single-call extend **2592 → 131**
  FAT reads (quadratic → linear, ~4/cluster); redundant intermediate data-reads gone.
- **C — no FAT-sector cache (DROPPED):** a `SECTOR_BUF`-keyed cache is clobbered by a data read
  EVERY hop (kernel.asm:1044 then 1100-1101), so ~0 benefit; and P makes the remaining walk a
  once-per-call amortized cost. A useful C needs a dedicated FAT buffer — low value, deferred.
- **A — allocator rescan-from-2 (DEFERRED):** `fat_alloc_cluster` restarts the free-scan at cluster 2
  each call → K-cluster extend still O(K²). Carries a next-free-hint + free-invalidation correctness
  surface; reopen if a workload needs it. **This is why the `rr24` single-record 33-cluster extend
  is UNCHANGED by M29** (one position call, allocation-bound) — still needs `--end 150`, verified
  byte-identical there (no regression). An earlier spec draft wrongly claimed M29 speeds rr24 up;
  corrected in §6.
- **Verification:** existing tests pass with NO expected-value edits (artifact byte-identical);
  new `test_wrblk_cursor.py` asserts O(N) shape (16-rec call ≤28 reads vs old ≥136); Tier-1 green
  (16384 B, 0 `k_*` moved); round-trip byte-identical incl. a NEW `multi` case (8 records/call,
  `checkrec=6`) that directly exercises the cursor path against the CF-3300 oracle.

**RESOLUTION 2026-07-04 — M30 fat_alloc_cluster next-free hint DONE (perf; A, user "continue with A").**
[tier2-m30-alloc-hint-spec.md](tier2-m30-alloc-hint-spec.md). Per-operation hint (`FAT_ALLOCHINT`
`$E7FB`) reset in `fat_mount`, scan-from-hint + advance-on-success in `fat_alloc_cluster`. The feared
**free-invalidation correctness surface does not exist**: only 2 free sites (`wrblk_shrink`, `fdel_body`),
`$16` create orphans, and NO single operation frees-low-then-allocates — so per-operation reset makes it
provably byte-identical to today with ZERO free-site changes.
- **Win is CPU-only (honest correction):** the allocation quadratic was in FAT-entry RAM scans, NOT I/O —
  `fat_alloc_cluster`'s existing `FAT_WRTMP2` intra-call cache already made alloc I/O linear. Measured
  M29→M30 (`wrblk_perf.py --alloc`): CPU **4.4×** (K=32, free 64 in) → **9.2×** (free 400 in); **I/O 1.0×**.
  So modest real-hardware benefit (unlike M29's P, which cut actual sector accesses). `rr24` unchanged.
- **PRE-EXISTING finding surfaced (not M30):** ours is lowest-free-first (reuses freed low clusters); the
  CF-3300 is NOT (`del_realloc`: ours `[340,336]` vs stock `[340,339]`; a HEAD ROM gives the SAME ours
  chain). Round-trip `del_realloc` case is `kind="divergence"` (documents, asserts ours self-consistent).
  **Open item (D) — CHARACTERISED 2026-07-05** (black-box, no ROM read;
  [tier2-alloc-order-findings.md](tier2-alloc-order-findings.md) +
  [disk_probe_alloc_order.py](../../probes/disk/disk_probe_alloc_order.py), 7 differential layouts on
  stock+ours). Stock is a **tail-relative contiguity allocator**, not free-order/rover: extending a file
  whose tail cluster is L, it takes **L−1 if free** (walking down: `order4`/`descend4` → 339,338,337,336),
  else the **first free scanning UP from L** (`gap` tail=349, L−1 used → 350, NOT lowest-free 340). Ours =
  global lowest-free-from-2 (no tail bias); agrees with stock only when nothing's free just below the tail.
  Divergence is **cosmetic** (valid FAT12, identical data/free-count). **Recommendation: document & accept**
  (keep `del_realloc` as `kind="divergence"`); full match would rework the core alloc policy for all writes —
  large surface, cosmetic gain. Decision deferred to user; not forced.
- **Verification:** 30/30 unit tests, NO expected-value edits (the 2 test edits are FIXTURE seeding of
  `FAT_ALLOCHINT=2`); new `test_fat_alloc_hint.py` (behaviour-identity vs from-2 incl. holes, invariant,
  reset, O(N), disk-full); Tier-1 16384 B + 0 `k_*` moved; byte-identical to a HEAD ROM on `del_realloc`.

_**Batch-synced 2026-07-04** (consolidation sweep) — the M19→M27 block (20 entries) was
reviewed and moved to [tier2-review-archive.md](tier2-review-archive.md). The Tier-2
DOS-boot-to-`A>` goal is **MET**, full BDOS surface coverage is complete (M26 closed), and
all four post-M26 residuals (LSTOUT characterise+wire, `$2E` VERIFY, M22b slice-2) are
closed. **Nothing is currently open.** A clean-room finding surfaced by the 2026-07-04
whole-target paper-trail audit — a decoded-listing quarantine in tier2-m20-spec.md §11.1 —
was remediated the same pass and logged in
[clean-room-audit.md](../../docs/clean-room-audit.md), not carried as an open item._

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

