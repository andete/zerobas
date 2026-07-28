# D-MISS-2 — the string functions' argument-domain checks

Status: ✅ **LANDED 2026-07-28** — signed off on S-SD-1..4, `make
str-domain-acceptance` **89/89**, falsified **51/89**, low region **7 B → 30 B
free**. Roadmap item: the last 🔴 in [`TODO.md`](../TODO.md). Predecessor:
[`spec-basic-abort-depth.md`](spec-basic-abort-depth.md) (`4d35b6d`), which this
slice is deliberately ordered behind.

Probe: `probes/basic/basic_probe_str_domain.py`, 89 rows, six batteries.
Measured against `Philips_VG_8020` on a clean-built `4d35b6d`, batched with
self-heal **and** confirmed `--boot-per-case`.

---

## 1. What is wrong

`CHR$` / `LEFT$` / `RIGHT$` / `MID$` accept out-of-range arguments **silently
and compute a wrong answer**, where the reference raises. Found by the
MISSING-class calibration battery ([`missing-vg8020-characterization.md`](missing-vg8020-characterization.md)
§8), which was not looking for it.

**41 of 89 rows diverge.** The seven rows the roadmap already knew about are a
small corner of it; §2, §3 and §3a are what the extra 82 rows bought.

---

## 2. The rule, as measured

| surface | argument | legal domain | outside it, inside int16 | outside int16 |
|---|---|---|---|---|
| `CHR$(c)` | `c` | 0..255 | `Illegal function call` | `Overflow` |
| `LEFT$(a$,n)` | `n` | 0..255 | `Illegal function call` | `Overflow` |
| `RIGHT$(a$,n)` | `n` | 0..255 | `Illegal function call` | `Overflow` |
| `MID$(a$,p[,n])` fn | `p` | **1..255** | `Illegal function call` | `Overflow` |
| `MID$(a$,p,n)` fn | `n` | 0..255 | `Illegal function call` | `Overflow` |
| `MID$(a$,p[,m])=b$` stmt | `p` | **1..255 and ≤ LEN(a$)** | `Illegal function call` | `Overflow` |
| `MID$(a$,p,m)=b$` stmt | `m` | 0..255 | `Illegal function call` | `Overflow` |
| `INSTR(p,a$,b$)` | `p` | **1..255** | `Illegal function call` | `Overflow` |

Four properties of that table are measurements, not inferences, and three of
them were never measured before this probe existed.

### 2.1 The int16 gate is a RANGE, not a magnitude

`CHR$(-32768)` → `Illegal function call`; `CHR$(-32769)` → `Overflow`. So
stage 1 accepts the whole int16 range **−32768..32767** and rejects only what
falls outside it. It is *not* `|x| ≤ 32767`.

This mattered because `get_byte_arg`'s own header (`basic/interp.asm:1378`) is
written in terms of `fac_to_int_strict`, documented as "FPERR set if
|x| > 32767" — which would have made `−32768` an `Overflow` and put every
existing caller off by one at that single value. **It does not.** The `bnd`
battery ran `STRING$(-32768,65)`, `STRING$(-32769,65)` and `SPACE$(-32768)`
through the EXISTING implementation and all three already agree with the
reference. `get_byte_arg` is exactly the reference rule, boundary included.

⚠️ So `fac_to_int_strict`'s "|x| > 32767" comment is imprecise about the one
value where it matters. Worth a comment fix; not worth code.

### 2.2 The coercion truncates toward zero BEFORE the domain check

`CHR$(255.9)` is legal (→ 255) and `CHR$(-0.5)` is legal (→ 0). A rounding
coercion would reject the first and a flooring one the second. zerobas already
agrees on both, so this is a property the fix must not disturb rather than one
it must add.

### 2.3 `MID$`'s position is the family's one 1-based argument

`MID$("abc",0)` raises where `MID$("abc",255)` does not. So `p`'s domain is
**1..255**, and it is the only argument in the family that is not
`get_byte_arg`'s plain 0..255 rule. An implementation that reached for
`get_byte_arg` everywhere would be wrong on exactly this one.

### 2.4 Arguments are checked left to right, each one fully, before the next

- `MID$(a$,99999,-1)` → `Overflow` — `p`'s *stage 1* beats `n`'s stage 2.
- `MID$(a$,0,99999)` → `Illegal function call` — `p`'s *stage 2* beats `n`'s stage 1.
- `MID$(a$,0,)` → `Illegal function call`, **not** `syntax error` — the domain
  check also beats the deferred-syntax-error machinery, so a check may sit
  immediately after its own argument's `eval`, before the closing `)` has been
  looked at. That is the cheapest placement and it is the correct one.
- `LEFT$(1,-1)` → `Type mismatch` — the type check still precedes the domain
  check. zerobas already agrees.

---

## 3. The `MID$` STATEMENT is a second broken surface — newly found

`MID$(a$,p[,m])=b$` is a different code path
([`basic/str-engine.asm:862`](../basic/str-engine.asm:862)) from the `MID$`
function, with the same two numeric arguments and the same domain. **It was not
in the roadmap item and it is broken in both possible ways:**

| case | reference | zerobas |
|---|---|---|
| `MID$(A$,0)="X"` | `Illegal function call` | `syntax error` |
| `MID$(A$,-1)="X"` | `Illegal function call` | `syntax error` |
| `MID$(A$,256)="X"` | `Illegal function call` | `syntax error` |
| `MID$(A$,4)="X"` (p > len) | `Illegal function call` | `syntax error` |
| `MID$(A$,255)="X"` | `Illegal function call` | `syntax error` |
| `MID$(A$,99999)="X"` | `Overflow` | `syntax error` |
| `MID$(A$,1,-1)="X"` | `Illegal function call` | `syntax error` |
| `MID$(A$,1,256)="X"` | `Illegal function call` | 🔴 **`[Xbc]` — it performs the assignment** |
| `MID$(A$,1,99999)="X"` | `Overflow` | 🔴 **`[abc]` — it silently does nothing** |

The first seven are wrong-error-code (`ON ERROR` sees the wrong `ERR`); the last
two are silent wrong answers of exactly the D-MISS-2 kind. Leaving them would
fix half a verb.

⚠️ **Doc debt this exposes.** `basic/str-engine.asm:848` states the range errors
raise `stmt_error` because *"zerobas has no `Illegal function call`, D-3"*. That
has not been true for a long time — `ASC("")` raises it, and the `ctl` battery
proves it is reachable from evaluator depth. The comment is the reason the
statement path funnels three distinct reference errors into one wrong one.

---

## 3a. `INSTR` is broken too — and nobody had it on any list

§8's S-SD-3 originally proposed *assuming* the rest of the string engine was
clean, on the grounds that no silent row was on record. That assumption was
tested instead of trusted, and it was **wrong**:

| case | reference | zerobas |
|---|---|---|
| `INSTR(1,A$,"b")` | ` 2 ` | ` 2 ` ✅ |
| `INSTR(0,A$,"b")` | `Illegal function call` | `Illegal function call` ✅ |
| `INSTR(-1,A$,"b")` | `Illegal function call` | `Illegal function call` ✅ |
| `INSTR(256,A$,"b")` | `Illegal function call` | 🔴 **` 0 `** — silently "not found" |
| `INSTR(99999,A$,"b")` | **`Overflow`** | `illegal function call` |

`INSTR` has **half** the rule: it hand-rolls a `p < 1` test
([`basic/str-engine.asm:1277`](../basic/str-engine.asm:1277)) and has neither an
upper bound nor a stage-1 int16 gate. So `INSTR(256,…)` is a silent wrong
answer of exactly the D-MISS-2 kind, and it survived the SILENT-GAP sweep for
exactly the reason D-MISS-2 did.

⚠️ **"No row on record" is not a measurement.** This is the fifth slice running
whose calibration battery found a live defect in code that was not under test,
and the first where the defect was found *because a sign-off question was
answered by running the probe instead of by argument*.

`HEX$`/`OCT$` are clean: `HEX$(-1)` → `FFFF` and `OCT$(-1)` → `177777` (the
documented unsigned-16 reading) and both raise `Overflow` past int16, all
agreeing today. `STRING$`'s char code and `SPACE$(256)` also agree.

---

## 4. The design

Two shared helpers in **page 1**, beside `get_byte_arg`
([`basic/interp.asm:1382`](../basic/interp.asm:1382)):

```
eval_pos_arg:                       ; MID$'s position: 1..255
                call    eval_byte_arg
                or      a
                ret     nz
                jp      gb_illegal
eval_byte_arg:                      ; every other string-fn numeric argument: 0..255
                call    eval
                jp      get_byte_arg
```

Every call site then changes `call eval` → `call eval_byte_arg` (or
`eval_pos_arg`), which costs **zero bytes at the site**. Eight sites: `CHR$`,
`LEFT$`'s `n`, `RIGHT$`'s `n`, the `MID$` function's `p` and `n`, the `MID$`
statement's `p` and `m`, and `INSTR`'s `p`.

Three further edits, all in the low region — and **all three are deletions or
near-deletions**, which is why this slice's net effect on the tighter wall is
to *widen* it:

- the `MID$` statement's hand-rolled `bit 7,d` / `jp nz,ems_err_pop1` negative
  test is **deleted** (−5 B) — `eval_byte_arg` subsumes it and gets the error
  code right, which the hand-rolled test never did.
- `INSTR`'s two hand-rolled `p<1` blocks (`bit 7,b` … `jp ev_f_ifc` and
  `ld a,b`/`or c` … `jp ev_f_ifc`, plus their IX-restore dances) are **deleted**
  (−20 B) — `eval_pos_arg` subsumes both and adds the upper bound and the
  stage-1 gate they never had.
- `ems_range` (the sub-ROM tenant's `SH_ERR=3`, i.e. `p > LEN(a$)`) stops
  raising `stmt_error` and raises `Illegal function call` (+2 B).

### 4.1 Why the helpers, and why in page 1

`call eval` is **already present** at all seven sites. Folding `eval` and
`get_byte_arg` into one helper means the domain check rides in for free at the
site and is paid for once, centrally — and paying centrally lets it be paid on
the **other wall**. This is the opposite of the usual
[`generalisation-not-free-at-two-callers`](../MEMORY.md) result, and the reason
is that the shared helper *absorbs a call that was already there* rather than
adding one.

`get_byte_arg` already lives in page 1 and `str_fn_space` (low region) already
calls it, so the direction is proven, not new.

### 4.2 Registers — why no guard bytes are needed

`get_int16_checked` **guards HL** across the conversion (its own header says so,
`basic/interp.asm:1360`) and `get_byte_arg` returns `D=0, E=byte` with only `A`
clobbered. Every site keeps its token cursor in `HL` and either has `BC` on the
stack or dead. `IX` is not an issue: `str_fn_space` already does exactly
`eval` + `get_byte_arg` inside the same `$FF` dispatch context, and `SPACE$`
agrees with the reference today.

**This is where the roadmap's cost estimate went wrong** — it assumed
push/pop guards around each call.

### 4.3 An abort mid-`LEFT$` leaks nothing

`LEFT$`/`RIGHT$`/`MID$` snapshot the source into a temp before evaluating the
numeric argument, so a raise now unwinds out of a half-built expression. That is
safe: `raise_error` resets `SP` from `SAVSTK` (`4d35b6d`), and `exec_stmt`
empties the temp-descriptor stack at **every** statement boundary
([`basic/interp.asm:147`](../basic/interp.asm:147)), so the orphaned temp's slot
and heap body are both reclaimed at the next statement.

### 4.4 Why this had to wait for `4d35b6d`

All seven sites are inside the **expression evaluator**, far below
statement-handler depth. Before the abort-depth fix, `jp raise_error` from
there printed and `ret`ed into the caller's frame — the exact defect that made
`WIDTH 300` corrupt the screen. Landing this slice first would have given the
right `ERR` under `ON ERROR` and trailing junk without it.

---

## 5. Cost and funding — MEASURED, and the roadmap was wrong

Prototyped on `4d35b6d` in an isolated worktree, built from **clean**:

| wall | before | after | delta |
|---|---|---|---|
| page-0 low region | 7 B free | **30 B free** | **+23 B** |
| main page 1 | 44 B free | **30 B free** | −14 B |

**No promotion. No carve.** The low region — the tighter of the two walls, and
the one this slice lands in — comes out with *four times* the room it went in
with, because the three deletions in §4 dwarf the two added bytes. Both walls
land on 30 B, which is the healthiest the tree has been in several slices.

⚠️ **Adding `INSTR` to the slice made it CHEAPER, not more expensive** (+3 B →
+23 B on the low region). Its 20 B of hand-rolled half-a-rule is deleted, and
the shared helper it is redirected to was already being paid for. The instinct
to defer a newly-found defect to keep a slice small would have cost 20 B here.

⚠️ **The roadmap's funding premise was wrong by a wide margin and should be
corrected when this lands.** [`TODO.md`](../TODO.md) and
[`spec-basic-abort-depth.md`](spec-basic-abort-depth.md) §5 both record that
D-MISS-2 needs "four to five new `call get_byte_arg`s", "a page-1 cost of
≈45–50 B against 44 B free", and "one small carve". The real shape is 14 B on
page 1, 3 B *back* in the low region, and nothing to fund. Two independent
reasons:

1. it assumed register-guard bytes that §4.2 shows are not needed;
2. it costed *added* calls, missing that `call eval` was already at every site,
   so the helper replaces rather than adds.

The first naive shape — a plain `call get_byte_arg` bolted after each `eval`,
plus an inline zero-test at the two position sites — was also built and
measured: **+26 B, all of it in the low region**, a 19 B overrun needing a
promotion. That is the version the roadmap was estimating, and it is 49 B worse
on the wall that matters.

For the record, since the roadmap's promotion plan would have been acted on:
`promote_scout`'s per-label sizes are **label-to-label, not routine sizes**, so
`str_fn_str` "26 B" is really 66 B once its own `sfs_*` labels are counted. A
promotion sized off that listing would have been picked wrong. Nothing needs
promoting now, but the next slice that reaches for the tool should know.

⚠️ The lean cart is **byte-identical** (`check_reloc.py`: "lean `basic.rom`
byte-identical"), so `LEAN_SHA256` does not move.

---

## 6. The gate

`probes/basic/basic_probe_str_domain.py`, target `make str-domain-acceptance`
(`str-domain-characterize` for the ungated measurement run). 89 rows:

- **`ctl` (7) — read FIRST and separately.** `LEN(A$)` proves the readout;
  `ASC("")` proves an abort is reachable at evaluator depth; `STRING$`/`SPACE$`
  are the family members that already check and are the working reference
  implementation of the two-stage rule. **If a control diverges the probe exits
  non-zero and says no other row in the run is readable as a D-MISS-2 finding.**
- **`in` (23) — the anti-over-rejection half.** A domain check's failure mode is
  rejecting what it should accept, and a matrix of only out-of-range rows goes
  green on an implementation that raises `Illegal function call` for
  everything. These rows are not padding — and §6.2 shows all 23 survive
  falsification, which is precisely why they cannot be the gate's evidence and
  precisely why they have to be in it.
- **`out` (24)** — the rejected domain, both error kinds, on all four functions.
- **`bnd` (7)** — the int16 boundary (§2.1), four of them on the callers that
  already check, as calibration.
- **`ord` (4)** — evaluation order and precedence vs `Type mismatch` and vs the
  deferred syntax error (§2.4).
- **`stmt` (12)** — the `MID$` statement surface (§3).
- **`ext` (12)** — the rest of the string engine's numeric arguments (§3a).
  This battery exists because a sign-off question was answered by running it,
  and it found `INSTR`.

Conventions inherited from `basic_probe_abort_depth.py`, each for a reason that
already bit someone: **no row may arm `ON ERROR`** (a handler selects the trap
branch, the one that was always correct); **every value row is
bracket-delimited** (abort junk can be whitespace, which a right-stripped scrape
reads as clean); **`WIDTH 40` is pinned and the subject is carried in `A$`** (the
two machines boot at different widths, and a wrapped echo breaks the
`screen_tail` readout silently); **message case is folded** (the documented
two-spelling divergence at `basic/arrays.asm:44`).

### 6.1 Results

The §4 design was built and run in an isolated worktree **before** this spec was
written, so none of §5's numbers was ever an estimate; the landed tree then
reproduced them exactly (low region `__MEAS_LOW_END` $3FE2 both times).

- `make str-domain-acceptance` — **89/89**, every battery, including all 23
  in-domain rows.
- pre-fix baseline on `4d35b6d` — **48/89**, `--boot-per-case`, matching the
  batched+self-healed run row for row.
- falsified — **51/89** (§6.2).

### 6.2 Falsification — ✅ RUN, 89/89 → 51/89

Per [`gate-can-be-green-while-measuring-nothing`](../MEMORY.md). All eight call
sites reverted to plain `call eval`, rebuilt **from clean**: the gate drops to
**51/89**, so 38 rows are held up by the eight call sites alone.

⚠️ **The wall does NOT move under this falsification** (30 B / 30 B either way),
unlike the abort-depth one. `call eval` and `call eval_byte_arg` are both 3 B
and the helpers stay assembled, so "the low region went back" is *not* available
here as proof the code left the image. The evidence is the asserted count of
reverted sites plus the red gate — worth knowing before anyone tries to
falsify this the way the previous slice was falsified.

**Every survivor is explainable, and that is the real check:**

| battery | survives | why it must |
|---|---|---|
| `ctl` | 7/7 | exercises `STRING$`/`SPACE$`/`ASC`, which this slice never touches |
| `in` | 23/23 | **in-domain rows pass with and without the checks** — which is exactly why they can never be the gate's evidence, and exactly why they must be there |
| `bnd` | 4/7 | the 4 survivors are all `STRING$`/`SPACE$` (pre-existing `get_byte_arg` callers); the 3 that die are the new `LEFT$`/`MID$` ones |
| `ord` | 1/4 | `ord-type` only — `Type mismatch` is checked before the domain and is untouched |
| `ext` | 8/12 | the 4 that die are all four `INSTR` rows |
| `stmt` | 8/12 | the 4 that die need the reverted sites; the other 5 non-in-domain survivors pass through `ems_range`, which this falsification deliberately leaves in |

Two of those rows are worth calling out. **`ext-instr-0` and `ext-instr-neg`
PASSED in the true pre-fix baseline and FAIL under falsification** — because the
hand-rolled `p<1` tests are deleted in the landed tree, so reverting the call
site leaves `INSTR` with no check at all. That asymmetry is the proof that the
call site, not the deletion, is doing the work. And the surviving `stmt-p-*`
rows show `ems_range` contributing independently of the call sites, which is why
§4 lists it as its own edit rather than as a consequence.

### 6.3 Regressions — and the three that are EXPECTED to go red

Run on the prototype: `abort-acceptance` **23/23**, `intarg-acceptance`
**ALL PASS**, `string-acceptance` five of six batteries PASS, `unit-test`
**52/53**. Three gates go red **because this slice closes a divergence they
record**, and each needs an edit as part of the slice — none is a regression:

1. **`missing-acceptance`** — its stale-marker check fires: all eight `d2-*`
   rows recorded as expected-divergent now AGREE. Expected-divergent count drops
   **17 → 9**. Exactly what happened when the abort-depth slice landed; the
   marker is doing its job. *Edit: drop the eight from `XDIVERGENT`.*
2. **`string-acceptance` → `basic_probe_mid_stmt.py`** — it hard-asserts the
   recorded divergence *"reference `Illegal function call` vs zerobas
   `syntax error`"* for `n > LEN(A$)`. zerobas now says `Illegal function call`
   and matches. *Edit: turn that asserted divergence into an asserted agreement.*
   ⚠️ Its other nine oracle rows and the `A$ unchanged` invariant all still pass,
   which is the evidence that §4's `ems_range` change corrected the error code
   without disturbing the overwrite semantics.
3. **`tests/test_str_fn.py`** — `INSTR(0,"HELLO","L")` now runs away in the host
   harness (`runaway: 2000001 steps`). Not a defect: the harness calls `eval`
   directly, bypassing `exec_stmt`, so `SAVSTK` is never set and `raise_error`'s
   `ld sp,(SAVSTK)` has nothing to land on. `INSTR`'s `p<1` moves from the
   *deferred* `ev_f_ifc` convention to the immediate `raise_error` one, which
   this harness structurally cannot model. **There is direct precedent**: when
   D-F2-2 moved `SPACE$`/`STRING$` onto `get_byte_arg`, those out-of-domain rows
   were removed from this same file with a comment pointing at the openMSX gate
   ([`tests/test_str_fn.py:198`](../tests/test_str_fn.py:198)). *Edit: same
   treatment, pointing at `make str-domain-acceptance`.*

⚠️ Note what #3 means for coverage: **no host unit test can cover any row in this
slice**, because every one of them ends in `raise_error`. The openMSX
differential is the only instrument, which is why §6.2's falsification is not
optional.

---

## 7. Out of scope

- **`DEF FN`/`FN`** — an arc, not a slice.
- **The `CLEAR` string-pool partition** — its own spec, its own gate.
- **The two spellings of one message** (`overflow` vs `Overflow`) — the
  deliberate house-style/arrays split at `basic/arrays.asm:44`. Folded in the
  comparison, not a finding.
- **`WIDTH 300`'s valid domain** — still open from the abort-depth slice.
- **`VAL`** — takes a string, so it has no numeric argument domain to check.
- **`HEX$`/`OCT$`/`BIN$`** — measured clean (§3a). `BIN$` was gated by its own
  slice.

---

## 8. Sign-off questions

- **S-SD-1 — the two helpers, and putting them in page 1.** §4. Recommended:
  take it. Measured at **+23 B** on the low-region wall and −14 B on page 1, it
  needs no funding at all, and the naive alternative was built and is 49 B worse
  where it hurts. The one thing to weigh is that page 1 goes to 30 B free — but
  the low region, which is the wall that has actually been binding, goes from
  7 B to 30 B, so the tree ends up more balanced and with more total headroom
  (51 B → 60 B) than it started.

- **S-SD-2 — is the `MID$` STATEMENT in scope?** §3. Recommended: **yes, fold
  it in.** It is the same two arguments and the same rule, two of its rows are
  silent wrong answers of exactly the class this slice exists to close, and it
  costs −3 B (it is where both deletions live). Splitting it out would leave the
  verb half-fixed and would need its own gate for nine rows. The argument
  against is that it also changes `p > LEN(a$)` from `syntax error` to
  `Illegal function call`, which is a behaviour change in a case that is not
  strictly an argument-*domain* error — measured as `Illegal function call` on
  the reference (`stmt-p-past`, `stmt-p-255`), so it is a correction either way.

- **S-SD-3 — ✅ ANSWERED BY MEASUREMENT, not left as a question.** The `ext`
  battery was written and run rather than assumed, and it found `INSTR`
  silently wrong (§3a). **Recommended: fold `INSTR` in** — it is the same rule,
  the same helper, it is a silent wrong answer of exactly this class, and it
  makes the slice 20 B *cheaper*. Folding it in is what lets this slice claim
  to close the class rather than most of it.

- **S-SD-4 — is `MID$`-statement `p > LEN(a$)` really an argument-domain
  error?** It is the one case where the new error is raised by the sub-ROM
  tenant rather than by the coercion, and it is a *state*-dependent rejection
  (it depends on `a$`), not a domain one. The reference says `Illegal function
  call` for it (`stmt-p-past`, `stmt-p-255`), so changing it is a correction —
  but it is the one edit in this slice whose justification is "the reference
  does this" rather than "this is the argument's domain". Flagged rather than
  hidden. Recommended: take it; it is 2 B and it is measured.
