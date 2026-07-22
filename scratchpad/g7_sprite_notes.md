# G7 sprites — characterization notes (VG-8020 black box)

Probes: `g7_sprite_char1.py` (tokens / `SPRITE$` writes / attribute writes /
errors), `char2.py` (16×16 mode, attribute edges, table state, `RG1SAV`),
`char3.py` (omitted-arg defaults isolated, EC sweep, domains, coercion),
`char4.py` (residuals). All read-only, no ROM disassembly.

## Tokens (C1) — PIN
```
SPRITE            $C7          ($ is separate ASCII $24)
SPRITE$(0)="ab"   C7 24 28 11 29 EF 22 61 62 22
A$=SPRITE$(0)     41 24 EF C7 24 28 11 29        (same token as a factor)
PUT SPRITE …      B3 20 C7 20 …                  (PUT $B3 + space + SPRITE $C7 + space)
PUT SPRITE 0,STEP(10,20),4,1  → … 11 2C DC 28 …  (STEP $DC after the comma)
SPRITE ON/OFF/STOP  C7 20 95 / C7 20 EB / C7 20 90
ON SPRITE GOSUB n   95 20 C7 20 8D 20 …
```

## `SPRITE$(n) = <string>` (C2, D1, F) — PIN
- Writes the sprite **pattern generator table at `$3800`**, entry `n`.
- **Size follows the SCREEN sprite-size argument**: `SCREEN 2,0` / `2,1` are
  8×8 ⇒ **8 bytes** per entry (`$3800+8n`); `SCREEN 2,2` / `2,3` are 16×16 ⇒
  **32 bytes** (`$3800+32n`). (Round 1's "16×16" cases used `,1` — which is
  8×8 *magnified* — and that is why they read as 8-byte.)
- Shorter string ⇒ **zero-padded** to the entry size; longer ⇒ **truncated**;
  `""` ⇒ all-zero entry. No error either way.
- `n` domain **0..255 in every size**, `ERR 5` outside (both read and write).
  In 16×16 mode `n` is NOT clamped to 63: `SPRITE$(255)` writes at
  `($3800+255*32) & $3FFF = $17E0` — a plain **VRAM address wrap** (F4).
- Read-back `A$=SPRITE$(n)` returns **exactly 8 / 32 bytes** (the entry size)
  — never the length that was assigned.
- Write in `SCREEN 0` ⇒ **ERR 5**; write in `SCREEN 1` works ($3800).
  **Read is legal in every mode incl. SCREEN 0** (asymmetric — F5).
- `SPRITE$(0)=5` ⇒ **ERR 13** (type mismatch). `MID$(SPRITE$(0),1,1)="A"` ⇒ ERR 2.
- `n` is an ordinary numeric expression, **truncated** (`SPRITE$(1.9)` ⇒ entry 1).

## `PUT SPRITE p,(x,y),c,n` (C3, D2, E1, E2, E4) — PIN
Attribute table `$1B00`, 4 bytes per plane: **`y, x, pattern, colour`**.

- `p` = plane **0..31**, else ERR 5. Entry address `$1B00 + 4p`.
- `y`, `x` stored as the **low byte of the int16** — `256→0`, `300→44`,
  `32767→255`; **no clipping and no error** (only `>int16` ⇒ ERR 6).
- **Negative x ⇒ the early-clock rule**: `attr_x = (x+32) & 255` and the
  colour byte gets **bit 7 ($80)** set. Verified over a sweep
  (−64→224, −33→255, −32→0, −1→31, all with colour byte `$80|c`).
  `x ≥ 0` ⇒ EC bit **cleared** (F1), including when the colour arg is omitted.
- `c` domain 0..15 (ERR 5 outside). Stored in the colour byte's low nibble.
- Pattern number `n`: **8×8 ⇒ stored as-is, domain 0..255**; **16×16 ⇒ stored
  as `4n`, domain 0..63** (`n=1`→4, `n=2`→8, `n=63`→252; `n=64` ⇒ ERR 5).
- **Omitted argument = keep the byte already in the attribute entry** (E1,
  boot-per-case): omitted colour keeps the entry's colour (then re-applies EC
  from the sign of x); omitted pattern keeps the entry's pattern byte; the
  whole `PUT SPRITE p,,c,n` form keeps **both** y and x (it does NOT use
  `GRPAC` — a `PSET` before it changes nothing).
- `STEP(dx,dy)` is relative to `GRPAC` (`PUT SPRITE 0,(50,60),…:PUT SPRITE
  0,STEP(5,5),…` ⇒ (55,65)).
- **Work area:** a coordinate-carrying `PUT SPRITE` sets `GRPACX/Y` **and**
  `GXPOS/GYPOS` to the raw (unwrapped, still-negative) coordinate — same as the
  other graphics statements. The omitted-coordinate form leaves them alone.
- Float args **truncate toward zero** (`(10.7,20.2),4.9,1.9` ⇒ 10,20,4,1;
  `-5.7` ⇒ −5 ⇒ attr x 27 + EC).
- `SCREEN 0` ⇒ ERR 5; `SCREEN 1` works (attribute table also `$1B00`).
- `PUT SPRITE 0` (no coords, no comma) ⇒ ERR 2. `(,20)` / `(10,)` ⇒ ERR 2.
- Needs **no `SPRITE ON`**; `SPRITE ON/OFF/STOP` are accepted and change nothing
  observable here (they belong to the interrupt-trap surface).

## Mode/init state (D5, D5b, F) — PIN
- `SCREEN 2` (or `SCREEN 1`) initialises **all 32 attribute entries** to
  `y=209`, `pattern = plane index`, `colour = FORCLR` (measured: `COLOR 4,1,1:
  SCREEN2` ⇒ colour byte 4) — and **leaves the x byte untouched** (a stale x
  from before the mode set survives).
- `y=209` is the "hide all following planes" value; that is the idle state.
- **`CLS` touches neither table.** A re-`SCREEN 2` re-runs the attribute init
  but **leaves the pattern table intact**.
- The sprite-size argument lives in **`RG1SAV $F3E0` bits 1..0** (`SCREEN 2,0`
  ⇒ $F0, `,1` ⇒ $F1, `,2` ⇒ $F2, `,3` ⇒ $F3) and **PERSISTS across later
  `SCREEN` statements that omit it** — `SCREEN2,2:SCREEN2` stays $F2, and it
  survives `SCREEN 0`/`SCREEN 1` too. (Same shape as DRAW's S/A persistence.)
- Our `ex_screen` currently **evaluates and discards** the sprite-size argument
  ([basic/screen.asm:60](../basic/screen.asm:60)) — G7 must make it real,
  because it selects the pattern-entry size and the pattern-number scaling.

## Open / deliberately not characterised
- `SPRITE ON/OFF/STOP` + `ON SPRITE GOSUB` semantics (collision trap) — that is
  the **interrupt-trap** TODO item, not G7. G7 only needs the keyword to exist
  and the three forms to parse without error.
- Sprite *display* (collision flag, 4-per-line, 5th-sprite status bits) is VDP
  behaviour we inherit from the hardware, not BASIC behaviour to reimplement.
