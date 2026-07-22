# G8 `VDP(n)` / `BASE(n)` — measured record (Philips VG-8020, 2026-07-22)

Black-box only (KEYBUF-injection REPL, work-area reads). No ROM disassembly.
Scripts: `g8_vdp_char1.py` … `g8_vdp_char7.py` in this directory.

## Method notes (two traps hit, both worth remembering)

1. **A case that ENDS erases the evidence.** Round 3's first run reported "(no
   change)" for every case: falling back to the READY prompt re-selects SCREEN 0
   and reprograms the VDP from scratch. Every state-delta case must hold the
   screen in a self-`GOTO` and be captured mid-hold (the G3 bitmap trick).
2. **Screen capture dies the moment the case moves the name table.** `BASE(n)=`
   relocates the text base, so the SCREEN-0 scrape reads the wrong VRAM and comes
   back blank. Report through memory (`capture=("mem_abs", …)`) instead.

## C1 — tokens (crunch bytes)

| source | crunch |
|---|---|
| `A=VDP(0)` | `41 EF C8 28 11 29` |
| `VDP(1)=2` | `C8 28 12 29 EF 13` |
| `A=BASE(0)` | `41 EF C9 28 11 29` |
| `BASE(0)=&H1800` | `C9 28 11 29 EF 0C 00 18` |

`VDP` = **$C8**, `BASE` = **$C9**, both single-byte function tokens. The
assignment form is NOT a separate statement token: a statement that begins with
the function token `$C8`/`$C9` is an assignment.

## C2 — `VDP(n)` read

* `VDP(0..7)` returns the RAM write-shadow: `VDP(1)` == `PEEK(&HF3E0)` (240 in
  SCREEN 0), for every mode.
* `VDP(8)` returns **159 == `PEEK(&HF3E7)`** = STATFL, the ISR's status copy —
  not a live port read.
* `n < 0` or `n > 8` → **ERR 5**.

Per-mode shadows measured (`R0..R7`, then STATFL):

| mode | R0 | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|---|
| SCREEN 0 | 00 | f0 | 00 | 00 | 01 | 00 | 00 | f4 |
| SCREEN 1 | 00 | e0 | 06 | 80 | 00 | 36 | 07 | 04 |
| SCREEN 2 | 02 | e0 | 06 | ff | 03 | 36 | 07 | 04 |

## C3 / E2 — `VDP(n)=v` write

* Updates the shadow **and reaches the chip**: `VDP(1)=VDP(1)AND223` (clear the
  interrupt-enable bit) froze `TIME` — delta 0 over a loop where the control case
  advanced 62. Nothing else moves (a `VDP(2)=7` delta is exactly `R2 06->07`).
* `v < 0` or `v > 255` → ERR 5; `n = 8` → **ERR 5** (read-only); `n` outside
  0..7 → ERR 5.

## D3 — coercion

Index and value both **truncate**, and the domain check runs AFTER truncation:

| case | result |
|---|---|
| `VDP(0.6)` | index 0 |
| `VDP(1.5)` | index 1 |
| `VDP(3.9)` | index 3 |
| `VDP(-0.4)` | index 0 — accepted, no ERR 5 |
| `VDP(0)=2.5` / `=2.9` | 2 |
| `VDP(0)=-0.4` | 0 — accepted |
| `VDP(0)=255.6` | 255 — accepted |

## C4 — `BASE(n)` read

Mode-INDEPENDENT (identical in SCREEN 0/1/2); `n` 0..19, anything else ERR 5.
The values are exactly the work-area words at `$F3B3 + 2n`:

```
BASE(0..4)   0000 0000 0800 0000 0000     (SCREEN 0)
BASE(5..9)   1800 2000 0000 1B00 3800     (SCREEN 1)
BASE(10..14) 1800 2000 0000 1B00 3800     (SCREEN 2)
BASE(15..19) 0800 0000 0000 1B00 3800     (SCREEN 3)
```

Slot kind by `n mod 5`: 0 name, 1 colour, 2 pattern generator, 3 sprite
attribute, 4 sprite pattern generator.

**★ Our runtime already matches this byte for byte** — the same dump on
`C-BIOS_MSX1_EU_REPACK_DISK` gives an identical 20-word table in all three
modes. `BASE(n)` needs no invented table; it is a word fetch.

## G1 / G2 — `BASE(n)=v` accepted values

Value must satisfy `0 <= v < $4000` **and** be a multiple of the slot's grain:

| slot kind | grain | exception |
|---|---|---|
| name | $400 | — |
| colour | $80 | **group 2 (SCREEN 2): $2000** |
| pattern | $800 | **group 2 (SCREEN 2): $2000** |
| sprite attribute | $80 | — |
| sprite pattern | $800 | — |

Anything else → ERR 5. The check is tied to the **slot's group, not the current
mode**: writing `BASE(11)=&H0400` from SCREEN 0 still fails, and the group-3
slots validate the same way from any mode.

## E1 / F1 / I1 — what `BASE(n)=v` does to the chip

1. Store the word (always, if it validates).
2. Reprogram the VDP **only when the slot's group == SCRMOD**; a cross-group
   write (e.g. `BASE(10)=` from SCREEN 0) touches no register at all.
3. And the reprogram is where the reference gets strange:

| current mode | effect |
|---|---|
| SCREEN 0 | writes exactly the one register the slot owns, = `v / grain` (`BASE(3)=&H1F00` → `R5=$3E`) |
| SCREEN 3 | same, correct single-register update |
| **SCREEN 1** | ignores `v`'s own register; programs the chip from **group 2's** table + SCREEN 2's mode bits |
| **SCREEN 2** | ignores `v`'s own register; programs the chip from **group 3's** table + SCREEN 3's (multicolor) mode bits |

`SCRMOD` never changes — the *mode variable* stays put while the *chip* is left
configured for the next mode.

The off-by-one-group reading is not inferred, it is **poison-tested** (I1): with
`BASE(13)` (group 2, sprite attribute) pre-set to `&H0400` from SCREEN 0, a
`BASE(8)=&H1F00` write in SCREEN 1 leaves `R5=$08` — the poisoned group-2 value
(`$0400/$80`), not `$3E` from the value just written, and not the untouched
`$36`. Same for SCREEN 2 reading group 3 (`R5=$08` from `BASE(18)`, `R6=$02`
from `BASE(19)`).

A following plain `SCREEN 2` puts everything right (`R5=$3E` from the newly
stored `BASE(13)`), so the mode-setup path is correct — only the
assignment's immediate reprogram is off by one group.

## H1 — grammar edges

| form | result |
|---|---|
| `VDP(0)=VDP(0)`, `BASE(0)=BASE(0)` | OK |
| `A=1:VDP(0)=2:B=3`, `IF 1 THEN VDP(0)=2` | OK |
| `LET VDP(0)=2`, `LET BASE(0)=…` | **ERR 2** |
| `VDP(0)` alone, `VDP=1`, `BASE=1`, `VDP 0=1`, `A=VDP`, `A=VDP 0` | ERR 2 |
| `VDP(0,1)=2`, `VDP(0)=1,2` | ERR 2 |
| `FOR VDP(0)=0 TO 1`, `SWAP VDP(0),A` | ERR 2 |
| `VDP(0)=` | **ERR 24** (Missing operand) |
| `VDP(0)="A"`, `VDP("A")=1`, `BASE(0)="A"` | ERR 13 |

## Residual: our register values differ in SCREEN 0/1

C-BIOS programs a few registers differently from the reference BIOS:

| mode | reference | ours |
|---|---|---|
| SCREEN 0 | R3=00 R5=00 R7=f4 | R3=**80** R5=**36** R7=f4 |
| SCREEN 1 | R3=80 R5=36 R7=**04** | R3=80 R5=36 R7=**f4** |

So `VDP(3)`/`VDP(5)`/`VDP(7)` read back different values on our runtime in
SCREEN 0/1. That is a BIOS-level difference, below the BASIC statement — it is
not something the G8 code can or should paper over. SCREEN 2 agrees exactly.
