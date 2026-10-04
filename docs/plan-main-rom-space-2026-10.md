<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Main-ROM space: the plan from the 2026-10-03/04 hunt

Status: **📋 PLAN, not started.** Nothing below is committed. Every byte figure
is a `make basic-reloc` wall reading taken in a git worktree on `4306a5a0` /
`fab3f01d`, **one candidate at a time**. None is a stacked total, and none has
been through the emulator.

Starting point (2026-10-03): main LOW **1 B**, main PAGE 1 **1 B**, sub p0
18 B, sub p1 205 B, disk ~5.4 KB (largest hole ~1.5 KB).

## 0. Where this comes from

A multi-agent hunt ran in four steps:
- **Readers.** 8 readers covered regions, structure, tables, shared bodies and
  placement.
- **Builds.** 24 candidates were each built and measured in their own
  worktree.
- **Refuters.** Each measured candidate got a refuter working three lenses:
  correctness, faithfulness and apparatus.
- **Cap.** 50 lower-ranked candidates were never built (below the cap).

The diffs are still in `.claude/worktrees/wf_d5394b86-4e4-<n>` (table below).
Each slice starts from that patch, not from a description.

**What the hunt changed about the picture.** The standing routes were spent:
- `jr_mapper` found 0 sites.
- The dup-span route was exhausted.
- Page-0 eviction of verbs was closed.

Two sources nobody had worked were not spent:
- **C-BIOS's own padding and dead bytes below `$2812`.** About 260 B of zero
  runs lie between and around the two islands the merge already fills, plus
  dead strings.
- **Ordinary carving the earlier sweeps could not see**: shared tails,
  `jr cc,<ret>` → `ret cc`, a dense dispatch table, tenant stubs with an
  inline index, and main twins of shared bodies.

## 1. The candidates, measured and reviewed

`main B` = (low + page 1) after − before. `sub p1` = its own cost there.

| id | main B | sub p1 | worktree | review | what |
|---|---|---|---|---|---|
| C3 | 173 | 0 | 13 | stands | delete C-BIOS `str_nocart` (143 B) + `str_basic` (30 B); lower `BASIC_ORG` by `$AD` |
| ISL-1 | 175 | 0 | 12 | stands | 13 low-region leaf routines into islands 1/2 |
| C1 | 174 | 0 | 11 | stands | other low-region leaves into islands 1/2 |
| DT-3 | 124 | 0 | 14 (7) | stands, high | 11 read-only data blocks into islands 1/2 (+5 B `rn_in` dedup) |
| DT-2 | 63 | 0 | 21 | stands | `fperr_to_err` + one more table into islands 1/2 |
| C2-GAP1 | 53 | 0 | 19 | stands | islands 3/4 in C-BIOS gap 1 (`$09D9..`, `$0CC9..`), boot-only code |
| C2 | 50 | 0 | 22 | stands | island 3 only, `ex_let_arr` |
| DT-1 | 82 | 0 | 18 | **refuted as written** | dense statement table indexed by token−`$81`; `kwknife.py` must change with it |
| C8 | 73 | 0 | 15 | **refuted as written** | `flt_fmt` over `widen_fac_to`; breaks `ram-map-check`, false prose |
| C4 | 68 | 0 | 26 | stands | shared-tail merges, 11 files |
| SBH-3 | 52 | −24 | 23 | stands | drop main's twin of the `fat_io_create` chain; sub/disk copies serve it |
| C6-FORMAT | 48 | 0 | 16 | stands | FORMAT menu to disk.rom (disk-only behaviour) |
| GA-CROSS-ROMSCAN | 41 | 0 | 28 | stands, **high** | 23 exact equivalences: `ret cc`, inversions, tail `jp`; every hot path faster |
| B4 | 32 | 0 | 25 | stands | 11 merges, graphics/screen |
| GA-VERBRUN | 30 | 0 | 27 | stands | 4 disk.rom verbs stop reloading `DISKOP_STATUS`; chan_gate's A becomes the contract |
| B1 | 29 | 0 | 29 | stands | tenant stub `call` + inline index, 19 page-1 sites (26 low sites untouched) |
| C6 | 26 | **+47** | 9 | **refuted as written** | sample of eviction step 13; DSKI$/DSKO$ return under DI |
| GA-LHSTYP2 | 19 | 0 | 32 | stands, **high** | `push_lhs_frame` absorbs `set_factyp_int_ret` (6 sites) |
| DT-6 | 5 | 0 | 31 | stands | retire the message-escape decoder |
| C5-LOW | 80 | **−102** | 17 | stands | 4 low-region error strings into the errmsg tenant |
| SBH-1 | 77 | **−79** | 20 (8) | stands | APPEND's walk evicted to a sub tenant |
| C5 | 37 | 0 | 24 | stands | a **published-contract SYNCHR** at `rst $08`, used at our 12 `skip_comma`+`jp nz,stmt_error` sites (contract check pending, §3) |
| SBH-10 | 17 | −7 | 30 | **refuted, drop** | splits a tape header block across a slot crossing (D-CASCOMP timing) |
| C7 (S10) | — | — | 10 | not buildable | the S10 disk-channel programme; not a carve |

## 2. Conflicts: what cannot be added up

- **Islands 1/2 hold ~183 B** (124 B in island 2 before `$0200`, 59 B in
  island 1 before `$1BBF`). DT-3, DT-2, ISL-1 and C1 all spend that same space.
  **Choice: DT-3 + DT-2 (187 B, data only, one reader each, the lowest risk).**
  That fills both islands. ISL-1 and C1 then have no room, except the 4–8 B
  left over.
- **Gap-1 holds 77 B** (21 B + 56 B). C2 and C2-GAP1 both spend it.
  **Choice: C2-GAP1 (53 B).** It is boot-only code, with no hot path; C2 moves
  the `A(i)=` path.
- **RST `$08`** belongs to SYNCHR. C5 implements that published contract;
  R1 (a tenant dispatcher) would replace it and is rejected (§4).
- So **B1** (`call` + inline index, no vector) is the tenant-stub route.
- **C4 / B4 / GA-CROSS-ROMSCAN** can touch the same tails. Rebase each on the
  last one and re-measure; expect a few bytes of overlap.
- **Sub p1 is 205 B.** C5-LOW (−102), SBH-1 (−79) and SBH-3 (−24) would take
  all of it. Do SBH-3 and defer the other two until eviction step 13 frees the
  disk-only sub tenants (C6, fixed, is that step's first sample: +47).

## 3. The plan: slices in order

**Every slice follows the same procedure:**
1. Cherry-pick the worktree patch onto HEAD.
2. Rebuild.
3. Compare the walls with the single-candidate reading, and record any overlap.
4. Run the loop pipeline (gates-fast, knife pin `--all`/`--allfn`, citations,
   tiers-md).
5. Run the **FULL** battery plus the suites the refuter named. It is always
   `nodisk-acceptance` and `switch-build-check`, plus the five excluded suites.
6. Commit with the regenerated `sub/` and `disk/basic-resident-abi.inc` and the
   `zerobas-main-eu.ips/.bps` pair.
7. Fix the prose the move falsified.
8. Commit and push.

Predict each wall before building it, and score the prediction.

### Phase A: C-BIOS capacity (no ruling, ~413 B)

| # | slice | main B | slice-specific conditions (from the refuter) |
|---|---|---|---|
| A1 | **C3** dead C-BIOS strings, lower `BASIC_ORG` | 173 | Sweep the base literal in `probes/disk/bas_tokenise.py:53` (and teach `check_wall_literals` the alias). Run `make repack-boot` (cold boot + `PRINT 12+34`) and `make patches` / `patch-freshness-check`. |
| A2 | **DT-3** data into islands | 124 | Watch the rows: Break in N, RENUM, FORMAT menu, LOG, the `$FF` function arg table. Watch that island data is invisible to a page-0 tenant (none reads it today: assert that). |
| A3 | **DT-2** error tables into islands | 63 | Run `switch-build-check` (CLEARPOOL=0). Any ERROR n / FPERR raise row. |
| A4 | **C2-GAP1** islands 3/4 | 53 | `tools/build_mainrom.py` must REFUSE `tape_end > $0CC9` and island-4 top > `TAPE_BODY_LO`; the non-zero-overlap check alone misses zero bytes. Record that it takes C-BIOS's "wrong jumper" NOP slide at `$0CC9–$0CF1`. Fix `keytrap.asm:51`, `main.asm:251-253`, `rom-region-structure-review.md:59`, TODO lever-B note. |

After phase A: about **413 B** free (page 1 + low combined).

### Phase B: carves, no ruling (~330 B)

| # | slice | main B | conditions |
|---|---|---|---|
| B-1 | **GA-CROSS-ROMSCAN** | 41 | Battery; the PRINT/CRLF hot path rows; `scratchpad/playop_knife` re-check. |
| B-2 | **GA-LHSTYP2** | 19 | The FOR/NEXT rows plus the five excluded suites (shared evaluator). |
| B-3 | **C4** tails | 68 | Fix the `inm_ok` comment (it is FRE, not the VAL family) and `sc_call`'s docstring count. |
| B-4 | **B4** graphics/screen merges | 32 | `test_traps.py`, `test_screen.py`; re-run `jr_mapper` (it opens 2 sites). |
| B-5 | **GA-VERBRUN** | 30 | diskbasic + nodisk (KILL/NAME/COPY/FILES/LFILES); document A = DISKOP_STATUS on chan_gate's claimed exit as a contract in its header. |
| B-6 | **DT-1** dense dispatch | 82 | **In the same commit**, fix `scratchpad/kwknife.py` `plant()` (offset `stmt_table + 2*(tok-$81)`) and `enumerate_targets()` (88 rows, skip `stmt_error`). A build-time row count assert. kwtime on the dispatch path. |
| B-7 | **C6-FORMAT** to disk.rom | 48 | `ram-map-doc`; the FORMAT probes on both geometries; nodisk (FORMAT must still be refused there); `hook-equate-check`. |
| B-8 | **SBH-3** fat_io_create twin | 52 | diskbasic OPEN/PRINT#/CLOSE, ASCII SAVE, D-DISKFULL faces, bdos, fat-error. Costs 24 B of sub p1. |
| B-9 | **DT-6** escape decoder | 5 | Fix `probes/lib/errmsg_alphabet.py`'s `MSGESC_SUB` parse; `test_msgenc.py`. |
| B-10 | **C8** `flt_fmt`, after its fix | 73 | Keep the `(1)` width comment at end-of-line (`ram_map.py` PARENN); rewrite the C8 prose; kwtime on PRINT of floats (it adds a widen call). |
| B-11 | **B1** inline-index stubs | 29+ | The tenant-stub route (R1 is rejected). Extend it to the 26 low-region sites. A site missing its `db` is invisible to every gate: add a static check. |
| B-12 | **C5** SYNCHR at `rst $08` | 37 | FIRST check the implementation against the PUBLISHED SYNCHR contract (MSX2 Technical Handbook / BIOS documentation, never a ROM): `(HL)` compared with the byte after the `rst`, Syntax error on a mismatch, then CHRGTR. C5 runs `skip_spaces` before the compare. If that differs from the published entry state, make it match or drop the slice. kwtime caveat: kwtime's marks are POKEs. |

After phase B: about **740 B**, before overlaps.

### Phase C: sub-ROM capacity (needs eviction step 13 first)

- C-1 **C6** (sample of step 13), after its fix (`ei` after chan_gate in
  `dsk_core`, 1 B low): it frees sub p1 +47.
- C-2 then **SBH-1** (77 B; record or fix the pending-DSKIO-after-APPEND
  difference, ~3 B sub; fix `fiawalked-body.inc:10`, `fatprim.asm:74`,
  `spec-eviction-g7-space.md` §4, `spec-basic-append-missing-refuse.md` F1,
  TODO.md:5028).
- C-3 **C5-LOW** (80 B; run `msgexact-gate`, which `make gates` does not
  collect).
These belong with S10/step 13 of `disk/docs/spec-diskcode-eviction.md`, not
before it.

### Dropped

- **SBH-10.** If the tape-name eviction is ever wanted, move the whole
  `cas_write_ea_header` (TAPOON … TAPOOF) into the SAVE tenant, so the slot
  crossing sits outside a block.
- **ISL-1, C1.** Only take them if C3/A-phase leftovers leave island room.
  Re-measure then.

## 4. Rulings (Joost)

🔴 **THE RULE (2026-10-04): A PUBLISHED BIOS ENTRY POINT KEEPS ITS PUBLISHED CONTRACT.** zerobas may implement it (as `$10` CHRGTR and `$18` OUTDO are), never repurpose it.

| # | question | buys (estimate) | costs |
|---|---|---|---|
| ~~R1~~ | ~~Repoint RST `$08` (SYNCHR) to a tenant dispatcher~~ | ~~~190 B~~ | **REJECTED 2026-10-04 (Joost's question: "doesn't that change the BIOS API?" — yes).** SYNCHR is a published entry point that extension ROMs and machine-code statement handlers call. `$10`/`$18` were repointed to code that implements the SAME published contract (what a real MSX does); a dispatcher changes what the vector does. |
| ~~R2~~ | ~~RST `$28` (GETYPR) as `skip_spaces`~~ | ~~~124 B~~ | **REJECTED**, same reason: GETYPR is a published entry point extension ROMs use to read DAC's type. |
| ~~R3~~ | ~~Reuse C-BIOS's published debug stubs + INLIN/PINLIN/QINLIN~~ | ~~~300 B~~ | **NOT OFFERED**, same reason: published BIOS entries. Only C-BIOS's INTERNAL bytes (strings, padding, stubs whose vectors the merge already repoints) are fair game. |
| R4 | Is a **machine-layout change** on the table: a page-2 ROM island in slot 0 (16 KB, only the logo ROM lives there), or a second sub-ROM in empty slot 3-3? | 16–32 KB | Hardware faithfulness; the harness machine configs; program text sits at `$8000` (page 2), so a page-2 island hides it during the call. |
| R5 | **Dispatcher calls handlers** (`ret` = next statement; `jp exec_stmt`, 44 real sites, becomes `ret`)? Not a ruling by itself, but a large convention change. | ~60 B | Touches every handler's exit, ON ERROR/RESUME, GOTO's SP handling. |

## 5. What this plan does not cover

- **Stacking.** Each figure is one candidate on `4306a5a0`. Overlaps (C4/B4/
  GA-CROSS) are expected to cost a few bytes; each slice re-measures.
- **Runtime.** No candidate has booted. Every slice's FULL battery is the first
  runtime witness.
- **Speed.** kwtime has not run on any of them. DT-1 (dispatch), C8 (float
  PRINT), B1/R1 (tenant call) are the ones to watch.
- **The 50 unbuilt candidates.** These are lower-ranked estimates in the hunt's
  journal. Re-run the hunt after phase B, because carves renew (`jr_mapper`
  re-opens sites after every layout change).
