<!-- Copyright (c) 2026 Joost Yervante Damad ; SPDX-License-Identifier: 0BSD -->
# D-ONEFLG — the stale in-handler flag: reset scope, measured

**Status: ✅ LANDED 2026-07-29 — signed off, built, gated, and each site
individually falsified.** §4.1 and §5.1 carry the as-built numbers; the spec
below is unchanged from sign-off except where marked AS-BUILT.
Owns filed defect (2) of [`docs/spec-basic-filechan-alloc.md`](spec-basic-filechan-alloc.md)
§5d, and closes the open half of
[`docs/spec-basic-error-handling-s2b-packet.md`](spec-basic-error-handling-s2b-packet.md)
§7 (`ONEFLG`; the `ONELIN` half stays open as defect (1)).

## 1. The defect

`ONEFLG` ($E1CA) means *"execution is currently inside an `ON ERROR` handler with
no intervening `RESUME`"*. `raise_error_hl` sets it to 1 when it takes the trap,
and reads it to decide **trap vs forced abort**
([`basic/interp.asm:872`](../basic/interp.asm:872)). It is written back to 0 at
exactly four places today: `run_prog` (RUN,
[`basic/program.asm:332`](../basic/program.asm:332)), cold `init`
([`basic/interp.asm:65`](../basic/interp.asm:65)), `ON ERROR GOTO 0`
([`basic/program.asm:2131`](../basic/program.asm:2131)) and the `RESUME` family
([`basic/interp.asm:1299`](../basic/interp.asm:1299),
[`:1166`](../basic/interp.asm:1339)).

**Nothing on the abort path clears it, and nothing on any run-termination path
clears it.** So every re-entry that is not a fresh `RUN` — `GOTO <line>`,
`GOSUB`, a direct `RESUME` — inherits a stale 1 and force-aborts the next error
instead of trapping it.

## 2. The measurement — 10 cases, both machines, boot-per-case

Driven through [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py) (KEYBUF
injection), reference = Philips VG-8020, subject = `C-BIOS_MSX1_EU_REPACK_DISK`
at `6d2569b`. Two readout shapes:

* **re-entry** — after the run under test, a direct `GOTO 200` into
  `200 ON ERROR GOTO 300 : 210 B=SQR(-1) : 300 PRINT"R<";1;">"`. The re-arm at
  200 makes `ONELIN` fresh, so the *only* thing that can decide trap-vs-abort is
  `ONEFLG`. Marker printed ⇒ trapped; `illegal function call in 210` ⇒ aborted.
* **direct `RESUME`** — reads `ONEFLG` head-on: `RESUME without error` ⇒
  `ONEFLG` is already 0.

⚠️ **Round 1 of this battery used `300 PRINT"R<TRAP>"` and its own SOURCE ECHO
matched the scrape** — a force-aborted case still read `R<TRAP>` off the typed
line and scored as a trap. Round 2 switched to the corpus convention
`PRINT"R<";1;">"`, whose echo yields the artifact `";1;"` and whose output
yields `1`; the two can never be confused. This is the same class as
[[clearpool-slice]]'s wrapping echo — *the readout is part of the measurement*.

| # | shape | reference | zerobas | |
|---|---|---|---|---|
| c1 | nested forced abort → re-arm + re-raise | **traps** | **force-aborts** | ❌ |
| c2 | control: same program, no prior error at all | traps | traps | ✅ |
| c3 | handler `END`s the run → re-arm + re-raise | **traps** | **force-aborts** | ❌ |
| c3b | handler falls off the end of the program → direct `RESUME` | `No RESUME in 100`, then `RESUME without error` | *silent*, then resumes line 20 | ❌ |
| | *(post-D-ERR21, 2026-07-31: zerobas now prints `no resume in 100` then `resume without error` — both halves match, and the row is a full text differential)* | | | ✅ |
| c3c | handler `END`s the run → direct `RESUME` | `RESUME without error` | resumes line 20 | ❌ |
| c4b | `STOP` in handler → `CONT` → `RESUME 120` | reaches 120 | reaches 120 | ✅ |
| c5 | nested forced abort → direct `RESUME` | `RESUME without error` | re-raises in 100 | ❌ |
| c6 | `STOP` in handler → re-arm + re-raise | **force-aborts** | force-aborts | ✅ |
| c8 | `STOP` → `CONT` → `END` → re-arm + re-raise | traps | **force-aborts** | ❌ |
| c10 | `STOP` in handler → a DIRECT erroring line → `CONT` → `RESUME` | `RESUME without error in 110` | reaches 120 | ❌ |

## 3. The rule the reference is following

Two facts, and c6/c4b/c10 are what pin them apart:

1. **Any abort clears `ONEFLG`** — run-mode (c1, c5) *and* direct-mode, even
   while a run is merely suspended (c10: a typed `PRINT 1/0` between the Break
   and the `CONT` is enough to kill the handler context, and the reference then
   reports `RESUME without error in 110` from inside the resumed handler).
2. **Ending the run clears it; suspending the run does not.** An `END` inside
   the handler clears (c3, c3c). A `STOP`/Ctrl-STOP does **not** (c6: a direct
   re-entry after a Break still force-aborts on *both* machines; c4b: the
   handler's own `RESUME` still works after `CONT`). That asymmetry is not
   incidental — `CONT` has to be able to continue *inside* the handler.

c3b shows the reference's third termination path is itself an abort: falling off
the end of the program while inside a handler raises ERR 21 **`No RESUME`**,
which zerobas does not raise at all (§7, newly filed).

### 3.1 What this rules OUT

* **"Clear at the prompt / at every direct line"** — falsified by c6 and c4b.
* **"Clear at the run-loop exit"** — the `ENDFLAG` exit
  ([`basic/program.asm:467`](../basic/program.asm:467)) is shared by `END` and
  the `STOP` statement, and c6 says those two must differ.
* **"Clear at the run-loop exit gated on `CONTVALID`"** — this *does* reproduce
  every measured row, in 8 B at a single site, and it was the leading candidate.
  **Rejected**: it works only because zerobas's `END` leaves no CONT resume
  point, and c7 shows that is itself a divergence (VG-8020: `CONT` after a plain
  `END` **continues**; zerobas: `can't continue`). Building this fix on a known
  divergence means the day that one is fixed, this one silently regresses. The
  rule above is `CONTVALID`-independent.

## 4. The fix — three sites, ~12 B, no carve

All three are inside existing `IF ROM_BASE < $4000` regions or become one, so the
lean 16 KB `basic.rom` stays byte-identical and **no label aliasing or call-site
gating is needed** (contrast the S-FCH-2 trick).

**Site A — the abort funnel**, `fre_abort_low`
([`basic/arrays.asm:94`](../basic/arrays.asm:94), low region, repack-only
wholesale). It already does `xor a` / `ld (PRDEST),a`; add one store:

```
                xor     a
                ld      (ONEFLG),a          ; §3 rule 1: an abort ends the handler
                ld      (PRDEST),a
```

**3 B, low region.** Unconditional — **not** gated on `DIRECTF`, which is exactly
what c10 measures. Covers all ten `jp fre_abort_low` sites; the raisers that
never set the flag store an already-0 value, which is a no-op.

**Site B — `ex_end`** ([`basic/interp.asm:505`](../basic/interp.asm:505), page 1):

```
ex_end:
    IF ROM_BASE < $4000
                xor     a                   ; §3 rule 2: END TERMINATES the run,
                ld      (ONEFLG),a          ; so the handler context dies with it
                inc     a
    ELSE
                ld      a,1
    ENDIF
                ld      (ENDFLAG),a
                ret
```

**+3 B, page 1.** `ex_stop` does not come through here
([`basic/interp.asm:384`](../basic/interp.asm:384) dispatches it separately), so
the c6/c4b asymmetry is structural rather than a test.

**Site C — falling off the end of the program** — 🔴 **DELETED 2026-07-31 by
D-ERR21** ([`docs/spec-basic-err21-no-resume.md`](spec-basic-err21-no-resume.md)
§2.2/§3.1). It is redundant with site A once the fall-off with `ONEFLG` **set**
raises ERR 21 (which aborts through `fre_abort_low`, i.e. site A), and on the
arm that survives `ONEFLG` is already 0. **It was also causing a defect of its
own that this spec's battery never measured:** a *typed* line ends by falling
through `dir_line`'s own `$0000` link into this very exit, so site C silently
killed the handler context on every benign direct line at a `Break in <handler>`
prompt — the reference keeps it. `oneflg_falloff` now holds down site A here,
and the new `e21_typed`/`e21_ctl_typed` pair holds down the absence of the
clear. As filed, the site read:

`rp_lp`'s `$0000`-link exit
([`basic/program.asm:338`](../basic/program.asm:338), page 1). **AS-BUILT — 1 B
cheaper than specced, and the reason is worth keeping:** the branch is taken
exactly when `A` (which holds `d|e`) is zero, so the clear needs **no `xor a`
and no out-of-line tail**:

```
                ld      a,d
                or      e
    IF ROM_BASE < $4000
                jr      nz,rp_notend
                ld      (ONEFLG),a          ; A is ALREADY 0 on this arm
                ret
rp_notend:
    ELSE
                ret     z                   ; $0000 link -> end of program
    ENDIF
```

**+5 B, page 1** (specced 6 with a `jr z,rp_endprog` + out-of-line tail — which
would additionally have been a long-jump risk: a throwaway variant of this site
that grew the run loop by 5 B in a different spot pushed an *unrelated* `jr` at
[`basic/program.asm:550`](../basic/program.asm:550) out of range).

### 4.1 Wall accounting — AS-BUILT

Clean `rm -rf build && make basic-reloc` at `6d2569b`: **page 1 13 B free, low
region 9 B free.** Estimate was page 1 −9, low −3. **Measured: page 1 −8 → 5 B
free, low −3 → 6 B free** (11 B total, one under estimate — Site C's free `A=0`).
`tools/check_reloc.py` confirms the lean 16 KB `basic.rom` byte-identical.
No carve and no promotion was needed. **Both walls are now very tight (5 / 6).**

## 5. The gate — `oneflg_*`, added to the standing error-trap gate

Seven rows in [`probes/basic/basic_probe_error_trap.py`](../probes/basic/basic_probe_error_trap.py)
(`make error-trap-acceptance`), modelled on `NESTED_ABORT` / `RESET_SCOPE_CASES`.
Each row names the site it holds down, so a later carve cannot quietly remove one:

| row | shape | holds down | falsified by |
|---|---|---|---|
| `oneflg_stale` | c1 | Site A | reverting A → force-aborts |
| `oneflg_ctl` | c2 | the two-sidedness (no prior error ⇒ traps anyway) | — |
| `oneflg_direct_resume` | c5 | Site A, read head-on | reverting A |
| `oneflg_end` | c3 | Site B | reverting B → force-aborts |
| `oneflg_falloff` | c3b — ⚠️ **now a full TEXT differential** (D-ERR21) | Site A (was Site C, deleted) | reverting A |
| `oneflg_keep` | c6 | **over-clearing** — must still force-abort | any prompt/loop-exit placement |
| `oneflg_suspend_resume` | c4b | over-clearing from the `CONT` side | clearing at `ex_cont`/loop exit |

`oneflg_keep` and `oneflg_suspend_resume` are the rows that make the *placement*
load-bearing rather than the *existence* of a clear: a fix that simply zeroes
`ONEFLG` at the prompt passes the first four and fails these two.

`oneflg_falloff` **was** deliberately not a text differential: the reference
printed `No RESUME in 100` before its `RESUME without error` and zerobas printed
nothing (§7's filed gap), so the row gated only the `RESUME` response. 🔴 **That
reason expired on 2026-07-31 — D-ERR21 raises it, and the row now compares BOTH
lines on BOTH machines** (case-folded; zerobas is house-style lowercase).
`oneflg_direct_resume` compares error **classes**, never wording — zerobas's
messages are house-style lowercase (D-2).

**Falsification is by DELETING each site and re-running**, not by argument
([[gate-can-be-green-while-measuring-nothing]]).

### 5.1 Falsification — AS-RUN, four builds

Each site was deleted on its own, rebuilt from clean, re-installed and re-run.
**The site→row map is 1:1 — every deletion turned red exactly the rows attributed
to it, and nothing else:**

| deleted | rows that went red |
|---|---|
| Site A (abort funnel) | `oneflg_stale`, `oneflg_direct_resume` |
| Site B (`ex_end`) | `oneflg_end` |
| Site C (fall-off) | `oneflg_falloff` |

A fourth build tested the **rejected placement** rather than a missing one: an
unconditional `ld (ONEFLG),a` at `dl_cmd` (i.e. "clear at the prompt"), with all
three real sites still in place. It passed **all five** must-clear rows and
failed **exactly** `oneflg_keep` and `oneflg_suspend_resume`. §5's claim that
those two rows are what make the *placement* load-bearing is therefore measured,
not asserted.

⚠️ **The first attempt at that fourth build FAILED TO ASSEMBLE and the probe ran
anyway, against the previous machine** — the run looked like a dramatic result
(five rows red) and was pure noise. [[stale-machine-reads-as-unimplemented]],
[[ips-rebuild-after-basic-change]]: chain the build and the probe with `&&`, or a
broken build reads as a behavioural finding.

## 6. Regression surface

`make error-trap-acceptance` (incl. `nested_forced_abort`, `resume_*`,
`reset_scope_*`), `make unit-test`, `make abort-acceptance`,
`make stop-trap-acceptance`, `make linemax-acceptance`, `make arrdim-acceptance`,
`make clearpool-acceptance`, `make array-acceptance` (149/151 standing — the two
`ifc.instr.*` rows confirmed BY NAME), `make diskbasic-acceptance`,
`make bdos-acceptance`, `make fat-error-acceptance`, `make chancost-characterize`.
Site A sits in the abort funnel every runtime error in the corpus passes through,
so the whole error surface is the regression surface.

## 7. Newly filed, NOT fixed here (one TODO item per session)

1. **ERR 21 `No RESUME` is never raised.** A program that runs off the end while
   inside a handler must abort with `No RESUME in <line>` (VG-8020, c3b);
   zerobas ends the run silently. The code exists in `err_msgtab`; the raiser
   does not. ✅ **FIXED 2026-07-31 as D-ERR21,**
   [`docs/spec-basic-err21-no-resume.md`](spec-basic-err21-no-resume.md).
   ⚠️ `err_msgtab`'s entry 21 was a HOLE pointing at `err_unprintable`, not a
   working entry — `ERROR 21` printed the wrong message too. And the line named
   is the **last executed** one, not the handler's (§2 c3b could not see the
   difference: its handler line was also its last line).
2. **`CONT` after a plain `END` must continue.** VG-8020 resumes at the
   statement after `END` (c7); zerobas reports `can't continue`. The comment at
   [`basic/program.asm:683`](../basic/program.asm:683) asserts the opposite as
   fact and is wrong — `END` records a resume point on the reference.

Both are independent of this fix and neither is touched by it.

## 8. Sign-off — ANSWERED 2026-07-29

1. **Placement** — *3 sites, measured rule.* The `CONTVALID`-gated single site
   (8 B, 1 site) was rejected for coupling to the `CONT`-after-`END` divergence
   (§3.1, §7.2).
2. **Overrun policy** — *land A+B+C and re-scout page 1 if over.* It did not
   overrun: 11 B against 13 + 9 free (§4.1).
3. **`oneflg_falloff`** — *keep as a zb-only row*, gating the `RESUME` response
   only, with the missing ERR 21 filed separately (§7.1). **(SUPERSEDED
   2026-07-31: §7.1 landed, so the row is now a full two-machine text
   differential.)**

## 9. Clean-room

Every fact in §2 and §3 is **black-box observed behaviour** of a Philips VG-8020
under the published-sysvar KEYBUF driver — an allowed source
([`docs/allowed-sources.md`](allowed-sources.md), the same oracle-capture basis
as the rest of the error-handling arc). No reference ROM was disassembled and no
reference sysvar layout was consulted: `ONEFLG` is zerobas's own cell at its own
address, and *where* zerobas clears it (`fre_abort_low` / `ex_end` / `rp_lp`) is
own code chosen to reproduce the measured behaviour, not a mirror of the
reference's internal structure. The §3 rule is a description of what the machine
does, derived from the ten cases in §2 and from the three that discriminate
between candidate rules (c6, c4b, c10). Message wording is untouched by this
slice and keeps its existing house-style status (D-2).
This section is the provenance record for the slice; `basic/PROVENANCE.md` has no
error-handling chapter to extend.
