# D-LNBLANK — blanks inside a line number

> **STATUS: SPEC, AWAITING SIGN-OFF.** Nothing under `basic/` has been edited.
> The rule this spec will pin is **not yet known**; §3 lists what will be
> measured and §5 lists the *candidate* fixes, deliberately undecided.

Filed item: [`TODO.md:3251`](../TODO.md:3251) — "Line-number scan does not skip
embedded blanks", found 2026-07-29 as a **failing two-sided control** inside
D-LINEMAX's `tok` battery ([`spec-basic-linemax.md`](spec-basic-linemax.md),
[`basic_probe_linemax.py:139`](../probes/basic/basic_probe_linemax.py:139)).

```
typed:      20 0#0#0#0#0#
VG-8020 ->  line 200, body = 0x23 ('#') + four double literals
zerobas ->  line 20,  body = five double literals
```

## 0. What is actually filed, and what is not

The filed row is **one input**. It establishes that on the VG-8020 the leading
line-number scan crossed a blank and kept accumulating (`20` + ` ` + `0` = 200),
and that zerobas stopped at the blank. It establishes **nothing** about:

* whether the reference skips *one* blank or *any run* of blanks;
* whether the blank must be *between* digits, or may precede the first one;
* whether a **tab** behaves like a space;
* where the **body** then starts — the filed row shows the body changing too,
  and that is a second axis (`20␣␣REMX`: does the reference keep one blank in
  the crunched body, or eat them all as zerobas does?);
* whether the accumulator can be walked **past 65529** through blanks;
* whether a line-number **reference inside a statement** (`GOTO 1 0`) obeys the
  same rule — that is a *different code path*
  ([`basic/tokenise.inc:444`](../basic/tokenise.inc:444) `branch_lineno`), and
  the TODO says in as many words to check rather than assume;
* whether the rule is a property of the **line-number scan** at all, or of the
  machine's **number scanner in general** (`A=1 0`) — which changes the size of
  the fix by an order of magnitude;
* whether the two reference machines even **agree with each other**.

That last one is why this slice runs **two oracles** (§2.1).

## 1. The sites, re-verified 2026-07-31

The line numbers in the filed TODO text have drifted; these are current.

| # | site | role |
|---|---|---|
| P1 | [`basic/program.asm:30`](../basic/program.asm:30) `dispatch_line` | decides "leading digit → numbered line" (after `skip_spaces`) |
| P2 | [`basic/program.asm:200`](../basic/program.asm:200) `parse_lineno` | **the accumulator**. `pl_lp` does `cp '0' / ret c / cp '9'+1 / ret nc` — it RETURNS on the first non-digit, so a blank terminates it. This is the defect site. |
| P3 | [`basic/files.asm:1593`](../basic/files.asm:1593) `mrg_storeline` | ASCII `LOAD`/`MERGE`. **Calls `dispatch_line`**, so it inherits P1+P2 by construction — but "by construction" is a claim, and §3.4 pins it with a row. |
| P4 | [`basic/tokenise.inc:444`](../basic/tokenise.inc:444) `branch_lineno` / `bl_acc` | **different code, different question**: the crunch-time line-number REFERENCE after `GOTO`/`GOSUB`/`THEN`/`RESTORE`/`RUN`/`RESUME`. `bl_acc` has its own copy of the same `cp '0' / jr c,bl_done` idiom. |

Two facts about P4 that matter for the row design:

* `bl_yes` copies blanks *before* the number **verbatim** into the crunched
  output, then `bl_acc` accumulates. So a blank *inside* the number would, under
  a skip-blank rule, be **dropped** from the stored bytes rather than copied.
  Whether the reference drops it is directly visible in the capture.
* zerobas emits `$0E` only for those six keywords. `LIST` / `DELETE` / `AUTO` /
  `RENUM` are **not** in `bl_yes`'s list, so their arguments crunch as ordinary
  numeric literals today. §3.3 measures what the reference does there; see §7
  for why a divergence found there is *filed*, not fixed, in this slice.

## 2. The measurement

### 2.1 Two oracles, not one

Every row is asked of **both** reference machines:

* **`Philips_VG_8020`** — the machine that produced the filed row. No disk.
* **`National_CF-3300`** — the Disk BASIC oracle
  ([`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md)).

This is not redundancy. A rule that both machines share is a property of
**MSX-BASIC**, which is what zerobas is a faithful implementation *of*; a rule
only one shows is a property of *that ROM*, and copying it would be a mistake
this project has no way to detect from a single oracle. The whole slice rests
on a single filed row from a single machine, and the cheapest way to find out
whether that row generalises is to ask a second machine before writing any code.

CF-3300 apparatus notes (from [`diskbasic_probe_chancost.py:96`](../probes/disk/diskbasic_probe_chancost.py:96)):
it has a **boot date prompt** (answered with a bare CR emitted as part of
`reset`), boots slower (12 s), and boots to **SCREEN 1**. The last one costs us
nothing here — this probe's readout is **memory, not screen** — which is
precisely why a second oracle is affordable at all.

### 2.2 The instrument

`("stored_line", TXTTAB)` — [`omsx_repl.py:277`](../probes/lib/omsx_repl.py:277)
`__hex_line` dereferences `TXTTAB` ($F676) and returns the **exact bytes of the
first stored line** (link, line number, crunched body, terminator), using the
link word for the extent so an embedded `$00` never truncates it. This is the
instrument that found the defect, and it is the only one that can tell
"different line number" from "different body" — the filed row differs in *both*.

Three distinct readings, never folded together:

| reading | means |
|---|---|
| `line N …` + body bytes | the line was stored; both fields are compared **byte-exact** |
| `REFUSED (empty program)` | the line was rejected on entry (`""`) |
| `NOCAPTURE` / `TIMEOUT` | the apparatus failed — **fatal**, never `agree` |

It dereferences `TXTTAB` rather than assuming `$8001`, so the CF-3300's
disk-shifted text base needs no special case.

### 2.3 Guards — ported, not invented

The recurring trap this project keeps re-learning is that a green row can be
green for a reason that has nothing to do with the machine. Three guards, the
first two ported from [`diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py):

1. **`NOCAPTURE` / `TIMEOUT` are distinct fatal sentinels, not `None`.** Two
   sides that both failed to run compare EQUAL and would print `agree`. Any row
   carrying one suppresses **every** derived number in the run.
2. **An echo guard.** A dropped keystroke changes the stored bytes and looks
   exactly like a semantic divergence. A separate screen-capture pass over the
   same payloads asserts each typed line is on screen verbatim; a `MANGLED` row
   is fatal for the run. ⚠️ This calibrates the *cadence*; it does not certify
   the specific boot that produced a memory reading — which is why guard 3 exists.
3. **⚠️ REPEAT=2 ON EVERY REFERENCE PASS, and this one is not optional.**
   The oracle-lock step writes the reference's answers down as the oracle. A
   mangled reference row there does not fail loudly — it becomes a **wrong
   oracle** that every later run agrees with. So each reference battery runs
   **twice, on two independent boots**, and any row whose two readings differ is
   `UNSTABLE` and fatal. (In the *differential* direction a mangle mostly
   produces a false FAIL, which is loud and safe; in the *oracle-lock*
   direction it produces a false PASS forever. The two directions do not
   deserve the same guard.)

### 2.4 Order of work — oracle-lock BEFORE zerobas is run

The two-step method that worked in D-MFDOM and D-RNDDIR:

* **Step 1 (commit).** Probe + both references only. Results written to
  [`docs/lnblank-msx1-characterization.md`](lnblank-msx1-characterization.md)
  and committed **before zerobas is run even once**, so no oracle can be
  back-fitted to what zerobas happens to do.
* **Step 2 (commit).** Run zerobas against the locked oracle; record which rows
  diverge and *why*, unfixed.
* **Step 3 (commit).** The fix + the gate + the falsification.

## 3. The battery — the denominator

Payload convention: `REMX` bodies, because `REM` keeps its tail verbatim on both
machines (the same property [`basic_probe_linemax.py:36`](../probes/basic/basic_probe_linemax.py:36)
relies on), so the body is trivially readable in hex.

Two competing rules are named throughout:

* **rule T** (*terminate*) — the scan ends at the first non-digit. This is
  zerobas today.
* **rule S** (*skip*) — blanks are transparent to the scan; it ends at the first
  non-digit, non-blank.

**Rows are chosen so T and S predict different bytes.** A row where they predict
the same bytes is labelled a **control** and is pinned *because* it agrees —
that is what caught the shipped regression in D-BADFNUM.

### 3.1 `num` — the leading line number (P1/P2)

| label | typed | T predicts | S predicts |
|---|---|---|---|
| `num-plain` | `20 REMX` | line 20, `REM X` | same — **control** |
| `num-nospace` | `20REMX` | line 20, `REM X` | same — **control** |
| `num-stop` | `2 X=1` | line 2, `X=1` | same — **control** (a letter stops both; [`basic_probe_linemax.py:145`](../probes/basic/basic_probe_linemax.py:145) already asserts this) |
| `num-blank1` | `2 0 REMX` | line **2**, body `0`+` `+`REM X` | line **20**, `REM X` |
| `num-blank2` | `2  0 REMX` | line 2 | line 20 *if any run of blanks is transparent* |
| `num-blank3` | `2 0 0 REMX` | line 2 | line 200 |
| `num-lead` | `␣20 REMX` | line 20 | line 20 — **control** (`dispatch_line` already `skip_spaces`) |
| `num-filed` | `20 0#0#0#0#0#` | the **filed row**, reproduced verbatim |
| `num-mid` | `20 0REMX` | line 20, `0`+`REM X` | line 200, `REM X` |
| `num-body1` | `20␣␣REMX` | body starts at `REM` | **body-offset axis**: does either machine keep a blank? |
| `num-body2` | `20␣␣␣REMX` | ditto, three blanks |
| `num-zero` | `0 REMX` | line 0 | line 0 — **control** |
| `num-max` | `6 5 5 2 9 REMX` | line 6 | line 65529 (the documented ceiling) |
| `num-over` | `6 5 5 3 0 REMX` | line 6 | 65530 — **past** the documented range: accepted, or refused? |
| `num-huge` | `9 9 9 9 9 REMX` | line 9 | 99999 — wraps (`parse_lineno` is unguarded) or refuses? |
| `num-tab` | `2<TAB>0 REMX` | ⚠️ **informational, non-gating.** The MSX line editor may expand TAB *in the input buffer*, in which case this row measures the editor, not the scan. Reported with that caveat either way. |
| `num-only` | `20 REMY` then `2 0` | S deletes line 20 → `REFUSED (empty program)`; T deletes the non-existent line 2 → `line 20 REM Y` survives. **The crispest separator in the battery** — the two rules produce not just different bytes but different *program lengths*. |

### 3.2 `lit` — is it the line-number scan, or the number scanner?

The structural question, and the one that sizes the fix.

| label | typed | T predicts | S predicts |
|---|---|---|---|
| `lit-ctl` | `20 A=10` | one literal `10` | same — **control** |
| `lit-assign` | `20 A=1 0` | literal `1`, blank, literal `0` | one literal `10` |
| `lit-print` | `20 PRINT 1 0` | ditto | ditto |

If these come back S-shaped, the defect is **not** the line-number scan and this
spec is wrong about its own subject — which is a result worth having before
writing a fix, not after.

### 3.3 `ref` — the line-number REFERENCE (P4)

Readout is again the stored bytes: `$0E,<lo>,<hi>` makes the crunched value
directly visible, and a blank that was copied rather than skipped is visible as
a `$20` byte in the body.

| label | typed | separates |
|---|---|---|
| `ref-ctl` | `20 GOTO 10` | **control** — `$0E,0A,00`, no blank involved |
| `ref-sp` | `20 GOTO␣␣␣10` | **control** for the *leading* blanks `bl_yes` copies verbatim |
| `ref-goto` | `20 GOTO 1 0` | T: `$0E,01,00` + ` 0`. S: `$0E,0A,00` |
| `ref-gosub` | `20 GOSUB 1 0` | same, other keyword |
| `ref-then` | `20 IF A THEN 1 0` | `THEN` arm |
| `ref-restore` | `20 RESTORE 1 0` | `RESTORE` arm |
| `ref-run` | `20 RUN 1 0` | `RUN` arm |
| `ref-resume` | `20 RESUME 1 0` | `RESUME` arm |
| `ref-onlist` | `20 ON A GOTO 1 0,2 0` | the list loop, both slots |
| `ref-oncomma` | `20 ON A GOTO 1 0 , 2 0` | blanks around the comma too |
| `ref-list` | `20 LIST 1 0` | ⚠️ zerobas emits no `$0E` here at all (§1). **Measured, filed if divergent, not fixed here** (§7) |
| `ref-delete` | `20 DELETE 1 0` | ditto |
| `ref-auto` | `20 AUTO 1 0` | ditto |
| `ref-renum` | `20 RENUM 1 0` | ditto |
| `ref-else` | `20 IF A THEN 1 0 ELSE 2 0` | ⚠️ `ELSE <line>` is a **known, documented gap** ([`basic/tokenise.inc:441`](../basic/tokenise.inc:441)). Informational. |

### 3.4 `cas` — the third consumer (P3)

`mrg_storeline` reaches P1/P2 through `dispatch_line`, so the fix covers it *by
construction*. That is exactly the kind of claim D-LOF found to be false three
sites out of three, so it gets rows rather than an argument. The VG-8020 has no
disk, so the only ASCII-program path both references accept is a cassette —
the same `build_ascii_cas` tape [`basic_probe_linemax.py:404`](../probes/basic/basic_probe_linemax.py:404)
already uses. **Two rows only** (one control, one blank case): these cost a tape
and a boot each, and their job is fix-coverage, not rule discovery.

| label | tape line | role |
|---|---|---|
| `cas-ctl` | `20 REMX` | control |
| `cas-blank` | `2 0 REMX` | the rule, on the ASCII path |

## 4. What the spec will assert

Deliberately blank until §3 has run. The rule is **whatever both references do**;
if they disagree, that disagreement is the finding and this section will say so
instead of picking a winner.

## 5. Candidate fixes — costed, undecided

Walls re-measured from clean at `1d9beb5`: **low region 23 B, page 1 69 B**
([`rom-region-structure-review.md`](rom-region-structure-review.md)). `program.asm`
and `tokenise.inc`'s placement decides which wall each candidate pays from; that
is checked at implementation time, not asserted here.

* **P2 only** — make `pl_lp`'s non-digit exit fall through a `cp ' '` that loops
  back instead of returning. `cp '0' / ret c` already catches the blank, so this
  is `ret c` → `jr c,pl_nd` (+1 B) plus a four-instruction tail (≈ +6 B).
  **≈ +7 B.**
* **P4 only** — the identical shape at `bl_acc` (`jr c,bl_done` → `jr c,bl_nd`),
  ≈ +6 B.
* **Both** — ≈ +13 B, which page 1 can pay at 69 B free *if* both sites live
  there.
* **Shared helper** — a single blank-transparent digit fetch called from both.
  Costs a `call`/`ret` per digit and, at two callers, is a **down-payment, not a
  saving** ([[generalisation-not-free-at-two-callers]]). Costed only if the two
  sites turn out to need identical semantics *and* the inline pair overruns a wall.

Whether P4 is fixed **at all** depends on §3.3: if the references do *not* skip
blanks in a line-number reference, then changing `bl_acc` would be a regression,
and the row that says so is a row this spec would otherwise never have run.

## 6. Falsification

Per the standing method: revert **the fix alone**, re-run, and confirm that
exactly the intended rows go red while every control stays green.

⚠️ If the fix lands byte-neutral there is no symbol witness, so the witness must
be a **probe row** — and it must be a row **downstream of the edit**
([[notopen-chan-err59-slice]]). The `num-only` row (§3.1) is the designated
witness: it changes the *number of stored lines*, which no adjacent behaviour
can produce by accident.

Gates to re-run after any `basic/` change (the standing corpus):
`make unit-test` 55/55 · `badfnum-acceptance` 93 · `lof-acceptance` 45 ·
`chancost-characterize` 53 (allowlist EMPTY) · `diskbasic-acceptance` 34/34 ·
`bdos-acceptance` 12/12 · `fat-error-acceptance` 8/8+dir · `error-trap-acceptance` ·
`abort-acceptance` 49/49 · `stop-trap-acceptance` · `linemax-acceptance` 60/60 ·
`arrdim-acceptance` 73/73 · `clearpool-acceptance` 52/52 ·
`array-acceptance` 149/151 (`ifc.instr.zero`, `ifc.instr.neg` standing, by name).

⚠️ **`linemax-acceptance` is the one to watch.** Its `tok` battery carries `A=`
in the payload *specifically to dodge this defect*
([`basic_probe_linemax.py:139`](../probes/basic/basic_probe_linemax.py:139)).
Fixing the defect does not change those rows, but the comment that explains the
`A=` becomes a historical note and must be updated to say so.

## 7. Out of scope

* **`LIST`/`DELETE`/`AUTO`/`RENUM` line-number references** (§3.3). If the
  references crunch these to `$0E` and zerobas does not, that is a *missing
  feature*, not this defect, and it gets its own TODO item. Measured here
  because it is part of the denominator; not fixed here because it is a
  different claim.
* **`ELSE <line>`** — a pre-existing documented gap.
* Line numbers **above 65529** as a *domain* question (`num-over`/`num-huge` are
  measured; if they reveal a missing range check that is its own slice, in the
  shape D-MFDOM took).
* The other open TODO items: `CAS:` modes 7/8, reset-between-`PUT`-and-`CLOSE`,
  the stale README "Limitations", the `PROVENANCE.md:3591` policy sharpening.

## 8. Deliverables

| file | what |
|---|---|
| `probes/basic/basic_probe_lnblank.py` | the batteries, the guards, both oracles |
| `docs/lnblank-msx1-characterization.md` | what the two references do (step 1) |
| this spec §4 | the rule, once measured |
| `Makefile` | `lnblank-characterize`, `lnblank-acceptance` |
| `basic/…` | the fix, if §3 says there is one |
| `TODO.md`, `PROVENANCE.md` | item closed, provenance row appended |
