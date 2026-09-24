# Where the cycles go — a PC profile, and the two dispatch fixes it bought (D-SPEEDPROF)

TIER 4 (on-par speed; TIER 5 since the 2026-09-24 swap, D-TIERSWAP). The interpreter-speed item had a measured ratio (2.5–3.8×
the CF-3300) and a refuted cause (the sub-ROM eviction: §5 of that item), but no
profile. `scratchpad/speedprof_rig.py` samples `reg PC` every 5 emulated ms
through a run, symbolises against `build/basic-reloc.sym` (code labels only —
ALL-CAPS equates are cells, not routines) and ranks by sample count.

## 1. The profile

`FOR I=1 TO 2000:NEXT`, 8 s inside the loop (1600 samples):

| share | routine | what it is |
|---|---|---|
| 20.0% | (BIOS < $2812) | `BREAKX` per statement + the ISR |
| **16.9%** | **`es_scan`** | **the statement-table walk** |
| 10.0% | `d10_lp` | `TIME`'s decimal print (the row's own readout) |
| 8.0% | `wsrc_unpack` | float unpack (the `TIME` compare) |
| 4.3% | `dtw_lp` | digit-to-word |

`FOR I=1 TO 2000:X=I*2+1:NEXT`, 35 s (7000 samples): `fpm_inner` 15.4%,
`fpm_reduce_done` 12.0%, `es_scan` **7.9%**, `digit_mul` 6.6%, `dmul_lp` 4.8% —
i.e. once real arithmetic runs, the float pack dominates and dispatch is a
sixth of what it is in a bare loop.

⚠️ **The first three profiles were of the WRONG WINDOW.** The harness types the
program during the first ~20 s of emulated time, so a window opening at 12 s
sampled the tokeniser and the REPL — `ev_ff_argtab_len` at 65% was a `db` table
being *symbolised over*, not code being run (the symboliser now ignores ALL-CAPS
names, and the window's start is a parameter). A profile whose window does not
contain the subject reports the apparatus.

## 2. Fix 1 — `es_scan`'s order (D-STMTORDER, 0 bytes)

`stmt_table` was ordered "as the pre-refactor `cp` chain ran", which put the
loader verbs first and **`NEXT` 65th of 90**; each entry costs 3 bytes of walk.
The hot twelve — `:` `NEXT` `FOR` `IF` `GOTO` `GOSUB` `RETURN` `PRINT` `ON`
`LET` `ELSE` `END` — move to the front. A pure permutation: the table is
searched by token byte, so order is free.

## 3. Fix 2 — an assignment never walks the table (D-LETFIRST, net 0 bytes)

`X=I*2+1` is the commonest statement in any program and it has **no table
entry** — it used to walk all 90 and reach the `es_noentry` fallback's
`is_letter`. `exec_stmt` already holds the statement byte in A (`skip_spaces` /
`or a` / `ret z`), and tokenised text carries identifiers upper-cased, so
`sub 'A' / cp 26 / jp c,ex_let` is the whole test; the fallback's `ld a,(hl)` +
`call is_letter` + `jp c` are gone, and `es_noentry` is now `jp stmt_error`.

🔴 **The letter test now runs BEFORE the table, so no table entry's token byte
may lie in $41..$5A.** Today none does (`COLON` $3A, `'_'` $5F, every keyword
token ≥ $80, `PEEK_PREFIX` $FF) — and `tests/test_stmt_dispatch.py` asserts it,
because a future single-letter statement byte would be silently shadowed.

## 4. Measured (jiffies, zerobas, two runs each — identical)

| row | before | after | change | CF-3300 | ratio before → after |
|---|---|---|---|---|---|
| `FOR I=1 TO 2000:NEXT` | 623 | **507** | −18.6% | 200 | 3.12× → **2.54×** |
| `I=0:FOR J=1 TO 2000:I=I+1:NEXT` | 1728 | **1415** | −18.1% | 576 | 3.00× → **2.46×** |
| `FOR I=1 TO 500:A$="AB"+"CD":NEXT` | 303 | **225** | −25.7% | — | — |
| `I=I+1:IF I<2000 THEN 10` (2000×) | 1840 | **1529** | −16.9% | — | — |

The band's floor moves from ~2.5× to ~2.0× only when the float pack is attacked
(§1's second profile says where); dispatch is done as cheaply as a linear table
allows. A jump table keyed on the token byte would cost 256 B of page 1, which
has 1 B free — not a candidate until a carve pays for it.

## 5. Not claimed

That 20% in BIOS is removable: `BREAKX` per statement is how Ctrl-STOP works and
the reference pays it too. That these two fixes change the *shape* of the
remaining gap — they do not: every row moved by roughly the same fraction, which
is what a per-statement constant predicts.
