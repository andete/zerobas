# The ARRAY-LVALUE target surface (MSX1, measured) — D-ARYLV carve scout

> ✅ **IMPLEMENTED 2026-08-08.** The zerobas column below is the **before**
> reading, at `112f569`. All 12 divergent array-lvalue rows here (and the 6 filed
> by `readvar`/`inputary`) are now green: `make arylv-acceptance` **16/16 + 2
> deferred**, `readvar-acceptance` **24/24**, `inputary-acceptance` **7/7**.
> As-built, walls and knives: [`spec-basic-arylv.md`](spec-basic-arylv.md) §11.
> 🎯 **Every byte prediction in §5 was exact** — three helper sizes, five site
> deltas, both walls. §5.5's *"the real number comes from a build"* still stands
> as the rule; this is what it looks like when a calibrated instrument is right.

Measured 2026-08-08 against **two** references — the Philips VG-8020 and the
National CF-3300 — by `probes/basic/basic_probe_arylv.py`
(`make arylv-characterize`). **Both references agree on all 18 rows**, so every
row has an oracle; the probe counts and prints rows where they split, and that
count is **0**.

This is the SCOUT for the residual
[`TODO.md`](../TODO.md) §"Open — standing residuals" carries as *"an array
element is not acceptable as an lvalue target to `READ` or `INPUT`"*. That item
already had six measured rows
([`readvar-msx1-characterization.md`](readvar-msx1-characterization.md),
[`inputary-msx1-characterization.md`](inputary-msx1-characterization.md)) and a
**price question**: four parse sites against a main page-1 wall with 126 B free,
*"a scout question, not an arithmetic one"*. This document answers both halves —
how WIDE the surface is, and what it COSTS.

Clean-room: observed screen output only; both reference ROMs are black boxes.

The reading is the `[...]` span printed **by the RUN**, taken from the screen tail
after `RUN` — never the whole screen (D-READVAR §3: the echo of
`PRINT"[";A;"]"` contains a `[`, and matching it turns "printed nothing" into a
value-shaped artifact).

---

## 1. The rows

Each program is typed as numbered lines, then `RUN`; the `INPUT` rows inject
their **response** as a further line, which lands while the read is blocked.

| row | program (after `DIM`, where present) | both references | zerobas @ `112f569` |
|---|---|---|---|
| `c.read` | `DATA 7` / `READ A` | ` 7 ` | ` 7 ` 🟢 **positive control** |
| `c.let` | `DIM A(3)` / `A(1)=7` | ` 7 ` | ` 7 ` 🟢 **positive control** |
| `c.for` | `FOR A=1 TO 3` / `NEXT` | ` 4 ` | ` 4 ` 🟢 **positive control** |
| `r.aryvar` | `I=1` / `READ A(I)` | ` 7 ` | **Syntax error** |
| `r.aryexpr` | `READ A(1+1)` | ` 7 ` | **Syntax error** |
| `r.arypct` | `DIM A%(3)` / `I=1` / `READ A%(I)` | ` 7 ` | **Syntax error** |
| `r.arystrv` | `DIM A$(3)` / `I=1` / `READ A$(I)` | `HI` | **Syntax error** |
| `r.ary2d` | `DIM A(3,3)` / `READ A(1,2)` | ` 7 ` | **Syntax error** |
| `r.aryoor` | `DIM A(3)` / `READ A(9)` | **Subscript out of range** | **Syntax error** |
| `r.mix` | `READ A(1),B` | ` 7  8 ` | **Syntax error** |
| `r.mixrev` | `READ B,A(1)` | ` 7  8 ` | **Syntax error** |
| `i.aryvar` | `I=1` / `INPUT A(I)` | ` 7 ` | **Syntax error** |
| `i.ary2d` | `DIM A(3,3)` / `INPUT A(1,2)` | ` 7 ` | **Syntax error** |
| `i.aryoor` | `DIM A(3)` / `INPUT A(9)` | **Subscript out of range** | **Syntax error** |
| `i.mix` | `INPUT A(1),B` | ` 7  8 ` | **Syntax error** |
| `f.ary` | `DIM A(3)` / `FOR A(1)=1 TO 3` | **Syntax error** | **Syntax error** ✅ |
| `f.two` | `FOR AB=1 TO 3` / `NEXT` | ` 4 ` | **Syntax error** |
| `f.pct` | `FOR A%=1 TO 3` / `NEXT` | ` 4 ` | **Syntax error** |

**4/18 agree, 14 diverge, 0 rows without an oracle.**

Together with the six rows already filed (`a.ary`, `a.arystr`, `i.ary`,
`i.arystr`, `i.lineary`, `i.arynodim`) the array-lvalue class is **18 measured
divergent rows**, not six.

---

## 2. What the scout was sent to find, and what it found

### 2.1 🔴 `FOR` IS **NOT** A FIFTH ARRAY PARSE SITE — and the row that says so AGREES

The scout was asked whether `FOR A(1)=…` diverges, because `ex_for`
([`basic/program.asm`](../basic/program.asm)) still parses its loop variable with
the **single-letter shim** `ex_read` stopped using at D-READVAR: one `upcase`d
char into `FOR_CUR`, then `var_set`. If it diverged, the array work would have
five parse sites, not four.

**It does not.** `f.ary` is `Syntax error` on the VG-8020 *and* on the CF-3300.
An MSX `FOR` does not take an array element, so refusing it is correct, and the
array-lvalue slice must **keep** refusing it.

⚠️ **This claim rests on the REFERENCE column alone, and it has to.** zerobas also
answers `Syntax error` — but zerobas answers `Syntax error` to `FOR AB=` as well,
so its agreement here is worth nothing on its own
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]: a row whose answer is an
error passes a dead subject). The finding is *"both references refuse it"*, which
is a statement about the language, and `f.ary` therefore becomes a **negative
control** for this slice and a **pin** for any later `FOR` slice.

### 2.2 🔴 …BUT `FOR` CARRIES A D-READVAR-CLASS DEFECT OF ITS OWN, AND NOBODY HAD LOOKED

`f.two` (`FOR AB=1 TO 3`) and `f.pct` (`FOR A%=1 TO 3`) read ` 4 ` on both
references and are `Syntax error` here. That is not an array question at all: it
is **exactly the defect D-READVAR fixed in `ex_read`**, still live in `ex_for`,
in a verb no row of that slice re-checked. Two rows, one shim, a separate
residual — filed, not taken here.

The two findings are opposite in direction and were produced by the same three
rows. Asking only *"does `FOR A(1)=` diverge?"* would have returned "no" and
closed the question with the larger defect untouched.

### 2.3 The subscript is a full EXPRESSION, and the RANK is not 1

`r.aryvar` (`A(I)`), `r.aryexpr` (`A(1+1)`) and `r.ary2d` (`A(1,2)`) all read the
value on both references. Every one of the six previously filed rows uses the
literal form `A(1)`, so none of them could say this. **A fix that special-cases a
literal subscript, or a single index, is measurably wrong** — the target parse has
to hand the whole subscript list to the array engine, which is what
`ary_op0_resolve` already does for `LET` and `SWAP`.

### 2.4 🎯 The ERROR face: `Subscript out of range`, not `Syntax error`

`r.aryoor` / `i.aryoor` are the only rows here whose reference answer is an
**error**, and it is a *different* error from the one zerobas gives. This matters
more than it looks: a fix that routed a failed resolve to `stmt_error` would
answer `Syntax error` — which is what the tree says **today**, so the row would
score *"unchanged"* and read as untouched rather than as wrong. Without this row
the fix has a whole failure mode whose right and wrong answers are indistinguishable
from the outside.

### 2.5 POSITION in the variable list is two rows, not one

`r.mix` (`READ A(1),B`, array at the **head**) and `r.mixrev` (`READ B,A(1)`,
array as a **continuation** reached through the comma loop) both diverge. They are
two rows because one row could not separate them, and because the continuation
form is the one where a scalar allocation has already happened before the array
target is resolved.

### 2.6 The type axis — added because designing a KNIFE found the hole

`r.arypct` (`DIM A%(3)` / `I=1` / `READ A%(I)`) and `r.arystrv` (the string
sibling) were **not** in the first 16-row run. They were added after the knife
set was drafted, because K-AL4 below — substituting `VARTYPE` for `ARY_TYPE` in
the store — was predicted to redden *"every numeric array row"* and on the
original row set would have reddened **none**: with an untyped `A(I)` both cells
hold the same DEFtbl double, so the substitution is invisible. `A%(I)` is the row
that makes the difference observable, and re-measuring cost one probe run.

⚠️ Recorded as a **denominator hole found by writing a knife, not by writing the
gate** ([[a-hand-listed-denominator-is-a-scope-claim]]). The first 16 rows would
have shipped a gate that could not tell the two cells apart.

---

## 3. 🔴 "FOUR PARSE SITES" WAS A HAND-LIST, AND A WALK FINDS MORE

The filed item says the fix has four target-parse sites. That number is the count
of sites **measured to diverge**, not the count of sites that parse an lvalue
target. Walking every caller of `var_name_key` outside `vars.asm` finds these
lvalue-shaped ones:

| site | file | in this slice? |
|---|---|---|
| `exr_lp` (`READ`) | [`basic/program.asm`](../basic/program.asm) | ✅ measured, IN |
| `inpc_vloop` (`INPUT`, numeric) | [`basic/input.asm:97`](../basic/input.asm) | ✅ measured, IN |
| `inpc_vstr` (`INPUT`, string) | [`basic/input.asm:117`](../basic/input.asm) | ✅ measured, IN |
| `inpc_line` (`LINE INPUT`) | [`basic/input.asm:187`](../basic/input.asm) | ✅ measured, IN |
| `ex_for` (`FOR`) | [`basic/program.asm`](../basic/program.asm) | ✅ measured — **OUT, correctly** (§2.1) |
| `inp_readvar` (`INPUT #n` / `LINE INPUT #n`) | [`basic/files.asm:702`](../basic/files.asm) | ⚠️ **UNMEASURED** |
| `FIELD` target | [`basic/field.asm:194`](../basic/field.asm) | ⚠️ **UNMEASURED** |
| `LSET` / `RSET` target | [`basic/field.asm:283`](../basic/field.asm) | ⚠️ **UNMEASURED** |
| `MID$(…)=` lvalue | [`basic/str-engine.asm:957`](../basic/str-engine.asm) | ⚠️ **UNMEASURED** — its own header already says *"array lvalues deferred"* |
| `sw_operand` (`SWAP`) | [`basic/missing.asm:425`](../basic/missing.asm) | ✅ **ALREADY HANDLES ARRAYS** — §4 |

The four unmeasured rows need a file/`FIELD` fixture rather than a bare boot, so
they are not free the way this battery's rows were. They are **named, not
measured, and not silently folded into the scope**.

---

## 4. 🎯 THE FIX ALREADY EXISTS IN THIS TREE, TWICE

`c.let` is green: `A(1)=7` works. So does `SWAP A,Q(0)`. zerobas therefore
**already accepts an array element as an lvalue target** — in `LET`
(`ex_let_arr` / `ex_let_arr_str`, [`basic/arrays.asm`](../basic/arrays.asm)) and
in `SWAP` (`sw_operand` / `sw_array`, [`basic/missing.asm`](../basic/missing.asm))
— and refuses it in `READ`, `INPUT` and `LINE INPUT`. This is an internal
inconsistency, not a missing capability, and it is why `c.let` is a positive
control rather than a curiosity: it is the row that says every red row above is a
missing **parse**, not a missing **store**
([[row-with-two-candidate-causes]]).

`sw_operand` is the shape to copy. It does, in order: `var_str_type` → keep the
mode → `var_name_key` → pick the type (mode 1 → string, else `VARTYPE`) → peek
`(` → `ary_op0_resolve` → `jp nz,fp_runtime_error`. Its own header already records
the two measured behaviours this slice needs: *"`SWAP A,Q(0)` on an undimensioned
Q"* auto-dims, and *"`SWAP A,Q(9)` on `DIM Q(2)` is Subscript out of range"* —
which is `r.aryoor`'s oracle, already shipped in another verb.

---

## 5. The carve scout — numbers

All spans off `build/basic-reloc.sym` from a clean
`rm -rf build && make basic-reloc` at `112f569`; walls printed by that build.

### 5.1 The walls

| wall | free at `112f569` |
|---|---|
| main low region (`$2812-$3FFF`) | **3 B** |
| **main page 1 (`$4000-$7FFF`)** | **126 B** |
| sub page 0 | 3769 B |
| sub page 1 | 1483 B |

🔴 **THE TWO REGIONS SPLIT THE FOUR SITES, AND THAT IS THE WHOLE PRICE QUESTION.**
`basic/program.asm` (`ex_read`) is **page 1**. `basic/input.asm` — all three
`INPUT` sites — is the **LOW REGION**, which has **3 bytes free**. So *"126 B free"*
is not the wall three of the four sites are measured against. The regions are
co-mapped slot-0 pages and a low-region routine may `call` into page 1 freely
(`inpc_vloop` already calls `var_name_key`, `var_store_fac` and `str_set_key`,
all page 1), so the shape that fits is: **put the shared code in page 1 and let
the low-region sites shrink**.

### 5.2 The estimator, calibrated before it is used

Every byte below is hand-counted from the source. Before quoting a hand count for
code that does not exist, the same counter was run over code that does, and
checked against the `.sym`:

| routine | hand-count | `.sym` span | |
|---|---|---|---|
| `exr_lp` | 49 | **49** | ✅ |
| `exr_str` | 11 | **11** | ✅ |
| `inpc_vloop` | 45 | **45** | ✅ |
| `inpc_vstr` | 22 | **22** | ✅ |
| `inpc_line` | 53 | **53** | ✅ |
| `ex_let_arr` | 65 | **65** | ✅ |
| `ex_let_arr_str` | 56 | **56** | ✅ |
| `sw_array` | 12 | **12** | ✅ |

**8/8 exact over 313 B**, and those eight are the very routines the change edits
or copies. This is what makes §5.4 a bound with a stated instrument rather than a
guess ([[filed-justification-is-a-claim]]).

### 5.3 What the four sites can actually SHARE — and what they cannot

They differ in real ways, and a single shared head would be a prediction:

* `exr_lp` stores from a **DATA item** (`read_one_value`), `inpc_vloop`/`inpc_vstr`
  from a **typed console field** (`read_into_strscr`), `inpc_line` from a **whole
  line** and has no variable list at all.
* `exr_lp` is **page 1**; the other three are **low region**.
* The *store* differs by TYPE (numeric / string), and independently by TARGET
  FORM (scalar key / element address) — a 2 × 2, of which the four sites use
  three combinations.

So the sharing is **not one head; it is one head and two stores**, and the split
falls on the type axis, not on the verb axis:

| helper | what it is | used by |
|---|---|---|
| `tgt_parse` | name + type suffix + optional `(subscripts)` → key, or element address | all four sites |
| `tgt_store_num` | int16 in `DE` → scalar key *or* element address | `exr_lp` numeric, `inpc_vloop` |
| `tgt_store_str` | `STRSCR` bytes → scalar key *or* element address | `exr_str`, `inpc_vstr`, `inpc_line` |

The store is what the four sites do NOT share, and folding it into the parse is
the mistake this table exists to prevent.

### 5.4 The cost — a BOUND, with the twin named for every part

New page-1 code (`basic/vars.asm`, which is **617 B, 49 of 49 labels in page 1**):

| helper | bytes | twin the number comes from |
|---|---|---|
| `tgt_parse` | **32** | `sw_operand`'s equivalent span is **28 B** shipped; `tgt_parse` adds a 4-B scalar sentinel write SWAP does not need (SWAP always yields an address) |
| `tgt_store_num` | **24** | its array arm is `ex_let_arr`'s own `ld a,(ARY_TYPE)` + `ary_store_write` tail |
| `tgt_store_str` | **30** | its array arm (12 B) is `ex_let_arr_str`'s shipped tail **byte for byte**, `call`+`pop hl` → `jp` |
| | **86 B** | |

Per-site deltas (each replaced sequence hand-counted and `.sym`-checked in §5.2):

| site | region | today | after | Δ |
|---|---|---|---|---|
| `exr_lp` numeric store (`ld a,2`/`ld (FACTYP),a`/`ld a,(VARTYPE)`/`call var_store_fac`) | p1 | 11 | 3 | **−8** |
| `exr_str` string store (`strscr_desc`/`ex de,hl`/`str_set_key`) | p1 | 7 | 3 | **−4** |
| `exr_lp` resolve abort (`jp nz,fp_runtime_error`) | p1 | 0 | 3 | **+3** |
| `inpc_vloop` numeric store | low | 11 | 3 | **−8** |
| `inpc_vloop` resolve abort | low | 0 | 3 | **+3** |
| `inpc_vstr` string store | low | 7 | 3 | **−4** |
| `inpc_vstr` resolve abort | low | 0 | 3 | **+3** |
| `inpc_line` string store | low | 7 | 3 | **−4** |
| `inpc_line` resolve abort | low | 0 | 3 | **+3** |

| region | free now | Δ | free after |
|---|---|---|---|
| **main page 1** | 126 B | **+77 B used** | **≈49 B** |
| **main low region** | 3 B | **−7 B used (FREED)** | **≈10 B** |

RAM: **+2 B**, `TGT_ADDR` at `$E555` — the 5-byte gap between `RDV_MODE` (`$E554`)
and `GFX_DSCALE` (`$E55A`), inside the same one-statement-at-a-time aliasing
window `RDV_VAL`/`RDV_ST`/`RDV_MODE` already rely on (a `READ`/`INPUT` and a
`DRAW` are never in flight together). No wall moves; the slice adds its own
`IF TGT_ADDR + 2 > GFX_DSCALE` assert next to the two already there.

### 5.5 ✅ VERDICT: **GO. No carve, and it relieves the tighter wall.**

**+77 B against 126 B free, ~49 B to spare — one slice, not two.** And the low
region, which has **3 bytes**, ends up with about **10**: every low-region site
gets *smaller*, because the sequences the helpers replace are longer than a
`call`. This is the move
[[rom-region-structure-review]] names — *carve where you can, then promote to
where it hurts* — arriving for free, because the shared code has to live in page 1
anyway for the one page-1 site.

⚠️ **These are byte counts of code that does not exist.** The instrument is
calibrated (§5.2, 8/8 exact) and every part is anchored to a named shipped twin
(§5.4), but the real number comes from a build. Recorded as a **bound**, not a
measured cost.

The carve reservoir, had one been needed and it is not:
`basic/program.asm` **2407 B** leaves page 1 if the file moves;
`basic/vars.asm` **617 B**.

---

## 6. What this document does NOT do

⚠️ **It measures the SURFACE and prices the fix. No byte has moved.**
`make arylv-characterize` is a characterization target and deliberately **not** an
acceptance gate, the same disposition as `inputary-characterize`: 14 of its 18
rows can only be red until the work lands, and a row that can only ever be red is
doc debt, not a gate. The design, the constraints, the knives and the gate live in
[`spec-basic-arylv.md`](spec-basic-arylv.md).

**All four ROMs hash identically to `112f569`** (`basic-reloc.rom 38d79ffd…`,
`sub.rom 33af21eb…`, `disk.rom 2c630d3d…`, `zerobas-main-eu.rom 87afd9ea…`) and
all four walls are unmoved (low **3 B**, page 1 **126 B**, sub p0 **3769 B**, sub
p1 **1483 B**), which is the whole claim a measurement-only change has to
support. `unit-test` **59/59**, `deadcode` main **1567/289 → 0** and sub
**1522/102 → 0** (+1 allowlisted), `latch-check` **16/16** — all at their filed
values.

### 6.1 The apparatus was exercised on every path it will be used on

A probe's failure branches only ever run under a knife, so a latent traceback
there is invisible to every green run and to the whole corpus (D-RUNTAIL
§6.3, D-CASOPEN §7.3). All four paths of the new probe were run before this
document was committed, not left for the slice that will depend on them:

| path | how | result |
|---|---|---|
| three sides, all rows | `make arylv-characterize` | 18 rows, §1 |
| the `make` target itself, with `ONLY=` / `SIDES=` | `make arylv-characterize ONLY=c.read SIDES=zb` | rc 0, one row |
| ONE side (no agreement verdict) | `--sides zb` | rc 0, `CHARACTERIZATION (one side)` |
| `--gate`, the acceptance form the fix will use | `--only c.read,r.aryvar --sides vg8020,zb --gate` | **rc 1**, one `DIFF` |
| **exit 2** — a positive control failing | `CONTROL_WANT` monkeypatched in memory (no repo file touched) | **rc 2**, complete report, and **`probe_report.parse()` reads all 3 rows** |

🔴 **The exit-2 run found one property a knife runner has to expect: the failed
control is printed TWICE** — once as its `FAIL` row, once again in the `....`
not-scored block — so a runner keying rows by label collides on that one label.
Benign (both rows read the same `results[side][control]` and can never disagree)
and **pre-existing** — `basic_probe_readvar.py` and `basic_probe_inputary.py`
have the identical branch. Written down here rather than rediscovered by the
runner that trips on it.

---

## 7. The static counters this moves, predicted and measured

| gate | before | predicted | measured |
|---|---|---|---|
| `audit-citations` files swept | 736 | **739** (the probe + this document + the spec — the sweep walks every file, not just `.py`) | **739** ✅ |
| `audit-citations` basic provenance-bearing | 189 | **190** (+1 per real `probes/basic/*.py`) | **190** ✅ |
| `injector-check` files | 337 | **338** | **338** ✅ |
| `rowshape-check` walked / report-row / in-contract / conform / violations | 178 / 31 / 7 / 7 / 0 | 179 / 32 / 8 / 8 / 0 | **179 / 32 / 8 / 8 / 0** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |

The swept count is predicted from the sweep's own definition (*every file walked*,
not *every new `.py`*) rather than from the thing being added — which is the
correction D-INPUTARY's own §"static counters" section had to record after
predicting 735 and measuring 736
([[a-count-is-predicted-by-reading-its-definition]]).
