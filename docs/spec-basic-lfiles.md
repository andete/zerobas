<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-LFILES — `LFILES`, and the carve that pays for it

Measurement: [`lptverb-msx1-characterization.md`](lptverb-msx1-characterization.md)
§4 (R-LF1..R-LF6). Predecessor: [`spec-basic-lptverb.md`](spec-basic-lptverb.md),
which landed `LPRINT`/`LPOS`, measured `LFILES` in full, and **refused to
implement it with a number** — ≈42 B against 10 B of combined headroom.
Carve scout: [`rom-region-structure-review.md`](rom-region-structure-review.md).

This closes the last word of `TODO.md`'s printer-surface residual.

---

## 0. The question, and why it is two questions

> `LFILES` — the LAST of the printer surface. ≈42 B needed against 10 B of
> combined headroom, so **the next slice to touch main BASIC must carve before it
> can add.**

* **Q1 — where do the bytes come from?** §2. This is the first job and it is not
  optional; §1 measures the wall before anything is designed.
* **Q2 — what does `LFILES` have to do?** §3, off R-LF1..R-LF6.
* **Q3 — what does the fix touch that this battery does NOT measure?** §2.2. The
  answer turned out to be a shipped verb with an unmeasured divergence.

---

## 1. The wall, measured from clean at `b5f4135`

`rm -rf build && make basic-reloc` ([[measure-the-wall-from-clean]] — D-LPTVERB's
own §6.7.4 is why that is written as a command and not as a habit):

| region | free |
|---|---|
| main page-0 low | **3 B** |
| main page 1 | **7 B** |
| sub page 0 | 3869 B |
| sub page 1 | 1824 B |

🔴 **The two main regions are ONE budget of 10 B, not two of 3 and 7.** They are
co-mapped slot-0 pages, so a pressure-placed leaf moves between them freely;
D-LPTVERB §6.3 predicted them independent and was wrong by construction. Any
number in this spec that treats them separately is wrong the same way.

### 1.1 🔴 One line of the ≈42 B estimate was already wrong, in our favour

D-LPTVERB §3.4 priced `LFILES` at ≈42 B including **9 B of `kwtable.inc`**. The
crunch table has not been main-resident since the sub-ROM arc's wave 3 —
`sub/sub.asm` is its sole include site and `basic/kwtable.inc`'s own header says
so — so a keyword entry costs **zero main bytes**. The honest main-side estimate
for a naive `LFILES` is therefore ≈33 B, plus the ≈12 B R-LF6 turned out to cost
(§2.2), against **10 B**. Still does not fit, and by enough that the conclusion
does not depend on the estimate.

### 1.2 Files this slice ADDS, against the sweep filters

* `docs/spec-basic-lfiles.md` — `docs/` is in `audit_citations.py`'s `SWEEP_DIRS`,
  `.md` is in `SWEEP_EXTS`. **+1 swept file: 705 → 706.**
* No new `.py` and no new `.asm`: the probe, the characterization and the tenant
  file all exist. So `injector-check` stays at **327**.
* ⚠️ **Seed prediction, stated as a number to be checked.** `check_dead_code.py`
  seeds the main walk with every identifier appearing anywhere under `sub/` and
  `tools/`, comments included. This slice writes `sub/dirverb.asm` prose that
  names the resident head **`do_files`**, which is a main label and is *not*
  currently mentioned anywhere sub-side. So main seeds should go **286 → 287**
  and sub stay at **102**. D-EDITVERB got exactly this wrong once and D-LPTVERB
  got it right once; it is a prediction, not an assumption.

---

## 2. The carve

### 2.1 🎯 The FILES directory walk becomes a fourth `dirverb_tenant` op

The disk/file cluster eviction ([[diskfile-cluster-eviction]]) landed KILL and
NAME as `dirverb_tenant` (`SUBROM_IDX_DIRVERB = 13`, sub page 1) in Phase 2 and
**dropped FILES**, for a reason recorded at the time:

> its emit loop interleaves `CHPUT` + main-resident `print_crlf`, a head/body fork

That reason is disposable now, and this slice is what disposes of it:

* a **page-1 tenant keeps page 0 mapped**, so `CHPUT` ($00A2) and `LPTOUT`
  ($00A5) are both reachable — `errmsg_tenant` already emits whole error messages
  through `CHPUT` from exactly this island, and the closure checker enforces the
  rule rather than trusting it;
* `print_crlf` is main page 1 and unreachable — but it is `pchar(13)` +
  `pchar(10)`, and `FILES` only ever runs with `PRDEST = 0` (`exec_stmt` zeroes it
  at the top of **every** statement), so `pchar` there *is* `CHPUT`. Emitting 13
  and 10 through the tenant's own sink is **behaviour-preserving, not a
  compromise**;
* `fat_mount`, `read_sector` and `name_cmp` are all **sub-local** in that build
  (`basic/fat-prim-body.inc` is included in `sub/fatprim.asm`, which precedes
  `dirverb.asm`), so the walk costs no nested marshalling. That is the same
  property that made Phase 2 cheap.

The head/body split is the one the arc already forces: `eval`/`parse_disk_fcb` and
the statement tail stay **main-resident**, the sector work and the emit go
**sub-side**, and results ride `DISKOP_STATUS` because Cy cannot survive CALSLT.

### 2.1.1 Sized from `build/basic-reloc.sym`, not from arithmetic

`ex_files` through `de_ext` is one contiguous span, `$6B3A..$6C27` = **237 B**,
and every label in it is private to the verb:

| label | B | disposition |
|---|---|---|
| `ex_files` / `do_files` / `df_nofilespec` | 4 / 29 / 18 | **head** — rewritten, stays resident |
| `df_secloop` / `df_entloop` / `df_do_emit` / `df_nextent` | 23 / 38 / 3 / 27 | moves |
| `df_end` / `df_endline` / `df_io_pop` / `df_entptr` | 9 / 4 / 4 / 16 | moves |
| `df_emit` / `de_sep` / `de_field` / `de_name` / `de_ext` | 21 / 7 / 2 / 20 / 12 | moves |

The new resident head — the `DISKSLOT_OK` test, the filespec parse, one
`subrom_call`, and the status dispatch — counts to **≈68 B** by instruction, plus
**3 B** for `LFILES`'s `stmt_table` row. §4.1 predicts the measured result and §6
replaces the estimate with `build/basic-reloc.sym`, because a size from arithmetic
is not a measurement ([[linemax-slice]]).

### 2.1.2 The carve's control is a set of GREEN gates, not a knife

A knife that removes the `subrom_call` reddens the whole `lfl-` battery *and*
every `FILES` row, which localises nothing. The carve's falsification is the
other direction and it already exists: **`FILES`'s screen output must not
change by one byte.** `disk_probe_files.py`, `disk_probe_files_wildcard.py`,
`diskbasic-acceptance` (34 rows, CF-3300 oracle differential, `FILES` and
`FILES(wild)` among them), `fat-error-acceptance`'s `fat-alive` control
(`FILES"A:HI.TXT"`) and this battery's own `lfl-ctlf` all read that output today
and must read it identically afterwards.

### 2.2 🔴 The fix touches `FILES`, so `FILES` got measured — and diverged

R-LF4 is a rule about `LFILES`: a no-match prints nothing to the printer and
`File not found` to the screen. The cheapest implementation puts the no-match test
in the **shared** walk, which means it lands on `FILES` too — a verb the `lfl-`
battery did not measure. **A change to an unmeasured verb is a change made blind.**

So `lfl-nonef` (`FILES"NOSUCH.XXX"`, screen readout) was added to the battery and
written down as a **fork with two named dispositions, before the reading**:

| if the CF-3300 answers | then |
|---|---|
| `File not found` | the message belongs in the shared walk; `FILES` gets it too |
| nothing | the message goes behind the `LFILES` op alone and `FILES` keeps its silence |

**Measured: `File not found`** — and zerobas answers **nothing at all**. Recorded
as **R-LF6**. So the first branch is taken, and the slice also closes a divergence
in a verb that has shipped since Phase 2 and that nothing had ever asked this
question.

⚠️ And it puts a caveat on `lfl-none`, the one `LFILES` row that already **agreed**
at the baseline: an empty printer log is what a machine with no `LFILES` at all
prints for every input. It agreed for the wrong reason
([[kwsweep-msx1-denominator]]).

### 2.3 What the message costs: **5 B**, because ERR 53 already prints

zerobas has no `File not found` string and does not need one. D-MSGSUB hosts the
fourteen never-raised MSX codes in `sub/errmsg.asm`, and **53 is one of them**
(`em_file_notfound`). `err_msgtab[53]` is `err_subhosted`, a single `MSGESC_SUB`
byte. So the whole main-side cost of the message is:

```
                ld      a,53
                jp      raise_error
```

⚠️ `raise_error`, not `load_error`. That makes the no-match a **real MSX error**:
`ERR` reads 53 and `ON ERROR` traps it. Neither is measured by any row here —
stated as a consequence of the mechanism, not claimed as a rule.

⚠️ **`KILL` is left alone**, and deliberately. `do_kill`'s no-match comment says
*"File not found"* and its code says `jp z,load_error`; pointing it at the new
label would cost 0 B and would change an **unmeasured** verb on the strength of a
reading taken for a different one. `fat-error-acceptance` pins `kill-missing` to
`load error` on purpose. Filed as a residual, not fixed here.

### 2.4 The arm this slice does NOT change, and says so

The tenant seeds "matched" to 1 when **no** filespec was given, so a bare `FILES`
or `LFILES` on an empty directory prints nothing rather than `File not found` —
today's behaviour, unchanged. That case is **unmeasured**: it needs an empty disk
fixture this battery does not have, and R-LF6 was taken with a pattern. The
conservative arm is the one that changes nothing, and this is the note that says
which arm that is ([[a-hand-listed-denominator-is-a-scope-claim]] — the rows the
battery cannot reach are part of its scope claim).

✅ **MEASURED AND CHANGED 2026-08-07 by D-DSKMSG** (R-LF7,
[`lptverb-msx1-characterization.md`](lptverb-msx1-characterization.md) §4.2):
the CF-3300 raises `File not found` there too, so the seed is now unconditional
and the `xor` is gone (−4 B of sub page 1). **"The conservative arm" was the
WRONG arm** — which is the useful part of this note, because it was written
without a way to know, and said so.

---

## 3. Design

### 3.1 The resident head — one head, two verbs, one selector byte

`ex_files` and `ex_lfiles` differ **only** in the `DISKOP_OP` value they load,
which is also the tenant's sink selector. No new RAM cell: the mode rides the
selector that already had to be marshalled.

```
ex_files:       ld      a,DISKOP_SEL_FILES      ; 2 -> screen
                jr      df_head
ex_lfiles:      ld      a,DISKOP_SEL_LFILES     ; 3 -> printer
df_head:        inc     hl                      ; past the token
                ld      (DISKOP_OP),a
                <DISKSLOT_OK or a / jp z,load_error>
                <optional "filespec" -> parse_disk_fcb, FILES_HASPAT>
df_nofilespec:  push    hl                      ; guard the text cursor
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_DIRVERB
                call    subrom_call
                pop     hl
                jp      c,load_error            ; sub-ROM absent
                ld      a,(DISKOP_STATUS)
                or      a
                jr      z,df_notfound           ; 0 -> nothing matched
                dec     a
                jp      nz,load_error           ; 2 -> mount / DSKIO error
                jp      exec_stmt               ; 1 -> ok
df_notfound:    ld      a,53
                jp      raise_error             ; "File not found" (sub-hosted)
```

⚠️ `DISKOP_OP` is written **before** `parse_disk_fcb`, and that is checked, not
assumed: `parse_disk_fcb`'s tenant (`fcbname`) aliases `DISKOP_HL`/`DISKOP_STATUS`
as `BN_PTR`/`BN_STAT` and touches `DISKOP_OP` nowhere. Our own `DISKOP_STATUS`
read happens strictly after our own `subrom_call`, so the alias is dead by then —
the same "never in flight at once" argument `sysvars.inc` already records for
`CM_STATUS`/`LE_STATUS`.

⚠️ The `DISKSLOT_OK` test sits **before** the `push`, so its `jp z,load_error`
cannot leak a stack slot.

### 3.2 The tenant — `DISKOP_SEL_FILES` / `DISKOP_SEL_LFILES`

A fourth and fifth op on the existing `dirverb_tenant`: no new index, no new
`SUB_PARTS` entry, no new entry-table row. The body is the moved walk with three
mode branches, all of which cost **sub-ROM** bytes:

* **the sink.** One `tf_out` helper reads `DISKOP_OP` and calls `CHPUT` or
  `LPTOUT`. Every emit site goes through it. For `FILES` this is byte-identical to
  today's `call CHPUT` (§2.1).
* **the layout (R-LF1).** Screen: the `CSRX`/`LINLEN` separator-or-wrap decision,
  unchanged. Printer: **no separator and no wrap at all** — R-LF1 makes the
  printer path *simpler*, and the wrap arithmetic reads the screen cursor and the
  screen width, neither of which a printer moves.
* **the terminator (R-LF2).** Printer: each entry is followed by `' '` then CR
  then LF. ~~Screen: nothing per entry, and `df_end`'s `CSRX != 1` test
  terminates the final line as today.~~
  🔴 **BOTH SCREEN CLAUSES RETRACTED 2026-09-12 (D-DFEND), and they were claims
  about THIS CODE, not about the reference.** The CF-3300 emits the trailing
  space on the SCREEN too — it is a trailing space, not a separator emitted
  before the next field — and it does **not** terminate the final line. The two
  arrangements are indistinguishable row by row and differ only where the cursor
  comes to REST: column 19 after `FILES"PROG.BIN"` and 31 after a bare five-entry
  listing, against 18 and 30 for the separator form and a whole row further for
  the terminator ([readings](../scratchpad/kwdrain_dfend_after.out)). The printer
  still skips the terminator — every entry has already ended its own line.

`DISKOP_STATUS` carries three states back: **0** nothing matched (→ ERR 53),
**1** ok, **2** mount/DSKIO error (→ `load_error`, today's disposition).

### 3.3 What is NOT done, and why each is a choice

* **The sink is never re-pointed.** `PRDEST`/`PRDEV` are untouched; the tenant
  cannot reach `pchar` anyway. R-LF5 ("the screen sink is restored for the next
  statement") therefore holds **by construction**, which is also why it has no
  knife — §5 says so rather than inventing a cut that would pass.
* ~~**`LPTPOS` is not maintained by `LFILES`.** ... Every `LFILES` entry ends
  with CR/LF, so the head is at column 0 when the statement ends and the R-LP16
  flush at command level is a no-op either way. No row measures it~~
  🔴 **RETRACTED 2026-09-12 (D-DFEND). The premise is true and the conclusion
  does not follow.** The head is at column 0 when the statement ends **only if
  nothing PARKED it mid-line first**. `LPRINT"AB";` then `LFILES` read `LPOS` **2**
  here against **0** on the CF-3300, and R-LP16's flush then put two extra bytes
  on the printer (79 against 77) — so the choice was observable in both the
  returned value and the byte stream
  ([`scratchpad/kwdrain_lfflush.py`](../scratchpad/kwdrain_lfflush.py),
  [readings](../scratchpad/kwdrain_lfflush.out), with the head-at-rest and the
  flush-alone arms agreeing on both machines).
  ⚠️ **"No row measures it" IS THE PART THAT MADE THIS SAFE TO WRITE, and it was
  true when written.** A choice whose only guard is the absence of a row is one
  nobody revisits until a row appears [[a-justification-parenthesis-is-an-unrun-claim]].
  🟢 **`df_end` now zeroes `LPTPOS` — but ONLY when the walk emitted an entry.**
  On a no-match both machines print `File not found`, send nothing to the printer
  and leave the head parked, so R-LP16 must still fire; an unconditional store
  would have fixed one arm and broken that one. `DISKOP_STATUS` already carries
  the condition.
* **The tenant emits under DI.** `subrom_call` wraps the call, so `CHPUT` for a
  whole directory listing now runs with interrupts off where it previously ran
  with them on. `errmsg_tenant` and `title_tenant` already do exactly this, and
  `read_sector`'s `dskio_calslt` EIs mid-walk anyway — the `htimi_guard` seam
  exists because a VBLANK *can* land inside a page-1 tenant. Named because it is a
  real change of condition, not because it is novel.

---

## 4. Predicted GREEN, at exact values — fixed BEFORE the change

1. `rm -rf build && make basic-reloc`: page 1 **7 B → between 140 and 200 B**;
   low **3 B unchanged** (nothing this slice writes is pressure-placed low).
   Stated as ONE budget: **10 B → 150..210 B combined**.
2. Sub page 0 **3869 B unchanged**; sub page 1 **1824 B → between 1580 and
   1680 B**.
3. `kwtable` pin: **1058 → 1067 B**, and the delta must be **exactly 9** —
   `[klen][6 chars][tlen][1 token]` for `LFILES`. A delta that is not 9 says the
   table gained something else.
4. `test_stmt_dispatch.py`: **79 → 80** entries, all dispatching.
5. `audit-citations`: **706** files swept, self-tests 10/10 11/11 12/12 14/14,
   4 advisory all acknowledged.
6. `deadcode`: main **286 → 287** seeds → 0 dead; sub **102** → 0 (+1
   allowlisted). §1.2 names the one new seed.
7. `injector-check`: **327** files, 4 exempt, 3 RECORDs, 0 offenders.
8. `lptverb-acceptance` with **no `ONLY=`**: **39/39** rows (16 `lpr-`, 10 `lps-`,
   5 `scr-`, 8 `lfl-`), and the `NOT GATED: lfl-` line **gone** because the hole
   is closed. Baseline for the `lfl-` battery alone is **3/8**.
9. 🔴 **The carve's control set, all unchanged:** `diskbasic-acceptance` **34/34**
   (incl. `FILES` and `FILES(wild)`), `fat-error-acceptance` **8/8 + directory
   check**. `FILES`'s screen bytes are the thing being preserved and these are
   what read them.
10. `lnrx-lfiles` **fires**: `20 LFILES 10` goes from `L<B7> <0F><0A>` (a stray `L`
    plus the genuine `FILES` token) to the reference's own `<BB> <0F><0A>`, so it
    leaves `INFORMATIONAL` for the ordinary gating set — the tenth cohort to fire
    and be graduated rather than updated. `lnrx-wait` survives as the control of
    that shape, and the `lnrx` informational set is then **empty of L-words**.
11. Every other corpus gate at its recorded value: `unit-test` **58**,
    `latch` 16/16, `lnblank` **536/536** (`REPEAT=2`, since this slice adds a
    crunch-table entry), `lnblank-say` 204/204, `logicops` 193/193, `float` ALL
    PASS, `linemax` 60/60, `dexp5` 16 ALL PASS, `editverb` 61/61.
12. All four ROM hashes change **except `build/disk.rom`**, which
    [`spec-basic-editverb.md`](spec-basic-editverb.md) §6.7.2 established cannot
    move for a slice that touches only `basic/` and `sub/`. Baselines at
    `b5f4135`: `disk.rom 2c630d3d…`, `sub.rom 1ddd0fe8…`,
    `basic-reloc.rom fdb88aaa…`, `zerobas-main-eu.rom 3f8f9361…`.

## 5. Predicted RED, with knives

Each knife names a predicted RED set **and** predicted GREEN survivors; a knife
that reddens everything has localised nothing. **Run twice.** The subject is
`basic_probe_lptverb.py --gate --sides cf3300,zb --only lfl-`, invoked directly:
the runner reads the **probe's** exit code, never `make`'s, because `make` exits 2
for any failed recipe and would flatten a tree fault into an instrument fault
([[injjudge-slice]]). The restore point is a **scratchpad snapshot** taken after
the change and before the first cut, never `git checkout --`
([[knife-cleanup-restores-from-head]]). ⚠️ And the baseline is captured through the
probe's **own parse path**, so an empty baseline refuses the run rather than
scoring every cut a CUT (D-LPTVERB §6.7.4).

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K1** | `kwtable.inc`'s `"LFILES"` → `"LFILEZ"` — the word stops crunching, and nothing is orphaned | `lfl-all`, `lfl-wild`, `lfl-noneb`, `lfl-sink` | `lfl-ctlf`, `lfl-ctlp`, `lfl-nonef` — `FILES` is untouched — and ⚠️ `lfl-none`, which reads `<nothing printed>` either way and is the row that CANNOT tell an absent verb from a correct one |
| **K2** | `tf_out` always calls `CHPUT` (layout kept, sink not) | `lfl-all`, `lfl-wild`, `lfl-sink` → empty log | `lfl-ctlf`, `lfl-ctlp`, `lfl-none`, `lfl-noneb`, `lfl-nonef` — the knife that isolates the SINK from the LAYOUT |
| **K3** | the printer path takes the screen separator/wrap branch (R-LF1's knife — D-LPTVERB's unrun K8, re-aimed onto the design that actually shipped) | `lfl-all`, `lfl-wild`, `lfl-sink` → three-per-row on the printer | the same five as K2 — the knife that says a sink re-point alone would NOT have passed |
| **K4** | drop the `' '` before the CR/LF (R-LF2) | `lfl-all`, `lfl-wild`, `lfl-sink` | the same five — same RED set as K3 by construction, a FINER claim over it. 🔴 **D-DFEND (2026-09-12) MOVED WHAT THIS CUTS**: the space is now emitted on BOTH sinks from one site, so the same cut also takes the SCREEN's inter-entry space and the kwsweep `files` row with it — a WIDER red set than when this knife was written, and the knife is stronger for it, not stale |
| **K5** | the tenant ignores `FILES_HASPAT` and emits every entry (R-LF3) | `lfl-wild`, `lfl-none`, `lfl-noneb`, `lfl-nonef` | `lfl-all`, `lfl-ctlp`, `lfl-sink` — and ⚠️ `lfl-ctlf`, which lists everything anyway |
| **K6** | `df_notfound` → `jp load_error` (R-LF4/R-LF6's message) | `lfl-noneb`, `lfl-nonef` → `load error` | `lfl-none` (the log is empty either way — the pair that proves a printer-log row is blind to half its rule), `lfl-all`, `lfl-wild`, both controls |
| **K7** | the tenant seeds `DISKOP_STATUS` from `FILES_HASPAT` no longer — always 0 | *nothing in this battery* | everything — ⚠️ **this is a PREDICTED MISS, written down as one**: §2.4's arm needs an empty-directory fixture the battery does not have. Recorded as an unexercised arm rather than left implicit |

🔴 **K3 is the knife this slice exists to have**, and it is the one D-LPTVERB filed
and could not run. R-LF1 says the printer form is one entry per line; the single
most likely implementation is `FILES` with the sink moved, which would put the
screen's three-per-row layout on the printer and pass any battery that only
checked *which device* got the bytes. K3 builds exactly that mistake.

⚠️ **R-LF5 has NO knife, by construction** (§3.3): the implementation never
re-points `PRDEST`/`PRDEV`, and `exec_stmt` zeroes `PRDEST` at the top of every
statement, so a cut that sets the sink would still leave `lfl-sink` green. Stated
as structurally unknifeable with the reason, not re-aimed into something that
would pass ([[rule-gated-structurally-has-no-knife]]).

⚠️ **And the carve has no knife either, for the reason in §2.1.2** — its
falsification is a GREEN control set (`FILES`'s bytes unchanged across four
independent readers), which is the honest instrument for "this move changed
nothing".

---

## 6. As-built

### 6.1 Predictions, scored

| § | predicted | measured |
|---|---|---|
| 4.1 | page 1 **7 → 140..200 B**; low **3 B unchanged** | **7 → 194 B**; low **3 B** ✅ — one budget, 10 → 197 B |
| 4.2 | sub p0 **3869 unchanged**; sub p1 **1824 → 1580..1680** | 🔴 **BOTH HALVES WRONG, and the baseline itself does not reproduce** — §6.3 |
| 4.3 | `kwtable` **1058 → 1067**, delta exactly **9** | **1067**, delta **9** ✅ |
| 4.4 | `test_stmt_dispatch` **79 → 80** | **80 entries, 80 dispatch OK** ✅ |
| 4.5 | `audit-citations` **706** files swept | **706**, self-tests 10/10 11/11 12/12 14/14, 4 advisory ✅ |
| 4.6 | `deadcode` main **286 → 287** seeds, sub **102** | 🔴 **286 → 286** — §6.4 |
| 4.7 | `injector-check` **327** files, 0 offenders | **327 / 4 exempt / 3 RECORDs / 0** ✅ |
| 4.8 | `lptverb-acceptance` **39/39**, no `NOT GATED: lfl-` line | **39/39** on three sides ✅; baseline for `lfl-` alone was **3/8** |
| 4.9 | `diskbasic-acceptance` **34/34**, `fat-error-acceptance` **8/8** | **34/34**, **8/8 + directory check** ✅ — the carve's control set |
| 4.10 | `lnrx-lfiles` fires and graduates | fired, `<BB> <0F><0A>` on all three sides, graduated ✅ — and §6.5 is what it found on the way |
| 4.11 | every other corpus gate at its recorded value | `unit-test` **58** (after §6.6), `latch` 16/16, `lnblank` **536 → 539** (§6.5), `lnblank-say` 204/204, `logicops` 193/193, `float` ALL PASS, `linemax` 60/60, `dexp5` 16, `editverb` 61/61 ✅ |
| 4.12 | all four ROM hashes change **except `disk.rom`** | `disk.rom` **2c630d3d… unchanged** ✅; `sub.rom` 1ddd0fe8 → **01805491**, `basic-reloc.rom` fdb88aaa → **29032918**, `zerobas-main-eu.rom` 3f8f9361 → **50a1eaf6** |

The head measured **69 B** against §2.1.1's 68 B estimate (`ex_files` 4 +
`ex_lfiles` 2 + `do_files` 33 + `df_nofilespec` 25 + `df_notfound` 5), and the
carve is **237 B out, 69 B back, 3 B for the `stmt_table` row, and ~29 B of dead
`name_cmp` shim** (§6.6).

### 6.1.1 ➕ Two gate figures this slice did NOT record — added 2026-08-07 by D-SUBWALL

⚠️ **Not a correction and not part of the original run.** This slice moved both of
the figures below and recorded neither, so the last documents that mention them —
[`spec-basic-editverb.md`](spec-basic-editverb.md) §6.7 and the six JUDGE-arc specs —
became the newest *recorded* values while no longer being the *current* ones. That gap
is what sent D-SUBWALL's own baseline table two and four commits stale
([`spec-subwall-readout.md`](spec-subwall-readout.md) §6.5), so it is filled here
rather than left for the next slice to trip over.

**Measured at `0cbf495` from a removed `build/` on 2026-08-07, by D-SUBWALL, not by
D-LFILES:**

| gate | at `0cbf495` | previous recorded value |
|---|---|---|
| `check_tenant_closure` (resident ABI) | **122 + 4** | 122+4, unchanged since D-PINDATA |
| `check_tenant_closure --page0` | **718 + 15** | 718+15, unchanged |
| `check_tenant_closure --page1` | **582 + 41** | **564+41** at `b5f4135`; 522+41 through the JUDGE arc — **this slice's `dirverb_tenant` walk is the 564 → 582** |
| `preflight-check` | **181** spawn sites, **86** exempt, **95** require a guard, **95 guarded, 0 UNGUARDED** | 180 / 85 / 95 / 95 / 0 at `b5f4135` — **this slice is the 180 → 181** |

Both moves are this slice's own, and neither gate's verdict changed (0 escapes,
0 UNGUARDED):

* **the closure +18** is the evicted `FILES` walk entering the page-1 closure. An
  independent re-walk of `sub_p1_table` names **17** of them and no removals —
  `tnt_files`, `df_secloop`, `df_entloop`, `df_do_emit`, `df_nextent`, `df_end`,
  `df_entptr`, `df_crlf`, `df_emit`, `df_out`, `dfo_lpt`, `dfo_done`, `de_sep`,
  `de_field`, `de_name`, `de_ext`, `tf_ioerr`. ⚠️ That re-walk is not
  `check_tenant_closure.py` and its absolute counts differ from the tool's by a
  seed-handling offset, so **it accounts for 17 of the 18 and the residual was not
  chased**. Stated rather than rounded off.
* **the spawn site +1** is [`tests/test_wildcard.py:65`](../tests/test_wildcard.py:65),
  the second `pasmo` call added by §6.6 when `name_cmp`'s test was re-pointed at the
  `$0000`-based sub image. Classified `EXEMPT` (list literal, no `-machine`), which is
  why "require a guard" stays at 95.

🔴 **The lesson is the one D-SUBWALL had to learn twice**: an *un-recorded* number and
a *copied* number are indistinguishable to the next slice, because both look like a
number in a document. `preflight-check` and all three closure walks already print on
every `make basic-reloc` — the figures were simply never read off it.

### 6.2 🎯 The carve worked, and the knives say the verb is real

Six knives CUT at **exactly** the predicted RED set with **exactly** the predicted
GREEN survivors; the seventh missed as predicted. Both rounds byte-identical —
which, openMSX being deterministic, is not evidence of soundness. The named
survivors are.

| # | verdict |
|---|---|
| K1 | **CUT** — `LFILEZ`: all four subject rows die (`<nothing printed>`, `lfl-noneb` → `Syntax error`) while `FILES` holds on `lfl-ctlf`/`lfl-nonef` |
| K2 | **CUT** — `df_out` pinned to `CHPUT` empties the printer log with every screen row intact. The sink is separable from the layout |
| K3 | **CUT**, and it is the knife this slice existed to have — §6.2.1 |
| K4 | **CUT** — the trailing space alone: `'TEST    .BIN \r\n'` → `'TEST    .BIN\r\n'`, nothing else moves |
| K5 | **CUT** — no filespec filter: `lfl-wild` lists all five, `lfl-none`'s log fills, and `lfl-noneb`/`lfl-nonef` lose their message because a match was recorded |
| K6 | **CUT** — `load_error` instead of ERR 53 moves `lfl-noneb`/`lfl-nonef` to `load error` and **nothing else**, `lfl-none` included: the pair that proves a printer-log row is blind to half its rule |
| K7 | **MISS, predicted as a MISS before the run** — §2.4's empty-directory arm has no row, and saying so beforehand is the difference between an unexercised arm and an undiscovered one |

#### 6.2.1 🔴 K3: a sink re-point does not produce the screen layout — it produces neither

§5 predicted K3 would put "three-per-row on the printer". It does not. Measured:

```
correct : 'TEST    .BIN \r\nHI      .TXT \r\nPROG    .BIN \r\n…'
knifed  : 'TEST    .BINHI      .TXTPROG    .BINPROG    .BASPROG2   .BAS'
```

No separators, no line breaks, nothing. The reason is the sharper form of R-LF1:
the screen path's separator-and-wrap decision is driven by **`CSRX`**, and a
printer never moves `CSRX`, so every entry reads "column 0, first field on the
line" and the whole listing runs together on one line. The naive implementation
does not merely put the screen's layout on the wrong device — **it produces a
layout that exists on neither device**, because it is reading a cursor that is not
its own. The prediction understated the defect; the knife is what said so.

### 6.3 🔴 §4.2 was wrong twice, and the recorded sub baseline does not reproduce

**Wrong the first time, against a fact this spec states two sections earlier.**
§4.2 predicted sub page 0 unchanged. §1.1 had already established that
`basic/kwtable.inc` is a **sub-ROM page-0 tenant**, which is the whole reason the
9 B keyword entry costs no main bytes — and page 0 is therefore exactly where those
9 B land. Sub p0 moved by **−9, which is the entry to the byte**. The spec knew the
fact and the prediction did not use it: the same shape as D-LPTVERB §6.3 treating
two coupled walls as independent, one level down.

**Wrong the second time, in size.** Sub p1 went **1821 → 1542**, i.e. −279 for the
walk; §4.2's band was 1580..1680, so the tenant body is **38 B larger** than the
resident code it replaced allowed for. That is the mode branches (`df_out`, two
`cp DISKOP_SEL_LFILES` tests, `df_crlf`) landing sub-side, which is precisely what
the design wanted — but the band was written from the resident span and never added
them.

🔴 **And the baseline the prediction was written against does not reproduce.**
`3869` / `1824` are the figures D-LPTVERB and D-EDITVERB recorded. Rebuilt at
`b5f4135` the sub ROM measures **3852 / 1821**, by **two independent instruments
that agree exactly**: an `$FF` tail scan of the image, and zero-byte `__MEAS_SUB_*`
labels injected in front of each `ds $4000-$,$FF` / `ds $8000-$,$FF` — the pad-label
method [`rom-region-structure-review.md`](rom-region-structure-review.md) prescribes
precisely because an `$FF` scan can lie. Here they do not disagree; the *record*
does, by 17 and 3.

⚠️ So every sub-ROM wall figure in this project is a hand-carried number with no
gate behind it. `check_reloc.py` prints the two MAIN walls on every build from
`__MEAS_LOW_END`/`__MEAS_PAGE1_END`; the sub ROM has no such labels and no such
readout, so its figures are re-derived per slice by whatever instrument that slice
happened to use. **Filed as a residual**, not fixed here: adding the two labels
costs zero bytes but belongs in a slice that can also fix the readout and re-derive
the historical series, rather than in one that would leave two conflicting numbers
in the record with no account of which past figures were affected.

✅ **ANSWERED 2026-08-07 by D-SUBWALL**
([`spec-subwall-readout.md`](spec-subwall-readout.md)). The two labels landed,
`make basic-reloc` now prints all four walls, and the series was re-derived by
building all 436 commits since `sub/sub.asm` existed (424 built):

* the **17** is D-LPTVERB's own `LPRINT`+`LPOS` `kwtable` entries — which that
  slice measured, in the row below the one where it wrote "sub sides unchanged";
* the **3** is not a mis-measurement of anything: `p1 = 1824` occurs at **0 of 424**
  commits, and a different page end, a different pad convention, a stale
  `sub/basic-resident-abi.inc`, a stale `build/` and 2324−500 arithmetic are each
  tested and refuted. The true D-EDITVERB carve is **−503**;
* **the drift does not go back** — 104 of the 112 recorded sub-wall sites in this
  repo reproduce to the byte, including every figure from D-P0BASE backwards.
  Exactly two slices carry a wrong one, and this spec's own baseline table is where
  they stopped.

### 6.4 🔴 The seed prediction was wrong, and it was two errors cancelling

§1.2 predicted main seeds **286 → 287**, "the one new seed being `do_files`, named
in `sub/dirverb.asm`'s header". Measured: **286**, and the zero is a sum:

* **+1** — `print_crlf`, which the new tenant header names when it explains why the
  routine is unreachable from a page-1 island. It is a main label newly appearing
  in `sub/` prose, so it becomes a seed. `do_files` never did: the prose that was
  going to name it ended up naming the FILE instead.
* **−1** — `name_cmp` stopped being a main label at all when its shim died (§6.6),
  so it dropped out of `set(main.nodes) & external_names(['sub','tools'])`. It had
  been a seed for as long as `sub/fatprim.asm` has mentioned it.

Verified by diffing `external_names(['sub','tools'])` between HEAD and this tree
rather than by re-reading the total. **A net-zero seed count is not the same as an
unchanged seed set**, and a prediction stated only as a total cannot tell them
apart — which is the more useful half of this miss.

### 6.5 🔴 D-LPTVERB's `lnrx` graduation had never reached the code

`lnrx-lfiles` fired and graduated as predicted. On the way, the same edit found
that **`lnrx-lprint` and `lnrx-lpos` were still in `INFORMATIONAL`** — the set whose
membership `basic_probe_lnblank.py`'s verdict loop tests with
`if label not in INFORMATIONAL` before counting a row at all.

D-LPTVERB's spec §6.5, its commit message, and a paragraph in the probe itself all
state that both rows "left INFORMATIONAL to become ordinary gating rows". They did
not. For one whole slice the two rows agreed with the reference and **gated
nothing**.

The number is the proof: `lnblank` went **536 → 539** gating rows, +3. Had the
previous graduation landed, this slice's single new row would have made it +1.
Same family as [[review-fix-that-never-reached-the-tool]], and the corrective is
written into the probe: **a graduation is a deletion from that set literal, never
prose about one.**

### 6.6 🔴 The carve killed a shim, and its second consumer was not an `.asm` file

Deleting `do_files`'s walk left `name_cmp`'s ~29 B main-ROM marshalling shim with
no caller, so it had to go — the dead-code gate fails the build otherwise, which is
the difference between a carve and a leak. The denominator for "who calls
`name_cmp`" was walked as `call name_cmp` over `basic/*.asm` and `*.inc`, and
returned exactly one hit.

**It missed `tests/test_wildcard.py`**, which calls the label BY NAME through
`msxtest`'s sub-ROM bridge. Not a `call` site, so not a match — the
[[a-hand-listed-denominator-is-a-scope-claim]] shape, with the scope claim hidden
inside the *grep pattern* rather than the file list. `make unit-test` found it
(1 of 58 files failed), which is the argument for running the whole corpus rather
than the gates a slice believes it touched.

Fixed by pointing the test at the image where the body now lives — a `$0000`-based
`sub.rom`, the `test_msgsub.py` pattern — so it exercises the code every real caller
reaches instead of a marshalling layer that no longer exists. ⚠️ **And the re-pointed
test was falsified**: breaking `'?'` in `basic/fat-prim-body.inc` reddens 4 of its 8
match rows while all four negative rows correctly hold, so the fix reached the tool
([[review-fix-that-never-reached-the-tool]] again, in the direction that check
exists for).

### 6.7 Two stale claims corrected in passing, both about `FILES`

* `basic/files.asm`'s header and `basic/PROVENANCE.md` §FILES both said *"an
  optional `<filespec>` pattern argument is parsed-past and IGNORED — pattern
  matching is a later Phase-2 item"*, sitting directly above code that parses the
  pattern and applies it with `name_cmp`. Stale since the wildcard work landed.
* `tests/test_stmt_dispatch.py` carried *"LFILES is not here either … page 1 came
  out at 15 B"* — a figure that was already wrong when written (D-LPTVERB measured
  7 B) and a claim this slice makes false. Replaced by the row, not left standing.

### 6.8 What is left open

✅ **ALL FOUR CLOSED** — the sub-ROM walls by D-SUBWALL (2026-08-07) and the
other three by **D-DSKMSG** the same day,
[`spec-basic-dskmsg.md`](spec-basic-dskmsg.md). Each was blocked on a reference
reading, and every reading changed the answer: R-LS4's own "out-of-byte" clause
had no row; the empty directory turned out to be a **divergence**, not merely an
unexercised arm; and *"the fix is 0 B"* below is **false** (§4.1 there —
`fat_delete` collapses not-found, mount and I-O into one `Cy=1`, so the swap
would have re-pointed all three).

* ~~**R-LS4 is still UNKNIFED**~~ (D-LPTVERB §6.7.3) — untouched here.
* ~~**The sub-ROM walls have no gated readout** (§6.3).~~ ✅ **CLOSED 2026-08-07 by
  D-SUBWALL**, [`spec-subwall-readout.md`](spec-subwall-readout.md).
* ~~**`do_kill`'s no-match still prints `load error`**~~ where its own comment says
  `File not found` (§2.3), and `fat-error-acceptance` pins it. Unmeasured for
  `KILL`; ~~the fix is 0 B~~ once someone takes the reading.
* ~~**The empty-directory arm** (§2.4, K7) has no row and needs an empty-disk
  fixture.~~
