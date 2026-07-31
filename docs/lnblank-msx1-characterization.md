# D-LNBLANK — what a blank inside a number does, measured on two MSX1 machines

> **ORACLE-LOCK PASS. Recorded 2026-07-31, BEFORE zerobas was run once.**
> Probe [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
> `make lnblank-characterize`. Spec: [`spec-basic-lnblank.md`](spec-basic-lnblank.md).

Machines: **`Philips_VG_8020`** and **`National_CF-3300`** (Disk BASIC).
Readout: `("stored_line", TXTTAB)` — the exact bytes of the first stored line,
link word dropped (it is an absolute address and the two machines' text bases
differ). Every row run **twice on independent boots per machine**; no row read
`UNSTABLE`. Echo guard (`make lnblank-echo`) clean on every gating payload.

## 0. The headline

**The two references agree on every one of the 54 rows — 48 gating, 6
informational — byte for byte.** So everything below is a property of MSX-BASIC,
not of one ROM. That was worth the second oracle: the whole slice was filed off a
single row from a single machine.

**And the filed item names the smallest part of it.** TODO
([`TODO.md:3251`](../TODO.md:3251)) describes a *line-number* scan that skips
blanks. The `lit` battery says the rule is not the line-number scan's at all:

```
20 A=1 0   ->  line 20 | A<EF><0F><0A>      ; the single literal 10
20 A=10    ->  line 20 | A<EF><0F><0A>      ; byte-identical
```

It is the **decimal number scanner**, and the leading line number is one of its
customers. §2 bounds how far it reaches.

## 1. R1 — blanks are transparent to a DECIMAL number scan

Everywhere a decimal number is scanned, a blank between digits is skipped and
accumulation continues.

| row | typed | stored reading |
|---|---|---|
| `num-blank1` | `2 0 REMX` | `line 20 \| <8F>X` |
| `num-blank2` | `2  0 REMX` | `line 20 \| <8F>X` — **any run** of blanks |
| `num-blank3` | `2 0 0 REMX` | `line 200 \| <8F>X` |
| `num-mid` | `20 0REMX` | `line 200 \| <8F>X` |
| `num-filed` | `20 0#0#0#0#0#` | `line 200 \| #<1F>…` — **the filed row, reproduced** |
| `lit-assign` | `20 A=1 0` | `line 20 \| A<EF><0F><0A>` — the literal 10 |
| `lit-print` | `20 PRINT 1 0` | `line 20 \| <91> <0F><0A>` |
| `lit-add` | `20 A=1 0+2 0` | `line 20 \| A<EF><0F><0A><F1><0F><14>` — 10 and 20 |
| `lit-float` | `20 A=1 . 5` | `line 20 \| A<EF><1D>A<15><00><00>` — **1.5**, across two blanks |
| `lit-exp` | `20 A=1E 2` | `line 20 \| A<EF><1D>C<10><00><00>` — **100** |
| `ref-goto` | `20 GOTO 1 0` | `line 20 \| <89> <0E><0A><00>` — **line 10** |

The float rows matter more than they look: `1 . 5` puts blanks on both sides of
the decimal point and still lands on 1.5, and `1E 2` crosses the exponent
marker. This is not "digits are joined"; the whole decimal-number scan is
blank-transparent.

### Controls that hold

`num-plain` (`20 REMX`), `num-nospace` (`20REMX`), `num-lead` (` 20 REMX`),
`num-stop` (`2 X=1` → `line 2 | X<EF><12>`, a letter still stops the scan) and
`lit-ctl` (`20 A=10`) all read exactly as both rules predict. They are pinned
*because* they agree.

## 2. R2 — where blank-transparency STOPS

The rule is not "the crunch ignores blanks". Four measured boundaries:

| row | typed | stored reading | boundary |
|---|---|---|---|
| `lit-hex` | `20 A=&H1 F` | `line 20 \| A<EF><0C><01><00> F` | **a HEX literal does NOT skip**: `&H1` = 1, then ` F` left as source |
| `lit-str` | `20 A$="1 0"` | `line 20 \| A$<EF>"1 0"` | inside a **string literal** the blank survives |
| `lit-rem` | `20 REM1 0` | `line 20 \| <8F>1 0` | a **REM tail** is verbatim |
| `lit-varname` | `20 A B=1` | `line 20 \| A B<EF><12>` | a **variable name** keeps its blank in the crunched bytes |

⚠️ `lit-hex` is the sharpest of these. Decimal skips, hex does not — so a fix
written as "make the crunch's digit fetch blank-transparent" would be **wrong**,
and only a row that asked about hex could have said so.

## 3. R3 — where the BODY starts, and the discriminator is the VALUE

The leading line number consumes **its digit characters plus exactly one
following blank — unless the line number's value is zero, in which case it
consumes no blank at all.**

| row | typed | stored reading | digits | value | blanks eaten |
|---|---|---|---|---|---|
| `body-d1` | `1 REMX` | `line 1 \| <8F>X` | 1 | 1 | 1 |
| `body-d1b2` | `1  REMX` | `line 1 \| ␣<8F>X` | 1 | 1 | 1 |
| `body-d2` | `12 REMX` | `line 12 \| <8F>X` | 2 | 12 | 1 |
| `body-d3` | `123 REMX` | `line 123 \| <8F>X` | 3 | 123 | 1 |
| `body-d4` | `1234 REMX` | `line 1234 \| <8F>X` | 4 | 1234 | 1 |
| `num-body1` | `20␣␣REMX` | `line 20 \| ␣<8F>X` | 2 | 20 | 1 of 2 |
| `num-body2` | `20␣␣␣REMX` | `line 20 \| ␣␣<8F>X` | 2 | 20 | 1 of 3 |
| `body-z1` | `0 REMX` | `line 0 \| ␣<8F>X` | 1 | **0** | **0** |
| `body-z2` | `0␣␣REMX` | `line 0 \| ␣␣<8F>X` | 1 | **0** | **0** |
| `body-z0` | `00 REMX` | `line 0 \| ␣<8F>X` | 2 | **0** | **0** |
| `body-zl` | `01 REMX` | `line 1 \| <8F>X` | 2 | 1 | 1 |
| `body-x1` | `1 X=1` | `line 1 \| X<EF><12>` | 1 | 1 | 1 |
| `body-zx` | `0 X=1` | `line 0 \| ␣X<EF><12>` | 1 | **0** | **0** |

⚠️ **`body-z0` vs `body-zl` is the pair that pins it, and neither row does it
alone.** `00 REMX` and `01 REMX` both have two digits and both start with the
digit `0`; they differ only in the *value*. `00` eats no blank, `01` eats one.
So the discriminator is the **value being zero**, not a leading zero and not the
digit count.

The first run had only `20 REMX` (0 blanks kept), `0 REMX` (1 kept) and
`2 X=1` (0 kept) — one digit and one blank giving two different answers — and no
single rule fits those three. The rule came from the battery, not from reasoning
about the three rows already in hand.

This is not cosmetic: the body offset is part of the stored bytes, and the filed
row diverges in the body as well as in the line number.

## 4. R4 — the ceiling still bites, even reached through blanks

| row | typed | stored reading |
|---|---|---|
| `num-max` | `6 5 5 2 9 REMX` | `line 65529 \| <8F>X` — accepted |
| `num-over` | `6 5 5 3 0 REMX` | **`REFUSED (empty program)`** |
| `num-huge` | `9 9 9 9 9 REMX` | **`REFUSED (empty program)`** |

65529 is the documented maximum and both machines take it; 65530 and 99999 are
refused outright, nothing stored. The accumulator walks to the ceiling *through*
blanks and the range check still fires on the far side.

## 5. R5 — in a line-number REFERENCE, the inner blank is DROPPED

`branch_lineno`'s territory. The crunched bytes make both halves visible at once:

| row | typed | stored reading |
|---|---|---|
| `ref-ctl` | `20 GOTO 10` | `line 20 \| <89> <0E><0A><00>` |
| `ref-goto` | `20 GOTO 1 0` | `line 20 \| <89> <0E><0A><00>` — **byte-identical** |
| `ref-sp` | `20 GOTO   10` | `line 20 \| <89>␣␣␣<0E><0A><00>` |
| `ref-gosub` | `20 GOSUB 1 0` | `line 20 \| <8D> <0E><0A><00>` |
| `ref-then` | `20 IF A THEN 1 0` | `line 20 \| <8B> A <DA> <0E><0A><00>` |
| `ref-restore` | `20 RESTORE 1 0` | `line 20 \| <8C> <0E><0A><00>` |
| `ref-run` | `20 RUN 1 0` | `line 20 \| <8A> <0E><0A><00>` |
| `ref-resume` | `20 RESUME 1 0` | `line 20 \| <A7> <0E><0A><00>` |
| `ref-onlist` | `20 ON A GOTO 1 0,2 0` | `line 20 \| <95> A <89> <0E><0A><00>,<0E><14><00>` |
| `ref-oncomma` | `20 ON A GOTO 1 0 , 2 0` | `line 20 \| <95> A <89> <0E><0A><00> , <0E><14><00>` |

Blanks **before** the number are copied verbatim (`ref-sp`: three of them
survive between `$89` and `$0E`); a blank **inside** the number is consumed and
leaves no byte. Blanks around a list comma are preserved. Both list slots
convert.

## 6. R6 — the reference emits `$0E` for FIVE more verbs than zerobas does

Measured because it is part of the denominator of the reference path; **filed,
not fixed here** (spec §7 — it is a missing feature, not this defect).

| row | typed | stored reading | token |
|---|---|---|---|
| `ref-list` | `20 LIST 1 0` | `line 20 \| <93> <0E><0A><00>` | `LIST` = `$93` |
| `ref-delete` | `20 DELETE 1 0` | `line 20 \| <A8> <0E><0A><00>` | `DELETE` = `$A8` |
| `ref-auto` | `20 AUTO 1 0` | `line 20 \| <A9> <0E><0A><00>` | `AUTO` = `$A9` |
| `ref-renum` | `20 RENUM 1 0` | `line 20 \| <AA> <0E><0A><00>` | `RENUM` = `$AA` |
| `ref-else` | `20 IF A THEN 1 0 ELSE 2 0` | `line 20 \| <8B> A <DA> <0E><0A><00> :<A1> <0E><14><00>` | `ELSE` = `:`+`$A1` |

zerobas's `bl_yes` ([`basic/tokenise.inc:445`](../basic/tokenise.inc:445)) tests
only `GOTO`/`GOSUB`/`THEN`/`RESTORE`/`RUN`/`RESUME`, so all five crunch as
ordinary numeric literals today.

## 7. R7 — a blank-split number with no body DELETES that line

| row | typed | stored reading |
|---|---|---|
| `num-only` | `20 REMY` then `2 0` | **`REFUSED (empty program)`** |

`2 0` is read as line **20** and, having no body, deletes it — the program ends
up empty. Under a terminate-at-blank rule it would have deleted the
non-existent line 2 and left line 20 standing. The two rules differ here in the
**number of stored lines**, which is why this row is the slice's falsification
witness (spec §6).

## 8. R8 — TAB behaves like a blank (informational)

| row | typed | stored reading |
|---|---|---|
| `num-tab` | `2<TAB>0 REMX` | `line 20 \| <8F>X` |

⚠️ **This row measures the editor and the scan together, and cannot separate
them.** The echo guard reports that neither reference echoes a literal TAB — the
MSX line editor transforms it inside the input buffer — so "TAB is transparent to
the scan" is *not* what this shows. What it shows is that typing a TAB there
produces line 20 on both machines. Kept informational for that reason.

## 9. Apparatus notes worth keeping

* ⚠️ **The echo guard the other probes use would have been blind here.**
  [`diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py)
  squeezes runs of blanks so a wrapped echo still matches. This subject **is**
  the blank: squeezed, `2 0 REMX` and `20 REMX` are the same string, so a
  dropped space — the exact mangle the guard exists to catch — would have read
  as a clean echo.
* ⚠️ **And not squeezing exposed a left margin that the squeeze had been hiding
  rather than tolerating.** The first guard cut compared `row.rstrip()` against
  the typed text and reported `MANGLED` for **every row on both references**,
  while the memory pass was reading those same rows perfectly. The screen puts a
  two-column indent in front of everything (`'  Ok'`, `'  20 REMX'`).
  `lstrip()` is not the fix either — `num-lead` types ` 20 REMX`, whose leading
  blank *is* the measurement. The margin is now **measured per capture** (the
  narrowest indent on the screen, which the prompt row always supplies) and
  exactly that many columns are removed.
* **`repeat=2` on every reference pass.** A dropped keystroke changes the stored
  bytes and looks exactly like a semantic divergence. In the differential
  direction that is a loud false FAIL; in the oracle-lock direction it is a
  false PASS forever. The two directions do not deserve the same guard.
* The CF-3300's boot **date prompt** is answered by a bare CR emitted as part of
  `reset`; at the BASIC prompt every later one is a no-op. Its 4.5 s cadence is
  D-LOF's measured figure, not a guess.
* Because the readout is **memory**, the CF-3300's SCREEN 1 Disk BASIC boot cost
  nothing — no geometry handling, no name-table width switch. That is the only
  reason a second oracle was affordable at all.

## 10. Addendum — two rows the first battery could not answer

Added after §1–§9 were locked, oracle-locked in their turn on both references
(`repeat=2`) **before** being compared with zerobas.

### 10.1 The range question, asked without a blank in the way

⚠️ **`num-over`/`num-huge` cannot answer the range question on a machine that
stops at the blank** — that was a hole in this battery's own denominator.
zerobas reads `6 5 5 3 0 REMX` as line **6**, so the row diverges for the *blank*
reason and says nothing whatever about what zerobas does with 65530.

| row | typed | both references |
|---|---|---|
| `num-max0` | `65529 REMX` | `line 65529 \| <8F>X` — accepted |
| `num-over0` | `65530 REMX` | **`REFUSED (empty program)`** |
| `num-huge0` | `99999 REMX` | **`REFUSED (empty program)`** |

The refusal is independent of blanks. `--say` gives its **class**, on both
machines: **`Syntax error`**. `num-max0` prints nothing.

### 10.2 The value-zero rule, reached THROUGH a blank

`00 REMX` vs `01 REMX` (§3) says the discriminator is the value and not the
leading digit — but both reach their value with the digits *adjacent*. One way
was left for the rule to be about the digit run instead:

| row | typed | both references |
|---|---|---|
| `body-z00` | `0 0 REMX` | `line 0 \| ␣<8F>X` — value 0 through a blank, **still no separator eaten** |

The rule is about the **value**. Confirmed.

## 11. What zerobas does — 18/48 gating rows agree

`make lnblank-acceptance` at `5eaf1d7`. Five distinct divergence groups.

### A. The leading line-number scan stops at the blank *(the filed defect)*

| row | typed | reference | zerobas |
|---|---|---|---|
| `num-blank1` | `2 0 REMX` | `line 20 \| <8F>X` | `line 2 \| <11> <8F>X` |
| `num-blank3` | `2 0 0 REMX` | `line 200 \| <8F>X` | `line 2 \| <11> <11> <8F>X` |
| `num-mid` | `20 0REMX` | `line 200 \| <8F>X` | `line 20 \| <11><8F>X` |
| `num-filed` | `20 0#0#0#0#0#` | `line 200 \| #<1F>…` | `line 20 \| <1F>…` |
| `num-max` | `6 5 5 2 9 REMX` | `line 65529` | `line 6 \| <16> <16> <13> <1A> <8F>X` |
| `num-only` | `20 REMY` / `2 0` | `REFUSED (empty program)` | `line 2 \| <11>` — **line 20 still there** |

### B. The line-number REFERENCE scan stops too, and the list breaks after it

| row | typed | reference | zerobas |
|---|---|---|---|
| `ref-goto` | `20 GOTO 1 0` | `<89> <0E><0A><00>` | `<89> <0E><01><00> <11>` |
| `ref-onlist` | `20 ON A GOTO 1 0,2 0` | `<95> A <89> <0E><0A><00>,<0E><14><00>` | `<95> A <89> <0E><01><00> <11>,<13> <11>` |
| `ref-oncomma` | `20 ON A GOTO 1 0 , 2 0` | `… <0E><0A><00> , <0E><14><00>` | `… <0E><01><00> <11> , <13> <11>` |

⚠️ **`ref-oncomma` carries a second defect the blank rule does not explain.**
The reference converts the *second* list slot to `$0E` as well; zerobas emits an
ordinary literal for it. `bl_done` tests for `,` at the very next character, so a
**blank before the comma ends the list** — every later target then crunches as a
plain number. This is the same class of bug `bl_num`'s own comment already
records for an *empty* slot ([`basic/tokenise.inc:459`](../basic/tokenise.inc:459)),
one character to the left of where that one was fixed.

### C. The body offset — zerobas eats every blank, the reference eats one

`dispatch_line` calls `skip_spaces`, which consumes the whole run.

| row | typed | reference | zerobas |
|---|---|---|---|
| `num-body1` | `20␣␣REMX` | `line 20 \| ␣<8F>X` | `line 20 \| <8F>X` |
| `num-body2` | `20␣␣␣REMX` | `line 20 \| ␣␣<8F>X` | `line 20 \| <8F>X` |
| `body-d1b2` | `1␣␣REMX` | `line 1 \| ␣<8F>X` | `line 1 \| <8F>X` |
| `num-zero` | `0 REMX` | `line 0 \| ␣<8F>X` | `line 0 \| <8F>X` |
| `body-z0` | `00 REMX` | `line 0 \| ␣<8F>X` | `line 0 \| <8F>X` |
| `body-zx` | `0 X=1` | `line 0 \| ␣X<EF><12>` | `line 0 \| X<EF><12>` |

⚠️ **`num-zero` was declared a two-sided CONTROL and it is red.** That
classification was right about the blank *rule* — T and S both predict line 0 —
and wrong as a claim about the row, because the row also exercises the body
offset, which no rule in the spec covered when the label was assigned. A control
is a claim about *which* variables a row holds still, and this one held fewer
than its label said.

### D. 🔴 The general decimal-literal scanner — NOT what the TODO filed

| row | typed | reference | zerobas |
|---|---|---|---|
| `lit-assign` | `20 A=1 0` | `A<EF><0F><0A>` (literal 10) | `A<EF><12> <11>` (1, blank, 0) |
| `lit-print` | `20 PRINT 1 0` | `<91> <0F><0A>` | `<91> <12> <11>` |
| `lit-add` | `20 A=1 0+2 0` | `A<EF><0F><0A><F1><0F><14>` | 1,blank,0,+,2,blank,0 |
| `lit-float` | `20 A=1 . 5` | `A<EF><1D>A<15><00><00>` (1.5) | — |
| `lit-exp` | `20 A=1E 2` | `A<EF><1D>C<10><00><00>` (100) | — |

**Filed as its own slice, not fixed here.** The site is `tk_float`
([`basic/tokenise.inc:57`](../basic/tokenise.inc:57) → the sub-ROM float pack),
a different ROM from the two scanners the TODO names, and the change would
affect every numeric literal in every program — it deserves its own
falsification. The controls that bound it (`lit-str`, `lit-rem`, `lit-hex`) are
already measured above and go with the item.

### E. 🔴 The line-number ceiling is unguarded — a SILENT WRAP

| row | typed | reference | zerobas |
|---|---|---|---|
| `num-max0` | `65529 REMX` | `line 65529` | `line 65529` — agrees |
| `num-over0` | `65530 REMX` | `REFUSED`, `Syntax error` | **`line 65530`** stored |
| `num-huge0` | `99999 REMX` | `REFUSED`, `Syntax error` | **`line 34463`** stored |

`parse_lineno`'s header says in as many words that it "wraps past 65535" and that
line numbers above 65529 are "not guarded here"
([`basic/program.asm:198`](../basic/program.asm:198)). 99999 − 65536 = **34463**:
typing `99999 REM` on zerobas today silently creates a line with a *different
number than the one typed*, and nothing reports it.

⚠️ This is live **now**, independent of blanks — but the blank fix widens its
reach, because `9 9 9 9 9 REM` goes from a visibly-wrong line 9 to a silently
wrapped 34463. Spec §7 had scoped the range question out; it is pulled in for
that reason. Shipping the blank fix without it would repeat D-LINEMAX exactly,
where fixing one limit turned a previously-safe unbounded buffer into a live
defect.

### F. Five `$0E` verbs zerobas has no arm for (informational)

`LIST`/`DELETE`/`AUTO`/`RENUM`/`ELSE` — §6. And it is worse than a missing
`$0E` arm: zerobas has no token for three of these verbs at all —
`20 DELETE 1 0` crunches to `DE<88>E …` and `20 RENUM 1 0` stores `RENUM`
verbatim. Filed; a much larger gap than this slice.
