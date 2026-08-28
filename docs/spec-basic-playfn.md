# D-PLAYFN — `PLAY(n)` measured in full, implemented, and priced at 49 B of main page 1

**2026-08-28.** Takes the item filed 2026-08-24 by the seam classifier from
*"unpriced; needs its own probe"* to a **working implementation with an exact
price**. The patch is banked, not landed: 49 B is 55 % of main page 1's remaining
budget, and that is Joost's call. Marked 🔭.

## 1. The filed claim, re-run

Confirmed. `PLAY(0)` answers on both references and raises **ERR 24 Missing
operand** on zerobas — the function form is unparsed, while the PLAY *statement*
works on all three (`q.stmt`, the control).

## 2. The semantics, measured — and the item's own description was incomplete

The item said only "-1 (voice 0 playing) / 0 (idle)". The real rule needed two
more rounds to pin, because **two rules fit every row the first round produced**:

* **A** — `n=0` means "is ANY voice playing", `n=1..3` are the three voices.
* **B** — the numbering is 0-based, `n=0` being voice 1.

A single `PLAY"…"` string plays voice 1, so both rules predict `PLAY(0)=PLAY(1)=-1`
and cannot be told apart. The separating rows play **only the second** and **only
the third** voice ([`scratchpad/playfn_voice_probe.py`](../scratchpad/playfn_voice_probe.py)):

| playing | `PLAY(0)` | `PLAY(1)` | `PLAY(2)` | `PLAY(3)` |
|---|---|---|---|---|
| `PLAY"L1CDEFGAB"` (voice 1) | −1 | −1 | 0 | 0 |
| `PLAY "","L1CDEFGAB"` (voice 2) | −1 | 0 | −1 | 0 |
| `PLAY "","","L1CDEFGAB"` (voice 3) | −1 | 0 | 0 | −1 |

**Rule A. B is refuted.** Both references agree on every cell, so there is a clean
oracle. Domain: `PLAY(4)` and `PLAY(-1)` are **ERR 5**.

### 2.1 The argument TRUNCATES, and one row was not enough to say so

`PLAY(1.7) = -1` with voice 1 playing points at truncation — but `PLAY(0.9) = -1`
fits truncation *and* rounding, so it separates nothing. The decisive pair plays
voice 3 ([`scratchpad/playfn_coerce_probe.py`](../scratchpad/playfn_coerce_probe.py)):

| row | truncate predicts | round predicts | measured (both refs) |
|---|---|---|---|
| `PLAY(2.7)` | 2 → **0** | 3 → −1 | **0** |
| `PLAY(3.7)` | 3 → **−1** | 4 → **ERR 5** | **−1** |
| `PLAY(-0.4)` | 0 → −1 | 0 → −1 | −1 (control) |

`PLAY(3.7)` is the sharpest: the two rules predict *an answer* and *an error*.

## 3. Why this is a function and not a feature

🎯 **The state is already maintained.** `basic/playsvc.asm`'s H.TIMI servicer
clears each voice's `MUSICF` bit at OP_END, so `MUSICF` bits 0/1/2 (voices A/B/C)
**are** the answer — the implementation is a masked read, not an audio subsystem.

⚠️ **Doc debt found in passing:** `basic/play.asm`'s header still says *"Slice 2a
has NO live drain (the interrupt servicer is Slice 3), so PLAY returns immediately
after the parse."* The half about returning is true; the half about the drain is
**stale** — `basic/playsvc.asm` ships. Read as current it says `PLAY(n)` is
unimplementable, which is how a stale sentence prices a feature out of existence.

## 4. The implementation, and its measured price

[`scratchpad/playfn_impl.patch`](../scratchpad/playfn_impl.patch) — applies clean.
A factor-dispatch arm in `basic/expr.asm` beside `POINT`/`VDP`, and `ev_f_play` in
`basic/play.asm` reusing `g8_open_paren` (which already parses `(n)` and raises
ERR 13 on a string). The voice mask is a **table**, not a shift loop, because
`n=0` is not voice 0 — it is all three, so "any" is a table entry rather than a
special case.

**Verified on the machine, not by reading:** with the patch applied, all 18 rows
across the three probes match both references exactly — every voice-isolation
row, both coercion separators, and the ERR 5 domain edge.

| wall | before | with the patch |
|---|---|---|
| main page-1 free | **89 B** | **40 B** |
| page-0 low, sub p0, sub p1 | 39 / 2434 / 1622 | unchanged |

**49 B.** That includes **+1 B that is genuinely part of the price**: the 5-byte
dispatch arm pushed `jr z,ev_f_erlfn` — already ~170 lines from its target — out
of relative range (*"Relative jump out of range on line 504"*), so it had to
become a `jp`. A cost that only appears when you build it.

## 5. Why it is banked rather than landed

49 B is **55 % of main page 1's remaining 89 B** for one function. Nothing has to
be *evicted* to fit it, which is the strict reading of 🙋 — but `TODO.md`'s own
rule is that **ties go to 🙋**, and spending over half the scarce page in one go
is at minimum a tie. The measuring and pricing were mine; the spend is not.

The tree is reverted and page 1 is back to **89 B**, verified by rebuild. Applying
is one command:

```bash
git apply scratchpad/playfn_impl.patch && make repack-machine
```
