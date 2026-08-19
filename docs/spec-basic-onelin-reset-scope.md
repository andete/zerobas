<!-- Copyright (c) 2026 Joost Yervante Damad -->
<!-- SPDX-License-Identifier: 0BSD -->

# D-ONELIN — what disarms `ON ERROR`: reset scope, measured

**Status: ✅ LANDED 2026-07-29. Signed off before implementation; built, gated,
falsified against three rejected builds.**
Sibling of [`docs/spec-basic-oneflg-reset-scope.md`](spec-basic-oneflg-reset-scope.md)
(landed `6ac2285`). Together they close
[`docs/spec-basic-error-handling-s2b-packet.md`](spec-basic-error-handling-s2b-packet.md)
§7, whose `ONEFLG` half is already answered and whose `ONELIN` half is exactly
this slice. Filed defect: [`TODO.md`](../TODO.md), "`CLEAR`/`MAXFILES` inside a
run do not suppress an armed `ON ERROR` handler".

New slice doc rather than an in-place §7 edit, for the same reason D-ONEFLG got
one: §7 is a *question* section in a landed packet, and the answer needs a
measurement table, a falsification log and a wall accounting that would swamp it.
§7 gets a two-line STATUS pointer here, as it already has for `ONEFLG`.

---

## 1. The defect

`10 ON ERROR GOTO 100 : 20 CLEAR : 30 B=SQR(-1)` — the CF-3300/VG-8020 prints
`Illegal function call in 30` (the handler never runs); zerobas traps and runs
the handler. `MAXFILES=1` behaves identically (it ends in `jp clr_done`, i.e. a
verbatim `CLEAR` tail — [`basic/files.asm:1467`](../basic/files.asm:1467)).

It owns three of `chancost-characterize`'s four filed divergences:
`clr_disarm`, `mf_disarm`, and — since S-FCH-2 — `err_badchan`, whose line 20
`MAXFILES=1` is what suppresses its handler on the reference.

---

## 2. The measurement — 14 cases, both machines

⚠️ **Every previously-filed row was CONFOUNDED FOR PLACEMENT.** `error-trap-
acceptance`'s three `reset_scope_*` cases, and the TODO table's rows, all type a
program line *between* the direct-mode arm and the trigger — so "the EDIT
disarmed it" and "`RUN`/`CLEAR` disarmed it" are indistinguishable there. This
battery types the WHOLE program FIRST and arms LAST, so each trigger is measured
alone. Marker rule `100 PRINT"R<";1;">"` (echo yields `";1;"`, output yields `1`)
— a literal-string marker matches its own source echo
([[gate-can-be-green-while-measuring-nothing]]).

`fired` = the handler ran. Batched with a boot-per-case self-heal on every
disagreeing row, so verdicts equal a full boot-per-case run.

| case | what it asks | ref | zerobas |
|---|---|---|---|
| `ctl_goto` | CONTROL: direct-mode arm, nothing in between | **fires** | fires |
| `run_after_arm` | does `RUN` **alone** disarm? | no | no |
| `clear_direct` | does a **direct-mode** `CLEAR` alone disarm? | no | **fires** ❌ |
| `print_direct` | CONTROL: an innocuous direct statement | **fires** | fires |
| `edit_retype` | retype an existing line — same length, nothing moves | no | **fires** ❌ |
| `edit_insert` | insert BEFORE line 10 — the handler line MOVES | no | no ⚠️ |
| `edit_append` | append AFTER line 100 — the handler line does NOT move | no | **fires** ❌ |
| `inrun_clear` | in-run `CLEAR` (the filed row) | no | **fires** ❌ |
| `inrun_ctl` | CONTROL: `REM CLEAR` | **fires** | fires |
| `inrun_rearm` | re-arm at line 25 after the in-run `CLEAR` | **fires** | fires |
| `inrun_dim` | MUST NOT: `DIM Q(50)` | **fires** | fires |
| `inrun_str` | MUST NOT: string-heap traffic | **fires** | fires |
| `stop_cont` | MUST NOT: `STOP` suspension + `CONT` | **fires** | fires |
| `clear_before_arm` | CONTROL: direct `CLEAR` *before* the in-program arm | **fires** | fires |

### 2.1 🔴 The §7 gate rows were VACUOUS — and that is where the wrong lead came from

The three `reset_scope_*` rows in
[`probes/basic/basic_probe_error_trap.py`](../probes/basic/basic_probe_error_trap.py)
were judged on `"R<LEAKED>" in raw`, with a marker line `100 PRINT"R<LEAKED>"`
— **whose own source echo contains that exact string**. The test was TRUE on
every machine, in every build, from the day it landed. Three rows of the standing
error-trap gate had never measured anything.

It was not harmless. The §5d.5 claim that "the reference DOES fire the handler"
on `reset_scope_clear` was read off this vacuous row — and that false reading is
what pointed the filed defect away from the variable-clear rule and toward
`ONELIN`-invalidation-at-relink. **A wrong measurement is worse than none: it
does not merely fail to inform, it actively steers.**

Fixed here: all three moved onto the numeric marker (`PRINT"R<";1;">"`) and
oracle-locked. On the real readout they say **no fire, both machines, all three**
— which is what §3's rule predicts, and which no longer agrees with §5d.5 at all.
Same class as D-ONEFLG's round-1 marker collision
([[gate-can-be-green-while-measuring-nothing]]); the difference is that D-ONEFLG
caught its own within one session, and this one survived an entire arc because
nothing ever forced the row to state an expected value.

⚠️ **`edit_insert` AGREES FOR THE WRONG REASON — it is a second, worse defect.**
zerobas does not disarm there; it takes the trap through a **stale link address
into moved program text** and reports `syntax error in 4850` — a line number that
does not exist. (Reference on the same case: `Illegal function call in 10`.) An
agreeing row was hiding a wild branch; only reading the WHOLE screen showed it
([[read-the-screen-when-a-probe-fails]]).

---

## 3. The rule the reference is following

> **`ON ERROR` is disarmed exactly when the variable table is cleared** — by
> `RUN`, by `NEW`, by `CLEAR` (direct-mode *or* in-run, and so by `MAXFILES`),
> and by **any program EDIT**. Nothing else disarms it.

`inrun_rearm` is what makes this a *disarm* and not a suppression mode: put
`ON ERROR GOTO` back at line 25 and the trap fires again, so the ARM is what got
zeroed. `clear_before_arm` is the same fact from the other side: a `CLEAR` that
runs *before* the arm cannot suppress anything.

### 3.1 What this rules OUT

* 🔴 **`ONELIN` invalidation at relink — the filed hypothesis — is WRONG.** It
  reads `ONELIN` as a resolved link address that the reference invalidates *when
  what it points into moves*. **`edit_append` falsifies it**: appending line 200
  moves nothing (line 100 keeps its address) and the reference disarms anyway.
  `edit_retype` (a same-length retype) says the same. The trigger is the EDIT,
  not the MOVE.
* 🔴 **`clear_vars` is the wrong site**, as TODO.md already warned but for the
  wrong reason. It is not that `RUN` must not disarm — **`run_after_arm` proves
  `RUN` DOES disarm** (unconfounded, no edit in sight), and zerobas already
  agrees. It is that `clear_vars` is *not reached by a program edit* — the edit
  path calls `vars_reset` alone — so a `clear_vars` fix leaves all three
  `edit_*` rows red.
* 🔴 **The claim in [`docs/spec-basic-filechan-alloc.md`](spec-basic-filechan-alloc.md)
  §5d.5 that "`reset_scope_clear` measures a direct-mode `CLEAR` … and the
  reference DOES fire the handler there" is FALSE.** The reference does not fire
  on that case; it disarms at the `10 B=SQR(-1)` edit the case types between the
  arm and the `CLEAR`. The row is green because **both** machines fail to fire,
  for two different reasons. Corrected in place by this slice.
* `DIM`, string-heap traffic, an ordinary direct statement, and a `STOP`
  suspension resumed by `CONT` all keep the handler — so the disarm must not
  live in `ary_reset`, `heap_reset`, or anything on the statement path.

---

## 4. The fix — ONE site, net **0 bytes**

`vars_reset` ([`basic/arrays.asm:285`](../basic/arrays.asm:285), low region
`$3D6B`) is exactly the routine the reference's rule names: "the variable world
was reset". Its call sites are, in full:

| caller | reached by |
|---|---|
| `new_prog` ([`basic/program.asm:285`](../basic/program.asm:285)) | `NEW`, cold `init`, `LOAD` |
| `run_prog` ([`basic/program.asm:300`](../basic/program.asm:300)) | `RUN` |
| `clr_done` ([`basic/clear.asm:93`](../basic/clear.asm:93)) | `CLEAR` — and `MAXFILES`, via `jp clr_done` |
| `relink` ([`basic/lineedit-body.inc:217`](../basic/lineedit-body.inc:217), and the sub-ROM tenant [`sub/lineedit.asm:642`](../sub/lineedit.asm:642)) | every program EDIT, `MERGE`, `CLOAD`/`LOAD` |

That set is the measured set, 1:1. So the fix is not an addition — it is a
**MOVE**: `run_prog`'s existing `ONELIN:=0` goes down into `vars_reset`, where
the other four callers pick it up.

```asm
vars_reset:
                ld      hl,0
                ld      (ONELIN),hl         ; D-ONELIN: clearing the variable world
                call    heap_reset          ; disarms ON ERROR -- RUN/NEW/CLEAR/
                ...                         ; MAXFILES/EDIT all funnel through here
```

and `run_prog` ([`basic/program.asm:319`](../basic/program.asm:319)) loses its
now-redundant `ld hl,0 / ld (ONELIN),hl` (6 B), since it calls `vars_reset` a few
instructions earlier.

* **Gating:** none needed. `basic/arrays.asm` is repack-only wholesale (every
  byte inside `IF ROM_BASE < $4000` — [`basic/main.asm:84`](../basic/main.asm:84)),
  and the lean 16 KB build has no `ON ERROR` at all. `tools/check_reloc.py`'s
  byte-identity check is the gate on that claim, not this paragraph.
* **The sub-ROM tenant gets it for free.** `sub/lineedit.asm` calls `vars_reset`
  in-slot (it is low-region resident, page 0 is always mapped), so a repack-build
  program edit — which runs the *tenant's* relink — disarms without a marshalling
  change. No sub-ROM byte moves.
* **`init` keeps its explicit `ONELIN:=0`** ([`basic/interp.asm:52`](../basic/interp.asm:52)).
  It is reachable-redundant (init → `new_prog` → `jp vars_reset`), but that
  redundancy rests on an ordering invariant documented three routines away, and 3
  bytes of page 1 is not worth resting a power-on-RAM-garbage guarantee on.

### 4.1 Wall accounting — AS-BUILT

Both readings from a clean `rm -rf build && make basic-reloc`
([[measure-the-wall-from-clean]]).

| | low region | page 1 |
|---|---|---|
| at `6ac2285` (before) | 6 B free | 5 B free |
| `vars_reset` gains `ld hl,0` + `ld (ONELIN),hl` | **+6 B** | — |
| `run_prog` drops the same two instructions | — | **−6 B** |
| **AS-BUILT after** | **0 B free** | **11 B free** |

Predicted exactly. `check_reloc.py` confirms the lean 16 KB `basic.rom` is
**byte-identical** (no gating needed: `basic/arrays.asm` is repack-only
wholesale, and the lean build has no `ON ERROR`).

Net zero. ⚠️ **The walls REBALANCE, they do not grow** — but low goes to 0 B free
and becomes the hard blocker for the next slice. That is a *transfer* of the
existing block, not a new one (both walls were already too tight to fund
anything). If a low byte is needed later, page 1 and the low region are co-mapped
slot-0 pages, so a small leaf can be relocated between them without a shim.

---

## 5. The gate — `onelin_*`, added to the standing error-trap gate

Eight new rows in [`probes/basic/basic_probe_error_trap.py`](../probes/basic/basic_probe_error_trap.py),
straight differential against the VG-8020, each judged on the marker:

Fourteen rows, each oracle-locked to the reference's own measured answer (so a
row that starts reading differently trips the gate instead of quietly redefining
the target), plus the three repaired `reset_scope_*` rows.

**Must disarm** (4, red before the fix): `onelin_clear_direct`,
`onelin_edit_retype`, `onelin_edit_append`, `onelin_inrun_clear`.
**Must NOT disarm** (5 — the load-bearing half, [[oneflg-reset-scope-slice]]):
`onelin_print_direct`, `onelin_inrun_dim`, `onelin_inrun_str`,
`onelin_stop_cont`, `onelin_clear_before_arm`, and `onelin_inrun_rearm` (a
re-arm restores the trap, which is what makes this a *disarm* and not a
suppression mode).
**Controls** (3): `onelin_ctl_goto`, `onelin_inrun_ctl`, `onelin_run_arm` — the
last one carries the fact that `RUN` disarms, unconfounded, which is what
licences reclaiming `run_prog`'s write.

Plus `onelin_edit_insert` judged on the **abort line number**, not the marker —
the one row that catches the stale-pointer wild branch (§2) and that a
marker-only comparison scores as agreement.

`chancost-characterize` loses three `KNOWN_DIVERGE` entries (`clr_disarm`,
`mf_disarm`, `err_badchan`), leaving one (`lof_new`) — 39 cases, 1 filed
divergence.

### 5.1 Falsification — AS-RUN, three builds

Every build below was assembled, installed and measured boot-per-case. Only the
rows that changed are listed; everything else stayed green.

| build | red rows | reading |
|---|---|---|
| **pre-fix baseline** (`6ac2285` sources) | `clear_direct`, `edit_retype`, `edit_append`, `inrun_clear`, `edit_insert` | 5 red / 9 green. The gate is **not vacuous** — it fails on the code it was written for. |
| **REJECT A** — the write in `clear_vars` instead | `edit_retype`, `edit_append`, `edit_insert` | The CLEAR half goes green and **the whole EDIT half stays red**. This is the placement TODO.md's text steered toward; it would have shipped two-thirds of the defect plus the wild branch. |
| **REJECT B** — the write at the edit path only (`store_line`) | `run_arm`, `clear_direct`, `inrun_clear` | The exact mirror: edits fixed, `CLEAR` untouched. **And `run_arm` goes red** — which is the proof that `vars_reset` is genuinely what covers `RUN` after `run_prog`'s own write was reclaimed, rather than the reclaim being a lucky no-op. |

⚠️ REJECT B's first attempt was built WRONG and would have failed for the wrong
reason: inserting `ld hl,0` before `ld (SL_TOK),hl` clobbers the token-body
pointer `store_line` was called with. A rejected build has to be a *correct*
implementation of the rejected idea, or it refutes nothing.

The site→row map is 1:1 in both directions: the `CLEAR` rows and the `EDIT` rows
are separable, and only a placement that covers both — `vars_reset` — turns all
five green at once.

---

## 6. Regression surface — AS-RUN

* `reset_scope_*` — see §2.1: they were vacuous, are now on a real marker, and
  read "no fire, both machines" on all three. Green for a reason now.
* Nothing relies on a handler surviving a `CLEAR`; the `resume_*` and `oneflg_*`
  families arm and trap inside one run. All seven `oneflg_*` rows still pass,
  including both "must NOT clear" guards.
* `chancost-characterize` drops from **4 filed divergences to 1**: `err_badchan`,
  `mf_disarm` and `clr_disarm` all now agree, leaving only `lof_new`.
* `LOAD`/`CLOAD`/`MERGE` now disarm (they relink). Consistent with the rule and
  with the reference's documented "LOAD clears variables", but **not measured
  here** — it needs a disk/tape fixture. Recorded as an assumption, not a claim.
* One row flaked once in a shared boot (`onelin_stop_cont`, a case that suspends
  and resumes a run has two extra REPL round trips to race). The ONELIN block
  therefore runs through `run_differential`'s self-heal, so a flake costs one
  pair of boots instead of a red gate. Boot-per-case: 14/14, three times over.
* Full gate list in §8, all RUN.

### 6.1 Found, NOT fixed here (one TODO item per session)

**`CONT` that runs off the end of the program aborts with a nonexistent line.**
`10 STOP : 20 B=1 : 30 PRINT"…"` then `RUN`, `CONT` — the reference resumes,
prints, and returns to `Ok`; zerobas prints, then reports
`Illegal function call in 3346`. **Verified PRE-EXISTING at `6ac2285`** by
re-running it against the parked pre-fix build, not assumed. No `ON ERROR` is
involved (`ONELIN` is 0 throughout), so it is not this slice's. Filed in
[`TODO.md`](../TODO.md) next to its two siblings from the D-ONEFLG battery
(`CONT` after a plain `END`; ERR 21 `No RESUME` never raised) — the three look
like one cluster around what the run loop leaves behind at its exit.

---

## 7. Sign-off — ANSWERED 2026-07-29, before implementation

1. **Placement** — `vars_reset`, on the measured rule, **accepting low → 0 B
   free**. ✅ Signed off. Rejected: three sites across page 1 + sub-ROM (more
   bytes, more places to forget), and rebalancing the walls in the same slice
   (an unrelated relocation mixed into a behavioural fix).
2. **`init`'s explicit `ONELIN:=0`** — KEPT (3 B). Reachable-redundant via
   `init → new_prog → jp vars_reset`, but that redundancy rests on an ordering
   invariant documented three routines away, and 3 bytes is not worth resting a
   power-on-RAM-garbage guarantee on.
3. **`edit_insert`'s wild branch** — folded into this slice, gated on the abort
   **line number** rather than the marker. ✅ Signed off.

⚠️ **The low region is now the hard blocker at 0 B free.** That is a *transfer*
of the existing block, not a new one — page 1 went 5 → 11 B and both walls were
already too tight to fund a slice. Page 1 and the low region are co-mapped
slot-0 pages, so if a low byte is needed, a small leaf can be relocated between
them without a shim; that is the cheap move, ahead of any carve.

---

## 8. Gates

`make unit-test` · `make error-trap-acceptance` (incl. the new `onelin_*`) ·
`make abort-acceptance` · `make stop-trap-acceptance` · `make linemax-acceptance` ·
`make arrdim-acceptance` · `make clearpool-acceptance` · `make diskbasic-acceptance` ·
`make bdos-acceptance` · `make fat-error-acceptance` · `make chancost-characterize` ·
`make array-acceptance` (149/151, the two `ifc.instr.*` capitalisation rows are the
standing baseline — confirmed BY NAME) · clean `make basic-reloc`.

## 9. Clean-room

No reference-ROM disassembly. The rule in §3 is stated from black-box
observation of a Philips VG-8020 through the KEYBUF-injection REPL driver only;
the implementation is zerobas's own `vars_reset`, and the change is a
relocation of zerobas's own existing instruction.
