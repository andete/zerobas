# zerobas roadmap

zerobas is a **clean-room reimplementation of MSX1 system software** — three
components (BASIC interpreter + cassette + disk) combined with an open BIOS (C-BIOS)
only at runtime — with **two co-equal goals**: the clean-room implementations
themselves, and the clean-provenance **documentation** of how these systems work
that the same discipline yields (see [`MISSION.md`](MISSION.md)). Scope today
is MSX1; the BASIC half targets **faithful, full MSX1 BASIC** (Phase 1 shipped the
*game-loader-stub* subset — enough to boot disk/tape game loaders — and the charter
has since been raised to full-language faithfulness, pursued in Phase 3), while tape
and disk are device-complete (read **and** write).

See [`README.md`](README.md) for the charter and the legal/provenance firewall,
[`PROVENANCE.md`](PROVENANCE.md) for the traceability rules every item below must
honour (allowed sources only; no disassembly), and
[`docs/dev-workflow.md`](docs/dev-workflow.md) for how to implement + validate one
item — do **one item per session** to keep context lean.

## Phases at a glance

| Phase | Scope | State |
|---|---|---|
| **1 — loader-stub BASIC + transports + standardization** | just enough MSX-BASIC to run `.BAS`/binary loader stubs; tape + disk read/write; standard DSKIO/`HPHYD` interfaces | **✅ closed** |
| **2 — full disk (Disk BASIC integration)** | the full file-channel verb surface (sequential + random-access + dir mgmt + `CALL FORMAT`), all oracle-validated | **✅ verb surface complete** — only the Tier-2 provider oracle (a distinct DOS-boot sub-track) + a few Phase-3-gated verbs remain |
| **3+ — full MSX1 BASIC** | floating point, full string engine, arrays, graphics, sound, … | **active charter** (raised from loader-stub) — landed: string engine, float pack, math pack, **arrays/DIM arc CONCLUDED** (through slice-4c string-scalar unification — the faithful unified variable area; no fixed variable pool remains) |

## Open — standing residuals (INDEX; this is the pickup list)

🔬 **RE-SWEEP DONE 2026-08-26 (D-TODOSWEEP), 65 TRANCHES** —
[`docs/todo-sweep-2026-08-26.md`](docs/todo-sweep-2026-08-26.md), verdicts in
`scratchpad/sweep_verdicts.json`, denominator `tools/todo_inventory.py`.
**Rule: re-run everything, inherit no claim.** ✅ **COMPLETE 2026-08-26 —
178 of 178 subject blocks carry a verdict** (`tools/todo_inventory.py --audit
scratchpad/sweep_verdicts.json` reports `subject with NO verdict: 0`).
📏 **HOW THEY WERE SETTLED: 68 RAN** (emulator, probe or gate), **53 INSPECTED**
(source, tree, git), **57 READ** from the block's own text. **32 carry an
explicit `read-not-run` caveat** — a read is a verdict about the WRITING, not
about the machine, and this file says which is which rather than averaging them.
🔴 **THE SUBJECT SET GREW WHILE BEING SWEPT, 177 → 178**: the last tranche
measured `NAME "old" AS <non-string>`, found two divergences, and REOPENED the
item that had closed that question at six verbs. A sweep that files nothing has
not thereby been thorough.
⚠️ **THE VERDICTS ROT LIKE ANY OTHER FIGURE.** The 2026-08-09 staleness sweep
covered 17 items and nothing gated it; this one is 178 and nothing gates it
either. Re-derive from `scratchpad/sweep_verdicts.json` and the audit, never
from this paragraph.

📦 **AND THEN THE CLOSED WORK WAS SPLIT OUT — 2026-08-26.** 233 blocks and three
whole done-record sections moved to [`docs/TODO-done.md`](docs/TODO-done.md),
**12577 → 3722 lines**, leaving **111 open items and 4 closed blocks whose
verdict is LIVE**.
📦 **SECOND PASS 2026-08-30**: 54 more blocks and three whole done-record
sections moved, **6145 → 4676 lines**; the archive grew to ~10400. **Count the
markers, do not quote these** — `python3 tools/todo_inventory.py --count`.
🟢 **THE TWO DEFECTS THAT SECOND PASS FOUND ARE FIXED (D-SPLITFIX, 2026-08-30)**
— the archive is APPENDED to and refuses to shrink, and the citation repointer no
longer backtracks into a shorter line number. Seven arms, collected by
`make selftest-check`. 🔴 **THE SPLIT RULE IS THE VERDICT, NOT THE CHECKBOX** —
`- [x]` was not evidence of finished work until the sweep said so, which is the
whole reason this section exists. Regenerate with
[`tools/split_todo_archive.py`](tools/split_todo_archive.py) (it refuses unless
the two files reconstruct the original byte for byte).
🟢 **AND THE CITATIONS INTO THIS FILE NO LONGER ROT SILENTLY.** All 42 now carry
the block's content-derived id beside the line — the line is for a human's
click, the **id** is what [`make todo-citation-check`](Makefile) trusts, with
`--fix` to repair a drifted line and `--annotate` to attach a missing id.

🤖🙋 **EVERY OPEN ITEM CARRIES A PICK-UP MARKER, AND THE MARKER SAYS WHO HAS TO
BE IN THE ROOM** — not what the item touches. Derived 2026-08-26 by
[`scratchpad/classify_open.py`](scratchpad/classify_open.py), which prints the
signal that decided each one so it can be argued with.

⚠️ **THE `n` COLUMN ROTS — RECOUNT IT, DO NOT QUOTE IT:**
`python3 scratchpad/classify_open.py --count`. It reads the markers actually in
this file and FAILS if an open item carries none. The figures below are **as
measured 2026-08-27** and stand as taken; on that day the previous set was wrong
by **12** in the 🤖 bucket, and three items were `- [ ]`, unmarked, and ended
"✅ DONE" — so the loop would have re-picked finished work. (`classify_open.py`'s
own headline re-DERIVES a classification from signals and may differ by an item
or two; the MARKERS in this file are what the loop reads, and `--count` counts
those.)

| marker | meaning | n (2026-08-27) |
|---|---|---|
| 🤖 **AUTONOMOUS** | the reference or a gate settles it; finishable unattended | **62** |
| 🔭 **SCOUT-THEN-ASK** | the decision is Joost's, the measuring and pricing in front of it are not | **6** |
| 🙋 **NEEDS-JOOST** | a call that is his: what to evict from a scarce page, a refactor with no oracle, a charter question, a retirement | **25** |
| ⛔ **BLOCKED** | neither can start it now — an idle host, a missing fixture, apparatus that must be built first | **9** |

**102 open items, 102 markers, 0 unmarked** — the invariant above, checked.

🔴 **A MISFILED 🤖 IS NOT A STOP CONDITION — WRAP UP AND REFILE.** If an item
marked autonomous turns out to need a decision of his: **finish and commit
whatever was actually measured** (the finding, the probe, the row — nothing is
thrown away), **re-mark the item 🙋 with the reason on its marker line**, and
**pick up the next 🤖**. Never decide on his behalf; never idle waiting for an
answer. That discipline is what makes a generous 🤖 list safe.

⚠️ **TIES GO TO 🙋, AND AN UNMARKED OPEN ITEM IS UNCLASSIFIED, NOT AUTONOMOUS.**
Misfiling toward 🤖 is the expensive direction; misfiling the other way only
costs a question.
⚠️ **THE MARKERS ARE A HEURISTIC OVER THE BLOCK TEXT PLUS THREE HAND
CORRECTIONS**, not a reading of all 111. Three were re-marked by hand because
the signal that caught them was not their reason — the override list is in the
classifier, because tuning the pattern until it agrees is fitting an answer you
already hold.

⚠️ **This section exists so a residual cannot be lost by being written up inside a
`- [x]` block.** Several of the items below were filed that way — accurate, dated,
and invisible to anyone scanning for `- [ ]`. Each line here is a **one-line
pointer**: the detail stays where the slice wrote it, at the cited line. Keep this
list short — close items, do not restate them.

Also the reason `MEMORY.md` no longer carries a copy of this list: the memory index
is loaded every session and must stay compact, so it points here instead of
duplicating (and drifting from) what is written below.

📏 **DATED 2026-08-09 BY A STALENESS SWEEP**,
[`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md).
All **56** open items were enumerated mechanically and classified; the **17** that
assert a concrete, checkable behavioural divergence were re-run on both references
and on zerobas from a clean build (164 case-runs, 48 s). **6 were STALE** and are
closed below with the measurement that closed them; **11 are LIVE** and carry a
`RE-MEASURED 2026-08-09` line; **3** more are behavioural but not reachable by this
instrument and say so; the remaining 36 are apparatus, carve prices, doc debt or
scope and were excluded **by kind**, listed by line in §6 of that document —
and the partition is **machine-checked complete and disjoint** against this
file's own `- [ ]` lines (§1.1), so no open item was skipped without leaving a
trace.
🔴 **Two of the eleven live items no longer read as filed** — see the `ON ERROR
GOTO 0` and `DEFINT` entries. 🔴 **And five of the six stale ones were closable
from evidence already in this file or in a gate that runs on every build**: a
residual gets closed by a slice aiming at something else, and nothing re-reads the
list. **When a slice lands, grep this list for what it just shipped.**

**BASIC surface**

- [ ] ⚠️ **`check_todo_citations.py --fix` CANNOT TELL A CITATION QUOTED AS AN
      EXAMPLE FROM A LIVE ONE, AND REWRITES BOTH.** Found 2026-08-30 while
      writing D-SPLITFIX, whose comment explains the citation-corruption bug BY
      QUOTING A CITATION. `--fix` repointed the example twice (`4618` -> `3251`
      -> `3287`), leaving the sentence self-contradicting — *"on `TODO.md:3287`
      the greedy `\d+` takes `4618`"* — and silently drifted the selftest's input
      fixture with it.
      🔴 **THE ARM KEPT PASSING**, because ANY already-id'd citation is skipped,
      so nothing but reading it would have caught the drift. **A green arm on a
      mutated fixture is the failure mode here**, not a red one.
      🎯 **THIRD INSTANCE OF ONE CLASS IN A DAY**, and the first that MUTATES
      rather than miscounts: a `FOUTBUF`-writer grep and a knife's guard counter
      both hit a comment written an hour earlier
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      ➡️ **WORKED AROUND AT THE ONE SITE** (the comment spells the shape
      `TODO<dot>md:`, the fixture is assembled by concatenation so no literal
      citation exists in the file). **The general fix is not done**: any doc that
      quotes a `TODO.md:NNN (T-xxxxxx)` as an example is exposed, and neither the
      fixer nor `todo-citation-check` has a way to mark one inert.
      ➡️ Candidate: an explicit escape the tools honour (a leading `!` or a
      fenced span), plus a gate arm that a marked example survives `--fix`.
      🤖 AUTONOMOUS — a gate settles it.

- [x] 🟢 **FIXED 2026-08-30 (D-SPLITFIX) — BOTH DEFECTS, WITH SEVEN ARMS THE
      BATTERY COLLECTS.** `(?!\d)` added to `CITE` (backtracking is what defeated
      the already-id'd lookahead: greedy `\d+` takes `4618`, the lookahead
      rejects it, the engine retries `461` where the next char is `8` and it
      PASSES); and the archive write became APPEND-with-a-shrink-refusal, sharing
      one `_append_or_write` helper with `main()` so the arm scores the shipped
      path and not a copy. Falsified by planting the old code back: each plant
      reddens its own two arms and leaves the controls green.
      🎯 **THE HELPER WAS FACTORED FOR THE ARM, NOT FOR TIDINESS** — inline in
      `main()` the only way to check it was to READ it, and reading it is what
      missed the defect.
- [x] 🔴 **`tools/split_todo_archive.py --apply` IS A ONE-SHOT TOOL THAT DOES NOT
      SAY SO, AND THE SECOND RUN DAMAGED TWO TRACKED FILES.** Found 2026-08-30
      while doing the routine second split; both were caught by hand, and
      **neither was caught by the tool's own checks**.
      🔴 **(1) IT CLOBBERS THE ARCHIVE.** It regenerates
      `docs/TODO-done.md` from `TODO.md` ALONE, so a second run rebuilds the
      archive out of only what is still in the pickup list: it **deleted 8857 of
      the 8903 lines** already there. Its `lossless` check passed while doing it,
      because that check reconstructs the **SOURCE** (`TODO.md`), not the
      destination. Recovered with `git checkout` + appending the new blocks by
      hand, insertions only, verified line-for-line against the pre-split file.
      ➡️ **Needs an APPEND mode**, and a losslessness check that includes the
      DESTINATION's prior content.
      🔴 **(2) THE CITATION REPOINTER CORRUPTS OVERLAPPING REWRITES — 19
      citations in 12 files.** It produced
      `TODO.md:325 (T-6FE392)8 (T-529ABE)` from `TODO.md:3532 (T-529ABE)`: a
      rewrite for one citation landed INSIDE another's line number, because the
      old-line → new-line map is applied as plain text substitution and
      `TODO.md:461` is a prefix of `TODO.md:4618`. Every damaged file was
      reverted and repointed with `check_todo_citations.py --fix`, which resolves
      by **block id** and got 18 of 19 right; the 19th named a block that had
      moved to the archive, which `--fix` cannot do because it rewrites the LINE
      and not the FILE.
      ➡️ **Repoint by ID, or match the whole `file:line (T-xxxxxx)` token** —
      never by line-number substring. And **teach `--fix` to change the FILE**
      when a block's id resolves in the other document.
      ⚠️ **`todo-citation-check` DID catch (2) once the corruption existed** —
      it is the gate that found all 19 — but nothing catches (1), because no gate
      reads the archive's line count against its own history.
      🤖 AUTONOMOUS — both defects are reproducible from this commit's parent and
      settled by the tool's own `--verify` once it is extended.

- [ ] 💰 **D-NGRAM: EXACT REPEATED INSTRUCTION SEQUENCES — `req_letter` SHIPPED
      (−50 B), THREE CANDIDATES LEFT.** [`docs/spec-ngram.md`](docs/spec-ngram.md),
      `scratchpad/ngram_sweep.py --main`. Built because `clone_scout` masks two
      operands BY DESIGN and so cannot see EXACT repeats collapsible into a
      shared body — the shape that paid in D-BAREEND (+45 B) and D-POPRAISE.
      ✅ **SHIPPED: `req_letter`.** `call skip_spaces / call is_letter /
      jp nc,stmt_error` stood open-coded at **TEN** statement entries (DIM,
      ERASE, DEF FN, FIELD, the disk string-var parse, INPUT, both SWAP
      operands, FOR, READ) at 9 B each; one 10 B body + ten 3 B calls replaces
      90 B. Low region read 50 → 68 B free, page 1 154 → 186 B, 2026-08-28.
      🔴 **TWO INSTRUMENT FAULTS CAUGHT BEFORE ANY NUMBER WAS QUOTED**: the raw
      table was ALL `sub/` (mathpack repeats, where thousands of bytes are
      already free — `--main` rescores on main sites only), and **a CONDITIONAL
      jump is not a terminator**, so the top candidate was first mispriced as a
      shared tail it can never be.
      ✅ **SHIPPED 2026-08-28: `req_operand`** (D-NGRAM2,
      [`docs/spec-basic-ngram2.md`](docs/spec-basic-ngram2.md)) — `call
      skip_spaces / or a / jp z,loc_missing / cp COLON / jp z,loc_missing`, the
      top-ranked exact repeat in the SCARCE regions. 6 sites x 12 B -> one 13 B
      body + six 3 B calls. **Page 1 read 185 -> 226 B free on 2026-08-28** (a
      READING; run `make basic-reloc`). 18 rows, DIFF 0/18; 2 knives.
      🔬 **A LINE-BASED GREP FINDS ONLY 4 OF THE 6** — four sites carry comment
      lines INSIDE the sequence. Enumerated at instruction level, and checked for
      an INTERIOR LABEL (none), which is what would make the span byte-identical
      without being ENTERED the same way.
      ✅ **ALSO SHIPPED 2026-08-28: `le_call` / `le_call_op`** (D-NGRAM3,
      [`docs/spec-basic-ngram3.md`](docs/spec-basic-ngram3.md)) — the
      `subrom_call` + LE_STATUS sequence at LIST / line-STORE / DELETE / RENUM /
      AUTO. Filed at 40 B; **it is 49 B**, because four of the five set `LE_OP`
      immediately before, so a 3 B second ENTRY drops four `ld (LE_OP),a`.
      **Page 1 read 226 -> 275 B free on 2026-08-28** (a READING; run
      `make basic-reloc`). 9 rows, DIFF 0/9.
      🔴 **THE PER-SITE WITNESS HAD TO BE STATIC.** The line STORE is one of the
      five sites and the probe harness TYPES its own program through it, so a
      knife on the helper takes the fixture down and EVERY row moves, controls
      included — there is no control on that apparatus that survives it. Arm S1
      enumerates instead: 0 open-coded copies left, exactly 5 calls.
      ⚠️ **A SIXTH SITE (`relink`) MEASURED AND DECLINED**, 7 B: it returns
      WITHOUT reading `LE_STATUS`, so folding it in changes the A/flags its
      callers see, and `cload.asm` has two plain `call relink` sites whose flag
      dependence is unverified.
      ✅ **ALSO SHIPPED 2026-08-28: `shx_tail` / `shx_op_tail`** (D-NGRAM4,
      [`docs/spec-basic-ngram4.md`](docs/spec-basic-ngram4.md)) — the sub-ROM
      string-op RESULT tail at CHR$ / HEX$-OCT$-BIN$ / SPACE$ / STRING$. **Low
      region read 70 -> 94 B free on 2026-08-28** (a READING; run
      `make basic-reloc`). 13 rows, DIFF 0/13.
      🔴 **I NAMED THE SITES FROM NEARBY PROSE AND ONE WENT UNWITNESSED**: the
      sweep reports LINE NUMBERS, and `:733` is CHR$, not SPACE$ as I wrote — so
      CHR$ had no row while the set looked complete. The knife caught it only
      because its prediction named WHICH rows should move. **Name a site from
      its ENCLOSING LABEL.**
      ➡️ **STILL OPEN, measured 2026-08-28:** an `inc hl` +
      req_letter variant (**31 B**, 6 sites) that **OVERLAPS what shipped and
      must be RE-RUN, not inherited**.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended.

- [ ] 💰 **D-PEEPHOLE: THE CLASSIC Z80 SIZE IDIOMS, COUNTED — SAFE CLASS TAKEN,
      FLAG-CHANGING CLASS STILL OPEN (20 B).** Pattern list from the WikiTI
      "Z80 Optimization" page (Joost, 2026-08-28);
      `scratchpad/peephole_sweep.py --sites` counts each against basic/ + sub/
      (76 files, 20579 instructions). Two entries were ALREADY CLOSED and are
      reported rather than re-counted: `jp`→`jr` (D-JRSLICE/2, banked
      2026-08-24) and `call X`/`ld a,(hl)` (D-RETLN/D-EVSPDUP, gated).
      🎯 **REGION IS WHAT THE BYTES ARE WORTH**: of a 106 B ceiling only **47 B
      is in MAIN** (35 page 1, 12 low, measured 2026-08-28) — the rest is sub,
      which had thousands of bytes free and is not a carve.
      ✅ **SAFE CLASS SHIPPED 2026-08-28: 14 B** — 12 `call X / ret` → `jp X`
      tail calls (each read individually first) + 2 `ld r,n / ld r',n` →
      `ld rr,nn`. Low region read 38 → 44 B, page 1 124 → 132 B on 2026-08-28.
      ✅ **THE FLAG-CHANGING RULES ARE A MEASURED NEGATIVE, 2026-08-28 — the
      ~20 B ceiling is really 1 B, and sweeping it would have shipped SIX
      REGRESSIONS.** Every one of the six main-region `ld a,0` sites is
      LOAD-BEARING: `cload.asm:777`/`:850` are `call cal_refill / ld a,0 /
      jr nc` (xor clears the carry the branch tests), `float.asm:308`/`:351` are
      16-bit NEGATES where the borrow from `sub l`/`sub e` must reach the
      following `sbc` — and `program.asm:555`/`:1994` already said so in a
      comment. Only the `djnz` at `cload.asm:376` converts: **1 B, taken**
      (nothing reads `dec b`'s flags — `ccn_flag` opens `ld a,c / or a`).
      🔴 **AND THE SWEEP WAS REPORTING A DISHONEST 18.** It counted every
      `ld a,0` as a candidate. It now walks forward and rejects the site if any
      instruction CONSUMES a flag before the flags are redefined, treating a
      label / a call / the end of the window as LIVE. It reports **1** tree-wide
      and independently rejects exactly the six rejected by hand.
      🎯 **FOUR OF THE SIX HAD NO COMMENT SAYING WHY** — annotated in place
      (0 B; comments do not assemble), because that is where the next person
      running a peephole sweep will land, not in a spec file.
      ➡️ Also open: `ld a,(v)/inc a/ld (v),a` → `ld hl,v / inc (hl)`, 29 sites,
      58 B ceiling — needs HL free AND A dead at each, unmeasured.
      🔴 **THE SWEEP'S FIRST RUN REPORTED 54 HITS FOR THE PAIR-LOAD RULE AND THE
      TRUE COUNT IS 9**: `a b c d e` are all valid HEX DIGITS, so `is_imm()`
      accepted a bare register name and counted `ld d,a / ld e,b` — a register
      MOVE — as a constant pair.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended.

- [ ] 🔬 **IXH/IXL/IYH/IYL: MEASURED **NO** ON SIZE (2 B), UNMEASURED ON SPEED.**
      Asked by Joost 2026-08-28, who confirmed every official MSX machine
      supports them (and `pasmo` encodes them correctly), so availability is
      SETTLED and is not the question.
      [`docs/spec-halfindex.md`](docs/spec-halfindex.md),
      `scratchpad/halfindex_sweep.py --selftest`.
      🎯 **THE PREFIX BYTE DECIDES THE SIZE AXIS**: a half-index access is 2 B
      against 1 B for a register and 1 B each for `push`/`pop`, so it NEVER beats
      either — only a MEMORY temporary at 3 B. The whole size opportunity is one
      shape, `ld (cell),a … ld a,(cell)` → `ld ixl,a … ld a,ixl`, 2 B a pair.
      📏 **13 raw main-region pairs (26 B) → ONE convertible (2 B).** The test
      that decides it is *does anything else read the cell*: `factyp` has 36
      refs, `fp_lhsval` 12, `directf` 10, `trapena`/`in_rdlen` 9, `mul_i`/
      `mul_carry`/`cas_wcnt` 8 — those are STATE, not spills. Only `mul_adig`
      (2 refs, `basic/float-arith.asm:827→844`, low region) qualifies.
      ⚠️ **AND THE TREE'S ONLY THREE HALF-INDEX REFERENCES TODAY ARE ABI, NOT
      OPTIMISATION** — all three are `IYh` carrying a slot id for `CALSLT`
      (`initext.asm:127`, `subromcall.asm:49`, `sub/format.asm:76`), so IY is
      spoken for on any path reaching a BIOS or sub-ROM call.
      ➡️ **THE PERF AXIS IS THE LIVE ONE AND HAS NO MEASUREMENT.** The 24
      sub-ROM pairs are in the inner loops (**9 in `sub/graphics.asm`**, 11 in
      `fp_rnd`/`fp_log`/`fp_sqrt`) where sub bytes are ~free. Round trip:
      memory 26 T-states, `push`/`pop` 21, **half-index 16**. Same territory as
      the PAINT perf work. A CANDIDATE, not a finding — nothing is claimed until
      a differential times it.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended.

- [ ] 🙋 **THE `String too long` PRECEDENCE RESIDUAL — RE-MARKED 🙋 ON
      2026-08-29: THE FILED ROUTE HAS A GC HAZARD, AND ITS OBVIOUS REPAIR IS
      CLOSED BY A STATED INVARIANT.** Filed 2026-08-28 by D-STRLONG
      ([`docs/spec-basic-strlong.md`](docs/spec-basic-strlong.md) §5).
      📏 **RE-MEASURED 2026-08-29, still 3 DIFF of 20** (`f.128` `f.200`
      `s.200`): zb reports `Out of string space` (ERR 14) where both references
      report `String too long` (ERR 15). ⚠️ **`FRE("")` is 200 on all three
      sides**, so `X$=STRING$(128,"A"):PRINT LEN(X$+X$)` — no `CLEAR` at all —
      is a real user-visible case, not a corner.
      🎯 **THE CAUSE IS EXACT AND WAS CONFIRMED IN THE CODE:** `sh_append`
      already tests the length FIRST and raises correctly (D-STRLONG). The
      failure is EARLIER — `str_concat_tail`'s unconditional
      `call str_snapshot_to_temp` copies operand 1's BODY, which exhausts a
      200 B pool holding a 128 B operand before `sh_append` is ever entered.
      🔴 **THE FILED ROUTE IS UNSAFE AS WRITTEN.** It says to save operand 1's
      3-byte descriptor instead of copying its body, on the grounds that *"only
      the DESCRIPTOR is at risk, never the body"*. **That is false for a heap
      body.** GC compacts and MOVES heap bodies, fixing up only the descriptors
      it can ENUMERATE — `sg_walk_temps` / `_fnframe` / `_scalars` / `_arrays`.
      A private scratch copy is none of those, so operand 2's evaluation can GC
      and leave the saved `ptr` dangling: **silent corruption, not an error.**
      🔴 **AND THE OBVIOUS REPAIR IS CLOSED.** Making the copy an enumerated root
      means pushing it on the temp-descriptor stack — but `sh_src_is_temp`'s
      header states the invariant a temp entry is **"UNIQUELY OWNED (nothing
      else holds its body)"**, and D-CLP rests on it twice. Aliasing a variable's
      body from a temp entry breaks it.
      ➡️ **SO THE REMAINING ROUTES ARE ALL DECISIONS, NOT MEASUREMENTS:** (a) a
      new GC root kind, (b) relax unique-ownership and re-verify D-CLP's two
      uses, or (c) accept the body copy and fix the PRECEDENCE some other way.
      Each touches a load-bearing subsystem whose internal invariant has no
      external oracle — which is why this is now 🙋 and not 🤖.
      🙋 **NEEDS-JOOST** — a refactor of the string heap's ownership rules.

- [ ] 🙋 **THE MISSING-OPERAND HALF: `5+` READS ERR 24 WHERE BOTH REFERENCES SAY
      ERR 2 — ENUMERATED 2026-08-29, AND THE PRICE IS THE REASON IT IS NOW 🙋**
      ([`docs/spec-basic-numstr.md`](docs/spec-basic-numstr.md) §4.1).
      📏 **THE ENUMERATION IS RUN, NOT READ.** Planting `ld e,4` at
      `ev_f_missop` and re-running the whole D-MISSOP row set gives the list
      directly: **independent** (keep their 24) are `PLAY`, `PRINT USING`,
      `WIDTH`, `LOCATE`; **dependent** (lose it) are `POKE`, `DRAW`, `FIELD`,
      `INPUT#`, `OPEN`, `PRINT#`, plus three string-assignment shapes (`A$=`,
      `A$=+`, `MID$(A$,2)=`).
      🎯 **THE INDEPENDENT FOUR ARE EXACTLY D-NGRAM2's OWN SITES** — `req_operand`
      already guards them, which says the helper is the right shape and the
      remaining work is MORE OF IT rather than something new.
      💰 **PRICE: ~18 B for six statement slots, plus an UNPRICED route for the
      three string-assignment shapes, to correct TWO rows** (`5+`, `5*` — a
      trailing binary operator with nothing after it).
      ⚠️ Affordable against a page 1 that was 343 B free on 2026-08-29
      (`make basic-reloc`; do not quote this) — but a poor trade, and it puts a
      rule that took a whole slice to establish back in motion. **That is a
      judgement about what a scarce page is for, not a measurement**, so it is
      🙋 rather than 🤖. The measuring in front of the decision is DONE.
      🙋 **NEEDS-JOOST** — spend ~18 B and reopen D-MISSOP's rule, or leave it.

- [ ] 🔴 **THE CONCATENATION PAIR: `5+"AB"` READS ERR 24 AND
      `"AB"+(0*(1/0)+1)` READS ERR 13, WHERE BOTH REFERENCES SAY 13 AND 11.**
      Found 2026-08-29 by D-STRTM
      ([`docs/spec-basic-strtm.md`](docs/spec-basic-strtm.md) §4).
      ⚠️ **NOT FIXED WITH D-STRTM's ROUTE, AND THE REASON IS A HAZARD.** Both live
      at `sct_err2`, which calls `type_mismatch_set` and then RETURNS NC so the
      caller re-drives the whole expression numerically. Evaluating the operand
      inside `sct_err2` would evaluate it **TWICE** — once there and once on the
      re-drive — and a string operand can contain a `USR` call or a `DEF FN`
      invocation with side effects.
      ⚠️ **AND REMOVING THE ARM IS CLOSED BY BUG C:** without it `PRINT A$+5`
      printed `" 0"`, a silent wrong answer, which this project ranks worse than
      the refusal beside it.
      ➡️ So the fix probably belongs in whatever the NUMERIC RE-DRIVE meets, not
      in `sct_err2`. Unpriced.
      🤖 AUTONOMOUS — the references settle the behaviour.

- [ ] 🔬 **`LSET`/`RSET` ON A NEVER-FIELDED VARIABLE HAS NO ORACLE: THE TWO
      REFERENCES DISAGREE.** Found 2026-08-29 by D-NGRAM11. `A$="12345":LSET
      A$="AB"` reads `Illegal function call` on the cassette-only VG-8020 and
      pads in place (`AB   `) on the disk-equipped CF-3300. zerobas targets the
      disk machine and agrees with it, so **nothing is known to be wrong** — but
      the row cannot score either way and is marked NO-ORACLE in the probe rather
      than dropped from it.
      ➡️ The open question is whether the split is DISK vs CASSETTE (a machine
      capability) or a firmware revision, which decides whether the CF-3300 is
      the right oracle for this row at all. `b.lset` (`LSET A$=5`) is in the same
      bucket: ERR 5 / ERR 13 / ERR 2 across the three sides.
      🤖 AUTONOMOUS — a third reference or the disk-ROM source settles it.
      [[an-unnamed-outcome-reads-as-no-outcome]]

- [ ] 🔬 **`ON ERROR GOTO <non-line>` IS UNTRAPPABLE ON BOTH REFERENCES —
      MEASURED 2026-08-29 (D-ONERRARM), AND BOTH OF MY HYPOTHESES WERE REFUTED**
      ([`docs/spec-basic-onerrarm.md`](docs/spec-basic-onerrarm.md),
      [`scratchpad/onerrarm_probe.py`](scratchpad/onerrarm_probe.py)). 12 rows,
      4 DIFF. Pre-existing (HEAD gives the same reading).
      🔴 **NOT "disarm before parsing"** — the guess this item was filed with.
      `ON ERROR PRINT` fails EARLIER in the same statement and TRAPS on all three
      sides; `ON ERROR GOTO 12345` fails LATER and traps too. Only the `$0E`
      operand stage differs. [[a-justification-parenthesis-is-an-unrun-claim]]
      🔴 **NOT a tokenise-time rejection either.** `CLS:ON ERROR GOTO A:B=9`
      printing `B` reads the MESSAGE on both references, not `9` — a line
      rejected at entry would leave `B=9` to run, which the 🟢 control
      (`ON ERROR GOTO 900:B=9`) shows this shape does report as `9`. The line was
      stored, executed, and raised UNTRAPPED.
      ➡️ **SO IT IS A ONE-STAGE ASYMMETRY**, and any fix must reproduce exactly
      that: trap the wrong-token stage, trap the undefined-line stage, and NOT
      trap the operand stage in between.
      ⚠️ **UNPRICED AND NOT CHEAP:** `req_lineno` (D-NGRAM10) is now shared by
      four verbs and only ON ERROR wants this exit, so it needs a second entry
      point or a flag — against a page 1 that was 348 B free on 2026-08-29
      (`make basic-reloc`; do not quote this). And "untrapped" must be
      EXPRESSIBLE: it needs a raise that skips the trap check, which is not what
      `stmt_error` does.
      🤖 AUTONOMOUS — the references settle the behaviour; the cost is the open
      part.

- [ ] 🔬 **KNIFE TAGS ARE NOT UNIQUE: `K2`/`K5`/`K6` ARE REUSED ACROSS SLICES.**
      Filed 2026-08-28 by D-KNIFEROM
      ([`docs/spec-kniferom.md`](docs/spec-kniferom.md) §7).
      📏 **7 of 22 recorded null verdicts cannot be traced to their knife**
      because the tag matches several scripts — `K6` matches 3, `K5` matches 3,
      `K-FE1` matches 2 (`scratchpad/knife_verdict_audit.py`, the AMBIGUOUS
      bucket). A further 7 carry no tag near the claim at all.
      🎯 **THIS IS A NAMESPACE PROBLEM, NOT A KNIFE PROBLEM** — every one of
      those knives may be perfectly sound; the point is that no tool can say so.
      The slice-prefixed form (`K-NG1`, `K-SL4`) is already the majority
      convention and is unambiguous; the bare `K<n>` form is the whole gap.
      ⬇️ **DOWNGRADED 2026-08-28 after costing it.** Three routes measured, all
      worse than the problem: renaming historical tags edits shipped specs; a
      `SPEC =` declaration per runner is a 43-file sweep; and mapping by the
      runner's own docstring fails because **only 6 of 43 cite their spec**. A
      frozen-baseline gate would need updating on every new knife.
      🟢 **AND NOTHING IS SUSPECT**: D-KNIFEROM §6 measured 0 of 22 null verdicts
      resting on an unguarded knife, so this is TRACEABILITY hygiene, not
      correctness. The cheap half is free and needs no gate: **use the
      slice-prefixed form (`K-NG1`, `K-SL4`) for new knives**, already the
      majority convention.
      🙋 NEEDS-JOOST — worth doing only if the traceability is wanted for its own
      sake; I do not think it pays for itself.

- [ ] 💰 **A 2 B CARVE WITH ITS EVIDENCE ALREADY ATTACHED: `ems_typecheck`'s
      two `pop de` ARE PROVABLY UNNECESSARY.** Filed 2026-08-26 by D-MIDOP
      ([`docs/spec-basic-midop.md`](docs/spec-basic-midop.md) §4). They were
      written to be correct under a DISAGREEMENT between two records about
      whether `raise_error` resets SP — and **knife K-MD2 deleted both and moved
      0 rows of 9**, so it does: the trap arm at `basic/interp.asm`:1022, the
      abort arm through `fre_abort_low` (`:1731`, citing `4d35b6d`).
      🎯 **NOT TAKEN AT THE TIME ON PURPOSE**: popping is correct under both
      readings, and removing it makes the code DEPEND on the SAVSTK behaviour
      rather than merely survive it. `els_tc_common`'s header says *"every path
      out of here errors"*, so the dependency is sound — but that is a decision
      to take deliberately, not at the end of a slice.
      ⚠️ **AND THE SAME 2 B SIT IN `ems_err_pop2`/`ems_err_pop1` NEXT DOOR**, and
      in every other hand-rolled pop-then-raise tail in the tree. **The class is
      worth more than the bytes**: `scratchpad/` has no sweep for "a pop that
      only exists to satisfy a raise that unwinds anyway". ~~Unpriced.~~
      ✅ **SWEPT AND PRICED 2026-08-28 (D-POPRAISE,
      [`docs/spec-popraise.md`](docs/spec-popraise.md),
      `scratchpad/popraise_sweep.py --selftest`)**, and the class splits into
      THREE questions the filing above runs together. **16 tails**, never-return
      set derived as a fixed point from `raise_error` (120 routines), not
      declared. **Q1 delete the pops: 21 B — still 🙋 and still for the reason
      given above.** Q2 merge identical bodies: 21 B. 🎯 **Q3, the one neither
      the filing nor Q2 could see: 34 B.** Tails that share a RAISE TARGET but
      differ in POP COUNT are not identical bodies, yet **one chain serves them
      all** — the deeper entry falls through into the shallower one, the shape
      `ems_err_pop2 -> ems_err_pop1` has had all along.
      ✅ **THE `fp_runtime_error` GROUP SHIPPED 2026-08-28: −13 B; page 1 read
      106 → 119 B free on 2026-08-28** (a READING, not a standing figure — run
      `make basic-reloc`). Four routines (`cee_abort_fp`/`cepb_abort_fp`/
      `ela_abort_fp`/`elas_abort_fp`), all page 1, **18 B of code measured
      2026-08-28**, were one sequence in four register names; the register was free because the word is DISCARDED and
      `fp_runtime_error` writes A/DE/HL before reading anything.
      🔴 **THE KNIFE ON THE POPS CANNOT FALSIFY THIS** (K-MD2 already moved 0 of
      9), so the four ENTRIES are witnessed one knife each — 7 rows, DISJOINT,
      0 controls moved. 🔴 **AND THE FIRST CUT OF THAT KNIFE WAS A DESIGNED
      NO-OP**: retargeting to `stmt_error` re-raises the identical code, because
      `stmt_error` opens with `call check_expr_errors` (D-STMTPEND); three tails
      read "UNWITNESSED" for a reason that was not about the tails.
      ✅ **AND THE `stmt_error` GROUP'S ONE FREE MEMBER SHIPPED: `ela_err equ
      ems_err_pop2`, −5 B; page 1 read 119 → 124 B free on 2026-08-28.**
      🔴 **I FILED THAT GROUP AT "13 B nominal, ~10 B net" AND THE MEASUREMENT
      REFUTES IT — it is worth 5 B.** What decides is not the ADDRESS but the
      **CALL SITE'S JUMP FORM**: a `jr` caller PINS its target beside itself, so
      moving the body costs +1 B per site and eats most of a 3–4 B body.
      `ee_synerr_pop` (2 `jr`) nets **+2 B**, `ex_let_err` (2 `jr`) nets **+1 B**,
      `ems_err_pop2` (2 `jr`) is the canonical; only `ela_err` is reached solely
      by `jp` (arrays.asm:849) and only it could move. Witnessed alone by K-EL1
      ([`scratchpad/elaerr_knife.py`](scratchpad/elaerr_knife.py), row `s.ary`).
      ➡️ **STILL OPEN, measured, not shipped:**
      `gosub_stk_over` (**4 B, measured 2026-08-28**, adjacent, page 1, but
      **UNWITNESSED** — no probe row fills a control stack or over-nests a
      trap); `els_tc_common` (**4 B, measured 2026-08-28**, but it is a LOW →
      page 1 region trade, not a carve).
      🙋 NEEDS-JOOST — Q1 only (page-1 budget was the WRONG reason on the filing:
      a carve frees bytes. The real call is whether to depend on `raise_error`
      resetting SP).

- [ ] ⚠️ **THE STALL WATCHDOG NO LONGER MIS-ASSERTS, BUT `run_gates.py` STILL
      CALLS A CONTENDED UNIT *REAL*.** Filed 2026-08-26 by D-DRAWOP; the
      diagnostic half FIXED the same day by D-STALLSLOW (`a897bcd`), the
      classifier half OPEN. The message used to assert *"a stall is a FROZEN OR
      CRASHED emulator, NOT A SLOW ONE"*. `probes/lib/omsx_repl.py`:981 appends that clause
      to every stall kill, and justifies it with *"the heartbeat is on the HOST
      clock"* — **which is exactly why the claim fails.** A host-clock deadline
      cannot separate a FROZEN guest from a STARVED one; when the host is
      oversubscribed, a perfectly healthy emulator misses it.
      🎯 **AND THE REFUTATION IS PRINTED IN THE SAME SENTENCE AS THE CLAIM.**
      The message ends *"the run wrote N line(s)"*, and across the two degraded
      batteries those N were **1886, 90, 88, 6, 4, 3, 2 and 0**. **A frozen or
      crashed emulator does not write 1886 lines.** The field that falsifies the
      clause is adjacent to it.
      📏 **MEASURED**: wall **3509 s against a normal ~420 s**, lineerr shards at
      ~1000 s against ~100 s, **20 capture failures and every one a stall kill**,
      and **two different machines** (`C-BIOS…REPACK_DISK` and
      `National_CF-3300`) killed at **947 s — the same deadline to the second**.
      Two independent guest crashes do not share a timestamp; one expiring timer
      does. A second battery went **17 red**. The serial retry called several
      REAL, because the retry also ran contended.
      📏 **THIRD INSTANCE 2026-08-27/28 (D-FNGCROOT), AND IT YIELDS A FREE
      DISCRIMINATOR THE CLASSIFIER DOES NOT USE.** Wall **3785 s against ~426 s**;
      5 recovered flakes; the two units left REAL (`stmtpend-acceptance`,
      `graphics-acceptance`) were **stall kills at 929–1031 s writing 0 lines, on
      `Philips_VG_8020`** — a REFERENCE machine. 🎯 **A zerobas ROM change cannot
      make a reference machine hang**, so any stall kill whose missing capture is
      on `Philips_VG_8020` or `National_CF-3300` is mechanically NOT caused by the
      ROM under test. That is a one-line rule and it was decisive here: it took a
      genuine sub-ROM change from "prime suspect" to exonerated.
      🔴 **AND THE RETRY IS STILL NOT ENOUGH ON ITS OWN.** A serial re-run of
      `stmtpend-acceptance` at **load 2.05** failed again at 898 s — so a quiet
      host is not sufficient either, and only an explicit REVERT differential
      settled it: with the change backed out, the same unit failed identically at
      903 s (on `National_CF-3300` that time). Logs:
      `scratchpad/gate_logs/{stmtpend-acceptance,graphics-acceptance}.retry.log`.
      🟢 **THE HOST IS NOT BROKEN — it is self-contended.** With the battery
      stopped, a single `make error-acceptance` runs in **7.2 s** (normally 13),
      so the deadline is not fighting a sick machine, it is fighting `J=8` on
      10 cores plus whatever else the host is doing.
      🔴 **AND `omsx_repl.py`:477's REASONING IS WHERE IT WENT IN.** It records
      that a FIRST design beat on EMULATED time and false-fired on a
      slow-but-advancing emulator, and moved to `after realtime` so a beat lands
      *"regardless of emulation speed... as long as openMSX's event loop is
      alive"*. **That holds only if the process is SCHEDULED.** The fix moved the
      dependency from emulation speed to process scheduling, and both fail under
      the same condition. The comment then draws the conclusion the code has
      been asserting ever since: *"never merely slow"*.
      🔴 **SO THE FLAKE-vs-REAL CLASSIFIER INHERITS THE FAULT.** `run_gates.py`
      calls a unit REAL when it fails twice, and under sustained host load it
      will fail twice for the same non-semantic reason — the opposite of the
      2026-08-25 failure mode, where a real defect was retried into GREEN.
      🟢 **PARTLY FIXED 2026-08-26 (D-STALLSLOW), and the fix is EVIDENCE, not a
      better guess.** The heartbeat file's CONTENT is already `[machine_info
      time]` — the EMULATED instant — and only its MTIME was ever read. It is now
      read before the unlink and reported, and the *"not a slow one"* clause is
      replaced by the two fields that bear on it plus an explicit *"a host-clock
      deadline CANNOT separate a frozen emulator from one starved of CPU"*.
      🔴 **AND THE FIRST CUT OF THAT FIX WAS THE SAME DEFECT ONE LAYER ALONG.**
      It classified on a RATE THRESHOLD (*"emulated/wall > 0.02 means starved"*)
      — and its own falsification vector killed it: **12.4 emulated seconds in
      947 wall is 0.013x, plainly ADVANCING and plainly below the line.** The
      LAST beat's value cannot separate *"froze at 12.4s"* from *"starved at
      12.4s"*; only a DELTA could, and the watchdog keeps no previous value. **A
      threshold invented to look decisive is the same defect as the sentence it
      replaced.**
      ⚠️ **STILL OPEN, AND THIS IS THE PART THAT MATTERS**: `run_gates.py`'s
      flake-vs-real classifier is unchanged, so a contended battery still
      produces REAL verdicts for non-semantic reasons. A real discriminator
      needs the watchdog to keep the PREVIOUS emulated instant and report the
      DELTA over the stall window — that is the fix, and it is not done.
      🔴 **AND ONE FALSIFICATION ARM IS RECORDED AS NOT EXERCISED**
      (`scratchpad/stallslow_falsify.py`): forcing a real kill with
      `ZEROBAS_OMSX_STALL=2` did **not** kill, so nothing proves the READ happens
      at a real kill site — only that the parse and the message are right. **An
      arm that passes because it never fired is not an arm.**
      ⛔ BLOCKED — neither of us can start it now (needs an idle host).

- [x] ⚠️ **FIVE MORE NON-ATOMIC PUBLISHES INTO THE SHARED openMSX TREE, AND NO
      GATE WOULD SEE A SIXTH.** Filed 2026-08-26 by D-MACHXML
      ([`docs/spec-probe-machxml.md`](docs/spec-probe-machxml.md)), which fixed
      the one that FIRED. `tools/install-openmsx-machine.py`:379/392/401/440/455
      all publish with `open(out, "w").write(...)` into
      `~/.openMSX/share/{machines,extensions}` — the same truncate-then-write
      window, **measured at 34.3 % of concurrent reads torn**
      (`scratchpad/machxml_repro.py`).
      🟢 **THEY ARE OFF THE HOT PATH, AND THAT IS MEASURED NOT ASSUMED**: they
      are reached only from `machines` / `machines-oracle`, and the Makefile's
      own comment says *"`machines` is the RELEASE-INSTALL path, not a gate
      path"*. The one that fired, `install-repack-machine.py`, is a prerequisite
      of **112 targets** that `make gates` runs in parallel. So this is a real
      but cold instance of a hot class.
      ✅ **FIXED 2026-08-26 — ALL SIX PUBLISH SITES NOW GO THROUGH ONE HELPER,
      `openmsx_paths.publish()`.** The cure sits beside `find_user()` because
      the module that knows where the shared tree IS should know how to write
      into it; `install-repack-machine.py`'s inline copy was folded in too, so
      the mechanism and its 34.3 %-torn measurement are documented at **one**
      site rather than six. **Verified, not assumed**: `make repack-machine`
      publishes an XML that parses and leaves no `.tmp`, and the five rewritten
      sites were driven with `--user` pointed at a scratch tree —
      **5 XML files, all parse, no `.tmp`** — so the release-install path was
      exercised without touching the real `~/.openMSX`.
      🔴 **THE CHECKER IS STILL OPEN, AND IT IS NOW TRACTABLE.** The filed
      obstacle was the DENOMINATOR: the destination is built by
      `openmsx_paths.find_user()` at runtime, so a textual sweep cannot resolve
      it. `publish()` sidesteps that — the rule no longer needs to resolve a
      path, it needs a **file set**: within `tools/install-*.py` and
      `openmsx_paths.py`, any `open(..., "w")` outside `publish()` itself is the
      finding. That denominator is small, complete and statable.
      ✅ **CHECKER SHIPPED 2026-08-26 as rule PUBLISH of `make chokepoint-check`**
      ([`docs/spec-chokepoint-gate.md`](docs/spec-chokepoint-gate.md)) — one gate
      for three items, because they were one property. Denominator **3 files**.
      🔴 Its first cut reddened `openmsx_paths.py` **twice, on the COMMENT that
      explains why the raw call is forbidden** — a regex cannot tell code from
      prose ABOUT code, and a file documenting a chokepoint is the likeliest
      place to contain its own subject. AST now.
      ✅ **DONE** — both halves.

- [ ] 💰 **A 4 B DUP-SPAN THE D-ONLIST FIX CREATED, AND ITS OWN KNIFE FOUND
      IT.** Filed 2026-08-26. `esn_notlineno`'s discriminator
      (`dec de / ld a,d / or e / jr …`) is **byte-identical to `esn_p1`'s own
      countdown test** four instructions above it — the K-OL2 anchor guard
      reported *"anchor appears 2 times"* and that is what a duplicate span
      looks like from the outside.
      🔴 **RUN, NOT ASSUMED: `tools/dupspan_indep.py` DOES NOT SEE IT** —
      `scratchpad/onlist_dupspan.out`, zero mentions of `esn_p1` or
      `esn_notlineno` in a report that lists 169 nominal bytes. The reason is
      structural: the two spans end in DIFFERENT jumps (`jr z,esn_found` vs
      `jr nz,esn_nocf`), so the identical part is a 4-instruction **PREFIX**,
      and the tool's model is spans-with-terminators. That is a hole in the
      model, not a near miss —
      [[dupspan-slice]] already records that a span can be byte-identical
      without being ENTERED the same way; this is the mirror, byte-identical
      without EXITING the same way. **The tooling question is worth more than
      the 4 bytes.**
      ⚠️ Unpriced, and probably not worth taking alone: folding it needs a
      shared entry with the exit selected somehow, which is likely to cost more
      than it saves. Filed for the SWEEP, not for the carve.
      🙋 NEEDS-JOOST — a call that is yours to make (page-1 budget).

- [ ] 🔴 **`KEY n,"str"` AND `KEY LIST` ARE UNIMPLEMENTED — A WELL-FORMED
      STATEMENT IS `Syntax error` HERE AND SILENT ON BOTH REFERENCES.** Filed
      2026-08-26 by D-MISSOP3. `KEY1,"X"` reads **0 / 0 / 2**: both references
      complete it, zerobas refuses it. [`basic/screen.asm`](basic/screen.asm):294
      is `jp stmt_error` with the comment *"KEY <n>,\"str\" / KEY LIST
      unsupported"*, so `ex_key` handles only `KEY ON` / `KEY OFF` (plus the T3
      `KEY(n)` arming form).
      🔴 **IT WAS ALREADY WRITTEN DOWN, INSIDE A `- [x]` BLOCK, AND THEREFORE
      INVISIBLE** — TODO.md:3532 (T-529ABE), a Phase-1 entry ending *"all Phase-3 scope"*.
      That is the exact failure this section's own preamble exists to prevent,
      and it survived the 2026-08-09 staleness sweep because the sweep
      enumerated `- [ ]` items. `docs/kwsweep-msx1-coverage.md` cannot see it
      either: its scope claim is **reserved words only**, and it says so —
      *"a word can be present and still wrong in its third argument"*. So
      `make kwsweep` printing no `MISSING=` line is not evidence about this.
      🎯 **FOUND BY A CONTROL, NOT BY THE SUBJECT.** `r.keyok` was a
      throwaway well-formed row expected to be green on all three; the filed
      residual it sits next to (`KEY1,` reading ERR 2 where the references say
      24) is a SYMPTOM of the whole form being absent, and "fix the error code"
      would have been the wrong repair. Under the charter the reference wins.
      📏 **SCOUTED 2026-08-26 — D-KEYSTR,
      [`docs/spec-basic-keystr-scout.md`](docs/spec-basic-keystr-scout.md)**
      (`scratchpad/keystr_probe.py`, 6 rows x 3 machines, measurement only).
      The storage is MEASURED, not assumed: a distinctive plant (`KEY n,"ZQX"`)
      reads back at **base `$F87F`, stride 16, NUL-terminated**, with two
      controls making it a reading rather than a coincidence — planting slot 1
      and reading slot 2 returns `"auto"` (F2's default), and planting nothing
      returns `"colo"` (the head of F1's `"color "`).
      🔴 **AND THE GAP IS BIGGER THAN THIS ITEM SAYS: zerobas reads `0 0 0 0` AT
      EVERY SLOT WITH NOTHING PLANTED.** The references' DEFAULTS are present on
      a cold boot and zerobas's are not — so the function-key string area is
      **UNPOPULATED**, not merely unwritable, and `KEY ON` renders it. A fix
      that added only the parse and the copy would leave nine slots holding
      zeros where the reference holds `color `/`auto`/`goto`/`list`/…
      ⚠️ **SECOND REFRAMING OF THIS ITEM BY A CONTROL RATHER THAN ITS SUBJECT** —
      D-MISSOP3's `r.keyok` turned *"wrong error code"* into *"the form is
      absent"*; this scout's `k.none` turns that into *"the storage is empty
      too"*.
      💰 **STILL UNPRICED, AND THE DEFAULTS ARE THE LARGER HALF**: ~160 B of
      DATA, which needs a home outside main page 1 (**85 B** free 2026-08-26 —
      read the wall, never this line) before it needs a design. Also still
      unmeasured: the `n` domain (`KEY 0,` / `KEY 11,`), the truncation length
      (15 is read off the stride, not off a machine), and `KEY LIST` entirely.
      🔭 SCOUT-THEN-ASK — the decision is yours; the measuring and pricing in front of it are not (charter / scope, but unpriced/unmeasured first).

- [x] 🔴 **D-TODOSWEEP'S OWN ELEVEN PROBES RE-IMPLEMENT THE `[...]` READER, WHICH
      IS THE TRAP THE ITEM BELOW DESCRIBES.** Filed 2026-08-26 by D-TODOSWEEP
      tranche 55, against itself. `probes/lib/omsx_repl.py` ships
      `result_span_after_echo` (:1765) specifically so *"an aborted case's echoed
      `[` is not misread as printed output"* — and
      `scratchpad/sweep_tranche{1,11,12,16,17}.py`,
      `scratchpad/{citepaths,patchfresh}_falsify.py` and
      `scratchpad/editscout_{layout,reentry,reentry2}.py` each carry their own
      `spans()` instead — **ELEVEN, not nine: the filed count was written from
      memory and corrected by counting 2026-08-26 (tranche 58)**, and **0 of the
      eleven import the shared reader**. 🎯 **THE ITEM WAS READ AFTER THE NINE PROBES WERE
      WRITTEN**, which is the item's own thesis demonstrated. ⚠️ None of the nine
      is a GATE — they are one-shot sweep instruments — so the exposure is to
      wrong readings in this sweep's own record, not to a green battery. The
      cheap fix is to import the shared reader; the durable one is whatever stops
      the next scratch probe copying the last scratch probe.
      🔴 **COUNTED A THIRD TIME 2026-08-26, AND 11 IS WRONG IN BOTH DIRECTIONS.**
      The real membership is **8**, and the list above names **ten** files for a
      count of eleven — it does not even agree with itself:
      * **NOT MEMBERS:** `citepaths_falsify.py` and `patchfresh_falsify.py`
        **never import `omsx_repl` and never read a screen** — they falsify the
        two citation gates. They were swept in by name, not by property.
      * **NOT MEMBERS (weaker sense):** `editscout_{layout,reentry,reentry2}`
        slice rows, but only to **print the whole screen** for inspection; they
        extract no `[...]` value, so they cannot misread one.
      * **MISSED:** `sweep_tranche2`, `sweep_tranche3` and `sweep_paintflood`
        each carry their own `spans()` and were not listed.
      🎯 **AND THE EXPOSURE IS VISIBLE, NOT SILENT — MEASURED, NOT ARGUED.**
      [`scratchpad/spanreader_diff.py`](scratchpad/spanreader_diff.py) separates
      the two readers on **4 of 4** cases: the hand-rolled one returns a LIST
      whose **first element is always the echo's bracket fragment**
      (`'";1+1;"'`), where `result_span_after_echo` returns the value. But
      **all 8 print the whole list** (`spans={...}`) and none picks an element in
      code — so the echo fragment was on the page for a human to see, and **no
      verdict rests on a code-chosen element**. The sweep's record is not
      corrupted by this.
      🔴 **ONE REAL HAZARD SURVIVES THAT MEASUREMENT.** On an **aborted** case
      the hand-rolled reader returns a **non-empty** list — the echo fragment
      alone — where the shared reader returns `None`. *"No output"* can therefore
      read as *"a value"*, which is this tree's oldest trap
      [[an-unnamed-outcome-reads-as-no-outcome]].
      ⚠️ **THE 8 WERE DELIBERATELY NOT REWRITTEN.** They are one-shot
      instruments whose printed output IS the sweep's evidence; changing the code
      changes what that record is reproducible from. The open half is the durable
      fix — whatever stops the next scratch probe copying the last — and
      today's `sweep_tranche65.py` is evidence it is still needed: it imports the
      shared reader now, but **its first cut hand-rolled a finder and read its
      own echo**, at rc 0.
      ✅ **THE DURABLE FIX SHIPPED 2026-08-26 as rule READER of
      `make chokepoint-check`**
      ([`docs/spec-chokepoint-gate.md`](docs/spec-chokepoint-gate.md)). The 8 are
      PINNED with that reason in `tools/chokepoint-allow.txt`; a NEW unfenced
      reader is RED. Pins may shrink, never grow, and a stale pin is itself RED.
      🔴 **THIS ITEM'S SCOPE CLAIM IS FALSIFIED.** *"None of the nine is a
      GATE — so the exposure is … not to a green battery"* is wrong: **two gate
      probes define an unfenced reader**, `basic_probe_direct_ctrl.py` and
      `basic_probe_time.py`. On reading, both are SAFE — they use `#…#` markers,
      so `result_span`'s `[` never applies, and both handle the echo explicitly
      and say so — but the reason for not worrying was wrong even though the
      conclusion held [[a-justification-parenthesis-is-an-unrun-claim]].
      🔴 **THE RULE IS "REACHES A FENCE", NOT "DEFINES A `bracket()`"** — the
      first cut tested the name and reddened **24 correct gate probes** that wrap
      `screen_tail` and add sentinels. Wrapping a chokepoint is the goal; only
      bypassing it is the finding.
      ✅ **DONE** — counted, measured, and gated.

- [x] 🧹 **A TRACKED `scratchpad/` SCRIPT CAN HARDCODE THE AUTHOR'S ABSOLUTE
      PATH, AND NOTHING CHECKS IT.** Filed 2026-08-26 by D-CITEPATH, which found
      `cd /Users/joost/projects/zerobas` inside one of the four `.sh` battery
      wrappers it was triaging. That one is gitignored, so it does not matter —
      **but the class is not about `.sh`**: `scratchpad/*.py` IS tracked and
      shipped, and a tracked script with an absolute home directory in it
      resolves in a fresh clone and then does the wrong thing, which is worse
      than dangling. 🎯 The new citation gate proves the PATH exists; nothing
      asks whether the file it points at can RUN anywhere else. Unmeasured: the
      denominator over `scratchpad/**` + `probes/**` + `tools/**` has not been
      taken, and some hits will be legitimate (a C-BIOS checkout default). Cheap
      to sweep, a judgement to remediate.
      📏 **SWEPT AND FIXED 2026-08-26. THE DENOMINATOR IS 511 EXECUTABLE TRACKED
      FILES** (`.py`/`.sh`/`.asm`/`.inc`/Makefile under those three trees).
      ⚠️ **`.log` AND `.out` CAPTURES ARE EXCLUDED ON PURPOSE** — they hold 343
      of the 372 raw hits, and an absolute path inside a captured log is
      *evidence of what ran*, not a portability bug. Sweeping them in is how a
      372-hit number gets quoted for a 25-hit problem.
      🟢 **`/opt/homebrew/bin/openmsx` (44 files) IS NOT A HIT.** It is the last
      term of `os.environ.get("OPENMSX") or shutil.which("openmsx") or …`, and
      guarded after by `if not isfile: OMSX = "openmsx"`. It resolves on any
      host. Read before counting.
      🔴 **THE REAL CLASS WAS 25 ASSIGNMENTS IN 24 FILES** — `ROOT`/`REPO` set
      to the literal `/Users/joost/projects/zerobas`. **11 of the 24 are knife
      runners**, which CUT SOURCE FILES: in a fresh clone they would compute the
      wrong root and cut nothing, or the wrong file.
      ✅ **REMEDIATION WAS NOT A JUDGEMENT AFTER ALL — THE TREE HAD ALREADY
      VOTED 190 TO 25** for `dirname(dirname(abspath(__file__)))`. All 24
      conformed, **0 remain**, and each rewrite was PROVEN value-preserving:
      the new expression is evaluated with that file's `__file__` and must equal
      the old literal exactly — **24/24 did**, so no instrument changed what it
      reads. (My first pass skipped 9 of them by testing `^import pathlib$`
      against files that say `import hashlib, os, pathlib, re, subprocess, sys`.)
      ✅ **CHECKER SHIPPED 2026-08-26 as rule ROOT of `make chokepoint-check`**
      ([`docs/spec-chokepoint-gate.md`](docs/spec-chokepoint-gate.md)).
      Denominator **495 files**.
      🔴 **AND IT IMMEDIATELY FOUND ONE THE FIX HAD MISSED.** The sweep above
      reported *zero remaining*; `scratchpad/runline_knives.py` still hardcoded
      it. The sweep's regex required exactly one space before `=` and the file
      says `ROOT  = pathlib.Path(...)`. **The AST does not care about
      whitespace, and that is the whole argument for it.** Now 0, checked.
      ✅ **DONE** — swept, fixed, and gated.

- [ ] 🧹 **122 HARDCODED `/tmp/...` LITERALS ARE OUTSIDE THE TEMP ROOT** — pinned,
      not fixed. `probes/lib/probe_tmp.py` owns `/tmp/zerobas` and sets
      `tempfile.tempdir`, which relocated **140** bare `tempfile.*` call sites at
      a stroke; string literals cannot be relocated that way. **67 files, 10 of
      them reached by a gate.** 🔴 **THEY ARE NOT UNIFORMLY WRONG — 11 are
      `argparse` defaults**, a documented output location someone may rely on,
      which is exactly why they were not moved in bulk: that would be a silent
      behaviour change in probes no gate runs. The rest are one-shot capture
      files; each is a small safe conversion for whoever next touches that probe.
      🟢 `tools/temp-root-allow.txt` pins the set and `make temp-root-check`
      makes it **shrink-only** — a new literal is RED, and a pin that stops
      matching is STALE, so the file cannot drift from what it claims.
      Filed 2026-08-26 by the temp-root work, which chose containment + a gate
      over a 122-site edit it could not verify.
      📏 **RE-MEASURED 2026-08-26. IT IS 124 LITERALS IN 69 FILES**, not 122 in
      67 — it drifted **+2 within the day**, which is the gate doing its job
      rather than a problem: a new literal is RED, so the pin file cannot lie.
      🔴 **AND "10 OF THEM REACHED BY A GATE" DOES NOT REPRODUCE UNDER ANY
      DEFINITION I CAN CONSTRUCT.** Taking the **real** `GATES` list out of
      `run_gates.py` (41 targets), resolving each target's recipe to its scripts
      (48 seeds) and closing over imports (58 files), exactly **2** pinned files
      are on a battery path — and **both ARE the temp-root machinery itself**:
      `probes/lib/probe_tmp.py`, whose literals *define* the root, and
      `tools/check_temp_root.py`, whose two are its own matching regex and its
      docstring. **Zero of the 124 is a stray write on a battery path.**
      🔴 **MY OWN FIRST MEASUREMENT WAS WRONG THE SAME WAY THE FILING WAS.** It
      reported a different pair, including `probes/disk/disk_probe_dskio.py`
      (which really does write `/tmp/disk_probe_ours.txt`) — because I selected
      battery targets by *"the target name appears somewhere in `run_gates.py`"*,
      and **`probe` matched the substring `probes/lib`**. `make probe` is a
      SMOKE target, explicitly not a gate. A substring is not a membership test.
      ✅ **SO THE CONTAINMENT DECISION IS VINDICATED AND THIS DE-ESCALATES.** No
      bulk edit: today's lesson is that a mechanical sweep whose blast radius
      cannot be verified breaks invariants its own rule cannot see
      [[a-mechanical-fix-can-break-a-different-invariant]]. Convert
      opportunistically, when touching a probe for another reason.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (re-measured 2026-08-26: 0 stray writes on a battery path; DE-ESCALATED).

- [ ] 🐌 **`PAINT` IS STILL 1.9–2.0× SLOWER THAN BOTH REFERENCES — HALVED BY
      D-PAINTVRAM, NOT CLOSED.** Was 2.4–3.4× (filed 2026-08-24 out of the budget
      instrument, [`docs/spec-probe-budget.md`](docs/spec-probe-budget.md), this
      project's first per-operation performance differential against the two real
      machines). **Policy (user): faster or comparable is not a worry;
      significantly SLOWER is.** Exact emulated seconds, mark stopwatch,
      deterministic (`scratchpad/paint_stopwatch.py`):

      | operation | vg8020 | cf3300 | zb before | zb after | |
      |---|---|---|---|---|---|
      | PAINT, whole-screen flood | 14.736728 | 15.536890 | 46.252527 | **29.742824** | 🔴 2.98× → **2.02×** |
      | PAINT, bounded by a circle | 3.885463 | 4.097390 | 10.874419 | **7.403163** | 🟠 2.65× → **1.91×** |
      | CIRCLE draw, no fill | 0.409343 | 0.430918 | 0.253305 | 0.253305 | ✅ 0.62× faster |
      | LINE, corner to corner | 0.135319 | 0.142345 | 0.122553 | 0.122553 | ✅ 0.91× faster |

      🔴 **A PREDICTION MISSED, AND IT IS THE USEFUL KIND.** I predicted the flood
      would land UNDER 15 s, reasoning from `gbf_row`'s own *"two blind writes per
      byte instead of eight read-modify-writes … and it is the whole 23×"*. It did
      not. **The 23× applies to the WRITE, and the write is no longer where PAINT
      spends its time.** The filed item's warning — *expect a SECOND factor and do
      not stop at the first explanation that fits one row* — was right, and the
      2× VRAM-traffic story that fitted the bounded row was never the whole story.
      📏 **THE RESIDUE IS THE NEIGHBOUR-ROW SCAN, AND IT WAS COUNTED, NOT
      ARGUED** (§7.1 of [`spec-basic-paintvram.md`](docs/spec-basic-paintvram.md),
      `scratchpad/paint_callcount.py` — the real `gfx_paint_op` in the host Z80
      sim with the three VDP-touching leaves trapped, over three box sizes so the
      SCALING is measured): `gfx_paint_scan_row` tests EVERY column one pixel at a
      time on TWO neighbour rows per span, and **the scan's share of all VDP
      accesses RISES with area — 76.9 % → 84.6 % → 89.0 %**. At the largest box
      48898 of 54912 accesses are pixel tests and the blind byte fill this slice
      installed is ~5 % of them.
      🎯 **THE CANDIDATE FIX IS PURE CACHING, NOT A SEMANTICS CHANGE**: eight
      consecutive pixels of a row share ONE pattern byte and ONE colour byte, and
      `gfx_paint_scan_row` only TESTS (it never writes), so the row's VRAM is
      stable across its own pass — read the two bytes once per cell and answer
      eight columns from the cached pair.

      🔴 **BUILT, MEASURED AND *DECLINED* 2026-08-25 (D-PAINTSCAN) —
      [`docs/spec-basic-paintscan.md`](docs/spec-basic-paintscan.md). No ROM
      change: `sub.rom` `ae796ccb` before and after, 2464 B free both sides.**
      The cache was implemented in full (42 B, invalidated by every VRAM write in
      a PAINT) with every correctness gate green — unit-test 59/59, PHASE H-V
      12/12, `vram_fidelity.py` 0 divergent — and then reverted.

      📏 **THE TWO THINGS MEASURED FIRST WERE BOTH RIGHT.** Hit rate
      (`scratchpad/paintscan_scout.py`, post-invalidation, three box sizes):
      **79.5 % → 83.5 % → 85.5 %** for a ONE-ENTRY cache against an unbounded
      ideal of 93.3 %, so the cheap design was the right one. RAM: the 4 B aliased
      `GFX_CX`/`GFX_CY`, **verified two independent ways and neither vacuous**
      (`scratchpad/paintscan_ramclaim.py`) — STATIC, the 62-routine closure of
      `gfx_paint_op` over 67 sources mentions neither cell while 10 routines
      elsewhere DO; DYNAMIC, identical 3185-px fill under two poison seeds with
      both seeds intact afterwards. **That verification stands and is reusable.**

      🔴 **AND THE STOPWATCH FALSIFIED THE PROJECTION.** Predicted from the
      access counts: ~54.9 k → ~13 k accesses, i.e. the flood far under 14.7 s.
      Measured: flood **29.742824 → 26.193087** (2.02× → **1.78×**), bounded
      7.403163 → 6.622417 (1.91× → 1.70×). **1.14×, not 4×.**
      🎯 **THE MISS IS THE FINDING: TIME IS NOT PROPORTIONAL TO VDP ACCESSES.**
      Removing ~85 % of what was ~89 % of all accesses bought 12 %; had the reads
      dominated it would have bought ~76 %. `gfx_rd_raw` is ~85 T-states (two
      `out`s, a 3-`nop` fetch-window settle, an `in`) while the per-column loop
      around it — `gpsr_loop`/`gpsr_test` bookkeeping, `gfx_paint_inside`'s four
      RAM loads and two stores, `gfx_calc_addr`, `gfx_point_extract`, `call`/`ret`
      — is comparable or larger, and a read cache removes NONE of it (it adds a
      tag compare to every read). 🟢 **`PAINT` IS Z80-LOOP-BOUND, NOT VDP-BOUND.**

      💰 **DECLINED WITH NUMBERS**: designed for ~4×, delivers 1.14×; does not
      close the item (1.78× is still "significantly slower"); costs a permanent
      invariant (*every VRAM write in a PAINT must invalidate*) plus an aliasing
      coupling to the Bresenham cells; and **the right fix subsumes it**.

      🎯 **WHAT THE SUCCESSOR SHOULD DO — the unit of work must become a CELL,
      NOT A COLUMN.** Restructure `gfx_paint_scan_row` to fetch the
      pattern/colour pair once and answer up to eight columns from REGISTERS: no
      `call gfx_paint_inside` per column, no `GFX_PTESTX`/`GFX_PTESTY` round
      trip, no `gfx_calc_addr` per column. Span-end partials stay on the existing
      per-column path, exactly as `gfx_paint_row` already does for the write side.
      SCREEN 2 only. ⚠️ **The host unit test is structurally blind to it** —
      `tests/test_graphics.py` traps `gfx_paint_read` wholesale, so anything
      below that trap is invisible; the emulator differential is the only gate
      with teeth. The standing asymmetric perf check is what should gate it, and
      the stopwatch is what should score it.
      💡 A standing **asymmetric** perf check falls out of the same instrument:
      RED only when an operation is significantly slower than BOTH references,
      never when it is faster.
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).
- [ ] 🔬 **THE HARNESS'S WALL TIME HAS A ~5.7 s PERIODIC STALL THAT COSTS ~50 % OF
      AN EMULATOR GATE — AND IT MUST BE RE-MEASURED ON AN IDLE HOST BEFORE ANYONE
      ACTS ON IT.** Measured 2026-08-25, `scratchpad/harness_walltime.py`
      (attribution over a real probe) and `scratchpad/harness_tail.py` (minimal
      reproducer, phase-split).

      📏 **THE SHAPE, MEASURED.** `basic_probe_graphics` = 463 openMSX
      invocations, 216.7 s wall, 23209 emulated s scheduled. Median invocation
      **0.117 s**; a stall of **~5.7 s** recurs and the slowest 10 % are **~55 %
      of all wall**. It is **TIME-periodic, not count-periodic** — proven by
      changing the invocation size:

      | invocation | stall period (count) | × median wall | = period in TIME |
      |---|---|---|---|
      | 1 case | 44.6 | 0.117 s | **5.2 s** |
      | 8 cases | 20.0 | 0.276 s | **5.5 s** |
      | 1 case, diskless VG-8020 | 31.3 | 0.168 s | **5.3 s** |

      🔴 **RULED OUT BY MEASUREMENT, EACH ITS OWN RUN** — harness Python
      (preflight 0.000 s, spawn 0.001 s; the stall is entirely elsewhere);
      emulated-time length (the 40 LONGEST timelines are 42 % of emulated time
      but only 21 % of wall); temp-file Spotlight indexing (a `.noindex` TMPDIR
      changes nothing); the disk image and the machine (diskless VG-8020 shows
      the identical signature); process spawning in general (`/bin/echo` at the
      same rate: **0 stalls**); and launching the binary (`openmsx --version` at
      20/s: **0 stalls**, max 42 ms). A plain compute+file-I/O Python loop shows
      **1 %** in its tail, so the host is not globally freezing.
      🎯 **WHAT IS LEFT: openMSX INITIALISING AND RUNNING A MACHINE.** Sampled
      during a stall, openMSX is at **0.0 % CPU, state `Ss` — sleeping, BLOCKED,
      not starved** — while `WindowServer` (~50 %) and `Claude Helper`
      (~40 %) saturate the host.

      🔴 **AND THAT IS WHY THE NUMBER IS NOT ACTIONABLE YET.** The contention is
      with the GUI rendering the session that MEASURED it. On an idle host or in
      CI it may be absent or entirely different, and a harness redesign priced
      against it would repeat D-PAINTSCAN's mistake — optimising against an
      unvalidated model. **RE-RUN `python3 scratchpad/harness_tail.py` ON AN IDLE
      MACHINE FIRST** (~3 min, N=250); it prints the stall positions and the
      count/time period directly. If the stall survives an idle host, the lever is
      to spawn FEWER emulators (batching where a probe's hold allows it), since
      the cost attaches to running a machine and not to the timeline's length —
      NOT to trim budgets, which are only ~35 % of wall.
      ⚠️ Every wall figure quoted anywhere in this repo was taken in this
      environment, including the battery's 476 s / 502 s and
      `graphics-acceptance`'s 347–373 s.

- [~] 🕐 **SENTINEL — SHIPPED AS A *STOPWATCH* (`f6bb5a0`); SHIPPED BUT *NOT
      ADOPTED* AS A CAPTURE TRIGGER (`c04606b`).** Both modes exist and are gated;
      what changed is which one is justified.
      🟢 **ADOPTED — the emulated-time stopwatch.** `sentinel=(addr,val)` +
      `settle_out` logs `(emulated instant, value)` for every write the case's own
      BASIC makes, so marks either side of an operation give its EXACT duration,
      on the black-box references too. **Emulated time is DETERMINISTIC** —
      measured bit-identical across repeats (14.736728 s twice, 46.252527 s twice)
      — so this is the only basis on which a performance differential can be gated
      **without flaking**, which wall-clock timing (±0.2 s noise here) can never
      offer. It produced the exact PAINT figures in the item above.
      ✅ **SHIPPED 2026-08-25 (D-SNCAP) — THE REFUSAL IS LIFTED AND THE PAINT
      PHASES CAPTURE ON SIGNAL.** `graphics-acceptance` 216.7 → 186 s solo
      (−14 %), battery **502 → 445 s**, 37/37 green, ROM hashes unchanged.
      🟢 **THE DIFFERENTIAL THAT CARRIES IT** (`scratchpad/sentinel_screen_diff.py`,
      6 rows × 2 machines): **RAW differs on every row** — the `Ok`/`ZB` prompt,
      exactly as the old measurement said, *and that is also the proof the
      sentinel FIRED* — while the **ANSWER after `_points` is identical on every
      row**, with a teeth control (flood `[15,15]` vs box `[7,1]`) so a 0-DIFF
      tally cannot be vacuous. The 2 characters are precisely what `_answer()`
      documents itself as stripping.
      🔬 **AND THE ADOPTION IS FALSIFIABLE, WHICH MATTERS MORE THAN THE 14 %.** A
      case whose sentinel never fires falls back to the budget and passes
      IDENTICALLY, so a green phase proves nothing on its own
      ([[savestate-slice]]). Each converted phase now prints its tally: **28 / 34
      / 52 captured on signal, 0 fallbacks**, in the battery as well as solo.
      🎯 **THE BUDGETS ARE NOW FAILURE DETECTORS**: `PAINT_STEP` = 90 s fires only
      if a case never signals at all. Deterministically the captures land at
      **23.2–50.6 emulated s** against that 90 s.
      ⚠️ **PHASE J (PAINT errors) IS DELIBERATELY NOT CONVERTED** — a case that
      raises never reaches its `POKE`. Measured, not assumed: an `ONERRORGOTO` row
      falls back (`fallback 113.0 s`) and saves nothing. That is the intended
      backstop.
      ✅ **EXTENDED TO EVERY BOOT-PER-CASE PHASE (2026-08-25): 321 captures on
      signal, 0 fallbacks**, `graphics-acceptance` PASS, battery 37/37 at 452 s,
      ROM hashes unchanged. Phases A, C, E, G, I, K, N, P, Q1, Q3, R joined
      H/H-V/H-MC. `paint_mark()` handles all four program shapes this module
      produces — a `:END` readout, a `GOTO`-self hold (renumbered so the hold
      stays self-referential and the poke runs ONCE), a program that runs off its
      end, and a two-exit `ON ERROR` case which is marked on **BOTH** paths.
      🔬 **THE CHECK THE TALLY CANNOT MAKE**: a fallback proves a mark was never
      REACHED, but nothing in the tally would catch a mark placed too EARLY —
      that would capture a half-finished machine on both sides and could agree
      wrongly. So each conversion round was verified by diffing all **395 row
      values** against the previous run: byte-identical every time.
      ⛔ **THE 8 BATCHED PHASES ARE DELIBERATELY NOT CONVERTED** (B, D, F, J, L,
      M, O, Q2). With one boot per matrix the later cases are scheduled at FIXED
      emulated instants and the generated Tcl only exits early on the LAST case,
      so capturing early reclaims nothing there. PHASE J additionally cannot
      work: its programs raise, so they never reach a `POKE`.
      📏 **AND CONVERTING THE SMALL BUDGETS BOUGHT NO WALL, MEASURED**: the
      90 s/30 s/25 s phases went 186 → 184 s. The remaining phases run at the
      2.5 s default and were converted for the FAILURE-DETECTOR property and
      uniformity, not for speed — stated so nobody reads a performance claim into
      them later.
      ✅ **EXTENDED TO SIX MORE GATES (2026-08-25, D-SNCAP2): 1344 captures on
      signal, 1 fallback**, `penderr` / `screenerr` / `stmtpend` / `tmfp` /
      `lineerr` / `deffn-strict`, all 6/6 green, ROM hashes unchanged. The
      plumbing moved to **`probes/lib/probe_signal.py`** (address, kwargs,
      tally) so it is no longer copy-pasted; `basic_probe_graphics.py` delegates
      to it and its `paint_mark()` — the part that is NOT shareable, because
      where the mark goes is the only part that can be silently wrong — stays
      local. See `docs/spec-probe-mark.md`.
      🔬 **VERIFIED THE ONLY WAY THAT HAS TEETH: 557 report rows across 13
      reports, byte-identical before vs after** (`scratchpad/sncap/rowdiff.py`,
      itself teeth-checked against a mutated log).
      🎯 **THE DETECTOR EARNED ITS KEEP ON ITS FIRST RUN.** `deffn`'s
      `o.clearwipe3` never signalled — its `CLEAR` wipes the `ON ERROR` handler
      along with the DEF FN table, so the row aborts UNTRAPPED and reaches
      neither `END`. Its reading is unchanged and correct; the tally is the only
      thing in the tree that could have said so. 🔴 **AND THE FIRST TALLY COULD
      NOT NAME IT** — it printed `1 fell back` out of 72 and the gate had to be
      re-run to find out which row. `Tally.add(label=...)` now names them: an
      unnamed outcome reads as no outcome.
      📏 **THE DETERMINISTIC COST/BENEFIT, COMPUTED NOT TIMED**
      (`scratchpad/sncap/emutotal.py` reads `_tcl`'s own generated timeline, no
      emulator): **71 104 → 63 927 emulated s, −10.1 %** over the six gates ≈
      **21 s of wall** at §5's measured 0.003 s/emulated s. 🔴 **NO WALL CLAIM IS
      MADE AND NONE CAN BE**: the emulator-free warm-up control moved **7 s →
      14 s** between the before and after batteries, and two converted runs of
      the same battery differed by **59 s** — both an order of magnitude above
      the effect. Measured signal instants land within **0.1–0.7 emulated s** of
      the computed `t_run` floor, so the old budgets were pure idle.
      ⚠️ **`screenerr` IS THE OUTLIER AT −5.1 %, AND THE REASON IS THE MARK
      ITSELF.** `POKE&HE000,255` pushes its line 50 from 36 to 51 characters,
      past the 38-char KEYBUF chunk boundary, buying an extra typing slot that
      gives back half the reclaim. A mark is BASIC TEXT and text is not free.
      ⛔ **STILL UNCONVERTED, AND EACH FOR A STATED REASON.** `array`, `math`,
      `float` and every other `batch=True` matrix (rule 1 — capturing early
      reclaims nothing in a shared boot). `interval-trap-acceptance` does not go
      through `run_cases` at all and its subject IS emulated timing. The
      untrapped/cold rows of the six converted suites (rules 2 and the
      `screen_tail` prompt burden). `deffn`'s five `ADDR` rows (rule 3).

      🟢 **DECIDED 2026-08-25 (user): ADOPT IT FOR SCREEN CAPTURES TOO —
      *"even if we verify via a screenshot, a sentinel still makes sense"*.** The
      refusal below was measured but it was WEIGHED WRONG, and the item may not
      keep quoting the measurement as if it settled the question.
      ✅ **DONE 2026-08-25 — the refusal was lifted, both graphics and six more
      gates adopted it, and `probes/lib/probe_signal.py` carries the burden that
      replaced it. The block below is the record of what the refusal SAID; read
      it as history, not as current behaviour.**
      ⏸️ **~~IMPLEMENTED, GATED, NOT YET ADOPTED~~ — `sentinel_capture=True`.** It
      makes the budget a pure failure detector and measures 1.1 s → 0.2 s with the
      capture byte-identical. It is currently refused for `capture="screen"`, and
      that refusal is MEASURED, not caution: the sentinel fires before the
      interpreter prints its `Ok`/`ZB` prompt, and text captures differed by
      exactly those 2 characters on all three machines. **Every PAINT-phase case
      in `graphics-acceptance` is a screen capture whose program `END`s** — i.e.
      exactly that shape.
      🔴 **AND THOSE 2 CHARACTERS ARE THE ONE THING EVERY TEXT READOUT ALREADY
      THROWS AWAY.** `basic_probe_graphics.py`'s `_answer()` says so in its own
      docstring — *"the trailing BASIC prompt / 'Ok' / 'No RESUME' text (which
      differs per machine) is ignored"* — and `_points` is built on it. A capture
      taken BEFORE the prompt is not a degraded reading of the same screen, it is
      the screen WITHOUT the machine-specific noise the readouts exist to strip,
      and `screen_tail` terminating AT the prompt is a property of the
      TERMINATOR, not evidence that the reading is wrong. The real argument for
      the sentinel was never the 0.3 s: it is that **a fixed-time budget captures
      a half-finished machine and a partial result reads as SEMANTICS**, and that
      hazard is identical whether the capture is text or VRAM.
      ~~To pick up: lift the `capture="screen"` refusal in `omsx_repl`, prove each
      phase's readout is prompt-independent (assert the sentinel-captured and
      fixed-time answers are equal AFTER `_answer`, not before), then adopt
      per-phase behind that differential with a teeth control.~~ ✅ **ALL THREE
      DONE** — refusal lifted, `sentinel_screen_diff.py` for graphics and
      `scratchpad/sncap/rowdiff.py` (557 rows) for the six error-shaped gates.
      ⛔ BLOCKED — neither of us can start it now (needs an idle host).

- [ ] 🔴⚡ ~~**CAPTURE ON A `done` SENTINEL**~~ — original framing, kept for its
      reasoning; the speed case it was filed on is DEAD (the window it removes is
      idle emulation, ~0.3 s/case, under the noise floor) and the win was the
      budgets' SCOPE instead. Filed 2026-08-24 (user), out of the
      budget instrumentation. **The budgets are not timeouts, they are GUESSES AT
      THE COMPLETION TIME**: `_tcl` schedules the capture at `after time
      RUN+step`, so it fires whether or not the work finished. That is why the
      budget cannot be cut (fires MID-FILL, and a partial result reads as
      SEMANTICS) and why leaving it generous is ruinous — **one graphics PAINT
      case buys 676 emulated seconds** (6 slots × `PAINT_STEP` 90) for work whose
      worst measured need is 53.6 s.
      🔴 **THE ROOT CAUSE IS AN OVER-GENERALISED CONSTRAINT.** The clean-room rule
      forbids disassembling the reference ROMs → no breakpoint on *ROM internals*
      → which became "completion cannot be detected", hence fixed-time schedules
      everywhere. **But the PROGRAM can announce its own completion**, which
      watches emulated *RAM* and needs no ROM knowledge on any machine:
      `30 POKE &HE000,255` + `debug set_watchpoint write_mem 0xE000 {} {
      <capture>; exit }`. The repo ALREADY does the sentinel pattern on the disk
      side (`omsx_run.py --bp`, `spec-rdblk-anchor-flake.md` §2 *"the readout is
      already sentinel-gated inside the emulator"*) and the standing lesson says
      *gate every reading on a `done` sentinel* — the BASIC side just never got it.
      ✅ **WHY THIS BEATS TIGHT BOUNDS**: the capture fires the instant the work
      ends (no wasted emulated time at ANY generosity), the bound becomes a PURE
      FAILURE DETECTOR that only fires when the test or harness actually failed,
      **no per-case measurement is needed at all**, no budget can be cut below its
      need, and it self-adapts to the slowest machine (zerobas writes both VRAM
      tables, so it currently sets a floor everyone pays for).
      ⚠️ **IT CHANGES WHAT IS MEASURED, SO IT NEEDS THE SAVESTATE TREATMENT.**
      Today both machines are sampled at the SAME emulated instant; with sentinels
      each is captured at ITS OWN completion. Arguably more correct (final states,
      not an arbitrary shared moment) — but *arguably* is not a licence. Gate it
      exactly as `savestate-check` gates restore-vs-cold: sentinel-captured
      results **byte-identical** to fixed-time ones across the corpus, subject AND
      both oracles, with a teeth control, BEFORE it replaces anything.
      🔬 **FIRST STEP IS THE DIFFERENTIAL, NOT A FEASIBILITY RUN.** openMSX is
      mature and `throttle off` is implemented properly (user, 2026-08-24) —
      *"does the watchpoint fire?"* is not a real doubt and must not be dressed up
      as one. The earlier `savestate` feasibility runs earned their keep on **API
      SHAPE** (`savestate -f` is not the API; `loadstate` re-appends `.oms`; a
      relative name resolves against `~/.openMSX/savestates/`) — shape is
      discovered while building, not in its own ceremony. **The risk here is not
      the emulator, it is the SEMANTICS CHANGE above**, so build the
      byte-identical differential directly and let it find the API on the way.
      ⚠️ Cases that ERROR never reach their `POKE`, so the generous bound remains
      the backstop for that path — which is exactly "no bound needed unless there
      is a test or harness failure".
      📏 **STATE AS OF 2026-08-26, MEASURED NOT INHERITED.** The mechanism is
      **BUILT** (`sentinel` + `sentinel_capture` in `omsx_repl._tcl`: the
      watchpoint captures, and the fixed-time schedule is demoted to the pure
      failure detector this item asked for). **ADOPTION IS ZERO** — no probe
      under `probes/basic/` uses it; only `probes/lib/`, `probe_signal.py` and
      scratchpad experiments — so nothing has been replaced and nothing is at
      risk today. 🔴 **AND THE MODEL GATE THIS ITEM NAMES DOES NOT EXIST:**
      `savestate-check` was **WITHDRAWN 2026-08-24** and the code reverted
      ([`docs/spec-probe-savestate.md`](docs/spec-probe-savestate.md)). The
      PATTERN it stands for survives; the target to copy does not.
      ✅ **THE GRAPHICS HALF WAS ALREADY DIFFERENTIALLED** —
      [`scratchpad/sentinel_screen_diff.py`](scratchpad/sentinel_screen_diff.py),
      re-run today: 3 cases × 2 sides, raw **differs** (the prompt, so the
      sentinel demonstrably fired), answers **identical**, teeth fire. But every
      answer there is a VRAM point sample, and it never drove the second oracle.
      ✅ **THE TEXT HALF IS NOW MEASURED TOO —
      [`scratchpad/sentinel_text_diff.py`](scratchpad/sentinel_text_diff.py),
      12/12 SPANS IDENTICAL ON ALL THREE MACHINES** (value / string / FOR-loop /
      error × vg8020, cf3300, zb), with `' 42 '` vs `'ZB'` as teeth.
      🎯 **AND `screen_tail` BREAKS EXACTLY WHERE THE CODE SAID IT WOULD — BUT
      ASYMMETRICALLY, WHICH THE CODE DID NOT SAY.** `result_span_after_echo`
      (strips the prompt) is identical on 12/12. `screen_tail` (TERMINATES at the
      prompt) **DIFFERS on 6 of 12: both references, all three signalling cases,
      and NOT on zerobas.** So converting a tail-style readout would not merely
      lose 2 characters — it would manufacture a **machine-asymmetric** reading,
      i.e. an apparatus-made divergence between subject and oracle
      [[apparatus-is-part-of-the-measurement]].
      ✅ **THE FALLBACK PATH IS EVIDENCED, NOT ASSUMED.** The `1/0` case dies
      before its `POKE`, so the sentinel *cannot* fire — and all three machines
      still read `Division by zero in 10`, identically, from the fixed-time
      schedule.
      🔴 **THE FIRST RUN OF THAT DIFFERENTIAL WAS VACUOUS ON 8 OF 12 ROWS AND
      EXITED 0.** The CF-3300 got the same `("NEW","CLS")` reset as the others
      and returned `None` for every span; the error case returned `None` on both
      sides because a dead program prints no `[...]`. Four "same"s agreeing on
      nothing, plus a `3/3 FALLBACK` claim resting on `None == None`
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. Fixed: Disk BASIC
      gets `("", "SCREEN 0", "NEW")` like every other probe that drives it, the
      aborted case is scored on its MESSAGE, and a row with no reading on the
      fixed side is now an INSTRUMENT FAULT (rc 2) rather than a pass.
      ➡️ **WHAT REMAINS IS THE GATE AND THE CORPUS**, not the question: a
      standing check that sentinel-vs-fixed stays byte-identical, over the real
      acceptance corpus rather than 7 hand-written cases. **Adoption is licensed
      for span-style readouts and REFUSED for tail-style ones**, on the rows
      above.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (both halves differentialled 2026-08-26; the standing gate remains).

- [ ] ⚡ ~~**THE REAL GATE-SUITE LEVER IS THE EMULATED-TIME BUDGETS**~~ (original
      framing, kept for the reasoning it carries)
      ⚠️ **PARTLY SUPERSEDED by the sentinel item above** — a sentinel capture
      makes per-case budget tuning unnecessary for every case that reaches its
      sentinel. What survives regardless: the **two knobs are conflated** (below),
      and the error paths still need a bound.
      💡 **AND THE CHEAPEST WIN NEEDS NEITHER**: `step` spaces EVERY injected line,
      not just RUN→capture, so a graphics case waits 90 emulated s between each
      TYPED line (including `NEW`/`CLS`) when line spacing only has to cover
      KEYBUF drain (measured ~20 ms; the 2.5 s default is already 100×).
      Separating the two — lines at the default, RUN→capture keeping its measured
      90 — is **676 s → 151 s, a 4.5× cut, with NO budget made tighter than its
      measured need**. ⚠️ Safe for STORED cases (only `RUN` executes); a
      DIRECT-mode line executes as it is typed, so its gap genuinely is a
      completion budget.
      Filed 2026-08-24 out of the savestate measurement above, which found the
      per-case cost is dominated by `step` / `cap_gap` / `PAINT_STEP` — every one
      a hand-picked margin and several explicitly generous (`PAINT_STEP = 90.0`
      *"generous; see above"*, `MC_PAINT_STEP = 45.0`, the default `step = 2.5`
      and `cap_gap = 2.5`). A case's wall time is essentially linear in these, so
      this is where a multiple lives. 🔴 **AND THEY MAY NOT BE TRIMMED BY
      REASONING**: several are documented as sized against a MEASURED worst case
      (a whole-screen `C != B` PAINT flood; a cassette LOAD/SAVE running 10–30
      emulated s while the harness keeps injecting), and a budget cut below its
      operation fires the capture MID-FILL — which reads as a hang or a wrong
      partial result, i.e. as SEMANTICS. Any cut needs a per-phase measurement of
      what the operation actually takes plus a margin, and a gate that would go
      RED if the margin were too thin (the `graphics-acceptance` rows are the
      obvious subject).
      ✅ **INSTRUMENTED 2026-08-24 (`44fe13c`),
      [`docs/spec-probe-budget.md`](docs/spec-probe-budget.md)** —
      `_run_batch(settle_n=, settle_out=)`, inert when off (generated Tcl
      byte-identical to before), driver `scratchpad/budget_probe.py`.
      **MEASURED** (`used` = to the last change in the capture region; the window
      a budget buys is exactly `step`, since `cap_gap` falls AFTER the capture):

      | case | window | vg8020 | cf3300 | zerobas | worst |
      |---|---|---|---|---|---|
      | `paint.flood` | 90.00 | 16.005 | 16.005 | **53.610** | **59.6%** |
      | `paint.circle` | 90.00 | 4.778 | 4.778 | 11.330 | 12.6% |
      | `circle` | 90.00 | 0.715 | 0.715 | 0.426 | 0.8% |
      | `text.err` | 2.50 | 0.094 | 0.094 | 0.024 | 3.8% |

      🟢 **`PAINT_STEP = 90.0` IS EARNED — 1.68× margin, the TIGHTEST budget
      measured; the "generous" comment is wrong about the number. DO NOT CUT IT.**
      🎯 **The waste is its SCOPE, not its size**: it is applied to a whole phase
      while only the flood needs it. **Per-case budgets, or an adaptive capture
      that fires when the region settles, is where the wall time is** — neither
      makes any budget tighter than its own measured need.
      🔴 **`step` DOES DOUBLE DUTY** — inter-line injection spacing (the
      drained-buffer property the D-LATCH/D-DELIVER apparatus rests on) AND the
      RUN→capture budget; lowering it to reclaim the second tightens the first.
      **The cut needs a SEPARATE knob defaulting to `step`** (hence inert), plus
      the RED-if-thin gate above. ⚠️ zerobas is slowest on every fill row, so it
      sets the floor for any budget. ⚠️ **The parenthesis "*it writes both VRAM
      tables … a performance fact, NOT a divergence*" was FALSE and was the
      justification nobody ran** — writing both tables WAS the divergence, closed
      2026-08-25 by D-PAINTVRAM
      ([`docs/spec-basic-paintvram.md`](docs/spec-basic-paintvram.md)).

      ✅ **THE CORPUS AUDIT RAN, 2026-08-25, AND IT IS GREEN.**
      `scratchpad/settle_audit.py` had been built and never pointed at the
      corpus; the standing worry was that a budget too SHORT does not raise, it
      captures a half-finished machine and the partial result reads as SEMANTICS.
      Over the whole of `basic_probe_graphics` — **773 cases sampled, 🔴 still
      moving at capture: 0, 🟠 settled in the last 10%: 0**; tightest margin seen
      **56.2 % of its window (1.41 / 2.50 s)**.
      🎯 **THE DENOMINATOR, STATED**: graphics-acceptance ONLY — but that is the
      gate where the question has teeth, because it owns the only non-default
      budgets (`PAINT_STEP` 90 s, `MC_PAINT_STEP` 45 s), and its many 2.5 s cases
      mean the DEFAULT budget was sampled in the same run (the 56.2 % row is one
      of them, so the default carries ~1.8× margin). Other probes are unaudited.
      ⚠️ Run on the POST-D-PAINTVRAM build, where the flood settles in 29.7 s of
      its 90 s rather than 46.3 s — so the margins are the ones that exist NOW,
      not the ones the pre-fix corpus had.

**Language / verb surface**
      ⛔ BLOCKED — neither of us can start it now (needs an idle host).

- [ ] ⚠️ **TEN `tests/_tmp.py` ARTIFACT NAMES ARE SHARED BY 2–4 FILES, AND
      `tp()`'s FALLBACK BASE IS THE *SHARED* ROOT.** Found 2026-08-26 while
      driving the `unit-test` flake (item above), by walking every `tp("…")` in
      the tracked tree rather than inheriting *"`zb_eval.rom` is used by one
      test file"* — which is **true**, and true of only 96 of the 106 names.
      ```
      zb_graphics_sub.rom/.sym   tests/test_graphics.py + 3 scratchpad/paint*.py
      zb_io.rom/.sym             test_poke / test_screen / test_usr / test_vdpio
      zb_print.rom/.sym          test_list / test_print
      zb_vars.rom/.sym           test_strvar / test_vars
      zb_wrblk_e2e_ut.rom/.sym   test_rdblk_randrecord / test_wrblk_body_e2e
      ```
      🎯 **`tp(name)` IS `BASE/name` WITH NO PROCESS IDENTITY**, and
      `BASE = $ZB_TEST_TMP or probe_tmp.ROOT` — the **shared** `/tmp/zerobas`,
      *not* `probe_tmp.tmp()`'s per-process directory, which exists precisely to
      stop fixed names colliding. It does not fire today only because
      `tests/run.py` is serial and the four `zb_io` writers are all inside it.
      ⚠️ **THE `zb_graphics_sub` ROW IS THE ONE THAT CAN BITE**: three
      `scratchpad/paint*.py` probes share those names with a unit test, and a
      scratch probe run while a battery is running is a normal thing to do.
      ⚠️ **NOT REPRODUCED, AND THIS IS NOT THE FLAKE ABOVE** — `zb_eval.rom` has
      one writer, and the shared-path arm of that repro was **0/96**. Filed as a
      latent collision, not a diagnosis.
      💰 0 ROM bytes. But the fix is a change to the test harness's ISOLATION
      MODEL (the shared fallback is deliberate — the docstring says a runner
      that wants isolation sets `ZB_TEST_TMP`), so it is a decision, not an edit.
      🙋 NEEDS-JOOST — a call that is yours to make (changes the documented test-isolation contract).

- [ ] 🧭 **THE BOOT BANNER STILL CALLS ZEROBAS A "PROGRAM LOADER", AND THE
      CHARTER STOPPED BEING THAT ON 2026-07-17.** Noticed 2026-08-26 while
      gating the banner. [`basic/title-body.inc`](basic/title-body.inc) prints:
      ```
      zerobas version 0.1
      clean-room MSX-BASIC program loader
      ```
      The second line is the loader-stub-era scope. The charter is **faithful
      full MSX1 BASIC** [[charter-faithful-full-msx1-basic]], and the memory
      index's own rule is that top-level text saying otherwise is doc debt.
      🎯 **BUT THIS IS NOT DOC DEBT LIKE A COMMENT IS** — it is the first thing
      a user sees on every boot, it is version-stamped, and it is the product's
      own description of itself. Changing it is a decision about what zerobas
      says it IS, not a correction.
      ⚠️ **AND IT IS NOW GATED, WHICH CUTS BOTH WAYS**: `banner-acceptance`
      reads its expectation out of this same file, so editing the text keeps the
      gate green by construction. That is deliberate (the gate asserts the
      header REACHES THE SCREEN, not what it says) — but it does mean nothing
      will ever flag the wording for you.
      💰 Zero ROM bytes if the replacement is the same length or shorter; the
      strings live in the sub-ROM tenant, not main page 1.
      🙋 NEEDS-JOOST — a call that is yours to make (user-visible product text, and what the project says it is).

- [ ] 🔴 **`NAME "old" AS <non-string>` DIVERGES TWICE, AND `NAME` IS THE VERB
      D-FNEXPR2's OWN PLAN NAMED AND ITS MEASUREMENT SKIPPED.** Measured
      2026-08-26 by D-TODOSWEEP tranche 65
      ([`scratchpad/sweep_tranche65.py`](scratchpad/sweep_tranche65.py),
      [`scratchpad/sweep_t65.out`](scratchpad/sweep_t65.out)), differential vs
      the National_CF-3300 on a scratch copy of `disk/test720.dsk`.
      ```
      NAME"X.DAT"AS 5     (old file ABSENT)   cf3300 ERR 53   zb ERR 24   DIFF
      NAME"HI.TXT"AS 5    (old file EXISTS)   cf3300 ERR 13   zb ERR 24   DIFF
      NAME 5 AS"X.DAT"    (old-name position) cf3300 ERR 13   zb ERR 13     ok
      ```
      Controls on the same run: `KILL 5` 13=13 and `OPEN 5 AS #1` 13=13 (the two
      D-FNEXPR2 itself measured), `KILL 1/0` 11=11 (D-MISS-1's operand's-own-fault
      rule), `NAME"NOSUCH.DAT"AS"Y.DAT"` 53=53. The apparatus is not the story.
      🎯 **THE DISCRIMINATOR IS WHAT MAKES IT A RULE AND NOT A ROW.** With an
      absent old file the reference's 53 has TWO sufficient causes — *lookup
      first*, or *never faults on the new-name operand at all*. `HI.TXT`
      **exists** on the test disk, so the lookup succeeds and the reference
      still answers 13. The reference rule is **look the old file up FIRST,
      then evaluate the new name, which then faults like every other verb.**
      🔴 **ZEROBAS IS WRONG IN BOTH ROWS, FOR DIFFERENT REASONS**: wrong ORDER
      when the old file is absent (24 where 53 is due), wrong FACE when it
      exists (24 where 13 is due). The FIRST `fname_expr` call did inherit
      D-FNEXPR2's fix — `NAME 5 AS"X.DAT"` agrees at 13 — so this is the
      **second operand position only**.
      🔴 **AND THE COMMENT ABOVE THE CODE ARGUED FOR THE INVERSE.**
      [`basic/files.asm`](basic/files.asm) read *"Evaluating early is what
      preserves the error ORDER … `NAME"x.dat"AS 5` is still `Syntax error`,
      not `File not found`"* — and `File not found` is precisely what the
      reference says there. The face it named is not the one this tree produces
      either. **Corrected in place 2026-08-26**: conclusion inverted, analysis
      kept [[a-fix-falsifies-the-justification-beside-it]].
      ⚠️ **OUT OF SCOPE FOR THE FIX WAS NOT OUT OF SCOPE FOR THE DENOMINATOR** —
      D-FNEXPR2 closed at six verbs while its own plan said *"a row on each of
      `OPEN`/`KILL`/`NAME`"*, and the verb it dropped is the one that diverges
      [[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]].
      💰 Not priced. The two rows above exist and are in **no gate**; the change
      is a REORDER in `do_name`, not a new tail — `els_tc_common` already ships
      the face. ⚠️ ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express
      `NAME`).
      🔭 SCOUT-THEN-ASK — the decision is yours; the measuring and pricing in front of it are not (charter / scope, but unpriced/unmeasured first).

- [ ] 🔴 **A TRAP HANDLER LEFT WITHOUT ITS `RETURN` IS PERMANENTLY DEAD — AND
      THAT IS FAITHFUL; WHAT IS NOT IS THE SIX-EVENT CAP.** Measured 2026-08-23,
      D-TRAPSVC, [`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §4/§6
      (`scratchpad/trapsvc_probe.py`, 7 rows x 3 machines, 2 knives EXACT).
      `RESUME <line>` **and** a plain `GOTO` out of an `ON INTERVAL` handler kill
      that trap on the VG-8020, the CF-3300 **and** zerobas alike (`1 0`), while
      `RESUME NEXT` — one keyword apart — keeps it alive on all three (`1 1`).
      The residual is `TRAPSVC`: it is decremented ONLY by `ex_return`'s
      `trap_return_check`, so each abandoned dispatch leaks a `TRAPSTK` record.
      After **6**, `ct_svc_full` raises ERR 7 with the entry still `ON`+`PENDING`
      and `TRAPPEND` still set, so it re-raises inside the active `ON ERROR`
      handler and the program **aborts** (`Out of memory in 800`). Row `int.six`:
      **`6 18` vs `9 18` on both references**; `gos.leak` (no trap in it) caps at
      **8**, which is what says the cap is `TRAPSTK_MAX` and not `GOSUB_DEPTH`.
      💰 **PRICED AND DECLINED**: the only fix that closes the class is popping
      the stale record when a `SERVICING` entry is explicitly re-armed, **~25–30 B
      of main page 1**, and it still misses a nested leak.
      🔴 **THE COST HALF OF THAT DECLINE IS STALE AND IS CORRECTED HERE, 2026-08-30:
      it read "against 2 B free (measured `b8a8137`)", and page 1 read 333 B free
      after D-CLRTRAP.** The ~25–30 B is affordable now. **The decline STANDS on
      its other half** — §6 rejects the two cheaper designs on principle and one
      of them makes a trap SILENTLY dead — so this stays 🙋. A price rots like a
      wall; re-read it before quoting a decline that rests on it. The two cheaper designs are rejected on principle in
      §6 — one of them makes the trap *silently* dead.
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).

- [ ] ⚠️ **KEY / STRIG / SPRITE / STOP were NOT run against the D-TRAPSVC rows.**
      2026-08-23, [`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §7.
      `ON INTERVAL` is the only self-firing MSX1 trap, so the other four are
      covered by a **code** argument (they share `check_traps`, `ct_find`,
      `set_state` and `trap_return_check` verbatim; the index is a parameter),
      not by a measurement. The device-driven harnesses exist
      (`basic_probe_key_trap.py`, T2/T4 probes) if the argument is ever attacked.
      ✅ **THE CODE ARGUMENT IS NOW A MEASUREMENT — ON `SPRITE`, 2026-08-26**
      ([`scratchpad/clrtrapstk_sprite.py`](scratchpad/clrtrapstk_sprite.py),
      [`scratchpad/clrtrapstk_sprite.out`](scratchpad/clrtrapstk_sprite.out)).
      🎯 **THE `CLEAR`/`TRAPSTK` DEFECT MEASURED THE SAME DAY IS A DISCRIMINATOR
      FOR EXACTLY THIS CLAIM**: it lives in `trap_return_check`, the routine the
      argument says all five traps share verbatim. Replaying that 2×2 with
      `SPRITE` instead of `INTERVAL` puts the SAME cell live and leaves the other
      three agreeing at 1:
      ```
      case                        vg8020   zb
      CLEAR, still SERVICING           1  250 (SATURATED)   DIVERGENCE
      CLEAR, trap killed               1    1
      no-CLEAR, still SERVICING        1    1
      no-CLEAR (control)               1    1
      ```
      So the sharing is real where it matters, and the defect is **worse** here:
      `SPRITE` re-fires once per FRAME, so the re-enabled trap saturated the
      counter and **starved the program** — it never completed its second wait.
      ⚠️ **ON THAT ROW THE MECHANISM CELLS ARE UNWRITTEN, NOT ZERO.** `TRAPSVC` /
      `TRAPENA` print as `0` because the starved program never reached the lines
      that `POKE` them. The `INTERVAL` run is where those cells were actually
      read (`TRAPENA=1`); here the evidence is the fire count and the starvation.
      🔴 **AND `basic_probe_sprite_trap.py`'s HEADER IS STALE.** It says
      *"`ON SPRITE GOSUB` is unimplemented on the zerobas side (D-G7-4 left
      `SPRITE ON/OFF/STOP` a no-op)"*. It fires — `basic/sprtrap-body.inc` is
      included via `subromcall.asm`, `ZTI_SPRITE` is a live index, and the
      control rows show one fire on both machines. Doc debt, filed not fixed.
      ➡️ **STILL A CODE ARGUMENT FOR `KEY` / `STRIG` / `STOP`** — those three need
      device input (key matrix, joystick, the STOP key), and the harnesses exist.
      `SPRITE` was taken first because a sprite collision is reachable from pure
      BASIC, so it needed no device at all. **1 of 4 converted.**
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (SPRITE measured 2026-08-26; KEY/STRIG/STOP still argued).

- [ ] 💰 **MAIN PAGE 1 WAS 1 B FREE ON 2026-08-23 AT `4db8010` — NOTHING LANDS
      THERE WITHOUT FUNDING FIRST.** Filed as its OWN open item because this
      section's preamble says exactly what happens to a residual written up
      inside a `- [x]` block: it is accurate, dated and invisible. D-PAINTMISS
      spent 3 of the 4 B that were free.
      🔴 **DO NOT QUOTE THE FIGURE ABOVE — `make basic-reloc` prints all four
      walls on every run** and a wall rots faster than this file does.
      **Two routes, neither costed here:** (a) a page-1 CARVE — the dup-span
      survey ([`docs/spec-basic-dupspan.md`](docs/spec-basic-dupspan.md),
      D-DUPSPAN/D-DUPSPAN2/D-XREG) is the standing method and has produced
      +50/+122/+46 B; (b) a PROMOTION into the page-0 low region (10 B free,
      2026-08-23), the shape D-MISSOPFIX used on `basic/title.asm`, which left
      the wall LOOSER than it found it.
      ⚠️ **Price a draft with a SCAFFOLDED build** (ceiling temporarily raised,
      read `__MEAS_PAGE1_END`, restore immediately) — `make basic-reloc` fails
      hard on overrun, so an unfunded draft cannot be measured any other way,
      and a scaffolded build **is a different machine**: a SIZE READING ONLY.
      🎯 And read D-PAINTMISS's own arithmetic before assuming a raiser costs
      5 B: with `jr` call sites a 3 B trampoline to an EXISTING `*_missing`
      label beat both the inline raiser (5 B) and widening the jumps (+4 B).
      Check for an existing label before writing one.
      🙋 NEEDS-JOOST — a call that is yours to make (no oracle can settle it).

- [ ] 📏 **CARVE SCOUT 2026-08-24 — TWO OF THE THREE FUNDING ROUTES FOR MAIN
      PAGE 1 ARE MEASURED SHUT.** Measurement only, no byte moved
      ([`docs/spec-carve-scout-2026-08.md`](docs/spec-carve-scout-2026-08.md)).
      Read this BEFORE opening any slice that needs main page-1 bytes.
      * **Route A, the dup-span collapse: EXHAUSTED.** 1440 spans walked, 27
        byte-identical groups, 190 B nominal → **MEASURED SAFE NET 4 B**
        (`tools/dupspan_indep.py`). Every large group dies on one of the three
        blind spots — an escaping relative jump, running off its own end, or
        fallthrough entry. D-DUPSPAN/D-DUPSPAN2/D-XREG worked this seam out.
        ⚠️ Includes this week's own `ep_missing` ≡ `wid_missing`, priced at
        **NET +1 B** because four `jr` edges would have to widen.
      * **Route B, eviction to a page-0 sub-ROM tenant: STRUCTURALLY CLOSED FOR
        VERBS**, despite 2563 B free over there. 🔴 **A verb that can PRINT or
        can RAISE AN ERROR reaches the BIOS transitively** (`pchar → CHPUT`,
        `raise_error → BREAKX`), and a page-0 tenant runs with that region
        switched out. Five candidates sized at 177–762 B of movable code and
        **all five refused, all by those same two paths**. 🎯 The shipped
        tenants (circle generator, flood fill, string heap) are pure computation
        reporting errors through a SLOT rather than raising — that is the only
        shape the slot configuration permits, not a style choice.
        📏 **Denominator: 5 files of 22 tested.** The blocker is generic so it
        very likely generalises, and the cheap way to settle it is to ask
        whether ANY page-1 entry point avoids both `pchar` and `raise_error`.
      * **Route C, the page-1 eval-bounce co-routine: OPEN, UNPRICED.** Sub page
        1 has 1617 B free and `sub/circleparse.asm` proves a verb's grammar can
        live there via `GFX_DREQ` request/resume. It is the only route left for
        a verb and it is not cheap — pricing it means picking a verb and
        counting its value requests.
      ⚠️ `tools/carve_scout.py --census` prints nothing and exits 0 without
      `--files` (documented, but it is the 0-byte-report-at-rc-0 shape).
      🙋 NEEDS-JOOST — a call that is yours to make (page-1 budget).

- [ ] ⚠️ **AN UNNAMED OUTCOME READS AS NO OUTCOME, AND THE FIX MOVES THE HOLE
      ONE MESSAGE ALONG.** Filed 2026-08-23, D-CLRTRAP §5 — a probe-design
      residual, not a BASIC one. `face()` knew only about a numeric fence, so an
      untrapped `Missing operand in 30` scored `<NO OUTPUT>`; naming
      `UNTRAPPED <msg> in <line>` fixed it, and **within the hour `t.after`
      scored `<NO OUTPUT>` on ALL THREE machines because "Division by zero" was
      missing from the new alternation.** 🎯 Every probe in this tree that
      buckets an unmodelled result as *"nothing"* has this shape. The standing
      question: **what might the machine legitimately DO that this readout has
      no name for — and when you add one name, what is the next one?** No gate
      covers it; `scratchpad/circmiss_sib2.py` carries the widened list.
      📏 **THE STANDING QUESTION NOW HAS A NUMBER — SWEPT 2026-08-26**
      ([`scratchpad/unnamed_outcome_sweep.py`](scratchpad/unnamed_outcome_sweep.py),
      [`scratchpad/unnamed_outcome_sweep.out`](scratchpad/unnamed_outcome_sweep.out)).
      Denominator is the ROM's OWN table — every `db "…",0 ; ERR n` in
      [`sub/errmsg.asm`](sub/errmsg.asm), **30 messages** — so it cannot drift
      from what the machine can print.
      ```
      probes with a <NO OUTPUT> bucket            53
        classify by MESSAGE TEXT  (the subject)   31
        classify by ERR code / span / VRAM        22
      coverage of the canon      min 1   median 6   max 15
      COMPLETE readouts                            0 of 31
      sentinels that do NOT carry the text        52 of 53
      ```
      🎯 **SO "ADD THE NEXT NAME" IS PROVABLY UNBOUNDED, WHICH IS THE ITEM'S OWN
      THESIS MEASURED.** Not one readout in the tree can name even half the
      canon; the widest — `basic_probe_fldwidth.py`, 15/30 — is still blind to
      `Bad FAT`, `Bad drive name`, `Bad file name`, `Bad sector number`,
      `Can't CONTINUE` and ten more. The file this item names as carrying the
      widened list, `scratchpad/circmiss_sib2.py`, reaches **11/30**: genuinely
      widened, still less than half.
      ➡️ **THE DURABLE FIX IS THE SELF-DESCRIBING SENTINEL, NOT A LONGER
      ALTERNATION** — emit the unrecognised screen text INSIDE the sentinel, so
      an unmodelled outcome names itself and the hole cannot move one message
      along. **52 of 53 sentinels are bare literals**; exactly one already does
      this. It is the same cure as `omsx_repl._why_missing` and D-PASMOSAY, both
      of which turned a silent `<NO CAPTURE>` into a diagnosis.
      ⚠️ **NOT MASS-EDITED, DELIBERATELY.** It is ~52 sites whose printed output
      IS the evidence for shipped slices, and today's lesson is that a mechanical
      sweep whose blast radius cannot be verified breaks invariants its own rule
      cannot see [[a-mechanical-fix-can-break-a-different-invariant]]. Convert
      opportunistically, when touching a probe anyway — and the sweep above is
      the standing measure of how far that has got.
      🔴 **MY OWN FIRST DETECTOR MEASURED THE SPELLING, NOT THE LIST**: it looked
      for quoted literals and scored `circmiss_sib2.py` at **1/30**, because that
      file spells its list as a regex alternation. It was the anomaly — the item
      names that file as the remedy — that exposed it, not the tally.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (measured 2026-08-26; conversion is opportunistic, the sweep is the standing measure).

- [x] ⚠️ **`CLEARPOOL=0` IS UNTESTED AND CANNOT BE ADDED TO
      `switch-build-check`.** 2026-08-23, D-MISSOPFIX. `FPERR_MISSOP` is equated
      inside the `IF CLEARPOOL` in `basic/sysvars.inc` (12 with, 11 without)
      because `fperr_to_err` is a **dense** table whose next free index moves
      with the switch — and an off-by-one is SILENT: it reads a neighbouring
      byte and reports some other error. The `ELSE` arm has never been
      assembled. `tools/check_switch_builds.py` cannot cover it: its scope claim
      is *"no switch is read outside `basic/`"* and **CLEARPOOL is read from
      `sub/arrays.asm` and `sub/strheap.asm`**, so adding it to `SWITCHES` trips
      the tool's own `scope_holds()` check. Widening the tool to two-ROM builds
      is the fix; unpriced.
      ✅ **BOTH DONE 2026-08-26: THE ARM IS ASSEMBLED *AND* THE GATE COVERS IT.**
      ```
      CLEARPOOL=1   main+sub assemble   FPERR_MISSOP=12   fperr_to_err[12]=24
      CLEARPOOL=0   main+sub assemble   FPERR_MISSOP=11   fperr_to_err[11]=24
      ```
      The `ELSE` arm builds — **both ROMs** — and in each arm the dense table's
      slot holds **24**, so the equate and the table have not drifted. The
      feared silent off-by-one does not exist today
      ([`scratchpad/clearpool_off.py`](scratchpad/clearpool_off.py)).
      🎯 **THE SCOPE CLAIM WAS THE PROBLEM, SO THE SCOPE IS NOW PER-SWITCH.**
      `SWITCHES` is a dict of *switch → trees it is read from*, and `assemble()`
      builds every tree the switch declares. **A global claim of "no switch is
      read from `sub/`" had excluded the one switch that most needed covering** —
      a scope that excludes its hardest case has chosen its own denominator.
      `CLEARPOOL` is in the gate now: **7 of 7, `(basic+sub)`.**
      🔴 **AND ASSEMBLING IS THE EASY HALF.** The failure this item was FILED for
      *builds*: a wrong index reads a neighbouring byte and raises some other
      error. A switch may now declare a **POSTCHECK** read back out of the
      assembled image; `CLEARPOOL`'s asserts `fperr_to_err[FPERR_MISSOP] == 24`,
      and the baseline must satisfy it too or the run refuses.
      🔬 **FALSIFIED BY PLANTING, TWICE, EACH RESTORED BYTE-IDENTICALLY.** A
      break visible only in the OFF arm → `FAIL CLEARPOOL`, 6 of 7. And an
      off-by-one that **assembles perfectly** (`FPERR_MISSOP equ 10`) →
      *"fperr_to_err[FPERR_MISSOP=10] is 13, want 24 — the equate and the dense
      table have DRIFTED APART, and a raise there would report ERR 13"*. Without
      the postcheck that second plant is a clean PASS.
      🔴 **MY OWN FIRST TABLE READ WAS A FALSE RED**: it fell back to a default
      org of `0x4000` when it found no `MAIN_ORG` symbol (there is none — it is
      `BASIC_ORG`, `$2812`) and reported bytes **32** and **67** on a tree that
      is fine. An offset computed from a default is not a reading.

- [x] ⚠️ **NO GATE READS THE BOOT BANNER, AND D-MISSOPFIX MOVED IT.** 2026-08-23.
      The 5 B fix was funded by PROMOTING `basic/title.asm` from page 1 into the
      low region. Every probe program in this tree opens with `CLS`, which wipes
      the startup header, so **not one of the 34 gates would notice if
      `show_title` stopped printing.** `scratchpad/missop_circle.py`'s `banner`
      row is a one-off check (run without `CLS`, assert the header text is on
      screen); it is NOT a gate. Making it one is cheap and unclaimed.
      ✅ **GATED 2026-08-26 — `make banner-acceptance`, a unit of `make gates`**
      ([`probes/basic/basic_probe_banner.py`](probes/basic/basic_probe_banner.py)).
      No `CLS` anywhere; asserts both header lines are above the prompt.
      🎯 **THE EXPECTATION IS READ OUT OF THE SOURCE**, not pinned in the probe
      ([`basic/title-body.inc`](basic/title-body.inc)) — a copy would rot the day
      the banner changes, and the gate would then be "fixed" by editing the
      expectation to match whatever it now prints, which asserts nothing.
      🎯 **AND THE PROGRAM'S OWN MARKER IS THE CONTROL.** Header absent + marker
      absent is a machine that never booted, not a banner that stopped printing;
      that case is **rc 2, an instrument fault, never a verdict**
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      🔬 **K-BANNER** ([`scratchpad/banner_knife.py`](scratchpad/banner_knife.py)):
      marker `' 7  0 '` printed, **both header lines GONE**, gate RED. Restored
      byte-identically, mtime deliberately NOT preserved (D-KNIFEGUARD).
      🔴 **THE FIRST KNIFE WAS THE WRONG CUT AND THE GATE'S OWN CONTROL CAUGHT
      IT.** Cutting `call show_title` in `interp.asm`'s init gave a screen of
      GARBAGE — banner *and* marker gone — because the body opens with
      `call INITXT`, which is what puts the VDP in SCREEN 0 text mode. That cut
      tested *"no text mode"*, not *"no header"*, and the gate refused to score
      it (rc 2) instead of reporting a false RED. The surgical cut keeps `INITXT`
      and returns before the print loop.

- [ ] 🔴 **A RULE WITNESSED ONLY BY A *DEFERRED* ERROR IS WITNESSED BY NOTHING —
      and one shipped guard was in exactly that state.** Filed 2026-08-23 by
      D-DEFFNKNIFE,
      [`docs/spec-basic-deffnknife.md`](docs/spec-basic-deffnknife.md) §4.
      `raise_error`'s `FN_FEND` reset had a comment in TWO files
      (`basic/interp.asm`, `sub/arrays.asm`) naming `o.errrestore` as *"the row
      that says so"*. Knife K-FE1 disabled the reset and `deffn-strict` stayed
      **0 of 69 divergent**: `X/0` is a DEFERRED FPERR *"realized at the
      statement boundary"* (`fp_runtime_error`'s own header), so the FN call
      RETURNS NORMALLY, `fn_leave` restores the frame, and `raise_error` runs
      with nothing stale to reset. ✅ **The instance is CLOSED** — `o.errfend18`
      / `o.errfend13` were measured on both references (`5 18` / `5 13`, and
      `2 18` / `2 13` under the knife), added to the row set (`deffn-strict` is
      now **0 of 71**), and both comments corrected.
      📏 **SCOUTED 2026-08-23**,
      [`docs/deferblind-scout-2026-08-23.md`](docs/deferblind-scout-2026-08-23.md),
      no ROM byte moved. **21 `penderr_set` sites; exactly ONE raises on the
      spot** (`str_heap_oom_error`), the other 20 return — so ERR 6/11/5/2/9/7/
      10/13 can EACH arrive deferred or immediate depending on the SITE, and
      🔴 **the ERR code a row expects carries NO information about whether that
      row can witness an ordering-sensitive guard.** The class was then stated
      checkably (*a cell meaning "we are inside X", cleared by X's normal exit,
      NOT cleared at the statement boundary, and READ outside X* — `exec_stmt`'s
      own `xor a / ld (PRDEST),a` is why PRDEST is safe by construction and
      FN_FEND was not) and **measured EMPTY for the FOR stack, the GOSUB stack
      and the string heap**: 27 of 27 readings agree across both references and
      zerobas. ✅ **And the instrument was CALIBRATED on the known positive** —
      the same 12 rows re-run under K-FE1 move `fn.imm` (`5`→`2`) and **nothing
      else**, so the nine zeros are a reading and not a silence.
      🔴 **STILL OPEN — THE DENOMINATOR IS THREE CONSTRUCTS.** 96 cells in
      `sysvars.inc` describe themselves as live/in-progress/pending; the
      "read outside X" filter leaves a short untested list, headed by
      **`TRAPSVC`** (incremented on trap dispatch, decremented ONLY by
      `ex_return`'s hook — so a handler left via `RESUME <line>` never
      re-enables its trap, and `TRAPSTK_MAX` is 6), then `FCH_ACTIVE`/`FCH_NUM`/
      `FCH_MODE` and `GFX_DFTOP`. ⚠️ **`TRAPSVC`'s trigger is a DIFFERENT one** —
      *RESUME out of a trap handler*, not deferred-vs-immediate — and both
      references would be expected to leak too, so it needs its own reference
      measurement. Use §4's shape: three ways (immediate / deferred / no fault)
      and prove the row can go red before believing a zero.
      ⚠️ `o.errrestore` looked like a *stronger* row than the two that
      replaced it, and nothing but a knife could tell.
      🔴 **`TRAPSVC` MEASURED 2026-08-26 — AND IT IS A LIVE DIVERGENCE WITH A
      CEILING OF SIX.**
      ([`scratchpad/trapsvc_depth.py`](scratchpad/trapsvc_depth.py),
      [`scratchpad/trapsvc_depth_screen.py`](scratchpad/trapsvc_depth_screen.py)).
      Same program on both machines: an `ON INTERVAL` handler that re-arms and
      leaves by `GOTO` — the leak form, which needs no fault at all.
      ```
      zerobas    dies after 6 leaked dispatches:  "Out of memory in 900"
      VG-8020    no error at all in the same window; still running
      control (handler RETURNs)   30 fires, err 0, done 1 — IDENTICAL on both
      ```
      🎯 **SIX IS `TRAPSTK_MAX`.** `check_traps` guards `cp TRAPSTK_MAX` and
      jumps to `gosub_stk_over` → ERR 7. The references have no `TRAPSTK`; they
      leak GOSUB frames, and that stack is far deeper.
      🔴 **AND THE FAILURE IS UNTRAPPABLE.** The message is *"Out of memory
      **in 900**"* — line 900 is the `ON ERROR` handler. The raise enters the
      handler, the handler needs a frame it cannot have, and the program stops
      dead. So `ON ERROR` does not merely fail to help; it is the line that gets
      blamed.
      ⚠️ **THE `141` FROM THE COUNTER RUN IS NOT QUOTED AS A COUNT.** That read
      came back with `err=115` and `done=76` beside it — neither a valid ERR nor
      a valid flag — so the whole $D000 window is untrustworthy on a program
      that never finished. The screen is the reading; "well past 6" is all the
      counter supports.
      ⚠️ **ONE REFERENCE.** `basic_probe_interval_trap` has only ever driven the
      VG-8020; pointing its `run()` at the CF-3300 returned an **all-$FF** window
      on every row, which the first cut printed as `fires=255 err=255 done=255`
      — garbage read as data. The probe now calls that an instrument fault.
      🎯 **SO THE FILED SHAPE HELD BUT THE TRIGGER WAS NARROWER THAN THE CLASS,
      AGAIN**: the item says *"RESUME out of a trap handler"*; a plain `GOTO`
      does it, with no error anywhere, and that is the form measured here
      [[trapsvc-slice]].
      💰 **NOT PRICED, AND THE FIX IS A SPEND.** Raising `TRAPSTK_MAX` costs
      3 B per slot of RAM; popping the record when a frame is abandoned costs
      main page-1 bytes. Both are budget decisions.
      🔭 SCOUT-THEN-ASK — measured and isolated 2026-08-26; the FIX costs bytes, which is yours to spend.

- [ ] ⚠️ **DEF FN's knife roster is EIGHT, and eight is a candidate roster, not a
      verdict.** Filed 2026-08-23 by D-DEFFNKNIFE,
      [`docs/spec-basic-deffnknife.md`](docs/spec-basic-deffnknife.md) §9.
      `scratchpad/deffn_knives.py` (+ `scratchpad/deffn_de_knife.py`'s K-DE1)
      now cut the ceiling in BOTH directions, `fn_leave`'s DE, PRINT's item
      classification, the result-type coercion, the frame reset and the stack
      floor. **Unknifed and named**: the phase discriminator (`dfn_is_result`'s
      `inc a` — what reddens if the body and actual phases are confused?),
      `fn_enter`'s "only the live part" copy length, the `$FFFF` result-slot
      **key** (K-RT1 cuts the TYPE it writes, not the key), `dfn_delim`'s
      two-cursor swap, and `dfn_a_x`'s grow-never-shrink `FN_FEND` rule. Each was
      skipped because its predicted set is wide (most of the successful-call
      rows) and a wide prediction scored EXACTLY is worth less than a narrow one
      — but "wide" is a guess until it is measured
      [[a-hand-listed-denominator-is-a-scope-claim]].
      ✅ **THREE OF THE FIVE KNIFED 2026-08-26 — ROSTER 9 → 12, ALL EXACT**
      ([`scratchpad/deffn_knives.py`](scratchpad/deffn_knives.py)). *"Wide" was
      a guess until measured; it is now three different numbers.*
      ```
      K-IR1  dfn_is_result `inc a` -> `or a`        42 of 71 rows
      K-DL1  dfn_delim `cp c` -> `cp a`              2 rows
      K-GS1  dfn_a_x grow-never-shrink guard removed 0 rows
      ```
      🔴 **K-DL1 FALSIFIED THE COMMENT ABOVE ITS OWN SITE.** `dfn_delim`'s header
      claimed the compare *"is the WHOLE of the arity rule, and it is why ERR 2
      comes out of `FNA(1,2)` on a one-formal FN (o.toomany)"*. With the two
      delimiters forced to agree, `o.toofew` and `o.aryformal` go red and
      **`o.toomany` does NOT** — too many actuals is still ERR 2, decided
      somewhere else. A comment naming three rows owned two. **Corrected in
      place**, 0 ROM bytes (hashes unchanged)
      [[a-fix-falsifies-the-justification-beside-it]].
      🔴 **K-GS1 REDDENED NOTHING — 0 of 71.** `deffn-strict` cannot witness the
      grow-never-shrink rule at all, so the 2 B `jr c,dfn_a_x` guard is
      **unobservable by this row set**. Encoded EXACT with an empty prediction,
      because the emptiness IS the result
      [[knife-that-reddens-nothing-is-the-finding]]. ⚠️ That is not a licence to
      delete it — D-RESUME's withdrawal had a row that CONTRADICTED the rule;
      this has none either way. What it says is that nothing here would notice
      if the guard were wrong.
      🟢 **AND K-IR1 VINDICATES THE ITEM'S OWN REASON FOR SKIPPING IT**: 42 of 71
      rows scored exactly says very little about the one line cut, which is
      precisely why a wide prediction is worth less than a narrow one.
      ➡️ **TWO REMAIN**: `fn_enter`'s "only the live part" copy length and the
      `$FFFF` result-slot **key** (K-RT1 cuts the TYPE it writes, not the key).
      Neither has a label this sweep could site precisely; they need reading
      before cutting.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (3 of 5 knifed 2026-08-26; 2 remain, unsited).

- [ ] ⚠️ **`clone_scout` prices LABEL-BLOCKS, so a routine split by an interior
      label is priced at a fraction of its collapse.** Filed 2026-08-23 by
      D-DEFFNLAND, [`docs/spec-basic-deffnland.md`](docs/spec-basic-deffnland.md)
      §4.3. `arga_pack_fac`/`arga_pack_single` were ranked at **14 B** and
      measured at **27 B**: the tool compared only their 22-byte header spans,
      because `apf_lp`/`aps_lp` are separate symbols, so the two identical
      13-byte LOOPS were invisible to it. The remaining ranked groups are
      therefore FLOORS, not estimates — and 🔴 **three of them are now known to
      be worth ZERO** (§4.4: `ev_t_mul`/`ev_t_div`, `ev_e_add`/`ev_e_sub`,
      `dde_div`/`pn_div`/`pfi_div` all push PERSISTENT frames a helper's own
      return address cannot sit under). Unspent and unre-ranked:
      `raf_noround`/`rsp_noround` (12), `ev_usr_index`/`usr_index` (8),
      `detok`/`pu_emit_tail` (8), the `files.asm` four (8),
      `ev_ff_stick`/`ev_ff_strig` (6).
      ✅ **`clone_scout --extend` SHIPPED 2026-08-26 — AND THE RANKED GROUPS ARE
      NOT FLOORS TODAY.** After grouping, each group now grows forward across
      label boundaries while every member's next block still agrees, bounded by
      a real terminator.
      📏 **CALIBRATED EXACTLY ON THIS ITEM'S OWN EXAMPLE.** `head 22 B` alone
      gives `save = (n-1)·22 − 4n = **14**`; extended by the 13-byte loop it
      gives `save = (n-1)·35 − 4n = **27**` — the two numbers the item records
      as *ranked* and *measured*. The match test was verified against the
      pre-carve source (`dd0c84d~1`), where the two loop bodies compare EQUAL.
      🔴 **AND ON TODAY'S TREE IT FINDS NOTHING.** 8 groups extend
      (`dde_div` +11 B, `vsf_single` +42, `print_string` +57, …) and **not one
      of them reaches the ranked table**; every group that IS ranked extends by
      **zero**, so the ranked rows are byte-identical with and without the flag.
      The floors claim is now measured, and it is currently vacuous.
      🎯 **THREE SHAPES, AND ONLY THE CALIBRATION SEPARATED THEM.**
      **(1) merge-then-match** — pre-merging blocks into terminator-delimited
      runs made spans LONGER and so LESS likely to match: **10 groups / 55 B**
      against 27 / 180. Two routines sharing a prefix and diverging after it are
      a real clone at block granularity and vanish at run granularity. Wrong
      shape, discarded.
      **(2) strict extend** — required successors byte-identical, and **failed
      this item's own example**: `apf_lp`/`aps_lp` differ in exactly one
      position, `djnz apf_lp` vs `djnz aps_lp`, each block's jump into ITSELF.
      **(3) alpha-normalised extend, terminator-bounded** — normalise a block's
      own label to `<self>` before comparing, and stop where the routine does.
      🔴 Unbounded, (3) ran away: `gosub_stk_over` grew **+1307 B** and
      `tokenise` **+1107 B** — the rest of the file, not a clone. Those values
      never reached the output, which was LUCK, not design.
      ⚠️ **THE `arga_pack` PAIR IS ALREADY SPENT** — `basic/float-arith.asm` now
      carries *"Two ENTRY POINTS … is 27 B smaller"*, so the item's example is
      history, not a candidate. That is why the calibration had to be done
      against `dd0c84d~1` and by arithmetic rather than by re-ranking it.
      ➡️ The five unspent groups it lists are unchanged by this: they do not
      extend. Re-ranking them is still owed, but not for the label-block reason.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (tool fixed + calibrated 2026-08-26; the ranked groups extend by zero).
- [ ] ⚠️ **Main page 1 is 2 B free and the low region 17 B, at
      `031184d9`/`34bb8554` (2026-08-23).** Filed by D-DEFFNLAND. The next slice
      that adds a byte to page 1 has to carve one first or promote again;
      `scratchpad/region_sizes.py` prints per-include sizes split by region,
      which is how `poke.asm`+`sound.asm` were picked. **Run `make basic-reloc`
      — it prints all four walls; never quote this line.**
      🙋 NEEDS-JOOST — a call that is yours to make (page-1 budget).
- [ ] ⚠️ **D-DUPSPAN2 shipped 28 aliases with NO per-site row set.** Filed
      2026-08-22, [`docs/spec-basic-dupspan2.md`](docs/spec-basic-dupspan2.md)
      §5.1. Eleven emulator batteries say the collapse broke nothing; none of
      them can say it was OBSERVABLE — a site nothing exercises stays green
      through any mistake made to it, which is why D-DUPSPAN built
      `scratchpad/dupspan_probe.py` and cut its canonical VALUES. The substitute
      here is `tools/dupspan_indep.py`'s machine-checked per-alias verdict, an
      argument about the MECHANISM rather than the observable. Owed: one row per
      aliased site, and a knife per canonical whose predicted set is that
      canonical's aliases and nothing else.
      📏 **THE PER-SITE DENOMINATOR EXISTS NOW, TAKEN FROM THE SOURCE**
      ([`scratchpad/dupspan2_roster.py`](scratchpad/dupspan2_roster.py)): **27
      aliases in 16 files, 21 distinct canonicals**, each named with its
      canonical and its file:line. A per-site row set needs a per-site list, and
      the list was a sentence in a spec.
      🔴 **AND IT IS 27, NOT 28 — THE SPEC'S §3 HEADING CONTRADICTED ITS OWN
      §6.** The 28th is `dr_stored equ dl_run`, which §6 records as **DECLINED**
      (its comment holds a deliberately unshipped `jp run_prog_top` that an
      `equ` would erase). The heading was written before that decision and never
      re-counted; the FILE count, 16, was right all along. **Corrected in
      place** [[two-sections-of-one-doc-disagreed]].
      🔴 **AN ALIAS IS SPELLED TWO WAYS AND A SCANNER THAT KNOWS ONE
      UNDERCOUNTS.** `ee_synerr_pop:` is a LABEL; `poke_err equ ex_let_err` is an
      EQU. My first cut looked only for `^name:` and resolved **22 of 27** — and
      the five it could not place were all EQUs, which are the *clearest* aliases
      in the tree [[a-hand-listed-denominator-is-a-scope-claim]].
      ➡️ **THE OBSERVABILITY HALF IS STILL OWED, AND NOW IT IS PRICED.** The
      knives the item asks for are **21** (one per canonical, not 27), each
      needing its own battery to score — roughly 21 × 7 min. That is the real
      cost of turning the mechanism argument into an observable, and it is why
      nobody has done it; a cheaper design (one knife reddening several
      canonicals at once) cannot say WHICH site was observed, which is the whole
      question.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (roster + count fixed 2026-08-26; the 21 knives remain, now priced).

- [ ] ⚠️ **A probe with an honest `rc` that NO battery collects is not an oracle.**
      Opened 2026-08-27 by D-WALLIT,
      [`docs/spec-wall-literals.md`](docs/spec-wall-literals.md) §3.1.
      `basic_probe_cas_verbs.py` had **two failing cases for an unknown number of
      months** — it returns a correct `rc=1`, it is listed in `README.md:360`, and
      nothing ever ran it. The new `wall-literal-check` covers the CAUSE of that
      particular break (a stale address literal) but not the SHAPE: a probe outside
      every battery fails silently for any other reason too. **Two things are owed
      and only the first is autonomous:** (a) COUNT the probes that no `make` target
      and no battery invokes — the denominator is unmeasured, and `cas_verbs` was
      found by accident; (b) decide which of them earn a battery slot. (b) is a
      RUNTIME-BUDGET call: `cas_verbs` alone is a ~4 min tape probe against a 426 s
      battery, so adding the tape corpus could roughly double it.
      🙋 NEEDS-JOOST — a call that is yours to make (battery runtime budget). The
      COUNT in (a) is autonomous and should be measured first; the spending is not.

- [ ] ⚠️ **`DEF FN`: two formals of ONE call can alias, and no row separates
      it.** Filed 2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](docs/deffn-impl-2026-08-22.md) §8. The
      draft binds in place: `FNA(P,Q)` called as `FNA(X, X*2)` from inside an FN
      whose own formal is `X` writes slot 0 before the second actual reads it.
      The reference's behaviour is UNMEASURED — the 82-row design set has no
      case where a caller's formal is read by a LATER actual of a callee that
      overwrites it. Needs a reference reading before the fix is priced; the
      alternative (evaluate every actual into a stack temp first) is ~30 B in a
      region that has none.
      ✅ **THE REFERENCE READING IS TAKEN (2026-08-27, D-FNALIAS),**
      [`docs/spec-deffn-alias.md`](docs/spec-deffn-alias.md). Premise re-run on the
      SHIPPED code, not the draft it was filed against. **Both references agree, so
      there is an oracle: every actual is evaluated in the CALLER's scope.**
      `DEF FNA(P,Q)=P*100+Q : P=3 : FNA(5,P)` → ref **503**, zb **505**;
      `DEF FNA(X,Q)=X*100+Q : DEF FNB(X)=FNA(9,X) : FNB(3)` → ref **903**, zb **909**;
      both controls green at 507/907. ⚠️ I predicted zb correctly and guessed the
      reference WRONG — it does not shadow.
      🔴 **TWO ROWS, TWO CAUSES, NOT ONE FIX.** Top-level is the *grow, never shrink*
      in `dfn_a_x` (deleting it fixes that row and FREES 8 B). Nested is `fn_enter`
      resetting `FN_SLOTP` to slot 0, which **physically overwrites** the caller's
      slot — the grow is not even involved.
      🎯 **This is why D-DEFFNKNIFE's K-GS1 reddened ZERO rows**: it cut exactly that
      block and no row separated the behaviours. `o.alias` is that row.
      🔴 **THE ITEM'S PRICE WAS WRONG AND ITS CONCLUSION SURVIVES ANYWAY.** The fix
      lands in `sub/` (**2464 B free on page 0**, measured), not "a region that has
      none" — but the cheap design (slots above the caller, relocate at `dfn_body`,
      ~+17 B) is **REFUTED BY A SECOND MEASUREMENT**: `FN_AREA` is exactly nine slots
      (`((LINEBUF - FN_PAREA)/11)*11`) and the reference gives **nine formals to a
      NESTED call too** (`o.p9nest` = 9/9/9) — which zerobas matches *precisely
      because it clobbers*. Two coexisting frames need ~198 B where 99 exist.
      ⚠️ The four `o.alias*` rows are deliberately NOT in the probe: `deffn-strict`
      has no XFAIL class and a knowingly-red row would redden a green battery.
      They reproduce from `scratchpad/deffn_alias_probe.py`; adding them is step 1
      of whichever fix is chosen.
      🙋 NEEDS-JOOST — a call that is yours to make (page-3 RAM eviction below
      LINEBUF, or accept one of two MEASURED divergences: fix top-level only for
      −8 B and leave the nested row, or grow the shadow area ~+99 B of RAM).

- [ ] ⚠️ **`DEF FN`: a STRING formal's shadow slot is not a GC root.** Filed
      2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](docs/deffn-impl-2026-08-22.md) §8. The
      slot holds a `[len][ptr]` descriptor and `strheap_gc`'s walk enumerates
      the variable chain and the temp-descriptor stack, not this area. No
      measured row provokes a collection inside an FN call (all three string
      rows concatenate into a temp), so this is a hole in the ROW SET as much as
      in the code — the fix is either a `sg_walk_fnframe` or a snapshot at bind
      time, and the ROW that would catch it does not exist yet.
      ✅ **THE ROW EXISTS, IT WENT RED, AND THE LIVE FRAME IS FIXED (2026-08-27,
      D-FNGCROOT),** [`docs/spec-deffn-gcroot.md`](docs/spec-deffn-gcroot.md).
      Both halves of the premise re-ran true on the SHIPPED code. `sg_walk_fnframe`
      walks `[FN_PAREA, FN_FEND)` — **30 B of sub page 0** (2464 → 2434); main ROM
      does not move (low 39 B, page 1 89 B, identical). `o.gcroot` **`376A` →
      `ABCD`**; four rows now gate under `deffn-strict`.
      🔴 **TWO ROUNDS OF GREEN PROVED NOTHING FIRST.** Round 1's "does the heap
      move" arm used `VARPTR`, which is the DESCRIPTOR address and never moves —
      blind, and kept as a negative control. Reading the descriptor's PTR field
      instead showed the body moves **UPWARD** (47851 → 47868), and the dead copy
      is the LOWEST allocation — so a collection alone moves everything AWAY from
      it. The catching row needs THREE things: a formal, a collection, and an
      **allocation after it**. Three controls each remove exactly one.
      🔴 **A CONTROL CAUGHT A CONFOUND BEFORE THE SUBJECT DID** — at `CLEAR 100`
      the no-FN variable control failed on zerobas with `Out of string space`
      while both references returned ABCD. Filed separately below.
      ⚠️ **RESIDUAL, MEASURED NOT IMPLIED:** the walk covers the LIVE frame only;
      an OUTER frame is parked on the Z80 stack where no walk can reach it.
      `n.outer` → zb `q75AB` vs ref `qABCD`, control green. **Same root cause as
      D-FNALIAS** — `fn_enter` resets `FN_SLOTP` and stacks the caller — so both
      want frames that coexist in the shadow area, which needs page-3 RAM.
      🙋 NEEDS-JOOST — the RESIDUAL only (page-3 RAM below LINEBUF, shared with
      D-FNALIAS). The live-frame half is shipped and gated.

- [x] 💰 **THE GENERIC ERROR-LAYER SEAM: per-verb error checks that duplicate a
      layer that already exists — a carve AND a correctness seam.** Opened
      2026-08-24 by D-SWAP3, [`docs/spec-basic-swap3.md`](docs/spec-basic-swap3.md)
      §6, on the user's observation that SWAP is one instance of a class. **Two
      generic layers get reimplemented per-verb:**
      * **Trailing-token → ERR 2**: `exec_stmt`'s `es_noentry`
        (`basic/interp.asm`) already raises `Syntax error` for any leftover token
        after a statement returns via `jp exec_stmt`. Bespoke duplicates alias
        `pl_syntax` and are reached from a `cp ','`/`cp COLON`/`or a` peek PAST
        the last valid argument: `graphics.asm:748/798` (PAINT 3rd/4th arg),
        `1203`/`1210` (`PUT SPRITE 0`/`0,`), `1250` (5th sprite arg),
        `play.asm:73` (PLAY 4th voice). **DELETED so far: SWAP, PAINT `:798`,
        SPRITE `:1250`, CIRCLE `cpt_asp_done`** (D-SWAP3/D-PAINT4/D-SPRITE5/
        D-CIRCTC). ⚠️ The incomplete-arg siblings (PAINT `:748`, SPRITE
        `:1203`/`:1210`) are NOT deletable — they raise before the effect and
        agree on both refs — the per-site oracle split, measured. PLAY `:73` is
        KEEP (raises before playing). 🟢 **CIRCLE turned out DELETABLE too, not a
        restructure** (D-CIRCTC — the classifier's one wrong verdict, reasoned not
        measured): the resident's `cp_done` already `jp exec_stmt`s after the
        draw, so the trailing comma delegates like the other three. **ALL FOUR
        trailing-token members are now SHIPPED; this half of the seam is CLOSED.**
      * **Missing/empty operand → ERR 24 / ERR 2**: `ev_f`'s
        `ev_f_missop`/`ev_f_empty` machinery — the D-MISSOP arc already found
        this is *"one rule at 16 slots"* (docs/spec-basic-missop.md).
        🟢 **FIVE MEMBERS SHIPPED 2026-08-26, AND ONLY KEY'S ABSENT FORM IS
        LEFT** (and that one is BLOCKED on ~160 B of defaults data, not on
        knowledge). What each one COST: `ev_f_err`'s seven sites (D-EVFERR)
        spent **0 B**; `PLAY` (D-PLAYOP) spent **+2 B**; `PRINT USING`
        (D-PUSING) **freed 6 B** and turned 2 filed rows into 13; `MID$()=`
        (D-MIDOP) spent **+6 B**, and spent it in the low region, not page 1;
        `DRAW` (D-DRAWOP) spent **0 B**.
        🎯 **ONE RULE, THREE VERBS, THREE DIFFERENT PRICES.** The last three
        slices all split the SAME shared tail — `call str_eval / jp nc,<one
        error>`, where str_eval declines both for *"nothing is here"* and for
        *"this is not a string"* and the references answer **24** and **13**.
        The rule is shared; **the price is a property of each site's stack and
        neighbourhood**, and so is the fix's SHAPE — an EOL/`:` peek works at
        `PRINT USING` and is WRONG at both `MID$()=` and `DRAW`, where a stray
        operator must read 24. Ask *"can a FACTOR start here"*, which is `ev_f`'s
        question, by delegating to `els_tc_common`.
        📏 **D-PUSING is still the one to read before pricing anything else**:
        the filed item named TWO rows and the verb had **THIRTEEN**, and the
        rows that found that were the ones added to keep the fix NARROW. 🟢 **THE `ev_f_err` SEVEN-SITES MEMBER IS SHIPPED**
        (D-EVFERR 2026-08-26, [`docs/spec-basic-evferr.md`](docs/spec-basic-evferr.md)):
        five live sites split by MEANING onto `ev_f_empty` (2) and `ev_f_ifc`
        (5) at **ZERO bytes**, 11 DIFF → 1, and `ev_f_err` now has **no
        incoming jumps at all**. 🔴 Its lesson is the seam's own: **four of the
        five rows filed as AGREEING agreed through a DIFFERENT LAYER** —
        `es_noentry`, `fch_check`, `gfx_syntax` — which is the same shape as
        this seam's thesis read backwards, and it is why a per-site oracle is
        not optional here either.
      🎯 **The failure is not just wasted bytes — the bespoke check is usually
      subtly WRONG**: SWAP had wrong CODE (5 not 2) AND wrong ORDERING (raised
      before its exchange; the ref swaps then raises). The SAME ordering bug is
      FILED for two more verbs — **PAINT's 4th argument** (D-PAINT4, CLOSED
      2026-08-24, fill-then-raise) and **CIRCLE's trailing comma** ("draw before
      raising", still open, the cross-ABI tenant case) — so this class has three
      measured instances, **two fixed (SWAP, PAINT)**.
      ⚠️ **THE CARVE IS REAL BUT NOT UNIFORM, and the split is the whole job.**
      SWAP was a clean 23 B DELETE because its side effect (the exchange) is
      INLINE and guards the cursor, so falling to `jp exec_stmt` with the cursor
      on the leftover token Just Works. PAINT/SPRITE/CIRCLE issue their side
      effect through a sub-ROM TENANT (`ep_draw`/`GFX_OP`), so whether deleting
      the check is free (draw, `jp exec_stmt`, boundary rejects — matching the
      ref's draw-then-fail) or a restructure depends on whether the parse cursor
      SURVIVES the tenant round-trip. PAINT's DID — `ep_draw` already `push hl`s
      across the tenant and `pop hl`s before `jp exec_stmt`, so it was a clean
      delete like SWAP; CIRCLE's may not (parse in the tenant, result tested
      before the draw op — likely a second flag, not a delete). That is a
      per-verb MEASUREMENT (build +
      3-machine differential + a value read for the side effect), one verb at a
      time — never a mechanical sweep. Reuse `scratchpad/swap3_probe.py`'s shape.
      🎯 **BUT MEASURING PER-VERB DOES NOT MEAN THE VERBS ARE DIFFERENT — HEAVY
      SHARING IS THE EXPECTED RESULT.** The per-verb differential CONFIRMS a verb
      belongs to the shared rule; it does not presume uniqueness. Direct
      precedent: D-MISSOP measured the missing-operand case verb-by-verb and found
      **one rule at 16 slots** (docs/spec-basic-missop.md). So the likely finding
      is that most of these bespoke ERR-2 raisers ARE the one `es_noentry` rule
      wearing per-verb labels — which is why the consolidation is a real carve,
      not a marginal one. The per-verb measurement is the ADMISSION test; the
      shared handler is the payoff.
      📏 **ONE-PASS CLASSIFICATION 2026-08-24** (`scratchpad/seam_classify.py`,
      SPRITE/CIRCLE/PLAY in a single differential, each with an effect column):
      * **SPRITE `PUT SPRITE …,` (`:1250`, 5th arg) → DELETABLE — ✅ SHIPPED
        (D-SPRITE5, −8 B).** Refs PLACE then raise (`2 30`, sprite-0 Y attr), zb
        raised before placing (`2 209`); `pspr_go` guards the cursor like `ep_draw`
        (and has no overflow check, so even cleaner). 8 rows, 3 DIFF → 0, knives
        2/2 EXACT. [`docs/spec-basic-sprite5.md`](docs/spec-basic-sprite5.md).
        The `:1203`/`:1210` incomplete-arg sites KEEP their gfx_syntax (raise
        before place, agree — sp.incomp/sp.barep).
      * **CIRCLE trailing comma → classified RESTRUCTURE, but SHIPPED AS A CLEAN
        DELETE** (D-CIRCTC, −5 B). Refs DRAW then raise (`2 15`/`2 5`), zb raised
        before (`2 4`) — the filed `x.extra2`. The classifier's *"second flag, not
        a delete"* was REASONED, not measured, and wrong: `cp_done` already
        `jp exec_stmt`s after the draw, so deleting `cpt_asp_done`'s `cp ',' /
        jp z,cpt_err2` delegates the leftover comma to the statement boundary —
        draw-then-raise, like the other three. 🎯 The one wrong verdict in the
        one-pass classification, and it was wrong by reasoning where the others
        were right by measuring.
      * **PLAY 4th voice (`:73`) → KEEP.** Refs raise BEFORE any voice plays
        (`2 0`, `PLAY(0)`=0-not-playing) — the bespoke check's ordering is CORRECT.
        🎯 This is the concrete verb a blind batch delete would have REGRESSED
        (it would have made zb play 3 voices then error, where the reference plays
        none). The measurement is exactly what caught it.
      ✅ **RETIRED 2026-08-28 — BOTH HALVES ARE CLOSED.** Trailing-token: all four
      members shipped (SWAP −23 B, PAINT, SPRITE −8 B, CIRCLE −5 B).
      Missing-operand: five of six shipped (`ev_f_err` 0 B, PLAY +2 B, PRINT USING
      −6 B, `MID$()=` +6 B, DRAW 0 B); only `KEY`'s absent form remains, blocked on
      ~160 B of defaults DATA rather than on knowledge, and it lives on its own
      🔭 item rather than here.
      🎯 **WHAT THE SEAM TAUGHT, and why the doc stays: ONE RULE, SIX VERBS, SIX
      DIFFERENT PRICES.** The rule is shared; the price and the FIX'S SHAPE are
      properties of each site's stack and neighbourhood. An EOL/`:` peek is right
      at PRINT USING and WRONG at both `MID$()=` and DRAW. A blind batch delete
      would have REGRESSED PLAY — the per-verb measurement is exactly what caught
      it. Retired because nothing is left to DECIDE, not because the class stopped
      mattering: on Joost's 2026-08-28 steer toward aggregation/size work, the live
      remainder of this class is the ranked CLONE GROUPS, not this item.

- [x] 🔴 **zerobas does NOT implement the `PLAY(n)` FUNCTION (background-queue
      status).** Found 2026-08-24 by the seam classifier
      (`scratchpad/seam_classify.py`). `P=PLAY(0)` returns **-1** (voice 0
      playing) / **0** (idle) on both the VG-8020 and the CF-3300; on zerobas
      every `PLAY(0)` read raised **`Missing operand`** — the function form is
      unparsed. Separate from the `PLAY` STATEMENT surface. Unpriced; needs its
      own probe (is `PLAY(n)` in the kwsweep denominator? it is a one-token
      function like `USR`). A real MSX1 BASIC function gap, not apparatus.
      ✅ **MEASURED IN FULL, IMPLEMENTED, AND PRICED (2026-08-28, D-PLAYFN),**
      [`docs/spec-basic-playfn.md`](docs/spec-basic-playfn.md). Claim re-ran true.
      🎯 **THE ITEM'S OWN DESCRIPTION OF THE SEMANTICS WAS INCOMPLETE**, and TWO
      RULES fit every row of the first round: `n=0` = "ANY voice" vs a 0-BASED
      numbering. A single `PLAY"…"` plays voice 1, so both predict
      `PLAY(0)=PLAY(1)=-1`. Playing ONLY voice 2, then ONLY voice 3, separates
      them: `-1 0 -1 0` and `-1 0 0 -1`. **Rule A; B refuted.** `PLAY(4)`/
      `PLAY(-1)` = ERR 5, both refs agreeing throughout.
      🔴 **THE ARGUMENT TRUNCATES, AND ONE ROW COULD NOT SAY SO** — `PLAY(0.9)`
      fits truncate AND round. `PLAY(2.7)`→0 and `PLAY(3.7)`→-1 settle it (rounding
      would make the second **ERR 5** — an answer vs an error).
      🎯 **IT IS A FUNCTION, NOT A FEATURE: the state already exists.** `playsvc.asm`'s
      H.TIMI servicer clears each voice's `MUSICF` bit at OP_END, so bits 0/1/2 ARE
      the answer. ⚠️ `play.asm`'s header still claims *"NO live drain (the
      interrupt servicer is Slice 3)"* — **stale**, `basic/playsvc.asm` ships; read
      as current it prices this feature out of existence.
      📏 **PRICE MEASURED BY BUILDING IT: 49 B of main page 1 (89 → 40 free)**;
      low/sub walls unchanged. Includes **+1 B nothing predicted** — the 5 B
      dispatch arm pushed `jr z,ev_f_erlfn` out of relative range and it had to
      become a `jp`. Patch banked and VERIFIED: with it applied all **18 rows ×
      3 machines** agree. `git apply scratchpad/playfn_impl.patch`.
      ✅ **LANDED 2026-08-28 — Joost spent the bytes.** Main page 1 was **110 B →
      61 B free on 2026-08-28**, the 49 B priced. Now GATED: 7 differential rows in
      `make play-acceptance` (`fn_dom_hi`/`fn_dom_neg` in `ERR_CASES`, and a new
      `FN_CASES` value table), all PASS against the VG-8020.
      🔴 **AND THE GATE FIXTURE CAUGHT SOMETHING THE SCOUT'S HAD HIDDEN.** Read
      IMMEDIATELY after the PLAY statement, the reference answers `-1 -1 -1 0` for a
      ONE-voice `PLAY"L1CDEFGAB"` — voice 2 active with no music given to it — and
      settles to `-1 -1 0 0` after any delay at all (a `CLS` suffices). zerobas
      answers the settled value straight away. The scout fixture did a `CLS` before
      printing, so it only ever saw the settled state. Rows now carry an explicit
      `SETTLE` loop and measure the settled answer, which is the property worth
      gating; **the transient is a real divergence and is filed separately below**.
      ⚠️ Earlier this item said *"is at least a tie"* and `wall-assertion-check`
      flagged the byte figure beside it as PRESENT-TENSE — its pattern includes
      `\bis at\b`, which ordinary English hits. A false positive costs one
      rephrase, the trade its own header argues for — recorded, not filed.

- [ ] ⚠️ **`PLAY(n)` READ IMMEDIATELY AFTER `PLAY` SEES A REFERENCE TRANSIENT THAT
      zerobas DOES NOT REPRODUCE.** Filed 2026-08-28 by D-PLAYFN,
      [`docs/spec-basic-playfn.md`](docs/spec-basic-playfn.md).
      `10 PLAY"L1CDEFGAB" : 20 PRINT PLAY(0);PLAY(1);PLAY(2);PLAY(3)` with NO delay
      between the two lines gives **vg8020 `-1 -1 -1 0`** — voice 2 reading active
      although only one MML string was supplied — against zerobas's `-1 -1 0 0`.
      Insert ANY delay (a `CLS`, `FOR I=1 TO 200:NEXT`) and both sides agree
      exactly, on that row and on the voice-2 and voice-3 rows.
      🎯 So the reference marks something active during PLAY's own start-up window
      and zerobas settles instantly. **Unmeasured: what exactly, and for how long.**
      Reproducer varies ONLY the delay and prints both columns:
      [`scratchpad/playfn_fixture_probe.py`](scratchpad/playfn_fixture_probe.py).
      ⚠️ Whether it is worth reproducing is a real question — a BASIC program cannot
      easily observe a window a `CLS` closes — but it is a measured difference and
      the gate rows are written AROUND it (`SETTLE`), which is the kind of
      accommodation that should be visible rather than silent.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended
      (both machines answer; the open question is the window's mechanism and width).

- [ ] ⚠️ **The bare-`jp raise_error` carve family is worth ~2 B, and the reason
      is worth more than the bytes.** Filed 2026-08-22 by D-DUPSPAN,
      [`docs/spec-basic-dupspan.md`](docs/spec-basic-dupspan.md) §2.1.
      `scratchpad/dupspan_sweep.py` ranks it fourth (six copies, 15 B nominal),
      but **five of the six are entered by FALLTHROUGH from a different
      `ld a,N`** — `ee_raise` (A=5), `sid_raise`/`exf_raise`/`gp_raise` (61),
      `tm_raise` (24) — so each needs a 3 B `jp` to replace 3 B removed. Only
      `pl_parse_err` is free and its one caller is a `jr` that must widen.
      **DECLINED at 2 B.** 🔴 **A span is byte-identical without being ENTERED
      the same way**; the sweep cannot see this and says so.
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).

- [ ] ⚠️ **A linear predecessor walk stops at `ENDIF` and calls it an
      instruction.** Filed 2026-08-22 by D-DUPSPAN,
      [`docs/spec-basic-dupspan.md`](docs/spec-basic-dupspan.md) §2.1.
      D-DUPSPAN's fallthrough survey reported `gfx_syntax` as a fallthrough
      target because the line above it is `ENDIF`, which
      `check_tenant_closure._is_terminator` correctly says is not a terminator —
      **but a conditional-assembly directive is not an instruction, and a walk
      that stops at one has stopped in the wrong place.** Both arms of its
      `IF G6_RESIDENT` end in `jp exec_stmt`, so the real answer is "not a
      fallthrough target", and the +22 B measurement is what settled it.
      `_is_terminator` itself is fine; what needs the fix is any CALLER that
      walks backwards over source lines. 🔴 **This one over-reported and cost
      nothing. The same walk under-reports whenever the ENDIF's arms do NOT both
      terminate**, and that direction is silent.
      📏 **MEASURED 2026-08-28 (D-ENDIFWALK),**
      [`docs/spec-endifwalk.md`](docs/spec-endifwalk.md). **The class is 68 span
      pairs, and `ENDIF` is under half of it**: `endif` 32, **`if` 22**,
      **`include` 13**, `else` 1, over 1476 main + 1485 sub pairs. The other 36
      are the same defect unnamed — and `include` is the one that mattered.
      🔴 **IN `check_dead_code` IT FAILS THE OTHER WAY ROUND FROM THIS ITEM'S
      READING.** A phantom fallthrough edge makes the next label REACHABLE, so it
      HIDES dead code — a gate going quiet, and that same sweep is a HARD gate
      inside `make basic-reloc`. Corrected verdicts: **30 phantom edges, 18 agree,
      20 undecidable** (their opening `IF` is in a PREVIOUS span, so a per-span
      walk cannot see the arms; those keep their edge — a guessed True deletes a
      real edge, a guessed False only keeps a phantom one).
      ✅ **AND IT WAS HIDING AN 11 B DEAD ROUTINE, NOW REMOVED.**
      `skip_to_eol`/`ste_done` (`basic/interp.asm`) survived the G4 line-editor
      eviction as a SECOND COPY: `sub/lineedit.asm:738` defines its own and holds
      all EIGHT callers, while main's whole 50-file closure contained exactly one
      mention — `jr skip_to_eol` INSIDE THE ROUTINE'S OWN BODY. ⚠️ NOT the
      `IF SUB_BUILD` shape (fix 4, `disk_putword`, where deletion broke the build):
      that is ONE definition in a shared `.inc`; this was TWO definitions and the
      sub build does not include `basic/interp.asm` at all. Main page 1 was
      **94 B → 105 B free on 2026-08-28**; battery 43/43, `deadcode` clean.
      🎯 It hid because `tok_skip_to`'s span ends on
      `include "basic/tokskip-body.inc"`, whose real last instruction is the
      unconditional `jr tsk_data`.
      ✅ **BOTH REMAINING SPANS ADJUDICATED AND THE `include` HALF OF THE WALK
      FIXED (2026-08-28).** `fat_delete` was the SAME SHAPE AGAIN: `basic/fat.asm`
      is main-only, the body `.inc` and BOTH callers are sub-only, and main's copy
      was the thirteenth uniform resident shim with **no caller** — the twelve
      above it are called by name from `files.asm`, but KILL does not use the
      primitive layer at all (`ld a,DISKOP_SEL_KILL / call subrom_call`, its own
      comment saying the tenant calls `fat_delete` sub-locally). ⚠️ Checked, not
      assumed, that no resident-ABI list or dispatch table reaches it by ADDRESS.
      **+5 B.** `__MEAS_SUB_P1_END` is `ds`-padding read from the SYM file by
      `check_sub_walls.py` — true and useless as a finding; fix (9) skips a span
      whose only code line is a `ds`, PROVES it narrow (a `db` table stays
      reportable), and PRINTS what it skipped.
      📏 **TOTAL 16 B of main page 1 from code no gate could see: 94 B → 110 B free
      on 2026-08-28.** `--blind` still exits non-zero (the allowlist canary fires,
      so the sweep has not gone quiet); battery 43/43, 5 flakes recovered serially
      on a contended host.
      ➡️ **STILL OPEN: the `IF`/`ELSE`/`ENDIF` half — 55 of the 68 pairs.** Deciding
      one needs EVERY ARM to terminate, and **20 conditionals OPEN IN A PREVIOUS
      SPAN**, where a per-span walk cannot see the arms at all; that needs
      file-level structure. Those keep their edges, which is the safe direction (a
      guessed "terminates" invents a finding; a guessed "does not" only hides one),
      and the 20 are enumerable by name from the verdict scout.
      Scouts: [`scratchpad/endif_walk_sweep.py`](scratchpad/endif_walk_sweep.py),
      [`scratchpad/endif_walk_verdict.py`](scratchpad/endif_walk_verdict.py),
      [`scratchpad/endif_walk_impact.py`](scratchpad/endif_walk_impact.py).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended
      (include half SHIPPED 2026-08-28 with 16 B recovered; what remains is the
      IF/ELSE/ENDIF half, which needs a file-level walk, not a per-span one).

- [x] 🔴 **`castail-acceptance` VOIDS THE WHOLE BATTERY WHEN A CONTROL FAILS ON
      THE **ZEROBAS** SIDE, SO IT CANNOT SCORE ITS OWN KNIVES.** Filed
      2026-08-21 by D-FNRUN, found by running K-FR3 against it.
      K-FR3 (`dr_cas_close`'s `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)`) cut exactly
      what it aimed at — `cas-run-hit` went `ZQ9` → `<load-failed>` and
      `cas-run-hit-res` with it. But `cas-run-hit` is a POSITIVE CONTROL, so the
      probe printed **`33 printed, 0 scored — NOT MEASURED (a positive control
      failed)`** and exited 2. A knife is *supposed* to break things; a battery
      that treats any control failure as a broken instrument cannot measure one.
      🎯 **`basic_probe_namspc.py` ALREADY HAS THE RIGHT RULE AND IS THE
      PRECEDENT**: *"ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control
      that fails on `zb` is a finding and is scored below like any other row."*
      That is [[classify-a-control-failure-by-which-side-failed-it]], applied in
      one probe and not the other.
      ⚠️ **THE READING SURVIVED ONLY BECAUSE THE RUNNER READS ROWS, NOT `rc`.**
      Scoring on the exit code would have recorded rc 2 (instrument fault) as
      "the knife did nothing" — 8 of 11 knives were mis-scored exactly that way
      once already [[injjudge-slice]].
      💰 0 ROM bytes; a probe change. Shape: split the control check by side, as
      namspc does — a reference miss is exit 2, a zerobas miss is an ordinary
      scored divergence. ⚠️ Re-run the battery after: some rows may then SCORE
      that were previously only printed, and a row that starts being scored is a
      claim about it.
      ✅ **FIXED AND PROVEN WITH THE FOUNDING KNIFE 2026-08-28 (D-CASTAILCTL),**
      [`docs/spec-castail-control.md`](docs/spec-castail-control.md). 0 ROM bytes.
      `control_faults()` skips `zb`, exactly namspc's rule.
      **Falsified twice.** `--selftest` plants readings and checks WHICH SIDE
      decides (zb-only miss → 0 faults; reference miss → 1; both → 1, only the
      reference listed) with no machine booted. Then K-FR3 itself — **not tracked
      anywhere, so re-created** as
      [`scratchpad/castail_knife.py`](scratchpad/castail_knife.py) — with the cut
      in: `32 printed, 31 scored — 29 agree, 2 diverge`, exit **1**, naming
      `cas-run-hit` and `cas-run-hit-res`. Was `33 printed, 0 scored — NOT
      MEASURED`. Clean tree 31/31, unchanged, so no row starts being scored today.
      🔴 **THE KNIFE TAUGHT TWO THINGS.** The instruction alone was NOT the site:
      `ld hl,(FN_RESUME) ; D-FNRUN: …` occurs TWICE in `basic/cload.asm` (the disk
      path at :231, whose comment continues `--`), so the bare line matched both as
      a PREFIX and the uniqueness guard refused to cut — anchored on the LABEL
      instead. And ⚠️ **`make`'s exit code is not the probe's**: `make` exits 2 on
      any failed target, and the first reading nearly recorded "still voided" when
      the probe had in fact exited 1.

- [ ] 💰 **`RUN <lineno>` IN DIRECT MODE IS STILL THE OLD BEHAVIOUR — R2, ONE
      RULE AT A SECOND SITE (filed 2026-08-22 by D-RUNLINE §4).** `RUN 20` typed
      at the PROMPT never reaches `do_run`: `dispatch_line` runs `is_cmd` against
      the **raw `LINEBUF`, before `tokenise`**, so direct mode never sees `$0E`
      and `dl_run` still ignores the number. 🔴 **GUARDING ONE INSTANCE OF A
      CLASS IS NOT GUARDING THE CLASS** — D-LOADERR-FIX's lesson, and it broke
      the cassette last time; this is filed rather than skipped for that reason.
      🎯 **ONE RULE, TWO MECHANISMS** (the D-FNARG2 shape): the direct-mode parse
      is `parse_lineno`, itself a **sub-ROM tenant** (`SUBROM_IDX_PARSELN`), not
      GOTO's token grammar.
      💰 **~15–17 B against 8 B free (2026-08-22) — needs a carve.** ⚠️ The
      instrument is NOT the obstacle: `basic_probe_lnblank.py` already has a
      `dir-*` battery that types lines straight at the REPL, so the row is a port
      of an existing fixture kind. `namspc`'s own DENOMINATOR already names
      direct mode as NOT COVERED.
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).

- [ ] ⚠️ **BARE `RUN` INSIDE A RUNNING PROGRAM STILL RE-ENTERS THE LOOP NESTED —
      R3, 0 B, AND THE ROW IS THE HARD PART (filed 2026-08-22 by D-RUNLINE §4).**
      `dr_stored`'s `jp run_prog` is the ONE arm D-RUNTAIL did not convert;
      `jp run_prog_top` is the whole fix and costs nothing.
      🔴 **IT WAS SHIPPED AND THEN BACKED OUT.** Writing its row is what showed
      why D-FNRUN said *"a form no row drives"*: **a bare RUN CLEARS VARIABLES,
      so a program that reaches one restarts FOREVER — on the references too.**
      There is no value to read. The row has to separate *"hangs silently"*
      (correct) from *"prints a bogus error then stops"* (the defect) on a
      **TIMEOUT**, plus a control proving the fixture would have printed at all —
      otherwise it is the `<NO OUTPUT>`-means-two-things trap `n.runlinectl`
      exists to prevent.
      🎯 **A deferral honoured is worth more than one filed**: shipping a 0-byte
      behaviour change beside a measured one puts an unrowed claim inside a rowed
      slice. Backing it out cost 0 B, confirmed by rebuild.
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).

- [x] 💰 **A DATA-ONLY SPAN STILL CONFERS FALLTHROUGH ON WHATEVER FOLLOWS IT**
      (filed 2026-08-22 by D-PROLOGUE, §12.5). `err_io: db "load",…` falls into
      `do_cload` in this model, and nothing ever runs off the end of a string
      table. **Measured**, cutting fallthrough only out of spans that EMIT DATA
      (never out of empty ones — that is §12.1's 1227-span error): main 43 edges
      → **1 finding, `ex_sep`, 4 B**; sub 77 edges → **4 findings, 97 B**.
      🔴 **NOT SHIPPED, AND THE SUB COLUMN IS WHY: `sub_p1_table` (72 B) IS THE
      PAGE-1 ENTRY TABLE** — unmistakably live, reached by the main ROM through
      **address arithmetic** (`SUBROM_ENTRY_BASE_P1 + 3*index`), which no
      name-following model can see. So this change does not merely find dead
      code, it surfaces a whole CLASS of labels reached by arithmetic rather than
      by name (`em_ill_direct` looks like the same shape, indexed off a message
      table). Each needs a seed or an allowlist entry with a reason before the
      gate could be believed. That triage is the slice, not the edge rule.
      ✅ **TRIAGED AND SHIPPED 2026-08-28 (D-DATASPAN),**
      [`docs/spec-dataspan.md`](docs/spec-dataspan.md) — and the numbers above moved
      in BOTH directions.
      🔴 **THE TRACKED SCRIPT REPRODUCED §12.1'S CATASTROPHE, NOT THIS
      MEASUREMENT** — `main 1195 findings / 28820 B in a 22510 B ROM`. One line:
      `return seen or True`, which is `True`, so an EMPTY span counts as data-only
      — the exact thing this item says was excluded. The script implements §12.1's
      DEMONSTRATION (its own commit is titled *"the obvious fix reports 27 KB in a
      22 KB ROM"*); `--empty-too` now reproduces that deliberately, and with empty
      spans excluded the filed numbers come back exactly.
      🔴 **THEN BOTH `dw`-TABLE FINDINGS TURNED OUT TO BE THE RULE'S OWN ARTIFACT.**
      A fallthrough edge and a REFERENCE edge to the same label are ONE entry in
      the edge dict, so discarding one discards both: `stmt_table` contains
      `dw ex_sep` AND is followed by `ex_sep`. Main's only finding was manufactured
      by the rule; `em_table`/`em_ill_direct` is identical. **main 1 → 0,
      sub 4/97 B → 3/82 B.**
      ✅ **ALL THREE SURVIVORS WERE THE ARITHMETIC CLASS.** `sub_p1_table` (72 B)
      and `sub_p0_table` are now SEEDED, not allowlisted — an allowlist entry would
      claim "dead and kept on purpose", which is false. `tkf_ref65535`/`tkf_ref32768`
      were GENUINELY DEAD and are deleted: `flt_to_int16` lives in
      `basic/float-arith.asm`, not in sub's closure, and all three loads are BY NAME
      with no arithmetic over the table. ⚠️ `tkf_ref32767` stays — the file header's
      plural *"the tkf_ref* bound tables … used by tkf_cmp32767"* is true of ONE of
      three, and that is how two dead tables kept their place.
      📏 **Sub page 0 was 2434 B → 2444 B free on 2026-08-28**; main does not move.
      The bytes are not the point — the gate now cuts 26 main / 37 sub fallthrough
      edges that never existed. `--blind` still exits non-zero; both new predicates
      unit-checked (empty is NOT data-only; a named target keeps its edge); battery
      43/43 with 7 flakes recovered serially.

- [ ] ⚠️ **THE `tools/` SEED ARM IS AN INTERSECTION, NOT AN ASSERTION** (filed
      2026-08-22 by D-SEEDHOLE2, §11.5). `init`, the sub entry-table tenants and
      the resident-ABI import each fail loudly if they stop resolving; the
      `tools/` arm is `set(m.nodes) & external_names(['tools'])`, so a main
      routine renamed out from under a `tools/` by-name `.sym` lookup drops out
      of the seed set **silently**. It over-seeds by construction, so the failure
      direction is a MISSED finding rather than a false one — which is why it is
      filed rather than fixed. 🔴 **`docs/spec-deadcode-gate.md` §2.2 claimed
      *"every seed name is asserted to resolve to a real label"* for the whole
      set; that sentence was never true of this arm.** Corrected in place, not
      deleted. The real fix is a per-tool lookup model, not a stricter regex.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **`SAVE` / `LOAD` / `BLOAD` WITH NO ARGUMENT SAY `Syntax error` WHERE
      BOTH THE REFERENCE AND D-MISS-1 SAY `Missing operand`.** Filed 2026-08-21
      by D-FNEXPR2 (rows `n.savebare`, `n.loadbare`, `n.bloadbare`, DEFERRED).
      Measured on the CF-3300 by reading the screen directly, because the
      probe's classifier could not name it and reported `<NO OUTPUT>` for all
      three: **`Missing operand in 10`** — raised, with a line number.
      ✅ **THE DISPOSITION IS ALREADY FIXED and only the WORDING is left**: these
      three printed a non-raising `load error` before D-FNEXPR2 and now RAISE,
      so `ERR` is set and `ON ERROR` traps them. What remains is that zerobas
      has no `Missing operand` message at all.
      🎯 **SO THIS IS NOT A DISK ITEM — IT IS D-MISS-1's OWN OPEN RESIDUAL AT
      THREE MORE VERBS.** [`basic/missing.asm`](basic/missing.asm)
      `els_typecheck` already records it for the LET mirror: *"The reference's
      `Missing operand` for those is a THIRD wording zerobas does not produce
      here"* (`A$=` and `A$=+`). One message, one ERR code, five known sites —
      price it once, at the message, not once per verb.
      💰 Not priced. Shape: a message-table entry (the D-MSGSUB sub-ROM host
      machinery exists) plus whatever `els_tc_common`'s `jp nz,stmt_error` arm
      becomes. ⚠️ The MSX ERR code for it is **not measured**, only the wording.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **`CSAVE` AND `CLOAD` STILL TAKE A LITERAL FILENAME ONLY, AND THAT IS
      NOW A DIVERGENCE OF ITS OWN RATHER THAN PART OF A FAMILY.** Filed
      2026-08-21 by D-FNEXPR2. Every OTHER filename verb — `OPEN`, `KILL`,
      `NAME`, `SAVE`, `BSAVE`, `LOAD`, `BLOAD`, `FILES` — takes a string
      EXPRESSION as of `cffb34d` + this slice; `do_cload`
      ([`basic/cload.asm`](basic/cload.asm)) and `do_csave`
      ([`basic/save.asm`](basic/save.asm)) keep their `cp '"'` gates, and
      `basic/PROVENANCE.md` now says so explicitly instead of describing both
      halves with one sentence.
      🔴 **UNMEASURED, AND THE APPARATUS IS THE PROBLEM, NOT THE PRICE.** These
      are CASSETTE verbs: `CSAVE A$` on the CF-3300 needs a tape, and the
      `namspc` battery has none. `cassave-acceptance` / `castail-acceptance` are
      the batteries that CAN drive tape — the reading belongs there, and it
      should come before any byte. 💰 The edit itself is the same shape as the
      five this slice did and would likely RECOVER bytes (each gate is longer
      than the `call fname_expr` that replaces it); what is not free is knowing
      what the reference does with `CSAVE`'s OPTIONAL argument, which has the
      `FILES`-style "is there an argument at all" question in it.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **THE `do_files` OP-SELECTOR GUARD IS PINNED BY NOTHING.** Filed
      2026-08-21 by D-FNEXPR2 §3.5, against its own fix.
      `do_files` parks its dirverb op selector on the stack across the filespec
      parse (+5 B) because `str_eval` can now run `INPUT$(n,#ch)`, which reaches
      the drive through `fatprim_bounce` and overwrites `DISKOP_OP`. **No row in
      any battery executes `FILES INPUT$(n,#ch)`**, so a knife that unparked the
      selector would redden nothing — and that would be a claim about the ROW
      SET, not about the code [[a-shadowed-guard-has-no-knife]] [[fnfund-slice]].
      The BALANCE of the push/pop is pinned (every FILES row would derail), the
      CLOBBER protection is not.
      💰 0 B of ROM; this is a row. Shape: `10 OPEN"HI.TXT"FOR INPUT AS #1` /
      `20 FILES INPUT$(3,#1)` / `30 PRINT"[OK]"`, against the CF-3300.
      ⚠️ **THE CAPTURE WINDOW IS THE RISK** and it is a measured one in this
      battery: `OPEN`+`CLOSE`+`KILL` did not fit the default `step` (D-FNFUND),
      and this row does an OPEN, a channel read and a directory walk. Build it
      with a shape control, or give it a per-row `step` override rather than
      raising the battery's.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **A MALFORMED FILESPEC PRINTS `load error` AND `FILES` LISTS ANYWAY.**
      Noticed 2026-08-21 while walking D-FNEXPR2's sites; not measured on the
      reference, so it is filed rather than fixed.
      `parse_disk_fcb` rejects a name that does not fit 8.3 with
      `jp bl_load_error` ([`basic/pdfcb-body.inc`](basic/pdfcb-body.inc)), and
      `load_error` **prints and RETURNS** — from inside `parse_disk_fcb`, so the
      `ret` lands back in the CALLER, one level up, and `do_files` carries on to
      the directory walk with a half-built pattern. This is the nested-reject
      hazard [`sub/bload.asm`](sub/bload.asm) already names in prose
      ([[load-error-is-not-abort]]); what is new is that it has a VISIBLE
      symptom at `FILES`, which D-FILESIDE's `listface` readout can now see.
      ⚠️ **PRE-EXISTING AND NOT WIDENED BY D-FNEXPR2** — the same `jp` served the
      literal gate. 💰 Not priced; the reference's answer to
      `FILES"TOOLONGNAME.EXTRA"` is unmeasured, and D-LOADERR-FIX's lesson
      applies directly: `load_error` has ~73 resume-through callers, so guarding
      one instance is not guarding the class.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **Two `fat-error` gaps left by the 8-of-8 closure** — (1) no knife
      separates `bload-alive`, `open-alive` or `append-alive` from the shared
      `fat_io_getbyte` layer, so each is shown to see its READ PATH die but not
      proven verb-specific; (2) `merge-alive`, `append-alive` and `kill-alive`
      lean on a SECOND verb (`SAVE",A"`, OPEN/OUTPUT+INPUT, FILES), so a break
      elsewhere can mark their row NOT MEASURED — loud, but not their own verb.
      Detail:
      [`docs/spec-fat-error-verb-control.md`](docs/spec-fat-error-verb-control.md) §8.6.
      *(Item (3), `run-missing`'s second message, is CLOSED — see D-RUNTAIL
      below.)*
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] 📌 **`file:LINE` CITATIONS ARE UNMAINTAINED AND BROADLY ROTTED — ONLY
      31% OF THEM WERE STILL CORRECT, AND NO GATE READS ONE.** Filed 2026-08-19
      by D-DEFTYPEDOC's follow-up sweep, which found a drifted anchor by READING
      and then found the class by MACHINE.
      ✅ **MEASURED REPO-WIDE 2026-08-19, and 594 REPAIRED** — see the audit
      block below. **Denominator machine-produced, not hand-listed**: 1994
      `file:LINE` citations across 924 tracked text files, into 318 distinct
      targets; **1392 resolve to a tracked file** and are decidable (the rest are
      prose-relative or name no tracked path).

      | verdict, whole tree | n |
      |---|---|
      | STILL CORRECT | **426** |
      | REPAIRABLE (unique content match) — **all 594 fixed** | **594** |
      | CONTENT GONE (cited code deleted since) | **258** |
      | AMBIGUOUS (cited line too generic to locate) | **93** |
      | out of range even when written | **10** |
      | cited a blank line / target absent at birth | **11** |

      🔴 **426 of 1392 is 31%.** The original filing said "broadly rotted" on the
      evidence of a 212-anchor window; that was a rule claiming more than its
      evidence, so the whole tree was measured rather than the phrase softened.
      It turned out to UNDERSTATE the problem.
      Restricted to the five source files `7aadd36`..`840ed59` rewrote
      (`basic/interp.asm`, `basic/kwtable.inc`, `basic/sysvars.inc`,
      `basic/usr.asm`, `sub/deftype.asm`): **212 unique citations, of which 87
      now point at a line whose CONTENT differs from what stood there before
      those two commits.** ⚠️ **THAT 87 IS AN UPPER BOUND ON DAMAGE AND A LOWER
      BOUND ON ROT** — it says the anchors moved, NOT that they were right
      beforehand; several were already stale from earlier commits (the sweep's
      own control: `basic/vars.asm:174` was 4 lines off with `vars.asm` untouched
      by any of the three commits in this window).
      🔴 **AND THE SENTENCE THAT STOOD HERE WAS WRONG.** It said sorting "these
      commits broke it" from "it was already broken" *"needs a semantic notion of
      correct that this measurement does not have"*. It does not: **`git blame`
      supplies it exactly.** Blame the CITING line for the commit that wrote the
      citation, read the target file AT that commit to learn what the author
      actually pointed at, then find where that content lives today. Decidable,
      cheap, and it splits the 87 three ways: **61 correct-when-written and
      mechanically repairable · 18 citing content DELETED since · 8 undecidable**
      (7 citing a line too generic to locate uniquely — `ret`, `ENDIF`, `ret nz`
      — plus 1 already correct, which is `0936943`'s own repaired anchor and so
      doubles as the audit's control).
      ✅ **THE 61 ARE FIXED 2026-08-19** — 89 textual occurrences across 41 files,
      since a markdown link cites the same anchor twice. Verified **61/61**: every
      repaired anchor now lands on exactly the content its citing commit pointed
      at. That is a repair WITHIN the convention, not a change to it; option (b)
      below is still open and still the human's call.
      ✅ **THEN ALL 594 REPO-WIDE** (`scratchpad/anchor_audit_all.py`): 832 textual
      occurrences across 176 files, verified **594/594** by the same invariant.
      ⚠️ **A REPAIR MAY ONLY TOUCH PROSE, AND THAT IS ENFORCED, NOT HOPED.** The
      applier locates each citation inside a COMMENT or STRING span (`tokenize`
      for Python, first `;` for asm) and refuses anywhere else — a first, blunter
      guard rejected 17 legitimate ones sitting in docstrings, so it was replaced
      with the exact one rather than left to reject good repairs. **Zero live-code
      edits**, and the ROMs stayed byte-identical through both passes.
      🔴 **AND A DOC-ONLY SWEEP CAN EDIT A GATE INPUT.** The 594 included one
      anchor inside `tools/injector-record-allow.txt` — a prose description field
      in a file `make injector-check` PARSES. Byte-identical ROMs say nothing
      about that, so the gates that READ the touched files were run afterwards and
      are green: `injector-check` (one live injector across 407 files),
      `audit-citations` (CLEAN, 798 files swept), `latch-check` **16/16**,
      `basic-reloc`, `preflight-check`, `rowshape-check`, `deadcode`, `unit-test`
      **59/59**. ⚠️ `latch-check` first returned rc=2 — an APPARATUS refusal, not a
      regression: `rm -rf build` had removed `build/zerobas-main-eu.rom` and the
      preflight refused to measure rather than report a missing ROM as a missing
      FEATURE. `make repack-machine`, and it passes. **Byte-identity is the wrong
      instrument for a sweep that touches `tools/`, and the gates were run after
      the commit rather than before it — the wrong order.**
      ⚠️ **THE 18 AND THE 8 ARE DELIBERATELY NOT TOUCHED.** The 18 point at code
      that no longer exists (`err_overflow` msgtab rows, `TMISMATCH` reads,
      `fre_illegalfn_lc`), so moving a number cannot fix them — the prose around
      them has to be re-read by whoever knows what replaced that code. The 7
      generic ones have no unique target, and a guess is worse than a stale
      number. Both lists reproduce from
      [`scratchpad/anchor_audit.py`](scratchpad/anchor_audit.py).
      🔴 **A SYMBOL GREP CANNOT FIND ONE.** D-DEFTYPEDOC's `ex_def_type`/
      `ex_defint` grep was exhaustive and still missed
      `docs/spec-basic-deftbl-strcode.md`'s anchor, because a drifted line number
      contains no symbol. Found only by reading the cited line.
      🔴 **AND THE RE-ANCHORING ITSELF DRIFTED, INSIDE ONE COMMIT.** `0936943`
      corrected that anchor `:66` -> `:86` from a grep taken BEFORE its own
      `sub/deftype.asm` header edit, which shifted the target by one; the write is
      at `:87`. **Re-read an anchor AFTER the last edit to the file it points
      into, not before.** Both anchors in that sentence are corrected now.
      **Options, priced, none taken**: (a) do nothing, accept prose-only anchors
      as approximate — free, and honest only if the docs say so; (b) drop line
      numbers from citations that already name the symbol — a large mechanical
      edit, no gate needed afterwards; (c) a gate that verifies an anchor lands
      near a symbol named in the citing text — fuzzy, and the false-positive rate
      is the whole question. ⚠️ Cheapest EXACT sub-gate available today: flag
      anchors that are out of range or land on a blank line (zero false
      positives, low yield — the 87 above are none of those). This is a
      convention decision, not a defect fix, so it is filed rather than taken.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 📌 **`basic_probe_kwsweep.py` PRINTS ROWS NO RUNNER CAN PARSE, AND ITS
      EXIT-2 PATH PRINTS A DIFFERENT TABLE ENTIRELY.** Found 2026-08-07 by
      D-ROWSHAPE's walk ([`docs/spec-probe-rowshape.md`](docs/spec-probe-rowshape.md)
      §2.4) — the hand-list in the residual above did not have it, and the walk
      did. `kwsweep`'s scored rows print `{state:5}  {key:9} {body}` with the
      body **undelimited**: no `repr()`, so a value containing a space cannot be
      recovered from the line by any parser, whatever the layout. It is
      therefore **out of the row-grammar contract by definition, not by
      exemption**, and `make rowshape-check` does not watch it.
      Its `return 2` block prints `    {k:9} {n} chars` — a *probe-defect* table
      (keywords whose direct-mode exec line exceeds one screen row), not its
      readings — so a runner holding a `kwsweep` baseline sees **zero** rows
      under that knife.
      ⚠️ **That abort is CORRECT** (the probe genuinely measured nothing) and the
      landed §Knives rule *"enumerate the probe's exit codes and parse all of
      them"* already covers it, which is why this is filed rather than fixed.
      **Priced:** de-tabulating the defect list is one line; giving the scored
      rows a parseable encoding is a format change to a **162-word** sweep whose
      re-run is the real cost, bought to prevent a fault the runner rule already
      prevents. **No byte count is implied.**
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **`s.fldarymix` IS A GATE ROW NO KNIFE CAN REDDEN, and that is recorded
      rather than fixed** (D-FLDARY, spec §10.6). A scalar field and an
      array-element field coexisting in one `FIELD` is the row that makes §4.2's
      disjoint-key-space argument a measurement — but **no reachable program can
      collide the two spaces** (a scalar `k0` is an upcased letter `$41..$5A`; an
      element `k0` is `>= $80`), so K-FA1 moved `s.fldary2` and left this one
      green. Its falsifier is the assembly-time **assert** (K-FA7, which does
      refuse the build), not a cut. Anyone re-reading the knife table should not
      "fix" the row or the cut — the claim is structural
      ([[rule-gated-structurally-has-no-knife]]).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **3 B carve candidate: `ex_mid_stmt`'s resolve abort is SHADOWED.**
      D-LVFIX's `jp nz,fp_runtime_error` at `ex_mid_stmt` is **not falsifiable**:
      K-LV3 cut it and reddened nothing, because `eval_pos_arg` →
      `get_int16_checked` → `check_fperr_only` re-raises the same `FPERR` on the
      very next instruction, so the message is identical. The same is true of
      `inp_readvar`'s (K-LV4), and the row added to make its wild store
      observable (`f.aryoortrap`) missed too — `ary_op0_resolve` clobbers `BC`,
      so the store lands where no row looks. Kept for uniformity with the five
      other `tgt_parse` callers (at `exr_lp` the equivalent abort **is**
      one-row-knifeable, D-ARYLV K-AL3). 3 B of the low region, which had 7 on
      2026-08-08.
      ⚠️ Removing it makes `ex_mid_stmt` the one caller that trusts a *callee's*
      error check — weigh that against the bytes
      ([[rule-gated-structurally-has-no-knife]]).
      🙋 NEEDS-JOOST — a call that is yours to make (page-1 budget).
- [ ] 📋 **THE PICKUP LIST IS 38/62 APPARATUS, AND THE REAL BASIC SURFACE IS 15
      ITEMS — SWEPT AND RANKED 2026-08-21.**
      [`docs/gapsweep-2026-08-21.md`](docs/gapsweep-2026-08-21.md). Commissioned
      after four consecutive 0-byte apparatus slices, against the charter
      (faithful full MSX1 BASIC). Denominators RE-RUN at `cf0c4b6`, not quoted:
      `kwsweep` **MISSING 1 · DIVERGENT 1 · NO-ORACLE 5 · SUPPORTED 29**
      (37 of 55 executed, 18 crunch-only); `sysvarsweep` apparatus OK.
      🎯 **EXACTLY ONE MSX1 RESERVED WORD IS GENUINELY MISSING: `DEF FN`/`FN`.**
      The lone `DIVERGENT` (`csrlin`) is a documented PROBE ARTIFACT — its row has
      no `CLS`, so it reads ambient scroll, and the REFERENCE disagrees with
      itself (4 vs 9) across differently-scrolled batches.
      ➡️ **RANKED, each re-verified against the tree rather than taken from its
      filing:** ~~(1) filename arguments accept a LITERAL only where the reference
      takes any string EXPRESSION — 8 rows, 7 verbs, ONE mechanism at **11
      `parse_disk_fcb` sites, re-walked and exact**~~; (2) `DEF FN`/`FN`,
      200–400 B, an arc; (3) SCREEN 3, ✅ **SCOUTED AND PRICED 2026-08-22** — it
      needs ~6 B of page 1 and ~170–280 B of sub page 0, so it does NOT need the
      carve this list assumed; was filed as a whole-feature gap, unpriced and never
      scouted; (4) a line store bounded by `TXTMAX` not HIMEM (silent wrong
      answer); (5) a stored `DATA` literal charging the pool 25 B against 0.
      🔴 **RANK 1 SHIPPED THE SAME DAY THIS RANKING WAS WRITTEN, AND THE RANKING
      STOOD FOR A DAY AFTER IT** — corrected 2026-08-21 by D-SEEDPROSE's memory
      pass. All eight verbs (`OPEN`/`KILL`/`NAME`/`SAVE`/`BSAVE`/`LOAD`/`BLOAD`/
      `FILES`/`RUN`) take a string EXPRESSION and a non-string is `Type mismatch`;
      `namspc-acceptance` 62/62 → **99/99**
      ([`docs/spec-basic-fnexpr.md`](docs/spec-basic-fnexpr.md),
      [`spec-basic-fnexpr2.md`](docs/spec-basic-fnexpr2.md),
      [`spec-basic-fnrun.md`](docs/spec-basic-fnrun.md)).
      🎯 **AND THE PRICE FILED WITH IT WAS WRONG IN BOTH HALVES**: the parser
      needed **no second source and no staging buffer** (0 B), and the cost was in
      the quote GATES, not the 11 `parse_disk_fcb` sites. **The mechanism count
      was right and the unit was not** — which is the reason a filed price is
      re-derived, not spent.
      🔴 **THIS ENTRY FELL TO ITS OWN LESSON.** It exists because ranking on filed
      text nearly re-implemented shipped code (D-LINEMAX), and it then carried a
      shipped item at rank 1. **Dating a ranking is not enough: re-verify at
      PICKUP, by whoever picks it up.**
      ⚠️ **THE SURVIVING ITEMS ALL STILL NEED A CARVE FIRST — main page 1 read
      31 B on 2026-08-22** after D-SEEDHOLE2 (`make basic-reloc`; it read 11 B on
      2026-08-21 after D-STRPAREN, and the 12 B in the original ranking was read
      earlier that day). 🔴 **AND THIS PARAGRAPH FELL TO ITS OWN LESSON A SECOND
      TIME**: it pointed at "the 16 B second seeding hole filed by D-SEEDPROSE"
      as the measured page-1 candidate, and that item SHIPPED on 2026-08-22 (20 B,
      not 16). A pointer to a candidate rots the same way a wall does — **it is a
      dated reading, and it must be re-verified at pickup, not quoted.** No
      page-1 carve candidate is currently priced: `DEF FN` / SCREEN 3 / TXTMAX
      still need one, and the two residuals D-SEEDHOLE2 filed are apparatus
      (sub-side and gate-honesty), not main page-1 relief.
      ⚠️ **UPDATE 2026-08-22, SAME DAY: page 1 is back to 8 B.** D-SEEDHOLE2's
      20 B went straight into D-RUNLINE (23 B), which is what a carve is FOR —
      but it means every item above still needs one, and D-RUNLINE's own R2
      (~15–17 B) has joined the queue.
      💰 0 ROM bytes; this is a reading. What it changes is which item is picked
      up next, and it already retired one (D-LINEMAX, above).
      🙋 NEEDS-JOOST — a call that is yours to make (retire / delete).

- [ ] ⚠️ **THE THIRD TRAILING `SCREEN` ARGUMENT'S DOMAIN IS UNMEASURED.**
      Filed 2026-08-10 by D-SCRERR. Slot 1 (sprite size) is pinned to 0..3 and
      slot 2 (key click) to 0..255; `scr_extra` treats slots 3+ identically to
      slot 2, so the open risk is a reference that narrows a later one.
      `SCREEN 1,,,300` — one row, no scouting done.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **`a.spr` IS BLIND TO A CUT THAT STOPS THE SPRITE SIZE BEING APPLIED.**
      Filed 2026-08-10 by D-SCRERR ([`docs/spec-basic-screenerr.md`](docs/spec-basic-screenerr.md)
      §9), found by knife K-SE5, which reddened `a.sprslot1` and left `a.spr`
      untouched. `SCREEN 1,3` reads only the ERROR CODE, and a size that is
      never applied raises nothing. Harmless — `a.sprslot1` reads
      `LEN(SPRITE$(0))` and covers it — and **not** a reason to change `a.spr`,
      which is the row that says an in-domain size is accepted. Recorded because
      the same shape recurs in any row that tests an effect by its absence of an
      error.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **A SCREEN-2 `PAINT` WITH `C != B` FLOODS THE ENTIRE SCREEN ON THE
      REFERENCES WHATEVER IS DRAWN, AND HERE ONLY WHEN A BORDER PIXEL SHARES A
      COLOUR GROUP WITH A REACHABLE PIXEL.** ⚠️ **RETRACTS AND REPLACES** the
      item filed 2026-08-22 by D-PAINTMC §7 as *"a `,B` wall sharing a colour
      group with the fill is eaten"*. Measured 2026-08-22 by the scout,
      [`docs/ntwall-scout-2026-08-22.md`](docs/ntwall-scout-2026-08-22.md),
      `scratchpad/ntwall_probe.py`, five rounds, both references agreeing on
      every row. **The row was right and the mechanism was wrong**, and it
      pointed the next reader at `gfx_color_rmw`, which is not where this lives.

      🎯 **THE WALL'S GEOMETRY DECIDES NOTHING.** `LINE(0,20)-(255,20),7` with
      NO gap: `PAINT(128,8),9,7` then `POINT(50,21)` — BELOW the wall — reads
      **9** on both references and **4** here. Three stacked plain LINEs: the
      references cross **all three rows**. A VERTICAL 1-px wall: **all three
      cross**, because there the 8-pixel group straddles it and this engine's
      eating does reach. It is `spec-basic-graphics-g5.md` §5's own dichotomy,
      measured on a box and holding here for walls: **`C == B` bounded,
      `C != B` floods everything.** `C == B` on the same wall agrees on all
      three sides, which is what stops the claim being unfalsifiable.

      🔴 **AND THE INSTRUMENT IS PART OF THE FINDING.** `POINT` collapses the
      pattern bit and both colour nibbles into one number. `VPEEK` says the two
      engines write DIFFERENT BYTES for the same filled group: the references
      write `pattern := 0, bg := C`, this engine writes `pattern := $FF,
      fg := C`. **Both `POINT`-read as C.** One scout row reads 9 on all three
      sides with `0`/`$09` behind it on the references and `$FF`/`$94` here — a
      row that AGREES through the instrument it was written for and DIVERGES
      underneath it. Every PAINT row in `basic_probe_graphics.py` PHASE H is
      `POINT`-sampled and structurally blind to this.
      🔴 **`,BF` DOES NOT SET THE PATTERN BITS AT ALL** — a fully covered group
      is written as *"background = c"*, bits clear, on all three machines — so a
      `,BF` wall is not a border anywhere and three of this scout's own rows
      agreed for a reason unrelated to the subject.

      💰 **NO PRICE AND NO DESIGN YET, deliberately.** Matching the reference
      means changing what a filled span WRITES, which is `gfx_plot_cur`'s
      contract, shared with PSET/LINE/CIRCLE/DRAW — all of which measurably
      agree today and must keep agreeing (`vp.pset.pre` / `vp.solid.pre` are
      identical on all three sides). Its own slice, with its own knives.
      ⚠️ **AND THE FIRST THING THAT SLICE MUST MEASURE IS NOT IN HAND**: §4 says
      what the reference WRITES, not how its walk reaches a border row it can
      still see. No row yet separates the candidate rules.
      🟢 Two rows SHIP GREEN as pins against a fix that overshoots
      (`plain_wall_cb_bounded`, `bf_wall_not_a_border`, PHASE H).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **A KNIFE RUNNER STILL HAS NO SHARED WAY TO SCOPE A CUT TO ONE
      ROUTINE.** Filed 2026-08-11 by D-PAINTSEED
      ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md) §9.6). K-PS1's
      first runner did `src.replace("call gfx_point_gate  ; BC/DE/HL preserved",
      …, 1)` — a line that occurs THREE times in `basic/graphics.asm` — and cut
      `gfx_plot_stmt`'s copy, i.e. the probe's own `PSET(7,4)` seed. It was
      caught only because the runner read the report TAG. `docs/dev-workflow.md`
      §Knives has eight rules about how a runner reads a report and none about
      how it makes a cut. The mechanical remedy is one helper — scope to the
      routine's region, assert the occurrence count is 1 — but knife runners are
      deliberately throwaway (`spec-probe-injjudge.md` §1.3), so where it should
      live is the open question, not what it should do.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **NOTHING IN 360 ROWS PINS THE TENANT'S `GRPACX` STORE.** Filed
      2026-08-17 by D-GATEBLIND round 5 (§21.2). `K-GR4` diverts
      `gfx_line_op`'s `ld (GRPACX),hl` and **not one row of 360 moves** — the
      resident's write covers the drawn path and the tenant never runs on the
      error path. 💰 It may still be load-bearing for **CIRCLE's spokes**, which
      call `gfx_line_op` internally (`gco_done` writes the circle's own work-area
      values AFTER the spokes, so the ordering matters); before removing ~3 B of
      sub p0, READ that path rather than trusting the gate's silence — the gate
      having no row for it is exactly what this residual says. ⚠️ The claim is
      narrow: only the `GRPACX` store was diverted, not `GXPOS`/`GYPOS`/`GRPACY`.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **NINE ACCEPTANCE ROWS STILL NEED A REFUSAL CUT, ONE PER PATH.** Filed
      2026-08-17 by D-GATEBLIND round 5 (§20). `M-PSETOFF` and `M-DRWSCALE` proved
      the shape works — an off-screen `PSET` made to raise reddens
      `pset_offscr_ok`, and a narrowed `S` bound reddens `scale255ok`/`scale0` —
      but each remaining acceptance row sits on its own path: `off_ok` (LINE),
      `clip_neg_ok` / `clip_offscr_ok` (CIRCLE), `border16_flood_ok` (PAINT),
      `bare_b` / `empty` / `offscreen` (DRAW), `arc_ovf_r260` /
      `arc_ovf_wrap300` (the arc mask). 💰 Six or seven cuts, one each; there is no
      shared site the way `gdrw_err5` was for phase L.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **PHASE Q3's CONTROL SHARES ITS SUBJECT'S STATEMENT, SO THE PAIR CANNOT
      TELL THE TWO FAILURES APART.** Filed 2026-08-17 by D-GATEBLIND round 2
      (§9). Q3 freezes TIME with `VDP(1)=VDP(1)AND223` and proves the emulator is
      alive with a control case — but the control's restore line is
      `VDP(1)=VDP(1)OR32`, **the very statement under test**. `M-G8PAREN`
      reddened `C-BIOS/control` along with `C-BIOS/ie_off`, which I had predicted
      would hold. A control is only honest about the cell it reads
      ([[girdom-slice]]) — and this one reads the subject. 💰 Give the control a
      restore that does not go through `VDP(n)=` (a `POKE` of the mirror plus a
      mode set), or state in the probe that Q3 is a pair, not a control.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **`M-SPRPBASE` AND `M-SPRSZAPL` EACH HAVE ONE ROW THAT *SHOULD* SEE THEM
      AND DOES NOT.** Filed 2026-08-17 by D-GATEBLIND round 2 (§9). `pat_8_empty`
      (`SPRITE$(0)=""`) writes eight zeros, so an 8-byte base shift leaves the
      read cell at 0 — the row cannot distinguish the right entry from the wrong
      one **for the empty string only**; and `put_pat63_16` compares the error
      outcome, which is "accepted" under both the 8×8 and 16×16 pattern rules.
      Neither is wrong as written, but neither is coverage of what its name
      suggests. 💰 Give `pat_8_empty` a non-zero neighbouring entry first.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [x] ⚠️ **ZEROBAS DRAWS ARCS 5–6× SLOWER THAN THE REFERENCE, AND FULL CIRCLES
      1.5× FASTER.** Filed 2026-08-17 by D-ARCMASK (§6), measured in VDP frames
      via `TIME` with the empty `FOR` loop measured per machine and subtracted
      (`scratchpad/arcmask_time.py`, `arcmask_time2.py`):

          r=95  full  ref 445/448 ms  zb 289/292 ms   0.65x
          r=95  ARC   ref     224 ms  zb    1272 ms   5.68x
          r=200 ARC   ref     436 ms  zb    2600 ms   5.96x

      An arc is CHEAPER than its full circle on the reference (224 vs 448 ms)
      and **4.4× DEARER** on zerobas (1272 vs 292). `gfx_circ_keep` runs two
      `gfx_cross_ge0` per emitted point and D-CIRCOVF widened each to two
      16×16→32 multiplies + a 32-bit compare — eight times per octant step,
      plotted or not. ⚠️ The widening is FORCED (without it the products wrap,
      `docs/circovf-msx1-oracle.md` §5.2); the question is whether the 32-bit
      path can be gated on a cheap 16-bit precondition rather than always taken.
      💰 Not priced. ⚠️ **NO GATE MEASURES TIME AT ALL** — this is invisible to
      `graphics-acceptance`, which only compares planes.
      🔴 Round 1 of this measurement reported three `None`s at N=20; they were
      the CAPTURE WINDOW, not the machine. Re-run at N=5/step 45 s, with the
      `r95` row reproducing round 1 to within one frame as the cross-check.
      ✅ **CLOSED 2026-08-17 by the wedge rewrite, re-measured**
      (`arcmask_time2.py` on `sub.rom e4fbf667`): r=95 arc **1272 → 204 ms**
      (0.91× the reference), r=200 arc **2600 → 368 ms** (0.84×), arc+aspect
      **1384 → 236 ms** — arcs now beat the reference like every other CIRCLE
      form. The full-circle control rows are unchanged (292/340 ms), which is
      what says the win is the mask and not the rig. ⚠️ Still true: **no gate
      measures time** — this closure is a hand-run probe, not a standing gate.

- [ ] ⚠️ **`fp_exp`/`fp_log`'s `$8000` REACHABILITY WAS REASONED, NOT
      MEASURED.** Filed 2026-08-11 by D-NEG8K (same doc, §4.4). Both take a
      magnitude by negation (`DE := |n8|` / `DE := |e'|`) and both are
      **correct at `$8000` either way**, because the following
      `widen_uint_to` reads the magnitude as UNSIGNED and the sign is poked
      separately — so `$8000` widens to 32768 and comes back as −32768, the
      original value. That verdict is sound from the source. What was NOT
      done is establishing whether `n8` or `e'` can BE `$8000` for any
      `EXP(x)`/`LOG(x)`. Low value precisely because both branches are
      correct — but it is an unmeasured reachability claim sitting in a table
      of measured ones, and D-NEG8K's own lesson is that a claim reached by
      reasoning about a site reads exactly like one reached by measuring it.
      ⚠️ `math-acceptance` owns this surface.
      💰 Zero bytes either way; the cost is one reading.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **THE THREE SCALE STATES ARE NOT SWEPT THROUGH `X` SUBSTRINGS OR
      `=var;` SUBSTITUTION.** Filed 2026-08-11 by D-DSCALE. §12 measured the
      never-set / `S4` / `Sn` distinction at literal counts only. `DRAW"XA$;"`
      and `DRAW"BU=V;"` reach `gdrw_scale` by different argument paths, and
      `d.sub2` already showed the substitution path has a NARROWER domain than
      the literal one (int16 vs 65535 — measured, on the references too). So
      `V=40000:DRAW"BU=V;"` cannot even express the count that exposes the
      default state, and whether a large count reachable through substitution
      (`V=-25536`, the int16 face of 40000) scales the same way is **unasked**.
      One row each would settle it; both are cheap and neither is expected to
      diverge, which is exactly why nobody has run them.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **`GFX_OP=1`'s MARSHALLING IS STILL ALIASED TO THE WORK AREA, AND THAT
      IS A DECISION NOTHING RE-EXAMINES.** Filed 2026-08-11 by D-GIRDOM.
      `PSET`/`PRESET` hand the tenant their target through `GXPOS/GYPOS` and it
      is currently correct — those verbs write those cells as their contract, so
      the aliasing is invisible. But it is invisible by COINCIDENCE of the two
      values being equal, not by construction: nothing asserts that the
      marshalled value and the contracted value can never diverge, and the same
      coincidence at `GFX_OP=2` is what D-GIRDOM just paid for. Cheap to settle
      (`GFX_PTX/GFX_PTY` exist now and the write is the same size), but it is a
      change with no failing row behind it — so it is filed, not folded in.
      ⚠️ Whoever picks it up must produce the row FIRST; a fix with no row is
      how the G2-g disposal happened in the first place.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [x] 🟢 **NOT A DIVERGENCE — RETIRED 2026-08-30 (D-FIELDCH). THE REFERENCE SIDE
      WAS VOID.** Probe `scratchpad/fieldch_probe.py`, 9 rows x 3 machines,
      **0 DIFF against the CF-3300**.
      🔴 **THE VG-8020 IS DISKLESS AND HAS NO `FIELD` AT ALL**, so it answers
      `Illegal function call` to EVERY row — including `FIELD #1,1 AS Z$`, an
      ordinary well-formed FIELD. It is not an oracle for this statement, and the
      filed row compared zerobas against a machine that cannot express the
      question. Other disk items in this file carry that caveat verbatim ("ONE
      REFERENCE (Disk BASIC; a diskless VG-8020 cannot express it)"); this one
      lacked it. [[classify-a-control-failure-by-which-side-failed-it]]
      🎯 **AND THE STATED RULE WAS UNTESTABLE FROM ONE ROW ANYWAY.** "The channel
      is classified before the expression" is a claim about an ORDER, and one row
      cannot show an order. The cheaper rule it never tested: a comparison yields
      -1 or 0 and BOTH are illegal channel numbers, so `#(1<2)` raises ERR 5 with
      no ordering involved — it does, on both machines, as does a bare `#-1`,
      while `#(2<1)` and `#0` both give `File not open`. The type error and the
      channel-domain error are simply different rows.
      ⚠️ Was `- [ ] 🔴 FIELD #(A$<5) ... Illegal function call ON THE VG-8020`,
      filed 2026-08-09 by D-STMTPEND.
      ✅ **AND THE CLASS WAS SWEPT, NOT JUST THE ITEM** (2026-08-30): every other
      TODO mention of a diskless VG-8020 beside a disk verb either already
      carries the "ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express
      it)" caveat, or says outright that the machine cannot exercise it — and the
      one item whose caveat WAS wrong had already been refuted properly by
      re-measuring on the CF-3300 (the 267 B channel-context target). **This was
      the only outlier.**

- [ ] 🔴 **K-FA5's FALSIFIABILITY PREMISE IS STALE, AND SO ARE FOUR OTHER
      COMMENTS.** Filed 2026-08-09 by D-STMTPEND
      ([`docs/spec-basic-stmtpend.md`](docs/spec-basic-stmtpend.md) §6.3).
      `basic/field.asm` (`tgt_parse_fld`) and
      `probes/basic/basic_probe_fldary.py` both argued that an abort is
      falsifiable *because* "exec_stmt CLEARS FPERR at the statement boundary
      ... so cutting this makes FIELD..A$(9) print OK". The boundary is a READER
      now, so a cut would fall through to a report rather than to silence — the
      check still earns its place (it raises BEFORE `ex_field`'s side effects,
      which the boundary is by construction too late for), but the stated reason
      no longer holds. All five comments were reworded to say so; **what has NOT
      been done is re-running K-FA5 to measure what the cut now reads.** Same
      shape at `basic/input.asm`, `basic/program.asm` (`exr_str`) and
      `basic/expr.asm` (`ev_mc_arg_checked`).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **K-PE1's FOUR UNEXPLAINED ROWS: SOMETHING RAISES ERR 5 WITHOUT THE
      WRITER.** Filed 2026-08-09 by D-PENDERR
      ([`docs/spec-basic-penderr.md`](docs/spec-basic-penderr.md) §9.1). With
      `penderr_set` cut so that NO deferred code can be recorded, four rows keep
      answering ERR 5 — `o.nn.5dz`, `o.nn.5ov`, `o.sub.5ex`, `u.nn.5dz`, all with
      `0*SQR(-1)` as their FIRST operand — while `n.5.w` (same first operand,
      nothing after it) correctly loses its error. So the SQR-domain error can
      reach ERR 5 by a route that does not pass through the pending-error cell,
      but only when another operand follows. This is a property of a CUT tree, so
      it does not bear on shipped correctness; it is filed because an unexplained
      knife result is a gap in the model of the error surface, not a curiosity.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **"THE APPARATUS IS STILL MEASURED" IS A CLAIM ABOUT A ROW SET, AND
      `locarg`'s IS MUCH WEAKER THAN ITS OWN SENTENCE SAYS.** Filed 2026-08-21 by
      D-LOCPARK, knife K-LP1
      ([`docs/spec-basic-locarg.md`](docs/spec-basic-locarg.md) §11.4).
      D-LOCARG §3.2 defends deleting a refuted justification by saying the eleven
      `u.*` rows still run every abort class untrapped, and it names the symptom:
      *"`LOCATE "5",3` printing `Type mismatch` and then `Missing operand`"*.
      **Put the depth-dependence back** — cut `fre_abort_low`'s `ld sp,(SAVSTK)`
      — **and `u.str` is GREEN.** Exactly ONE row of forty-five moves, `u.bare`,
      and it reads `''`, not a doubled message. So the battery does detect the
      property, at one row, by a symptom other than the advertised one, and the
      row the sentence names cannot see it at all.
      ➡️ **WHAT IS OPEN:** why `u.str` survives. `ENDFLAG` is set by
      `fre_abort_low` before its `ret`, so the run may simply stop at the next
      `rp_run` check before a second message can print — that is a hypothesis,
      not a reading. Either the mechanism is established and §3.2 is narrowed to
      what it can support, or a row is added that DOES see it.
      💰 0 ROM bytes; apparatus. ⚠️ This does NOT bear on the carve: D-LOCPARK's
      licence comes from reading both arms of `raise_error_hl`, not from this
      knife.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (hand-corrected: its own body prices it at 0 ROM bytes).

- [ ] 🔴 **`t.zero` IS BLIND TO A CUT THAT ALSO DISABLES ITS SEED, AND THE PROBE
      CLAIMS OTHERWISE.** Filed 2026-08-09 by D-LOCARG
      ([`docs/spec-basic-locarg.md`](docs/spec-basic-locarg.md) §8.3), found by
      knife K-LA5. Every `t.*` program in `basic_probe_locarg.py` opens with
      `CLS:LOCATE 7,4` so that "the cursor did not move" reads ` 4  7 ` and is
      distinguishable from the CLS home position ` 0  0 ` — the probe's `SEED`
      comment says so. That holds for every row **except the one whose target IS
      home**: `t.zero` (`LOCATE 0,0`) reads ` 0  0  0 ` whether both `LOCATE`s
      applied or neither did. Harmless in the shipped tree (where the seed
      applies) and **not** a reason to change the row — `LOCATE 0` being a VALUE
      and not an omission is what it is for. Recorded because the comment
      currently over-claims, and because the same shape will recur in any probe
      that seeds a cell it also tests.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [x] 🟢 **D-DEVBARE 2026-08-30: the `FOR` clause is OPTIONAL on a device channel
      — ZERO BYTES.** Spec
      [`docs/spec-basic-devbare.md`](docs/spec-basic-devbare.md); probe
      `scratchpad/devbare_probe.py`, knife `scratchpad/devbare_knives.py` (4/4).
      `basic/files.asm` read `jr nz,oo_fail_syn ; device channels require FOR
      OUTPUT` — a rule the reference does not have. `OPEN"CRT:"AS #1` and
      `OPEN"LPT:"AS #1` are accepted on a CF-3300 and the channel WORKS
      (`PRINT#1` and `CLOSE#1` both fine). A jump-target change fixes 4 rows.
      🔴 **FOUND BY A CONTROL THAT FAILED** — it was the baseline of a D-OPEN2
      discriminator run and voided it before I noticed the baseline was what was
      red. [[classify-a-control-failure-by-which-side-failed-it]]
      🟢 **`LEN=` STAYS REFUSED, FOR FREE** (the terminator check does it), and
      `w.crtlen` proves the refusal survived rather than assuming it.
      ⚠️ **`FOR INPUT` ON A DEVICE IS NOT COPIED**: the reference HANGS there, and
      a hang is not a behaviour to reproduce.

- [ ] 🔴 **A SECOND DISK `OPEN` RAISES A SPURIOUS `Syntax error` — THE OPEN
      ITSELF SUCCEEDS. (Corrected TWICE: first from "only ONE file may be open at
      a time" — device+device, device+disk and disk+device all WORK — and then
      from "refuses", which the channel table refutes.)** Measured 2026-08-30,
      [`docs/spec-basic-open2.md`](docs/spec-basic-open2.md), probe
      `scratchpad/open2_probe.py` (13 rows vs a CF-3300, **9 DIFF**).
      ```
      MAXFILES=2 : OPEN"TS.DAT"AS #1 LEN=128 : OPEN"TS2.DAT"AS #2 LEN=128
          cf3300 -> [OK]        zb -> Syntax error
      ```
      Every DISK shape: two random channels either order, two SEQUENTIAL
      channels, with or without `LEN=`, at `MAXFILES=2` or `3`.
      🔴 **MY FIRST WRITE-UP SAID "any second concurrent OPEN" AND THAT WAS
      WRONG** — every row in it opened two DISK channels (`A.TXT` and `B.TXT` are
      disk files too), so a device channel was never in the comparison and "every
      shape" was one shape. `v.2dev`, `v.dev1dsk2` and `v.dsk1dev2` all pass on
      both machines. Rows unchanged; the CONCLUSION was corrected.
      🎯 **AND THE NARROWER FINDING NAMES ITS OWN CAUSE.** `basic/sysvars.inc`:
      *"Because fat.asm keeps ONE global set of streaming state … only one
      channel's state is 'live' in those globals at a time"*, swapped by a
      write-back cache discipline. A device channel needs none of it, which is
      why it coexists — and the swap does not carry two open DISK channels.
      ✅ **THE SEPARATE DIVERGENCE THAT VOIDED A DISCRIMINATOR RUN IS FIXED**
      (D-DEVBARE, above, zero bytes): `OPEN"LPT:"AS #1` was `Syntax error` here
      and `OK` on the CF-3300, and it was the BASELINE of the device-vs-disk
      comparison.
      🎯 **THE CEILING IS HONOURED; TWO-DISK CONCURRENCY IS NOT.** After `MAXFILES=2`,
      channel #2 opens fine ON ITS OWN on both sides — so the table does raise
      the ceiling. And with NO `MAXFILES`, a second open reads `Bad file number`
      on both, which is what says the default ceiling of 1 is enforced correctly
      and the fixture is sound.
      ⚠️ **THE FACE IS WRONG TOO**: for the same file on two channels the
      reference says `File already open`; zerobas says `Syntax error`, naming the
      parser for a condition the parser is not in.
      🔴 **NARROWS TWO RECORDED CLAIMS** (it does not falsify them, which is what
      the first pass wrote): `basic/PROVENANCE.md` §MAXFILES said it *"retires
      the single-channel limit"*, and this file marked the multi-channel table
      **DONE**. Both are MOSTLY RIGHT — the token work, the ceiling and
      device-channel concurrency are all real. Only two-disk concurrency fails.
      [[a-fix-falsifies-the-justification-beside-it]]
      ➡️ **NARROWED 2026-08-30 BY ROWS, AND TWO OF MY HYPOTHESES REFUTED.**
      `ERL` says `ERR 2 AT 40` — the OPEN itself, not the statement after it (so
      it is not cursor damage); and `g.nolen`, the same open with NO `LEN=`
      clause, is also `AT 40` — so it is NOT the `jr c,oo_fail_syn` after
      `oo_parse_reclen`, which cannot fail without a clause. That was the only
      `Syntax error` exit I had enumerated on the disk path after the channel
      check, so the enumeration is incomplete.
      🎯 **AND IT IS NOT A REFUSAL — THE OPEN COMPLETES (2026-08-30).** Trapping
      the ERR 2, RESUMEing past it and reading the channel table out of RAM shows
      `FCH_MODES[1]=4, FCH_MODES[2]=4, FCH_ACTIVE=2`: **both channels marked
      open, channel 2 active**. The second OPEN did all its work and the error is
      raised AFTERWARDS — a spurious DEFERRED error, which is why `oo_nodisk` and
      `oo_fail` never matched: neither ran. And the channels are usable: `FIELD`
      on both works, and a `PUT` on each works individually.
      ⚠️ **`u.both` (write both, read one back) is `<NO OUTPUT>` and is NOT read
      as "two-channel writes fail"** — three sufficient causes (D-PUT3's counter,
      two 128 B `STRING$` temps in the default pool, a real two-channel write
      fault) and separating them needs its own rows.
      ➡️ **SO THE FIX MAY BE SMALL: STOP RAISING THE ERROR.** What remains is
      finding what sets `FPERR`=4 on this path.
      ✅ **LOCATED TO ONE CALL 2026-08-30, BY DIAGNOSTIC KNIVES.** Cutting
      `call fch_save_active` in `fch_claim` REMOVES the spurious error; cutting
      only the flush, only the `ldir`, clearing `SH_ERR`, or guarding `IX` each
      leave it. So the raise is in what survives all of those: **`fch_ctx_addr`**,
      the op-18 CALSLT that asks the string-heap tenant for the channel's
      context-block address.
      🔴 **SIX HYPOTHESES REFUTED, ALL MINE** — cursor damage, the reclen exit,
      the flush, the `ldir`, a stale `SH_ERR`, an `IX` clobber.
      🎯 **AND WHY NOTHING CAUGHT IT: `fch_save_active` returns early when
      `FCH_ACTIVE` is 0, so `fch_ctx_addr` — and op 18 — NEVER RUN with a single
      channel.** The path executes for the first time when a second disk channel
      is claimed; it is untested by construction.
      ✅ **AND THE TENANT CALL ITSELF IS EXONERATED (RAM readout, not reasoning):**
      `SH_ERR`=0, `SH_LEN`=1 (correct — channel 1 is the one being saved), and
      `SH_PTR`=`$B9D4`, which is plausible against `TXTTAB`=`$8001` /
      `HIMEM`=`$F380` since the table is carved below **TXTMAX**, not HIMEM. So
      the 50-byte save is NOT landing in the program, and the tidy "stray write
      corrupts the tokenised text" theory is unsupported. The one-channel
      controls read UNINITIALISED (255/65535), which is the direct measurement
      that op 18 never runs with a single channel.
      ⚠️ **SEEN IN PASSING, NOT CHASED:** `VARTAB` ($F6C2) and `STREND` ($F6C6)
      both read **0** — zerobas does not maintain those published MSX cells. Its
      own question; filed here only so it is not lost.
      ⚠️ **NEXT NEEDS A DEBUGGER, NOT A READING**: a breakpoint on the second
      `fch_ctx_addr` with a register/RAM dump. The handler and its callee chain
      read correctly for both channels, and BASIC-level bisection has bottomed
      out — guessing further is what produced the six refutations.
      🎯 **SUPERSEDED CANDIDATE (kept for the reasoning):**
      `fch_claim` is reached only by a DISK open, and claiming a SECOND channel
      calls `fch_save_active` -> `fch_flush_active` — the write-back that
      persists the FIRST channel. That path runs ONLY when a second disk channel
      is claimed, and a device open never calls `fch_claim` at all, which is why
      device+disk coexists. Neither `oo_nodisk` nor `oo_fail` maps to ERR 2, so
      the raise is either in that chain or a deferred `FPERR`=4 surfacing at the
      statement boundary. Distinguishing them wants instrumentation.
      ⚠️ **`MAXFILES` DISARMS `ON ERROR`** (both machines): arm the handler
      AFTER it, or the probe measures nothing.
      ➡️ **BLOCKS D-PUT3's per-channel question** — the row that would answer it
      needs two channels and is unwritable on this machine.
      ⚠️ ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express it).
      🤖 AUTONOMOUS — the reference settles the behaviour.

- [ ] 🔴 **THE THIRD `PUT` OF A SESSION HANGS ZEROBAS, UNTRAPPABLY — AND A
      RANDOM-ACCESS WRITE LOOP IS AN ORDINARY MSX BASIC PROGRAM.** Measured
      2026-08-30, [`docs/spec-basic-put3.md`](docs/spec-basic-put3.md),
      probe `scratchpad/reclen_probe.py` (15 rows, CF-3300 vs repack).
      ```
      OPEN"TS.DAT"AS #1 LEN=128 : FIELD#1,128 AS A$
      LSET A$=STRING$(128,"B") : PUT#1,1   ok
                                 PUT#1,2   ok
                                 PUT#1,3   cf3300 [OK]   zb <NO OUTPUT>
      ```
      🔴 **AND THE FIRST FILING CONFLATED TWO RULES — SEPARATED 2026-08-30.**
      Every row paired an `LSET ... STRING$` with each `PUT`, so "the third PUT"
      and "the third LSET" coincided on all of them. Four rows separate them:
      three LSETs with ONE put is OK, three LSETs with NO put is OK, one LSET
      with three puts DIES, and **no LSET at all with three puts DIES**. The
      claim survives and the reproducer is now three statements with no string
      handling anywhere. [[two-rules-that-coincide-on-every-row-you-have]]
      ```
      OPEN"TS.DAT"AS #1 LEN=128 : FIELD#1,128 AS A$
      PUT#1,1 : PUT#1,1 : PUT#1,1
      ```
      ➡️ **PATH NARROWED, NOT READ**: `ex_put` (`basic/field.asm`) is
      stack-balanced, so the subject is inside `fat_rand_put`
      (`basic/randio-body.inc`) and its chain — `frnd_locate`, which extends the
      cluster chain with `GP_FLAGS=1`, and the `fat_dir_update` tail.
      🎯 **THREE FACTS, EACH WITH ITS OWN ROW.** It is the `PUT` COUNT and
      nothing else (`p.same3` writes the SAME record three times and dies, so no
      layout or straddle question is involved); it is CUMULATIVE ACROSS THE
      SESSION (`p.close3` closes and reopens between writes and still dies, so
      `CLOSE` does not release whatever is consumed); and it is NOT A TRAPPABLE
      ERROR (`p.trap3`, with a handler the interpreter can reach, prints nothing
      at all — the handler never runs). `p.put1` / `p.put2` / `p.trap2` are the
      controls and all pass.
      ✅ **CHARACTERISED FURTHER 2026-08-30** (spec §3a): three `GET`s are fine,
      so it is `PUT`s and not disk ops; a `GET` between the second and third does
      NOT reset it; `CLOSE` + `CLEAR` + reopen does NOT reset it; the count does
      not move with record length (64 and 128 alike); it dies on a file that does
      not exist yet; and `1,1,1` and `1,2,3` both die. **The third `PUT` of a
      run, unconditionally.**
      ✅ **THE "UNTRAPPABLE" CLAIM NOW RESTS ON A LIVE HANDLER, NOT ON SILENCE
      (2026-08-30).** It was concluded from a row that printed NOTHING with a
      handler in place — an ABSENCE, which is also what a broken fixture looks
      like. `k.puttrap` arms the same handler, does TWO `PUT`s, then forces a
      KNOWN `ERROR 7`, and traps it (`ERR 7 AT 60`) on both machines; `k.put3` is
      the same program with the third `PUT` instead and still dies.
      ⚠️ **FIXTURE CAVEAT THAT COST A PROBE: `MAXFILES=n` DISARMS `ON ERROR`** —
      on BOTH machines (correct behaviour, not a divergence). An earlier run put
      `MAXFILES=2` between the handler and the subject and read the untrapped
      error as a finding.
      🔴 **STILL OPEN: PER-CHANNEL OR GLOBAL?** The row is four `PUT`s spread
      two-and-two over two channels, and it CANNOT BE WRITTEN on this machine —
      D-OPEN2 (two disk channels are `Syntax error`) blocks it, which is the
      reason the two-channel fixture kept failing.
      ⚠️ **FOUR FIXTURE FAULTS IN ONE SITTING, THREE OF WHICH LOOKED LIKE
      FINDINGS**: `ON ERROR GOTO 100` on a harness numbering 10,20,30…;
      `OPEN … AS #2` under the default `MAXFILES=1`; and the two-channel
      `Syntax error`. Budget for that when picking this up.
      ➡️ **NEXT: find what the third `PUT` consumes.** The `CLOSE`-survives clue
      points at a cumulative resource rather than per-`FCB` state.
      ⚠️ ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express it).
      🤖 AUTONOMOUS — the reference settles the behaviour and the bisect is done.

- [x] 🟢 **D-RECLEN2 2026-08-30 — THE FACE SHIPPED, THE DOMAIN DID NOT**
      ([`docs/spec-basic-reclen2.md`](docs/spec-basic-reclen2.md)). An
      out-of-range `LEN=` now raises **`Illegal function call`** as the CF-3300
      does (`LEN=0`/`257`/`512`), not `Syntax error` — 3 rows closed, K-RL2 5/5.
      🔴 **THE DOMAIN WIDENING WAS TRIED AND REVERTED: ZEROBAS CANNOT STRADDLE.**
      `fat_rand_put`'s overlay `ldir`s into `FWBUF + within` for `reclen` bytes,
      so record 6 at `r=100` (within=500) writes **88 bytes past the 512-byte
      sector buffer**. Two `PUT`s at `LEN=100` including record 6 kill the
      program; the same shape at `LEN=128` is fine.
      🔴 **AND THE PROBE THAT "PROVED" IT SAFE WAS BLIND TWICE**: a round trip
      cannot see a wrong offset (`PUT`/`GET` share `frnd_calc`), and
      `mul_reclen` is a SHIFT loop, so `r=100` computed `*64` and the record
      never straddled at all. **`tests/test_open_len.py` caught it** — it checks
      the arithmetic against an INDEPENDENTLY derived offset.
      🎯 **D-RECLEN's ORIGINAL CAUTION WAS RIGHT AND MY REFUTATION WAS WRONG**:
      the reference not needing the constraint does not mean this engine does not.
      ➡️ **Widening needs BOTH**: `mul_reclen` to really multiply (shift-add,
      ~9 B, written and measured working) AND `fat_rand_put`/`get` to span two
      sectors. Until then `LEN=100`/`255` stay divergent, now with an ERR 5 face.
      📐 **THE DESIGN, WORKED OUT 2026-08-30 SO THE NEXT SESSION WRITES RATHER
      THAN DESIGNS:**
      - **At most TWO segments, never a loop.** `reclen <= 256` and a sector is
        512, so a record touches two sectors at most: `n1 = min(reclen, 512 -
        within)` from sector `GP_SEC`, then `reclen - n1` from `GP_SEC + 1` at
        offset 0. Both `fat_rand_put`'s `frp_overlay` and `fat_rand_get`'s
        read-back copy take the same shape, so the split belongs in ONE helper.
      - **The second segment re-enters `frnd_locate`** with `GP_SEC` bumped —
        for `PUT` that is also what allocates a new cluster if the record crosses
        one, which is why `GP_FLAGS`'s extend bit must still be set on the second
        pass.
      - ⚠️ **RAM: two words are wanted (running destination + remaining count),
        and `sysvars.inc` ADVERTISES `$EA92..$EAFF` free (110 B) — DO NOT TRUST
        THAT LINE.** RAM has no gate here; walk it with
        `scratchpad/rammap_sweep.py` and then ASK THE MACHINE with
        `ramfree_probe.py`. A delta between two names is not free space.
      - 🟢 **THE INSTRUMENTS ALREADY EXIST, AND THEY ARE THE POINT.**
        `tests/test_open_len.py` checks `frnd_calc` against an INDEPENDENTLY
        derived offset and is what caught the shift loop; restore its `r=100`
        geometry rows (recno 1/5/6/7/11/255 — record 6 is the straddle) as the
        first gate. `scratchpad/reclen2_probe.py`'s `x.adjacent` is the
        emulator-side check that does not round-trip through the arithmetic
        under test.
      - ⚠️ **A ROUND-TRIP ROW IS NOT EVIDENCE HERE** — `PUT` and `GET` share
        `frnd_calc`, so they agree on a wrong offset. That mistake shipped once
        already.
- [ ] 🔴 **A NON-TILING `LEN=r` IS `Syntax error` HERE AND `OK` ON THE CF-3300 —
      AND THE DOC CLAIMED BYTE-IDENTITY ON A CORPUS THAT NEVER CONTAINED THE
      CASE.** Filed 2026-08-19 by D-RECLEN, found by a row that MISSED its
      prediction while measuring something else.
      ```
      OPEN"TS.DAT"AS #1 LEN=100 : PRINT"[";"OK";"]"
          cf3300 -> [OK]        zb -> Syntax error
      ```
      (row `r.len100`, `make fldwidth-acceptance`; DEFERRED, measured, printed.)
      `oo_parse_reclen` ([`basic/files.asm:578`](basic/files.asm:578)) validates
      the record length to a **power of two in 1..256** *"so records tile the
      512-byte sector with no straddle"* and raises `Syntax error` otherwise.
      The CF-3300 accepts 100 — `r.sum` reached a `FIELD overflow` behind it.
      🔴 **`disk/docs/diskbasic-option-surface.md` SAID `non-tiling → Syntax
      error … byte-identical to CF-3300`, AND THE PROBE IT CITES DRIVES `LEN=128`
      AND NOTHING ELSE** — a power of two. An "all match" is a statement about a
      corpus, not about a rule ([[arcmask-slice]]); the row that would have
      falsified it was never in the corpus. Doc corrected to `◐` with the
      divergence named.
      ⚠️ **NOT PART OF THE ERR-50 RULE and must not be folded into it** — it is
      an `OPEN` parse question, not a `FIELD` one. 💰 Not scouted, not priced:
      the straddle argument is a REAL design constraint (a 100-byte record does
      not tile a 512-byte sector), so "just widen the validator" is exactly the
      cheap wrong answer — what the reference DOES with a straddling record is
      unmeasured, and `GET`/`PUT` round-trip rows come before any byte.
      ✅ **THE STRADDLE PREMISE IS REFUTED, 2026-08-30**
      ([`docs/spec-basic-put3.md`](docs/spec-basic-put3.md) §2). The CF-3300
      round-trips record 6 at `LEN=100` — bytes 500..599, ACROSS the 512-byte
      boundary — intact, and damages neither neighbour; `LEN=96` agrees. So the
      constraint `oo_parse_reclen`'s comment asserts is not one the reference
      has, and the power-of-two validator is zerobas's own invention.
      🔴 **RECORD 6 IS THE ONLY ROW THAT COULD HAVE SAID SO** — records 1 and 5
      lie wholly inside the first sector and would round-trip on an
      implementation that cannot straddle at all.
      ✅ **AND THE VALIDATOR IS NOW WIDENED (D-RECLEN2, 2026-08-30).** The
      "still unmeasured, needs three `PUT`s" caveat that stood here is
      DISCHARGED: writing only record 6 is a SINGLE `PUT`, and zerobas
      round-trips it exactly as the reference does.
      ⚠️ ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express it).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **A STORED `DATA` LITERAL CHARGES THE STRING POOL NOTHING ON BOTH
      REFERENCES AND 25 BYTES HERE — measured 2026-08-20 (D-ARYOOS §2.3), and
      it is the S-CLP-5 body-ownership class with a new, sharper pair of rows.**

      | row | program | vg8020 | cf3300 | zb |
      |---|---|---|---|---|
      | `s.readary` | `CLEAR 60` / `DIM A$(5)` / `B$=STRING$(25,"A")` / `A$(1)=B$` / `DATA <25 chars>` / `READ A$(2)` / `PRINT"[OK]"` | **`[OK]`** | **`[OK]`** | `Out of string space in 60` |
      | `s.readscal` | same, `READ D$` into a **scalar** | **`[OK]`** | **`[OK]`** | `Out of string space in 50` |

      🎯 **THE SCALAR TWIN IS WHAT MAKES IT THE OWNERSHIP QUESTION AND NOT AN
      ARRAY ONE** — both destinations diverge identically, so no array rule can
      be at fault. The reference points a stored literal's descriptor straight
      AT THE PROGRAM TEXT (already recorded by `hold-lit-prog` in the
      `clearpool` `share` battery, 2026-07-29, as a FRE reading); these two rows
      are the first time it shows up as a **divergent ERROR** rather than a
      divergent number, which is a much harder thing to be relaxed about.
      ⚠️ Carries the hazard S-CLP-4 already wrote down: a variable pointing into
      program text means `MID$(A$,1,1)="X"` writes into the PROGRAM. Unpriced,
      and it is a design question (store-by-reference), not a byte question.
      🙋 NEEDS-JOOST — a call that is yours to make (refactor, no oracle).
- [ ] 🟡 **`load error` IS PRINTED, NOT RAISED — ✅ FIXED AT ALL SIX MISSING-FILE
      VERBS (D-LOADERR-FIX 2026-08-20, 16 B; D-BLNF 2026-08-21, `BLOAD`, 4 B main
      + 12 B sub). WHAT REMAINS IS ONE ROW AND IT IS A DIFFERENT FACE.**
      [`docs/loaderr-fix-notes.md`](docs/loaderr-fix-notes.md).
      `LOAD`, `RUN"f"`, `MERGE`, `OPEN…FOR INPUT` and `OPEN…FOR APPEND` now raise
      **ERR 53 `File not found`** and stop, matching both references;
      `dskmsg-acceptance` went **5/5 + 7 reported → 10/10 + 2 reported**, the
      five rows graduating the day they were filed.
      🎯 **THE SPLIT NEEDED NO NEW STATUS.** `fatprim_bounce` already writes
      `DISKOP_OP` with the selector it is about to run, so `DISKOP_OP ==
      FAT_FIND` on a failure means exactly *mounted fine, name not there*. One
      11-byte helper (`df_or_loaderr`) plus a 5-byte tail; every consumer is a
      **0-byte retarget**.
      🔴 **THE FIRST DRAFT BROKE THE CASSETTE AND AN EXISTING GATE RAN THE KNIFE.**
      `dpl_err` is shared with `do_tape_prog` (nine sites) and no cassette op
      writes `DISKOP_OP`, so a broken TAPE read a stale cell and answered
      `File not found`. `castail-acceptance`'s `cas-run-brk` caught it on the
      first run. I had identified that exact hazard for the `DISKSLOT_OK == 0`
      arm and guarded **that one instance** — 🎯 **guarding an instance of a
      class is not guarding the class.** The default is now inverted: `dpl_err`
      is safe and the stale read is **opt-in** at `dpl_nf`. Byte-neutral.
      🔴 **FIVE PINNED ROWS WERE A GREEN ORACLE FOR THE DEFECT** —
      `disk_probe_fat_error_disposition.py` pinned zerobas's own `load error` for
      exactly these verbs and passed for as long as the defect lived; the FIX is
      what turned them red [[a-green-oracle-can-assert-the-defect]]. The pins
      were honest (marked *not measured on the reference*) and moved in the same
      commit as the code, as `kill-missing`'s did. `runtail`'s per-side
      normalisation collapsed to one string too.
      ✅ **`BLOAD` CLOSED 2026-08-21 (D-BLNF)** — `docs/loaderr-fix-notes.md` §6.
      Everything the 08-20 entry said about *why it cannot use the `DISKOP_OP`
      test* was true and still is; the wrong half was reading that as *cannot
      make the distinction*. `fat_io_open` IS mount-then-find, so a zero-byte
      label (`fat_io_find`) between them gives the tenant a carry that means
      exactly "mounted, name not there". `BL_STAT` gained a third value and the
      resident stub raises ERR 53 at the same `df_notfound`.
      🎯 **AND THE FIX OPENED A HOLE ITS OWN COMMIT CLOSES:** BLOAD's MOUNT arm
      had no row anywhere, so re-pointing it at the new raise left
      `dskmsg-acceptance` 11/11 and `bload-missing` PASSING. `bload-nodisk` now
      sits with `kill-nodisk`/`name-nodisk`, and knife K-BN3 is the measurement
      that it cuts. `bload-missing`'s pin moved with its own code, as the rule
      required. `dskmsg-acceptance` **10/10 + 2 → 11/11 + 1 reported**, knives
      4/4 EXACT.
      ➡️ **WHAT REMAINS IS ONE ROW, `dsk-bloadmode`, AND IT IS NOT A SMALLER
      VERSION OF THIS ONE** — see the standing residual below.
      💰 **Main page 1 measured 22 B before D-LOADERR-FIX, 6 B after it and 2 B
      after D-BLNF (2026-08-21, `make basic-reloc`)** — the next page-1 slice
      needs a carve scouted before a byte moves.
      *Original filing:* — 🔴 **`load error` IS PRINTED, NOT RAISED — THE PROGRAM
      RUNS ON. MEASURED 2026-08-20 (D-FNARG2), and it is the reading two earlier
      slices said the class was blocked on.**
      [`docs/fnarg2-msx1-characterization.md`](docs/fnarg2-msx1-characterization.md)
      §4.2/§4.3.

      | row | program | cf3300 | zb |
      |---|---|---|---|
      | `f.loadlit` | `10 LOAD"FCZ.DAT"` (missing) / `20 PRINT"[OK]"` | **`File not found in 20`** | **`load error`** then **`[OK]`** |
      | `f.bloadlit` | `10 BLOAD"FCY.BIN"` (missing) / `20 PRINT"[OK]"` | **`File not found in 20`** | idem |
      | `f.savevar` | `10 A$="FC2.DAT"` / `20 SAVE A$` / `30 PRINT"[OK]"` | `OK` | `load error` then `[OK]` |

      🔴 **NOT A WORDING DIVERGENCE — A CONTROL-FLOW ONE.**
      [`basic/bload.asm:160`](basic/bload.asm) `load_error` is `TAPIOF`, an
      `ERRMARK` byte, `print_msg`, **`ret`**. No ERR code, no line number, no
      `ON ERROR` trap, and execution continues into the next line — `[OK]` is
      printed *underneath* the message. **Same class as the `ex_let_arr_str`
      swallow D-ARYOOS closed the same day**, in a different verb family.
      ⚠️ **THIS CLASS HAD NO OPEN PICKUP ENTRY.** D-DSKMSG §4.2 and D-DKNAME
      §3.4/§6.5 both name it — *"that reading opens the whole `load error`
      wording divergence for `LOAD`/`RUN`/`BLOAD`/`OPEN`/`APPEND`/`MERGE` — six
      verbs nothing has measured"* — but only inside a **`- [x]`** item, which
      is exactly how §4.7 rotted for eleven days. It is open now.
      ✅ **ALL SIX VERBS MEASURED 2026-08-20 (D-LOADERR)**,
      [`docs/loaderr-msx1-characterization.md`](docs/loaderr-msx1-characterization.md).
      `LOAD`, `BLOAD`, `RUN"f"`, `MERGE`, `OPEN…FOR INPUT`, `OPEN…FOR APPEND`:
      every one is `File not found in <line>` — **raised, and it stops** — on the
      CF-3300, and `load error` + carry on here. Two green controls (the same
      two OPEN forms against a file that EXISTS) read `[OK]` on both sides, so
      it is the failure path and not the verb.
      🎯 **AND A SEVENTH FACE THE CLASS DID NOT KNOW ABOUT:** `BLOAD"PROG.BAS"`
      — a real file that is not binary — is **`Bad file mode in 10`** there and
      `load error` here. The reference tells NOT FOUND apart from WRONG KIND and
      zerobas collapses both.
      🎯 **`KILL` AND `NAME` ARE THE PRECEDENT AND ARE ALREADY RIGHT** —
      `dsk-killnone`/`dsk-namenone` are GATED and agree, their arms routing at
      `df_notfound`. Eight verbs in one class: two fixed, six not.
      ✅ **SEVEN ROWS NOW LIVE IN `make dskmsg-acceptance`, PRINTED AND NOT
      GATED** (5/5 gated rows unchanged), with the reason printed in the run's
      own tail. They graduate into the tally the day the split lands, exactly as
      `dsk-namenone` did — so this item cannot rot the way §4.7 did.
      🔴 **AND THE REAL BLOCKER IS NOW EXACT, NOT A GUESS.** It is **not** that
      `load_error` is shared with cassette: it is that `load_error` **RETURNS**,
      and [`basic/cload.asm:840`](basic/cload.asm) says in as many words that
      several of its **73** call sites *"RESUME into their caller on purpose"*.
      So the fix is per-arm — and the arms are themselves conflated: `oo_fail`
      covers *not found / dir-full / mount / I-O*, `dpl_err` covers *not found /
      mount / I-O / EOF-before-data*, and both get their CF from `fat_io_open`,
      **which returns carry and nothing else**. 🎯 **THE PRIMITIVE MUST RETURN A
      STATUS BEFORE EITHER ARM CAN SPLIT — the `ARY_ERR=4` shape exactly**
      ([[aryoos-slice]]). Routing `oo_fail` wholesale at `df_notfound` reports
      `File not found` for an unreadable disk: a new defect for an old one.
      💰 **NOT PRICED, AND DELIBERATELY NOT FOLDED INTO D-FNARG.** That slice is
      about PARSING (a second source for `parse_disk_fcb`); this one is about
      RAISING. ERR 53's machinery already exists and ships —
      [`basic/files.asm:144`](basic/files.asm) `ld a,53`, message sub-hosted by
      D-MSGSUB — so the shape is "route the disk arms at a raise", but
      `load_error` is shared with the CASSETTE paths, where a bare C-BIOS
      TAPION always fails and the right face is unmeasured. **Separating those
      two callers is the design question**, and it must not be assumed to be a
      rename [[a-filed-blocker-can-name-the-wrong-obstacle]].
      🔭 SCOUT-THEN-ASK — the decision is yours; the measuring and pricing in front of it are not (refactor, no oracle, but unpriced/unmeasured first).
- [ ] 🔴 **Two type-code namespaces share the value `1`** — the published `DEFTBL`
      string code and zerobas's own variable-chain string tag. D-DEFSTR fixed the
      three sites that crossed them (one was a live memory corruption) but the two
      namespaces still overlap on the numeric values, so the next site that feeds
      one into the other reintroduces the class. Collapse to ONE. Detail:
      *“`DEFTBL_STR` SHOULD BE `3`, NOT `1`”*, line 4072.

**Apparatus / gate limits (each is a stated limit, not a filed defect)**
      🙋 NEEDS-JOOST — a call that is yours to make (refactor, no oracle).

- [ ] 🔴 **A PAGE-ALIGNMENT ASSERT WITH NO ENFORCEMENT IS A LANDMINE FOR THE
      NEXT UNRELATED EDIT — one fired, and the class is not swept.** Filed
      2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](docs/deffn-impl-2026-08-22.md) §4.5.
      `sub/deftype.asm`'s `edt_codes` guard (`IF (high edt_codes) != (high
      (edt_codes+3))`) fired because a 40-byte routine was added to a file
      INCLUDED AHEAD OF IT. The guard was right and useless: *"never let an
      unrelated sub-ROM edit relocate this table"* is not a rule anyone can
      keep, and every future page-0 tenant re-rolls the dice. ✅ That one is
      now ENFORCED (≤3 B of pad, assert kept as a proof). ⚠️ **The SWEEP is
      what is open**: `basic/usr.asm`'s `IF (low USRTAB) + 18 > 255` is the same
      shape over a sysvar rather than a ROM label, and nothing has walked the
      tree for the rest. A `db UNDEFINED_SYMBOL` assert that a stranger's edit
      can trip is a build break with a diagnostic and no remedy.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **NOTHING POLICES A RAM FREE-SPACE CLAIM, AND THE ONE IN THE MAP WAS
      36x WRONG.** Filed 2026-08-22 by the D-DEFFN RAM hunt,
      [`docs/deffn-ramhunt-2026-08-22.md`](docs/deffn-ramhunt-2026-08-22.md) §1.
      `make wall-assertion-check` gates ROM figures and dates them; RAM figures
      rot silently (`basic/sysvars.inc` offered *"376 B spare"* where **10**
      were, for three slices). Two tools now exist and neither is a gate:
      `scratchpad/rammap_sweep.py` (walks the `equ` chain, calibrated) and
      `scratchpad/ramfree_probe.py` (fills a window, works the machine, reads
      it back). ⚠️ **A delta between two names is NOT free space** — `TOKBUF`'s
      612 B delta is 36 B free and `LINEBUF`'s 256 B delta is 0. Promoting
      either tool to a gate needs that caveat encoded, not just documented.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **THE `[...]` READOUT FAMILY IS DEFENDED BY ACCIDENT IN EVERY SCRATCH
      PROBE.** Filed 2026-08-22 by the D-DEFFN RAM hunt,
      [`docs/deffn-ramhunt-2026-08-22.md`](docs/deffn-ramhunt-2026-08-22.md)
      §5.3. `BR.search` returns the FIRST `[...]` on screen, which is the ECHO of
      the typed `PRINT"[";V;"]"` line — a reading shaped like a result. The
      SHIPPED gate `probes/basic/basic_probe_deffn.py` knows this and defends
      with an explicit `CLS`, documented in its own comment (*"eleven rows"*).
      🔴 **The scratch probes do not**: `paintmc_probe.py`, `dupspan_probe.py`,
      `s3_scout_probe.py`, `point3_recheck.py`, `mc_layout_probe.py` and
      `deffn_scout.py` all use `BR.search`, and are protected only because their
      fixtures enter a graphics mode and the closing `SCREEN 0` clears the
      screen. **A fixture that never leaves SCREEN 0 has no defence at all** —
      which is exactly which rows of `ramfree_probe.py` failed. Remedy is
      `findall()[-1]` (the program's own output is always the last bracket) or
      the shipped `CLS`; pick one and apply it to the family.
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).

- [ ] ⚠️ **A SCRATCH PROBE THAT NEEDS A DISK MUST MOUNT ONE, AND THE FAILURE
      READS AS A LANGUAGE RULE.** Filed 2026-08-22,
      [`docs/deffn-ramhunt-2026-08-22.md`](docs/deffn-ramhunt-2026-08-22.md)
      §5.6. Booting `C-BIOS_MSX1_EU_REPACK_DISK` without `diska=` made
      `OPEN"TS.TXT"FOR OUTPUT AS #1` answer **ERR 59**, which is exactly what a
      channel-ceiling violation looks like. The shipped batteries pass a
      **writable copy** of `disk/test720.dsk` (mounting the original mutates the
      fixture — [[test-disk-mutation-gotcha]]). 🔴 And an OPEN can fail *without
      raising* (it printed `load error` and carried on), so a disk row must
      READ BACK what it wrote rather than trust that it ran.
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).

- [ ] ⚠️ **`check_probe_preflight.py` carries the IDENTICAL `SCAN_DIRS`** — the
      denominator D-INJJUDGE derived for `injector-check` was left hand-listed
      here, and **6** out-of-scope `.py` launch openMSX. Same shape, different
      rule, and **that rule has not been walked**: widening it on the strength of
      the sibling's measurement is exactly [[a-borrowed-window-inherits-its-corpus]].
      Re-open by walking preflight's own rule over its subject's life first.
      Detail: `docs/spec-probe-injjudge.md` §3.6.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **Three probe page-0 entry addresses stay HARDCODED** —
      `basic_probe_subrom_boot.py` (`$0040`), `basic_probe_subrom_inttest.py`
      (`$0049`), `basic_probe_graphics_floor.py` (`$0058`). All three ARE scored;
      deriving them from `sub/equates.inc` needs its own falsification because they
      inject raw bytes into a bare machine deliberately. Detail: line 2582.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **`build/disk.rom` pad-only damage is invisible ON PURPOSE** — 9543 of
      16384 bytes (58.2 %) are `$00` pad in 252 runs. Closing it needs a whole-image
      digest, which would pin the ROM against every legitimate `disk/*.asm` change.
      Re-open only with an argument that answers that. Detail: line 2577.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **The raw-byte class beyond the dump row has NO mechanical floor, by
      measurement** — check 6 covers 1 of the 20 residue lines. The other 19 are
      the human full-verify trail's job, exactly like the inline decoded form
      below. Re-open only with a discriminator scoring **0** on all three of the
      179-line replacement corpus, the **984-line kept-context corpus** (the new
      and harder bar) and the 15 live reference-attributed lines, while still
      firing on ≥1 residue line. Detail:
      `docs/spec-audit-citations-bytes.md` §3.1.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **The INLINE decoded form is measured UNDECIDABLE, and that is a standing
      hole, not a closed item** — `$0246: LD A,(…) / AND A / CALL Z,…`. Every
      threshold that catches any of it fires on the hand-reviewed prose that
      replaced it, and on 25–464 honest lines (four variants measured). The human
      full-verify is the only backstop; re-open only with a discriminator that
      scores 0 on the 156-line replacement corpus. Detail:
      `docs/spec-audit-citations-docs.md` §2.2.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **Both check-5 allowlist entries need a HUMAN paper-trail confirm** —
      `probes/lib/{omsx_repl,latch_check}.py` render C-BIOS instructions.
      `allowed-sources.md` grades C-BIOS **B/Conditional** ("we don't lift its
      code/expression"), which is a judgement `docs/clean-room-audit.md` reserves
      for a human; the tool deliberately does not make it. Reasons are written in
      `tools/citations-listing-allow.txt`. Detail:
      `docs/spec-audit-citations-docs.md` §2.6.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] ⚠️ **`disk/runtime.asm:423` `int_h_body` awaits a HUMAN decision** — newly
      visible (D-NEGJUDGE) and acknowledged in `tools/citations-advisory-allow.txt`,
      not resolved. Its block attests in prose (*"the MSX1 standard,
      BIOS-agnostic"*) but names no document; the finding it restates is
      `disk/docs/provider-oracle-scope.md` **§8.70** (O-2, the KEYINT chaining
      contract), and the header's own name carried *"(A-2/8.70)"* until the A-3
      rename (`71b1096`) dropped it. Remedy is to name §8.70 in the block **or**
      to delete the dead body the header itself calls `SUPERSEDED` — a judgement
      the tool declines to make. Detail:
      `docs/spec-audit-citations-negation.md` §2.5.
      🙋 NEEDS-JOOST — a call that is yours to make (retire / delete).
- [ ] ⚠️ **`lof-acceptance` intermittent oracle drift — two sightings, nothing
      since.** Sighting 3 has not occurred across EIGHT consecutive slices
      (D-PINDATA, D-INJSINK, D-ROMJUDGE, D-DSKJUDGE, D-CITEJUDGE, D-DOCJUDGE,
      D-BYTEJUDGE, D-REVJUDGE — the last at 45 cases, 0 oracle drift, whole log
      captured, 59 lines). A third IS a finding to
      chase; capture the **whole** log (`> file 2>&1`), because sighting 1's row
      identity was lost to a `tail -6`. Detail: line 3678.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

## Phase 1 — committed loader-stub target (✅ closed)

The charter (README) is deliberate: *just enough MSX-BASIC to run the `.BAS` /
binary loader stubs that boot disk and tape games — **not** full-language
compatibility.* That loader-stub target is **complete**:

1. **Loader-stub BASIC** — ✅ done.
2. **Tape transport** (read + write) — ✅ done. `BLOAD"CAS:",R`/`CLOAD`/`LOAD"CAS:"`
   load and `CSAVE`/`SAVE"CAS:"`/`BSAVE"CAS:"` save on-device (tokenised-only SAVE;
   `,A`/ASCII save is a Phase-3 language item).
3. **Disk transport** (read + write) — ✅ done (`disk.rom`; see [`disk/TODO.md`](disk/TODO.md)).
4. **Disk interface standardization ("Phase 1.5")** — ✅ done. `zerobas-BASIC` reaches
   disk files through the **standard `$4010` DSKIO sector interface** (owning the
   FAT12/dir logic loader-side); `zerobas-disk` installs the standard **`HPHYD`→DSKIO**
   hook + a real `GETDPB`, so any standard disk ROM works under zerobas-BASIC **and** a
   real BIOS can drive zerobas-disk. Host + provider + the host-side and Tier-1 provider
   oracles all pass. *(Spike note: the drive-letter loader path is pure PHYDIO/DSKIO —
   the BASIC DEVICE/expansion mechanism is never called — so the basic-side FAT is the
   necessary price of the universal sector interface, not avoidable duplication. See
   [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md).)*

The one open checkbox under Phase 1.5 — the **Tier-2** provider oracle (a real
DOS/Disk-BASIC *filesystem* host, the only organic `GETDPB` consumer) — is the seam
into the next phase and is carried into **Phase 2** below. Phase 1 is otherwise
closed; the per-item done-record follows further down.

## Status today — three components, two axes

zerobas is three separately-built artifacts, combined only at runtime: `basic/` →
`basic.rom` (cartridge, slot 0 page 1); `tape/` → the zerobas-tape IPS patch
(C-BIOS page 0 cassette signal layer); `disk/` → `disk.rom` (slot 3-1).

| | Device / transport layer | Interpreter statements (basic.rom) |
|---|---|---|
| **Tape** | ✅ read **and** write signal layer (MSX1/2/2+) | ✅ `BLOAD"CAS:",R`, `CLOAD`, `LOAD"CAS:"` load on-device; `CSAVE`, `SAVE"CAS:"`, `BSAVE"CAS:"` write on-device — full read+write parity (tokenised-only SAVE, `,A`/ASCII is Phase 3) |
| **Disk** | ✅ DSKIO + FAT12 + BDOS, read **and** write (differential vs CF-3300 & MSX-DOS 1) | ✅ `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for `"A:"` † |

† `zerobas-BASIC` reaches the disk through zerobas-disk's **private** `bdos_entry`
(published at SYSTEM vector `$F37D`), **not** the standard `$4010` DSKIO sector
interface — so a *foreign* disk ROM does not work under it, and zerobas-disk is not
reachable by real BASIC/DOS. Phase 1.5 (below) closes this by driving standard
DSKIO loader-side and installing the standard `HPHYD` hook provider-side.

Language (Phase 1, done): byte-identical tokeniser (keywords, integer / `&H` /
`&O` constants, `= + - * / \ < >`, `MOD`/`AND`/`OR`/`XOR`/`NOT`), stored
numbered-line programs (`NEW`/`RUN`/edit), control flow (`GOTO`, `GOSUB`/`RETURN`,
`FOR`/`NEXT`, `IF`/`THEN`/`ELSE`, `ON … GOTO`/`GOSUB`, `END`/`STOP`, `CONT` +
Ctrl-STOP), `DATA`/`READ`/`RESTORE`, `POKE`/`PEEK`, `PRINT`, `CLEAR`,
`DEF USR`/`USR`, screen-setup verbs (`SCREEN`/`COLOR`/`CLS`/`WIDTH`/`KEY`),
`LIST`, the memory/I-O primitives (`VPOKE`/`VPEEK`, `OUT`/`INP`, `VARPTR`),
multi-character 16-bit integer vars, minimal string vars for `PRINT`, and the
storage statements above.

## Phase 1 record — committed work (all ✅ done)

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — its preamble says so: 'nothing here is outstanding'.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
## Phase 2 — full disk (Disk BASIC integration) — ✅ VERB SURFACE COMPLETE

**Close-out (2026-06-22).** The Disk BASIC verb surface zerobas's current
capabilities can faithfully support is **done and oracle-validated** — sequential
file I/O (`OPEN`/`CLOSE`/`PRINT#`/`INPUT#`/`LINE INPUT#`/`INPUT$`, `MAXFILES`,
`APPEND`), `PRINT USING` (+`PRINT# USING`), file/dir management
(`FILES`/`KILL`/`NAME`/`MERGE`), position/info (`EOF`/`LOF`/`DSKF`), random-access
records (`FIELD`/`GET`/`PUT`/`LSET`/`RSET` + `MKI$`/`CVI`), and `CALL FORMAT` (both
geometries + menu). The whole stack was also proven **host-BIOS-independent** on a
real Philips VG-8020. The in-RAM halves of these verbs now also carry a fast
emulator-free regression (`make unit-test`: `test_tokenise`/`test_field`/
`test_printusing`); the sector-moving halves stay in the openMSX probes.

**Explicitly carried / deferred (not part of "complete"):**
- **Tier-2 provider oracle** (a real MSX-DOS 1 host driving zerobas-disk) — a
  distinct DOS-boot sub-track. **ACTIVE again (2026-06-23):** an earlier "walled by
  policy" call (§8.12) was retracted — it forgot that undocumented disk-ROM entries are
  characterisable by **black-box oracle** (the same discipline that nailed GETDPB), not
  only by published docs. The boot already loads+executes MSXDOS.SYS byte-perfect off
  our `bdos_entry`; the gap is one disk-ROM entry (`$4030`), now under active black-box
  characterisation (oracle built, first contract captured). **Not** writing our own
  MSX-DOS 1 — existing disks drive our clean-room reimplementation of the observed entry
  contract. See below + provider-oracle-scope.md §8.13.
- **`DSKI$` / `DSKO$`** — investigated, **deferred to Phase 3** (obscure CF-3300
  semantics + needs the Phase-3 string heap; see the item below).
- **`MKS$`/`MKD$`/`CVS`/`CVD`** (random-access float conversions) and the float-only
  `PRINT USING` specs — gated on **Phase-3 floating point**.
- **`LOC(#n)`** (unclear sequential semantics) and **`LFILES`** (printer-bound) —
  deferred; observed + documented in PROVENANCE.

A deliberate **charter raise** from loader-stub toward a faithful disk experience.
Chosen as the next phase because it *completes the storage story* the
basic/tape/disk split is built around — a self-contained, oracle-validatable slice
— rather than boiling the ocean on the full language (that stays Phase 3+). The
disk *ROM* (`disk/`) is already complete (FDC + FAT12 + BDOS, read+write,
oracle-confirmed); this phase is the **interpreter-side Disk BASIC integration**.

**Approach — spike first, then decide, then build.** Unlike Phase-1 items the
protocol isn't pinned, so step 0 is a research spike; only after it do we pick the
architecture and write code. Each step is independently oracle-validatable.

### Step 0 — file-channel protocol spike (the gate) — ✅ DONE
      - [x] **read path: `OPEN…FOR INPUT` + `INPUT#` + `LINE INPUT#` + `CLOSE`** —
            DONE (basic/files.asm). EXTEND over the fat.asm sequential reader
            (`fat_io_open`/`fat_io_getbyte`); single channel; string vars only.
            Tokens OPEN=$B0/INPUT=$85/LINE=$AF/CLOSE=$B4 oracle-locked to the
            VG-8020 crunch; `OPEN"HI.TXT"…:LINE INPUT#1,A$:CLOSE#1:PRINT A$` prints
            the file's line byte-for-byte and the **real CF-3300 prints it
            identically** (`disk_probe_fileread.py` differential). See
            basic/PROVENANCE.md §file channel — sequential read.
      - [x] **write path: `OPEN…FOR OUTPUT` + `PRINT#` + `CLOSE`** — DONE
            (basic/files.asm + the PRDEST/`pchar` redirect in basic/print.asm).
            `PRINT#` reuses the screen-PRINT item loop redirected to the channel;
            CLOSE appends the `Ctrl-Z` ($1A) text-EOF marker. Tokens oracle-locked
            (`OUTPUT`→`OUT $9C`+`PUT $B3`, `PRINT#`→$91); write→read-back round-trips
            and the on-disk `OUT.TXT` is **byte-identical to the real CF-3300**
            (`b"hello world\r\n\x1a"`, `disk_probe_filewrite.py` differential). See
            basic/PROVENANCE.md §file channel — sequential write.
      - [ ] 🔴 **`MAXFILES` + the multi-channel table** — **DONE EXCEPT FOR TWO
            OPEN DISK CHANNELS** (measured 2026-08-30, D-OPEN2,
            [`docs/spec-basic-open2.md`](docs/spec-basic-open2.md), 9 DIFF of 13):
            a second concurrent DISK `OPEN` is `Syntax error`. Device+device,
            device+disk and disk+device all WORK, so the table and the ceiling
            are real — it is two open DISK channels that fail, which is what
            fat.asm's single global streaming state predicts. Was marked DONE (basic/files.asm channel
            manager + basic/sysvars.inc FCH_CTX). Retires the single-channel limit:
            up to `FCH_CEIL`(=2) channels open at once, via a **write-back context
            cache** over the UNCHANGED fat.asm (each channel owns a saved
            [state][512-buf] block; the globals hold the active channel; switching
            saves+loads). `MAXFILES` = MAX($CD)+FILES($B7) oracle-locked; default 1;
            bare CLOSE closes all. Two OUTPUT files written **interleaved** produce
            on-disk images **byte-identical to the real CF-3300**
            (`disk_probe_maxfiles.py`). RAM-bounded ceiling (real MSX=15) documented.
            See basic/PROVENANCE.md §MAXFILES.
      - [x] **`OPEN…FOR APPEND`** — DONE (basic/fat.asm `fat_io_append` +
            basic/files.asm OPEN mode parse). Opens an existing file positioned at
            EOF; "APPEND" = APP(ascii)+END($81), already byte-identical (no new
            token). Walks the chain reusing the read primitives, primes the write
            iterator at EOF, and overwrites a trailing Ctrl-Z (CP/M text append).
            On-disk result **byte-identical to the real CF-3300**
            (`disk_probe_append.py`: create "first" + append "second" ->
            `first\r\nsecond\r\n\x1a`). See basic/PROVENANCE.md §OPEN … FOR APPEND.
      - [x] **`INPUT$(n,#f)`** — DONE (basic/strvar.asm `str_eval` INPUT$ branch).
            Reads exactly n raw bytes from channel f as a string (no delimiters;
            cursor advances by n). zerobas's first string-returning function;
            "INPUT$" = INPUT($85)+'$' (no new token). `A$=INPUT$(5,#1)` then
            `INPUT$(6,#1)` on HI.TXT yield "Hello" then " from " **byte-identical to
            the CF-3300** (`disk_probe_inputdollar.py`). STRMAX clamp + keyboard form
            (no `#`) deferred. See basic/PROVENANCE.md §INPUT$.
      - [x] **`PRINT USING`** — DONE (basic/printusing.asm). Formatted output:
            numeric `#` fields (right-justified, `%` overflow, negative sign),
            string fields (`\ \` fixed width, `!` first char, `&` whole), literal
            passthrough, and format reuse when values outrun the template. USING token
            $E4 (oracle-locked). 7 cases incl. `PRINT USING "## ";1;2;3` →
            ` 1  2  3 ` **byte-identical to the real VG-8020** (`basic_probe_printusing.py`).
            This is the COMPLETE feature for zerobas's integer domain; the float-only
            specs (`.` decimal, `^^^^`, `+`/`,`/`**`/`$$`) arrive with Phase-3 floats.
            See PROVENANCE §PRINT USING.
      - [x] **`PRINT# USING`** — DONE (basic/print.asm). The file form: after
            `PRINT #n[,]` the USING token routes into the same ex_print_using formatter
            with PRDEST=1, so the formatted bytes stream to the channel via pchar. On-
            disk round-trip byte-identical to the CF-3300 (disk_probe_printusing_file.py).
            Oracle finding: the CF-3300 (National ROM) supports only `#`/`!` PRINT USING
            fields, not `\..\`/`&` (which the VG-8020 — and zerobas — do); see PROVENANCE.
      - [x] **`MERGE "name"`** — DONE (basic/files.asm `ex_merge`). Reads an ASCII
            (SAVE",A") line-numbered program file and feeds each line through the
            same `dispatch_line` (tokenise + `store_line`) path as a typed line, so
            lines insert/replace into the CURRENT program (kept, unlike LOAD). Token
            $B6 oracle-locked. Build-source-via-PRINT# + MERGE + RUN computes 123
            **identical to the CF-3300** (`disk_probe_merge.py`). ASCII-only (no
            tokenised MERGE). See basic/PROVENANCE.md §MERGE.
      - [x] **`NAME "old" AS "new"`** — DONE (basic/files.asm). Rewrites the dir
            entry's 8.3 name (no FAT change); token $D3 oracle-locked; post-rename
            disk image **byte-identical to the real CF-3300** (`disk_probe_name.py`).
            See PROVENANCE §NAME.
      - [x] **`KILL "name"`** — DONE (basic/files.asm + fat.asm `fat_delete`). Frees
            the FAT chain + marks the dir entry `$E5`; token $D4 oracle-locked; the
            post-KILL disk image is **byte-identical to the real CF-3300**
            (`disk_probe_kill.py`). Single file (no wildcard). See PROVENANCE §KILL.
      - [x] **`FILES`** — DONE (basic/files.asm). Lists the root directory by
            EXTEND over the fat.asm engine (`fat_mount` + directory walk + 8.3 field
            render); width-driven wrap via `CSRX`/`LINLEN`. Token `$B7` oracle-locked
            to the VG-8020 crunch (`basic_probe_crunch.py` case `files`); listing
            **byte-identical to the real CF-3300** at WIDTH 29 and correct at native
            width (`disk_probe_files.py` / `diskbasic_probe_files.py`); LIST detok +
            the host unit-test suite still pass. Divergence: optional `<filespec>`
            pattern parsed-past + ignored (full-dir listing only). See
            basic/PROVENANCE.md §FILES.
      - [x] **`EOF(#n)` + `LOF(#n)`** — DONE (basic/expr.asm `ev_f_ff`). $FF-prefixed
            function tokens ($FF$AB / $FF$AD), oracle-locked; `PRINT LOF(1);EOF(1)`
            after OPEN = `26 0` byte-for-byte vs the real CF-3300, and EOF→-1 once
            the file is exhausted (`disk_probe_eof.py`). See PROVENANCE §EOF / LOF.
      - [x] **`DSKF(d)`** — DONE (basic/expr.asm + fat.asm `fat_count_free`). Free-
            cluster count via a sector-cached FAT scan; $FF$A6 oracle-locked;
            `PRINT DSKF(0)`=707 matches a direct FAT12 count AND the real CF-3300
            (`disk_probe_dskf.py`). See PROVENANCE §DSKF.
      - [ ] **`LOC(#n)`** — deferred: CF-3300 `LOC(1)` returns 26 (file size) both
            before and after a read; sequential-file semantics unclear, so not
            cargo-culted. **`LFILES`** — printer-bound (LPT), no device in zerobas.
            Both observed + documented in PROVENANCE §LOC / LFILES.
- [ ] **Direct sector access — INVESTIGATED, DEFERRED to Phase 3** — `DSKI$` (fn,
      $EA) / `DSKO$` (stmt, $D1). Tokens oracle-confirmed real (VG-8020 crunch), but
      NOT a clean "sector ↔ string" pair, and blocked on three counts:
      1. **Obscure semantics.** Black-box CF-3300: `A$=DSKI$(0,0)` succeeds but
         `LEN(A$)=0` — it does NOT return the sector as the string value (data goes to
         a system buffer, accessed elsewhere); and `DSKO$ 0,0,A$` is a *Syntax error*
         (the 3-arg form is wrong). The real buffer/arg model needs more CF-3300
         reverse-engineering of an arcane, rarely-used verb.
      2. **String model.** A sector is 512 B; an MSX string's length byte maxes at 255;
         zerobas's inline strings cap at STRMAX=32. Representing sector data as a string
         value needs the Phase-3 string engine (heap + real descriptors), not the
         minimal inline store.
      3. **No clean oracle.** The only disk oracle (CF-3300) shows the quirky behavior
         above; the VG-8020 is diskless so can't exercise it functionally.
      Low-value + low-use; revisit once Phase-3 strings exist. (Was assumed a thin
      DSKIO wrapper; the oracle proved otherwise — 2026-06-22.)
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).
      - [x] **`MKI$(n)` + `CVI(s$)`** — DONE (basic/strvar.asm + basic/expr.asm). The
            integer conversion pair: MKI$ packs a 16-bit int into a 2-byte LE string
            ($FF$AE, string result, in str_eval); CVI is the inverse ($FF$A8, numeric
            result with a string arg, in ev_ff_cvi bridging IX↔HL to str_eval).
            `A$=MKI$(258)` + `C$=MKI$(CVI(A$))` write M.DAT = `\x02\x01\x02\x01\x1a`
            **byte-identical to the CF-3300** (`disk_probe_mkicvi.py`). Float siblings
            (MKS$/MKD$/CVS/CVD) need Phase-3 floats — deferred. See PROVENANCE §MKI$/CVI.
      - [x] **`FIELD` + `LSET` + `RSET` (slice 1 of 2)** — DONE (basic/field.asm +
            str_eval/clear_vars/OPEN hooks). RANDOM open (`OPEN"name" AS #n`, no FOR)
            sets up an in-RAM record buffer; FIELD partitions it into named slices (a
            side table, since zerobas stores strings inline — no MS-BASIC descriptor to
            repoint); LSET/RSET store left/right-justified + space-padded; reading a
            fielded var yields its slice (str_eval hook). Tokens oracle-locked (FIELD
            $B1 / LSET $B8 / RSET $B9). `OPEN"R.DAT" AS #1 : FIELD#1,5 AS A$,10 AS B$ :
            LSET A$="HI" : RSET B$="END" : PRINT` → `<HI   |       END>` **byte-
            identical to the CF-3300** (`disk_probe_field.py`). See PROVENANCE
            §FIELD/LSET/RSET.
      - [x] **`GET` + `PUT` (slice 2 of 2)** — DONE (basic/field.asm). Random record
            I/O: `PUT #f,N` writes the record buffer to record N (256-byte records,
            oracle-confirmed via LOF), `GET #f,N` reads it back. Composes the fat.asm
            engine unchanged — the chain walk uses a private `frnd_next` over FWBUF so
            the live record in FSECTOR_BUF survives; PUT read-modify-writes the shared
            512-byte sector (2 records/sector) and extends the cluster chain; the dir
            entry is stamped so data survives CLOSE/reopen. RANDOM open made real
            (`fat_rand_open` opens-or-creates + seeds channel state). Tokens GET $B2 /
            PUT $B3. Write 2 records → CLOSE → reopen → GET back = `<alpha|  bet>` +
            `<gamma|delta>` **byte-identical to the CF-3300** (`disk_probe_getput.py`).
            Divergences: record 1..255, bare GET/PUT default to record 1, no LEN=.
            See PROVENANCE §GET/PUT. **→ sub-phase 2c (random-access) COMPLETE** (the
            float-conversion siblings MKS$/MKD$/CVS/CVD still await Phase-3 floats).
      - [x] **360 KB + the geometry menu** — DONE (basic/format.asm). Added a
            GEOM_360K descriptor (media $FD, 720 sectors, 2 sec/FAT) and a minimal
            `1=360k 2=720k?` prompt (read via the REPL line editor; drive + confirm
            prompts trimmed). do_format reads the chosen descriptor through FMT_DESC —
            geometry-agnostic. Both geometries' BPB + FAT head byte-identical to the
            matching CF-3300 format (360K = "2 sides", 720K = "2 sides double track"),
            and a file round-trips on each fresh disk (disk_probe_format.py).
- `CALL SYSTEM` **[out]** — exit to MSX-DOS = the DOS-boot path (Tier-2 sub-track).
- `CALL CHDRV` etc. **[out]** — Disk BASIC v2/v3 additions, beyond DOS1-class 1.0.

### Carried oracle — Tier-2 provider (DOS1; a distinct DOS-boot sub-track)
The only Phase-2 thread still genuinely open: a real **MSX-DOS 1** filesystem host
(black-box; **DOS1 is the confirmed ceiling**), the only organic `GETDPB` consumer,
driving zerobas-disk end-to-end. Per the circularity finding a real DOS only exists
once a disk ROM loads `MSXDOS.SYS`, so this is gated on building **MSX-DOS-boot
support** in zerobas-disk — a distinct sub-track from the verb surface above. **DOS2**
(Nextor / Sunrise 2.20 / the open MSX-DOS2 kernel) is a future axis, not this phase.

- [ ] **2-Tier2-a — DOS boot (steps 4–7).** Deeper than first scoped: a build attempt
      proved the boot is a **four-step environment hand-off** (MSX2 TH ch.3), not a
      one-call bridge — see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).
      - [x] **a1 — steps 4–5 (boot bridge). DONE + regression-gated.** `boot_disk` in
            INIT reads sector 0 → `$C000`, checks the `$EB`/`$E9` signature, and `CALL
            $C01E` CY-reset; the data-disk `RET NC` fall-through is preserved. **Now
            committed to `disk.asm`** (not reverted): regression-gated on
            `C-BIOS_MSX1_BASIC_DISK` + `test720.dsk` — `disk_probe_files` and
            `disk_probe_bload_disk` both PASS (BASIC+disk boots, byte-identical FILES,
            BLOAD `,R`/plain), and oracle-confirmed on `National_CF-3300_ZEROBASDISK` +
            a DOS disk (`$C01E` reached, `AF=$EBAC` ⇒ A=`$EB`, carry reset).
      - [ ] **a2 — step 6 (the real work): page-0 MSX-DOS environment.** Designed:
            see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.1
            (documented page-0 layout pinned + the step-5→7 RAM-in-page-0 delta
            traced). Order: (1) page RAM into page 0 (slot paging — the hang-prone
            part, validate in isolation); (2) lay the page-0 env per the CP/M-style
            layout (`$0000` warm-boot, `$0005`→a trampoline to our existing
            **`bdos_entry`**, `$0006-7` TPA top, `$0038` int, `$0080` DMA); (3) the
            two-phase `$C01E`. **Reuse:** `bdos_entry` (oracle-validated MSX-DOS-1 FCB
            BDOS) IS the resident BDOS — don't rebuild it. **Open Q (resolve by
            experiment, not by tracing the MS boot code):** does the boot code load
            MSXDOS.SYS via `$0005` BDOS or via direct PHYDIO sector reads?
            **(1) is VALIDATED** (§8.2): the RAM-into-page-0 slot dance works on the live
            Tier-1 machine (`$A8` page-0→slot 3 + `$FFFF` page-0 subslot→0, run from
            page 1, `di`; wrote/read `$A5` at `$0000`, ROM `$F3` restored after).
            **Open Q RESOLVED** (§8.3): the boot loads MSXDOS.SYS by **direct sector
            reads, NOT `$0005` BDOS** (the first BDOS calls come from already-relocated
            high-RAM DOS, not the boot sector) → no resident-BDOS/TPA needed.
            **Real core of step 6 found** (§8.4): with RAM in page 0, `H.PHYD`'s
            `RST 30h`/CALLF breaks (page-0 BIOS gone), so step 6 must stand up a minimal
            RAM-resident inter-slot path. **Advantage:** page 1 stays our ROM, so DSKIO
            is directly `CALL $4010`-able — next build = a tiny `$0030` CALLF shim in RAM
            page 0 + the two-phase `$C01E`, then observe whether `A>` appears.
            **First full build done + reverted** (§8.5): the DOS boot path now RUNS
            (both `$C01E` calls reached, RAM in page 0, code executes in page-0 RAM,
            screen "MSX system version 1.0" not the BASIC fall-through). Two concrete
            gaps remain: **(A) CHARACTERISED (§8.6):** a black-box trace of the *working*
            CF-3300 boot shows it **does** reach standard DSKIO (`$4010`, 5×) via a *full*
            page-0 `JP`-vector table (`$000C`/`$001C`/`$0024`/`$0030`/`$0038`). Our build
            hung at `$1418` *before* the DSKIO call because our minimal env (`$0030` shim +
            `$0038` stub) lacked a vector the boot calls. Fix: lay the fuller vector set
            (shape per TH ch.3, our own RAM targets), disk path via `$0030`→direct `CALL
            $4010` (our ROM stays in page 1). Residual: trap which vector fires at `$1418`
            in the next bridge build. **(B) RESOLVED + VALIDATED:**
            the paging hardcoded "RAM = slot 3-0" (`or $03`/`and $FC`) — broke the C-BIOS
            host; corrected to **derive the RAM slot from page 3's bits** (`$A8`/`$FFFF`
            bits 7-6 → page-0 bits). `page0_ram_in`/`page0_ram_out` are now in `disk.asm`,
            **self-tested on `C-BIOS_MSX1_BASIC_DISK`** (the previously-hanging host):
            `$0000` accepts `$A5` after RAM-in, reads `$F3` after restore, machine running
            (§8.2). Routines committed but uncalled; **step 6 wires them in next.**
            **STEP 6 BUILT + regression-green (§8.7).** The `$0030` CALLF handler (register-
            preserving → direct `CALL $4010`), the `lay_page0_env` JP-vector set
            (`$000C`/`$0014`/`$001C`/`$0024`/`$0030`/`$0038` → our own page-1 handlers),
            and the step-6/7 wiring (`di`→`page0_ram_in`→`lay_page0_env`→`scf`→step-7
            `$C01E`→ data-disk return → `page0_ram_out`→`ei`→BASIC) are in `disk.asm`.
            `disk_probe_files` + `disk_probe_bload_disk` PASS on `C-BIOS_MSX1_BASIC_DISK`
            (step 6 paging runs there: sig `$EB`, `$1E` stub `D0 C9`); `disk_probe_init`
            PASS (`bdos_entry` now `$439F`). a3 trap verified the env is laid correctly at
            step-7 entry — **but REFUTED the §8.4 inter-slot premise** (§8.7): the real
            MSX-DOS boot uses **none** of H.PHYD / DSKIO / our page-0 vectors / our ROM
            header; it expects the standard **disk WORK AREA** (`DRVTBL` + driver slot/entry)
            and, absent it, falls back to a slot scan that wedges on the expanded slot 3.
      - [ ] **a3 — SIZED by black-box differential = charter-level subsystem (§8.8).** A
            clean-room RAM differential (stock CF-3300 vs Tier-1, data disk → BASIC) shows
            the base BIOS sets only `EXPTBL`; the **disk ROM** installs `RAMAD0-3`
            (`83 00 83 83` stock vs **`FF` ours**), the `$F348` disk work-area/DRVTBL JP
            table (into high-RAM `$95xx/$DFxx`), the `$FE/$FF` DOS hook set, per-drive DPBs,
            and the device table — all absent in ours. Those targets are a **resident DOS
            kernel the stock relocates into high RAM**, i.e. the opaque proprietary code the
            clean-room rule forbids. ⇒ DOS-boot = build the disk ROM's full resident DOS
            environment, a multi-slice Phase-2+ effort that abuts the no-disassembly wall.
            **REOPENED + progressing (2026-06-22, §8.9) — §8.8 pessimism refuted.** The boot
            drives our OWN `bdos_entry`, not a rebuilt kernel. **Slice-1 DONE + committed**
            (`f1035a0`): `$F37D` is the disk system's BDOS-call JP vector (the boot `CALL`s it
            with C=$0F Open, DE=FCB "MSXDOS  SYS"); INIT had written a raw word there → the
            `$0038` wedge. INIT now publishes `$F37D` = `JP bdos_entry` (safe — Phase-1.5
            loader no longer reads it). Wedge gone; boot reaches bdos_entry/Open/fat_mount,
            finds MSXDOS.SYS. Regression-green (files+bload_disk+init on C-BIOS; bdos oracle
            PASS via `$F37E`). **Slice-3 (next):** the boot loads MSXDOS.SYS via BDOS **`$27`
            (Random Block Read)**, which `bdos_entry` doesn't implement (returns `$FF`) →
            implement it (DE=FCB, HL=rec count, start=FCB random-record `+33`, recsize `+14`,
            read into DTA), validate via a `$27` case in `disk_probe_bdos.py`, re-trap. The
            whole remaining gap to `A>` is that one BDOS function.
            **Slices 3–4 DONE; gap relocated to disk-ROM entry `$4030` (§8.10/§8.11), then
            mis-declared "walled by policy" (§8.12) — that verdict is RETRACTED (§8.13).** The
            §8.12 wall conflated *no published doc* with *no allowed method*: it forgot the
            project's core discipline, **black-box oracle observation** (how undocumented GETDPB
            was nailed byte-identical). `$4030` is the same kind of undocumented disk-ROM entry,
            characterisable as a black box on the genuine CF-3300 and reimplementable from the
            observed contract — no charter change, and **not** writing our own MSX-DOS 1.
            **Oracle built + first contract captured (2026-06-23, `probes/disk/disk_probe_dosboot_4030.py`):**
            deterministic — `$4030` returns a pointer in `HL` (`$F1C9`→`$DD0E`), preserves
            AF/BC/DE/IX/IY, writes nothing in `$F1xx`; on entry `IX` points at drive A's DPB
            (byte-identical to our CF-3300 GETDPB), confirming the disk-driver context.
            **`$4030` IMPLEMENTED + work-area characterised (§8.13-8.15).** Boot drives our
            BDOS, loads MSXDOS.SYS byte-perfect, consumes the `$4030` pointer; derailed at `$0038`.
            **RAMAD0-3 lever found + fixed (2026-06-23, §8.16; `disk_probe_dosboot_lowstore.py`).**
            §8.15's "work-area-layout" theory was REFUTED by oracle (MSXDOS makes 0 post-`$4030`
            low-storage writes; `$0038→$0C3C`, not the work area). The real lever: the Tier-1 vs
            stock differential showed page 0 = all `$FF` (unmapped slot) → `$0038` `RST 38h` wedge,
            because MSXDOS reads **RAMAD0-3 (`$F341-4`, 84×)** to re-page page-0 RAM and the disk
            ROM's INIT (ours) never set it. `set_ramad` (host-adaptive, `$FF`-gated, C-BIOS-safe)
            now sets it `83 83 83 83` = byte-identical to stock; **page-0 RAM maps and MSXDOS
            installs its BDOS (`$0005→$E106`)** — a real advance. `bdos_entry`→`$43EA`; regression
            green (init/files/bload/dskio). **Next gap PINNED (§8.17):** after RAMAD, MSXDOS.SYS's
            init does **`CALL $F368`** — a fixed disk-work-area **jump table** (`$F368-$F37C`, stock:
            `$F368→JP $DF57`, `$F36B→$DF59`, `$F36E→$DF70`, `$F371→$F327`, `$F374→$F32C`,
            `$F37D→SYSTEM`) the disk ROM builds; ours has only RAMAD + `$F37D`, so `$F368` is `$FF`
            and the call slides through `$FF` (`RST 38h`). (The apparent "interrupt storm" was a
            SYMPTOM of that slide — `int_h` clears the VDP fine, the FDC is idle; §8.16's ISR guess
            was refuted.) See §8.17.
            **`$F368` TABLE BUILT (§8.18, `disk_probe_dosboot_f368.py`).** Profile: only `$F368`
            (32×) + `$F36B` (31×) are called (IX=drive-A DPB); both are **no-ops on this 64K
            machine** (register/flag-transparent, zero mem/FDC/I/O effects — the disk system's
            RAM-segment-switch hooks, no-op without a mapper). `build_wa_table` lays `JP wa_stub`
            (a `RET`) into `$F368-$F37A` (gated like `set_ramad`; `$F37D`=SYSTEM left intact).
            `bdos_entry`→`$43FB`; regression-green. **Result — biggest advance yet:** the slide is
            gone, MSXDOS.SYS runs its init and is caught **executing inside our disk driver**
            (`PC=$431x/$436x`, `SP=$C004`) reading the directory — stack holds `"VOL_ID"`. **New gap
            (next):** a downstream **stack-corruption derail** — MSXDOS reaches `$4010` once with
            garbage args (`Cy=1`, `B=232`, `DE=$E880`) because `SP` points into ASCII data, not a
            stack. See §8.18.
            **ROOT CAUSE FOUND (§8.19) = HIGH-RAM COLLISION.** The derail is a `RST 38h` slide at
            `$8004` reached via a corrupted stack: `SP=$E6FE` points into MSXDOS.SYS's relocated
            kernel jump table at `$E700+`. MSXDOS's kernel sits at `$E1xx-$E7xx` (BDOS `$E106`),
            **overlapping our disk-ROM scratch** (`SECTOR_BUF $E2A0`, `WBUF $E560`, `GETWRK_AREA
            $E780`). The stock avoids it by reserving high RAM (`HIMEM $FC4A=$DF93`, work area
            `$DD0E`); ours never reserves, so MSXDOS relocates up into our scratch → collision.
            **Lever narrowed (§8.20): NOT HIMEM.** Stock BDOS base (`$0005`) = `$D606`, ours =
            `$E106` — differ by exactly `$1000` (4KB). Setting `HIMEM=$DF93` did NOT move the kernel
            (and regressed the boot) → reverted. MSXDOS-1 reads some other top-of-RAM source `$1000`
            higher on our host. See §8.20.
            **CONCRETE LEVER FOUND (§8.21).** A no-disk VG-8020 control confirms our disk ROM does
            **zero** high-RAM reservation (HIMEM `$F380` = the no-disk baseline; stock reserves to
            `$F1BF`/`$DF93`) — the `$1000` is the disk resident footprint we under-reserve. And the
            decisive find: **MSXDOS.SYS reads the `$F348` DRVTBL 208×** after `$4030`, but **ours is
            unbuilt/garbage**, so MSXDOS dispatches disk ops through garbage pointers → the bad jumps
            (the `$8004` slide = a garbage `$95xx`→`$80xx` driver pointer). Stock DRVTBL =
            `87 93df 0edd 95ef..95f1` = slot id | HIMEM top | `$4030` work area | driver-routine
            pointers. **Resume:** build the `$F368`-style `$F348` DRVTBL — slot `$87`, reserved-top +
            `$4030` ptr, driver pointers aimed at OUR `$4010-$401F` entries (never the stock `$95xx`
            kernel); reserve the high RAM alongside; re-trap. This is §8.8's table, now a confirmed
            live dependency — data + pointers to code we have, not a kernel to write. See §8.21.
            **DRVTBL FULLY CHARACTERISED (§8.22, probe `disk_probe_dosboot_drvtbl.py`).** Corrected
            layout: `$95` is the *low* byte — driver pointers are `$EF95/$ED95/$EB95/$F195`, evenly
            `$0200`-spaced and **all above HIMEM `$DF93` in page 3 (always-mapped RAM)**. Decisive
            write-watch: **the disk ROM builds the whole table** (every meaningful write from page 1
            `$453D-$5EAE`; MSXDOS never writes it; reader is one routine at `$0368`, hot field `+5`
            `$EF95`). The pointers are **always-mapped high-RAM trampolines** that CALSLT (slot `$87`)
            into the `$4010` BIOS — needed because under DOS page 1 is the TPA, so `$4xxx` isn't
            directly callable; this IS the `$1000` reservation's purpose. **Build spec:** in INIT,
            under the `$FF` gate — (1) reserve high RAM (lower HIMEM, claim a page-3 block); (2) build
            CALSLT trampolines there, one per driver routine, into our `$4010-$401F`; (3) write `$F348`
            = slot id | reserved-top | `$4030` ptr | trampoline addrs | sentinel. Next micro-step:
            map each trampoline → its `$401x` entry (trap the CALSLT target per pointer), then build.
            **BUILT + COMMITTED (§8.23): `build_drvtbl` in INIT (4 CALLF trampolines @`$E800` +
            the `$F348` DRVTBL), `$FF`-gated, regression-green; bdos_entry `$43FB`→`$4453`.
            VALIDATED CONSUMED** — Tier-1 MSXDOS reads our `$F348` 37× from PC `$0368` (the stock's
            reader). **But NEGATIVE: reserved-top in DRVTBL+1 does NOT move the kernel** — BDOS stays
            `$E106` (stock `$D606`); the §8.19/§8.20 `$1000` collision persists. Derail re-measured:
            the `$0038` wedge is GONE (set_ramad/`$F368`); MSXDOS now re-enables ints (idle in our
            `int_h`) but the main thread runs away to `$FFFF` (98.7% of int samples) — garbage-RET
            from the `$E106` kernel overlapping our `$E2A0-$E780` scratch. **NEXT LEVER: find MSXDOS-1's
            real top-of-RAM source** — trap the stock's kernel-base computation (where it derives
            `$D606`) for the cell/probe it reads, then set it on ours. Strong candidate: a RAM-size
            probe skewed by our ROM's page-2 `$FF` ($8000-$BFFF) vs the stock disk ROM's mapped
            content. (Trampolines built but not yet exercised; their `$401x` mapping unverified until
            the collision clears.) See §8.23.
            **KERNEL LEVER FOUND + FIXED (§8.24, probe `disk_probe_dosboot_ramtop.py`).** Black-box
            differential of the `$0006-7` BDOS-base write: stock `LD ($0006),HL`@`$D7C0` HL=`$D606`
            DE=`$DC80`; Tier-1 same routine @`$E2C0` HL=`$E106` DE=`$E780`. **Invariant DE−HL=`$067A`
            on both** ⇒ `$067A` = kernel size, **DE = kernel TOP = the `$4030` work-area pointer
            (DRVTBL+3)** — so DRVTBL+3 is the lever, NOT DRVTBL+1/HIMEM. (Real gap is `$0B00`, not the
            `$1000` §8.20 mis-arithmetic'd.) **Fix = one equate: `GETWRK_AREA $E780→$DD0E`** (stock
            value); kernel now relocates to **`$D606`, byte-identical to stock**, below our `$E29A`
            scratch. Equate-only, `bdos_entry` stays `$4453`, C-BIOS regression green. **Validated:**
            `final_bdos=c306d6`, `$FFFF`-runaway GONE, boot reads disk heavily through our driver
            (64× `$4030`, 24 open, 37 RDBLK), gets through the MSX banner. **NEXT GAP: a re-init /
            warm-boot spin** — BDOS vector re-published 6× (stock: once); DOS loads but loops before
            `A>`. Characterise what fails between publications (COMMAND.COM load/exec or a disk op
            erroring → warm-boot); trampolines now finally reachable. See §8.24.
            **SPIN ROOT-CAUSED (§8.25, probe `disk_probe_dosboot_reinit.py`).** After a clean
            publication the kernel does `CALL $50A9` (page 1) on BOTH machines (identical regs,
            identical `ppi $A8=$FF` — page-1 slot-3 RAM, NOT corruption). Stock `$50A9` = real
            MSXDOS.SYS loader (boots, publishes once); Tier-1 `$50A9` = **all zeros** → NOP-slide
            crash → warm-boot loop (publishes 6×). No real DSKIO ever fires (crash precedes the first
            sector read). **Root: MSXDOS.SYS's page-1 portion (`$4000+`) was never written to RAM
            during our DOS-boot bridge** — page 1 held our disk ROM during the load, so the upper
            sectors went to ROM / were discarded; the kernel's `$50A9` continuation is empty. The
            page-1 analog of the §8.16 page-0 RAMAD fix. **NEXT: the boot bridge must map page-1 RAM
            (not our ROM) while storing the loaded MSXDOS.SYS**, so `$50A9` holds its loader when the
            kernel calls it. See §8.25.
- [ ] **2-Tier2-b — organic GETDPB.** With DOS up, run a real DOS command (`DIR`/copy)
      and trap `$4016` to prove **real DOS code** consumes our GETDPB + DSKIO + dir/FAT
      — the organic evidence the Tier-0/1 differential could only approximate.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] **2-Tier2-c — regression.** Host-unit-test the sector-0 read + handoff setup;
      pin the `A>` screen in `disk_probe_provider_dosboot.py`.

**Charter note.** This raises the README's loader-stub charter toward "real MSX
BASIC" on the disk axis. That is the intended scope of Phase 2 — a conscious step
up, kept narrow to the disk/file story so it stays validatable.

### Phase 1 close-out — owed oracles (polish, non-blocking)
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).
## Done — Phase 1 (loader-stub BASIC)

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — 'Complete and oracle-validated; kept below as the provenance record'.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
## Phase 3+ — full MSX1 BASIC (active charter)

**Precondition solved — BASIC ROM space (the C-BIOS repack arc, ✅ 2026-07-10).** The
page-1 `basic.rom` was byte-full at 16 KB, so any Phase-3 feature would have hit a hard
wall. The repack arc ([`docs/spec-cbios-repack-tooling.md`](docs/spec-cbios-repack-tooling.md))
broke it: dropping C-BIOS's dead ROM-BASIC placeholder frees `$2812–$3FFF` in page 0,
contiguous below page 1, so the relocated BASIC grows to a **`$2812–$7FFF` ≈ 21.5 KB**
window (+37 %). Ships as one merged 32 KB main ROM
([`zerobas-main-eu.ips`](zerobas-main-eu.ips)/`.bps`, boots end to end via `make
repack-boot`) with the firewall proven in
[`docs/cbios-repack-provenance.md`](docs/cbios-repack-provenance.md). Shipping `basic.rom`
+ the page-1/tape patches are untouched (`ROM_BASE` defaults to `$4000`); the grown image
is the reloc build. Non-EU variants (br/jp) are a documented later add.

Beyond Phase 2's disk axis — the rest of "real MSX BASIC." **Charter raised
2026-07-17 from loader-stub to faithful, full MSX1 BASIC** (see the banner in
[`README.md`](README.md) and [`MISSION.md`](MISSION.md)); this section is the
**active work-face**, no longer aspirational. Several arcs have **concluded on
main** — floating point (F1+F2+F3), the string engine, arrays/`DIM`, math pack,
console `INPUT`, error handling, `SOUND`/`PLAY`/`BEEP`, D-F2-2 int-arg coercion —
each with a standing acceptance gate. The remaining unchecked items below are the
open work; the disk/file story (`OPEN`/`CLOSE`/`PRINT#`/…) already landed in
**Phase 2** above.

- [x] **Direct-mode control flow — ✅ DONE 2026-07-26**, spec + as-built
      [`docs/spec-basic-direct-ctrl.md`](docs/spec-basic-direct-ctrl.md), gate
      [`make direct-ctrl-acceptance`](Makefile) **40/40** vs the VG-8020
      (probe [`probes/basic/basic_probe_direct_ctrl.py`](probes/basic/basic_probe_direct_ctrl.py),
      boot-per-case, 6 groups). `FOR`/`NEXT`, `GOSUB`/`RETURN`, `GOTO`,
      `IF..THEN <line>` and `ON..GOTO` **typed at the prompt** — an execution
      MODE that had **zero** coverage: every earlier loop/trap/graphics gate runs
      its BASIC as a stored program + `RUN`.
      Two defects, and the reported one (`FORI=1TO7:NEXT` → `out of memory`) was
      the milder: `GSP`/`FSP` had exactly one init site (`run_program`), so before
      the first `RUN` they held power-on garbage (**D-DIR-1**); and
      `dispatch_line` ran a typed line with a bare `jp exec`, which walks
      statements but never services the deferred-transfer flags, so a direct
      `GOTO`/`IF..THEN`/`ON..GOTO` was a **silent no-op** (**D-DIR-2**). Fixing
      D-DIR-1 alone would have been *worse* than the bug — a loud ERR 7 traded for
      a `FOR` body silently running zero times.
      As built: a typed line executes as a **virtual line** (`dir_line`, a 4-byte
      **ROM** header whose two words overlap so the link doubles as the `$0000`
      end marker) through the real run loop, so no direct-mode special case exists
      anywhere in the loop; `DIRECTF` is **derived** at `rp_exec` from `CURLINE`'s
      high byte, never carried, because direct mode is a property of the line
      *being run* (a typed `GOSUB` into line 10 reports `Syntax error in 10`, the
      `RETURN` back into the typed line reports a bare `Syntax error` — measured);
      and the control-stack reset moved from `run_prog` into `clear_vars`, whose
      four call sites are exactly the four the reference resets on (cold boot,
      `RUN`, `NEW`, `CLEAR` — and a frame does **not** die at the next prompt).
      **DEFERRED (D-DIR-3):** interrupt traps still do not dispatch in direct
      mode. Before this slice no trap *could* fire at the prompt, and whether the
      reference fires them there is UNMEASURED — so the conservative answer is
      gated in at one RAM load rather than changed as a side effect. Spec §6 names
      the characterization that closes it.
- [ ] **Screen-editor REPL** — real MSX BASIC does not use a sequential prompt
      loop; Enter reads the *current cursor line from VRAM* (not a dedicated
      input buffer), so the user can cursor-up to any visible output, edit it
      in place, and re-enter it. Needs cursor-key handling and VDP line-readback.
      Our `repl.asm` is a deliberate simplification; full replacement is Phase 3.
      📏 **SCOUTED 2026-08-26 (D-EDITSCOUT)**,
      [`docs/spec-basic-editscout.md`](docs/spec-basic-editscout.md) — placement
      only, nothing priced. **The feature is measured, not inferred**: the
      reference's counter payload reads **1 → 2 → 3** as re-entries accumulate,
      and entering from EITHER row of a wrapped line re-executes the whole
      LOGICAL LINE, so the reader must walk back to its start and forward through
      its continuations.
      🟢 **C-BIOS's `CHPUT` ALREADY HONOURS THE CURSOR-MOTION CODES ON THE
      ZEROBAS MACHINE** (`PRINT CHR$(31);CHR$(31);"Z"` moves Z +2 rows on BOTH
      sides), so the OUTPUT half is present and free. What is missing is the
      INPUT half: `read_line`'s `cp 32 / jr c,rl_loop` throws `$1C`–`$1F` away
      before `CHPUT` ever sees them.
      🎯 **THE PER-KEYSTROKE SUB-ROM-CROSSING WORRY IS REFUTED**: the
      per-keystroke path is `CHPUT`, and the novel work is ONE act per Enter —
      `lineedit_tenant`'s exact granularity. The "in-window 0.6–0.9 KB"
      classification in `docs/decision-phase3-space-strategy.md` §3 was signed
      off **2026-07-11, before the sub-ROM tenant architecture existed**; sub
      page 1 has 1622 B free and sub page 0 has 2464 B. ⚠️ **The byte cost is
      still NOT measured**, nor how the reader finds a logical line's START
      (the reference keeps per-row continuation bookkeeping; zerobas has none),
      nor `INS`/`HOME`/`CTRL` keys, and **`CF-3300` was not run**.
      🔴 **THE FIRST RE-ENTRY ROW WAS BLIND BY CONSTRUCTION** — `PRINT"AAA"`
      re-entered reprints `AAA` over the `AAA` already there, so a WORKING
      re-entry leaves the screen byte-identical to none. It read as "no feature".
      The wrong-row control (cursor-up ×1 onto an `Ok` row → `Syntax error`) is
      the only row that saw anything, and it had been written to rule out a
      different hypothesis.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
- [ ] **Editor / program management** — `RENUM`, `AUTO`,
      `TRON`/`TROFF`, `SWAP`, `WAIT`, `FRE`, full `CLEAR` semantics (`ERASE`
      shipped 2026-07-15 with the arrays arc, slice 2; `DELETE <range>` shipped
      2026-08-02 with D-DELETE and **`LIST <range>` the same day with D-LSTRNG**,
      `.` excepted in both — its own item below).
      ⚠️ **THE PAGE-1 WALL WAS 14 B ON 2026-08-06**, not the 82 B D-LSTRNG
      started from, and
      82 B was itself the post-carve figure. Any remaining item here needs a carve
      or an eviction before it needs a design.
      ⚠️ **THAT 14 B IS STALE — THE WALL IS 64 B AT `b51bbbb` (2026-08-19).**
      Stands as written for the date it carried; only the figure has moved
      (D-EVSPDUP's 24-site carve, then D-VPTRDOM's 5 B). The *conclusion* is
      unchanged and the reason is not bytes: this is a BUCKET
      (`TRON`/`TROFF`, `WAIT`, `FRE`, full `CLEAR`), not one slice, and the
      keyword sweep below prices its remainder at **183–268 B** — still well over
      64 B. Re-priced in
      [`docs/repricing-page1-2026-08-19.md`](docs/repricing-page1-2026-08-19.md)
      §3.4/§4.
      ~~(`SWAP` itself is still unimplemented — `SWAP A,B` is a syntax error here,
      where the reference swaps. Its MALFORMED forms already match, via the
      trap-class fix below.)~~
      ✅ **THAT PARENTHETICAL IS STALE — MEASURED FALSE 2026-08-09**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.7): `A=1` / `B=2` / `SWAP A,B` / `PRINT"[";A;B;"]"` reads ` 2  1 ` on
      **all three sides**, against a ` 1  2 ` control with the `SWAP` removed.
      `SWAP` swaps. 🎯 The control is load-bearing: had `SWAP` errored, the
      direct-mode `PRINT` would still have run and printed ` 1  2 `, so
      "swapped" and "did nothing" are only distinguishable because the control
      pins what "did nothing" looks like. The BUCKET stays open — `TRON`/`TROFF`,
      `WAIT`, `FRE`, full `CLEAR` semantics are not re-measured here.
      **All of these are now measured, not estimated** — see the keyword sweep
      item directly below.
      🙋 NEEDS-JOOST — a call that is yours to make (retire / delete).

- [ ] **Keyword-completeness gaps — the measured remainder of MSX1 BASIC.**
      **The coverage denominator now exists** (2026-07-26,
      [`docs/kwsweep-msx1-coverage.md`](docs/kwsweep-msx1-coverage.md), probe
      [`probes/basic/basic_probe_kwsweep.py`](probes/basic/basic_probe_kwsweep.py),
      `make kwsweep`): of **162** MSX1 reserved words, **124 tokenise** and
      **34 are genuinely absent** (38 lack a `kwtable.inc` entry; 3 of those —
      `DEFSNG`/`DEFDBL`/`DEFSTR` — work anyway via `DEF_TOKEN` + literal ASCII,
      and 1 is `INTERVAL`, which needs no token).
      **Why a sweep existed at all:** `TIME` and `TAB(` were both found *by
      accident*, six days apart, with the same silent shape — the word parses as
      an ordinary variable, nothing errors, the program computes the wrong
      answer. `TAB(` was worse: it had been written down as *"Already faithful
      (NO work)"* in
      [`docs/spec-basic-df2-2-intarg-coercion.md`](docs/spec-basic-df2-2-intarg-coercion.md)
      §1.2 because `PRINT TAB(99999)` raises ERR 6 on **both** sides — for
      structurally different reasons (absent `TAB(` ⇒ `TAB` is an *array*, and
      the subscript bound-check yields the same code). **The differential passed
      and the feature did not exist.** That §1.2 claim is doc debt and is
      corrected in this commit.
      - ✅ **SILENT-GAP (was 8) — THE CLASS IS EMPTY (2026-07-27).** The worst
        class: a wrong answer with no error, a live landmine in a user program.
        All eight are now implemented and gated —
        `EQV`/`IMP` (`ef098e9`, 156/156), `TAB(`/`SPC(`/`CSRLIN`/`POS`
        (`99c0f6d`, 67/67), `FRE`/`BIN$` (`2facfc0`, 83/83) — plus `TIME`
        (`2026-07-26`), which was the ninth and which the sweep picked up with
        no edit to the probe. **No MSX1 reserved word silently computes a wrong
        answer.** That was the keyword arc's exit criterion (D-KW-3).
      - ✅ **MISSING (6) — THE CLASS IS EMPTY (2026-07-28).** All five words plus
        D-MISS-1: `LOCATE` · `TRON` · `TROFF` · `MOTOR` landed 2026-07-27, and
        **`SWAP` landed 2026-07-28** once two clone collapses funded it (+45 B
        `fat_rand_*` onto the existing `fatprim_bounce`, +41 B the five TOTAL math
        calls onto one table — neither of them SWAP's own code). Gated by
        `make missing-acceptance` at **214/214 as recorded**.
        `DEF FN`/`FN` stays out — it is an arc, not a slice (D-MC-3).
      - **NO-ORACLE (5).** `MKI$` `MKS$` `MKD$` `CVS` `CVD` — the MK/CV family
        lives in Disk BASIC, so a **diskless** VG-8020 reference measures the
        absence of a disk ROM, not of a language feature. The probe routes these
        to `National_CF-3300`, which does not yet give a readable SCREEN-0
        capture under `omsx_repl`; until it does they report `NO-ORACLE` rather
        than answering from the wrong machine. Blocks nothing —
        `MKS$`/`MKD$`/`CVS`/`CVD` are already deferred under the float pack.
      - **18 crunch-only** — destructive (`DSKO$`, `IPL`), interactive (`AUTO`,
        `INPUT$(n)`), non-terminating (`WAIT`), printer-bound with the known
        unplugged-`LSTOUT` hang hazard (`LPRINT`, `LLIST`, `LPOS`, `LFILES`),
        disk-fixture-dependent (`COPY`, `SET`, `ATTR$`, `DSKI$`, `LOC`), or
        covered elsewhere (`INTERVAL` → the T5 slice probe). These are coverage
        holes **in the probe**, listed in its output with reasons rather than
        silently dropped.
      - ⚠️ **`INPUT$` is the one to watch:** it crunches *identically* to the
        reference (`INPUT` is a keyword and `$` follows), so layer 1 says
        "present" while support is untested — the exact `INTERVAL` shape. Open
        under the **I/O** item above; the sweep has **not** settled it.
      **Scope boundary:** reserved words only. Statement *option* surfaces
      (`SCREEN 3`, `KEY LIST`, argument forms of words that *are* present) are
      not covered — a word can be present and still wrong in its third argument.
      **✅ SLICED + COSTED 2026-07-27** —
      [`docs/decision-kwgaps-slicing.md`](docs/decision-kwgaps-slicing.md),
      **awaiting sign-off** (D-KW-1..3). The sweep was **re-pinned** against a
      clean-built HEAD first (`git=e9843c4`,
      `zerobas-main-eu.rom=05f43b…`→`4ea7a2…`): **every tally unchanged**, so the
      8/6/5 finding was not an artifact of the stale over-ceiling build. All 14
      reference tokens are now **oracle-measured** from Layer 1's own crunch diff
      (table in the coverage doc) rather than read off Table 2.20.
      ⚠️ **The funding premise in the line this replaces was stale AND wrong.**
      Page 1 is no longer 14 B over — it is **375 B free** (low region 5 B) after
      the FAT tenant-shim collapse (`6f8ac0f`, +367 B: thirteen byte-identical
      34 B shims onto one shared body), which answered D-KW-1 "carve first". More importantly the item is not blocked on *funding* but on
      **placement**: `sub.rom` had **≈8 KB free** on 2026-07-26
      (4509 B page-0 + 3497 B page-1)
      and `kwtable.inc` entries + leaf compute already live there, so the only
      number that matters per keyword is its **main-ROM dispatch glue** —
      and `exec_stmt` is a 67-entry linear `cp`/`jp z` chain charging **5 B per
      statement token before it does anything**. Recommended first slice:
      **`EQV`/`IMP` via a table-driven logical layer** — `ev_xor`/`ev_or`/`ev_and`
      are uniform at 34 B each (measured), so one generic 5-entry layer lands both
      words for **≈ 0 net bytes**.

      ✅ **Steps 1, 2 and 4 are DONE and the exit criterion is MET** — the
      SILENT-GAP class is empty (see above). Each slice was funded by collapsing
      a clone group it was itself a member of, and each one's calibration battery
      turned up pre-existing silent divergences nobody was looking for (two per
      slice, three slices running).

      **What remains of this arc, in order:**
      - **The MISSING class (6)** — ✅ **LANDED 2026-07-27 except `SWAP`.**
        `LOCATE` · `TRON`/`TROFF` · `MOTOR` + D-MISS-1 are in and gated
        (163/163 as recorded, 20 expected-divergent, every marker carrying a
        reason). Spec, as-built costs and the two places the spec turned out to
        be WRONG:
        [`docs/spec-basic-missing-class.md`](docs/spec-basic-missing-class.md).
        ✅ **`SWAP` LANDED 2026-07-28** — 183 B (re-measured from clean; the
        split had recorded 186 B), funded by two repack-only clone collapses and
        leaving 44 B banked (SWAP + its dispatch arm + the two operand guards =
        198 B against the 242 B the carves freed). **"Flipping the flag plus one probe line is the whole
        of the wiring" was WRONG**: `SWAP_RESIDENT` guarded only two of the three
        sites the spec claimed — there was no `stmt_table` dispatch arm at all, so
        the first run had all 20 `swap` rows reporting `syntax error`,
        indistinguishable from SWAP being absent. The gate also found that SWAP
        accepted non-name operands (`SWAP A,1` → `Illegal function call` plus
        trailing output, where the reference says `Syntax error`) — fixed with an
        `is_letter` guard at the *handler's own depth*, because sw_operand is
        `call`ed and the abort chain returns into its caller (D-CUR-D).
        ✅ **CHARACTERISED 2026-07-27**,
        [`docs/missing-vg8020-characterization.md`](docs/missing-vg8020-characterization.md),
        probe [`probes/basic/basic_probe_missing.py`](probes/basic/basic_probe_missing.py),
        `make missing-characterize` (`BOOTPC=1` for the confirmation run) —
        175 cases, 8 batteries, every number boot-per-case. **SLICED + COSTED**,
        [`docs/decision-missing-class-slicing.md`](docs/decision-missing-class-slicing.md),
        **awaiting sign-off (D-MC-1..4)**.
        ✅ **D-MC-2 SIGNED OFF 2026-07-27**: D-MISS-1 folds into this slice,
        D-MISS-2 gets its own. ✅ **D-MC-4 O-1 CLOSED** before any clamp was
        written (battery `locrow`, `make missing-characterize ONLY=locrow`,
        18 rows, batched + boot-per-case identical): **`LOCATE`'s row clamps to
        the console's own bottom row**, which moves with `KEY` (reference 22 at
        `KEY ON`, 23 at `KEY OFF`; zerobas 23 in both) — **not** a literal 23 and
        **not** `CRTCNT`, which measures 24 on both machines everywhere. Also
        measured for the spec: the argument domain has **two** error stages
        (`Overflow` past int16, `Illegal function call` outside `0..255`), and
        the five tokens are pinned from the reference's own crunch
        (`LOCATE $D8`, `SWAP $A4`, `TRON $A2`, `TROFF $A3`, `MOTOR $CE`).
        📋 **SPEC WRITTEN, awaiting sign-off (S-MC-1..5)**:
        [`docs/spec-basic-missing-class.md`](docs/spec-basic-missing-class.md)
        — 300–420 B against 420 B free, proposed **repack-only** so the lean
        cart stays byte-identical, ordered cheapest-first
        (`MOTOR` → `TRON`/`TROFF` → D-MISS-1 → `LOCATE` → `SWAP`).
        ✅ **D-MC-1 SIGNED OFF + D-KW-2 LANDED 2026-07-27**: the `exec_stmt`
        dispatch table replaced the 69-entry `cp`/`jp z` chain, **page-1 free
        311 B → 420 B (+109 B)**, dispatch block 377 B → 268 B, and the
        per-token cost is now 3 B instead of 5 B. Gated by
        [`tests/test_stmt_dispatch.py`](tests/test_stmt_dispatch.py) in
        `make unit-test`: **all 121 entries** (52 lean + 69 repack) reach the
        handler the pre-refactor chain sent them to, plus the fallthrough paths.
        ⚠️ It moves the **LEAN** cart too (shared code) — `LEAN_SHA256` updated
        deliberately in the same commit, as `tools/check_reloc.py` requires, and
        lean is gated per-entry exactly like repack. **The first version of that
        gate was green and worthless** — it read its expectations from the table
        under test, and passed with `PRINT` deleted and `CLS` re-pointed; the
        fix was an expectation recovered from the pre-refactor chain in git.
        **The measurement changed the plan: the class does NOT fit.** The
        roadmap costed it as dispatch glue only, on the premise that bodies live
        in `sub.rom`; but four of the five touch interpreter-core state (cursor,
        variable table, line executor) and are real statements. Measured against
        whole-statement spans already in the tree (`ex_color` = **100 B** for the
        same 3-optional-argument parse shape, with no bound check and no clamp),
        the five come to **300–405 B + 25 B glue against 311 B free**. So
        **D-KW-2 is now a prerequisite, not an option** — exactly as this item
        predicted. Its saving is re-measured on the current tree and confirms the
        estimate: 69 entries, 345 B of chain → 223–231 B of table, **−114…−122 B**.
        Surface highlights the spec turns on: `LOCATE`'s bound is
        **`WIDTH`-relative** and all three arguments are byte-domain-then-clamped
        (`0,255` accepted, `0,256` → `Illegal function call`); `SWAP` requires
        **exact type equality** (`%`≠`!`≠`#`), and its **second** operand must
        already exist while the first may be created; `TRON` traces per **LINE**,
        never in direct mode, survives `RUN` but not `NEW`; `MOTOR` is three
        forms and everything else is `Syntax error` — and
        [`tape/tape.asm:175`](tape/tape.asm:175) **already implements `STMOTR`
        (`$00F3`)** with the matching convention, so its body is a parse and a
        `call`.
      - **`DEF FN`/`FN`** — ⚠️ **THE FILED PRICE IS PART MEASURED AND PART
        REFUTED, 2026-08-22**, by
        [`docs/deffn-scout-2026-08-22.md`](docs/deffn-scout-2026-08-22.md)
        (`scratchpad/deffn_scout.py` + `.out`, four rounds, both references
        agreeing on every row). It read *"an arc, not a slice (200–400 B): a
        definition table, argument binding, re-entrant evaluation"*.
        ❌ **NO DEFINITION TABLE EXISTS IN THE CRUNCH.** `FN` is ONE token,
        **`$DE`** — the byte immediately after `USR`'s `$DD`, whose statement
        (`ex_def`) and function (`ev_f_usr`) paths both already ship — and the
        NAME is stored as plain ASCII after it, arbitrary length, read at run
        time like any identifier. Here the same line crunches `46 4E` ("FN" as
        text), one byte longer per occurrence, which is why `DEF` reaches
        `stmt_error`; `basic/usr.asm`'s own comment already names the hook.
        ✅ **`ERR 18` AND ITS MESSAGE ALREADY SHIP** (`err_msgtab` entry 18,
        `sub/errmsg.asm` `em_undef_fn`).
        ✅ **RE-ENTRANT EVALUATION IS CONFIRMED**: direct recursion is **ERR 7**
        on both references, i.e. it runs the stack out rather than refusing.
        🔴 **AND THE BINDING IS DEARER THAN FILED.** `X=5:DEF FNA(X)=X+1:
        Y=FNA(2)` leaves **X = 5** on both references — the formal is SAVED AND
        RESTORED, not bound through the variable table the way classic MS BASIC
        does. The surface is also wider: **0, 1 and 2 parameters all legal**
        (`DEF FNA=7` → 7; `DEF FNA(X,Y)=X+Y` → 5), string-typed forms work
        (`DEF FNA$(X$)=X$+"!"` → `hi!`), redefinition takes the last, and FN
        calling FN works.
        🔴 **TWO ROWS ARE A SILENT WRONG ANSWER HERE**: `FNZ(1)` undefined, and a
        `DEF` on a later unexecuted line, are **ERR 18** on both references and
        read **`0`** here.
        💰 **NO TOTAL IS CLAIMED** — nothing has been assembled, and a size from
        arithmetic is not a measurement. ⚠️ It is RESIDENT wherever it lands:
        `FN` evaluation must call `eval`, which is main page 1, and no sub-ROM
        tenant can reach main page 1. **Read both walls from `make basic-reloc`
        at the time.**
        ⚠️ **AND THE SCOUT'S OWN HEADLINE IS NOW REFUTED, 2026-08-22**, by
        [`docs/deffn-design-2026-08-22.md`](docs/deffn-design-2026-08-22.md)
        (rounds 5–10, `scratchpad/deffn_round5.out` … `deffn_round10.out`,
        **82 rows, both references agreeing on every scored one**).
        ❌ **THERE IS NO SAVE AND NO RESTORE.** The scout read *"the formal is
        SAVED AND RESTORED … that is the fact the design turns on"*; the
        variable is **never written**. `X=5:P=VARPTR(X):DEF FNA(X)=PEEK(P)` →
        **5**, and `DEF FNA(X)=VARPTR(X)-P` → **30327, not 0**: the formal is a
        **SHADOW CELL that only the defining function's own body sees**
        (`DEF FNB(Y)=X` called from inside `FNA(X)`'s body reads the GLOBAL).
        Nothing has to be unwound, which is also why `X` survives a body that
        RAISES. 🔴 The round-8 row built to prove the opposite (`PEEK(VARPTR(X))`
        → 2) **agreed for the wrong reason** — `VARPTR` inside the body resolves
        the name the same way the body does.
        🎯 **THE CEILING IS A DIVISION, NOT A RULE**: 9 formals legal / 10 →
        **ERR 5 at the call**, and the reference's shadow reads `$F6EB`, i.e.
        3 B into a 100-byte block; a slot shaped like a variable entry is 11 B;
        100/11 = 9.
        🎯 **`DEF FN` DOES NOT PARSE ITS BODY** — `DEF FNA(X)=X+*2` and even
        `DEF FNA(X) X+1` (no `=`) are accepted; the ONLY DEF-time check is that
        a letter follows `FN`. The skip to end-of-statement is token-aware
        (`DEF FNA$(X$)=X$+":Q"` → `a:Q`), i.e. `if_skip_to_else`'s shape with
        `COLON`.
        🎯 **`DEF FN` IN DIRECT MODE IS `Illegal direct` (ERR 12)**, pinned by
        two controls (`DEF USR` and a direct `LET` in the same position are
        both fine). ✅ ERR 12's message already ships.
        🎯 **`CLEAR` ERASES A DEFINITION** and `A`/`FNA` coexist — so the
        definition lives in the VARIABLE TABLE under a key no variable can
        make (bit 7 of `name0`), needing **no new table**:
        `var_alloc_or_find(BC,2)` already allocates a typed 2-byte entry and
        2 B is exactly a text pointer.
        📏 **GATED**: `make deffn-acceptance` (`probes/basic/basic_probe_deffn.py`,
        82 rows + 3 claim rows). At `84e080c`: **8 of 8 positive controls PASS,
        67 of 69 subject rows divergent** — red by design until the verb ships;
        `make deffn-strict` is the target that flips.
        🔴 **SIX ROWS ARE A SILENT WRONG ANSWER, NOT TWO** (`b.undef`,
        `b.forward`, `o.undefarg`, `o.ifnot`, `d.def`, `d.defrun`): an undefined
        `FN<name>(…)` parses as a subscripted array reference and reads **`0`**.
        🔴 **AND THE TWO GREEN SUBJECT ROWS ARE VACUOUS** — `o.twofault` /
        `o.badname` want `ERR 2 AT 20` and so do 44 of the 69, because this tree
        answers `Syntax error` to EVERY `DEF FN` line. The probe detects the
        blanket and prints `GREEN BUT VACUOUS` beside them.
        💰 **STILL NOT LANDED, AND NOW FOR A MEASURED REASON.** Walls at
        `84e080c`, clean, 2026-08-22: **main page 1 = 4 B, main page-0 low =
        46 B** (sub p0 3075 B, sub p1 1624 B). The draft was assembled far
        enough to hit a second obstacle and then REVERTED (the tree is
        byte-identical): 🔴 **the RAM window the 100-byte parameter area needed
        IS NOT FREE, AND `basic/sysvars.inc` SAID IT WAS** — *"376 B spare"*
        below `$E560`, while `GFX_PSTK`/`GFX_DBUF` have sat at `$E3F2` (256 B)
        since G5. **10 bytes are actually free there.** That comment is FIXED
        (conclusion inverted, 0 ROM bytes), as is `basic/vars.asm`'s header
        filing `var_find`/`var_get_key`/`var_set_key` as an available carve —
        R1 took them three weeks ago.
        💰 **THE FUNDING SURVEY IS MEASURED**:
        `scratchpad/dupspan_sweep.py` (calibrated with a planted pair, prints
        its 1467-span denominator) finds ~150–190 B of byte-identical spans on
        the D-PAINTBORD `gfx_absent equ gfx_err5` precedent — the biggest being
        **8 copies of `ld a,5 / jp raise_error` (35 B)** and **6 of `ld a,2 /
        jp raise_error` (25 B)**. 🔴 Every row is a CANDIDATE, not a verdict:
        some sites are FALLTHROUGH targets (`sw_illegal` recovers 2 B, not 5)
        and seven are reached by `jr` (1 B each to widen). **DEF FN is an arc
        with a funding slice in front of it — but for a different and now
        measured reason than the filed one.**
      - **The `CLEAR` string-pool partition** — ✅ **LANDED 2026-07-29, 51/51
        gated, falsified.** Opened by the `BIN$`/`FRE` slice (D-BF-A(c)):
        zerobas had ONE free gap where the reference has TWO pools, and
        `CLEAR`'s string-space argument was evaluated and discarded. The six
        recorded-not-gated `FRE` rows are back in a gate.
        [`docs/spec-basic-clearpool.md`](docs/spec-basic-clearpool.md),
        [`docs/clearpool-vg8020-characterization.md`](docs/clearpool-vg8020-characterization.md),
        [`docs/decision-clearpool-funding.md`](docs/decision-clearpool-funding.md),
        `make clearpool-acceptance` (57 rows, twelve batteries). Baseline 6/51.
        FUNDED by promoting `fld_lookup` to a page-0 sub-ROM tenant
        (`sub/fldlook.asm`, index 12 — **the last page-0 index that fits before
        the fixed `$0038` vector**): page 1 3 B → 41 B free.
        ⚠️ **THREE THINGS THE SPEC DID NOT ANTICIPATE, all found by measuring.**
        (1) `FRE(n)` needed its own handler — both forms shared op 15 because
        there was one gap, and left alone `FRE(0)` reads 200 at boot (the
        probe's `ctl-fre0` CONTROL catches it). (2) **A sized pool measures the
        PEAK, and zerobas's peak was 3×**: `A$=STRING$(100,"A")` charged 300
        (the `STRING$` temp, `str_set_key`'s H1 snapshot *of that temp*, and the
        variable's body) where the reference charges 100 — and **`FRE("")` HID
        it**, because FRE GCs first, so the resting number looked right while
        `CLEAR 100 : A$=STRING$(100,"A")` raised ERR 14. Fixed by skipping the
        redundant snapshot for a source that is already a temp, and by having
        `sh_var_store` **adopt** a temp's body instead of copying it.
        (3) ERR 14 cost **one byte** — a different FPERR code, not a different
        code path. Also: **`oos-vs-oom` was measuring two claims at once** and
        was SPLIT rather than silenced; the six ungated rows are ungated for
        three different reasons and the battery names (`rep`/`share`/`arr`)
        carry which.
        The model is a **single moving boundary, not a second
        allocator** — `CLEAR 200`→`FRE(0)`=28815 and `CLEAR 4000`→25015, a
        difference of **exactly 3800**, so the pool is carved from the same RAM.
        The pools are independent: the equal-depth `FRE(0)` delta across
        `A$=STRING$(100,"A")` is **6 on the reference at both 100 and 200
        chars** (the entry only) against zerobas's 106 and 206.
        `CLEAR n` sizes the pool to exactly n; the default is 200 but a **bare
        `CLEAR` KEEPS the current size** (`CLEAR 500:CLEAR` → 500, and so do
        `NEW`/`RUN`/`CLEAR ,himem`); **`B$=A$` COPIES** the body; a dead body is
        reclaimed and a pure temp fully given back; **`Out of string space`
        (ERR 14) is real and the failed allocation is ROLLED BACK**; and
        `CLEAR -1`/`32768`/`"200"` raise IFC/Overflow/Type mismatch where
        zerobas raises **nothing**. ERR 14 is currently a **hole** in
        `err_msgtab` pointing at `err_unprintable`, exactly as ERR 24 was.
        ✅ **S-CLP-1 the carve, S-CLP-2 derive-don't-store, S-CLP-3 the 200-byte
        default, S-CLP-4 the stored literal and S-CLP-5 body sharing are all
        answered — see the spec's §7.** S-CLP-4 is the one whose ANSWER moved
        it: a stored-program literal costs the pool **nothing** (measured, and a
        25-char literal still costs nothing, so it is zero and not slack),
        because the reference points the descriptor at the program text — but
        matching that needs storing by REFERENCE, which is S-CLP-5's scope, not
        a `heap_alloc` change as the question assumed.
        ⚠️ **S-CLP-3 was the user-visible one**: the 200-byte default means
        programs that used to have ~15 KB of string space now get 200 unless
        they say otherwise. The full acceptance corpus was re-run, not just this
        slice's gate.
      ⛔ BLOCKED — neither of us can start it now (needs a fixture).

- [ ] **`LOAD"CAS:"` ACCEPTS A TOKENISED TAPE; the reference does not return.**
      Found 2026-08-03 by D-DOTGAPS (§1.2). With only a $D3 file on the tape the
      VG-8020 printed no `Found:` and no error and sat there — it searches past
      a non-ASCII header to the end of the tape and waits. zerobas answers, via
      the 3-way header dispatch in [`basic/cload.asm`](basic/cload.asm).
      ⚠️ **NO ROW CAN CARRY THIS**: the faithful behaviour is a HANG, and a row
      that hangs one side gates nothing (the same reason `kwgz-`'s AUTO/LLIST
      rows are side-locked). Filed for the judgement call — bug-for-bug fidelity
      here costs a working feature — not for a fix.
      ⚠️ **CONSIDERED AND NOT RE-MEASURED, 2026-08-09** — NOT MEASURABLE THIS
      WAY, for the reason the entry gives itself: the faithful behaviour is a
      HANG, and `omsx_repl` raises `SystemExit` at its 240 s cap, so such a row
      does not degrade a run, it kills it. Recorded in
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §5 so the skip is a decision and not an omission.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **A LINE STORE IS BOUNDED BY THE CONSTANT `TXTMAX`, NOT BY HIMEM.**
      Found 2026-08-03 by D-DOTGAPS (§4.2/§6 D4). After
      `CLEAR 300,TXTTAB+1000` both references have **148** free bytes and refuse
      a 32-byte line with `Out of memory`; zerobas has **646**, stores it, and
      prints nothing — `CLEAR`'s HIMEM argument does not reach the store check
      at [`sub/lineedit.asm:139`](sub/lineedit.asm:139), which compares
      `PRGEND + size` against a fixed `$BB00`.
      💰 **SCOUTED 2026-08-20 (not priced, not opened).** The right ceiling
      already exists and is already reachable — the obstacle is neither the
      arithmetic nor the bytes, it is that the two ends are in different
      tenants.
      * The bound wanted is the VARIABLE-region ceiling, `min(HIMEM,TXTMAX) −
        POOLSIZE − MAXF×FCH_CTXSZ`, which is exactly
        [`strheap_varceil`](sub/strheap.asm) — derived, never stored, so it is
        current by construction and `CLEAR ,himem` falls out for free.
      * 🎯 **NO NEW SUB-ROM OP IS NEEDED.** `sh_chan_addr` (op 18) answers
        `strheap_varceil() + (ch−1)×FCH_CTXSZ`, so **channel 1 IS the varceil**;
        `basic/files.asm`'s `fch_ctx_addr` is the existing main-ROM wrapper and
        returns it in HL.
      * 🔴 **THE OBSTACLE IS THE TENANT SPLIT, AND IT IS THE WHOLE COST.**
        `le_store` is in `lineedit_tenant` (sub **page 1**); `strheap_engine` is
        sub **page 0**. A tenant cannot call across, so the ceiling has to be
        fetched by the MAIN-ROM store head (`dl_store`, `basic/program.asm`)
        before it marshals, and published in a RAM cell beside `SL_NUM`/
        `SL_TOK`. Shape: main ROM ≈ a `ld a,1` + `call fch_ctx_addr` + a store;
        sub page 1 **+1 B** (`ld de,TXTMAX` → `ld de,(cell)`).
      * ⚠️ **UNVERIFIED, AND IT IS THE FIRST THING TO CHECK**: `sh_chan_addr` sits
        behind an assembly-time `IF` in `sub/strheap.asm`, so a build without
        D-FCH may not have it. Read the guard before believing the 7-byte shape
        [[a-filed-blocker-can-name-the-wrong-obstacle]].
      * ⚠️ And the rule itself is UNMEASURED beyond the three rows below: what
        the references do when the program grows into the variables *while
        variables exist* is a different question from the empty-program case
        these rows drive.
      ✅ **RE-MEASURED 2026-08-20 AT `ef50f4c` — STILL LIVE, BYTE FOR BYTE**, all
      three rows and all three sides unchanged from the 2026-08-09 reading
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.8 and its §7 addendum): ` 148 ` / ` 148 ` / ` 646 ` free, the 32-byte
      line refused by both references and stored here, `99 REM Z` green on all
      three as the control. **Pinned** as `crf-oomsay` /
      `crf-oomlst`.
      🔴 **AND IT IS WHY D-DOTGAPS' OWN RULE HAS NO EMULATOR GATE.** No typed row
      can reach the OOM path on this side, so `crf-oom` agrees at ` 20  0 ` for
      the wrong reason (a *successful* store writing the same number the
      references write on a *refusal*), and R-DOT3a′ is gated by
      [`tests/test_program.py`](tests/test_program.py) alone. Fixing this bound
      would give that rule a real row.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, both numbers exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.8): after `CLEAR 300,TXTTAB+1000`, `FRE(0)` reads ` 148 ` on both
      references and ` 646 ` here, and the 32-byte line the references refuse is
      LISTED here beside the `99 REM Z` that fits.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **README "Limitations (this slice)" IS STALE** — pre-existing doc debt, FLAGGED
      2026-07-29 by S3 of the lean-cart retirement, which deliberately did not fix it
      (out of scope; S3 was a byte-identical mechanical edit plus its own doc sweep).
      [`README.md:291`](README.md:291) describes an early game-loader-scoped slice, not
      today's BASIC. Measured false claims: it lists **`ON … GOTO` as "still out"**
      (it is implemented — `ON_TOKEN` → `ex_on` in `stmt_table`, gated by
      `tests/test_stmt_dispatch.py`, and `tests/test_control_flow.py` exercises the
      branch), and it says **"variables are single-letter integers (`A`–`Z`); no
      strings, arrays, or multi-character names"** and "no `/`, no string ops", all of
      which predate the string engine, the float pack and the array engine.
      A warning banner is in place so a reader is not misled, but the section needs
      rewriting against the CHARTER (faithful full MSX1 BASIC), not patching
      claim-by-claim. **Check the neighbouring prose too** — the same slice-era framing
      likely leaks into the sections around it.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (hand-corrected: the charter it contradicts is already settled).

- [ ] **REGIONALISE THE REPACK BUILD** (filed 2026-07-29, S2 of the lean
      retirement — user answer B: "note it, revisit later"). The shipped BASIC
      patch `zerobas-main-eu.ips/.bps` is **EU-only by construction**:
      [`tools/build_repacked_cbios.py`](tools/build_repacked_cbios.py) applies
      `cbios-repack/eu-drop-statements.patch` and reads
      `derived/bin/cbios_main_msx1_eu.rom`. The retired lean splice was a page-1
      overlay and so was region-universal — `make machines` used to write a
      `_BASIC`/`_BASIC_DISK` pair for all four MSX1 C-BIOS regions (intl / BR /
      EU / JP) and now writes one EU pair. **This is a real coverage loss, on
      record rather than silently absorbed.** The `_TAPE` machines carry no BASIC
      and stay region-universal, so the tape corpus is unaffected. Judged nominal
      for now: these are C-BIOS *region* variants, not hardware the project
      targets, and the CF-3300 oracle plus every standing gate already run
      EU-only. Revisit if a BR/JP user turns up, or when the repack tooling is
      next opened. Measured: [`docs/spec-lean-retire-s2-switch.md`](docs/spec-lean-retire-s2-switch.md) §2.1.
      🙋 NEEDS-JOOST — a call that is yours to make (retire / delete).

- [ ] **SLIM THE FILE-CHANNEL CONTEXT toward the reference** — ✅ **MEASURED
      2026-07-29; awaiting spec sign-off.**
      [`docs/chancost-cf3300-characterization.md`](docs/chancost-cf3300-characterization.md),
      probe [`probes/disk/diskbasic_probe_chancost.py`](probes/disk/diskbasic_probe_chancost.py)
      (boot-per-case, both machines, reference answers self-checked for drift).
      🔴 **THE ITEM'S OWN CAVEAT IS REFUTED.** It said 267 "cannot be the goal
      for a channel doing FAT12 I/O" because it came from a diskless VG-8020.
      The disk-capable **CF-3300 charges exactly the same 267 B** — linear with
      no intercept across `MAXFILES` 0/1/2/3/4/8/15, non-adjacent points on the
      same slope. **267 IS a valid target.**
      Also measured: the ceiling is **exactly 15** (not "at least"), `16`/`255`
      raise **`Illegal function call`**; the buffers are charged at **`MAXFILES`
      time, not `OPEN` time**; the **string pool is untouched** (`FRE("")`=200
      either side); and `TXTTAB`/`HIMEM` are **constant**, so the carve is
      downward from the top — `FRE(0)` counts to **SP**, which is what moves.
      **267 < 512, so the sector buffer is NOT in it** — the reference shape is
      one *shared* sector buffer plus a small per-channel block, exactly as
      hypothesized.
      **zerobas, measured the same way:** `FRE(0)` = 13875 at `MAXFILES` 0, 1
      AND 2 — **it does not move at all**, because `FCH_CTX $EA00..$EE63` is
      reserved statically whether or not a channel is open. Its 512 B per
      channel is **purely a save copy** of the single global `FSECTOR_BUF`
      (`fch_save_active`/`fch_load_ctx`, [`basic/files.asm:914`](basic/files.asm:914));
      the reference gets the same effect by treating the shared buffer as a
      **cache** — flush on switch away, re-read on switch back.
      **Sizing:** drop the save copy → at `FCH_CEIL=2` the table falls 1124 B →
      100 B (**frees 1024 B**); at `FCH_CEIL=15` (full reference parity) it is
      750 B, still **374 B less than today**.
      ⚠️ **THE ROM COST IS NOT MEASURED** — flush-and-re-read instead of memcpy
      is an unknown-size change to `files.asm` against the **9 B** free low /
      **6 B** free page 1 of 2026-07-29. Estimating it from reading code would be a hypothesis, not a
      measurement (D-ARR-C §7a).
      ⚠️ **THOSE TWO FIGURES ARE STALE — 5 B low / 64 B page 1 at `b51bbbb`
      (2026-08-19)**; they stand as taken for their date. 🎯 **The caveat itself
      is UNCHANGED and is the live blocker:** the ROM cost is still not measured,
      so this is not a decline the wall can lift in either direction — and note
      the LOW region went the other way (9 B → **5 B**), which is where a
      `files.asm` change is most likely to land.
      [`docs/repricing-page1-2026-08-19.md`](docs/repricing-page1-2026-08-19.md)
      §4.
      ⚠️ **FREEING PAGE 3 DOES NOT BY ITSELF RETURN PROGRAM SPACE.** `TXTMAX`
      rises only if a page-2 buffer MOVES into the freed window: `TOKBUF`
      (576 B @ `$B700`) and the input line buffer are movable; `DETOKBUF`
      (1280 B @ `$BB00`) does not fit in 1024 B. So the D-LINEMAX refund is
      **partial at best**, not the full 1792 B.
      **FORK RESOLVED (user, 2026-07-29): the fully faithful DYNAMIC mechanism**
      — carve channel blocks out of the pool at `MAXFILES` time, ceiling 15,
      nothing charged for channels a program never asks for, `FRE(0)` moves.
      Spec written: [`docs/spec-basic-filechan-alloc.md`](docs/spec-basic-filechan-alloc.md)
      (**D-FCH**), ⚠️ **awaiting sign-off — no code written.**
      Semantics + error codes now MEASURED too (characterization §9/§10):
      `MAXFILES` **CLEARs variables UNCONDITIONALLY**, even when the value does
      not change (the `sem_same` row is what pins that — the natural reading
      "clears only when it reallocates" is wrong), **closes all channels**, and
      **keeps** the `CLEAR`-set string-pool size. Codes: `MAXFILES=16` → **ERR
      5**, bad channel number → **ERR 52 `Bad file number`**, touching a closed
      channel → **ERR 59 `File not OPEN`**; zerobas raises **ERR 2** for the
      first two and returns **−1** for the third. The whole disk error block
      50–65 is mapped black-box via `ERROR n`.
      ⚠️ **`Bad file number` is NOT trappable on the reference** — with a
      handler installed the other two trap cleanly but this one prints
      `Bad file number in 30` and never reaches it. Pin it, don't "fix" it.
      ⚠️ [`basic/files.asm:332`](basic/files.asm:332) **already comments
      `bad file number`** and jumps to `stmt_error`; six sites do the same.
      ⚠️ **`err_msgtab` stops at 25** — reaching 59 densely is ~100 B against
      9 B/6 B free. S-FCH-2 offers a sparse side-table instead.
      **S-FCH-1 ✅ BUILT + GATED 2026-07-29.** The shared-cache change costs
      **5 B of main page 1, 0 B of low region — NO CARVE** (fits the existing
      6 B with 1 B spare) and frees **1024 B** of page 3 (`FCH_CTX` 1124 → 100).
      The per-channel 512 B save copy is gone: `fat_detach_channel` flushes the
      dirty partial sector in place and `fat_restage_channel` reads it back
      (both sub-ROM, rows 19/20), so `FSECTOR_BUF` is a real write-back cache.
      🔴 **THE COST WAS SITING, NOT SUBSTANCE, AND ONLY BUILDING IT SHOWED
      THAT: 43 B → 9 B → 5 B.** Resident, the detach half cost 43 B (37 over) —
      a carve scouted from that number would have been scouted for a
      requirement **8× too big**. It calls `fat_flush_data_sector`, which was
      ALREADY a sub-ROM primitive, so keeping its caller resident bought
      nothing. The last 4 B came from hoisting ONE IX guard into `fch_select`
      instead of two inside save/load.
      ⚠️ **The IX contract was a live hazard**: those routines had no CALSLT
      before and promise IX/IY survive because `EOF`/`LOF`/`INPUT$` hold their
      token cursor there.
      ⚠️ **The gate was FALSIFIED**: stubbing `fat_restage_channel` to `ret`
      makes `disk_probe_maxfiles`'s interleaved two-channel write return **B's
      bytes in A.TXT** and fail both functionally and vs the CF-3300.
      ⚠️ **Repack-only** — ungated it overran the byte-full lean cart's `$8000`
      ceiling outright; the cart keeps the memcpy path, byte-identical.
      ⚠️ **Left open:** `fch_save_active` ignores the detach's `Cy`. A channel
      switch could never fail before and now can (disk full mid-flush);
      propagating it needs a disposition at every `fch_select` caller.
      **§3.3 ✅ BUILT 2026-07-29 — THE 1024 B IS NOW SPENT, AND IT IS PROGRAM
      SPACE: `FRE(0)` 13875 → 14899** (measured). `LINEBUF` `$BA00`→`$EB00`
      (page-aligned, cursor idiom untouched), `TOKBUF` `$B700`→`$EC00`,
      `TXTMAX` `$B700`→`$BB00`. **Zero ROM cost** — address constants only, so
      page 1 stayed at the 1 B free it had on 2026-07-29 and the lean cart
      stayed byte-identical.
      Usability CHECKED, not assumed: `CLEAR 200 : DIM A%(7000)` (14002 B, over
      the old 13875) now succeeds with **both ends written and read back**
      (11/22), 889 B still free. A `DIM` that merely succeeds witnesses nothing.
      ⚠️ **`TXTMAX` IS NOW BOUNDED BY `DETOKBUF`, NOT BY FREE RAM** — at 1280 B
      it does not fit the 1024 B window, so `$BB00` is the stop until DETOKBUF
      is dealt with. Of D-LINEMAX's 1792 B, **1024 recovered, 768 still charged**.
      ✅ The ~12 KB string workload D-LINEMAX cost the suite is affordable again
      (the array rows' shrunken payloads were deliberately LEFT — restoring them
      is a separate call, not a silent side effect of a RAM change).
      **§3.2 ✅ BUILT + GATED 2026-07-29 — `MAXFILES` IS NOW FAITHFUL IN
      MECHANISM.** The channel table is CARVED OUT OF THE POOL at `MAXFILES`
      time, immediately below the string-pool floor
      (`min(HIMEM,TXTMAX) − POOLSIZE − MAXF×50`), so **`FRE(0)` moves −50 per
      channel** (14899 at `MAXFILES=0` → 14149 at 15), `FRE("")` stays 200,
      `OPEN` costs zero further, and **`FCH_CEIL` is 15** — the measured
      reference ceiling. `MAXFILES` now also **CLEARs variables
      unconditionally**, the `sem_same` behaviour.
      **Cost: 1 B of main page 1, 0 B of low region, NO CARVE** (measured by
      relaxing the `$8000` guard and reading `__MEAS_PAGE1_END`, then
      restoring). ⚠️ **Page 1 was at 0 B free on 2026-07-29** (`$8000` exactly).
      🔴 **THE COST WAS SITING, A THIRD TIME.** The first build overran by 8 B
      and all 8 were `MAXFILES`' `CLEAR` — which is verbatim `ex_clear`'s own
      tail. `jp clr_done` costs the 3 bytes the `jp exec_stmt` it replaced
      already spent, so the `CLEAR` came free. The allocation itself was ~free
      because its whole arithmetic chain (`strheap_varceil` →
      `strheap_floor` → `strheap_ceiling`) was ALREADY sub-ROM.
      **DECISION (user, 2026-07-29): charge 50 B/channel, not the reference's
      267.** A zerobas block genuinely IS 50 B (shared `FSECTOR_BUF` cache), so
      it charges what it uses; padding to 267 would reserve 217 B/channel that
      nothing reads and cost a user 4005 B at `MAXFILES=15` instead of 750.
      ⚠️ **This CORRECTS spec §6**, which asked the gate to assert 267 on both
      sides — the gate asserts the MECHANISM (linear per-channel, ceiling 15,
      both sides) and reports each machine's own constant.
      ⚠️ **THE SLOPE ALONE IS A GATE THAT CAN MEASURE NOTHING, AND THIS WAS
      FALSIFIED, NOT REASONED.** With the array ceilings reverted to
      `strheap_floor` — i.e. the carve REPORTED but not RESERVED — `mf0`/`mf2`/
      `mf15` still read a flawless 14899/14799/14149 while arrays grew straight
      through the channel table. The new two-sided `dim_fits`/`dim_over` rows
      catch it (`dim_over` returned 7777 instead of `Out of memory`); its +400 B
      overshoot is sized against the 750 B of slack the bug creates.
      ⚠️ **AND ONE EXISTING ROW WAS UNMEASURABLE**: `sem_str` typed
      `PRINT A$`, and a cleared A$ (empty line) and an uncleared one (`XY`) BOTH
      score `<none>` in this probe's readout — equal on both sides, PASS
      forever. Now `PRINT LEN(A$)` (0 vs 2) with a `REM` control.
      `make chancost-characterize` is now a real GATE (non-zero on unfiled
      divergence / oracle drift / a flat ladder), 31 cases, 9 filed divergences.
      **S-FCH-2 ✅ MEASURED 2026-07-29 (built all four parts, measured each,
      kept the free one).** Full cost **45 B page 1 + 41 B low region = 86 B**
      against **0 B / 9 B free** — the ~100 B estimate was close this time.
      ✅ **ERR 5 IS LANDED AND COST EXACTLY ZERO**: `gb_illegal` is already the
      ERR 5 raiser and already in page 1, so `jp cc,gb_illegal` spends the same
      3 bytes `jp cc,stmt_error` did. `MAXFILES=16`/`255` now raise **Illegal
      function call** and `err_over` traps **ERR 5** — the gate's filed
      divergences drop **9 → 6**.
      **Breakdown (spec §5c):** ERR 5 = 0 B · ERR 59 (closed-channel EOF/LOF)
      = 8 B page 1 · ERR 52 raiser + 2 message strings + sparse table = 14 B
      page 1 + 41 B low · the sparse lookup in `raise_error` = 23 B page 1.
      ⚠️ **64 of the 86 bytes are MESSAGE DATA + A TABLE WALK** — the most
      evictable shape there is. A page-0 sub-ROM tenant could own it and stage
      the message into the **208 B still free at `$EA30..$EAFF`**, leaving a
      shim; that would cut the resident need to ~35-40 B. **MEASURE THAT BEFORE
      SCOUTING A CARVE** — this arc has three times found the cost was siting.
      ✅ **THE EVICTION IS MEASURED TOO: the carve drops 77 B -> 26 B.** The
      table, both strings and the walk move to the EXISTING string-heap tenant
      as op 19 (no new dispatch index), staging the message into page-3 RAM at
      `$EA30`; the two raisers move to the low region. Result: page 1 20 over,
      low 6 over. Moving the shim down too only trades one wall for the other --
      the total stays 26 B, so ONLY A CARVE closes it.
      ⚠️ **BOTH S-FCH-2 BUILDS ARE COST PROBES: MEASURED, NEVER RUN.** ERR 5 is
      the only part executed and gated. Before any of the rest lands: (1)
      `err_bad_filenum` forces `ONEFLG=1` to reach the abort arm and LEAVES IT
      SET -- if the REPL return does not clear it, the NEXT error force-aborts
      instead of trapping; (2) the ten repointed `jp` sites are unconditional in
      the probe, so the LEAN CART WOULD NOT ASSEMBLE -- landing needs per-site
      gating, or the lean cart retired.
      ⚠️ **THE MEASUREMENT APPARATUS WAS WRONG FIRST AND READ PLAUSIBLY (77 B).**
      Relaxing the low region's guard removes its `ds $4000 - $` pad — and that
      pad is what puts the cartridge header at `$4000`. Without it page 1 slides
      down with the low region and `__MEAS_PAGE1_END` measures BOTH walls. Pin
      the header with an explicit `org $4000`. Corrected: 45 B, not 77.
      ✅ **THE CARVE IS DONE: D-MSGENC LANDED 2026-07-29 (`9a0300d`,
      docs/spec-basic-msgenc-carve.md).** Phrase-encoding the 25 resident error
      messages took page 1 from **0 → 24 B free** and the low region from
      **9 → 68 B free**. S-FCH-2's evicted form needs 20 + 15: **funded, with
      4 B and 53 B spare.**
      ✅ **S-FCH-2 LANDED ALL-RESIDENT 2026-07-29 (spec §5d).** ERR 52 `bad file
      number` and ERR 59 `file not open` are raised and printed by the resident
      ROM. It cost **11 B of page 1 + 59 B of low**, not the 45 + 32 estimated:
      page 1 **24 → 13 B free**, low **68 → 9 B free**, lean cart byte-identical.
      No eviction, no tenant op 19, no `ERRMSG_BUF` staging, no repointed `jp`
      sites — **both §5c blockers dissolved rather than gated.** The gate goes
      31 cases / 6 filed divergences → **39 / 4**, closing `sem_zero`,
      `sem_hinum`, `sem_reopen` and `err_notopen`.
      ⚠️ **AND IT WAS NEVER A DEMOTION.** The scout ran first and returned
      **zero**: page-0 tenants reach *no* main routine at all (709 routines,
      every one sub-local — the only main-side import list in the sub-ROM is
      `sub/basic-resident-abi.inc`, eleven page-1-tenant seeds already below
      `$4000`). Nothing in page 1 is pinned there by tenancy, so the cheap move
      was to site S-FCH-2's OWN new content low and leave existing code alone.
      **A shortfall stated as "N bytes short" invites relocating N bytes; ask
      first whether the NEW content has to be where the estimate put it.**
      🔴 **BLOCKER (2) — the lean cart — was dissolved by aliasing the LABEL,
      not by gating the SITES:** `IF ROM_BASE >= $4000 : oo_fail_bfn equ
      oo_fail_syn`. All six rejects keep their existing 3-byte `jp cc,`, which in
      the lean build assembles to the exact bytes it did before. Zero sites
      gated.
      🔴 **BLOCKER (1) — "ERR 52 is not trappable" — WAS A CONFOUND, and so was
      the ONEFLG forcing built on it.** The `err_badchan` row types `MAXFILES=1`
      BETWEEN the arm and the error, and that statement suppresses the handler
      on the reference. Measured three unconfounded ways on the CF-3300:
      `OPEN…AS #2`, `OPEN…AS #0` and `EOF(1)` on a closed channel ALL trap
      (ERR 52, 52, 59). So both codes go through the shared `raise_error_hl`
      trap decision like every other code and **write `ONEFLG` nowhere**.
      Gate rows `bfn_trap`/`bfn_zero`/`fno_eof` + the `bfn_ctl` two-sided
      control now measure the CODE instead of its neighbours.
      🙋 NEEDS-JOOST — a call that is yours to make (retire / delete).

- [ ] **`GET`/`PUT`/`FIELD`/`INPUT$` on a `CAS:` channel (`FCH_MODES` 7/8) are
      INFERRED, not measured.** D-NOTOPEN2 swept modes 0–6 against the CF-3300 and
      sends 7/8 down the *device* arm (CF clear, since both are >= `LPT_MODE`), i.e.
      `GET`/`PUT` → 58, `FIELD` → 5, `INPUT$` → 55, **by analogy with `LPT:`/`CRT:`
      rather than by measurement.** 🔴 That is precisely the shape that slice spent
      two batteries avoiding everywhere else, so it is filed rather than shipped
      quietly. Blocked on apparatus, not on ROM space: `diskbasic_probe_lof.py`
      mounts a disk image per case and has no way to attach a tape, so this needs a
      `disk_probe`-side (or new cassette-side) harness. ⚠️ The reference may well
      not agree with the analogy — `LPT:` itself answers **two different codes**
      (58 to `GET`, 5 to `FIELD`), which is the local evidence that device handling
      here is per-verb and not a single rule.
      ⚠️ **CONSIDERED AND NOT RE-MEASURED, 2026-08-09** — NOT MEASURABLE THIS
      WAY, on two counts: no harness on either side drives a tape and a disk at
      once (the entry's own blocker, unchanged), and there is **no reading to
      falsify** — the item records that modes 7/8 are INFERRED, which is a gap
      rather than a divergence. Still open, still correct as filed.
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §5.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **UNMEASURED: a machine reset BETWEEN a RANDOM `PUT` and its `CLOSE`.**
      Filed 2026-07-31 by D-RNDDIR as the one thing its rows do not reach. In
      that window the two disks genuinely differ: the reference has stamped
      nothing and loses the write, while zerobas's root-directory entry is
      already stamped and points at a chain whose FAT state at that instant
      NOTHING HAS EXAMINED. ⚠️ Blocked on APPARATUS, not ROM space:
      `diskbasic_probe_lof.py` reads the disk image after the machine exits
      normally and has no way to cut power mid-program. It is a robustness
      question, not a parity one — and it is filed rather than argued in either
      direction, because "zerobas is more robust here" and "zerobas leaves a
      dangling entry here" are both plausible from what is known and neither has
      been typed.
      ⚠️ **CONSIDERED AND NOT RE-MEASURED, 2026-08-09** — NOT MEASURABLE THIS
      WAY: it needs power cut mid-program, and the harness reads the image after
      the machine exits normally. Filed as UNMEASURED, and it still is.
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §5.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **`float-acceptance` HAS NO NAMED EXPECTED-FAILURE MECHANISM.** Filed
      2026-08-01 by D-EXPKW. The suite is green today, so this is not urgent —
      but it reports `371 PASS, 1 FAIL` and exits non-zero with **nothing naming
      the expected count**, which is exactly what made the D-EXPKW regression
      unreadable for a whole slice. `array-acceptance`'s 149/151 names
      `ifc.instr.zero`/`ifc.instr.neg`, and lnblank's `KNOWN_DIVERGE` pins each
      entry to its exact observed value so a row that silently starts passing
      breaks the gate. `float-acceptance` has neither. ⚠️ Give it the
      *control* shape, not the suppression shape.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **THE TWO TYPE-CODE NAMESPACES SHOULD PROBABLY BECOME ONE.** Filed
      2026-08-01 by D-DEFSTR. The references use `3` for **both** the DEFtbl code
      and the variable-chain type byte, which makes `elsize == type` an identity
      and [`elsize_from_type`](sub/arrays.asm:943) — plus ~7 call sites —
      deletable. zerobas uses `1` in the chain with a `1 → 3` map.
      ⚠️ The chain's stored type byte is **RAM-observable**, so this needs its own
      oracle-lock on that byte before anything moves; D-REHOME measured only that
      the string scalar entry's SIZE agrees (+6 B, `ARYTAB $8003→$8009`), never
      its contents. ⚠️ Also note the entry field ORDER may differ from the
      reference's — unmeasured. A separate slice, not a ride-along.
      🔭 SCOUT-THEN-ASK — the decision is yours; the measuring and pricing in front of it are not (refactor, no oracle, but unpriced/unmeasured first).

- [ ] **HOW MUCH OF THE 311-BYTE `NO-ORACLE` BUCKET IS A POINTER?** Filed
      2026-08-01 by D-REHOME. `FRETOP` sat in that bucket scored as *"no
      reading"* while all three sides agreed **perfectly** on the movement
      (−4/−20). The sweep now has a `SAME-DELTA` verdict, but it is only applied
      in the re-homing table — **the 3199-byte census still classifies every byte
      absolutely.** 🔴 `NO-ORACLE` is a verdict about the COMPARISON, not about
      the variable, and the bucket is an over-count by an unmeasured amount.
      ⚠️ A byte-wise delta pass needs a rule for what counts as a pointer PAIR;
      naive per-byte deltas on a 16-bit cell will agree by luck on the high byte.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **zerobas' `VALTYP $E0C8` READS `$FF` AT COLD BOOT — ✅ CAUSE MEASURED
      2026-08-21 (D-VALTYP), FIX PRICED AT 3 B AND DECLINED.**
      [`docs/valtyp-coldram-notes.md`](docs/valtyp-coldram-notes.md).
      🎯 **IT IS POWER-ON RAM, NOT A WRITE.** Read as a WINDOW instead of one
      byte: every never-written cell in this private `$E0xx` block is `$FF`, and
      every cell an init writes (`PRDEST`, `PRDEV`, `CONTVALID`) is `00`.
      Nothing writes a third value; the item's implicit hypothesis is refuted.
      💰 **THE FIX IS `ld (VALTYP),a` IN THE COLD HOOK = 3 B OF MAIN PAGE 1,
      WHICH MEASURED 2 B FREE ON 2026-08-21.** It does not fit, no cheaper
      encoding exists (`ld (nn),a` and `ld (nn),hl` are both 3 B and no adjacent
      pair is already zeroed), and every cold-init routine in the tree
      (`interp.asm`, `clear_vars`, `init_filechan`) is in page 1. The low region
      had 22 B and the two walls are COUPLED, so a promotion could fund it — but
      that is its own slice with its own closure check, and this is hygiene.
      **Reopen for a new caller that READS BEFORE WRITING, not for a spare
      byte.**
      🔴 **AND THE MEASUREMENT FOUND A DEFECT NEXT DOOR** — see the item below.
      Filed 2026-08-01 by D-REHOME from the new private-cell capture. Benign
      today (written before read at every eval), so this is a *hygiene* item,
      not a defect — but it is exactly the shape that becomes one when a new
      caller reads before writing.
      ✅ **RE-MEASURED 2026-08-09 AND AGAIN 2026-08-20 AT `ef50f4c` — STILL
      `ff`**, read as MEMORY (`capture=("mem_abs",[(0xE0C8,1)])`) on a case whose
      only line is `REM`, so no expression of ours evaluates first and writes the
      cell. Zerobas-only by construction: it is our own private cell, so there is
      no reference column and no gate can ever be two-sided about it.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE: `E0C8 = $ff`**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.9). ⚠️ Read as MEMORY (`capture=("mem_abs",[(0xE0C8,1)])`) on a case
      whose only line is `REM`, because `PRINT PEEK(&HE0C8)` cannot answer this
      question: evaluating PEEK's own argument writes `VALTYP` before PEEK reads
      it. One-sided by construction — the cell is zerobas's own private one and
      has no reference column.
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).

- [ ] ⚠️ **THE `--say` SURFACE IS STILL UN-GATED OUTSIDE `ONLY=lnrd-`.** Split
      out 2026-08-09 from the `dir-name` item above, whose *payload* is now green
      (D-NAMSPC) but whose *apparatus* half never was. `--say` rows are filtered
      out of `lnblank-acceptance` entirely; `make lnblank-say-acceptance` exists
      but is scoped to `lnrd-` because THIS surface is where `dir-name` was
      hiding, and a whole-surface default would have shipped a red target.
      ✅ **That reason is now spent** — the row that made the default narrow
      reads ` 7 ` on all three sides — so widening the default is unblocked, and
      it is the fix. ⚠️ **A payload that now agrees says nothing about the rows
      nobody looks at** [[echo-guard-never-saw-say-rows]]: ask what else the say
      pass says BEFORE widening, because the answer decides whether widening is
      a one-line Makefile change or a slice.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **A `--say` row with no brackets cannot have a reading.**
      Found 2026-08-01 in D-NAMBLANK. `result_span_after_echo`
      ([`probes/lib/omsx_repl.py:1212`](probes/lib/omsx_repl.py:1212)) returns the
      text between the last `[` and its `]`, so a `SAY_ONLY` payload that prints
      no brackets reads `<none>` on **every** side — and sides that all failed
      compare EQUAL and report *agrees*. `basic_probe_lnblank.py`'s `dir-print`
      had been in that state since it was written (dormant rather than green: the
      gate filters `--say` rows out). Both its payload and the new `dir-name` are
      bracketed now and locked.
      ⚠️ **The class is not closed** — this was found in one probe by accident.
      Sweep every `SAY_ONLY`/`result_span` row in `probes/` for a payload that
      cannot produce a bracketed span, and consider making the helper *fail loudly*
      on a payload with no `[` in it rather than returning the same `None` a
      genuine abort returns. Same shape as [`chancost` NOREAD](docs/chancost-cf3300-characterization.md):
      a sentinel that also means "no reading" is not a measurement.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] **A TRAILING BLANK at end of line is not measurable through the keyboard.**
      Found 2026-07-31 in D-DECBLANK (`dec-eol` / `dec-eolctl`, both
      informational **by construction**). At `--repeat 2` the references drop a
      trailing blank and zerobas keeps it — in a `REM` tail as well as after a
      literal, and a `REM` tail is **verbatim**, so the difference is at **line
      ENTRY** (the editor), not in any scanner.
      ⚠️ But an earlier `--repeat 1` pass read the same `REM` row on zerobas
      *without* the blank, for a payload no crunch change can touch — so the cell
      is not stable enough to ground a rule, only to be filed.
      ⚠️ **The echo guard cannot referee it**: `echo_missing()` `rstrip`s every
      screen row, so a trailing blank is invisible to the guard no matter what the
      machine did with it, and a payload whose delivery cannot be verified may not
      gate. Resolving the cell needs a delivery path that bypasses the line editor
      — an ASCII `LOAD"CAS:`, the way `basic_probe_floatlit.py` reaches literals.
      Detail: [`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md) §5.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] 🔴 **`err_verify` AND `brk_msg` ARE THE LAST TWO MAIN-RESIDENT MESSAGES,
      AND THEY ARE BLOCKED FOR TWO DIFFERENT REASONS.** Filed 2026-08-02 by
      D-MSGMIGRATE §6.2/§6.3, which measured both and declined both.
      * `err_verify` (8 B): `verify_error` ([`basic/cload.asm:580`](basic/cload.asm:580))
        is `ld hl,err_verify / jp print_msg` with **no `ld (ERRFLG),a`**. Adding
        one costs 5 B to save 8 -- a net 3 B not worth taking blind, because it
        also makes `PRINT ERR` read 20 after a `CLOAD?` mismatch, which is an
        **observable change with no oracle reading behind it**. ⚠️ Exactly the
        shape D-MSGMIGRATE's own §6.4 turned out to be, and there the reading
        (both refs read 6) is what made the fix correct AND free -- so TAKE THE
        READING FIRST. The CAS: harness is the cost; `Verify error` is still
        `<not-measured>` in the msgexact denominator for the same reason.
      * `brk_msg` (6 B): printed by `call print_string`, and **`print_string` has
        no escape decoder at all** -- a `MSGESC_SUB` byte there is `pchar`'d as a
        literal $06. And `Break` is not an error, so ERRFLG is stale. Two
        independent blockers; this one needs a PRINTER change, not a key.
      🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).

- [ ] ⚠️ **AN INDIRECT REACHER CANNOT BE ENUMERATED BY NAMING THE CALLEE.**
      Filed 2026-08-02 by D-MSGMIGRATE §9, whose blast-radius sweep grepped for
      `jp|call|jr .*print_msg` and therefore missed a FOURTH reacher:
      `dispatch_line`'s line-number-out-of-range arm arrives by
      `jr dl_ovf_report`, a shared tail, and never names `print_msg`.
      The BUILD caught it (the label vanished with a collapsed branch), not the
      sweep. It passes a resident string so it reaches nothing sub-hosted today --
      but it would have, silently, had that string ever migrated.
      Worth a tool: resolve fall-through and shared-tail edges when enumerating
      "who can reach routine X", the same way `check_tenant_closure.py` walks a
      call graph rather than grepping for names.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [ ] ⚠️ **A PROBE'S MESSAGE LITERAL IS EITHER AN ASSERTION OR A CLASSIFIER
      NEEDLE, AND THEY LOOK IDENTICAL.** Filed 2026-08-02 by D-MSGEXACT §6b,
      which silently broke **30 comparisons across 9 files** and every one failed
      by **agreeing**: a needle matched against an already-`.lower()`-ed screen
      string cannot match if it is capitalised, so the row reclassifies from
      `error:<phrase>` to `value` instead of going red.
      ⚠️ `badfnum` was invisible to two rounds of auditing — it has no `.lower()`
      at all; it `setdefault`s its needle into an `ERR_CLASSES` dict **imported
      from `lof`**. The gate caught it (12 oracle drifts), not the audit.
      Worth a lint: a capitalised message literal reaching a case-folded
      comparison, across module boundaries. Until then the vocabularies carry
      explicit "MUST STAY LOWERCASE" comments
      ([`basic_probe_kwsweep.py`](probes/basic/basic_probe_kwsweep.py) has the
      worked one).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [x] ✅ **CLOSED 2026-08-21 (D-FNEXPR2), 0 ROM BYTES — THE FACE FOR A
      NON-STRING FILENAME (`OPEN 5 AS #1`) WAS UNMEASURED.**
      [`docs/spec-basic-fnexpr2.md`](docs/spec-basic-fnexpr2.md) §2. Measured at
      SIX verbs, not the three this item named: `OPEN 5 AS #1` / `KILL 5` /
      `SAVE 5` / `LOAD 5` / `BLOAD 5` / `FILES 5` are **`Type mismatch`** on the
      CF-3300. 🎯 So the hunch recorded below — *"if `OPEN` agrees with `PLAY`
      on the reference, the fix is one instruction at one site"* — was right in
      both halves, and it was right about MORE verbs than it claimed: zerobas
      answered a non-quote with THREE different things and the reference answers
      one thing at all six.
      🔴 **BUT "NON-STRING → Type mismatch" IS NOT THE WHOLE RULE, AND THE ROW
      THAT SAYS SO WAS NOT IN THIS ITEM'S PLAN.** `SAVE 1/0` and
      `OPEN 1/0 AS #1` are **`Division by zero`** — the reference EVALUATES the
      operand and the operand's own fault wins. That is D-MISS-1's `A$=1/0`
      rule at the filename position, and a blanket ERR 13 would have matched six
      rows and been wrong on two.
      💰 **The item priced 0–3 B and it cost ZERO**: `els_tc_common`
      ([`basic/missing.asm`](basic/missing.asm)) already IS that whole tail
      (clear ERRMARK → `eval` → `check_expr_errors` → `Syntax error` if nothing
      parsed, else `type_mismatch_error`) and already had two entry points that
      each pop their own saved word before falling in. `fname_expr` has none to
      pop, so it enters at the common label and one jump target changed.
      *The original filing:*
      ⚠️ **THE FACE FOR A NON-STRING FILENAME (`OPEN 5 AS #1`) IS UNMEASURED.**
      Filed 2026-08-21 by D-FNEXPR §3.3, which deliberately PRESERVED today's
      answer rather than guess at a better one. zerobas says `Syntax error`,
      before the change (a non-quote failed `cp '"'`) and after it (`str_eval`
      returns CF clear on a numeric operand and `fname_expr` jumps to the same
      `stmt_error`). **No row drives it on either reference.**
      🎯 The reason to doubt it is inside this tree: `ex_play`
      ([`basic/play.asm`](basic/play.asm)) answers `Type mismatch` for exactly
      this shape — a numeric expression where a string operand is required — and
      that face was measured against the reference. If `OPEN` agrees with `PLAY`
      on the reference, the fix is one instruction at one site.
      💰 A row on each of `OPEN`/`KILL`/`NAME`, then 0–3 B. Cheap, and it is a
      MEASUREMENT before it is a change.

- [x] ✅ **`.` — THE CURRENT-LINE PSEUDO-LINE-NUMBER — LANDED 2026-08-02
      (D-DOTLINE). Four pins RETIRED, none added; `lnblank-say-acceptance`
      108 -> 181 rows with 6 -> 2 pins; `lnblank-acceptance` 530 -> 536,
      allowlist still EMPTY. 16 corpus targets green, six knives scored.** Spec
      [`docs/spec-basic-dotline.md`](docs/spec-basic-dotline.md), measurement
      [`docs/dotline-msx1-characterization.md`](docs/dotline-msx1-characterization.md).
      Filed by D-DELETE, confirmed on a second verb by D-LSTRNG, both of which
      measured `.` and DECLINED it rather than ship a rule one verb wide.
      🔴 **THEY WERE RIGHT, AND FOR A BIGGER REASON THAN EITHER GAVE.** The four
      filed rows measured ONE writer — storing a line — and ONE argument
      position. The 77-row walk found **four writers and eleven measured
      NON-writers**, and three of the four would have been implemented WRONGLY
      from a `DELETE`- or `LIST`-shaped reading:
      * **`LIST` writes it**, to the LAST LINE IT PRINTED — not the argument,
        not either end — and a `LIST` that prints nothing writes nothing
        (`cln-listrng` 30, `cln-listbare` 40, `cln-listmiss` unchanged; the
        filed `LIST 40` row could not separate four candidate rules);
      * 🔴 **an ASCII `SAVE` WRITES IT TOO (40) and a tokenised one does not
        (20)**, because both drive the same walk.
        ⚠️ **THIS IS THE EXACT MIRROR OF THE HAZARD D-LSTRNG §3.3 HAD TO FIX IN
        THAT VERY ROUTINE** — a `LIST` range leaking into `SAVE",A"` was a
        data-loss bug — so reasoning by analogy says keep `DOT` OUT of the
        shared `list_walk` for ~16 B. The measurement says put it IN for 4 B.
        Same routine, two shared-code questions, **opposite answers**;
      * 🔴 **a DIRECT-MODE error writes NOTHING** — it does not take `ERRLIN`'s
        measured 65535 sentinel, so the two cells are written by the same event
        under different rules and the obvious shared tail (4 B cheaper) is
        wrong;
      * 🔴 **the `DELETE` VERB does not write it** even though the
        bare-line-number delete does. Two ways to remove a line, same visible
        effect on the program, different effect on `.`;
      * 🔴 **`RESUME` IS NOT A WRITER — AND THIS SLICE SHIPPED ONE BEFORE ITS
        OWN KNIFE FOUND IT.** `cln-trap` alone reads the HANDLER's line and
        would have been written up as "a trapped error records where control
        went"; `clp-trapend` (`50 END`) reads the ERRORING line, and
        `clp-onerr`/`-goto`/`-gosub` kill the rival "a line LOOKUP is the
        writer" reading. What replaced them — "a RESUME records the line it is
        IN" — was **implemented, ~12 B of page 1, and wrong**. Knife K5 cut it
        and moved **ZERO of 139 rows**: every supporting row had TWO SUFFICIENT
        CAUSES, because `RESUME NEXT` resumes into line 30 which then FALLS
        INTO line 50 again, raising ERR 22 *in line 50*. `clp-resend`
        (`30 A=A+4:END`, so line 50 is never re-entered) reads **20** on both
        references against the shipped build's 50. Withdrawn, **14 B
        recovered**; the slice costs 10 B of page 1, not 24
        [[knife-that-reddens-nothing-is-the-finding]];
      * **`NEW` does NOT reset it**, which `LIST .` is structurally blind to.
      🎯 **THE PUBLISHED WORK AREA NAMES THE VARIABLE — `DOT $F6B5`, "line
      number of last used (changed, listed, added) line"** (C-BIOS
      `systemvars.asm`, the same allowed source the sysvar denominator is
      generated from). Claimed at the published address under the published
      name for **zero ROM bytes**, D-REHOME's sixth honoured cell and the first
      that was never re-homed — it did not exist before. PUB-FREE measured
      first: zerobas' byte there read 0 in all 24 swept states.
      🎯 **AND THAT CELL IS WHY THE COLD MACHINE AND `NEW` ARE MEASURED AT ALL.**
      `LIST .` cannot ask either — on a cold machine, and after a `NEW`, the
      program is EMPTY, so nothing is listed whatever the cell holds and every
      reading compares EQUAL on every side. Every one of the 24 `clp` PEEK rows
      has a behavioural twin and **every twin agrees**, which is what makes the
      PEEK evidence about `.` and not about a byte.
      ⚠️ **AN APPARATUS FAULT OF THE FAIL-BY-AGREEING KIND, CAUGHT ONLY BY AN
      ASYMMETRY.** The first cell readout was 38 characters — inside the 40-byte
      KEYBUF cap, which is why it looked safe — but the screen's two-column
      margin pushed its closing quote onto the next row, so `_echo_idx` found no
      row carrying the command and the reader returned `<none>`, a sentinel that
      also means "no reading". It did that on vg8020 and zb but NOT cf3300,
      whose Disk BASIC lays the prompt out differently; had cf3300 wrapped too,
      all three sides would have reported THREE-WAY AGREEMENT on nothing. The
      value was on screen the whole time. **The binding constraint is COLS minus
      the margin, not the KEYBUF cap.**
      Landed **+10 B main page 1** (311 -> 301 free) and **+17 B sub page 1**;
      one resolver in `ldr_num`, the single site both `le_delrange` and
      `le_lstrange` read a line number from, so `AUTO`/`RENUM` get `.` free the
      day they are dispatched.
      ⚠️ **STILL UNMEASURED, and recorded as choices rather than readings**:
      whether an ASCII LOAD/MERGE writes `.` per line (zerobas' `cload.asm`
      reaches `store_line`, so it inherits writer (a) either way); whether an
      OOM store writes it; and the ASCII-SAVE reading is **cf3300 only** —
      `SAVE"CAS:",A` would give a second reference and needs cassette support
      this probe does not have.

## Beyond — post-MSX1 axes (out of charter, far future)

Two distinct axes past MSX1, captured so the boundaries aren't lost. **Neither is
scheduled**; both require a charter raise. They differ in *provenance*, which is the
whole point of listing them apart.

**A. Later generations — a *clone* axis (has oracles).** MSX2, MSX2+, Turbo-R.
Official ASCII BASIC shipped for these and real machines exist, so this is **today's
method with more surface**: clone-and-validate against an oracle. New ground would be
the V9938/V9958 `SCREEN 4–12` modes + blitter, MSX-DOS 2, R800 timing, and the extra
BASIC verbs each generation added. Methodologically identical to current work — just
bigger.

**B. Extension-cartridge hardware — a *greenfield* axis (no oracle).** Additive,
**own-design** BASIC support for cartridge hardware that **never had official BASIC**.
This is the project's only own-authorship corner: no reference implementation to
clone, no oracle to match — correctness is defined by our own spec + the hardware
documentation, and the rule is *additive-compatible* (new verbs / `SCREEN` numbers
above the built-in range; standard programs untouched). Provenance varies **per chip**:

- **Yamaha V9990 (E-VDP III)** — GFX9000 / Power Graph / Video9000 video cartridge.
  **Clean**: an official Yamaha datasheet exists (A; see `docs/allowed-sources.md`,
  gen `ext`). Not V99x8-register-compatible — its own P1/P2/Bx modes + I/O ports.
- **Konami SCC / SCC+** (K051649 / K052539) — wave-table sound in Konami carts
  (Snatcher, Metal Gear 2, Nemesis…). **Caveat**: *no published manufacturer
  datasheet* — the register interface is known only through community
  reverse-engineering. So support would need our **own black-box characterisation**
  of the chip (the oracle discipline applied to silicon), with community register
  maps as **C-tier corroboration only**, never an authoritative spec.
  **Two deliverables, and the document is the more lasting one:** because no
  datasheet exists, a careful black-box characterisation *produces* primary
  documentation rather than reproducing protected work — for once zerobas is
  *upstream*, a source not a sink. The result (register + waveform reference, with
  method and reproducible raw captures — the probe corpus *is* the document) would
  be an **A-grade, clean-provenance** artifact by our own scale, promoting the SCC
  from "C-tier community-RE only" to "A, our own characterisation," and a standalone
  gift to MSX preservation (emulator authors, homebrew musicians, the next
  reimplementation) **independent of whether the BASIC extension ever ships**.

(Third-party BASIC extensions exist for both — proprietary, **not** a source; design
our own from the hardware docs / our own characterisation.)

## Done — storage transports

➡️ **Moved to [`docs/TODO-done.md`](docs/TODO-done.md) on 2026-08-26** — a prose done-record of disk and tape; no items at all.
The record is unchanged there; this heading is kept only so the citations and
the phase narrative above still have somewhere to land.
