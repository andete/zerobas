# A BLANK INSIDE A VARIABLE NAME — MSX1 characterization

*Measured 2026-07-31/08-01 on **two** reference machines that agree on **all 25 rows**:
`Philips_VG_8020` (MSX1, cassette BASIC) and `National_CF-3300` (MSX1, Disk
BASIC). Probe: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
`nam` battery. Spec: [`docs/spec-basic-nameblank.md`](spec-basic-nameblank.md).*

Readout is `("stored_line", TXTTAB)` — the stored line's **own bytes**, gloss
`printable ASCII verbatim, everything else as <XX>`. The 2-byte link is dropped
(an absolute address; the CF-3300's text base is not the VG-8020's).

**Every payload passed the echo guard on both references before it was read, and
every reference pass ran at `--repeat 2` on independent boots.** No row came back
`UNSTABLE`. The `--repeat 2` is not ceremony: in the oracle-lock direction a
dropped keystroke is a false PASS *forever*
([[lineno-blank-echo-guard]], [`docs/lnblank-msx1-characterization.md`](lnblank-msx1-characterization.md)).

---

## 0. Why this battery exists, and why its filed title was wrong

`TODO.md` filed this as *"`&B` is not a radix on MSX1 — and zerobas
half-crunches it anyway"*, from D-DECBLANK's informational `dec-bin` row:

```
20 A=&B1 1   ref -> A<EF>&B1 1     VERBATIM
             zb  -> A<EF>&B1 <12>  the trailing 1 crunched to an integer token
```

🔴 **The `&` has nothing to do with it, and one row proves it positively rather
than by argument:**

```
nam-amp1   20 A=&1    ref -> A<EF>&<12>    zb -> A<EF>&<12>    AGREE
```

A digit *directly* behind the `&` is crunched **by both references**. The `&` is
inert — `tk_hex` ([`basic/tokenise.inc:294`](../basic/tokenise.inc:294)) copies it
verbatim for `&B`/bare `&`, which is an oracle-pinned own-design descope, and the
references do the same thing. What the filed row actually carries is the text
`B1 1`, in which **`B1` is an ordinary variable name**.

⚠️ **And `dec-oct` had been arguing the same thing since D-DECBLANK without
anyone reading it that way.** `20 A=&O1 7` reads `A<EF><0B><01><00> <18>` on both
references — an octal *token* is not a name, no name state survives it, and the
reference crunches the `7` exactly as zerobas does. Same shape as `dec-bin`,
opposite reading, and the only difference between the two rows is **whether a
name preceded the blank**.

---

## 1. The rule — rule **P**

> **A blank is COPIED but changes no tokeniser state.** The "previous character
> was part of a name" condition survives a blank run intact, so a digit behind
> the blank still **continues the name** instead of starting a numeric constant.

zerobas today is **rule K**: `tk_loop` reloads `TKNAME` into `B` and then zeroes
it at the top of *every* character; a blank reaches `tk_copy`, which never sets it
again, so the in-a-name flag dies at every space.

### 1.1 The rows that separate K from P

| label | typed | both references | zerobas | |
|---|---|---|---|---|
| `nam-ctl` ^ | `20 A=B11` | `A<EF>B11` | *agrees* | control: no blank |
| `nam-eqnum` ^ | `20 A= 1` | `A<EF> <12>` | *agrees* | control: a blank alone makes **no** name state, and **the blank is kept** |
| `nam-digblk` | `20 A=B1 1` | `A<EF>B1 1` | `A<EF>B1 <12>` | ★ the filed row, **with no `&`** |
| `nam-letblk` | `20 A=B 1` | `A<EF>B 1` | `A<EF>B <12>` | ★ a **letter** sets the state too |
| `nam-two` | `20 A=AB 1` | `A<EF>AB 1` | `A<EF>AB <12>` | not a one-char-name rule |
| `nam-run` | `20 A=B1  1` | `A<EF>B1  1` | `A<EF>B1  <12>` | any **run** of blanks |
| `nam-more` | `20 A=B 1 0` | `A<EF>B 1 0` | `A<EF>B <0F><0A>` | 🔴 see §2 |
| `nam-op` | `20 A=B 1+2` | `A<EF>B 1<F1><13>` | `A<EF>B <12><F1><13>` | an operator still **breaks** the name |
| `nam-lval` | `20 B1 1=5` | `B1 1<EF><16>` | `B1 <12><EF><16>` | LVALUE position, not just after `=` |
| `nam-print` | `20 PRINT B1 1` | `<91> B1 1` | `<91> B1 <12>` | after a **keyword token** |
| `nam-ampz` | `20 A=&Z1 1` | `A<EF>&Z1 1` | `A<EF>&Z1 <12>` | an unknown radix letter — `Z1` is just a name |
| `nam-ampl` | `20 A=&b1 1` | `A<EF>&B1 1` | `A<EF>&B1 <12>` | lowercase, **upcased** by both |

`^` = two-sided control (K and P predict the same bytes).

**Ten gating rows diverge, and none of them needs an `&`** — plus `dec-bin`, the
filed row itself, which is the eleventh and the only one that has an `&` at all.

### 1.2 The rows that bound it — where the name state still dies

These agree with zerobas **today** and pin the cells the fix must not move.

| label | typed | both references | zerobas | what it pins |
|---|---|---|---|---|
| `nam-sfx` | `20 A=B$ 1` | `A<EF>B$ <12>` | *agrees* | `$` ends the identifier |
| `nam-sfx0` | `20 A=B$1` | `A<EF>B$<12>` | *agrees* | …blank or not, so `nam-sfx` is about `$` |
| `nam-sfxp` | `20 A=B% 1` | `A<EF>B% <12>` | *agrees* | and `%` too — not a one-suffix rule |
| `nam-kw` | `20 A=B AND 1` | `A<EF>B <F6> <12>` | *agrees* | a **keyword** kills the state; both blanks kept |
| `nam-amph` | `20 A=B &H1` | `A<EF>B <0C><01><00>` | *agrees* | the `&H` radix scan **ignores** the state |
| `nam-amp0` ^ | `20 A=&B11` | `A<EF>&B11` | *agrees* | the filed shape with no blank |
| `nam-amp1` | `20 A=&1` | `A<EF>&<12>` | *agrees* | ★ **the `&` is inert** |
| `nam-ampe` | `20 A=&` | `A<EF>&` | *agrees* | a bare `&` at EOL |
| `lit-varname` | `20 A B=1` | `A B<EF><12>` | *agrees* | the blank inside a name is **kept**, and `=` still breaks it |
| `lit-assign` | `20 A=1 0` | *(single literal 10)* | *agrees* | D-DECBLANK: **must not move** |
| `nam-paren` | `20 A=B(1)` | `A<EF>B(<12>)` | *agrees* | 🔴 plain punctuation ends the name — added because a **knife** found the hole (§6) |
| `nam-parenblk` | `20 A=B( 1)` | `A<EF>B( <12>)` | *agrees* | `(` clears, and the blank preserves the **cleared** state |

⚠️ `nam-amph`, `nam-kw` and `nam-dot` are the three constructs entered **without
consulting** the in-a-name state. Two of them agree; the third is §3.

---

## 2. 🔴 `nam-more` — the defect is bigger than one byte

```
20 A=B 1 0   ref -> A<EF>B 1 0        the identifier B10, stored VERBATIM
             zb  -> A<EF>B <0F><0A>   B, a blank, and THE SINGLE LITERAL 10
```

zerobas does not merely crunch *a digit*. Once the name state is lost it hands
the rest of the run to the **decimal literal scanner**, which then correctly
applies **D-DECBLANK's** own blank-transparency rule and **joins `1 0` into
10** ([`docs/decblank-msx1-characterization.md`](decblank-msx1-characterization.md)).

Two rules compound: the first loses the name, the second swallows a blank the
reference keeps. `nam-more` is the only row in the battery that shows it — every
other divergent row has a single digit behind the blank, where the two rules are
indistinguishable. A slice that sampled `B1 1` alone would have described this
defect as *"one byte becomes a token"* and been wrong about its own size.

---

## 3. ⚠️ `.` IS AN IDENTIFIER CHARACTER — a SEPARATE defect, filed not fixed

| label | typed | both references | zerobas |
|---|---|---|---|
| `nam-dot` | `20 A=B .5` | `A<EF>B .5` | `A<EF>B <1D>@P<00><00>` |
| `nam-dot0` | `20 A=B.5` | `A<EF>B.5` | `A<EF>B<1D>@P<00><00>` |

🔴 **`nam-dot0` carries no blank at all and diverges anyway.** MS-BASIC allows a
period *inside* an identifier (`MY.VAR`), so `B.5` is the variable `B.5` and
`B .5` is the same variable reached across a blank. zerobas' `tk_loop` dispatch
([`basic/tokenise.inc:83`](../basic/tokenise.inc:83)) looks exactly one character
past a `.` and hands it to `tk_float` on a digit — for a reason that has nothing
to do with the name state, and that no `TKNAME` change can reach.

Reading `nam-dot` through the blank rule alone would have said *"a blank stops a
literal from starting"* — a rule this project would then have implemented. Its
control says otherwise. **This is the D-MFDOM trap** (closing an item on a
measurement that belongs to a different defect), and the pair is what avoided it.

⚠️ **And it is not a tokeniser-only fix**, which is why it is a slice of its own:
the crunched line would store `B.5` as name bytes, so the RUN-time variable-name
scan ([`basic/vars.asm`](../basic/vars.asm)) has to accept `.` as well, or the
executor would look up a different variable than the one the tokeniser stored.

> 🔴 **REFUTED BY MEASUREMENT — D-NAMDOT, 2026-08-01**
> ([`docs/namedot-msx1-characterization.md`](namedot-msx1-characterization.md) §4).
> MSX1 stores name bytes it then **refuses to resolve**: `B.5=7` and `A=B.5` are
> `Syntax error` (ERR=2) on both references against a `B5=7` control at ERR=0.
> The tokeniser's identifier charset and the executor's are different charsets,
> and making `vars.asm` accept `.` (run as knife K4) turned those rows ERR 2 → 0
> — the prescribed fix would have shipped a live divergence. The landed fix is
> tokeniser-only, sub-ROM only, and both main ROMs stayed byte-identical.
> Kept in place: a prediction a measurement overturned is worth being able to
> re-read.

Both rows are pinned as `KNOWN_DIVERGE` entries with their exact bytes and filed
in `TODO.md`. `lit-assign`'s `20 A=.5` and D-DECBLANK's `dec-dotlead` (`20 A=. 5`)
remain **green** — a `.` at the *start* of an expression does lead a literal on
every side, so the defect is confined to a `.` behind a name.

---

## 4. Direct mode — the stored bytes do not say what the line MEANS

`--say`, screen readout, `--repeat 2`, both references locked before zerobas ran:

| label | typed | both references | zerobas |
|---|---|---|---|
| `dir-name` | `B1 1=7` then `PRINT"[";B11;"]"` | ` 7 ` | ` 0 ` |
| `dir-print` | `PRINT"[";1 0;"]"` | ` 10 ` | *agrees* |

The byte gloss shows `B1 1` verbatim; `dir-name` shows the reference *resolves*
it as the single identifier `B11` — the assignment made through the blank is
readable through the joined name. That is the claim the gloss cannot make on its
own. zerobas reads `0`: its assignment went somewhere else entirely.

### 4.1 ⚠️ Apparatus — a say row without brackets cannot have a reading

🔴 **`dir-print` had been unable to produce a reading since the day it was
written, and it would have reported `agrees`.** Every `SAY_ONLY` row is read by
`result_span_after_echo`, which returns the text between the last `[` and its `]`
([`probes/lib/omsx_repl.py:1212`](../probes/lib/omsx_repl.py:1212)). Its payload was
a bare `PRINT 1 0`, which prints no brackets — so the reading is `<none>` on
*every* side, and three sides that all failed compare EQUAL.

Found here only because `dir-name` was written in the same style and came back
`<none>` on both references, where the expected answer was obvious enough to be
disbelieved. Same shape as [[chancost-noread-guard]]: **a sentinel that also
means "no reading" is not a measurement.** The row escaped notice because
`lnblank-acceptance` filters `--say` rows out entirely — it was dormant, not
green. Both payloads now print bracketed and both are locked above; `dir-print`
still asks its original question (under rule K it would print two numbers
` 1  0`, under S the single ` 10`).

---

## 5. What was NOT measured

* Only `$20` is measured as "a blank". A TAB inside a line is the line editor's
  business (`num-tab`, informational since D-LNBLANK) and no payload here can
  deliver one through the keyboard.
* A trailing blank at end of line remains **not measurable through the keyboard**
  (`dec-eol`/`dec-eolctl`, informational *by construction*: `echo_missing()`
  `rstrip`s every screen row, so the guard is structurally blind to it).
* The other two type suffixes `!` and `#` were not asked; `$` and `%` agree, and
  the fix does not touch the suffix path at all.

---

## 6. 🔴 The battery's own blind spot, found by a knife

Every row written in rounds 1–2 reaches `tk_copy` through a **blank**, an
**operator** or a **type suffix**. Not one put *ordinary* punctuation between a
name and a digit — and `tk_copy` is the fallthrough target of the `is_letter`
test, the busiest exit in the whole loop.

Knife **K2** found it the hard way: this slice's first cut parked `tk_blank`
immediately before `tk_copy`, so **every** punctuation character fell into it and
stored a register `match_kw` had already clobbered. The flawed build read
**29/31 green** on whatever value happened to be there — clean *by luck*.

```
nam-sfx0   20 A=B$1   ref -> A<EF>B$<12>   zb (flawed cut, under K2) -> A<EF>B$1
```

A row containing **no blank at all** went red under a knife that only touches
blank handling. `nam-paren` / `nam-parenblk` exist because of that, and were
oracle-locked on both references before zerobas was run on them. Detail:
[`docs/spec-basic-nameblank.md`](spec-basic-nameblank.md) §5.1.
