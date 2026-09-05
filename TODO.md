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

**RE-CHECKED 2026-09-01: 116 open blocks, 116 markers, 0 unmarked.** It was
**118 blocks / 115 markers** when this session opened — 🔴 **THREE OPEN ITEMS HAD
NO MARKER, WHICH IS THE FAILURE THIS INVARIANT EXISTS TO CATCH, AND IT HAD BEEN
FAILING SILENTLY**: nothing runs `--count`, so the line below said "checked"
about a day in August. Two of the three (`subrom-closure-check`'s `equ` alias;
the truncated tokenised load) were **finished work still spelled `- [ ]`** — both
re-verified by RUNNING, not reading, then closed — and the third (D-NGRAM) is the
arc this loop has shipped nineteen slices of, invisible to the pick-up rule for
want of one emoji. The figures in the table above are **2026-08-27** and stand as
taken; these are today's. Recount, never quote.

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

- [x] 🟢 **`check_todo_citations.py --fix` CANNOT TELL A CITATION QUOTED AS AN
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
      citation exists in the file).
      🟢 **CLOSED 2026-09-01 (D-REPOINTMARK)** —
      [`docs/spec-repoint-marker.md`](docs/spec-repoint-marker.md).
      🔴 **THE ITEM WAS STALE ON BOTH OF THE NAMES IT ACCUSED, AND BLIND TO THE
      ONE THAT WAS GUILTY.** *"neither the fixer nor `todo-citation-check` has a
      way to mark one inert"* was already false when written down: D-FILEDROT had
      given `check_todo_citations.py` the `NOT-A-CITATION` marker, honoured in
      `scan()` — which `--fix` runs off — with a both-directions arm. The escape
      and the gate arm this item asks for **had both shipped**.
      What no one had noticed is that the repo has a **SECOND** citation
      rewriter: `tools/split_todo_archive.py`'s `repoint()`. It substituted over
      WHOLE-FILE text, so the marker was not merely unimplemented there, it was
      **unimplementable in that shape**. Swept: **5 lines carry the marker and
      match its `CITE`, every one of them in the rewriter's own file**, including
      arms S1/S2/S3's fixtures. S2 and S3 would have gone red; **S1 asserts
      `== []`, so its vector would have been gutted SILENTLY** — the exact
      failure the marker exists to stop, one file over.
      ➡️ Fixed: per-line substitution in `_repoint_text()`, factored so an arm
      scores the shipped path. Arms **S8/S9/S10** (rewrite / exempt /
      line-scoped), each falsified by planting both failure directions; S8 is the
      load-bearing control, and only S10 survives neither plant. `in_href` moved
      to a per-line offset — **the two readings disagree on 0 of the tree's 12
      matches**. Markdown needed two spellings (an HTML comment in prose, an
      elision inside a fenced quote) and this doc's own first draft shipped
      three unmarked examples.
      🎯 **A RESIDUAL CAN BE CLOSED HALF BY A SLICE AIMING ELSEWHERE AND HALF BY
      A HOLE IT NEVER NAMED** — re-run the item's own accusation before building
      on it [[a-justification-parenthesis-is-an-unrun-claim]].

- [ ] 🔴 **`check_todo_citations.py` VERIFIES THAT AN ID MATCHES ITS LINE, NEVER
      THAT THE CITED BLOCK IS THE ONE THE PROSE IS ABOUT — AND ONE CITATION HAD
      BEEN POINTING AT AN UNRELATED ITEM FOR AN UNKNOWN LENGTH OF TIME.** Found
      2026-09-05 by D-EXPBAND, by accident.
      `docs/gapsweep-2026-08-21.md:124` reads **“`LOAD"CAS:"` accepts a tokenised
      tape (`../TODO.md:5345 (T-DB105B)`)”**, and `TODO.md:5345` was  NOT-A-CITATION
      `fp_exp`/`fp_log`'s `$8000` reachability item — a different subject
      entirely. The gate was GREEN on it, correctly by its own rule: the id
      really was the id of the block at that line. The real `LOAD"CAS:"` item is
      at `TODO.md:8317 (T-A55F3D)`, now cited. **It surfaced only because closing
      the `$8000` item changed that headline, so the id stopped resolving** — had
      I not touched that line it would still be wrong and still be green.
      🎯 **THE HOLE IS STRUCTURAL, NOT A TYPO**: the id is derived from the
      headline, so a citation whose line and id agree is self-consistent no
      matter which block it names. `--fix` makes it worse in exactly this case —
      it rewrites the LINE from the ID, so a citation pointing at the wrong block
      gets its wrong target mechanically preserved across every future edit.
      🔴 **FOUR INSTANCES, NOT ONE — AND THE FOURTH WAS GREEN.** Having found the
      first by accident I walked the docs that cite items I had touched, and
      every one of the four citations I inspected named the wrong block:
      | doc | says | actually pointed at | state |
      |---|---|---|---|
      | `gapsweep-2026-08-21.md:124` | `LOAD"CAS:"` tokenised tape | the `$8000` reachability item | red (today) |
      | `spec-lean-retire-s3-gates.md:7` | RETIRE THE LEAN 16 KB CART | the DRAW scale-state item | red (today) |
      | `spec-lean-retire-s2-switch.md:7` | RETIRE THE LEAN 16 KB CART | `GFX_OP=1`'s marshalling | red (today) |
      | `spec-lean-retire-s1-explicit-machine.md:7` | RETIRE THE LEAN 16 KB CART | "a wall figure hardcoded inside a GATE" | 🔴 **GREEN** |
      All three lean-retire steps cite the same parent, and the real parent is
      block **T-9C566E** in `docs/TODO-done.md` — a file none of them named.
      (Cited by id, not `file:line`: the checker resolves a citation's path
      relative to the CITING file, so the `TODO-done.md:NNN` spelling that works
      from `docs/` cannot be written from `TODO.md` at the repo root at all.) **S1's was
      GREEN and verified-against-the-block-id at the moment I read it**, which is
      the proof this hole is not hypothetical: the gate's strongest category
      ("verified") contained a citation pointing at an unrelated subject. All
      four are repointed; the count is now 37 verified, 0 red.
      ⚠️ **This is 4 of the ~5 citations I actually inspected, NOT 4 of 37** — I
      looked only where an edit had already made one go red, plus the sibling
      docs beside it. The rate over the whole set is unmeasured, and the
      archive-move shape above (an item cited in `TODO.md` that later moved to
      `TODO-done.md`) predicts more. A cheap first cut: flag any citation whose
      surrounding sentence shares no distinctive token (a backticked identifier,
      a quoted keyword) with the cited block's headline; expect false positives,
      so report ADVISORY rather than red [[readout-blind-to-its-own-subject]]
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
      💰 Zero ROM bytes; a tools-only change.
      🤖 AUTONOMOUS — a gate settles it; finishable unattended (no his-decision signal found).

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
      `TODO.md:1917 (T-6FE392)8 (T-529ABE)` from `TODO.md:7520 (T-529ABE)`: a
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
      ✅ **ALSO SHIPPED 2026-08-30: `load_commit_prog`** (D-NGRAM12,
      [`docs/spec-basic-ngram12.md`](docs/spec-basic-ngram12.md)) — the
      ten-instruction completion tail that the TAPE loader (`do_tape_prog`,
      CLOAD) and the DISK loader (`disk_prog_load`, `LOAD"file"`) each carried
      verbatim. `dpl_done`'s WHOLE BODY was the run, so it is a free `equ`
      alias, not a 3 B shared-tail jump: **22 B gross, 21 B net** after the
      `jr z,dpl_done` that no longer reached had to widen to `jp`. **Page 1 read
      323 -> 344 B free on 2026-08-30** (a READING; run `make basic-reloc`).
      11 disk + 31 tape rows, DIFF 0; 2 knives + S1; 47/47 battery.
      🔴 **THE SWEEP RANKED IT AT 19 B AND IT IS WORTH 22** — it prices every
      collapse as a shared TAIL (one site pays a jump), and cannot see that a
      site whose whole label block IS the run can be reached by a free `equ`.
      **Worth checking on any candidate whose second site is a whole label
      block.** The `--main` board below it is now thin: 18, 16, 15, then 14s.
      🔴 **AND ITS FIRST KNIFE FOUND A HOLE IN A STANDING GATE.** Cutting the
      `$0000` end-of-program marker moved the tape row and NOT ONE disk row:
      `runtail-acceptance`'s fixture re-loads a program byte-identical to the
      one it just typed, so the terminator the cut failed to write was already
      in RAM. Nine rows agreed for a reason that had nothing to do with the
      marker. Closed by a new row, `load-short` (a LONGER program resident, so
      the loader must terminate a real line away) — 11/11 agree with the
      CF-3300, and it moves under the knife.
      ✅ **ALSO SHIPPED 2026-08-31: `str_eval_ix`** (D-NGRAM15,
      [`docs/spec-basic-ngram15.md`](docs/spec-basic-ngram15.md)) — `push ix /
      pop hl / call str_eval` at SEVEN sites (relational LHS and RHS, CVI, FRE,
      the shared string-arg parse, INSTR, the string relational's RHS). **Low
      region read 112 -> 121 B free and page 1 361 -> 367 on 2026-08-31**
      (a READING; run `make basic-reloc`). 14 rows, 1 scored DIFF (pre-existing),
      1 NO-ORACLE; 2 knives + S1; 48/48 battery.
      🎯 **THE BODY IS SITED WHERE THE CALLERS ARE NOT.** Four callers are in
      page 1 and three in the SCARCE low region — but `str_eval` itself is a
      page-1 routine the low-region callers already reach, so the body goes
      beside it and the scarce region takes the LARGER share (+9 vs +6).
      Siting by "where the code lives" would have given low +3.
      🔴 **A LINE-BASED GREP FOUND 6 OF THE 7** — `ev_ff_fre`'s site carries a
      comment on its `push ix` line. Enumerated at instruction level instead.
      🔴 **AND A THIRD KNIFE WAS BUILT, RUN AND DELETED**: forcing CF set moved
      ALL FOURTEEN rows, both CONTROLS included — a knife that moves the controls
      has broken the machine, not the subject. The decline half therefore rests
      on the rows agreeing with both references plus K-N15B's asserted zero, and
      the spec says so rather than papering over it.
      ✅ **ALSO SHIPPED 2026-08-31: `fname_dev`** (D-NGRAM16,
      [`docs/spec-basic-runarg.md`](docs/spec-basic-runarg.md)) — `call
      fname_expr / ld de,dev_cas / call dev_cmp` at LOAD, RUN"name", SAVE and
      BSAVE, 9 B each. **+15 B**, spent again by the D-RUNARG fix the same row
      set found (net −6 B, page 1 355 -> 349).
      🔴 **THE RISK WAS `fname_expr`'s OUTWARD JUMP, NOT THE Z FLAG** — it does
      `jp nc,els_tc_common` on a non-string filename, which behind a helper sits
      one frame deeper (the D-NGRAM8 shape). Both of that tail's exits RAISE and
      never return, so it cannot bite — and three `n.*` rows drive a non-string
      filename through three of the four verbs to say so.
      ✅ **ALSO SHIPPED 2026-08-31: `req_comma`** (D-NGRAM17,
      [`docs/spec-basic-reqcomma.md`](docs/spec-basic-reqcomma.md)) — the
      MANDATORY-comma run at FIELD, INPUT#, SWAP and SOUND. **Low region read
      121 -> 127 B free and page 1 349 -> 357 on 2026-08-31** (a READING; run
      `make basic-reloc`). 12 rows, 2 knives + S1, 48/48.
      📏 **THE DENOMINATOR IS 72 `cp ','` SITES**, grouped at instruction level
      by WHERE THEY JUMP: 4 to `stmt_error` (required — these), 3 to `exec_stmt`
      (an optional comma that ends the statement), the rest two-site groups with
      their own local labels. Only a shared DESTINATION can share a body.
      🔴 **AND THE KNIVES FOUND FOUR ROWS THAT CANNOT REACH THEIR SITE**: I
      predicted 5 and 4, and 4 and 2 moved. `g.sound` read the NEXT LINE's PRINT
      (fixed — joined with `:`, and the knife then moves it); `g.field` reads
      after a CLOSE (the divergence above); `b.field` raises Bad file number
      first; and `b.swap` never presents a missing comma at all, because the
      crunch folds `A B` into the variable `AB` — measured by `x.spacename`, not
      guessed.
      ✅ **ALSO SHIPPED 2026-08-31: `req_gosub`** (D-NGRAM18,
      [`docs/spec-basic-reqgosub.md`](docs/spec-basic-reqgosub.md)) — the GOSUB
      keyword the four TRAP statements require (ON STOP / ON INTERVAL= / ON
      STRIG / ON KEY). **Page 1 read 357 -> 371 B free on 2026-08-31** (a
      READING; run `make basic-reloc`). 12 rows on three machines, DIFF 0;
      1 knife + S1; 48/48.
      🔴 **A LINE-BASED MATCH FOUND ZERO OF THE FOUR** — the token is
      `GOSUB_TOKEN` (not the lower-case name the sweep prints) AND a comment line
      sits between the `jp` and the `inc hl` at every site. Matched at
      instruction level, tolerating interior comments.
      🔴 **AND TWO FINER KNIVES WERE INVISIBLE TO THEIR OWN ROWS.** Dropping the
      `inc hl` moves NOTHING: the slot loop then finds no line number and
      SILENTLY CLEARS the handlers, and no row here makes a trap FIRE. Accepting
      a missing GOSUB moves nothing either: `ON KEY 100` is rejected LATER, not
      by this check. What does work is making the helper ALWAYS RAISE — exactly
      the four `g.*` rows move, the three controls hold — which is the
      observable form of "every site was rewired" and refuted the live
      hypothesis that the sites were dead code.
      ✅ **CLOSED SAME DAY (D-NGRAM18b) — AND MY "OWED" NOTE WAS WRONG ABOUT THE
      TREE.** It said a firing row "needs an input fixture this probe does not
      build"; `probes/basic/basic_probe_stop_trap.py` ALREADY presses Ctrl-STOP
      through openMSX's key matrix, and five trap probes sit beside it. Scored
      against it, dropping the `inc hl` moves **all 8** zb rows — the handler is
      silently cleared so the trap never fires.
      🎯 **AND THE OTHER BRANCH IS REACHED, NOT DEAD**: pointing it at a
      DISTINGUISHABLE error makes `ON STOP/KEY/STRIG 100` report `Illegal
      function call`, so the arm runs. `ret nz` moved nothing because a
      DOWNSTREAM check reports the identical `Syntax error` — the D-CVISTRTM
      shape. (`ON INTERVAL=100 100` stays `Overflow`, confirming from the machine
      what its geometry predicted.)
      ⚠️ **"No fixture exists" is a claim about the tree and deserved a
      `ls probes/` before it was written down.**
      ✅ **ALSO SHIPPED 2026-08-31: `evmc_arg_int`** (D-NGRAM19,
      [`docs/spec-basic-argint.md`](docs/spec-basic-argint.md)) — the argument
      gate + "is it already an int16?" that ABS, SGN, INT and FIX each opened
      with. **Page 1 read 371 -> 378 B free on 2026-08-31** (a READING; run
      `make basic-reloc`). 16 rows on three machines, DIFF 0; 2 knives + S1.
      🔴 **THE SWEEP RANKED IT 14 B AND IT IS WORTH 7.** Two things leave the run
      for the caller and the ranking can see neither: the `ret nz` returns FROM
      THE VERB (inside a helper it would land one frame too shallow -- the
      D-NGRAM8 bug), and the final `cp 2` publishes a Z FLAG each of the four
      branches on DIFFERENTLY. So the malformed case moves to CARRY and each site
      keeps a 1 B `ret c` -- the D-ARGOPEN shape, a flag a row can see beating a
      frame trick. **The ranking is a floor in BOTH directions**: D-NGRAM12 was
      worth more than ranked, this is worth less.
      🔴 **AND A THIRD MASKED CHECK IN ONE DAY.** `scf` -> `or a` (malformed
      stops reporting carry) moved ZERO rows: `ev_mc_arg_checked` has already
      armed the deferred D-F2-4 error and `check_expr_errors` reports it at the
      statement boundary regardless. The `ret c` decides whether the verb's BODY
      runs on garbage, not what is printed. Re-aimed at reachability, it moves
      all 14 subject rows with both controls holding.
      ➡️ **STILL OPEN, measured 2026-08-28:** an `inc hl` +
      req_letter variant (**31 B**, 6 sites) that **OVERLAPS what shipped and
      must be RE-RUN, not inherited**.
      ✅ **ALSO SHIPPED 2026-08-30: `dpl_get_store`** (D-NGRAM13,
      [`docs/spec-basic-ngram13.md`](docs/spec-basic-ngram13.md)) — the disk
      loader's `fat_io_getbyte` + store-at-CLPTR run, open-coded 3x at 14 B.
      **Page 1 read 344 -> 355 B free on 2026-08-30** (a READING; run
      `make basic-reloc`). 9 rows, 3 DIFF (all pre-existing, see below);
      2 knives + S1.
      🔴 **THE 15 B VERSION WORKED AND WAS THE WRONG ONE.** Folding
      `jp c,dpl_err_pop` into the helper is 4 B cheaper and needs a frame fix
      (the helper's own return address sits on the caller's guarded count, so
      the tail must drop two). **K-N13A cut that fix and moved ZERO rows — on
      TWO fixtures picked to make the bogus return address hostile ($0007, then
      $0BB3).** The stack below the loader is the REPL's own, so a stray `ret`
      finds a plausible address in it and the machine wanders back to the
      prompt. 4 B given back for the CF-return shape, whose failure IS a
      reading. The D-ARGOPEN call, for the same reason.
      🔴 **AND A SECOND CHECK DOWNSTREAM HID THE FIRST ONE'S FAILURE.** With the
      EOF swallowed the loader runs past the file and hits EOF again at the next
      LINK-WORD read, which prints the IDENTICAL message — so the two rows that
      read only the MESSAGE cannot move. Only the rows that read the resulting
      PROGRAM see it.
      ✅ **AND THE CLASS IS NOW COUNTED (2026-09-01, D-LOADSHAPE,
      `scratchpad/loadshape_audit.py` — the audit's answer is in its header):
      denominator 9, fully blind 0, partial 1.** Four candidates are genuinely
      guarded (NEW / POKE witnesses); four of the finder's own flags were FALSE
      POSITIVES (token vectors, error-surface rows, a VPOKE-sentinel the regex
      missed); ONE is partial — `disk_probe_save_ascii` witnesses only the
      corrupted line's restoration — adjudicated as covered because a partial
      load is a REFUSAL on this tree (D-TRUNCLOAD's measured EOF arms), so the
      silent-partial shape cannot occur without truncload's rows going red
      first. 🔴 **The four names the filing guessed (`castail`, `bload`,
      `fat-*`, `merge`) are not in the class at all** — their loads come from
      minted fixtures, not a same-boot save. The fear outran its instances.
      🤖 AUTONOMOUS — **marker added 2026-09-01; this block had none**, and an
      unmarked open item is unclassified, so the loop was skipping the one arc it
      has shipped nineteen slices of. Not a tie: what is left is a MEASUREMENT
      (`scratchpad/ngram_sweep.py --main` — does any candidate still rank above
      its call overhead in the scarce regions?), and D-NGRAM2..19 all shipped
      unattended. ⚠️ **THE TITLE'S "THREE CANDIDATES LEFT" IS A RANKING AND
      RANKINGS ROT** — re-run the sweep, do not spend that number.
      📏 **RE-RUN 2026-09-02 (`scratchpad/ngram_sweep.py --main`, 20760
      instructions, 524 positively-priced candidates before dedup). "THREE" WAS
      STALE: 14 ranked, 3 already ⛔ DECLINED with their reasons recorded, so
      ~11 open.** The ranking has NOT collapsed, but the HEAD has: the top three
      are all declined, and the best open candidate is **12 B**, where the
      shipped slices were 17–50 B. Top open, verbatim:

          12  [TAIL] ld (errmark),a | ld de,0 | ret             4 sites
          12  [sub]  jp nz,ev_f_empty | inc ix | call ev_sp     4 sites
          12  [TAIL] call penderr_set | ld de,0 | ret           4 sites
          12  [TAIL] ld (strptr),hl | pop hl | jp str_eval_ok   4 sites
          12  [sub]  call skip_spaces | or a | ret z | cp colon 5 sites

      ⚠️ **THE FIRST ONE IS THE DECLINED 18 B CANDIDATE'S TAIL** — the same four
      sites minus `ld a,$dd`. D-EVFERR's decline is about what a `jp ev_f_err`
      MEANS (failing with NO error code), so whether it also forbids the tail is
      an open question, not an inherited answer.
      🎯 **THE LAST ONE IS `req_operand`'S NEAR-TWIN** — the same
      end-of-statement test with `ret z` instead of a raise. Read it against
      `req_operand` and `scan_stmt_end` before treating it as new.
      💰 **NOT SPENT, AND THE REASON IS THE WALL, NOT THE RANKING**: page 1 was
      301 B free on 2026-09-02. At 12 B a slice, each costing a knife and a row
      set, the carve pressure that justified D-NGRAM2..19 is not there today.
      Re-read this when a slice is actually blocked on bytes.

- [ ] 📌 **ANY BATTERY OR KNIFE SCORE TAKEN 2026-08-30 EVENING .. 2026-08-31
      04:30 IS SUSPECT — THE HOST WAS ASLEEP UNDER IT.** Found 2026-08-31 by
      D-NOSLEEP2, [`docs/spec-nosleep2.md`](docs/spec-nosleep2.md).
      `caffeinate -i` asserts `PreventUserIdleSystemSleep` and does NOT block
      macOS's scheduled **'Maintenance Sleep'**, which fired on AC power at 100%
      charge: 15 minutes asleep, 45 seconds awake, repeatedly. A battery walled
      at **3861 s against 471 s** for the same ROM hashes, and
      `graphics-acceptance` reported a **977 s** stall against a **979 s** sleep.
      ✅ **FIXED**: `caffeinate -i -s -w <pid>`, at the `omsx_repl` chokepoint, so
      every probe and knife runner holds it.
      🔴 **AND THE OLD ARM PASSED ALL NIGHT** — `S1` asked whether *an* assertion
      was held and one always was, the idle one. New `S6` names
      `PreventSystemSleep`; re-planting the old flags makes S6 red while S1 stays
      green.
      ✅ **RE-VERIFIED 2026-08-31 ON AN AWAKE MACHINE**: the D-NGRAM14 arms
      re-run identically (S1 green, K-N14A moves exactly `r.atn r.round2 x.m100
      x.p100`), and D-CLOSALIAS's red/green plant was taken after the fix. The
      D-NGRAM12/13, D-TRUNCLOAD and D-DEADBODY batteries all walled at 449-476 s,
      which is the AWAKE wall -- a slept-through run walls at 3861 s, so the wall
      itself dates them outside the window.
      ➡️ **STILL OWED:** re-run anything ELSE scored in that window before
      building on it. **The wall time is the cheap discriminator.**
      🤖 AUTONOMOUS — a re-run settles each one.

- [x] 🟢 **`subrom-closure-check` CLASSIFIES A SUB-LOCAL `equ` ALIAS AS A
      MAIN-ROM ESCAPE.** Found 2026-08-30 by D-NGRAM14,
      [`docs/spec-basic-ngram14.md`](docs/spec-basic-ngram14.md) §5.
      `fexp_underflow equ fexp_overflow` in `sub/fp_exp.asm` -- the D-DUPSPAN2
      shape, keeping the name and both call sites -- was REFUSED: `FAIL: page-1
      escapes ... fexp_underflow = 4F5C <- main-BASIC page-1`. Both names
      resolve to the SAME address in `build/sub.sym`; the checker finds
      sub-local symbols by `label:` and its own header records why an `equ` may
      not count ("an `equ` is a VALUE, only a `label:` is a LOCATION" — without
      that rule 63 spurious escapes appear).
      ➡️ **THE FIX IS NARROW AND SAFE:** an `equ` whose VALUE equals the address
      of a known sub-local label IS sub-local. That reclassifies aliases only,
      and `build/sub.sym` already carries both sides of the equality.
      ⚠️ **AVOIDED, NOT WORKED AROUND**, in D-NGRAM14: the two callers name
      `fexp_overflow` directly, which costs nothing here — but the next sub-side
      alias will hit this again, and D-DUPSPAN2's whole method is aliasing.
      ✅ **FIXED 2026-08-31 (D-CLOSALIAS,
      [`docs/spec-closure-alias.md`](docs/spec-closure-alias.md))**: an `equ`
      whose right-hand side is a BARE IDENTIFIER already known sub-local is now
      sub-local too, resolved to a fixed point. 8 arms, 4 of them controls that a
      constant / an expression / an address literal / an alias of an unknown stay
      OUT — the label-only rule is repaired, not widened.
      🔴 **THE UNIT ARMS WERE NOT ENOUGH AND SAID SO**: arm `L1` reports the live
      tree has **0** such aliases (D-EXPNEG's was reverted), so the rule is
      vacuous today and unit arms could only prove the helper. Falsified
      end-to-end instead with a BYTE-IDENTICAL plant — rename one `jp
      fexp_underflow` to an alias — which is RED on the unfixed checker
      (`fexp_und_alias = 4F66 <- main-BASIC page-1`) and GREEN on the fixed one,
      with identical ROM hashes proving the plant changed only a name.
      ✅ **RE-VERIFIED 2026-09-01, NOT RE-READ** (this block was `- [ ]` and
      UNMARKED, so the loop could have re-picked it): `make subrom-closure-check`
      green on both tenancies, and `check_tenant_closure.py --selftest` green on
      all 8 arms including the 4 controls. **Closed.**

- [x] ✅ **`CVI(5)` READS `Syntax error` HERE AND `Type mismatch` ON THE
      CF-3300 — CLOSED 2026-08-31 (D-CVITM,
      [`docs/spec-basic-cvitm.md`](docs/spec-basic-cvitm.md)), and it took THREE
      dispositions, not one. 14 rows, DIFF 3 -> 0, +11 B, 3 knives, 48/48.**
      🎯 **THE FIRST FIX IS ZERO BYTES BECAUSE THE HELPER WAS ALREADY WRITTEN**:
      `ev_f_tmm`'s own header names `LEN(5)/ASC(5)/VAL(5)` and explains that
      FIRST-ERROR-WINS keeps a nested malformed string fn's syntax error. `CVI`
      simply was not wired to it — one operand changed.
      🔴 **A SECOND DIVERGENCE NOBODY HAD FILED**: `CVI("A")` (a 1-byte string)
      read one byte of the string and one of whatever followed, and answered a
      plausible `8769`; the reference says `Illegal function call`. Guarded on
      the descriptor's length byte (6 B).
      🔴 **AND MY FIRST CUT OVER-REACHED**: routing every decline to `ev_f_tmm`
      turned `CVI()` from Syntax error into Type mismatch. An EMPTY argument is a
      grammar fault and must be settled BEFORE the type question — the D-LEFTTM
      shape again, the fix is the ORDER. Caught by a row that already AGREED,
      kept because the domain was mapped rather than sampled (5 B).
      🔴 **AND IT HAD A HOLE, CLOSED THE SAME DAY BY D-CVISTRTM**
      ([`docs/spec-basic-cvistrtm.md`](docs/spec-basic-cvistrtm.md)):
      `CVI(0*(1/0)+1)` armed Type mismatch where both references answer Division
      by zero, because first-error-wins only splits the causes WHEN THE INNER
      THING ALREADY SET FPERR — and `str_eval` declines WITHOUT evaluating.
      **D-STRTM's own comment, in the file being edited, describes this exact
      trap.** Fixed the way it was fixed there: evaluate the operand, THEN defer.
      🎯 **AND THAT SUBSUMED THE `cp ')'` TEST**, which K-CV3 then measured as
      moving ZERO rows — `eval` meets the `)` and raises the syntax error itself.
      Test and knife both deleted, 5 B back, so the whole correction is +1 B.
      ⚠️ Original filing follows.
- [x] ✅ **CLOSED 2026-08-31 (D-FILEDROT) — ALREADY FIXED WHEN IT WAS FILED.**
      `CVI(5)` reads **`ERR 13` on the CF-3300 AND here**, re-measured with the
      refcache OFF. **`fef3d69` (D-CVITM) fixed it the same day this entry was
      written**, and D-CVITM found a THIRD wrong disposition (`CVI("A")`) while
      it was in there — see
      [`docs/spec-basic-cvitm.md`](docs/spec-basic-cvitm.md).
      🔴 **AND THE ROW WENT ON READING `DIFF` AFTERWARDS, FOR A DIFFERENT
      REASON.** `scratchpad/ngram15_probe.py` scored `b.cvi` against BOTH
      references, and the VG-8020 answers `Illegal function call` to every `CVI`
      — the exact structural problem for which `g.cvi` was already excluded. So
      the row said this tree was wrong while it AGREED WITH THE ONLY REFERENCE
      THAT CAN ARBITRATE. `b.cvi` joins `g.cvi` in `NO_ORACLE`; the probe is now
      0/12 DIFF. **A stale entry and a mis-scored row kept each other alive.**
      ⚠️ Original filing follows.
- [x] 🟢 **`CVI(5)` — THE ITEM WAS STALE ON THE DAY IT WAS FILED, AND THE ROWS
      ARE NOW SCORED RATHER THAN PARKED.** Filed 2026-08-31 by D-NGRAM15;
      re-verified and closed 2026-09-02.
      🔴 **THE PREMISE IS FALSE. `CVI(5)` reads `ERR 13` here**, and has since
      **D-CVITM (`fef3d69`) fixed it THE SAME DAY this was filed** — the probe's
      own source says so in a comment nobody re-read. Re-measured with the
      refcache OFF: `b.cvi` = `ERR 13 AT 60` on cf3300 AND zb.
      **A FILED DIVERGENCE ROTS LIKE A WALL** — check whether it still
      reproduces before costing a fix. [[a-ranked-candidate-rots-like-a-wall]]
      ✅ **AND THE `NO-ORACLE` PARK IS DISSOLVED TOO**, by the D-LSETREF argument
      applied to a second verb ([`docs/spec-basic-lsetref.md`](docs/spec-basic-lsetref.md)).
      Measured all four sides:

          row      vg8020     cf3000     cf3300      zb
          g.cvi    ERR 5      ERR 5      16961       16961
          b.cvi    ERR 5      ERR 5      ERR 13      ERR 13

      The National CF-3000 is a CASSETTE machine whose main BASIC ROM is
      **byte-identical** to the CF-3300's (same `<sha1>` in both openMSX XMLs),
      and it answers ERR 5 like the VG-8020. Same ROM, one has a drive ⇒ the
      split is the DISK ROM, and a machine without `CVI` **refuses the verb**
      rather than holding a second opinion. `NO_ORACLE` is now EMPTY in
      `ngram15_probe` (12 → 14 scorable, 0 DIFF).
      🔴 **AND THE SAME PASS PAID MY OWN DEBT**: `ngram11_probe` was STILL
      marking `g.lset`/`g.rset` NO-ORACLE four hours after D-LSETREF resolved
      them — the finding had landed in `lrvar` and `TODO.md` and not in the
      probe that filed it. Now empty there too (14 → 16 scorable, 0 DIFF).
      ⚠️ **THE ARGUMENT HAS A BOUNDARY, AND THE SWEEP FOUND IT.**
      `truncload_probe`'s six NO-ORACLE rows are a DIFFERENT cause —
      uninitialised-RAM history behind a truncated store, not disk-vs-cassette —
      and they legitimately stay.

- [ ] 🔴 **A FILED *FACE* ROTS WITHOUT THE ROW CEASING TO DIVERGE, AND NOTHING
      DETECTS THAT.** Found three times on 2026-09-04, each by hand while picking
      the item up:
      • the NAME rows — entry and the corrected comment in `basic/files.asm` both
        said `zb ERR 24`; both read **ERR 2** (noted 2026-09-02, and the entry
        called it "THIRD STALE FILING");
      • `LEN=r` — entry says `zb -> Syntax error`; both sides raise **ERR 5**, so
        the CODE agrees and only the domain differs (D-RECLENDOM);
      • the concatenation entry — its whole subject had been FIXED by D-CATFIX
        three days earlier and the box was never struck (D-CATGATE).
      🎯 **`filed_row_sweep` CANNOT SEE THIS CLASS, AND ITS OWN DESIGN SAYS WHY.**
      It adjudicates each divergent row as *known* / *unfiled* / *no longer
      diverging*. A row that still diverges but now diverges **to a different
      face** is `known`, and reads green. The 2026-09-04 run was **0 UNFILED, 0
      NO-LONGER-DIVERGING** on all 15 probes — and two of the three above were
      live at that moment.
      ⚠️ **THIS IS NOT "add faces to the pin file" WITHOUT A DESIGN.**
      `tools/filed-row-known.txt` is row-labels-only and its loader refuses a
      degenerate parse (`< 5` probes) on purpose; a face column would have to
      survive that refusal, and several probes in the corpus print faces the
      sweep cannot even parse into row names (`playfn` reads *"6 marker(s) in 0
      parsed line(s)"* and works only by substring containment).
      💰 Not priced. The cheap half may be that a face belongs in the PROBE's own
      pin, not in the sweep's — the `basic_probe_nodisk.py` `PINNED` dict already
      does exactly this for 8 rows and goes RED on drift **in either direction**,
      which is the shape this wants.
      🤖 AUTONOMOUS — the corpus and the failure mode are both in hand; what is missing is a design, not a decision.

- [ ] 🔴 **SEVEN FILED PROBES PRINT DIVERGENCES AND EXIT 0.** Measured
      2026-08-31 by D-FILEDROT,
      [`docs/spec-filed-row-rot.md`](docs/spec-filed-row-rot.md), instrument
      `scratchpad/filed_row_sweep.py` — every open TODO item's cited row set,
      re-run serially with the refcache OFF. **THE DENOMINATOR: 18 probes — 14
      diverge, 7 of those INVISIBLE to any rc-only collector, 2 clean, 2 with no
      verdict channel at all.**
      The seven: `deffn_alias_probe`, `keystr_probe`, `ntwall_probe`,
      `onerrarm_probe`, `open2_probe`, `playfn_fixture_probe`, `trapsvc_probe`.
      Several are divergences we have DECIDED not to fix (`keystr` is the
      NOT-THIS-ONE `KEY n,"str"` item, ~160 B), so the fix is NOT "make them
      exit 1" — a deliberate non-fix must still be VISIBLE, and a probe cannot
      tell the two apart. What is owed is a convention that separates *measured
      and known* from *measured and unnoticed*.
      🔴 **AND THERE IS NO VERDICT CONTRACT TO BUILD ON**: the 18 probes use
      **eight** output shapes and two rc conventions. The sweep reads markers
      and rc as INDEPENDENT channels for exactly that reason, and refuses to
      call anything clean when they disagree.
      ✅ **CONVENTION LANDED 2026-08-31 (same day):**
      `tools/filed-row-known.txt` pins, per probe, the divergent rows a
      filed item OWNS — named by the owning entry's HEADING, because line
      numbers rot. The sweep adjudicates every marker line against it and the
      verdict now reads `[N known]`, `🔴 UNFILED — read them`, or `⚠️ NO LONGER
      DIVERGING — the CVI shape, re-run and re-file`. **Measured on all 18: 0
      unfiled, 0 stale — every divergence in the corpus is owned by an entry.**
      Falsified by planting BOTH directions on the same output (a dropped known
      row reads UNFILED; a ghost row reads NO-LONGER-DIVERGING; the unmodified
      control reads neither). The set is pinned; the judgement is not.
      📏 **RE-RUN IN FULL 2026-09-02 (13 probes, serial, refcache OFF).** The
      corpus shrank 18 → 13 because five items closed; **0 UNFILED, 0 NO-LONGER-
      DIVERGING** across all thirteen. The one stale pin the day produced —
      `onerrarm_probe`'s four rows, fixed by D-ONERRGO an hour earlier — was
      found and removed by hand before this run, which is the debt a fix leaves
      when it does not move the pin with it.
      ✅ **AND THE RUN CLOSED THE `reclen_probe` HOLE (D-RECLENV).** It reported
      `🔴 NOTHING PARSED`, and the sweep's own source says why: *"a two-column
      table, NO verdict word anywhere -- an EIGHTH shape that simply has no
      channel to read"*. That refusal is honest, but the consequence was that a
      probe documenting an **untrappable hang** (D-PUT3) was invisible to the one
      instrument built to notice unnoticed divergences. It now emits per-row
      `DIFF <label>` markers and a `DIFF: n/m` summary, and the sweep reads
      `DIVERGES 4/7 ... [4 known]`.
      🔴 **A NAIVE DIFF COUNT WOULD HAVE BEEN WRONG, AND THAT IS THE DESIGN.**
      Ten `k./x./ctl./s.` rows read blank on zb as a CONSEQUENCE of that same
      hang (their programs issue 3+ PUTs). Counting them would inflate ONE defect
      into fourteen and claim record-layout evidence the run does not have, so
      they are reported separately and **deliberately NOT pinned**. The split is
      derived from the CASES data, not a hand-kept list that would drift.
      🔴 **AND THE FIRST CUT OF THAT CHANNEL DID NOT WORK** — a `DIFF:` summary
      alone made the sweep say *"0 known, ⚠️ 4 known row(s) NO LONGER DIVERGING"*
      while listing those four AS DIVERGING: its `MARKER` wants `DIFF` followed
      by whitespace, and `DIFF:` has a colon. Caught by RUNNING the sweep against
      the file rather than assuming the channel worked.
      📌 **12 of 13 now have a readable verdict channel.** `budget_probe` is the
      last, and it is a TIMING TABLE with no verdict concept at all — an honest
      unparsed, not a hole.
      🤖 AUTONOMOUS — what remains is keeping the file honest as entries close,
      and the sweep now says so itself when one rots.

- [x] ✅ **D-OOMTAIL (2026-08-31): the two store-overflow exits share one
      body — +13 B main page 1.** `ctp_oom`'s seven-instruction tail was
      byte-for-byte `dpl_oom`'s whole body (its own comment said "mirrors
      dpl_oom"); it is now `jp dpl_oom`.
      [`docs/spec-basic-oomtail.md`](docs/spec-basic-oomtail.md), probe
      `scratchpad/oomtail_probe.py` — both exits WITNESSED for the first time
      (castail's spec records them differentially unreachable; the functional
      rows reach them by exceeding the REAL bound, a fixed `$BB00`, with a
      ~17 KB fixture). zb rows IDENTICAL before/after the carve; the probe was
      wrong four ways first and the spec names each. The 17 KB fixture's
      CF-3300 divergence is the SETTLED D-LINEMAX/D-FCH ceiling (14079 B by
      measurement) — rows print ADJ and are pinned in
      [`tools/filed-row-known.txt`](tools/filed-row-known.txt), the D-FILEDROT
      convention's first live entry.

- [x] ✅ **D-MUSICF (2026-08-31): a PLAY naming FEWER voices stopped a
      still-playing voice's drain WITHOUT silencing it.** Found by Joost's
      review request over the PLAY implementation, then measured: `pt_commit`
      stored `AUDIO_VMASK` into `MUSICF` wholesale, so `PLAY"C"` while voice B
      was mid-music cleared B's bit — drain stopped, `psv_end` (the only amp-0
      writer) unreachable, channel sounding FOREVER, `PLAY(2)` idle under an
      audible tone. Both references keep the voice playing (`r.drop`:
      -1/-1/**0**). Fix: OR into `MUSICF` (+2 B sub p1); 5/5 SAME after.
      [`docs/spec-basic-musicf.md`](docs/spec-basic-musicf.md),
      `scratchpad/gicini_probe.py`.

- [x] ✅ **D-PLAYCORNER (2026-08-31): the three PLAY corners MEASURED — two
      were real, one holds.**
      [`docs/spec-basic-playcorner.md`](docs/spec-basic-playcorner.md),
      `scratchpad/playcorner_probe.py`, 10 rows x 3 machines, **5 DIFF -> 0**.
      (1) `pt_number`'s 16-bit wrap was REAL x4: `T65568`/`O65537`/`V65551`/
      `M65600` all ERR 5 on both references, all accepted here by aliasing into
      range. Fixed: overflow latch (`PLY_NUMOVF`, the byte the unused `PLY_NUM`
      declaration held) + saturate to $FFFF so every 8-bit range check rejects
      with ZERO call-site changes; `M` reads the latch (m.max: `M65535` is
      LEGAL, so the $FFFF value alone cannot decide). (2) `M0` was REAL: ERR 5
      on both references, accepted here. Fixed alongside. (3) The edge
      accidental clamps HOLD at the accept/reject level (`O1 C-` and `O8 B#`
      play on all three).
      ✅ **AND THE NARROW RESIDUAL WAS THE REAL FINDING (D-CLAMPPITCH, same
      day,** [`docs/spec-basic-clamppitch.md`](docs/spec-basic-clamppitch.md)):
      the trace shows the reference's accidental **wraps the semitone mod 12
      INSIDE the octave** — `C-` plays B of the SAME octave, `B#` plays C of
      the SAME octave, at EVERY octave — so the "edge clamp" was wrong
      mid-range too, and the accept/reject rows were blind to it by
      construction. Two rules coincided on every edge row; the mid-octave rows
      separated them. Fixed (accidental before octave base, mod 12; clamp
      deleted as unreachable); 8/8 traces identical, fast-layer vectors added.

- [x] ✅ **D-GICINI — AN ABORTED PROGRAM KEPT PLAYING FOREVER, AND THE DEFERRAL
      SWEEP POINTED STRAIGHT AT IT.** Found and fixed 2026-09-03,
      [`docs/spec-basic-gicini.md`](docs/spec-basic-gicini.md).
      `basic/sound.asm` deferred a GICINI-equivalent to *"Slice 2"* on the
      grounds that *"there are no PLAY queues / MUSICF to zero yet"*. The queues
      shipped; nothing watched the trigger. **Six divergent rows**, both
      references agreeing on every one, `PEEK(&HFB3F)` (MUSICF, a published work-
      area address zerobas places deliberately):

          e.untrap / e.errnat   untrapped error in a program   refs 0   here 1
          e.errdir              the same error typed direct     refs 0   here 1
          e.stop / e.cont       STOP, and CONT afterwards       refs 0   here 1
          m.beep                BEEP during an active drain     refs 0   here 1

      🎯 **THE DEFERRAL NAMED THE WRONG THING.** It promised an *init*; what was
      missing is a *teardown*. Reading the file would never have said so — only
      the reference would.
      🟢 **THE ROWS THAT MAKE THE RULE PRECISE ARE THE ONES THAT AGREE**: a clean
      `END` leaves the music playing on all three (so the trigger is ABORT, not
      "back to `Ok`"), a TRAPPED error leaves it playing (so it is not error-
      raising), and `SOUND` — including a mixer write to R7 — never touches the
      queue (so `BEEP` is not clearing it merely by being a PSG writer).
      🔬 **AND THE FIX HAD TO SILENCE, NOT JUST ZERO MUSICF** — measured, not
      argued, with `probes/lib/psgtrace.py`: both references drop the tone
      amplitude to 0 at the abort; zerobas held the note at volume 8 forever.
      🔴 **THE ROW SET LIED TWICE ON THE WAY, IN THE SAME WAY.** `omsx_repl`
      types one line per 8 s slot and the first `PLAY` ran ~16 s, so any row with
      two typed lines after it outlived its own queue: four rows read as
      "zerobas already matches" (`e.errdir`, `e.new`, `e.cont`, `e.nop`) and
      **`NEW`'s answer was the exact opposite of the one recorded**. Caught by
      `e.nop`/`e.nop2` — a HARMLESS statement in the subject's position, written
      to fail if the fixture outlived the case. Re-measured at `T32` (7.5 s per
      whole note). The identical artefact then bit the two `e.replay` rows and
      was caught immediately, because by then it had a name.
      💰 **COST: page-0 low region 106 → 79 B free, page 1 272 → 269 B** (read
      from `make basic-reloc`, before and after). One 21 B routine, three 3 B
      call sites.
      📏 **0 DIFF / 36 rows** on three machines afterwards, including
      `e.replay`/`e.replayfn` — a `PLAY` after the abort still works, so the
      queue is left reusable and not merely quiet.

- [x] ✅ **D-FACZERO — ZERO KEPT THE PREVIOUS VALUE'S MANTISSA.** Found and
      fixed 2026-09-03, [`docs/spec-basic-faczero.md`](docs/spec-basic-faczero.md).
      Found by [`scratchpad/mkfloat_scout.py`](scratchpad/mkfloat_scout.py) while
      SIZING the MKS$ slice below — asking "is our stored float byte-identical to
      the reference's?" (it is: 1.5 -> `65 21 0 0`, 1/3 -> `64 51 51 51 51 51 51
      51`, so MKS$ really is MKI$ with a different length).
      **12 of 29 rows diverged.** Every zero exit wrote the LEAD BYTE ONLY and
      left the mantissa holding whatever the destination contained:

          A!=0                refs 0 0 0 0   here 0 255 255 255
          A!=1.5 : A!=0       refs 0 0 0 0   here 0  21   0   0   <- 1.5's OWN byte
          A!(1)=0 / READ A! / DEFSNG B : B=0 / the double forms: all the same

      🎯 **`z.reassign` NAMES THE MECHANISM** — 21 is 1.5's mantissa byte. A read
      of stale memory wearing the value's clothes.
      🟢 **INVISIBLE BECAUSE LEAD BYTE 0 *IS* "THE VALUE IS ZERO"** — flt_out
      never reads further, so every zero always PRINTED correctly. `A!=0.0` was
      green even before the fix (a dotted literal crunches as a float and packs a
      real mantissa; a bare `0` crunches as an INTEGER and reaches the store
      through the int->single widen). Two spellings, two paths, one wrong.
      ⚠️ **AND IT WOULD NOT HAVE STAYED INVISIBLE** — `MKS$(0)` emits these exact
      bytes as a STRING that a program writes to a file. Caught before the verb
      could ship the divergence to disk.
      🔬 **THE DENOMINATOR CHOSE THE SITE.** Scalars, arrays, READ and DEFSNG all
      diverged and have different store paths, but all of them `ldir` from FAC —
      so the fix is at the two PACKER zero exits, not at `var_store_fac`, which
      would have left `z.arr` and `z.read` behind.
      🔴 **AND A THIRD CALL SITE WAS DELETED BECAUSE ITS OWN KNIFE FAILED.** K-FZ3
      removed the `vars.asm` unset-arm call and moved ZERO rows — including the
      two rows added specifically to witness it — because `A!=B!` RE-PACKS rather
      than handing FAC's bytes to the store. 3 bytes no row could defend, so they
      are gone; the spec records the condition that brings them back.
      💰 **COST: page-0 low region 79 -> 63 B free; page 1 UNCHANGED at 269 B.**
      📏 **0 DIFF / 31 rows**, knives 2/2 on the arms that survived.

- [x] ✅ **D-MKSD — `MKS$` / `MKD$` / `CVS` / `CVD` SHIP.** 2026-09-03,
      [`docs/spec-basic-mksd.md`](docs/spec-basic-mksd.md).
      **The real defect was that they were absent from
      [`basic/kwtable.inc`](basic/kwtable.inc) entirely** — 148 entries, only
      `MKI$` and `CVI` from the family — so `MKS$(1.5)` was never tokenised as a
      keyword: it parsed as the string ARRAY `MKS$(1)`. That is the mechanism
      behind the filed "MKS$ returns an empty string", and a SILENT WRONG ANSWER.
      📏 **0 DIFF / 32 rows** (cf3300 vs zb) including every error case, the byte
      formats, the coercion rounding and the domain. The VG-8020 column is
      printed throughout: it answers ERR 5 to all of them, which is the
      disk-vs-cassette split D-LSETREF settled, shown rather than asserted.
      🔬 **`MKS$` EMITS EXACTLY WHAT THE VARIABLE STORE HOLDS** — `MKS$(1.5)` is
      `65 21 0 0`, byte-identical to `PEEK(VARPTR(A!))` for `A!=1.5`. So the
      coercion is the same widen+round/pack pair `var_store_fac` uses, not a
      private encoder that could drift from it.
      ⚠️ **`MKS$(0)` is `0 0 0 0` on the reference and would have shipped here as
      `0 255 255 255`** — D-FACZERO fixed that the day before, and was itself
      found by the scout that was only SIZING this slice.
      🎯 **THE WIDTH *IS* THE FACTYP CODE** (2/4/8 for int/single/double), so one
      register sizes the length check and types the result; K-MK4 exists to prove
      the code depends on it. Two shared bodies, so `CVS`/`CVD` inherit `CVI`'s
      error ordering (D-CVITM, D-CVISTRTM) instead of re-deriving it twice.
      💰 **COST: main page 1 269 -> 164 B free; sub-ROM page 0 1992 -> 1962 B**
      (the four table entries — the table has a single copy and it lives there).
      Low region unchanged at 63 B. ⚠️ Five `jr`s became `jp`s in `strvar.asm`:
      the new body pushed `str_eval_no` out of relative range.
      📏 **DENOMINATOR:** `make kwsweep` went `SILENT-GAP=2 MISSING=2
      SUPPORTED=31` -> **`DIVERGENT=1 SUPPORTED=35`**, all five MK/CV words
      `present SUPPORTED match`. The lone DIVERGENT is `csrlin`, the documented
      probe artifact.
      🔴 **KNIVES 4/4 — after THREE faults in the knife harness**, none of them in
      the fix: a row parser that ate the count and failed all four arms; a ROM
      guard hashing the main ROM when the keyword table lives in the sub-ROM; and
      the guard's own INERT fast path finishing inside `make`'s 1-second mtime
      resolution, so the next arm built against a STALE sub-ROM and measured the
      previous plant. I then inherited that contaminated result as a prediction.
      Spec §5.1.

- [x] 🟢 **"RND NOT YET IMPLEMENTED" — THREE STALE COMMENTS, NO DEFECT.** Same
      sweep, same day. `basic/sysvars.inc` said it three times; `fp_rnd` ships as
      a sub-ROM tenant and `RND(1)`, `RND(0)`, `RND(-1)` all work, with the value
      in [0,1) on all three machines (`r.range` = 1 everywhere).
      🎯 **A VALUE ROW CANNOT TEST RND** — it is random, so the rows ask only what
      the comment raises: does it EXIST and is it in range. Corrected in place.

- [x] ✅ **D-MKHOOK — THE HOOK MECHANISM WORKS, PROVED ON `MKI$`.** 2026-09-03,
      [`docs/spec-basic-nodisk.md`](docs/spec-basic-nodisk.md) §9.
      **The first BASIC-extension hook zerobas has ever claimed, and the first it
      has ever CALLED** — `HPHYD` was installed for foreign hosts and never
      invoked here, so the whole round trip (main page 1 -> a RAM `CALLF` stub ->
      `RST 30h` across slots -> `disk.rom` -> back) was unproven.

          LEN(MKI$(258))   vg8020 ERR 5   zb-disk  2    zb-nodisk ERR 5 ✅
          ASC(MKI$(1))     vg8020 ERR 5   zb-disk  1    zb-nodisk ERR 5 ✅
          CVI(MKI$(258))   vg8020 ERR 5   zb-disk 258   zb-nodisk ERR 5 ✅

      📏 **Pins 8 -> 5** in `nodisk-acceptance`; the three rows are now scored as
      ordinary agreeing rows so the gate enforces they STAY fixed. ⚠️ `k.cvi`
      moved because its ARGUMENT is `MKI$` — **CVI itself is not hooked yet**, and
      `v.cvistr` (`CVI("AB")`) still measures CVI alone and is still pinned.
      🟢 **No regression on the disk side**: `mksd_probe` 0 DIFF / 32.
      💰 **COST: main page 1 164 -> 146 B free.** Gating one verb COSTS 18 B, which
      is §8's arithmetic playing out — this migration buys FAITHFULNESS, not space.
      🔧 `install_hook` factored out of `disk/init.asm` into the free corridor: the
      pad before the `$41EF` pin is 25 B and one inline install had spent it all, so
      a second overran and pasmo emitted an EMPTY image (`pad_rom.py` refused it,
      exactly as its header describes). 9 B per hook now, not 25.
      🔴 **KNIVES 2/2 — after THREE faults in the harness, none in the fix**: the
      comparison ran backwards; `os.utime(+1)` on restore left files dated in the
      FUTURE so the next arm went INERT; and stamping the plant forward too made
      the source permanently newer than the ROM, so the PREFLIGHT REFUSED TO
      MEASURE — **and the scorer read that refusal page as "agrees on
      everything"**. The scorer now refuses a run with no verdict line, and the
      arms delete the ROMs instead of playing with mtimes.
      📋 **NEXT:** `MKS$`/`MKD$` share `str_mkf` with `MKI$`, so they need a
      per-verb hook address at the shared call site; `CVI`/`CVS`/`CVD` share
      `ev_ff_cv`; `DSKF` has almost no main-side body (spec §8).

- [x] ✅ **DISK-BASIC VERBS NOW GO THROUGH THE DOCUMENTED HOOKS — the diskless
      build is faithful. (Joost's question AND his decision, 2026-09-03.)**
      Completed by D-MKHOOK the same day, [`docs/spec-basic-nodisk.md`](docs/spec-basic-nodisk.md) §10.
      **`nodisk-acceptance` pins 8 -> 0**: every verb that needs no medium
      (`MKI$` `MKS$` `MKD$` `CVI` `CVS` `CVD` `DSKF`) is routed through its own
      documented hook, so a diskless zerobas REFUSES because the handler is not
      there — the way the reference does it. Disk build unchanged (`mksd_probe`
      0 DIFF / 32).
      🔴 **AN EMPTY PIN SET IS THE STRICTEST STATE THIS GATE HAS**, not the
      weakest: every row is now scored against the oracle, and a NEW disk verb
      that answers on a diskless build lands as a red row rather than as an entry
      someone must remember to add.
      💰 **COST: main page 1 164 -> 75 B free** (2026-09-03) — 89 B to gate seven
      verbs, pure overhead because this slice moved no bodies. ⚠️ **75 B is
      tight** and the next page-1 slice must reckon with it; §8 measured ~50 B of
      conversion that could still follow into `disk.rom`, which would claw most of
      it back — a separate slice that must justify itself.
      🔴 **KNIVES 4/4**, and two are the batch's own argument: dropping `H_CVS`
      costs ONLY the CVS row while dropping `H_MKS` costs the MKS$ row AND the CVS
      row (which builds its argument with `MKS$`). A blanket presence check would
      have moved both arms alike — that asymmetry is what proves the selection is
      per-verb.
      🔴 **AND THE CHANNEL VERBS WERE NEVER "UNREADABLE" — that exclusion is
      WITHDRAWN the same day** ([`docs/spec-basic-nodisk.md`](docs/spec-basic-nodisk.md) §11).
      I wrote twice that `OPEN`/`FILES`/`KILL`/`NAME` return *"the FIXTURE's `load
      error` … an UNREADABLE cell, not a divergence"*, once arguing that counting
      them "would have inflated this finding by a third". **`load error` is
      zerobas's OWN message**: the machine prints it and carries on — a following
      `PRINT"C"` still answers. Traced directly, `PRINT"A":FILES` gives `A` then
      `Illegal function call in 10` on the VG-8020 and `A` then `load error` here.
      So they were always readable and always divergences: the oracle REFUSES
      because the verb does not exist, while zerobas RUNS it and fails on the
      MEDIUM. **4 rows the gate had been blind to, now scored and pinned:**

          h.files  oracle ERR 5  here `load error`   H.FILE $FE7B unclaimed
          h.kill   oracle ERR 5  here `load error`   H.KILL $FDFE unclaimed
          h.name   oracle ERR 5  here `load error`   H.NAME $FDF9 unclaimed
          h.open   oracle ERR 2  here `load error`   -- different class

      ⚠️ `h.open` is pinned as CHARACTERISATION, not as a hook candidate: the
      oracle answers Syntax error because `FOR OUTPUT` is not parseable at all
      without Disk BASIC — a keyword-surface question no handler hook fixes.
      🎯 **"I do not recognise this output" and "the instrument failed" look
      identical until you look.** The probe's own scorer carried the same premise
      (it treated the STRING `load error` as an apparatus failure); that rule is
      gone, and only a genuinely absent capture counts as unreadable now.
      ✅ **DONE THE SAME DAY (D-CHANHOOK)**: `FILES`/`KILL`/`NAME` go through
      `H.FILE`/`H.KILL`/`H.NAME`, diskless answers ERR 5 like the oracle, disk
      build unchanged. `nodisk-acceptance` 16 rows PASS with **1** pin (`h.open`,
      characterisation). 🔴 **COST: page 1 75 -> 39 B free (2026-09-03) — the
      tightest it has been**, and the next slice cannot ignore it.
      ✅ **AND THE BLOCKER IS GONE (D-DISKABI, same day)** —
      [`docs/spec-basic-nodisk.md`](docs/spec-basic-nodisk.md) §13.
      `disk/basic-resident-abi.inc` is generated per build by the SAME
      `tools/gen_resident_abi.py` the sub-ROM uses (a PROFILE, not a fork, so the
      two cannot drift); `make diskrom-abi-check` is the standing assert and
      `patch-freshness-check` now covers it as `abi-disk` — that gate's own header
      records the sub-ROM copy having been **stale in HEAD across 11 commits**
      before it was covered.
      🎯 **AND IT IS WITNESSED, NOT SPECULATIVE**: `hk_mkfloat` — `MKS$`/`MKD$`'s
      round-and-pack — now runs INSIDE `disk.rom`, the first disk-verb body
      actually to live there rather than merely be gated from there.
      💰 **Page 1 39 -> 61 B free** (2026-09-03), 22 B recovered.
      🔴 **TWO REGISTER MISTAKES, BOTH CAUGHT BY MEASUREMENT.**
      `widen_rhs_operand` CANNOT move: for an INTEGER argument it reads `DE`,
      which `CALSLT` does not preserve — moving it broke `MKS$(0)`, `MKS$(1)`,
      `MKD$(7)`, `MKS$(3%)` while every FLOAT argument stayed green (5 DIFF).
      Then the repair went in AFTER `HL` held the hook address and clobbered it —
      24 DIFF, controls included. ⚠️ So the recovery is **22 B, not the 37 B the
      first build reported**: that number was measured on a ROM that did not work.
      ⚠️ Superseded, kept for the reasoning — §8's ~50 B of movable conversion would
      now be PURE recovery (the gates are already paid for), but **`disk.rom` has
      no main-ROM ABI bridge** — `sub/basic-resident-abi.inc` is generated for the
      sub-ROM alone, so `disk/*.asm` cannot see `ARGA`/`STRSCR`/`FAC` or
      float-arith. Building the equivalent (a generated include + a staleness
      check, mirroring `tools/gen_resident_abi.py`) is the prerequisite and is a
      slice of its own.
      🎯 **A REGRESSION THE GATE CAUGHT THAT REVIEW DID NOT**: the first cut
      clobbered HL — the statement cursor — to load the hook address, and all
      three verbs answered ERR 2 **on the DISK build** while the diskless side
      looked perfect. The `zb-disk` column is in that table for exactly this.

      *(original question, kept for the reasoning:)*
- [x] 🙋 **SHOULD THE DISK-BASIC VERBS LIVE IN `disk.rom` BEHIND A HOOK, AS ON
      REAL HARDWARE? (Joost's question, 2026-09-03.)** Raised while D-MKSD was
      landing `MKS$`/`MKD$`/`CVS`/`CVD` into the MAIN ROM.
      🟢 **THE KEYWORD-TABLE HALF IS SETTLED AND MEASURED: main-ROM placement is
      FAITHFUL.** Pointed at the DISKLESS Philips VG-8020
      (`basic_probe_kwsweep.py --disk-machine Philips_VG_8020 --layer crunch`),
      all five MK/CV words crunch **SAME** as zerobas — the VG-8020 tokenises
      `MKS$` to `FF AF` with no disk ROM present. So on real MSX the MAIN ROM
      owns the crunch table and the disk ROM supplies only the IMPLEMENTATION,
      via hooks. That is exactly why a diskless machine tokenises `MKS$` happily
      and then answers ERR 5 at execution.
      🔴 **THE IMPLEMENTATION HALF IS A REAL, STANDING DIVERGENCE, AND IT LONG
      PREDATES D-MKSD.** `disk/disk.asm`'s own header says zerobas-BASIC reaches
      the file layer through the BDOS SYSTEM vector with CALSLT, *"NOT through
      the H.* / HPHYD chain; HPHYD exists for FOREIGN hosts"* — `disk.rom` is a
      STORAGE PROVIDER and carries no BASIC-extension hook at all. So every disk
      verb (`FILES` `KILL` `NAME` `OPEN` `FIELD` `MKI$` `CVI` …) is implemented
      BASIC-side, and has been since Phase 1.5.
      📏 **MEASURED, NOT ARGUED — AND IT IS 8 ROWS.**
      ⚠️ The first draft of this item called the consequence "a divergence in
      PRINCIPLE, not one a user can currently reach", because every installed
      machine carries `disk.rom`. **Joost: "it should also be possible to ship
      zerobas without a disk ROM."** That makes it reachable, so it was measured
      instead ([`scratchpad/nodisk_probe.py`](scratchpad/nodisk_probe.py)):
      `ZB_REPACK_NODISK`, the shipped repack machine with the disk.rom slot
      removed and nothing else changed, against the VG-8020 — which IS that
      configuration on real hardware.

          row        vg8020    zb-nodisk
          k.mks      ERR 5      4          MKS$/MKD$/CVS -- D-MKSD, today
          k.mki      ERR 5      2          MKI$/CVI      -- shipped LONG ago
          k.cvi      ERR 5      258
          v.dskf     ERR 5      0          DSKF
          v.cvistr   ERR 5      16961
          🟢 c.print / c.str  identical -- the diskless machine boots and runs
          🟢 v.eof / v.lof    ERR 59 on ALL THREE -- already refuse correctly

      🎯 **THE SHAPE IS SHARPER THAN "DISK VERBS LEAK": it is exactly the disk
      verbs that need NO MEDIUM.** `EOF`/`LOF` want a channel and already raise;
      the CONVERSION functions and `DSKF` compute an answer and so answer.
      ⚠️ Four rows (`OPEN`/`FILES`/`KILL`/`NAME`) read the fixture's `load error`
      on a diskless machine — UNREADABLE, and explicitly not scored; counting
      them would have inflated this by a third.
      🔴 **AND IT IS NOT NEW WITH D-MKSD** — `MKI$`, `CVI` and `DSKF` show it too,
      so this is the standing architecture, not something today's slice broke.
      🔴 **I MEASURED THE DISK ROM'S SPACE WRONG, AND JOOST CAUGHT IT.** This
      item first said moving the verbs was "NOT AN OBVIOUS SPACE WIN", on the
      grounds that `build/disk.rom` had "a trailing free run of 2 bytes". That
      was a TRAILING scan, which cannot see interior holes — and Joost's reply
      was *"there's holes, plenty of space"*. Re-measured 2026-09-03 by scanning
      for interior fill runs: **9012 bytes of 0x00 fill across 32 runs >= 16 B**,
      the largest being **3420 B at $2849** and **2531 B at $1602** (mapped
      $6849 / $5602). Main page 1 was **164 B** free on 2026-09-03. So the move
      is a LARGE space win, not a neutral one, and the claim that priced it out
      was an instrument error of exactly the kind this project keeps filing
      against other people's numbers.
      ⚠️ Not all 9012 B are necessarily free: the disk ROM has pinned
      fixed-offset entry points and stub bodies at known addresses, so a real
      figure needs a disk-ROM WALL CHECK, which does not exist
      (`make basic-reloc` reports main and sub walls only). The two large runs
      are the candidates.

      🧭 **DECIDED IN PART (Joost, 2026-09-03): "the diskless zerobas should be an
      official build target and any disk related thing should be validated on
      both."** Shipped that same day:
      * **`C-BIOS_MSX1_EU_REPACK_NODISK`** — same merged main ROM and sub-ROM,
        slot 3-1 empty; `tools/install-repack-machine.py --no-disk`, and
        `make repack-machine` installs BOTH so neither can go stale.
      * **`make nodisk-acceptance`** — in the battery. Oracle: the VG-8020, which
        needs no argument, being that configuration on real hardware.
      * The 8 divergences are **PINNED to their exact values**, so the gate goes
        RED if either column changes — a regression AND an unannounced fix both
        show. Also listed in [`tools/filed-row-known.txt`](tools/filed-row-known.txt).
      ⚠️ **ANY NEW DISK-RELATED VERB OR FIX ADDS ITS ROWS TO THAT PROBE.** That is
      the "validated on both" half of the directive and the part most likely to be
      forgotten.
      🧭 **AND THE ARCHITECTURAL HALF IS NOW DECIDED TOO (Joost, 2026-09-03):**
      *"not only should diskless match vg8020 and withdisk the cf, the
      implementation of the disk related keywords should probably be in the disk
      rom (there's holes, plenty of space) and work via the officially documented
      hooks."*
      So the target shape is: **main ROM keeps the keyword TABLE** (measured
      faithful — the diskless VG-8020 crunches `MKS$` to `FF AF`), and the
      **BODIES move into `disk.rom`, reached through the published MSX BASIC
      expansion hooks**. Diskless then matches the VG-8020 *because the code is
      not there*, which is how the reference gets it right, rather than by a
      guard bolted on.
      ⚠️ **THE HOOK SET MUST COME FROM A PUBLISHED SOURCE AND BE CITED** (MSX
      Technical Handbook / MSX Assembly Page, into PROVENANCE) — NOT from
      recall. It is also directly measurable without any document: diff the hook
      RAM region between the VG-8020 (no disk) and the CF-3300 (disk) and the
      differences ARE the hooks disk BASIC installs. Do that first; it is an
      observation of an interface boundary, the same class as the already-published
      HPHYD -> DSKIO vector, and it needs no disassembly.
      📋 **SCOPE:** this is a multi-slice migration (`MKI$` `MKS$` `MKD$` `CVI`
      `CVS` `CVD` `DSKF` first — the no-medium verbs the gate already pins — then
      the channel verbs). Each slice must leave `nodisk-acceptance` GREEN with its
      pins MOVED, since a fixed row that keeps its old pin is the failure mode
      that gate was built for.

- [x] ✅ **D-PUSTAR — `PRINT USING`'s `**` ASTERISK FILL SHIPS** (2026-09-03,
      [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md)), the first of the
      six. `"**##"` gives `***5` / `**-5` / `1234`, matching both references.
      🔬 **The full contract for all six is now measured**:
      [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py), **36 rows on
      which both references AGREE**, 3 carried as NO-ORACLE (`$$`, `&`, `\ \` —
      the references split on those and zerobas matches a different one in each,
      which is worth its own look).
      💰 **AFFORDABLE ONLY BECAUSE THE SCANNER IS NOT IN PAGE 1**:
      `basic/pu-render.inc` is included ONLY by `sub/printusing.asm`, so
      recognition and width accounting cost SUB-ROM bytes and just the pad-char
      choice touches page 1. **Page 1 61 -> 50 B; sub page 0 1962 -> 1894 B.**
      `PU_FLAGS` bit 2 — no new RAM cell.
      🔴 **KNIVES 2/2, and `a.full` is the evidence**: it emits NO padding, so
      killing the FILL cannot touch it while killing the WIDTH makes it overflow.
      Two claims, separated. ⚠️ Round 1 predicted both sets without `a.dot` and
      both arms read FAIL — `**#.##` exercises `**` even though its `.` half is
      unimplemented. The arms were right; the prediction was short.
      ✅ **AND `+` / `-` SHIP TOO (D-PUSIGN, same day)** — six more rows:
      `+##` gives ` +5` / ` -5`, `##+` gives ` 5+` / ` 5-`, `##-` gives ` 5 ` /
      ` 5-`. **THREE transformations, not one**: prepend `+`, append `+`-or-SPACE,
      and MOVE the leading `-` to the end (where it stays `-` even under `##+`).
      `+##` with a NEGATIVE needs nothing at all — `pu_fmt_int` already wrote it.
      💰 Sited sub-side for SPACE, not structure: pure RAM work over `NUMBUF`,
      ~60 B, and page 1 had 50. `pu_sign_tenant`, page-0 index 15, closure trivial
      (no main-ROM call); main pays 18 B for the flag test and the CALSLT.
      **Page 1 50 -> 32 B; sub page 0 1894 -> 1668 B.**
      🔴 **KNIFE 1/1, and the rows that must NOT move are the claim**: dropping the
      leading-`-` removal moved `p.trailneg` and `n.neg` and left `p.trail` /
      `n.pos` alone. Had the positives moved too, the arm would only have said
      "trailing signs exist", which the six green rows already say.
      🔴 **AND THE PLAIN `#` FIELD IS ITSELF WRONG — my controls were too narrow
      to see it** ([`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §5):

          PRINT USING"#######";1234567   refs 1234567   here `      0`
          PRINT USING"#####";1.5         refs `    2`   here `    1`
          PRINT USING"#####";2.5         refs `    3`   here `    2`

      None involves a specifier. `pu_do_number` evaluates to a 16-bit DE and
      formats with `pu_fmt_int`, so the numeric field is INTEGER-ONLY and
      TRUNCATING: past int16 it silently renders 0, and a fraction is chopped
      where both references ROUND HALF-UP. The int16 boundaries themselves
      (32767, -32768) are exact on all three.
      🎯 **THE CONTROLS ARE WHY IT HID**: `c.hash`/`c.neg`/`c.over` all used SMALL
      INTEGERS, agreed, and I read that as "the `#` field is already right". A
      control only certifies the ground it stands on.
      ✅ **D-PUNUM SHIPPED THE RENDERER (same day)** — `pu_num_tenant`
      (`sub/punum.asm`), a sub-ROM **PAGE-1** tenant calling the main ROM's OWN
      `flt_fmt` through the generated ABI, so `PRINT USING` and `PRINT` cannot
      disagree about what a number looks like. **4 fixed, 0 broken**: `c.over16`
      `1234567`, `c.round` 2, `c.round2` 3, `d.roundup` ` 2.`. The integer path
      stays for `FACTYP==2` (already correct at both boundaries, and cheaper).
      🎯 **Rounding the rendered TEXT is EXACT** — MSX floats are BCD, so
      `flt_fmt`'s decimal output IS the value; no binary tie-breaking to
      reproduce, and the references pin half-up.
      🔴 **KNIFE 1/1 — and the scoring itself needed a design fix.** Truncating
      instead of rounding moves EVERY fractional row, including the ten still
      waiting on `.`, so an exact-set arm read FAIL on a correct fix (the THIRD
      such this session). It now scores the DISCRIMINATION: `c.round`/`c.round2`/
      `d.roundup` must MOVE and `c.over16` — which has no fraction — must HOLD.
      🔴 **AND A REGRESSION THE UNIT TEST CAUGHT THAT THE EMULATOR PROBE DID
      NOT**: `tests/test_printusing.py` stubs `eval` and set only DE, never
      FACTYP. That was invisible while `pu_do_number` read DE unconditionally;
      the type test sent every stubbed integer to a sub-ROM the emulator-free
      harness cannot reach, and four cases printed 0. **A stub that models a
      routine must model the part the caller reads.**
      💰 **COST: page 1 32 -> 12 B; sub page 1 1586 -> 1480 B.**
      🔴 **`.` WAS ATTEMPTED AND REVERTED (D-PUDOT, same day)** —
      [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §9. It crashed
      the fixture on every `d.*`/`e.*` row AND broke a previously-correct row
      (`d.roundup`: `"##."` with 1.5 went ` 2.` -> `  2`; a point with ZERO places
      still prints the point), while leaving page 1 at **2 B**. Backed out rather
      than debugged at that headroom.
      📏 **WHAT IT ESTABLISHED, MEASURED:** the main-side cost is **16 B** and
      lands page 1 at 2 B, so `.` is **blocked on evicting `pu_do_number`'s
      pad/emit tail**, not merely tight.
      ✅ **AND THAT EVICTION IS DONE (D-PUEMIT, same day): page 1 18 -> 42 B**
      free, sub page 0 1668 -> 1590 B. `.` now fits with room instead of landing
      at 2 B. ⚠️ A tenant **cannot call `pchar` at all** — it reaches CHPUT in the
      BIOS (page 0) and lives in main page 1, and whichever island a tenant runs
      on, one of those is switched out — so the tenant BUFFERS into DETOKBUF and
      the stub drains it through the real `print_string`, honouring PRDEST. That
      is the shape `pu_to_field` always had; reading WHY is what made this an
      eviction rather than a crash.
      🟢 Proved neutral AND live: 0 of 44 rows moved, and both branches of the
      evicted body are still exercised (8 rows on the `%` arm, 3 on the `*` arm).
      "Nothing moved" is equally what evicting DEAD code looks like. The renderer design survives (digits
      built CONTIGUOUSLY, point inserted last, so rounding is one carry walk over
      one array); the carry/shift implementation is what was wrong. And `.##` --
      an EMPTY integer part -- never reaches the renderer at all, because
      `ptf_num` only starts a field on a `#`: a separate scanner entry point.
      🔴 **AND IT EXPOSED A REAL LATENT BUG, NOW FIXED**: `sub/punum.asm` was
      never in `SUB_PARTS`, so `make sub` said "nothing to be done" after a full
      rewrite -- D-PUNUM shipped with `build/sub.rom` able to go quietly stale.
      ✅ **AND THE GATE IS NOW WRITTEN — `make rom-parts-check`**, in the
      battery ([`tools/check_rom_parts.py`](tools/check_rom_parts.py)). It
      compares each ROM's TRANSITIVE include closure against the prerequisites
      its Makefile rule actually has. **Its first run found THREE MORE of the
      same bug**, none of them from tonight: `sub/lrsetst.asm`, `sub/deffn.asm`
      (both included by `sub/sub.asm`) and `basic/pdfcb-body.inc` (by
      `sub/bload.asm`) — each a tenant whose edits would not have triggered a
      rebuild. All fixed; `disk.rom` was already clean.
      🔴 **THE GATE'S OWN FIRST RUN WAS CONFIDENTLY WRONG** — it reported 63
      missing files, because it parsed the Makefile line-at-a-time and
      `SUB_PARTS` spans a dozen continuations. A plausible table from a misread
      input, in the very tool whose docstring is about that failure. Both
      behaviours are now TESTED: a degenerate parse exits 2 with nothing checked,
      and a planted removal is caught and exits 1.
      📋 **`.` `,` `^^^^` ARE ONE SLICE, NOT THREE** — PRINT USING needs a
      FLOAT RENDERER, which fixes the three rows above on the way past. It also
      re-explains `m.big` (` 0,`), filed as a comma gap and really the same
      truncation. Shape: a SUB-ROM PAGE-1 tenant (1586 B free) calling `flt_fmt`
      in the main low region, with text-level half-up rounding — exact, because
      MSX floats are BCD. Main pays a flag test and a CALSLT, as D-PUSIGN does.
      📋 **9 of the divergent rows are closed;
      `p.dot`/`n.dot`/`a.dot` each combine a SHIPPED specifier with `.` and will
      fall out of that slice rather than needing new sign or fill work.
      🔴 **PAGE 1 IS AT 32 B (2026-09-03) AND `.` IS THE LARGEST OF THE THREE** —
      it needs rounding at a decimal position, not just placement. Scanner and
      buffer work can go sub-side as these two did, but the EMITTER cannot. **A
      page-1 carve, or moving more of `pu_do_number` sub-side, is now the
      prerequisite** — not an optimisation to do afterwards.

- [x] ✅ **D-PUDOT — `PRINT USING`'s `.` DECIMAL SPECIFIER SHIPS** (2026-09-04,
      [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §12), on the
      SECOND attempt; §9 records the first and its revert.

          PRINT USING"##.##";1.5          refs ` 1.50`      was ` 1`
          PRINT USING"##.";1.5            refs `  2.`       was ` 2`
          PRINT USING"####.####";3.14159  refs `   3.1416`  was `    3`

      **12 rows green**, taking
      [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py) to **11
      divergent of 43** — and every one of the 11 is now in a family with no
      code at all (`,`, `^^^^`) plus `d.lead`. Knives **6/6**
      ([`scratchpad/pudot_knives.py`](scratchpad/pudot_knives.py)).
      🎯 **THE MODEL CAME BEFORE THE ASSEMBLY.** The reverted attempt was written
      straight into Z80 and crashed the fixture; this one was written in Python
      and checked against the measured values first. It settled two corner cases
      the first attempt had wrong — `##.` (zero places) still PRINTS the point,
      and rounding can GROW the integer part (`##.` with 9.5 is `10.`). Those two
      existed only as model predictions, so they were added to the probe as
      `d.grow` / `d.growfrac` and **confirmed on both references** before the code
      was trusted; they are also the only rows that witness knife K-PD2.
      🔴 **ELEVEN GREEN ROWS HID A BUG EXACTLY ONE ROW COULD SEE** (§12.3): the
      new scanner code saved the field width with `push bc` and restored it with
      `pop bc`, which preserves `B` — **and rewinds `C`, the scan cursor**. Every
      `d.*` row is blind to it (a re-entered field with no argument left is just a
      trailing literal); `##.##-` is not, because the character *after* the
      decimal part is load-bearing there. That row went green with the fix.
      🔴 **THE HARNESS LOST TWO RUNS TO A PLANT THAT OUTLIVED ITS RUN** (§12.5) —
      `finally` does not survive `SIGTERM`, and the next run read the planted file
      as its own baseline. Plants now go through a **disk sidecar** restored at
      startup; the sidecar's existence is the alarm.

- [x] ✅ **D-PUCOMMA — `PRINT USING`'s `,` SHIPS, AND IT FOUND A RAM COLLISION**
      (2026-09-04, [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §13).

          PRINT USING"#,###";1234          refs `1,234`       was `%1234,`
          PRINT USING"##,###,###";1234567  refs ` 1,234,567`  was `%1234567,`

      **8 rows green on the first build**, taking
      [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py) to **6
      divergent of 47** — `d.lead` plus the five `^^^^` rows. Knives **4/4**
      ([`scratchpad/pucomma_knives.py`](scratchpad/pucomma_knives.py)).
      🎯 **THREE ROWS WERE MEASURED BEFORE ANY CODE**, because the original five
      pinned neither where a `,` may sit nor what the grouping rule is. `m.pos`
      (`USING"####,####";12345678`) **separates two rules that agree everywhere
      else**: commas every three from the RIGHT versus commas at the format's own
      `,` POSITIONS. They differ in LENGTH here — every-three gives 10 characters
      and overflows a 9-wide field (`%12,345,678`, which is what both references
      say); format-positions gives 9 and would have fitted.
      🔴 **IT ALSO FOUND THAT D-PUDOT'S `PU_DEC` WAS ALIASING `FMT_DESC`** (§13.2).
      §12 placed it at `$EEFE` calling that *"a free byte in the same gap"* — the
      gap is FULL (`PU_WP` ends at `$EEFC`, `FMT_SEC`/`FMT_DESC` own
      `$EEFD..$EEFF`). **RAM HAS NO GATE**, so nothing could have caught it, and
      the claim that hid it was a parenthesis in a comment nobody could run.
      Aliasing is not itself the defect — `scratchpad/rammap_sweep.py` reports 50
      addresses already carrying more than one name — the PARTNER was. `PU_DEC`
      and `PU_COMMAS` now share `PU_WP`, where the exclusivity is provable in one
      file against one flag, and **row `x.mixed` measures it** rather than
      asserting it: one format string carrying both a plain field and a `.` field.

- [x] 🔴 **D-PUBUF — `PRINT USING` WAS RENDERING INTO AN 8-BYTE BUFFER**
      (2026-09-04, [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §15).
      Found while sizing the `^^^^` renderer. `NUMBUF` is EIGHT bytes at `$E0C0`
      and is shared with `print.asm` / `list.asm` / `str-engine.asm`, so widening
      it was not the fix. **D-PUCOMMA already overran it** — `1,234,567` is ten
      bytes with its terminator — reaching `VALTYP` and `STRPTR`, which are
      rewritten before any read, and **RAM HAS NO GATE**, so nothing flagged it.
      🎯 **THE WITNESS WAS ALREADY IN THE ROW SET, PRINTING NOTHING.** `e.huge`
      renders `15000000000.00` — FIFTEEN bytes — reaching **`PRDEST`**, the cell
      `PRINT` reads to pick its sink, and the row produced **no output at all**.
      An empty column reads like a row with nothing to say rather than the defect
      itself. Fixed with a 32-byte `PU_NUM` at `DETOKBUF + 256` (the buffer
      D-PUEMIT already established as PRINT USING scratch); 30 references
      retargeted. Knife **1/1**
      ([`scratchpad/pubuf_knives.py`](scratchpad/pubuf_knives.py)) — and the
      plant's ROM hash is **byte-identical to the pre-fix baseline**, so the arm
      reproduces the shipped state rather than approximating it.
      🔴 **THE 30-REFERENCE SWEEP BROKE `STR$` AND THE BATTERY CAUGHT IT** (§15.4,
      92/97: `unit-test`, `string-acceptance`, `graphics-acceptance` and three
      `lineerr` shards). `"N="+STR$(5)` returned `b'N= \x00'`. **`pu_fmt_int` is
      not PRINT USING-private** — `basic/str-engine.asm` calls it and reads
      `NUMBUF` itself, so that buffer is part of STR$'s contract too. The sweep
      moved the writer and left the reader behind: a mechanical rule applied
      correctly, breaking a different invariant. Fixed by DECOUPLING rather than
      chasing readers — `pu_fmt_int` keeps `NUMBUF` (8 bytes is right for
      `-32768`) and `pu_do_number` copies across, so only the renderer holds the
      wide buffer. **0 of 64 rows move**, which is what makes the copy equivalent
      rather than merely plausible.

- [x] ✅ **D-PUEXP — `^^^^` SHIPS; THE FLOAT SPECIFIER SET IS COMPLETE**
      (2026-09-04, [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §16).

          PRINT USING"##.##^^^^";1.5     refs ` 1.50E+00`    was ` 1.50^^^^`
          PRINT USING"**##.##^^^^";1.5   refs `*150.00E-02`  was `***1.50^^^^`

      **All 17 exponent rows green**, taking
      [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py) to **1
      divergent of 47** — only `d.lead`. Knives **6/6**
      ([`scratchpad/puexp_knives.py`](scratchpad/puexp_knives.py)), two of them
      moving exactly one row each.
      🟢 **ZERO RESIDENT COST.** §14 planned `PU_TYPE` bit 2 plus ~8 bytes of
      routing against main page 1's 14. Not needed: `PU_FLAGS` bit 7 already
      means "needs the renderer" and adds no width, so the scanner just sets it,
      and `PU_DEC` bit 7 carries the marker (masked by the two sub-ROM readers).
      325 bytes landed in sub page 1 (1321 -> 996); **main page 1 did not move**.
      🔴 **ONE OF THE TWO FIRST-BUILD DEFECTS LIED CONVINCINGLY** (§16.2): `n` was
      computed BEFORE `call flt_fmt` and read out of `C` after, and BC does not
      survive that call — but **one of the two wrong answers was a plausible 0**,
      so `e.round` PASSED on the same format string (`#.#^^^^`) that `e.big` and
      `e.small` failed on. The other: writing `' '` in the leading column, when
      the fixed-point path writes NOTHING and `pu_sign_tenant` PREPENDS its `+`
      rather than overwriting a blank — `+##.##^^^^` overflowed its own field.
      K-PX4 is its regression arm.

- [x] ✅ **D-PULEAD — `.##` SHIPS; THE `PRINT USING` PROBE CLOSES AT 0 DIVERGENT**
      (2026-09-04, [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §17).

          PRINT USING".##";.5    refs `.50`    was `. 1`
          PRINT USING".##";0     refs `.00`    was `. 0`
          PRINT USING".##";1.5   refs `%1.50`  was `. 2`

      **All 67 agreeing rows in
      [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py) match.** The
      format-specifier surface — `**`, `+`/`-`, `.`, `,`, `^^^^` and a leading
      `.` — is complete. Knives **4/4**
      ([`scratchpad/pulead_knives.py`](scratchpad/pulead_knives.py)).
      🎯 **THE LEADING ZERO BELONGS TO THE COLUMN, NOT THE VALUE.** `.##` gives
      `.50` where `#.##` gives `0.50`; the difference is one `#`, so "a pure
      fraction gets a leading zero" is the wrong reading. `d.leadzer` shapes the
      code: `flt_fmt` renders 0 as `" 0 "`, a REAL integer digit, so a field with
      no integer column would print `%0.00` unless it is dropped — while
      `d.leadover` (`.##` with 1.5 -> `%1.50`) shows a digit that is really there
      must be KEPT and overflow. Hence: drop a LONE `0`, nothing else.
      🔴 **K-PL4 GUARDS A CONSEQUENCE, NOT A FEATURE**: claiming `PU_DEC` bit 6
      made every existing `and $7F` on that cell wrong — three, across two files
      — since places would read as 64 + places. Nothing about the `.##` rows
      points at that mask.
      🔴 **K-PL3 READ FAIL ON ITS FIRST RUN AND THE CODE WAS FINE** (§17.3):
      inverting `jr z` to `jr nz` does not "keep the lone zero", it drops every
      NON-zero digit. Suppressing a branch means REMOVING it. Second arm this
      session whose prediction was wrong while the code under it was right, and
      both times the **must-hold** list is what said so.

- [x] ✅ **CLOSED 2026-09-04 — ALL SIX SPECIFIERS SHIP, AND THE PROBE IS GATED.**
      `**` (D-PUSTAR), `+`/`-` (D-PUSIGN), the float `#` field itself (D-PUNUM),
      `.` (D-PUDOT), `,` (D-PUCOMMA), `^^^^` (D-PUEXP) and a leading `.`
      (D-PULEAD). [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py)
      reads **67 rows with an oracle, 0 divergent**.
      ⚠️ **THE COVERAGE MOVED BEFORE THE ITEM DID.** `filed_row_sweep.py` walks
      only `- [ ]` items (`open_items()`), so closing this entry would have
      dropped the probe out of the only thing watching it — and it had no
      acceptance gate, printing divergences and exiting 0 like the seven named
      in the D-FILEDROT item. So `make pusing-acceptance` landed FIRST
      (D-PUGATE, [`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §18)
      and this box was ticked after.
      🔴 **AND THE `52 agreeing rows` I WROTE IN §17, IN THIS FILE AND IN
      D-PULEAD's COMMIT MESSAGE WAS WRONG** — the measured figure was **67**
      (`references agree on 67 row(s)`). The conclusion (0 divergent) is
      unchanged; the count was quoted rather than read, which is the failure this
      file's own header warns about. The docs are corrected; the commit message
      stands as written.
      The original finding, for the record: found 2026-09-02 by D-PUSING
      (review tier, [`scratchpad/pusing_probe.py`](scratchpad/pusing_probe.py),
      15 rows x 3 machines, **10 DIFF**).
      `basic/printusing.asm`'s header said the `.` `,` `+` `-` `**` `$$` `^^^^`
      specs *"arrive with Phase-3 floats"*. **Floats arrived** — SNG/DBL tokens,
      the float-pack arc is concluded, `PRINT 1.5` renders — so the deferral's
      precondition is satisfied and the specs are simply missing. Both references
      agree on every row below:

          PRINT USING"##.##";1.5      refs ` 1.50`      ✅ D-PUDOT
          PRINT USING"##.##";5        refs ` 5.00`      ✅ D-PUDOT
          PRINT USING"#,###";1234     refs `1,234`      ✅ D-PUCOMMA
          PRINT USING"+##";5          refs ` +5`        ✅ D-PUSIGN
          PRINT USING"##-";5          refs ` 5 `        ✅ D-PUSIGN
          PRINT USING"**##";5         refs `***5`       ✅ D-PUSTAR
          PRINT USING"##.##^^^^";1.5  refs ` 1.50E+00`  ✅ D-PUEXP

      🔭 **`^^^^`'s RULE IS NOW PINNED AND MODELLED, Z80 NOT YET WRITTEN**
      ([`docs/spec-basic-pufloat.md`](docs/spec-basic-pufloat.md) §14, 2026-09-04).
      **13 rows measured before any code**, and they changed the design three
      times — the five original `e.*` rows do not pin the rule at all (`##.##`
      gives ONE mantissa integer digit, `#.#` gives ZERO, and both "always one"
      and "a reserved sign column" fit those five). 🎯 **TWO SPECIAL CASES NEARLY
      GOT WRITTEN AND NEITHER IS REAL**: a leading sign and the `**` pair each
      looked like its own clause, but every row follows ONE rule — mantissa
      integer digits = (field columns before the point) − 1, counting `#`, `,`,
      `**` and the sign alike. `e.comma` makes it unmistakable (`#,###` is five
      columns, four integer digits, and the comma is never printed).
      🟢 **NO NEW RAM**: n = PU_W − 4 − (1 + PU_DEC if a point) − 1, verified on
      all seven format shapes; the flag goes in PU_TYPE bit 2 (`or a` -> `and
      $03`, one byte). ⚠️ `flt_fmt`'s own text is NOT uniform — `PRINT 1.5E+10`
      is plain but `PRINT 1.5E-10` is already exponential (rows `f.*`), so the
      parser must accept an `E±dd` suffix on its INPUT. A model in those exact
      digit-string terms passes **11/11**.

      🟢 **AS OF 2026-09-04 ONLY `^^^^` REMAINS** (now 13 rows), plus `d.lead`
      (`.##`, an empty integer part — a SCANNER entry point, not a renderer
      change: `ptf_num` only starts a field on `#`). `^^^^`'s MANTISSA is already
      correct; only the exponent is missing.

      🟢 **FOUR CONTROLS GREEN** (`###`, `## ` repeat, `!`, a literal `[#]`), so
      the formatter's own machinery is right and this is the specifier set.
      ⚠️ **TWO ROWS ARE REFERENCES-DISAGREE AND ARE NOT IN THE TEN**: `$$` reads
      vg8020 `  $5` vs cf3300 `$$ 5` (this tree matches the CF-3300), and `&` /
      `\ \` read `ABC`/`ABCDE` on the VG-8020 and **ERR 5** on the CF-3300 — a
      split worth its own look before either is called a defect.
      🎯 **HOW IT WAS FOUND: THE ARC NAME AGAIN.** `ex_print_using`'s claimed
      cover is `spec-print-hash-using.md` — the FILE form. The SCREEN probe is
      RETIRED (its vehicle was a cartridge boot the repack image cannot be), and
      its retirement note says *"the SUBJECT survives"* in that spec plus
      `disk_probe_printusing_file` — **both of which are the file form**. What
      actually runs covers three format strings: `"## "`, `"###"`, `"[!]"`.
      ✅ **THE STALE HEADER IS ALREADY CORRECTED** (zero bytes) — read as current
      it priced the feature out of existence, the same trap `play.asm`'s "NO live
      drain" header sprang on D-PLAYFN.
      💰 **UNPRICED.** Six specifiers over a float formatter; needs its own slice
      and its own rows before any byte.
      🤖 AUTONOMOUS — the references settle every row; the price is the open part.

- [ ] 📊 **THE CORRECTNESS SCOREBOARD — WHAT "FULL CORRECTNESS" ACTUALLY
      REQUIRES, 2026-09-02.** Built the moment Joost's sequencing (below) made
      "reach full correctness" the goal, because the file had no map of it.
      🔴 **54 PINNED DIVERGENT ROWS IS NOT 54 DEFECTS**, and reading it that way
      would send the next slice at the wrong things. Classified from
      `tools/filed-row-known.txt`, every row owned by a filed item:

          ACCEPTED DEVIATION, signed off — not defects               9
            ngram14  9  the §12.9-adjudicated negative-EXP carve-out
          DECLINED, priced and refused                               5
            keystr   5  NOT-THIS-ONE `KEY n,"str"` (~160 B)
          APPARATUS, not BASIC behaviour                             9
            ramfree  9  echo-fence readout rows; the entry says so
          SPEED, not correctness (reclassified today)                4
            reclen   4  D-PUT3SLOW: all four PASS with the CORRECT
                        answer at a 5 s step; blank only at 2.5 s
          ---------------------------------------------------------------
          REAL OPEN CORRECTNESS DEBT                                16
          ✅ ALL SIX CLUSTERS RE-RUN 2026-09-02 — EVERY PIN ACCURATE.

          🤖 AUTONOMOUS, BUT BEHIND A DESIGN STEP                    6
            ntwall       6  PAINT: a borderless wall is eaten
                            19 rows / 6 DIFF. "No row yet separates the
                            candidate rules", and the fix touches
                            gfx_plot_cur, shared with PSET/LINE/CIRCLE/
                            DRAW — all agreeing today and required to.

          🙋 BLOCKED ON JOOST                                        7
            deffn_alias  2  two formals of one call alias. TWO PRICED
                            OPTIONS, and one is FREE: fix top-level only
                            for **−8 B** (closes 1 of 2), or grow the
                            shadow area **+99 B RAM** (closes both).
            trapsvc      2  trap handler w/o RETURN; six-event cap.
                            Priced and DECLINED — charter/scope.
            playfn       2  PLAY(n) start-up transient. Measured in full
                            2026-09-02 (D-PLAYWIN): the window closes
                            within ONE STATEMENT and BOTH machines have
                            one, of different shape. The measurement
                            argues for declining.
            open2        1  same file on two channels. **+165 B RAM.**

      🎯 **SO THE AUTONOMOUS CORRECTNESS QUEUE IS EMPTY.** Everything left is
      either waiting on a decision that is Joost's (7 rows) or behind a design
      question the owning item states it cannot yet answer (6 rows). Nothing here
      is blocked on effort.
      🔴 **AND `ngram13` LEFT THE BOARD ENTIRELY (16 → 13).** Its 3 rows are
      NO-ORACLE, not divergences: a truncated store's last line has no `$00`
      terminator, so relink's scan stops wherever RAM holds one, and the machines
      reach those rows over different RAM history. `10 POKE` vs `10` is **the same
      store rendered past its own end** — D-TRUNCLOAD proved that with a PEEK
      instrument and closed the item at 18/18. `ngram13_probe` is the OLDER probe
      and never got the classification, so it kept reporting history as
      divergence. Now marked; it reads 6 scored / 6 agree / 3 NO-ORACLE.
      **That is the third time today a NO-ORACLE classification decided whether a
      row was debt at all.** [[no-oracle-is-about-the-comparison]]

      🎯 **SO THE CORRECTNESS QUEUE IS 16 ROWS, NOT 54** — and one of those is
      already 🙋 on a spend. That is a finishable number, which is the point of
      writing it down.
      🔴 **THE FIRST VERSION OF THIS BOARD SAID 17, AND IT WAS WRONG WITHIN THE
      HOUR.** `reqcomma`'s pinned `g.field` reads **10 on both machines** (0/12
      DIFF) — its item shipped 2026-09-01 and the row that still diverges is
      `e.val`, a different, structural 🙋. `oomtail`'s two are stale the same way
      (0/3 DIFF). **A scoreboard built from pins inherits every stale pin**, so
      each line was re-run rather than trusted; `ngram13` survived that and
      `reqcomma`/`oomtail` did not.
      🎯 **AND THE CAUSE IS STRUCTURAL, WHICH IS WHY IT KEEPS HAPPENING.**
      `filed_row_sweep.py` validates the probes cited by OPEN items. When an item
      CLOSES its probe leaves that corpus and **its pin becomes unreachable by
      the one instrument that would notice it going stale.** Five stale pins in
      one day, and the last two were invisible by construction. New
      `--check-orphans` reports any pin whose probe no OPEN item cites; it found
      both within a minute of existing. **Run it whenever an item closes.**
      ⚠️ **THIS COUNTS ONLY WHAT IS PINNED.** It is the set of divergences some
      filed item OWNS; it is NOT a claim that the tree has no others. The
      denominators that would say so are `kwsweep` (keywords), `sysvarsweep`
      (sysvar cells) and the NO-ORACLE buckets — **and the last of those moved
      TWICE on 2026-09-02**, when a third reference dissolved `LSET`/`RSET` and
      `CVI` from unscorable to scored-and-agreeing. A row parked NO-ORACLE is
      unmeasured, not clean. [[no-oracle-is-about-the-comparison]]
      ✅ **EVERY LINE RE-RUN, NOT TRUSTED (2026-09-02).** `ntwall` 19 rows / 6
      DIFF — exactly the pinned six (`wall.row solid.row h2 h4 hp3 vp.solid`),
      pin ACCURATE. `ngram13` 3 of 9, pin ACCURATE. `reqcomma` 0/12 and `oomtail`
      0/3, pins REMOVED. Four probes re-run; two pins died.
      🤖 AUTONOMOUS — the 16 are named; work them.

- [ ] 🔁 **STANDING (Joost, 2026-09-04): A PURELY STYLISTIC ORACLE SPLIT GOES TO
      THE VG-8020, ON BOTH TARGETS.** *"when there is stylish differences (color,
      screen) between the oracles, pick the VG8020"*. So a references-split row
      that is only presentational is neither a NO-ORACLE park nor a per-target
      answer: the VG-8020 value ships everywhere, including the disk build whose
      oracle is otherwise the CF-3300. **The point is that a cosmetic split must
      not fork the ROMs** — the first such row, `KEY`'s F6 default (`color
      15,4,4` vs `color 15,4,7`), would otherwise have made the two targets
      differ in shipped DATA rather than only in the disk ROM's presence.
      ⚠️ **SCOPE, as given: colour and screen.** It does NOT cover splits that
      exist because the CF-3300 has **Disk BASIC** — those are capability
      differences and each target still follows its own oracle. Measured examples
      of the distinction, all in
      [`probes/basic/basic_probe_pusing.py`](probes/basic/basic_probe_pusing.py):
      `PRINT USING"&";…` and `"\ \"` print on the VG-8020 and are ERR 5 on the
      CF-3300 — Disk BASIC, **not covered**. And `PRINT USING"$$#";5` reads
      `  $5` vs `$$ 5`, which is formatting rather than colour or screen —
      **outside the words as given, so not assumed covered; ask before
      extending.**
      ⚠️ **IT DECIDES THE VALUE, NEVER WHETHER TO MEASURE.** A split still has to
      be read off both machines first; this only says which reading ships.

- [ ] 🔁 **STANDING SEQUENCING (Joost, 2026-09-02): SPEED MATTERS AND WE SHOULD
      AT LEAST TRY — BUT CORRECTNESS COMES FIRST.** Answers the charter question
      D-INTERPSPEED raised (*does "faithful MSX1 BASIC" include speed?*): **yes**,
      and the 2.5–3.8× measured against the CF-3300 (the band was 2.5–3.1× until
      2026-09-04, when the missing seventh row was measured at 3.81×) is
      therefore a real defect
      and not an accepted property. **It is also NOT the next thing to work on.**
      🎯 **WHAT THIS RE-ORDERS.** Every open DIVERGENCE outranks every speed item.
      A row where zerobas answers differently from the reference is correctness;
      a row where it answers the same thing slower is not, and optimising code
      whose behaviour is still wrong means optimising code that will change.
      ⚠️ **SO THE Z80 REFERENCES ARE PARKED, NOT DECLINED**
      (<https://shiar.nl/calc/z80/optimize>,
      <https://www.smspower.org/Development/Z80ProgrammingTechniques>) — they sit
      on the D-INTERPSPEED item and stay unread until the correctness queue is
      down. Reading them now would invite spending page-1 bytes and review effort
      on the wrong axis.
      ➡️ **AND IT GIVES "DONE" A MEASURE**, which the file did not have before:
      correctness is reached when the open divergence set is EMPTY — the filed
      row sets (`scratchpad/filed_row_sweep.py`), `kwsweep`'s keyword
      denominator and `sysvarsweep`'s cell denominator all read clean, with no
      row parked as NO-ORACLE that a third reference could settle.
      🔴 **WHEN SPEED DOES COME UP, THE BASELINE IS NOT 1.0** — `PAINT`'s filed
      "1.9–2.0× slower" is measured against a zero that does not exist on this
      tree (D-INTERPSPEED §4), and any future speed row has the same problem.
      🙋→🤖 The charter half is ANSWERED; what remains under it is autonomous.

- [ ] 🔁 **STANDING TIER (Joost, 2026-08-31): WHEN THE 🤖 QUEUE DRAINS, REVIEW
      EACH STATEMENT'S IMPLEMENTATION IN FULL, one verb at a time.** The
      calibration: PLAY was picked at RANDOM for review and yielded D-MUSICF (a
      stuck-voice bug both references separate,
      [`docs/spec-basic-musicf.md`](docs/spec-basic-musicf.md)) plus
      D-PLAYCORNER (four wrap divergences + `M0`,
      [`docs/spec-basic-playcorner.md`](docs/spec-basic-playcorner.md)) — two
      commits from one verb nobody suspected. Method that worked: read all
      layers of the implementation first, code-review for suspicious mechanism,
      THEN write the differential rows for what the review flags, fix against
      the rows. The review finds what row-first sweeps cannot: a wholesale
      store that is only wrong across TWO statements, a wrap that only shows
      at 65536+.
      📋 **WORKLIST DRAFTED (2026-08-31, while a battery ran):**
      [`docs/review-tier-worklist.md`](docs/review-tier-worklist.md) — 133
      handlers, 48 with a same-named spec, 85 without, grouped into likely-THIN
      (the `OUT`/`POKE`/`VPOKE` raw-I/O trio first: the coercion SURFACE is
      gated, the port/address MECHANISM never reviewed, and the D-PLAYCORNER
      wrap class lives exactly there; then DATA/RESTORE, DEFtype, TIME, CALL,
      MOTOR, AUTO/RENUM) vs arc-covered-under-another-name. ⚠️ A RANKED
      CANDIDATE ROTS — the file says so itself; re-verify per verb at pick-up.
      🔁 **PIPELINE RULE (Joost, same day): battery time is the NEXT verb's
      reading time.** Only emulator rows and tracked-file edits serialize
      behind a running battery; the read-and-review phase runs in parallel,
      with notes in /tmp until the battery lands.
      🤖 AUTONOMOUS — kwsweep's keyword list is the denominator; work through
      it verb by verb, cheapest-context verbs first, and file what each review
      measures.

- [x] ✅ **D-DATACOLON (2026-08-31): three DATA/RESTORE defects from one
      review read** ([`docs/spec-basic-datacolon.md`](docs/spec-basic-datacolon.md),
      `scratchpad/datacolon_probe.py`, 7 rows x 3 machines, 6 DIFF -> 0). The
      DATA body scan had NO QUOTE STATE at both sites (crunch `tk_data_rest` +
      runtime `ex_data`), so `DATA "A:B"` split at the quoted colon and
      executed the string tail as code; bare `RESTORE`'s `ret` ended the WHOLE
      LINE (the dispatcher enters handlers by push/ret), so `RESTORE:C=9`
      skipped `C=9`; and `RESTORE X` was silence where both references raise
      ERR 8 (RESTORE-to-nothing). An unterminated quote swallows the line on
      both references — the row that decided the flag's EOL rule. Second verb
      group off the review tier; the reverse of the trio's no-finding.

- [x] ✅ **D-DEFCORNER (2026-08-31): a DEFtype item's tail ran as a
      statement, hidden by a row that agreed for the wrong reason**
      ([`docs/spec-basic-defcorner.md`](docs/spec-basic-defcorner.md),
      `scratchpad/defcorner_probe.py`, 9 rows x 3 machines, 1 DIFF -> 0).
      `DEFINT AC=7` executed `C=7` here (refs: ERR 2) — the item-end check
      accepted any non-comma byte. `DEFINT AB` agreed on ERR 2 by COINCIDENCE
      (zb re-dispatched the bare `B`, also ERR 2 at the same line); the
      separating row made the tail harmless and observable. The hazard was
      written into the probe's docstring BEFORE the first run — without it,
      0/8 would have closed the review as a no-finding with the defect alive.
      Item end is now ',' / ':' / EOL only. Sub-ROM only, no patch pair due.

- [x] 🟢 **`CALL FORMAT`'s NAME-TAIL AND ARGUMENT SKIP ARE SLOPPY-ACCEPT —
      UNMEASURED.** Filed 2026-08-31 by the review tier (reading
      `basic/format.asm` `exc_name`/`exc_skip`): after matching the 6 chars
      "FORMAT", everything up to ':'/EOL is silently swallowed, so
      `CALL FORMATFOO` and `CALL FORMAT anything` both FORMAT here — and the
      skip is quote-blind (`("A:")` stops at the quoted colon, the D-DATACOLON
      class). The reference's surface is unknown: its CALL FORMAT is
      INTERACTIVE (diskbasic_probe_format.py answers its prompts by timed
      keys), so the rows need that rig. Sketch: `CALL FORMATX` /
      `CALL FORMAT X` / `_FORMAT("A:")` on the CF-3300, watching whether an
      error lands BEFORE the prompt appears; a minted scratch disk per row.
      ✅ **MEASURED AND FIXED 2026-09-01 (D-FMTTAIL,
      [`docs/spec-basic-fmttail.md`](docs/spec-basic-fmttail.md); rows in
      `scratchpad/fmttail_probe.py`)** — **4 DIFF of 8 rows → 0, for ZERO
      BYTES** (page 1 free 358 B before and after). The reference is **strict on
      every count**:
      `CALL FORMATX`, `CALL FORMATFOO`, `CALL FORMAT X` and `_FORMAT("A:")` are
      all `Syntax error` on the CF-3300.
      🔴 **AND THE FILED NAME UNDERSTATES IT — "sloppy-accept" DESTROYS DATA.**
      On zerobas `CALL FORMATX`, a typo one key past the verb, **silently
      FORMATTED the disk** where the reference refuses and touches nothing.
      ➡️ `exc_skip`'s swallow-to-delimiter loop became a require-end-of-STATEMENT
      test raised BEFORE `do_format` (the reference errors before its prompt).
      ⚠️ **`CALL FORMAT:PRINT 1` is accepted on both**, so it is end-of-statement,
      not end-of-line — and that row is the ONLY one of the eight that separates
      the two rules [[two-rules-that-coincide-on-every-row-you-have]]. The
      `or a / jr z / cp COLON / <error>` idiom occurs at **0** other main-ROM
      sites, so there was nothing to aggregate.
      🟢 **A GATE MADE THE FIX FREE.** The first cut cost 1 B and
      `redundant-load-check` went **REAL red on the serial retry** (not a flake),
      naming the site: `skip_spaces` ALREADY returns `A = (HL)`, so the reload
      was dead. 🎯 The gate knew a calling contract the code being written did
      not — the argument for asserting contracts instead of documenting them.
      🎯 **THE ROWS NEEDED NO FORMAT TO COMPLETE** — a rejection lands before
      anything happens and an acceptance parks the CF-3300 at its prompt, so the
      observable is REJECTED-vs-ACCEPTED read off the screen with the prompt
      never answered. Nothing was formatted on the reference.
      🔴 **THREE INSTRUMENT FAULTS, AND THE NEGATIVE CONTROL CAUGHT ALL OF
      THEM** by reading ACCEPTED for `CALL FORMA`: a name-table plane chosen by
      "whichever renders more non-blank rows" (the PATTERN GENERATOR won — two
      different lines gave BYTE-IDENTICAL screens); the two machines putting the
      name table at DIFFERENT addresses (CF-3300 `$1800`, zerobas `$0000`, both
      stride 40, and `$F3B3` reads `0000` on both); and `rstrip()` breaking
      `Syntax`/` error` across the 40-column wrap. The plane is now selected by
      **containing the echo of the line we typed**
      [[readout-blind-to-its-own-subject]].
      🔬 **SIDE FINDING, FIXED:** the kept provenance spike
      `probes/disk/diskbasic_probe_format.py` renders that same `$1800` at width
      **32**, so every screen dump it ever printed was scrambled (its `PROCNM`
      evidence is a hex read and was unaffected). Corrected to 40.

- [ ] 📌 **THE NEGATIVE-EXP DEVIATION IS WIDER THAN §12.9 RECORDED — and it is
      DELIBERATE, not a defect.** Re-measured 2026-08-31 by D-NGRAM14,
      [`docs/spec-basic-ngram14.md`](docs/spec-basic-ngram14.md) §5, rows in
      `scratchpad/ngram14_probe.py`.
      [`docs/spec-basic-mathpack-slice2.md`](docs/spec-basic-mathpack-slice2.md)
      §12.9 recorded ONE argument (`EXP(-200)`) as a disposition BUG in the
      reference, with zerobas correctly returning the true 0. These rows show
      the whole negative tail behaves that way — `EXP(-150)`, `-175`, `-180`,
      `-200`, `-1E30`, `-1E38` all read `ERR 6` on both references and `0` here,
      while `EXP(-100)` (still representable) reads `3.72E-44` on all three and
      `EXP(1E30)` (a real overflow) reads `ERR 6` on all three.
      🎯 **AND IT IS PRODUCED BY TWO DIFFERENT PATHS.** K-N14B moves
      `EXP(-175/-180/-200)` and NOT `EXP(-1E30)`/`EXP(-1E38)`: the extreme
      arguments raise from `evmc_exp_huge` in the main ROM before the sub-ROM is
      dispatched at all, the rest from `fexp_underflow` in `sub/fp_exp.asm`.
      Worth knowing whenever §12.9 is revisited.
      🔴 **D-EXPNEG "FIXED" THIS TO MATCH THE REFERENCES AND WAS REVERTED IN
      FULL** — `math-acceptance` encodes the §12.9 decision and went red.
      Nothing here is owed; this entry exists so the next reader finds the
      MEASUREMENT rather than repeating the mistake.
      🙋 NEEDS-JOOST — only if the §12.9 carve-out is ever to be re-opened, and
      that is your call, not a gate's.

- [x] 🟢 **`ATN(1)`, `EXP(-100)` and `EXP(100)` differ in the LAST DIGIT only.**
      Re-measured 2026-08-30 by D-NGRAM14 (pre-existing; identical before and
      after that slice). `ATN(1)` reads `.78539816339746` against
      `.78539816339745` on both references. A mathpack rounding question.
      ✅ **CLOSED 2026-09-01, NO CODE CHANGE (D-MATHACC,
      [`docs/spec-basic-mathacc.md`](docs/spec-basic-mathacc.md); 38 rows in
      `scratchpad/mathacc_probe.py`).**
      🔴 **EVERY CLAUSE ABOVE IS WRONG, INCLUDING THE MARKER'S PREMISE — "the
      references settle it" is exactly backwards, they are the LESS ACCURATE
      SIDE.** A differential cannot say who is wrong, and this item was entirely
      a question of who is wrong, so every row is now scored against a 60-digit
      oracle in **units of the last place**.
      📏 **`EXP`: zerobas is within ±0.5 ulp on ALL TEN rows; the references
      reach 330.8 ulp** (`EXP(-50)`), 100.6 (`EXP(-100)`), 74 (`EXP(±100)`,
      `EXP(50)`). "Last digit only" describes which printed COLUMN first differs,
      not the size of the error — which is why this read as trivial for a month.
      🔴 **THE IMPLIED FIX WOULD HAVE BEEN A REGRESSION**: matching the
      references means adopting a 330-ulp error — the D-EXPNEG mistake recorded
      two items above in this same file.
      📏 **`ATN`: no defect.** `ATN(1)` alone looks damning (+1.2 ulp vs +0.2),
      and TWELVE arguments still said so. **TWENTY-SIX refuted it**: zerobas is
      1 ulp worse on 5 (`0.1 .75 1 -.75 -1`) and 1–2 ulp BETTER on 5
      (`0.3 0.4 0.8 0.9 1.25`), identical on 15, and neither side is correctly
      rounded. Over all 38 rows, rows ≥0.5 ulp from truth: **refs 23, zb 16**.
      🎯 **A SPOT FINDING ROTS THE WAY A RANKING DOES** — one argument was enough
      to file this defect and would have been enough to "fix" one that does not
      exist. Both of the hypotheses this slice started with were refuted by
      WIDENING THE DENOMINATOR, including "the error is one-sided, so it lives in
      the final rounding".
      🔴 **AND THE ORACLE FAILED FIRST, PLAUSIBLY**: it printed `ATN(100)` as
      `1.0623664808539` under a heading of *correctly rounded* while all three
      machines agreed on the true `1.5607966601082` — Euler's series at
      `z = 0.9999` hit its iteration cap and **returned the truncated sum**. Now
      range-reduced AND refusing instead of returning
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

- [x] 🟢 **`basic/lineedit-body.inc` IS ASSEMBLED BY NOTHING — DELETE IT OR KEEP
      IT?** Found 2026-08-30 by D-DEADBODY,
      [`docs/spec-deadbody-gate.md`](docs/spec-deadbody-gate.md). It is the ONLY
      `.inc` under `basic/` or `sub/` that no source includes, and it holds a
      COPY of the `relink` loop D-TRUNCLOAD had just bounded — byte-identical
      until that fix, divergent since. Still a Makefile dependency of the sub
      ROM, which can never affect the build.
      ✅ **THE CLASS IS GATED NOW**: `make shared-body-check` (static tier),
      allowlist with a reason in `tools/shared-body-allow.txt`. The file is
      annotated at the top with both facts.
      ⚠️ **NOT SYNCED, DELIBERATELY** — syncing a dead copy restores the illusion
      that either one is authoritative.
      🙋 NEEDS-JOOST — deleting a deliberate historical record is a call that is
      yours, not the gate's. The measuring in front of it is DONE.
      ✅ **ANSWERED 2026-09-01: DELETE — AND IT HAD ALREADY BEEN DONE.** The file
      was removed on 2026-08-31 in `b58f34b` ("Joost's call"); `Makefile:707`
      and `docs/spec-deadbody-gate.md` both record it, and commit `136aee8` keeps
      the historical content.
      🔴 **THE ITEM SURVIVED ITS OWN EXECUTION AND COST A REAL QUESTION.** It was
      still `- [ ] 🙋` a day later, so it was put to Joost as an open decision
      when the answer was already in the tree — the exact failure the pickup
      list's own rule names: *"when a slice lands, grep this list for what it
      just shipped"*. **Re-run a filed claim before spending someone's attention
      on it, not just before spending bytes on it.**

- [x] 🟢 **A TRUNCATED TOKENISED BASIC FILE: THE REFERENCE ACCEPTS IT SILENTLY,
      ZEROBAS REPORTS `load error`.** Measured 2026-08-30 by D-NGRAM13 on the
      UNMODIFIED tree, [`docs/spec-basic-ngram13.md`](docs/spec-basic-ngram13.md)
      §5, rows in `scratchpad/ngram13_probe.py`. Nothing in the tree reached
      `dpl_err_pop` before that slice, so this path had never been read on
      either machine.
      | row | CF-3300 | zerobas |
      |---|---|---|
      | `d.body` (message) | `<nothing>` | `load error` |
      | `d.lineno` (message) | `<nothing>` | `load error` |
      | `d.lineno-l` (listing) | `<nothing>` | `0` |
      🟢 **WHERE THEY AGREE THEY AGREE EXACTLY**: `d.body-l` lists `10` on both,
      and a truncated load OVER a resident program leaves the same mangled
      `10 POKE ZQ1"` on both, byte for byte. So this is not a broken loader —
      it is one extra message and one extra empty line.
      🔬 **THAT HYPOTHESIS IS NOW REFUTED, 2026-08-30**
      ([`docs/spec-basic-truncload.md`](docs/spec-basic-truncload.md)). A
      garbage-padded truncation with the SAME recorded size reads IDENTICALLY to
      the zero-padded one on the CF-3300, so the reference honours the length and
      sees the EOF -- it simply does not REPORT it.
      📏 **AND THE RULE IS MAPPED AT ALL FIVE EOF SITES**, including a zero-byte
      file: the reference is SILENT at every one. 13 rows,
      `scratchpad/truncload_probe.py`.
      ✅ **CLOSED 2026-08-30 — 18 scored rows, 18 agree, 0 diverge.** All five
      message divergences gone. Main page 1 −4 B (355 → 351), sub page 1 +1 B.
      🔴 **AND THE FIX WAS NOT IN THE LOADER.** The memory read this item asked
      for showed both machines write the IDENTICAL store on a truncated file;
      the only difference was that the reference had RELINKED and zerobas had
      not, because it took the error path. So the loader change is exactly the
      repair that hung — and the hang was `sub/lineedit.asm`'s `rlb_lp`, which
      stopped only on `HL == PRGEND`. A truncated store's last line has no `$00`
      terminator, so `skip_to_eol` OVERSHOOTS and an equality test never fires
      again: relink walks RAM forever. Bounded to `>=`, which agrees exactly on
      every well-formed program and is **2 B smaller**.
      📌 **SIX ROWS HAVE NO ORACLE and are named, not dropped**: an unterminated
      last line makes relink's forward scan stop wherever RAM happens to hold a
      `$00`, and the two machines reach these rows over different RAM history
      (`$FF` vs a preceding `NEW`'s zeros). The STORES agree, which is what says
      it is history and not behaviour.
      🔴 **AND I WROTE A WRONG MECHANISM INTO A FILE**: `?PEEK(...)` read
      `<NO ECHO>` on zerobas only, and I commented "`?` is not accepted as PRINT
      here". `ctl.qmark` asks directly — both machines print `2`. The cause was a
      39-character line wrapping on one machine. An unverified mechanism in a
      comment is worse than a row.
      🗄️ HISTORY — **two repairs built, measured and reverted first, BOTH
      HANGING THE MACHINE.**
      (A) EOF joins the completion path (+4 B): closes all five message rows,
      then `relink` walks a body with no `$00` terminator, follows the line's
      saved ABSOLUTE link past the end marker and never returns -- `<NO ECHO>` on
      three rows. (B) terminate the partial line first (+7 B): the body case
      stops hanging and reads `10 POKE` against the reference's `10`, and the
      hang MOVES to `t.lno-l` and `t.link-l`, one of which (A) had right.
      A loader that hangs on some truncated files is worse than one that prints
      a message the reference does not.
      ✅ That instrument was built and it is what closed the item — `PRINT PEEK`,
      three rows per fixture, both machines (spec §4). **It refuted the reading
      that motivated it**: repair B's `10 POKE` vs `10` looked like different
      stores and was the same store rendered past its own end.
      ✅ **RE-VERIFIED 2026-09-01, NOT RE-READ** (this block was `- [ ]` and
      UNMARKED): `scratchpad/truncload_probe.py` on a clean rebuild reads
      **24 printed, 18 scored, 18 agree, 0 diverge, 6 NO-ORACLE** — the filed
      figure exactly. **Closed.**

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

- [x] 🟢 **THE MISSING-OPERAND HALF: `5+` READS ERR 24 WHERE BOTH REFERENCES SAY
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
      ✅ **CLOSED 2026-09-01 BY D-MISSOPBOUND, AT ZERO EXTRA COST — THE DECISION
      EVAPORATED RATHER THAN BEING MADE.** Re-measured, 7 trailing-operator
      shapes, all three machines: **0 DIFF.**
      | typed | all three |
      |---|---|
      | `X=5+` · `PRINT 5+` · `X=5+:PRINT 1` · `X=5+6+` | ERR 24 |
      | `X=(5+)` · `IF 5+ THEN Z=1` · `X=ABS(5+)` | ERR 2 |
      🎯 **THE DIVERGENT ROWS WERE THE ONES WHERE SOMETHING FOLLOWS THE
      OPERATOR** — `)`, `THEN` — which is exactly the boundary D-MISSOPBOUND
      implemented. The truly EMPTY slots (`5+` at end of statement) read 24 on
      the references too and were never divergent.
      💰 **SO THE ~18 B TRADE IS MOOT**, and the six "dependent" statement slots
      the enumeration worried about kept their 24 for free: the fix is
      conditional on something being PRESENT, and end-of-statement is untouched
      (`missing-acceptance` green).
      🔴 **AND THE FILED ROW WAS CONTEXT-BLIND.** `docs/spec-basic-numstr.md`
      §4.1 lists `5+` *(expression-internal)* as "references 2, zerobas 24" with
      no following token shown; the answer depends entirely on what follows, and
      the bare form agrees. **When a divergence is filed, record the WHOLE typed
      line** — that file's own §2 already warns about a claim written before it
      was run [[a-justification-parenthesis-is-an-unrun-claim]].
      🙋 **NEEDS-JOOST** — spend ~18 B and reopen D-MISSOP's rule, or leave it.

- [x] ✅ **`RUN <argument>` IGNORED ITS ARGUMENT AND RAN THE RESIDENT PROGRAM —
      CLOSED 2026-08-31 (D-RUNARG,
      [`docs/spec-basic-runarg.md`](docs/spec-basic-runarg.md)).** 20 rows,
      DIFF 7 -> 0; 2 knives + S1; 48/48.
      🔴 **A WRONG PROGRAM RUN, NOT A WRONG MESSAGE**, which is the class this
      project ranks worst. `RUN 20` ran from the TOP; `RUN "name"`, `RUN A$`,
      `RUN A+0` and `RUN (A)` all ran the RESIDENT program. Only the no-space
      forms (`RUN20`, `RUN"name"`) were ever right.
      🎯 **ONE WORD IN A DELIMITER TEST.** The REPL's `dl_cmd` matches `RUN`
      with `is_cmd`, whose contract accepts end / SPACE / ':' — right for telling
      `RUN` from `RUNNER`, wrong as a "takes no argument" test. A space is a
      delimiter, so `RUN <anything>` took the bare-RUN fast path and the argument
      was discarded. The no-space forms worked only because `"` and `2` are not
      delimiters, so the line was crunched and reached `do_run`, which handles
      arguments correctly. `dl_bare` now asks the second question.
      ⚠️ **FOUND BY A CARVE'S ROW SET**, not by looking for it: D-NGRAM16 gave
      each of the four filename verbs a non-string row, and `RUN`'s came back
      `<nothing>` — which one more row (a resident program) separated from
      "refused quietly".

- [x] 🟢 **`CLOSE` EMPTIES A FIELDED VARIABLE HERE AND DOES NOT ON THE
      REFERENCE.** Found 2026-08-31 by D-NGRAM17,
      [`docs/spec-basic-reqcomma.md`](docs/spec-basic-reqcomma.md) §5, rows
      `g.field` / `g.field2` in `scratchpad/reqcomma_probe.py`.
      | | CF-3300 | zerobas |
      |---|---|---|
      | `FIELD#1,10 AS A$` -> `LEN(A$)` | 10 | 10 ✅ |
      | ...then `CLOSE#1` -> `LEN(A$)` | **10** | **0** |
      🎯 **READING BEFORE THE `CLOSE` AGREES, so `FIELD` is right** — it is
      `CLOSE` that resets the descriptor. The reference leaves it pointing into
      the released buffer.
      ⚠️ Pre-existing (identical before and after that carve); NO PRIOR
      ADJUDICATION FOUND (checked, after D-EXPNEG).
      ✅ **MEASURED 2026-08-31 (D-FLDCLOSE,
      [`docs/spec-basic-fldclose.md`](docs/spec-basic-fldclose.md)) — Joost asked
      what the dangling one actually DOES before deciding, and it is the more
      dangerous of the two possibilities: THE REFERENCE'S DESCRIPTOR IS LIVE, not
      a stale copy.** After `CLOSE`, `A$` survives 8 string allocations intact
      (the FIELD buffer is not in the string heap) — but re-opening a channel and
      `FIELD`ing it makes `A$` read `ZZZZZZZZZZ`, the NEW field's content. A
      later FIELD silently rebinds it.
      ⚠️ **NEITHER CHOICE IS SAFE.** Matching the reference fixes the COMMON
      idiom (read a record, close, use the value) and buys a silent alias in a
      narrow one. Keeping today's reset guarantees a wrong value in the common
      case and never dangles.
      🙋 NEEDS-JOOST — still a judgement, but now against the real behaviour.

      ✅ **DECIDED AND SHIPPED 2026-09-01 (Joost's call: MATCH THE REFERENCE).**
      `CLOSE` no longer calls `fld_clear_chan` — **8 of 9 rows now agree, from
      3 of 9 — and it GAVE BACK 6 B** (page 1 349 → 355 B free). The common
      idiom works again: read a record, `CLOSE`, use the value.
      🟢 Every FIELD-adjacent suite green on the change: `fldary`, `fldwidth`,
      `lrvar`, `diskbasic`.
      🔴 **ONE ROW STILL DIVERGES, AND IT IS THE DANGEROUS ONE — `e.val`.** After
      `CLOSE` + reopen + `FIELD#1,10 AS C$` + `LSET C$="ZZZZZZZZZZ"`, the CF-3300
      reads `A$` as **`ZZZZZZZZZZ`**; zerobas reads `<nothing>`.
      🎯 **BECAUSE THE TWO BIND A FIELDED VARIABLE DIFFERENTLY, AND THAT IS
      STRUCTURAL.** zerobas resolves `A$` THROUGH `FLD_TAB`, so the new `FIELD`
      on that channel drops `A$`'s entry (`field.asm:282`, the caller that must
      stay or 16 slots fill). The reference stores a POINTER in the variable
      itself, so re-FIELDing rebinds what it READS without unbinding it.
      Reproducing that row means moving to descriptor-based binding — a much
      larger change than this one.
      ⚠️ **AND THE REMAINING DIVERGENCE IS IN ZEROBAS'S FAVOUR**: the reference
      silently hands back another channel's data; zerobas hands back nothing.
      Filed as its own question below rather than left implicit.
- [x] ✅ **CLOSED 2026-09-01 (D-CATFIX,
      [`docs/spec-basic-catfix.md`](docs/spec-basic-catfix.md)): `sct_err2` now
      runs the reference's SINGLE PASS** — missing operand -> ERR 24 (three
      more divergences `cattrail_probe` measured first), otherwise evaluate the
      operand ONCE and arm TM through `penderr_set` (first-error-wins keeps the
      operand's own fault), return CF=1 with the partial result so the driver
      NEVER re-drives. `c.strfault` reads 11; `u.cat`'s counter reads 1, the
      references' count, BY CONSTRUCTION. -21 B low region. FPERR-not-TMISMATCH
      keeps `AB` off the screen (`ems_print` checks FPERR before emitting);
      no check_expr_errors precedence change, so D-TMFP's rows are untouched.
      ⚠️ Original filing follows.
- [x] ✅ **CLOSED 2026-09-04 — IT WAS ALREADY FIXED, AND THIS ENTRY IS A
      DUPLICATE OF THE `- [x]` D-CATFIX ONE.** `4d5420e` (2026-09-01)
      implemented *exactly* the design written at the bottom of this entry —
      "evaluates the operand … returns CF=1 … the count stays 1 by
      construction" — and the open box was never struck. Re-measured 2026-09-04
      before touching anything: `c.strfault` reads **ERR 11 on all three**
      (0/9 DIFF) and `u.cat` reads **1 on all three**. Both symptoms gone.
      🔴 **THIS ENTRY SAID 🤖 AUTONOMOUS AND FOLLOWING IT WOULD HAVE CHANGED
      WORKING CODE.** A written design in an open item is not evidence that the
      work is outstanding; running the item's own rows first is what caught it.
      ✅ **AND CLOSING IT WOULD HAVE DELETED THE COVERAGE (D-CATGATE).** No gated
      probe carries `"AB"+(0*(1/0)+1)` at all — the two probes were in
      `filed_row_sweep`'s corpus ONLY because this open item cited them, and that
      sweep walks `- [ ]` items. ⚠️ **AND THE GAP WAS NOT THE `exit 0` CLASS:**
      both probes already returned rc=1 on DIFF. They were the OTHER filed class
      — *an honest rc that no battery collects is not an oracle*. So they are
      promoted to `probes/basic/` and collected as `make catterm-acceptance` /
      `make catusr-acceptance`, mutation-swept 4/4
      ([`scratchpad/catgate_blindness.py`](scratchpad/catgate_blindness.py)):
      N1 (no evaluation) reddens both, **N2 (wrong error armed) reddens catterm
      and leaves catusr green** — which is what says the two gates are not one
      gate wearing two names — and N0, a comment-only edit, leaves both green
      with the ROM byte-identical.
      The original finding, for the record:
      `"AB"+(0*(1/0)+1)` READ ERR 13 WHERE BOTH REFERENCES SAY 11.
      Filed 2026-08-29 by D-STRTM §4; **re-measured 2026-08-31 by D-CATTM**
      ([`docs/spec-basic-catterm.md`](docs/spec-basic-catterm.md),
      `probes/basic/basic_probe_catterm.py`, 9 rows, three machines).
      🔴 **HALF THE ORIGINAL CLAIM IS STALE:** `5+"AB"` reads **13 on all three**
      now. The likely closer is D-TMFP — *"the rule was not a rank between two
      flags but which fault happened first"* — the same question, settled for
      that row and never struck from this entry.
      🎯 **AND THE MIRRORS NARROW IT TO ONE ORDER.** `"AB"+5`, `A$+5`, `5+A$` all
      agree; so does `(0*(1/0)+1)+"AB"` — with the faulting operand on the LEFT
      it is evaluated first and raises Division by zero. Only
      `<string> + <numeric expression carrying its own fault>` diverges.
      🔴 **THE STATED HAZARD IS NOT THE OBSTACLE.** The filing barred D-STRTM's
      route because evaluating in `sct_err2` would evaluate TWICE. But
      `sct_err2` does not evaluate the operand at all — the numeric re-drive
      does, and the operand's fault is reachable and merely OUTRANKED, because
      `type_mismatch_set` arms FPERR *before* the re-drive and `ev_f_defer` is
      first-error-wins.
      ➡️ **SO THE FIX IS ABOUT WHEN THE TYPE MISMATCH IS ARMED, NOT WHERE THE
      OPERAND IS EVALUATED**: it must arm at a LOWER PRIORITY than anything the
      re-drive raises — a `check_expr_errors` precedence change, not an
      `sct_err2` evaluation change. Removing the arm stays closed (Bug C:
      `PRINT A$+5` printed `" 0"`).
      ✅ **MEASURED 2026-08-31 (D-CATUSR,
      [`docs/spec-basic-catusr.md`](docs/spec-basic-catusr.md),
      `probes/basic/basic_probe_catusr.py`)** — a `USR` routine that INCREMENTS A BYTE
      turns the question into a count:
      | `PRINT "AB"+USR(0)` | vg8020 | cf3300 | zerobas |
      |---|---|---|---|
      | evaluations of the operand | 1 | 1 | **0** |
      🔴 **BOTH HYPOTHESES WERE WRONG.** Mine (D-CATTM: "reachable and merely
      outranked") is refuted — the operand is evaluated ZERO times. And this
      entry's hazard ("would evaluate it TWICE") is refuted as stated: the
      references evaluate it ONCE, so one evaluation is the CORRECT behaviour.
      🔴 **AND THE EVALUATION COUNT IS ITSELF A PRE-EXISTING DIVERGENCE**, 0
      against 1 — the error code was never the only symptom.
      🔬 **THE FIX WAS BUILT AND REVERTED.** `call eval` before
      `type_mismatch_set` in `sct_err2` makes EVERY error row agree (0/9 DIFF,
      `"AB"+(0*(1/0)+1)` -> 11) **and takes the count to 2**. A second variant
      that leaves `HL = R` exactly as the old `pop hl` did gives the same 2, so
      the extra evaluation is NOT the cursor. A silent doubled side effect is
      worse than a loud wrong error code (the Bug C ranking), so it does not
      ship.
      ✅ **THE NARROW QUESTION IS ANSWERED (2026-09-01, by reading, verified
      against u.cat's row shape):** the numeric re-drive's factor for a string
      LITERAL (the D-NUMSTR site, expr.asm ~656) defers TM and returns
      **WITHOUT CONSUMING THE LITERAL** — IX still points at the `"`, no
      operator can follow, the re-driven expression ends right there, and the
      `+ operand` is never parsed. Count 0. Any variant that evaluates in
      `sct_err2` double-counts because the decline path is RE-ENTERED by the
      driver (count 2, measured). A string VARIABLE would be consumed by the
      var parse — the asymmetry that made the question look paradoxical.
      ➡️ **AND THE REFERENCE'S SINGLE-PASS ORDER DISSOLVES THE PRECEDENCE
      QUESTION TOO:** it evaluates the RHS during its one drive, so the
      operand's DZ fires BEFORE any TM conclusion — first-error-wins already
      produces 11 if the evaluation order matches. **Design (unimplemented):
      `sct_err2` evaluates the operand, arms TM only if that eval was clean,
      and returns CF=1 with R (the partial result) as the string value — no
      NC decline, so the driver NEVER re-drives** and the count stays 1 by
      construction. Guards to satisfy: the 9 catterm rows, catusr's counts
      (u.cat -> 1, u.catl stays 1), penderr `o.pt.left`, tmfp-acceptance,
      string-acceptance.
      🤖 AUTONOMOUS — the design is written; the rows and gates are named.
      🤖 AUTONOMOUS — the references settle the behaviour; the separating row is
      named.

- [x] 🟢 **`LSET`/`RSET` ON A NEVER-FIELDED VARIABLE — NO LONGER NO-ORACLE. THE
      SPLIT IS THE DISK ROM, AND A sha1 SETTLED IT BEFORE ANY MACHINE BOOTED.**
      Filed 2026-08-29 by D-NGRAM11, closed 2026-09-02 by D-LSETREF
      ([`docs/spec-basic-lsetref.md`](docs/spec-basic-lsetref.md),
      [`scratchpad/lsetref_probe.py`](scratchpad/lsetref_probe.py)).
      🎯 **THE CONTROLLED PAIR WAS FREE.** openMSX's own configs give
      `National_CF-3000` (cassette) and `National_CF-3300` (disk) the SAME
      `<sha1>` for their main BASIC ROM — `c7a2c5ba…`, byte-identical, published
      in both machine XMLs. So "firmware revision" is excluded arithmetically for
      that pair; whatever separates them is the disk ROM. The CF-3000 then
      answers **ERR 5 on every LSET/RSET row**, like the VG-8020, with both
      controls green. **A cassette machine refuses the VERB; it holds no opinion
      about the row.** zerobas ships a disk ROM ⇒ the CF-3300 is the oracle, the
      cassette machines have no vote, and `g.lset`/`g.rset` score as ordinary
      agreeing rows. 🟢 **CLEAN-ROOM INTACT** — a `<sha1>` in an emulator config
      is not ROM content; nothing was disassembled or byte-copied.
      ➡️ **AND THE PROMOTION PAID.** `b.lset` (`LSET A$=5`) was parked in the same
      bucket as a three-way disagreement; once the cassette reading is known to
      be a refusal of the verb, it is a plain divergence — **ERR 2 here, ERR 13
      on the reference.** Fixed the same day, +4 B, six rows:
      [`docs/spec-basic-lsettm.md`](docs/spec-basic-lsettm.md).
      ⚠️ **ONE DISK LINEAGE ONLY, AND SAYING SO IS THE POINT.** The Spectravideo
      SVI-738 (a second, unrelated DiskROM) could not be run: its XML wants
      `svi-738_rs232.rom` at sha1 `4e9384c9…` and the local dump is `9de525e0…`,
      so openMSX refuses the machine. Sony HB-701FD and Gradiente Expert DD Plus
      have no local ROMs. "Disk BASIC pads" is measured on **National's disk ROM
      alone**; whether other vendors agree is open, untested, and irrelevant to
      zerobas, whose target IS the CF-3300.
      [[an-unnamed-outcome-reads-as-no-outcome]]

- [x] 🟢 **A DEAD REFERENCE MACHINE WAS CACHED AS A READING — FIXED 2026-09-02
      (D-SCRAPEMODE), AND THE HARNESS HAD DIAGNOSED IT THREE TIMES ALREADY.**
      Filed and closed the same day,
      [`docs/spec-scrapemode.md`](docs/spec-scrapemode.md).
      🔴 **THE DIAGNOSIS EXISTED AND WAS DISCARDED.** Re-running the exact call
      that wrote seven ghost entries prints
      `verdicts: ['BLIND/mode', 'BLIND/mode', 'BLIND/mode']`,
      `mis_echoed() == []`, `storable() == True`. `BLIND/mode` is emitted when
      the echo oracle reads **SCRMOD out of the machine's own RAM** and finds it
      non-zero — *"this scrape is not looking at the text plane"*. The harness
      concluded that three times out of three and dropped all three, because
      `mis_echoed()` counts only `MANGLED`.
      🎯 **THAT RULE IS RIGHT AND IS NOT THE BUG.** A blind SLOT really is a
      refusal to judge. But `BLIND/mode` is not a blind spot — it is a POSITIVE
      reading, from the machine, that the instrument is aimed wrong. Nothing
      downstream asked for it.
      ✅ **FIXED**: `scrape_invalid()` at the single `run_cases` chokepoint —
      every judged slot `BLIND/mode` ⇒ **do not store**, and say why on stderr.
      ⚠️ The predicate is `BLIND/mode` SPECIFICALLY, not "all blind": a probe
      that CLSes early legitimately produces `BLIND/rewrote` throughout, and
      refusing on that would redden correct runs.
      🎯 **IT REFUSES TO CACHE, NOT TO RUN** — readings still returned and
      printed, so an early refusal cannot bury a divergence the way 08-31's did.
      🟢 **RED AND GREEN ON THE SAME APPARATUS**, same machine and probe, only
      `reset` differing, scored by COUNTING CACHE ENTRIES ON DISK rather than by
      reading the guard's own message: off-plane 0 → 0 (refused, guard spoke),
      on-plane 0 → 1 (stored, guard silent).
      ➡️ **STILL OPEN, named:** the scrape is still SCREEN-0-only (this does not
      teach it `$1800`/32 columns — a stock MSX1 side must still inject
      `SCREEN 0` in its `reset`), and `storable()` still tests the wrong layer
      for every OTHER way a capture can be junk.

- [ ] 🔬 **A HAND-WRITTEN ERROR-MESSAGE ALPHABET IS A BLIND SPOT, AND 19 PROBES
      CARRY ONE.** Found 2026-09-02 by D-LSETTM
      ([`docs/spec-basic-lsettm.md`](docs/spec-basic-lsettm.md) §5).
      `basic_probe_lrvar.bracket()` classifies a screen against a literal list of
      error strings; anything absent reads `<NO OUTPUT>`, which routes to
      *"without a reference"* — **a sentence about the MACHINE, for a fault in
      the PROBE.** Three new rows whose answer is `Missing operand` (ERR 24, not
      in the list) were reported as unscored while BOTH machines had printed it.
      ✅ **FIXED IN `lrvar` ONLY**: alphabet re-derived from `sub/errmsg.asm` +
      main's `err_msgtab` (15 → 37), and an unclassifiable NON-EMPTY screen now
      returns `<UNREADABLE: …>`, deliberately **not** a sentinel, so the gate
      scores it RED and carries the text. K-LT3 plants the omission back and the
      loud path fires. 27/27 scored, 0 without a reference.
      📏 **THE CLASS IS 19 PROBES** (`grep -rln '"Type mismatch"' probes/`), and a
      sweep of every message literal against the ROM source found the SAME
      casing defect in **four more**: `fldary`, `lvfix`, `lvsites`, `tgtspc` all
      said `Field overflow` where the ROM says **`FIELD overflow`**.
      ⚠️ **THOSE FOUR ARE FIXED BUT UNWITNESSED** — no row in any of them
      provokes a FIELD overflow (`fldary` names it in its own NOT-COVERED list:
      *"unchecked today, unchanged here"*), so the fix removes a latent blindness
      and **changes no current reading**. Do not read it as a measured win.
      ➡️ **OPEN: the `<UNREADABLE>` fallback in the other 18**, and better, ONE
      shared classifier (there is precedent — `probe_report`) so the alphabet
      cannot drift per-probe again.
      🤖 AUTONOMOUS — the alphabet is derivable from the ROM source and each
      probe's own rows are the control.
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]]

- [x] 🟢 **`ON ERROR GOTO`'s OPERAND STAGE — FIXED 2026-09-02 (D-ONERRGO), AND
      IT HAD **THREE** OUTCOMES, NOT THE TWO THIS ITEM DESCRIBED.**
      Filed 2026-08-29 by D-ONERRARM, closed by
      [`docs/spec-basic-onerrgo.md`](docs/spec-basic-onerrgo.md).
      **+26 B (page-1 free 327 → 301 B), nine rows, D-ONERRARM 4/12 DIFF → 0/12,
      eight standing rows in `onerr0-acceptance` (32/32, two references each).**
      🔴 **BOTH FILED OBSTACLES WERE WRONG, AND THE SECOND WAS THE EXPENSIVE
      ONE.** *"It needs a raise that skips the trap check, which is not what
      `stmt_error` does"* — **it was already expressible.** `raise_error`'s tail
      is split: `raise_error_hl` makes the trap decision and **`ra_abort` is the
      abort body below it**. Entering at `ra_abort` with the message in HL IS the
      untrapped raise, and it is the same shape `raise_error_forced` (ERR 22) has
      used all along. And `req_lineno` needed no second entry point — the CALLER
      makes the test before calling.
      🔴 **THE THIRD OUTCOME NEARLY SHIPPED AS A NEW BUG.** The obvious fix is one
      test (`cp LINENO_TOKEN / jp nz,<untrapped>`) — and `ON ERROR GOTO` with NO
      operand fails that test too, while on both references it is **not an error
      at all**: it is exactly `ON ERROR GOTO 0`. The draft would have converted a
      row the old code got right BY ACCIDENT into a fresh divergence. Measured
      before any code moved. **Second time in one day that asking "what else
      reaches this test?" was the whole slice** (D-LSETTM was the first).
      [[two-rules-that-coincide-on-every-row-you-have]]
      🎯 **"THE BARE FORM IS `GOTO 0`" IS THREE CLAIMS AND GOT THREE ROWS** — it
      DISARMS (`h.bare` ≡ `h.off`), it **RE-RAISES inside an active handler**
      (`i.bare` ≡ `i.zero`, D-ONERR0's special case inherited whole — which is
      why routing to `oe_disable` had to be measured, its own header warning that
      *"disarming is special"*), and the statement after it on the same line
      still runs (`j.colonrun` → `[B= 7 ]`). Both controls moved in both
      directions.
      ⚠️ **ONE ROW SITES `record_errline` AND NOTHING ELSE DOES**: `e.errl` reads
      `[ 2  30 ]` on both references (against an `e.ctl` of `[ 5  20 ]`). A fix
      that skipped the record would read `[ 0  0 ]` **and every other row would
      still be green.** K-OG3 plants exactly that.
      🟢 **`o.gotoctl` IS THE LEAK DETECTOR** — plain `GOTO A` must still TRAP,
      since `req_lineno` is shared by GOTO/GOSUB/RESUME/ON ERROR and only ON
      ERROR wanted the new exit.
      ⚠️ **NOT COVERED, named:** the same bad operand in DIRECT mode (every row
      is run-mode, and the abort's ` in <line>` suffix has no direct-mode
      analogue); `ON ERROR GOSUB` and the other `ON <expr> GOTO` forms, which
      share no code with this site.

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
      INVISIBLE** — TODO.md:7520 (T-529ABE), a Phase-1 entry ending *"all Phase-3 scope"*.
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
      ✅ **MEASURED AND PRICED 2026-09-04 — D-KEYSCOUT2**
      ([`docs/spec-basic-keystr-scout.md`](docs/spec-basic-keystr-scout.md),
      [`scratchpad/keylist_probe.py`](scratchpad/keylist_probe.py), 11 rows x 3
      machines). All three unmeasured things are now read off machines:
      • **the `n` domain is 1..10**, and `KEY 0,` / `KEY 11,` / `KEY -1,` are
        **ERR 5**; the empty string is legal. zerobas answers **ERR 2 to every
        form**, and the `A=1` control is green on all three, so that is a reading
        about zerobas and not about the program.
      • **truncation is 15**, measured (`KEY 1,"ABCDEFGHIJKLMNOPQRST"` lists back
        `ABCDEFGHIJKLMNO`) — it AGREES with the stride inference, but it is now a
        reading rather than a deduction from a memory map.
      • **`KEY LIST` works on both references** and is `Syntax error` here — and
        it is also the cheapest way to read the defaults: one row instead of
        forty PEEK rows over FNKSTR.
      🔴 **THE DEFAULTS ARE NOT UNIVERSAL, WHICH THIS ITEM DID NOT KNOW.** Slot
      **F6** is `color 15,4,4` on the VG-8020 and `color 15,4,7` on the CF-3300.
      zerobas has TWO official targets with different oracles, so "F6's default"
      is a per-target answer, not a constant.
      ⚠️ `KEY LIST` cannot show trailing spaces or a CR, and the real defaults
      have both (`color `, and a CR is what makes `run` execute). The first
      scout's PEEK read `"colo"` from `"color "`, consistent. So a packed figure
      is a LOWER bound and a straight 160-byte image sidesteps the question.
      💰 **PRICED: ~7 B of main page 1, everything else sub-side.** `ex_key` is
      at `$5AB8` — main page 1, the constrained region — but only the dispatch
      needs to live there: `jp stmt_error` (3 B) becomes `ld ix` / `call
      subrom_call` / `jp c,...` (~10 B). A page-0 tenant may call main page 1, so
      it can reach the expression evaluator (the D-PUSIGN / D-PUEMIT pattern).
      The 160-byte FNKSTR image plus ~120 B of parse/store/list code go in sub
      page 0. **Run `make basic-reloc` for the walls — do not quote this line.**
      ✅ **THE F6 QUESTION IS ANSWERED (Joost, 2026-09-04): "when there is
      stylish differences (color, screen) between the oracles, pick the VG8020".**
      So F6 ships **`color 15,4,4`** — the VG-8020 value — on **BOTH** targets,
      including the disk build whose oracle is otherwise the CF-3300. A cosmetic
      split does not fork the ROMs. This is a STANDING rule, not a one-off: see
      the "Settled decisions" note below.
      🔭 **ONLY THE IMPLEMENTATION DECISION IS LEFT** — whether to spend the ~7 B
      of main page 1 (read `make basic-reloc`; it was 8 B free 2026-09-04) plus
      the sub-side body. Everything the fix needs is measured.

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

- [x] ✅ **ARC: CONTROL FRAMES BELONG IN ONE HIMEM-BOUNDED POOL, NOT THREE FIXED
      ARRAYS.** 🟢 **LANDED 2026-09-04** (D-CTLPOOL, spec §17): depth **8 -> 2866**,
      linear in `CLEAR` at 8.0 B/frame, `CLEAR ,himem` responds, all three
      D-CTLCROSS rows close, `d.selfarm` unmoved, **146 B of page-3 RAM
      recovered**, 105/105 gates + 59/59 unit files. ✅ **AND THE STORED-FLOOR
      RESIDUAL IS GATED** (D-CTLLIM, spec §18): `make ctllim-acceptance` fills
      memory, drives the pool to its floor and counts corrupted cells -- 0 on all
      three machines, both allocators exercised, knives **3/3 and orthogonal**.
      🔴 Its first matrix scored **0/3** and found two defects IN THE GATE: the
      two refresh hooks cover for each other, and a blank reading on zerobas alone
      -- what a stale floor actually produces, because the machine dies -- was
      reported as an instrument fault instead of as the finding.
      ⚠️ **STILL NOT COVERED:** that no THIRD growth path exists. That would need
      the derivation back, not a cache. Opened 2026-09-04 (Joost) out of D-TRAPSVC, after D-TRAPDEPTH and
      D-STACKPOOL measured what the references actually do
      ([`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §10–§11).

      **THE MODEL, MEASURED — not inferred.** `CLEAR n` resizes the string space
      and `CLEAR n,addr` sets HIMEM:

          row                     vg8020   cf3300   zb
          baseline, no CLEAR        4080     3311    8
          CLEAR 2200  (+2000 B)     3793     3024    8
          CLEAR 4200  (+4000 B)     3508     2738    8
          CLEAR 200,&HC000          2195     2195    8

      • **+2000 B of string space costs 286 frames on BOTH references**, and the
        next +2000 costs 285/286 — **7.0 B per frame, linear, four times over.**
        One shared pool.
      • **Pinning HIMEM makes the references agree EXACTLY (2195 = 2195).** They
        differed only because Disk BASIC had taken RAM. A fixed array cannot
        produce that.
      • **zerobas reads 8 in every row.** `CLEAR` and HIMEM change nothing.
      • And an abandoned trap dispatch costs ~1 frame on the references too
        (D-TRAPDEPTH) — **nothing is reclaimed anywhere.** `SP` simply moves.

      🎯 **SO THE GAP IS AN ALLOCATION MODEL, NOT A NUMBER**, which is why both
      options the trap item had left were the wrong shape: one added a reclaim the
      reference does not do, the other swapped a fixed array for a bigger fixed
      array — still insensitive to `CLEAR` and HIMEM.

      **WHAT WE HAVE — 154 B of page-3 RAM in three arrays:**

          GOSUB_STK  $E050   8 x 6 B  = 48    GOSUB_DEPTH=8, GOSUB_FRAME=6
          FOR_STK    $EA3A   8 x 11 B = 88    FOR_DEPTH=8,   FOR_FRAME=11
          TRAPSTK    $E20D   6 x 3 B  = 18    TRAPSTK_MAX=6

      🟢 **THE GROUNDWORK EXISTS.** `HIMEM` ($FC4A) is live, `CLEAR` already
      records its second argument, and `basic/str-engine.asm` already computes
      `FRETOP := min(HIMEM,TXTMAX)`. The ceiling concept is there; the control
      frames are what do not use it.

      **THE CHANGE:**
      1. `GSP` / `FSP` / `TRAPSVC` become pointers into one DESCENDING pool
         instead of indices into three arrays.
      2. Overflow stops being "index >= DEPTH" and becomes "collided with the
         variable / string area" — **one check replacing three**.
      3. `CLEAR` resets the pool; that is what makes depth respond to `CLEAR` and
         HIMEM at all, which is rows 2–4 above.
      4. Callers: [`basic/program.asm`](basic/program.asm),
         [`basic/traps.asm`](basic/traps.asm), [`basic/vars.asm`](basic/vars.asm),
         plus the FOR/NEXT path.
      🟢 It also RECOVERS the 154 B and deletes two of the three overflow paths.

      🔴 **AND THE MECHANISM QUESTION RE-OPENED ON 2026-09-04 (D-CTLSTACK §14,
      D-CTLFRE §15, D-EVALDEPTH §16), MEASURED RATHER THAN ARGUED.** The oracles
      were asked WHERE their stack is, not just how deep:
      • `CLEAR n` lowers the published `STKTOP` by exactly n; `MEMSIZ` does not
        move. `(STKTOP-STREND)/depth` = **7.0**, and `FRE(0)` falls **7 B per
        GOSUB level** (7/70/140) — **three independent routes to one number.**
      • 🔴 `CLEAR n,addr` does NOT set `MEMSIZ` to addr: it sets
        `addr - 269 - MAXFILES*267`, so **`MAXFILES` moves the stack top** (the
        ⚠️ filed here as "measure it before assuming it is benign" — it is not).
      • 🎯 **`STKTOP` and zerobas's `strheap_varceil` ARE THE SAME FORMULA.** We
        already compute the reference's stack top and put nothing there.
      • 🔴 **THE EVALUATOR NESTS OUT OF THAT POOL TOO** — 25 B per `DEF FN`
        level, 6 B per parenthesis, both references — **and zerobas caps `DEF FN`
        nesting at THREE** (`FN_STK_FLOOR` `$F200` against `SP` from `$F380` =
        384 B). A separating row proves it is DEPTH, not definition count.
      ⇒ **SO THERE ARE TWO CAPS WITH ONE CAUSE** (GOSUB 8, DEF FN 3), and a
      software pointer running down from `varceil` fixes only the first: `SP`
      stays at `$F380`. Relocating `SP` fixes both, which is why the reference
      has ONE stack — and the honest cost of merging is the per-frame type tag a
      `NEXT` then needs. **The design below is the software-pointer option;
      it is no longer the only candidate. Decide before building.**

      🟢 **THE SHAPE IS SETTLED (2026-09-04), and it is cheap in the SCARCE ROM.**
      Read against the walls (`make basic-reloc`: the main low region and page 1
      are the scarce halves; the sub ROM has ~1.4 KB of page-0 island):

          CTLTOP   the pool's high boundary = `strheap_varceil()`, the SAME cell
                   the string pool already derives from. DERIVED sub-side, never
                   stored -- strheap_floor's own rule and the reason
                   `CLEAR ,himem` falls out for free.
          CSP      the allocation frontier, descending. Empty pool -> CTLTOP.
          GSP      the newest GOSUB frame's address 🎯 AND THEREFORE THE FLOOR OF
                   THE `FOR` RUN -- that is what D-CTLCROSS buys: the FOR frames
                   a NEXT may match are exactly the contiguous run above it, so
                   NO PER-FRAME TAG AND NO WALK.
          TRAPSVC  stays a BYTE COUNT (`ex_return` gates on it with one RAM load
                   on every RETURN; a pointer would cost a 16-bit compare there),
                   beside a new 2-byte `TSP`. 18 B of array -> 2 B.

      🟢 **THE SYMMETRIC HALF IS ONE LINE IN THE SUB ROM.** The variable/array
      allocator already calls `strheap_varceil` for its ceiling (a sub-LOCAL
      call, not a CALSLT) — it becomes `min(varceil, CSP)`, and `sh_free_vars`
      then reports FRE(0) counting down past the live control frames, which is
      what the reference does (`basic_probe_clearpool.py`'s docstring records
      `FRE(0)` falling ~6 B per nesting level there).
      🔴 **THE PUSH SIDE MUST NOT CALSLT.** `GOSUB` push is hot and the
      interpreter is already 2.5–3.8× slow; the collision floor is `ARYEND+2`,
      which lives sub-side. Cache it in a RAM cell the sub-ROM allocator writes
      when it moves `ARYEND` (it is walking the region anyway) so the main ROM's
      check is a plain 16-bit compare. ⚠️ That is a STORED derivation and
      therefore a staleness hole of exactly the kind `strheap_floor`'s comment
      warns about — it needs a gate, not a comment.
      ⚠️ **`MAXFILES=n` MOVES THE POOL TOP** (the channel table is carved below
      the string pool floor). With frames live that is a hazard the string pool
      already has; measure what the references do before assuming it is benign.
      ⚠️ **AND `clear_vars` IS ALREADY THE RIGHT HOOK** — cold boot, RUN, NEW and
      CLEAR, exactly four sites, and `ex_clear` stores POOLSIZE and HIMEM BEFORE
      falling into `clr_done`, so a pool reset sited there picks up the new
      ceiling for free. Point 3 needs no new plumbing.

      ✅ **STEP 1 LANDED 2026-09-04 — THE ACCEPTANCE IS GATED.** All three probes
      are promoted, collected in `tools/run_gates.py`, pinned BY FACE
      (D-NAMEGATE) and **falsified by planting**
      ([`scratchpad/ctlpool_knives.py`](scratchpad/ctlpool_knives.py), 9 cells,
      9 as predicted):

          make stackpool-acceptance   probes/basic/basic_probe_stackpool.py   29 s
          make trapdepth-acceptance   probes/basic/basic_probe_trapdepth.py   52 s
          make ctlcross-acceptance    probes/basic/basic_probe_ctlcross.py    22 s

      ⚠️ **`stackpool-acceptance` GATES A RELATION, NEVER AN ABSOLUTE DEPTH** —
      the two machines have different memory maps by construction, the same rule
      `basic_probe_clearpool.py` states for `FRE(0)`. It asserts sensitivity,
      linearity, the stopping `ERR`, and — between the two REFERENCES, where it
      means something — that pinning HIMEM makes them agree exactly. 🎯 Knife
      K-CP1 (`GOSUB_DEPTH` 8→7) is the control that proves it: the depth moves,
      the MODEL does not, and stackpool correctly stays **green** while trapdepth
      goes red.
      🟢 The filed claims were RE-RUN before any of this was built on: §10's and
      §11's tables reproduce exactly, and `d.selfarm` reads `9 0` on all three.

      🔴 **AND A NEW DIVERGENCE CAME OUT OF DESIGNING IT — D-CTLCROSS
      ([`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §12).** Three
      fixed arrays make a whole class of question INVISIBLE: a `NEXT` can always
      reach its `FOR` frame, because no GOSUB frame can ever be between them.
      Both references raise **`NEXT without FOR`** whenever it is:

          row         vg8020   cf3300   zb     what the row does
          x.nxgos      0 1      0 1    1 0     NEXT inside a sub, FOR outside
          x.nxdeep     0 1      0 1    1 0     NEXT I across [FOR J][GOSUB][FOR I]
          x.nxagain    0 1      0 1    2 0     ...and the loop-CONTINUES arm

      🎯 **A single pool whose `NEXT` search stops at the first non-`FOR` frame
      closes all three for free** — they diverge BECAUSE the stacks are separate.
      Pinned as known-divergent; **the pins come out in the commit that lands the
      pool.**

      🟢 **AND THE ROWS SETTLE THE FRAME LAYOUT, so it is not a taste question:**
      • **no per-frame type tag** — the `FOR` frames a `NEXT` may match are
        exactly the contiguous run newer than the newest GOSUB frame, and `GSP`
        IS that run's floor;
      • D-FORRET's `FSP-at-push` field becomes **`GSP-at-push`** (`x.retfor`, the
        mirror direction, is already faithful and must stay so);
      • a trap's service record is pushed **before** its GOSUB frame, so it lands
        below it and stays out of the run a `NEXT` walks.

      ⚠️ **GUARDS THAT MUST NOT MOVE:** `d.selfarm` (a handler that re-enables its
      own trap then RETURNs) reads `9 0` on all three TODAY — the case
      `spec-basic-trapsvc.md` §6 warns a fix must not break. And `gosub_push`'s
      `FSP-at-push` field (`GOSUB_FRAME` = `[CURLINE][resume][FSP-at-push]`, from
      D-FORRET) is a cross-stack invariant: a pooled design still has to restore
      the FOR stack on RETURN.
      ⚠️ **`CLEAR` RESETS THE ERROR VECTOR** — measured while writing these rows.
      Any probe that arms `ON ERROR` before a `CLEAR` reads `<NO OUTPUT>`.
      🏗️ ARC — its own slice, its own knives, per verb (GOSUB/RETURN, FOR/NEXT, traps) plus the CLEAR interaction.

- [ ] 🏗️ **THE Z80 STACK IS IN THE WRONG PLACE, AND THE `DEF FN` CAP IS THE
      SYMPTOM.** Opened 2026-09-04 out of D-EVALDEPTH/D-CTLPOOL (D-FNSTK,
      [`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §19).
      `DEF FN` nesting caps at **3** here against the references' ≥4 at 25 B/level
      — and asking to raise it found the filed arithmetic wrong:
      • **`SP` is at `$F2EA`, not `$F380`** (measured via `SAVSTK`), so the
        headroom to `FN_STK_FLOOR` is **234 B**, ~78 B/level — not 384.
      • 🔴 **That region is claimed RAM.** `CURDRV_CELL $F247`,
        `RES_STUBS $F24E..$F2B8`, `DRVCNT/DRVTBL $F347/$F348`, `F365_STUB $F365`.
        Snapshotting `$F24E..$F2B8`: **`X=1` alone changes 87 bytes.** ⚠️ NOT a
        defect — those are tier-2 MSX-DOS stubs plain Disk BASIC never calls, and
        the battery is green — but it means **there is no unclaimed room to give**.
      ⇒ **THREE THINGS THAT LOOK LIKE FIXES ARE NOT:** lowering the floor buys
      ~48 B (< one level); raising it to a safe `$F2B8` leaves **50 B** and breaks
      nested `DEF FN` entirely; moving the FN save into the control pool is ~16 of
      78 B, **20 %**, and 3 stays 3.
      🎯 **THE FIX IS SP RELOCATION** — the VG-8020's `STKTOP` is `$F0A0`, BELOW
      the work areas, descending into the free gap; zerobas never sets `SP` at all.
      ⚠️ Hazards, and why this is filed rather than rushed: the stack and the
      control pool both want the top of the free gap (partition, or merge as the
      reference merges them); moving `SP` with live return addresses is only safe
      at specific points; and a boot-fixed stack above a later `CLEAR n,addr`
      HIMEM lands in memory the user just reserved — the exact `$D000` accident
      §17 records.
      ⚠️ **FIRST THING TO MEASURE IF PICKED UP:** how much of the ~78 B/level is
      evaluator recursion vs FN machinery. The 20 % above is arithmetic from the
      save size, not a measurement of the rest.
      🙋 NEEDS A DECISION — the mechanism (partition vs merge) is Joost's call; the
      measurements are done.

- [ ] 🐌 **THE INTERPRETER IS 2.5–3.8× SLOWER THAN THE CF-3300 — ON EVERYTHING,
      NOT ON ONE VERB — AND IT REFRAMES EVERY OTHER SPEED ITEM.**
      🔴 **THE BAND WAS 2.5–3.1× UNTIL 2026-09-04, AND THE APPARATUS WAS PICKING
      IT.** The seventh row, `FOR I=1 TO 2000:X=I*2+1:NEXT`, read `<NO OUTPUT>`
      at the probe's 60-emulated-second budget and never entered the table below
      — it needs ~64 s on zerobas. It is the **worst ratio in the set (3.81×)**,
      so its absence pulled the reported ceiling down by 0.7×. A missing
      measurement printed like a row with nothing to say, in a probe
      `filed_row_sweep` cannot parse and therefore never adjudicated. Budget
      widened to 150 s; all seven rows report. **The independent `width: TIME`
      rows in `playfn_fixture_probe` had already read ~3.5×**, above the old
      band, and nothing connected them. Measured 2026-09-02 (D-INTERPSPEED,
      [`docs/spec-basic-interpspeed.md`](docs/spec-basic-interpspeed.md),
      [`scratchpad/interpspeed_probe.py`](scratchpad/interpspeed_probe.py)).
      **Measurement only, no code change.** `TIME` jiffies read from inside the
      machine, so the harness step is not in the loop:

          FOR I=1 TO 1000:NEXT          cf3300   96   zb  295   3.07x
          FOR I=1 TO 2000:NEXT                  200       611   3.06x
          FOR I=1 TO 4000:NEXT                  407      1242   3.05x
          I=I+1:IF I<2000 THEN 30 (no FOR)      718      1797   2.50x
          FOR J=1 TO 2000:I=I+1:NEXT            576      1692   2.94x
          FOR I=1 TO 500:A$="AB"+"CD":NEXT      122       300   2.46x
          FOR I=1 TO 2000:X=I*2+1:NEXT         1004      3826   3.81x  <- added 09-04
          X=1                    (the floor)      0         0     --

      ✅ **IT IS A RATIO, NOT AN OFFSET** — 3.07/3.06/3.05 across a 4x range of
      loop counts; a per-statement overhead would shrink as the loop grows.
      ✅ **IT IS NOT `FOR`/`NEXT`** — the `GOTO` row has no FOR machinery at all
      and is still 2.50x. The subject is statement dispatch and expression
      evaluation.
      🟢 **AND THE CLOCK IS THE SAME**, which is the control that would have
      dissolved the whole thing: neither machine XML carries a clock-frequency
      tag and both are `<type>MSX`, so openMSX runs both at 3.58 MHz.
      🎯 **THIS REFRAMES THE `PAINT` ITEM BELOW.** "1.9–2.0x slower" is measured
      against a baseline of 1.0 that does not exist on this tree — at a 2.5–3.1x
      interpreter, PAINT is **faster than the machine it runs on**. Not a
      retraction (PAINT may have its own gap on top), but the number has to be
      re-read against 2.5–3.1x.
      🔴 **THE CALSLT MECHANISM WAS TESTED THE SAME DAY AND IS REFUTED — THE
      THIRD PLAUSIBLE MECHANISM TO DIE ON 2026-09-02.** The hypothesis was that
      the repack's sub-ROM eviction puts a cross-slot call on a per-statement
      path.
      ✅ **THERE IS SUCH A CALL, ON A HOTTER PATH THAN EXPECTED.** A bounded
      call-graph walk: `exec_stmt`, `ex_next` and `ex_if` do NOT reach
      `subrom_call`, but `ex_for` does — via `var_store_fac` →
      `var_alloc_or_find` → `ary_engine_call`. And `var_alloc_or_find` is **not**
      the array path despite its callee's name: it sets `op = 5 SCALAR_ALLOC` and
      calls unconditionally, so **every scalar variable store crosses a slot.**
      🔴 **AND IT COSTS NOTHING DISPROPORTIONATE.** Two measured rows differ by
      exactly one scalar store per iteration — `FOR I=1 TO 2000:NEXT` (200/611)
      and `FOR J=1 TO 2000:I=I+1:NEXT` (576/1692). The MARGINAL cost of the store
      is 376 jiffies on the reference and 1081 on zb: **1081/376 = 2.87×**, the
      same as the baseline and slightly BELOW it. A cross-slot call unique to
      zerobas would put this far above 3.
      🎯 **THE ORDERING AGREES**: `FOR`/`NEXT` (3.06×) does NOT cross a slot per
      iteration (`ex_next` writes through the cached `FOR_CUR` address) while the
      `GOTO` loop (2.50×) does. **The path that crosses a slot is the LESS slowed
      of the two** — the opposite of what a dominant CALSLT cost predicts.
      ⇒ **THE EVICTION IS NOT WHAT MAKES THIS TREE SLOW.** The factor is in the
      interpreter's own RESIDENT code. That matters because "the repack bought
      space with speed" is the intuitive story and it is wrong — un-evicting
      tenants would not buy the speed back.
      ⚠️ Not claimed: that the cross-slot scalar store is free, or that no other
      tenant call is expensive. Only that this is not the explanation.
      ⚠️ **WHETHER 3x MATTERS IS A CHARTER QUESTION, NOT A MEASUREMENT** — the
      project targets *faithful* MSX1 BASIC and whether faithful includes speed
      is Joost's call.
      🔬 **HOW IT WAS FOUND, because the lesson generalises**: not by looking for
      it. D-PUTTIME added a pure-CPU row purely to VALIDATE that `TIME` can see
      CPU work before trusting it on disk work. The control was the finding.
      📚 **REFERENCES (Joost, 2026-09-02): <https://shiar.nl/calc/z80/optimize>
      and <https://www.smspower.org/Development/Z80ProgrammingTechniques>** —
      Z80 size/speed idioms. Filed HERE rather than on a carve item on purpose:
      the constant factor is in resident interpreter code (§5's CALSLT route is
      refuted), so instruction-level work on the hot dispatch path is the shape
      that could actually move it. ⚠️ Not read yet, and it changes nothing about
      the charter question below — optimising is only worth starting once "does
      faithful include speed?" is answered.
      🙋 **NEEDS-JOOST** on the charter question (does faithful include speed?);
      🤖 the non-repack comparison in §5 is autonomous and comes first.

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

- [x] 🟢 **TEN `tests/_tmp.py` ARTIFACT NAMES ARE SHARED BY 2–4 FILES, AND
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

      ✅ **DONE 2026-09-01 (Joost's call: isolate by default) — BUT
      PER-INVOCATION, NOT PER-PROCESS, AND THE DIFFERENCE IS LOAD-BEARING.**
      `tests/run.py` now mints one temp base per run and exports `ZB_TEST_TMP`;
      every child inherits it, so a bare `make unit-test` can no longer collide
      with a `scratchpad/paint*.py` probe. `tools/run_gates.py` already did this
      for the battery — a bare run had nothing.
      🔴 **PER-PROCESS WAS THE OBVIOUS READING AND WOULD HAVE BROKEN A DOCUMENTED
      DEPENDENCY**: `test_rdblk_randrecord.py:53` reads
      `test_wrblk_body_e2e.py`'s ROM and says so on the line that names it, and
      `_tmp.py`'s own docstring calls that sharing deliberate. One base per
      invocation keeps the sharing exactly and removes only the cross-invocation
      collision [[a-mechanical-fix-can-break-a-different-invariant]].
      📏 **THE COUNT IN THE HEADLINE HAD ROTTED: 8 shared names, not ten**
      (4 pairs of `.rom`/`.sym`). 59/59 test files pass isolated, which is what
      shows the deliberate sharing survived.
- [x] 🟢 **THE BOOT BANNER STILL CALLS ZEROBAS A "PROGRAM LOADER", AND THE
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

      ✅ **DONE 2026-09-01 (Joost's call, wording reviewed against a real boot
      capture before settling).** Now `clean-room MSX1 BASIC` — it names the
      charter's TARGET rather than the old role.
      📏 **−14 B, AND NOT WHERE A READER WOULD LOOK**: both MAIN walls are
      unchanged (low 106 B, page 1 349 B) because `banner_text` lives in the
      `title_tenant`. The saving shows in **sub page 1: 1572 → 1586 B free**.
      ⚠️ **THE `ZB` PROMPT WAS LEFT ALONE, DELIBERATELY** (same call). It sits
      beside every typed line where both references show `Ok`, so it is a larger
      identity signal than the banner — and it stays as the marker that this is
      not the reference while the charter work is unfinished.
      🟢 `banner-acceptance` needed no edit: it reads the strings from the source
      rather than pinning a copy, so it re-verified the NEW text
      (`PRESENT 'clean-room MSX-BASIC implementation'`) on the same run. A gate
      that derives its expectation instead of freezing one costs nothing here.
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
      💰 **SCOUTED AND PRICED 2026-09-02 — +6 B, AND THE MECHANISM IS ALREADY
      PROVEN BY A GREEN ROW.** The reference rule is *look the old file up FIRST,
      then evaluate the new name*, so the reorder moves `call fname_expr` (the
      NEW name) from before `fat_mount` to after `fat_find` succeeds. The only
      cost is parking the text cursor across the disk primitives, which
      `FN_RESUME` is already documented to survive (*"the text cursor no longer
      needs guarding across CALSLT -- it lives in FN_RESUME"*):
      `ld (FN_RESUME),hl` + `ld hl,(FN_RESUME)` = **6 B**, against a page 1 that
      was 301 B free on 2026-09-02 (`make basic-reloc`; do not quote this).
      🔴 **MEASURED 2026-09-04 (D-NAMEORD,
      [`docs/spec-basic-nameord.md`](docs/spec-basic-nameord.md)): THE REORDER
      SHIPPED AT THE PRICED +6 B AND FIXES ONE ROW, NOT TWO.** `name.as5` goes
      2 -> **53** and matches; `name.ex5` stays at **2** where 13 is due; all five
      controls hold. **And the cause is not the ordering** — a bisect with the
      cursor round-trip and NO disk primitive in between still read 2, so
      `FN_RESUME` is not clobbered ($E227, no declared overlap, two writers in the
      tree) and the second `fname_expr` site produces `Syntax error` for a numeric
      operand for a reason that predates this change. The same routine gives 13
      from the old-name position (`name.old5`, green). A separate defect, still
      open — **and now localised**: `els_tc_common` (`basic/missing.asm:562`)
      RE-DRIVES the operand with `eval` and reports `stmt_error` when `ERRMARK`
      says nothing was parsed, so ERR 2 is that routine saying *"the re-drive
      found no operand"*. **Four hypotheses measured and refuted**: the disk
      primitives (park+restore with none between → still 2), the operand's shape
      (`AS 5` / `AS 5+0` / `AS5` → all 2), end-of-statement (`AS 5:REM` → 2, while
      `NAME 5` at EOL → **13**), and the D-NUMSTR literal/variable asymmetry in
      the OLD name (`A$="HI.TXT":NAME A$ AS 5` → still 2). What survives is the
      CALL SITE. Next step is reading what `str_eval` leaves in HL on each path,
      not more black-box rows. ⚠️ `els_tc_common` is a SHARED TAIL — every
      `fname_expr` caller lands there — so a fix sited in it is a decision about
      all of them. ⚠️ And the side-effect this entry named is now REAL and unmeasured:
      `DISKSLOT_OK` is checked before the new name is evaluated, so the diskless
      build answers the no-disk error there — measurable against the VG-8020,
      which has no drive either.
      The claim this replaces read:
      🎯 **THE REORDER ALONE FIXES BOTH ROWS, AND NOTHING NEW HAS TO PRODUCE
      ERR 13**: with the old file absent, `fat_find` misses and the new name is
      never evaluated → 53; with it present, `fname_expr` runs and faults → 13,
      which is exactly what the FIRST `fname_expr` call already does — row
      `name.old5` (`NAME 5 AS"X.DAT"`) reads 13=13 today.
      🔴 **RE-MEASURED, AND THE FILED zb FACE HAD ROTTED.** This item and the
      corrected comment in `basic/files.asm` BOTH say `zb ERR 24`. Both rows now
      read **ERR 2**:

          NAME"X.DAT"AS 5    (old ABSENT)   cf3300 53   zb 2   DIFF
          NAME"HI.TXT"AS 5   (old EXISTS)   cf3300 13   zb 2   DIFF

      The DIVERGENCE is unchanged and the rule is unchanged; only the face this
      tree gives has moved, some time after 2026-08-26. Six controls green on the
      same run (`name.old5` 13=13, `ctl.kill5`, `ctl.open5`, `ctl.div0` 11=11,
      `ctl.wf` 53=53), so the apparatus is not the story.
      **THIRD STALE FILING FOUND ON 2026-09-02** — after the CVI row (fixed the
      day it was filed) and `filed-row-known.txt`'s `onerrarm` pin.
      ⚠️ **ONE SIDE-EFFECT TO WEIGH, NOT HIDDEN**: the reorder also moves the
      `DISKSLOT_OK` check ahead of the new-name evaluation, so on a machine with
      NO disk `NAME"x"AS 5` would read the no-disk error rather than a type one.
      Unmeasured — the reference always has a drive.
      ⚠️ The two rows are still in **NO GATE**. ONE REFERENCE (Disk BASIC; a
      diskless VG-8020 cannot express `NAME`).
      🙋 **NEEDS-JOOST — PRICED, YOURS TO SPEND.** 6 B for two rows on a verb no
      program in the corpus renames with a numeric operand. The scouting the 🔭
      asked for is DONE; what is left is the call.

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
      🔴 **MEASURED 2026-09-04 (D-TRAPDEPTH,
      [`scratchpad/trapdepth_probe.py`](scratchpad/trapdepth_probe.py),
      [`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §10): THE
      REFERENCES LEAK TOO, AND §6's PRINCIPLE IS REFUTED.** Two rows, the same
      program byte-for-byte except one has its `INTERVAL ON` removed so the trap
      never fires: 20 abandoned dispatches cost **24 frames** of control stack on
      the VG-8020 (4040 -> 4016) and **24** on the CF-3300 (3271 -> 3247).
      **≈1 frame each — the same rate as zerobas. Nothing is reclaimed on either
      reference.** Plain depth is **4071 / 3302 / 8**, and the two references
      differ from EACH OTHER because the limit is free RAM, not a constant.
      ➡️ **SO OPTION 3 IS NOT WHAT THE REFERENCE DOES.** "Pop the stale record"
      would invent a mechanism the oracles do not have to patch one symptom, and
      still leave us at 8 against ~4040 — and it cannot make `int.six` pass
      anyway: `TRAPSTK_MAX` 6 -> `GOSUB_DEPTH` 8, and the row needs 9.
      ➡️ **AND OPTION 1 INVERTS.** It was rejected as *"a bigger number is a
      different wrong answer, not a fix"*; measured, the reference's leak is ALSO
      unbounded and a bigger number is exactly what it has.
      ⚠️ **THIS IS NOT A TRAP DEFECT.** It is the fixed-size control-stack design
      (`GOSUB_DEPTH`=8, `TRAPSTK_MAX`=6) seen through a trap, and belongs with
      that item — priced against a RAM-bounded stack, not a bigger array.
      ✅ **AND THE MODEL IS NOW MEASURED, NOT INFERRED (D-STACKPOOL, §11, Joost's
      read: "does that smell like they use the generic stack?").** `CLEAR`
      resizes the string space and `CLEAR n,addr` sets HIMEM:
      • **+2000 B of string space costs 286 frames** on the VG-8020 and **286**
        on the CF-3300; the next +2000 costs 285 / 286 — **7.0 B per frame,
        linear, four times over on two machines**. One shared pool.
      • **`CLEAR 200,&HC000` makes the references agree EXACTLY: 2195 = 2195.**
        They differed only because Disk BASIC had taken RAM. That is a
        HIMEM-bounded stack and a fixed array cannot produce it.
      • **zerobas reads 8 in every row** — `CLEAR` and HIMEM change nothing.
      ➡️ **SO THE GAP IS AN ALLOCATION MODEL, NOT A NUMBER**, and BOTH of §6's
      surviving options are the wrong shape: option 3 adds a reclaim the
      reference does not do, and option 1 swaps one fixed array for a bigger one,
      still insensitive to `CLEAR` and HIMEM — measurably unlike the reference on
      all three rows.
      🟢 **AND `d.selfarm` IS GREEN ON ALL THREE** (`9 0`): the case §6 warns a
      fix must not break already works here, and now has a row.

      🔴 **THE COST HALF HAS NOW ROTTED TWICE, IN BOTH DIRECTIONS.** 2026-08-30 it
      read *"against 2 B free"* and was corrected UP to 333 B free after
      D-CLRTRAP, with the note *"affordable now"*. **2026-09-04: main page 1 is
      back to 8 B** (`make basic-reloc`; D-PUDOT/D-PUCOMMA/D-PUEXP and D-NAMEORD
      spent it), so ~25–30 B is **NOT affordable there** today. 🟢 **But that may
      no longer be the right region to price against**: the same day's PRINT USING
      arc put a 325-byte renderer in the SUB ROM for **zero** resident bytes by
      reusing an existing flag, and sub page 0 reads 1416 B free. A tenant-side
      design was never costed for this item. **Re-measure before quoting either
      number** — this is the second correction to this one line. **The decline STANDS on
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
      📏 **RE-SWEPT 2026-09-02 (D-CARRYTEXT), AND THE THESIS IS ACTED ON RATHER
      THAN RE-STATED.** The corpus is bigger than the 2026-08-26 numbers above
      (82 probes with the bucket, 34 classifying by message text):

          COMPLETE readouts                    0 of 31  ->  1 of 34
          sentinels NOT carrying the text     52 of 53  ->  68 of 82
          the widest readout                     15/30  ->  30/30

      🎯 **CARRYING THE TEXT IS THE BOUNDED FIX, AND IT IS THIS ITEM'S OWN LOGIC
      FOLLOWED THROUGH.** If "add the next name" is unbounded, stop adding names:
      make the readout say WHAT IT COULD NOT NAME. Twelve probes now do
      (`lrvar`, `fldwidth`, and ten more sharing one exact `for e in ERRORS`
      shape — `readvar inputary arylv forvar nxary nxlist lvsites lvfix fldary
      tgtspc`). `<NO OUTPUT>` now means the screen was genuinely EMPTY;
      `<UNREADABLE: …>` means it had text this probe cannot spell — a sentence
      about the PROBE, where the old one was a sentence about the MACHINE.
      ✅ **WITNESSED, BECAUSE THE BATTERY MOVED ZERO ROWS** (92/92 green, as it
      should be — every currently-named reading is still named). A change that
      moves nothing is unwitnessed, so K-CT1/K-CT2 EMPTY a probe's alphabet
      entirely: `fldary` then reads 4 rows and `forvar` 30 rows as
      `<UNREADABLE: Subscript out of range in 30>` / `<UNREADABLE: NEXT without
      FOR in 20>`, with **zero** `<NO OUTPUT>`. The path is live and carries the
      line suffix too.
      🔴 **AND THE SWEEP COULD NOT SEE ITS OWN SUBJECT.** After all twelve edits
      it still reported `80 of 82`, because its predicate matched the SPELLING —
      `<NO OUTPUT` followed by a `{` — rather than the PROPERTY. A separate
      `<UNREADABLE:` sentinel is strictly MORE informative (it separates "nothing
      printed" from "something I cannot spell") and scored as no fix at all.
      Widened to accept both shapes; the count then moved 80 → 68, exactly the
      twelve. **The instrument said the fix had not happened, and a planted
      knife said it had.** [[readout-blind-to-its-own-subject]]
      ➡️ **REMAINING: 68**, of which 48 classify by code/span/VRAM rather than by
      message text and may not want this shape at all — check before assuming
      the number is a to-do list.
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
      ✅ **(a) MEASURED 2026-08-31 (D-PROBEREACH,
      [`docs/spec-probe-reach.md`](docs/spec-probe-reach.md)): 204 probes — 89
      invoked by a `make` recipe, 11 imported by an invoked one, **104
      unreached**.** `make probe-reach-check`, static tier, 49/49.
      🔴 **THREE STATES, NOT TWO.** `basic_probe_deffn` is the expression harness
      a dozen probes drive: no target of its own, and its code runs on every
      battery. A check asking only "is it in the Makefile?" would call every
      harness dead — the very failure it exists to prevent — so the tool walks
      the IMPORT GRAPH and `S2` is the control for it.
      🎯 **THE 104 ARE PINNED AS A RATCHET**, with grouped reasons, so the number
      can only go DOWN: any probe added from here must get a target or be pinned
      on purpose, and it is reported the same day instead of months later. `S6`
      drops an entry and requires RED, so the allowlist cannot be vacuous.
      🔴 **AND THE FIRST CUT'S REASONS WERE WRITTEN FROM FILENAMES, WRONG FOR
      65 OF THEM** (D-PROBEREACH2, same day): reading the files, **65 of the 104
      describe themselves as differential / functional / regression /
      acceptance** — LIVE VERDICTS nobody collects, the D-WALLIT shape at scale,
      not spent oracles. The reasons now say which is which.
      🔴 **SIX NAME THE RETIRED LEAN CART — AND RUNNING THEM SAYS THREE
      DIFFERENT THINGS** (my "six cannot run" was an over-claim, corrected by
      running them serially on a fresh build): **2 refuse BY DESIGN** with the S1
      message and merely need an argument; **1 CRASHED** (`os.path.exists(None)`)
      and is now **REPAIRED and ALL PASS** — half of the S3 lean-cart retirement
      had landed in the prose and not in the code, and nothing noticed because no
      target runs it; **3 genuinely preflight-refuse**, and for those the
      preflight's own advice ("FIX: make repack-machine") cannot help.
      🗄️ Original wording: they default to `build/basic.rom`,
      the LEAN CART that `docs/spec-lean-retire-s1..s3` removed — the Makefile
      says "there is no `build/basic.rom` rule any more". Run bare they REFUSE at
      preflight. A three-slice arc retired the artifact and six probes still ask
      for it. (The first count was 2: grepping `build/basic.rom` misses
      `os.path.join(ZEROBAS,"build","basic.rom")`. Matching the FILENAME found
      six.)
      📏 **SAMPLE RUN, six probes, SERIALLY on a fresh build: 5 green, 1
      refusing.** ⚠️ Run in PARALLEL on a stale ROM first, all six came back
      non-zero — a headline that would have been entirely my own apparatus.
      🎯 **REFRAMED BY JOOST 2026-08-31: A PROBE THAT PROVED A DOCUMENTED FACT
      IS WORTH KEEPING AS AN *ARCHIVE*, because the fact stays RE-PROVABLE.** The
      criterion that follows is sharper than "does it deserve a slot": **an
      archived probe is only worth keeping if it still RUNS** — otherwise it is a
      fossil and nobody finds out until they try. 📏 93 of the 104 are CITED in a
      spec or doc (measured, not guessed); 11 are cited nowhere and are the
      separate deletion question.
      ✅ **ALL 26 `probes/basic/` ONES RUN, SERIALLY ON A FRESH BUILD
      (D-PROBEREACH4): 22 GREEN**, 1 repaired to refuse legibly and verified to
      run on the merged rig (`cas_leader_budget` — the THIRD probe with the same
      half-finished lean-cart migration), 2 require `--cart` by design, and
      **exactly 1 is genuinely rotten** (`basic_probe_printusing`, bound to the
      retired cart; needs a design call, not a one-line default).
      🎯 **`basic_probe_cas_verbs` IS GREEN** — the probe D-WALLIT found failing
      "for an unknown number of months", which opened this item. It got fixed and
      NOBODY KNEW, because nothing ran it. An archive nothing runs cannot deliver
      the good news either.
      ✅ **AND ALL 65 `probes/disk/` ONES RUN (D-PROBEREACH5): 47 GREEN**, 10
      need a `--dos-disk` image this repo does not ship, 4 need another argument,
      2 are bound to the retired lean cart, and **2 GENUINELY ROTTED**:
      • ✅ `disk_probe_files` — REPAIRED 2026-09-01 (D-FILESROT) as prescribed:
      BOTH frozen constants (EXPECT and the WIDTH-29 wrap reference — the
      second one the filing had not named) re-MEASURED by booting the CF-3300
      on the current disk. Six fields, directory order, W29 wrap
      byte-identical; both PASS against zb. 🔴 The first W29 re-measure skipped
      the date-clear \r and the prompt swallowed both typed lines — a listing
      of nothing that would have frozen as the new reference.
      • ✅ `disk_probe_bload_fcb` — RE-SITED 2026-09-01 (D-FCBSITE),
      breakpoint-FREE: both the frozen address AND the frozen machine choice
      were obsolete (build_83_name is a sub-ROM tenant too, and the old
      diskless machine has no zerobas sub-ROM, so the parse could not even run
      there). Now: repack machine, echo-paced delivery, mem_abs capture of the
      12 FCB bytes after the statement — the subject was never the address.
      3/3 PASS, refcache off.
      🔴 **THE FIRST DISK BATCH ASKED THE WRONG QUESTION AND THE TIMING SAID SO**:
      every failure returned in 0.1 s, so no emulator ever started — the S1
      "pass --machine, there is no default" rule WORKING, not rot. Re-run with
      `ZEROBAS_BASIC_MACHINE` supplied. *A 0-second refusal is not contention.*
      ✅ **AND THE LAST TWO GROUPS RAN (D-CASINSETTLE,
      [`docs/spec-casin-settle.md`](docs/spec-casin-settle.md)): `probes/tape/`
      (12) and `probes/lib/` (1) are VERIFIED.** Seven documented cassette facts
      were RE-PROVED END TO END on the Philips VG-8020 — `STMOTR` (`$5A`→`$4A`,
      delta `$10`), `TAPOON` (motor bit cleared), `TAPIOF`/`TAPOOF` (PPI-C
      unchanged), `TAPOUT` (carry 0), `tapraw` (R14 half-periods ~4 on a `.cas`
      vs ~14 on a 1200-baud WAV, a 3.5× against the encodings' 3.1×), and the
      flagship `tapfile` two-block round-trip, header AND data byte-identical
      from a fixture the probe MINTS ITSELF. `winwid_idle` and `cas_baud_oracle`
      run bare and green; `probe_cart` is INFRASTRUCTURE, not a probe.
      🔧 **AND ONE PROBE WAS SILENTLY WRONG:** `bios_probe_casin` printed BOTH
      candidate lines static — the REFUTATION of its own recorded finding
      ("PPI-B static, PSG R14 carries the FSK") — and exited 0. `tapraw`, on the
      SAME WAV in the same sitting, read the signal, which convicted the probe
      rather than the rig. Two hypotheses died first (settle too long; the
      in-loop R14 re-latch); the cause was the settle being too SHORT — ~119 ms
      against openMSX's ~0.5 s player start-up. Widened to ~0.9 s (23
      transitions, 127/256 high) AND taught to return 2 when neither line moves,
      so a null reading can never again be printed in the same calm voice as a
      result. Scored RED on the old capture and GREEN on the fixed cart.
      🔴 **THREE TIMES IN ONE SITTING A TABLE OF PLAUSIBLE EXIT CODES ANSWERED
      A QUESTION NOBODY ASKED**: `rc=2` was "you forgot a flag", `rc=127` was
      "`timeout(1)` is not on macOS", and `rc=0` in 0.1 s was "phase one of a
      two-phase mint-then-boot probe succeeded". Only reading the OUTPUT
      separated them.
      ⚠️ **TWO TAPE PROBES REMAIN UN-RE-RUN, BOTH FOR NAMED REASONS**:
      `bios_probe_tapread` asserts against a byte pattern only
      `bios_probe_tapwrite` lays down (pairing the two carts is a job, not a
      rot), and `bios_probe_realtape` needs an external tape corpus this repo
      does not ship and refuses legibly saying so.
      ✅ **AND THE TWO CART-VEHICLE PROBES ARE RETIRED (2026-09-01,
      D-LEANRETIRE-PROBES)**: `basic_probe_printusing` and
      `disk_probe_crossbios` booted zerobas AS A CARTRIDGE on a real VG-8020 —
      the lean cart was their VEHICLE, and the repack main ROM cannot be a
      cartridge by construction, so no S1 machine flag revives them.
      printusing's subject survives in the standing rows +
      `disk_probe_printusing_file`; crossbios's CLAIM was a property of the
      cart and retired with it. Both files kept, now printing the retirement
      and exiting. Authorized by your standing "only keep the ones that
      genuinely test something of value".
      🙋 **(b) IS STILL YOURS** — which of the 104 earn a battery slot is a
      runtime-budget call (one tape probe is ~4 min against a ~460 s battery).
      The measuring in front of it is DONE.

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
      ✅ **BOTH OPEN QUESTIONS MEASURED 2026-09-02 (D-PLAYWIN), AND THE FILED
      FRAMING IS WRONG IN TWO WAYS.**
      ⏱ **WIDTH: THE WINDOW CLOSES WITHIN ONE STATEMENT.** Not "a CLS suffices" —
      `FOR I=1 TO 1:NEXT` suffices, and so does every longer delay tried (5, 20,
      50, 200). So **no BASIC program that does anything at all between the `PLAY`
      and the read can observe it**; only a read on the very next statement can.
      🔴 **SHAPE: IT IS NOT "VOICE 2 IS MARKED", AND THE FILED ROW IS A SPECIAL
      CASE READ AS THE RULE.** Playing only voice 2 gives the reference
      `-1 -1 -1 0` and only voice 3 gives `-1 -1 0 -1` — in BOTH the extra voice
      is **VOICE 1**, not voice 2:

          supplied        reference (no delay)   settled
          v1 only         -1 -1 -1 0             -1 -1 0 0    extra: v2
          v2 only         -1 -1 -1 0             -1 0 -1 0    extra: v1
          v3 only         -1 -1 0 -1             -1 0 0 -1    extra: v1
          v1+v2           -1 -1 -1 0             (agrees)     extra: none
          v1+v2+v3        -1 -1 -1 -1            (agrees)     extra: none

      The one-string row this item was filed on is the ONLY case where the extra
      voice is v2. The precise rule is still unnamed — but it is not the one
      written above, and any fix aimed at "stop marking voice 2" would be aimed
      at the wrong thing. [[two-rules-that-coincide-on-every-row-you-have]]
      🔴 **AND ZEROBAS HAS A WINDOW TOO — the item says it "settles instantly"
      and that is false.** `PLAY""` reads `-1 0 0 0` on the reference and
      `-1 -1 0 0` here, and **both settle to `0 0 0 0`**. So this is not
      "reference has a transient, zerobas does not"; it is **two transients of
      different shape**, which is a different fix and a different risk.
      🟢 `no PLAY at all` reads `0 0 0 0` on both — the resting state is shared,
      so every row above is read against a real zero.
      🙋 **NEEDS-JOOST — and the measurement argues for DECLINING.** The window is
      unobservable to any program that executes one statement first; the gate rows
      already accommodate it explicitly (`SETTLE`); and reproducing it means
      matching a transient whose rule is still unnamed, in `playsvc.asm`'s
      interrupt servicer. **Worth-it is the question, and it is yours** — the
      measuring the item asked for is done.

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
      ✅ **MEASURED AND GUARDED 2026-09-05 (D-SEEDARM) — the hole is real and
      its EXPOSURE IS ZERO, so the coarse arm is safe to leave coarse.**
      The arm contributes **37 seeds of 1650 main nodes, 23 of them seeded no
      other way** — and **removing it entirely changes no finding**: dead-with =
      dead-without = **0**. Every name it seeds is already reachable from `init`
      + the resident ABI + the prologue seeds, so BOTH failure directions are
      empty today: nothing is over-seeded into invisibility, and a rename can
      drop a seed without costing anything.
      🎯 **THE GUARD IS NOT "every tools/ name resolves"** — that IS the per-tool
      lookup model, and this does not substitute for it. It is **"this arm still
      carries no weight"**: `deadcode` now computes `dead(seeds)` with and
      without the arm and REFUSES if they differ, naming the routines that have
      become dependent on it. The moment the arm starts carrying weight is
      exactly the moment its silence begins to matter, and that is when the real
      model is owed — for the specific names the failure prints.
      🔬 **ARMED**: forcing the arm to matter (dropping `init`+abi from the
      comparison baseline) makes it refuse with rc 2 and name 1569 routines;
      restored byte-identically, `deadcode` green again.
      ⚠️ So this closes the *"filed rather than fixed"* status honestly: the
      hole is not fixed, it is **measured empty and instrumented to say when it
      stops being empty**.
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
      ✅ **THE CODE IS MEASURED 2026-09-04 (D-MISSOPERR,
      [`scratchpad/missop_err_probe.py`](scratchpad/missop_err_probe.py)):
      `Missing operand` is ERR 24**, on both references, read through `ON ERROR`
      + `ERR` rather than off the screen — a number needs no classifier and
      cannot come back as `<NO OUTPUT>`, which is how the first attempt lost it.
      🟢 **AND THE THREE FILED VERBS ALREADY ANSWER 24 HERE**: `SAVE`, `LOAD`,
      `BLOAD` and `A$=` all read 24/24/24. So the disposition really is closed and
      only the WORDING is outstanding for those four.
      🔴 **BUT A FIFTH SITE IS WRONG ON THE CODE, NOT JUST THE WORDING:
      `A$=+` reads ERR 2 here against 24 on both references.** The entry names
      `A$=+` as a mirror but never recorded it as currently divergent.
      🎯 **AND IT SITS EXACTLY ON D-MISSOPBOUND'S BOUNDARY.** `ev_f_missop` gives
      24 for an EMPTY slot and 4 -> ERR 2 for a WRONG one (a stray operator), and
      that rule is measured — D-MISSOPBOUND took 11 DIFF to 0 with it. `A$=+` is a
      stray operator that both references nevertheless call `Missing operand`, so
      the boundary is not "empty vs wrong" everywhere: **the LET RHS position
      disagrees with the factor position.** That is the question a fix has to
      answer, and it was invisible while only the wording was in view.
      ⚠️ `els_tc_common` is a SHARED TAIL (every `fname_expr` caller plus the LET
      mirror), and `ev_f_missop`'s own comment records why the last fix here got
      its own label instead of joining one — a shipped gate went 209/210.
      💰 Still not priced. Shape: a message-table entry (the D-MSGSUB sub-ROM host
      machinery exists) plus a decision about that boundary.
      🔴 **THE BOUNDARY QUESTION IS ANSWERED, AND THE ENTRY'S FRAMING OF IT IS
      REFUTED (2026-09-05, D-UNARYPLUS, `scratchpad/missop_err_probe.py`).** It
      is **not** positional. The separating cases are the operators with NO unary
      form: `A=*`, `A=/`, `A$=*` and `PRINT *` all read **2 on all three
      machines**, so `*` in the LET RHS behaves exactly as in the factor
      position. *"The LET RHS position disagrees with the factor position"* was
      a rule that coincided with the real one on every case then measured
      [[two-rules-that-coincide-on-every-row-you-have]]. The real rule is about
      the TOKEN: an operator that HAS a unary form, with its operand missing, is
      `Missing operand` (24) in every position — `A=-`, `A=1+`, `A=1*` are all 24
      on all three, ours included.
      🔴 **AND THE FOUR REMAINING `+` ROWS ARE NOT A WORDING GAP AT ALL — THEY
      ARE DOWNSTREAM OF A MISSING LANGUAGE FEATURE.** See the new entry directly
      below: zerobas does not implement **unary plus**. `ev_f` tests
      `MINUS_TOKEN` and has no `PLUS_TOKEN` arm, so a leading `+` is never "an
      operator whose operand is missing" here — it is simply not a factor, hence
      ERR 2. Fix that and `A=+`, `A$=+`, `PRINT +` and `SAVE +` all become 24 by
      themselves, with no message work.

- [ ] 🔴 **UNARY PLUS IS NOT IMPLEMENTED: `A=+1` IS ERR 2 HERE AND LEGAL ON BOTH
      REFERENCES.** Found 2026-09-05 by D-UNARYPLUS while answering the boundary
      question in the entry above. **Six forms measured, all ERR 2 here and `0`
      on both the VG-8020 and the CF-3300**: `A=+1`, `PRINT +1`, `A=(+1)`,
      `B=1:A=+B`, `IF +1 THEN A=2`, `A=1++2`. 🟢 Unary MINUS is the control and
      is correct on all three (`A=-1`, `B=1:A=-B` → 0).
      🎯 **THE SITE IS ONE MISSING ARM.** `basic/expr.asm` `ev_f` reads
      `cp MINUS_TOKEN / jp z,ev_f_neg` and has no `PLUS_TOKEN` test, so a leading
      `+` falls through to "not a factor". `PLUS_TOKEN equ $F1` already exists.
      💰 **PRICED AT 10 B AND IT DOES NOT FIT — the build overran the `$8000`
      ceiling** (`BASIC_IMAGE_OVERRAN_8000_CEILING__TRIM_IT_OR_EVICT_TO_SUBROM`),
      against **6 B free in main page 1** on 2026-09-05. So it needs ~4 B of
      carve. ⚠️ Wall readings rot — re-run `make basic-reloc`.
      🔴 **AND 10 B, NOT THE 8 I ESTIMATED, FOR A REASON WORTH RECORDING**: both
      jumps had to be `jp` rather than `jr`. `ev_f_pos` sits beside `ev_f_neg`,
      ~390 B from `ev_f`, so the test's `jr z` was refused AND the body's `jr`
      back was refused — each costing a byte, the second only after the first was
      fixed. **In a page this dense, inserting anywhere also moves everything
      after it**; the second refusal was an unrelated-looking line number until I
      read it and found it was my own new code.
      ✅ Shape, measured: `cp PLUS_TOKEN / jp z,ev_f_pos` at `ev_f`, and
      `ev_f_pos: inc ix / jp ev_f` beside `ev_f_neg` — unary plus is the
      identity, so consuming the token and re-entering is the whole fix.
      ⚠️ Closes four rows of the entry above for free if it lands.
      🤖 AUTONOMOUS — the reference settles it; finishable unattended (no his-decision signal found).
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
      ✅ **MEASURED 2026-09-04 — D-CSAVEEXPR
      ([`scratchpad/csaveexpr_probe.py`](scratchpad/csaveexpr_probe.py)), on a
      fresh recording tape per row (the `basic_probe_cassave.py` fixture). Both
      references agree on every row; **SEVEN divergences, not one**:

          CSAVE A$        refs accepted (silent)   zb `load error`
          CSAVE A$+""     refs accepted            zb `load error`
          CSAVE           refs `Missing operand`   zb SILENT -- accepted
          CSAVE 5         refs `Type mismatch`     zb `load error`
          CSAVE"P"        silent on all three      (control)

      🔴 **AND `CSAVE`'s NAME IS NOT OPTIONAL AT ALL.** `csav_noname` serves three
      forms and the reference **errors on every one**, with TWO different faces:

          CSAVE       refs `Missing operand`   zb SILENT
          CSAVE:      refs `Missing operand`   zb SILENT
          CSAVE,2     refs `Syntax error`      zb SILENT
          CSAVE"P",2  accepted on all three    (control)

      So the entry's "optional argument … the `FILES`-style *is there an argument
      at all* question" is answered and the premise is wrong: there is no
      no-name form. **Seven divergences**, and the three above are all SILENT
      ACCEPTANCE — this tree runs a `CSAVE` the reference refuses. The face
      depends only on whether a `,` follows, which fully specifies the fix.
      🔴 **EVERY ZEROBAS REFUSAL HERE IS NON-RAISING.** `do_csave`'s `cp '"'`
      gate goes to `load_error`, which PRINTS and carries on, so `ON ERROR`
      cannot trap any of them — exactly the class D-FNEXPR2 closed for the other
      eight filename verbs and did not close here.
      ⚠️ **THE INSTRUMENT TOOK THREE CUTS AND EACH FAILED DIFFERENTLY**, which is
      why the probe reports TWO channels: an `ERR`-reading probe scores a
      non-raising `load error` as **accepted**; a screen-reading one that maps an
      EMPTY capture to "accepted" scores an error the same way; and a `<...>`
      fence matches the `PRINT` statement in the SOURCE IT ECHOES. The trap
      channel currently reads `<NO READING>` on every row and says so rather than
      agreeing — the screen channel carries the result, corroborated by the first
      cut's ERR codes (24 = Missing operand, 13 = Type mismatch).
      The original framing, for the record: these
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
      🟡 **ROW BUILT 2026-09-05 (`f.filesinp` in `namspc-acceptance`), AND IT IS
      NOT YET A PIN — the item stays open, better characterised.**
      • ✅ The window was NOT the risk: the row fits the default `step`.
      • 🔴 **The shape this entry proposed does not reach the case.**
      `OPEN"HI.TXT"FOR INPUT AS #1` / `FILES INPUT$(3,#1)`: HI.TXT is 26 bytes,
      so the whole file arrives in the buffer at `OPEN` and the 3-byte read
      touches no FAT primitive at all
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]]. The read must
      force a REFILL — `TEST.BIN` (2048 B), two 255-byte reads to leave the
      channel 2 bytes short of the sector boundary, and the filespec's own
      `INPUT$(3,#1)` crosses it. (`CLEAR 1000` first, before the `OPEN`: two
      255-byte strings do not fit the default pool, and `CLEAR` closes channels.)
      • 🔬 **The clobber is REAL, measured**: a throw-away diagnostic read
      `DISKOP_OP` ($E9FB) either side of that `INPUT$` and found
      **7 = `DISKOP_SEL_FAT_READ_FILE_SECTOR`** — the file read does reach
      `fatprim_bounce`.
      • 🔴 **And the row still HOLDS under a faithful pre-fix knife**
      (`scratchpad/filesinp_knife.py`). ⚠️ Its FIRST cut was wrong and the green
      control said so: changing only the read left `DISKOP_OP` never written at
      the head, so a stale cell reached every row and `f.filesbare` moved too —
      not the pre-fix behaviour but a third thing. With the head write restored,
      all five plain FILES rows correctly hold and `f.filesinp` holds as well.
      🎯 **SO THE OPEN QUESTION IS NOW SHARP**: handing the dirverb tenant
      selector **7** instead of the FILES selector changes nothing observable in
      these rows, and **why** is unmeasured. Either the tenant does not consult
      `DISKOP_OP` on the FILES path, or 7 is harmless there. That is a smaller
      and much more answerable question than the one this entry was filed with.

- [x] ✅ **A FILESPEC OF CONTROL BYTES: CF-3300 SAYS `Bad file name`, ZEROBAS
      SAYS `File not found`.** **FIXED 2026-09-05 (D-FSPECCHAR) — 45/45 byte
      values now agree, for 39 B.** `bn_chk` in `basic/fcbname-body.inc` refuses
      the `$01`–`$1F` control band with a single `cp ' ' / ret c`, and the nine
      separators plus `$FF` with a 10-byte `cpir` table. Called from BOTH field
      loops, before the upcase. Sub page 1 went 957 → 918 B free; no main-ROM
      bytes.
      🟢 **Five gate rows in `namspc-acceptance`, and TWO OF THEM ARE ACCEPTED
      cases**: `m.hi80` (`$80` accepted beside `$FF` refused) is what forbids
      re-writing this as a high-bit test, and `m.gtchar` (`>` accepted) forbids
      reading `<`/`>` as a separator pair. Without them the three refusals are
      equally explained by a check that is too broad.
      🔬 **Knives 3/3 exact** (`scratchpad/fspecchar_knives.py`), and BOTH of my
      first two arms were wrong in instructive ways:
      • **K-FC2's cut broke the machine, not the table.** `BN_NBAD equ 0` makes
      `ld bc,0` / `cpir` run **65536 times** and walk all of memory, so four
      unrelated rows moved and neither predicted row did. The table is neutered
      by filling it with `$01` instead — a control byte the band test already
      refuses, so it can never reach the walk.
      • **K-FC3's prediction was one row short**: a high-bit-only rule drops the
      control band as well. 🎯 What still holds under it is `m.ffchar` — `$FF` is
      high-bit, so **the WRONG rule gets that row right**, which is exactly why
      `m.hi80` and not `m.ffchar` is the row that forbids the mistake.
      --- the original filing ---
      Found 2026-09-05 by D-FILESINP while building the row above. `FILES INPUT$(3,#1)` against `TEST.BIN` builds a 3-character
      filespec out of the file's own bytes, which at that offset are the value
      `$04` — non-printable control characters. The CF-3300 REJECTS the name;
      zerobas accepts it and reports the search result.
      ⚠️ **Not a made-up case**: any program that builds a filespec from data it
      read reaches it, and the row that found it was written for something else
      entirely.
      🎯 This is `build_83_name`'s domain, which D-FSPEC (2026-09-04) has just
      been through for LENGTH and DOT rules — it validates neither the character
      SET nor control bytes. The reference evidently does.
      ✅ **DOMAIN SWEPT 2026-09-05 (D-FSPECCHAR, `scratchpad/fspecchar_probe.py`),
      47 byte values, `FILES CHR$(n)+"BC.TXT"` on both machines.**
      | | bytes |
      |---|---|
      | **both refuse** | `$00` NUL · `$20` space · `$22` `"` · `$2E` `.` |
      | 🔴 **CF-3300 refuses, zerobas ACCEPTS** | the whole `$01`–`$1F` control band · `+` `,` `/` `:` `;` `=` `[` `\` `]` · `$FF` |
      | **both accept** | letters (upper and lower) · `! # $ % & ' ( ) - < > ? @ ^ _ \` { \| } ~` · `$7F` DEL · `$80` · the wildcards `*` `?` |
      🎯 **That is the DOS/CP-M illegal-character set** — controls, space, and
      `" . + , / : ; = [ ] \` — plus `$FF`. zerobas already refuses four of them
      (`NUL`, space, `"`, `.`), so `build_83_name` has *some* character
      validation; what it lacks is the control band, the nine separators and
      `$FF`. **41 byte values in total.**
      ⚠️ **`$80` is ACCEPTED and `$FF` is REFUSED on the reference**, so this is
      NOT a high-bit rule and must not be implemented as one. `<` and `>` are
      both accepted — they are not a separator pair here.
      ⚠️ Two rows in the sweep are CONTROLS and must stay accepted (`A`, and `*`,
      the wildcard every FILES row uses); the probe refuses to report a finding if
      either is rejected, because a column of `Bad file name` reads the same
      whether the reference is strict or the row shape is broken. `.` is in the
      sweep as a KNOWN-SHAPE anchor, not a finding — it is the 8.3 separator, so
      that row is the two-dot case D-FSPEC already settled.
      💰 **AND THERE IS ROOM.** `basic/fcbname-body.inc` has exactly ONE include
      site — `sub/fcbname.asm`, i.e. the sub-ROM **page-1 island**, which `make
      basic-reloc` printed at **957 B free** on 2026-09-05. So the check costs no
      main-ROM bytes at all. ⚠️ That is a wall reading and wall readings rot:
      re-run `basic-reloc` before spending it.
      ⚠️ `namspc-acceptance` owns the surface.
      🤖 AUTONOMOUS — the reference settles it; finishable unattended (no his-decision signal found).
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [x] ✅ **FIXED 2026-09-04 — 13 of 14 rows graduated the day they were filed.**
      `build_83_name` truncates POSITIONALLY and `parse_disk_fcb` RAISES
      `Bad file name` (ERR 56); knives 3/3 exact. Only `m.blank` (a blank
      filespec = no filespec) stays deferred — a `do_files` question, different
      site, ~~unmeasured on the other verbs~~.
      ✅ **"UNMEASURED ON THE OTHER VERBS" IS NO LONGER TRUE (2026-09-05).**
      `KILL"A:"`, `LOAD"A:"` and `SAVE"A:"` all read `Bad file name` on BOTH
      sides — now the scored rows `m.drvkill` / `m.drvload` / `m.drvsave`. So
      `bn_done`'s empty-name rejection is RIGHT for every verb that has no bare
      form, and the fix for this class must go in `do_files`; those three rows
      are what would catch it going anywhere else.
      🔴 **AND THE CLASS HAS A SECOND MEMBER, found the same day while checking
      D-FSPECCHAR for over-reach**: a filespec that is ONLY a drive prefix.
      `FILES"A:"` lists the directory on the CF-3300 (`5 entries + OK`) and is
      `Bad file name` here — deferred as `m.drvbare`, same site, same shape as
      `m.blank`. ⚠️ **NOT a regression from the character check**: `bn_done`'s
      comment has named `"A:"` as a rejected case all along, and
      `FILES"A:HI.TXT"` / `OPEN"A:HI.TXT"` are OK on both sides, so the drive
      prefix is stripped before the name builder and the new `:` rule never sees
      it.
      💰 **SITE AND BUDGET MEASURED 2026-09-05 — it needs a carve.** The fix
      cannot go in `parse_disk_fcb`: it RAISES internally (`jp pdf_badname`), so
      `do_files` never sees the reject, and the routine is shared with KILL /
      LOAD / SAVE, which `m.drvkill`/`m.drvload`/`m.drvsave` now pin as *correctly*
      rejecting. So it has to be a PRE-CHECK local to `do_files`: after
      `fname_expr` stages the string, skip spaces and an optional `X:` prefix and
      jump to `df_nofilespec` if the next byte is the closing quote.
      🔴 **That is ~15–20 B and `basic/files.asm` is included at
      `basic/main.asm:289`, i.e. MAIN PAGE 1, which `make basic-reloc` printed at
      6 B free on 2026-09-05.** It does not fit. ⚠️ Wall readings rot — re-run
      `basic-reloc` — but the SITE is structural and will not.
      ⚠️ **One tempting cheap version is WRONG**: testing `DISK_FCB_NAME[0]` for
      a space after the reject does not isolate the empty-name case, because a
      filespec whose FIRST character is illegal (`FILES CHR$(58)+"BC.TXT"`) also
      leaves position 0 unwritten — it would turn `m.sepchar` into a
      directory listing.
      🔴 **CONFIRMED IN FULL — AND MY OWN FIRST READING OF IT WAS WRONG.**
      Measured 2026-09-04 (D-FSPEC,
      [`docs/spec-basic-fnexpr2.md`](docs/spec-basic-fnexpr2.md)), 20 rows in
      `namspc-acceptance`.
      🔴 **THE FIRST PASS CONCLUDED "the filed symptom is not reproduced" AND
      PUBLISHED THAT TWICE. It was false.** `listface` reported the FIRST match
      in a fixed `ERRORS` tuple and stopped, so a row printing TWO messages lost
      one — and WHICH one survived was decided by the tuple's order, not by the
      machine. The real screen for `FILES"TOOLONGNAME.EXTRA"` is `load error`
      then `File not found in 10`. With the readout fixed, **every** malformed
      `FILES` form here reads `<load error+File not found>`
      [[readout-blind-to-its-own-subject]].
      ⚠️ **Two rows flipped AGREE -> DIVERGE** (`m.long`, `m.both`): the blind
      readout manufactured two false agreements, which is the expensive kind.
      🟢 **THE REFERENCE'S THREE RULES, all missing here:**
      • an **over-long** name/ext is NOT an error — it is **TRUNCATED, and not at
        the dot**: 8 chars of name then the **next three POSITIONALLY** as the
        extension, so `SAVE"TOOLONGNAME.BAS"` creates **`TOOLONGN.AME`** and
        `AB.EXTRA` creates `AB.EXT`. 🎯 **No error-face row could find this** —
        "reject" and "truncate" both give `File not found` at FILES; only a verb
        that WRITES separates them
        [[two-rules-that-coincide-on-every-row-you-have]]. The rule also explains
        the error rows: the pattern built is `TOOLONGN.AME`, which is why a real
        `TOOLONGN.BIN` on the disk still reads `File not found`;
      • a **structurally** malformed name (`""`, `"."`, `".."`, `"A.B.C"`) is
        **`Bad file name`**, RAISED — not printed-and-continued;
      • a **blank** filespec is **no filespec at all** and lists the whole
        directory.
      🟢 **AND THE VERB SWEEP WAS RUN THE SAME DAY — the blast-radius question is
      SETTLED, in the good direction.** `""` and `"A.B.C"` on every verb:

          verb   cf3300            zb
          KILL   Bad file name     File not found
          LOAD   Bad file name     File not found
          SAVE   Bad file name  🔴 load error
          OPEN   Bad file name  🔴 load error

      **`Bad file name` is UNIFORM on the reference**, so one check in the shared
      `parse_disk_fcb` is not a risk to manage — it is the correct site, because
      the reference's rule is shared too.
      🔴 **AND `load error` IS REAL — IT IS JUST NOT AT `FILES`.** `SAVE""` and
      `OPEN""` print exactly the symptom this item was filed for. **The filing was
      right about the mechanism and wrong about where to look**; its own proposed
      row could not have found it.
      ⇒ **THE FIX IS FULLY SPECIFIED:** `parse_disk_fcb` answers `Bad file name`
      for a structurally malformed 8.3 name (empty / second dot / only dots) and
      **not** for an over-long one, which is `File not found` on both. Disk ROM
      free was 8910 B on 2026-09-04. 13 rows DEFERRED in `namspc-acceptance`
      carry the whole contract.
      --- the original filing, kept because its MECHANISM note is still true ---
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
      ✅ **GAP (1) CLOSED and GAP (2) DEMONSTRATED, 2026-09-05 (D-FATVERB,
      `scratchpad/fatverb_knives.py`) — knives 4/4 exact.**
      • **K-FE2 / K-FE3 / K-FE4 each cut code only ONE verb executes** — BLOAD's
      own `cp BSAVE_DISK_ID` marker compare, `oo_input`'s own `mode = INPUT`
      store, and `fat_io_append`'s own re-use of the existing chain — and each
      moves its own `*-alive` row. That is precisely what gap (1) said was
      missing: the rows are now proven VERB-specific, not merely "the read path
      died".
      • **K-FE1 is the other half of the claim, and nobody had run it**: cutting
      the shared `fat_io_getbyte` moves **all six** byte-reading controls
      (load/run/bload/open/append/merge) while the DIRECTORY ones — `fat-alive`
      (FILES), `kill-alive`, `name-alive` — correctly hold. Those greens are what
      say the cut breaks the read layer and not the disk.
      • 🎯 **GAP (2) IS VISIBLE IN K-FE3's OWN RESULT**: breaking `OPEN FOR
      INPUT` moves `append-alive` too, because `append-alive` reads its data back
      through an `OPEN FOR INPUT`. The prediction SAYS so rather than discovering
      it, since a prediction omitting it would score the arm as a miss. Gap (2)
      is therefore no longer a suspicion — it is a measured coupling with a named
      mechanism.
      🔴 **AND THE MATRIX'S FIRST RUN REPORTED TWO FALSE MISSES — the READOUT,
      not the knives.** `append-alive` is printed TWICE (`FAIL append-alive …`
      and later `PASS append-alive (directory) …`, a second check under the same
      leading name), and a `name -> verdict` dict keeps the LAST, so a failing row
      read as passing. A row is FAILing if ANY of its lines says so
      [[readout-blind-to-its-own-subject]]. With that fixed, K-FE1 and K-FE4 were
      exact all along.
      ⚠️ **Gap (2) is DEMONSTRATED, not fixed**: `merge-alive`/`append-alive`
      still lean on a second verb. Rebuilding them to stand alone is separate
      work and is not done here.
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
      ✅ **VERIFIED 2026-09-05 — the note is right, and every part of it was RUN
      rather than re-read.** A filed claim is worth nothing until someone
      executes it, and all three parts of this one execute cheaply:
      • **K-FA7 is not vacuous**: loosened from `> $7FFF` to `> $0100` the build
      is REFUSED (rc 2) and the log names
      `FLD_ELEMENT_KEY_BIT15_NOT_FREE__ARRAY_REGION_MAY_EXCEED_…`.
      `basic/field.asm` restored byte-identically after.
      • **The two key spaces are disjoint by construction**, read at the sites:
      `basic/field.asm:245` does `set 7,h` on the ARYTAB-relative offset, so an
      element `k0` is `>= $80`; a scalar's `k0` is the UPCASED FIRST CHARACTER of
      a name whose `is_letter` the caller has already checked, so `$41..$5A`.
      • **And the assert guards exactly the right thing**: `set 7,h` is only a
      valid tag while the raw offset cannot already carry bit 15, which is what
      `(TXTMAX - TXTBASE) > $7FFF` refuses. The looser `offset>>8 <= $3A < $41`
      argument in the comment is the FALLBACK (disjoint even without the tag),
      needing `< $4100` — a different and weaker bound, correctly described as
      the 1.1x margin the two bytes widen.
      🟢 It is also now inside a swept denominator: `make build-assert-check`
      (added 2026-09-05) classifies it as one of the 18 BUDGET asserts, so it can
      no longer be the kind of guard nobody has enumerated.
      ⚠️ **STAYS OPEN ONLY AS A NOTE-TO-READERS**, which is what it was filed as:
      do not "fix" `s.fldarymix` or K-FA1.
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
      ✅ **MEASURED 2026-09-04 (D-SCRSLOT,
      [`docs/spec-basic-screenerr.md`](docs/spec-basic-screenerr.md) §10), and
      the worry was RIGHT.** Twelve rows, both references agreeing on all twelve,
      now in `screenerr-acceptance`:
      • 🔴 **slot 3 is the cassette BAUD RATE and its domain is `1..2`** —
        `SCREEN 1,,,0` and `SCREEN 1,,,3` are **ERR 5** on both references and
        ACCEPTED here.
      • 🔴 **the argument list stops at FIVE** — `SCREEN 1,,,,,1` is **ERR 2**
        there, accepted here.
      • 🟢 slot 4 (printer) really IS byte-wide (0/1/2 accepted, 300 → ERR 5), so
        the narrowing is specific to slot 3 rather than general to "later
        slots" — a shape the filing could not have guessed.
      🎯 `t.b1`/`t.b2` (accepted) and `t.b300`/`t.bneg` (ERR 5) are what make it a
      DOMAIN reading: without the accepted pair a refusal of 0 and 3 is equally
      "the slot rejects everything".
      💰 **PRICED, NOT FIXED: ~12 B for the slot-3 arm + ~8 B for the arity
      bound.** Main page 1 free was **6 B on 2026-09-04** (`scr_extra` and
      `spr_extra_arg` both live there; the latter already dispatches on
      `GFX_SARGN`, so the arm has a natural home). The three rows are DEFERRED in the gate with that price
      attached. 🔴 **RE-PRICE BEFORE INHERITING** — a decline resting on a wall
      reading rots [[repricing-page1-slice]].
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

      ✅ **RE-VALIDATED 2026-09-02: 19 rows, 6 DIFF — `wall.row solid.row h2 h4
      hp3 vp.solid`, exactly the pinned set.** Both references agree on every
      row; the 13 that agree include the two GREEN PINS below and every `vp.*`
      write-shape control, so the divergence is narrow and the fixture is sound.
      ⚠️ **THE PROBE RUNS FIVE ROUNDS AND A BARE INVOCATION RUNS ALL OF THEM** —
      a partial read of its output shows 4 rows and 2 DIFF, which is what a
      too-early wait predicate reports. It prints `done` when finished; wait for
      that, not for the first `DIFF`.
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
      2026-08-17 by D-GATEBLIND round 5 (§21.2). ✅ **READ AND ANSWERED
      2026-09-05 (D-GRPACDUP) — the residual asked for exactly this and the
      answer inverts the code's own justification.**
      🔴 **THE CIRCLE-SPOKES WORRY IS FALSE.** `gco_done` writes GRPACX/GRPACY
      **unconditionally, AFTER** calling `gco_spoke_s`/`gco_spoke_e`, so a
      spoke's own work-area write is always superseded — `gfx_line_op`'s own
      header says so in as many words ("a spoke's endpoint never survives as the
      last-referenced point"). The comment at `basic/graphics.asm` that keeps the
      duplicate *because* "the CIRCLE spokes ... rely on it" is therefore wrong
      about its reason; corrected in place, not deleted.
      🔴 **AND ON THE LINE PATH THE RESIDENT ALREADY WROTE p2**: `elg_second`
      parses p2 and then `call gfx_point_gate` → `gfx_work_area`, BEFORE the
      tenant runs. That is why the store is unobservable, and it is a mechanism
      the residual could not see from the gate's silence.
      🔬 **TWO INDEPENDENT KNIVES AGREE**: `K-GR4` (divert the store) and
      `M-GRPAC2` (feed it the Y value) each move **0 of 360 rows**. M-GRPAC2's
      own PREDICT named 8–9 rows and **had never been run**; corrected in the
      sweep, with the wrong prediction kept beside it.
      ✅ **VERDICT: KEEP THE WRITE, and the residual's "before removing ~3 B"
      is answered "do not".** The bytes are sub page 0, which `make basic-reloc`
      printed at **1348 B free** on 2026-09-05 — there is no budget pressure, so
      removing a redundant write buys nothing and risks a path no row watches.
      The conclusion the code reached stands; only its reason was wrong.
      --- the original filing ---
      `K-GR4` diverts
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
      `arc_ovf_wrap300` (the arc mask). ~~💰 Six or seven cuts, one each; there is no
      shared site the way `gdrw_err5` was for phase L.~~
      🔴 **THE COST ESTIMATE IS WRONG, MEASURED 2026-09-05 by walking every site.
      ONE of the nine has a retargetable branch; two are miscategorised; six
      would need a check SYNTHESISED, not a jump retargeted.**
      | row(s) | verb | reads | arm |
      |---|---|---|---|
      | `border16_flood_ok` | PAINT | **pixels** | ✅ **DONE** — `M-PAINTBDOM` |
      | `arc_ovf_r260`, `arc_ovf_wrap300` | arc | **pixels** | ⚠️ not acceptance rows at all |
      | `off_ok` | LINE | error code | ❌ nothing to retarget |
      | `clip_offscr_ok`, `clip_neg_ok` | CIRCLE | error code | ❌ nothing to retarget |
      | `offscreen`, `empty`, `bare_b` | DRAW | error code | ❌ nothing to retarget |
      🎯 **WHY `M-PSETOFF` WORKED AND THESE CANNOT.** PSET's off-screen decision
      is a BRANCH IN THE RESIDENT (`basic/graphics.asm:101`,
      `jp nc,exec_stmt`), where `gfx_err5` is reachable — so the cut is one
      retarget. LINE/CIRCLE/DRAW do not decide off-screen at all: they clip in
      the TENANT, at `gfx_plot_cur`'s three bare `ret`s (`sub/graphics.asm:665`
      /`669`/`672`), deep inside plotting loops that cannot raise. And `empty` /
      `bare_b` are accepted by the **absence** of any test — the only exit they
      share is `gdo_done`, which EVERY `DRAW` takes, so a cut there reddens the
      whole verb and isolates nothing. **These six rows read only the error code,
      so no cut that changes what is DRAWN can move them; the arm has to make the
      statement RAISE, which means writing a bounds check that does not exist.**
      ⚠️ **AND TWO WERE NEVER ACCEPTANCE ROWS.** `arc_ovf_r260` /
      `arc_ovf_wrap300` are documented IN THE PROBE as *"ONE-SIDED DETECTORS…
      blank on BOTH machines now, and a both-blank row is vacuous"*. Their arm is
      "make the mask paint again", not "make it refuse" — they belong to the
      arc-mask residual, not this one.
      ✅ **`M-PAINTBDOM` LANDED** (`ep_b_dom`: SCREEN 2's border domain narrowed
      from 0..255 to the nibble, so `PAINT(5,5),9,16` raises). PAINT's border is
      the one argument here that is genuinely domain-checked, which is why it has
      a branch. Measured: 2 rows red, ROM restored byte-identical.
      🔴 My prediction said "`border16_flood_ok` ONLY" and was one row too
      narrow. `b_s2_16_comma` moved too (`ref='E 2'` → `zb='E 5'`) — it is the
      row that races this domain against the grammar's trailing-comma ERR 2, and
      it is the reason the check sits ABOVE the fill, so a domain cut cannot help
      moving it. **A prediction can be too narrow because it forgot which row
      exists to pin the check's PLACEMENT.**
      💰 **REVISED: 1 done. 6 need a synthesised check each (not a retarget) —
      genuinely more expensive than filed, and worth asking whether an
      error-code-only acceptance row is the right shape before writing six of
      them.** 2 to be re-filed under the arc mask.
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
      ✅ **FIXED 2026-09-05 (D-Q3CTL), and it needed NO new machinery — nor
      either of the two remedies suggested above.** The control never disabled
      interrupts, so **it needs no restore at all**: the line was pure ceremony
      inherited from a shared template. The restore is now the case's own
      (`ie_off` keeps `VDP(1)=VDP(1)OR32`, the control's is empty), so the two
      programs differ only where they must. ⚠️ The restore sits AFTER the
      measurement in both, so dropping it cannot move the reading the control
      takes — and it does not: `delta=62` / `246`, unchanged.
      🔬 **RE-RUN OF THE VERY MUTATION THAT EXPOSED IT.** Under `M-G8PAREN`,
      `C-BIOS ie_off` now **FAILs** (`delta=None`) while `C-BIOS control` still
      **PASSes** (`delta=246`). Before, both moved. The pair can now tell "the
      emulator is dead" from "the subject is broken", which is the whole job of a
      control. The sweep's own PREDICT for `M-G8PAREN` already said "Q3 ie_off
      too", implying the control holds — that prediction is now satisfied instead
      of contradicted.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).

- [x] ✅ **`M-SPRPBASE` AND `M-SPRSZAPL` EACH HAVE ONE ROW THAT *SHOULD* SEE THEM
      AND DOES NOT.** CLOSED 2026-09-05 — **both confirmed by re-running the two
      mutations, and only ONE was a row defect.**
      • Baseline re-measured first: under `M-SPRPBASE`, `pat_8_empty` PASSed
      (`ref='00000000' zb='00000000'`) while all seven sibling pattern rows
      FAILed; under `M-SPRSZAPL`, `put_pat63_16` PASSed while `put_pat64_16`
      FAILed (`ref='ZE 5' zb='ZK'`). The filing was exact.
      • **`pat_8_empty` FIXED.** 🎯 The generalisable part is not "give it a
      neighbour" but **an empty write is indistinguishable from NO write at ANY
      single address** — freshly cleared VRAM already reads what a correct `""`
      leaves, so no choice of window fixes it alone. The window must contain
      something NON-ZERO whose POSITION moves. Entry 4 now holds `204`s and the
      window spans both entries: correct `00000000`+`204`×8, mutant sixteen
      zeros. Re-measured PASS → FAIL, red rows 13 → 14, green on the unmutated
      ROM with both sides agreeing.
      • 🔴 **`put_pat63_16` WAS NOT A ROW DEFECT — THE PREDICTION WAS**, and it
      had been contradicted inside the same dict since it was written:
      `M-SPRPATSC`'s entry says *"put_pat63_16 should NOT move: accepted either
      way"* while `M-SPRSZAPL`'s listed it as expected-to-move. **Two
      predictions disagreed about one row and neither was read against the
      other** — a class worth watching in any table of per-mutation expectations
      [[two-sections-of-one-doc-disagreed]]. Corrected, with `put_pat64_16`
      named as the discriminator it always was.
      Recorded in [`docs/gate-blindness-sweep.md`](docs/gate-blindness-sweep.md)
      §9 beside the original over-prediction list; `cls_keeps`/`M-SPRXREST`, the
      third entry there, is untouched and stays open.
      ⚠️ **Instrument hazard met on the way, not fixed:** running
      `gate_blindness_sweep.py` with a SUBSET of mutations rewrites the tracked
      `scratchpad/gate_blindness_round2.json` to just that subset — my
      one-mutation re-run replaced `M-GRPAC2`'s recorded prediction with
      `M-SPRPBASE`'s. Reverted by hand here, and the only signal was `git
      status`. A subset run should not be able to narrow a recorded round
      [[a-mechanical-fix-can-break-a-different-invariant]].
      --- the original filing ---
      Filed 2026-08-17 by D-GATEBLIND round 2 (§9). `pat_8_empty`
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

- [x] ✅ **`fp_exp`/`fp_log`'s `$8000` REACHABILITY WAS REASONED, NOT
      MEASURED.** CLOSED 2026-09-05 (D-EXPBAND). **Unreachable in both, and the
      bound is the DOMAIN, not the arithmetic.** `evmc_exp` disposes `dexp>=4`
      (`|x|>=1000`) before `fp_exp` runs and step 2's own `dexp>4` arm jumps to
      the tails WITHOUT negating, so the largest `|n8|` that can reach the
      negation site is `round(999.9999999999*8/ln10) = 3474` — short of `$8000`
      by 9.4x. `e'` is `dexp-1` off an FPNUM field, so `|e'| <= 64`, short by
      ~500x. ⚠️ THE PART THAT WAS ACTUALLY UNMEASURED was whether the domain
      guards hold, and they do: `EXP(-999.9)` returns `0`, which ONLY step 3's
      underflow tail produces, so `fp_exp` ran and negated an `n8` of ~3474 —
      now a `math-acceptance` row, together with the format corners
      (`EXP(1E10)`, `EXP(-9.9E62)`, `LOG(1E-64)`, `LOG(9.9E62)`, all disposed
      identically on both references).
      🎁 **AND THE ROW LADDER FOUND SOMETHING THE ITEM DID NOT ASK FOR.** The
      reference's documented EXP underflow deviation (spec §12.9) is a **BAND,
      not a half-line**: refs return `0` — agreeing with us — for results in
      `[1E-65, 1E-64)` AND for results `< 1E-129`, and raise `Overflow` only in
      between, a band exactly **64 decades wide** with both edges on an exact
      decade (measured to <0.02 in `x` on BOTH references). Every sample ever
      taken (`EXP(-200)`, `10^-70.5` = `EXP(-162)`) fell inside it. 🔴 `exp(-1000)`,
      the anchor `sub/fp_exp.asm` cited as PROOF we deviate, is a row where the
      references return `0` too — it never witnessed a deviation
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. The DECISION is
      unchanged and strengthened (0 is the refs' own answer on both sides);
      D-EXPNEG stays reverted; the four band edges are now gate rows so the
      extent is gated instead of asserted in prose. Also measured: the deviation
      is EXP-LOCAL (`1E-40*1E-30` → `0` on all three), NOT the shared
      `round_and_finalize`, which step 8's own comment invites you to believe.
      --- the original filing, kept because its VERDICT note is still true ---
      Filed 2026-08-11 by D-NEG8K (same doc, §4.4). Both take a
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

- [x] ✅ **THE THREE SCALE STATES ARE NOT SWEPT THROUGH `X` SUBSTRINGS OR
      `=var;` SUBSTITUTION.** CLOSED 2026-09-05 (D-DSCALE round 4). Nine rows
      (`d.eq*`, `d.xs*`) in `lineerr-acceptance`, on both references:
      **all nine agree on all three sides — no divergence, no code change.**
      • The `=V;` path is the SAME STATEMENT as the literal one: `d.eq8193`
      (`V=8193:DRAW"BU=V;"`) reads `57347`, byte-for-byte `d.def8193`'s literal
      reading, and `d.eqs48193` reads its `S4` twin `8195`.
      • The filed item's own proposal — `V=-25536`, 40000's int16 face — works
      too (`25540`/`58308`, exactly `d.lit2`/`d.s4.40k`), ⚠️ **but it is not the
      row that settles it**: it carries a second question (does a negative count
      reach the multiply as `$9C40`?). `8193` is positive, fits int16, and is
      `d.def8193`'s minimal discriminator, so it separates the two states with no
      domain and no sign question attached. **A row proposed in a filing can be
      one question wider than the filing needs.**
      • The `X` path asks SCOPE, not domain (a count inside a substring is still
      literal text). 🎯 `d.xspost` (`A$="S4":DRAW"XA$;BU40000"`) reads `58308`,
      not the never-set `25540`: **an `S` inside a substring PERSISTS after the
      substring returns** — a substring has no scale state of its own. The two
      hypotheses give different numbers, which is what makes it a discriminator
      rather than a row that agrees.
      Recorded at `sub/graphics.asm`'s `gdrw_scale` (so no future fix re-scopes
      it), in `docs/spec-basic-lineerr.md` §12.9, and in the probe's own
      DENOMINATOR — which had said the X path was unswept and now names what
      still is (`X`'s own argument domain, `A`/`C`'s, and the coroutine's second
      and later round trips). `lineerr-acceptance` 219/219, 0 deferred.
      --- the original filing ---
      Filed 2026-08-11 by D-DSCALE. §12 measured the
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

- [x] ✅ **K-FA5's FALSIFIABILITY PREMISE IS STALE, AND SO ARE FOUR OTHER
      COMMENTS.** RE-RUN 2026-09-05 (`scratchpad/fa5_knife.py`). The entry asked
      for exactly one thing — *"what has NOT been done is re-running K-FA5 to
      measure what the cut now reads"* — and the answer is **nothing: 0 of 16
      rows move.** The ROM hash changes across the plant, so the cut took.
      🔬 **AND THE ROW SET WAS EXTENDED BEFORE CONCLUDING THAT**, because "0 rows
      moved" is a claim about the rows as much as the code. The reworded comments
      say the check still earns its place by raising **before `ex_field`'s side
      effects** — and no row read the field table after a FAILED resolve; every
      `s.fld*` row uses a valid subscript
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]]. Two rows now do,
      at both target positions, each agreeing with the CF-3300:
      • `d.aryoor2` — valid target FIRST, then out-of-range: `LEN(A$(1))` = **5**.
      The earlier target IS committed before the later one fails, on both
      machines. ⚠️ So "raises before the side effects" is **false as stated for
      earlier targets**; the abort protects only the failing target's.
      • `d.aryoor3` — out-of-range target FIRST: `LEN(A$(1))` = **0**. Nothing
      commits, on both machines.
      **Neither moves under the cut either.**
      🔬 **A SECOND ARM SETTLES THAT IT IS NOT DEAD CODE.** An UNCONDITIONAL,
      distinguishable ERR 5 planted at the same site moves **14 of 16** — the
      abort executes. 🔴 My write-up of that arm called it "unambiguous" and it is
      not: the one row that HELD (`d.aryoor3`) holds because it traps the error
      and reads `LEN`, so ERR 5 and ERR 9 give it the same reading — a row built
      to be blind to the error's identity is blind to the arm too. What it does
      establish is the reverse of the header-comment story: `d.aryoor` MOVED, so
      for a single out-of-range target control **does** return to this `jp nz`,
      and `tgt_parse`'s *"a failed array resolve does NOT return"* describes some
      other failure mode.
      🎯 **THE STANDING RESULT, as a reading and not a mechanism: the abort runs,
      and removing it changes no BASIC-visible outcome across 16 rows** — the
      statement boundary reports the same error, and the field table ends in the
      same state at both target positions. The reworded justification is
      therefore still UNWITNESSED; it is not refuted, but nothing distinguishes
      having the check from not having it. ⚠️ Leave the check in — a defensive
      abort that no row can see is not the same as one no row NEEDS, and the cut
      leaves `FPERR` set with `(TGT_ADDR)` unset for whatever the rows do not
      reach.
      --- the original filing ---
      Filed 2026-08-09 by D-STMTPEND
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
      🔬 **ONE HYPOTHESIS ELIMINATED WITH EVIDENCE, 2026-09-05 — STILL OPEN.**
      `WIDTH`'s own domain is **1..40, and `WIDTH 0` is itself ERR 5** — measured
      on the VG-8020 and zerobas (`WIDTH 41` too; `WIDTH 1`/`WIDTH 40` not).
      Every `FP*` constant in the probe is `0*(<faulting expr>)`, so a row's
      argument collapses to **0** whenever its fault does not fire, which makes
      the READER VERB able to raise the very code the pending cell delivers —
      and would have explained all four rows AND why `n.5.w` (`WIDTH {FP5}+1`,
      argument 1, legal) was the one that behaved.
      🔴 **Tested twice, refuted twice.** (1) Cutting `penderr_set`'s store
      outright: `n.dz.w` reads **0, not 5** — `WIDTH 0`'s own ERR 5 is recorded
      through the SAME cell, so a cut that silences the cell silences the
      collision with it. (2) Cutting ONLY `evmc_sqr_err`'s writer: `o.nn.5dz`
      reads 11 and `n.5.w` reads 0, **identically with and without** a leading
      `1+` on every row — the rows detect a per-writer defect unaided. A `1+`
      repair was drafted and **REVERTED**: it changed no reading in either cut,
      and lengthened the typed line enough to provoke mis-echoes.
      ⚠️ **AND I COULD NOT REPRODUCE THE ORIGINAL OBSERVATION AT ALL**, which is
      the more useful half. Under the cut this entry describes, the probe's four
      POSITIVE CONTROLS now fail (correctly — with nothing recorded, `n.dz.w`
      reads 0 where it wants 11), so it REFUSES and prints no scored rows. The
      four rows' readings under that cut are therefore **no longer obtainable
      from this probe as it stands**; whatever produced them in 2026-08 cannot be
      re-read today without either a narrower cut or a mode that reports rows
      through a control failure. 🎯 **The next step is to find out whether that
      run's cut was the same one** — this one neuters the store inside
      `penderr_set`, and a cut placed elsewhere may leave a writer standing that
      mine does not.
      The `WIDTH 0` fact is recorded in the probe beside the constants so the
      next reader does not re-derive it.
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

- [x] 🟢 **A SECOND DISK `OPEN` — FIXED 2026-09-02 (D-OPEN2FIX), +2 B, 9 DIFF →
      1.** [`docs/spec-basic-open2fix.md`](docs/spec-basic-open2fix.md).
      🎯 **A REGISTER CLOBBER, AND THE GUARD WAS ONE CALL TOO LATE.** `HL` (the
      token cursor) enters `fch_claim` as `$EC15` and the statement boundary
      reads it back as `$E9FB`, so the parser resumes on garbage and raises
      `Syntax error` AFTER the OPEN has completed — which is exactly why the
      channel table showed both channels correctly open. The call site already
      guards HL, one call below, for `fat_io_*`'s CALSLT; `fch_claim` runs its
      OWN CALSLT (`fch_save_active` → `fch_ctx_addr`) and was uncovered, though
      its header says `Clobbers regs.`
      🔬 **FOUND WITH THE DEBUGGER THIS ITEM ASKED FOR.** openMSX is driven
      through Tcl, so breakpoints and watchpoints are available to the same
      harness the probes use; breakpointing the OPEN path and logging hit order
      showed the cursor moving across `fch_claim` in one run.
      🔴 **AND IT REFUTED TWO OF THIS ITEM'S OWN CONCLUSIONS.** A watchpoint on
      `FPERR` recorded only TWO writes in the whole run, both `00`, the second
      from inside `record_errline` (the consume); `penderr_set` and `ev_f_empty`
      never fired. So it is **not a deferred error and nothing sets FPERR=4** —
      the filed next step ("what remains is finding what sets `FPERR`=4") was
      chasing something that does not happen. A direct `jp stmt_error`.
      🎯 **UNTESTED BY CONSTRUCTION, exactly as this item said**: `fch_claim`
      returns at its `ret z` before any CALSLT when the channel already owns the
      globals, so the missing guard is unreachable with a single channel.
      ✅ **9 DIFF → 1 of 18.** Two random channels either order, two sequential,
      mixed, with/without `LEN=`, `MAXFILES=2` and `3` — all now agree. Controls
      green, `n.nomaxf` still `Bad file number` on both.
      ➡️ **ONE ROW LEFT, WHICH THE Syntax error WAS HIDING — filed below.**
      [[a-scratch-register-that-was-the-callers-value]]

- [ ] 🔴 **THE SAME FILE ON TWO CHANNELS IS ACCEPTED HERE AND REFUSED ON THE
      CF-3300.** Uncovered 2026-09-02 by D-OPEN2FIX, which removed the
      `Syntax error` that was killing every two-channel open before this could be
      reached.
      ```
      MAXFILES=2 : OPEN"TS.DAT"AS #1 : OPEN"TS.DAT"AS #2
          cf3300 -> File already open      zb -> OK
      ```
      Row `e.same2` in `scratchpad/open2_probe.py`, the only remaining DIFF of 18.
      ✅ **CHARACTERISED 2026-09-02 (D-DUPOPEN,
      [`scratchpad/dupopen_probe.py`](scratchpad/dupopen_probe.py)), 11 rows,
      6 DIFF — AND THE RULE IS EXACT:**

          s.same      TS.DAT twice                cf3300 File already open  zb OK
          s.case      ts.dat after TS.DAT         cf3300 OK                 zb OK
          s.space     "TS.DAT " (trailing space)  cf3300 File already open  zb OK
          s.newtwice  a name NOT on disk, twice   cf3300 File already open  zb OK
          s.modes     same file, different mode   cf3300 File already open  zb OK
          s.seqsame   sequential, same name       cf3300 File already open  zb OK

      🎯 **CASE-SENSITIVE, TRAILING-SPACE-INSENSITIVE, AND IT READS THE CHANNEL
      TABLE, NOT THE DISK.** `s.newtwice` refuses a file that does not exist yet,
      so the comparison cannot be a directory lookup; `s.space` collapsing and
      `s.case` NOT collapsing is exactly the 11-byte space-padded 8.3 name field
      compared WITHOUT case folding. Mode is irrelevant.
      🔴 **AND THE CHEAP IMPLEMENTATION ROUTE IS REFUTED.** The per-channel
      context block already carries `FWR_DIRSEC`/`FWR_DIROFF` — the directory
      entry's LOCATION — so comparing those would cost ZERO new RAM and
      reproduces five of the six rows. It dies on `s.case`: `q.upcase` shows a
      file created as `zz2.dat` opens fine as `ZZ2.DAT`, so the lookup is
      case-insensitive and `ts.dat`/`TS.DAT` are ONE directory entry — a dirent
      comparison would REFUSE `s.case`, which the reference ALLOWS.
      💰 **SO THE PRICE IS RAM, AND IT IS NOT SMALL.** There is no `FCH_NAMES`
      array — `FCH_MODES` and `FCH_RECLENS` are per-channel, names are not — and
      the 50-byte context block is a span of existing sysvars with no name in it.
      Storing the parsed name per channel is **11 B × `FCH_CEIL` (15) = 165 B of
      page-3 RAM**, plus the compare. ⚠️ **RAM HAS NO GATE** — `wall-assertion-
      check` covers ROM only — so this is not a wall you can read.
      🙋 **NEEDS-JOOST — the measuring is DONE, the spend is yours.** 165 B of
      RAM to make zerobas refuse what it currently permits. Worth noting it is
      protective and not cosmetic: two channels writing one file corrupts it.
      [[deffn-ramhunt-slice]]

- [x] 🟢 **(superseded, kept for its row work) A SECOND DISK `OPEN` RAISES A
      SPURIOUS `Syntax error` — THE OPEN
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

- [ ] 🐌 **`PUT` IS SLOWER THAN THE REFERENCE — AND THE "UNTRAPPABLE HANG" THIS
      ITEM WAS FILED AS IS WITHDRAWN (D-PUT3SLOW, 2026-09-02,
      [`docs/spec-basic-put3slow.md`](docs/spec-basic-put3slow.md)).**
      🔴 **NOTHING HANGS.** Every reading behind the hang claim was taken at a
      **2.5 s step**, and `step` is how long the harness waits before typing the
      next line — so a statement needing longer reads as a blank screen.
      **"Hung" and "slow" are the same observation at a fixed step.** Same
      program, same machine, only the wait changed:

          3 PUTs + LOF(1)      2.5s blank | 5s 128 | 10s 128 | 90s 128
          4 PUTs + LOF(1)      2.5s blank | 5s 128 | 10s 128 | 90s 128
          the filing's own LSET+STRING$+PUT x3 shape   -> OK from 5s up
          PUT then DSKF(0)     2.5s blank | 5s 706 | 20s 706 | 90s 706

      The answers are also CORRECT (706 is the CF-3300's own answer). That
      dissolves "untrappable" too — the most alarming part of the filing — since
      **no handler runs because there is no error.**
      ✅ **THE DIVERGENCE IS REAL, AND IT IS PERFORMANCE.** The obvious worry is
      the probe's own asymmetry (`SIDES` gives cf3300 `step=4.5`, zb `step=2.5`),
      which would manufacture exactly this. **Controlled: the CF-3300 passes
      every row at zerobas's own 2.5 s step.** So zb needs >2.5 s where the
      reference needs <2.5 s. Bounded **>2.5 s and <5 s**, not pinned.
      🔴 **BOTH PROPOSED MECHANISMS REFUTED.** A per-`PUT` cluster leak (growing
      chain ⇒ longer `frnd_locate` walk each time) predicts falling free space:
      `DSKF` after 1/2/3 writes reads **706 / 706 / 706 on both machines** — the
      chain does not grow. And `fat_count_free`'s "cache keyed by `FWR_FIRST`"
      (the same cell `frnd_locate` writes) initialises it to `$FFFF` on entry, so
      it inherits nothing.
      ⚠️ **A CLAIM I AM NOT MAKING:** that the third `PUT` is individually
      slower. 1 and 2 pass at 2.5 s and 3 does not, but the harness types at
      fixed intervals, so three writes of ~2.4 s each overrun **cumulatively**
      with none of them growing. Flat-vs-rising is UNMEASURED, and the leak
      refutation removes the only mechanism proposed for rising.
      ➡️ **AT A 20 s STEP, ZB MATCHES THE CF-3300 ON ALL TWELVE ROWS.** There is
      no behavioural divergence here at all.
      ⚠️ **AND D-PUT3CONSUME's "DSKF AFTER ONE PUT DIES" (committed EARLIER THE
      SAME DAY) IS WITHDRAWN BY THIS** — same cause, same correction. It returns
      706, slowly.
      ➡️ **WHAT IS STILL OWED:** the per-`PUT` cost, measured rather than
      bounded, against the reference's. A write loop at ~2x the reference is a
      real defect against a faithful-implementation charter — just not the
      correctness emergency this was filed as.
      🤖 AUTONOMOUS — the reference settles it; what is left is a timing
      measurement, not a bisect.

      ⬇️ **THE ORIGINAL FILING FOLLOWS, KEPT BECAUSE ITS ROW WORK IS SOUND** —
      every characterisation below (PUT count, not layout; survives CLOSE; not
      the LSET) reproduces; only the word "hangs" was wrong.
      🔴 **THE THIRD `PUT` OF A SESSION HANGS ZEROBAS, UNTRAPPABLY — AND A
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
      ✅ **RE-MEASURED 2026-09-02 (D-PUT3CONSUME,
      [`scratchpad/put3consume_probe.py`](scratchpad/put3consume_probe.py)), AND
      THE CLAIM SURVIVES A CONFOUND OF MY OWN MAKING.** The first design read
      `DSKF(0)` at the end of every PUT ladder — and `DSKF` after a PUT turns out
      to die on its own (below), so every "third PUT" row had two sufficient
      causes. `x.put3lof` reads `LOF(1)` instead and touches no `DSKF`:
      **3 PUTs `<NO OUTPUT>` on zb against `128` on the CF-3300, while 2 PUTs
      read `128` on both.** The filed claim stands, now on a row that cannot mean
      anything else. [[two-rules-that-coincide-on-every-row-you-have]]
      🔴 **AND A SECOND, SIMPLER DEFECT WAS UNDER IT: `DSKF(0)` AFTER A SINGLE
      `PUT` DIES.** One write, not three:

          OPEN"TS.DAT"AS #1 LEN=128 : FIELD#1,128 AS A$
          PUT#1,1 : PRINT"[";DSKF(0);"]"     cf3300 706   zb dies

      `x.dskf0` (no PUT) reads 707 on both and `x.getdskf` (a GET, then DSKF)
      reads 707 on zb, so it is the **PUT** that arms it, not any disk op — and
      ONE is enough.
      🎯 **THE FAILURE SIGNATURES DIFFER, AND THAT LOCALISES BOTH.** The 3-PUT
      rows print **nothing at all** (`<NO OUTPUT>`) — they die before reaching
      the `PRINT`. The DSKF rows print **`[`** and stop (`<UNREADABLE: [>`), so
      the statement is reached and the machine dies **inside `DSKF(0)`**. That
      distinction did not exist before 2026-09-02, when the probe's blank-face
      fallback was made to carry the text: both readings used to be `<NO OUTPUT>`
      and were indistinguishable.
      ⚠️ **AND THE `d.lof*` LADDER SAYS THE FILE IS FINE**: `LOF(1)` reads 128
      after one PUT and after two, on both machines. Whatever accumulates is not
      visible in the file's length.
      ⚠️ **A REFERENCE COLUMN I FIRST MIS-READ**: three CF-3300 rows showed
      `<NO OUTPUT>` and looked like the ORACLE failing. They are
      `<Input past end>` — a `GET` past EOF on a freshly-created empty file,
      correct behaviour — and `basic_probe_fldwidth`'s error alphabet simply did
      not contain that message. **An unreadable answer on the oracle side reads
      as "the reference is broken", which is the worst direction for this class
      of mistake to point.** Alphabet re-derived from the ROM's own `db` strings
      and the loud fallback added.
      ➡️ **NEXT: two separate hunts, and the DSKF one is cheaper.** `DSKF` needs
      only ONE `PUT` to arm and dies inside a known, small routine, so whatever a
      `PUT` corrupts is reachable from there; the 3-PUT hang may share the root.
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
      🔬 **ATTEMPTED 2026-08-30 AND REVERTED AT THE LAST STEP — three of the four
      pieces WORK, and the fourth is localised.** The tree is back at the
      face-only commit; nothing below is speculation, it was built and measured.
      - ✅ **`mul_reclen` shift-add multiply: CORRECT.** Verified by
        `tests/test_open_len.py`'s independent oracle for r=100 AND r=255,
        record 6 (within=500) included. ~9 B.
      - ✅ **`frnd_seg1` / `frnd_seg2`, one shared pair for `PUT` and `GET`, and
        NO NEW RAM** — n1 is the only value that must survive the second sector
        and it fits on the stack, so the RAM question the design below worried
        about does not arise. A record touches at most two sectors, so it is one
        optional second segment, never a loop.
      - 🔴 **`write_sector` CLOBBERS BC**, and n1 lives there. Without a
        push/pop around it the NO-STRADDLE path reached `frnd_seg2` with garbage,
        invented a second segment and wrote rubbish — `LEN=128` regressed. Caught
        by the `a.tiling` CONTROL row, i.e. by a length the change was not even
        about.
      - 🔴 **STILL OPEN: the SECOND sector on a `PUT`.** `LEN=100` with record 6
        still fails. The first sector has a read-vs-fill decision
        (`frp_readold` / `frnd_fill_fwbuf`) driven by `GP_OLDNSEC`; the second
        segment re-enters `frnd_locate` + `read_sector` with no equivalent, and a
        newly-allocated sector past EOF has nothing to read. That distinction is
        what the tail needs.
      - ⚠️ Adding the two-segment tail also pushed `jr nz,frp_err` out of
        relative range; both early rejects need `jp`.
      📐 **THE ORIGINAL DESIGN NOTE (its RAM paragraph is superseded by the
      stack, above):**
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
      ✅ **SCOUTED 2026-09-04 — D-RECLENDOM
      ([`scratchpad/reclendom_probe.py`](scratchpad/reclendom_probe.py), 21 rows),
      AND THE RULE IS EXACT:** the reference accepts **1 ≤ r ≤ 256** and rejects
      0, 257, 300, 512, 1000, 32767 and −1; zerobas accepts only the **powers of
      two** in that range (1, 2, 128, 256 pass; 3, 7, 100, 127, 255 do not).
      🔴 **THE FILED FACE IS STALE: BOTH SIDES RAISE ERR 5**, not `Syntax error`.
      The CODE already agrees and only the DOMAIN differs — third stale filed
      face this session.
      🔴 **AND THE ENTRY'S OWN FRAMING IS REFUTED.** It says this "is an `OPEN`
      parse question, not a `FIELD` one". Measured, the reference supports a
      non-tiling record END TO END: `LEN=100` then `FIELD #1,100 AS A$` **works**
      (`f.100` → 0), fielding one byte PAST the record is the ordinary
      `FIELD overflow` (`f.over` → **ERR 50**), and `LSET` + `PUT #1,1`
      **writes it** (`p.100` → 0). `f.128`, the tiling twin, is 0 on both sides,
      so FIELD itself is not the variable.
      ➡️ **SO THE PARSE CHECK IS GUARDING A GEOMETRY LIMITATION, AND THE PRICE IS
      THE GEOMETRY, NOT THE PARSE.** `GET`/`PUT` here are built on
      `recPerSec = 512/r` with no straddle; dropping the power-of-two test alone
      would accept `LEN=100` and then compute the wrong sector — **worse than the
      error it replaces**. Removing the check is a one-liner and is the WRONG
      one-liner.
      💰 Still not priced, but priced AGAINST THE RIGHT THING now: straddling
      record geometry.
      The framing this replaces read: ⚠️ **NOT PART OF THE ERR-50 RULE and must
      not be folded into it** — it is an `OPEN` parse question, not a `FIELD` one.
      💰 Not scouted, not priced:
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

- [x] 🟢 **`badfnum-acceptance` REPORTED `1 unfiled divergence` AND NEVER SAID
      WHICH ROW — THEN PASSED ON RETRY.** Seen 2026-09-02 in a full battery
      (`rc 2 -> 0`, "recovered flake"). The summary line is
      `93 cases, 0 mangled, 0 oracle drift, 1 unfiled divergence` on the failing
      run and `... 0 unfiled divergence` on the retry, and **nothing anywhere in
      the log names the row.**
      🎯 **AN UNNAMED OUTCOME READS AS NO OUTCOME**
      [[an-unnamed-outcome-reads-as-no-outcome]]. A count says the detector
      fired; only the label says what it caught — the same lesson
      `probe_signal.add`'s docstring already records for fallbacks ("the first
      run reported '1 fell back' out of 72 and could not say WHICH row"). A
      TRANSIENT divergence is exactly the case where the log is the only
      evidence there will ever be, and this one threw it away.
      ⚠️ **AND THE RETRY LAUNDERED IT.** Under `run_gates.py`'s flake-vs-real
      rule a green retry is accepted, so a stochastic row divergence in a
      differential currently leaves no trace at all. That rule is right for
      contention; it is wrong here, and the log cannot tell the two apart
      because it does not name the row.
      ➡️ Make the probe print the diverging row's label, expected and observed —
      then a repeat is diagnosable from the log alone.
      🔴 **THAT FILING WAS WRONG, AND I CORRECTED IT THE NEXT MORNING.** The
      probe DOES name the row: its per-row table prints
      `DIVERGE (UNFILED)` against the label, expected and observed. I had only
      `tail`ed the log and never grepped it — **an incomplete read reported as an
      absent feature** [[a-justification-parenthesis-is-an-unrun-claim]].
      🎯 **THE REAL GAP IS THAT THE EVIDENCE DOES NOT SURVIVE.**
      `tools/run_gates.py:453` does `rm -rf {OUT}` at the START of every battery,
      so the failing run's log — the only artifact that can diagnose a
      stochastic failure — is destroyed by the NEXT battery. And because the
      retry turned the battery green, nothing prompts anyone to look before
      then. That is why the row was unavailable by the time I went back for it.
      ✅ **FIXED 2026-09-02 (D-FLAKEKEEP)**: a unit that goes red now has its log
      AND its retry log copied to `/tmp/zerobas/gate_flakes/<stamp>-<unit>/`
      before the next battery can wipe them — outside `OUT`, under the sanctioned
      temp root, and untracked so the pool-write detector is unaffected.
- [x] 🟢 **8192 B OF BASIC MEMORY IS RESERVED BY A CONVENTION NOBODY PRICED —
      `$C000`–`$E000` HOLDS TWO ALLOCATED BYTES.** Measured 2026-09-01
      (D-FREGAP, [`docs/spec-fre-gap.md`](docs/spec-fre-gap.md)), asked while
      reviewing the boot banner: what would a `Bytes free` line print?
      📏 **`FRE(0)`: zerobas 14767, CF-3300 23348, VG-8020 28733** — and the
      shape says it is NOT a leak: zerobas's HIMEM is HIGHER than the CF-3300's.
      Not the file buffers either (`MAXFILES=0` recovers 41 B).
      🎯 **THE REAL CEILING IS `TXTMAX $BB00`, NOT HIMEM.** `$BB00 − $8001 =
      15103`, against `FRE(0) = 14767` — that is the whole figure. Above it,
      walked with `scratchpad/rammap_sweep.py` and an `equ` sweep, never read off
      a comment:
      | span | size | what is there |
      |---|---|---|
      | `$BB00`-`$C000` | 1280 B | `DETOKBUF`, a one-shot detokenise buffer |
      | `$C000`-`$E000` | **8192 B** | the BLOAD/boot region — **2 bytes allocated** (`GFX_DJ`/`GFX_BAD` at `$C120`) |
      | `$E000`-`$F380` | 5000 B | the real workspace, 502 named cells |
      ⚠️ **THE SOURCE KNEW THE SMALL LEVER AND NOT THE BIG ONE.** `sysvars.inc`
      states the rise is "BOUNDED BY DETOKBUF" — true, and worth only ~768 B.
      The 8192 B `$C000` reservation is priced NOWHERE, and the reference does
      not make it: the CF-3300 runs BASIC to `HIMEM $DE77` and expects a program
      that BLOADs high to lower `HIMEM`/`CLEAR` first.
      🙋 NEEDS-JOOST — raising the ceiling over `$C000` changes where a BLOAD or
      a boot sector may safely land, and its failure mode is a SILENTLY
      overwritten program. That is a design call, not a measurement. The
      measuring is done: the prize is ~768 B behind `DETOKBUF` and **~8 KB behind
      the convention**.
      🔬 Worth a look either way: the two bytes at `$C120` are stranded above a
      boundary every other allocation respects.
      ✅ **SPENT 2026-09-01 (D-RECLAIM,
      [`docs/spec-reclaim.md`](docs/spec-reclaim.md); rows in
      `scratchpad/reclaim_probe.py`) — `FRE(0)` 14767 → 22959, +8192 B, ZERO ROM
      COST** (low 106 B, page 1 331 B, both unchanged). From **8581 B short of
      the CF-3300 to 389 B short.**
      🎯 **THE DECISION WAS JOOST'S AND IT WAS ONE SENTENCE**: *"BASIC and DOS
      never co-exist."* That is what makes the `$C000`–`$E000` DOS territory
      (boot load, kernel work area, BDOS dispatcher, kernel FCB, DOS work area)
      free in BASIC mode — and the reference already proves the model, running
      BASIC to `HIMEM $DE77` and expecting a program that BLOADs high to
      `CLEAR`/`HIMEM` down first.
      ➡️ Three constants: `TXTMAX` and `DETOKBUF` `$BB00` → `$DB00` (the buffer
      tops out exactly at the `$E000` workspace floor), and the two stranded
      bytes rehomed to `$E220` / `$E3E5`, cells this file already documents as
      retired.
      🔴 **THOSE TWO BYTES WOULD HAVE CORRUPTED SILENTLY** — with the ceiling
      raised they sit INSIDE the text area, written by any draw, wrecking a
      program over ~16 KB. Small test programs would never have caught it. Being
      stranded above a boundary is what made them findable.
      🔬 **THE ROWS ALLOCATE, THEY DO NOT JUST READ `FRE`**: a rising `FRE(0)` is
      an arithmetic change, not proof the memory works. `d.big` (`DIM C%(9000)`,
      18000 B) does not fit the old 14767 and does fit the new 22959, so **the
      row IS the reclaim**; `d.big0` reads the far end back. 0 DIFF on 5 rows,
      and **`d.huge` still ERR 7 on both — the ceiling still EXISTS**, which a
      change that removed the bound entirely would have passed.

- [ ] 🙋 **THE LAST FIELD ROW (`e.val`) NEEDS DESCRIPTOR-BASED BINDING, AND IT IS
      THE ROW WHERE THE REFERENCE IS WORSE.** Filed 2026-09-01 after D-FLDCLOSE
      shipped (`CLOSE` matches the reference on 8 of 9 rows).
      After `CLOSE` + reopen + `FIELD#1,10 AS C$` + `LSET C$="ZZZZZZZZZZ"`:
      CF-3300 `A$` = **`ZZZZZZZZZZ`** (another channel's data, silently),
      zerobas `A$` = `<nothing>`.
      🎯 **STRUCTURAL, NOT A MISSING GUARD.** zerobas resolves a fielded variable
      through `FLD_TAB`; the reference stores a pointer in the variable. Matching
      it means changing how `FIELD` binds — and keeping `fld_clear_chan` on the
      FIELD path, which is what stops 16 slots filling.
      ⚠️ **SO THE CHARTER AND THE SAFER ANSWER POINT OPPOSITE WAYS HERE**, which
      is exactly the shape of the `ZB`-prompt and disk-banner calls: faithful vs
      sane, decided case by case. Today's answer was "faithful" and it improved
      BOTH; this row is the one where it would not.
      🙋 NEEDS-JOOST — the measuring is done (9 rows, both machines, mechanism
      identified); what is left is whether to reproduce a silent aliasing bug.
- [x] 🟢 **THE REFERENCE PRINTS A DISK-ROM BANNER LINE AND ZEROBAS PRINTS NONE.**
      Noticed 2026-09-01 by Joost while reviewing the main banner.
      | | reference (CF-3300) | zerobas |
      |---|---|---|
      | main BASIC | `MSX BASIC version 1.0` / `Copyright 1983 by Microsoft` / `23430 Bytes free` | `zerobas version 0.1` / `clean-room MSX1 BASIC` |
      | disk ROM | `Disk BASIC version 1.0` | *(nothing)* |
      📏 **MEASURED: `disk/` HAS NO BANNER AT ALL.** Its only string is the `"AB"`
      ROM signature at `$4000` (`disk/init.asm:16`). Every other banner reference
      in `disk/` is DOS-mode: emitting the MSXDOS.SYS sign-on, and — the one
      worth knowing — **CLEARING** the BASIC banner on DOS handoff
      (`disk/runtime.asm:569`, "blank BASIC banner + home cursor").
      💰 **SPACE IS NOT THE OBSTACLE HERE, WHICH IS UNUSUAL FOR THIS PROJECT**:
      `build/disk.rom` carries a **3464 B** run of `$00` at `$281D`, so a line
      costs nothing scarce. That makes this purely an identity question.
      ⚠️ **AND IT IS THE SAME QUESTION AS THE `ZB` PROMPT**, which was decided on
      2026-09-01 to STAY as `ZB` — the marker that this is not the reference. A
      disk-ROM banner would pull the boot screen toward the reference in the same
      breath that the prompt deliberately does not. Decide them together or not
      at all.
      🙋 NEEDS-JOOST — what the boot screen SAYS is a charter/identity call, not
      a measurement.
      ✅ **DONE 2026-09-01 (Joost: `zerobas Disk BASIC`, no version number).**
      The boot screen now reads `zerobas version 0.1` / `clean-room MSX1 BASIC` /
      `zerobas Disk BASIC`, in the reference's order.
      🔴 **I PRICED IT "FREE" AND WAS WRONG TWICE.** The disk ROM's APPENDABLE
      TAIL IS 2 B (image ends `$7FFD`); the 3464 B run I quoted is INTERIOR pad,
      and I gave its address as a file offset (`$281D`) rather than `$681D`.
      Three attempts to add ~25 B to `init` drove a `ds $XXXX - $` count NEGATIVE
      and ran pasmo past 64 KB — loudly, because `pad_rom.py` refuses to pad an
      empty image.
      🔴 **AND THE OBVIOUS IMPLEMENTATION HANGS THE MACHINE.** Printing from the
      disk INIT is one line — but `init_ext_roms` is what DISCOVERS the sub-ROM
      slot, `show_title` is a SUB-ROM tenant, and `show_title`'s `INITXT` clears
      the screen. So the scan must run first (or `show_title` CALSLTs a slot
      nothing was recorded in — **measured: never reaches BASIC**), and anything
      the scan printed is then wiped.
      ➡️ **Shipped shape:** body + string in the disk ROM's largest pad
      (`kernel.asm:2046`), exposed at the unused pinned entry **`$4022`**, and
      CALSLTed from `interp.asm` AFTER `show_title`, gated on `DISKSLOT_OK`.
      💰 **Page 1 355 → 331 B (−24 B)** — the text is free in the disk ROM, the
      CALSLT machinery is not, and it lives in the scarce region.
      📏 **AND THE HOLES ARE DOCUMENTED NOW** (Joost's call):
      [`docs/disk-rom-layout.md`](docs/disk-rom-layout.md) + **`make diskmap`**,
      which reads the BUILT ROM so no figure can rot. **9328 B of 16384 (56.9%)
      sits in pads**; the tail that you must not spend is printed beside them.

- [ ] 🐌 **THE BATTERY IS NOW 846 s AND EACH EMULATOR UNIT PAYS ITS OWN BOOT —
      COLLAPSE SUITES THAT SHARE A MACHINE INTO ONE RUN.** Joost's suggestion,
      filed 2026-09-01 with the number that motivates it: D-COLLECTALL took the
      battery from **49 units / 450 s to 92 units / 846 s**. Nothing is wasted —
      every added unit measures something real and 92/92 are green — but the
      marginal cost is dominated by **per-unit openMSX boots**, not by rows.
      📏 **64 EMULATOR UNITS.** Individual probes already batch their cases
      (`omsx_repl.run_cases(..., batch=True)`), so the win left is one level up:
      several SUITES that want the same machine and the same reset sharing a
      single boot.
      ⚠️ **THE OBSTACLE IS STATE, AND IT IS THE REASON THIS IS NOT FREE.** Some
      suites boot per case ON PURPOSE — D-EDITVERB's printer-log deltas and
      D-LPTVERB's accumulated `LPOS` state both say so in their headers — and
      D-EDITVERB records the exact failure mode: a shared log where one case's
      capture becomes a whole log and every later delta is silently wrong "in
      the direction of a plausible-looking divergence".
      ➡️ So the shape is a per-suite OPT-IN, not a blanket change: a suite
      declares "machine M, reset R, no cross-case state" and the runner packs
      those together. 🔴 **And it needs the control D-EDITVERB's note implies —
      a batched suite must produce the SAME rows as it did unbatched, checked
      once per suite when it opts in.**
      🤖 AUTONOMOUS — a gate settles it, and the before/after row sets are the
      oracle.
      🔴 **RE-MEASURED 2026-09-01 (D-BATCH1) AND THE PREMISE ABOVE IS WRONG.**
      "The marginal cost is per-unit openMSX boots, so share a boot across
      SUITES" — no. `run_cases` already defaults to `batch=True`, **one boot for
      a whole matrix**, so a batched suite boots ONCE and sharing across suites
      would save ~0.5 s each.
      🎯 **THE COST IS BOOT-PER-CASE WITHIN A SUITE.** `batch=False` — described
      in `run_cases`'s own docstring as "the historical default" — is passed by
      **35 of the 60 emulator probes**, and it is the battery's dominant cost.
      **30 of those 35 carry no reason within 25 lines of the call** (a crude
      scan: a candidate list, not a verdict).
      📏 **PROVED ON ONE: `strparen-acceptance` 35 s → 5 s (7x), 16/16 rows still
      matching their references**, verified by running the matrix BOTH ways and
      diffing every row (0/16 differ) before flipping it.
      🔴 **AND THE GENERIC CONTROL WAS BUILT AND WITHDRAWN — IT WAS UNSOUND.** A
      `$ZB_BATCH=0` switch at the `run_cases` chokepoint cannot reproduce the old
      behaviour, because **`reset` lives in different places in the two modes**:
      the probe prepends it per case for `batch=False`, the harness injects it
      for `batch=True`. Forcing the other mode from outside yields a THIRD
      behaviour (no reset, or two). Its first run said `rc 0 vs 2` and that was
      the instrument, not the suite.
      ➡️ **So the remaining work has a PREREQUISITE nobody had named**: make
      `run_cases` own `reset` in BOTH modes, and the both-ways diff becomes a
      one-command control for all 30 candidates. Until then each conversion needs
      its own hand-built comparison, which is what this one got.
      ✅ **PREREQUISITE DONE 2026-09-01 (D-BATCH2), AND THE CONTROL EXISTS:
      `python3 scratchpad/batchcheck.py <make-target>`.** `_run_cases_impl`'s
      boot-per-case branch passed `reset=()`; it now passes the caller's `reset`,
      so a mode forced from outside is FAITHFUL instead of a third behaviour.
      🔴 **THAT ONE-LINE CHANGE HAD A 69-SITE BLAST RADIUS, AND A PROBE CAUGHT
      IT IMMEDIATELY.** `banner-acceptance` went red on the first spot-check: its
      subject IS the untouched boot screen, and the now-injected default `CLS`
      wiped the header it reads — *"the marker printed but 2 header line(s) are
      GONE ... no other gate in this tree would have noticed"*. The resets are
      all idempotent (`NEW`/`CLS`/`SCREEN 0`), but idempotent is not the same as
      HARMLESS when the screen is the subject.
      ➡️ Fixed by making the implicit explicit: **69 sites in 33 probes** now
      pass `reset=()` where they were relying on the mode's default. Behaviour-
      preserving by construction, and it means every probe now DECLARES its reset
      instead of inheriting one that differed by mode. 92/92 green after the
      sweep.
      🟢 **AND THE CONTROL DISCRIMINATES, WHICH IS THE ONLY THING THAT MAKES IT
      WORTH HAVING**: `runtail` 22/22 rows identical → CONVERTIBLE; `lptverb`
      rows DIFFER, and the difference is the exact accumulation D-EDITVERB
      predicted — the batched printer log reads
      `CTL\r\nX\r\n 5 \r\n-5 \r\nAB\r\nA B\r\n` where boot-per-case
      reads `A B\r\n`.
      🔴 **BOTH MODES REPORTED `ok` AND rc=0.** The suite PASSES while measuring
      a running total, so exit status could never have caught it — only the row
      diff does. That is what "silently wrong in the direction of a plausible-
      looking divergence" looks like when you finally point an instrument at it.
      🔴 **AND THE CONTROL'S FIRST SWEEP WAS A FALSE POSITIVE — GUARDED
      2026-09-01 (D-BATCH3).** It reported `screenerr`, `tmfp`, `stmtpend` and
      `penderr` all **CONVERTIBLE**, having compared two IDENTICAL runs: those
      probes loop in PYTHON and call `run_cases` once per case, so forcing
      `batch=True` on a ONE-CASE matrix batches nothing. Both modes booted per
      case, every row matched, and **the only tell was a 1.0x "speedup"**
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ➡️ `run_cases` now records the matrix width (`$ZB_BATCH_STAT`) and
      `batchcheck` **REFUSES with `NOT TESTED`** when the widest matrix a suite
      ever handed it is < 2, naming the remedy. Verified in all three
      directions: `strparen` CONVERTIBLE (4.3x, 16-case matrix), `lptverb`
      ROW(S) DIFFER (16-case, real state), `tmfp` NOT TESTED (1-case).
      📏 **SO THE REMAINING WORK IS BIGGER THAN "RUN A COMMAND 29 TIMES"**, and
      that is the useful part of this pass: **25 of the 35 boot-per-case probes
      call `run_cases` inside a for-loop** and need a `run_side` restructure
      before the control can say anything at all; only **10** hand it a
      multi-case list, and 3 of those are now judged (strparen converted,
      lptverb refused, runtail cleared).
      ✅ **THE TESTABLE SET IS NOW FULLY JUDGED (2026-09-01, D-BATCH4).** All
      ten multi-case candidates run through the control:
      | verdict | suites |
      |---|---|
      | **CONVERTIBLE → converted** | `strparen` (4.3x), `dskmsg` (4.6x), `msgexact` (2.2x), `runtail` (1.6x) |
      | **must stay boot-per-case, reason now IN THE SOURCE** | `lptverb`, `castail`, `editverb` |
      | **NOT TESTED (matrix=1, needs a restructure first)** | `banner`, `cassave` |
      | not run (no battery target) | `bload_fcb` |
      📏 Measured effect: `dskmsg` 11 s → 3 s, `runtail` 10 s → 2 s,
      `msgexact` → 2 s.
      🔴 **AND THE STATIC HEURISTIC OVER-COUNTED**: it called `banner` and
      `cassave` testable; the control's matrix-width guard says they are
      matrix=1. The guard is the authority, the grep was an estimate — worth
      remembering before trusting the "25 need restructuring" figure, which comes
      from the SAME grep.
      🟢 **EVERY REFUSAL NOW SAYS WHY, IN THE SOURCE**, which is what the item
      asked for: `lptverb`'s accumulating printer log (with the measured
      before/after strings), `castail`'s rc 2-vs-0, and `editverb`'s
      header-warning now backed by a measurement.
      🔴 **AND THE FOUR SLOWEST FOR-LOOP PROBES SHARE ONE BLOCKER, WHICH TURNED
      OUT TO BE A DEFECT (2026-09-01, D-BATCH5).** `screenerr`, `stmtpend`,
      `penderr` and `tmfp` all carry the same comment: *"A FRESH `so` PER CALL
      ... every boot indexes from 0, so one dict reused across the loop would
      hold a single entry and the tally would silently under-count."* **Seven
      probes use `probe_signal`; all seven are boot-per-case; none is batched.**
      🎯 **THE COMMENT IS A STATEMENT ABOUT `batch=False`, AND BATCHING FIXES
      WHAT IT FEARS.** `settle_out` keys by the case index the emulator emits, so
      a batched matrix of N cases writes N DISTINCT keys into ONE dict. The
      per-call dict was a boot-per-case workaround, not a barrier.
      📏 **`tmfp` CONVERTED AND MEASURED: 61.7 s → 15.1 s (4.1x), 58 of 59 rows
      IDENTICAL.** The one differing row is the instrument's own tally —
      **`capture-on-signal: 123 on signal` batched vs `3` boot-per-case.** 41
      signal cases x 3 sides = 123, so the batched figure is the arithmetically
      consistent one and **boot-per-case has been under-counting 40x**: exactly
      the failure the comment warned a shared dict would cause, happening all
      along in the mode it thought was safe.
      ⚠️ The tally is report-only, so no verdict was ever wrong — but it is the
      detector that reports FALLBACKS, so **40 of every 41 fallbacks were
      invisible**. The other six `probe_signal` probes are presumed to carry the
      same under-count; it is not measured for them yet.
      ⚠️ The conversion splits the matrix by `kind == "t"`, because
      `probe_signal.kwargs` is a whole-CALL setting and a mixed matrix would
      apply sentinel capture to the non-signal cases too. The disk is now one per
      GROUP, not per case — a real reduction in isolation, which is why this only
      lands with the control green.
      📏 **TWO MORE JUDGED 2026-09-02 (D-BATCH6), AND THEY SPLIT — WHICH IS THE
      POINT.** `screenerr` and `penderr` have **BYTE-IDENTICAL** `run_side`
      bodies (modulo the disk name), so the same transformation applied to both:
      | suite | verdict | |
      |---|---|---|
      | `penderr` | **CONVERTED** | 3.7x; the ONLY differing row is the tally, 165 vs 3 |
      | `screenerr` | **REVERTED** | a REAL leak: `a.sprskip` reads ` 99 , 2 ` batched, ` 0 , 2 ` fresh |
      🔴 **AND THE LEAKING ROW STILL SAYS `ok` IN BOTH MODES**, because all three
      sides agree on the polluted value too. Cross-side agreement cannot see it;
      only the both-ways diff can
      [[a-case-that-agrees-can-agree-for-the-wrong-reason]]. The file's own
      DENOMINATOR names sprite-size persistence as something it does NOT sweep —
      batching would have swept it accidentally and silently.
      🎯 **SAME SHAPE, DIFFERENT VERDICT: run the control on EACH ONE.** Two
      probes with identical bodies came out opposite ways, so an argument by
      analogy ("its twin converted, so this one will") would have been wrong half
      the time. `screenerr`'s reason is now in its own docstring.
      📏 **THE `probe_signal` FAMILY IS NOW SETTLED (2026-09-02, D-BATCH7).**
      | suite | verdict | |
      |---|---|---|
      | `tmfp` | CONVERTED | 4.1x (61.7 s → 15.1 s) |
      | `penderr` | CONVERTED | 3.7x (~170 s → 22 s) |
      | `stmtpend` | CONVERTED | 3.8x (73.5 s → 19.5 s); per-case `NO_CLS_RESET` variation preserved |
      | `screenerr` | REVERTED | `a.sprskip` leaks: ` 99 , 2 ` vs ` 0 , 2 ` |
      | **`lineerr`** | **REVERTED** | **30 of 220 rows leak** |
      | `graphics` | not attempted | 44 separate `run_cases` sites, a different job |
      | `deffn` | not attempted | imported by a dozen probes; wide blast radius |
      🔴 **`lineerr` WAS THE BIGGEST PRIZE IN THE BATTERY (~210 boots, 3.2x on
      offer) AND IT IS NOT AVAILABLE.** Its `d.*` rows PEEK system variables
      (`GRPACX`/`GRPACY`, `GXPOS`/`GYPOS`) that survive a case, so a shared boot
      reads the PREVIOUS case's graphics accumulator: `d.defd40k` reads
      ` 0 , 7 , 7236 ` batched against ` 0 , 7 , 40004 ` fresh.
      ⚠️ **AND ALL 30 STILL SAY `ok` IN BOTH MODES** — all three sides agree on
      the polluted value too. Four suites in this family converted and two leak,
      which is why each gets the control rather than an argument from its
      siblings.
      ✅ **THREE MORE CONVERTED 2026-09-02 (D-BATCH8), ALL CLEAN — 0 DIFFERING
      ROWS EACH**: `width` 3.5x (134.1 s → 37.9 s, 94-case matrix, 103 rows),
      `locarg` 3.9x, `forvar` 3.2x. These have no `probe_signal` and no per-case
      `run_gap`, so the transformation is the plain one.
      🟢 **`width` IS THE INTERESTING PASS**: `WIDTH n` is exactly the kind of
      state that does not survive a shared boot, and it converts cleanly because
      each case's own `cfg["reset"]` is prepended to its lines and re-establishes
      the screen before it runs. Being stateful is not the same as leaking —
      which is why the control decides and not a reading of the subject.
      ✅ **THREE MORE 2026-09-02 (D-BATCH9), 0 DIFFERING ROWS EACH**: `nxary`
      4.6x, `nxlist` 3.3x, `readvar` 2.3x. **13 converted, 6 refused.**
      🔴 **AND "THE TRANSFORMATION IS NOW MECHANICAL" WAS WRONG.** Normalised
      against a converted template, **none of the ten remaining candidates is
      byte-identical** — a blind bulk transform would have been applied to
      shapes it does not fit. The differences turn out to be shallow (the disk is
      hoisted and shared rather than copied per case; the `CASES` tuple has 2 or
      3 fields), so `nxary`/`nxlist`/`readvar` are the `forvar` shape EXACTLY and
      converted from that template — but that had to be checked, not assumed.
      ➡️ Remaining, each needing its own read: `arylv` (per-case `responses`),
      `fldary`, `fldwidth`, `inputary`, `lrvar`, `lvfix`, `onerr0`, `cassave`,
      `namspc`/`tgtspc` (2 `run_cases` sites each), `sysvarsweep` (85-line
      `run_side`), `banner` (no single `run_side` at all), plus `graphics` (44
      sites) and `deffn` (shared harness).

- [x] 🟢 **`make gates` COLLECTS 22 OF THE 68 `*-acceptance` TARGETS, NOTHING
      RECORDED WHY, AND THREE OF THE REST ARE RED.** Found and gated 2026-09-01
      (D-UNCOLLECTED, [`docs/spec-uncollected.md`](docs/spec-uncollected.md);
      per-suite rc reproduced by running each excluded target serially with
      `ZEROBAS_REFCACHE=0`; the roster is `tools/battery-exclusions.txt`).
      🎯 **THE GAP IS BETWEEN "REACHABLE" AND "COLLECTED".** `probe-reach-check`
      asks whether SOME make target runs a probe; it does not ask whether the
      BATTERY does. **All 46 uncollected suites pass probe-reach.** There is no
      aggregate `acceptance` target, and exactly one exclusion in the whole tree
      carried a written reason.
      ➡️ **GATED: `make battery-membership-check`** (static tier; battery 26 → 27
      static, 50 total). An acceptance target must be in the battery or in
      `tools/battery-exclusions.txt` WITH A REASON — the `EXPECT_ARG` /
      `REGENERATED` discipline. **38 of the 46 entries read `UNREVIEWED`**, each
      carrying its measured colour: the debt is now visible and counted rather
      than invisible, and inventing rationales for 38 undocumented decisions
      would have been worse than naming the gap.
      🔴 **S4 IS NOT HYPOTHETICAL** — this slice's own first measurement parsed
      **zero** gate names (the lists are triple-quoted strings, not a list
      literal) and produced a tidy table calling all 86 probes uncollected. The
      floors exist because the instrument failed that way inside this slice
      [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

- [x] 🟢 **`X=TAB(5)` OUTSIDE A `PRINT` GIVES `Missing operand` WHERE BOTH
      REFERENCES SAY `Syntax error` — AND `cursor-acceptance`'s KNOWN-RED
      EXEMPTION NAMES SOMETHING ELSE.** Found 2026-09-01 by D-UNCOLLECTED,
      which ran the suite the battery does not collect
      ([`docs/spec-uncollected.md`](docs/spec-uncollected.md)).
      Three rows fail: `X=99:X=TAB(5)`, `X=99:X=SPC(5)`, `IF TAB(5)=0 THEN Z=1`.
      `TAB(`/`SPC(` are PRINT-only on the reference; anywhere else is a Syntax
      error.
      🔴 **AND THE SUITE'S OWN EXEMPTION IS STALE**: its `KNOWN_RED` set of 8
      rows is banner-documented as *"a mid-statement error does not abort the
      statement"* (D-CUR-3), and **all 8 now AGREE** — so the exemption
      suppresses nothing while the suite is red for a reason it never names.
      Whatever fixed D-CUR-3 did not update the exemption
      [[a-fix-falsifies-the-justification-beside-it]].
      ✅ **FIXED 2026-09-01 (D-MISSOPBOUND,
      [`docs/spec-basic-missopbound.md`](docs/spec-basic-missopbound.md); rows in
      `scratchpad/missopbound_probe.py`) — 11 DIFF of 18 → 0, page 1 358 → 349 B
      (−9 B).**
      🔴 **THE THREE ROWS WERE A TENTH OF THE DEFECT.** zerobas answered ERR 24
      for **nine token classes** the references call ERR 2: a bare operator
      (`X=*5`), `TAB(`/`SPC(`, and `THEN TO STEP GOTO PRINT INPUT USING`.
      📏 **THE RULE IS A BOUNDARY, NOT A SPECIAL CASE**: a factor slot ended by
      END OF STATEMENT (EOL or `':'`) is `Missing operand`; anything actually
      PRESENT is `Syntax error`. Two rules fit every row either side had, so the
      probe was built to separate them
      [[two-rules-that-coincide-on-every-row-you-have]].
      🟢 **`X=ELSE` IS THE ROW THAT PROVES IT AND LOOKS LIKE A COUNTER-EXAMPLE** —
      ERR 24 on all three, because MSX tokenises `ELSE` as `:ELSE` so the slot
      really sees a colon. An AGREEING row that separates two rules is worth more
      than a diverging one that does not.
      🔴 **AND `basic/print.asm`'s COMMENT WAS FALSIFIED FIRST** — it claimed
      siting TAB(/SPC( outside `ev_f` "is what makes `X=TAB(5)` a SYNTAX error
      (MEASURED)". The design is right, the consequence was wrong, and the claim
      carried the word MEASURED
      [[a-fix-falsifies-the-justification-beside-it]].
      ⚠️ The deferred code is **FPERR 4**, not 2: `fperr_to_err` is a dense index,
      not a BASIC error number
      [[a-derived-constant-falsified-from-another-file]]. Regression checks all
      green and all needed: `missing-acceptance` (D-MISSOP's 16 slots),
      `lineerr-acceptance` (which D-MISSOP's first draft broke), `cursor`.
      ✅ **AND THE STALE EXEMPTION IS RETIRED.** All 8 `KNOWN_RED` rows agree, so
      it suppressed nothing while the suite was red for a reason its banner never
      named. 🔴 **An exemption that no longer fires is not inert — it is a row set
      silently ungated.** Emptied; 67 rows green. **`cursor-acceptance` now JOINS
      the battery** (51 units, 23 of 68 acceptance targets collected).

- [x] 🟢 **`namspc-acceptance` REFUSES: A POSITIVE CONTROL FAILS ON THE
      REFERENCE.** Found 2026-09-01 by D-UNCOLLECTED. `f.filesbare` expects
      `6 entries + OK` from the CF-3300 and does not get it, so the probe
      correctly reports *"A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing
      was measured"* and exits 2.
      🎯 **THE D-FILESROT CLASS, AND THIS SESSION ALREADY REPAIRED ONE**: a
      frozen FILES expectation measured against a disk whose contents have since
      changed. The repair is prescribed — re-measure the constant on the current
      fixture, do not edit it to taste.
      ⚠️ The instrument is behaving CORRECTLY here; a suite that refuses is the
      good outcome. What is wrong is that **nothing collected the refusal**.
      ✅ **CLOSED 2026-09-01 (D-FIXTUREPOLL,
      [`docs/spec-fixturepoll.md`](docs/spec-fixturepoll.md)) — AND THE
      PRESCRIBED REPAIR WAS THE WRONG ONE.** The constant was RIGHT; the FIXTURE
      was wrong. `disk/test720.dsk` is **untracked and generated** (`e7c5eab`
      removed it from git to kill "the openMSX write-back hazard on a committed
      image"), and a probe had written `TS.DAT` into the local copy — attr `$00`
      where every generated file is `$20`. A fresh generation has FIVE files.
      🔴 **`make test-dsk` CANNOT CATCH IT**: make is timestamp-driven and a
      polluted image is NEWER than its generator, so the rule is satisfied and
      nothing rebuilds. The file has to be deleted first.
      🔴 **AND D-FILESROT (EARLIER THE SAME DAY) FROZE THE POLLUTION.** It did
      exactly what its filing prescribed — re-measure the CF-3300, never edit the
      constant into agreement — but it booted against the POLLUTED disk and
      froze `TS      .DAT` into two constants. 🎯 **RE-MEASURING IS NOT ENOUGH IF
      THE THING MEASURED IS CONTAMINATED.** Both reverted and re-verified on a
      fresh image; D-FILESROT's measuring METHOD is kept in the comment.
      ➡️ **GATED: `make fixture-integrity-check`** — regenerates each generated
      image hermetically and compares the DIRECTORY (name + attr), not the whole
      image. 4 arms; the S3 plant is the exact wild pollution.
      **`namspc-acceptance` now JOINS the battery.**

- [x] 🟢 **`time-acceptance`: `is_jiffy` READS 12289, WANT 12288.** Found
      2026-09-01 by D-UNCOLLECTED. One row, off by one.
      ⚠️ **RUN IT TWICE BEFORE BELIEVING IT IS A DEFECT** — a jiffy counter is
      the one quantity in this tree where an off-by-one can be genuine sampling
      jitter rather than a divergence, and a frozen `want=` for a free-running
      counter is a suspect construction in itself. Establish which it is BEFORE
      changing anything.
      ✅ **CLOSED 2026-09-01 (D-FIXTUREPOLL). RUNNING IT THRICE WAS RIGHT AND
      THE ANSWER WAS THE OPPOSITE OF THE WARNING**: not jitter — **deterministic
      on all eight phases, three runs** (ref 12288, zb 12289).
      🎯 The row POKEs JIFFY and reads TIME back, so it measures **how many
      interrupts fit between the POKE and the read** — interpreter speed.
      `TIME=0:PRINT TIME` reads **1 / 2 / 1** on VG-8020 / CF-3300 / zerobas, and
      `PEEK(&HFC9F)`=`$30` on all three, so TIME and JIFFY are the same cell.
      ⚠️ **THE FILE HAD ALREADY DRAWN THE LINE**: `run_side` excludes the clock
      group from the equality differential because "the tick rate belongs to the
      host BIOS/VDP". `is_jiffy` is that same kind of quantity in the wrong
      group — pinned at the VG-8020's value it asserted that zerobas interprets
      at the VG-8020's SPEED. Now an inclusive window `12288..12304`.
      🔴 And the module docstring exempts "every row but `is_jiffy`" from the
      tick race; it is subject to the same race, its window is just long enough
      to be deterministic [[a-justification-parenthesis-is-an-unrun-claim]].
      **`time-acceptance` now JOINS the battery.**

- [x] 🟢 **A RECURRING "FLAKE" WAS A REAL RACE, AND THE MUTATOR LIST NAMED THREE
      UNITS THAT MUTATE NOTHING WHILE MISSING THE ONE THAT DOES.** Found and
      fixed 2026-09-01 (D-SELFMUT, [`docs/spec-selfmut.md`](docs/spec-selfmut.md);
      instrument `scratchpad/stale_sampler.py`).
      `float-acceptance` scored rc=2 and passed on the serial retry in BOTH of
      the day's full batteries (`math-acceptance` earlier). It was not a flake:
      the probe never booted — preflight refused because **both repack ROMs had
      gone stale mid-battery**, and the retry rebuilt them on its way past.
      🔬 **GUESSING REFUTED TWO HYPOTHESES** (the serial mutator phase; a gate
      re-linking via `make basic-reloc`). What settled it was sampling `make -q`
      on both ROMs once a second and printing on every state change with the
      mtime that moved: stale at **t=53.5 s — inside the POOL — and never
      recovering**.
      📏 **THEN ONE GATE AT A TIME, FROM A FRESH TREE:** `switch-build-check`,
      `diskdep-check`, `wall-literal-check` mutate **nothing**;
      `selftest-check` mutates `basic/sysvars.inc`, the `Makefile` and
      `probes/basic/basic_probe_clear.py` and leaves both ROMs stale. The first
      three are exactly `MUTATORS`. **The list was inverted.**
      🎯 **THE GUARD WAS AIMED AT THE TOOLS, NOT AT THE CALLERS THAT ARM THEM** —
      planting lives behind `--selftest` and those three recipes never pass it;
      only `check_selftests.py` does. Exit-safe (D-KNIFEGUARD), never
      concurrency-safe. Ask not *can this tool mutate* but *does THIS INVOCATION
      mutate* [[exit-safe-is-not-concurrency-safe]].
      ➡️ Fixed three ways: `selftest-check` joins `MUTATORS`; a **rebuild after
      the mutator phase** (a restored plant is not a restored tree — the bytes go
      back, the MTIME does not); and the battery now **reports any tracked file
      it leaves dirty**, exempting only the six paths D-GENFRESH enumerated as
      legitimately regenerated.
      ✅ Verified on a forced-full battery: **49/49 green with NO retry line and
      NO recovered flakes**, and the sampler shows the pool running **0 s** with
      stale ROMs where it previously ran ~390 s.
      ⚠️ **THE COST ESTIMATE WAS 10x THE MEASUREMENT, IN THE DIRECTION THAT
      ARGUES AGAINST FIXING IT**: moving a 44 s unit out of the pool cost **4 s**
      (449 s vs 445 s) — the wall clock is bound by the long acceptance shards,
      not by total work.
      ➡️ **The TORN READ half is NOT fixed and is filed separately below** — a
      residual written up inside a `- [x]` is exactly what this section exists to
      prevent, so it gets its own line rather than a paragraph in this one.

- [x] 🟢 **NOTHING STOPS THE NEXT PLANTING `--selftest` FROM LANDING IN A POOL
      UNIT — THE TORN READ HAS NO WITNESS.** Filed 2026-09-01 by D-SELFMUT
      ([`docs/spec-selfmut.md`](docs/spec-selfmut.md)), which fixed the other
      half of the same race.
      While a plant is live, any parallel unit that assembles
      `basic/sysvars.inc` or reads the `Makefile` sees **deliberately corrupted
      content**. Serialising `selftest-check` closes the window *today*, by
      hand, on a list a human maintains.
      🔴 **AND ONLY THE OTHER HALF IS OBSERVABLE.** The stale-ROM half announces
      itself because a preflight refuses and scores rc=2. A torn read has no such
      witness: it surfaces as an inexplicable red in an unrelated unit, or as a
      build that silently used corrupted bytes — the `unit-test` case
      `tools/run_gates.py`'s own header records, where the retry passed and the
      race was called a flake.
      ⚠️ **THE LIST WAS ALREADY WRONG ONCE, IN BOTH DIRECTIONS AT THE SAME
      TIME** (three inert units serialised, the one live one in the pool), which
      is the argument against maintaining it by hand.
      ➡️ Candidate: a gate that runs each unit and asserts no tracked file is
      written outside `MUTATORS` — the battery-wide version of the
      one-gate-at-a-time measurement D-SELFMUT did by hand. Cost is the problem:
      the honest form re-runs the battery. A cheap first cut is to snapshot
      tracked-file mtimes around each POOL unit inside `run_gates.py`, which
      needs no extra runs at all.
      ✅ **CLOSED 2026-09-01 (D-POOLWRITE,
      [`docs/spec-poolwrite.md`](docs/spec-poolwrite.md))** — the cheap cut was
      the right one, and it turned out to **ATTRIBUTE, not merely detect**.
      🎯 **THE MTIME IS A TIMESTAMP**: the file records WHEN it was written and
      the runner already tracks each unit's start/end, so the candidates are the
      units whose window contains it. Two `os.stat` passes over the tracked tree,
      no extra runs — the battery already held the information and never looked.
      ⚠️ Under parallelism that is a **candidate set, not a culprit** (up to `J`
      names) and the report says so; a restore that also restores the mtime stays
      invisible, which is why the snapshot carries **size as well as mtime**.
      🔬 **FALSIFIED BY PUTTING THE REAL DEFECT BACK** — a one-line revert of
      D-SELFMUT, not a synthetic plant: the battery FAILS, names all three files,
      and attributes every one to `selftest-check`; the control is `26/26` green.
      The attribution logic is separately armed against synthetic windows,
      including the case that matters — **a unit that finished before the write
      is excluded**, so the set narrows instead of listing everything that ran.
      ➡️ A pool write **sets the exit status**; an advisory nobody collects is the
      shape `check_selftests.py` exists to end. Exemptions go in `REGENERATED`
      with their reason — and that list is not hand-kept either, it is the
      six-path class D-GENFRESH enumerated from make's own database.

- [x] 🟢 **A GENERATED FILE THAT IS ALSO TRACKED CAN GO STALE IN A COMMIT, AND
      THE GATE FOR THAT COVERED 2 OF THE 6.** Found and fixed 2026-09-01
      (D-GENFRESH, [`docs/spec-genfresh.md`](docs/spec-genfresh.md)).
      `sub/basic-resident-abi.inc` — the sub-ROM's table of MAIN-ROM addresses —
      had been **stale in HEAD across 11 main-ROM commits**. Surfaced by
      accident: a probe's preflight refused on a stale ROM, and
      `make clean && make repack-machine` reproduced the dirty working copy
      **byte for byte**, which says the tree was right and HEAD was wrong.
      🎯 **A DEFECT WITH NO FAILING BEHAVIOUR IS NOT A SMALL ONE, IT IS AN
      UNGATED ONE.** Its Makefile rule regenerates it on every build, so it
      self-heals before anything reads it wrong; the only symptoms are a tree
      that is dirty the moment you build it (the `git status` noise that makes
      the banned `git add -A` tempting) and a committed file naming wrong
      addresses to anyone who READS rather than builds.
      ➡️ **THE FIX IS THE DENOMINATOR, NOT THE FILE.** The class is *a tracked
      path that is also a Makefile target*, asked of make's own database: **six
      members**, of which `check_patch_freshness.py` covered two (the main and
      tape patch pairs). Its header already had the instinct — *"TWO shipped
      patch deliverables, not one"* — it just never asked whether two was the
      total. Both uncovered members are entered; **6 of 6**.
      🔬 **NO PLANT WAS NEEDED — the stale file WAS the red state**, and fixing
      the denominator bought a control set the size of the class: five green in
      the same invocation that reddens the sixth.
      ⚠️ Two traps the generalisation had to dodge: `make_target` is the
      STALENESS question, not the shipped file (the include's own prerequisites
      are a build product and a script, so a dirty check on them is vacuous —
      the 61 tracked sources of `build/basic-reloc.sym` are what get asked); and
      the coeffs regeneration goes through `--emit` under `cwd=<tmp>`, the branch
      the Makefile uses, not the dry-run branch that would have left it
      unmeasured. Costs ~5.6 s, almost all of it the minimax fitting.

- [x] ✅ **A PAGE-ALIGNMENT ASSERT WITH NO ENFORCEMENT IS A LANDMINE FOR THE
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
      ✅ **SWEPT AND GATED 2026-09-05 — `make build-assert-check`
      (`tools/check_build_asserts.py`), collected in the battery.** It walks
      `basic/`, `sub/` and `disk/` and finds **22 asserts: 18 BUDGET, 4
      ALIGNMENT.**
      🎯 **The rule is the CONJUNCTION, and that is what the sweep established**:
      alignment-shaped **and** an operand that can move. Three of the four are
      over symbols that CANNOT — `USRTAB` is the published MSX `$F39A`,
      `SUBROM_ENTRY_BASE_P1` is `equ $4010`, `FN_BASE` is an `equ` chain
      *separately pinned* by its own `IF FN_BASE != $EA92`. **An assert over a
      pinned literal is a PROOF, not a landmine**: the only way to trip it is to
      edit the literal, which is deliberate and self-explanatory. So the entry's
      own worry about `basic/usr.asm` is answered — it is safe, and for a reason
      it can state.
      The one over a **code label** is `edt_codes`, i.e. exactly the one that
      fired, and it is enforced.
      🔴 **MY OWN DETECTOR MISSED ONE ON ITS FIRST RUN.** Matching `high`/`low`
      classified `basic/expr.asm:1656` as a budget assert, because it spells the
      same page-crossing question `(X >> 8) - (Y >> 8)`. **The shape is the
      question, not the operator** — `>> 8` and `& $FF00` ask it too. Widened,
      and the count went 3 → 4.
      ⚠️ **Enforcement is DETECTED IN THE SOURCE, not acknowledged in a list.**
      The check looks for the `IF (low $) > n / ds` pad ahead of the label, so
      deleting the pad turns the row red by itself — an allowlist entry would
      have recorded the fix and then gone stale the day someone removed it,
      which is the exact failure mode this check exists to prevent. Armed: with
      the pad deleted the check goes rc 1 and names the landmine; restored, rc 0;
      `sub/deftype.asm` byte-identical after.
      ⚠️ SHAPE-LEVEL ONLY, and it says so: it cannot tell whether a pad is still
      BIG ENOUGH — the assert itself answers that, at build time.
      🔴 **AND ADDING THIS GATE EXPOSED A HOLE IN THE BATTERY ITSELF, FIXED HERE.**
      `build-assert-check` was added to the Makefile *and* to the `gates`
      variable, the full battery then ran **108/108 GREEN — and the new gate had
      not run at all.** The battery's real membership lives in
      `tools/run_gates.py`'s `STATIC`/`EMULATOR` lists, a **second list nothing
      cross-checked**; the only signal was grepping the log for the target's own
      name. 🎯 `battery-membership-check` could not have caught it by
      construction: its denominator was `*-acceptance` ONLY, and the static
      `-check` tier is precisely the one D-GATESKIP measured as catching the real
      reds — so the gate's scope inverted its own priority. Its denominator now
      covers `-check` too: **109 targets, 103 collected, 6 excused.** The single
      new gap it found was `citation-check`, excused with its reason (a
      standalone ALIAS — `check_citation_paths.py` already runs as a step of
      `basic-reloc`, deliberately, because a cadence in a comment is a habit and
      a habit is not a control). ⚠️ Its selftest caught my exclusions line being
      space-separated where the file is TAB-separated, which had silently made
      the entry not parse.
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
      ✅ **HALF DONE 2026-09-04 — `make ram-claim-check` IS A GATE** (107/107):
      a claim is DECLARED (`; FREE-RAM $A..$B`) and no `equ` name may resolve
      inside it. 🎯 **It found a defect ONE COMMIT OLD** — D-CTLPOOL's own
      `CTLLIM equ $E056` sat inside a neighbouring `$E056..$E080 is FREE` — plus
      a stale `$E220 is FREE` that `GFX_DJ` had retaken. Five spans declared and
      verified; 7 prose spans listed ADVISORY rather than dropped.
      🔴 **THE CAVEAT IS ENCODED AS A REFUSAL, NOT AS COVERAGE.** The check says
      out loud that it is NAME-LEVEL ONLY and cannot see a cell extending up into
      a claim from below (`TOKBUF`: 612 B delta, 36 B free). ⚠️ **THE EXTENT HALF
      IS STILL OPEN**: generalise `scratchpad/ramfree_probe.py` (fill the window,
      work the machine, read it back) from its one hardcoded window to the
      declared set. That is the only thing that can settle extent.
      ✅ **AND THE EXTENT HALF LANDED 2026-09-04 TOO — `make ramfree-acceptance`**
      (D-RAMFREE): fill every DECLARED span, run 9 subsystems hard, read back and
      count changes PER SPAN. All five spans survive every workout. 🎯 The spans
      are parsed by `check_ram_claims.py`'s OWN regex, so a span that is declared
      and name-checked but never extent-checked cannot exist. Two controls, both
      asserting: `ctl.poke` (one byte into EACH span, every counter must read 1)
      and `ctl.pool` (a deep GOSUB nest must move the pool while no declared span
      moves). ⇒ **THE ITEM IS CLOSED** — both halves gated, 108/108.
      🔬 It also caught its ancestor going stale: `scratchpad/ramfree_probe.py`'s
      `ctl.forstk` required a `FOR` workout to change `$EA3A`, and D-CTLPOOL moved
      control frames out of that array — the control reads 0 now, correctly RED.
      🔬 And the first cut of the checker PROSE-MATCHED and reported 7 violations
      of which most were its own misreading — a cell's own extent read as a
      claim, a layout table's `FREE` describing the named cell, a comment quoting
      a claim it had already corrected [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
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
- [x] ✅ **Three probe page-0 entry addresses stay HARDCODED** —
      `basic_probe_subrom_boot.py` (`$0040`), `basic_probe_subrom_inttest.py`
      (`$0049`), `basic_probe_graphics_floor.py` (`$0058`). All three ARE scored;
      deriving them from `sub/equates.inc` needs its own falsification because they
      inject raw bytes into a bare machine deliberately. Detail: line 2582.
      **DERIVED 2026-09-05 (D-P0ENTRY, `probes/lib/subrom_entry.py`).** Each
      probe's `ld ix,nnnn` operand bytes are now
      `le16(page0_entry("PING"|"INTTEST"|"GRAPHICS"))`, computed from
      `SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_<name>` in `sub/equates.inc` at
      import time. **Byte-identical to the old literals today** (checked by
      assembling each `STUB_BYTES` and comparing the operand), so this is a
      zero-behaviour change with a live derivation; all three gates PASS.
      🎯 **THE FALSIFICATION IS THE REFUSAL, not the arithmetic** — which is
      what the entry's "needs its own falsification" turns out to mean. A
      derivation that quietly returned 0 on a broken parse would inject
      `ld ix,$0000`, an RST vector, into a running machine, and the probe would
      then FAIL for a reason that reads like a ROM defect. So a missing symbol
      RAISES, and the module's `--selftest` plants four things and requires each
      to be seen: a MOVED base (the answer must move), a MISSING index (must
      refuse), a MISSING base (must refuse), and a **page-1-only index** (must
      refuse even though it is defined — `FORMAT` is 10 in one table and
      `READVAL` is 10 in the other, so a name that only lives in the page-1
      block is pointed at the wrong table silently unless the derivation reads
      the page-0 block alone).
      🟢 Auto-collected by `selftest-check` (its `TREES` includes `probes/lib`
      and it matches the literal `"--selftest"`): 29 scripts run, 0 failing.
      ⚠️ The selftest also carries the three historical literals as a CONTROL,
      not a pin: if `equates.inc` ever moves them, the derivation moves and that
      one line is the thing to update, deliberately.
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

- [x] ✅ **`GET`/`PUT`/`FIELD`/`INPUT$` on a `CAS:` channel (`FCH_MODES` 7/8) are
      INFERRED, not measured.** MEASURED 2026-09-05 (D-CASFCH,
      `scratchpad/casfch_probe.py`). **15 of 16 cells confirm the inference; ONE
      DOES NOT, and it is a real divergence.**
      🔴 **BOTH RECORDED BLOCKERS WERE STALE.** *"No harness on either side
      drives a tape and a disk at once"* was already false when written:
      `basic_probe_cas_verbs.py` runs on `C-BIOS_MSX1_EU_REPACK_DISK`, whose own
      `<CassettePort/>` sits beside the disk, and
      `basic_probe_cas_match_cf3300.py` boots the **stock CF-3300 with `-diska`
      AND `-cassetteplayer` together** — the exact combination the entry says
      nobody has. 🎯 **And it did not matter, because the OUTPUT half needs no
      tape at all**: `OPEN"CAS:T"FOR OUTPUT` succeeds with nothing in the drive,
      so the channel can be interrogated on a bare machine. The blocker described
      apparatus for a harder experiment than the question needs.
      *"There is no reading to falsify"* was true of the FILING, not of the
      world — **an inference predicts values, and predictions are falsifiable.**
      | | CF-3300 | zerobas | |
      |---|---|---|---|
      | `OPEN"CAS:T"FOR OUTPUT` (mode 7) | 0 | 0 | ✅ |
      | `FIELD#1` · `GET#1` · `PUT#1` · `INPUT$(1,#1)` | 5 · 58 · 58 · 55 | same | ✅ |
      | `OPEN"CAS:D"FOR INPUT` (mode 8) | 0 | 0 | ✅ |
      | `FIELD#3` · `GET#3` · `PUT#3` | 5 · 58 · 58 | same | ✅ |
      | **`A$=INPUT$(1,#3)`** | **0, and `A$`=`"H"`** | **ERR 55** | 🔴 **DIFF** |
      🔬 **The reference READS**, and the row proves it positively rather than by
      an absent error: the `$EA` tape's one line is `HELLO`, and `ASC(A$)` comes
      back **72**. zerobas raises 55 and never writes the byte slot. Filed as its
      own item below.
      🟢 **The `LPT:` control was re-measured on the same machines in the same
      run** — 0 / 5 / 58 / 55, per-verb, exactly as this entry predicted from the
      local evidence. 🔴 Its first run was INVALID and agreed anyway: it opened
      `AS#2` while `MAXFILES` defaulted to 1, so all four slots read 52 (*Bad file
      number*) on BOTH sides — a tidy agreeing column measuring "channel 2 does
      not exist" [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
      ⚠️ **THE ARMS ARE NOT INDEPENDENT.** In the full program the CF-3300 never
      reached the INPUT arm — its done-marker read `$FF`, which is exactly what
      the markers exist to distinguish from a measured value. Isolated
      (`--input-only`), the same machine completes at the same 40 s cap, so time
      is not the cause: running the OUTPUT arm first stops the INPUT arm finding
      its file. Stated as the reading; which of consume-vs-reposition does it is
      not measured.
      --- the original filing ---
      D-NOTOPEN2 swept modes 0–6 against the CF-3300 and
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

- [ ] 🔴 **`INPUT$` ON A `CAS:` CHANNEL OPENED FOR INPUT READS ON THE REFERENCE
      AND RAISES ERR 55 HERE.** Found 2026-09-05 by D-CASFCH while measuring the
      entry above; `scratchpad/casfch_probe.py --input-only` is the reading.
      `OPEN"CAS:D"FOR INPUT AS#3` then `A$=INPUT$(1,#3)`: the CF-3300 returns no
      error and `A$` is `"H"` — the first byte of the `$EA` tape's `HELLO`,
      asserted as `ASC(A$)=72`, so the row witnesses the READ and not merely the
      absence of an error. zerobas answers ERR 55.
      🎯 **THE SITE, READ RATHER THAN INFERRED.** ~~`basic/files.asm` sends 7/8
      down the *device* arm because both are `>= LPT_MODE`~~ — **that was my own
      first write-up and it is wrong**; I inferred it from the entry above instead
      of opening the file. The real dispatch is
      [`basic/strvar.asm:434`](basic/strvar.asm:434), and it is an explicit
      **whitelist of one**: `fch_mode_class` then `cp 1 / jr z,sid_ok`, `cp 4` →
      ERR 61 for RANDOM, **everything else → ERR 55**. `CAS_IN_MODE` (8) simply is
      not mode 1.
      🔴 **AND THE COMMENT BESIDE IT IS NOW FALSIFIED.** It reads *"Measured
      reference rule: mode 1 reads; RANDOM is ERR 61; EVERY other open mode is
      ERR 55."* That rule was measured by D-NOTOPEN2 **over modes 0–6** and then
      stated over ALL modes — the generalisation this very entry was filed to
      complain about, with a concrete wrong answer at the end of it. Annotated in
      place, not deleted.
      ⚠️ **The read machinery exists but is not simply reusable**: `input_common`
      has its own `cp CAS_IN_MODE / jr z,inp_cas` arm sourcing bytes through
      `cas_in_getbyte`, whereas `INPUT$`'s `sid_ok` tail goes `fch_select` +
      `str_inputd_read`, which are disk-oriented. So the fix is a second source
      for `str_inputd_read`, not a one-line widening of the `cp 1`. **Cost
      unmeasured — do not quote this paragraph as a price.**
      ⚠️ The other seven cells of the same sweep AGREE (`FIELD` 5, `GET` 58,
      `PUT` 58 in both modes; `INPUT$` 55 in OUTPUT mode is correct — a channel
      open for writing cannot be read). Only the one cell where the mode's own
      direction makes the verb legal is wrong.
      💰 **SHAPE MEASURED 2026-09-05, AND IT DOES NOT FIT TODAY.** `strvar.asm` is
      included at `basic/main.asm:192`, i.e. **main page 1**, which `make
      basic-reloc` printed at **6 B free** on 2026-09-05 (low region 9 B). 🔴 The
      cost driver is that `str_inputd_read` calls **`fat_io_getbyte` directly** —
      no vector — so serving a cassette source needs either an indirection at
      that call site plus a per-channel-type setter, or a parallel loop. With the
      `cp CAS_IN_MODE / jr z,…` dispatch arm on top, the shape is **~12–20 B**,
      against 6. ⚠️ **That is a WALL READING and wall readings rot** — re-run
      `make basic-reloc` before believing it, and note `input_common` solves the
      same problem with an `ARL_GETBYTE` vector, so a shared indirection might pay
      for itself across both sites rather than costing twice.
      ⚠️ `diskbasic-acceptance`/a cassette-side gate owns the surface, and the row
      set has no CAS: channel rows at all yet.
      🤖 AUTONOMOUS — the reference settles it; finishable unattended (no his-decision signal found).

- [x] ✅ **UNMEASURED: a machine reset BETWEEN a RANDOM `PUT` and its `CLOSE`.**
      **MEASURED 2026-09-05 (D-PUTCUT, `scratchpad/putcut_probe.py`) — and the
      filing's expectation is INVERTED.**
      🎯 **THE POWER CUT IS ONE TCL LINE.** openMSX backs `-diska` with the host
      file and writes sectors through as the guest issues them, so **killing the
      emulator IS the power cut** and the `.dsk` left behind is the artifact. The
      only real requirement is that the cut land at a chosen INSTANT rather than
      a guessed one, and the guest can say when: the program POKEs a sentinel
      after `PUT` and spins; the script polls that byte and exits the moment it
      appears. No race, no sleep-and-hope. Both re-examinations
      (2026-08-09 included) said *"the harness reads the image after the machine
      exits normally"* — which is true of `diskbasic_probe_lof.py` and was never
      a property of the question.
      | | clean `CLOSE` | CUT after `PUT` |
      |---|---|---|
      | **zerobas** | entry, size=16, clus=3, FAT=EOC, record on disk | **IDENTICAL** |
      | **CF-3300** | entry, size=16, clus=3, FAT=EOC, record on disk | **entry present, clus=0, size=0, no chain, no data** |
      🔴 **"The reference has stamped nothing" is FALSE.** It stamps a directory
      entry at `OPEN`; what is missing after the cut is the cluster, the size and
      the chain — so the reference leaves a **0-byte entry pointing at NOTHING**,
      which `DIR` will show. That is arguably worse than stamping nothing at all.
      ✅ **And zerobas's chain — "whose FAT state at that instant NOTHING HAS
      EXAMINED" — is now examined: `FAT=EOC`, a proper single-cluster chain, with
      the record's bytes actually on the disk.** For zerobas the `CLOSE` changes
      nothing on disk at all; everything the file needs is committed by the `PUT`.
      🎯 **So it is not a parity question in either direction.** Under normal
      operation the two images are byte-for-byte the same story (the clean-CLOSE
      row is identical on both machines); the difference exists ONLY inside the
      crash window, and there **zerobas is strictly the more robust of the two**.
      The filing offered "zerobas is more robust here" and "zerobas leaves a
      dangling entry here" as the two plausible outcomes — the first is right,
      and the dangling entry is the REFERENCE's.
      ⚠️ **The control is what makes any of that readable.** An entry present
      after a cut means nothing without the same machine's clean-CLOSE image
      beside it, so all four arms run and are compared as a matrix.
      🔴 My first formatter CRASHED on `clus=0` — `if entry and clus` skipped the
      FAT lookup and left `fat=None`. A cluster of 0 is a real state, not a
      missing reading, and it was the whole finding.
      --- the original filing ---
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

- [x] ✅ **`float-acceptance` HAS NO NAMED EXPECTED-FAILURE MECHANISM.** CLOSED
      2026-09-05. All five suites now name their denominator and the one
      known-deviation table is a CONTROL rather than a suppression.
      🔴 **THE SUPPRESSION WAS REAL AND WAS WRITTEN DOWN AS A FEATURE.**
      `float_arith`'s `KNOWN_DEV_DIV` stores both values per row — the
      correctly-rounded zerobas one AND the reference's low-biased one — and its
      comparator read **only** `zb_span`, never `ref_span`. The comment said so
      out loud: *"the reference's low value noted, NOT asserted == reference."*
      So if a reference had ever started AGREEING with us, the deviation would
      have silently stopped being a deviation and the row would still print
      PASS. The data for the control was already there and nothing read it.
      Both halves are asserted now; pinning the reference is no more fragile than
      the rest of the suite, every other row of which asserts exact reference
      text already.
      ✅ **AND THE DENOMINATOR IS PINNED**, per suite: 66 / 60 / 203 / 65 / 8 =
      **402 cases**, printed in each `ALL PASS` line and refused if a full run
      builds a different number. `ALL PASS` over a matrix that silently shrank
      reads exactly like `ALL PASS` over the whole one.
      🎯 **PRINTING THE COUNT EXPOSED A SECOND HOLE ON SIGHT**: `--only` with a
      filter matching nothing printed **`ALL PASS (0 cases)`** and exited 0 — the
      0/0-ALL-CONVERGED shape, pre-existing and invisible until there was a
      number in the line. An empty selection now refuses in all five.
      🔬 **THREE ARMS RUN, NOT ASSUMED:** a corrupted pinned reference reddens its
      row (rc 1, and it would have PASSed under the old comparator); a matrix
      shrunk by one fires the pin (rc 2, naming 202 vs 203, and again 64 vs 66 in
      a second suite, so the mechanically-applied guards were each fired rather
      than only parsed); a legitimate `--only` narrowing still runs green (17
      cases). Probe restored byte-identical after each arm.
      ⚠️ The filing's *"reports 371 PASS, 1 FAIL and exits non-zero"* is
      historical — the suite is green today, and the count is 402, not 372.
      --- the original filing ---
      Filed 2026-08-01 by D-EXPKW. The suite is green today, so this is not urgent —
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
      ✅ **MEASURED 2026-09-05 (D-NOORCNT) — the census now prints the breakdown
      every run, so it cannot rot back into "an unmeasured amount".**
      Of the **311 B**: **26 B in derived 2-byte cells (13 cells)**, 280 B in
      cells of another width, 2 B unnamed.
      🔴 **14 B (7 cells) AGREE ON THE DELTA — an oracle the absolute test threw
      away**: `MEMSIZ`, `STKTOP`, `FRETOP`, `SAVSTK`, `FILTAB`, `NULBUF`,
      `HIMEM`. Identical across all 13 movement states. So the over-count is
      **14 B, ~4.5% of the bucket** — not the whole 311, and now a number.
      12 B (6 cells) disagree on the delta too, so NO-ORACLE stands for those.
      🎯 **THE PAIRING RULE IS THE ENTRY'S OWN WARNING, HONOURED**: a pair is
      never guessed from adjacency — it is a PUBLISHED head whose DERIVED extent
      (distance to the next published symbol) is exactly 2 and BOTH of whose
      bytes are in the bucket. The 280 B in other-width cells are counted and
      LEFT ALONE: their width is unknown, and inventing one is the error the
      entry warned against.
      🔴 **AND THE FIRST RUN OVER-COUNTED, for exactly the reason this sweep
      already guards elsewhere**: it included the BASELINE state, where every
      delta is 0 and `0 == 0`, and reported **13** cells agreeing instead of 7.
      `classify` already refuses to dress up baseline agreement ("a machine that
      never touches a byte agrees with one that does"); the breakdown now skips
      the baseline for the same reason.
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
      ✅ **THE GROUND TRUTH IS MEASURED, 2026-09-05 (D-TRAILBLANK,
      `scratchpad/trailblank_probe.py`) — the entry's own suggested path, built.**
      An `$EA` ASCII program on tape, `LOAD"CAS:"`, and the readout is the
      TOKENISED PROGRAM at TXTBASE via `debug read_block` — **bytes, not a
      screen, so nothing rstrips anything.** Same payload path on all three
      machines; only the COMMAND differs (typed on the VG-8020 and zerobas,
      shipped as an `AUTOEXEC.BAS` on a disk for the CF-3300, whose date prompt
      hijacks the keyboard — the disk carries the command, never the payload).
      | line | delivered | vg8020 | cf3300 | zb |
      |---|---|---|---|---|
      | `10 REM HELLO ` | verbatim | `<8F> HELLO ` | same | same |
      | `20 A=1 ` | verbatim | `A<EF><12> ` | same | same |
      🎯 **ALL THREE KEEP THE TRAILING BLANK, in the `REM` tail AND after a
      literal.** So **the tokeniser is innocent on every machine** — "not in any
      scanner" is no longer a suspicion, it is a reading, and the crunch cannot
      be where the typed-path difference comes from.
      ⚠️ **What that does NOT do is establish the editor**, and this entry is the
      reason to be careful: its own second paragraph records the typed-path cell
      as unstable (`--repeat 1` read the `REM` row WITHOUT the blank on zerobas,
      for a payload no crunch change can touch). So the pair is
      "scanner: measured identical" + "editor: an unstable reading" — the
      difference itself needs re-establishing before anyone chases the editor,
      and this run deliberately does not lean on the unstable half.
      🎁 **AND THE GATING OBJECTION IS ANSWERED TOO.** *"A payload whose delivery
      cannot be verified may not gate"* was true of the KEYBOARD path; this one is
      verified by construction — the bytes are read out of memory, and the two
      informational rows could become scored rows through it. Not built here.
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
      ✅ **BUILT 2026-09-05 (D-WHOREACH, `tools/who_reaches.py`).** It asks
      `check_dead_code.Spans` the REVERSE question — that graph already resolves
      fall-through and shared-tail edges for the dead-code sweep — and reports
      reachers by HOP DISTANCE, which is what makes the answer readable:
      | | `print_msg` | |
      |---|---|---|
      | hop 1 | **9** routines | **all 9 NAME it** — which is why a grep finds them |
      | hop 2 | **64** routines | **all 64 SILENT** — no grep for the callee can list one |
      🎯 **THE HOP-1 COLUMN IS THE LOAD-BEARING HALF.** That every hop-1 reacher
      names the target is what makes "silent" mean something: it establishes the
      grep/hop-1 equivalence the report asserts, so hop 2+ is exactly the blind
      spot and not merely a bigger number. The selftest requires it.
      🔬 **AND ITS SELFTEST IS THIS ENTRY'S OWN CASE**: `dl_store` — the
      line-number-out-of-range arm that reaches `print_msg` by `jr
      dl_ovf_report` and never names it — must come back as a reacher beyond hop
      1, and must not name the target. Without that the tool would only be
      re-deriving what a grep already finds. `dl_ovf_report` is required at hop 1
      in the same run.
      ⚠️ **A QUERY TOOL, NOT A GATE, deliberately**: "no silent reachers" is not
      a property this tree has or should have — 64 legitimate ones for this one
      callee. What a blast-radius sweep needs is the LIST, not a verdict. It is
      collected by `selftest-check` (its `TREES` includes `tools`).
      ⚠️ `@prologue:` nodes are filtered: they are the dead-code graph's own
      per-file artefact, not routines anyone can name or migrate, and counting
      them would pad the answer with things that are not callers.
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
