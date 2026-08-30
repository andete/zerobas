# D-PCTTRUNC / D-VALUNDER — three defects in the float crunch, found by asking VAL's questions of the LITERAL

*2026-08-30. `sub/tkfloat.asm`. Probe `scratchpad/val_probe.py`; knives K-PT1 /
K-PT2 / K-VU1 in `scratchpad/crunch_knives.py`.*

## 0. How they were found, which is the transferable part

None of this was the job. The job was activating `tk_float` for `VAL`, and the
design needed the reference's answer to three questions VAL had never had to
have: a value past int16, a type suffix, and the overflow reject. Every one of
those rows got a **literal twin** — `PRINT 1.7%` beside `PRINT VAL("1.7%")` —
for the standing reason that a case which agrees can agree for the wrong reason
and the second cause of green has to be named
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).

🎯 **All three defects were in the twins.** VAL's own rows were *accidentally
right* — its integer-only parser stops at the dot, so `VAL("1.7%")` answered 1
for a reason that had nothing to do with `%`. The crunch, which every program
line goes through, answered **17**.

That is also why they had to be fixed first: routing VAL through `tk_float`
would have imported all three as regressions.

## 1. D-PCTTRUNC — `%` concatenated the fraction instead of truncating it

| literal | vg8020 | cf3300 | zerobas (before) |
|---|---|---|---|
| `1.7%`     | 1 | 1 | **17** |
| `1.9%`     | 1 | 1 | **19** |
| `2.5%`     | 2 | 2 | **25** |
| `0.7%`     | 0 | 0 | **7** |
| `.5%`      | 0 | 0 | **5** |
| `40000.5%` | `Overflow` | `Overflow` | **-25536** |
| `0%`       | 0 | 0 | 0 |

Five silent wrong answers and one silent **wrap**, on a suffix that had no row.

**The cause.** `TKDCOUNT` counts every *significant* digit, fraction included,
and `tkf_int_value` reads `TKDCOUNT` of them as though they were all in front of
the dot. The classification then ranged-checked the concatenation, so
`40000.5%`'s six digits took the `D>5` arm and, for `VAL`, wrapped.

**The fix.** The integer part is `TKDIG[0 .. TKINTLEN-TKNZPOS-1]`: `TKINTLEN` is
how many characters the integer part had, `TKNZPOS` how many of them were
skipped leading zeros, so the difference is how many *stored* digits belong in
front of the dot. Write that back into `TKDCOUNT` and every downstream step —
the `cp 5` classification, `tkf_cmp32767`, `tkf_int_value` — is already right,
including the range check now running on the **truncated** value, which is what
turns `40000.5%` from a wrap into `Overflow`.

⚠️ **Two clamps, and each has a row — but only after the knife said so.** The
difference can go negative, and `0%` has `TKINTLEN=1` with **nothing stored at
all** (reading one digit there would have read uninitialised `TKDIG`), so the
count is also clamped to `TKDCOUNT`.

🔴 **K-PT2 PREDICTED TWO ROWS AND MOVED ZERO, AND THE CODE WAS RIGHT — THE ROWS
WERE NOT.** I cut the negative clamp expecting `.5%` and `0.7%` to redden. They
cannot: **`TKPOS` counts DIGITS and the dot does not advance it**, so `.5` is
`TKINTLEN=0` / `TKNZPOS=0` and `0.7` is `1` / `1` — a difference of **zero**, not
a negative. `TKNZPOS` only passes `TKINTLEN` when the **fraction** carries its
own leading zeros. `0.07%` and `.007%` do that, and with the clamp cut they read
7 instead of 0. The arm found a hole in the row set, which is what an arm is
for — [[a-coverage-row-whose-geometry-cannot-reach-the-case]] in the shape where
the geometry was mine, not the gate's.

🟢 Overwriting `TKDCOUNT` is safe **on this path only**: nothing after the
percent arm reads the original, and `tkf_cmp32767` walks `TKDIG[0..4]` without
it.

## 2. D-VALUNDER — `1E-66` is an Overflow, not a silent zero

The file's own header said *"dec_exp<=-64 -> TKLEAD=0 … the `1e-65` case: reads
as value 0, no error"*. That row is real. It is also the **last** one that is:

| literal | dec_exp | vg8020 / cf3300 | zerobas (before) |
|---|---|---|---|
| `1E-64` | -63 | `1E-64` | `1E-64` |
| `1E-65` | -64 | 0 | 0 |
| `1E-66` … `1E-70`, `1E-99` | <= -65 | **`Overflow`** | **0** |

Six silent zeros where the reference stops the line.

🎯 **The boundary was already being computed, and the arm below it was doing
nothing.** `dec_exp == -64` reaches `tcr_leadok`, whose `+64` makes `TKLEAD` 0
on its own — so the "forced lead 0" arm produced an answer the normal path
produced anyway, and cost 5 bytes to say so. Everything **below** -64 is the
reject. Net **-4 bytes**, six rows fixed.

⚠️ The boundary was pinned by rows, not reasoned: `-64` and `-65` were measured
green before `-66`…`-70` were even asked for, precisely because the header cited
`1e-65` and the header was half right.

## 3. 🔴 `tcr_ovf` — an outward jump one frame deeper than its landing site

`tkf_overflow`'s first act is `pop de`, and what it means to pop is the TOKBUF
destination `tk_float` pushed **at entry**. Reached by `jp` from the
classification chain, that is true. Reached from inside `tkf_calc_and_round` — a
`call` — the top of the stack is that routine's own return address instead, so
`DE` came back as a code address and one word was left on the stack.

[[factoring-a-run-into-a-helper]]: *a `call` moves an outward jump one frame
deeper.* This is the same fault, in a routine written long before that rule.

**It was invisible, and D-VALUNDER is what makes it matter.** In tokenise mode
the leaked word is absorbed by the error path's stack reset, and the wrong `DE`
only mis-sites a `0` terminator on a line being rejected anyway — which is why
`1E99` has always *looked* right. The fix is `inc sp` / `inc sp` before the jump.

⚠️ **THERE IS NO ARM FOR IT IN THIS RUNNER, AND THAT IS SAID OUT LOUD.** Cutting
it moves zero rows today; a designed no-op reporting "moved 0" is exactly what
D-POPRAISE mistook for an arm. Its witness is **VAL mode**, where `tkf_rej` ends
in `ret` and that `ret` would go to the destination pointer. The arm lands with
the VAL activation. [[a-guard-witnessed-only-by-a-deferred-error]]

## 4. Verification

`scratchpad/val_probe.py` — 93 rows over a VG-8020, a CF-3300 and zerobas.
Eleven rows moved to SAME here (five `%`, six exponent), with `0%`, `12%`,
`0.07%` and `.007%` as the non-moving controls — the last two accidentally right
before the fix and still right after it, which is what makes them controls for
the clamp rather than for the truncation. Knife predictions and the measured sets are in
`scratchpad/crunch_knives.py`; the full battery is `make gates` (under
`caffeinate`, D-NOSLEEP — the battery now holds its own assertion).
