# `READ` — what a target may be, and how a DATA item lexes (MSX1, measured)

Measured 2026-08-07 against **two** references — the Philips VG-8020 and the
National CF-3300 — by `probes/basic/basic_probe_readvar.py`
(`make readvar-characterize`). **Both references agree on all 24 rows**, so every
row has an oracle; the probe counts and prints rows where they split, and that
count is **0**.

Spec: [`docs/spec-basic-readvar.md`](spec-basic-readvar.md). Clean-room: observed
screen output only; both reference ROMs are black boxes.

The reading is the `[...]` span printed **by the RUN**, taken from the screen
tail after `RUN` — never from the whole screen (§3 of the spec: the echo of
`PRINT"[";A$;"]"` contains a `[`, and matching it turns "printed nothing" into a
value-shaped artifact).

`PRINT` spacing convention: a non-negative number prints as
`<space><digits><space>`, so ` 7 ` is the number 7. **A string prints with no
spaces at all** — which is why `DATA 42` read into `A$` answering `42` rather
than ` 42 ` is the tell that the value is a STRING.

---

## A — the target grammar

`READ` takes a **variable reference**: a name of one or two identifier
characters, an optional type suffix, an optional subscript, with the DEFtbl
supplying the type when the suffix is absent.

| row | program | both references | zerobas @ `16ba60f` |
|---|---|---|---|
| `a.one` | `DATA 7` / `READ A` | ` 7 ` | ` 7 ` 🟢 **positive control** |
| `a.two` | `DATA 7` / `READ AB` | ` 7 ` | **Syntax error** |
| `a.digit` | `DATA 7` / `READ A1` | ` 7 ` | **Syntax error** |
| `a.pct` | `DATA 7` / `READ A%` | ` 7 ` | **Syntax error** |
| `a.bang` | `DATA 7` / `READ A!` | ` 7 ` | **Syntax error** |
| `a.hash` | `DATA 7` / `READ A#` | ` 7 ` | **Syntax error** |
| `a.str` | `DATA HELLO` / `READ A$` | `HELLO` | **Syntax error** |
| `a.str2` | `DATA HELLO` / `READ AB$` | `HELLO` | **Syntax error** |
| `a.ary` | `DATA 7` / `DIM A(3)` / `READ A(1)` | ` 7 ` | **Syntax error** |
| `a.arystr` | `DATA HI` / `DIM A$(3)` / `READ A$(1)` | `HI` | **Syntax error** |
| `a.defstr` | `DEFSTR Z` / `DATA HELLO` / `READ Z` | `HELLO` | **Type mismatch** |
| `a.defint` | `DEFINT Z` / `DATA 7` / `READ Z` | ` 7 ` | ` 7 ` ✅ |

**The rule:** a `READ` target is *any* variable reference — exactly what `LET`
and `INPUT` accept.

⚠️ **`a.defstr` fails DIFFERENTLY from the rest — `Type mismatch`, not `Syntax
error`.** That is not noise: it is D-DEFSTR's own fix showing through. The name
is a bare letter, so `ex_read`'s one-letter parse succeeds and the failure lands
later, in `deftbl_num_type`, which raises ERR 13 on a string default. D-DEFSTR
turned a memory corruption into that clean error. Two dispositions, one cause.

✅ **`a.defint` already agrees**, and it is the second row that does. The
single-letter shim resolves the DEFtbl type before storing, so an *unsuffixed*
name whose default is numeric works today. It is the boundary of what the shim
gets right, and it must **stay** green through the fix.

---

## B — how a DATA item lexes into a string

🔴 **This whole surface is INVISIBLE on zerobas today**, and not because it is
untested: an int16 parse cannot distinguish `DATA HELLO` from `DATA "HELLO"`
from `DATA HI THERE`, so there has never been a reading to disagree with. These
rows are characterization of something never before read here.

All rows read into `A$` unless shown otherwise.

| row | `DATA` line | both references | note |
|---|---|---|---|
| `b.bare` | `DATA HELLO` | `HELLO` | unquoted text is taken verbatim |
| `b.digits` | `DATA 42` | `42` | **a STRING** — no `PRINT` spaces |
| `b.quoted` | `DATA "HI"` | `HI` | the quotes are delimiters, not content |
| `b.qcomma` | `DATA "A,B"` | `A,B` | quotes protect the separator |
| `b.embsp` | `DATA HI THERE` | `HI THERE` | embedded spaces preserved |
| `b.leadsp` | `DATA   PAD` | `PAD` | **leading spaces stripped** |
| `b.trailsp` | `DATA PAD  ,X` | `PAD  ` | 🔴 **trailing spaces PRESERVED** |
| `b.qspace` | `DATA " P "` | ` P ` | quotes preserve both sides |
| `b.empty` | `DATA ,X` | `` (empty) | an empty item is the empty string |
| `b.two` | `DATA A,B` / `READ A$,B$` | `AB` | two items, two targets |
| `b.mixed` | `DATA 1,X` / `READ A,B$` | ` 1 X` | mixed types in one `READ` list |

**The rule, stated from the rows:** skip leading spaces, then take bytes
verbatim up to the next comma or the end of the statement; a leading `"` instead
delimits the item and the closing `"` ends it, so a comma inside quotes is
content. Nothing is trimmed from the end.

🔴 **`b.trailsp` is the row that pays for having been measured.** The obvious
assumption — that an unquoted DATA item is trimmed at both ends, since the
leading spaces plainly are — is **wrong on both references**: `DATA PAD  ,X`
reads back as `'PAD  '`, two trailing spaces intact. An implementation written
from the leading-space rule alone would have been symmetric, plausible, and
divergent, and no numeric row could ever have caught it.

---

## C — the reverse cross

| row | program | both references | zerobas @ `16ba60f` |
|---|---|---|---|
| `c.strnum` | `DATA HELLO` / `READ A` | **Syntax error** | ` 0 ` |

🔴 **THE ONE DIVERGENCE THAT POINTS THE OTHER WAY, and the residual never
mentioned it.** Every other row is zerobas refusing something the references
accept. Here zerobas **accepts** something the references *refuse*: reading
non-numeric text into a numeric target is a `Syntax error` on both machines,
while zerobas's `data_parse_int` parses no digits, yields 0, and stores it
silently.

That matters for the fix's shape: routing the target parse through
`var_name_key` does not touch this row. Making `READ A` ← `DATA HELLO` an error
is **separate work in the DATA engine**, and a fix that closed the other 21 rows
would leave a silent wrong answer behind — the failure mode this project keeps
recording, where the loud defects are fixed and the quiet one survives.

---

## Totals

**24 rows, 3 sides. Both references agree on all 24 (0 rows without an oracle).
zerobas agrees on 2** — `a.one` (the positive control) and `a.defint`.
**22 divergences: 21 refusals and 1 over-acceptance.**

---

## After D-READVAR — 22 of the 24 closed, and the other two are named

Measured 2026-08-07 on the same three sides, `make readvar-acceptance`:
**22/22 scored readings agree**, `a.one` holding as the positive control.

Every zerobas column above now reads its **"both references"** neighbour, with
exactly two exceptions:

| row | both references | zerobas after | status |
|---|---|---|---|
| `a.ary` | ` 7 ` | **Syntax error** | **DEFERRED** — printed `....`, not scored |
| `a.arystr` | `HI` | **Syntax error** | **DEFERRED** — printed `....`, not scored |

Those two need `ex_let`'s array lvalue path (`ary_op0_resolve` /
`ary_store_write`), which is outside the `INPUT` twin the fix was priced against —
`basic/input.asm` has no array handling at all — so they are measured, printed and
**excluded from the tally in both directions**. A row that can only ever be red is
doc debt, not a gate. Re-filed in `TODO.md` with its price.

⚠️ **The zerobas columns above are kept as MEASURED AT `16ba60f`**, not rewritten.
They are the reading the fix was written from, and a characterization table that
edits its own before-column stops being one.
