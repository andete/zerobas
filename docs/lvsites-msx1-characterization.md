# The four lvalue parse sites D-ARYLV did NOT measure (MSX1, measured)

Measured 2026-08-08 by `probes/basic/basic_probe_lvsites.py`
(`make lvsites-characterize`), 10 rows. This closes the scope gap
[`spec-basic-arylv.md`](spec-basic-arylv.md) §3 opened and
[`arylv-msx1-scout.md`](arylv-msx1-scout.md) §3 tabulated: D-ARYLV's *"four parse
sites"* was the count of sites **measured to diverge**, not the count of sites
that parse an lvalue target, and a walk of `var_name_key`'s callers outside
`vars.asm` found four more that were never checked against an array element
([[a-hand-listed-denominator-is-a-scope-claim]]).

Clean-room: observed screen output only; both reference ROMs are black boxes.

---

## 0. 🔴 READ THIS BEFORE THE TABLE — the oracle here is WEAKER than D-ARYLV's

Every row D-ARYLV measured had **two** independent references agreeing.
**Eight of these ten have one.** `INPUT #n`, `FIELD` and `LSET`/`RSET` are Disk
BASIC, and a diskless Philips VG-8020 answers `Syntax error` to every one of
those words — it cannot express the question, so recording its answer would
manufacture an agreement out of an absent disk controller. Those rows rest on the
National CF-3300 alone. The probe prints `[ONE REFERENCE ONLY]` per row and
counts them; it never says "both references agree" about a row that has one.

This is a stated limit, not a defect in the measurement — but a single-reference
row is a weaker claim, and any slice acting on these rows inherits that.

---

## 1. The rows

| row | statement under test | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `m.ctl` | `A$="HELLO"` / `MID$(A$,1,2)="XY"` | `XYLLO` | `XYLLO` | `XYLLO` 🟢 **control** |
| `m.ary` | `MID$(A$(1),1,2)="XY"` | `XYLLO` | `XYLLO` | **Syntax error** 🔴 |
| `f.ctl` | `INPUT#1,A$` | *no disk* | `HI` | `HI` 🟢 **control** |
| `f.ary` | `INPUT#1,A$(1)` | *no disk* | `HI` | **Syntax error** 🔴 |
| `d.ctl` | `FIELD#1,10 AS A$` | *no disk* | `OK` | `OK` 🟢 **control** |
| `d.ary` | `FIELD#1,10 AS A$(1)` | *no disk* | `OK` | **Syntax error** 🔴 |
| `s.ctl` | `A$="XXXXX"` / `LSET A$="HI"` (**not** FIELDed) | *no disk* | `HI   ` | **Syntax error** 🔴 |
| `s.ary` | `LSET A$(1)="HI"` (not FIELDed) | *no disk* | `HI   ` | **Syntax error** ⚠️ |
| `s.fld` | `FIELD#1,10 AS A$` / `LSET A$="HI"` | *no disk* | `HI        ` | `HI        ` 🟢 **control** |
| `s.fldary` | `FIELD#1,10 AS A$(1)` / `LSET A$(1)="HI"` | *no disk* | `HI        ` | **Syntax error** 🔴 |

**4/10 match their reference, 6 diverge, 0 rows without a reference.**

---

## 2. All four sites DO diverge — the class was real

| site | file | verdict |
|---|---|---|
| `ex_mid_stmt` — `MID$(…)=` | [`basic/str-engine.asm:957`](../basic/str-engine.asm) | 🔴 diverges, **two references** |
| `inp_readvar` — `INPUT #n` | [`basic/files.asm:702`](../basic/files.asm) | 🔴 diverges, one reference |
| `ex_field` — `FIELD` | [`basic/field.asm:194`](../basic/field.asm) | 🔴 diverges, one reference |
| `lrset_common` — `LSET`/`RSET` | [`basic/field.asm:283`](../basic/field.asm) | 🔴 diverges **via its FIELDed arm**, one reference |

All four do `var_str_type` → `var_name_key` → use the KEY, with no `(` peek — the
same shape D-ARYLV fixed in the other four sites, and the same fix applies
(`tgt_parse`, [`basic/vars.asm`](../basic/vars.asm)).

🎯 **`d.ary` answers the one genuinely unobvious question.** It was not clear that
an MSX accepts an array element as a **`FIELD`** target at all — a FIELD target
is a buffer *alias*, not a value, so refusing arrays would have been a defensible
language design. The CF-3300 accepts it. `ex_mid_stmt`'s own header had already
conceded its half in writing (*"array lvalues deferred"*), so that gap was known
and merely unpriced; `FIELD`'s was not known either way.

---

## 3. 🔴 THE `LSET` SITE NEEDED A 2×2, AND A PAIR OF ROWS WOULD HAVE FILED THE WRONG RESIDUAL

`s.ctl` — `LSET` on a plain **non-FIELDed** variable — is **red on zerobas**:
`Syntax error` against the CF-3300's `HI   `. Source confirms it is deliberate:
`lrset_notfld` ([`basic/field.asm`](../basic/field.asm)) is a bare
`jp stmt_error` commented *"LSET/RSET on a non-fielded var (slice-1 limit)"* — a
**known limit that had never been measured**, and it is a separate defect from
anything about subscripts.

With only `s.ctl` + `s.ary`, this site's reading would have been *"the array
question is unanswerable here until `LSET` works at all"* — **and that is wrong.**
Adding the FIELDed arm shows:

* `s.fld` (FIELDed scalar) is **GREEN on zerobas** — the FIELDed `LSET` path works.
* `s.fldary` (FIELDed array element) **diverges**, with its own control green.

So the site's array gap **is** real and separable, and it is reachable through the
arm that works. The probe encodes this: `SITE_CONTROL` maps each array row to its
**own arm's** control, so a red non-FIELDed control annotates `s.ary` and
correctly does **not** touch `s.fldary`.

⚠️ **A site with two arms needs a control per arm.** One control per *site* was
the natural first draft and it would have disqualified a row that was good
evidence ([[one-positive-control-per-gated-verb]], one level up).

---

## 4. 🔴 AND THE INSTRUMENT'S FIRST DRAFT REPORTED A TREE DEFECT AS A BROKEN INSTRUMENT

The first run **exited 2 and scored nothing**, because `s.ctl` failed and the
probe treated any control failure as "the fixture is broken". Six perfectly good
readings from the other three sites were thrown away — and their own controls had
all passed, which was itself proof the disk had mounted and the channels had
opened.

The rule that replaced it:

* a control failing on a **REFERENCE** → the fixture is broken; exit 2, score
  nothing. *Only a reference can tell you the apparatus is wrong, because only it
  is supposed to be right.*
* a control failing on **zerobas** → an ordinary divergence, scored like any other
  row, which additionally **scopes its own arm**.

[[classify-a-control-failure-by-which-side-failed-it]]. The all-or-nothing rule
comes from the right instinct — a green run against a dead fixture is the classic
false pass — applied without asking *who* failed.

---

## 5. What this does NOT establish

* **`RSET` is not separately measured.** `ex_lset` and `ex_rset` both fall into
  `lrset_common`, so they are **one** parse site and one row covers the parse.
  A row that distinguished their *justification* would be a different question.
* **`LINE INPUT #n`** shares `inp_readvar` with `INPUT #n` and is not separately
  measured.
* **Numeric `INPUT #n`** cannot be measured at all here: `files.asm` rejects it
  with *"numeric INPUT# = Phase 3"* before any target parse, so `INPUT#1,A(1)`
  would be red for a reason that has nothing to do with subscripts.
* **No price.** Nothing here is carve-scouted. ⚠️ Main page 1 is at **49 B** after
  D-ARYLV, so unlike that slice this one cannot assume it fits.

---

## 6. Status

⚠️ **MEASUREMENT ONLY. No byte has moved for it**, and
`make lvsites-characterize` is deliberately **not** an acceptance gate: 6 of its
10 rows can only be red until the work lands, and a row that can only ever be red
is doc debt, not a gate. All four ROMs hash identically to `acfcfd7`
(`basic-reloc 7d78c4b6…`, `sub de1ad5d0…`, `disk 2c630d3d…`,
`main-eu 85da929d…`).

The static counters this moves, predicted from each check's own definition and
then measured:

| gate | before | predicted | measured |
|---|---|---|---|
| `audit-citations` files swept | 739 | **741** (the probe + this document — the sweep walks every file) | **741** ✅ |
| `audit-citations` basic provenance-bearing | 190 | **191** (+1 per real `probes/basic/*.py`) | **191** ✅ |
| `injector-check` files | 338 | **339** | **339** ✅ |
| `rowshape-check` walked / report-row / in-contract / conform / violations | 179 / 32 / 8 / 8 / 0 | 180 / 33 / 9 / 9 / 0 | **180 / 33 / 9 / 9 / 0** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **unchanged** ✅ |
