# LOAD's hook cell — analysis for Joost (2026-09-19)

Read-only analysis. No ROM source changed, no hook installed, no cell picked,
nothing committed, no emulator run. Every claim is cited `file:line` or marked
**HYPOTHESIS**. Clean-room: nothing below required, or records, any instruction
of the reference ROM; hook cells are read for slot and idiom only
([disk/docs/expansion-protocol.md](../disk/docs/expansion-protocol.md) §2).

## 0. The verdict in five lines

1. §6.6j's measurement is **sound for what it measured** and **over-stated in
   what it concluded**. It proves *no candidate cell on LOAD's OPEN path is
   LOAD-specific*. It cannot see any cell reached after the directory search,
   because the only readable case fails there — by design
   ([spec-diskcode-eviction.md:1046-1051](../disk/docs/spec-diskcode-eviction.md#L1046)).
2. "LOAD is the first verb measured not to have a cell" is not an anomaly: the
   reference's disk ROM leaves `H.MERG`, `H.SAVE` and `H.LOPD` **unclaimed**
   ([docs/spec-basic-nodisk.md:211-217](../docs/spec-basic-nodisk.md#L211)) and
   `MERGE` was measured to flip at the same `$FE5D`
   ([spec-diskbasic-hook-rearchitecture.md:410-417](../disk/docs/spec-diskbasic-hook-rearchitecture.md#L410)).
   *No per-verb cell for the program-file verbs* is the reference's pattern.
3. §6.6k's *"`$FE5D` is referenced nowhere in the tree"*
   ([spec-diskcode-eviction.md:1154](../disk/docs/spec-diskcode-eviction.md#L1154))
   is **false**: it was identified four days earlier
   ([hook-rearchitecture:403](../disk/docs/spec-diskbasic-hook-rearchitecture.md#L403)),
   named `H.NULO` from the public table
   ([spec-basic-nodisk.md:188](../docs/spec-basic-nodisk.md#L188)), and cited in
   §11 itself ([:1487-1489](../disk/docs/spec-diskcode-eviction.md#L1487)).
4. The "shared cell dispatches several verbs" hypothesis is **separable from
   "these cells are primitives, not entries"** by a hit-count experiment on
   hook cells that uses only published RAM addresses (§3 below) — the method
   D-CFARCH and the expansion spike already used
   ([expansion-protocol.md](../disk/docs/expansion-protocol.md) §0, §7).
5. Whichever way that comes out, this repo already has **both** dispatch
   shapes: two cells → one body + flag (`hk_lrset`,
   [disk/kernel.asm:2232-2233](../disk/kernel.asm#L2232)) and **one cell → two
   verbs selected by the token in program text** (`hk_files`,
   [disk/kernel.asm:2549-2572](../disk/kernel.asm#L2549)). The second is the
   one a shared cell needs.

---

## 1. What was actually measured — restated exactly

| fact | where |
|---|---|
| 35 cells carry `F7 87 lo hi C9` on the CF-3300 and `C9×5` on the VG-8020 | [spec-basic-nodisk.md:135-152](../docs/spec-basic-nodisk.md#L135) |
| all 35 have public names (TH appendix, grade B) | [spec-basic-nodisk.md:167-192](../docs/spec-basic-nodisk.md#L167) |
| 17 are named in `disk/equates.inc` and claimed by our ROM | [disk/equates.inc:69-109](../disk/equates.inc#L69), [disk/kernel.asm:2218-2240](../disk/kernel.asm#L2218) |
| candidate set = claimed − named = 18, parsed not transcribed | [scratchpad/hookid_load.py:76-119](hookid_load.py#L76) |
| case: `LOAD"NOSUCH.BAS"`, witness = `ERR` trap, baseline 53 with a disk mounted | [hookid_load.py:65-69](hookid_load.py#L65) |
| three controls (base / named cell flips FILES / same poke leaves LOAD) | [hookid_load.py:206-231](hookid_load.py#L206) |
| result: `$FE5D`→51, `$FEB7`→OK, 16 others→53; round 2: both move `OPEN"NOSUCH"` identically | [spec-diskcode-eviction.md:1106-1112](../disk/docs/spec-diskcode-eviction.md#L1106) |
| `$FE5D` = `H.NULO`, `$FEB7` = `H.NODE` (public names, labels not contracts) | [spec-basic-nodisk.md:188-191](../docs/spec-basic-nodisk.md#L188) |
| 09-15: `OPEN` and `MERGE` both flip at `$FE5D` (70→51); `$FEB7` **gave no reading** | [hook-rearchitecture:410-437](../disk/docs/spec-diskbasic-hook-rearchitecture.md#L410) |

Note the last row against §6.6j: on 09-15 `$FEB7` read *nothing* for `OPEN`
and was listed as outstanding; on 09-19 it read `OK` for `OPEN`. The 09-19
instrument has the guard that silence is not the baseline
([hookid_load.py:171-174](hookid_load.py#L171)), so it is the better reading,
but the two runs disagree on the same cell and verb and nobody has said why.

---

## 2. Q1 — Is the measurement sound? Where could it have missed?

**Sound as an instrument.** Controls are the right three; the candidate set is
derived, not quoted; the census reads the debugger, steps by 1, waits for boot
([hookid_load.py:85-119](hookid_load.py#L85)); silence is scored as a change
([hookid_load.py:151-161](hookid_load.py#L151)); each case boots its own machine.
I found no fault in the apparatus. The holes are all in **what the case can
reach** and **what a null row means**, ranked by how much they matter:

### 2.1 🔴 The case geometry cannot reach any cell past the directory search

`LOAD"NOSUCH.BAS"` was chosen *because* it fails before touching the program
([spec-diskcode-eviction.md:1046-1051](../disk/docs/spec-diskcode-eviction.md#L1046)).
That makes every cell the reference reaches **after** a successful open
invisible: for those rows "53 = unchanged" is what the row would read whether
the cell is LOAD's or not. By their public names at least seven candidates are
data-phase-shaped — `$FE80 H.DGET`, `$FE85 H.FILO`, `$FE8A H.INDS`, `$FE99
H.LOC`, `$FE9E H.LOF`, `$FEA3 H.EOF`, `$FEAD H.BAKU`
([spec-basic-nodisk.md:189-191](../docs/spec-basic-nodisk.md#L189)) — and
`$FE4E`, `$FE58`, `$FE62` are not obviously open-phase either. So of the 16
"unchanged" rows, **at least seven are uninformative by construction**. This is
[[a-coverage-row-whose-geometry-cannot-reach-the-case]] exactly. The honest
statement is: *no cell on LOAD's open path is LOAD-specific*; nothing is known
about the data path. `hookid_chan.py` already says it in its own header: *"a
cell that does not flip is not evidence of absence"*
([hookid_chan.py:30-32](hookid_chan.py#L30)).

Why this matters for step 9 specifically: step 9 moves the **loop**, and the
loop runs in the data phase. The one phase the instrument cannot see is the
phase the eviction is about.

### 2.2 🔴 One claimed-looking cell was never a candidate: `$FEBC`

The census keeps a cell only if byte 0 is `F7` and byte 4 is `C9`
([hookid_load.py:109-110](hookid_load.py#L109)). `$FEBC` (`H.POSD`) holds
`33 33 C3 1D 6F` on the CF-3300 — flagged as a loose end, "claimed by a
different mechanism (a bare `JP`...) or misaligned"
([spec-basic-nodisk.md:204-210](../docs/spec-basic-nodisk.md#L204)) — and is
therefore excluded from the 35 and from the 18. `POKE &HFEBC,201` costs one
boot and closes it either way.

### 2.3 🟠 Sixteen of the seventeen named cells were never tested against LOAD

Only `H_FILE` was crossed against LOAD (`ctrl_cross`,
[hookid_load.py:209](hookid_load.py#L209)). The instrument's own *no-hits*
branch names the possibility that LOAD's cell is "one of the sixteen already
named — which would mean a cell serves two verbs"
([hookid_load.py:246-250](hookid_load.py#L246)); its *two-hits* branch stops
before checking. Given 2.1 the interesting ones are again data-phase: none of
the named 17 is, so this is a completeness gap rather than a likely miss — but
it is 16 boots to close and the table should say "tested", not "assumed".

### 2.4 🟠 A `RET`-unclaim is not "the handler is absent" for every cell

The method models an unclaimed hook as a bare `RET` with flags untouched
([spec-basic-nodisk.md:248-253](../docs/spec-basic-nodisk.md#L248)). That is
the correct model of a **diskless machine** — but the reference's main BASIC may
expect a *result* from some hooks, and then a bare `RET` is "handled with
garbage", not "not handled". `ERR 51` (Internal error) at `$FE5D` is what that
looks like: the caller went on with something unset. Likewise `OK, nothing
happened` at `$FEB7` is consistent with "not entered" **and** with "entered,
returned, and the caller took the result as 'nothing to do'". Consequence: the
reading in §6.6j that `$FEB7` "looks like an entry point" and `$FE5D` "like a
routine they both call"
([spec-diskcode-eviction.md:1132-1136](../disk/docs/spec-diskcode-eviction.md#L1132))
is correctly labelled a hypothesis; the POKE readings **cannot** support it
either way. Only hit counts and order can (§3).

### 2.5 🟢 The public table already answers "is LOAD unusual?" — no

The 24 public-table cells the CF-3300 does **not** claim include `H.MERG`,
`H.SAVE` and `H.LOPD`
([spec-basic-nodisk.md:211-217](../docs/spec-basic-nodisk.md#L211)). `MERGE`
has a public cell and the reference does not use it; `MERGE` was measured to
flip at `$FE5D` only
([hook-rearchitecture:413](../disk/docs/spec-diskbasic-hook-rearchitecture.md#L413)).
So the reference's program-file verbs (LOAD, MERGE, and — by its unclaimed cell —
SAVE) are **all** routed through shared cells. The standing ruling "behind ITS
hook" held for `KILL`/`NAME`/`COPY`/`FILES`/`LSET`/`RSET`/`FIELD`
([spec-diskcode-eviction.md:1125-1128](../disk/docs/spec-diskcode-eviction.md#L1125))
because those verbs have per-verb cells in the reference; it was never going to
hold for the file-stream verbs, and steps 10–12 will meet the same wall for the
same reason (§6.6k already did for step 10).

### 2.6 🟢 A black-box arithmetic bound on the reference's data loop

The reference LOADs at **0.0376 ms/byte**
([spec-diskcode-eviction.md:586-591](../disk/docs/spec-diskcode-eviction.md#L586));
one inter-slot crossing costs **0.156 ms** main→disk / **0.170 ms** disk→main
on our machine ([:1237-1241](../disk/docs/spec-diskcode-eviction.md#L1237)).
Unless the CF-3300's BIOS crosses slots four-plus times cheaper than ours
(**unmeasured**), the reference **cannot be crossing per byte** during LOAD.
Whatever its data loop is, it is either inside one slot for the whole file or
crosses per block. That does not name a cell; it rules out one shape, and it is
consistent with §6.3 without confirming H1 or H2 in §3.

### 2.7 minor / checked and closed

* Census range `$FD9A..$FFCF` ([hookid_load.py:108](hookid_load.py#L108),
  [cf3300_arch_probe.py:31](cf3300_arch_probe.py#L31)) vs hookdiff's
  `$FD9A..$FFE7`: the six cells above `$FFCA` are non-stubs on both machines
  ([spec-basic-nodisk.md:162-166](../docs/spec-basic-nodisk.md#L162)). No miss.
* Ordering: the `POKE` runs in the same stored program before the verb
  ([hookid_load.py:144-148](hookid_load.py#L144)); hooks consulted at program
  start are not LOAD's. No miss.
* Alignment: stride 1, all five phases. No miss.
* 109 B vs 111 B: §6.6g says the port cost 111 B (8435→8324,
  [:982](../disk/docs/spec-diskcode-eviction.md#L982)); the dead sweep and
  allowlist say 109 B ([tools/deadcode-allow.txt:19-23](../tools/deadcode-allow.txt#L19)).
  Two instruments, two numbers, 2 B apart, unreconciled. Not this item's
  subject, but it should not be quoted as one figure.

---

## 3. Q2 — The distinguishing experiment

### 3.1 The two hypotheses, stated so they can lose

* **H1 — shared ENTRY, verb dispatched inside.** LOAD, OPEN, MERGE each enter
  the reference's disk ROM once through `$FEB7` (and/or `$FE5D`), and the whole
  verb — including LOAD's data loop — runs there. Prediction: during a LOAD of a
  *real* file the entry cell is hit **exactly once**, the count does **not**
  scale with file size, and **no other** claimed cell is hit between the entry
  hit and the verb's end (except `$FFA7 H.PHYD`, which fires per sector on the
  physical path, [expansion-protocol.md](../disk/docs/expansion-protocol.md) §0).
* **H2 — the cells are PRIMITIVES (name/device resolution, open), not verb
  entries.** The verb's loop lives outside the disk ROM and calls back in per
  byte or per block. Prediction: during the same LOAD, one or more claimed cells
  other than the entry are hit with a count that **scales** with the file
  (per byte ≈ N, or per sector ≈ N/512), or `$FEB7`/`$FE5D` themselves are hit
  more than once per statement.

They coincide on every row §6.6j has (both predict both cells move a
missing-file LOAD and OPEN). They separate on **counts on a successful load**.

### 3.2 The instrument — counting, not poking

Set openMSX **breakpoints on the hook cell addresses** (RAM, published) and
count hits per statement. This is the method the expansion spike used ("BP on
documented hook addresses",
[expansion-protocol.md](../disk/docs/expansion-protocol.md) §0 and §7) and
D-CFARCH's census reads the same cells. The breakpoint handler does exactly two
things: `incr` a counter keyed by PC, then `debug cont`. **Never `step`, never
read memory at the target, and — to stay on the conservative side of §2 — do
not record the register file** (counts and order answer the question; registers
would start describing the reference's internal ABI).

Cells to arm: all 35 claimed (so the control cells are in the same run), plus
`$FEBC` (§2.2). Statements, each on its own boot, with a disk mounted
(`disk/test720.dsk`, [hookid_load.py:65](hookid_load.py#L65)), using
`loadrun_probe.py`'s technique of a marker as the loaded program's first line so
the witness survives the load
([spec-diskcode-eviction.md:571-576](../disk/docs/spec-diskcode-eviction.md#L571)):

| # | statement | what it asks |
|---|---|---|
| S1 | `LOAD"S.BAS",R` (1055 B, from loadrun's image) | counts on a small tokenised load |
| S2 | `LOAD"L.BAS",R` (14369 B) | **the scaling row** — which cells' counts move with size |
| S3 | `LOAD"NOSUCH.BAS"` | replicates §6.6j as counts: which cells fire before ERR 53 |
| S4 | `OPEN"X.DAT"FOR INPUT AS#1` … `CLOSE#1` (real file) | OPEN's counts on the same cells |
| S5 | S4 + `INPUT#1,A$` ×k | which cells count per record/byte |
| S6 | `MERGE"A.BAS"` (ASCII file) | MERGE's counts; ties to the 09-15 `$FE5D` result |
| S7 | `SAVE"T.BAS"` | free finding for step 10+: SAVE's route, `H.SAVE` unclaimed |

**Controls, each of which voids the run if it fails:**

* **C1 positive/method:** `FILES` must hit `$FE7B H.FILE` exactly once and
  `LOAD` must hit it zero times (the same pair §6.6j's `ctrl_file`/`ctrl_cross`
  used, [hookid_load.py:206-209](hookid_load.py#L206)).
* **C2 scaling-visible:** `$FFA7 H.PHYD` must count **more** on S2 than S1, and
  roughly in sector ratio. If a per-sector cell does not scale, the counter
  cannot see scaling and no null in the table means anything.
* **C3 quiescent:** a boot with **no** statement must count zero on every cell
  except `$FD9F H.TIMI` (which fires at interrupt rate,
  [expansion-protocol.md](../disk/docs/expansion-protocol.md) §2). Establishes
  the noise floor and that breakpoints armed after INIT wrote the table
  (the `after time 40` lesson, [hookid_load.py:97-101](hookid_load.py#L97)).
* **C4 identity:** the loaded program prints its own marker (loadrun's
  identity witness, [:624-626](../disk/docs/spec-diskcode-eviction.md#L624)), so
  a failed load cannot pass as a fast one.

### 3.3 What each outcome proves

| reading | proves | consequence for step 9 |
|---|---|---|
| S1/S2: `$FEB7` (or `$FE5D`) = 1 each, size-independent; **no other** unnamed cell hit except `H.PHYD` | **H1**: a shared entry, the loop inside the disk ROM | Option A/D (shared cell + selector) is the reference's shape; install there |
| S1/S2: some cell(s) count ∝ bytes | **H2-byte**: loop outside, per-byte call-in | contradicts §2.6's bound unless crossing is cheap on that BIOS — re-price, then Option C is the faithful shape |
| S1/S2: some cell(s) count ∝ sectors (≈2 vs ≈28) beyond `H.PHYD` | **H2-block**: loop outside, per-block call-in | Option C is the reference's shape; §6.3 is not violated (it bans per-byte) |
| `$FEB7` counts > 1 per statement, or counts on S4/S5 differ in kind from S1 | it is a per-item primitive, not an entry | Option A must not be sited on it; whichever cell counts once is the entry |
| S3 hits `$FEB7` and `$FE5D` and nothing else before the trap | confirms §6.6j as counts | — |
| `$FEBC` counts on any LOAD row | §2.2 was a real miss | add it to every candidate list |
| C1–C4 fail | apparatus | no reading |

⚠️ A null on a cell under this design **is** meaningful, unlike the POKE
design: C2 proves the counter sees per-sector activity, so a data-phase cell
that counts zero on S2 was genuinely not reached.

### 3.4 A cheaper adjunct that reuses the POKE instrument as-is

Extend `hookid_load.py`'s round 1 with a **success-path** case: `LOAD"S.BAS",R`
with the marker as line 1 (loadrun's witness), one cell un-claimed per boot.
Reading: marker printed = LOAD survived the un-claim; no marker / hang / garbage
= the cell is on LOAD's path. This lifts §2.1 for the seven data-phase cells and
costs ~18 boots. It cannot count, so it does not separate H1 from H2 — but it
turns seven uninformative rows into informative ones, and it is 30 lines of
change to an instrument whose controls already work.

---

## 4. Q3 — Architectural options, with the numbers the repo already has

Fixed facts the options are priced against:

| figure | value | where |
|---|---|---|
| crossing main→disk / disk→main | 0.156 ms / 0.170 ms | [:1237-1241](../disk/docs/spec-diskcode-eviction.md#L1237) |
| our LOAD / reference LOAD | 0.2178 / 0.0376 ms per byte | [:586-591](../disk/docs/spec-diskcode-eviction.md#L586) |
| per-byte crossing on LOAD | ×1.72 (3.57 s → 6.12 s on 16 KB) | [:592-599](../disk/docs/spec-diskcode-eviction.md#L592) |
| hook install in disk.rom | 9 B per hook + one `hook_tab` row | [spec-basic-nodisk.md:390-393](../docs/spec-basic-nodisk.md#L390), [disk/kernel.asm:2218](../disk/kernel.asm#L2218) |
| main stub per verb | `ld hl,H_x` + `call chan_gate` = 6 B; "~10 B" with dispatch | [basic/files.asm:81-82](../basic/files.asm#L81), [:49-53](../disk/docs/spec-diskcode-eviction.md#L49) |
| stream layer already in disk.rom | 109/111 B, unreferenced, allowlisted | [:973-999](../disk/docs/spec-diskcode-eviction.md#L973), [tools/deadcode-allow.txt:19-23](../tools/deadcode-allow.txt#L19) |
| out-edges of the moved bodies | 5 (`df_or_loaderr`, `load_commit_prog`, `load_error`, `new_prog`, `print_msg`), all once-per-load/failure; `fat_io_getbyte` local | `dpldep_census.py --move`, run 2026-09-19, matches [:988-990](../disk/docs/spec-diskcode-eviction.md#L988) |
| §6.6h design | hook returns CF=1 + code in A; **0 call-backs** | [:1026-1031](../disk/docs/spec-diskcode-eviction.md#L1026) |
| Joost's placement rules | R1: 1–2 call-backs natural; R2: duplicate hot path, call back for errors | [:1297-1368](../disk/docs/spec-diskcode-eviction.md#L1297) |
| what stays in main regardless | parse, raise, channel-table readers, `init_filechan` | [:1422-1435](../disk/docs/spec-diskcode-eviction.md#L1422) |
| disk.rom free | 8324 B / 29 runs on 09-19 — **rots; run `make basic-reloc`** | [:982](../disk/docs/spec-diskcode-eviction.md#L982) |
| size of the six `dpl_*` bodies | **unmeasured** as a number (spans [basic/cload.asm:984-1239](../basic/cload.asm#L984)) | — |

### Option A — a shared cell with a selector (the `hk_files` pattern, not `hk_lrset`)

Install `hk_dpload` at one of the two cells the reference claims and every
file verb passes through. Two selector mechanisms already exist in-tree:

* **token-in-text** — `hk_files` reads the byte before `FN_RESUME` to tell
  FILES from LFILES, "no call-back and no new sysvar"
  ([disk/kernel.asm:2549-2572](../disk/kernel.asm#L2549)). For LOAD vs OPEN vs
  MERGE the verb token is in exactly that place.
* **flag-before-gate** — `LRSET_JUST` written by main, read by the body
  ([basic/field.asm:565-569](../basic/field.asm#L565),
  [disk/kernel.asm:1959](../disk/kernel.asm#L1959)). Note `hk_lrset` is *two
  cells → one body*, the inverse of what a shared cell needs; the flag is what
  transfers, not the cell arrangement. `DISKOP_OP`/`DISKOP_SEL_*` is the
  existing selector cell family.

| | |
|---|---|
| bytes, disk.rom | 9 B install + 4 B `hook_tab` + the six bodies (unmeasured) + selector dispatch (a `cp`/`jr` ladder, ~3 B per verb); the 109/111 B already there become live |
| bytes, main | −(six bodies) + ~10 B stub + the A-code dispatch (unmeasured) |
| crossings | 1 per LOAD (+0 call-backs per §6.6h; up to 5 if the design regresses to the census's out-edges) |
| speed | unchanged per byte (loop and cursor local) |
| R1/R2 | 0–2 call-backs: natural |
| risk 1 | **which cell** — free for our own ABI, but §3 should be run first so the cell we claim is the one that counts once per verb, not a per-item primitive |
| risk 2 | **diskless LOAD must not raise ERR 5.** `chan_gate` raises on an unclaimed cell ([basic/files.asm:84-92](../basic/files.asm#L84)); the reference's diskless LOAD goes to cassette (unreadable rows, [probes/basic/basic_probe_nodisk.py:154-155](../probes/basic/basic_probe_nodisk.py#L154)). LOAD's stub needs a *test-then-fall-through* gate, not `chan_gate`'s *raise*. Today main does `diskslot_test` → `dpl_err` ([basic/cload.asm:986-989](../basic/cload.asm#L986)); the hook-claimed test replaces `diskslot_test` there |
| risk 3 | once OPEN/MERGE/SAVE also route through the same cell (steps 10+), the selector must be verb-aware from day 1 — see D |
| clean-room | a claimed cell with our own signalling is what every hook here already is ("own-design signalling over a published layout", [spec-basic-nodisk.md:270-275](../docs/spec-basic-nodisk.md#L270)) |

### Option B — leave LOAD's loop in main; delete the port

| | |
|---|---|
| bytes | −109/111 B in disk.rom (delete [tools/deadcode-allow.txt:19-23](../tools/deadcode-allow.txt#L19) and the canary reports it); main unchanged |
| crossings / speed | unchanged |
| what it gives up | §0.0's end-state gate (step 14, "no disk-implementation symbol reachable in main+sub", [:484](../disk/docs/spec-diskcode-eviction.md#L484)) stays open for LOAD's six bodies **and** for main's private copy of the FAT stream (`fat_io_open`/`fat_io_getbyte` with its own state block, [:872-886](../disk/docs/spec-diskcode-eviction.md#L872)); the one-engine goal of §0.1 is not met for LOAD |
| when it is right | if §3 comes out H2-block and Option C is chosen instead, or if Joost rules that a verb without its own reference cell stays in main. It is not a compromise; it is a different answer to §0.0 |

### Option C — the STREAM is the service: loop in main, refill per sector across the seam

Not in the spec by name, but every piece is hinted: "INPUT#/INPUT$ may keep
their cursor across the seam" ([:522-525](../disk/docs/spec-diskcode-eviction.md#L522)),
§6.3 bans **per-byte** crossing only ([:644-662](../disk/docs/spec-diskcode-eviction.md#L644)),
and §6.6e already moved the cursor's 6 B state to the disk side
([:981-983](../disk/docs/spec-diskcode-eviction.md#L981)). The disk ROM exposes
*open / refill-sector / close* behind hook cells; the sector buffer is RAM,
mapped in both ROMs; main's `dpl_*` loop reads bytes from the buffer and calls
the refill hook once per 512 B.

| | |
|---|---|
| crossings on the 14369 B load | ≈29 × 0.156 ms ≈ **4.5 ms** against 3.57 s measured — ~0.1 %, **arithmetic, not a measurement** |
| bytes | **unmeasured**: main keeps the six bodies but loses `fat_io_open`/`fat_io_getbyte` and its FAT state; disk.rom gains a refill entry (small) and the install; net direction is favourable for main page 1 but nobody has priced it |
| what it buys beyond LOAD | **one stream ABI for steps 9, 10, 11 and 12** — OPEN/INPUT#/INPUT$/PRINT#/MERGE all consume the same refill/flush service — which is what the reference's public cell names for this region suggest (**HYPOTHESIS**, names are labels not contracts, [:1489-1490](../disk/docs/spec-diskcode-eviction.md#L1489)) |
| against | the LOAD *verb* stays in main (its loop is BASIC-text knowledge — link words, line numbers — arguably not disk implementation at all; the DISK part is the stream); still needs a cell to install the refill at, so it does not escape the cell question, it changes which verb's cell we are looking for |
| when it is right | if §3 reads H2-block, this is the reference's shape and A is not |

### Option D — A, designed for N verbs: a program-file service cell

Option A with the selector defined up front for the verbs the reference measurably
routes through the shared cells: LOAD (tokenised), MERGE (ASCII,
[basic/files.asm:1776-1787](../basic/files.asm#L1776)), OPEN
([hook-rearchitecture:412](../disk/docs/spec-diskbasic-hook-rearchitecture.md#L412)),
and — by its unclaimed public cell — SAVE. Costs as A plus one selector value
per verb. It is the shape §6.6j's own closing paragraph asked about, made
concrete: the cell is the *file-verb entry*, the selector is the verb, the
bodies are per-verb tenants behind it. Its risk is that it is designed against
H1 before H1 is measured — hence §3 first.

### Not an option: guessing the cell's meaning

Picking `$FEB7` over `$FE5D` on the grounds that one "looks like an entry"
([:1132-1136](../disk/docs/spec-diskcode-eviction.md#L1132)) is choosing, not
measuring (§2.4). For our own ABI either cell works identically today — nothing
in main calls either (tree grep, 2026-09-19: only docs and the probes mention
them). The choice only starts to matter when a **foreign** disk ROM sits in the
slot, and then *neither* choice makes our LOAD stub speak that ROM's ABI, which
is already true of all 17 hooks we claim.

---

## 5. Q4 — What cannot be known without crossing the clean-room line

* **What the reference's handlers at `$FE5D`/`$FEB7` do**, what registers or
  work-area cells its main BASIC passes them, and what it expects back. §11 of
  the spec already says this ("the published names are not contracts we can
  read without a disassembly", [:1489-1490](../disk/docs/spec-diskcode-eviction.md#L1489)).
  Everything above uses names as labels only.
* **Why un-claiming `$FE5D` yields ERR 51** rather than 53 or a hang. It is a
  reading; its cause is internal.
* **Whether the reference's LOAD loop is in its disk ROM or its main ROM.** §3
  can establish the *shape of the crossings* (once / per block / per byte),
  which is enough to choose between A and C; it cannot say where the bytes that
  execute between hits live, and does not need to.
* **Whether `$FEBC`'s `33 33 C3 1D 6F` is a claim.** A POKE (§2.2) can show
  whether it *matters*; what it is stays unread.
* Anything about the target addresses in the 35 stubs beyond "non-zero, in
  slot `$87`" ([expansion-protocol.md](../disk/docs/expansion-protocol.md) §2).

---

## 6. For Joost — the ruling this needs, in three questions

1. **Does "behind ITS hook" mean a per-verb cell, or the cell the reference
   uses?** The measurement plus the public table say the reference has no
   per-verb cell for LOAD, MERGE or SAVE. If the ruling means *the reference's
   cell*, LOAD's is a shared one and Option A/D is the design. If it means *a
   cell of its own*, LOAD has none to be behind, and Option B (stay in main) or
   C (stream service) follows.
2. **May §3 be run before any code?** ~10 boots on an idle machine with the
   breakpoint-count instrument; it separates A/D from C and closes §2.1 and
   §2.2. Until it runs, the spec's "entry vs routine" reading is a hypothesis
   and any cell chosen is chosen, not measured.
3. **Diskless LOAD.** Under any option that routes LOAD through a hook, the
   main stub must fall through to cassette on an unclaimed cell, not raise ERR
   5 as `chan_gate` does. That is a small new gate variant and a divergence row
   to check on `C-BIOS_MSX1_EU_REPACK_NODISK` — it should be in the ruling so it
   is not discovered by the gate later.

Doc debt found on the way, not fixed (no commits by instruction): §6.6k:1154
("referenced nowhere") is false; §6.6j's `$FEB7 → OK` for OPEN contradicts the
09-15 "no reading" without comment; 109 B vs 111 B for the port.
