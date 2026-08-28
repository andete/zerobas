# D-NGRAM — repeated instruction *sequences*, and the 50 B the clone tool could not see

**Status:** `req_letter` SHIPPED 2026-08-28, **−50 B of main** (low region read
50 → 68 B free, page 1 154 → 186 B, both on 2026-08-28 — readings, not standing
figures; `make basic-reloc` is the current one).

## 1. Why another sweep

[`tools/clone_scout.py`](../tools/clone_scout.py) masks up to **two operands by
design**, so it finds *parameterisable* clones and prices them as a `call`. Twice
on 2026-08-28 its ranking was beaten 3:1 by grepping a shape by hand — D-BAREEND
(+45 B) and D-POPRAISE (+13 B) — because those wins were **exact** repeats
collapsible into a shared body, which is a different object.
[`scratchpad/ngram_sweep.py`](../scratchpad/ngram_sweep.py) looks for that kind:
exact operands, no masking, sequences of 3–12 instructions, never spanning a
label (another entry path would enter mid-body).

**Pricing is unforgiving, and that is the point of printing it:**

```
as a SUBROUTINE   k sites of m bytes -> one body (m+1 for `ret`) + k calls (3 B)
                  saving = m(k-1) - 3k - 1
as a SHARED TAIL  the sequence already ends in an UNCONDITIONAL terminator
                  saving = (m-3)(k-1)
```

A 6 B sequence at 3 sites is worth **2 B**. Sizes are estimated from the mnemonic
form; anything the estimator cannot price is reported UNKNOWN and never counted,
so a mis-estimate cannot manufacture a candidate.

## 2. 🔴 Two instrument faults, both caught before a number was quoted

* **The raw table was all `sub/`.** Hundreds of bytes of repeated mathpack calls
  in `sub/fp_atan.asm` and friends — and sub p0/p1 had 2444 + 1622 B free. Those
  bytes buy nothing. `--main` rescores each candidate on its **main-region sites
  only**, which is what surfaced the real ones. Third time in one day that region
  turned a nominal price into a real one ([[grep-the-idiom-beats-the-clone-ranking]]).
* **A conditional jump is not a terminator.** The first cut keyed "is this a
  tail?" on the *mnemonic*, so `jp nc,stmt_error` counted as one — and the top
  candidate was priced as a shared tail it can never be, because execution falls
  through a conditional. Only an unconditional `ret`/`jp`/`jr` ends a sequence.

## 3. What shipped: `req_letter`

```
call skip_spaces / call is_letter / jp nc,stmt_error        9 B, x10
```

*"A name must start here, else Syntax error."* Open-coded at **ten** statement
entries: `DIM` and `ERASE` ([arrays.asm](../basic/arrays.asm)), `DEF FN`,
`FIELD`, the disk string-variable parse ([files.asm](../basic/files.asm)),
`INPUT`, both `SWAP` operands ([missing.asm](../basic/missing.asm)), `FOR` and
`READ` ([program.asm](../basic/program.asm)). One 10 B body plus ten 3 B calls
replaces 90 B.

```
req_letter:     call    skip_spaces
                call    is_letter
                ret     c                   ; a letter: hand it back untouched
                jp      stmt_error          ; not a letter: the statement aborts
```

🎯 `ret c / jp stmt_error` is byte-for-byte the same 4 B as the `jp nc,stmt_error
/ ret` it replaces, and inverting it that way leaves the caller's state **exactly**
as the open-coded form did: CF still set on return, A still the letter, HL still
the cursor — `call`/`ret` touch none of them.

⚠️ The extra return address costs nothing on the failing path: `stmt_error` never
returns and both its arms reset SP (the trap arm at `interp.asm:1022`, the abort
arm through `fre_abort_low`) — the same fact D-POPRAISE's discard-tails rest on.

## 4. Folding lines orphans the comments that lived on them

Collapsing three instructions into one deleted the trailing comments of two of
them, leaving dangling half-sentences (*"…masked exactly this)"* with no opening)
and silently dropping site notes like *"READ needs a variable"* and *"operand 2
is not a name"*. Every site's own analysis was reattached to its surviving `call`
line. **A carve that leaves the tree smaller and less explained has not paid for
itself** — docs are a co-equal deliverable here
([[documentation-deliverable-discipline]]).

## 5. Still open, measured, not taken

| B | shape | sites |
|---|---|---|
| 41 | `call skip_spaces / or a / jp z,loc_missing / cp COLON / jp z,loc_missing` | 6 |
| 40 | the `subrom_call` + `LE_STATUS` sequence | 5 |
| 31 | `inc hl` + the `req_letter` shape | 6 — **overlaps §3, re-measure** |

The first two are genuine and unclaimed. The third overlapped what shipped and
must be re-run rather than inherited — **a ranked candidate rots like a wall**
([[a-ranked-candidate-rots-like-a-wall]]).
