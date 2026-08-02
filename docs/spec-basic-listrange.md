<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LSTRNG — `LIST <range>`: the statement half

Measurement:
[`docs/listrange-msx1-characterization.md`](listrange-msx1-characterization.md) —
the crunch half is ten `lna-list*` rows (all three sides byte-identical **before**
this slice), the run-time half is a 34-row walk in two rounds (20 `lst` tail rows
+ 14 `lse` ERR rows). Two references (Philips VG-8020, National CF-3300) agreeing
on **every** row, `--repeat 2`, every payload past the echo guard on all three
sides.

Neighbours whose cells this must not move: D-DELETE
([`spec-basic-delete.md`](spec-basic-delete.md) **R-D1..R-D8**), D-KWGAP4
(**R-K1/R-K2/R-K3**), D-LNREF (**R-R1/R-R2/R-E**), D-LNLIST (**R-L1/R-L3** — note
the name collision: this document's rules are numbered **R-LS1..R-LS7**), D-RETLN,
D-CONTR.

---

## 1. What is missing

`ex_list` ([`basic/list.asm:41`](../basic/list.asm:41)) does `inc hl` past the
`LIST` token and walks the whole program; **the argument is discarded**. That is
a Phase-2 divergence filed in the file's own header
([`basic/list.asm:31`](../basic/list.asm:31)) and in `TODO.md`. Sixteen of the
twenty `lst` rows and two of the fourteen `lse` rows diverge because of it.

This slice takes **numeric arguments only**. `.` is measured, understood and
deliberately deferred (§6); `RENUM`, `AUTO` and `LLIST` stay filed for the
reasons D-KWGAP4 gave.

## 2. The rules to implement

All seven are measured on both references, both agreeing.

🔴 **THE HEADLINE IS THAT `DELETE`'S RANGE RULES DO NOT TRANSFER, AND FIVE OF THE
TWENTY SHAPES WOULD HAVE BEEN WRONG IF THEY HAD BEEN ASSUMED TO.** D-DELETE
measured, one week earlier, with the same grammar and the same instrument, that
the high end must name a stored line exactly, that a reversed range is ERR 5,
and that an absent number is 0 on either end. **`LIST` has none of those rules.**

* **R-LS1 — `LIST n` is `LIST n-n`.** `lst-one` and `lst-same` both read `B`.
  The one rule the two verbs share.

* **R-LS2 — neither end has to name a stored line, and nothing is ever raised
  for a range.** `LIST 20-35` lists `B|C` (`lst-himiss`) where `DELETE 20-35` is
  ERR 5; `LIST 10-65529` lists everything (`lst-hitop`) where `DELETE 10-65529`
  is ERR 5. `lse-himiss` and `lse-above` confirm **ERR 0**.

* **R-LS3 — the walk starts at the first stored line ≥ lo and stops after the
  last one ≤ hi.** Measured where the low bound is a strict inequality
  (`lst-lomid`, `LIST 25-30` → `C` only).

* **R-LS4 — an empty range lists nothing and raises nothing.** `lst-miss`,
  `lst-zero`, `lst-below`, `lst-above`, `lst-rev` and `lst-empty` all print
  nothing; `lse-rev`, `lse-miss`, `lse-above` and `lse-empty` all read **ERR 0**.
  🔴 **`lst-rev` IS THE ROW THAT MATTERS HERE**: under `DELETE` a reversed range
  is a *rule* (ERR 5), and round 1 could not tell "listed nothing" from "refused
  silently" because six rows shared one value. Round 2 asked `ERR` and the answer
  is 0 — **there is no reversal check to write.**

* **R-LS5 — 🔴 an absent number is NOT 0; it is the nearest extreme.** `LIST -30`
  = `0-30` (`lst-openlo` → `A|B|C`), but **`LIST 20-` = `20-65535`**
  (`lst-openhi` → `B|C|D`), and bare `LIST` is `0-65535` (`lst-all`). This is the
  single rule most likely to be got wrong by copying `le_delrange`, where
  `DELETE 20-` is `20-0` and therefore ERR 5.

  Bare `LIST` is what forbids the tidier rule *"hi defaults to lo"*: under it,
  bare `LIST` would be `0-0` and would list nothing. The fitted algorithm is:

  ```
  lo = 0 ; hi = 65535
  if a $0E number is present         :  lo = hi = that number
  if a $F2 '-' follows               :  hi = 65535
      if a $0E number follows the '-':  hi = that number
  ```

* **R-LS6 — anything but end-of-statement after the range is ERR 2, raised
  BEFORE anything is listed.** `LIST 10,30` prints `Syntax error` and no
  listing (`lst-comma`), `lse-comma` reads ` 2 `. A `:` **is** accepted (R-LS7).

* **R-LS7 — `LIST` ENDS the line and the program, exactly as `DELETE` does.**
  Inside a `RUN` the program stops with ERR 0 and no further line executes
  (`lse-inprog` ` 1  0 `, against ` 13  0 ` if it continued); in direct mode the
  rest of the typed line does not run either (`lse-tail` ` 0  0 ` against its
  control `lse-tailctl` ` 9  0 `), and that is not a syntax error — the `:` is
  accepted and then abandoned.

  ⚠️ **I PREDICTED THE OPPOSITE FOR BOTH ROWS AND WROTE THE PREDICTION DOWN
  FIRST.** The reasoning was that `DELETE` ends the run because it has just
  memmoved the text `CURLINE` points into, and `LIST` moves nothing — a
  mechanism story, and the measurement refuted it. It is recorded here because
  it is the only place in this slice where a plausible-sounding derivation beat
  a measurement in my head, and because it makes the implementation *cheaper*:
  nothing needs marshalling back.

* **R-LS8 — `LIST` is NOT a program edit.** Variables survive (`lse-vars`
  ` 1  0 `) and `CONT` still resumes (`lse-cont` ` 5  0 `, matching its control
  `lse-contctl`). 🔴 **This is a POSITIVE requirement, not an absence**:
  `ex_delete` clears `CONTVALID` and `ex_list` must **not**, even though it now
  shares `ENDFLAG` with it. `lse-cont` is the row that gates the difference.

### 2.1 What this does NOT change

* **the crunch.** All ten argument shapes are already byte-identical on all three
  sides (characterization §1). Nothing in `tokenise.inc` or `kwtable.inc` is
  touched and no `lna-list*` / `ref-list` cell may move.
* **bare `LIST`.** `lst-all` must keep reading the full listing. It is also the
  control that separates a range divergence from a detokeniser one, so it is
  load-bearing in both directions.
* **`DELETE`.** `le_delrange` and every `dlt-` cell stay exactly as they are.
  This slice adds a `LE_OP`; it changes none.
* **ASCII SAVE.** `SAVE"F",A` and `SAVE"CAS:",A` must keep writing the WHOLE
  program (§3.3).
* **`RENUM` / `AUTO` / `LLIST`**, and **`.`** (§6).

## 3. Funding — re-measured from a clean build at HEAD `406b9e3`

`rm -rf build && make basic-reloc`:

| region | free |
|---|---|
| main page-0 low region | **23 B** |
| main page 1 | **82 B** |
| sub page 0 | 3913 B |
| sub page 1 | **3145 B** |

Component sizes read from `build/basic-reloc.sym`: `ex_list` **11 B**,
`list_walk`+`lst_lp` **38 B**, `list_num` 4 B. `skip_spaces` ($4243) and
`find_line_bc` ($7767) are both main page 1 and reachable by ordinary call.

### 3.1 Three designs, costed — and the one `DELETE` shipped is IMPOSSIBLE here

🎯 **D-DELETE's K6 is the precedent: cost the candidates, do not estimate them.**
Counted by hand from the actual opcodes each design would emit.

| design | main page 1 | sub page 1 | verdict |
|---|---|---|---|
| (a) whole verb sub-side — *what `DELETE` shipped* | ~10 B | ~150 B | 🔴 **IMPOSSIBLE** |
| (b) **parse sub-side, walk + filter resident** | **68 B measured** (est. 65) | 96 B measured | ✅ **SHIPPED** |
| (c) whole verb resident | **~128 B measured** (est. 107) | 0 | 🔴 does not fit in 82 B |

**Measured, not estimated (knife K7).** (b) is the shipped build: page 1 went
82 B → **14 B** free, so the slice cost **68 B** against a hand-counted 65 B —
the estimate was honest to within 3 B. (c) is computed from `build/sub.sym` the
way D-DELETE's K6 computed its three: `le_lstrange` **70 B** + `ldr_num` **19 B**,
less the ~4 B of `LE_STATUS` plumbing a resident version would not need, plus
the 68 B already spent, less the **25 B** marshalling head (`ld (LST_PTR),hl` /
`ld a,LE_OP` / `ld ix` / `call subrom_call` / `jp c` / `ld a,(LE_STATUS)` /
`or a` / `jp nz,raise_error`) it would delete → **~128 B**.

⚠️ **THE (c) ESTIMATE IN THE SIGNED-OFF DRAFT WAS 21 B OPTIMISTIC** (107 vs 128).
The verdict is unchanged and in fact holds by a wider margin — 46 B over the wall
rather than 25 — but the number that was signed off was wrong, and it is
corrected here rather than quietly left standing.

🔴 **(a) IS NOT MERELY EXPENSIVE, IT CANNOT BE BUILT.** `list_walk` prints
through `pchar` (main page 1) and reaches the detokeniser by CALSLT to a sub-ROM
**page-0** tenant (`SUBROM_IDX_DETOK`). A sub page-1 tenant has main page 1
switched out and cannot call either. The trick that made `DELETE` cost only 37 B
of page 1 is unavailable to `LIST`, and the reason is structural, not budgetary.

🔴 **AND (c) DOES NOT FIT, which is why the parse goes sub-side anyway.** The
resident parse is ~63 B of `ex_list` growth plus a 16 B `lst_num` — and page 1
has 82 B for the whole slice, of which the walk filter (§3.2) already claims 25.
The "simple, obvious" design is off the table for the second slice running.

(b)'s main-side cost, itemised:

| where | what | cost |
|---|---|---|
| `basic/list.asm` | `ex_list`: marshal the cursor, `subrom_call`, raise / walk / stop | 35 B − 11 B existing = **+24 B** |
| `basic/list.asm` | the `lst_lp` range filter (two 16-bit compares + two exits) | **+25 B** |
| `basic/list.asm` | `lst_setall` + the `list_all` entry (§3.3) | **+16 B** |
| | **total main page 1** | **~65 B of 82** |

⚠️ These are hand-counted opcode budgets, not measurements. **Knife K7 (§7)
measures the shipped figure and the (c) figure and is scored against this
table** — a justification that cannot be measured is not a reason.

### 3.2 The walk filter, and why it lands in `lst_lp`

`list_walk` already loads each line's number into `BC` before printing it. The
filter is two 16-bit compares inserted there: `number > hi` → stop (lines are
stored ascending, so nothing further can be in range either), `number < lo` →
skip to the next line. Both exits reuse the link the loop has already pushed.

### 3.3 🔴 `list_walk` HAS THREE CALLERS AND A RANGE MUST NOT LEAK INTO TWO OF THEM

`ex_list` is not the only caller: `ascii_save`
([`basic/save.asm:227`](../basic/save.asm:227)) and `cas_ascii_save`
([`basic/save.asm:280`](../basic/save.asm:280)) drive the same walk to disk and
to tape. Left unhandled, `LIST 20-30` followed by `SAVE"F",A` would silently
write **two lines** — a data-loss bug in a verb this slice never mentions.

The fix is a second entry point:

```
lst_setall:   lo := 0 ; hi := 65535 ; ret
list_all:     call lst_setall ; fall into list_walk
```

and the two SAVE call sites become `call list_all` (a 3-byte call either way, so
0 B at the sites). ⚠️ **Knife K6 (§7) exists specifically to find out whether
anything in the tree actually gates this**, and its predicted result is that
nothing does.

### 3.4 RAM — no new cells

The two ends ride **`SL_NUM`** (lo) and **`SL_SIZE`** (hi) and the cursor rides
**`SL_TOK`**, aliased as `LST_LO` / `LST_HI` / `LST_PTR` — the same second-value-
namespace pattern D-DELETE established, and the same three cells.

🔴 **The non-overlap is proved by grep, not asserted, and the grep is WIDER than
D-DELETE's had to be.** `LIST`'s range must survive the whole walk, which
CALSLTs the page-0 detokeniser and — on the SAVE paths — runs the FAT12 disk
writer or the cassette block writer. So the question is not just "is a store in
flight" but "does anything on any of those three paths touch these cells".
`grep -rn 'SL_NUM\|SL_SIZE\|SL_TOK\|SL_SLOT\|SL_DEL' basic/*.asm sub/*.asm`
returns readers in exactly two places: `basic/program.asm`
(`store_line`, `ex_delete`) and `sub/lineedit.asm` (`le_store`, `le_delrange`,
`prog_find_del`, `delete_at`, `open_gap`). **No detok, save, FAT or cassette path
appears.** One `subrom_call` reaches one `LE_OP`, so a store, a delrange and a
listrange are never in flight together.

## 4. The change

1. **[`basic/sysvars.inc`](../basic/sysvars.inc)** — `LE_OP_LSTRANGE equ 3`, the
   `LST_LO`/`LST_HI`/`LST_PTR` aliases with §3.4's grep recorded at the equates.
2. **[`basic/list.asm`](../basic/list.asm)** — `ex_list` becomes the marshalling
   head; `lst_setall`/`list_all`; the `lst_lp` range filter. The file header's
   "Phase-2 divergence" paragraph is replaced by the measured rules.
3. **[`basic/save.asm`](../basic/save.asm)** — two call sites `list_walk` →
   `list_all`.
4. **[`sub/lineedit.asm`](../sub/lineedit.asm)** — `le_lstrange`; `ldr_num`
   gains a CF "was a number present" result (DELETE ignores CF, so its behaviour
   is unchanged — and K3 is scored partly on `dlt-` rows to prove it); one new
   arm in `lineedit_tenant`'s selector.

⚠️ No `stmt_table` change: `LIST` already has its row
([`basic/interp.asm:284`](../basic/interp.asm:284)) and is already declared in
[`tests/test_stmt_dispatch.py:125`](../tests/test_stmt_dispatch.py:125), so that
gate will not fire for this slice.

## 5. Rows and pins

* **new**: 20 `lst` rows + 14 `lse` rows (run time) and 4 `lna-list*` crunch rows
  (`-listhi`, `-listnone`, `-listcomma`, `-listdot`).
  `lst-`/`lse-` join `lnblank-say-acceptance`'s default `ONLY=`, taking it from
  74 to **108** rows.
* **new apparatus**: `TAIL_ONLY`, a third readout arm (characterization §0).
* **pinned `KNOWN_DIVERGE`**: **three**, all at zerobas's exact post-fix
  `syntax error` — `lst-dot` and `lse-dotedit` (`.`, §6) and `lst-comma`. The say
  gate goes 74/74 with 4 pins to **108/108 with 7**; the pin set GREW by three
  and that is said out loud rather than rounded.
* 🔴 **`lst-comma` IS A PIN THIS SLICE DID NOT EXPECT AND DOES NOT OWN.** The
  rule is implemented correctly — `lse-comma` reads ` 2 ` on all three sides, so
  the error CLASS agrees. What differs is the message TEXT: zerobas prints
  `syntax error` where both references print `Syntax error`. Described at
  [`basic/arrays.asm:608`](../basic/arrays.asm:608) as a deliberate lowercase
  house style — *"the same documented deviation as every other zerobas syntax
  error"*. Pinning it inside a `LIST` slice, with the owner named, is the honest
  option. **It is the first row in this probe to read an error MESSAGE rather
  than an error CODE**, which is why nothing had surfaced it before — and any
  future battery using the `screen_tail` readout on an error path will hit it too.

  🔴 **AND THAT "EVERY OTHER" CLAIM IS FALSE — THE SAME CORPUS RUN DISPROVES IT
  FROM THE OTHER DIRECTION.** `array-acceptance`'s two standing failures read
  `want='illegal function call' zb='Illegal function call'` — zerobas emitting a
  **capitalised** message where that probe expects lowercase, the exact mirror of
  `lst-comma`. zerobas is **inconsistent with itself**: lowercase for *syntax
  error*, capitalised for *Illegal function call*. This slice pins its own row
  and files the inconsistency rather than repeating a tree-wide claim that two
  rows in one corpus run contradict. ⚠️ It also raises the possibility that the
  two long-standing `array` failures are a message-case defect rather than a
  wrong probe expectation — nobody has checked, and this slice does not either.
* **controls that must stay green**: `lst-all` (the detok control),
  `lse-ctl` ` 0 `, `lse-tailctl` ` 9  0 `, `lse-contctl` ` 5  0 `,
  `lse-vars` ` 1  0 `, `lse-cont` ` 5  0 `.
* ⚠️ **cells that AGREE TODAY FOR THE WRONG REASON and must still agree after
  the handler lands** — the `dlt-comma` shape: `lst-hipast` and `lst-hitop`
  (their correct answer happens to be the whole program, which is what an
  argument-ignoring `LIST` prints anyway) and `lse-tail` ` 0  0 ` (zerobas
  already fails to run the tail, for a reason that is not R-LS7).

## 6. Deliberately out of scope: `.`

`LIST .` works on both references. `lst-dot` reads `40 REM D` — but line 40 is
both the last line typed **and** the highest-numbered, the identical ambiguity
`dlt-dot` had. **`lse-dotedit` re-enters line 20 last and the answer moves to
`20 REM B`**, so `LIST`'s `.` is the same *line the editor last touched* that
D-DELETE measured for `DELETE`, and the shared-mechanism claim in that slice's §5
now has a second verb behind it.

It stays out of scope for the same reasons: zerobas records nothing of the kind,
the mechanism spans `LIST`/`DELETE`/`AUTO`/`RENUM`/`EDIT`, and what `.` reads
after a `RUN`, after an error, after a `LIST` and on a cold machine is still
unmeasured. It is filed in `TODO.md` and **pinned, not dropped**: `.` reaches the
statement as the literal `$2E` (characterization §1), which **R-LS6 answers with
ERR 2** — so the pinned value is a consequence of a rule this slice *does*
implement, and K4 is the knife that proves the pin is load-bearing rather than
inert.

## 7. Knives — each with a predicted RED set **and** predicted GREEN survivors

Scored against the **whole 34-row battery** (20 `lst` + 14 `lse`) on zerobas
only, against a saved unknifed baseline, with every RED row's **exact predicted
value written down before the build**.

* **K1 — "an absent HIGH end is 0" (i.e. copy `DELETE`'s R-D5)**: in the `-` arm,
  `ld de,$FFFF` → `ld de,0`.
  RED (1): `lst-openhi` (`LIST 20-`) → `<nothing listed>`.
  GREEN (33): `lst-openlo` still `A|B|C` (its hi is explicit), `lst-all` still
  the full listing (it never enters the `-` arm).
  🎯 The knife aimed at the exact rule the neighbouring slice would have led me
  to get wrong.
* **K2 — the BARE-`LIST` default**: the *initial* `hi` → `ld de,0`.
  RED (1): `lst-all` → `<nothing listed>`.
  GREEN (33): including `lst-openhi`, whose hi comes from the `-` arm.
  🔴 **K1 and K2 are each other's control.** Two different defaults produce
  R-LS5; one knife could only have half-shown that they are separate.
* **K3 — R-LS1 (`LIST n` is `LIST n-n`)**: delete the `ld (LST_HI),de` after the
  low read.
  RED (3): `lst-one` → `B|C|D` · `lst-miss` → `C|D` · `lst-zero` → `A|B|C|D`.
  GREEN (31): `lst-same` **must stay `B`** — its hi comes from the `-` arm, which
  is what separates R-LS1 from R-LS5. Every `dlt-` row must also stay green,
  which is what proves the `ldr_num` CF change did not disturb `DELETE`.
* **K4 — the trailing-junk check (R-LS6)**: drop the `cp COLON` / fail arm.
  RED (4): `lst-comma` → `10 REM A` · `lse-comma` → ` 0 ` · `lst-dot` →
  `A|B|C|D` · `lse-dotedit` → `A|B|C|D`.
  GREEN (30).
  🎯 **The two `.` rows redden here, which is the point**: it proves the pins of
  §6 are held up by a rule this slice implements, not sitting inert.
* **K5 — drop `ENDFLAG` (R-LS7)**: delete `ld a,1 / ld (ENDFLAG),a`.
  RED (1): `lse-inprog` → ` 13  0 `.
  GREEN (33) — and 🔴 **`lse-tail` IS PREDICTED TO STAY AT ` 0  0 `.** D-DELETE's
  K5 found exactly this split: `ENDFLAG` ends the *program*, while the handler's
  plain `ret` abandons the rest of the *line* because nothing marshals the cursor
  back. Predicting the split in advance this time is the test of whether that
  finding generalises. If `lse-tail` moves, the two verbs' mechanisms differ and
  R-LS7 needs splitting the way R-D8 did.
* **K6 — the ASCII-SAVE leak (§3.3)**: revert the two SAVE call sites to
  `call list_walk`.
  🔴 **PREDICTED RED: ZERO of the 34 rows.** The `lnblank` battery never saves,
  so it cannot see a `LIST`-range leaking into `SAVE",A"`. **That prediction is
  the finding, not a failure of the knife** — if it holds, the hazard §3.3
  removes is gated by *nothing* in the tree, and this slice must either add a row
  that lists a range and then saves, or say plainly that it did not.
* **K7 — aimed at the JUSTIFICATION, not the code.** §3.1 claims (c) needs
  ~107 B against 82 free. Build the resident variant and read `make basic-reloc`'s
  page-1 figure; scored against §3.1's table, not against the battery.

⚠️ Every knife reverted against **the build it cut**, never `git checkout` (that
reverts the slice), and the restoration verified by hashing all touched sources
**and both ROMs** against a pre-knife record. Never `copy2` — it preserves mtime,
`make` skips the rebuild, and the check hashes the stale knifed ROM.

### 7.1 Results

| knife | predicted RED | measured | verdict |
|---|---|---|---|
| K1 | `lst-openhi` → `<nothing listed>` | see below | |
| K2 | `lst-all` → `<nothing listed>` | exactly that; 33 green | ✅ |
| K3 | `lst-one` → `B\|C\|D`, `lst-miss` → `C\|D`, `lst-zero` → `A\|B\|C\|D` | all three exact; 31 green | ✅ |
| K4 | `lst-comma` → `10 REM A`, `lse-comma` → ` 0 `, `lst-dot` / `lse-dotedit` → `A\|B\|C\|D` | all four exact; 30 green | ✅ |
| K5 | `lse-inprog` → ` 13  0 ` | exact; **`lse-tail` did NOT move**, as predicted; 33 green | ✅ |
| K6 | **zero** of 34 rows | zero — and the *disk row* fails | ✅ prediction exact |
| K7 | (c) ≈ 107 B > 82 B | (c) ≈ **128 B** > 82 B | ✅ verdict holds, estimate was 21 B out |

🎯 **K5 PREDICTED D-DELETE'S SPLIT INSTEAD OF DISCOVERING IT.** D-DELETE's own K5
found `dlt-tail` unmoved by an `ENDFLAG` cut and had to split R-D8 into two
mechanisms *after* the fact. Here the same split was written into §2's R-LS7 and
into K5's predicted-GREEN set **before** the build, and `lse-tail` stayed at
` 0  0 `: `ENDFLAG` ends the **program**, while the handler's plain `ret`
abandons the rest of the **line** because nothing marshals the cursor back. The
`ret` still cannot be knifed — cutting it to `jp exec_stmt` would re-dispatch the
same `LIST` token forever — so `lse-tail` remains gated structurally, held up
only by its control `lse-tailctl` (` 9  0 ` on all three sides).

🔴 **K3 AND K2 SEPARATE THE TWO DEFAULTS IN BOTH DIRECTIONS.** K2 removes the
bare-`LIST` default and reddens `lst-all` alone, leaving `lst-openhi` green; K3
removes R-LS1 and reddens `lst-one`/`lst-miss`/`lst-zero` while **`lst-same`
stays `B`** — its high end comes from the `-` arm, not from R-LS1. Neither rule
is doing the other's work.

🎯 **K4 PROVES THE `.` PINS ARE LOAD-BEARING.** Both `lst-dot` and `lse-dotedit`
move when the trailing-junk check is removed, so their pinned `syntax error` is
a consequence of R-LS6 — a rule this slice implements — and not an inert value
that could drift for an unrelated reason.

### 7.2 🔴 K6 — the hazard was gated by NOTHING, and the tree's apparent guard is not one

K6 had to be run **twice**, and the difference between the two runs is the whole
result.

**K6, both SAVE call sites reverted to `list_walk`: the build FAILS.**
`list_all` and `lst_setall` lose their only callers, and `check_dead_code.py`
reports **2 unreachable spans**. That looks like the tree catching the
regression — and it is not. It catches the *shape* (is `list_all` called at
all?), not the *hazard* (does a `LIST` range leak into a save?).

**K6a, the DISK site only — the realistic regression — builds clean:**

| gate | result |
|---|---|
| `check_dead_code` | **0 dead** (the tape site keeps `list_all` reachable) |
| the whole 34-row `lst`/`lse` battery | **IDENTICAL — zero rows moved** |
| `disk_probe_save_ascii.py` | **FAIL** — `<None>`, nothing printed |

🔴 **THE PREDICTION WAS EXACT, AND IT IS THE FINDING.** A one-line regression on
the disk save path passes the dead-code gate, passes every row this slice added,
and is invisible to the entire `lnblank` corpus — because that corpus never
saves. The `list 20` inserted into
[`probes/disk/disk_probe_save_ascii.py`](../probes/disk/disk_probe_save_ascii.py)
is the only thing in the tree that sees it, and its `<None>` is a *truncated
saved file*: the reload restored a program with lines 10 and 30 gone, so nothing
printed at all.

⚠️ That row was verified GREEN on the unknifed build **before** it was trusted as
a knife detector. A gate that has never been seen to pass cannot be read as
meaningful when it fails.

⚠️ **K1 DID NOT FAIL — IT REFUSED TO CUT.** Its first pattern did not match the
source (the comment layout differed from the draft), and `_kn.py` aborts when a
pattern occurs anything other than exactly once rather than silently editing
nothing and scoring a green battery as "no effect". A knife that cannot find its
own target must abort; a knife runner that reports "nothing to see" is the
failure mode D-RETLN deleted its runner over.

⚠️ **Run the whole 34-row battery for every knife**, not just its predicted-RED
subset: a knife scored only against what it was expected to break cannot detect
that it broke something else instead.

## 8. Gates

Full corpus against the shipped bytes. Most exposed: `lnblank-say-acceptance`
(this slice's own), **`diskbasic-acceptance` and the `CAS:` suite** (the
`list_all` split, §3.3), and `basic_probe_list.py`'s 8 functional LIST probes.

Measured on the shipped bytes, rebuilt from clean after the last knife was
reverted and hash-verified against the pre-knife build:

`unit-test` **55/55** · `deadcode` **0 dead** both builds ·
`lnblank-say-acceptance` **108/108**, 7 pins · `lnblank-echo` green ·
plus `lnblank-acceptance REPEAT=2`, `logicops`, `float`, `array`, `arrdim`,
`clearpool`, `badfnum`, `lof`, `chancost-characterize`, `linemax`,
`sysvarsweep`, `error-trap`, `abort`, `stop`/`strig`/`key`-trap, `fat-error`,
`diskbasic`, `bdos` — see the commit message for the run.

⚠️ `lnblank-echo` reports `dec-eolctl` MANGLED on **all three sides**
(`'20 REMX '`, a trailing blank). It is non-gating, it is D-DECBLANK's row, it
reads identically on every side, and the pass line
(*"every gating payload typed verbatim on every side"*) is green. Recorded here
rather than left for the next reader to rediscover.
