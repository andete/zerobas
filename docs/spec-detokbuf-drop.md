<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-DETOKBUF — drop the 1280 B render buffer

**Status:** SPEC, 2026-09-25. **Tier:** 4 (RAM usage, goal (a) free memory).
**Ruled by Joost, 2026-09-25:** *"Drop DETOKBUF"* — the recommended lever of the
6030 B scout (TODO §"COMPARE RAM *USAGE*", `scratchpad/ramlayout_probe.py`).

## 0. What it buys

`DETOKBUF` is `$DB00..$DFFF`, 1280 B, between zerobas's text ceiling
(`TXTMAX` = `$DB00`) and its `$E000` workspace. It is the ONLY block there, so
removing it lets `TXTMAX` rise to `$E000`: **+1280 B of `FRE(0)` on both
builds.** Against the CF-3300 the disk build then leads by ~635 B; against the
diskless VG-8020 the gap falls from 6030 B to ~4750 B. `HIMEM` follows, because
the cold boot stores `TXTMAX` into it (D-HIMEMLIE).

## 1. Why the buffer exists

Five users write it, all from SUB-ROM tenants, and the resident side drains it:

| user | tenant | worst-case bytes | re-runnable? |
|---|---|---|---|
| `LIST` / ASCII `SAVE` | `dtk_tenant` (sub/detok.asm) renders ONE line | 1271 (254 × `?` → `PRINT`, spec-basic-linemax) | yes — pure over the line + `NUMBUF` |
| `KEY LIST` | `keystr_tenant` op `ks_list` | ~200 (ten lines) | yes — reads the key table only |
| `PRINT USING` literals | `pu_tofield_tenant`, `pu_tail_tenant` | 32 (`PU_FMTMAX`) | **NO** — `pu_to_field` advances `PU_POS` |
| `PRINT USING` numeric field | `pu_emit_tenant` | field width + sign/`$`/`%`, < 40 | no |
| the string collector's sort array | `strheap_gc` phase C | 2N ≤ 512 (N ≤ 256 roots) | n/a (scratch) |

A tenant cannot print directly: `pchar` lives in main page 1 and reaches `CHPUT`
in BIOS page 0, and under any tenant one of the two is switched out. So a
buffer is the only sink a tenant has — but it need not be 1280 B.

## 2. The design

### 2.1 One 96 B window (`DB_WIN`), rendered windowed

The shared sub-side `pchar` (sub/detok.asm, used by all four renderers) gains a
**skip count** and a **more flag**:

* it counts rendered bytes; bytes before `DB_SKIP` are discarded, bytes that
  fit in `[DB_WIN, DB_WIN+96)` are stored, and a byte beyond the window sets
  `DB_MORE` instead of being stored;
* the resident drain loops: `skip = 0`; call the tenant; drain the window; while
  `DB_MORE`, `skip += 96` and call again.

Only a RE-RUNNABLE renderer may take a second window — `LIST` and `KEY LIST`
are. The `PRINT USING` tenants are not, and their worst case (< 40 B) is below
one window, so they never take a second: a pasmo assert pins `PU_FMTMAX` and
the numeric field bound below the window, and the drain for those three stays a
single call.

**Cost in time — AS BUILT, NOT AS FIRST DESIGNED.** Re-rendering from the line's
start per window (the design above) measured >8 s of emulated time for the
250 × `?` line against the VG-8020's <1 s. So a LIST render RESUMES AT A TOKEN:
detok's main loop is stateless between tokens, `dt_lp` marks each token start
(`DT_TOK`), `pchar` counts that token's output (`DT_TOKN`), and on overflow it
records the resume point and aborts the render (SP back to `DB_SP`); the
resident loop restarts at that token, skipping only its drained bytes. Linear:
the same line lists in 1.5–2.5 s emulated. `KEY LIST` (~200 B, pure) keeps the
cheap skip-from-start re-run.

**Home:** `$E381..$E3E0` — the 96 B `TEMPPOOL` left when the temp pool moved to
the published `TEMPST` (D-ADDR29, 2026-09-25). Verified free with
`tools/ram_map.py`, not assumed.

### 2.2 The collector sorts in the string pool's own free gap

Phase C needs 2N bytes for N ≤ 256 roots. The string pool's free gap
`[floor, FRETOP)` is idle during a collection — compaction moves bodies UP from
`FRETOP` toward the ceiling and never writes below `FRETOP`. So the sort array
goes at `floor` when `2N ≤ FRETOP − floor`; otherwise the existing no-buffer
`gc_slow` (O(n²), already the path for N > 256) runs.

⚠️ NOT the variable free area below the control pool: since D-SPMERGE the Z80
stack lives in it.

⚠️ A collection triggered by "out of string space" is exactly when the gap is
smallest, so near-full pools will take `gc_slow` more often. Measure: a
many-strings program at a tight `CLEAR` on both machines, before and after.

### 2.3 Then `TXTMAX` rises

With no user left, `DETOKBUF` goes and `TXTMAX` becomes `$E000`. Every reader of
`TXTMAX` is symbolic; `HIMEM` follows through D-HIMEMLIE's boot store.

## 3. Slices

1. ✅ **S1 — the window. SHIPPED 2026-09-25** (15/15 smoke rows; the first cut
   clobbered `dtk_tenant`'s HL in `db_begin` and rendered every line blank). `DB_WIN` at `$E381` (96 B), `DB_SKIP`/`DB_MORE`, the
   windowed `pchar`, the resident loops for `LIST` and `KEY LIST`, the
   `PRINT USING` single-window assert. `DETOKBUF` still exists but no renderer
   writes it. Rows: LIST of an ordinary line, of a 254 × `?` line, and ASCII
   SAVE of it (byte-identical file), `KEY LIST`, `PRINT USING` — all against
   the reference; the existing lnblank/pusing/keystr/castail suites.
2. ✅ **S2 — the collector. SHIPPED 2026-09-26, and NOT as designed above:** the
   sort array went to the VARIABLE free area under the live SP (usually KBs),
   not the string pool's gap (smallest exactly when a collection runs). The
   N ≤ 256 cap went with DETOKBUF; `scratchpad/gcspeed_probe.py`: 1.48× / 0.42×
   the reference's time at 150 / 300 roots. The original plan: Sort array in `[floor, FRETOP)`, `gc_slow` otherwise.
   Rows: the GC-stress rows already in the battery, plus a tight-`CLEAR`
   many-strings row timed on both machines.
3. **S3 — the ceiling.** Delete `DETOKBUF`, `TXTMAX` = `$E000`. Re-run
   `scratchpad/fremem_probe.py` and `scratchpad/ramlayout_probe.py`: every
   `FRE(0)` +1280, economy still identical.
