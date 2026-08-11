# G6 `DRAW` — VG-8020 black-box characterization notes (2026-07-22)

Notebook for the G6 slice: dated raw findings, the provenance trail behind the
pins that get distilled into `docs/spec-basic-graphics-g6.md`. Pure black box —
`DRAW` was exercised on a real reference machine profile under openMSX and its
observable effects (work-area cells, VRAM pattern **and** colour planes, `ERR`)
recorded. No ROM was disassembled.

Probes (all in `scratchpad/`, re-runnable):

| probe | what it measured |
|---|---|
| `g6_draw_char1.py` | token crunch; endpoints for every command; error surface |
| `g6_draw_char2.py` | persistence/reset; colour; odd-value endpoints; `X` substrings; bitmap vs `LINE` |
| `g6_draw_char3.py` | `S0`; the count wrap; bare letters; angle × `B`/`N`; separators |
| `g6_draw_char4.py` | the scale-arithmetic model, falsified on fresh pairs; negative rounding |
| `g6_draw_char5/6/7.py` | disambiguating what owns the DRAW colour (3 rounds — see §6) |

Measurement method note: every case prints its readout behind a **per-case tag**
(`Q<i>Q`) because a batched case's output can otherwise be mistaken for a stale
line still on the screen from an earlier case. Round 1 was first read without the
tag and looked like nonsense — see §2.

---

## 1. Grammar (round 1)

Crunch: `DRAW` = token `$BE` (matches the arc-level pin), argument is an ordinary
string expression (`DRAW A$`, `DRAW "a"+"b"` all crunch and run).

Commands measured, from `PSET(100,100)`, default state:

| form | effect |
|---|---|
| `U D L R` | up/down/left/right; **bare letter = 1** (`U` → y−1) |
| `E F G H` | the four diagonals; `E10` → (+10,−10), `F10` → (+10,+10), `G10` → (−10,+10), `H10` → (−10,−10) — i.e. `n` in **each** axis |
| `M x,y` | **absolute** move-and-draw when the *first* operand has no sign prefix |
| `M ±x,±y` | **relative** when the first operand is `+`/`-` prefixed; the second operand then need not be prefixed (`M+20,10` = relative both) |
| `B` prefix | move without drawing |
| `N` prefix | draw, then restore the previous position |
| `C n` | colour |
| `S n` | scale, in **quarter** units (`S4` = 1:1) |
| `A n` | angle, `0..3` = 0/90/180/270° |
| `X <strvar>;` | execute a substring |
| `=<var>;` | substitute a variable's value as the argument |

Separators: spaces and TAB are skipped anywhere; a `;` **terminates** a command
(trailing `;` fine, but a *leading* `;`, a doubled `;;`, or a `,` between
commands → `ERR 5`). Lowercase command letters are accepted. Empty string = no-op.

## 2. ★ The state persists (round 1 → round 2)

Round 1's results looked incoherent until the cause showed: **`S` and `A` persist
across `DRAW` statements *and* across `RUN`s.** Every "odd" row was exactly
explained by a carried-over `S=8, A=1` from an earlier case in the same boot.

Round 2 `P1` then tried to find something that resets them: `RUN`, `NEW`,
`SCREEN 2`, `SCREEN 0`+`SCREEN 2`, `CLS`, `CLEAR`, `COLOR` — **none** reset the
state. Only a power-on does: a fresh boot measures `S=4, A=0` (`P1b`).

🔴 **`S=4` HERE IS AN INFERENCE, NOT A READING — see §3 round 5.** `P1b` observed
1:1 motion at a small count and *named* it `S4`; the never-set state produces the
identical motion there. What `P1b` actually measured is "the state is not `S8` or
`S2`", which is true and is all it can support. `A=0` survives: an explicit `A0`
and the boot default are measured to be the same state (`d.a0.32k`).

## 3. Scale + the count arithmetic (rounds 3–4)

The scale is quarter-units and *truncates*: `S1U10` → 2, `S2U10` → 5, `S3U10` → 7,
`S5U2` → 2. `S0` behaves as `S4` (verified against a pre-set `S8` and `S2`, so it
is a real reset to 4, not "leave unchanged").

Large counts wrap in a way that pins the internal arithmetic exactly. Measured
`U<n>` at `S4`: 32767 → **down 1**, 32768 → no move, 33000 → up 232, 40000 → up
7232, 65535 → down 1. All five are reproduced by one model:

> **distance = signed16( (n × S) mod 65536 ) ÷ 4**, truncating toward zero.

Round 4 falsified it on seven *fresh* pairs (`S3/S5/S7/S9/S255`, n up to 20000) —
all seven predicted exactly. The negative cases discriminate the rounding:
`S3U-10` → 7 (not 8), `S1U-2` → 0, `S3U-2` → 1 — **truncate toward zero**, not
floor. A count above 65535 (`U99999`) → `ERR 5`.

🔴 **ROUND 5 (2026-08-11, D-DSCALE) — ALL TWELVE POINTS ABOVE ARE CORRECT AND
THE MODEL DRAWN FROM THEM IS WRONG IN TWO PLACES.** Both are invisible in this
notebook's own class, and the reason is the same each time: *what the twelve
points have in common is not a property of `DRAW`, it is a property of how I
happened to sample it.*

1. **Every one of the twelve set `S` explicitly first**, so the class never
   contained the power-on state — and §2 above recorded that state as `S = 4`
   from a *fresh boot* reading (`P1b`) that could only ever have measured 1:1
   motion, which the never-set state also produces. `DRAW"BU40000"` from boot
   moves the full **40000**; `DRAW"S4BU40000"` moves **7232**. The multiply is
   the identity for every `n` where `n × S` stays inside 16 bits, so **a large
   count is the only observable that separates them**, and no row here had one
   at the default.
2. **None of the twelve produced the product `$8000`.** `S4U8192` moves **up**
   8192 on both references, where the model above predicts down 8192. So does
   `S2U16384`, `S8U4096`, `S1U32768`, `S4U24576`, `S4U-8192`. One step either
   side behaves as the model says (`S4U8191` → up 8191, `S4U8193` → down 8191),
   so the sign boundary is **`$8001`**, not `$8000`. `$8000` is the single
   16-bit value that is its own two's-complement negation — a "fit it, then
   falsify it on fresh pairs" method finds it only by landing on it exactly, and
   nineteen points across two rounds did not.

Corrected rule, and the corrections are now gated in
`make lineerr-acceptance` (`d.def*`, `d.p8.*`, `d.p7ffc`, `d.p8004`):

> **distance = n if no `S` has been executed; otherwise
> `f((n × S) mod 65536) ÷ 4`, where the product is negative iff ≥ `$8001`,
> truncating toward zero.**

See [`../docs/spec-basic-lineerr.md`](../docs/spec-basic-lineerr.md) §12.

Consequences that fall out of the model and are worth stating separately:

- a **negative** count moves in the *opposite* direction (`U-5` = down 5);
- `+` may prefix a count (`U+5`);
- `=var;` counts are coerced like any int arg: `V=10.6` → 10 (truncates), a
  negative or >255 value is fine (`Z=300` → up 300).

## 4. Angle

`A1/A2/A3` rotate 90/180/270°. It applies to **relative** motion only — the eight
direction letters and relative `M±x,±y`, including under a `B` or `N` prefix — and
**not** to absolute `M x,y` (`A1M150,60` still lands on (150,60)).

## 5. Off-screen + coordinates

Nothing off-screen errors. The position cells follow the *unclipped* coordinate
(`BM5,5U100` leaves GRPACY = −95; `BM250,100R100` leaves GRPACX = 350) exactly as
G2/G3 already do, and the drawn pixels are masked. Absolute `M` accepts operands
up to 65535 (`M65535,0` ok, GRPACX = 65535); 99999 → `ERR 5`.

`GXPOS`/`GYPOS` carry the same sorted-endpoint residue G3/G4 already documented
(they track one end of the rasterised segment, not necessarily the DRAW cursor),
and a `B` (blank) move does not touch them.

## 6. Colour — it is the SHARED graphics attribute, not a DRAW-private cell

This took three rounds because two early tests were confounded.

Measured facts: a colourless `DRAW` draws in FORCLR after a fresh `SCREEN`; `C6`
then a second `DRAW` in the same run still draws in 6; but `C6` then a colourless
`LINE` draws in **15**, and after a new `RUN` a `DRAW` was back to 15.

Rounds 5/6 read that as "C is reset by RUN / by SCREEN" — **wrong**: both of those
programs had a *colourless* `PSET` between the setter and the measurement, and a
colourless graphics statement re-stamps the shared attribute with FORCLR. Round 7
removed the intervening statement by moving with DRAW's own `BM`, and the picture
resolved:

- `LINE(100,100)-(108,100),4 : DRAW"BM100,140R8"` → the DRAW drew in **colour 4**;
- `PSET(100,100),4 : DRAW"BM100,140R8"` → likewise **4**;
- `DRAW"C6R8" : SCREEN2 : DRAW"BM100,140R8"` → still **6**; `SCREEN 2` does *not*
  re-stamp it;
- control: `DRAW"C6R8"` then a colourless `LINE` → 15 (the colourless statement
  stamps FORCLR).

So: one shared graphics-attribute cell (the published MSX work area `ATRBYT`,
`$F3F2`). Every graphics statement given an explicit colour stamps it; every
graphics statement *without* one stamps FORCLR — **except `DRAW`, which reads it
and only writes it on `C n`.** That single rule reproduces all seven observations.

(Note this is a small gap in our current engine: `basic/graphics.asm` resolves
defaults straight from `FORCLR` and keeps no `ATRBYT`. See spec §9 D-G6-3.)

## 7. `X` substrings

`X A$;` executes the named string variable's contents; execution then continues
after the `;` (`XA$;R5` does both). State set inside the substring **persists**
after it returns (`A$="S8"`, `DRAW"XA$;U10"` → moved 20). Nesting works (`A$` =
`"XB$;"`). An empty string is a no-op. Omitting the `;` → `ERR 5`.

## 8. Error surface

| case | result |
|---|---|
| unknown letter (`Z10`), bare `S`/`A`/`C`/`M`/`X` with no argument | `ERR 5` |
| `A4`, `C16`, `C-1`, `S256`, count > 65535 | `ERR 5` |
| `M100` (missing 2nd operand), `=var` without `;`, `XA$` without `;` | `ERR 5` |
| leading `;`, doubled `;;`, `,` between commands, junk char | `ERR 5` |
| `SCREEN 0` / `SCREEN 1` | `ERR 5` |
| numeric argument (`DRAW 5`) | `ERR 13` |
| off-screen motion, huge counts ≤65535, empty string, bare `B`/`N`, `S0`, `S255` | accepted |

## 9. Rasteriser identity

`PSET(20,20):DRAW"M53,37"` and `LINE(20,20)-(53,37),15` produce the **same
bitmap** (captured both, row for row). So DRAW's segments are the same line
rasteriser G3 already landed and host-fit — no second rasteriser to characterize,
and no new fit oracle needed for G6.
