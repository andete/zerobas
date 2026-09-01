# D-RECLAIM — +8192 B of BASIC memory, from a region that was reserved for nothing

**2026-09-01.** `FRE(0)` **14767 → 22959**, against the CF-3300's 23348 — from
**8581 B short of the reference to 389 B short**. No ROM cost: both walls are
unchanged (low 106 B, page 1 331 B). It is a RAM-layout change, and the whole of
it is three constants.

D-FREGAP ([`spec-fre-gap.md`](spec-fre-gap.md)) found the gap and priced it. This
spends it.

## What was actually reserving the memory: nothing, in BASIC mode

`TXTMAX` — the text ceiling, not HIMEM — sat at `$BB00`, so everything above was
invisible to BASIC. Above it:

| span | size | what is there |
|---|---|---|
| `$BB00`–`$C000` | 1280 B | `DETOKBUF` |
| `$C000`–`$E000` | **8192 B** | MSX-DOS territory — **two allocated bytes** |
| `$E000`–`$F380` | 5000 B | the real workspace, 502 named cells |

The 8192 B is real DOS territory: boot-sector load `$C000`, kernel work area
`$D606`, BDOS dispatcher `$D831`, kernel FCB `$DA40`, DOS work area
`$DD0E`–`$DD8E`. Every one of those is live **only under MSX-DOS**, and
**BASIC and DOS never co-exist** (Joost, 2026-09-01) — a DOS boot replaces BASIC
wholesale, and the boot sector loads at `$C000` during INIT, before any program
exists.

🟢 **AND THE REFERENCE ALREADY PROVES THE MODEL.** The CF-3300 runs BASIC up to
`HIMEM $DE77` and expects a program that BLOADs high to `CLEAR`/`HIMEM` down
first — which is what those verbs are for. zerobas was reserving statically what
the reference reserves dynamically.

## The change

* `TXTMAX` `$BB00` → **`$DB00`**
* `DETOKBUF` `$BB00` → **`$DB00`** (1280 B, `$DB00..$DFFF`, topping out exactly
  at the `$E000` workspace floor — its size is a consequence of LINEMAX and is
  unchanged)
* `GFX_DJ` `$C120` → `$E220`, `GFX_BAD` `$C121` → `$E3E5`

🔴 **THOSE TWO BYTES ARE THE PART THAT WOULD HAVE CORRUPTED SILENTLY.** They sat
alone in the 8192 B, above a boundary every other allocation respects — which is
how D-FREGAP found them. With the ceiling raised they would be **inside the BASIC
text area**, written by any draw, corrupting a program larger than ~16 KB. Small
test programs would never have caught it. They are rehomed into two cells this
file already documents as retired and free: `$E220` (was `STOPGRACE`, retired
2026-07-25) and `$E3E5` (was `STRENG_SPARE`, the D-2 flag).

## The rows: usable, not merely reported

A rising `FRE(0)` proves an arithmetic change. It does not prove the memory
*works* — a ceiling can be raised over a region that faults, is shadowed, or is
overwritten by something unmapped. So `scratchpad/reclaim_probe.py` **allocates
across the old ceiling and reads the data back**.

| row | | CF-3300 | zerobas |
|---|---|---|---|
| `d.small` | `DIM A%(1000)` | 7 | 7 |
| `d.mid` | `DIM B%(6000)` | 11 | 11 |
| **`d.big`** | **`DIM C%(9000)`** — 18000 B | **13** | **13** |
| **`d.big0`** | far end of the same array | **17** | **17** |
| `d.huge` | `DIM E%(15000)` — 30000 B | ERR 7 | ERR 7 |

**0 DIFF on all five.** `d.big` is 18000 B of elements: it does not fit the old
14767 and does fit the new 22959, so **the row is the reclaim**.

🟢 **BOTH CONTROLS EARN THEIR PLACE.** `d.small` shows the apparatus can allocate
at all. `d.huge` shows **the ceiling still EXISTS** — a change that removed the
bound entirely would pass every other row here and be a far worse bug.

## Falsified by planting

Putting `$BB00` back, on the same rows:

| | old ceiling | new ceiling |
|---|---|---|
| `FRE(0)` | 14767 | 22959 |
| `d.big` / `d.big0` | **ERR 7** | 13 / 17 |
| `d.small` / `d.mid` | unchanged | unchanged |
| `d.huge` | ERR 7 | ERR 7 |

The two reclaim rows move and nothing else does.

## What the battery caught, which is the part worth keeping

The first full run after the change was **88/92, two of them REAL on the serial
retry**. Both were the change's own consequences, and neither would have been
obvious by reading:

**`graphics-floor-acceptance`** read `GFX_DJ`/`GFX_BAD` at their **old**
addresses and got `dj=0`, `bad=255` — uninitialised memory. It scored a draw
that never happened, and **failed loudly rather than passing**, which is the good
outcome: the probe hardcoded `$C120`/`$C121` in three places.

**`array-acceptance`**'s two chain-OOM rows stopped OOM-ing. They squeeze memory
with `CLEAR 200,50000 : DIM Z(1840)`, and the allocation ceiling is
`min(HIMEM,TXTMAX)`: while `TXTMAX` was `$BB00` **it** was the binding term and
the `CLEAR` value was a no-op, so raising it handed the rows 2128 B they did not
expect.

🎯 **THE FIX WAS TO PIN THE SQUEEZE, NOT TO GROW THE ARRAY.** `CLEAR 200,47872`
restores the geometry exactly and makes the rows depend only on a number they set
themselves. **A test whose squeeze is defined by someone else's ceiling is
measuring that ceiling, not its subject** — and would have gone red again on the
next TXTMAX move.

⚠️ Two more rows carry `CLEAR 400,50000` with a comment reading `-> C=$BB00`.
They still pass, and that comment is now false; left as noted doc debt rather
than edited blind, since changing a passing squeeze is how you lose one.
