# D-BAREEND — nine statement entries spent eleven bytes each on the same six instructions

**2026-08-28.** Landed on Joost's steer toward *"the ones that aggregate common
behaviour … simplifying the code and reducing size."* **Main page 1: 61 B → 106 B
free — +45 B**, and the idiom now has a name.

## 1. The idiom

Nine statement entry points open with the identical question — *"skip my own
token; did the statement end right here?"*:

```
                inc     hl                  ; past the <VERB> token
                call    skip_spaces
                or      a
                jr      z,<done>            ; end of line
                cp      COLON
                jr      z,<done>            ; before ':'
```

`pcr_flag_end` · `ex_clear` · `ex_close` · `ex_resume` · `ex_return` ·
`b4_maybe_s` · `ex_color` · `clr_bd` · `ex_width` — eleven bytes each, 99 in all.

🎯 **In every one of the nine, BOTH `jr z` go to the SAME label.** So the idiom
takes **one** parameter, not two, and collapses to a flag the caller branches on.
That is what makes a helper possible at all; had the two branches differed per
site, the shared part would have been the first four instructions only.

```
stmt_bare_end:  inc hl / call skip_spaces / or a / ret z / cp COLON / ret
```

9 B, returning **Z iff the statement ends here**, with exactly the A, HL and CF
the inline copies left behind — because it *is* those copies, with `ret z` where
they wrote `jr z,<own label>`. Each site becomes `call stmt_bare_end / jr z,<own
label>`: 5 B. **99 B → 9 + 45 = 54 B.**

## 2. 🔴 The tool found three of the nine, and priced them wrong

`clone_scout` ranked one live group — `ex_clear`, `ex_close`, `pcr_flag_end`,
*"est. save 48 B"*. Both halves of that are misleading, and neither is a bug:

* **Three, not nine.** It groups on a fixed span window with up to two operands
  masked. The other six differ *beyond* that window, so they never grouped. The
  family was found by grepping the **idiom** instead — a six-line regex over
  `basic/*.asm` — which is the question the tool is approximating.
* **48 B assumes a plain `call`.** Its estimate is `(n−1)·each − 4n`, which prices
  a body that can be called and returned from unchanged. This body *ends in a
  branch to a per-site label*, so the collapse is a flag-returning helper and the
  arithmetic is different.

⚠️ And the ranked figure the item quoted before today (`raf_noround`/`rsp_noround`
12 B, `ev_usr_index`/`usr_index` 8, `detok`/`pu_emit_tail` 8, the `files.asm` four
8, `ev_ff_stick`/`ev_ff_strig` 6) reproduces as **none of those groups at all** —
the ranking had rotted completely. Re-run it; never quote it.

🔴 A dump of the three ROM bodies shows how thin the byte-level agreement is: they
share **six bytes**, then diverge at the `jr` displacement.

```
ex_clear      23cd6042b72859 fe3a2855…
ex_close      23cd6042b72830 fe3a282c…
pcr_flag_end  23cd6042b72806 fe3a2802…
```

So "30 B each" is a source-level identity modulo masked operands, not a byte one.
Both readings are legitimate questions; only one of them is a price.

## 3. Region, checked first

**All nine callers and `skip_spaces` itself are page 1** (`$4260`–`$792E`). Nothing
reaches across the low/page-1 boundary to get to the helper — the hazard that
D-DUPSUPPLY had to price around, checked here before writing any code rather than
after.

## 4. Falsification

The nine verbs are CLEAR, CLOSE, RESUME, RETURN, COLOR, WIDTH, BSAVE's `,S`,
BLOAD's flag tail and `pcr`. **Battery 43/43 green** (`error-acceptance`,
`error-trap-acceptance`, `onerr0-acceptance`, `screenerr-acceptance`,
`stmtpend-acceptance`, `lineerr` ×8 and `clearpool-acceptance` all cover the
affected statements), and `make deadcode` is clean — the helper is reached, and no
site's tail became unreachable.

⚠️ The `jr z,<own label>` at each site still has to reach. Replacing 11 B with 5 B
moves every target *closer*, so no branch could go out of range; the assembler is
the authority and it linked without complaint.

## 5. What this does not claim

The nine sites are not "the same verb" — they are the same *question* asked at the
top of nine different verbs. Nothing about their bodies below the terminator test
is shared, and this change does not touch them.
