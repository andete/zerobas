<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# A LINE-NUMBER LIST IS A MODE, NOT A LIST — MSX1 characterization (D-LNLIST)

Measured 2026-08-01 on **two** references — a **Philips VG-8020** (MSX1, cassette
BASIC) and a **National CF-3300** (MSX1, Disk BASIC) — which **agree on every row
below**, `--repeat 2` on independent boots, past the echo guard. Probe
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
batteries `lnl` (stored bytes) and `lnld` (what those bytes *mean*).
Readout `("stored_line", TXTTAB)`; the gloss prints ASCII verbatim and everything
else as `<XX>`.

Spec: [`docs/spec-basic-lnlist.md`](spec-basic-lnlist.md).

---

## 0. Why this battery exists

D-NAMDOT filed **one** row and deliberately did not fix it
([`docs/namedot-msx1-characterization.md`](namedot-msx1-characterization.md) §6):

```
20 GOTO 1.5   ref -> <89> <0E><01><00>.<0E><05><00>
              zb  -> <89> <0E><01><00><1D>@P<00><00>
```

The reference crunches `1` to `$0E,0001`, copies the `.` **verbatim**, and
crunches `5` as a **second** `$0E`. `TODO.md` filed it as *"a `.` does not end a
line-number list"* and pointed at `bl_num`'s comma-list loop.

🔴 **THAT TITLE IS WRONG, AND ONE ROW IS WHY IT COULD BE.** The `.` is not
special at all. `1+5`, `1-5`, `1*5`, `1;5`, `1#5`, `1(5)`, `1/5`, `1^5`, `1\5`,
`1=5`, `1<5`, `1>5` **all** grow a second `$0E`, and `1.5.7` grows a third. What
the reference has after a branch keyword is not a comma list with one extra
separator — it is a **MODE** that runs to the end of the *statement*. Fixing this
from the row that found it would have added `.` to a separator test and shipped a
rule roughly a dozen characters too narrow.

Three named rules; every row below separates them.

| | rule |
|---|---|
| **E** (end) | the list ends at the first character that is neither a digit nor `,`. **zerobas today** ([`basic/tokenise.inc`](../basic/tokenise.inc) `bl_num`). |
| **D** (dot) | `.` *joins* `,` as a separator that does not end the list; everything else still ends it. **The filed prescription.** |
| **A** (mode) | a branch keyword arms a *line-number mode*: while armed, every digit run that would begin a numeric constant becomes `$0E,<v>` instead. Everything else crunches normally. |

⚠️ **`dot-goto` cannot tell D from A.** Both predict its exact bytes. That is
precisely why it may not be fixed from the row that found it — the
[D-NOTOPEN2](notopen-chan-err59-slice.md) trap, where 3 of 7 rows gave a
different answer than all 7.

---

## 1. Round 1 — rule D is refuted outright

```
lnl-plus     20 GOTO 1+5      <89> <0E><01><00><F1><0E><05><00>
lnl-minus    20 GOTO 1-5      <89> <0E><01><00><F2><0E><05><00>
lnl-star     20 GOTO 1*5      <89> <0E><01><00><F3><0E><05><00>
lnl-semi     20 GOTO 1;5      <89> <0E><01><00>;<0E><05><00>
lnl-hash     20 GOTO 1#5      <89> <0E><01><00>#<0E><05><00>
lnl-paren    20 GOTO 1(5)     <89> <0E><01><00>(<0E><05><00>)
lnl-quote    20 GOTO 1"5"     <89> <0E><01><00>"5"
lnl-three    20 GOTO 1.5.7    <89> <0E><01><00>.<0E><05><00>.<0E><07><00>
```

An operator becomes its **operator token** and the number behind it is *still* a
line-number reference. `1.5.7` yields **three** `$0E`s. The mode is not a list
and the `.` is not a separator.

**Where it stops, and where it never started:**

```
lnl-colon    20 GOTO 1.5:A=7  <89> <0E><01><00>.<0E><05><00>:A<EF><18>
lnl-colctl^  20 GOTO 1:A=7    <89> <0E><01><00>:A<EF><18>
lnl-alpha    20 GOTO 1X5      <89> <0E><01><00>X5
lnl-nokw^    20 A=1.5         A<EF><1D>A<15><00><00>
lnl-ctl^     20 GOTO 15       <89> <0E><0F><00>
```

After the `:` the `7` is an ordinary `<18>`, so the mode ends somewhere. `1X5`
keeps `X5` as name bytes — a name absorbs the following digit before any numeric
path sees it. With **no** branch keyword, `1.5` is still the ordinary
single-precision literal `<1D>A<15><00><00>`: the mode is scoped to the branch
keyword and does not touch the number scanner every other battery in this probe
pins.

**Blanks and a leading `.`:**

```
lnl-blkl     20 GOTO 1 .5     <89> <0E><01><00> .<0E><05><00>
lnl-blkr     20 GOTO 1. 5     <89> <0E><01><00>. <0E><05><00>
lnl-blk2     20 GOTO 1 . 5    <89> <0E><01><00> . <0E><05><00>
lnl-lead     20 GOTO .5       <89> .<0E><05><00>
lnl-bare     20 GOTO .        <89> .
```

⚠️ **`lnl-lead` and `lnl-bare` say the `.` does not lead a literal in this mode.**
`GOTO .5` stores the value **5**, not 0.5 — the `.` is copied and the digit run
behind it is its own line-number reference. And a bare `.` after `GOTO` stays a
bare `.`, where D-NAMDOT's **R-D2** would make it the single-precision literal 0
(`20 A=.` → `$1D,0,0,0,0`). The mode suppresses R-D2.

**All six branch keywords behave alike**, and the real comma list still works:

```
lnl-gosub    20 GOSUB 1.5           <8D> <0E><01><00>.<0E><05><00>
lnl-then     20 IF A THEN 1.5       <8B> A <DA> <0E><01><00>.<0E><05><00>
lnl-restore  20 RESTORE 1.5         <8C> <0E><01><00>.<0E><05><00>
lnl-run      20 RUN 1.5             <8A> <0E><01><00>.<0E><05><00>
lnl-resume   20 RESUME 1.5          <A7> <0E><01><00>.<0E><05><00>
lnl-on1      20 ON A GOTO 1.5,2     <95> A <89> <0E><01><00>.<0E><05><00>,<0E><02><00>
lnl-on2      20 ON A GOTO 1,2.5     <95> A <89> <0E><01><00>,<0E><02><00>.<0E><05><00>
```

**Rule A holds. Rule D and rule E are both refuted.**

---

## 2. Round 2 — what turns the mode OFF, and a confound in my own row

Round 1 made *"what clears it"* the whole remaining question, and answered only
`:` — or so it looked.

```
lnl-thenpr   20 IF A THEN PRINT 5   <8B> A <DA> <91> <16>
lnl-kw       20 GOTO 1 AND 5        <89> <0E><01><00> <F6> <16>
lnl-fnkw     20 GOTO 1+ABS(5)       <89> <0E><01><00><F1><FF><86>(<16>)
lnl-name     20 GOTO X,5            <89> X,<16>
lnl-qtail    20 GOTO 1"A"5          <89> <0E><01><00>"A"<0E><05><00>
lnl-hex      20 GOTO &H10           <89> <0C><10><00>
```

🔴 **`lnl-thenpr` IS THE MOST LOAD-BEARING ROW IN THE PROBE.** If a statement
keyword did **not** clear the mode, `IF A THEN PRINT 5` would crunch its `5` as a
line number and every program of that shape would break. It clears. zerobas
cannot regress here *today* because it has no mode at all — an implementation of
rule A can, which is exactly what makes this cell worth pinning.

A **name** clears it too (`X,5` → `<16>`, and no `$0E` anywhere). A string
literal does **not**. `&H10` never reaches the digit path at all — a radix
constant is crunched as `$0C,<v>` as usual.

🔴 **AND `lnl-colon` TURNED OUT NOT TO MEASURE `:` AT ALL.** Its payload is
`GOTO 1.5:A=7`, and the statement after the colon begins with the **name** `A` —
which `lnl-name` now shows clears the mode on its own. A row carrying two
candidate causes measures neither. It is kept (its `$0E . $0E` half is still a
reading) and round 3 asks the question properly.

---

## 3. Round 3 — the boundary is ALPHABETIC vs SYMBOLIC, not a token value

Round 2 left an apparent contradiction: `+` `-` `*` keep the mode but `AND`
drops it, and a value threshold cannot explain that (`$F1..$F3` keep, `$F6` AND
drops, and `$91` PRINT is *below* all of them and drops). Round 3 walked the
whole contiguous operator range.

```
lnl-colsep   20 GOTO 1:5        <89> <0E><01><00>:<16>            :   CLEARS
lnl-namemid  20 GOTO 1,X,5      <89> <0E><01><00>,X,<16>          name CLEARS
lnl-gt       20 GOTO 1>5        <89> <0E><01><00><EE><0E><05><00>  $EE keeps
lnl-eq       20 GOTO 1=5        <89> <0E><01><00><EF><0E><05><00>  $EF keeps
lnl-lt       20 GOTO 1<5        <89> <0E><01><00><F0><0E><05><00>  $F0 keeps
lnl-slash    20 GOTO 1/5        <89> <0E><01><00><F4><0E><05><00>  $F4 keeps
lnl-pow      20 GOTO 1^5        <89> <0E><01><00><F5><0E><05><00>  $F5 keeps
lnl-or       20 GOTO 1 OR 5     <89> <0E><01><00> <F7> <16>        $F7 CLEARS
lnl-mod      20 GOTO 1 MOD 5    <89> <0E><01><00> <FB> <16>        $FB CLEARS
lnl-idiv     20 GOTO 1\5        <89> <0E><01><00><FC><0E><05><00>  $FC keeps
```

🔴 **`\` IS `$FC` AND KEEPS THE MODE; `MOD` IS `$FB` AND CLEARS IT.** The two
classes are *interleaved* in the token-value space, so no threshold, mask or
range test can separate them. What separates them is that `MOD`, `OR`, `AND`,
`PRINT` and `ABS` are spelled with **letters** and `\ ^ / < = > + - *` are
**symbols**.

And `lnl-colsep` settles the confound: `GOTO 1:5` — a colon with no name behind
it — reads `<16>`. **`:` clears the mode on its own.**

So the clearing set is: **anything alphabetic** (a reserved *word*, or a variable
*name*) **and the statement separator `:`**. Symbolic operators, punctuation
(`, ; # ( ) .`), string literals and blanks all leave it armed.

---

## 4. Round 4 — the two symbols that expand to words

zerobas' tokeniser already splits along exactly the boundary round 3 found: word
keywords go through `match_kw`, symbolic operators through the `tk_op_*` arms. Two
characters break that alignment — `?` (PRINT) and `_` (CALL) are **symbols that
expand to word tokens** without entering `match_kw`.

```
lnl-quest    20 IF A THEN ?5          <8B> A <DA> <91><16>
lnl-apos     20 GOTO 1'5              <89> <0E><01><00>:<8F><E6>5
lnl-under    20 IF A THEN _X 5        <8B> A <DA> _X 5
lnl-call     20 IF A THEN CALL X 5    <8B> A <DA> <CA> X 5
```

🔴 **`?` CLEARS THE MODE.** `IF A THEN ?5` stores `<91><16>`, not `<91>` +
`$0E,0005`. An implementation that hangs the clear off `match_kw` alone is wrong
on a shape as ordinary as `?`.

🔴 **`lnl-under` AND `lnl-call` ARE BOTH CONFOUNDED — the same mistake as
`lnl-colon`, one round later.** Their trailing `5` is stored as **verbatim ASCII
`5`**, not as `<16>` and not as `$0E`: the CALL device-name scan reached across
the blank and took the digit before any numeric path could see it. Neither row
can say whether `CALL` clears the mode. `lnl-callp` (`20 IF A THEN CALL X+5`)
asks it past the name scan, using round 3's result that a *symbolic* operator
leaves the mode armed.

🔴 **AND `lnl-callp` WAS EATEN TOO — three rows, three times.** The reference
stores `<CA> X5`: it dropped the `+` **entirely** and still kept the `5` as
verbatim ASCII. The way past the scan is not a different operator but a different
**terminator** — `(` is what ends an extended statement's name, and round 3
already pins that `(` on its own leaves the mode **armed** (`lnl-paren`):

```
lnl-callpar^   20 IF A THEN CALL X(5)   <8B> A <DA> <CA> X(<16>)
lnl-underpar^  20 IF A THEN _X(5)       <8B> A <DA> _X(<16>)
```

**`CALL` and `_` DO clear the mode.** The `5` is the ordinary integer `<16>`, not
`$0E,0005`, and with `(` armed-neutral the only thing left to have cleared it is
the `CALL` token itself. zerobas already agrees on both rows, so they are
two-sided controls — and they are the cells that say *where* the clear belongs
(§3 of the spec: at the `match_kw` site, not inside `branch_lineno`, which
`CALL` bypasses).

The three eaten rows are kept anyway: that verbatim `5` is a reading nobody had,
and the zerobas column (`_X <16>`, `<CA> X<F1><16>`) made the CALL device-name
scan a separate filed item.

✅ **CLOSED by D-CNAME** ([`spec-basic-cname.md`](spec-basic-cname.md),
[`cname-msx1-characterization.md`](cname-msx1-characterization.md)). All three
rows now agree on all three sides and their `KNOWN_DIVERGE` entries are
**retired**. ⚠️ And the rule they suggested was wrong: a 56-row contiguous walk
showed the scan drops `$21..$2F`, **keeps** `; < = > ? @ [ \ ] ^ _ ` ~`
verbatim, and ends only at EOL / `:` / `(`. `+ - * /` are dropped while
`^ \ = < >` are kept, so these three rows agreed with two different wrong rules
— the same "one row cannot separate two rules" shape this battery was built to
answer.

**The trap-parser shapes, pinned here on purpose:**

```
lnl-empty    20 ON KEY GOSUB 100,,600  <95> <CC> <8D> <0E>d<00>,,<0E>X<02>
lnl-empty2   20 ON STRIG GOSUB ,300    <95> <FF><A3> <8D> ,<0E>,<01>
```

`ON KEY GOSUB` / `ON STRIG GOSUB` walk the crunched list looking for `$0E`, and
`bl_num`'s own comment records what happened the last time this path emitted the
wrong number of them — the parsers ran off the end of their list and the executor
landed on a bare literal. Any change to how many `$0E` bytes a list carries has
to answer to these two rows.

---

## 5. What the bytes MEAN — the `lnld` say battery

The stored bytes cannot say whether the executor *reads* the extra `$0E`, and
that is the question that decides how much of this matters. Every payload prints
brackets and asks `ERR`, because a statement that aborts never reaches its own
`]` and `<none>` on every side compares EQUAL
([`namedot-msx1-characterization.md`](namedot-msx1-characterization.md) §4).
Reading is `[ A  ERR ]` — where the branch landed, and whether it aborted.

| row | program | ref |
|---|---|---|
| `lnld-ctl`^ | `10 GOTO 30` | ` 30  0 ` |
| `lnld-goto` | `10 GOTO 30.40` | ` 30  0 ` |
| `lnld-und2` | `10 GOTO 30.99` (99 absent) | ` 30  0 ` |
| `lnld-und1` | `10 GOTO 99.30` (99 absent) | ` 0  8 ` |
| `lnld-onctl`^ | `10 ON 2 GOTO 30,50` | ` 50  0 ` |
| `lnld-on` | `10 ON 2 GOTO 30.40,50` | ` 0  2 ` |

**`GOTO` honours the FIRST `$0E` and ignores everything after it.** The
`und1`/`und2` pair is what says so and neither row alone could: a missing
*second* target is harmless, a missing *first* one raises error 8
(`Undefined line number`).

**`ON … GOTO` does not.** `ON 2 GOTO 30.40,50` is **error 2, `Syntax error`** —
the extra `$0E` inside the first slot is not a new list entry and not ignorable
either; the `ON` executor chokes on it. So the `.` is not a separator to the
*executor* any more than it is to the crunch.

---

## 6. The rule, as measured

* **R-L1 (arm)** — crunching `GOTO`, `GOSUB`, `THEN`, `RESTORE`, `RUN` or
  `RESUME` arms *line-number mode*. It is armed afresh for each line.
* **R-L2 (effect)** — while armed, a digit that would begin a numeric constant
  begins a **line-number reference** instead, crunched `$0E,<value LE>` with
  D-LNBLANK **R5**'s blank transparency (`GOTO 1 0` is still `$0E,000A`); and a
  `.` that would begin a numeric constant under D-NAMDOT **R-D2** is copied
  **verbatim** instead. Everything else crunches exactly as it does outside the
  mode.
* **R-L3 (disarm)** — the mode is cleared by anything **alphabetic** — a reserved
  word (`AND`, `OR`, `MOD`, `PRINT`, `ABS`, `CALL`, …) or a variable **name** —
  by the two symbols that expand to word tokens (`?` and `_`, both measured),
  and by the statement separator **`:`**. Symbolic operators
  (`> = < + - * / ^ \`), punctuation (`, ; # ( ) .`), string literals and blanks
  leave it armed.

⚠️ **R-L1 is not new; R-L2 and R-L3 are.** zerobas already crunches the *first*
number after those six keywords, and already walks a comma list. What it has
never had is a mode that survives a non-comma character.

---

## 7. What was NOT measured

* **Whether the mode survives `&H…`** — `lnl-hex` shows a radix constant is not
  crunched as a line number, but nothing follows it in that row, so whether the
  mode is still armed afterwards is unread. It cannot change the fix: `&`
  reaches `tk_hex` before any digit path.
* **`LIST` / `DELETE` / `AUTO` / `RENUM` / `ELSE`** — these emit no `$0E` at all
  and `DELETE`/`AUTO`/`RENUM` have no token; already filed as separate `TODO.md`
  items and deliberately not folded in (the [D-MFDOM](maxfiles-domain-slice.md)
  trap).
* **The verbatim `5` in `lnl-under` / `lnl-call`** — a property of the CALL
  device-name scan, not of this mode. Whether zerobas matches it is read from
  the zb column and filed separately if it does not.
