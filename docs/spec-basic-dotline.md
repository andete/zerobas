# D-DOTLINE — `.`, the current-line pseudo-line-number

**Status: SIGNED OFF 2026-08-02. §8's three questions answered — all four
writers, accept the one-reference ASCII-SAVE reading and write in the shared
`list_walk`, and claim the published `$F6B5`.**

Measurement: [`docs/dotline-msx1-characterization.md`](dotline-msx1-characterization.md)
— 4 batteries, 77 new rows, both references agreeing on every one at
`--repeat 2`.

Filed 2026-08-02 by D-DELETE ([`spec-basic-delete.md`](spec-basic-delete.md) §6),
confirmed on a second verb by D-LSTRNG ([`spec-basic-listrange.md`](spec-basic-listrange.md)
§6), and declined by both rather than ship a rule one verb wide.

---

## 1. Why now

D-DELETE's cost objection was real when it was made and is **void**: D-MSGMIGRATE
carved 289 B and page 1 went from 22 B free to **311 B** (re-measured from clean
at HEAD `40647bd`: main page-1 free **311 B**, main page-0 low free **23 B**, sub
p0 **3913 B**, sub p1 **2428 B**).

⚠️ **"There is room" is not the argument.** The argument is **pin pressure**:
four `KNOWN_DIVERGE` pins ride on this item today (`dlt-dot`, `dlt-dotedit`,
`lst-dot`, `lse-dotedit`) and **every further editor verb adds two more**.
`RENUM` and `AUTO` are both tokenised-but-not-executed and both take `.`.
Doing `.` as its own cross-cutting slice **before** them retires four pins;
doing it after would mean retiring eight.

## 2. The rules

Copied from the characterization §5, which is where each one's row lives. Nothing
here is inferred from the published work-area comment.

* **R-DOT1** — `.` reaches the statement as the literal `$2E`, in **every**
  argument position, and does **not** disarm line-number mode: the number behind
  a `-` is still an armed `$0E` (`lna-listdotd` `lna-delddot`, §1). Every verb
  therefore resolves it itself. ⚠️ Not the obvious answer — `.` is a **name**
  character everywhere else in the tokeniser, and a name character disarms.
* **R-DOT2** — `.` resolves to a 2-byte cell holding a line number.
  **Cold value 0** (`clp-cold`).
* **R-DOT3** — the writers, and **nothing else is one**:
  * **(a) storing a line** — insert, replace, *or* the bare-line-number delete —
    records the line number **typed**, even when the line is thereby removed;
  * **(b) the LIST walk** — records the **last line it printed**; a walk that
    prints nothing writes nothing. **Including ASCII SAVE**, which drives the
    same walk (§4 of the characterization — ⚠️ **one reference**); a tokenised
    SAVE does not;
  * **(c) an error in a STORED line** — records the erroring line. A
    **direct-mode** error writes **nothing** (⚠️ *not* `ERRLIN`'s 65535);
  * ~~**(d) `RESUME`**~~ — 🔴 **WITHDRAWN AFTER THE FACT.** This slice
    implemented it, knife **K5** cut it and moved **zero of 139 rows**, and the
    row written to settle that (`clp-resend`) reads **20** on both references
    against the shipped build's 50. There is no RESUME writer; see §9.1.
* **R-DOT4** — measured **non**-writers, each with its own row: `RUN`,
  `STOP`/break, `CONT`, `CLEAR`, **`NEW`**, the `DELETE` **verb**, a direct-mode
  statement, `GOTO`, `GOSUB`, `ON ERROR GOTO`, a direct-mode error, a tokenised
  `SAVE`.
* **R-DOT5** — once resolved, `.` is an **ordinary line number** in either end of
  either verb's range: DELETE's asymmetric R-D2 (the high end must name a stored
  line) and R-D4 (lo > hi is ERR 5) and LIST's R-LS1/R-LS3/R-LS5 all fire on it
  unchanged.
* **R-DOT6** — a verb **resolves `.` before it writes it**.

🔴 **THREE OF THESE WOULD HAVE BEEN WRONG UNDER THE OBVIOUS DESIGN**, and each
was caught by a row whose only job was to be the other half of a pair:
`NEW` looks like it should reset the cell (`TRACEFLAG`'s only non-statement
writer is `new_prog`) and does not; the error writer looks like it belongs on
`record_errline`'s shared tail and must **skip its direct arm**; and the LIST
writer looks like it must be kept out of `SAVE",A"` — the exact hazard D-LSTRNG
§3.3 fixed in the same routine — where the reference does the opposite.

## 3. Where it goes, and what it costs

`DOT` is claimed at the **published address `$F6B5`**, under the published name,
with D-REHOME's four-point record beside its equate
([`sysvar-rehoming-decisions.md`](sysvar-rehoming-decisions.md) §3's format):

| | |
|---|---|
| **SEMANTICS** | SAME-VAR, measured: 22 `clp` rows read `$F6B5` on both references after 22 different stimuli, and **every one agrees with its behavioural `cln`/`cle` twin**. |
| **OBSERVER** | `PEEK` — and that is how the cold value and `NEW` were read at all. Whether `POKE`-then-`LIST .` reads back is **not measured**; see §7 K6. |
| **COST** | **ZERO ROM bytes** — every access is through the symbol, and no cell moves. |
| **PUB-FREE** | measured: zerobas's byte at `$F6B5` reads **0 in all 22 states** (the `clp` zb column), so nothing — zerobas or C-BIOS — claims it today. |

⚠️ `$F6B5` sits between two cells zerobas **already** holds at their published
addresses, `ERRLIN $F6B3` and `ONELIN $F6B9`. No new private RAM is claimed and
the `$E234..$E23F` free window is **not** touched.

### 3.1 The edit list

| # | file | what | region | est. |
|---|---|---|---|---:|
| 1 | [`sub/lineedit.asm`](../sub/lineedit.asm) `ldr_num` | **the resolver** — a `cp '.'` arm returning `DE=(DOT)`, CF set | sub p1 | 11 B |
| 2 | [`sub/lineedit.asm`](../sub/lineedit.asm) `le_ok` | **writer (a)** — `ld hl,(SL_NUM) / ld (DOT),hl` | sub p1 | 6 B |
| 3 | [`basic/list.asm`](../basic/list.asm) `list_walk` | **writer (b)** — `ld (DOT),de` at the emit site | main p1 | 4 B |
| 4 | [`basic/interp.asm`](../basic/interp.asm) `record_errline` | **writer (c)** — `ld (DOT),hl` on the **run-mode arm only** | main p1 | 3 B |
| ~~5~~ | ~~`ex_resume`~~ | ~~writer (d)~~ — **REMOVED, §9.1**: the rule does not exist | — | **−14 B** |
| 6 | [`basic/interp.asm`](../basic/interp.asm) `init` | cold init to 0 (`HL` is already 0 there) | main p1 | 3 B |
| 7 | [`basic/sysvars.inc`](../basic/sysvars.inc) | `DOT equ $F6B5` + the §3 record | — | 0 B |
| 8 | [`probes/basic/basic_probe_sysvarsweep.py`](../probes/basic/basic_probe_sysvarsweep.py) | the new honoured entry | — | — |

**Estimated main page 1: ~22 B of 311 free. Sub page 1: ~17 B of 2428 free.**

✅ **AS BUILT: main page 1 311 → 301 free (10 B), sub page 1 2428 → 2411 (17 B),
main page-0 low 23 B unchanged, sub page 0 3913 B unchanged.** The estimate was
12 B over because §9.1's writer (d) — 14 B of it — turned out not to be a rule
at all. The sub-side estimate was exact.

🎯 **ONE RESOLVER, AND IT IS ALREADY SHARED.** `ldr_num` is the single place both
`le_delrange` and `le_lstrange` read a line number from — D-LSTRNG widened it to
report *presence* in CF precisely because the two verbs' defaults differ. Adding
`.` there serves **both implemented verbs at one site**, and `AUTO`/`RENUM` get it
for free the day they are dispatched. No new `sub/*.asm` file, so **no
`SUB_PARTS` entry is needed** — the trap that silently ships a stale `sub.rom`
does not apply here, and that is checked rather than assumed.

🎯 **WRITER (b) IS 4 BYTES *BECAUSE* THE MEASUREMENT INVERTED THE DESIGN.**
Placed in the shared `list_walk`, it is automatically right about all three
things the rows measured: last-printed (each line overwrites), printed-nothing
(the branch never runs), and ASCII SAVE (the same walk, which the reference also
writes from). The "safe" variant — keep it out of SAVE by writing in `ex_list`
from a scratch cell `list_walk` fills, plus a seed so a nothing-listed `LIST`
leaves `DOT` alone — costs **~16 B** and is **measurably wrong**.

⚠️ **Item 5's 12 B may factor to ~4.** `record_errline`'s run arm, `ex_resume`'s
new write and `print_in_lineno` ([`basic/program.asm`](../basic/program.asm)) all
do the identical `CURLINE+2` line-number fetch. A shared leaf is 10 B and saves 6
at each other caller. At two callers that is +10 vs +12 — a down-payment, not a
saving ([[generalisation-not-free-at-two-callers]]); at three it is +4. **This is
decided by building both and reading `make basic-reloc`, not by this paragraph**
(knife K7).

### 3.2 What is deliberately NOT touched

* **`new_prog` gains nothing.** `NEW` does not reset `.` (`clp-new` = 20). A
  measured non-change, recorded so nobody "tidies" it in later.
* **`AUTO` / `RENUM` / `LLIST`** stay undispatched. This slice designs the
  resolver so they can call it and does not widen into their TODO item.
* **`EDIT`** does not exist in zerobas at all.
* **ASCII LOAD/MERGE** — zerobas's `cload.asm` reaches `store_line`, so it will
  inherit writer (a) whether or not the reference does. **Unmeasured** (§5.1 of
  the characterization); this is a **choice**, stated, not a reading.

## 4. Rows and pins

* **new**: 35 `cln` (tail readout) + 12 `cle` (bracket) + 24 `clp` (the published
  cell) + 6 `lna-*dot*` crunch rows.
* `cln-`/`cle-`/`clp-` join `lnblank-say-acceptance`'s default `ONLY=`, taking it
  from **108** rows to **179**.
* 🎯 **RETIRED — four pins, DELETED not edited**: `dlt-dot`, `dlt-dotedit`,
  `lst-dot`, `lse-dotedit`. **All four must go green.** A pin that survives this
  slice is a finding, not an inconvenience: each is a consequence of R-D6/R-LS6
  answering the unknown `$2E`, so once `.` is known they cannot stay red for the
  reason they were pinned.
* **new pins: ∅ expected.** Every measured rule above is implementable; if a pin
  is added, §8 says which and why.
* **controls that must stay green**: `cln-sdelctl`, `cln-delctl`, `cln-coldctl`,
  `cln-runctl`, `cle-ctl`, `cle-dctl`, `clp-runctl`, `clp-untouch`, and every
  existing `dlt-`/`lst-`/`lse-` row (the resolver touches `ldr_num`, which both
  verbs' whole parse runs through).

## 5. Predicted RED and predicted GREEN

**Derived from the EDIT LIST in §3.1, not from the scope list**
([[predicted-red-set-must-not-inherit-scope]] — D-LSTRNG predicted 25 and got 40
by deriving from scope).

**Predicted RED → GREEN (rows that must MOVE, with their exact new values).**
All are `Syntax error` / ERR 2 on zerobas today.

| rows | new value |
|---|---|
| `cln-store` `cln-list` `cln-listbare` | `40 REM D` |
| `cln-edit` `cln-direct` `cln-del` `cln-clear` `cln-both` `cln-listmiss` `cln-direrr` | `20 REM B` |
| `cln-ins` | `25 REM E` |
| `cln-sdel` `cln-cold` | `<nothing listed>` |
| `cln-lo` | `20 REM B\|30 REM C\|40 REM D` |
| `cln-hi` `cln-numhi` | `10 REM A\|20 REM B` |
| `cln-lonum` `cln-blank` | `20 REM B\|30 REM C` |
| `cln-rev` | `<nothing listed>` |
| `cln-listrng` `cln-dotthen` | `30 REM C` |
| `cln-runctl` `cln-run` `cln-stop` `cln-cont` `cln-goto` | `10 A=A+1` |
| `cln-err` `cln-trapend` | `20 ERROR 7` |
| `cln-onerr` | `10 ON ERROR GOTO 50` |
| `cln-trap` `cln-reslin` | `50 RESUME NEXT` / `50 RESUME 30` |
| `cln-res15` | `15 RESUME NEXT` |
| `cle-ctl` `cle-cold` | ` 0 ` |
| `cle-colddel` | ` 5 ` |
| `cle-donly` `cle-dboth` | ` 13  0 ` |
| `cle-dlo` | ` 1  0 ` |
| `cle-dhi` | ` 12  0 ` |
| `cle-drev` | ` 15  5 ` |
| `cle-dgone` | ` 13  5 ` |
| all 24 `clp-` rows | the reference values in characterization §3/§3.1 |

**Predicted GREEN (must NOT move).** Every `dlt-`, `lst-`, `lse-`, `lnrd-`,
`kwgd-`, `lnrt-` row that does not contain a `.`; all 6 `lna-*dot*` crunch rows
(zerobas already agrees — the tokeniser is not edited); `cln-sdelctl`,
`cln-delctl`, `cln-coldctl`, `cle-coldlist`, `cle-colddel0`, `cle-dctl`,
`clp-untouch`.

🔴 **THE `dlt-`/`lst-` GREEN SET IS THE REAL TEST OF ITEM 1.** `ldr_num` is on
the parse path of *every* `DELETE` and `LIST` row, so a resolver that disturbs
the CF contract, `A`, or `HL` breaks 34 rows that have nothing to do with `.`.
D-LSTRNG's K3 was scored on the `dlt-` rows for exactly this reason.

## 6. The whole corpus

Any `basic/`/`sub/` change requires the full list in `TODO.md`'s standing note —
`unit-test` 56/56 · `deadcode` 0/0 both builds · `msgexact --gate` 54/54 +
`--relock` · `lnblank-acceptance REPEAT=2` 530/530 allowlist EMPTY ·
`lnblank-say-acceptance` (108 → **179**) · `lnblank-echo` · `logicops` 193/193 ·
`array` 151/151 · `sysvarsweep` · `error-trap`/`error`/`abort` ·
`direct-ctrl` · `kwsweep` · the rest.

⚠️ **`sysvarsweep` is not a formality this time** — item 7 claims a byte in its
denominator. Its `s0-boot` baseline for `$F6B5` currently reads 0 on zerobas and
must go on reading 0; its post-stimulus states must move exactly as the `clp`
rows say.

⚠️ Standing, not caused here: `audit_citations.py` 2 gating findings
(`basic/fat.asm:81`, `basic/missing.asm:1`); `lnblank-echo` `dec-eol`/`dec-eolctl`
MANGLED on all three sides (non-gating, exit 0).

## 7. Knives — each with a predicted RED set **and** predicted GREEN survivors

Scored against the **whole** `cln`+`cle`+`clp`+`dlt`+`lst`+`lse` battery on
zerobas, every RED row carrying an exact value written down before the build.
⚠️ Every knife reverted against **the build it cut**, never `git checkout`, and
the restoration verified by hashing all touched sources **and both ROMs**. Never
`copy2` (it preserves mtime; `make` skips the rebuild and the check hashes the
stale knifed ROM). 🔴 **When a knife shows NO change, hash the built ROM against
the pre-cut baseline before concluding anything** — "the cut did nothing" and
"the cut never happened" look identical.

* **K1 — the resolver (item 1)**: drop the `cp '.'` arm.
  RED: every `.` row — all 20 `cln` `.`-carrying rows back to `Syntax error`, 8
  `cle` rows back to ERR 2.
  GREEN: **all 34 `dlt-`/`lst-`/`lse-` rows**, and every `clp` row (the cell is
  still written; only reading it through `.` is gone). 🎯 That `clp` stays green
  under K1 is the point: it separates the **resolver** from the **writers**,
  which no single readout could.
* **K2 — writer (a) (item 2)**: drop the `le_ok` write.
  RED: `cln-store` `cln-edit` `cln-ins` `cln-sdel` + their `clp` twins → `LIST .`
  reads whatever `LIST` last left.
  GREEN: 🔴 **`cln-list` MUST STAY `40 REM D`** — its value comes from writer
  (b), not (a). K2 and K3 are each other's control; one knife could only have
  half-shown that the two writers are separate.
* **K3 — writer (b) (item 3)**: drop `ld (DOT),de` from `list_walk`.
  RED: `cln-list` `cln-listrng` `cln-listbare` `cln-dotthen` `clp-list` → each
  reads the value writer (a) left (`20 REM B` / 20).
  GREEN: 🔴 **`cln-listmiss` MUST STAY `20 REM B`.** It is already "unchanged" in
  the reference, so it cannot move — a predicted-GREEN that proves the
  "prints nothing writes nothing" arm is **structural**, not a rule this slice
  implements. ⚠️ That makes it a rule with **no knife**, held up only by its
  control ([[rule-gated-structurally-has-no-knife]] — say so, do not pretend it
  is gated).
* **K4 — writer (c) (item 4)**: drop `ld (DOT),hl` from `record_errline`.
  RED: `cln-err` `cln-trapend` `clp-err` `clp-trapend` → `10 A=A+1` / 10.
  GREEN: 🔴 **`cln-stop` `cln-run` `cln-cont` `cln-goto` `cln-onerr` MUST STAY
  `10 A=A+1`** — they never wrote, so a cut to the error writer cannot move them.
  If any does, the write is on a shared path it should not be on.
* **K5 — writer (d) (item 5)**: drop the `ex_resume` write.
  Predicted RED: `cln-trap` `cln-reslin` `cln-res15` + their `clp` twins.
  🔴 **MEASURED: ZERO of 139.** §9.1 — the rule was fiction, and this is the
  knife that found it.
* **K6 — the cold init (item 6)**: delete `ld (DOT),hl` from `init`.
  🔴 **PREDICTED RED: ZERO ROWS.** openMSX zero-fills RAM, so an uninitialised
  `DOT` reads 0 anyway and `clp-cold` stays green. **That prediction IS the
  finding** ([[knife-that-reddens-nothing-is-the-finding]]): if it holds, the
  cold init is gated by **nothing** in this tree and is carried on the same
  power-on-RAM-is-garbage argument `init`'s own ERR/ERL reset already carries
  (`basic/interp.asm:51`). Say that plainly rather than let a green run read as
  coverage. ⚠️ Score it by hashing the ROM first — a 3-byte cut that changes no
  row is indistinguishable from a cut that never built.
* **K7 — aimed at the JUSTIFICATION, not the code.** §3.1 claims writer (b)
  costs 4 B where the SAVE-excluding variant costs ~16 B, and that item 5 may
  factor from 12 B to ~4 B across three callers. **Build both variants and read
  `make basic-reloc`'s page-1 figure**; scored against §3.1's table, not against
  the battery. D-LSTRNG's K7 estimate was 21 B out — the point is to find out by
  how much, not to confirm.
* **K8 — aimed at the PUB-FREE claim.** §3 says nothing else writes `$F6B5`.
  Poke a sentinel there at the prompt, run a program that does everything R-DOT4
  lists as a non-writer, and read it back; it must survive. ⚠️ Include a row the
  cut must NOT touch — D-MSGMIGRATE's K1 moved nine rows including a control that
  had no business moving, and that is what caught it.

## 8. Open questions for sign-off

1. **Scope.** The measurement found **four** writers where the TODO filed one
   mechanism and five call sites. Writers (c) and (d) — the error and `RESUME` —
   are ~15 B of main page 1 and are what make `LIST .` after a failure useful,
   which is `.`'s documented purpose. **Recommendation: implement all four.**
   They are separable if you want a smaller slice: (a)+(b) alone retire all four
   pins and leave (c)/(d) filed, at the cost of shipping a rule that is
   measurably wrong on `cln-err`/`cln-trap`.
2. **The one-reference reading.** §4 of the characterization (ASCII SAVE writes
   `.`) is **cf3300 only** and decides a 12 B design point. Accept it, or hold
   writer (b) to the LIST-only placement until a second reference can be had?
   **Recommendation: accept.** It is a positive reading with its own control on
   the same machine, and the alternative is to pay 12 B for the *opposite* of the
   only measurement there is.
3. **`$F6B5` at the published address.** This claims a byte in the sysvar
   denominator. PUB-FREE is measured; the `POKE`-read-back observer is not
   (§3, K6 is not that test). Take it, or home `DOT` privately at `$E234`?
   **Recommendation: take the published address** — it is free, it is the same
   decision D-REHOME made five times, and a private address here would be exactly
   the space-driven placement that review has twice had to undo.

---

## 9. 🔴 An apparatus finding the ROM-hash check caught, and nothing else would have

**A `make` that skipped a rebuilt sub-ROM because the source and the ROM shared
an mtime — to the second.**

Knife K2 deleted 6 bytes from [`sub/lineedit.asm`](../sub/lineedit.asm) and
`make basic-reloc && make repack-machine` produced **byte-identical ROMs**.
`sub/lineedit.asm` **is** in the Makefile's `SUB_PARTS` (line 183) — the
dependency is declared and correct. It was skipped anyway: the file and
`build/sub.rom` both carried mtime `21:53:19`, and `make` treats an equal
timestamp as *not newer*. A knife runner that writes a cut and rebuilds inside
the same one-second tick hits this every time.

🎯 **WITHOUT THE ROM-HASH CHECK, K2 WOULD HAVE SCORED 0 RED OF 139 AND BEEN
WRITTEN UP AS "WRITER (a) IS GATED BY NOTHING".** That is a false finding in the
direction that reads like a *result* — the same shape as
[[knife-runner-false-negatives]], where a runner that failed toward "nothing to
see" could not gate. §7's rule ("when a knife shows NO change, hash the built ROM
against the pre-cut baseline before concluding anything") is what turned a silent
wrong answer into a loud abort.

⚠️ **This is [[makefile-subparts-stale-tenant]] arriving by a different road.**
That entry warns that a sub include *missing* from `SUB_PARTS` silently ships a
stale `sub.rom`. Here the entry is present and correct and the rebuild is skipped
regardless, so the existing guard — "check the include is listed" — does not
detect it. Clean builds hide it completely, which is why it had never surfaced.

⚠️ **Deleting only `build/sub.rom` is NOT a fix**: the `.sym` then looks up to
date, the ROM rule does not re-run in the right order and the build fails
outright (`FileNotFoundError: build/basic-reloc.rom`). The repo's own standing
rule is the whole fix — **always `rm -rf build` first** — and the knife runner
now does exactly that on every build, at a cost of a few seconds per cut.

🔴 **CORRECTION 2026-08-07 (D-FEVERB): `rm -rf build` is NOT "the whole fix".**
Measured — a cut that lands in a **comment** (the ordinary mis-siting, since cut
strings usually carry their trailing comment) produces **byte-identical ROMs from
a clean build**, and a runner without the ROM-hash check scores it as a MISS.
Clean building fixes the **race**; only the hash separates *"the cut reached the
artifact and reddened nothing"* — a finding — from *"the cut never reached the
artifact"* — nothing measured. The two guards are complementary and the hash
strictly dominates for the scoring question. §7's rule here is the one that
generalises; this paragraph's is the one that does not. The cost argument is also
void: a clean rebuild measures **5.1 s** against 0.08 s incremental, so there was
never a reason to choose. See [`dev-workflow.md`](dev-workflow.md) §Knives and
[`spec-fat-error-verb-control.md`](spec-fat-error-verb-control.md) §6.2.

**Worth filing:** any fast edit-then-build in this tree can silently reuse a
stale `sub.rom`. A `.PHONY` force, an order-only rebuild stamp, or a
content-hash dependency would close it for good; this slice records the shape and
fixes its own runner rather than widening into the Makefile.

---

## 9.1 🔴 The knife that reddened NOTHING found a rule that does not exist — after it shipped

**Knife K5 cut the `RESUME` writer and moved zero of 139 rows.** Every other
knife in this slice hit its predicted set exactly; K5 hit nothing at all.

The tempting reading is "K5 is uninformative". The filed one is the opposite:
**a rule gated by nothing is the finding**
([[knife-that-reddens-nothing-is-the-finding]]). So the *rule* went back under
the microscope, and it turned out that every row supporting it had **two
sufficient causes**:

* `clp-trap` (`50 RESUME NEXT`) and `clp-reslin` (`50 RESUME 30`) resume into
  line 30, which then **falls through into line 50 again**, where a second
  `RESUME` with no active error raises **ERR 22 in line 50**. Writer (c) files
  50 unaided;
* `clp-res15` was never a `RESUME` row: its handler is at line 15, **before**
  the erroring line, so it runs in sequence and raises the same ERR 22 there.
  K4 moves it, K5 does not — which was visible in the knife table and read as
  noise until K5's zero forced the question.

`clp-resend` separates them — `30 A=A+4:END` stops the program before line 50 can
be re-entered, so only a `RESUME` writer could put 50 there:

| | vg8020 | cf3300 | zerobas **as shipped** |
|---|---:|---:|---:|
| `clp-resend` | **20** | **20** | **50** ❌ |

🔴 **A DIVERGENCE, IN CODE THIS SLICE HAD ALREADY WRITTEN, THAT ALL 139 ROWS AND
A GREEN 179/179 GATE AGREED WITH.** Writer (d) is deleted; `ex_resume` is back to
its pre-slice bytes and **14 B of main page 1 came back** (287 → 301 free). After
the removal `clp-trap` = 50, `clp-reslin` = 50, `clp-res15` = 15 on all three
sides: writer (c) covers every one.

⚠️ **The apparatus lesson is about ORDER, not about K5.** K5 could not have
failed — it scored a rule that was fiction, and "0 RED" is what fiction produces.
What converted that into a defect report was refusing to accept 0 RED as a pass
and **constructing the case the machine would get wrong**
([[readout-blind-to-its-own-subject]]'s discipline applied to a knife instead of
a readout). This is the fourth time in this tree a knife has found a defect in
the slice's own work ([[knife-found-defect-in-own-fix]]) and the first time it
did so by finding *nothing*.

⚠️ `cln-resend` / `clp-resend` join the battery as ordinary green rows, so the
"an ordinary `RESUME` leaves `.` on the erroring line" rule is now gated by
something rather than by an argument.

---

## 10. Results

### 10.1 Walls — clean `rm -rf build && make basic-reloc`

| | HEAD `40647bd` | as built | §3.1 predicted |
|---|---:|---:|---:|
| main page 1 free | 311 B | **301 B** | 289 B |
| main page-0 low free | 23 B | **23 B** | 23 B ✅ |
| sub page 1 free | 2428 B | **2411 B** | 2411 B ✅ |
| sub page 0 free | 3913 B | **3913 B** | untouched ✅ |

**10 B of main page 1, 17 B of sub page 1.** The sub-side estimate was **exact**;
the main-side estimate was 12 B pessimistic *because §9.1's writer (d) turned out
not to be a rule*. Four pins retired, none added, for 10 bytes.

### 10.2 Gates — 16 targets, every one exit 0

| | |
|---|---|
| `make unit-test` | **56/56** |
| `deadcode`, both builds | **0 dead** |
| `lnblank-acceptance REPEAT=2` | **536/536** (530 → 536), allowlist **EMPTY** |
| `lnblank-say-acceptance` | **181/181** (108 → 181), pins **6 → 2** |
| `msgexact --gate` / `--relock` | **55/55** / all 41 locked values reproduce |
| `sysvarsweep` | green — the new `DOT $F6B5` regression row holds |
| `error-trap` · `error` · `abort` · `stop-trap` · `direct-ctrl` | green |
| `array` · `logicops` · `string` · `kwsweep` | green |

🎯 **THE PIN SET SHRANK.** `dlt-dot`, `dlt-dotedit`, `lst-dot`, `lse-dotedit`
**deleted, not edited** — the first cohort in this battery to retire more pins
than it adds. The two survivors (`kwgd-renum`, `lnrt-forret`) are other items'.

⚠️ `lnblank-echo`: only the three standing informational rows (`dec-eol`,
`dec-eolctl`, `num-tab`) report MANGLED, on all three sides, as before. **No new
mangle on any of the 73 new payloads** — the delivery guard the whole battery
rests on.

### 10.3 Knives

Scored against the whole 141-row `cln`+`cle`+`clp`+`dlt`+`lst`+`lse` battery on
zerobas; every cut rebuilt from clean, **ROM-hash-checked as actually different
before scoring**, reverted against the build it cut, and both ROMs re-hashed back
to baseline afterwards.

| knife | predicted RED | measured | verdict |
|---|---|---|---|
| K1 resolver | every `.` row; **all 34 `dlt-`/`lst-`/`lse-` non-`.` rows GREEN** | **46 RED**, all four retired pins back to their exact pinned values, non-`.` rows green | ✅ |
| K2 writer (a) | the store rows; **`cln-list` MUST STAY `40 REM D`** | **44 RED**, and `cln-list`/`clp-list` **did not move** | ✅ |
| K3 writer (b) | `cln-list` `cln-listrng` `cln-listbare` `cln-dotthen` `clp-list`; **`cln-listmiss` MUST STAY** | **exactly those 5**; `cln-listmiss` stayed `20 REM B` | ✅ |
| K4 writer (c) | `cln-err` `cln-trapend` + `clp` twins; `cln-stop`/`-run`/`-cont`/`-goto`/`-onerr` GREEN | **12 RED** — and see below | ✅ |
| ~~K5~~ writer (d) | `cln-trap` `cln-reslin` `cln-res15` + twins | **0 RED** → **§9.1, the rule does not exist** | 🎯 finding |
| K6 cold init | **ZERO — predicted in advance** | **0 RED** | ✅ prediction exact |

🎯 **K4 GREW FROM 6 RED TO 12 ONCE WRITER (d) WAS GONE, AND THAT IS THE PROOF OF
§9.1.** On the first build, `cln-trap`/`clp-trap`/`cln-reslin`/`clp-reslin` did
not move under K4 — the phantom writer (d) was covering them. With it deleted
they move, together with `cln-resend`/`clp-resend`: **writer (c) alone accounts
for every one**, which is exactly what the two-sufficient-causes reading
predicted and what no single knife could have shown.

🎯 **K2 AND K3 ARE EACH OTHER'S CONTROL, MEASURED.** K2 cuts the store writer and
`cln-list` stays `40 REM D`; K3 cuts the LIST writer and the store value shows
through as `20 REM B`. Neither writer is doing the other's work.

🎯 **K3's `cln-listmiss` STAYED GREEN, AS PREDICTED — AND THAT RULE HAS NO KNIFE.**
"A walk that prints nothing writes nothing" is **structural** in this placement
(the branch simply never runs), so it is held up only by its own control
([[rule-gated-structurally-has-no-knife]]). Said out loud rather than counted as
coverage.

🎯 **K6 WAS PREDICTED TO REDDEN NOTHING AND DID.** openMSX zero-fills RAM, so the
cold init is gated by **nothing** in this tree and rests on the same
power-on-RAM-is-garbage argument `init`'s ERR/ERL reset already carries. Written
down before the build so a green run could not read as coverage.

### 10.4 ⚠️ Two knives in §7 were NOT run, and that is said rather than implied

* **K7 (the cost justification).** The half that mattered was answered by the
  measurement instead: §4 of the characterization shows the SAVE-excluding
  variant of writer (b) is **measurably wrong**, so costing it would have priced
  a defect. The other half — §3.1's estimate — is scored in §10.1: **22 B
  predicted, 10 B as built**, and §9.1 is the entire difference. The
  three-caller factoring of the `CURLINE+2` fetch was never needed, since writer
  (d) is gone.
* **K8 (the PUB-FREE claim).** Not run as specified. The evidence for it is the
  `clp` battery's **zerobas column reading 0 in all 24 states at HEAD `40647bd`**
  — i.e. measured *before* the claim — plus `sysvarsweep`'s new `DOT` row, which
  gates it from here on. A `POKE`-a-sentinel-and-run-the-non-writers test would
  be strictly stronger and was not performed.
