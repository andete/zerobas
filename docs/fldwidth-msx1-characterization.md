# D-FLDWIDTH — what a `FIELD` width may BE, and what `FIELD` does when it isn't

*Measured 2026-08-08 at `f0b688d` (D-NAMSPC), `make fldwidth-characterize`,
`probes/basic/basic_probe_fldwidth.py`. Two sides: National CF-3300, zerobas
repack. 42 rows in ~36 s.*

🔴 **EVERY `FIELD` / `LSET` ROW HAS ONE REFERENCE, NOT TWO.** `FIELD` is Disk
BASIC; a diskless Philips VG-8020 answers `Syntax error` to the word, so it is
not an oracle here — it is a machine that cannot express the question. All 41
`dsk` rows rest on the **CF-3300 alone** (the disposition
`basic_probe_fldary.py` / `basic_probe_lvsites.py` already carry). Only
`s.joinctl` needs no disk. The probe says so per row.

🎯 **THE READING IS `LEN(A$)` — THE FIELD'S OWN WIDTH — NOT `OK`.** This whole
subject lives between *"accepted as 10"* and *"accepted as 0"*, and an `[OK]`
fixture cannot tell those apart. Every accepting row reads the width back out of
the field table; every refusing row reads the error name. That decision is what
turned the residual's *"zerobas answers `OK`"* into the sharper **zerobas
answers ` 0 `** — the field is really created, at width zero
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).

---

## 1. The readings

Base fixture: `OPEN"TS.DAT"AS #1` (RANDOM, the default 256-byte record), then the
statement under test, then the read-back. A fresh copy of `disk/test720.dsk` per
row.

| row | program (one statement per line) | CF-3300 | zerobas at `f0b688d` |
|---|---|---|---|
| **0. the POSITIVE CONTROLS — the working forms** | | | |
| `c.lit` | `FIELD#1,10 AS A$` / `PRINT LEN(A$)` | ` 10 ` | ` 10 ` 🟢 **control** |
| `c.two` | `FIELD#1,5 AS A$,7 AS B$` | ` 5  7 ` | ` 5  7 ` 🟢 **control** |
| `c.lset` | `FIELD#1,5 AS A$` / `LSET A$="AB"` / `PRINT A$` | `AB   ` | `AB   ` 🟢 **control** |
| `c.wsp` | `FIELD#1, 10 AS A$` *(space before the width)* | ` 10 ` | ` 10 ` ✅ 🟢 **the carve's row** |
| `c.wsp2` | `FIELD#1,5 AS A$, 7 AS B$` *(space at the 2nd item)* | ` 5  7 ` | ` 5  7 ` ✅ 🟢 **the carve's row** |
| **1. WHAT TYPES may a width be — the NUMERIC family, all green BEFORE** | | | |
| `n.pct` | `N%=10` / `FIELD#1,N% AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.bang` | `N!=10` / `FIELD#1,N! AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.hash` | `N#=10` / `FIELD#1,N# AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.paren` | `N=10` / `FIELD#1,(N) AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.expr` | `FIELD#1,4+6 AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.mul` | `FIELD#1,2*5 AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.ary` | `DIM N(3)` / `N(1)=10` / `FIELD#1,N(1) AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.fn` | `B$="ABCDEFGHIJ"` / `FIELD#1,LEN(B$) AS A$` | ` 10 ` | ` 10 ` ✅ |
| `n.val` | `FIELD#1,VAL("10") AS A$` | ` 10 ` | ` 10 ` ✅ |
| **2. the STRING family — THE SUBJECT, four roads to one fault** | | | |
| `s.var` | `N$="X"` / `FIELD#1,N$ AS A$` | **`Type mismatch`** | **` 0 `** 🔴 |
| `s.lit` | `FIELD#1,"X" AS A$` | **`Type mismatch`** | **` 0 `** 🔴 |
| `s.ary` | `DIM N$(3)` / `N$(1)="X"` / `FIELD#1,N$(1) AS A$` | **`Type mismatch`** | **` 0 `** 🔴 |
| `s.fn` | `FIELD#1,STR$(10) AS A$` | **`Type mismatch`** | **` 0 `** 🔴 |
| `s.join` | `DIM A$(3)` / `N=10` / `FIELD#1,N AS A$(1)` | **`Type mismatch`** | **`Syntax error`** 🔴 ⇐ D-NAMSPC's `z.fldvar` |
| `s.joinctl` | `DIM A$(3)` / `N=10` / `X=N AS A$(1)` — **FIELD taken out** | `Type mismatch` | `Type mismatch` 🟢 **control** |
| **3. the DOMAIN** | | | |
| `d.zero` | `FIELD#1,0 AS A$` | **` 0 `** | ` 0 ` ✅ 🎯 **0 IS LEGAL** |
| `d.neg` | `FIELD#1,-1 AS A$` | **`Illegal function call`** | **` 255 `** 🔴 |
| `d.256` | `FIELD#1,256 AS A$` | **`Illegal function call`** | **` 0 `** 🔴 |
| `d.257` | `FIELD#1,257 AS A$` | **`Illegal function call`** | **` 1 `** 🔴 |
| `d.big` | `FIELD#1,70000 AS A$` | **`Overflow`** | **` 0 `** 🔴 🎯 **a DIFFERENT error** |
| `d.frac` | `FIELD#1,10.7 AS A$` | **` 10 `** | ` 10 ` ✅ **truncates** |
| `d.div` | `FIELD#1,1/0 AS A$` | **`Division by zero`** | **` 0 `** 🔴 |
| `d.sum` | `FIELD#1,200 AS A$,100 AS B$` *(total 300)* | **`FIELD overflow`** | **` 200  100 `** 🔴 ⏸ **DEFERRED** (§3) |
| `d.sum1` | `FIELD#1,200 AS A$,57 AS B$` *(total 257)* | **`FIELD overflow`** | **` 200  57 `** 🔴 ⏸ **DEFERRED** (§3) |
| `d.sumok` | `FIELD#1,200 AS A$,56 AS B$` *(total 256)* | ` 200  56 ` | ` 200  56 ` 🟢 **control** |
| **4. is it the WIDTH only? — the CHANNEL is a second `eval`** | | | |
| `ch.str` | `N$="1"` / `FIELD#N$,10 AS A$` | `Type mismatch` | `Type mismatch` ✅ |
| `ch.expr` | `FIELD#0+1,10 AS A$` | ` 10 ` | ` 10 ` 🟢 **control** |
| **5. the SECOND item — per-item, or once at entry?** | | | |
| `m.str2` | `N$="X"` / `FIELD#1,5 AS A$,N$ AS B$` | **`Type mismatch`** | **` 5  0 `** 🔴 |
| `m.trap` | …trapped: `PRINT ERR;LEN(A$)` | **` 13  5 `** | **`<NO OUTPUT>`** 🔴 🎯 **no rollback** |
| `m.neg2` | `FIELD#1,5 AS A$,-1 AS B$` | **`Illegal function call`** | **` 5  255 `** 🔴 |
| **6. the TARGET's type — the twin of D-LRVAR, one statement over** | | | |
| `t.num` | `FIELD#1,10 AS A` | **`Type mismatch`** | **`Syntax error`** 🔴 |
| `t.numctl` | `A=1` / `LSET A=2` — D-LRVAR's shipped row | `Type mismatch` | `Type mismatch` 🟢 **control** |
| `t.noas` | `FIELD#1,10 A$` — no `AS` | `Syntax error` | `Syntax error` ✅ 🔴 **NEGATIVE** |
| `t.nonm` | `FIELD#1,10 AS 5` — target is not a NAME | `Syntax error` | `Syntax error` ✅ 🔴 **NEGATIVE** |
| **7. ORDER — two faults competing in one statement** | | | |
| `o.wt` | `N$="X"` / `FIELD#1,N$ AS A` — string width, numeric target | `Type mismatch` | `Syntax error` 🔴 |
| `o.dt` | `FIELD#1,-1 AS A` — bad-DOMAIN width, numeric target | **`Illegal function call`** | `Syntax error` 🔴 🎯 **the row that ORDERS them** |
| `o.chan` | `N$="X"` / `FIELD#2,N$ AS A$` — bad channel, string width | `Bad file number` | `Bad file number` ✅ |

**24 of the 42 rows agreed** at `f0b688d`.

---

## 2. The rule, stated from the readings and from nothing else

> A `FIELD` width is a **BYTE ARGUMENT**, and it is the ordinary two-stage one
> this tree already implements for every other numeric argument: the expression
> is evaluated, a **STRING is `Type mismatch`** and a deferred arithmetic fault
> (`1/0`) is **`Division by zero`**; the value is then coerced to int16
> (**`Overflow`** beyond it) and required to lie in **0..255**
> (**`Illegal function call`** outside — and **0 is inside**); a fraction
> **TRUNCATES**. The width is then checked against the channel's record length
> as a **RUNNING TOTAL** — **`FIELD overflow`** the moment it would exceed it.
> Every one of these checks runs **PER ITEM**, in list order, and **does not
> roll back the items already placed**. The CHANNEL is checked before any of
> it; the WIDTH is checked before the TARGET's type.

Six clauses are readings no earlier row asked, and each one decides bytes:

* 🎯 **`d.big` vs `d.neg`/`d.256` — TWO DIFFERENT ERRORS, WHICH IS WHAT NAMES
  THE RULE.** 70000 is `Overflow` (ERR 6) and −1/256/257 are `Illegal function
  call` (ERR 5). That is not "a domain check"; it is exactly
  `get_byte_arg`'s **two stages** — `get_int16_checked` first, the 0..255 test
  second (`basic/interp.asm:1567`) — the routine `CHR$`, `STRING$`, `SPACE$`,
  `ON n` and `WIDTH n` already share. Had both come back as one error the fix
  would have been a hand-rolled bound; they did not, so the fix is a **call to
  code that already ships and is already the reference's rule**.
* 🎯 **`d.zero` — 0 IS LEGAL, and it is the row that stops the rule being
  1..255.** `basic/field.asm`'s own header says *"field widths are 1..255"*.
  The CF-3300 accepts `FIELD#1,0 AS A$` and reports `LEN(A$)` = 0. A fix built
  on the header's claim would have shipped a divergence the header invented.
* 🎯 **`s.var` / `s.lit` / `s.ary` / `s.fn` — FOUR ROADS, ONE ANSWER, AND NO
  SPACE IN ANY OF THEM.** The residual arrived with one row (`z.fldstr`). A
  string *variable*, a string *literal*, a string *array element* and a string
  *function* all read `Type mismatch` on the reference and all read **` 0 `**
  here. One shared cause, measured rather than assumed — and ` 0 ` (not `OK`)
  is the reading that says the field is genuinely created at width zero, which
  is what `type_mismatch_set` leaves in `DE`.
* 🎯 **`m.trap` — PER ITEM, AND NO ROLLBACK.** `FIELD#1,5 AS A$,N$ AS B$`
  trapped reads **` 13  5 `**: ERR 13, and `A$` is **still 5 bytes wide**. So
  the check cannot be a once-at-entry validation pass, and the items placed
  before the fault stay placed. This is the row that says the check belongs
  *inside* `exf_item`'s loop and needs no undo.
* 🎯 **`o.dt` — THE WIDTH IS CHECKED BEFORE THE TARGET.** `FIELD#1,-1 AS A` has
  two faults and the reference answers **`Illegal function call`**, not `Type
  mismatch`. ⚠️ `o.wt` **cannot** say this — a string width and a numeric target
  both raise ERR 13, so it agrees whichever fires first
  ([[one-row-cannot-separate-two-rules]]). `o.dt` was added for exactly that.
  And `o.chan` puts the CHANNEL first: `FIELD#2,N$ AS A$` is `Bad file number`
  on both sides, so the channel check already precedes the width on this tree.
* 🎯 **`d.sum` / `d.sum1` / `d.sumok` — THE RECORD-LENGTH RULE IS A SEPARATE
  RULE, AND NO PER-ITEM DOMAIN CHECK CAN REACH IT.** 200+56 = 256 is accepted;
  200+57 = 257 is **`FIELD overflow`** (ERR 50). Both individual widths are
  inside 0..255, so the two-stage byte rule above is blind to them by
  construction. Deferred — §3.

---

## 3. ⏸ `d.sum` / `d.sum1` — DEFERRED, and the control that says why

`d.sumok` (total exactly 256) is accepted on both sides; `d.sum1` (257) is
`FIELD overflow` on the CF-3300 and ` 200  57 ` here. The boundary is therefore
pinned to the byte, and the divergence is real — but it is a **different rule**
from the one this slice implements:

* it needs the channel's **record length**, which lives in `FCH_RECLENS[ch]`
  (`basic/sysvars.inc:2843`) and whose only accessor, `load_reclen`
  (`basic/randio-body.inc:270`), is **sub-ROM** (`sub/randio.asm:47`) and not
  callable from `ex_field` in main page 1;
* fetching it main-side is ~14 B of index arithmetic before any compare, and the
  whole check prices at **≈27 B** (spec §6.5) against a **6 B** page-1 wall;
* and its own denominator is not built: every row here uses the **default**
  256-byte record, so nothing measured separates *"checked against the record
  length"* from *"checked against a constant 256"*. That needs `OPEN ... LEN=r`
  rows, which is the disk-BASIC option surface, not this one.

Both rows are **measured, printed and scored in neither direction**; a deferred
row that started agreeing would itself be a finding. Filed in `TODO.md` as its
own residual with these three readings as its starting denominator.

---

## 4. 🔴 The reader was blind to its own subject, and the FIRST full run found it

The probe's `bracket()` walks a tuple of error names and returns the first that
appears in the screen tail. `Overflow` is a **substring of `FIELD overflow`**,
and the first draft listed it earlier — so a screen reading `FIELD overflow in
30` was recorded as `<Overflow>`, and the one error name this whole battery
exists to look for was invisible to its own reader
([[readout-blind-to-its-own-subject]]).

It failed by **agreeing with a plausible answer**: `d.sum` came back
`<Overflow>` and that is exactly what a naive reading of "300 is too big" would
predict, so nothing about the row looked wrong. What exposed it was `d.big`
(70000) returning the *same* string for a genuinely different fault — two rows
that must differ, reading identically. The needles are now sorted **longest
first**, and the two rows separate: `<FIELD overflow>` and `<Overflow>`.

⚠️ The same tuple is matched **case-insensitively**, and that is a scope
decision rather than an accident: zerobas prints `File not OPEN` where the
reference prints `File not open`. Message *wording* is D-MSGEXACT's surface, and
matching it here would put a separately-owned divergence inside every ERR 59
row.

---

## 5. Denominator

**(WHAT TYPE the width expression has: an integer literal, a `%`/`!`/`#`
scalar, a parenthesised unsuffixed name, a numeric array element, a `+`/`*`
expression, a numeric FUNCTION of a string (`LEN`) and of a literal (`VAL`) —
against a string VARIABLE, a string LITERAL, a string ARRAY ELEMENT, a string
FUNCTION, and the unsuffixed name D-NAMSPC's name scan JOINS with the following
`AS` into a string reference) × (WHAT DOMAIN: 0, negative, past the BYTE
`ex_field` keeps in `E` (256 and 257), past int16 (70000), a deferred
arithmetic fault (`1/0`), a non-integer (10.7 — truncate or round), and a
RUNNING TOTAL one byte either side of the 256-byte record) × (WHICH SURFACE:
the width, the CHANNEL's own second `eval`, the TARGET's type test, and the
SECOND item of a multi-item list — where a per-item check and a once-at-entry
one differ, with a TRAPPED row that reads whether the first item survived) ×
(WHICH ERROR and IN WHAT ORDER: width-vs-target and channel-vs-width, each with
two faults in one statement and — for `o.dt` — two DIFFERENT error codes so the
order is observable).** Every group carries the WORKING form of its own fixture
as its positive control, two negative controls bound the ERR-13 change (`t.noas`
no `AS` at all, `t.nonm` a target that is not a name), and every accepting row
reads the WIDTH BACK rather than printing `OK`.

⚠️ 🎯 **AND THE NUMERIC SPELLINGS ARE NOT FREE OF THE `AS` PROBLEM, WHICH IS WHY
THE GROUP LOOKS THE WAY IT DOES.** `AS` is not in `basic/kwtable.inc`, so a
width is followed by two bare LETTERS — and since D-NAMSPC an unsuffixed name
scan crosses a space. `FIELD#1,N AS A$` therefore parses as the single name
`NA$` (that IS `s.join`). The suffix, the `)` and the `(` are what terminate the
scan before ` AS`, which is why `n.pct`/`n.bang`/`n.hash`, `n.paren` and `n.ary`
are the green spellings of "a variable as the width" and a bare `N` is not one.

**Not covered, and named rather than implied:** `GET`/`PUT` record I-O through a
bad field; a `LEN=` record length other than the 256-byte default (which is what
`d.sum`'s residual needs); `FIELD` on a `CAS:` channel (`TODO.md` already
carries that as its own item); `RSET` (it shares `lrset_common` with `LSET`, so
it is not a second site); and message WORDING (D-MSGEXACT's surface — §4).
