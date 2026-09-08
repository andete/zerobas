# D-EXPKW — an exponent marker is not a marker in front of `L` or `Q`

Status: **awaiting sign-off**. Measurement:
[`docs/expkw-msx1-characterization.md`](expkw-msx1-characterization.md) (76 rows,
both references agree on all of them, oracle-locked before zerobas ran).

## 1. What was filed, and why it was the wrong subject

`../TODO.md:10070 (T-51AAE2)` filed **two standing-red acceptance suites with no expectation
written down** and asked for each to be fixed or pinned by name. The brief
carried three claims, and the measurement refutes all three:

1. *"`float-acceptance` → `reg.C.if_skip_over_float`, likely the `$0E`/`ELSE`
   class"* — it is neither the `$0E` class nor `tok_skip`'s float stride
   (`tokskip-body.inc:36` strides `$1D` correctly) nor `if_skip_to_else`. And it
   is **not about floats**: the same line with an integer literal breaks
   identically ([characterization §1.2](expkw-msx1-characterization.md)).
2. *"`logicops-acceptance` → 50 rows, all `EQV`/`IMP`, which are genuinely
   unimplemented, a recommended future slice"* — `EQV`/`IMP` landed in `ef098e9`
   at 156/156 (`basic/expr.asm:148`, `lg_eqv`/`lg_imp`). Of the 49 failing rows
   **every one contains `EQV` and none fails on `IMP` alone.**
3. *"two unrelated standing failures"* — **one defect.** `ELSE` and `EQV` are the
   only two reserved words in the language that begin with `E`, and the literal
   scanner eats their `E`.

🔴 **It is a regression, not a status quo.** `4b2202e` (D-EXPBAD, 2026-07-31)
deleted `tke_fail`, the rollback that put a digitless marker back, on the finding
that *"THE DIGITS ARE OPTIONAL AND THERE IS NO FAILURE CASE."* That generalisation
came from five rows — `1E`, `1E+`, `1D`, `1E#`, `12345EX` — **none of which puts a
reserved word behind the marker.** The rollback it removed was doing real work.

⚠️ D-DEFSTR's A/B falsification could not have found this: it stashed **`basic/`**
and rebuilt, but `tkf_try_exponent` lives in **`sub/tkfloat.asm`**. The A/B
answered "not mine" correctly and the conclusion drawn from it — "standing state,
pin it" — did not follow.

## 2. The rule (measured, both references)

In `tkf_try_exponent`, once the marker character is identified:

* **`D` marker** — always consumed. 26/26 second letters, no exception.
* **`E` marker** — the next character, reached **across a blank run** and
  **case-folded**, is examined. If it is **`L` or `Q`**, the marker is **not
  consumed at all** and the routine rolls back to its existing pre-blank target,
  leaving blanks, marker and letter verbatim in the source. Otherwise the
  existing D-EXPBAD path runs unchanged.
* The test sits at the character **immediately after the marker and nowhere
  else** — behind a consumed sign the ordinary rules resume (`1 E+L` is a single
  `1.0` then `L`).

**The test is the LETTER, not a keyword match.** `1 EQ` and `1 EL` keep their
marker although neither is a word; `1 ERL`, `1 DIM`, `1 EXP`'s `EX` lose theirs
although all are keywords. A `match_kw` implementation would diverge on `EQ`/`EL`
— and would cost a scratch destination cursor, because `match_kw` **emits** to
`(DE)` on a match.

## 3. The change

One site, `sub/tkfloat.asm`, in the `E` arm of the marker fetch — **sub-ROM page
0**, which has ~4008 B free. ⚠️ **No `basic/` byte is touched**, so the low
region (9 B) and main page 1 (5 B) are not disturbed and `input.asm` promotion
stays exactly as blocked as it was.

Sketch (~22 B), placed before `TKEXPD` is stored so a rejected marker writes
nothing:

```
tke_mark_e:     push    hl                  ; HL is ON the marker
                inc     hl
                call    tkf_fetch           ; blank-transparent lookahead
                call    upcase
                cp      'L'
                jr      z,tke_notmark
                cp      'Q'
                jr      z,tke_notmark
                pop     hl                  ; not L/Q: the E arm runs as before
                xor     a
                ld      (TKEXPD),a
                jr      tke_go
tke_notmark:    pop     hl                  ; discard the lookahead cursor
                pop     hl                  ; the routine's own pre-blank target
                ret                         ; has_exp stays CLEAR
```

Returning with `has_exp` clear is what makes `expb-elpct` (`1EL%`) come out
right: the suffix scan is *not* skipped, so `EL%` is an ordinary variable name.

## 4. Gates

**New rows** (76, all oracle-locked on both references before zerobas ran, all
past `make lnblank-echo` on all three sides), in `lnblank-acceptance`:

* `expk` 14 — the seam, both words, with and without a blank; `expk-ifelse` is
  the `float-acceptance` row's own stored bytes.
* `expw` 52 — the contiguous second-letter walk, both markers.
* `expb` 10 — the blank/sign boundaries the fix has to land in.

**Controls that must stay GREEN** (they agree today and must keep agreeing —
each one can move its own subject):

| control | what it would catch |
|---|---|
| `expk-nonkw` (`1 EX`) | a fix that stops eating the marker generally — reverting to pre-D-EXPBAD rule R |
| `expk-nonkwd` (`1 DX`) | the same on `D`, where the precision must survive |
| `expb-dlblk` (`1 D L`) | an `L`/`Q` test wired to **both** markers instead of `E` only |
| `expb-eldig` (`1E2L`) | a test placed after the digit loop instead of at the marker |
| `expk-okdig` (`1E2 EQV 3`) | a well-formed exponent broken by the new branch |
| `expb-elsign` (`1 E+L`) | a test placed after the sign lookahead (predicts eaten; a `L`/`Q` test in the wrong place makes it kept) |

🔴 **Falsification, and it must be run:** the two red suites are the knife.
`make logicops-acceptance` must go **49 FAIL → 0**, and `float-acceptance`'s
`reg.C.if_skip_over_float` must pass, *without* either suite being edited. Both
were red before the change and neither knows this slice exists. Reverting the
`sub/tkfloat.asm` hunk must take them back to exactly 49 and 1.

**Full corpus** after the change, per `TODO.md`: `unit-test` 55/55 · dead-code
gate 0/0 both builds · `lnblank-acceptance` **251+76 = 327/327** at `--repeat 2`
with `KNOWN_DIVERGE` **empty** · `array-acceptance` 149/151 (`ifc.instr.zero`,
`ifc.instr.neg`) · `arrdim` 73/73 · `clearpool` 52/52 · `float-acceptance` ·
`badfnum` 93 · `lof` 45 · `chancost-characterize` · `diskbasic` 34/34 · `bdos`
12/12 · `fat-error` · `error-trap` · `abort` 49/49 · `stop`/`strig`/`key`-trap ·
`linemax` 60/60 · `sysvarsweep` exit 0 with all five controls green.

## 4a. Results

| gate | before | after |
|---|---|---|
| `logicops-acceptance` | **49 FAIL** (every one an `EQV` row) | **193/193**, its landed count |
| `float-acceptance` → `reg.C.if_skip_over_float` | FAIL (371 PASS, 1 FAIL) | **PASS**, suite exits 0 |
| `lnblank-acceptance` | 251/251 | **327/327**, `KNOWN_DIVERGE` still **empty** |
| `unit-test` | 55/55 | 55/55 |
| dead-code gate | 0 dead both builds | 0 dead both builds |
| low region / main page 1 | 9 B / 5 B free | **9 B / 5 B free — untouched** |

Neither red suite was edited. The change is 22 B in sub-ROM page 0.

## 5. What still needs a decision (§6 of the TODO item stands)

Fixing this empties both red suites, so the *"pin it by name"* half of the filed
item becomes moot for them — **but the silence it complained about is real and is
not addressed by this fix.** Two follow-ons, filed rather than done here (one
item per session):

* ✅ **`logicops-acceptance` was not in the documented corpus** — that is why a
  tokeniser regression sat in it undetected across two slices. Added to the
  corpus list in `TODO.md` in this commit. It is a peer of the other standing
  gates and costs ~40 s.
  ⚠️ Note `make lnblank-acceptance` defaults to `--repeat 1`; the corpus
  requirement of `--repeat 2` needs `make lnblank-acceptance REPEAT=2`.
* **`float-acceptance` reports `371 PASS, 1 FAIL` and exits non-zero**, but
  nothing names the expected count, so "1 FAIL" reads the same whether it is
  known or new.

## 6. Sign-off questions

1. Fix, rather than pin? (The measurement says regression, and the fix is ~22 B
   in a region with 4008 B free.)
2. The `L`/`Q` **letter** test rather than `match_kw` — accepting that this is
   bug-for-bug fidelity to a hardcode, and that `1 EQ`/`1 EL` are the rows that
   force it?
3. 76 new rows into `lnblank-acceptance` (327 total, ~2.3 min at `--repeat 2`) —
   or should the 52-row `expw` walk be trimmed to its boundary rows once landed?
4. Add `logicops-acceptance` to the documented corpus in the same commit, or file
   it as its own item?
