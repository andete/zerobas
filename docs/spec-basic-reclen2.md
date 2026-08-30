# D-RECLEN2 — the out-of-range `LEN=` face is `Illegal function call`; the DOMAIN widening was tried and REVERTED

*2026-08-30. `basic/files.asm`. Probe `scratchpad/reclen2_probe.py` (12 rows),
knife `scratchpad/reclen2_knives.py`. **Ships the face only.***

## 1. What shipped

`oo_parse_reclen`'s reject raised **`Syntax error`**. The CF-3300 answers
**`Illegal function call`**:

| row | CF-3300 | zerobas before | after |
|---|---|---|---|
| `LEN=0` · `257` · `512` | `Illegal function call` | `Syntax error` | **`Illegal function call`** |

Three rows closed. K-RL2 moves **5 / 5** — every row that reaches the reject,
which includes the two non-tiling lengths still rejected for the reason in §2.

## 2. 🔴 What did NOT ship, and why — the interesting half

The same slice tried to widen the domain to any 1..256, because
[`spec-basic-put3.md`](spec-basic-put3.md) §2 had measured the **reference**
round-tripping a straddling record. **It was reverted. zerobas cannot straddle.**

`fat_rand_put`'s overlay is an `ldir` into `FWBUF + GP_WITHIN` for `GP_RECLEN`
bytes. Record 6 at `r=100` has `within = 500`, so it writes **88 bytes past the
512-byte sector buffer**. Measured: two `PUT`s at `LEN=100` including record 6
kill the program; the **same shape at `LEN=128` is fine**; and one `PUT` to
record 5 (`within=400`, no straddle) is fine.

**D-RECLEN's original caution was right and my refutation of it was wrong.** It
said the straddle argument is a real design constraint and *"just widen the
validator" is exactly the cheap wrong answer*. The reference not needing the
constraint does not mean this engine does not.

## 3. 🔴 The probe that "proved" it safe was blind TWICE

The emulator rows said a straddling record round-tripped. Both reasons they were
wrong are worth keeping:

1. **A round trip cannot see a wrong offset.** `PUT` and `GET` share
   `frnd_calc`, so they agree on the same wrong address and the record reads back
   perfectly while the on-disk layout is wrong.
2. **The record never straddled.** `mul_reclen` is a **shift loop** — `HL *
   2^floor(log2 r)` — so at `r=100` it computed `*64`, putting record 6 at
   `within=320`, comfortably inside the sector. The probe was not testing the
   case it was named for.
   [[a-coverage-row-whose-geometry-cannot-reach-the-case]]

🟢 **`tests/test_open_len.py` is what caught it**, because it checks `frnd_calc`
against an **independently derived** offset — `record N is [(N-1)r, Nr)` — rather
than against the ROM's own output. A host test with its own oracle saw in one run
what the emulator rows could not see at all.

⚠️ And the adjacency row now in the probe is the emulator-side version of the
same idea: at the correct stride records 5 and 6 do not touch, at `*64` they
**overlap**, so record 6's write corrupts record 5.

## 4. What widening would actually take

1. `mul_reclen` must **multiply** (shift-add, ~9 B more than the shift loop —
   written and measured working, then reverted with the rest).
2. `fat_rand_put` / `fat_rand_get` must span **two sectors** when
   `within + reclen > 512`.

Until both exist, the power-of-two rule stays and `LEN=100` / `LEN=255` remain
divergent — now with an `Illegal function call` face rather than `Syntax error`.

⚠️ **ONE REFERENCE:** Disk BASIC; a diskless VG-8020 cannot express these rows.
