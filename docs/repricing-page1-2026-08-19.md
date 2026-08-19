# Nothing was unblocked: re-pricing the page-1 declines against a 64 B wall

D-REPRICE, 2026-08-19, on `main`, based on `b51bbbb` (D-VPTRDOM). Not a fidelity
slice — a measurement of the *filed record*, in the way
[`gate-blindness-sweep.md`](gate-blindness-sweep.md) is a measurement of the
apparatus.

D-EVSPDUP (`33720ae`) took main page 1 from **3 B to 69 B** by deleting a
redundant `ld a,(ix+0)` at 24 `ev_sp` call sites. D-VPTRDOM (`b51bbbb`) spent 5.
Its own TODO entry then said the thing that made this document necessary:

> ⚠️ **Those declines are now UNPRICED, not automatically live**: each was a
> claim about a design as well as a wall, and re-opening one means re-reading
> its own reasoning, not just the free-byte count.

That is exactly right, and this document is the walk it asks for. **The answer is
that not one open item's stated blocker is cleared by the 64 B**, and the two
declines that entry named as examples were *already closed when it was written*.

---

## 1. The wall, measured — not carried forward

`rm -rf build && make basic-reloc`, at `b51bbbb`:

| region | free | note |
|---|---|---|
| **main page 1** | **64 B** | the subject of this document |
| main page-0 low | **5 B** | still the binding wall by a wide margin |
| sub page 0 | 3295 B | |
| sub page 1 | 1627 B | |

⚠️ **64 B, not the 69 B the D-EVSPDUP entry states** — D-VPTRDOM spent 5 the same
day. An estimate copied forward is indistinguishable from a reading, so every
figure in this document is from the run above.

---

## 2. The denominator, machine-produced — and falsified from a second direction

A hand-listed denominator is a scope claim, so the roster was produced by
script over all **63** `- [ ]` items in `TODO.md`, not by memory.

**Sweep A — keyed on decline vocabulary** (`DECLINED WITH NUMBERS`, `does not
fit`, `no room`, `not affordable`, …): **7 of 63** open items matched.

**Sweep B — keyed on the opposite thing**, deliberately not using decline words
at all: any open item mentioning **both** a byte quantity **and** a region
(`page 1`, `main page`, `low region`): **8 of 63** matched.

🔴 **Sweep B found one item sweep A missed, and that is the whole reason it was
run.** `ex_let_arr_str` (line 2695) mentions **49 B** and never uses a decline
word. Read in full it turns out not to be a price at all — see §3.7 — but a
keyword roster alone would have reported it as absent, and the absence would
have been a scope claim rather than a reading.

The union is **10 items**; the two sweeps disagree on three, and each
disagreement is informative:

| item | sweep A | sweep B | why they differ |
|---|---|---|---|
| SCREEN 3 (L1605) | ✅ | ❌ | uses the word "declined", carries **no price** — not a byte decline |
| `err_verify`/`brk_msg` (L7967) | ✅ | ❌ | prices are **carves** (bytes freed), not spends |
| `ex_let_arr_str` (L2695) | ❌ | ✅ | states the **wall**, not a price |

A docs-side sweep (`docs/*.md`, decline word + page-1 + a price within ±3 lines,
18 hits across 11 files) added **no live item**: every one resolves to a spec
that shipped or was superseded — `lvsites`/`fldary` (§3.1), `onerr0` (closed by
D-LOCARG at exactly its filed +7 B), `lrvar`, `listrange`, `delete`,
`print-hash-using`, `missing-class-slicing`, and `traps-t1-stop-reslice` (closed
with the trap arc; all five trap acceptance targets exist).

---

## 3. The verdicts — byte reason separated from the other reasons

### 3.1 🔴 The two declines the D-EVSPDUP entry named are BOTH ALREADY CLOSED

The entry cites *"`spec-basic-fldary.md` at 38 B, D-LVFIX's FIELD/LSET half at
~80 B"* as declines the carve might now fund. Both are `- [x]` in the same file:

* **D-FLDARY shipped 2026-08-08** — `make fldary-acceptance` **13/13**,
  `lvfix-acceptance` 18/18, **+40 B page 1 funded by a 57 B carve**
  (`lrset_store` → sub-ROM page-0 tenant). Three of the decline's four reasons
  did not survive a design.
* **The ~80 B FIELD/LSET half is the same slice**, and its TODO entry says so in
  its own title: *"SUPERSEDED BY THE ENTRY ABOVE … nothing here is open."*

🎯 **Neither was ever going to be funded by this carve, because neither was still
declined.** They were closed eleven days before the entry that cites them was
written — and closed *by a carve*, which is the same instrument, applied earlier.
The brief that opened this task flagged fldary as "worth checking first, because
a stale decline is exactly the failure mode here". It was, and it is.

### 3.2 `FIELD overflow` (ERR 50) — the ONLY item whose byte half the wall clears

Filed by D-FLDWIDTH, re-priced by D-EVALCHK. **≈27 B** (14 B to fetch
`FCH_RECLENS[ch]` main-side, 10 B for the 16-bit compare, 4 B to raise), against
6 B when filed and 16 B when re-priced — *"still short by 11 B"*.

💰 **At 64 B the byte half is now covered, and it is the only one in the file.**

🔴 **It is still declined, and its own document says why bytes were never the
whole blocker:**

1. **No accessor to borrow.** `load_reclen` (`basic/randio-body.inc:270`) is
   **sub-ROM** (`sub/randio.asm:47`) and not callable from `ex_field`;
   `GP_RECLEN` is only loaded at GET/PUT time, so reading it at `FIELD` time
   reads a stale cell.
2. **🔴 THE DENOMINATOR IS NOT BUILT.** Every measured row uses the **default
   256-byte record**, so nothing measured separates *"checked against the record
   length"* from *"checked against a constant 256"*. It needs `OPEN … LEN=r`
   rows before a byte is spent.

Its own words, and they still hold: *"Bytes alone were never the whole blocker
and are still not."* ⚠️ ONE reference (Disk BASIC; a diskless VG-8020 cannot
express the question).

### 3.3 SCREEN 3 — never a byte decline

*"Priced at nothing; not scouted."* A **whole-feature** gap: zerobas has no
SCREEN-3 pixel op at all, and SCREEN 3 is 64×48 multicolour, not a bitmap, so
closing it needs a second rasteriser and a second address/clash model. Two
references. **Unaffected by the wall in either direction.**

### 3.4 Keyword-completeness gaps — still over the wall

**183–268 B** for the measured remainder. 64 B does not reach it.

### 3.5 `err_verify` / `brk_msg` — carves, and blocked on non-byte grounds

These *free* bytes, so a larger wall is not the currency:

* `err_verify` (8 B): costs 5 B to save 8 — net 3 B — and **makes `PRINT ERR`
  read 20 after a `CLOAD?` mismatch, an observable change with no oracle reading
  behind it.** Blocked on a **missing reading**, not on space.
* `brk_msg` (6 B): `print_string` has **no escape decoder at all**. Blocked on a
  **printer change**.

### 3.6 "135 more dead bytes" — not a decline at all

D-RETLN carved **all 160**; the entry's own last paragraph says *"the open
question this leaves is not the 160 B (they are gone) but whether a gate should
exist for the shape"*.

🎯 **AND IT PREDICTED D-EVSPDUP, SEVENTEEN DAYS EARLY.** Filed 2026-08-02:
*"a redundant-load sweep is a two-line matcher, and there are certainly other
idioms like it."* `ev_sp` is that idiom — the identical contract (`ret nz` with
`A` already loaded), a different routine — and it was found on 2026-08-19 by
hand, while scouting 5 B for something else. **The tool this item asks for would
have found 72 B automatically, and the entire re-pricing this document performs
would not have been necessary.** That makes it the highest-value *open* item in
the roster, and it costs zero page-1 bytes.

### 3.7 `ex_let_arr_str` — a stale WALL, not a price

*"Main page 1 is down to **49 B** after D-ARYLV, so this one needs
`tools/carve_scout.py` before a byte moves."* The 49 B is the wall as it stood,
not the cost of the fix; the fix is **"not carve-scouted"** and unpriced. Its
real blocker is a design one and is stated: the obvious 4-byte `FPERR` check
raises **ERR 7 "Out of memory"** where both references say **ERR 14 "Out of
string space"**, because `ARY_ERR=4` **conflates** the `DIM` allocation OOM with
`aeng_copy_str`'s string-heap OOM. *"The 4-byte check would trade a swallowed
error for a WRONG MESSAGE, and score green on any gate that only asks 'did it
error'."* ⚠️ The `DIM` half is still **UNMEASURED**.

### 3.8 The two candidates that carry no price at all

* **`RETURN` does not discard an open `FOR`** — architectural (zerobas keeps FOR
  and GOSUB on separate RAM stacks), **two references**, never priced.
* **`OPEN A$ AS #1`** — *"Not scouted and not priced"*; needs its own
  denominator (`OPEN`/`KILL`/`NAME`/`SAVE`/`LOAD`/`BLOAD` × literal/variable/
  expression). One reference.

---

## 4. 🔴 The class this walk actually found: FOUR open items state the wall inline, and all four are wrong

Not one of these is a price. Each is an item asserting **current** free space, in
prose, as fact:

| item | asserts | actual at `b51bbbb` |
|---|---|---|
| Editor / program management (L4392) | *"THE PAGE-1 WALL IS NOW **14 B**"* | **64 B** |
| `FIELD overflow` (L1317) | *"main page 1 is now **16 B**"* | **64 B** |
| `ex_let_arr_str` (L2695) | *"Main page 1 is down to **49 B**"* | **64 B** |
| Slim the file-channel context (L5568) | *"**9 B** free low / **6 B** free page 1"* | **5 B** low / **64 B** |

🎯 **THIS IS THE SAME SHAPE AS THE 160 DEAD BYTES, IN PROSE.** A figure that was
a reading when written, copied nowhere, checked by nothing, and silently false
from the next slice onward — and the reason a decline can look priced years after
its price stopped being true. `make basic-reloc` prints all four walls on every
run; **no gate compares them to a single sentence in `TODO.md`.**

⚠️ **And the direction of the error is the dangerous one.** Three of the four
understate the wall, so each reads as *less* affordable than it is. A slice
opening any of these items and trusting the inline figure would decline work it
can now fund — which is precisely what the D-EVSPDUP entry warned about, one
level further down than it looked.

Per the house rule, the readings **stand as taken**; each gets a dated addendum
rather than a rewrite, and the figure is marked as of its date.

---

## 5. Verdict table

| # | item | byte reason cleared at 64 B? | other reasons | status |
|---|---|---|---|---|
| 1 | D-FLDARY 38 B | — | — | ✅ **SHIPPED 08-08** (stale citation) |
| 2 | D-LVFIX FIELD/LSET ~80 B | — | — | ✅ **SUPERSEDED by #1** (stale citation) |
| 3 | `FIELD overflow` ERR 50 | ✅ **YES** (≈27 B) | 🔴 no main-side accessor; 🔴 **denominator not built** | **STILL DECLINED — non-byte** |
| 4 | SCREEN 3 | n/a — never priced | whole-feature: second rasteriser | **NOT A BYTE DECLINE** (2 refs) |
| 5 | Keyword-completeness | ❌ 183–268 B | — | **STILL OVER THE WALL** |
| 6 | `err_verify` | n/a — a carve | missing oracle reading | **NOT BYTE-BLOCKED** |
| 7 | `brk_msg` | n/a — a carve | needs a printer change | **NOT BYTE-BLOCKED** |
| 8 | 135 dead bytes | n/a — already carved | it is a **tooling** item | **NOT A DECLINE** |
| 9 | `ex_let_arr_str` | n/a — 49 B is the wall | `ARY_ERR=4` conflation; `DIM` half unmeasured | **UNPRICED** |
| 10 | `RETURN`/`FOR`, `OPEN A$` | n/a — never priced | architectural / no denominator | **UNPRICED** |

🎯 **The 64 B unblocked nothing.** Exactly one item (#3) had a page-1 price the
wall now covers, and it stays declined on two non-byte grounds its own document
names. Every other byte figure in an open item is a stale **wall** reading (#9
and the four in §4), a **carve** that frees bytes (#6, #7, #8), or a price still
far over 64 B (#5).

⚠️ **That is the finding, and it is a good one.** "There is room now" was worth
testing precisely because it was plausible; it turns out the filed record's
byte-shaped blockers had already been dissolved by carves, and what remains is
blocked by missing measurements and missing designs — which no amount of free
page 1 buys.
