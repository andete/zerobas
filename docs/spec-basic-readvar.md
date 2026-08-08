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

### 5.1.1 ✅ MEASURED 2026-08-08 — it does, and on THREE arms

[`docs/inputary-msx1-characterization.md`](inputary-msx1-characterization.md),
`make inputary-characterize`. 7 rows × 3 sides, **both references agree on all 7**.
`INPUT A(1)` → ` 7 `, `INPUT A$(1)` → `HI`, **`LINE INPUT A$(1)` → `HI`** on both
references; all three are `Syntax error` here.

🔴 **The sentence above says "two verbs"; the measurement says two verbs and FOUR
PARSE SITES.** `basic/input.asm` parses its target in three separate places —
`inpc_vloop`, `inpc_vstr`, and `inpc_line`, which re-parses its own rather than
sharing the list driver — and all three diverge, alongside `ex_read`'s. §5.1's own
framing ("outside the `INPUT` twin", "`input.asm` has no array handling") was
correct about the code and **understated the surface**: no array handling in
`input.asm` means `INPUT` is a *fellow victim*, not merely a twin that lacks the
feature.

🎯 **`i.arynodim` is what makes that a cause rather than a coincidence.** An MSX
auto-dimensions an unDIMmed array to 10 on first reference, and both references
read ` 7 ` there — so the refusal is in the **parse**, not in a missing array, and
it is therefore the *same* `var_name_key`-has-no-subscript defect `READ` has. One
lvalue path closes all six rows.

⚠️ **This RAISES the deferred item's price and its value together**, and the
~25…40 B bound in §5/`TODO.md` was written for ONE site. It is not re-derived
here; four sites need a carve scout, not arithmetic
([[filed-justification-is-a-claim]]).

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

### 8.1 Revisions made BEFORE running, against the built implementation

The table above was written before a byte moved. Reading it against the code
that actually landed changed four of the seven, and one of them changed a
**prediction**, not just a cut site. Recorded here rather than silently applied.

| # | what changed | why |
|---|---|---|
| **K-RV1** | **cut SITE.** "Restore the one-letter parse" cannot be a verbatim revert: the DATA engine's return contract is now `A = status`, not `CF`, so the old body's `jr nc` would misread status 2, and the old body never wrote `RDV_MODE`, so a restored `READ` would read whatever the previous statement left there. The cut restores the *parse and key* — `ld a,(hl)` / `upcase` / `ld b,a` / `ld c,0` / `inc hl` / `deftbl_num_type` → `VARTYPE`, i.e. exactly what `var_set` used to build — and keeps `exr_bad`. | a restore that changes the ENGINE's contract is not a restore of `ex_read`; and a knife whose subject reads uninitialised RAM measures the RAM |
| **K-RV2** | **predicted GREEN gains `b.empty`.** Forcing the numeric arm makes `DATA ,X` / `READ A$` parse 0 into the *numeric* `A`, leaving `A$` unset — which prints as the empty string, **which is exactly what the references print**. The row agrees for the wrong reason. | a row can agree for the wrong reason; predicting it RED would have scored a MISS as a defect |
| **K-RV3** | **split, and the filed cut is now a PREDICTED MISS.** 🔴 The leading-space strip is implemented **twice** — `data_seek`'s `ds_sp` strips them after the `DATA` token, and `rov_str` strips them again — and **every B row is its statement's FIRST item**, so `ds_sp` alone already answers `b.leadsp`. Cutting `rov_str`'s skip (as filed) reddens **nothing**. Cutting both (**K-RV3b**) reddens **every string row — 14 of the 22**, not one: `tk_data_rest` (`basic/tokenise.inc:284`) copies a `DATA` body *verbatim from the character after the keyword*, so the crunched stream is `$84 $20 …` and with no skip anywhere every unquoted item gains a leading space and every quoted one fails its `"` test. | [[rule-gated-structurally-has-no-knife]] — a doubly-implemented rule has no one-row knife, and saying so is the finding |
| **K-RV4** | **cut SITE narrowed to the UNQUOTED path.** A trim applied after both paths converge also trims `b.qspace` (`" P "` → `" P"`), reddening two rows. The plausible mis-implementation — "skip leading, take verbatim, trim trailing" written as the *unquoted lexer's* rule — reddens exactly one. | the knife has to be the mistake a person would make, not the widest edit that moves the row |
| **K-RV5** | **cut SITE.** `jr nz,rovs_lp` → `jr rovs_lp` would orphan the quoted loop and be refused by `check_dead_code.py`, the D-MOUNTROW trap. Cut the *comparand* instead (`cp '"'` → `cp $01`): byte-neutral, statically reachable, orphans nothing. | [[a-knife-reddens-its-own-target-row]] — a cut can be refused by a gate other than the one it targets |
| **K-RV7** | **exempt from the ROM-hash assertion.** Its subject is the PROBE's own case table; the ROMs are *supposed* to be byte-identical, so the standard "the cut reached no ROM → nothing was measured" abort would kill it. | the hash guard's premise is a cut in the tree |

---

## 9. Scope taken, and what is deferred

**Taken:** all of A except the array rows, all of B, and C.
**Deferred with evidence:** `a.ary` / `a.arystr` — §5.1, outside the `INPUT`
twin and unpriced; they stay measured and RED, recorded in `TODO.md`.

⚠️ **A deferred row cannot be a gate row** — *"a row that can only ever be red is
doc debt, not a gate"* — so `readvar-acceptance` gates **22 of the 24**, prints
the 2 deferred rows as `....` with their reason, and says so in its tally.

## 10. As-built

Implemented 2026-08-07 on `main`, based on `6698e70`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/program.asm`](../basic/program.asm) `ex_read` | the target parse is now `ex_input`'s: `var_str_type` → `var_name_key` → (numeric: `FACTYP=2`, `VARTYPE`, `var_store_fac`) / (string: `strscr_desc` → `str_set_key` → `check_expr_errors`). The one-letter `is_letter`/`upcase`/`READVAR`/`var_set` head is gone |
| [`basic/program.asm`](../basic/program.asm) `read_one_value` stub | rebuilds `A = status` instead of `CF`; **4 B smaller** than the carry version |
| [`basic/readdata-body.inc`](../basic/readdata-body.inc) | `RDV_MODE` branch; the new `rov_str` raw-span capture into `STRSCR`; the trailing-junk test that makes `c.strnum` an error |
| [`sub/readdata.asm`](../sub/readdata.asm) | the tenant wrapper is 3 lines shorter — the status is now carried, not synthesised from a flag |
| [`basic/sysvars.inc`](../basic/sysvars.inc) | `RDV_MODE` ($E554) added, `RDV_ST` documented as three-valued, **`READVAR` ($E0BF) retired** — nothing latches a target name any more |
| [`probes/basic/basic_probe_readvar.py`](../probes/basic/basic_probe_readvar.py) | `DEFERRED`: the two array rows print `....` with their reason and are excluded from the tally in both directions |
| [`Makefile`](../Makefile) | `readvar-acceptance` (the `--gate` form), next to `readvar-characterize`, both `.PHONY` |

🎯 **`var_str_type` ALREADY RETURNS THE ITEM MODE.** It answers 1 for a string
target and 0 for a numeric one, which is exactly `RDV_MODE`'s encoding — so the
branch is decided *once*, stored, and re-read after the DATA read. That collapsed
two parallel arms (a separate `push`/`call`/`pop` sequence per type, as first
drafted) into one, and is where **17 of the 32 bytes** came from.

⚠️ **§5's *"give the existing stub `exr_call..exr_done` (61 B) a mode flag"* named
the WRONG STUB.** `exr_call`..`exr_done` is `ex_renum`'s LINEEDIT marshalling
head; the READ/DATA tenant's resident stub is `read_one_value`, and it is 22 B,
not 61. The advice was right and the label was wrong — and following it made the
stub *smaller*, because a three-valued status in `A` needs no flag reconstruction
at all.

⚠️ **One byte-count claim in §5 is now measured and was NOT a bound:** the `:`
arm the first draft carried in the trailing-junk test is **unreachable**.
`tk_data_rest` ([`basic/tokenise.inc:284`](../basic/tokenise.inc)) ends a `DATA`
body **at** a `:`, so a stored body never contains one. Deleted, 4 B of sub p0.

### 10.2 The walls, measured from clean

`rm -rf build && make basic-reloc`:

| wall | at `6698e70` | as built | Δ |
|---|---|---|---|
| main low region | 3 B | **3 B** | 0 |
| **main page 1 — the binding wall** | 158 B | **126 B** | **+32 B used** |
| sub page 0 | 3843 B | **3769 B** | 74 B used |
| sub page 1 | 1483 B | **1483 B** | 0 |

**+32 B against a scouted bound of +35…45 B** and 126 B still free. **No carve**,
so this stayed one slice.

ROM hashes after the corpus run, identical to the build the knives were scored
against and to every knife restore:

| ROM | at `6698e70` | as built |
|---|---|---|
| `basic-reloc.rom` | `2acb25db…` | **`38d79ffd…`** |
| `sub.rom` | `b3761022…` | **`33af21eb…`** |
| `disk.rom` | `2c630d3d…` | `2c630d3d…` (unmoved) |
| `zerobas-main-eu.rom` | `fd0bfa21…` | **`87afd9ea…`** |

⚠️ §7 predicted `sub.rom` unchanged *"iff no sub-side byte moves"*. Sub-side bytes
moved — the item capture is a sub-ROM tenant — so it moved, exactly as that
conditional said it would.

### 10.3 The gate — `make readvar-acceptance`, 22/22

```
ROWS: 24 printed, 22 scored — 22 agree, 0 diverge, 2 deferred (not scored)
22/22 readings agree (24 cases, 1 positive control, 0 row(s) with no oracle,
                      2 DEFERRED row(s) measured but not scored)
```

Every scored row answers the characterization's **"both references"** column —
including `b.trailsp` = `'PAD  '` and `c.strnum` = `Syntax error`, the two rows
that were counter-intuitive and reversed respectively. `a.one` held as the
positive control; `a.defint` held, which §6.3 required (it was already green).

⚠️ **§7 predicted "24/24".** It is **22/22**, and the difference is not a miss:
§9 of the same document already scoped the slice to 22 and said the gate would
score 22. §7 was written against the row COUNT rather than against §9's own scope.
The two deferred rows read `Syntax error` against ` 7 ` / `HI` and are printed.

### 10.4 Knives — 8 cuts × 2 rounds, 16/16 rounds identical

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly (`--sides zb`; a cut in zerobas can only move zerobas and the references
are constants), snapshot restore in a `finally`, `rm -rf build` + full rebuild
before every run, **all four ROM hashes asserted to have moved after every cut
build**, rows parsed with `probe_report.parse()` — no hand-rolled row regex, no
line diffing.

| # | cut | predicted RED | measured RED | verdict |
|---|---|---|---|---|
| **K-RV1** | one-letter parse + single-letter key restored | 19 rows | **19, exact** | ✅ CUT ×2 |
| **K-RV2** | every target down the numeric arm (`call var_str_type` → `xor a`+2×`nop`, byte-neutral) | 13 rows | **13, exact** | ✅ CUT ×2 |
| **K-RV3a** | `rov_str`'s leading-space skip only | **0 — a predicted MISS** | **0**, on a build whose ROMs moved | ✅ MISS confirmed ×2 |
| **K-RV3b** | + `data_seek`'s `ds_sp` | 14 rows | **13** — `b.mixed` held | 🔴 off by one, §10.5 |
| **K-RV4** | the SYMMETRIC trim, unquoted path | `b.trailsp` **only** | **`b.trailsp` only** (`'PAD  '` → `'PAD'`); `b.qspace` held at `' P '` | ✅ CUT ×2 |
| **K-RV5** | ignore the `"` delimiter (`cp '"'` → `cp $01`, byte-neutral) | `b.quoted`, `b.qcomma`, `b.qspace` | **exactly those 3** | ✅ CUT ×2 |
| **K-RV6** | restore the silent 0 (`ld a,2` → `ld a,1`, byte-neutral) | `c.strnum` **only** | **`c.strnum` only** → `' 0 '` | ✅ CUT ×2 |
| **K-RV7** | delete `a.one`'s `DATA` line | exit **2**, NOT MEASURED, 0 scored | rc=2, `a.one` = `<Out of DATA>`, `ROWS: 25 printed, 0 scored — NOT MEASURED` | ✅ CUT ×2 |

**K-RV4 and K-RV6 each reddened exactly ONE row**, which is what §8 said had to
happen and the reason those two are the ones that matter. K-RV4 in particular:
the implementation honours a rule that is counter-intuitive, and building the
intuitive rule instead moves that row and nothing else.

🟢 **The GREEN sets held in every run** — no cut moved a row outside its predicted
set except the one noted below, so 14 of the 16 rounds are exact on the whole
report, not just on the red half.

### 10.5 🔴 K-RV3b's predicted RED was ONE ROW TOO WIDE, and `b.mixed` is why

Predicted "every string row, 14 of 22". Measured **13**: `b.mixed`
(`DATA 1,X` / `READ A,B$`) did not move.

It is the only B row whose string item is **not its statement's first item**.
`ds_sp` runs once per `DATA` *statement*, not once per item, so the second item —
reached through `rov_comma`, which just steps over the comma — never had a leading
space to lose. Cutting both skips cannot move a row that passes through neither.

⚠️ **The prediction was made from the ROW CLASS ("string rows") rather than from
the cursor path each row takes**, which is the same shape as
[[a-count-is-predicted-by-reading-its-definition]]: the answer was in
`rov_comma`'s three lines, and the class name was easier to reach for. Recorded,
not corrected in place.

🎯 **And that is the finding K-RV3 as a whole exists to produce.** The
leading-space rule is implemented **twice** — `ds_sp` and the capture's own
`skip_spaces` — so it has **no one-row knife at all**: cut one and nothing moves
(K-RV3a), cut both and 13 rows move. §8 demanded a one-row cut here and the tree
cannot supply one. That is a property of the code, stated
([[rule-gated-structurally-has-no-knife]]), not a knife that failed.

### 10.6 Corpus — 22 targets, sequential from clean, **22/22 rc=0**

`unit-test` **ALL 59 files** · `audit-citations` CLEAN (**734** files swept, basic
**107 files / 188** provenance-bearing) · `preflight-check` **181 spawn sites /
86 exempt / 95 require a guard / 95 guarded / 0 UNGUARDED** · `injector-check`
ALL PASS, **336** files · `rowshape-check` **177 walked / 78 padded-label / 30
report-row / 6 in contract / 6 conform / 0 violations** · `latch-check` **16/16
rows** · `deadcode` main **1567 spans / 289 seeds** → 0 dead, sub **1522 / 102** →
0 dead (+1 allowlisted); page-1 closure **585 + 43**, page-0 tenant closure
**723 + 15**, resident ABI closure **122 + 4** · `lnblank-acceptance REPEAT=2`
**539/539** · `lnblank-say-acceptance` **204/204** · `logicops` · `float` ·
`linemax` · `dexp5-pin` · `editverb` **61/61** · `lptverb` **44/44** · `dskmsg`
**5/5** · `diskbasic` **34/34 verbs** · `fat-error` **8/8 FIND + 2/2 MOUNT + 5
directory checks** · `runtail` **9/9** · `castail` **31/31 + 1 pin** · `cassave`
**20/20** · **`readvar` 22/22 + 2 deferred**.

🔴 **THE FILED BASELINE IN §7 AND IN THE TASK WAS ONE SLICE STALE, AND THAT WAS
MEASURED RATHER THAN ASSUMED.** It read *citations 731 swept / basic 107/187,
`rowshape-check` 176 walked / 29 report-row*. Re-running those gates on a stashed
`6698e70` gives **734 / 107/188 / 177 / 30** — the numbers moved when D-CASSAVE
added `probes/basic/basic_probe_cassave.py`, one commit before this one, and the
filed set had been copied from
[`spec-probe-rowshape.md`](spec-probe-rowshape.md) §11.3 rather than re-run.
**This slice moved none of them** — it adds no file — so the correct claim is
*"unchanged at 734/177"*, and it takes a measured baseline to say that at all
([[a-prediction-copied-into-the-result-column]]). `injector-check` **336**,
`preflight-check` **181/86/95/95/0**, `unit-test` **59** and page-1 closure
**585+43** matched the filed values exactly.

⚠️ **THE FIRST CORPUS RUN WAS THROWN AWAY, AND THE REASON IS A RULE.** Two
**comment-only** edits to `sub/sub.asm` and `sub/equates.inc` landed *while* the
run was in flight; `omsx_preflight` correctly refused the next gate as
`STALE build/sub.rom`, and every reading after that point was worthless. The
standing rule is *"never rebuild while a differential runs"* — this widens it to
**never EDIT, of any kind**, because mtime does not care whether the bytes moved.
(They did not: the ROMs after those two edits hash identically to the ones the
knives were scored against.) The whole corpus was re-run from clean.

### 10.7 Corpus list, for the next slice

`unit-test` · `audit-citations` · `preflight-check` · `injector-check` ·
`rowshape-check` · `latch-check` (after `make repack-machine`) · `deadcode` ·
`lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance` · `logicops-acceptance` ·
`float-acceptance` · `linemax-acceptance` · `dexp5-pin` · `editverb-acceptance`
(61/61) · `lptverb-acceptance` (44/44) · `dskmsg-acceptance` (5/5) ·
`diskbasic-acceptance` (34/34) · `fat-error-acceptance` (8/8 + 2/2 + 5) ·
`runtail-acceptance` (9/9) · `castail-acceptance` (31/31 + 1 pin) ·
`cassave-acceptance` (20/20) · **`readvar-acceptance` (22/22 + 2 deferred) — new
this slice**.

⚠️ `lnblank REPEAT` defaults to 1. ⚠️ Write the loop in **bash**, not zsh: `make $t`
must word-split for `REPEAT=2`, and the rc must come from `make` itself and never
from a pipe's last stage.

### 10.8 The fix, as a program

Both columns are readings from the runs above — the "before" column is the
characterization's zerobas column at `16ba60f`, the "after" column is this
slice's `readvar-acceptance`. `RUN` is typed after each program.

```basic
10 DATA HELLO
20 READ A$
30 PRINT"[";A$;"]"
```

| | screen after `RUN` |
|---|---|
| VG-8020 / CF-3300 | `[HELLO]` |
| zerobas **before** | `Syntax error in 20` |
| zerobas **after** | `[HELLO]` |

```basic
10 DATA A,B
20 READ A$,B$
30 PRINT"[";A$;B$;"]"
```

| | screen after `RUN` |
|---|---|
| both references | `[AB]` |
| zerobas **before** | `Syntax error in 20` |
| zerobas **after** | `[AB]` |

And the two rows that are the point of having measured rather than guessed:

```basic
10 DATA PAD  ,X          ' trailing spaces are PRESERVED
20 READ A$
30 PRINT"[";A$;"]"
```
→ both references `[PAD  ]`, zerobas after **`[PAD  ]`**. The symmetric rule would
print `[PAD]`, and K-RV4 builds exactly that.

```basic
10 DATA HELLO            ' ...into a NUMERIC target
20 READ A
30 PRINT"[";A;"]"
```
→ both references **`Syntax error`**, zerobas **before** `[ 0 ]` (a silent wrong
answer), zerobas **after** **`Syntax error`**.
