# D-NAMBLANK — a blank does not break a variable name

*Status: **LANDED 2026-08-01 — 12 B, all sub-ROM, falsified on five knives.**
Both main ROMs stayed **byte-identical** to the pre-slice tree
(`1d270536…`, `90403dbb…`); sub page-0 free 4026 → 4014 B.*

🔴 **A knife found a live defect in this slice's own first cut** — see §5, K2.

Filed in `TODO.md` as *"`&B` is not a radix on MSX1 — and zerobas half-crunches
it anyway"*, found 2026-07-31 as [D-DECBLANK](spec-basic-decblank.md)'s
denominator (`dec-bin`, informational).

Measurement: [`docs/nameblank-msx1-characterization.md`](nameblank-msx1-characterization.md)
— 23 rows, both references, `--repeat 2`, every payload past the echo guard first.
Gate: `make lnblank-acceptance`, new `nam` battery.

---

## 0. 🔴 The filed title is the wrong subject, and one row says so positively

```
nam-amp1   20 A=&1     ref -> A<EF>&<12>    zb -> A<EF>&<12>    AGREE
```

A digit directly behind the `&` is **crunched by both references**. `&` is inert
on every side — `tk_hex` copies it verbatim for `&B`/bare `&`, an oracle-pinned
own-design descope, and the references do the same. The filed row's real content
is the text `B1 1`, where `B1` is an ordinary **variable name**:

```
nam-digblk 20 A=B1 1   ref -> A<EF>B1 1     zb -> A<EF>B1 <12>   NO `&` ANYWHERE
nam-letblk 20 A=B 1    ref -> A<EF>B 1      zb -> A<EF>B <12>
nam-lval   20 B1 1=5   ref -> B1 1<EF><16>  zb -> B1 <12><EF><16>
nam-print  20 PRINT B1 1  ref -> <91> B1 1  zb -> <91> B1 <12>
```

**Ten** gating rows in the `nam` battery diverge (plus `dec-bin`, the filed row
itself) and **none of them needs an `&`**. The item is a general tokeniser rule,
which changes both the site and the size of the fix.

⚠️ **`dec-oct` had been saying so since D-DECBLANK.** `20 A=&O1 7` reads
`A<EF><0B><01><00> <18>` on both references — an octal *token* is not a name, so
nothing survives it and the reference crunches the `7` exactly as zerobas does.
Same shape as `dec-bin`, opposite reading; the only difference is whether a
**name** preceded the blank.

---

## 1. The rule

> **R-N1 — a blank is COPIED but changes no tokeniser state.** The "previous
> character was part of a name" condition survives a run of blanks intact, so a
> digit behind the blank **continues the name** instead of starting a numeric
> constant. `B1 1` is the single identifier `B11`.

Pinned by `nam-digblk`, `nam-letblk`, `nam-two`, `nam-run`, `nam-more`, `nam-op`,
`nam-lval`, `nam-print`, `nam-ampz`, `nam-ampl` — and, semantically, by
`dir-name` (`B1 1=7` is readable back as `B11`, ` 7 ` on both references).

> **R-N2 — a LETTER sets the state, not just a digit.** `nam-letblk` (`B 1`,
> where the name carries no digit yet) diverges exactly like `nam-digblk`.

> **R-N3 — everything that broke a name still breaks it.** A type suffix (`$`,
> `%`), an operator, and a keyword all end the identifier, blank or no blank —
> `nam-sfx`/`nam-sfx0`/`nam-sfxp`, `nam-op`, `nam-kw`, and `lit-varname`'s `=`.
> These agree with zerobas **today** and are the cells the fix must not move.

> **R-N4 — constructs that never consulted the state still do not.** `&H` runs
> its radix scan across a preserved name state (`nam-amph` →
> `A<EF>B <0C><01><00>`), and a keyword still tokenises (`nam-kw` →
> `A<EF>B <F6> <12>`).

⚠️ Only `$20` is measured as "a blank". A TAB is the line editor's business
(`num-tab`, informational) and cannot be delivered through the keyboard.

---

## 2. 🔴 The defect is bigger than one byte — `nam-more`

```
20 A=B 1 0   ref -> A<EF>B 1 0        the identifier B10, VERBATIM
             zb  -> A<EF>B <0F><0A>   B, a blank, and THE SINGLE LITERAL 10
```

zerobas does not merely crunch *a digit*. Having lost the name state it hands the
run to the **decimal literal scanner**, which then correctly applies D-DECBLANK's
blank-transparency and **joins `1 0` into 10**. Two rules compound.

Every other divergent row has a single digit behind the blank, where the two are
indistinguishable — so a slice that sampled `B1 1` alone would have described its
own defect as *"one byte becomes a token"* and been wrong about its size. This is
the row that must appear in the commit message.

---

## 3. ⚠️ OUT OF SCOPE, MEASURED AND FILED: `.` is an identifier character

| label | typed | both references | zerobas |
|---|---|---|---|
| `nam-dot` | `20 A=B .5` | `A<EF>B .5` | `A<EF>B <1D>@P<00><00>` |
| `nam-dot0` | `20 A=B.5` | `A<EF>B.5` | `A<EF>B<1D>@P<00><00>` |

🔴 **`nam-dot0` carries no blank at all and diverges anyway**, so this is a
different defect: MS-BASIC allows a period inside an identifier (`MY.VAR`).
Reading `nam-dot` through the blank rule alone would have produced the rule *"a
blank stops a literal from starting"* — which this project would then have
implemented. **The D-MFDOM trap**, avoided only by the control.

It is not a tokeniser-only fix either: the crunched line would store `B.5` as
name bytes, so the RUN-time variable-name scan
([`basic/vars.asm`](../basic/vars.asm)) must accept `.` too, or the executor looks
up a different variable than the tokeniser stored. **Own slice.**

Both rows go into `KNOWN_DIVERGE` with their exact bytes plus a filed `TODO.md`
item — the allowlist stops being empty, and that is a measurement, not a
suppression: fix the charset and the entries stop matching and must be retired.

⚠️ **The fix below must leave these two rows reading EXACTLY what they read
today.** `tk_loop`'s `.` dispatch does not consult `TKNAME`, so it should — but
that is a prediction, and the allowlist is what tests it.

---

## 4. The fix

### 4.1 The site — sub-ROM only

`tk_loop` in [`basic/tokenise.inc:38`](../basic/tokenise.inc:38). That file is
`include`d by [`sub/sub.asm:209`](../sub/sub.asm:209) **and nothing else**, so
this slice cannot touch the main ROM. Sub page 0 has ~4026 B free.

`TKNAME` ([`basic/sysvars.inc:700`](../basic/sysvars.inc:700)) has no reader
outside `tokenise.inc` — verified by grep — so the blast radius is this one file.

### 4.2 The change — as LANDED

⚠️ **`tk_blank` sits past `tk_copy_up`, not next to `tk_copy`, and that placement
is load-bearing** — the first cut got it wrong and §5 K2 is what caught it.

`tk_loop` loads `TKNAME` into `B` and then zeroes it at the top of every
character; a blank reaches `tk_copy`, which never sets it again. Intercept the
blank **before** anything else and put the flag back:

```asm
                ld      a,(hl)
                or      a
                jp      z,tk_end
                cp      ' '                 ; R-N1: a blank copies but changes
                jr      z,tk_blank          ; NO state -- the name survives it
```
…and `tk_blank` itself goes **after `tk_copy_up`'s `jp tk_loop`**, well clear of
the fallthrough path:

```asm
tk_blank:                                   ; the in-a-name flag survives a blank
                ld      a,b
                ld      (TKNAME),a
                jp      tk_copy             ; ...and the blank itself is copied
```

**12 bytes, all sub-ROM** (the dispatch needs `jp`, not `jr` — `tk_blank` is out
of relative range). Asserted: `build/basic-reloc.rom` and
`build/zerobas-main-eu.rom` stayed **byte-identical** to HEAD
(`1d270536…`, `90403dbb…`), the way D-DECBLANK and D-EXPBAD did. Sub page-0 free
4026 → 4014 B.

### 4.3 Why the test goes THERE and not in `tk_copy`

⚠️ **`B` is only known-live before `match_kw`.** The existing code reads `B` at
[`tokenise.inc:57`](../basic/tokenise.inc:57), *before* the `match_kw` call at
line 93; a blank test inside `tk_copy` would read a `B` that `match_kw` has had
every opportunity to clobber. The early position is the correct one for a reason
that is not stylistic, and K4 (§5) is aimed at exactly this justification.

Short-circuiting also skips a blank past `match_kw` and the operator chain. That
is claimed to be **behaviour-neutral** (no keyword or operator begins with a
space) — a claim, so K4 tests it as a predicted-GREEN control.

---

## 5. Falsification — five knives

Each changes a **constant or one instruction**, never deletes a block: `make
basic-reloc` runs a hard dead-code gate (0 dead, both builds) and a knife that
orphans code fails the build and measures nothing.

Scope: `make lnblank-acceptance SIDES=vg8020,zb ONLY=nam,lit` — `lit` carries the
must-not-move cells (`lit-assign`, `lit-varname`), and `nam` is a substring of
`lit-varname` so that control comes along either way.

All five ran against the **corrected** code (`SIDES=vg8020,zb ONLY=nam,lit`,
34 gating rows including the 2 allowlisted `.` rows).

| knife | edit | predicted | measured |
|---|---|---|---|
| **K1** | `tk_blank`: `ld a,b` → `xor a` (the flag dies at a blank = pre-fix) | the 10 subject rows RED, every control GREEN | **24/34 — exactly those 10** ✓ |
| **K2** | `tk_blank`: `ld a,b` → `ld a,1` (the flag is *always* set after a blank) | subject rows GREEN; `nam-eqnum`, `nam-kw`, `lit-print` RED | **28/34** — those three **plus `nam-sfx`, `nam-sfxp`, `nam-parenblk`**, i.e. every row with a blank ahead of a digit where the state should be clear. Prediction was incomplete, not wrong |
| **K3** | `cp ' '` → `cp '$'` (the dispatch constant) | the 10 subject rows RED **and** `nam-sfx` RED | **23/34** — the 10, **and `nam-sfx0` rather than `nam-sfx`**: under K3 `nam-sfx`'s own blank clears the state again, so it agrees. The knife corrected which of the pair flips |
| **K4** | `tk_blank`: `jp tk_copy` → `ld a,(hl)` / `jp tk_nondigit` | **GREEN everywhere** | **GREEN** — see §5.2 |
| **K5** | `tk_namedig`: `ld a,1` → `xor a` (a digit stops extending a name) | `nam-ctl`, `nam-digblk`, `nam-run`, `nam-more` RED; `nam-letblk` GREEN | **25/34** — those four plus `nam-lval`, `nam-print`, `nam-amp0`, `nam-ampz`, `nam-ampl`; `nam-letblk`, `nam-two`, `nam-op` GREEN ✓ |

K1 and K5 partition the battery **differently** — K1 reddens `nam-letblk`/`nam-two`/`nam-op`
and spares `nam-ctl`/`nam-amp0`; K5 does the reverse. Two independent rules, two
disjoint witnesses.

### 5.1 🔴 K2 found a live defect in this slice's own first cut

The first cut placed `tk_blank` immediately **before** `tk_copy`. But `tk_copy`
is entered by **fallthrough** from `call is_letter / jr c,tk_copy_up` — so every
punctuation character fell *into* `tk_blank` and stored `B`, a register
[`match_kw`](../basic/tokenise.inc:103) uses as its own compare counter and has
long since clobbered by that point.

**That is exactly the liveness claim §4.3 makes, violated by the code §4.3
describes.** And the flawed build passed the differential **29/31** — it read
green on whatever `B` `match_kw` happened to leave behind. Clean **by luck**,
the [[cont-depth-slice]] pattern.

K2 exposed it because `ld a,1` makes the fallthrough's effect unmissable:

```
nam-sfx0   20 A=B$1   ref -> A<EF>B$<12>   zb(K2, flawed) -> A<EF>B$1
```

🔴 **A row with no blank in it at all went red under a knife that only touches
blank handling.** That is not a knife result — it is a defect report. The fix
moved `tk_blank` past `tk_copy_up`, and K2 re-run on the corrected code leaves
`nam-sfx0` and `nam-paren` **green**, which is the precise discriminator.

⚠️ **And the battery could not have caught this on its own.** Every row written
before the knife reached `tk_copy` through a blank, an operator or a type suffix;
none put *ordinary* punctuation between a name and a digit. `nam-paren`
(`20 A=B(1)`) and `nam-parenblk` (`20 A=B( 1)`) were added because of K2, and
oracle-locked on both references before zerobas was run on them.

### 5.2 K4 — predicted GREEN, and it needed triage to stay that way

K4 first reported `nam-parenblk` as **`REFUSED (empty program)`** — not wrong
bytes, a refused line. Run **alone at `--repeat 2`** on the same K4 build it reads
`A<EF>B( <12>)`, agreeing with the reference, with nothing printed to the screen.

The batched refusal was a **dropped keystroke**, and openMSX being deterministic
it would have reproduced on every re-run of that batch
([[deterministic-mangle-is-still-a-mangle]]). Triage order that settled it: run the
row alone → run it at `--repeat 2` → **read the screen** rather than the extracted
value.

So §4.3's second claim — that short-circuiting a blank past `match_kw` and the
operator chain is behaviour-neutral — **survives**: routing the blank back through
the full chain changes no row.

---

## 6. Gate changes

* `nam` battery: 23 new rows, oracle-locked before zerobas was run on any of them.
* `dir-name`: a new `--say` row for the semantic claim.
* 🔴 `dir-print`'s payload gains brackets. It had **no reading path at all** —
  `result_span_after_echo` returns the span between `[` and `]`, so a bracketless
  payload reads `<none>` on every side and compares EQUAL. Dormant rather than
  green (the gate filters `--say` rows out), but a row that cannot be wrong is
  not a row. Details: characterization §4.1.
* **Promote to gating** once the fix lands: `dec-bin` (this defect — it stops
  being informational the moment it has a rule) and `lit-varname` (it becomes a
  bounding control of R-N3).
* `KNOWN_DIVERGE` gains `nam-dot` and `nam-dot0` with exact bytes + a filed item.
  It stops being empty, and §3 is why.

---

## 7. Denominator — what this slice does NOT claim

* `!` and `#` type suffixes were not asked; `$` and `%` agree and the fix does not
  touch the suffix path.
* A trailing blank at end of line stays **not measurable through the keyboard**
  (`dec-eol`/`dec-eolctl`, informational by construction).
* Nothing here is claimed about a blank inside a **string** or a **REM**/`DATA`
  tail beyond the existing bounding controls `lit-str`, `lit-rem`, `dec-data`.
