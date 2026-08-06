<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-EDITVERB — `RENUM` / `AUTO` / `LLIST`: the statement half

Measurement: [`docs/editverb-msx1-characterization.md`](editverb-msx1-characterization.md).
Predecessors: [`spec-basic-kwgap4.md`](spec-basic-kwgap4.md) (the token half),
[`spec-basic-delete.md`](spec-basic-delete.md),
[`spec-basic-listrange.md`](spec-basic-listrange.md).

---

## 0. The question

`TODO.md`'s first standing residual reads:

> `AUTO` / `RENUM` / `LLIST` / `DELETE` — **the STATEMENT half.** Tokens are
> byte-exact (D-KWGAP4); nothing executes them.

Three questions, in the order they have to be answered:

* **Q1** — is the item's own framing true? (**No, twice.** §2.1)
* **Q2** — can this harness put these verbs to a reference at all? D-KWGAP4
  filed that it cannot: *"`AUTO` is interactive and `LLIST` hangs an unplugged
  `LPTOUT`, so `SIDE_LOCK` refuses a reference."* (**It can.** §2.2)
* **Q3** — do they fit? D-KWGAP4 measured four dispatch rows at 3 B against a
  6 B page-1 wall and stopped there. (**Yes, with 94 B to spare.** §6.1)

---

## 1. The denominator

### 1.1 The verbs

**Three**, not four. `DELETE` shipped 2026-08-02 — §2.1.

The reference surface is the 23 `RENUM` rules, 10 `AUTO` rules and 7 `LLIST`
rules of the characterization, taken on the VG-8020 and re-asked on the
CF-3300.

The `$0E` reference sites `RENUM` must rewrite are **not** enumerated by hand.
R-RN6 is *"every `$0E`, wherever it stands"*, which is exactly the set the
tokeniser's own line-number mode produces — `branch_lineno`'s arming list plus
D-LNREF's four added arms. Enumerating the arming keywords would have been a
second, drifting copy of that list; walking every `$0E` in the token stream is
the same set by construction, and it is what both references do (R-RN19 is the
row that proves the walk is over TOKENS and not over BYTES).

### 1.2 The wall, measured from clean at `0b31baa`

| region | free |
|---|---|
| main page-0 low | **23 B** |
| main page 1 | **356 B** |
| sub page 0 | 3869 B |
| sub page 1 | 2324 B |

Page 1 binds. D-KWGAP4's *"the table rows alone do not fit"* was measured
against a **6 B** wall and is stale by two carves; the 3 B/row rate it measured
still holds.

### 1.3 Files this slice ADDS, against the sweep filters

* `docs/spec-basic-editverb.md`, `docs/editverb-msx1-characterization.md` —
  `docs/` **is** in `audit_citations.py`'s `SWEEP_DIRS`, `.md` is in
  `SWEEP_EXTS`. **+2 swept files: 699 → 701.**
* `probes/basic/basic_probe_editverb.py` — `probes/` is swept and `.py` is in
  `SWEEP_EXTS`. **+1: 701 → 702.**
* Everything else is an edit to a swept file.
* Nothing lands in `scratchpad/` (not swept) and nothing in `tools/` or `sub/`
  **prose** that the dead-code sweep roots on — but `sub/lineedit.asm` gains
  ~170 lines of comment, and `check_dead_code.py` reads comments for its
  `external_names`. Predicted seeds unchanged at main **285** / sub **102**;
  movement there is a finding about this slice's own prose, not about the tree.

---

## 2. Falsify by measuring

### 2.1 🔴 Q1 — the filed framing is wrong on both of its clauses

**Clause 1, *"nothing executes them"*.** `DELETE` executes, and has since
2026-08-02: `stmt_table` row, `ex_delete` head, `le_delrange` tenant, 33 gated
rows. Two places in the tree already said so —
[`basic/sysvars.inc`](../basic/sysvars.inc) at `LLIST_TOKEN` (*"THREE OF THE
FOUR are still not dispatched"*) and the `delete-range-slice` memory — and the
index line did not follow either. **The denominator was 4 and is 3.**

**Clause 2, *"cannot be put to a reference in this harness"*.** Refuted for
both verbs it names, in one spike each:

| filed | measured |
|---|---|
| *"`LLIST` hangs an unplugged `LPTOUT`"* | **true, and it is not the question.** openMSX's `printerport` takes a `logger` pluggable that reports READY unconditionally, so nothing blocks — and the log file is a strictly **better** readout than a screen scrape: no wrap, no scroll, CR/LF visible as bytes |
| *"`AUTO` is interactive"* | **true, and it is not the question either.** Line entry rides the ordinary `CHGET` path the KEYBUF injector already feeds; Ctrl-STOP rides the key matrix (row 6 bit 1 + row 7 bit 4) through `keymatrixdown`, the primitive the input-devices arc's `holds` mechanism already uses |

⇒ the same shape as [[filed-justification-is-a-claim]]'s eighth entry: both
claims are **accurate about a mechanism** and answer a question nobody needed
answered. The load-bearing question was *"can it be READ?"*, not *"does the
default configuration hang?"*.

⚠️ This is not free: the same stated reason keeps `LPRINT`, `LPOS` and `LFILES`
out of `kwsweep`'s executed set. That correction is §7.

### 2.2 The readouts, and the control each one needs

| battery | reading | the control that makes it attributable |
|---|---|---|
| `rnm-` | the screen **after the RENUM command's own echo** — not after the trailing `LIST`, which would make the reading the listing only and hide every message the verb printed | `rnm-noop`, a `RENUM` that is the identity, so a divergence in the argument rows cannot be a detokeniser divergence |
| `aut-` | the same, anchored on the `AUTO` command, so the reading spans the whole session including the `*` marker | `aut-ctl`, an ordinary typed line, so a divergence cannot be a line-editor divergence |
| `llt-` | **the printer log**, read back from inside openMSX | 🔴 `llt-ctl` — §2.3 |

### 2.3 🔴 The zerobas printer channel needed a control, and it is not `LPRINT`

`LPRINT` is a **`Syntax error` on zerobas too** (no `kwtable.inc` entry at
all), so an empty log on the zb side has two candidate causes: no `LLIST`, or
no working `LPTOUT`/`pchar` path. `OPEN"LPT:" FOR OUTPUT AS #1 :
PRINT#1,"CTL" : CLOSE#1` drives the sink through code that already ships, and
it writes `'CTL\r\n'` at `0b31baa`.

⇒ the sink works, so every empty `llt-` reading is attributable to `LLIST`
alone. Without this row the whole battery is
[[readout-blind-to-its-own-subject]] with the blindness on **our** side, where
a false *"agrees on `<empty>`"* is impossible but a false *"zerobas is broken"*
is not.

### 2.4 🔴 Two measurement rounds landed on cases where the rules COINCIDE

Both nearly shipped as settled:

* the first `RENUM` round used a program numbered `10 20 30`, which `RENUM`
  maps to `10 20 30`. **The identity agrees with every rule anyone could
  propose, including "RENUM does nothing."** Re-run at `1..9`.
* the `CONT` and `RENUM`-in-a-program rows had the same defect (`10 STOP / 20
  PRINT 5`, `10 RENUM / 20 REM B` are already at the target numbering). R-RN17
  and R-RN20 are stated only from cases where the lines actually move.

Same family as [[err21-no-resume-slice]]: *the wrong implementation can
reproduce the filed measurement perfectly.*

### 2.5 🔴 And the `&H0E0E` row had to be read twice

After `RENUM`, `1 A=&H0E0E` lists as `10 A=&HE0E`, which looks mangled and is
not — `&HE0E` is 3598 and so is `&H0E0E`; the detokeniser strips the leading
zero, **before** `RENUM` as well (that is the control the row was missing on
its first run). The rule is settled by the **absence** of a message: a byte
scan for `$0E` finds the constant's own low byte, reads `$0E $00` as the target
14, and must print `Undefined line 14 in 1`. Neither reference prints anything.

⇒ **R-RN19: the walk is token-aware.** This is the row that chooses the
implementation, and a byte scan would have passed every other row in the
battery.

---

## 3. Design

Costs are from `build/basic-reloc.sym`, not arithmetic.

### 3.1 `LLIST` — `LIST` with a different sink, and nothing else

`ex_llist` and `ex_list` are **one body**. The verb rides in `LE_OP`
(`LE_OP_LLSTRANGE = 4`, routed to the same `le_lstrange` parse), which the
tenant does not write, so the resident head reads it **back** after the call
and derives `PRDEST` from it — `LE_OP - LE_OP_LSTRANGE` is 0 for `LIST` and 1
for `LLIST`. That is why the sink costs **no new RAM cell**.

Two constraints, both from measurement:

* the sink is chosen **after** the parse. Set it before, and an `LLIST 10,20`
  (R-LL4) raised inside a program with a live `ON ERROR` would enter the
  handler with `PRDEST = 1` and print the handler's own output to the printer.
* `PRDEST` is restored to 0 after the walk (R-LL6). The REPL's defensive reset
  covers the prompt case but not a handler that runs first.

### 3.2 `RENUM` — a page-1 tenant, and a report loop

🎯 **`RENUM` never changes a line's LENGTH.** A line number is a fixed 2-byte
header field; a reference is a fixed 3-byte `$0E,lo,hi`. So every rewrite is in
place: no gap, no memmove, **no relink and no `vars_reset`** — which is also
what R-RN17 measured (variables and the `CONT` point both survive, where
`DELETE` clears them). That is what makes the whole verb affordable.

`LE_OP_RENUM = 5` in `sub/lineedit.asm`:

* **parse** → `RN_NEW` / `RN_OLD` / `RN_INC`, reusing `ldr_num` (so `.` works
  for free — R-RN21);
* **validate** (`lrn_order`): increment 0 → ERR 5; the new numbering strictly
  above the last line left alone → ERR 5; the last computed number past
  `LINENO_CEIL`, or a 16-bit wrap → ERR 5;
* **pass 2, references** — before pass 3, and the order is forced: a reference
  names an OLD number, so it can only be resolved while the headers still hold
  old numbers;
* **pass 3, headers.**

🔴 **The report loop.** `Undefined line <n> in <m>` is emitted once per dangling
reference (R-RN9), and rendering it needs `print_string` + `list_num`, which
are main page 1 and unreachable from a page-1 tenant. So the tenant **stops**
at each one, hands back the pair, and `ex_renum` prints and re-enters with
`LE_OP_RENUM_NEXT`. The cursor lives in `RN_PTR` across the round trip — which
is precisely why `RN_PTR`/`RN_NEW`/`RN_OLD`/`RN_INC` may **not** be aliases of
the `SL_*` block the way `RN_TGT`/`RN_LINE` are: the head runs two other
routines in between.

Status 1 is a **report**, not an error: R-RN10 measured `ERR` at 0 and
`ON ERROR` not trapping, so only status ≥ 2 reaches `raise_error`.

### 3.3 `AUTO` — the mirror of `LIST`'s split

The **argument** is parsed sub-side (`LE_OP_AUTO = 7`); the **modal loop** is
main-resident, because it drives `read_line`, `dispatch_line`, `find_line_bc`,
`list_num` and `CHPUT` — all main page 1.

🎯 **The loop stores nothing itself.** It writes the line number's digits at the
front of `LINEBUF` (`list_num` already leaves them 0-terminated in `NUMBUF`),
points `read_line`'s cursor just past them, and hands the finished buffer to
`dispatch_line`, which sees an ordinary `<number> <body>`. Every rule
`dispatch_line` already enforces — the 65529 refusal, the crunch overflow,
D-DOTGAPS's `.` write — applies for free.

Three measured constraints:

* 🔴 **the `*` is screen-only** (R-AU6). The prompt reads `10*` when line 10
  exists and `10 ` when it does not, but the stored line is `10 REM X` either
  way. So the marker goes to `CHPUT` and a **space** goes to the buffer.
* 🔴 **an empty entry stores nothing** (R-AU7) — and that is *not* the same as
  storing an empty body, which `dispatch_line` reads as the bare-line-number
  form and would use to **delete** the line.
* 🔴 **`read_line` may not block.** Ctrl-STOP is not a character and never
  arrives through `CHGET`, so a blocking read makes the session unbreakable.
  `RL_AUTO` switches `rl_loop` to poll `CHSNS` + `BREAKX`. The flag is cleared
  defensively at the top of `repl`, because a typed line that ERRORs out of a
  session unwinds straight there — clearing it only in `ex_auto`'s own exit
  would leave the **prompt** polling.

### 3.4 The tenant selector — the same latent bug, one op later

D-LSTRNG found `dec a / jp nz,le_delrange` ("anything not 1 is a delrange")
would have routed `LIST` into the **delete** path, and replaced it with a
ladder whose last arm was still an unconditional `jp le_lstrange`. That arm was
correct only while 3 was the highest op. Every op is an explicit `jp z` now and
the tail is an **unreachable guard** that reports `Syntax error` — six bytes to
turn the next silent mis-route into a loud one.

---

## 4. Predicted GREEN, at exact values — fixed BEFORE the change

1. `make basic-reloc` from clean: low **23 B** unchanged; page 1 **356 B →
   between 60 and 130 B** (three verbs, ~266 B estimated).
2. Sub page 0 **3869 B unchanged** (nothing lands there); sub page 1 **2324 B →
   ~1800 B**.
3. `audit-citations`: **702** files swept, self-tests 10/10 11/11 12/12 14/14,
   4 advisory all acknowledged.
4. `deadcode`: main **285** seeds → 0, sub **102** → 0 (+1 allowlisted).
5. `injector-check`: 325 → **326** files, 4 exempt, 3 RECORDs, 0 offenders.
6. Every existing corpus gate at its recorded value; `lnblank-say-acceptance`'s
   `kwgd-renum` pin **fires and is retired** — it pins that `RENUM` does
   nothing, and it will now do something.
7. `editverb-acceptance` green on three sides.
8. All four ROM hashes **change** (unlike the previous eight slices).

## 5. Predicted RED, with knives

Each knife names a predicted RED set **and** predicted GREEN survivors; a knife
that reddens everything has not localised anything. Run twice.

| # | cut | predicted RED | predicted GREEN |
|---|---|---|---|
| **K1** | delete the three `stmt_table` rows | every `rnm-`/`aut-`/`llt-` row → `Syntax error` | every `dlt-`/`lst-` row (the control that says the table itself still works) |
| **K2** | `le_tok_skip` → a plain `inc hl` byte scan in `lrn_scan` | `rnm-hexref` only | every other `rnm-` row — this is the knife that proves R-RN19 is load-bearing and not decoration |
| **K3** | drop the `PRDEST` restore after `list_walk` | `llt-sink` | every other `llt-` row, and every `lst-` row |
| **K4** | run pass 3 before pass 2 | every `rnm-` row with a reference | `rnm-norefs`, `rnm-empty` |
| **K5** | `ex_auto` writes `*` into `LINEBUF` instead of a space | `aut-star` | `aut-plain` (no existing line ⇒ a space either way) |
| **K6** | `RL_AUTO` never set (block in `CHGET`) | every `aut-` row → harness timeout | the `rnm-`/`llt-` batteries |
| **K7** | `ex_auto` calls `dispatch_line` unconditionally | `aut-empty` (the line is deleted) | `aut-plain`, `aut-star` |
| **K8** | `lrn_order`'s strict-`>` test → `>=` | `rnm-ordeq` | `rnm-ordgt` — the pair is what makes the boundary a measurement |

⚠️ The restore point is a **scratchpad snapshot** taken after the change and
before the first cut, never `git checkout --` ([[knife-cleanup-restores-from-head]]).
The runner reads the **probe's** exit code, not `make`'s.

---

## 6. As-built

### 6.1 Predictions, scored

| § | predicted | measured |
|---|---|---|
| 4.1 | low 23 B unchanged; page 1 356 → 60..130 B | **23 B**; **356 → 94 B** ✅ (262 B for three verbs) |
| 4.2 | sub p0 3869 unchanged; sub p1 → ~1800 | **3869**; **2324 → 1824** ✅ |
| 4.3 | **702** files swept | **702** ✅ |
| 4.4 | `deadcode` main **285** seeds → 0 | **286** → 0 🔴 **the prediction is off by one** — §6.7.1 |
| 4.5 | `injector-check` **326** files, 4 exempt, 3 RECORDs, 0 offenders | **326 / 4 / 3 / 0** ✅ |
| 4.6 | `kwgd-renum` fires and is retired | fired; reads ` 2  0 ` like its control, entry **DELETED** ✅ |
| 4.7 | `editverb-acceptance` green on three sides | **61/61**, `--repeat 2` ✅ |
| 4.8 | all four ROM hashes change | **THREE of four** 🔴 — `disk.rom` is byte-identical and the build graph says it must be. §6.7.2 |

### 6.2 🔴 One divergence, and the fix made the boundary a SWEEP

The first build diverged on exactly one row: `RENUM 65529` on a **one-line**
program raised ERR 5 where both references renumber. `lrn_order` failed on the
carry out of `RN_NEW + RN_INC` — i.e. it rejected the number the **second** line
would have needed, on a program that has no second line. A wrapped value now
parks at `$FFFF`, which the *next* line's ceiling test rejects and which is
harmless when there is no next line.

A boundary found by one case is not left as one case: `rnm-ceil{1,2,3}at` and
`rnm-ceil{2,3}ov` re-ask it at one, two and three lines on both sides, and
`rnm-litover` keeps the two error CLASSES apart (a **computed** overflow is
`Illegal function call`, a **literal** argument past 65529 is `Syntax error`).

### 6.3 Knives — 8 knives, each run twice, plus 2 re-aimed and re-run twice

| # | verdict |
|---|---|
| K1 | **CUT** — severing the three dispatch rows kills all three verbs; `rnm-hexctl`/`aut-ctl`/`llt-ctl` survive |
| K2 | **CUT** (after re-aiming, below) |
| K3 | **MISS, and the miss is the finding** — §6.4 |
| K4 | **CUT** — deleting the reference pass leaves headers renumbered and every reference stale |
| K5 | **CUT** — `*` into `LINEBUF` breaks `aut-star`, not `aut-plain` |
| K6 | **CUT** — without `RL_AUTO` the session is unbreakable |
| K7 | **CUT** — an unconditional `dispatch_line` DELETES the line on an empty entry |
| K8 | **CUT** — accepting an equal new start breaks `rnm-ordeq`, not `rnm-ordgt` |

Both rounds were byte-identical: openMSX is deterministic, so a knife result
that reproduces is not thereby *sound* — which is why each also names survivors.

**K1 had to be re-shaped before it scored anything.** Deleting the three
`stmt_table` rows orphans `ex_llist`/`ex_renum`/`ex_auto`, the dead-code gate
fails the **build**, and a knife that will not assemble measures nothing. It
repoints the TOKEN bytes at values no crunch emits instead.

**K2's first GREEN set was wrong, and that is a finding about the design.** A
byte scan does not merely mis-resolve references: an operand byte equal to `$00`
ends the line early, the walk desynchronises and runs off into RAM, and four
rows sharing no `$0E` at all came back `<NO ECHO>` — the machine was gone. So
`le_tok_skip` is load-bearing for **termination** as well as for resolution,
which is what its own header says about float mantissas and what the prediction
under-read.

### 6.4 🔴 K3: R-LL5's second half is STRUCTURALLY gated, and two rows failed to see it

K3 deletes the `ENDFLAG` store so `LLIST` no longer ends the line.

* Against `llt-tail` it scored MISS because that row reads the **printer log**,
  which is byte-identical either way. The row gated half a rule while appearing
  to gate all of it. Fixed by adding `llt-tailb`, which reads `B` back off the
  **screen** — and which promptly exposed that the screen battery plugged no
  printer, so an `LLIST` row there **hangs the VG-8020** on an unplugged
  `LSTOUT`. (That hang is real and is exactly what D-KWGAP4 filed; what was
  wrong was the conclusion. Every battery plugs a printer now.)
* Against `llt-tailb` it **still** scored MISS. The reading did not move because
  the rule has **two mechanisms**: the `ENDFLAG` store *and* the fact that the
  handler never advances the statement cursor (its own header says the advanced
  cursor "has no reader and is never marshalled back"). Removing one leaves the
  other, so no single-cut knife can separate them.

⇒ recorded as a MISS with the reason, not converted into a knife that would
pass. Same shape as D-DELETE's R-D8 — see [[rule-gated-structurally-has-no-knife]].

### 6.5 🔴 And a knife found a defect in this slice's own fix

The **original** K3 cut the `xor a / ld (PRDEST),a` that stood after `list_walk`
and `llt-sink` **did not move**. The justification shipped with those four bytes
was false: it claimed to protect a `10 LLIST:…` whose `ON ERROR` handler runs
first, and no such path exists — `LLIST` ends the run on every path, and the
raise happens *before* the sink is ever set. Deleted; page 1 went 90 → **94 B**.
The reset is now `repl`'s job, which is a cross-file invariant with no gate of
its own, and `llt-sink` is the row that would catch it if `LLIST` ever stopped
ending the run.

### 6.6 Filed-claim score

Both clauses of the residual were wrong (§2.1), so this slice reads **0 of 2**
right — the tenth consecutive filed item to fail its own justification, and the
second (after D-DSKJUDGE) where the claims were *accurate about a mechanism* and
still pointed the work at the wrong question.

### 6.7 Corpus

Full corpus, run **sequentially from a removed `build/`**, one emulator gate at a
time, every log captured whole (never tailed):

`basic-reloc` low **23 B** / page 1 **94 B** / sub p0 **3869** / sub p1 **1824** ·
`repack-machine` OK ·
**`unit-test` ALL 58 test files PASSED**, `test_stmt_dispatch.py` **78 table
entries, 78 dispatch OK** ·
**`audit-citations` CLEAN — 702 files swept**, rule self-test **10/10**, listing
**11/11**, dump **12/12**, section **14/14**, 2 + 1 allowlisted, **4 advisory
section headers all acknowledged** ·
`preflight-check` 180 spawn sites, 85 exempt, 95 require a guard, **95 guarded,
0 UNGUARDED** ·
**`injector-check` self-test 4/4, 326 files, 4 exempt, 3 acknowledged RECORDs,
0 compose / 0 handle / 0 unparseable** ·
`latch-check` **16/16** rows (A–F) ·
`deadcode` main 1571 spans / **286** seeds → **0 dead** (+0 allowlisted), sub
1493 spans / **102** seeds → **0 dead** (+1 allowlisted) — §6.7.1 ·
**`editverb-acceptance` 61/61 rows across 3 sides (2 reference)** ·
`dexp5-pin` **16 rows ALL PASS** vs `Philips_VG_8020` ·
`linemax-acceptance` **60/60** ·
**`lnblank-acceptance` `REPEAT=2` — 536/536 gating rows agree** across all three
sides with **0 allowlisted as `KNOWN_DIVERGE`**, i.e. the allowlist is **EMPTY**
(the `kwgd-renum` retirement, §4.6, is what emptied it); the run's own SELF-HEAL
re-ran 23 suspect rows boot-per-case ·
`lnblank-say-acceptance` **204/204** gating rows, 4 allowlisted — the 4 that
predate this slice, `kwgd-renum` having been **deleted** rather than updated ·
`subrom-acceptance` **PASS** (page-0 `$C0`, page-1 `$C1`) ·
`subrom-inttest` **PASS** (JIFFY delta 28, serviced via the sub-ROM `$0038`
trampoline) ·
`graphics-floor-acceptance` **PASS** (JIFFY delta 40, **0** VDP latch read-back
mismatches) ·
`graphics-acceptance` **PASS** ·
`probe` **ALL PASS** (disk + basic + tape smoke) ·
`fat-error-acceptance` **8/8 + directory check** over a live FAT layer ·
`diskbasic-acceptance` **34/34 verbs converged** ·
`bdos-acceptance` **12/12 gated differentials converged** (1 screen skipped) ·
`lof-acceptance` **45 cases, 0 unfiled divergence, 0 oracle drift, 0 mangled**,
59-line log.

⚠️ **`lof-acceptance` is the standing flake watch, and it did NOT fire.** The full
log — read whole, never tailed — is 59 lines and reports the same 45 cases and the
same two FILED `dir` divergences (`rand_put`, `rnd_put_len`) as the last ten
slices. **Sighting 3 has still not occurred.**

#### 6.7.1 🔴 The main seed count is 286, and §4.4 predicted 285

§1.3 named this exact risk — *"`check_dead_code.py` reads comments for its
`external_names`… movement there is a finding about this slice's own prose, not
about the tree"* — and then §4.4 predicted no movement anyway. The prose moved it.

The gained seed is **exactly one label, `list_num`**, and it is a seed because
`sub/lineedit.asm`'s new report-loop comment *names* it (§3.2: rendering
`Undefined line <n> in <m>` needs main page-1 `print_string`/`list_num`, which a
page-1 tenant cannot reach). `external_names(['sub','tools'])` is deliberately
coarse — every identifier under those roots, comments included — so naming a main
routine in sub-side prose seeds it.

**It costs the gate nothing, and that was measured rather than assumed.** With
`list_num` removed from the seed set the closure is *identical*: `list_num` is
already live from `init` (`LIST` calls it), the dead count is **0 both ways**, and
the live-set difference is the **empty set**. So the extra seed masks nothing —
over-seeding is the direction the tool's own docstring calls safe. What is
recorded here is that the **headline number** moved, because a seed count that
drifts silently is how the next slice mistakes a real seed for prose.

#### 6.7.2 🔴 `disk.rom` did not change, and §4.8 could not have been right

Measured against the `0b31baa` baseline:

| image | baseline | after | |
|---|---|---|---|
| `build/disk.rom` | `2c630d3d…e33c27` | `2c630d3d…e33c27` | **IDENTICAL** |
| `build/sub.rom` | `b2935188…97e5e` | `7e23076dd47fe1cfc01ef6967292d7c67ab71dae303bc4506c0720f5c2feffa4` | changed |
| `build/basic-reloc.rom` | `3f1cd586…594af` | `75a0dffb2de0b80ef77f61d9115aaab4e9c372a89b9a1e80a0d6e7d566f6defc` | changed |
| `build/zerobas-main-eu.rom` | `d061cd58…d9e28e` | `4cee1f0d4c81d3f916feafb371fe3b10ad91a728c2d696ab38e1cda85e3efaaf` | changed |

`$(DISK_ROM)` depends on `$(DISK_SRC) $(DISK_PARTS)` — `disk/disk.asm` plus seven
files under `disk/`, and `disk/disk.asm` includes **nothing outside `disk/`**. So
the disk ROM's build graph contains no `basic/` and no `sub/` file, and a slice
that touches only those two **cannot** move it. §4.8 was not a prediction that
failed; it was a prediction the build graph forbids, and it was written down as
*"all four change (unlike the previous eight slices)"* because those eight were
apparatus-only slices where all four stayed identical — the contrast was reached
for without checking which images this slice can actually reach.

⇒ the honest form of the claim: **every image that depends on `basic/` or `sub/`
moved, and the one that depends on neither did not.** Three of four. Same family
as [[content-check-cannot-answer-a-length-question]]: the assertion was about a
quantity the instrument was never wired to.

⚠️ `make` alone does **not** build `zerobas-main-eu.rom`; that hash comes from
`make repack-machine`. A run that skips it scores three images and reports four.

---

## 7. What this slice did NOT do, and what would re-open it

* **`LPRINT` / `LPOS` / `LFILES`** — the other three printer words. All three
  are absent from `kwtable.inc`, and `kwsweep-msx1-coverage.md` lists them as
  *"not executed — the unplugged-`LSTOUT` hang hazard"*. §2.1 refutes that
  reason; the words are still absent. Filed.
* **`.` after `RENUM`/`AUTO`** — D-DOTLINE's `DOT` cell. `RENUM` does not write
  it and `AUTO` writes it only through `dispatch_line`. Neither is measured
  against a reference. Pinned, not claimed.
* **Backspacing over `AUTO`'s prompt digits** — `rl_bs`'s floor is `LINEBUF`,
  so the digits can be erased. Plausible for a screen editor and **unmeasured**.
* **An error inside an `AUTO` session** — whether a mistyped line ends the
  session on the reference is unmeasured; zerobas ends it (the unwind to `repl`
  clears `RL_AUTO`).
