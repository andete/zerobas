# D-NAMSPC — a SPACE *inside* a variable reference's NAME

*Measured 2026-08-08 at `36a107e` (D-TGTSPC), `make namspc-characterize`,
`probes/basic/basic_probe_namspc.py`. Three sides: Philips VG-8020, National
CF-3300, zerobas repack. 58 rows in ~87 s.*

🎯 **BOTH REFERENCES AGREE ON ALL 56 ROWS THEY CAN BOTH EXPRESS.**

🔴 **TWO ROWS HAVE ONE REFERENCE, NOT TWO.** `z.fldctl` / `z.fldvar` / `z.fldstr`
use `FIELD`, which is Disk BASIC; a diskless VG-8020 answers `Syntax error` to
the word, so it is not an oracle for them — it is a machine that cannot express
the question. Those rows rest on the **CF-3300 alone**. The probe says so per row.

---

## 1. The readings

| row | program (one statement per line) | both references | zerobas at `36a107e` |
|---|---|---|---|
| **0. the TOKENISER — is the space even THERE?** | | | |
| `t.ctl` | `1 AB=1` *(stored, never run)* | `4142ef1200` | same 🟢 **control** |
| `t.name` | `1 A B=1` | `4142**20**42…` → `412042ef1200` | same ✅ |
| `t.dctl` | `1 AB$="X"` | `414224ef22582200` | same 🟢 **control** |
| `t.dollar` | `1 AB $="X"` | `41422024ef22582200` | same ✅ |
| `t.digctl` | `1 A1=1` | `4131ef1200` | same 🟢 **control** |
| `t.dig` | `1 A 1=1` | `4120**31**ef1200` | same ✅ 🎯 **the digit is still VERBATIM** |
| `t.kwctl` | `1 SCORE=1` | `5343**f7**45ef1200` — `SC`+`OR`+`E` | same 🟢 **control** |
| `t.kw` | `1 SC ORE=1` | `534320**f7**45ef1200` | same ✅ 🔴 **the token is still there** |
| `t.andctl` | `1 AND=1` | `**f6**ef1200` — one token | same 🟢 **control** |
| `t.and` | `1 A ND=1` | `41204e44ef1200` — **no token** | same ✅ |
| `t.absctl` | `1 ABS=1` | `**ff86**ef1200` — one token | same 🟢 **control** |
| `t.abs` | `1 A BS=1` | `41204253ef1200` — **no token** | same ✅ |
| **1. R-VALUE — `ev_f_var` / `var_str_type`, which never touch `tgt_parse`** | | | |
| `c.let` | `AB=7` / `PRINT AB` | ` 7 ` | ` 7 ` 🟢 **control** |
| `r.name` | `AB=7` / `PRINT A B` | **` 7 `** — ONE value | **` 0  0 `** 🔴 🎯 **the universality row** |
| `r.multi` | `AB=7` / `PRINT A  B` *(2 spaces)* | ` 7 ` | ` 0  0 ` 🔴 |
| `r.three` | `AB=7` / `PRINT A B C` | ` 7 ` | ` 0  0  0 ` 🔴 |
| `r.run` | `AB=7` / `PRINT AB CD` | ` 7 ` | ` 7  0 ` 🔴 |
| `r.digctl` | `A1=7` / `A=3` / `PRINT A1` | ` 7 ` | ` 7 ` 🟢 **control** |
| `r.dig` | `A1=7` / `A=3` / `PRINT A 1` | ` 7 ` | **`<RUN SCROLLED OFF>`** 🔴 **a HANG** |
| `r.strctl` | `AB$="HI"` / `PRINT AB$` | `HI` | `HI` 🟢 **control** |
| `r.instr` | `AB$="HI"` / `PRINT A B$` | `HI` | ` 0 ` 🔴 |
| `r.dollar` | `AB$="HI"` / `PRINT AB $` | `HI` | **`<RUN SCROLLED OFF>`** 🔴 |
| `r.pctctl` | `AB%=7` / `PRINT AB%` | ` 7 ` | ` 7 ` 🟢 **control** |
| `r.pct` | `AB%=7` / `PRINT AB %` | ` 7 ` | **`<RUN SCROLLED OFF>`** 🔴 |
| `r.bangctl` | `AB!=7` / `PRINT AB!` | ` 7 ` | ` 7 ` 🟢 **control** |
| `r.bang` | `AB!=7` / `PRINT AB !` | ` 7 ` | **`<RUN SCROLLED OFF>`** 🔴 |
| `r.hashctl` | `AB#=7` / `PRINT AB#` | ` 7 ` | ` 7 ` 🟢 **control** |
| `r.hash` | `AB#=7` / `PRINT AB #` | ` 7 ` | **`<RUN SCROLLED OFF>`** 🔴 |
| **2. ASSIGNMENT — the space on the STORE side, read back CONTIGUOUS** | | | |
| `a.name` | `A B=7` / `PRINT AB` | ` 7 ` | `Syntax error` 🔴 |
| `a.dig` | `A 1=7` / `A=3` / `PRINT A1` | ` 7 ` | `Syntax error` 🔴 |
| `a.str` | `A B$="HI"` / `PRINT AB$` | `HI` | `Syntax error` 🔴 |
| `a.dollar` | `AB $="HI"` / `PRINT AB$` | `HI` | `Syntax error` 🔴 |
| `a.sig` | `A B C=7` / `PRINT AB` | ` 7 ` | `Syntax error` 🔴 |
| **3. OTHER STATEMENT SURFACES — nine more `var_name_key` / `var_str_type` callers** | | | |
| `s.ifctl` | `AB=7` / `IF AB=7 THEN…` | `OK` | `OK` 🟢 **control** |
| `s.if` | `AB=7` / `IF A B=7 THEN…` | `OK` | `Syntax error` 🔴 |
| `s.forctl` | `FOR AB=1 TO 2` / `NEXT AB` | `OK` | `OK` 🟢 **control** |
| `s.for` | `FOR A B=1 TO 2` / `NEXT AB` | `OK` | `Syntax error` 🔴 |
| `s.next` | `FOR AB=1 TO 2` / `NEXT A B` | **`OK`** | `NEXT without FOR` 🔴 ⇐ **D-TGTSPC's `x.name`** |
| `s.dimctl` | `DIM AB(3)` / `AB(1)=7` / `PRINT AB(1)` | ` 7 ` | ` 7 ` 🟢 **control** |
| `s.dim` | `DIM A B(3)` / … | ` 7 ` | `Syntax error` 🔴 |
| `s.ary` | `DIM AB(3)` / `A B(1)=7` / … | ` 7 ` | `Syntax error` 🔴 |
| `s.readctl` | `DATA 7` / `READ AB` / `PRINT AB` | ` 7 ` | ` 7 ` 🟢 **control** |
| `s.read` | `DATA 7` / `READ A B` / `PRINT AB` | ` 7 ` | `Syntax error` 🔴 |
| `s.swapctl` | `AB=7` / `CD=9` / `SWAP AB,CD` | ` 9  7 ` | ` 9  7 ` 🟢 **control** |
| `s.swap` | `AB=7` / `CD=9` / `SWAP A B,CD` | ` 9  7 ` | `Syntax error` 🔴 |
| **4. the KEYWORD constraint, at runtime** | | | |
| `k.and` | `AN=7` / `PRINT A ND` | ` 7 ` — the name `AN` | ` 0  0 ` 🔴 |
| `k.abs` | `AB=7` / `PRINT A BS` | ` 7 ` — the name `AB` | ` 0  0 ` 🔴 |
| **5. the NEGATIVE controls** | | | |
| `z.kw` | `SC ORE=7` / `PRINT"[OK]"` | **`Syntax error`** | `Syntax error` ✅ 🔴 **NEGATIVE** |
| `z.miss` | `FOR A=1 TO 2` / `NEXT A B` | **`NEXT without FOR`** | `Syntax error` 🔴 **NEGATIVE** |
| **6. a TRAILING space — the "must not disturb" set** | | | |
| `w.let` | `AB =7` / `PRINT AB` | ` 7 ` | ` 7 ` ✅ |
| `w.print` | `AB=7` / `PRINT AB ;` | ` 7 ` | ` 7 ` ✅ |
| `w.for` | `FOR AB =1 TO 2` / `NEXT` | `OK` | `OK` ✅ |
| `w.comma` | `AB=7` / `CD=9` / `SWAP AB ,CD` | ` 9  7 ` | ` 9  7 ` ✅ |
| **7. what the rule COSTS** *(CF-3300 only for the `fld` rows)* | | | |
| `z.fldctl` | `FIELD#1,10 AS A$(1)` | `OK` | `OK` 🟢 **control** |
| `z.fldvar` | `FIELD#1,N AS A$(1)` | **`Type mismatch`** | `OK` 🔴 ⏸ **DEFERRED** (§4) |
| `z.fldstr` | `FIELD#1,B$ AS A$(1)` *(no space anywhere)* | **`Type mismatch`** | `OK` 🔴 ⏸ **DEFERRED** (§4) |
| `z.join` | `DIM A$(3)` / `N=10` / `X=N AS A$(1)` | **`Type mismatch`** | `Syntax error` 🔴 |
| `z.joinnum` | `NAS=4` / `N=10` / `X=N AS A` | **` 4 `** | `Syntax error` 🔴 |

**29 of the 56 scored rows agreed** at `36a107e` (58 cases, 2 deferred, §4).
After D-NAMSPC the battery is **56/56**.

---

## 2. The rule, stated from the readings and from nothing else

> A variable REFERENCE's NAME may contain any run of spaces, at any position
> inside it, and any run of spaces may separate it from its type suffix. The
> reference then resolves to **exactly the variable the contiguous spelling
> names** — the same two significant characters, the same suffix type, the same
> key. This is the NAME SCAN's rule, not any statement's: it holds in an r-value
> expression, a LET target, an `IF` condition, `FOR`, `NEXT`, `DIM`, an array
> element lvalue, `READ` and `SWAP` alike.

Four clauses are readings no earlier row asked, and each decides bytes:

* 🎯 **`r.name` — IT IS UNIVERSAL, AND THAT IS THE READING THAT SIZED THE
  SLICE.** `AB=7` / `PRINT A B` reads ` 7 ` — **one** value, the variable `AB` —
  on both references, against ` 0  0 ` (two values) here. `PRINT` never touches
  `tgt_parse`. Had this come back ` 0  0 ` on the references, the fix would have
  been a second D-TGTSPC-shaped patch at a few target sites. It did not.
* 🎯 **`t.*` — THE SPACE SURVIVES THE CRUNCH IN EVERY POSITION.** Twelve rows
  read from the **stored line bytes** through `TXTTAB`, green on all three sides
  *before* the fix, so the crunch is not the subject and zerobas's tokeniser
  already agrees with both references byte for byte. 🔴 **`t.dig` is the one that
  could have moved the whole slice into `basic/interp.asm`**: a digit is copied
  verbatim only while the in-name flag `TKNAME` ($E028) is set, and had a space
  cleared it, `1 A 1=1` would store a numeric constant no parser could rejoin.
  It stores `41 20 **31**` — verbatim — on all three sides.
* 🎯 **`r.three` / `r.run` / `a.sig` — THE TWO-CHARACTER KEY IS UNCHANGED.**
  `A B C`, `AB CD` and `A B C=7` all key `(A,B)`: 3rd+ characters are consumed
  and ignored across a space exactly as without one, so a spaced name still
  **collides** with its contiguous spelling.
* 🎯 **`z.miss` — THE JOINED NAME IS A DIFFERENT VARIABLE, NOT TOLERATED JUNK.**
  `FOR A=1 TO 2` / `NEXT A B` is **NEXT without FOR** on both references. A fix
  that merely *ignored* the space and its tail would answer `OK` and pass every
  other row here.

---

## 3. 🔴 The KEYWORD constraint — and it points BOTH ways

This tree's tokeniser matches keywords at **every** position mid-identifier,
exactly like MS-BASIC (`dev-workflow.md` §"Tokeniser quirks"). Four `t.*` rows
fix what that means, and they are green on all three sides before anything is
changed:

| | contiguous | spaced |
|---|---|---|
| `SCORE` / `SC ORE` | `SC` + **`OR`** + `E` | `SC` + ` ` + **`OR`** + `E` — the token **survives** |
| `AND` / `A ND` | **`$F6`**, one token | `A`,` `,`N`,`D` — **no token at all** |
| `ABS` / `A BS` | **`$FF $86`**, one token | `A`,` `,`B`,`S` — **no token at all** |

⇒ the match is **positional**. A space blocks it at the position it occupies and
does not prevent one at the next, so a spaced name may or may not survive to the
parser — and **the name scan must not try to be cleverer than the tokeniser that
already ran.** `z.kw` pins that from the refusing side (`SC ORE=7` is
`Syntax error` on both references and here, before *and* after), and `k.and` /
`k.abs` pin it from the green side: `A ND` and `A BS` are ordinary names,
reading ` 7 ` on both references, precisely because the crunch found no keyword
in them.

---

## 4. ⏸ `z.fldvar` / `z.fldstr` — DEFERRED, and the row that says why has NO SPACE IN IT

`AS` is **not** in `basic/kwtable.inc` and is not a token: `ex_field`
(`basic/field.asm:270`) `eval`s the width and then reads the two literal
characters `'A'`,`'S'`. So a *variable* width is followed by bare letters, and a
name scan that skips spaces must swallow them — which is exactly what both
references do, and why the CF-3300 **refuses** `FIELD#1,N AS A$(1)`.

The honest price of the rule is therefore that this construct stops working in
zerobas too. But zerobas does **not** land on the reference's error, and the row
that explains it contains no space at all:

| row | program | CF-3300 | zerobas before | zerobas after |
|---|---|---|---|---|
| `z.fldstr` | `FIELD#1,B$ AS A$(1)` — **contiguous** | `Type mismatch` | `OK` | `OK` |
| `z.fldvar` | `FIELD#1,N AS A$(1)` | `Type mismatch` | `OK` | `Syntax error` |
| `z.join` | `X=N AS A$(1)` — FIELD taken out | `Type mismatch` | `Syntax error` | **`Type mismatch`** ✅ |
| `z.joinnum` | `NAS=4` / `X=N AS A` | ` 4 ` | `Syntax error` | **` 4 `** ✅ |

🎯 **THE JOIN IS EXACT, AND `z.join` / `z.joinnum` ARE THE CONTROL THAT SAYS SO.**
With FIELD out of the picture the same joined reference agrees on all three
sides: `N AS A$(1)` really is scanned as the single string array element
`NA$(1)`, and `N AS A` as the numeric `NA`.

🔴 **WHAT REMAINS IS A SHIPPED DEFECT IN `ex_field`, NOT IN THE NAME SCAN.**
`z.fldstr` gives a **string** as the field width, spelled contiguously, and
zerobas answers `OK`: `ex_field`'s `call eval` never checks what the width
evaluates *to*. The CF-3300 refuses the width **before** it ever looks for its
literal `AS`; this tree gets as far as the missing `AS` and says `Syntax error`.
Both rows are DEFERRED — measured, printed, never scored — because scoring them
would charge the name scan for FIELD's error classification and leave no row able
to separate the two ([[one-row-cannot-separate-two-rules]]). Filed in `TODO.md`
as its own residual with these four readings as its denominator.

⚠️ `z.fldvar` did move under this slice (`OK` → `Syntax error`), which is a
**strictly better** answer — the program is now refused, as on the reference —
but it is not yet the right one.

---

## 5. 🔴 Five rows were not "a Syntax error instead of a value" — they were a HANG

`r.dig`, `r.dollar`, `r.pct`, `r.bang` and `r.hash` read `<RUN SCROLLED OFF>`
before the fix. That sentinel exists because the first draft of the probe's
reader returned `<NO OUTPUT>` for them, which is the **opposite** of what was
happening: `PRINT A 1`, `PRINT AB %`, `PRINT AB !`, `PRINT AB #` and
`PRINT AB $` fill a SCREEN 0 page with ` 0 ` **forever**, because the PRINT item
loop never advances past the character after the name. Recording a runaway as a
silence would have understated the divergence by a whole category
([[readout-blind-to-its-own-subject]]).

---

## 6. Denominator

**(WHERE the space falls inside a reference: before the 2nd LETTER, before a
DIGIT, before each of the four type suffixes `% ! # $`, MORE THAN ONCE, and
between two names run together) × (the POSITION the reference stands in: r-value
expression, LET target, `IF` condition, `FOR`, `NEXT`, `DIM`, an array element
lvalue, `READ`, `SWAP` — of which only `NEXT` and `READ` reach `tgt_parse` at
all)**, plus whether the space **survives the crunch** in each of those positions,
plus what the **two-character key** does with a space in the middle, plus the
**keyword constraint** in both directions with its runtime negative control, plus
the converse row that says the joined name is a DIFFERENT variable, plus the
TRAILING-space set that is green before and must stay green, plus the one
construct the rule **takes away** (`FIELD #n,<var> AS`) with the space-free row
that isolates its cause.

**Not covered, and named rather than implied:** a TAB or any other whitespace
byte; DIRECT mode (`TODO.md`'s `dir-name` residual, whose program-mode twin
`a.dig` *is* here); a space inside a `DEF FN` name or inside a line-number list;
`RSET` and the rest of the `FIELD` family (D-TGTSPC's nine lvalue surfaces share
one parse site and already carry the `(` position); and `OPEN A$ AS #1`, measured
in passing on the CF-3300 as `OK` against `Syntax error` here — a divergence with
a different cause, unaffected by this fix, filed separately.
