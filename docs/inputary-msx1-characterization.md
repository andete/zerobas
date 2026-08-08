# `INPUT` with an ARRAY ELEMENT target (MSX1, measured)

Measured 2026-08-08 against **two** references — the Philips VG-8020 and the
National CF-3300 — by `probes/basic/basic_probe_inputary.py`
(`make inputary-characterize`). **Both references agree on all 7 rows**, so every
row has an oracle; the probe counts and prints rows where they split, and that
count is **0**.

This answers the one question
[`docs/spec-basic-readvar.md`](spec-basic-readvar.md) §5.1 left open when
D-READVAR deferred `READ A(1)` / `READ A$(1)`:

> ⚠️ It is also worth asking whether **`INPUT A(1)` diverges too** — if it does,
> the array work is shared between two verbs and is worth more than it looks.
> **Unmeasured; not assumed in either direction.**

Clean-room: observed screen output only; both reference ROMs are black boxes.

The reading is the `[...]` span printed **by the RUN**, taken from the screen tail
after `RUN` — never the whole screen (D-READVAR §3: the echo of
`PRINT"[";A;"]"` contains a `[`, and matching it turns "printed nothing" into a
value-shaped artifact).

---

## The rows

Each program is typed as numbered lines, `RUN`, then the `INPUT` **response**
injected as a further line — it lands while the read is blocked.

| row | program | response | both references | zerobas @ `c7323b9` |
|---|---|---|---|---|
| `i.ctl` | `INPUT A` | `7` | ` 7 ` | ` 7 ` 🟢 **positive control** |
| `i.strctl` | `INPUT A$` | `HI` | `HI` | `HI` 🟢 **positive control** |
| `i.linectl` | `LINE INPUT A$` | `HI` | `HI` | `HI` 🟢 **positive control** |
| `i.ary` | `DIM A(3)` / `INPUT A(1)` | `7` | ` 7 ` | **Syntax error** |
| `i.arystr` | `DIM A$(3)` / `INPUT A$(1)` | `HI` | `HI` | **Syntax error** |
| `i.lineary` | `DIM A$(3)` / `LINE INPUT A$(1)` | `HI` | `HI` | **Syntax error** |
| `i.arynodim` | `INPUT A(1)` (no `DIM`) | `7` | ` 7 ` | **Syntax error** |

**3/7 agree, 4 diverge, 0 rows without an oracle.**

---

## The answer, and it is bigger than the question asked

✅ **YES — `INPUT A(1)` diverges, on both references.** So the array-lvalue work
D-READVAR deferred is **not** a one-verb job, and pricing it against `READ` alone
under-counts it.

🔴 **AND IT IS THREE ARMS, NOT ONE.** `basic/input.asm` parses its target in
**three** separate places — `inpc_vloop` (numeric), `inpc_vstr` (string) and
`inpc_line` (`LINE INPUT`, which re-parses its own target rather than sharing the
list driver) — and **all three diverge**. The filed TODO price was written against
one parse site. The rows that say so are `i.ary`, `i.arystr` and `i.lineary`, and
they are three rows precisely because a single "INPUT takes arrays" row could not
have separated them.

🎯 **`i.arynodim` IS THE ROW THAT NAMES THE CAUSE.** Without a `DIM`, an MSX
auto-dimensions an array to 10 elements on first reference — and both references
read ` 7 ` there. So zerobas's `Syntax error` is **not** "that array does not
exist": it is the target **parse** refusing the `(`, which is the same root cause
as `READ`'s (`var_name_key` walks a name and a type suffix and never a subscript).
Without this row, "zerobas refuses `INPUT A(1)`" would have had two candidate
causes and no way to choose ([[row-with-two-candidate-causes]]).

⚠️ **The three positive controls are not decoration here.** Every row in this
battery needs a typed response to reach a **blocked** `INPUT`. If the response
never arrives the read never completes, nothing is printed, and all three sides
agree on nothing — perfect agreement about nothing, the shape
`make fat-error-acceptance` once scored 8/8 against an all-`$00` `disk.rom` with.
One control per arm, because the three arms are the three things that could
independently break; their failure exits **2**, not 1.

---

## What this does to the deferred item

`TODO.md` §"Open — standing residuals" carries the re-filed array item. This
measurement changes it in three ways, and none of them were assumed:

1. The divergent surface is **6 rows across two verbs**, not 2 across one —
   `READ A(1)`, `READ A$(1)`, `INPUT A(1)`, `INPUT A$(1)`, `LINE INPUT A$(1)`,
   plus the unDIMmed form.
2. The **price rises**: three `INPUT` parse sites plus `READ`'s one, against a
   main page-1 wall with **126 B** free. That is now a real carve question rather
   than an obvious fit, and it needs `tools/carve_scout.py` before a byte moves.
3. The **value rises with it** — one lvalue path, reused four times, closes all
   six rows. Whether the shared shape can be made cheap enough to fit is exactly
   what the scout is for, and it is still **not measured**.

⚠️ **This document measures the SURFACE, not the fix.** No byte has moved for it;
`make inputary-characterize` is a characterization target and deliberately not an
acceptance gate, because 4 of its 7 rows can only be red until the work lands.
**All four ROMs hash identically to `c7323b9`** (`basic-reloc.rom 38d79ffd…`,
`sub.rom 33af21eb…`, `disk.rom 2c630d3d…`, `zerobas-main-eu.rom 87afd9ea…`), which
is the whole claim a measurement-only change has to support.

---

## The static counters this moves, predicted and measured

| gate | before | predicted | measured |
|---|---|---|---|
| `audit-citations` files swept | 734 | ~~735~~ | **736** 🔴 |
| `audit-citations` basic provenance-bearing | 188 | **189** | **189** ✅ |
| `injector-check` files | 336 | **337** | **337** ✅ |
| `rowshape-check` walked / report-row / in-contract / conform / violations | 177 / 30 / 6 / 6 / 0 | 178 / 31 / 7 / 7 / 0 | **178 / 31 / 7 / 7 / 0** ✅ |

🔴 **The swept count was predicted from "one new `.py`" and this change adds
TWO files** — the probe *and* this document, which the sweep also walks. Same
shape as D-READVAR §10.5: predicted from the thing I was thinking about rather
than from the definition of what is counted
([[a-count-is-predicted-by-reading-its-definition]]). The `basic` counter, which
D-CASSAVE's record says moves **+1 per real `probes/basic/*.py`**, was predicted
correctly from that written rule — the difference between the two rows is whether
a rule was read or recalled.
