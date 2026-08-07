# D-READVAR — what a `READ` target may BE

**Status:** spec in progress 2026-08-07, written BEFORE implementation.
**Base:** `16ba60f`, branch `main`.
**Subject:** the `TODO.md` residual *"ZEROBAS HAS NO STRING `READ`"* (filed
2026-08-01 by D-DEFSTR), **scouted 2026-08-07 and measured to be one face of
five**.
**Cost:** carve-scouted — **+35…45 B in main page 1** for the four twin-covered
faces, against **158 B free**. No carve needed. §5.

---

## 1. The residual, and why its title under-claims it

`ex_read` (`basic/program.asm`) does this to find its target:

```
call    is_letter           ; ONE letter
call    upcase
ld      (READVAR),a
inc     hl                  ; consume it
...
call    var_set             ; the SINGLE-LETTER int16 shim (basic/vars.asm)
```

Every other variable reference in this tree goes through `var_name_key`, which
walks the whole identifier **and its type suffix**. So `READ` does not merely
lack a `$` path — it lacks the *second name character*, *every explicit suffix*,
and *any subscript*. The filed title names one consequence of a parse that stops
after one byte.

Scouted on three sides 2026-08-07 (`Philips_VG_8020`, `National_CF-3300`,
repack); **both references agreed row for row**:

| row | `DATA` | both references | zerobas |
|---|---|---|---|
| `READ A` | `7` | ` 7 ` | ` 7 ` 🟢 control |
| `READ A$` | `HELLO` | `HELLO` | **Syntax error** |
| `READ A$` | `42` | `42` | **Syntax error** |
| `READ AB` | `7` | ` 7 ` | **Syntax error** |
| `READ A%` | `7` | ` 7 ` | **Syntax error** |
| `READ A(1)` | `7` | ` 7 ` | **Syntax error** |

**Five divergences, one root cause** — therefore one slice, not five.

⚠️ Note `DATA 42` into a string target answers `42`, **not** ` 42 `. The missing
`PRINT` sign/trailing spaces are the tell that the value is a STRING. A row that
compared loosely would have called this agreement.

---

## 2. Two denominators, and they are different questions

A hand-picked row set is a scope claim
([[a-hand-listed-denominator-is-a-scope-claim]]). The scout's six rows were
chosen to *detect* the class; a gate has to *bound* it. The surface is the cross
of the things the parse actually reads:

### A — the TARGET GRAMMAR

A variable reference is **(name, type-suffix, subscript)**, with the DEFtbl
supplying the type when the suffix is absent. That is the surface the defect is
in, so it is the denominator: 1- and 2-character names, a letter+digit name,
each of `%` `!` `#` `$`, a numeric and a string array element, and both DEFtbl
resolutions (`DEFSTR` / `DEFINT`). **12 rows.**

### B — how a DATA ITEM LEXES into a string

🔴 **This axis is INVISIBLE TODAY and only becomes observable once a string
target exists at all.** An int16 parse cannot distinguish `DATA HELLO` from
`DATA "HELLO"` from `DATA HI THERE` — it never looked. So these rows are
**characterization of a surface this tree has never read**, not a regression
check, and they are where a surprise is most likely: quoting, embedded commas,
leading/embedded/trailing spaces, an empty item, and multi-item/mixed-type
`READ` lists. **11 rows.**

### C — the CROSS

A **string** DATA item read into a **numeric** target — the reverse of the filed
defect, with no reason to behave like it. **1 row.**

**24 rows total** (12 + 11 + 1), `probes/basic/basic_probe_readvar.py`, three
sides.

⚠️ **It was 22 until the denominator was re-read for what it had NOT asked.**
`b.leadsp` established that leading spaces are stripped; nothing asked about the
TRAILING end, or about whether quotes preserve spaces. Adding `b.trailsp` and
`b.qspace` cost three boots each and one of them overturned the rule the
implementation would otherwise have been written from (§6).

### 2.1 🟢 The positive control

`a.one` (`READ A` ← `DATA 7` → ` 7 `) is asserted on positive text before
anything else is scored, and its failure exits **2**, not 1. Every row in this
battery answers with a short bracketed span, and **a machine that ran no program
prints no bracket on any side** — three sides agreeing on "nothing" is perfect
agreement about nothing. `make fat-error-acceptance` once scored 8/8 against an
all-`$00` `disk.rom`; this is the row that makes that impossible here.

### 2.2 A row whose references disagree has NO ORACLE

The probe flags `[REFERENCES DISAGREE]` per row and counts them separately. Such
a row cannot be a gate row in either direction — it is a finding about the
machines, not about zerobas.

---

## 3. The reading, and the trap in taking it

Only the `[...]` span **printed by the RUN** is compared, taken from the screen
tail after `RUN`.

🔴 **NOT the whole screen, and this is a measured trap, not a precaution.** The
scout's first cut scanned the name table, so the `[` inside the *echo* of
`30 PRINT"[";A$;"]"` matched — and every zerobas row, on all five divergent
cases at once, reported `'";A$;"'`: an artifact shaped exactly like a reading.
The readout was blind to its own subject in the direction that produces *values*
rather than blanks, which is the direction that does not look broken.
[[readout-blind-to-its-own-subject]]

Sentinels (`<NO CAPTURE>`, `<NO OUTPUT>`) are **never** agreement, however many
sides answer them.

---

## 4. The design — make `ex_read`'s target parse what `ex_input`'s already is

The string machinery is **already resident and already exercised**. The literal
sequence at `basic/input.asm:117` is:

```
call    var_str_type        ; A = 1 if the name carries a '$'
call    var_name_key        ; BC = key, HL past the name + suffix
...                         ; numeric: var_store_fac    (input.asm:104)
call    strscr_desc         ; string: RVDESC -> [len][ptr] wrapping STRSCR
call    str_set_key         ; var$[key] = the bytes
```

`READ` needs the same shape. The one genuinely NEW routine is a **string variant
of `read_one_value`** that captures the DATA item's raw ASCII span into `STRSCR`
instead of parsing it as an int — and `read_one_value` **already positions HL at
the item start** and already owns the comma / `data_seek` walk
(`basic/readdata-body.inc:38-51`).

### 4.1 🔴 The sub/main split is FORCED, not chosen

| routine | address | region |
|---|---|---|
| `var_name_key` | `$46B2` | main page 1 |
| `var_str_type` | `$470A` | main page 1 |
| `var_store_fac` | `$47B2` | main page 1 |
| `str_set_key` | `$4890` | main page 1 |
| **`strscr_desc`** | **`$2896`** | **LOW region** |

A page-0 sub-ROM tenant runs with the low region **switched out** — it cannot
call `strscr_desc` at all. So the tenant may only *fill* `STRSCR`; the
descriptor wrap and the store must stay main-side. That is exactly what
`ex_input` does, which makes the twin the **right** shape rather than a merely
convenient one.

---

## 5. Cost — carve-scouted, and stated as a BOUND

Every number off `build/basic-reloc.sym`:

| measurement | value |
|---|---|
| main page 1 free — **the binding wall** | **158 B** |
| `INPUT` twin: head + NUMERIC arm | **45 B** (`$2F42-$2F6F`) |
| `INPUT` twin: STRING arm | **22 B** (`$2F6F-$2F85`) |
| `READ`'s current loop body, replaced | **39 B** (`$7A38-$7A5F`) |
| existing page-0 tenant stub `exr_call..exr_done` | **61 B** |
| sub page 0 free, for the item-span capture | **3843 B** |
| carve reservoir if ever needed (`basic/program.asm`) | **2375 B** leaves page 1 |

⇒ the four twin-covered faces cost about **(67 − 39) = +28 B** of dispatch plus
a few bytes to give the existing stub a mode flag rather than build a second
61 B one: **+35…45 B against 158 B free**, ~110 B to spare, **no carve needed**.

⚠️ **These are byte counts of ANALOGOUS code, not of code that exists.** The real
number comes from a build. Recorded as a bound from a measured twin so it cannot
later be quoted back as a measured cost ([[filed-justification-is-a-claim]]).

### 5.1 🔴 `READ A(1)` is OUTSIDE the twin and is DEFERRED

`basic/input.asm` has **no array handling whatsoever** — `var_name_key` parses a
name and a suffix, never a subscript — so the array face needs `ex_let`'s lvalue
path (`ary_op0_resolve` / `ary_store_write`, `basic/arrays.asm:773/721`) and is
**not priced by the twin**.

It is measured here anyway (`a.ary`, `a.arystr`) because a deferral has to carry
its evidence. ⚠️ It is also worth asking whether **`INPUT A(1)` diverges too** —
if it does, the array work is shared between two verbs and is worth more than it
looks. **Unmeasured; not assumed in either direction.**

---

## 6. Characterization — MEASURED

Full table: [`docs/readvar-msx1-characterization.md`](readvar-msx1-characterization.md).
**24 rows, 3 sides, both references agreeing on all 24** (0 rows without an
oracle). zerobas agrees on **2**: `a.one` (the control) and `a.defint`.
**22 divergences — 21 refusals and 1 over-acceptance.**

Three results the scout did not have, each of which changes the work:

1. 🔴 **`c.strnum` POINTS THE OTHER WAY.** `DATA HELLO` / `READ A` is a
   **Syntax error** on both references; zerobas answers ` 0 `. Every other row
   is zerobas refusing what the references accept — this is zerobas **accepting
   what they refuse**, because `data_parse_int` parses no digits, yields 0 and
   stores it silently. Routing the target parse through `var_name_key` does not
   touch this row: it is separate work **in the DATA engine**. A fix that closed
   the other 21 would leave the quiet wrong answer behind.
2. 🔴 **`b.trailsp`: trailing spaces are PRESERVED.** `DATA PAD  ,X` reads back
   `'PAD  '`. Leading spaces *are* stripped (`b.leadsp`), so the symmetric rule
   is the obvious one and it is **wrong on both references**. An implementation
   written from `b.leadsp` alone would have been plausible and divergent, and no
   numeric row could ever have caught it. This row exists because the denominator
   was re-examined for what it had not asked, not because a defect was suspected.
3. ✅ **`a.defint` already agrees** — the single-letter shim resolves the DEFtbl
   type before storing, so an unsuffixed name with a numeric default works today.
   That is the boundary of what the shim gets right, and it is a **GREEN that
   must survive the fix**, not a row to re-derive.

### 6.1 The DATA-item lexing rule, stated from the rows

Skip leading spaces; then take bytes **verbatim** to the next comma or the end
of the statement. A leading `"` instead delimits the item and the closing `"`
ends it, so a comma inside quotes is content. **Nothing is trimmed from the end.**

---

## 7. Predicted GREEN — the reference column IS the prediction

After the fix, `make readvar-acceptance` must read **24/24 with 1 positive
control**, every row answering the "both references" column of the
characterization table. Writing any other number here would be predicting my own
implementation rather than the machines
([[a-prediction-copied-into-the-result-column]]).

Unchanged and required to be:

| | value |
|---|---|
| sub p0 / sub p1 free | 3843 / 1483 B |
| `sub.rom`, `disk.rom`, `zerobas-main-eu.rom` hashes | unchanged **iff** no sub-side byte moves |
| `preflight-check` | 181/86/95/95/0 |
| `rowshape-check` | 176→177 walked, contract **6**, 6 conform, 0 violations |
| every other acceptance gate in the corpus | its current tally |

Changed by construction: **main page 1 158 B → ≈113…123 B** (§5's bound). ⚠️ If
the sub-ROM item-span capture lands, `sub.rom` moves and **sub p0 drops from
3843**; the exact figure is a build output, not a prediction.

---

## 8. Predicted RED — knives

Each cut names a RED **set** and a GREEN **set**; a run where nothing moves,
greens included, is an apparatus result. Every knife twice, ROMs hashed after
every cut build, subject = the probe invoked directly.

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-RV1** | `ex_read`: restore the one-letter parse (`is_letter`/`READVAR`) | all A/B rows except `a.one`, `a.defint` | `a.one`, `a.defint`, `c.strnum` |
| **K-RV2** | `ex_read`: force the string arm to take the numeric arm | `a.str`, `a.str2`, `a.arystr`, `a.defstr`, all `b.*` | every A numeric row |
| **K-RV3** | the item-span capture: stop skipping leading spaces | `b.leadsp` **only** | all 23 others — the tightest cut in the set |
| **K-RV4** | the item-span capture: trim trailing spaces too | `b.trailsp` **only** | all 23 others |
| **K-RV5** | the item-span capture: ignore the `"` delimiter | `b.quoted`, `b.qcomma`, `b.qspace` | `b.bare`, `b.embsp`, `b.leadsp`, `b.trailsp` |
| **K-RV6** | the `c.strnum` error path: restore the silent 0 | `c.strnum` **only** | all 23 others |
| **K-RV7** | delete `a.one`'s DATA line so the control cannot pass | probe exits **2**, "NOT MEASURED", no row scored | — the dead-subject test |

**K-RV3/K-RV4/K-RV6 are the ones that matter**: each reddens exactly ONE row.
A gate whose rows all move together is measuring that something changed, not
what ([[predicted-red-set-must-not-inherit-scope]]). K-RV4 in particular is the
knife for the rule §6 says is counter-intuitive — if it does not redden
`b.trailsp` alone, the implementation is not honouring the measurement.

---

## 9. Scope taken, and what is deferred

**Taken:** all of A except the array rows, all of B, and C.
**Deferred with evidence:** `a.ary` / `a.arystr` — §5.1, outside the `INPUT`
twin and unpriced; they stay measured and RED, recorded in `TODO.md`.

⚠️ **A deferred row cannot be a gate row** — *"a row that can only ever be red is
doc debt, not a gate"* — so `readvar-acceptance` gates **22 of the 24**, prints
the 2 deferred rows as `....` with their reason, and says so in its tally.

## 10. As-built

*(pending implementation)*
