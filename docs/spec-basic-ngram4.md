# D-NGRAM4 — one `shx_tail` for four sub-ROM string-op result tails

*2026-08-28. `basic/str-engine.asm`. Probe `scratchpad/ngram4_probe.py`, arms
`scratchpad/ngram4_knives.py`.*

**Cost: −24 B of the page-0 low region (70 → 94 B free).** Page 1 unchanged.
**Rows: 13, DIFF 0/13** against both references.

## 1. The shape

Four verbs ended with the identical 10 B run:

    call call_strheap / call shx_finish / pop hl / jp str_eval_ok

`str_fn_chr` (CHR$), `str_fn_radix` (HEX$/OCT$/BIN$), `str_fn_space` (SPACE$)
and `sfg_close` (STRING$). 🎯 **Three of the four set `SH_OP` immediately
before**, so `shx_op_tail` is a 3 B second *entry* rather than a second body —
the same shape D-NGRAM3 found at the lineedit sites. 49 B of sites becomes a
13 B body plus four 3 B jumps.

The fourth (`sfg_close`) guards its cursor with `push ix` and pops it into `HL`;
the tail is byte-identical, the prologue is not, so it enters at `shx_tail`
with `SH_OP` already set.

## 2. 🔴 I NAMED THE SITES FROM NEARBY PROSE, AND ONE OF THEM WENT UNWITNESSED

The sweep reports **line numbers**. I read each verb off the surrounding
comments and wrote *"SPACE$ (:733)"*. **`:733` is CHR$.** SPACE$ is 579 lines
further down.

The row set therefore looked complete — one row per site, four sites — while
**CHR$ had no row at all** and `s.space` was covering a site it never reaches.

🎯 **THE KNIFE IS WHAT SAID SO, AND ONLY BECAUSE ITS PREDICTION WAS SPECIFIC.**
K-N4B (drop the `SH_OP` store from the second entry) should move exactly the
rows whose sites enter *there*. It moved **five**: SPACE$ ×2 and the three radix
rows — and none of them was the row I believed covered `:733`. A knife predicted
only as *"some rows will move"* would have passed and taught nothing.

With CHR$ rows added: K-N4A moves all **10** subject rows; K-N4B moves exactly
**7** (CHR$ ×2, radix ×3, SPACE$ ×2) and the three STRING$ rows hold, which is
the discriminating prediction confirmed.

**Name a site from its ENCLOSING LABEL, never from the prose beside it.**
[[a-shared-tail-is-not-a-decision]]

## 3. Falsification

| arm | requires | measured |
|---|---|---|
| **S1** (static) | 1 open-coded run left — the body itself — and exactly 4 jumps to it | ✅ |
| K-N4A | retarget the body → every subject row moves | 10/10, controls held |
| K-N4B | drop the second entry's `SH_OP` store → only the 3 sites entering there move | exactly 7 rows; STRING$ ×3 held |

S1 is the per-site witness and is static for the reason D-NGRAM3 established: a
site left open-coded behaves identically at runtime. Every plant is hashed
around the build (D-KNIFEROM), so an inert cut cannot read as *"moved 0 rows"*.

## 4. An apparatus collision worth remembering

A row written as `"["+SPACE$(3)+"]"` came back as **`[`** on all three sides —
consistent, and meaningless. `basic_probe_deffn`'s `face()` reads the first
bracketed span, so **a literal `[` in a row collides with the harness's own
result fence.** The row now reads `ASC(SPACE$(1))` → `32`, which shows the byte
rather than a delimiter that the instrument eats.
