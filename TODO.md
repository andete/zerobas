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

**Apparatus / tooling**

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
      only exists to satisfy a raise that unwinds anyway". Unpriced.

- [ ] 🔴 **EVERY KNIFE RUNNER IN `scratchpad/` CAN EXIT BETWEEN THE WRITE AND
      THE RESTORE, LEAVING THE TREE CUT.** Filed 2026-08-26 by D-MIDOP
      ([`docs/spec-basic-midop.md`](docs/spec-basic-midop.md) §5.2), which hit
      it: an assertion fired after the cut was written, the only restore sat at
      the END of the loop body, and the run exited with
      `basic/str-engine.asm` still holding K-MD1. **The next invocation reported
      *"anchor appears 0 times"*, which reads as a bad anchor and is really a
      dirty tree** — and a dirty tree silently corrupts whatever is measured
      next.
      🟢 `scratchpad/midop_knives.py` now registers an `atexit` restore beside
      the read, covering the assert, the exception and the clean return alike.
      🔴 **THE OTHER ~20 RUNNERS DO NOT** (`onlist_knives.py`,
      `pusing_knives.py`, `playop_knives.py`, `evferr_knives.py`, and every
      earlier one) — they all share the shape the operating rules describe as
      *"RESTORE BY WRITING THE BYTES"*, which says nothing about WHEN.
      ⚠️ **THE DAMAGE IS SILENT AND CROSS-SLICE**: a runner that dies mid-cut
      leaves a tree whose next `make gates` measures a knifed machine, and the
      ROM-hash guard cannot see it because the hash legitimately differs from
      the baseline it was handed. Unpriced; the shape is three lines per runner,
      or one shared helper.

- [ ] 🔴 **A `unit-test` FLAKE IS OPEN AND UNCAUSED — the diagnostic that would
      have named it was only installed AFTERWARDS.** Filed 2026-08-26 by
      D-PASMOSAY ([`docs/spec-probe-pasmosay.md`](docs/spec-probe-pasmosay.md)).
      The D-PLAYOP battery went 38/38 with one *"recovered flake (green on
      serial retry)"* on `unit-test`; the failing file was `test_expr.py` and
      the cause was `pasmo` exiting 1 while assembling `basic/main.asm`. **Why
      it exited 1 is unrecoverable** — `capture_output=True` held the message
      and `CalledProcessError.__str__` does not print it.
      🟢 **THE NEXT ONE WILL SAY**: `tests/_tmp.py` now installs a
      `sys.excepthook` that prints the child's stderr, falsified 4 arms of 4.
      ⚠️ **THAT IS NOT A DIAGNOSIS OF THIS ONE.** Ruled out by measurement, not
      by argument: the artifact name `zb_eval.rom` is used by **one** test file,
      `tests/run.py` is **not** parallel, and `ZB_TEST_TMP` was set to a
      per-invocation directory — so it is not the fixed-name collision class
      `tests/_tmp.py` was written for. A solo `make unit-test` on the same tree
      is **59 PASS / 0 FAIL**. What is left is resource pressure under 8-way
      parallelism, or something not yet named. **Do not close this on the next
      green battery; close it on a captured message.**

- [ ] ⚠️ **FIVE MORE NON-ATOMIC PUBLISHES INTO THE SHARED openMSX TREE, AND NO
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
      🔴 **THE STANDING HOLE IS THAT NOTHING CHECKS IT.** A new
      `open(path,"w")` into the shared tree reintroduces the window silently,
      and the only thing that would notice is another named `<NO CAPTURE>` —
      i.e. a flake, after the fact, in a battery. A one-rule checker
      (*no `open(...,"w")` whose destination resolves under the openMSX user
      dir*) is cheap; ⚠️ its DENOMINATOR is the hard part, because the path is
      built by `openmsx_paths.find_user()` at runtime and a textual sweep cannot
      resolve it. Unpriced.

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

- [ ] 🔴 **`KEY n,"str"` AND `KEY LIST` ARE UNIMPLEMENTED — A WELL-FORMED
      STATEMENT IS `Syntax error` HERE AND SILENT ON BOTH REFERENCES.** Filed
      2026-08-26 by D-MISSOP3. `KEY1,"X"` reads **0 / 0 / 2**: both references
      complete it, zerobas refuses it. [`basic/screen.asm`](basic/screen.asm):294
      is `jp stmt_error` with the comment *"KEY <n>,\"str\" / KEY LIST
      unsupported"*, so `ex_key` handles only `KEY ON` / `KEY OFF` (plus the T3
      `KEY(n)` arming form).
      🔴 **IT WAS ALREADY WRITTEN DOWN, INSIDE A `- [x]` BLOCK, AND THEREFORE
      INVISIBLE** — TODO.md:6645, a Phase-1 entry ending *"all Phase-3 scope"*.
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

- [ ] 🔴 **A STALE TRACKED PATCH DELIVERABLE IS INVISIBLE TO THE WHOLE
      BATTERY.** Filed 2026-08-26 by D-EVFERR, which shipped TWO ROM-moving
      commits without regenerating `zerobas-main-eu.ips` / `.bps` — **and
      `make gates` went 38/38 green both times.** The pair is the *shipped BASIC
      deliverable* (Makefile header, and `release:` calls regenerating it *"the
      maintainer's step before committing a basic/ change"*), so a stale one
      means the repo's advertised artifact does not match its own source.
      ⚠️ **THE OMISSION IS NOT WHAT NEEDS FIXING — THE BLINDNESS IS.** Getting it
      wrong took nothing more exotic than `git add <paths>` instead of
      `git add -A`, which is the normal way to keep a scratchpad out of a commit.
      🎯 `patches` is deliberately NOT a prerequisite of `machines` so the build
      stays usable without a C-BIOS checkout
      (docs/spec-lean-retire-s2-switch.md §4.4) — that trade is right and this
      item does not propose reversing it. What is missing is a CHECK: regenerate
      to a temp path and compare against the tracked bytes, RED on a mismatch,
      SKIP (not pass) with no C-BIOS. ⚠️ A check that silently passes when it
      cannot run is the 0/0-ALL-CONVERGED shape and would be worse than nothing.
      Unpriced; the gate is small, the *skip* semantics are the design.

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

- [x] ✅ **THE PARALLEL BATTERY'S FLAKE HAD A CAUSE, AND THE HARNESS WAS
      THROWING IT AWAY — FIXED 2026-08-25.** Six of seven full batteries that day
      recovered a *"FLAKE (green on retry)"*, each a single `<NO CAPTURE>` on a
      random row and a random side, with **not one diagnostic line anywhere**:
      openMSX's stdout/stderr went to `DEVNULL` and its exit status was used as a
      liveness boolean and discarded.
      🔴 **`<NO CAPTURE>` IS THE SAME STRING FOR FOUR DIFFERENT EVENTS** — stall
      watchdog, abscap backstop, openMSX dying on its own, or the guest genuinely
      wedging — and **the fourth is a REAL DEFECT that `run_gates.py` retries into
      green and labels a flake.** `omsx_repl._why_missing()` now spends the
      evidence the run already held: which watchdog if either, the exit status or
      signal, the elapsed wall, the lines written, and openMSX's own last words.
      🎯 **ON THE FIRST BATTERY THAT HAD IT, IT NAMED THE CAUSE**: *"openMSX
      terminated ON ITS OWN (exit 1) after 0s wall … emulator said: Failed to
      parser settings file 'settings.xml'"*. Every openMSX process **reads
      `~/.openMSX/share/settings.xml` at start and REWRITES it at exit**, so in a
      parallel battery a starting process reads a torn file and refuses to boot.
      Each run now gets its own copy via openMSX's own `-setting`. ⚠️ Side effect,
      and a good one: probe runs no longer write the user's openMSX settings.
      📏 **MEASURED, because a flake count is not causal evidence**
      (`scratchpad/flake/repro.py` drives the mechanism instead of waiting for
      it): **SHARED 35/40 starts failed (87.5 %), ISOLATED 0/40**, both arms
      against a COPY so the user's file is never touched.
      🔬 **`make omsx-diag-teeth`** (`probes/lib/omsx_missing_teeth.py`) is the
      standing falsification — a GREEN control that must print NOTHING plus four
      forced failures that must each be named DIFFERENTLY. `_why_missing` is a
      failure-formatting branch, so no healthy run executes it and nothing else
      can notice it rot. ⛔ **NOT in `make gates`**: two cases signal `openmsx` by
      name and would hit a neighbour, so it refuses to start while any is running.
      🔴 **AND THE FIRST CUT MOVED THE RACE INSTEAD OF REMOVING IT — CAUGHT BY
      THE DIAGNOSIS IT SHIPPED WITH.** `shutil.copyfile` isolated the DESTINATION
      and still READ the shared source mid-rewrite, so a run got a torn copy of
      its own and died on that: two flakes in the very next battery, naming the
      temp path. 🎯 **A COPY IS A READ.** `_settings_read()` now VALIDATES what it
      got as XML before believing it — a torn read is not a rare event to hope
      past, it is a return value to check — retries briefly, and omits the flag
      if it never comes back clean (no worse than before).
      📏 **THE FLAKE COUNT, BEFORE AND AFTER.** Before: **6 flakes in 7 full
      batteries**, wall 337–672 s. After: **0 in 3**, wall **427 / 414 / 415 s** —
      and the stability is itself a consequence, because a flake costs a whole
      serial re-run. At the old rate three clean in a row is ≈0.3 %, which with
      the mechanism (24/40 → 0/40) and the captured messages is the case.
      ⚠️ **NOT "the flake is solved" — "this flake is".** Another cause would now
      NAME ITSELF instead of printing nothing, which is the durable part.
      ✅ **AND THE FILED RESIDUAL IS CLOSED TOO** (`probes/lib/probe_tmp.py`):
      21 sites across 19 probes built `zb_{probe}_{side}_{label}.dsk` from a
      fixed name with no process identity and no cleanup. 8 shards × 4 replicated
      `CONTROLS` = 12 paths copied onto concurrently. 🔴 **AND THE LEAK WAS THE
      BIGGER HALF: 2165 orphaned `zb_*` files, 1.1 GB**, because nothing ever
      deleted them — adding process identity WITHOUT cleanup would have made that
      strictly worse. One directory per process, removed at exit, honouring
      `$ZB_TEST_TMP` exactly as `tests/_tmp.py` does. Verified: 6 concurrent
      processes asking for one name get 6 distinct paths, all gone at exit.
      🎯 **`tests/_tmp.py` HAD CARRIED THIS LESSON SINCE THE UNIT TESTS HIT IT**
      (*"bit the parallel gate battery as a stochastic pasmo failure"*) and it was
      never carried across to the probes — the half that actually runs eight at a
      time. **When a fix is filed as a helper, grep for the OTHER callers.**

- [x] ✅ **FIXED 2026-08-25, SAME DAY IT WAS FILED — `lineerr`'s two `SLOW_ROWS`
      now carry their 12 s on `run_gap`, not on `step`.** `run_gap=` in
      `run_side`; `step` stays at the side's default. **236 report rows
      byte-identical** across the 8 shards, **0 fallbacks** before and after,
      `make gates` **37/37**, ROM hashes unchanged.
      📏 **The window is UNCHANGED and that was checked before booting anything**
      (`scratchpad/rungap/check_timeline.py`, off `_tcl`'s generated timeline):
      RUN..capture is **12.0 s in both configurations**, and the per-case
      schedule ends at **166.5 → 52.5** emulated s (vg8020/zb) and **196.5 →
      91.5** (cf3300). Six case-runs, **−666 emulated s ≈ 2 s of wall** — filed
      as bookkeeping and it stayed bookkeeping.
      🟢 **AND THE TALLY WITNESSED IT.** The two shards holding these rows had a
      max signal instant of **182.7 / 182.6 emulated s; now 78.0**, the same as
      an ordinary row. 🔴 **What that proves is SUFFICIENCY, not need**: 0
      fallbacks says 12 s is still enough, nothing says it is still required —
      and with capture-on-signal that no longer matters, because a budget only
      costs time on a row that FAILS to signal.
      ⏱️ The battery came in at 540 s against 672 s for the previous full run at
      the same 14 s warm-up. **That is NOT this change** — 2 s cannot be 132 s;
      the warm-up is a 14 s serial sample and does not bound contention over a
      540 s parallel battery. No wall claim.

      ~~⚡ **`lineerr`'s TWO `SLOW_ROWS` PAY THEIR 12 s BUDGET ON EVERY TYPED LINE —
      the exact mistake `run_gap` was built to fix, still standing in one probe.**~~
      `basic_probe_lineerr.py` `SLOW_ROWS = {"c.32767": 12.0, "c.m32768": 12.0}`
      raises `step`, and `step` is the inter-line KEYBUF spacing as well as the
      RUN..capture budget. MEASURED (deterministically, off `_tcl`'s own timeline,
      `scratchpad/sncap/emutotal.py`): those rows schedule **166.5 emulated s per
      case against 43.0** for an ordinary row — 12 slots at 12 s to cover one
      completion that D-SNCAP2's tally shows signalling **0.2 s after `RUN`**.
      Six case-runs (2 rows × 3 sides) ≈ **740 emulated s ≈ 2 s of wall**, so this
      is bookkeeping, not a speedup: fix it by moving the 12 s to `run_gap=` and
      letting `step` stay at the side's default. ⚠️ **VERIFY THE ROWS STILL READ
      THE SAME** — the whole point of those rows is that they are slow, and
      `run_gap` is a MINIMUM that never pulls a capture earlier, so a byte-identical
      before/after is the check (`scratchpad/sncap/rowdiff.py`). Filed 2026-08-25
      by D-SNCAP2, which measured it in passing and did not act on it.

- [x] 🔴 **SAVESTATE-RESTORE-PER-CASE — BUILT, MEASURED, AND WITHDRAWN 2026-08-24
      (user). THE CODE IS REVERTED.** Same-session A/B: **555 s with vs 642 s
      without** — but the OFF run's single flake cost ~124 s in serial retry,
      *more than the whole difference*, so that 13.5 % is not claimable. The
      least-confounded figure is same-gate: `graphics-acceptance` **425 s vs
      463 s, ~8 %**. **Not worth the inherent risk**: a behaviour change to the
      module every probe depends on, four failure modes that all presented as
      HANGS, an eligibility rule measured wrong twice in opposite directions, and
      a permanent 17 s battery gate to keep proving it safe. Kept as a record in
      [`docs/spec-probe-savestate.md`](docs/spec-probe-savestate.md) (marked
      WITHDRAWN) because the measurement outlived the mechanism — see the struck
      entry below for what it refuted. ⚠️ Revisit only if the budget/sentinel work
      lands and makes the boot a bigger share of what remains — **on fresh
      numbers, not these**.

- [x] ~~**SAVESTATE-RESTORE-PER-CASE — the premise, REFUTED**~~ (kept: this is the
      finding that redirected the arc)
      [`docs/spec-probe-savestate.md`](docs/spec-probe-savestate.md).
      🟢 **What shipped and is durable:** `omsx_repl.make_savestate` + the
      `state_load` path (boot once → `savestate` at the ready prompt → `loadstate`
      per case), and **`make savestate-check`** in the battery — the differential
      this item demanded *first*: **12/12 restore==cold, 0 DIFF** on the subject
      AND both oracles across text, POINT and raw-VRAM captures, with a within-run
      TEETH control so a 0-DIFF tally cannot be vacuous. Development differential
      behind it: circmiss 17 cases × 3 machines **51/51** raw-identical, plus a
      6144-byte SCREEN-2 pattern-table battery **15/15, 0 differing nibbles**.
      🔴 **What the measurement KILLED: "the per-case boot dominates".** It is
      ~0.7 s of wall per case, while the gates that dominate spend far more in
      their own EMULATED timelines (`graphics-acceptance` PAINT runs `step`
      45–90 emulated s — boot is ~10–15% there), and `lineerr` (210 rows, ~46% of
      serial), where boot *should* have dominated, is excluded by its own
      per-case disk isolation. Battery **555 s 38/38 green 0 flakes** (vs 680 s
      with the prior rule, against a 580–750 s baseline) = **within run-to-run
      noise, not the predicted multiple**; `graphics-acceptance` 269 s vs ~304 s
      (~12%). 🎯 **The eligibility rule was measured wrong TWICE, in opposite
      directions** (inert for one-case-at-a-time callers; a pessimism that took 6
      snapshots for 6 rows when a probe varies `diska` per case) — neither shape
      is visible in the code; both needed a stopwatch against
      `ZEROBAS_SAVESTATE=off`. Successor rule: warm on the SECOND sighting of a
      key. See [[parallel-gate-battery]].

- [x] ✅ **CLOSED 2026-08-25 (D-PAINTVRAM) — `PAINT` WROTE THE WRONG VRAM, AND
      THE FIX WAS A RULE THIS ROM ALREADY HAD.**
      [`docs/spec-basic-paintvram.md`](docs/spec-basic-paintvram.md).
      💰 **99 B of sub page 0** (2563 → 2464 free); `basic-reloc.rom`
      byte-identical — a `sub/` tenant edit, exactly as the two-ROM rule predicts.
      🟢 **`scratchpad/vram_fidelity.py` NOW READS 0 DIVERGENT CASES**: all eight
      primitives × three machines, **both** SCREEN-2 tables, 12288 bytes a side,
      byte-identical — including the circle-bounded fill's mixed partial/whole
      geometry (the 34 `$FF` pattern bytes the references leave reproduce exactly),
      not merely the uniform flood.
      🎯 **THE MECHANISM WAS D-BFBYTE's, ONE SLICE OLDER.** A run covering all
      eight pixels of a cell row is written blind as `pattern := $00,
      colour := C` — the colour in the BACKGROUND nibble, foreground forced to 0.
      `LINE ,BF` had done that since D-BFBYTE; `PAINT` fills by horizontal spans
      and never got it, so it wrote its spans through the per-pixel colour-clash
      RMW like eight `PSET`s. `gfx_span_bytes` is that loop, EXTRACTED from
      `gbf_row` and now shared by both; `gfx_paint_row` splits the span with the
      existing pure `gbf_split` and keeps the two partials per-pixel.
      ⚠️ SCREEN 2 only — an MC byte is two CELLS with no colour table, so
      MULTICOLOUR keeps the old per-pixel loop (also the only one that honours
      `GFX_PPITCH`'s 4). `gfx_paint_extend_lr` is untouched: it still paints each
      newly discovered pixel inline as it walks (its own header's bug fix), and
      the span's byte fill then overwrites those cells — which is the reference's
      own end state.
      ✅ **THE GATE ROW NOBODY HAD WRITTEN NOW EXISTS — PHASE H-V**, byte-level,
      seven cells over three programs, RED on the pre-fix build and GREEN after;
      plus PHASE H's `paint_then_pset`, which shows the SAME divergence through
      `POINT` after a second draw (`PAINT(128,96),15 : PSET(128,96),6` →
      references `6 15 15`, pre-fix zerobas `6 6 6`) and is why this was a bug and
      not cosmetics. **Every one of the seven reference oracles matched
      first time.**
      🔴 **THE FIXTURE, NOT THE DIAGNOSIS, WAS WRONG FIRST.** Draft 1's bounded
      case used `C != B` and all three of its cells came back identical on BOTH
      sides — the fill had flooded the screen on all three machines, so its two
      "partial" controls were reading whole-byte territory. That is the
      references' own dichotomy (`C == B` bounded, `C != B` floods whatever is
      drawn, [`ntwall-scout-2026-08-22.md`](docs/ntwall-scout-2026-08-22.md)), and
      the repair added a FOURTH cell outside the box, without which the case
      cannot tell a bounded fill from a flood at all.
      ⚠️ **AND `B == C` IS A REAL COVERAGE HOLE, NOT A CHOICE**: a bounded fill
      REQUIRES `C == B`, and an unbounded one runs every span the full 0..255 —
      32 cell-aligned whole cells, no partial at either end. So no fixture on
      these machines puts a partial cell and `B != C` together. `flood_c_ne_b`
      carries the *which colour* question alone; without it a fill that wrote the
      BORDER colour would pass every other row in the phase.
      🔬 **The host model needed the second write path too** — `tests/test_graphics.py`
      traps `gfx_paint_plot`, which whole cells no longer go through, so its three
      whole-algorithm cases failed until `gfx_span_bytes` was trapped as well.
      It also now pokes `SCRMOD` explicitly: nothing in that file ever set it, so
      the SCREEN-2 arm of `gfx_is_mc` was being taken by whatever the simulated
      RAM happened to hold. **An implicit mode is not a mode.**

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

- [x] ⚡ **THE REAL GATE-SUITE LEVER WAS THE BUDGETS' *SCOPE* — SHIPPED 2026-08-24
      (`c04606b`, `f9afec1`), 28% OFF THE BATTERY.** `step` did double duty: it is
      the inter-line injection spacing AND it was the RUN→capture completion
      budget, so a phase needing a long budget paid it on EVERY TYPED LINE (a
      graphics PAINT case bought 6 × 90 = 540 emulated seconds to cover one
      46-second fill). **`run_gap` separates them**; line spacing keeps the 2.5 s
      default, and **no budget is made tighter than its measured need**.
      **MEASURED:** per case 2.9 s → 0.5 s (VG-8020, 5.5×) with the capture
      BYTE-IDENTICAL; `graphics-acceptance` **269 s → 218 s** solo and
      **465 s → 347 s** in the battery; **battery 664 s → 476 s, 37/37 green, 0
      flakes, ROM hashes unchanged**. 13 call sites converted.
      ⚠️ **ONLY WHERE THE GAPS ARE PURE TYPING** (`("stored", …)`, or a single
      line): a DIRECT-mode line executes AS IT IS TYPED, so its gap genuinely is a
      completion budget — `deffn` (8 s), `arrays` (6/150 s) and `namspc` (12 s,
      whose own comment records the value exists so `OPEN`/`CLOSE`/`KILL` disk
      work finishes BETWEEN lines) are deliberately LEFT ALONE.
      🟢 **AND THE BUDGETS THEMSELVES ARE EARNED**: the flood needs **46.252527
      emulated seconds** on zerobas (exact, mark stopwatch) against `PAINT_STEP`'s
      90 — a 1.9× margin. It was the SCOPE that was wrong, never the size.
      📏 **`wall ≈ 0.003 s per emulated second`, UNIFORMLY** — a hypothesis that
      prompt-idle costs more than tight-loop-idle was tested and REFUTED, so
      emulated seconds convert to wall at a flat rate and the arithmetic above is
      the whole story.

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
      of main page 1** against **2 B free** (measured `b8a8137`), and it still
      misses a nested leak. The two cheaper designs are rejected on principle in
      §6 — one of them makes the trap *silently* dead.

- [ ] 🔴 **`CLEAR` BREAKS THE CONSTRUCTION THAT MAKES `TRAPSTK`'s GSP MATCH SOUND
      — UNMEASURED.** Filed 2026-08-23,
      [`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §7. After a
      leaked trap dispatch the abandoned GOSUB frame is still on the stack, so
      the only `RETURN` that can reach `record.gsp` is the one popping the trap's
      own frame — the match is sound *by construction*. **`clear_vars`
      (`basic/vars.asm:1061`) resets `GSP` and does NOT call `trap_init`**, so
      after a `CLEAR` an unrelated later `GOSUB`/`RETURN` pair can land on the
      stale record's gsp and re-enable a trap the program believes is dead
      (+`TRAPENA`). The references have no `TRAPSTK` at all. **Needs the T5
      probe's POKE-based readout, not D-TRAPSVC's** — `CLEAR` wipes the variables
      a fenced `PRINT` row carries its flags in.

- [ ] ⚠️ **KEY / STRIG / SPRITE / STOP were NOT run against the D-TRAPSVC rows.**
      2026-08-23, [`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §7.
      `ON INTERVAL` is the only self-firing MSX1 trap, so the other four are
      covered by a **code** argument (they share `check_traps`, `ct_find`,
      `set_state` and `trap_return_check` verbatim; the index is a parameter),
      not by a measurement. The device-driven harnesses exist
      (`basic_probe_key_trap.py`, T2/T4 probes) if the argument is ever attacked.

- [x] ✅ **`POKE <addr>,` WITH NO VALUE WROTE ZERO — FIXED 2026-08-23
      SILENT MEMORY WRITE, and it is not a carve artifact.** Found 2026-08-22 by
      D-DUPSPAN2's closing demo (`scratchpad/dupspan2_demo.py`,
      `poke.tail`/`poke.head`/`poke.ok`), measured with a marker on each side of
      the statement so "did it abort?" needs no trappable error:

          20 POKE &HE000,99 : 30 PRINT"<A>"; : 40 POKE &HE000, : 50 PRINT"<B>";PEEK(&HE000);

      VG-8020 and CF-3300 both print `<A>` and abort with **`Missing operand in
      40`**; zerobas prints `<A><B> 0` — it COMPLETES and has overwritten the
      byte with **0**. ✅ **PRE-EXISTING, MEASURED NOT ARGUED**: the identical
      program on the pre-carve ROM `834c45b5` reads the same `<A><B> 0`.
      🎯 The aliased label is NOT implicated and there is a green row that says
      so: `POKE ,1` (the missing ADDRESS) reaches `poke_err` and reads ERR 2 on
      all three, and `POKE &HE000,65` works. The missing-VALUE path never reaches
      `poke_err` at all — the empty operand evaluates to 0 and the store
      proceeds.
      ✅ **SWEPT 2026-08-23, D-MISSOP,**
      [`docs/spec-basic-missop.md`](docs/spec-basic-missop.md)
      (`scratchpad/missop_probe.py`, 26 rows x 3 machines, 78 runs).
      **IT IS ONE RULE AT SIXTEEN SLOTS: 16 DIFF, 10 agree, references unanimous
      on all 26.** 13 rows SILENTLY COMPLETE (four of them WRITE — `POKE` three
      ways and `VPOKE`, each turning a byte holding 99 into 0) and 3 abort with
      ERR 2 where the reference says 24. THE RULE: *a required slot that ends
      where a value was needed is `Missing operand` (ERR 24); an empty operand
      terminated by `)` or `,` is `Syntax error` (ERR 2); an OPTIONAL slot may be
      omitted and completes.* 🎯 **That partition is ALREADY `ev_f`'s partition**
      — `ev_f_empty` (at `)`/`,`) is exact today, and `ev_f_err` (end of
      statement, `:`, `+`) is the hole: it returns DE=0 with the `ERRMARK`
      landmark and **no `penderr_set` at all**. 💰 **~6 B — 5 in
      `basic/expr.asm` + 1 table byte in `basic/interp.asm`, BOTH page 1, which
      was 2 B free on 2026-08-23.** An ESTIMATE and therefore a lower bound.
      Funding: a 6 B page-1 carve, or PROMOTE `ev_f_err` into the low region
      (which was 17 B free on 2026-08-23) —
      but `ev_f_defer` falls THROUGH into it, so the net gain must be measured.
      §6.1 names what a knife must attack, headed by `str-engine.asm`'s
      backtracking `jp ev_f_err` sites.
      🔴 **AND THE SWEEP REFUTED THIS ITEM'S OWN JUSTIFICATION**: the
      parenthesis *"`LOCATE ,` correctly gives ERR 24"* is false — `LOCATE,1`
      reads **0 on all three** (an omitted LOCATE row is an OPTIONAL slot). The
      conclusion was right and the row named for it measured a different
      question; `LOCATE1,` is the row that shows the mechanism (§7).
      ✅ **CLOSED BY D-MISSOPFIX, 5 B** (`ev_f_missop`, basic/expr.asm +
      one `db 24` in `fperr_to_err`), funded by PROMOTING `basic/title.asm`
      into the low region: **13 of 16 rows closed, all four silent memory
      writes among them**, 3/3 knives EXACT, 34/34 gates green. The three
      rows that remain, and everything the fix widened past, are the OPEN
      items directly below. §10-§16 of the spec.

- [ ] 🔴 **THE `Missing operand` CLASS HAS THREE MECHANISMS; ONE IS CLOSED AND
      3 ROWS STILL DIVERGE.** D-MISSOPFIX shipped 2026-08-23, 5 B
      ([`docs/spec-basic-missop.md`](docs/spec-basic-missop.md) §10-§14),
      closing **13 of 16** rows including **all four SILENT MEMORY WRITES**
      (`POKE` three ways + `VPOKE`, each turning a byte holding 99 into 0).
      3/3 knives EXACT. What remains:
      * ✅ **CLOSED FOR CIRCLE 2026-08-23 (D-CIRCMISS, 7 B),**
        [`docs/spec-basic-circmiss.md`](docs/spec-basic-circmiss.md). A verb's
        own grammar swallowed the dangling comma before `eval` was ever reached,
        so `CIRCLE(50,50),20,` **drew the circle and reported nothing**. One
        `cpt_err24` raiser in [`sub/circleparse.asm`](sub/circleparse.asm) and
        **eight `jp z,cpt_finish` retargeted to it (0 B, same instruction)**;
        sub page 1 free **1624 → 1617 B**, the arithmetic estimate EXACT.
        **17 rows x 3 machines, 9 DIFF → 1; 4/4 knives EXACT; 34/34 gates.**
        🔴 The filing's label set was wrong and its count was right:
        `cpt_after_aspect` carries no such pair at all — the four labels are
        `cpt_at_c` / `cpt_at_start` / `cpt_at_end` / `cpt_at_aspect`.
        🎯 The slice's real work was the four `o.*` rows proving the LEGITIMATE
        omitted slot (`CIRCLE(50,50),20,,0.1,6.2`) still draws, and K-CM3/K-CM4
        proving those rows can go red. ✅ **PAINT WAS THE SAME DEFECT AND IS
        CLOSED 2026-08-23 (D-PAINTMISS, 3 B, below).**
      * 🔴 **RE-MEASURED 2026-08-26 — D-MISSOP3,
        [`docs/spec-basic-missop3.md`](docs/spec-basic-missop3.md),
        `scratchpad/missop3_probe.py`, 29 rows x 3 machines — AND THE FILED
        SENTENCE IS FALSE.** It read
        *"predicted not to move under the evaluator fix, and they did not"* —
        **`A$=` and `A$=+` now read 24 on all three and are GREEN.** Something
        between 2026-08-23 and today closed them and nothing re-read the item.
        🔴 **`KEY1,` IS MISDIAGNOSED, NOT UNFIXED**: it is not a wrong error
        CODE, it is `KEY n,"str"` being UNIMPLEMENTED — see the item below,
        found by a control that was supposed to be trivially green.
        **`MID$(A$,2)=` (zb 2, refs 24) is the ONE row of the three that
        survives as filed.**
      * 🔴 **AND THE SWEEP FOUND THREE MORE, NONE OF THEM FILED ANYWHERE**:
        `PLAY` (zb **2**, refs 24 — confirms the separate item below),
        `PRINT USING` (zb **2**, refs 24), and `ON 1 GOTO` (zb **0**, it
        SILENTLY COMPLETES, refs **2**).
      * ✅ **THE DENOMINATOR IS NO LONGER A SAMPLE — the ten verbs this item
        named as *"unmeasured, not green"* were all run.** Already correct:
        `WIDTH`, `OPEN`, `INPUT#`, `PRINT#` (24 on all three). `FIELD` is
        **excluded, not green**: the references DISAGREE (VG-8020 5, CF-3300
        24) because the VG-8020 has no disk. Bare `INPUT`/`LINE INPUT` are
        UNMEASURABLE by this instrument — they are valid statements that prompt
        and WAIT, so the row would hang rather than answer.
      * 🔴 **THE ONE-RULE PREDICTION WAS REFUTED, THEN HALF-RESTORED BY ITS
        OWN SEPARATORS.** *"A required slot that ends where a value was needed
        is 24"* is wrong on both references twice — `SWAP A,` is 2, `DRAW` is 5.
        `SWAP ,B` is **2 on all three** (its slot is a NAME), so SWAP is a real
        exception. 🔴 **`DRAW` NEVER WAS ONE: `SCREEN2:DRAW` is 24 on both
        references and 13 here.** The baseline row agreed at 5 on all three
        because **SCREEN 0 makes `DRAW` `Illegal function call` before the
        operand is ever looked at** — a case that agreed for the wrong reason,
        on every machine, hiding a live divergence.
        🎯 **THE REFINED RULE:** *a missing **VALUE** is 24; a missing **NAME**
        is 2; and a missing **SEPARATOR** is 2* — `PRINT USING"##"` is 2 on both
        references, not 24, because the format is present and the `;` is not.
        ⚠️ Rests on TWO separating rows; the scope is the verbs measured.
      * 📏 **FULL LIVE LIST — TEN, where this item knew of two:** `KEY1,"X"` and
        `KEY LIST` (refs **0**, zb 2 — the item below), `KEY1,` (24 vs 2),
        `MID$(A$,2)=` (24 vs 2), `PLAY` (24 vs 2), `PRINT USING` (24 vs 2),
        `PRINT USING"##"` (2 vs **0**), `ON 1 GOTO` and `ON 1 GOSUB` (2 vs
        **0**, they SILENTLY COMPLETE), `SCREEN2:DRAW` (24 vs 13).
        **Four roots, so four slices, none of them priced here** — page 1 was
        99 B free on 2026-08-26; read the wall, never this line.

- [x] ✅ **CLOSED 2026-08-23 — PAINT'S DANGLING COMMA RAISES ERR 24 AND NO
      LONGER FILLS** (D-PAINTMISS,
      [`docs/spec-basic-paintmiss.md`](docs/spec-basic-paintmiss.md)). Filed
      2026-08-23 by D-CIRCMISS §7, measured in full by D-CLRTRAP §2, fixed here.
      💰 **3 B of MAIN page 1 — free 4 B → 1 B**, both read from a clean
      `make basic-reloc` on 2026-08-23. `basic-reloc.rom` `abfefa7f → 59f0a082`
      and the merged image `a8173c25 → 5ea13c71`; **`sub.rom` unchanged at
      `490ffc49`** — the right signature for a `basic/*.asm` edit and the exact
      OPPOSITE of D-CIRCMISS's.
      🎯 **THE FIX IS ONE NEW LABEL AND FOUR RETARGETED `jr`s.**
      [`basic/graphics.asm`](basic/graphics.asm) `ep_missing: jp loc_missing`
      (3 B — `loc_missing` ALREADY EXISTED, the same label `wid_missing`
      forwards to), plus four `jr z,ep_default_b` → `jr z,ep_missing` at **0 B,
      same instruction**. A trampoline beats both alternatives *because* the
      sites are `jr`s: an inline `ld a,24 / jp raise_error` is 5 B and four
      `jp z,loc_missing` is +4 B.
      🔴 **`ep_default_b` IS A SHARED TAIL WITH SIX JUMPS AND ONLY FOUR MEAN
      THIS** — the property is *a comma has already been consumed*, not the slot
      and not the terminator. The other two (`PAINT(x,y)` with no comma at all,
      `PAINT(x,y),15` with no `,B`) are the LEGITIMATE omissions and must keep
      painting. Enumerated as INSTRUCTIONS, never by grepping the symbol.
      📏 **16 rows × 3 machines, 6 DIFF → 0** (`scratchpad/paintmiss_after.out`);
      all ten PAINT rows unanimous. **6/6 knives EXACT**
      (`scratchpad/paintmiss_knives.out`): K-PM1/K-PM2 each point ONE legitimate
      exit at the new raiser and redden exactly one green row — that is what
      makes the trap rows detectors; K-PM4 reverts ONE instruction and moves TWO
      rows, which is the dynamic proof that the B slot is reached by both of its
      routes; K-PM5 is the only knife that reddens `p.omit`, and 🔴 **its
      obvious first draft could not have been run at all** — pointing
      `jr z,ep_c_empty` at the raiser orphans that label, fails `make deadcode`
      and builds no ROM, so the cut had to be a VALUE (`inc hl` → `nop`).
      ⚠️ **NOT extended by analogy to anything unrun.** The `cp ','` arm three
      lines below is a FOURTH argument and is ERR 2 (D-PAINTBORD `od2.b16c`);
      `basic/screen.asm`'s three `clr_apply` sites have the identical shape and
      are CORRECT. All six PAINT slots were RUN.
      💰 **AND IT LEAVES MAIN PAGE 1 AT 1 B FREE (2026-08-23).** The next main
      page-1 slice needs a carve or a promotion into the page-0 low region
      (10 B free, 2026-08-23) BEFORE it writes a byte — see the D-MISSOPFIX
      promotion of `basic/title.asm` for the shape. **Read the wall, never this
      line: `make basic-reloc` prints all four.**

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

- [x] ✅ **CLOSED — `CLEAR 200,` RAISED THE RIGHT ERROR AND LOST THE TRAP, *AND* IT
      WRITES.** 🔴 **THIS ITEM'S FIRST FILING WAS WRONG AND IS INVERTED RATHER
      THAN DELETED**: on 2026-08-23 D-CIRCMISS §7 filed it as *"zerobas is
      UNMEASURED… an APPARATUS gap"*. It is not. D-CLRTRAP
      ([`docs/spec-basic-clrtrap.md`](docs/spec-basic-clrtrap.md) §3) read the
      raw screen: zerobas prints **`Missing operand in 30`** — the right code at
      the right line — and **`ON ERROR GOTO` does not catch it**, so no fence
      printed and the probe scored the reading as nothing.
      **The divergence is the TRAP, not the error** (both references trap it).
      🎯 **MECHANISM, source-confirmed:** `clr_himem` is `call eval` /
      `ld (HIMEM),de` / fall into `clr_done` → `clear_vars`. D-MISSOPFIX made
      that `eval` **DEFER** ERR 24; `ex_clear` never tests `FPERR`, so it stores
      and falls through, `clear_vars` wipes the trap, and `exec_stmt` raises into
      a machine with no handler.
      ⚠️ **A SUCCESSFUL `CLEAR` KILLS THE TRAP ON ALL THREE MACHINES — that half
      is FAITHFUL** (row `t.after` unanimous, control `t.notrap` trapped `11 0`
      on all three). The ORDERING is the defect.
      🔴 **AND THE SILENT WRITE IS MEASURED, NOT ARGUED**
      (`scratchpad/clrtrap_himem.py`): `CLEAR 200,` moves HIMEM **`62336 -> 0`**
      here while both references read `SAME`, with `CLEAR 200,&H9000` → `$9000`
      on all three as the positive control. **D-MISSOP's silent-memory-write
      class at a 17th slot**, surviving D-MISSOPFIX because the deferral lands
      AFTER the store — `do_poke` tests `FPERR` before storing and `ex_clear`
      does not.
      ✅ **CLOSED 2026-08-23 (D-CLRFIX,
      [`docs/spec-basic-clrfix.md`](docs/spec-basic-clrfix.md)) AT ZERO BYTES**:
      `clr_himem`'s `call eval` became `call eval_int16_checked`, which IS
      `eval` + `check_expr_errors` + `get_int16_checked` — one 3-byte call
      replacing another. The raise now happens before `ld (HIMEM),de` and before
      `clear_vars`, so the trap survives and nothing is written.
      🔴 **AND THE ITEM UNDERSTATED THE CLASS BY A FACTOR OF FIVE.** The slot had
      no guard of ANY kind: `CLEAR 200,1/0` and `CLEAR 200,"x"` were untrapped
      too, and `CLEAR 200,70000` completed where both references answer ERR 6
      (no int16 coercion at all). Seven statements wrote HIMEM, not one.
      🔴 **AND THE "harmless today, record-only" CLAUSE ABOVE IS FALSE** — it was
      copied from a comment in `basic/clear.asm` that is itself false and is now
      inverted there. `basic/str-engine.asm` `heap_reset`, called from
      `clear_vars`, computes `FRETOP := min(HIMEM,TXTMAX)`. Row `q.commak`
      (`CLEAR ,200:A=1`) answered **`Out of memory`** because of it.

- [x] ✅ **CLOSED 2026-08-23 — `CLEAR ,200` WAS `Syntax error` ON BOTH
      REFERENCES AND COMPLETED SILENTLY HERE, AND THE FIX IS A CARVE**
      (D-CLRFIX, [`docs/spec-basic-clrfix.md`](docs/spec-basic-clrfix.md) §2).
      Filed 2026-08-23, D-CLRTRAP §3.3. 💰 **DELETING
      [`basic/clear.asm`](basic/clear.asm)'s `cp ',' / jr z,clr_himem` is −4 B**,
      and the leading comma then reaches the POOL argument's
      `eval_int16_checked`, whose own `check_expr_errors` raises the references'
      ERR 2 at `ex_clear`'s depth — before `POOLSIZE` is stored and before the
      wipe. **The right answer out of machinery that was already there.**
      🎯 The original lesson stands and got worse: I read `clr_himem`'s
      EXISTENCE as evidence about the LANGUAGE — and so had a characterization
      document. 🔴 **`docs/clearpool-vg8020-characterization.md` §2.4 / §2.8
      record REFERENCE readings for `CLEAR ,&HD000`, which is ERR 2 on both
      machines**: the pool reads "unchanged" because the statement NEVER RAN.
      Row `z.seq` runs §2.4's line verbatim and both references answer
      `UNTRAPPED Syntax error in 30`. Three vacuous rows, annotated in place, and
      `basic/str-engine.asm` `heap_reset` cited them for a benefit to a form the
      language does not have.

- [x] ✅ **CLOSED 2026-08-24 (D-HIMRANGE) — CLEAR's THREE-BAND RANGE CHECK
      SHIPPED, +52 B, 15 DIFF → 0.**
      ([`docs/spec-basic-himrange.md`](docs/spec-basic-himrange.md), funded by
      D-JRSLICE/2, main page 1 was 120 B free before this.) Bands, as MEASURED
      (both references agree on every scored row):
      * **ERR 5 below `$8000`**; **ERR 5 above `$F380` (62336)**;
      * **ERR 7 (`Out of memory`) for `$8000` ≤ v < floor**, where
        `floor = PRGEND + POOLSIZE + 680` (tracks program TEXT + string space);
      * **accepted** `floor` ≤ v ≤ `$F380`.
      🔴 **BOTH OF D-HIMDOM §5's OPEN GUESSES WERE REFUTED by the finer rows
      (the two-rules-coincide trap again):**
      * The upper edge is a **CONSTANT `$F380`**, NOT machine-specific: both
        machines accept up to 62336 and refuse 62337 despite boot HIMEMs of
        62336 (VG) vs 56951 (CF), and raising the ceiling back up works
        (`t.4to6`). So it reads a fixed top, not live HIMEM — zerobas needs no
        boot-time HIMEM init.
      * The floor is **program-text + string-space dependent, NOT variable-
        dependent** — `DIM A#(1000)` before the CLEAR does not move it (CLEAR
        wipes it), but a large `CLEAR n,` string space does.
      ⚠️ Fixtures retired as filed: `probes/basic/basic_probe_arrays.py`'s
      `scalar.str.chain.oom`, `scalar.input.chain.oom` (were `CLEAR 200,&H8050`)
      and `gc.bugB.phantom` (was `CLEAR 400,&H82C0`) — all three now use a legal
      ceiling + a room-filling DIM; the floor GUARANTEES ≥678 B headroom so no
      legal ceiling can squeeze the chain. Knives 4/4 (`himrange_knives.py`).

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

- [x] ✅ **THE `jp`->`jr` PEEPHOLE SEAM — FULLY BANKED 2026-08-24 (D-JRSLICE
      + D-JRSLICE2): main page 1 2 B -> 120 B, low region 10 B -> 45 B.** Filed 2026-08-24
      ([`docs/spec-carve-scout-2026-08.md`](docs/spec-carve-scout-2026-08.md)
      §3b, `scratchpad/peephole_jr.py`). **155 `jp`/`jp cc` sites whose target
      is already in `jr` range — 120 of those sites in page 1 — recovering one
      byte apiece.** It is a
      FLOOR: converting one shifts later bytes down, which only tightens other
      displacements, so all 155 convert together and more may come into range.
      🔴 **SAFEST CLASS IN THE TREE: `jp` and `jr` are flag- and control-flow-
      identical, and pasmo enforces the only constraint (range) — "it assembles"
      == "it is correct".** No flag-liveness, no position-independence, no
      differential needed for safety. PROVEN: one page-1 conversion moved the
      wall 2 B → 3 B (`jp nz,elg_draw`, reverted).
      ⚠️ The only judgment call is SPEED (`jr` 12/7 vs `jp` 10 cyc), so a HOT
      loop may keep its `jp` — a per-site call, never a correctness gate.
      🎯 **This is the funding route the range-check item needs** — the dup-span
      seam is 4 B, this is ≥120 B. Run it as its own slice with the full
      battery (cheap insurance) before spending against it.
      ✅ **BANKED: 51 of the 120 page-1 sites, page-1 free 2 B -> 53 B**
      (D-JRSLICE, [`docs/spec-basic-jrslice.md`](docs/spec-basic-jrslice.md)) —
      the sites whose target label is UNIQUE in source, converted mechanically
      and certified by the assembler (range) and the ABI gates (the layout
      shifted under the sub-ROM). 🔴 One of 52 was reverted: `pdfcb-body.inc` is
      a shared body, in range in main and OUT of range in sub — a shared
      `*-body.inc` has two answers and only the assembler knows the second.
      🔴 **REMAINDER, ~69 B measured 2026-08-24, NEEDS ADDRESS-PRECISE MAPPING:**
      the 68 page-1 sites
      whose target is a shared tail (`raise_error`, `str_eval_no`, …) are not
      uniquely locatable by (mnemonic,label) text, and pasmo 0.5.5 emits no
      listing to map address->source. That mapper is the follow-up. Plus 35
      low-region sites that fund the LOW wall, not page 1.
      ✅ **REMAINDER LANDED (D-JRSLICE2,
      [`docs/spec-basic-jrslice2.md`](docs/spec-basic-jrslice2.md)): 102 more
      sites via an address->source mapper** (`scratchpad/jr_mapper.py`,
      region+ordinal join, all 104 resolved uniquely). Page 1 53 B -> 120 B,
      low region 10 B -> 45 B (measured 2026-08-24). sub.rom moved this pass
      (shared/both-side files), so the ABI gates were load-bearing -- both green.
      🔴 **STANDING EXCLUSION: `pdfcb-body.inc` — a shared `*-body.inc` whose
      `jr` is in range in main and OUT in sub.** It bit BOTH jp->jr passes at the
      same line 53; the only 2 convertible page-1 bytes left, held off-limits to
      a main-address-only mapper. A future taker must range-check the sub build.
            🔴 **OPCODE-SWALLOW MULTI-ENTRY TRICK: measured 10 groups / ~40 B and
      DECLINED WITH NUMBERS** (D-JRSLICE §6) — it widens clobber contracts (the
      12 disk primitives would newly trash BC/HL, a semantic change) and trades
      the co-equal-docs clarity of the cleanest dispatch tables, for fewer bytes
      than `jp`->`jr` banks at zero cost. Measured-not-taken, like de-eviction.
      ⚠️ SIBLING FINDINGS, both small: the `SLA A` class the idea came from is
      ALREADY EXHAUSTED (0 left; 17 `add a,a` / 149 `xor a` / 13 `rlca` already
      applied), and `ld a,0`->`xor a` is 9 sites but flag-UNSAFE (needs
      liveness, ≤9 B) — `scratchpad/peephole_scan.py`.

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

- [x] ✅ **CLOSED 2026-08-24 (D-CIRCTC) — AND IT WAS A CLEAN DELETE, NOT A
      RESTRUCTURE: −5 B of sub page 1.**
      [`docs/spec-basic-circle-restructure.md`](docs/spec-basic-circle-restructure.md).
      Filed 2026-08-23 (D-CIRCMISS §6) as row `x.extra2`
      (`CIRCLE(50,50),20,5,0.1,6.2,1,` — a comma after a COMPLETE argument list):
      both references DRAW then raise ERR 2 (`2 5`), zerobas raised without
      drawing (`2 4`), and every filing (D-CIRCMISS §6, D-DUPSPAN §6.1, the seam
      classifier) called it a cross-ABI RESTRUCTURE needing a *"second flag"*.
      🔴 **THAT VERDICT WAS REASONED, NOT MEASURED.** The trailing comma is not a
      CIRCLE error the tenant must signal — it is a leftover STATEMENT token, and
      the resident's `cp_done` ALREADY ends in `jp exec_stmt` after the
      `GFX_OP=4` draw. Deleting `cpt_asp_done`'s bespoke `cp ',' / jp z,cpt_err2`
      (`sub/circleparse.asm`) makes the tenant report success (`GFX_RES`=0) and
      leave the cursor on the comma; the draw happens and `exec_stmt`'s
      `es_noentry` raises ERR 2 AFTER it — draw-then-raise, exactly like
      SWAP/PAINT/SPRITE. `GFX_DPTR` survives GFX_OP=4 (a RAM sysvar `gfx_circle_op`
      never touches), which is the fact the "cursor survives the tenant" test got
      wrong. **17 rows × 3 machines, 1 DIFF → 0** (`circtc_before.out` /
      `circtc_after.out`); `x.extra` (`...,6.2,,`, empty aspect slot) correctly
      STAYS `2 4` — `cpt_at_aspect`'s `cpt_err2` is left in place (raise-first).
      `sub.rom` moves, `basic-reloc.rom` + merged do NOT. Knives 2/2 EXACT
      (`circtc_knives.py`): K-CT1 moves all THREE aspect-present rows together
      (the tenant no longer distinguishes the comma — the refutation itself);
      K-CT2 proves the empty-slot case must raise-before-draw. 38/38 gates green.

- [ ] ⚠️ **`latch-check` IS THE ONE GATE WITH NO PREREQUISITES, AND A HAND-ROLLED
      BATTERY WILL TRIP IT.** Filed 2026-08-23, D-CIRCMISS §8.
      [`Makefile`](Makefile):2498 is `latch-check:` with an empty prerequisite
      list, so running it straight after `rm -rf build` makes it refuse (*"a
      probe booted against this machine would report the absence of the ROM as
      the absence of the FEATURE"*) and `make` exits 2. **The gate is right and
      the driver is wrong** — but every other acceptance target self-heals via
      its own `repack-machine` prerequisite, so this one is the only way to
      learn the rule. Either give it the prerequisite or say so where batteries
      get written; unpriced, and 16/16 once the ROMs exist.

- [x] ✅ **`ev_f_err`'s OTHER SEVEN JUMP SITES — CLOSED 2026-08-26, D-EVFERR, at
      ZERO BYTES.** [`docs/spec-basic-evferr.md`](docs/spec-basic-evferr.md),
      `scratchpad/evferr_probe.py`, **26 rows x 3 machines, references unanimous
      on all 26, 11 DIFF -> 1.** The filing said EIGHT jump sites; today's tree
      has **SEVEN**, and **two of those are not assembled** (`expr.asm:2032/2037`
      sit inside `IF !G8_RESIDENT` and `sysvars.inc:475` is `G8_RESIDENT equ 1`).
      🔴 **AND EVERY ONE OF THE FIVE ROWS FILED AS "AGREES" AGREED FOR A REASON
      OTHER THAN ITS SITE**, which is the whole finding: `A=VARPTR 5` /
      `A=VARPTR(5)` answer 2 through **`es_noentry`**'s leftover-token layer
      because `ev_f_err` leaves the cursor UNADVANCED; `A=EOF(0)` / `A=LOF(0)`
      answer 59 inside **`fch_check`**, one call before the site; `A=BASE 5` /
      `A=BASE(0)` answer 2 in the RESIDENT `ev_f_base` (`graphics.asm:1292`).
      The separators are one character away and **four of the five sites were
      live divergences wearing a green row**: `A=VARPTR` and `A=VARPTR(`
      COMPLETED SILENTLY (refs 2), and `OPEN"CRT:"FOR OUTPUT AS#1:A=EOF(1)` /
      `A=LOF(1)` COMPLETED SILENTLY where both references say **ERR 5**.
      💰 **ZERO BYTES — all four walls identical (45 / 107 / 2464 / 1622) and
      `basic-reloc.rom` moved `41b8c4ed` -> `6db7c1f0`**: every fix is a `jp`
      whose TARGET changed, the byte-neutral cure `vptr_close` had carried in
      its own comment since the arrays slice. The ~6 B price and the page-1
      carve this item was blocked on were answers to the wrong question.
      🎯 **`ev_f_err` NOW HAS ZERO INCOMING JUMPS** — it is reached only by
      fall-through from `ev_f_defer`, and the three labels that replaced it each
      say ONE thing: `ev_f_missop` (24, a factor was required), `ev_f_empty`
      (2, malformed expression), `ev_f_ifc` (5, the value is out of domain).
      🔴 **AND THIS ITEM'S OWN JUSTIFICATION HAD ROTTED TOO**: *"BASE is
      descoped and carries its own inline `ERRMARK` body"* has been false since
      graphics slice G8 — right conclusion, dead reasoning.
      ✅ **AND THE LAST DIFF CLOSED TOO, +8 B** (main page 1 **107 → 99**, read
      from clean): `A=VARPTR(B` with B unset was ERR 5 where both references say
      2, an ORDERING divergence — `vptr_unset` now runs the closing-`)` check
      before deferring its domain error. **30 rows × 3 machines, 0 DIFF.**
      🎯 **THE RULE IS NARROWER THAN "SYNTAX OUTRANKS DOMAIN", AND ONE ROW SAID
      SO**: `DIM Z(2):A=VARPTR(Z(9)` is ERR **9 on all three** — an array
      reference's subscripts are evaluated WHILE the form is parsed, a scalar is
      looked up only AFTER the `)`. That row also VINDICATED `vptr_none`'s
      untested justification (*"no `')'` check — it could only raise a masking
      second error"*) rather than falsifying it. A second class member came free:
      `A=VARPTR(B$`.
      🔬 **Knives 5 of 6 EXACT** (`scratchpad/evferr_knives.py`). K-EV3/K-EV4
      move ONE row each and neither touches `v.nopar`/`v.badarg` — the §2 finding
      measured. K-EV6's ROM is byte-identical to the retarget-only commit.
      🔴 **K-EV2 found a row the prediction missed**: `A$=(1+2` moves to 24 when
      `:835` is pointed at `ev_f_missop`, because `missing.asm`'s
      `els_tc_common` reads the DEFERRED code — so that row is a LIVE DETECTOR
      for the code chosen there, not a control. §6.1 of
      [`docs/spec-basic-missop.md`](docs/spec-basic-missop.md) named that path
      and the knife shows it would have sunk a DIFFERENT choice.

- [ ] ⚠️ **`CLEARPOOL=0` IS UNTESTED AND CANNOT BE ADDED TO
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

- [ ] ⚠️ **NO GATE READS THE BOOT BANNER, AND D-MISSOPFIX MOVED IT.** 2026-08-23.
      The 5 B fix was funded by PROMOTING `basic/title.asm` from page 1 into the
      low region. Every probe program in this tree opens with `CLS`, which wipes
      the startup header, so **not one of the 34 gates would notice if
      `show_title` stopped printing.** `scratchpad/missop_circle.py`'s `banner`
      row is a one-off check (run without `CLS`, assert the header text is on
      screen); it is NOT a gate. Making it one is cheap and unclaimed.

- [x] 💰 **`DEF FN` SHIPS (2026-08-23, D-DEFFNLAND,
      [`docs/spec-basic-deffnland.md`](docs/spec-basic-deffnland.md)).** The real
      tenant is written (428 B of sub page 0, main-ROM cost **zero**), the last
      28 B were carved, and 112 B were PROMOTED from page 1 into the low region
      — `make basic-reloc` builds the SHIPPING feature set, `make deffn-strict`
      is **0 of 69 divergent / 0 of 8 controls failed / 3 of 3 claims PASS**, and
      `make kwsweep` no longer prints a `MISSING=` line (SUPPORTED 29 → 30).
      🔴 **THE GAP FIGURE WAS NEVER THE WHOLE PRICE**: `over − lowfree` went
      NEGATIVE (−19 B) on a tree that still did not assemble, because the two
      regions are fungible only if you actually MOVE bytes across the boundary.
      The promotion is the step this residual never carried. Everything below is
      the history that got here; read the spec, not these numbers.
      💰 **DEF FN IS WRITTEN, MEASURED GREEN, AND 350 B TOO BIG — the FUNDING
      is the whole remaining job.** Filed 2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](docs/deffn-impl-2026-08-22.md); the code
      is the branch **`deffn-draft`** (`git diff main..deffn-draft`), which does
      NOT build — it stops at the `$8000` ceiling assert, which is the reading.
      **450 B of main ROM** (`__MEAS_PAGE1_END` = `$818C`, page-0 low unmoved)
      against **100 B free (2026-08-22, at `b1a01be`)**. `make basic-reloc`
      prints all four walls — read them, never quote this line.
      `make deffn-acceptance` on a G6/G7/G8-off scaffold:
      **0 of 69 subject rows divergent, 0 of 8 controls failed, 3 of 3 claims
      PASS**. 🔴 **The 403 B in `scratchpad/dupspan_sweep.py` is NOT 403 B of
      supply** — the tool says out loud it cannot decide position-independence,
      and reading the groups by hand puts the safe subset near 200. The second
      source is evicting the PARSING (name resolve, list open, bind loop,
      `fn_slot`, all of `ex_deffn` — ~180 B, all page-0-tenant legal, no `eval`
      in any of it) into the sub page 0 that has 3 KB. ⚠️ **Both figures are
      estimates and both must be BUILT to be believed**, which is the whole
      lesson of this slice: 100 + 200 + 110 = 410 against 450, so a third source
      or a shave is needed and saying so now is cheaper than finding out later.
      📏 **RE-PRICED 2026-08-22 BY D-DUPSPAN2** (`b61d350` → this commit),
      [`docs/spec-basic-dupspan2.md`](docs/spec-basic-dupspan2.md): the carve
      was MEASURED with `tools/dupspan_indep.py` instead of read by eye, and
      **the ~200 B does not exist** — 403 B nominal → **162 B**
      position-independent → **119 B** that also stays inside its own ROM
      region → **+122 B shipped**. Two groups the hand reading called
      "safe-looking" (`sav_ascii_flag` 20 B, `eostr_lp` 13 B) run off their own
      end. 🔴 **AND THE SECOND SOURCE IS BIGGER WORK THAN FILED**: measured this
      session, NO page-0 tenant in this tree calls main page 1 by absolute
      address and there is no import mechanism for it (`sub/basic-resident-abi.inc`
      is generated for PAGE-1 tenants calling main's LOW region), so every main
      helper the parse uses — `var_name_key`, `deftbl_lookup`, `skip_spaces` —
      needs a sub-side clone. Free in bytes (sub page 0 has 3 KB) but it is work
      the "~46 B of tenant glue" estimate did not carry.
      📏 **AND THE EVICTION IS BUILT AND MEASURED, 2026-08-22 BY D-DEFFNEV**,
      [`docs/spec-basic-deffnev.md`](docs/spec-basic-deffnev.md), on branch
      `deffn-draft` (`3e3cb67`): `__MEAS_PAGE1_END` **`$8140` → `$80A4`**, i.e.
      **+148 B**, better than the filed ~110. `basic/deffn.asm` 419 → 263 B; the
      verb 450 → **294 B**.
      > 💰 **THE GAP IS 26 B (2026-08-22, after D-XREG): 294 B of verb against
      > 268 B free.** It was 350 B when the verb was written, 72 B after the
      > eviction was built, and 26 B once the cross-region aliases landed. Both
      > originally filed figures were wrong and they MISSED IN OPPOSITE
      > DIRECTIONS WITHOUT CANCELLING. **Run `make basic-reloc` and
      > `python3 scratchpad/deffn_measure_over.py`; never quote these numbers.**
      🔴 **AND THE DUP-SPAN FAMILY IS SPENT**, measured with a denominator:
      `scratchpad/nearspan_sweep.py` finds 148 pairs of spans differing in
      exactly ONE byte and **0 B usable** at the cheap end (not one has its
      difference as the FIRST instruction's immediate with both spans
      position-independent), ~6 B under a register-parameterised collapse. The
      remaining sources are `ex_deffn`'s own eviction (~10–17 B),
      `tools/clone_scout.py`'s ~96 B of genuine near-clone refactors, and ~5 B
      from passing the servicer's answer in `E`.
      🔴 **THE TENANT IS A SIZING STUB — the verb does NOT work on that branch**
      and `deffn-acceptance` was not run. The parse itself (name resolve, the two
      lists, `fn_slot`, both directions of ERR 13, the `$FFFF` result slot) plus
      sub-side `var_name_key` / `deftbl_lookup` clones is the next slice's job,
      and it is FREE in main-ROM bytes.
      🔴 **REFUTED, not deferred: the filed ~21 B `FN_WANT0` shave** of
      `ev_fn`/`str_ev_fn` is worth **1 B** — the two entries differ in their EXIT
      and that is not shareable. **And per-file eviction is refuted as a third
      source**: six candidate files, 417–606 B each, all NOT page-0-evictable
      (most statements reach `eval`, and `eval` bottoms out in the float pack).
      The remaining named sources are the 43 B cross-region carve, `ex_deffn`'s
      own eviction (~10–17 B) and `tools/clone_scout.py`'s ~96 B of near-clone
      refactors, which are a DIFFERENT class from dup-span (shared helpers, not
      `equ` aliases) and entirely unspent.

- [x] ✅ **CLOSED 2026-08-22 by D-XREG** ([`docs/spec-basic-xreg.md`](docs/spec-basic-xreg.md)):
      **+46 B**, 10 aliases, and 🎯 **THE GATE IS NOT BLIND** — K-XR1 aliases the
      one label the pre-flight calls FATAL (`affn_found`) and
      `check_tenant_closure.py` reddens naming it, because it resolves every
      callee's ADDRESS out of the sym file, where an `equ` and a `label:` are
      indistinguishable by construction. D-PINDATA's rule is about which
      references count as EDGES on the way IN, not about how a target is
      resolved once it is one. 🔴 **And draft 1 of that knife went red for the
      WRONG REASON and taught nothing**: pasmo refused the `jr` range before the
      gate ever ran. ~~Original entry:~~
      💰 **43 B of cross-region dup-span carve, and the gate that would clear it
      may be blind to the question.** Filed 2026-08-22 by D-DUPSPAN2,
      [`docs/spec-basic-dupspan2.md`](docs/spec-basic-dupspan2.md) §6. Eleven
      aliases are position-independent but cross the low ↔ page-1 boundary
      (`exps_print` 12 B, `vsf_wb_int` 7, `elas_err`/`exf_syn` 8, and seven
      smaller). Each needs a reachability proof — is the label reached from a
      tenant of the OPPOSITE kind, for which the target page is switched out? —
      and `check_tenant_closure.py` filters `equ` names as VALUES rather than
      LOCATIONS (D-PINDATA's own rule), so it may not follow an alias across the
      boundary at all. 🎯 **Test the gate on a deliberately-bad cross-region
      alias FIRST: that answer is worth more than the 43 B.**

- [x] ✅ **CLOSED 2026-08-23 by D-DEFFNKNIFE — `make switch-build-check` SHIPS,
      and it was RED ON TWO SWITCHES, one of them `G8_RESIDENT` AGAIN.**
      [`docs/spec-basic-deffnknife.md`](docs/spec-basic-deffnknife.md) §7.
      `tools/check_switch_builds.py` assembles the main image with each of
      `G6/G7/G8_RESIDENT`, `I1_RESIDENT`, `TRAPS_T3`, `TRAPS_T4` off in turn and
      asks ONLY that it BUILDS. First run: `G7_RESIDENT` died on `gfx_syntax`
      (defined in G7's block, used by G8's `LET VDP(0)=` refusal over in
      `interp.asm`) and `G8_RESIDENT` on `g8_open_paren` (defined in G8's block,
      called by G7's `spr_parse_index`). Fixing those revealed a THIRD:
      `spr_tenant`, defined in G7's block and called by G8's `g8_run`.
      🔴 **THE CLASS IS WIDER THAN ALIASES** — not one of the three is an `equ`;
      the real shape is *any* symbol defined inside one feature's `IF` and used
      from another's, and the sprite/VDP pair is riddled with it because the two
      share grammar. ⚠️ **AND EVERY DIAGNOSTIC NAMES A DIFFERENT FILE AND A
      DIFFERENT FEATURE FROM ITS CAUSE**, which is exactly why this had to be a
      standing gate rather than a thing re-derived mid-slice. 💰 All three fixes
      cost the shipping build **ZERO**, and the proof is the hash: clean rebuild
      after them is `7942cc20` / `34bb8554` / `031184d9`, byte-identical.
      🔴 **AND THE GATE'S FIRST GREEN RUN BROKE THE NEXT GATE**: it rewrites
      `basic/sysvars.inc` and restores it byte-identical, but the mtime bump made
      `make -q` call the shipping ROM STALE and `latch-check` refused with
      *"APPARATUS FAILURE -- NOTHING WAS MEASURED"*. Fixed with `os.utime()`
      after the byte-identity assert — the deliberate INVERSE of the knife rule,
      and documented as such at the site. Below is the original filing.
      ~~AN `equ` ALIAS TO A CONDITIONALLY-ASSEMBLED SYMBOL SILENTLY BREAKS
      THE BUILD SWITCH, AND NOTHING IN THIS TREE CAN SEE IT.~~ Filed 2026-08-23
      by D-DEFFNLAND,
      [`docs/spec-basic-deffnland.md`](docs/spec-basic-deffnland.md) §3.3.
      D-DUPSPAN2's `loc_missing equ g8_missing` sat in always-assembled code and
      pointed at a symbol that exists only under `IF G8_RESIDENT`, so
      `G8_RESIDENT equ 0` had stopped building — with an undefined-symbol error
      three files from its cause — for as long as that carve had shipped. **No
      gate in this tree ever runs with a switch flipped**, `tools/dupspan_indep.py`
      decides POSITION-independence and REGION and has no notion of conditional
      assembly, and the eleven emulator batteries all measure the enabled build.
      ✅ **The instance is FIXED** (an `ELSE` arm, zero shipping bytes) and
      `scratchpad/alias_gate_sweep.py` says it was the ONLY one of the 107 label
      aliases in `basic/` that crosses a gate — **but the CLASS is open**: the
      sweep is a scratch script, not a gate, so the next alias can reintroduce
      it. ⚠️ And the general form is wider than aliases: **any build switch this
      tree owns is only as flippable as the last person who tried**. A cheap
      standing control would be a CI target that assembles with each of
      `G6/G7/G8_RESIDENT`, `I1_RESIDENT`, `TRAPS_T3`, `TRAPS_T4` turned off in
      turn and requires only that it BUILDS. ✅ **THAT TARGET IS
      `make switch-build-check`, and it found three more instances on its first
      run — see the header of this item.**
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
- [ ] ⚠️ **Main page 1 is 2 B free and the low region 17 B, at
      `031184d9`/`34bb8554` (2026-08-23).** Filed by D-DEFFNLAND. The next slice
      that adds a byte to page 1 has to carve one first or promote again;
      `scratchpad/region_sizes.py` prints per-include sizes split by region,
      which is how `poke.asm`+`sound.asm` were picked. **Run `make basic-reloc`
      — it prints all four walls; never quote this line.**
- [ ] ⚠️ **`DEF FN` has NO KNIVES, and now it has a shipping ROM to cut
      against.** Filed 2026-08-23 by D-DEFFNLAND,
      [`docs/spec-basic-deffnland.md`](docs/spec-basic-deffnland.md) §7. Four
      obvious sites, three of them defects this arc actually found: `fn_slot`'s
      `E`, `fn_leave`'s `DE`, PRINT's item classification, and the servicer's
      `push de`/`pop de` around the tenant bounce (§3.2 — its knife is deleting
      those two bytes and watching `o.defint` go red). 🔴 **And the ceiling
      compare of §3.1 needs one too**: a knife that restores `cp low
      FN_PAREA_END` must redden `o.p3`, and a knife that widens `FN_AREA` by one
      slot must redden `o.p10` — the second is what would have caught the wrap
      the first version of that test also got wrong.
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

- [ ] ⚠️ **A wall figure hardcoded inside a GATE is unpoliced by design.** Filed
      2026-08-22 by D-DUPSPAN2, §5.2 — `tools/gen_resident_abi.py`'s
      `LOW_CEILING = 0x3FE5` under a comment naming `__MEAS_LOW_END`, stale by
      65 B; fixed in that commit by reading the label. The CLASS is open:
      `make wall-assertion-check` scopes itself to TODO.md's `- [ ]` items, so
      no gate reads a free-space or region-boundary figure baked into
      `tools/`, `probes/` or a source `equ`. A sweep for the class is owed.

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

- [ ] ⚠️ **`DEF FN`: a STRING formal's shadow slot is not a GC root.** Filed
      2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](docs/deffn-impl-2026-08-22.md) §8. The
      slot holds a `[len][ptr]` descriptor and `strheap_gc`'s walk enumerates
      the variable chain and the temp-descriptor stack, not this area. No
      measured row provokes a collection inside an FN call (all three string
      rows concatenate into a temp), so this is a hole in the ROW SET as much as
      in the code — the fix is either a `sg_walk_fnframe` or a snapshot at bind
      time, and the ROW that would catch it does not exist yet.

- [x] ✅ **CLOSED 2026-08-24 (D-PAINT4) — SAME DELETE-AND-DELEGATE AS SWAP, −8 B
      MAIN PAGE-1 CARVE (91 → 99 B free).**
      [`docs/spec-basic-paint4.md`](docs/spec-basic-paint4.md). The second verb
      from the generic error-layer seam. `PAINT(x,y),C,B,<trailing>` FILLS then
      raises ERR 2 on both references; zerobas raised ERR 2 BEFORE the fill via a
      bespoke `ep_syntax` check above `ep_draw`. Deleting that
      `call skip_spaces / cp ',' / jp z,ep_syntax` lets a complete arg list fill
      and `jp exec_stmt`; the boundary guard (`es_noentry`) rejects the leftover
      after the fill, matching the reference.
      🔴 **THE FILED "not obviously cheap … move below the tenant call" WAS AN
      UNRUN ASSUMPTION**: the check already sat above `ep_draw`, which already
      guards the cursor (`push hl`/tenant/`pop hl`) and ends in `jp exec_stmt`, so
      it was a DELETE, not a move.
      📏 8 rows × 3 machines, references unanimous, **3 DIFF → 0** (before
      `paint4_before3.out`, after `paint4_after.out`): `pa.4comma`/`pa.4arg`/
      `pa.4colon` `2 4` → `2 9` (now filled before the raise, `POINT`=9). Knives
      2/2 EXACT (`paint4_knives.py`); K-PA1's revert reproduced the pre-fix ROM
      hash exactly.
      🎯 **ONLY THE AFTER-COMPLETE-ARGS SITE MOVED.** PAINT's other two bespoke
      error sites stay: `:748` (doubled comma `PAINT(x,y),C,,`, `pa.ccomma`) and
      the dangling-border ERR 24 (`pa.3comma`) both raise BEFORE any fill and
      AGREE on both references — the per-site oracle check is what separated them.
      ⚠️ TIMING WAS THE APPARATUS: a PAINT flood is slow in emulated time; a first
      pass at `step=7` starved the fill (every reference row `<NO OUTPUT>`), and a
      bounded 10×10 box + the proven `step=90` fixed it.

- [x] ✅ **CLOSED 2026-08-24 (D-SWAP3) — AND IT WAS A GENERIC MECHANISM, NOT A
      PER-VERB PATCH: `SWAP`'s BESPOKE THIRD-OPERAND CHECK DELETED, −23 B MAIN
      PAGE-1 CARVE (68 → 91 B free).**
      [`docs/spec-basic-swap3.md`](docs/spec-basic-swap3.md). The filed fix
      (`jp sw_illegal` → `jp pl_syntax`, 0 B) was measured to WORK (per-verb
      knives 3/3 EXACT) but it was the wrong layer and it missed a second
      divergence. The user asked whether an extra operand is a generic mechanism;
      it is. `exec_stmt`'s statement-boundary guard (`basic/interp.asm`
      `es_noentry`, `jp stmt_error`) already rejects any leftover token after a
      statement. Deleting SWAP's own trailing-token block lets SWAP consume `A,B`,
      EXCHANGE them, `jp exec_stmt`, and the generic guard reject `,C`/`,` —
      ERR 2, trappable, first-error-wins, **after the swap**.
      🎯 **That closes TWO divergences the 0 B patch left open**: (1) the error
      code (`SWAP A,B,C` on a defined B: ERR 5 → ERR 2), and (2) the SIDE EFFECT
      — the references EXCHANGE A↔B and THEN raise (`s.ok3` `2 2` / `s.ok3b`
      `2 1`; the trailing comma too, `s.tc.va`/`s.tc.vb`). zerobas raised before
      the exchange and left A,B untouched; now it matches.
      📏 **21 rows × 3 machines, references unanimous, 4 DIFF → 0**
      (`scratchpad/swap3_probe.py`, before `swap3_probe.out` / after
      `swap3_after2.out`). Type mismatch still outranks the boundary (`s.mm3`
      ERR 13, A% unchanged) — the `sw_types` type check runs before the exchange,
      unchanged by the carve. **Knives 3/3 EXACT** (`swap3_knives.py`): K-SW1
      proves the ERR-5 rows are `sw_absent`, K-SW2/K-SW3 that each operand is
      written by the exchange before the boundary.
      🔴 **§4.5 WAS A CASE THAT AGREED FOR THE WRONG REASON**, NARROWED not
      deleted: its `SWAP A,B,C → Illegal function call` fixture left B undefined,
      so it measured the second-operand rule, and its own `SWAP A,B,` row was
      ERR 2 because it ran with the variables in scope — the table was
      inconsistent about state. `docs/missing-vg8020-characterization.md` §4.5
      now names each reject row's operand-2 state.

- [ ] 💰 **THE GENERIC ERROR-LAYER SEAM: per-verb error checks that duplicate a
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
        🟢 **THREE MEMBERS SHIPPED 2026-08-26**: `ev_f_err`'s seven sites
        (D-EVFERR, 0 B), `PLAY`'s missing operand (D-PLAYOP, +2 B) and
        **`PRINT USING`, which was a −6 B CARVE and 13 DIFF → 0**
        ([`docs/spec-basic-pusing.md`](docs/spec-basic-pusing.md)). What is left
        of this half is `MID$(A$,2)=`, `SCREEN2:DRAW`, and KEY's absent form.
        🎯 **D-PUSING is the one to read before pricing the rest**: the filed
        item named TWO rows and the verb had **THIRTEEN**, because the
        references distinguish FIVE cases where zerobas had two — and the rows
        that found that were the ones added to keep the fix NARROW. 🟢 **THE `ev_f_err` SEVEN-SITES MEMBER IS SHIPPED**
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

- [ ] 🔴 **zerobas does NOT implement the `PLAY(n)` FUNCTION (background-queue
      status).** Found 2026-08-24 by the seam classifier
      (`scratchpad/seam_classify.py`). `P=PLAY(0)` returns **-1** (voice 0
      playing) / **0** (idle) on both the VG-8020 and the CF-3300; on zerobas
      every `PLAY(0)` read raised **`Missing operand`** — the function form is
      unparsed. Separate from the `PLAY` STATEMENT surface. Unpriced; needs its
      own probe (is `PLAY(n)` in the kwsweep denominator? it is a one-token
      function like `USR`). A real MSX1 BASIC function gap, not apparatus.

- [x] ✅ **CLOSED 2026-08-26, D-PLAYOP, +2 B** —
      [`docs/spec-basic-playop.md`](docs/spec-basic-playop.md),
      `scratchpad/playop_probe.py`, **11 rows x 3 machines, references unanimous
      on all 11, 4 DIFF → 0**, 4/4 knives EXACT, main page 1 **85 → 83 B**.
      Filed 2026-08-22 by D-DUPSPAN §6.3.
      🎯 **THE FILING WAS RIGHT ON EVERY POINT — THE FIRST ONE IN THIS RUN THAT
      SURVIVED ITS OWN RE-RUN INTACT**, including the point it explicitly
      refused to guess: *"the fourth (a 4th voice string) is UNMEASURED — do not
      assume it into either half"* measured **2 on both references**, already
      correct. That sentence is why the site was cheap to check and impossible
      to get wrong by inheritance.
      🔴 **BUT IT COUNTED INSTRUCTIONS, AND `pl_voice` IS A LOOP.**
      `basic/play.asm:74` is `jr pl_voice`, so the three entry-side tests are
      re-entered after EVERY comma and each has TWO entry conditions — four
      sites are **seven rows**. Both conditions answer the same way at every
      site, so the conclusion holds; that is a RESULT, not something an
      instruction count could say. D-ONLIST had the identical shape and came out
      the OTHER way. **Ask it per site, every time.**
      💰 **AND THE PRICE INVERTS D-PAINTMISS's REASONING.** That slice recorded
      *"a trampoline beats both alternatives because the sites are `jr`s: four
      `jp z,loc_missing` is +4 B against a 3 B `ep_missing`"*. With **two**
      sites it is +2 B against 3, so the trampoline loses. **The arithmetic
      inverts below four sites** — a function of the site count, not a rule.
      ⚠️ **NOT MEASURED: whether PLAY QUEUES BEFORE RAISING.** The seam found
      wrong ordering at SWAP and PAINT; this probe reads the error code only.

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

- [ ] ⚠️ **The rest of the byte-identical-span supply: 53 groups, 403 B
      NOMINAL, and nominal is not a price.** Filed 2026-08-22 by D-DUPSPAN.
      Re-run `python3 scratchpad/dupspan_sweep.py` — never quote this figure,
      it rots exactly like a wall. The two error-tail families are gone; what
      remains is 11–20 B pairs (`sav_ascii_flag`/`sav_cas_flag`,
      `esn_p2`/`esn_scan_lp`, `ems_print`/`exps_print`, `ai14_lp`/`ai6_lp`,
      `raf_zero_ok`/`cpow_x0_pos`, `eostr_lp`/`eokey_lp`,
      `sst_overflow`/`shxf_overflow`, `ex_on_strig`/`ex_on_key`,
      `asw_single`/`vsf_single`). 🔴 **Each needs BOTH checks D-DUPSPAN ran**:
      a fallthrough predecessor (via `check_tenant_closure._is_terminator`, not
      a regex — `ret nz` and `jp nc,x` are not terminators) and `jr` reach at
      every caller. **These are LOOP BODIES, not error tails**, so unlike the
      tails they are not obviously position-independent: a relative jump out of
      the span makes two identical spans un-collapsible.

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

- [ ] 🔴 **`castail-acceptance` VOIDS THE WHOLE BATTERY WHEN A CONTROL FAILS ON
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

- [x] ✅ **CLOSED 2026-08-22 (D-RUNLINE R1), 23 B — `RUN <lineno>` STARTS AT THE
      LINE.** [`docs/spec-basic-runline.md`](docs/spec-basic-runline.md). Page 1
      **31 → 8 B**; 💰 **the D-SEEDHOLE2 carve is what paid for it** — page 1
      read 11 B before that slice and this fix needs 23.
      🎯 **NO LINE-FINDER AND NO RUN LOOP WAS WRITTEN.** `RUN <lineno>` IS a bare
      RUN whose `CURLINE` starts elsewhere: `goto_resolve` is GOTO's own tail
      (find + ERR 8 + the `GOTOTGT` store) and `run_prog` sets `CURLINE` from ONE
      store. `GOTOTGT` is the carrier — its SECOND TENANT, safe because
      `run_prog` clears `GOTOFLAG` and `rp_goto` is its only reader.
      ⚠️ `RESTORE_LINE` deliberately does NOT move (RUN resets DATA to the
      program top); splitting the two stores is +3 B of the 23, and `n.rundata`
      is the only thing that says the split was right.
      Rows: `n.runline` GRADUATED, `n.runundef` + `n.rundata` NEW, all three
      agreeing on both references; namspc **99/99 → 102/102**, deferred 4 → 3.
      4/4 knives EXACT, twice. 🔴 **The knives caught a defect in the KNIFE
      RUNNER first** — draft 1 read `0/4` with all four ROMs provably moved,
      because it grepped for `MISS` and the probe prints `DIFF`. A parser that
      cannot see a divergence reports a broken tree as CLEAN (D-WALLDATE's
      draft-1 failure). **Calibrate on known positives** — spec §6.
      ⚠️ **R2 (direct mode) and R3 (the 0-byte swap) are NOT shipped** and have
      their own items below.

  <details><summary>the original filing, kept for the record</summary>

- [x] ⚠️ **`RUN <lineno>` IGNORES THE LINE NUMBER AND RESTARTS FROM THE TOP.**
      Filed 2026-08-21 by D-FNRUN §2.1, measured while converting the verb next
      to it — and filed precisely so that slice cannot be read as having fixed a
      form it merely learned to RECOGNISE.
      ```
      10 GOTO 40 : 20 PRINT"[B]" : 30 END : 40 RUN 20
      vg8020 -> B      cf3300 -> B      zb -> Syntax error
      10 PRINT"[B]" : 20 END           🟢 all three -> B   (n.runlinectl)
      ```
      Both references RESTART AT LINE 20 and print `[B]`. zerobas routes
      `LINENO_TOKEN` to `run_prog`, which starts from the top — so line 10's
      `GOTO 40` runs again and the statement re-enters itself.
      🔴 **AND THE FACE IS `Syntax error`, NOT THE SILENT LOOP THAT SHAPE WOULD
      PRODUCE**, which says the arm does something beyond ignoring the operand.
      ✅ **CONFIRMED BY EXPERIMENT, not left as a hunch (E-FR1, D-FNRUN §5).**
      `do_run`'s stored-program exit is a plain `jp run_prog` where every file
      arm beside it is `jp run_prog_top` (`ld sp,(SAVSTK)` first). Swapping it —
      a **0-BYTE** target change — moves the reading from `<Syntax error>` to
      **`<NO OUTPUT>`**, an honest silent restart loop. So the `Syntax error`
      IS D-RUNTAIL's nested-run corruption, at the ONE arm that slice did not
      convert: guarding one instance of a class again.
      ⚠️ **MEASURED AND NOT SHIPPED, deliberately.** Neither state matches the
      reference (`B`), so there is no measured reason to prefer a hang over a
      bogus error, and the same swap moves bare `RUN` INSIDE a program — a form
      no row drives. It belongs with the real fix (start execution AT the line),
      where a `10 PRINT"[R]" : 20 RUN` row can be built alongside it.
      ⚠️ **DIRECT MODE IS A SECOND SITE and is NOT this row**: typed at the
      prompt, `RUN 20` never reaches `do_run` at all (`dispatch_line`'s `is_cmd`
      takes it to `dl_run`, which ignores the number for its own reasons). Two
      sites, one rule, and only one of them has a row.
      💰 Not priced. Starting execution at an arbitrary line is a `run_prog`
      entry-point question (find the line, set CURLINE, enter the loop there),
      not a parser one — so the +17 B filename shape says nothing about it.
      Rows `n.runline` + `n.runlinectl` 🟢 are built and DEFERRED.

  </details>

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

- [x] ✅ **CLOSED 2026-08-21 (D-SEEDPROSE) — A COMMENT IN `sub/` OR `tools/`
      MADE A MAIN-BUILD SPAN INVISIBLE TO `make deadcode`; BOTH HALVES SHIPPED,
      +24 B PAGE-0 LOW (22 → 46 B).**
      [`docs/spec-deadcode-gate.md`](docs/spec-deadcode-gate.md) §10.
      **(a) the gate**: `external_names()` now reads the CODE COLUMN — `;` tails
      go for `.asm`/`.inc`, `#` comments AND docstrings go for `.py` (tokenised,
      not regexed, so a `#` inside a string is not a comment), string literals
      STAY because a tool naming a symbol it looks up does so in one. Seeds
      **303 → 123**, findings **0** in both builds. A floored 7-vector
      `_selftest_code_column()` of BOTH senses runs on every invocation.
      Knives **6/6 EXACT**, and the pair that matters is K5/K6: the same planted
      dead span and the same mention text under `sub/`, differing by `; ` — the
      old scrape is blind to the comment form, the new one reports it, and both
      still honour the code form. `--blind` + the allowlist canary re-verified.
      **(b) the carve**, per-span and not on the strength of the hole that found
      it: `str_heap_alloc`+`sha_oom` (23 B) are glue for the string-heap tenant's
      op 0 (ALLOC) with no caller in either build's code column and no other
      issuer of op 0; `ex_mid_stmt`'s 1 B head is an `inc hl` past a `$FF` prefix
      that `ex_ff_stmt` already consumes, whose only caller was a unit test — and
      `tests/` is deliberately not a seed, so allowlisting it would have
      re-created by hand the seeding this gate refuses. The two labels are
      collapsed onto the surviving entry, keeping the widely-cited name.
      🔴 **THE CLASS HAD BEEN FILED TWICE, 15 DAYS APART** — see the
      2026-08-06 D-EDITVERB entry, also closed, which had already watched it fire
      with a number (`list_num`, seeds 285 → 286) and filed the drift rather than
      the blindness.
      ⚠️ **THE PREDICTION THAT (b) WOULD REPORT MORE THAN THREE SPANS WAS WRONG**:
      the code-column scrape drops **161** seeds and reports **exactly** those
      three. What it does NOT close is a SECOND, different seeding hole — see the
      new item below. Original filing:
      Filed 2026-08-21 by D-FNRUN §4, found because the gate declined to ask for
      6 B the slice had just killed.
      [`tools/check_dead_code.py`](tools/check_dead_code.py) seeds the MAIN build
      as `{init} | (labels named anywhere under sub/ or tools/)`, and
      `external_names()` scrapes every IDENTIFIER in those trees **including the
      ones inside comments**. Its docstring calls this *"deliberately coarse:
      over-seeding keeps a live routine alive, which is the safe direction"* —
      which is true about false negatives on LIVE code and says nothing about
      this:
      > **a main-build span is invisible to the gate for as long as its label's
      > name appears in PROSE anywhere under `sub/` or `tools/`.**
      🎯 **AND THE PROSE THAT HID THE FIRST ONE WAS THE COMMENT EXPLAINING ITS
      OWN REMOVAL FROM THE OTHER BUILD** (D-FNEXPR2's note in `sub/bload.asm`
      saying the `parse_close_run` head was dead there). Documenting a removal is
      what stopped the gate asking for the same removal in the main build.
      **FALSIFIED, NOT REASONED ABOUT:** mangling those three mentions drops the
      main seed count 304 → 303 and the span is reported at once.
      📏 **THE CLASS IS MEASURED, not estimated.** Over the whole main build:
      **254** labels seeded via `sub/`+`tools/`; **6** of those unreachable from
      `init`'s own closure; **2** named ONLY in comments. Mangling those two
      mentions reports **three dead spans, 24 B measured 2026-08-21**, all
      page-0 LOW:
      ```
      [main] str_heap_alloc  basic/str-engine.asm  0x281d  ~21 B
      [main] sha_oom         basic/str-engine.asm  0x2832   ~2 B
      [main] ex_mid_stmt     basic/str-engine.asm  0x2c09   ~1 B
      ```
      ⚠️ **MEASURED AND RESTORED, NOT DELETED.** The page-0 LOW wall read 22 B on
      2026-08-21, so 24 B is a real carve — and `str_heap_alloc` is not a name to
      delete on the strength of a hole found sideways during another slice. The
      string heap moved to a sub tenant, so a leftover main copy is PLAUSIBLE,
      which is not the same as proven; the deletion needs its own reading.
      💰 Two separable pieces: (a) the 24 B carve, needing a per-span check that
      each really has no main caller; (b) the GATE, where the honest fix is to
      scrape identifiers from the CODE COLUMN only (strip `;` comments in
      `.asm`/`.inc`) and let the resulting findings be worked rather than
      pre-suppressed. ⚠️ (b) will report more than these three — it must be run
      before it is trusted, and each new finding triaged, exactly as the
      allowlist's own rule demands. **[Both shipped 2026-08-21; the ⚠️ was wrong,
      (b) reports exactly these three.]**

- [x] ✅ **CLOSED 2026-08-22 (D-SEEDHOLE2), −20 B main page 1 (11 → 31 B free) —
      A NAME IS NOT A ROUTE.** [`docs/spec-deadcode-gate.md`](docs/spec-deadcode-gate.md)
      §11. The filed measurement below re-verified EXACTLY (4 spans, 16 B, all
      page 1) and was wrong in one direction only: **under**-counted. There are
      **17** sibling bounces, not ~15, and the carve is **five** spans / **20 B**
      — `read_sector` is dead too, hidden by a THIRD, different apparatus hole
      (now filed, §11.5). The gate half re-seeds main from the GENERATED
      `sub/basic-resident-abi.inc`: measured 65 main labels named in `sub/` code,
      **65 resolvable inside the sub build** (12 via the ABI, 53 sub-local),
      **0 escapes** — so the import list IS the surface, not a proxy for it, and
      that invariant ships as a standing control. Seeds 118 → 73, 0 findings.
      🎯 **THE MECHANISM IS AN EVICTION AND IT WILL RECUR**: moving a caller into
      the sub-ROM leaves its main-side shim standing, and the moved body's own
      `call` is then read as the reason to keep it — **the commit that orphans
      the span is the commit that hides it** (`d3885b3`, `0cbf495`). §10's lesson
      one turn out: there a COMMENT was a seed, here a real CALL is a seed for
      the WRONG BUILD.
      ⚠️ The "4 of ~15 sibling bounces" worry was not the hard part — they are
      **not a table**: no dispatch array, no index, and the header's only order
      claim is `jr` reach, which a carve only shortens.
      7/7 knives EXACT, run twice.

  <details><summary>the original filing, kept for the record</summary>

- [x] 💰 **A SECOND SEEDING HOLE, AND IT IS WORTH 16 B ON MAIN PAGE 1 (wall 11 B,
      2026-08-21).** Filed by D-SEEDPROSE §10.4, measured not estimated. The main
      seed scrape is a PROXY for *"what can reach main code from outside main?"*,
      and it is coarse in a way the code-column fix does not touch: a name
      referenced in `sub/` **code** seeds the main label of the same name **even
      when the sub reference resolves sub-locally**. Four labels sit there —
      `sub/fatprim.asm` calls `fat_read_fat_sector` / `fat_alloc_cluster` /
      `fat_write_fat_entry`, `sub/format.asm` defines its own `write_sector` —
      and each main label of that name is a 4 B `DISKOP_SEL_*` bounce in
      `basic/fat.asm` the sweep cannot reach from `init`. **Dropping those four
      names from the seed set reports 4 spans, 16 B, all PAGE 1** (measured
      2026-08-21 on `0598831`).
      💰 Not shipped, and the two halves are separable exactly as the comment
      hole's were. The GATE half is a redesign, not a strip: the true main-external
      surface is the generated `sub/basic-resident-abi.inc` (**12** symbols, none
      of them these four) plus whatever `tools/` looks up by name, and re-seeding
      from that has to answer what a tool's string-literal lookup means. The CARVE
      half needs the same per-span triage the 24 B got, and it is a harder claim:
      these are 4 of ~15 sibling bounces, so deleting part of a bounce table is
      not deleting an orphan. ⚠️ **`basic/format-body.inc` and
      `basic/randio-body.inc` both `call write_sector` — they are sub tenants, so
      the sweep is right that main's copy has no main caller, but check that
      before quoting the 16 B as recovered.** [Checked per body, and per BUILD:
      all three are in `sub/sub.asm`'s include closure and none in
      `basic/main.asm`'s.]

  </details>

- [x] ✅ **CLOSED 2026-08-22 (D-PROLOGUE), apparatus fix (7) —
      [`docs/spec-deadcode-gate.md`](docs/spec-deadcode-gate.md) §12.** A prologue
      that emits nothing confers no fallthrough, so a file's first label is no
      longer live by construction. Findings: **main 0** (its one candidate,
      `read_sector`, was carved by §11), **sub 1** — `fat_io_open` 4 B,
      ALLOWLISTED and now the gate's SECOND vacuity canary.
      🔴 **THE OBVIOUS GENERALISATION IS CATASTROPHIC AND THE ARITHMETIC SAID SO**:
      *"any empty span cannot fall through"* reports **1227 spans / 27727 B dead
      in a 22510 B ROM**. A bare label above another label is an ALTERNATE ENTRY
      POINT and its fallthrough IS the routine. Only `@prologue:` spans skip.
      ✅ Checked against a FLATTENED include tree first: of the 20 first labels
      whose flat predecessor "falls through", **all 20 predecessors are data or
      directives** (`org`, `db`, `dw`, `ENDIF`), so the removed edge is not a
      control path on either model.
      ⚠️ Fix (4)'s `IF SUB_BUILD` remedy DECLINED with a reason: byte-identical
      sharing is `basic/fatio-body.inc`'s stated design property, and 4 B of a
      page with **1624 B free (2026-08-22)** does not buy breaking it.
      5/5 knives EXACT, twice — **three of them SAFETY rows**, because the failure
      direction is under-seeding. 🔴 K-P5's first draft was wrong in the permissive
      direction, which is how an under-seeding fix ships unnoticed.

  <details><summary>the original filing, kept for the record</summary>

- [x] 🔴 **EVERY FILE'S FIRST LABEL IS UNCONDITIONALLY LIVE — THE PROLOGUE
      FALLTHROUGH (filed 2026-08-22 by D-SEEDHOLE2, §11.5).** Apparatus fix (2)
      gives each file an always-live PROLOGUE span so references made above its
      first label stay visible — and also a FALLTHROUGH edge from that prologue
      into the first label. **42 of 49 main files (53 of 66 sub) have a prologue
      that is comments only**, emitting no bytes, and a comment block cannot fall
      through into anything. So 42 main first labels can never be reported dead,
      whatever the seed set says. This is how `read_sector` hid through the
      §11.3 seed rebuild; it was carved anyway on an argument that does not
      depend on the hole (no code-column reference in main's closure, and
      `basic/list.asm` ends `jp print_string`).
      💰 **Measured 2026-08-22, dropping the edge for emitting-nothing
      prologues**: main +1 span (`read_sector`, since carved); **sub 2 spans /
      20 B** — `fat_io_open` (`basic/fatio-body.inc`, 4 B) and `fmt_menu_text`
      (16 B, ALREADY the allowlist's vacuity canary, so only **4 B is new**).
      ⚠️ **This is a change to the SPAN MODEL, and its failure direction is
      UNDER-seeding — reporting LIVE code as dead.** It needs its own knives and
      its own per-span triage; a wrong redesign here is how the gate stops being
      believed. Sub page 1 free was 1624 B on 2026-08-22, so this is apparatus
      value, not wall relief.

  </details>

- [ ] 💰 **A DATA-ONLY SPAN STILL CONFERS FALLTHROUGH ON WHATEVER FOLLOWS IT**
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

- [x] ✅ **CLOSED 2026-08-21 (D-FNRUN), −11 B main page 1 (50 → 39) —
      `RUN A$` RESTARTED THE PROGRAM FOREVER.**
      [`docs/spec-basic-fnrun.md`](docs/spec-basic-fnrun.md). `do_run` dispatches
      on end / `:` / `LINENO_TOKEN` and hands anything else to `fname_expr`, so
      `RUN A$` and `RUN A$+".DAT"` are `File not found` on both sides. Rows
      `n.runvar` and `n.runexpr` graduated and `n.runlinectl` 🟢 was added as a
      GATED control; `namspc-acceptance` 95/95 → **98/98**, deferred 5.
      💰 **THE FILED PRICE WAS EXACT: +17 B**, hand-counted against the
      D-FNEXPR2 shape before the build. The net is −11 because the fix killed
      `parse_close_run`'s 6 B head — `do_run` was its last caller.
      🔴 **AND THE DEAD-CODE GATE COULD NOT SEE THOSE 6 B, BECAUSE A COMMENT WAS
      SEEDING THEM** — see the new gate residual below; that is the more
      valuable half of this item and it is filed separately rather than buried
      here.
      ⚠️ **`RUN <lineno>` IS RECOGNISED, NOT IMPLEMENTED**, and rows
      `n.runline` / `n.runlinectl` 🟢 exist so this cannot be read otherwise —
      see its own open item below.
      *The original filing:*
      🔴 **`RUN A$` RESTARTS THE PROGRAM FOREVER, AND THE FILED REASON NOT TO
      FIX IT IS MEASURED FALSE.** Filed 2026-08-21 by D-FNEXPR2,
      [`docs/spec-basic-fnexpr2.md`](docs/spec-basic-fnexpr2.md) §1.2.
      ```
      10 PRINT"[R]" : 20 A$="FCZ.DAT" : 30 RUN A$ : 40 PRINT"[OK]"
      cf3300 -> File not found in 30      zb -> the program restarts, forever
      RUN"FCZ.DAT"  🟢 both sides -> File not found     (the literal control)
      ```
      `do_run` ([`basic/cload.asm:185`](basic/cload.asm:185)) reads any non-quote
      as a BARE RUN, so the argument is not refused — it is EATEN, and the
      statement re-enters the program from the top. That is a HANG, which is a
      stronger divergence than the "does not accept an expression" the residual
      it came from described.
      🎯 **AND THE BLOCKER NAMES AN OBSTACLE THAT IS NOT THERE.** `TODO.md` and
      [`docs/spec-basic-fnexpr.md`](docs/spec-basic-fnexpr.md) §2 both call this
      *"genuinely ambiguous with `RUN <lineno>`"* and priced it as a probable
      DECLINE. Rows `t.runnum` / `t.runvar` read the STORED LINE BYTES on all
      three machines and they are byte-identical on all three:
      ```
      1 RUN 30  ->  8a 20 0e 1e 00 00     RUN_TOKEN, ' ', $0E (LINENO_TOKEN) + 30
      1 RUN A$  ->  8a 20 41 24 00        RUN_TOKEN, ' ', "A$"
      ```
      The tokeniser ALREADY separates the two forms — `basic/tokenise.inc` arms
      line-number mode on `RUN_TOKEN` and emits `$0E` for that form and nothing
      else — so a parser that tests for `$0E` first is not guessing
      [[a-filed-blocker-can-name-the-wrong-obstacle]].
      💰 **PRICED, hand-counted against the D-FNEXPR2 shape: ~+17 B main page 1**
      — a three-way head (`or a` / `cp COLON` / `cp LINENO_TOKEN`, each `jr z` to
      one `jp run_prog`) at ~+11 B, plus `ld hl,(FN_RESUME)` at the disk and
      `CAS:` resumes at +3 each. **Main page 1 read 50 B on 2026-08-21**
      (`make basic-reloc`), so it is affordable and needs no carve. Row
      `n.runvar` is built, DEFERRED and waiting; its 🟢 literal control
      `n.runlit` is green on both sides today.
      ⚠️ Converting `do_run` also retires the resident `parse_close_run` HEAD:
      `do_run` is its last caller that still consumes a literal quote out of
      program text, so `check_dead_code.py` will ask for those 4 instructions
      back — the same finding it already made on the sub-ROM copy.

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

- [x] ✅ **`AUTO` / `RENUM` / `LLIST` — the STATEMENT half, CLOSED 2026-08-06 by
      D-EDITVERB**, [`docs/spec-basic-editverb.md`](docs/spec-basic-editverb.md),
      measured in
      [`docs/editverb-msx1-characterization.md`](docs/editverb-msx1-characterization.md),
      gated by `make editverb-acceptance` at **61/61 rows on three sides**.
      🔴 **THE ITEM SAID FOUR VERBS, AND BOTH OF ITS CLAUSES WERE WRONG.**
      `DELETE` has executed since 2026-08-02 (D-DELETE) — `basic/sysvars.inc`
      and the slice memory both said so and this index never followed, so the
      denominator was 3, not 4. And D-KWGAP4's *“`AUTO` is interactive and
      `LLIST` hangs an unplugged `LPTOUT`, so `SIDE_LOCK` refuses a reference”*
      is **true about a mechanism and answers the wrong question**: openMSX's
      `plug printerport logger` reports READY unconditionally so `LLIST` cannot
      block, and Ctrl-STOP is a KEY MATRIX combination (row 6 bit 1 + row 7
      bit 4) that `keymatrixdown` delivers and `BREAKX` sees. Both verbs are now
      measured on both references.
      Landed: three `stmt_table` rows, `ex_llist`/`ex_renum`/`ex_auto`, four new
      tenant ops, **262 B of main page 1** (356 → **94 B**) and 500 B of sub
      page 1; low **23 B untouched**. D-KWGAP4's *“does not fit”* was measured
      against a **6 B** wall and was two carves stale.
      🎯 **`RENUM` NEVER CHANGES A LINE'S LENGTH** — a number is a fixed 2-byte
      header field and a reference a fixed 3-byte `$0E,lo,hi` — so it is an
      in-place rewrite with no memmove, no relink and **no `vars_reset`**, which
      is exactly what R-RN17 measured: variables AND the `CONT` point survive a
      `RENUM` where `DELETE` clears both.
      🔴 **`Undefined line N in M` is a REPORT, not an error** — `ERR` stays 0
      and `ON ERROR` does not trap it — emitted once per REFERENCE (`1 ON 1
      GOTO 77,88` prints two, both `in 1`), so the page-1 tenant stops at each
      one and the resident head prints and re-enters.
      🔴 **The readout was blind to its own subject and the first version
      passed**: anchored on the trailing `LIST` it saw the LISTING ONLY, so every
      `Undefined line` message and AUTO's whole session including the `*` marker
      were outside the window. And a **batched MODAL verb measures the case
      before it** — batched, `aut-nocomma` read `0` on BOTH references and
      `aut-plain` read `<NO ECHO>`; alone it is `Illegal function call`
      everywhere. `--repeat` cannot catch that: openMSX is deterministic.
      Retires the `kwgd-renum` pin (ninth cohort to fire and be DELETED rather
      than updated; `lnblank`'s allowlist is EMPTY again).
- [x] ✅ **`LFILES` — the LAST of the printer surface, CLOSED 2026-08-06 by
      D-LFILES**, [`docs/spec-basic-lfiles.md`](docs/spec-basic-lfiles.md),
      measured in
      [`docs/lptverb-msx1-characterization.md`](docs/lptverb-msx1-characterization.md)
      §4 (R-LF1..R-LF6), gated by `make lptverb-acceptance` at **39/39 rows**, the
      `lfl-` battery included and its printed `NOT GATED` line gone with it.
      🎯 **THE CARVE WAS THE SLICE.** D-LPTVERB filed ≈42 B against 10 B; the item
      was funded by evicting the FILES directory walk + entry emit into the sub-ROM
      page-1 `dirverb_tenant` — the eviction Phase 2 listed and DROPPED because
      *"its emit loop interleaves CHPUT + main-resident `print_crlf`, a head/body
      fork"*. That reason is spent: a page-1 tenant keeps page 0 mapped, so CHPUT
      and LPTOUT are both reachable, and `print_crlf` is `pchar(13)+pchar(10)` over
      a sink that is CHPUT whenever `PRDEST=0`, which `exec_stmt` guarantees.
      **Page 1 7 → 194 B; low 3 B untouched.** 237 B out, 69 B of head back, 3 B of
      `stmt_table`, and a ~29 B `name_cmp` shim that died with its last caller.
      🔴 **AND ≈9 B OF THE FILED ≈42 WAS ALREADY WRONG**: `basic/kwtable.inc` has
      not been main-resident since the sub-ROM arc's wave 3, so a keyword entry
      costs **zero** main bytes and lands in sub page 0 instead.
      🔴 **A ROW ADDED TO KEEP THE FIX HONEST FOUND A DIVERGENCE IN A SHIPPED
      VERB.** R-LF4 is about `LFILES`, but the cheapest place for it is the walk
      `FILES` also runs — so `lfl-nonef` was written as a FORK WITH TWO NAMED
      DISPOSITIONS before the reading. The CF-3300 answers `File not found` to
      `FILES"NOSUCH.XXX"`; zerobas answered **nothing at all**. Recorded as
      **R-LF6** and fixed for 5 B, because ERR 53 already prints (D-MSGSUB hosts
      `em_file_notfound` and `err_msgtab[53]` is the 1-byte `err_subhosted`).
      🔴 **K3 SAYS THE NAIVE IMPLEMENTATION IS WORSE THAN THE SPEC PREDICTED.** A
      sink re-point does not put the screen layout on the printer — with `CSRX`
      frozen the wrap logic collapses to no separator and no line break at all
      (`TEST    .BINHI      .TXTPROG    .BIN…`), a layout that exists on neither
      device, because it reads a cursor that is not its own.
      Six knives CUT at exactly their predicted RED **and** GREEN sets, each run
      twice; K7 missed as **predicted in writing beforehand**.
      🔴 **AND IT FOUND D-LPTVERB'S OWN GRADUATION HAD NEVER REACHED THE CODE**:
      `lnrx-lprint`/`lnrx-lpos` were still in `INFORMATIONAL` while three documents
      said they had left it, so for a slice they agreed and gated nothing.
      `lnblank` **536 → 539** — +3, not +1, which is the proof.
      ⚠️ Carried out of it: **R-LS4 is measured but UNKNIFED** (spec-basic-lptverb
      §6.7.3 — the cut changes argument CONSUMPTION and returns garbage), and the
      three items in `docs/spec-basic-lfiles.md` §6.8. ✅ **ALL CLOSED 2026-08-07
      by D-DSKMSG** — see the `- [x]` entry below and
      [`docs/spec-basic-dskmsg.md`](docs/spec-basic-dskmsg.md).
- [x] ✅ **THE SUB-ROM WALLS HAVE NO GATED READOUT — CLOSED 2026-08-07 by
      D-SUBWALL**, [`docs/spec-subwall-readout.md`](docs/spec-subwall-readout.md).
      `sub/sub.asm` carries `__MEAS_SUB_P0_END`/`__MEAS_SUB_P1_END` and
      `tools/check_sub_walls.py` runs from `make basic-reloc` beside
      `check_reloc.py`, so **all four walls print on every build**. The labels emit
      nothing: **all four ROM hashes byte-identical**, which is the instrument's own
      control.
      🎯 **THE 17 WAS D-LPTVERB'S OWN COST, AND D-LPTVERB MEASURED IT.** Sub page 0
      went 3869 → **3852** at `b5f4135` for the `LPRINT`+`LPOS` entries in
      `basic/kwtable.inc` — a sub **page-0** tenant — and that slice's as-built table
      records *"+17 is exactly the 9 B LPRINT + 8 B LPOS entries"* two rows below
      *"sub sides unchanged ✅"*. The number was not mis-measured; **it was not
      measured at all** — the prediction was copied into the result column.
      🔴 **THE 3 IS A NUMBER NO TREE HAS EVER HAD.** All 436 commits since
      `sub/sub.asm` existed were built (424 succeeded): **`p1=1824` occurs at 0 of
      them.** A different page end, a different pad convention, a stale
      `sub/basic-resident-abi.inc` (four vintages tried), a stale `build/`, and
      2324−500 arithmetic are each TESTED and refuted. D-EDITVERB's true carve is
      **−503**, not −500.
      ✅ **THE DRIFT DOES NOT GO BACK**: 104 of the 112 recorded sub-wall sites
      reproduce to the byte — the review's 4054/3357, D-P0BASE's −44, D-EVLNO's −87,
      D-MSGSUB, D-MSGMIGRATE, D-DOTLINE, the whole JUDGE arc. **Exactly two slices**
      carry a wrong figure, and they are the last two before the one that noticed.
      🔴 Carried out of it: **K6 found a defect in this slice's own tool** (a
      negative "over-report" printed as a measurement sentence — fixed, re-knifed);
      **K5 relocated its own finding** (an overrun never reaches the wall check,
      `pad_rom.py` refuses the empty image first); **the knife runner reverted the
      Makefile wiring** and the resulting green read as a missed knife.
      🔴 **AND TWO OF D-SUBWALL'S OWN BASELINE ROWS WERE `grep`-ED, NOT MEASURED** —
      `preflight-check` is **181/86** not 180/85, the page-1 closure **582+41** not
      522+41, both at `0cbf495` as well. ⚠️ **The first write-up blamed the record and
      that was WRONG**: swept the same way, *every* recorded figure of both is CORRECT
      at its own commit (preflight 178/85 → 179/85 → 180/85 → **181/86 at D-LFILES**;
      closure 515 → 522 → **564 at D-EDITVERB** → **582 at D-LFILES**). Those two
      slices simply never recorded either gate — **a gap, not an error**, and the
      reading failure was mine: **do not populate a baseline table by `grep`. Run the
      gates.** Both already print on every `make basic-reloc`.
- [x] ✅ **THE THREE D-LFILES RESIDUALS — CLOSED 2026-08-07 by D-DSKMSG**,
      [`docs/spec-basic-dskmsg.md`](docs/spec-basic-dskmsg.md), measured in
      [`docs/dskmsg-msx1-characterization.md`](docs/dskmsg-msx1-characterization.md)
      (R-DK1/R-DK2) and
      [`docs/lptverb-msx1-characterization.md`](docs/lptverb-msx1-characterization.md)
      §3.4 + §4.2 (R-LS4's fourth value, R-LF7). All three were blocked on a
      **reference reading, not tooling**, and each reading changed the answer.
      Gated by `make lptverb-acceptance` at **44/44** (39 → +1 `lps-argover`,
      +4 `lfl-empty*`) and the new `make dskmsg-acceptance` at **3/3 + 1 printed
      characterization row**; `fat-error-acceptance` still 8/8 with its
      `kill-missing` pin MOVED in the same commit as the code.
      🎯 **R-LS4's KNIFE EXISTS, AND ITS OWN CLAIM HAD NO ROW.** The rule says
      "no domain check — not even for a negative or an **out-of-byte** value" and
      its evidence was `LPOS(1)/(255)/(-1)` — **255 is IN byte range**.
      `lps-argover` (`LPOS(300)`) reads `0` on both references. K-LS4a (argument
      as a selector with domain {0}) and K-LS4b (byte domain only) then CUT at
      exactly their predicted sets — and the point is the SURVIVORS: **3, 10 and
      14**, real columns, where D-LPTVERB's unsound K7 returned 195 and 243. The
      cut site is after `flt_int_result`, so it cannot change argument
      CONSUMPTION, which was K7's whole fault.
      🔴 **THE EMPTY DIRECTORY WAS A DIVERGENCE, NOT AN UNEXERCISED ARM.** The
      CF-3300 raises `File not found` for a bare `FILES` **and** a bare `LFILES`
      over a mounted, writable, empty volume; zerobas printed nothing. Fixed by
      dropping `tnt_files`'s `FILES_HASPAT / xor 1` seed — **−4 B of sub page 1**.
      Needed a second fixture (`make_test_dsk.py --empty`) and, because "the
      listing printed nothing" is what a DEAD disk prints, its own positive
      control on that image (`lfl-emptyctl` SAVEs and lists `CTL     .BAS`).
      🔴 **AND THE FILED "the fix is 0 B" WAS FALSE.** `fat_delete` returns
      `Cy=1` for *not found / mount / I-O error* alike, so `tnt_kill`'s
      deleted-any flag was 0 for all three: the jump-target swap would have turned
      a disk-offline `KILL` into a **trappable ERR 53** on no reading at all — the
      exact move the residual was filed to prevent. `tnt_kill` now mounts first
      and returns STATUS=2, as `tnt_files` already did. Real cost **+4 B main /
      +6 B sub**; page 1 194 → **190 B**, sub p1 1542 → **1540 B**, low **3 B**
      untouched. `disk.rom` hash unchanged, the other three moved.
      ⚠️ **K-KILL2 is a PREDICTED MISS and says so**: deleting that mount
      separation reddens nothing, because no row drives `KILL` at a broken volume.
      ⚠️ Two apparatus refusals paid for themselves — the knife runner refused a
      **failed build** twice (the naive cut site took `jr z,ev_ff_lof` out of
      range), and `omsx_preflight` refused a **stale ROM** after an out-of-band
      restore touched mtimes.
      🔴 **Seed prediction wrong for the third slice running**: main seeds
      286 → **287**, because this slice's own `sub/dirverb.asm` COMMENT names the
      main label `df_notfound`. Seeds are a function of the WORDS a slice writes
      under `sub/`+`tools/`, not of the code it adds.
- [x] ✅ **`NAME`'s missing-old-file message — R-DK2, CLOSED 2026-08-07 by
      D-DKNAME**, [`docs/spec-basic-dkname.md`](docs/spec-basic-dkname.md),
      measured in
      [`docs/dskmsg-msx1-characterization.md`](docs/dskmsg-msx1-characterization.md)
      §2. `dsk-namenone` moved from the printed characterization list into the
      gated set — `make dskmsg-acceptance` **5/5**, with the `NOT GATED:` line
      deleted with it (a list of exclusions holding a non-exclusion stops being
      read as a list of holes) — and `fat-error-acceptance`'s `name-missing` pin
      moved to `File not found` in the same commit as the code, its second
      reference-exact row of eight.
      🎯 **THE FILED ≈5 B WAS 4, AND THE FILED REASON WAS SHORT BY ONE LEVEL.**
      `nm_fail` was indeed a shared exit for the `fat_mount` failure and the
      `fat_find` miss, so the fix was an arm split (`nm_notfound`) and not the
      target swap — but the miss arm is **itself two dispositions**, because
      `fat_find`'s own contract is `Cy = 1 not found / error` (`ret c` on a
      `read_sector` failure mid-scan). So an I-O error during the
      root-directory walk now reads as `File not found` too: `KILL`'s residual
      one primitive over, accepted and named rather than hidden.
      **+4 B main page 1 (190 → 186 B), 0 B sub**; low **3 B** untouched.
      `disk.rom` **and `sub.rom`** both byte-identical — `NAME`'s tenant is the
      stamp only, so "did this need a tenant change?" is answered by a hash.
      🔴 **K-NAMECTL IS THE FINDING, AND IT IS BIGGER THAN THE ROW IT REDS.**
      With `tnt_name_stamp` re-reading the dir sector instead of writing it back
      — `NAME` reports success and renames nothing — `dsk-namenone` still reads
      `File not found` on **both** sides, `dsk-ctl` and `dsk-killhit` hold
      byte-for-byte, and `make fat-error-acceptance` scores **8/8 ALL PASS at
      exit 0** with its own PRECONDITION green. Two instruments reporting a clean
      run over a provably broken verb. Only the NEW control `dsk-namehit` reds
      (probe exit 2, the four rows below it printed `(not scored)`). ⇒ **one
      positive control per gated VERB**, not per battery
      ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).
      ⚠️ **K-NAME2 is a PREDICTED MISS and says so**, exactly as K-KILL2 was:
      re-pointing the mount arm at `df_notfound` moved **nothing**, both
      instruments, both rounds. Seed prediction held at **287** for the first
      time in four slices, and for the stated reason — nothing under `sub/` or
      `tools/` was touched.
- [x] ✅ **`KILL`/`NAME` at an unmounted volume — THE ROW EXISTS, CLOSED
      2026-08-07 by D-MOUNTROW**, in exactly the form D-DKNAME §3.4 sharpened it
      to: `fat-error-acceptance` gained `kill-nodisk` / `name-nodisk`, driven at
      an **EMPTY DRIVE** in a second boot and pinned to zerobas's own
      `load error` — **no reference reading, no ROM byte**. K-KILL2 **at its own
      filed site** (the tenant mount-separation deletion) now reds `kill-nodisk`
      and nothing else, so the predicted miss is a **cut**.
      ⚠️ **Two things the closure does NOT cover, and they stay open below**:
      what zerobas *prints* there (needs the reading, opens six verbs), and an
      **UNREADABLE** volume as distinct from an empty drive — the row keys say
      `nodisk` precisely so the narrower claim is the one written down.
      🔴 **And K-NAME2 AS FILED does not build**: `jr c,nm_fail` →
      `jr c,nm_notfound` orphans `nm_fail`, whose only reference it is, and
      `check_dead_code` refuses it — a knife aimed at the message gate refused by
      the dead-code gate. Re-sited at `nm_fail`'s body; the rule is now in
      `docs/dev-workflow.md` §Knives. Detail:
      [`docs/spec-fat-error-mount-row.md`](docs/spec-fat-error-mount-row.md).
      *Superseded filing, kept for the trail:* —
      D-DSKMSG's **K-KILL2** and D-DKNAME's **K-NAME2** are two written-down
      predicted misses that prove it: each re-points its verb's mount arm at
      `df_notfound` and reddens **nothing**. `do_kill`'s STATUS=2 arm and
      `do_name`'s `nm_fail` both keep `load error` there by design (the
      quarantined class), and an I-O error *inside* `fat_delete` — or inside
      `fat_find`'s root-directory scan — still reads as "nothing matched" /
      "not found"; separating either needs a status out of the primitive.
      🎯 **AND THE CHEAP HALF NEEDS NO REFERENCE READING** (D-DKNAME §3.4/§6.5).
      `fat-error-acceptance` is explicitly a **self-check against zerobas's own
      pinned wording**, not an oracle differential — so a row driving
      `KILL`/`NAME` at an **empty drive**, pinned to zerobas's own documented
      `load error`, would convert both knives into real cuts without measuring
      the CF-3300 at all. Changing what zerobas *prints* there is the expensive
      half: that needs a reading, and that reading opens the whole `load error`
      wording divergence for `LOAD`/`RUN`/`BLOAD`/`OPEN`/`APPEND`/`MERGE` — six
      verbs nothing has measured. Detail:
      [`docs/spec-basic-dskmsg.md`](docs/spec-basic-dskmsg.md) §4.2/§6.6 and
      [`docs/spec-basic-dkname.md`](docs/spec-basic-dkname.md) §3.4/§6.5/§6.7.
- [x] ✅ **`fat-error-acceptance`'s missing `NAME` control — CLOSED 2026-08-07 by
      D-FEVERB**,
      [`docs/spec-fat-error-verb-control.md`](docs/spec-fat-error-verb-control.md).
      A case may now name a **VERB CONTROL** that must succeed in the same run
      before the case is scored; if it fails, THAT case prints `NOT MEASURED` and
      the run exits **2**, while the others are still scored (its blast radius is
      its verb — a second battery-wide PRECONDITION was rejected as over-broad).
      `name-alive` = `NAME"A:PROG2.BAS" AS "REN2.BAS"` + `FILES"A:REN2.BAS"`, on
      **two instruments**: positive screen text, and the host parsing the
      machine's own image for `REN2    BAS` present / `PROG2   BAS` gone — the
      half a convincing screen cannot fool.
      🎯 **THE SAME KNIFE, BEFORE AND AFTER.** D-DKNAME's K-NAMECTL (`NAME`
      reports success, renames nothing) scored this battery **8/8 ALL PASS,
      exit 0**; it now scores **7/7 scored, 1 NOT MEASURED, exit 2**. K-FE2 is
      its green control — undo D-DKNAME's fix instead and the row goes red at
      exit **1**, *scored*, with `name-alive` still green. Two ways to break
      `NAME`, two different exit codes, which is the point.
      ⚠️ **1 OF 8 ROWS, AND THE GATE PRINTS THAT COUNT EVERY RUN** — see the next
      item. All four ROM hashes UNCHANGED (probe + docs only), so the emulator
      gates that can only re-drive the same machine were **not run**, stated
      rather than folded into "corpus green".
- [x] ✅ **`fat-error-acceptance`'s verb-success denominator CLOSES AT 8 of 8 —
      2026-08-07**,
      [`docs/spec-fat-error-verb-control.md`](docs/spec-fat-error-verb-control.md)
      §8. Every row's verb is now shown reaching a SUCCESS disposition in the same
      run; the gate prints the count and the four SCREEN-ONLY controls
      (`LOAD`/`RUN`/`BLOAD`/`OPEN` change no directory entry) derived from its own
      tables, so the number cannot rot silently.
      🎯 **EVERY CONTROL LINE WAS SCOUTED ON THE MACHINE FIRST, AND THE SCOUT
      REFUTED THE OBVIOUS DESIGN**: `MERGE` of the TOKENISED fixture raises
      `Syntax error` and merges nothing — MERGE wants an ASCII `SAVE",A"` file —
      so `merge-alive` does the round trip and asserts **both** lines, because
      merging INTO an existing program is the property that separates MERGE from
      LOAD. RAM is pre-poisoned where the evidence is a `PEEK` (batched = page-3
      RAM survives between cases).
      🔴 **THE KNIVES FOUND A BUG IN THE GATE, ON A PATH NO GREEN RUN CAN REACH.**
      Round 1 scored all three cuts as enormous CUTs — twenty rows "moved". They
      had not: the probe was raising `AttributeError` in the verb-control FAILURE
      branch (it formatted `dir_present.decode()` unconditionally, and four
      controls now carry `None`), printing a prefix and exiting 1. **A gate's
      failure path only ever runs under a knife**, so a traceback there is
      invisible to the whole corpus and surfaces as the most flattering possible
      reading. Fixed both ends: the formatter walks only the fields that exist,
      and the runner now REQUIRES the probe's own tally line in a knifed run —
      "refuse a short reading" applied to the knifed run, not only the baseline.
      Both are in [`docs/dev-workflow.md`](docs/dev-workflow.md) §Knives.
      3 knives, twice each, identical: **K-GB** (shared `fat_io_getbyte` → EOF)
      reds ALL SIX with both reference-exact rows still scored; **K-PL** and
      **K-MG** separate `load`/`run` and `merge` as verb-specific. Probe + doc
      only — all four ROM hashes unchanged.
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
- [x] ✅ **The tape twins of D-RUNTAIL are the same defect — CLOSED 2026-08-07 by
      D-CASTAIL.** `dl_cas_close` (`LOAD"CAS:x",R`) and `dr_is_cas`
      (`RUN"CAS:x"`) had **both** defects, not just A, and both are fixed for
      **+7 B**: `jp run_prog_top` at each site, and a CF-out contract on
      `do_tape_prog` consumed by `ret c` — whose producer is the **existing**
      `dpl_err`, so defect B's producer cost **0 B**. Gate
      `make castail-acceptance` **9/9 + 1 pinned divergence** at the time
      (**31/31 + 1 pin** since D-CASSEARCH and D-CASOPEN extended the same gate), three-sided
      (vg8020, cf3300, zb), 7 knives run twice.
      🔴 **The filed blocker was wrong on one half and understated on the other.**
      "`omsx_repl.run_cases` mounts a disk, not a `.cas`" is true of its
      *signature* and false of the *module* — the `prologue` seam already mounts
      tapes for `basic_probe_lnblank`, so **no library change was needed at
      all**. What was actually hard is that **a missing tape file is not an error
      on an MSX1**: the reference searches past the end of the tape and waits
      forever, so there is no tape twin of `run-miss`, and the only failure a
      reference reports and returns from is an operator **Ctrl-STOP**. Detail:
      [`docs/spec-basic-castail.md`](docs/spec-basic-castail.md),
      [`docs/castail-msx1-characterization.md`](docs/castail-msx1-characterization.md).
- [x] ✅ **zerobas printed NO tape-search progress line (`Found:` / `Skip :`) —
      CLOSED 2026-08-07 by D-CASSEARCH** for **57 B, all of it in SUB page 1**
      (1540 → 1483 B free; main low, main page 1 and sub page 0 all unmoved, and
      **three of the four ROM hashes hold** — only `sub.rom` moves).
      `basic/casmatch-body.inc` now emits the row at `com_match` / `com_miss`
      through `CHPUT` — page-0 BIOS, legal for a page-1 tenant, the
      `sub/title.asm` precedent — because `print_msg` at `$7687` is main page 1
      and the p1-closure rule forbids it. The scout confirmed that, so the
      "shim prints `Found:` on the way out" split this entry offered as the
      alternative was **not needed and not taken**. Gate `make
      castail-acceptance` **17/17 + 3 pinned divergences** at the time (**31/31
      + 1 pin** since D-CASOPEN closed two of them), three-sided, 4 knives run
      twice.
      🎯 **THE SITE WAS DECIDED BY A MEASUREMENT NOBODY HAD TAKEN, AND THIS ENTRY
      DID NOT KNOW TO ASK FOR IT.** It named `LOAD`/`RUN`/`CLOAD`, but
      `cas_open_match` has **three** callers: `MERGE"CAS:"` and `OPEN"CAS:" FOR
      INPUT` (`basic/files.asm`) share the same search engine, so a print sited
      there prints for them too. Measured: **all four verbs print the identical
      rows on both references** — so the shared engine is not merely the cheap
      site, it is the correct one. Had any one been silent, this siting would
      have closed one divergence by **opening two**, and no reading of the code
      could have said so. Detail:
      [`docs/spec-basic-cassearch.md`](docs/spec-basic-cassearch.md),
      [`docs/cassearch-msx1-characterization.md`](docs/cassearch-msx1-characterization.md).
- [x] ✅ **`OPEN"CAS:name" FOR INPUT` IGNORED THE NAME and opened the NEXT file on
      the tape — so it delivered the WRONG FILE'S BYTES. CLOSED 2026-08-07
      (D-CASOPEN) for 7 B in main page 1** (165 → 158 B free). Found by
      D-CASSEARCH's two-file-tape rows; nothing in the record had it. Both
      references **name-match on OPEN** — they step over `SK` and open `RT` — and
      read back `10 PRINT"ZQ9"`; zerobas opened `SK` and read back
      `10 PRINT"ZQ8"`. `basic/files.asm` `oo_dev_cas` now calls
      `cas_capture_name`; the search engine needed **no change at all**.
      🎯 **THE THREE MISSING READINGS WERE TAKEN FIRST, AND THEY MADE THE DEFECT
      NARROWER THAN IT WAS FILED.** The name was ALREADY parsed on the OPEN path
      (which is why `FOR OUTPUT` writes it into the `$EA` header correctly, and
      always did — measured off a decoded recording on all three sides); what was
      missing was the hand-off to the search. The compare is **case-sensitive**
      (`OPEN"CAS:rt"` does not find `RT`) and bare `OPEN"CAS:"` takes the next
      file — a **third face** of the divergence that the pinned row could not
      see, because that row asks a name which matches.
      🎯 **The entry deliberately carried NO byte count, and the scout is why
      that paid** ([[carve-scout-before-proposing]]): the fix's whole 7 B is the
      `CAS_WANT` → `TSV_NAME` copy the OUTPUT arm needs — the INPUT half is
      byte-**negative**.
      ✅ **The two pins are RECLASSIFIED, not re-pinned**: all three sides now
      agree, so `cas2-open` / `cas2-open:echo` join the SCORED set with a `ZQ9`
      control, and `castail-acceptance` reads **31/31 + 1 pin**. Detail:
      [`docs/spec-basic-casopen.md`](docs/spec-basic-casopen.md),
      [`docs/casopen-msx1-characterization.md`](docs/casopen-msx1-characterization.md).
- [x] 📌 **A KNIFE RUNNER READ A COMPLETE 32-ROW EXIT-2 REPORT AS TRUNCATED,
      BECAUSE THE TWO REPORT SHAPES ARE INDENTED DIFFERENTLY.** Found 2026-08-07
      by D-CASOPEN's K-CO1 round 1. `dev-workflow.md` §Knives already says *"the
      guard must know every shape the probe prints"* and D-RUNTAIL already
      enumerated the exit codes — and the runner still aborted, because the rule
      was applied to the *content* of the exit-2 report (`....` rows, no tally)
      and not to its *layout*: `basic_probe_castail.py` prints `ok `/`DIFF` rows
      at column 0 and `....` rows indented two spaces, so an `^`-anchored regex
      matches every green run and no knifed one.
      🔴 **AND THE SECOND HALF OF THE SAME FAULT IS WORSE, BECAUSE IT DOES NOT
      ABORT**: the two shapes also print different CONTENT per row (`ok  label
      'value'` vs `....  label  vg8020='..'  zb='..'`), so a runner diffing raw
      lines scores **every** row as moved — a spectacular false CUT. The fix is
      to compare the side under test's VALUE, not the line.
      ✅ **The runner-side rule is LANDED** in `docs/dev-workflow.md` §Knives:
      *parse rows into (label → the side-under-test's VALUE) and diff that; never
      diff report LINES.*
      ✅ **THE PROBE-SIDE HALF IS CLOSED 2026-08-07 by D-ROWSHAPE, for ZERO ROM
      bytes** — [`docs/spec-probe-rowshape.md`](docs/spec-probe-rowshape.md).
      All four walls (3 / 158 / 3843 / 1483) and all four ROM hashes came back
      byte-identical from clean; no `.asm` or `.inc` was touched.
      🎯 **"ONE ROW FORMAT" WAS DECLINED AS FILED, AND THE FILED QUESTION IS WHY.**
      The exit-2 report prints every side's value and `(not scored)` *because
      nothing was measured*; collapsing it into the agreed-value form deletes the
      information it exists to carry. What ships is one row **GRAMMAR** — a
      fixed-width tag at a constant column (I1), every side named on every row on
      every path (I2), and a `ROWS: n printed` terminator on every exit path (I3)
      — so a runner reads a stated COUNT instead of guessing a layout.
      📏 **THE DENOMINATOR WAS WALKED AND THE HAND-LIST WAS WRONG IN BOTH
      DIRECTIONS.** 175 probe `.py` files; 29 print a machine-parseable report
      row; **5** print rows on an exit-2 path AND another path — the only shape
      in which a runner meets two renderings of the same reading. Of the eight
      probes the residual guessed at, **four are not in the class at all**
      (`lnblank`, `diskbasic`, `lptverb`, `editverb` — `editverb` has exactly ONE
      row site), and the walk found **two it missed**, one of which is the green
      control.
      🟢 **THE REMEDY WAS ALREADY IN THE TREE, UNDER KNIVES.**
      `disk_probe_fat_error_disposition.py` already satisfied I1 and I2 on all
      five of its blocks, which is why D-FEVERB's and D-MOUNTROW's knives were
      caught by neither fault. Its **rows are not touched** by this slice — it
      gains only I3's terminator — so `rowshape-check` green is not the slice
      grading its own homework.
      🔴 **THE FIRST CUT OF THE GATE WENT BLIND TO ITS OWN SUBJECT BY FIXING IT**:
      the checker only recognised inline f-strings, so migrating `castail` to the
      shared formatter DROPPED it out of the contract (5 → 4) and a fully
      migrated tree would have scored `0 in contract`. Caught by watching the
      denominator move [[readout-blind-to-its-own-subject]].
      🔴 **A GATE THAT DELEGATES TO A SHARED MODULE INHERITS A BLIND SPOT EXACTLY
      THE WIDTH OF THAT MODULE.** K-RS1 (delete the tag pad *inside*
      `probe_report.row`) leaves `rowshape-check` GREEN by construction — the
      checker reads `TAG_W`, not the format string. The knife's predicted RED was
      **rewritten before it was run** to `unit-test`, and
      `tests/test_probe_report.py` is the grammar's own oracle. Two gates, two
      subjects; neither alone covers the claim.
      ✅ Runners no longer write the parser: `probe_report.parse()` ships, matches
      `side=<repr>` positively, and **raises** on a missing or disagreeing
      terminator. `docs/dev-workflow.md` §Knives now points at it.
      📊 7 knives × 2 rounds, **14/14 EXACT** (K-RS2/3/4 redden `castail` ONLY,
      K-RS7 reddens `fat_error` ONLY, K-RS5 exits **3** APPARATUS FAILURE).
      Corpus green; every predicted count hit on the nose — `unit-test` 58→**59**,
      `audit-citations` 727→**731**, `injector-check` 332→**335**,
      `preflight-check` 181/86/95/95/0 unchanged, `rowshape-check`
      **176 walked / 29 report-row / 5 in contract / 5 conform / 0 violations**.
      💰 **The other 25 gated multi-shape probes are PRICED AND DECLINED**: they
      print one shape *per exit path*, so a runner's baseline and its knifed run
      meet the same shapes and the fault needs two paths. Bringing them in would
      be 25 bespoke edits across ~19,000 lines (only 6 of 30 share a data model)
      plus a re-run of each one's emulator gate — see spec §10, and re-open it
      with evidence if a runner is ever actually caught by one.
- [x] ✅ **~~MAIN PAGE 1 HAS 2 B~~ — 69 B FREE SINCE 2026-08-19 (D-EVSPDUP).**
      `ev_sp` (basic/expr.asm) skips spaces and its ONLY exit is `ret nz`, taken
      with **A already holding the first non-space byte**. Every one of its **24**
      call sites in that file followed it with a redundant `ld a,(ix+0)` — 3 B
      each, **72 B**. Removed; page-1 free **3 B → 69 B**.
      🎯 **THIS WAS FOUND WHILE SCOUTING 5 B, AND IT CHANGES WHICH FILED SLICES
      ARE AFFORDABLE.** Several are DECLINED WITH NUMBERS against a wall that had
      2–5 B on it — `spec-basic-fldary.md` at 38 B, D-LVFIX's FIELD/LSET half at
      ~80 B, and others priced when the answer was "no room". ⚠️ **Those declines
      are now UNPRICED, not automatically live**: each was a claim about a design
      as well as a wall, and re-opening one means re-reading its own reasoning,
      not just the free-byte count.
      ✅ **THE WALK THIS ASKS FOR WAS DONE THE SAME DAY — D-REPRICE,
      [`docs/repricing-page1-2026-08-19.md`](docs/repricing-page1-2026-08-19.md)
      — AND IT UNBLOCKED NOTHING.** Two sweeps over all 63 open items (one keyed
      on decline vocabulary, one keyed on price+region so the roster is not a
      keyword artefact) found **exactly one** item whose page-1 price the wall now
      covers — `FIELD overflow` at ≈27 B — and it stays declined on two non-byte
      blockers its own document names. Everything else is a stale WALL reading, a
      CARVE that frees bytes, or still far over 64 B.
      🔴 **AND BOTH DECLINES NAMED IN THE PARAGRAPH ABOVE WERE ALREADY CLOSED
      WHEN IT WAS WRITTEN.** `spec-basic-fldary.md` SHIPPED 2026-08-08 (13/13,
      funded by a 57 B carve) and D-LVFIX's FIELD/LSET half is the same slice,
      marked SUPERSEDED in this very file — eleven days earlier, and closed by a
      CARVE, the same instrument. The paragraph stands as the correct *warning*;
      its two examples were stale on the day. ⚠️ **This is the wall figure too:
      69 B was the reading at `33720ae`; D-VPTRDOM spent 5 the same day and the
      wall is 64 B at `b51bbbb`.**
      ⚠️ **THE CONTRACT IS A REGISTER CONVENTION AND NO GATE READS ONE**, so it is
      written down at `ev_sp` itself: anything added there that can return by
      another route, or with A holding something else, breaks 24 sites silently.
      ✅ **AND THE 26 GREEN GATES WERE FALSIFIED BEFORE BEING BELIEVED.** K-VS1
      changed `ld a,(ix+0)` to `ld a,(ix+1)` — same length, wrong character in A —
      and **`unit-test` and `float-acceptance` both went RED**, so the gates do
      see this contract and the greens are evidence rather than silence. Green
      set: unit-test 59/59, basic-reloc, deadcode, float, string, logicops,
      error, missing, binfre, **graphics** (the 360-row one), array, arrdim,
      arylv, input, inputary, diskbasic 34/34, lvfix 20/20, cursor, error-trap,
      math, str-domain, forvar, nxlist, readvar, intarg, abort.
      🔴 **MY FIRST DRIVER DIED ON A TARGET THAT DOES NOT EXIST** (`arrays-`
      vs `array-acceptance`) and that is the good outcome: `make` exits 2 on an
      unknown target, and only because the driver checked the status directly did
      a typo become a hard stop instead of a silent pass — the exact failure
      `> file 2>&1` and a `set -e` driver exist to prevent.

- [x] ✅ **~~AN ITEM THAT STATES THE WALL INLINE GOES STALE SILENTLY~~ — GATED
      2026-08-19 (D-WALLDATE), `make wall-assertion-check`, 0 ROM bytes.**
      [`docs/spec-basic-walldate.md`](docs/spec-basic-walldate.md),
      [`tools/wall_assertion_check.py`](tools/wall_assertion_check.py). The rule
      is mechanical because the stale/not-stale question is not: **a free-space
      figure must carry a DATE or a COMMIT, and must not be in the present
      tense.** A dated reading then STANDS AS TAKEN and is never second-guessed.
      🔴 **DRAFT 1 CAUGHT 0 OF THE 4 DEFECTS IT WAS BUILT FOR, AND REPORTED
      CLEAN.** It looked for a date ANYWHERE in the item; every item names a
      slice or carries a date somewhere, so it exempted everything. **Calibrated
      against the pre-D-REPRICE `TODO.md` where all four were live** — draft 2
      (line-local, past tense allowed) caught 3/4, failing on the word `was`
      one line below the 14 B claim; draft 3 (date-or-commit only, present tense
      a separate finding) catches **4/4**.
      🎯 **A DATE ALONE IS NOT ENOUGH** — *"RE-PRICED 2026-08-09 … main page 1
      **is now 16 B**"* is dated and still read as current. PRESENT-TENSE is its
      own finding with its own remedy: **say WAS, not IS NOW**.
      🔴 **K-WA3 MISSED AND IS RECORDED, NOT TUNED AWAY.** The UNDATED half is
      weak: any date within one line exempts a figure, related or not. Radius
      chosen by measurement — 0 gives 4/4 but **6 false positives** on the clean
      tree, 1 gives 4/4 and **0**. PRESENT-TENSE is the strong half (K-WA2:
      flagged **despite** its date). ⚠️ **Read a clean run as evidence about
      present-tense claims and only weak evidence about undated ones.**
      📊 Fixed **10 figures across 5 open items** — including the surviving
      present-tense opening lines of three of the founding four, which had dated
      addenda but still greeted a skimming reader with *"IS NOW 14 B"*. Readings
      unchanged; only tense and dates.
      ⚠️ SCOPE, stated: open `- [ ]` items in `TODO.md` only. Dated slice docs
      under `docs/` are the house style and out of scope.

      **Filed 2026-08-19** by D-REPRICE Filed 2026-08-19 by D-REPRICE
      ([`docs/repricing-page1-2026-08-19.md`](docs/repricing-page1-2026-08-19.md)
      §4), which went looking for declines the new 64 B wall might fund and found
      this class instead. Four OPEN items assert a *current* free-space figure in
      prose, as fact, and every one is wrong:
      *"THE PAGE-1 WALL IS NOW **14 B**"* (editor/program management),
      *"main page 1 is now **16 B**"* (`FIELD overflow`),
      *"Main page 1 is down to **49 B**"* (`ex_let_arr_str`; ✅ that item is
      CLOSED 2026-08-20 by D-ARYOOS, whose fix cost 1 B of the LOW region and
      needed no page 1 at all — the wall it quoted was never its blocker, as the
      re-pricing itself concluded),
      *"**9 B** free low / **6 B** free page 1"* (slim the file-channel context)
      — against **5 B low / 64 B page 1** measured at `b51bbbb`.
      🎯 **THIS IS THE 160-DEAD-BYTES SHAPE, IN PROSE**: a figure that was a
      reading when written, copied nowhere, checked by nothing, and false from
      the next slice onward. `make basic-reloc` prints all four walls on every
      run; nothing compares them to a sentence in `TODO.md`.
      ⚠️ **AND THE ERROR LEANS THE DANGEROUS WAY.** Three of the four UNDERSTATE
      the wall, so each reads as *less* affordable than it is — a slice opening
      one and trusting the inline figure would decline work it can already fund.
      That is the D-EVSPDUP warning one level further down than it looked.
      💰 Worth a lint, and it is cheap and ROM-free: `make basic-reloc` already
      emits the four numbers, so a checker that greps `TODO.md`/`docs/` for a
      free-space assertion and diffs it against the live measurement is a
      report-parser plus a regex. ⚠️ The hard half is the GRAMMAR, not the
      compare — the four above are phrased four different ways, and a matcher
      that catches only the phrasings listed here has a hand-listed denominator
      ([[a-hand-listed-denominator-is-a-scope-claim]]). All four are addendum-ed
      in place rather than rewritten; the readings stand as taken.
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
- [x] ✅ **A KNIFE RUNNER'S "a failed build ABORTS" GUARD IS THE WRONG GUARD —
      CLOSED 2026-08-07**, and **the remedy I filed was DECLINED on a read of the
      record** ([[a-recommendation-in-the-record-is-still-a-claim]] — the filer
      was me, one commit earlier). `make` can exit **0 having rebuilt nothing**
      (GNU Make 3.81, one-second mtime granularity,
      [[make-mtime-race-skips-subrom]]), so the knife scores the **pre-cut** ROM
      and reads as a **MISS** — the reading that means "the tree cannot see
      this", which is a conclusion slices write down. D-FEVERB's K-FE1 scored CUT
      then MISS from the identical cut; only run-it-twice caught it.
      🔴 **THE FILED REMEDY — "make it shared (`probes/lib/`?) or the trap is
      permanent" — WAS WRONG ON THREE COUNTS, ALL OF THEM ALREADY IN THE TREE.**
      (1) The guard is **not missing**: `spec-basic-dotline.md` §7 derived it and
      `spec-basic-msgmigrate.md` §8 productionised it as a distinct
      **DID-NOT-HAPPEN** verdict — it was not carried into my runner, which is a
      RECALL failure, not an availability one. (2) Knife runners are
      **scratchpad by design** (`spec-probe-injjudge.md` §1.3, 0 swept files), so
      a shared module has no committed consumer. (3) A **preflight check for this
      exact class was built, knifed and REMOVED** as undetectable from mtimes
      alone ([[preflight-slice]]) — the one place it would have been automatic.
      ⇒ closed by writing the discipline where a runner author actually reads it:
      a new **"Knives — falsification runners"** section in
      [`docs/dev-workflow.md`](docs/dev-workflow.md), which carried **no** knife
      content at all despite four spec docs describing it.
      🎯 **AND TWO MEASUREMENTS CORRECTED A STANDING CLAIM.**
      `spec-basic-dotline.md` §7 says *"the repo's own standing rule is the whole
      fix — always `rm -rf build` first"*. **It is not.** A cut landing in a
      **comment** (the ordinary mis-siting, since cut strings carry their
      trailing comment) yields byte-identical ROMs **from clean** — measured —
      and scores as a MISS. `rm -rf build` fixes the *race*; only the hash
      separates "reddened nothing" from "never reached the artifact". And a clean
      rebuild costs **5.1 s** against 0.08 s incremental, so there was never a
      performance reason to skip it: do both.
      ⚠️ D-DKNAME's knives were re-run under the guard and all three verdicts
      stand — **K-NAME2's "predicted miss" is real**, not a stale build.
      Detail: [`docs/spec-fat-error-verb-control.md`](docs/spec-fat-error-verb-control.md) §6.2
      and [`docs/dev-workflow.md`](docs/dev-workflow.md).
- [x] ✅ **`LPRINT` / `LPOS` — the rest of the printer surface.** All
      three lacked a `kwtable.inc` entry, so they were `Syntax error` on zerobas,
      and [`docs/kwsweep-msx1-coverage.md`](docs/kwsweep-msx1-coverage.md)
      §“Not executed” lists them as *“printer-bound with the known unplugged-
      `LSTOUT` hang hazard”*. 🔴 **That reason is REFUTED** — D-EDITVERB measured
      `LLIST` on both references through a plugged `logger`, which never blocks
      (`docs/editverb-msx1-characterization.md` §1.1), and the sink itself works
      on zerobas today (`OPEN"LPT:"` writes to the printer, the `llt-ctl` row).
      So the sweep is carrying a stale reason for FOUR words and the other three
      are simply absent. Whoever adds them gets the readout for free.
      🔴 **BUT NOT UNIFORMLY, AND THIS ITEM SAID SO TOO BROADLY (corrected
      2026-08-06 while scouting D-LPTVERB).** `LFILES` does not live in that
      battery: [`probes/basic/basic_probe_kwsweep.py`](probes/basic/basic_probe_kwsweep.py)
      carries it in the **Disk-BASIC** group with **TWO** reasons, `NEEDS-DISK`
      *and* printer-bound, and D-EDITVERB refuted only the second. The first
      stands — the VG-8020 has no disk ROM, so putting `LFILES` to it measures
      the absence of a disk interface, not of a language feature (the same trap
      already recorded for the `MKS$`/`CVS` family). ⇒ **`LPRINT` and `LPOS` are
      three-sided; `LFILES` is CF-3300 + zb by construction**, and any gate must
      SAY that rather than let a reader infer it from a silent absence.
      ⚠️ And `LPOS` is not a sink re-point like the other two: no printer column
      counter exists anywhere in the tree (`pch_lpt` calls `LPTOUT` and tracks
      nothing), so it needs new state maintained in the hot path of every printed
      byte, plus a measured reset rule. Cost it separately from `LPRINT`.
- [x] ✅ **`READ` accepts only a single-letter, unsuffixed, non-array target —
      CLOSED 2026-08-07 by D-READVAR**,
      [`docs/spec-basic-readvar.md`](docs/spec-basic-readvar.md). **22 of the 24
      measured rows**, `make readvar-acceptance` **22/22 with 1 positive
      control**, **+32 B main page 1** (158 → 126) and **−74 B sub p0**.
      `ex_read` now parses its target with `var_str_type`/`var_name_key` and
      stores through `var_store_fac` / `strscr_desc`+`str_set_key` — ex_input's
      shape, routine for routine. The over-acceptance `c.strnum` closed WITH the
      21 refusals, in the DATA engine, not in the target parse.
      ➡️ **The array face is re-filed below as its own item, with its price.**
- [x] ✅ **CLOSED 2026-08-08 — AN ARRAY ELEMENT IS NOW A LEGAL LVALUE TARGET TO
      `READ`, `INPUT` AND `LINE INPUT`. All 18 divergent rows green.**
      `make arylv-acceptance` **16/16 + 2 deferred**, `readvar-acceptance`
      **24/24 (0 deferred**, up from 22/22 + 2), `inputary-acceptance` **7/7 and
      PROMOTED** from characterization — the "rows that can only ever be red"
      condition that blocked it is gone. Knives **14/14 rounds exact**, three of
      them reddening exactly ONE row. As-built:
      [`docs/spec-basic-arylv.md`](docs/spec-basic-arylv.md) §11.
      🎯 **THE SCOUT'S PRICE WAS EXACT ON EVERY ONE OF ITS TWELVE NUMBERS** —
      `tgt_parse` 32 B, `tgt_store_num` 24 B, `tgt_store_str` 30 B, all five site
      deltas, and both walls: main page 1 **126 → 49 B** (+77) and the low region
      **3 → 10 B** (7 B FREED). Not luck: the hand-counter was calibrated against
      313 B of the same routines first, and §4.1 drafted the helpers as the
      assembly that was later assembled.
      🔴 **`sub.rom` MOVED WHILE ITS WALLS DID NOT** (`33af21eb` → `de1ad5d0`),
      because `sub/basic-resident-abi.inc` is generated from main's `.sym` and
      main page 1 shifted. *"The sub walls held, so sub.rom held"* is a wrong
      inference; a wall is a size, a hash is an identity. Neither §6 nor §7
      predicted the hashes at all — a gap in the prediction, recorded as one.
      🔴 **K-AL4 justified the two rows the SCOUT added after drafting the
      knives.** Its class prediction names seven rows; it reddened **one**, and
      on the row set that existed before the knives were written it would have
      reddened **none** — the gate would have shipped unable to tell `ARY_TYPE`
      from `VARTYPE`.
      ➡️ **Still open below:** the four further lvalue parse sites
      (✅ the `ex_let_arr_str` string-space finding it also pointed at is CLOSED
      2026-08-20 by D-ARYOOS) — which are **no longer unmeasured**: all
      four diverge, measured 2026-08-08,
      [`docs/lvsites-msx1-characterization.md`](docs/lvsites-msx1-characterization.md).
      ✅ **`ex_for`'s single-letter name shim CLOSED 2026-08-08 by D-FORVAR**
      ([`docs/spec-basic-forvar.md`](docs/spec-basic-forvar.md)) — and it left
      one row of its own behind: the multi-variable `NEXT`, filed below.
      📄 **The pre-fix filing is NOT archived here.** It ran to 50 lines and this
      section is the PICKUP LIST -- a closed item's superseded text is doc debt in
      it. Everything it said is in the two documents linked above, which are the
      record: the scout carries the 18-row table, the four-site walk and the price;
      the spec carries the design, the forced constraints, the knives and §11
      As-built. Recoverable verbatim at `54f6e62` if it is ever wanted.
- [x] ✅ **~~AN `ERASE`D FIELDED ARRAY LEAVES A STALE `FLD_TAB` ENTRY~~ — CLOSED
      2026-08-08 (D-LRVAR), AND THE ORACLE REFUTED THE FIX THAT HAD BEEN PRICED
      FOR IT.** The settling row D-FLDARY named was taken, with the same program
      MINUS the `ERASE` as its own positive control:

      | row | CF-3300 | zerobas before |
      |---|---|---|
      | `e.ctl` (no `ERASE`) | `HI␣␣␣␣␣␣␣␣` | `HI␣␣␣␣␣␣␣␣` 🟢 control |
      | `e.erase` | **`HI␣␣␣␣␣␣␣␣`** | **Syntax error** 🔴 |

      🎯 **THE REFERENCE KEEPS THE FIELD ALIVE, SO THE PRICED SWEEP WAS THE WRONG
      FIX.** `fld_clear_ary` — *clear every entry whose `k0 >= $80`*, ≈20 B page 1
      + 3 B LOW — implements **drop**; the reference does not drop, so it would
      have left `e.erase` red for 23 bytes. Declining it for want of an oracle was
      right; the price was a claim about a design the oracle rejects
      ([[a-priced-decline-is-a-claim-about-a-design]]).
      🔴 **AND CLOSING IT WAS FORCED, NOT OPPORTUNISTIC.** D-LRVAR makes
      `lrset_notfld` a real store, so a stale element key stops being a LOUD
      `Syntax error` and becomes a **SILENT no-op** (K-LV7b reads exactly that:
      `HI␣␣␣␣␣␣␣␣` → empty). The slice could not ship the rule and leave the
      observability behind.
      💰 **THE SITING WAS THE EXPENSIVE PART, NOT THE SWEEP.** The real fix is to
      **fix the keys up** (`off -= stride` above the erased array; free the slot
      inside it), and `aeng_erase` (`sub/arrays.asm`) is **already a page-0
      tenant** that already holds both ends of the compaction and already reaches
      RAM, where `FLD_TAB` lives. Sited there: **0 B of main page 1**, 96 B of sub
      page 0 (3604 left). `aer_fldfix`; knife K-LV7b reddens `e.erase` and nothing
      else, ×2. [`docs/spec-basic-lrvar.md`](docs/spec-basic-lrvar.md) §5.4/§10.5.
      ⚠️ The neighbouring PRE-EXISTING version is still deliberately left alone: a
      bare program EDIT reaches `vars_reset` (which re-anchors `ARYTAB`) without
      reaching `clear_vars` (which is what calls `fld_init`), so a field entry can
      already outlive the variables it names — true of scalar entries today and
      not this slice's to change. ⚠️ **`ERASE` of the array a field names ITSELF**
      frees the slot, and the reference's answer for THAT arrangement is still
      unmeasured — named in the spec's §9 denominator, not claimed.
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
- [x] ✅ **`FIELD` AND `LSET`/`RSET` NOW ACCEPT AN ARRAY ELEMENT — SHIPPED
      2026-08-08 (D-FLDARY), and THREE of the four reasons the decline gave DID
      NOT SURVIVE A DESIGN.**
      [`docs/spec-basic-fldary.md`](docs/spec-basic-fldary.md); gate
      `make fldary-acceptance` **13/13**, `lvfix-acceptance` **18/18** with
      `d.ary`/`s.fldary` promoted out of DEFERRED,
      [`docs/lvsites-msx1-characterization.md`](docs/lvsites-msx1-characterization.md)
      **8/10** — all four lvalue parse sites closed.
      **+40 B main page 1** (18 → 35 free) and **+1 B LOW** (7 → 6),
      **FUNDED BY A CARVE**: `lrset_store`'s 68 B moved whole to a page-0 sub-ROM
      tenant (`SUBROM_IDX_LRSETST`, `sub/lrsetst.asm`) behind an 11 B stub, +57 B.
      **0 RAM, `FLD_TAB` byte-identical, `FLD_SLOTS` still 16.**
      🎯 **The decline's reason 2 was the expensive one and it was wrong.** It
      said an element needs a discriminator BESIDE the name key (`FLD_ENTSZ` 6→8,
      so `FLD_SLOTS` 16→12 or +32 B RAM). It does not: `fld_find` matches on
      `(k0,k1)` alone, so the discriminator can BE the key — a scalar stores its
      name, an element stores `(elem − ARYTAB) | $8000` — and the two spaces are
      disjoint by construction (a name's `k0` is an upcased letter; an element's
      is `>= $80`, guaranteed by an assembly-time assert on `TXTMAX − TXTBASE`).
      Reason 4 fell too: the cluster carve was refused, but the **leaf-only**
      re-run is page-0-tenant CLEAN. **Reason 1 stood and was load-bearing** — the
      READ hook on `str_eval_arr` is a real third site (`sea_fld`, page 1).
      🔴 **The gate found a defect the spec draft had: `sea_fld` omitted `push hl`
      / `pop hl`, and `fld_lookup` clobbers the live text cursor.** Six `s.*`/`r.*`
      rows read `<NO OUTPUT>` while every `d.*` row stayed green — which is what
      pointed at the read hook rather than at either parse site. 2 B.
      Knives 8 cuts × 2 rounds: 6 EXACT, 1 PARTIAL (K-FA1 — the second predicted
      row is structurally unreddenable, filed above), 1 re-sited (a knife may only
      name symbols the side it edits can SEE: `SUBROM_IDX_PING` is sub-only).
      🎯 K-FA5 is the abort knife D-LVFIX could NOT get, and the difference was
      **predicted from reading `exec_stmt`** rather than found by the run.
      ⚠️ ONE REFERENCE for every row (Disk BASIC; a diskless VG-8020 cannot
      express the question). Carried forward, not upgraded.
- [x] 🔴 **~~`FIELD` AND `LSET`/`RSET` STILL REFUSE AN ARRAY ELEMENT~~ — DECLINED
      WITH NUMBERS 2026-08-08 (D-LVFIX), ✅ SUPERSEDED BY THE ENTRY ABOVE. Kept
      only for the record of what a priced decline looked like before it was
      re-priced; nothing here is open.** The four
      lvalue parse sites D-ARYLV never measured all diverge
      ([`docs/lvsites-msx1-characterization.md`](docs/lvsites-msx1-characterization.md)).
      **D-LVFIX shipped two of them** — `ex_mid_stmt` (`MID$(…)=`) and
      `inp_readvar` (`INPUT #n` / `LINE INPUT #n`) — for **+31 B of main page 1
      and +3 B of the low region**, measured
      ([`docs/spec-basic-lvsites.md`](docs/spec-basic-lvsites.md)). These two are
      what is left, and they are ONE slice, not two rows of the old one:

      | site | statement | CF-3300 | zerobas |
      |---|---|---|---|
      | `ex_field` (`basic/field.asm`) | `FIELD#1,10 AS A$(1)` | `OK` | **Syntax error** |
      | `lrset_common` (`basic/field.asm`) | `FIELD#1,10 AS A$(1)` / `LSET A$(1)="HI"` | `HI        ` | **Syntax error** |

      🔴 **THE READ PATH IS A THIRD SITE AND NOBODY HAD LISTED IT.** `FLD_TAB`
      maps a 2-byte variable KEY to a (channel, offset, width) slice, and a
      fielded variable behaves only because `str_eval_one`
      (`basic/strvar.asm:79`) calls `fld_lookup` **on the scalar path**.
      `str_eval_arr` (`basic/arrays.asm`, **LOW region**) points `STRPTR` straight
      at the element and never consults the table — so `LSET A$(1)` can never be
      READ BACK, whatever `FIELD` records. Teaching only the two parse sites about
      subscripts would turn `d.ary` green **for the wrong reason** (subscript
      parsed and discarded, so `A$(1)` and `A$(2)` collide in the table) and leave
      `s.fldary` red.
      🔴 **AND THE TABLE CANNOT IDENTIFY AN ELEMENT.** A stable discriminator is
      the ARYTAB-relative offset (`FLD_ENTSZ` 6 → 8), but `FLD_TAB` is
      `$EE64..$EEC3` and `GP_RECNO` sits at `$EEC4` — so it costs `FLD_SLOTS`
      16 → 12 (a user-visible capacity cut) or +32 B of RAM rehomed.
      💰 **Design sketch, NOT a calibrated hand count: ≈ +80 B page 1, ≈ +5 B
      low**, against **18 B** and **7 B** free. And
      `carve_scout --entries ex_field,ex_lset,ex_rset,fld_add,fld_find` returns
      **NOT page-0-evictable** (313 absent-region callees, 7 DATA), so there is no
      ready carve either. **This slice needs its own carve scout before anything
      else.**
      🔴 **ONE REFERENCE ONLY** — Disk BASIC; a diskless VG-8020 cannot express
      the question. Weaker than anything D-ARYLV rested on. ⚠️ `RSET` shares
      `lrset_common` and is not separately measurable even after the fix.
- [x] ✅ **~~`INPUT #n` PARSES ONLY ONE TARGET~~ — FIXED 2026-08-19,
      D-INPLIST.** `inp_readvar` (basic/files.asm) takes a comma-separated LIST
      now: `INPUT#1,A$,B$` over a `HI,LO` file reads **`HILO`** here, the
      CF-3300's own answer, and so does the array form `INPUT#1,A$,B$(1)`.
      🎯 **THE LOOP IS THE ROUTINE ITSELF, so the fix is 7 B and no second
      parser.** `inp_readvar` already opened by requiring the separator — it was
      written for the comma between the CHANNEL NUMBER and the first target — and
      the comma between two targets is the same byte in the same place. The tail
      tests for one and re-enters at the top. Same `tgt_parse` /
      `read_into_strscr` / `tgt_store_str` path, no state to carry (the channel
      is selected before the routine is entered), same SP (both guard words are
      popped), and numeric `INPUT #n` is still rejected — this widens the COUNT
      of targets, not their type. The existing split was cheaper than a new
      guard, exactly as at `NEXT` ([[the-existing-split-is-cheaper-than-a-new-guard]]).
      💰 **FUNDED, and the slice is −1 B NET.** Main page 1 had **2 B**. The
      carve is in `do_open`: the "APPEND" match was four unrolled
      `cp`/`jp nz`/`inc hl`/`ld a,(hl)` groups (27 B) for what is plainly DATA,
      so it became a 13 B loop over a 5-byte `oo_app_seq`; and six
      `jp cc,stmt_error` sites in that parse now `jr cc,oo_synerr` to one local
      trampoline. **+8 B returned, 7 B spent: page-1 free 2 → 10 → 3 B.**
      ✅ **THE CARVE WAS MEASURED ALONE BEFORE ANYTHING SPENT IT** — built,
      `page-1 free = 10 B`, and `diskbasic-acceptance` **34/34** — so "behaviour
      unchanged" is an oracle reading and not an argument.
      ✅ **GATE: `lvfix-acceptance` 18/18 → 20/20**, deferrals 4 → 2. `f.mixctl`
      and `f.arymix` GRADUATED out of that probe's `DEFERRED` literal (a
      graduation is a DELETION FROM THE LITERAL, never prose about one), and
      **POSITION for `INPUT #n` left the NOT-COVERED list**: `f.arymix` going
      green is the array-element target in a CONTINUATION position, which is the
      axis D-LVFIX shipped and could not demonstrate until this unblocked it.
      🔴 **MY FIRST KNIFE OVER-REDDENED AND THE KNIFE WAS WRONG, NOT THE FIX.**
      K-IL1 cut `cp ','` to `cp 0` — same length — predicting the 2 rows. It
      reddened **8**: `0` is the end-of-statement terminator, so the loop fired at
      the END of every `INPUT #n` and re-entered demanding a comma, breaking the
      SINGLE-target base case too. **A knife byte must be one the site can never
      see.** Re-cut as K-IL1b (`cp '.'`, which cannot stand after a target):
      **exactly 2 diverge, 18 green — prediction EXACT.** K-IL2 corrupted
      `oo_app_seq`'s second byte and reddened **exactly** `PRINT#-append` with
      33/34 verbs still converging, so the carve is under test too.
      ⚠️ **ONE REFERENCE ONLY (CF-3300).** `INPUT #n` is Disk BASIC and a diskless
      VG-8020 cannot express it. Carried forward, not upgraded.

      **Originally filed** — MEASURED 2026-08-08 (D-LVFIX). `INPUT#1,A$,B$` reads `HILO` on the CF-3300 and is
      `Syntax error` here (`f.mixctl`), and so is the array form `INPUT#1,A$,B$(1)`
      (`f.arymix`). `inp_readvar` (`basic/files.asm`) has **no variable-list loop
      at all**: it parses ONE target and falls into `jp exec_stmt`, so the
      leftover `,` is what errors. Both rows are carried DEFERRED in
      `lvfix-acceptance`.
      🎯 **Only the SCALAR control could tell the two apart.** The probe's first
      draft had only the array half, which would have scored a LIST defect as an
      array failure and blamed D-LVFIX for a gap it does not own
      ([[row-with-two-candidate-causes]]). ⚠️ POSITION is therefore **not covered
      for `INPUT #n`** by any gate. ONE reference (Disk BASIC).
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.1): `INPUT#1,A$,B$` over a `HI,LO` file reads `HILO` on the CF-3300 and
      `Syntax error in 50` here, against an `INPUT#1,A$` control reading `HI` on
      both. `lvfix-acceptance`'s own DEFERRED `f.mixctl` row printed the same
      pair in the same session.
      ⚠️ **AND THE SWEEP'S FIRST PASS SCORED IT STALE, ON A READOUT FAULT.**
      Driven as DIRECT lines with the reporting `PRINT` last, the abort lands on
      a line that is NOT the last one, so a tail anchored on the `PRINT` cannot
      see it and zerobas read `[HI]` — a value consistent with the wrong
      hypothesis [[readout-blind-to-its-own-subject]]. Re-drive as a stored
      program with `RUN`, where the abort IS the tail.
- [x] ✅ **~~`VARPTR(<unset variable>)` IS `Illegal function call` ON BOTH
      REFERENCES AND SUCCEEDS HERE~~ — FIXED 2026-08-19, D-VPTRDOM.**
      `ev_f_varptr`'s scalar path calls `var_find_typed` (find, never allocate)
      and defers **FPERR=3 → ERR 5** through the shared `ev_f_defer` tail, so
      `X=VARPTR(Q)` with `Q` unset is `Illegal function call` on **all three
      sides**. `lvfix-acceptance` **20/20 → 22/22, and its DEFERRED literal is
      now EMPTY** — every row it prints is scored. Knife K-VP1 put
      `var_alloc_or_find` back (same length): **exactly 2 diverge, 20 green.**
      ⚠️ **SCOPE:** the ARRAY-element form is untouched — `VARPTR(A(1))` still
      auto-dims on read, as `ev_f_arr` and the references do. The oracle covers
      the unset SCALAR only and the fix is scoped to it.
      💰 **5 B, from the 66 B `ev_sp` carve** (D-EVSPDUP, same day); page-1 free
      69 → 64 B.
      🔴 **THE PRICE THIS ENTRY ASKED FOR, PAID AND LARGER THAN FILED.** The note
      said "anyone narrowing `VARPTR`'s domain should price what that makes
      dead". It is **five `array-acceptance` rows**, not just K-LV5's detector:
      `scalar.varptr.elem`, `scalar.varptr.neighbor`, `strarr.varptr.neighbor`,
      `h2.varptr.strarg.elem`, `h2.varptr.defstr.elem` — every one of them forced
      the §13a mid-eval `ARYTAB` shift through the auto-allocating `VARPTR`,
      because that was the only way to force it. **RETIRED, 151 → 146 rows, all
      passing**, with the reasoning kept verbatim in the probe.
      🎯 **AND THE CLASS IS UNREACHABLE NOW, NOT MERELY UNTESTED.** §13a's
      corruption REQUIRED an eval-time scalar allocator; there is no longer one
      on ANY of the three sides, so no program any side accepts can shift
      `ARYTAB` mid-statement. ⚠️ **THE GUARDS STAY** (`ex_let_arr`'s
      `ary_snapshot_offset`/`ary_apply_offset`, D-LVFIX's `tgt_desc`) — cheap,
      static argument, and needed again if an allocator ever returns; this entry
      said not to delete them on the note alone and they are not deleted.
      ⚠️ **K-LV5 HAS NO LIVE DETECTOR FROM HERE ON**, and rewriting the five rows
      to pass was REFUSED: with no allocator they would stop reaching the
      correction and go green while gating nothing.
      🔴 **THE DEAD-CODE GATE CAUGHT A REROUTE NO ACCEPTANCE GATE COULD HAVE.**
      The first draft put `vptr_unset:` immediately ABOVE `vptr_none:`, stealing
      `vptr_arr`'s NZ **fall-through**: the array-element error path started
      raising through the new block and `vptr_none` was orphaned. It would NOT
      have shown as a wrong answer — `ev_f_defer`'s `penderr_set` is
      first-error-wins and `ary_op0_resolve` had already set FPERR — so every
      differential would have stayed green. Only `make deadcode` failed the
      build, naming `vptr_none`. ⇒ **inserting a label before an existing one is
      an edit to whatever FELL INTO it.**

      **Originally filed** — MEASURED 2026-08-08 (D-LVFIX). Isolated
      away from any other verb: `X=VARPTR(Q)` with `Q` unset is IFC on the
      VG-8020 and `OK` on zerobas, which allocates `Q`. **TWO references.**
      🎯 **The consequence is bigger than the row.** Arrays slice-4b §13a names
      `VARPTR` as *the only* eval-time scalar allocator, so on the **reference**
      the entire §13a stale-array-element corruption class is **not expressible**
      — it exists in this tree only because zerobas's `VARPTR` accepts a domain
      the reference rejects. That makes every §13a guard (`ex_let_arr`'s
      `ary_snapshot_offset`/`ary_apply_offset`, and D-LVFIX's own `tgt_desc`
      correction) **correct and reachable but NOT oracle-able**: no program both
      references accept can shift `ARYTAB` mid-statement. ⚠️ Anyone narrowing
      `VARPTR`'s domain should price what that makes dead — but the guards are
      cheap and the argument is static, so **do not delete them on this note
      alone**. `m.ctldrift`/`m.arydrift` carry the evidence, DEFERRED, in
      `lvfix-acceptance`.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.2): `X=VARPTR(Q)` with `Q` unset is `Illegal function call` on the
      VG-8020 **and** the CF-3300 and raises nothing here, against a `Q=1` /
      `X=VARPTR(Q)` control silent on all three. `lvfix-acceptance` printed its
      two DEFERRED rows the same way in the same session.
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
- [x] ✅ **~~`LSET`/`RSET` ON A NON-FIELDED VARIABLE IS `Syntax error`~~ — SHIPPED
      2026-08-08 (D-LRVAR), AND THE LVALUE/FIELD SURFACE IS NOW CLOSED:**
      [`docs/lvsites-msx1-characterization.md`](docs/lvsites-msx1-characterization.md)
      reads **10/10** and has no red row left.
      [`docs/spec-basic-lrvar.md`](docs/spec-basic-lrvar.md); gate
      `make lrvar-acceptance` **21/21** (from 5/21), with `fldary-acceptance`
      13/13 and `lvfix-acceptance` 18/18 + 4 deferred both unchanged.
      **+29 B main page 1** (35 → 6), **0 B LOW, 0 RAM, NO CARVE NEEDED** —
      D-FLDARY's 57 B carve funded this slice too.
      🔴 **ONE DATA POINT IS NOT A RULE, and this item had exactly one.** The rule
      was MEASURED FIRST, over 21 rows, and three readings the single filed one
      could not have predicted are what decided the design: the target's **`LEN`
      never changes**; an **UNSET or EMPTY target is a NO-OP**, not an assignment
      and not an error; and **`RSET A$="HELLO"` on `A$="AB"` reads `HE`, not
      `LO`** — `RSET` truncates from the same end `LSET` does.
      🎯 **NO STORE ENGINE WAS WRITTEN.** That rule is byte for byte what
      `lrset_store_tenant` already did. The slice generalises the destination cell
      (`LRSET_OFF` → `LRSET_DEST`, an ADDRESS, same 2 bytes, 0 RAM) and takes the
      width from the target's own descriptor; **the tenant got 4 B SMALLER.**
      🎯 **AND THE TWO ARMS DO NOT STORE DIFFERENTLY.** The framing above assumed
      a scalar is inline `[name0][name1][len][bytes]` and an element a
      `[len][ptr]` descriptor, i.e. two stores — that is the **PRE-slice-4c**
      layout. Both are `[len][ptr]` now, `tgt_desc` already forks on how the
      descriptor is FOUND, and the stale `basic/field.asm` header that said
      otherwise is corrected (spec §5.1).
      💰 **A `Type mismatch` fell out for 0 BYTES:** `A=1` / `LSET A=2` is
      **`Type mismatch`** on the CF-3300 and was `Syntax error` here — a
      divergence nobody had listed, fixed by a byte-neutral `jp` target swap.
      Knives 10 cuts × 2 rounds, **7 EXACT** (K-LV2/K-LV7b/K-LV8 each redden
      exactly ONE row). 🔴 **THREE of the misses are findings**: `FLD_CHAN` is
      **uninitialised**, not 0, so the arm reset is load-bearing on EVERY
      non-FIELDed `LSET`; a stale WIDTH is **invisible** on a left-justified
      target's own bytes, so only the neighbour / `RSET` / unset rows can see it
      (which is what proves §4.3's width-0 safety); and `tgt_desc_fix` is
      **mandatory arithmetic, not a drift guard** — a "predicted miss" copied
      from D-LVFIX's framing rather than derived, which reddened five rows.
      ⚠️ ONE REFERENCE for every row (Disk BASIC; a diskless VG-8020 cannot
      express the question). Carried forward, not upgraded.
      📄 **The pre-fix filing is NOT archived here** — this section is the PICKUP
      LIST and a closed item's superseded text is doc debt in it. Recoverable
      verbatim at `76685e9`; the 2×2 argument it carried is
      [`docs/lvsites-msx1-characterization.md`](docs/lvsites-msx1-characterization.md)
      §3, which is the record.
- [x] ✅ **`ex_for`'s SINGLE-LETTER LOOP-VARIABLE SHIM — CLOSED 2026-08-08 by
      D-FORVAR**, [`docs/spec-basic-forvar.md`](docs/spec-basic-forvar.md),
      measured in
      [`docs/forvar-msx1-characterization.md`](docs/forvar-msx1-characterization.md),
      gated by `make forvar-acceptance` at **31/31 on three sides**, with
      **BOTH references agreeing on all 33 rows** — a stronger oracle than the
      whole lvalue/FIELD arc, which rested on the CF-3300 alone.
      `make arylv-acceptance` **16/16 → 18/18**: `f.two` and `f.pct` were
      deferred there *for this slice* and are now ordinary scored rows.
      🔴 **THREE READINGS WERE NOT A RULE, AND FOUR OF THE 33 DECIDED THE
      DESIGN** — none of them inferable from the filed rows:
      `n.xtype` (`FOR A%=1 TO 3` / `NEXT A` → **NEXT without FOR**) puts the
      resolved **TYPE** in the match key, so the frame holds
      `(name0, name1, type)` and the compare is **three** bytes;
      `n.prefix` (`FOR AB` / `NEXT A` → NEXT without FOR) says the shipped
      one-char shim was not too strict but too **LOOSE**;
      `n.strnx` (`FOR A` / `NEXT A$` → NEXT without FOR, **not** Type mismatch)
      says a `$` NEXT name must **MISS**, not error — the obvious symmetry with
      `FOR`'s own guard answers the wrong message, so `ex_next` gained no error
      path at all; and `f.defstr` puts the guard on the **resolved type** rather
      than on the `$` character.
      Landed: a shared `for_name`, an 11-byte frame, `var_get`/`var_set` →
      `for_get`/`for_set`, `deftbl_num_type` deleted. **+1 B of main page 1
      (6 → 5) and the low region ends 5 B RICHER (6 → 11), NO CARVE** — 20/20
      predicted spans and all five walls exact, because the counter was
      calibrated 18/18 against the `.sym` first. All four ROM hashes predicted,
      including the two that **HOLD**: `sub.rom` is byte-identical because every
      one of its 11 imported addresses lies below the only low-region edit.
      🎯 **WIDENING THE KEY IS WHAT PAID FOR WIDENING THE KEY** — the
      `upcase`/`ld c,0`/`deftbl_num_type` prologue dies in both shims (−9),
      `FOR_NEW` dies with it (−7), and `ex_for`'s bespoke `cp '$'` folds into a
      type check the DEFtbl path needed anyway. Inlining `for_name` at both
      sites instead of sharing it would have been **+13** against 6.
      🔴 **`FOR_DEPTH` STAYS 8 AND THE CROWDED `$E0` PAGE GAINS 72 BYTES.**
      8 × 11 does not fit at `$E070`, so the honest choices were "relocate" or
      "6 nested loops instead of 8"; `f.dep8` is the green-before/green-after row
      that makes that a measurement. The stack moved to `$EA3A` — and the comment
      claiming that window starts at `$EA39` was **one byte stale** (D-LPTVERB
      took `$EA39` for `LPTPOS` and never said so).
      🔴 **THE GATE FOUND A DEFECT IN THIS SLICE'S OWN FIRST DRAFT.**
      `LD (nn),BC` writes **C** first and `var_name_key` returns B = name0, so
      the frame's byte 0 is **name1** — which is **0** for every single-character
      name. The bare-`NEXT` sentinel sat on that byte, so `NEXT A` read as a bare
      `NEXT` and took the top frame whatever its name. Every row whose top frame
      happened to BE the right one passed anyway; only `n.xtype`, `n.prefix` and
      `n.strnx` could see it. Fixed byte-neutrally.
      🎯 **AND THE KNIVES DEMANDED A ROW THE GATE HAD NOT ASKED FOR.** K-FV1
      (match on one byte) and K-FV2 (two) reddened the **identical** set, because
      every mismatching row differed in `name1` and nothing said whether `name0`
      was compared at all. `n.samen1` (`FOR AB` / `NEXT CB`) separates them, and
      it exists because the cuts were drafted first.
      9 cuts × 2 rounds, **both rounds identical**, 7 exact; the two misses are
      findings recorded in [`docs/spec-basic-forvar.md`](docs/spec-basic-forvar.md)
      §10.5. `f.ary` (`FOR A(1)=`) stayed `Syntax error` on all three sides
      throughout — the negative control did its job.
- [x] ✅ **`NEXT` PARSES ONLY ONE VARIABLE — CLOSED 2026-08-08 by D-NXLIST**,
      [`docs/spec-basic-nxlist.md`](docs/spec-basic-nxlist.md), measured in
      [`docs/nxlist-msx1-characterization.md`](docs/nxlist-msx1-characterization.md)
      at **28 rows on three sides, BOTH references agreeing on all 28**, gated by
      `make nxlist-acceptance` at **25/25** (from 9/25) with 3 deferred, and
      `forvar-acceptance` **31/31 → 33/33** with an empty `DEFERRED`.
      🔴 **THE FILED SKETCH WAS RIGHT ABOUT `nx_end` AND WRONG ABOUT THE LEDGER.**
      `nx_end` really does grow by **+8 B** — but the same 200 bytes of `ex_next`
      carried its frame-stack bound test **twice** (`nx_find` "is the stack
      empty?" and `nx_miss` "did the walk run out?") and its limit comparison
      **twice** (`nx_have` / `nx_neg`). Merging both — with the frame-base
      computation folded into the surviving subtraction, so `nx_scan` stops
      reloading `(FSP)` — is **−22 B**. **Net −10 B: page 1 5 → 15 B**, 0 low,
      0 sub, 0 RAM, **13/13 spans and all 4 hashes exact**, `sub.rom` and
      `disk.rom` byte-identical. *"Does not fit without a carve"* was a claim
      about a ledger nobody had opened ([[which-wall-binds-is-a-history-question]]).
      🎯 **THE LIST STATE IS THE BARE-`NEXT` SENTINEL'S VALUE — TWO BYTES.**
      `nx_scan` already reads `FOR_CUR+1 = 0` as *"match the top frame"* and any
      other non-letter as *"match nothing"*, so `ex_next` parks 0 and `nx_comma`
      parks 1. No flag, no RAM cell, no second parse head.
      🔴 **AND THE MEASUREMENT REFUTED THE DESIGN TWICE, EACH TIME KILLING A
      CHEAPER ONE.** Round 1 (21 rows) yielded a complete rule and a design that
      fit. **`m.trail`** (`FOR A` / `FOR B` / `NEXT B,` → **NEXT without FOR**)
      killed the zero-byte *"a trailing comma is a bare `NEXT`"* reading — with an
      OUTER frame standing a bare `NEXT` would have closed it and the program
      would have finished. ⚠️ **`m.trail1` cannot say that**: its stack is empty
      at the comma, so both rules predict the same answer, and K-NL4 confirms it
      stays GREEN under its own knife. Then **`m.trailnum`** (`NEXT B,1` →
      **Syntax error**, not ERR 1) killed the replacement, and forced the fix onto
      `nx_notletter`'s *existing* terminator/not-a-name split — which is what made
      it two bytes instead of thirteen.
      🎯 **`n.nofor` / `n.barenofor` ARE THE CARVE'S OWN ROWS.** No row in the
      33-row D-FORVAR battery enters through `nx_find`'s bound test: every
      mismatching row there has exactly one frame, so it errors from `nx_miss`. A
      `NEXT` with no `FOR` **at all** is the only program that takes the other
      entry, and the merge was unguarded until this battery existed.
      Knives **7 cuts × 2 rounds, 7 EXACT, both rounds identical**, two of them
      one-row (K-NL3 `m.space`, K-NL6 `m.step`). Corpus **29/29 in 14 min 52 s**.
- [x] ✅ **`NEXT A(1)` — CLOSED 2026-08-08 by D-NXARY**,
      [`docs/spec-basic-nxary.md`](docs/spec-basic-nxary.md), measured in
      [`docs/nxary-msx1-characterization.md`](docs/nxary-msx1-characterization.md)
      at **22 rows on three sides, BOTH references agreeing on all 22**, gated by
      `make nxary-acceptance` at **21/21** (from 6/21) with 1 deferred.
      **+10 B of main page 1 (15 → 5 B), 0 low, 0 sub, 0 RAM**; `sub.rom` and
      `disk.rom` byte-identical.
      🎯 **THE EXPENSIVE PART WAS ALREADY BUILT.** `tgt_parse` (`basic/vars.asm`)
      is the whole rule — name, suffix, subscripts, `ary_op0_resolve` op=0 — and
      `ex_read` has reached it from page 1 since D-ARYLV. This is its **seventh**
      call site, not a new mechanism.
      🎯 **AND THE UNMATCHABLE KEY IS FREE, FOR THE THIRD SLICE RUNNING.**
      `(TGT_ADDR)`'s high byte is 0 iff the target is a scalar, and when it is
      not it is ≥ `$80` — which no `is_letter`-gated `name0` can be. So the byte
      that ANSWERS *"is this an element?"* **is** the byte that makes the key
      match nothing, and ERR 1 falls out with no error path. D-FORVAR did it with
      `DEFTBL_STR`, D-NXLIST with the list sentinel
      ([[the-existing-split-is-cheaper-than-a-new-guard]]).
      🔴 **`a.autodim` IS THE ROW NO DIRECT READING COULD TAKE.** Whether the
      resolve creates the array is a side effect on a row that ERRORS: trap the
      error, then `DIM A(3)`, and both references answer **Redimensioned array**.
      The resolve auto-DIMs, so the fix must use the auto-dimming one.
      🔴 **AND `a.str` WAS ALREADY GREEN FOR THE WRONG REASON.** `NEXT A$(1)`
      agreed here before the fix — D-FORVAR made a `$` name resolve to
      `DEFTBL_STR`, a type no frame holds, so ERR 1 fell out *without the
      subscript being looked at*. `a.stroob` (`NEXT A$(99)`) separates them.
      Knives 5 × 2, **4 EXACT**; two misses are findings (spec §10.5(c),(d)),
      and one of them demanded a row — **`a.strpick`**, which is what proves
      `var_str_type` is load-bearing.
      ⚠️ Carried out of it: the two `- [ ]` items directly below.
- [x] ✅ **`NEXT A (1)` — A SPACE BEFORE THE `(`, CLOSED 2026-08-08 by
      D-TGTSPC**, [`docs/spec-basic-tgtspc.md`](docs/spec-basic-tgtspc.md),
      measured in
      [`docs/tgtspc-msx1-characterization.md`](docs/tgtspc-msx1-characterization.md),
      gated by `make tgtspc-acceptance` at **26/26 rows on three sides** (28
      cases, 2 deferred), with **BOTH references agreeing on all 28**.
      D-NXARY deferred it for EVIDENCE, not budget, and the evidence is now all
      **NINE** statement surfaces that reach `tgt_parse`, each with the
      CONTIGUOUS form of its own statement as its own positive control on its
      own fixture: `NEXT`, `READ`, console `INPUT` (both arms), `LINE INPUT`,
      `MID$()=`, `INPUT #n`, `FIELD`, `LSET`/`RSET`. **12/26 → 26/26**, and
      `nxary-acceptance` **21/21 + 1 deferred → 22/22** with `a.spc` un-deferred
      ([[a-deferral-honoured-is-worth-more-than-one-filed]]). The fix is
      `call skip_spaces` in place of `ld a,(hl)`, **one instruction, +2 B**;
      page 1 **5 → 3 B**, low/sub/RAM untouched, `sub.rom` and `disk.rom`
      byte-identical.
      🎯 **THE FIRST QUESTION WAS NOT *"DOES THE REFERENCE SKIP THE SPACE"* BUT
      *"IS THE SPACE STILL THERE"*.** If the reference's CRUNCH stripped it, a
      parser-side fix would have spent every byte in the wrong file — and on
      screen the two hypotheses are identical (both give `NEXT without FOR`).
      Row `t.spc` reads the STORED LINE BYTES through `TXTTAB`, the instrument
      `basic_probe_crunch.py` uses: `1 NEXT A (1)` crunches to
      `83 20 41 **20** 28 12 29 00` on the VG-8020, the CF-3300 and here, byte
      for byte. The `$20` survives. ⇒ the parser skips it.
      🔴 **AND THE FILED ITEM WAS WRONG ON BOTH OF ITS NUMBERS.** The price said
      **3 bytes**; it is **2** — a cost that forgets what it DISPLACES is a cost
      for an insertion, not a substitution. And `tgt_parse` does not have
      **seven** call sites: it has **EIGHT `call` instructions from NINE
      statement surfaces**. The hand list is seven *other* surfaces and forgot
      to count `ex_next`, the site that filed the residual; it also folds the
      console `INPUT`'s two arms — two distinct `call`s — into one
      ([[a-hand-listed-denominator-is-a-scope-claim]]). Three documents carried
      the seven, `ex_next`'s own code comment included.
      🔴 **`m.trail` TURNED THE PREDICTED SIDE EFFECT INTO A SECOND FIX.**
      Skipping spaces also consumes a TRAILING space on the SCALAR path, and
      `ex_mid_stmt` is the only caller that then reads its delimiter with a bare
      `ld a,(hl)` — the other eight do their own `skip_spaces`. `MID$(A$ ,1,2)=`
      `"XY"` is **`XYLLO`** on both references and was **Syntax error** here, so
      the consumption is REQUIRED, not tolerated: one instruction closes two
      divergences at that site.
      🔴 **K-TS4 REDDENED A ROW THE PREDICTION EXCLUDED, BECAUSE THE PREDICTION
      SAID "SCORED" AND A KNIFE DIFFS WHAT THE PROBE *PRINTS*.** `probe_report.`
      `parse()` returns DEFERRED rows like any other. The extra row is
      corroboration rather than noise: `x.dollar` moving under a cut that
      touches nothing but the scalar marker proves zerobas really parses
      `NEXT A $(1)` as the scalar `A`, which is the deferral's own stated cause.
      Knives 5 × 2, **4 EXACT, both rounds identical**; K-TS2/K-TS3 are the same
      cut at two different callers and separate to one row each, which is the
      measurement a shared-engine slice owes.
      ⚠️ Carried out of it: the `- [ ]` item directly below.
- [x] ✅ **A SPACE INSIDE A VARIABLE REFERENCE'S NAME OR BEFORE ITS `$` SUFFIX
      IS INSIGNIFICANT — CLOSED 2026-08-08 by D-NAMSPC**,
      [`docs/spec-basic-namspc.md`](docs/spec-basic-namspc.md), measured in
      [`docs/namspc-msx1-characterization.md`](docs/namspc-msx1-characterization.md),
      gated by `make namspc-acceptance` at **56/56** (58 rows, 3 sides, both
      references agreeing on all 56 they can express) — from **29/56**. D-TGTSPC's
      `x.dollar` / `x.name` leave `DEFERRED` and `tgtspc-acceptance` goes
      **26/26 → 28/28**, its dict now EMPTY.
      🎯 **THE RULE IS UNIVERSAL, AND `r.name` IS THE ROW THAT SIZED THE SLICE.**
      `AB=7 : PRINT A B` reads ` 7 ` — **one** value, the variable `AB` — on both
      references, and `PRINT` never touches `tgt_parse`. So it is the NAME SCAN's
      rule, reaching all 11 `var_name_key` + 16 `var_str_type` call sites, not the
      nine lvalue targets D-TGTSPC fixed.
      🎯 **AND IT COST −3 B: THE SLICE FUNDS THE BINDING WALL INSTEAD OF SPENDING
      IT.** All three name-scan read points already did `ld a,(hl)` immediately
      before `call is_ident_cont`, so moving the load into the callee pays for the
      `call skip_spaces` exactly — three deletions for one insertion, **the rule
      itself is 0 B** — and deleting `vnk_dig2` (a reload of what `A` already
      holds; `is_letter` is `push af`..`pop af` on both exits) gives 3 B back.
      **Page 1 3 → 6 B**, low 11 B untouched, both sub ROMs byte-identical.
      A price of *"three `call skip_spaces` insertions, +6 B"* — the obvious
      shape — would have DECLINED this. Walking the callers before pricing is what
      made the difference.
      🔴 **THE `TKNAME` HAZARD THAT COULD HAVE MOVED THE WHOLE SLICE INTO THE
      TOKENISER IS REFUTED BY THE ARTIFACT.** A digit is copied verbatim only
      while the in-name flag is set, so `1 A 1=1` could have stored a numeric
      constant no parser could rejoin. It stores `41 20 **31**` — verbatim — on
      all three sides. Twelve `t.*` rows read the STORED LINE BYTES and are green
      **before** the fix in every position, which is what says the fix is the
      parser's ([[read-the-artifact-when-the-screen-cannot-witness]]).
      🔴 **THE KEYWORD CONSTRAINT IS REAL AND POINTS BOTH WAYS.** `SC ORE` still
      carries the `OR` token ($F7) and must STAY refused (`z.kw`, green before and
      after); `A ND` and `A BS` carry **no** token and are ordinary names reading
      ` 7 ` on both references. The match is POSITIONAL, and a name scan may not
      be cleverer than the tokeniser that ran first.
      🔴 **A PREDICTION WRONG IN THE DIRECTION THAT PRODUCED A FINDING.** §3.3
      predicted `FIELD#1,N AS A$(1)` would land on the CF-3300's `Type mismatch`;
      it landed on `Syntax error` (54/55). Isolating it needed rows that did not
      exist, and one of them has **no space in it at all** — see the new item
      below. Two rows added, two deferred, and §8's whole knife table recomputed:
      **a row set that grows invalidates every prediction written against it.**
      🔴 **AND FIVE ROWS WERE NOT AN ERROR BUT A HANG.** `PRINT A 1` / `AB %` /
      `!` / `#` / `$` filled the screen with ` 0 ` forever; the probe's first
      reader called that `<NO OUTPUT>`, the exact opposite of what happened,
      because `RUN` had scrolled off and the anchor search returned `None`.
      Knives 5 × 2, **3 EXACT, both rounds identical**. 🔴 Both misses are one row
      and one mistake: `z.join` is decided by `var_str_type`, not `var_name_key`,
      and **the `$` is tested in two independent places** (`vst_suffix` and
      `vnk_suffix`) so no single byte-neutral cut separates them — a fact about
      the code the battery established and the source reading did not.
      ⚠️ Carried out of it: the two `- [ ]` items directly below.

- [x] ✅ **`ex_field` NEVER TYPE-CHECKS ITS FIELD WIDTH — CLOSED 2026-08-08 by
      D-FLDWIDTH**, [`docs/spec-basic-fldwidth.md`](docs/spec-basic-fldwidth.md),
      measured in
      [`docs/fldwidth-msx1-characterization.md`](docs/fldwidth-msx1-characterization.md),
      gated by `make fldwidth-acceptance` at **40/40 (2 deferred, 42 cases)**
      from **24/42**. `namspc-acceptance` 56/56 + 2 deferred → **58/58 with its
      `DEFERRED` dict EMPTY** — the deferral was honoured, not merely filed
      ([[a-deferral-honoured-is-worth-more-than-one-filed]]).
      🎯 **THE RULE IS NOT "TYPE-CHECK THE WIDTH", IT IS `get_byte_arg`, AND THE
      DENOMINATOR IS WHAT SAID SO.** The item arrived with two rows and one
      clause. 42 rows later: a width is a **BYTE ARGUMENT** — a string is
      `Type mismatch`, a deferred `1/0` is `Division by zero`, **70000 is
      `Overflow` (ERR 6) while −1/256/257 are `Illegal function call` (ERR 5)**,
      a fraction TRUNCATES, and the checks are **PER ITEM with no rollback**
      (`m.trap` reads ` 13  5 ` — ERR 13, and the first field is still 5 wide).
      Two different error codes is exactly `get_byte_arg`'s two stages
      (`get_int16_checked`, then the 0..255 test) — code that already ships and
      is already the reference's rule — so the whole domain half cost **3 bytes
      of `call`** instead of a hand-rolled bound.
      🎯 **THE OBVIOUS PRICE WAS +6 AND THE REAL ONE IS +3.** `exf_item`'s own
      `call skip_spaces` is **dead**: `eval` reaches `ev_f`
      ([`basic/expr.asm:461`](basic/expr.asm:461)), whose first instruction is
      `call ev_sp`. Two calls in, one out. **Page 1 6 → 3 B**; low **11 B**, sub
      p0 **3604**, sub p1 **1483**, RAM all untouched; `sub.rom` **and**
      `disk.rom` byte-identical.
      🔴 **`basic/field.asm`'s OWN HEADER SAID "field widths are 1..255" AND IT
      WAS WRONG.** `d.zero` measured `FIELD#1,0 AS A$` as **accepted**, LEN 0, on
      the CF-3300. A design built on the source comment would have shipped a
      divergence the comment invented; the header is corrected in the same commit.
      🔴 **AND THE PROBE'S READER WAS BLIND TO ITS OWN SUBJECT.** `Overflow` is a
      SUBSTRING of `FIELD overflow`, listed earlier in the needle tuple — so a
      screen reading `FIELD overflow in 30` scored as `<Overflow>`, and the one
      error name this battery exists to find was invisible to it. It failed by
      **agreeing with a plausible answer**; what exposed it was `d.big` (70000)
      returning the same string for a genuinely different fault. Needles are now
      sorted longest-first ([[readout-blind-to-its-own-subject]]).
      🎯 **A SECOND FIX RODE ALONG FOR 0 B**: `FIELD#1,10 AS A` is `Type
      mismatch` on the CF-3300 and was `Syntax error` here — D-LRVAR's move one
      statement over, the same `jp cc,nn`. ⚠️ Only **one** of `ex_field`'s FOUR
      `exf_syn` arms moves, and `t.noas` / `t.nonm` are the negative controls
      that bound it ([[a-rule-can-claim-more-than-its-evidence]]).
      🎯 **`o.dt` IS THE ROW THAT ORDERS THE CHECKS AND `o.wt` CANNOT BE**:
      `FIELD#1,-1 AS A` has two faults and the reference answers `Illegal
      function call`, not ERR 13 — where `o.wt`'s two faults are BOTH ERR 13 and
      it agrees whichever fires ([[one-row-cannot-separate-two-rules]]).
      **Knives 5 × 2, ALL TEN EXACT, both rounds identical** — and K-FW1/K-FW2
      are PARTIAL reverts (`check_fperr_only` is `check_expr_errors`' own
      fall-in entry point; `get_byte_arg` is `get_int16_checked` plus two
      instructions), so each removes exactly one clause of the rule: `d.div`
      survives K-FW1 and **`d.big` survives K-FW2**, which is what says the ERR 6
      and the ERR 5 come from different stages.
      ⚠️ Carried out of it: the `- [ ]` item directly below.

- [x] ✅ **~~`FIELD overflow` (ERR 50) AGAINST THE RECORD LENGTH IS NOT
      CHECKED~~ — SHIPPED 2026-08-19 (D-RECLEN), DENOMINATOR AND ALL.**
      [`docs/spec-basic-fldwidth.md`](docs/spec-basic-fldwidth.md) §6.5 addendum.
      `ex_field` reads `FCH_RECLENS[ch]` **inline** and raises ERR 50 when the
      running total passes it — **+28 B main page 1 (50 → 22 free)**, 0 low,
      0 sub, 0 RAM. Sited AFTER `fld_add` bumps `FLD_CUROFF` so the test reads the
      total *including* this item and needs no second add.
      📊 **`make fldwidth-acceptance` 40/40 → 47/47, deferrals 9 → 2** — the two
      original ERR-50 rows (`d.sum`, `d.sum1`, red since D-FLDWIDTH) and all five
      `r.*` rows promoted out of DEFERRED and green. **Promoting is the stricter
      move**: a deferred row cannot fail; these now can.
      🎯 **K-RC1 IS THE WHOLE ARGUMENT IN ONE CUT.** It makes the bound a
      **constant 256** — precisely the wrong rule the old battery could not
      exclude — and reddens **only** `r.over`/`r.mid`/`r.sum128`, leaving
      `d.sum`/`d.sum1` GREEN because their totals (300, 257) exceed 256 either
      way. **That is a measurement of the claim the slice rests on: the rows that
      existed before D-RECLEN were structurally incapable of separating the two
      rules.** Knives 3/3 EXACT, three distinct ROM hashes.
      🔴 **THE DECLINE'S SECOND BLOCKER WAS NEVER ONE.** "No main-side accessor to
      borrow" — but its own ≈27 B hand-count already priced an INLINE
      `FCH_RECLENS` read at 14 B, and `oo_parse_reclen` writes that same table
      inline main-side at [`basic/files.asm:283`](basic/files.asm:283). It only
      ever meant the fix could not be 3 B. **Re-read a decline's arithmetic
      before believing its prose.**
      ⚠️ ONE REFERENCE for every row (Disk BASIC; a diskless VG-8020 cannot
      express the question). Carried forward, not upgraded.

      **Filed 2026-08-08** by D-FLDWIDTH, MEASURED and DECLINED WITH NUMBERS.
      CF-3300 vs zerobas, over the default 256-byte RANDOM record:

      | row | program | CF-3300 | zerobas |
      |---|---|---|---|
      | `d.sumok` | `FIELD#1,200 AS A$,56 AS B$` — total **256** | ` 200  56 ` | ` 200  56 ` 🟢 **control** |
      | `d.sum1` | `FIELD#1,200 AS A$,57 AS B$` — total **257** | **FIELD overflow** | ` 200  57 ` |
      | `d.sum` | `FIELD#1,200 AS A$,100 AS B$` — total **300** | **FIELD overflow** | ` 200  100 ` |

      🎯 **THE BOUNDARY IS PINNED TO THE BYTE, AND NO PER-ITEM DOMAIN RULE CAN
      REACH IT** — both individual widths are inside 0..255, so D-FLDWIDTH's
      byte-argument rule is blind to these three by construction. That is why
      they are a separate rule and not a conflation.
      💰 **PRICED AT ≈27 B AGAINST A 6 B WALL** (`docs/spec-basic-fldwidth.md`
      §6.5): 14 B to fetch `FCH_RECLENS[ch]` main-side, 10 B for the 16-bit
      compare, 4 B to raise.
      💰 **RE-PRICED 2026-08-09 by D-EVALCHK** (`docs/spec-basic-evalchk.md`
      §6.5): main page 1 is now **16 B**, not 6 — so the byte half of this
      decline is **narrower but still short by 11 B**, and neither of the other
      two blockers moved. **Bytes alone were never the whole blocker and are
      still not.**
      💰 **RE-PRICED AGAIN 2026-08-19 (D-REPRICE): THE BYTE HALF IS NOW CLEAR AND
      THIS IS THE ONLY OPEN ITEM IN THE FILE OF WHICH THAT IS TRUE.** The wall is
      **64 B** at `b51bbbb` against the ≈27 B priced here (the 6 B and 16 B above
      stand as taken for their dates). 🔴 **AND IT IS STILL DECLINED**, on the two
      blockers below that never moved: there is no main-side record-length
      accessor to borrow, and **the denominator is not built** — every row above
      uses the DEFAULT 256-byte record, so nothing measured separates "checked
      against the record length" from "checked against a constant 256". The
      `OPEN … LEN=r` rows come before the 27 bytes.
      [`docs/repricing-page1-2026-08-19.md`](docs/repricing-page1-2026-08-19.md)
      §3.2.
      There is no accessor to borrow — `load_reclen`
      ([`basic/randio-body.inc:270`](basic/randio-body.inc:270)) is **sub-ROM**
      (`sub/randio.asm:47`) and not callable from `ex_field`, and `GP_RECLEN` is
      only loaded at GET/PUT time so reading it here reads a stale cell.
      🔴 **AND ITS DENOMINATOR IS NOT BUILT.** Every row above uses the
      **DEFAULT** 256-byte record, so nothing measured separates *"checked
      against the record length"* from *"checked against a constant 256"*. It
      needs `OPEN … LEN=r` rows — the disk-BASIC option surface — before any
      byte is spent.
      ✅ **THE DENOMINATOR IS BUILT AND THE RULE IS THE RECORD LENGTH —
      MEASURED 2026-08-19 (D-RECLEN)**, five `r.*` rows in
      `basic_probe_fldwidth.py` opening a NON-default record:
      `r.ok` (LEN=64, width 64) ` 64 ` on both 🟢 · `r.over` (LEN=64, width 65)
      **FIELD overflow** vs ` 65 ` · `r.mid` (LEN=64, width **200**)
      **FIELD overflow** vs ` 200 ` · `r.sum128` (LEN=128, 100+50)
      **FIELD overflow** vs ` 100  50 `.
      🎯 **`r.mid` IS DECISIVE BECAUSE 200 IS UNDER 256** — a constant-256
      implementation accepts it and the CF-3300 refuses it. The check is against
      `FCH_RECLENS[ch]`.
      💰 **AND BOTH HALVES ARE NOW CLEAR**: the wall is **50 B** page 1
      (D-LOADSWEEP) against the same ≈27 B, whose hand-count ALREADY prices the
      inline `FCH_RECLENS` read at 14 B — so **"no main-side accessor" was never
      a blocker in its own right**, only a reason the fix cannot be 3 bytes.
      `oo_parse_reclen` writes that table inline main-side at
      [`basic/files.asm:283`](basic/files.asm:283); reading it is the same shape.
      **This item is now UNBLOCKED and priced.** Rows stay DEFERRED until it
      ships. [`docs/spec-basic-fldwidth.md`](docs/spec-basic-fldwidth.md) §6.5
      addendum.
      Both rows are DEFERRED in `probes/basic/basic_probe_fldwidth.py` —
      measured, printed, never scored; a deferred row that started AGREEING
      would itself be a finding.
      ⚠️ ERR 50's message text already exists (`sub/errmsg.asm em_field_ovf`)
      and **no zerobas site raises it**, so this is a raiser, not a message.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, all three rows exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.3): `d.sumok` ` 200  56 ` on both sides, `d.sum1` and `d.sum`
      **`FIELD overflow in 20`** on the CF-3300 against ` 200  57 ` / ` 200  100 `
      here. ⚠️ Same readout trap as the `INPUT #n` item above — driven as DIRECT
      lines the CF-3300 read ` 200  0 `, an abort between the two bindings
      wearing the shape of a value. Stored program + `RUN`.

- [x] ✅ **THE `ex_width` FUNDING CARVE LANDED AT −13 B, AND THE READING
      INVERTED THE DECLINE.** Filed 2026-08-08 by D-FLDWIDTH, closed 2026-08-09
      by **D-EVALCHK** ([`docs/spec-basic-evalchk.md`](docs/spec-basic-evalchk.md),
      [`docs/evalchk-msx1-characterization.md`](docs/evalchk-msx1-characterization.md)).
      The decline rested on *"folding `ex_width` in changes `WIDTH 1/0`'s
      answer"*. **It does not.** `get_int16_checked` already ends
      `jp check_fperr_only`, so a deferred FPERR was surfaced one step later
      with the same code — `WIDTH 1/0` read **ERR 11** on the VG-8020, the
      CF-3300 **and** zerobas before a byte moved.
      🎯 **THE ROW NOBODY HAD WRITTEN WAS THE FINDING.** `WIDTH 70000+0*(1/0)`
      — a deferred fault **and** an int16 overflow in one expression — was
      `Overflow` here and `Division by zero` on **both** references, because
      `fac_to_int_strict` writes `FPERR=1` over the pending one. Same at
      `WIDTH 70000+0*SQR(-1)` (→ `Illegal function call`, a **different** code,
      which is what makes it a rule rather than "div-zero is special"), and at
      `CLEAR` and `LOCATE`. **The carve was not free — it was a fix that also
      returns bytes.**
      Landed: `eval_int16_checked` (8 B) + `eval_byte_checked` (5 B) +
      `gba_byte` (a label, 0 B) — **two entry points because there are two
      coercions**, and they nest. Folded `ex_width` (−10 B), `ex_clear` (−10 B)
      and `exf_item` (−6 B). **Net −13 B; main page 1 3 B → 16 B.**
      `width-acceptance` 91/94 → **94/94** on three sides; knives 5×2 **all
      twelve exact**.

- [x] ✅ **A −29 B CARVE EXISTED IN `loc_next` — TAKEN 2026-08-09 BY D-LOCARG**
      ([`docs/spec-basic-locarg.md`](docs/spec-basic-locarg.md),
      [`docs/locarg-msx1-characterization.md`](docs/locarg-msx1-characterization.md)),
      at **exactly −29 B**, and it funded the +7 B `DIRECTF` derive below: main
      page 1 **0 B → 22 B**. `make locarg-acceptance` is a new 45-row gate,
      **38/45 → 44/45**, and `make missing-acceptance` held at 214/214.
      🔴 **THE DENOMINATOR THIS ITEM DEMANDS WAS ALREADY BUILT WHEN IT WAS
      FILED.** Every axis named below as missing — row/column, omitted
      arguments, the `CON_LASTROW` clamp, `CSRLIN`/`POS` read-back — was already
      in `make missing-acceptance`, 214 recorded rows. The one axis that
      genuinely did not exist was the deferred expression error itself, and
      `grep LOCATE probes/` is the command that would have said so. **A declined
      carve's stated blocker can name work that already exists**, because the
      person pricing it is reading the file the carve is in, not the gate list.
      🎯 `LOCATE 70000+0*SQR(-1),3` is what made it a rule rather than "division
      by zero is special": it faults with a **different** code (5, not 11)
      through the identical shape, and both references report that code.
      **The original filing, for the record:**

- [x] 💰 ~~**A −29 B CARVE EXISTS IN `loc_next`, IT FIXES A MEASURED DIVERGENCE,
      AND IT IS DECLINED ON SCOPE — NOT ON A MISSING READING.**~~ Filed
      2026-08-09 by D-EVALCHK
      ([`docs/spec-basic-evalchk.md`](docs/spec-basic-evalchk.md) §6.6).
      [`basic/missing.asm:237`](basic/missing.asm:237) is the FOURTH copy of
      `call eval` / inline `TMISMATCH` test / checked coercion — except the
      coercion is **written out in full** (17 B) instead of called. Replacing
      the lot with `call eval_byte_checked` is **−24 B**, and orphans
      `loc_illegal` for **−5 B** more.
      🔴 **AND IT IS A DIVERGENCE, MEASURED ON BOTH REFERENCES:**

      | program | VG-8020 | CF-3300 | zerobas |
      |---|---|---|---|
      | `LOCATE 70000+0*(1/0),1` | **ERR 11** | **ERR 11** | **ERR 6** |
      | `LOCATE 1/0,1` | ERR 11 | ERR 11 | ERR 11 🟢 control |
      | `LOCATE 70000,1` | ERR 6 | ERR 6 | ERR 6 🟢 control |
      | `LOCATE "5",3` | ERR 13 | ERR 13 | ERR 13 🟢 control |

      ⚠️ **WHY IT IS NOT IN D-EVALCHK.** The 17 B block exists because that
      file's header claimed `get_byte_arg` *"CANNOT BE CALLED here"* — the
      abort chain "PRINTS AND RETURNS". `4d35b6d` retired that (`fre_abort_low`
      does `ld sp,(SAVSTK)`; `raise_error_hl`'s trap arm always did), and **the
      header is corrected in D-EVALCHK's commit** — but taking the bytes means
      DELETING a defensive apparatus (`LOC_RET`, the parked frame,
      `loc_illegal`) on the strength of that refutation. That needs its own
      knife — put the frame back and show the aborts still land — and LOCATE's
      own denominator: row/column, omitted arguments, the `CON_LASTROW` clamp,
      `CSRLIN`/`POS` read-back. The width probe has none of it. A −29 B carve
      is exactly the size that should not ride along in someone else's slice.
      💰 Priced, reading taken, denominator NOT built.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, all four rows exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.4): `LOCATE 70000+0*(1/0),1` is `Division by zero` on both references
      and `Overflow` here, with `LOCATE 1/0,1`, `LOCATE 70000,1` and
      `LOCATE "5",3` green on all three sides.

- [x] ✅ **CLOSED 2026-08-09 BY D-TMFP — AND THE FILED RULE WAS WRONG.**
      ([`docs/spec-basic-tmfp.md`](docs/spec-basic-tmfp.md),
      [`docs/tmfp-msx1-characterization.md`](docs/tmfp-msx1-characterization.md),
      gate `make tmfp-acceptance`, 50 rows / 3 sides, 49 scored + 1 deferred.)
      It is **not** that a numeric fault outranks a type fault — it is that
      **whichever fault happened FIRST is reported**, because the reference
      raises eagerly and the second fault never occurs. `WIDTH 0*(1/0)+(A$<5)`
      reads 11 and `WIDTH (A$<5)+0*(1/0)` reads 13 on **both** references; swap
      the operands and the answer swaps. `WIDTH 0*SQR(-1)+(A$<5)` reads **5**, a
      different code, which is what makes it order and not rank.
      🔴 **THE FILED DECLINE WAS WRONG ON BOTH CLAUSES.** (a) §5.1 of
      `spec-basic-evalchk.md` was **not** frozen on `PRINT #A$,"X"` — that is
      D-BADFNUM §6's row, about `eval_chan`. §5.1's row is
      `WIDTH (A$<5)+0*(1/0)`, which discriminates perfectly, and it **refutes**
      the filed reorder: no static test order satisfies both rows. (b) The
      denominator was not four callers but **eighteen sites** — twelve
      `check_expr_errors` call sites, two further hand-rolled copies of the same
      ordering (`check_expr_errors_popbc`, `ex_let_arr`) that a
      `check_expr_errors` fix cannot reach, and four readers of `TMISMATCH` that
      never consult `FPERR` (`fch_check`, `ev_ff_ckpdl`, `ev_mc_arg_checked`,
      `sfr_argok`).
      🎯 Fixed at the **writer**, not the readers: `type_mismatch_set` is
      `TMISMATCH`'s only writer and `exec_stmt` clears both flags together, so a
      non-zero `FPERR` at arming time means the numeric fault came first — it
      does not arm. **One site, +5 B**, main low region (11 → 6 B). 21 divergent
      rows across nine callers closed; `locarg-acceptance` 44/45 → **45/45** with
      its DEFERRED dict emptied.

- [x] ✅ **THE TWO DEFERRED-ERROR FLAGS ARE ONE CONCEPT — COLLAPSED INTO A
      SINGLE SET-IF-EMPTY PENDING-ERROR CODE.** Filed 2026-08-09 by D-TMFP,
      **DONE 2026-08-09 by D-PENDERR**
      ([`docs/spec-basic-penderr.md`](docs/spec-basic-penderr.md),
      [`docs/penderr-msx1-characterization.md`](docs/penderr-msx1-characterization.md)).
      `TMISMATCH` retired; new gate `make penderr-acceptance` **61/61 on three
      sides** (44/61 before the slice — 17 rows moved, all from wrong to right).
      **−48 B: low 6 → 14, page 1 22 → 62**, hand count exact on both walls.

      🎯 **IT FUNDED ITSELF SEVERAL TIMES OVER, AND THE SCOUT MATTERED.** The
      collapse alone is −56 B of readers, but it is only SOUND once every writer
      is set-if-empty, which is one shared 14 B routine (`penderr_set`) and a
      `call` that is byte-for-byte the size of the `ld (FPERR),a` it replaces at
      all twenty-four stores. Pricing the deletion without the writer rule would
      have priced a 17-row regression.

      🔴 **AND THE REASON GIVEN FOR THE WRITER RULE WAS WRONG.** Both this item
      and the spec's first draft argued the merge would regress `dfe-tmfp`
      (`WIDTH (A$<5)+0*(1/0)`) to ERR 11. Knife K-PE2 deletes set-if-empty
      entirely and that row **stays at 13** — after a deferred TYPE fault zerobas
      never raises a second one from the rest of the expression, so there was
      never a clobber to prevent. The 17 rows that do need it are the
      numeric-vs-numeric pairs, the `r.hex` family, the parse-time rows and the
      three widened readers. Right conclusion, wrong evidence; see
      `spec-basic-penderr.md` §3.2.

      ⚠️ Two temperings in this item's own text were also wrong on measurement:
      the KIND-needing readers did **not** become `cp 10` (all three are WIDENED
      to "is anything pending", byte-neutral, and both references agree that is
      the correct reading — `PRINT LOF(0*(1/0)+1)` is ERR 11, not ERR 59); and
      `ERRMARK` was left out, as directed, correctly.

- [x] ✅ **`str_arg_empty` OVERWRITES A PENDING `FPERR`** — the clobber half.
      Filed 2026-08-09 by D-TMFP (§8 defect 2), **DONE 2026-08-09 by D-PENDERR**
      for **zero marginal bytes** instead of the +6 B priced here: routing that
      store through `penderr_set` like every other writer is what fixed it.
      `r.hex` reads ` 11 ` on all three sides, `r.oct` / `r.str` /
      `PRINT HEX$(…)` with it, and `make tmfp-acceptance` goes **49 scored + 1
      deferred → 50 scored, 50 agree, deferred dict EMPTY**. Knife K-PE4 restores
      the bare store and reddens exactly those five rows and nothing else.

- [x] ✅ **`str_fn_radix`'S CURSOR AFTER A STRING-COMPARE MISMATCH —
      CHARACTERISED, AND DELIBERATELY LEFT ALONE.** Filed 2026-08-09 by D-TMFP
      (§8 defect 1), restated by D-PENDERR (§8), **CLOSED 2026-08-09 by
      D-STMTPEND** ([`docs/spec-basic-stmtpend.md`](docs/spec-basic-stmtpend.md)
      §2,
      [`docs/stmtpend-msx1-characterization.md`](docs/stmtpend-msx1-characterization.md)
      §2).

      **MEASURED, not inferred.** Freezing zerobas at `type_mismatch_set` and
      reading `IX` out of `TOKBUF` puts the cursor on the RHS **operand** — `Q$`
      and `<` consumed, `5` not — where the coherent landing place is the inner
      `)` one token later. `ers_rhs_mismatch` restores the cursor it pushed
      *before* asking `str_eval` to read the RHS; `evr_mismatch` (`5<A$`) does
      the same. The bare-LHS form `HEX$(A$)` lands correctly and is the control.

      🎯 **AND IT SETTLED THE QUESTION `spec-basic-penderr.md` §3.2 DECLINED TO
      ANSWER.** Breaking at `penderr_set`, the FIRST code written for
      `HEX$((A$<5)+0*(1/0))` is 4 (`str_arg_empty`) and never 2 (`fp_div`); for
      `WIDTH (A$<5)+0*(1/0)` `penderr_set` is never called at all, against
      controls where it is. So after a deferred type fault **the rest of the
      expression is never evaluated** — not "evaluated and did not fault".

      🔴 **THE CURSOR IS A ROUTE, NOT THE RULE, WHICH IS WHY IT IS NOT FIXED.**
      A stranded cursor makes a well-formed statement look malformed; what
      happened next was decided by two places that threw the pending code away,
      and *those* are what D-STMTPEND fixed. Take the string out entirely and the
      same holes are there (`SCREEN 0*(1/0)` lost a division by zero with no
      comparison anywhere). Straightening the cursor would need the mismatch path
      to consume an arbitrary trailing operand — which the references never do
      either, since they raise eagerly — and would close none of the `s.*` rows.
      Held by `make stmtpend-acceptance` (56/58 scored + 2 deferred; 36/58
      before).

- [x] 🔴 **THE STATEMENT BOUNDARY IS TOO LATE FOR A DRIVER WITH A SIDE EFFECT.**
      Filed 2026-08-09 by D-STMTPEND; ✅ **CLOSED 2026-08-10 by D-SCRERR**
      ([`docs/spec-basic-screenerr.md`](docs/spec-basic-screenerr.md)).
      `ex_screen` validates the mode through `eval_byte_checked` **before**
      `CHGMOD`, so a deferred fault never applies the mode and the `RUN` echo
      the untrapped reading anchors on survives. `u.scr.dz` is **un-deferred**:
      `make stmtpend-acceptance` is now **57/57 scored + 1 deferred** (was 56/58
      + 2). ⚠️ **The general statement stands** — the boundary is still by
      construction too late for any driver with a side effect; what changed is
      that `ex_screen` no longer leans on it. `DEFUSR`/`FOR` have no side effect
      to be too late for; a future driver that does will need the same
      per-driver treatment.

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

- [ ] ⚠️ **THE THIRD TRAILING `SCREEN` ARGUMENT'S DOMAIN IS UNMEASURED.**
      Filed 2026-08-10 by D-SCRERR. Slot 1 (sprite size) is pinned to 0..3 and
      slot 2 (key click) to 0..255; `scr_extra` treats slots 3+ identically to
      slot 2, so the open risk is a reference that narrows a later one.
      `SCREEN 1,,,300` — one row, no scouting done.

- [ ] ⚠️ **`a.spr` IS BLIND TO A CUT THAT STOPS THE SPRITE SIZE BEING APPLIED.**
      Filed 2026-08-10 by D-SCRERR ([`docs/spec-basic-screenerr.md`](docs/spec-basic-screenerr.md)
      §9), found by knife K-SE5, which reddened `a.sprslot1` and left `a.spr`
      untouched. `SCREEN 1,3` reads only the ERROR CODE, and a size that is
      never applied raises nothing. Harmless — `a.sprslot1` reads
      `LEN(SPRITE$(0))` and covers it — and **not** a reason to change `a.spr`,
      which is the row that says an in-domain size is accepted. Recorded because
      the same shape recurs in any row that tests an effect by its absence of an
      error.

- [x] 🔴 **`LINE (0,0)-((A$<5),1)` IS ERR 5 HERE AND ERR 13 ON BOTH REFERENCES.**
      Filed 2026-08-09 by D-STMTPEND, the `c.line.tm` deferred row.
      ✅ **CLOSED 2026-08-11 by D-LINERR**
      ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md),
      `make lineerr-acceptance` **106/106 from 55/106** + 2 deferred, both
      references agreeing on every scored row; `stmtpend-acceptance`'s DEFERRED
      dict is now EMPTY). ⚠️ Those are the figures **on the day this closed**;
      the gate is **140/140 + 2 deferred over 142 rows** since D-PAINTSEED and
      D-GIRDOM the same evening. A row count quoted in a closed item is a
      timestamp, not a baseline — run the gate.
      🔴 **AND THE DIAGNOSIS FILED HERE WAS WRONG.** This entry said *"LINE
      raises its own `Illegal function call` eagerly from inside its coordinate
      parse"*. **There is no ERR 5 anywhere in `parse_coord`.** The refusal was
      `ex_line_gfx`'s own opening `cp 2`, three instructions in, before any
      coordinate was looked at, and the row runs in the boot default SCREEN 0 —
      so zerobas answered ERR 5 to a statement whose coordinates it never
      evaluated. **Reading the site was enough to refute it**; no emulator and
      no reference were needed. The wrong diagnosis also pointed at the wrong
      shape of fix — a per-driver patch in a coordinate walk — where the real
      rule is an ORDERING one at **five** verbs: *a graphics statement moves the
      work area to the point its MANDATORY arguments resolve to and refuses a
      wrong SCREEN mode immediately after that, before the first OPTIONAL
      argument is looked at.*
      🔴 **It became a five-verb rule because a NEGATIVE CONTROL diverged**:
      `n.pset0` was written as "the same question at a verb this slice claims
      nothing about" and came back identical, so the fix is one shared leaf
      (`gfx_point_gate`) and not one edit at LINE. **−26 B** (page 1 48 → 74 B),
      because the old code said the same thing five times.
      🎯 Two corollaries fell out: a LINE/PSET colour is a **0..15 range check**
      (`PSET(20,21),16` → ERR 5 on both references), not the silent `and $0F`
      mask that shipped; and a list that ENDS where the colour was required is
      **Missing operand (ERR 24)** — but one field along, at the box slot, the
      same two shapes are ERR 2.

- [x] ✅ **CLOSED 2026-08-22 (D-SCREEN3) — MULTICOLOUR LANDS, MINUS PAINT.**
      [`docs/spec-basic-screen3.md`](docs/spec-basic-screen3.md). PSET, PRESET,
      POINT, LINE, LINE,B/BF, CIRCLE and DRAW all agree with **both** references
      in SCREEN 3. 💰 **main page 1 8 → 4 B (4 B), sub page 0 3299 → 3156 B
      (143 B)** — both UNDER the scout's ~6 B / ~170–280 B estimate, because MC
      has no colour table so the arm replaces the clash RMW as well.
      🎯 **DRAW'S GATE PAID FOR PAINT'S**: DRAW carried 6 B of inline
      `ld a,(SCRMOD)/cp 2/jp nz,gfx_err5` — the shared gate's own test spelled out
      again. A 3 B `call gfx_mode_gate` keeps D-DRAWERR's measured ordering and
      freed the bytes; main cost fell 7 B → 4 B.
      ✅ **AND IT CLOSED THE SILENT WRONG ANSWER**: `POINT` had no mode gate, so
      SCREEN-3 `POINT` read the G2 address model against MC VRAM and returned a
      plausible wrong colour with no error (`1` vs the references' `4`). The same
      branch that implements the feature fixes it.
      🔴 **PAINT IS EXCLUDED ON PURPOSE — see its own item below.**

  <details><summary>the original filing, kept for the record</summary>

- [x] 🔴 **SCREEN 3 DRAWS ON BOTH REFERENCES; zerobas raises ERR 5.**
      Filed 2026-08-11 by D-LINERR
      ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md) §6.4), rows
      `m.s3` and `v.pset3` of `make lineerr-acceptance`, both **measured and
      deferred**: `LINE (11,12)-(20,21)` and `PSET(20,21)` in SCREEN 3 read
      ` 0 , 20 , 21 ` on the VG-8020 and the CF-3300 and ` 5 , 20 , 21 ` here.
      A **WHOLE-FEATURE gap**, not an error-surface defect — zerobas has no
      SCREEN-3 pixel op at all, so its `cp 2` refuses the mode, and the refusal
      is correct for every mode zerobas implements. Closing it needs a second
      rasteriser and a second address/clash model (SCREEN 3 is 64×48
      multicolour, not a bitmap), i.e. a graphics slice of its own. Priced at
      nothing; not scouted. Both rows stay printed and marked `....`, excluded
      from the tally in **both** directions.
      ✅ **SCOUTED 2026-08-22 —
      [`docs/screen3-scout-2026-08-22.md`](docs/screen3-scout-2026-08-22.md).**
      💰 **~6 B main page 1 + ~170–280 B sub page 0 — IT FITS IN BOTH WALLS AS
      THEY STAND** (8 B / 3299 B, 2026-08-22). This item was blocked on a page-1
      carve it does not need.
      🔴 **THREE OF THE CLAIMS ABOVE ARE WRONG, ALL IN THE CHEAP DIRECTION**, and
      the discriminating measurement is in §2 of the scout:
      (1) **The BASIC coordinate space is 0..255 × 0..191, IDENTICAL to
      SCREEN 2** — 64×48 is the HARDWARE cell size, and logical `(x,y)` addresses
      cell `(x>>2, y>>2)`. `PSET(0,0),7` then `POINT(3,3)` reads **7** and
      `POINT(4,4)` reads **4** on both references; `PSET(256,192)` is the same
      silent no-op SCREEN 2 has. So `gfx_in_range` needs NO change — that was the
      only part of the cost sitting on the binding wall.
      (2) **There is no second CLASH model** — multicolour has no colour table,
      so `gfx_color_rmw` has no counterpart. The twin is CHEAPER than the
      original, not dearer.
      (3) **It is not a whole-feature gap**: the mode switch already works
      (`ex_screen` accepts 0..3 and calls CHGMOD), **sprites already work in
      SCREEN 3** (they gate on `or a`, not `cp 2`), the VDP register layer already
      encodes multicolour, and the 464 B of Bresenham/line/box are mode-free. The
      gap is the address model and the pixel primitives — 280 B of measured
      SCREEN-2-specific code to twin.
      ✅ **THE MC VRAM LAYOUT IS NOW DERIVED (§6, same day, both references)** —
      the largest single unknown in the price is closed. `BASE()` says the tables
      are name **$0800**, generator **$0000**, colour unused; the generator fills
      with **$44** (both nibbles = background 4); and the address model is
      **`addr = (cy>>3)*256 + (cx>>1)*8 + (cy&7)`** with `cx=x>>2, cy=y>>2`, high
      nibble for even `cx` and low for odd. **Shifts only — no table, no
      multiply**, the same shape and roughly the same size as `gfx_calc_addr`'s
      33 B, and it replaces the clash RMW as well since a nibble write needs no
      colour byte. Verified against **three predictions written before the run**
      (71 / 116 / 71, both references, including the far corner at 1535).
      🔴 One sweep row was an **APPARATUS TIMEOUT recorded as one**: cell (63,47)
      is the LAST byte, so its scan ran all 1536 iterations and returned
      `<NO OUTPUT>` on both sides. A direct VPEEK at the predicted address
      replaced it — and is the stronger row.
      🔴 **The BASE() indices were wrong first, and the CONTROL AGREED WITH THE
      SUBJECT**: groups are 0-4/5-9/10-14/15-19, so SCREEN 1 and SCREEN 2 (whose
      nominal bases are identical) were being compared. The control is now the
      SCREEN-0 group, whose layout differs.
      ⚠️ **Still unmeasured (§7)**: PAINT's run scan, DRAW, CIRCLE aspect,
      `LINE ,B/BF`'s fast path, and **what the $0800 name table must contain**
      (its address is measured, its contents are not).

  </details>

- [x] ✅ **`PAINT` NOW WORKS IN SCREEN 3** (D-PAINTMC, 2026-08-22,
      `docs/spec-basic-paintmc.md`). 💰 **77 B of sub page 0, and 6 B of main
      page 1 RECOVERED** (PAINT rejoins `gfx_point_gate`; the narrow
      `gfx_mode_gate_s2` entry is retired).
      🎯 **THE DIAGNOSIS FILED HERE WAS RIGHT AND THE REMEDY WAS WRONG.** This
      item said the fix was "a flood engine that does not re-test painted
      cells", and named `gfx_paint_inside`'s own-design `== C` stop as the
      suspect. The fixture that decides it is a barrier ALREADY COLOURED C
      inside an open area with a border colour that appears NOWHERE:
      `LINE(0,40)-(255,40),9 : PAINT(10,10),9,15`. **Both references stop at
      it** — `POINT(10,0)`=9 (it spread) and `POINT(10,60)`=4 (it stopped) — in
      SCREEN 2 *and* in multicolour. The own-design stop is FAITHFUL, and it had
      been carried as "NOT measured by the pinned battery either way" since G5.
      The only thing that had to change was the walk's **PITCH**: 4 in MC, so a
      step always lands on a cell the fill has not touched.
      🔴 **AND ONE PREDICTION WAS WRONG: the SEED rule differs by mode.**
      `PAINT(20,20),9,15` with the seed exactly on a `,B` box drawn in 15 floods
      in SCREEN 2 (the shipped `seed_on_wall_pixel` rule) and paints **nothing at
      all** in multicolour — `POINT(20,20)`=15, `POINT(40,40)`=4 on both
      references. It is the `== B` half only: a seed already coloured C floods
      normally in MC (and, mirror-image, does not in SCREEN 2 — see the two new
      items below).
      💰 The pitch is CACHED in `GFX_PPITCH` (0 B — it aliases G8's dead
      `VDP(n)=` index cell) because asking `SCRMOD` at each of the seven step
      sites cost **+35 %** on every SCREEN-2 PAINT (3,205,330 -> 4,339,041 Z80
      steps on `tests/test_graphics.py`'s full-screen case; 3,352,745 = +4.6 %
      cached). 🔬 5 knives, 5 distinct predicted row sets, parser calibrated on
      clean / planted / deleted logs first.

- [x] ✅ **A SCREEN-2 `PAINT` WHOSE SEED IS ALREADY THE PAINT COLOUR NOW DOES
      NOTHING** (D-PAINTS2SEED, 2026-08-22, `docs/spec-basic-paints2seed.md`).
      💰 **4 B of sub page 0**; `basic-reloc.rom` byte-identical (tenant-only).
      🎯 **The rule is BROADER than the case that found it, and measured that
      way**: the references refuse a seed whose EFFECTIVE colour equals C,
      **drawn or not**. Three geometries on both machines — an open screen
      (`sc2.up`=4), a bounded box read at its interior (`su2.drawn`=4), and an
      UNDRAWN seed with C == the background (`su2.row.cbg`=9, where a flood would
      have ERASED the witness pixel via the `c==bg -> clear the bit` clash).
      🎯 **AND IT IS THE MIRROR OF MULTICOLOUR'S**, which refuses `== B` and
      floods on `== C`. Every cell of that 2x2 is measured; no single predicate
      produces it, so the implementation is one comparison whose COMPARAND is
      picked by mode.
      🔴 **THE FIRST DRAFT READ THE SEED'S COLOUR OUT OF REGISTER GARBAGE** —
      `gfx_paint_read` takes D=y/E=x in REGISTERS and does not read
      `GFX_PTESTX/Y`; the MC gate had been getting that loading for free from
      `gfx_paint_passable`. It was deterministic, so **8 of the 10 shipped PAINT
      rows still passed**, including `mc_border_is_bg`, whose whole job is that
      gate. The two that failed included one that had been PASSING before the
      edit, which is what made the cause unambiguous. The correct version is also
      **4 B smaller** than the draft.

- [x] ✅ **`PAINT`'s BORDER ARGUMENT IS RANGE-CHECKED ON THE REFERENCES AND NOT
      HERE, AND THE BOUND DEPENDS ON THE MODE** — **CLOSED 2026-08-22 by
      D-PAINTBORD**, `docs/spec-basic-paintbord.md`. Filed by D-PAINTMC §7.

      🎯 **`B` is 0..255 in SCREEN 2 and 0..15 in MULTICOLOUR; outside that,
      ERR 5** — and the check is on the FULL int16, not the stored byte (256 is
      `$0100`, low byte `$00`).
      ⚠️ **THE ORDERING WAS THE MISSING MEASUREMENT AND IT WENT THE OTHER WAY
      FROM THE CODE.** `PAINT(10,10),9,16,` in SCREEN 3 is **ERR 5** on both
      references, not ERR 2 — the domain BEATS the 4th-argument grammar — while
      the in-domain twin `,9,15,` on the same program is ERR 2 and is what makes
      that reading mean anything (rows `od3.b16c` / `od3.b15c` / `od2.b256c` /
      `od2.b16c`, `scratchpad/paintmc_probe.py` §10). So the check replaces the
      inline store, ABOVE the grammar test.
      💰 **PRICED AT ~21 B AND DECLINED; MEASURED AT 6 B** of main page 1
      (10 → 4 B, 2026-08-22). The filed shape was a standalone helper beside
      `gfx_store_colour_checked`; the two checks are in fact ONE leaf with a
      different constant (`gfx_chk_dom`, a high-nibble mask — `$F0` = 0..15,
      `$00` = 0..255, with `or d` folding the negative/>255 half in free), which
      also rewrote `gfx_store_colour_checked` (−5 B) and `g8_fn`'s VDP/BASE index
      check (−3 B). The carve that funds the rest: `gfx_absent` was
      byte-identical to `gfx_err5` and is now `equ` it (−5 B), on the
      `err_illegal_fn` precedent in `basic/interp.asm`.
      ✅ Ten rows ship in `basic_probe_graphics.py` PHASE J, both modes.
      ⚠️ And `border16_flood_ok` is STRENGTHENED: its `C = 1` was the background
      under `LINIT`, so the reference refused the seed and all four sample points
      read 1 either way — a coverage row whose geometry could not reach its case.
      `C = 9` makes the flood real.
      🔴 Four doc-debt sites INVERTED, not deleted: `ep_parse_b`'s own comment,
      `spec-basic-graphics-g5.md` §3/§5/§11, and `GFX_B`'s sysvar comment.

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

- [x] ✅ **`POINT` IN SCREEN 3 IS A SILENT WRONG ANSWER** — **STALE. CLOSED
      2026-08-22 BY RE-MEASUREMENT**, `scratchpad/point3_recheck.py`. Filed the
      same day by the SCREEN 3 scout §5, and shipped hours later by **D-SCREEN3**,
      which gave `gfx_point` its `gfx_is_mc` branch to `gfx_point_mc`. Nobody
      re-read the list.

      The filed row, verbatim, re-run on both references and on zerobas from a
      clean build: `SCREEN 3` then `POINT(30,30)` with nothing plotted reads
      **4 / 4 / 4**. It was filed as *"4 on the VG-8020 and the CF-3300 and 1
      here"*. Two more rows (`PSET(30,30),9` and `PSET(33,37),12`, the second off
      the 4x4 lattice corner where the two address models disagree about which
      byte holds the pixel) also agree on all three sides, and SCREEN-2 twins of
      both shapes agree as controls.
      ⚠️ **THE TWO `PSET`-THEN-`POINT` ROWS ARE NOT INDEPENDENT EVIDENCE** and
      are not what closes this: a write/read round trip through ONE address
      function cannot falsify that function — `docs/spec-basic-screen3.md`'s own
      recorded lesson. What closes it is the UNDRAWN row, which is the filed
      claim itself, plus PHASE H-MC's nine POINT-sampled multicolour fill rows,
      whose fills come from the tenant's own walk.
      📏 **THE FIFTH TIME A LOUD OPEN ITEM HAD ALREADY SHIPPED.** The pattern is
      not that the item was wrong when written — it was right — but that a slice
      aiming at something else closed it and nothing re-read this file.
      **When a slice lands, grep this list for what it just shipped.**

- [x] ✅ **PAINT'S OFF-SCREEN-SEED ERR 5 versus ITS WRONG-MODE ERR 5.** Filed
      2026-08-11 by D-LINERR, CLOSED the same day by **D-PAINTSEED**
      ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md) §9). The work
      area moves FIRST: `PAINT(300,100)` leaves GRPAC *and* GXPOS on the raw
      unclipped (300,100) on both references before raising ERR 5, in SCREEN 2
      as well as SCREEN 0 — so the seed test moved BELOW `gfx_point_gate`. 16
      rows added (`p.*`, `w.paint*.off`), 13 of them red before; net **zero
      bytes**; 3 knives, 6 of 6 EXACT. ⚠️ The seed test versus the GATE stays
      genuinely unordered and is not claimed: both raise ERR 5 with the same
      work area whichever runs first. 🔴 And the row this item NAMED could not
      have settled it — K-PS2 deletes the seed test and `PAINT(300,100)` in
      SCREEN 0 stays green, because the mode gate above the hole answers the
      same; the SCREEN-2 twin is what carries the measurement.

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

- [x] ✅ **`gfx_in_range`'s DOMAIN AT ITS OTHER TWO CALLERS.** Filed 2026-08-11
      by D-PAINTSEED, CLOSED the same day by **D-GIRDOM**
      ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md) §10). The
      domain AGREES at all three callers — `0..255 × 0..191`, edge `(255,191)`
      accepted, both off-by-ones refused, negatives stored raw as `65535` — on
      both references. 🔴 **But two rows added alongside it did NOT agree, and
      they are about `POINT`, not the domain:** `ev_f_point` marshalled its
      target to the tenant through `GXPOS/GYPOS`, a BASIC-visible work-area
      cell, so `V=POINT(20,21)` moved half the work area where both references
      move neither half (`w.pt.on`, `w.pt.step`). Now marshalled through its own
      `GFX_PTX/GFX_PTY`; **net zero bytes on both sides of the slot boundary**;
      3 knives, 6/6 EXACT. 🔴 `v.point0` — promoted as the control that keeps
      the `v.*` class honest — could never have caught it: it reads `GRPAC`,
      which `POINT` does not touch on any of the three sides.
      🔴 **AND `docs/spec-basic-graphics-g2.md` §5 CALLED THIS QUESTION
      "unpinned and low-value" IN WRITING**, naming only `GRPAC`; the cell it did
      not name is the one the implementation then used, because the `$E030` block
      header says coordinates are marshalled through `GXPOS/GYPOS` since "the
      resident stub writes them anyway" — true of every op in that block except
      the read-only one. Corrected in place.

- [x] 🔴 **`DRAW`'s BOOT-DEFAULT SCALE STATE IS NOT `S4`, AND ZEROBAS TREATS IT
      AS IF IT WERE.** Filed 2026-08-11 by D-DRAWERR; ✅ **CLOSED 2026-08-11 by
      D-DSCALE** ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md)
      §12, `make lineerr-acceptance` **210 rows, 208/208 + 2 deferred**).
      `GFX_DSCALE` now boots at **0**, a sentinel `gdo_s` can never write
      because it maps `S0` to 4, and `gdrw_scale` returns the count untouched
      when it reads 0. Both rows below are **undeferred and green**.
      🎯 **THE `GFX_DANGLE` HALF WAS ASKED AND THE ANSWER IS NO SENTINEL.** The
      angle has no wrap of its own, so `d.a0.32k` borrows the SCALE's wrap:
      `DRAW"A0BU32767"` still moves the full count on both references, as does
      `DRAW"C1BU32767"`, and `DRAW"BU32767S4"` does not let a trailing `S` reach
      back over the `U`. The cells are independent and an explicit `A0` is the
      boot state. The fork was written down with both branches priced BEFORE the
      run, and the rows chose the cheap one.
      🔴 **THE SWEEP FOUND A SECOND DEFECT, IN THE ARITHMETIC THE RESIDUAL
      CALLED CORRECT, AND IT WAS A ROW WRITTEN AS A CONTROL THAT FOUND IT.**
      `d.s4.8k` (`DRAW"S4BU8192"`) was the green control for the new default
      rows and diverged: the product `$8000` is **+32768** on both references
      and −32768 in `gdrw_scale`, so the sign boundary is `$8001`. Pinned at
      five `(n,S)` pairs reaching the same product plus the neighbours `$7FFC`
      and `$8004`. +4 B.
      🔴 **AND THE ROW DESIGNED AS THE SHARPEST DISCRIMINATOR READS NOTHING.**
      `d.def8k` (`BU8192`) was written as "the smallest count that separates the
      two states"; at a *correct* `S4` the two states COINCIDE there. The
      minimal discriminator is **8193**. A model has a blast radius too — the
      notebook's nineteen readings never landed on `$8000`.
      🔴 **AND `d.defneg` WAS GREEN AT HEAD FOR THE WRONG REASON** — the two
      defects cancel exactly at `DRAW"BU-8192"`. Only a knife reinstating ONE of
      them can say so.
      The original filing follows, unedited:

          d.def32k  DRAW"BU32767"    refs  0 , 7 , 32773    zb  0 , 7 , 5
          d.lit2    DRAW"BU40000"    refs  0 , 7 , 25540    zb  0 , 7 , 58308

      From boot both references move the FULL count; after an explicit `S4` they
      wrap exactly as `scratchpad/g6_draw_notes.md` §3 models
      (`distance = signed16((n×S) mod 65536) ÷ 4`), and zerobas matches them
      there — rows `d.s4.32k` / `d.s4.40k` / `d.s8.10` / `d.s2.10` all AGREE.
      🔴 **THE G6 NOTEBOOK'S FIVE FITTED POINTS ARE ALL CORRECT AND THE
      GENERALISATION IS NOT**: every one was taken after an explicit `S`, so the
      class it fitted never contained the default, and `S4` was assumed to *be*
      the default because the multiply is the identity everywhere except the
      wrap. A large count is the ONLY observable that separates the two states.
      ⚠️ Not folded into D-DRAWERR: it changes what DRAW **draws**, not what it
      refuses (`graphics-acceptance` and G6 own that surface), and it needs a
      sentinel that `S4` cannot collide with — `GFX_DSCALE` is initialised to 4
      at cold boot (`basic/interp.asm`) and `gdo_s` maps `S0` to 4, so
      "never set" currently has nowhere to live. `gdrw_scale` already has a
      `jr z` arm for a zero cell, which is the natural home.

- [x] 🔴 **NOTHING SWEEPS THE `$8000` FIXED POINT AT THE OTHER SIGNED-16
      DIVIDES.** ✅ **CLOSED 2026-08-11 by D-NEG8K**
      ([`docs/fixpoint8000-msx1-sweep.md`](docs/fixpoint8000-msx1-sweep.md),
      `make float-acceptance` + `make math-acceptance` both rc=0).
      **THE DENOMINATOR IS MACHINE-PRODUCED, NOT HAND-LISTED**
      (`scratchpad/negscan.py`): 97 asm files / 51 301 lines scanned, **18
      files with >=1 candidate, 79 files with a MEASURED ZERO** (incl.
      `program.asm` 2705, `str-engine.asm` 1754, `interp.asm` 1728). 15 negate
      sites + 25 shift sites, every one classified in writing.
      🎯 **THE STORAGE HALF IS AN EMPTY CLASS** — all 21 disk/tape/FAT shifts
      are on genuinely unsigned quantities and not one is preceded by a
      negate. The tree's ONE `sra` (`fp_exp`, `n8>>3`) is the single place a
      signed shift was written as a signed shift.
      🎯 **THE TREE ALREADY KNEW ABOUT `$8000` IN FOUR PLACES** and none of
      them was reachable from the residual's own grep: `ABS(-32768%)`,
      `-32768\-1`, `combine_mul`'s asymmetric 32767/32768 bound, and
      `combine_pow`'s. The gap was **unary minus**, which sits between them
      and had no escape.
      🔴 **AND THE ROW WRITTEN AS THE CONTROL THAT WOULD INDICT THE DEFECT
      DIVERGED THE OTHER WAY** — `0-cint(-32768)`: reference `-32768`,
      zerobas `32768`. Binary `-` with an `$8000` RHS **wraps and never
      promotes** on the reference (measured at a = 0/1/100/32767), while
      unary `-` **does** promote. zerobas had BOTH backwards. Two defects
      either side of one fixed point; the second would never have been
      looked for. Fixed at both: **+6 B page 1, +9 B low region** (walls
      14→**5** / 73→**67**, predicted exactly).
      🔴 **TWO OF THE FOUR DISCRIMINATORS WERE VACUOUS** —
      `-1-(-32768)`=32767 and `$8000-$8000`=0 do not overflow at all, so no
      promotion decision is reached and neither row could speak. I predicted
      values for both by pushing them through the fitted MODEL of the
      reference instead of computing the subtraction. D-DSCALE's own lesson,
      landing again inside the slice written to apply it.
      🔴 **`sub.rom`'s hash was predicted UNCHANGED and MOVED** — a
      low-region insertion shifts every resident symbol after it, and the sub
      ROM's tenants link against those by address. **A low-region edit is
      never sub-ROM-neutral.**
      The original filing follows, unedited:

      🔴 **NOTHING SWEEPS THE `$8000` FIXED POINT AT THE OTHER SIGNED-16
      DIVIDES.** Filed 2026-08-11 by D-DSCALE. `gdrw_scale` divided a signed
      product by 4 with `negate → shift → negate`, which is correct for every
      16-bit value except `$8000` — the sole fixed point of two's-complement
      negation — where it returns `-8192` and both references return `+8192`.
      That was found only because a control row happened to land on it. **The
      same `negate → shift → negate` shape is a common idiom and this tree has
      other signed right-shifts**; none of them has a row at `$8000`, and the
      value is unreachable from any small-count test by construction.
      ⚠️ Whoever picks this up must FIRST enumerate the signed divides (grep for
      `gdrw_negate_hl` / `srl h` / `sra h` pairs and the float pack's shifts),
      then ask of each: *is `$8000` reachable at this input, and what does the
      reference answer?* A denominator before a fix — the sweep is the
      deliverable even if every site turns out to be unreachable, because
      "unreachable" is currently an assumption at all of them.
      💰 Not priced: the enumeration has not been done, so any byte figure would
      be invented. `lineerr-acceptance` is the wrong gate for most of the
      candidates — the arithmetic ones belong to `graphics-acceptance` and the
      float ones to `intarg`/`missing`.

- [x] ⚠️ **FOUR `$8000` VERDICTS REST ON ONE COMMENT, AND IT IS AN OVERFLOW
      BOUND, NOT A `$8000` BOUND.** Filed 2026-08-11 by D-NEG8K
      ([`docs/fixpoint8000-msx1-sweep.md`](docs/fixpoint8000-msx1-sweep.md)
      §4.2). `gfx_circ_scale`, `gfx_circ_bvec_nudge`, `gcbv_y` and
      `gfx_neg16_bc`/`gfx_neg16_de` were all classified "`$8000` unreachable"
      on the SAME stated bound — `gfx_circ_scale`'s header,
      "Bounded-domain: `|v|*ASPS` assumed `<=65535` (true for `|v|<=255` …)".
      That is one assumption doing four rows' work, it is written as an
      *overflow* bound rather than a `$8000` bound, and **the sweep did not
      re-derive where the `r <= 255` domain is actually enforced**. It clearly
      is somewhere — `CIRCLE(0,0),32768` is already a probe row
      (`basic_probe_graphics.py` `ovf_radius`) — but "already a row" is not the
      same as "the negate sites can never see `$8000`". The cheap version is a
      reading, not a fix: find the enforcing site and cite it from the four
      headers, or measure a large-radius/large-aspect `CIRCLE` and see what
      reaches `gfx_circ_scale`. ⚠️ Belongs to `graphics-acceptance`, NOT to
      `float-acceptance`.
      💰 Not priced: if the domain holds, the cost is four citations and zero
      bytes; if it does not, the fix is a `$8000` arm per site and nobody has
      measured which sites would need one.
      ✅ **CLOSED 2026-08-16 by D-CIRCDOM**
      ([`docs/circdom-msx1-characterization.md`](docs/circdom-msx1-characterization.md)).
      **THERE IS NO `r <= 255` DOMAIN AND THERE NEVER WAS.** The radius is
      enforced at exactly two sites and it is **0..32767**:
      [`basic/graphics.asm`](basic/graphics.asm) `cp_req_int` → `gfx_eval_int16`
      (ERR 6 at `|r|>=32768`) and [`sub/circleparse.asm`](sub/circleparse.asm)
      `cpt_after_r` `jp m,cpt_err5` (ERR 5 at `r<0`). `CIRCLE(128,96),1000` is
      **K on both references**, measured. All five (six, with `gfx_cross_ge0`)
      verdicts **HOLD — and not one of them for the stated reason**: three are
      safe by a `ld l,h / ld h,0` **byte truncation** that needs no domain claim
      at all, three by the int16 coercion, which is 128× looser than the bound
      cited. Six citations, **0 B**, exactly as priced.
      🔴 **THE RE-DERIVATION FOUND TWO DEFECTS THE `$8000` QUESTION WAS NOT
      LOOKING FOR** — see the two entries below; the second is fixed, the first
      is filed. 🔴 And they are coupled: site 3 (`gfx_circ_scale`'s re-negate) is
      safe *because the multiply truncates*, so **fixing the overflow makes
      `$8000` reachable there for the first time**.

- [x] 🔴 **THE PRODUCT BOUND IS REAL AND REACHABLE: `CIRCLE` WITH r ≥ 256
      DRAWS PIXELS THE REFERENCE DOES NOT.** Filed 2026-08-16 by D-CIRCDOM
      ([`docs/circdom-msx1-characterization.md`](docs/circdom-msx1-characterization.md)
      §4.1). `gfx_mul16u` truncates at 16 bits, so `gfx_circ_scale`'s
      `|v|*ASPS` wraps once the product reaches 65536 — first reachable at
      **r=256 with the default ASPS=256**, and the radius domain allows 32767.
      Measured on the whole pattern plane, VG-8020 vs zerobas: at
      `CIRCLE(128,96),256` / `,300` / `,300,,,,.9` / `,900,,,,.3` /
      `,1900,,,,.137` **the reference draws 0 px on screen and zerobas draws
      31 / 512 / 376 / 512 / 512**. The control that settles which bound is
      real: `CIRCLE(128,96),700,,,,.137` — r 2.7× outside the retired claim,
      product 24500 — is **byte-identical, 421 px, sha1 `2f6257f6`**. Never
      crashes (13/13 rows K on both). ⚠️ The old header said a large radius
      "may mis-rasterise the **arc mask**"; `gfx_circ_scale` runs on **every
      point of every circle**, arc or not, aspect or not — four of the six DIFF
      rows are plain circles. ⚠️ `graphics-acceptance` owns this.
      ⚠️ **WHOEVER FIXES THIS MUST ADD THE `$8000` ARM AT `gfx_circ_scale`'s
      RE-NEGATE IN THE SAME SLICE**: an exact `(32767*256+128)>>8` is `32768` =
      `$8000`, and the truncation being removed is the only thing that
      currently makes that site unreachable (D-CIRCDOM §6).
      💰 Not priced: needs a 24-bit product or an overflow arm in
      `gfx_circ_scale` + `gfx_circ_bvec_mag` + `gfx_cross_ge0`, plus the
      `$8000` arm. Sub page 1 had **1483 B** free at D-CIRCDOM. Nobody has
      measured what the reference does at r ≥ 256 for a figure that is
      *partly* on screen — every measured DIFF has the reference drawing
      nothing at all, so the fix has no positive oracle yet. **That oracle is
      the first thing to measure, not the fix.**
      ✅ **CLOSED 2026-08-16 by D-CIRCOVF**
      ([`docs/circovf-msx1-oracle.md`](docs/circovf-msx1-oracle.md)).
      **The oracle exists and the answer is a FULL-WIDTH PRODUCT, ROUNDED
      HALF-UP.** The geometry that had blocked it is a theorem, not bad luck:
      an overflowing point has a scaled minor offset ≥ 256 and the screen is
      192 tall, so no overflowing point can be on screen *while the centre is*
      — and every CIRCLE row in the tree's history is centred at (128,96).
      Moving the centre off screen **along the minor axis** puts the
      overflowing part of the figure on the visible band. Four such rows, on
      all three code paths (default `ASPS=256`, `cpt_asp_le1`, and the `fp_div`
      branch), matched a full-width model **byte for byte across the whole
      6144-byte plane**; a saturating model and the wrapping model were both
      refuted at sha1 level; four controls at the same off-screen geometry with
      products that FIT were byte-identical. 8/8 whole-plane predictions exact.
      Fix: `gfx_mul16r` (24-bit accumulator) at `gfx_circ_scale` +
      `gfx_circ_bvec_mag`, `gfx_mul16u32`+`gfx_cmp32` at `gfx_cross_ge0`,
      `gfx_mul16u` deleted. **+65 B, and it lands in sub page 0, not the sub
      page 1 this entry priced it against** — `graphics_tenant` is a page-0
      tenant. Ten gate rows added; `sub.rom` `8161c1a2` → `bc7573df`, the other
      three ROMs byte-identical.
      🔴 **THE `$8000` COUPLING THIS ENTRY ASSERTS DOES NOT BIND, AND A
      DIFFERENT ONE DOES.** The arithmetic above is right — an exact
      `(32767*256+128)>>8` *is* `$8000` — but the conclusion is
      design-dependent. `ASPS` is 0..256 and `ASPS=256` is the only value that
      can reach 32768; it is also the value for which the scale is the
      **identity**, so 4 bytes of branch skip the multiply entirely. On that arm
      the result is `|v| ≤ 32767`; on the multiply arm `ASPS ≤ 255` gives at
      most 32639. **No `$8000` arm was needed** (600 000-case sweep,
      `scratchpad/circovf_asmsim.py`). What DOES bind is `gfx_cross_ge0`: its
      two products **were not broken before the slice** and are broken *by* it,
      because their inputs were byte-bounded by exactly the truncation being
      removed. Right structural claim, wrong site, opposite direction.

- [x] 🔴 **TWO KNIFE-RUNNER DEFECTS, BOTH FOUND BY READING THE RUNNER'S OWN
      OUTPUT RATHER THAN THE TREE'S.** Filed 2026-08-16 by D-CIRCDOM
      ([`docs/circdom-msx1-characterization.md`](docs/circdom-msx1-characterization.md)
      §9 and §9A). Neither is specific to that slice; both are shapes the
      *next* runner will reproduce, and `docs/dev-workflow.md` §Knives is where
      they belong once confirmed a second time.
      **(a) ROWS KEYED BY LABEL COLLAPSE DUPLICATES.** The runner reported
      `rows=289` where the probe printed **296** `PASS` lines, because it keyed
      a dict on the row label and five labels repeat across phases (`Philips`,
      `C-BIOS`, `after`, `colour16_err`, `scr0_err`). **A move confined to one
      instance of a duplicated label is silently under-reported** — the knife
      scores CUT NOTHING and the reader concludes "missing row". Key on
      `(phase, index, label)`. ⚠️ The `>= 250 rows` short-report guard is the
      only reason the discrepancy was visible at all; a runner without one
      never prints the number to notice.
      **(b) THE SCORER HAS NO STATE FOR A REGRESSION-CHECK KNIFE.** K-CD3's
      round-3 prediction was deliberately the round-2 **measurement copied
      forward** — a check on a known answer — and the binary EXACT/MISS verdict
      reported **MISS** for a knife doing exactly what it was designed to do.
      A copied-forward set is honest only if labelled, and the scorer needs a
      third state (`REGRESSION`) so the label survives into the scorecard.
      ⚠️ Related but distinct, and already fixed in that runner: **a
      hand-maintained prediction set is a pure transcription risk** — K-CD2
      missed by one row with **zero modelling content** because a hand-typed
      list was extended by hand. Derive prediction sets from the probe.
      💰 Zero bytes (scratchpad tooling only). The cost is one runner rewrite,
      and it is worth doing at the START of the next knife-bearing slice rather
      than after, since (a) can turn a real finding into a silent pass.
      ✅ **CLOSED 2026-08-16 by D-CIRCOVF**, at the start of the slice as this
      entry asked. [`scratchpad/circovf_knives.py`](scratchpad/circovf_knives.py)
      keys rows on `(phase, index, label)` and **asserts that key count against
      the probe's own PASS/FAIL line count**, so the two can never drift again —
      the assertion, not the keying, is what makes it stay fixed. `kind` now
      carries the scorer state: `predict` (EXACT/MISS), `regress` (HOLD/BROKEN,
      never scored EXACT), and a third the residual did not anticipate,
      `nothing` — a knife PREDICTED to redden nothing, where the missing row IS
      the finding. K-CO3 is that case: it undoes the 32-bit cross-product
      widening and no green gate row can see it. Every prediction set is derived
      from the probe's own `CIRCLE_CASES` at run time, from each row's `ops`
      string, including the "does this row draw anything on screen at all"
      filter — nothing is hand-typed.

- [x] 🔴 **THE ARC MASK DIVERGES AT LARGE RADII, AND IT IS NOT THE PRODUCT
      BOUND.** Filed 2026-08-16 by D-CIRCOVF
      ([`docs/circovf-msx1-oracle.md`](docs/circovf-msx1-oracle.md) §6.1).
      Measured on the whole pattern plane, VG-8020 vs zerobas:

          CIRCLE(128,352),200,15,1.1,2.04    ref 170 px 386f8fb8 / zb 181 px 7956e005
          CIRCLE(128,96),700,15,0,1.57,.137  ref 127 px ebfd085b / zb 126 px 752131e6
          CIRCLE(128,96),400,15,-1.57,0      ref  97 px cd7e5368 / zb  97 px 76352feb

      ⚠️ **ALL THREE ARE PRE-EXISTING AND THAT IS MEASURED, NOT ARGUED**:
      `scratchpad/circovf_prefix.py` reverts the slice's source edits, rebuilds
      the pre-slice `sub.rom` **`8161c1a2` byte for byte**, and re-asks the same
      rows. `arcctl_r200` reads **byte-identically on both builds** (`7956e005`
      either side) — at r=200 every cross product is 40000, inside 16 bits on
      both arithmetics, and `ASPS=256` makes the scale the identity on both, so
      nothing D-CIRCOVF touched can reach it.
      🎯 **THE ROW THAT SETS THE SCOPE IS THE ONE WRITTEN AS A CONTROL.**
      `arcctl_r200` was written to be green — same shape, same off-screen-centre
      geometry, products that fit — and came back red, which is what says the
      divergence is angular rather than arithmetic.

      🔬 **CHARACTERISED 2026-08-17 by D-ARCMASK**
      ([`docs/arcmask-msx1-characterization.md`](docs/arcmask-msx1-characterization.md)).
      **NOT FIXED — and the three unwalked candidates above are all wrong.**
      53 further rows measured on both machines (whole planes dumped to
      `scratchpad/arcmask_sweep.json` / `arcmask_fine.json`, so every question
      below is re-answerable with no emulator). Rig clean both runs: dead
      subject 1 px, `ctl_full_*` and `ctl_arc_r15` byte-identical, `lad_r200`
      replicating the §6.1 reading, and an offline zerobas model exact on
      **56/56 whole 6144-byte planes**.
      🔴 **THE PREMISE THE BOUNDARY RESTS ON IS MEASURED FALSE.** Spec §5.2.1
      and `sub/graphics.asm` both assert the reference's boundary vector is the
      EXACT ray `round(r*|cos|)`/`round(r*|sin|)`, citing "host-fit ALL MATCH".
      The fit is real; **its corpus is `g4_pointsets.json`, radii 4..20, every
      ARC row r=15** — and the divergence is 0.032 rad, which at r=15 is 0.5 px.
      Against 51 whole reference planes at radii to 200 that rule scores **2–4**.
      🎯 **WHAT THE REFERENCE DOES:** fold the angle to the nearest axis,
      `f ∈ [0,π/4]`; its boundary is the octant loop's **STEP INDEX distributed
      LINEARLY over `f`** — measured as a constant +6 steps per 0.035 rad right
      across the octant, 44 samples at r=190, both sides. Exact at `f=0` and
      `f=π/4` (where `r·sin(π/4)` is the octant's own step count), up to
      0.032 rad wrong between. **THE REFERENCE IS THE LESS ACCURATE MACHINE** —
      zerobas is within one QTAB step (0.012 rad), the reference is out by
      0.037 — so under the faithful-MSX1 charter our accuracy is the defect.
      Error in pixels grows with r: 1 step at r=24, 2 at 48, 2–3 at 95, 4–5 at
      190, 5–6 at 200.
      🎯 **THE RULE IS SOLVED (same slice, second pass).** The axis-folded
      model's residuals were not noise: at r=190 they ALTERNATE between the rays
      just below π/2 and those just above — **the reference is not symmetric
      about the axis**, and folding to |θ−axis| is what threw that away.
      Restated in OCTANTS, with `o = ⌊θ/(π/4)⌋` and `u` the fraction into it:

          M   = ⌊r/√2⌋            the octant's top step index
          pos = ⌊u·M⌋             position along the octant, always
          k   = pos               in an EVEN octant   (step rises with θ)
          k   = M − pos           in an ODD octant    (step falls with θ)

      both boundaries inclusive. **No fitted constant, no per-side offset.**
      `scratchpad/arcmask_refmodel2.py` scores it on whole 6144-byte planes:
      **52/54**, against 22/54 axis-folded and 2–4/54 for the exact-ray rule the
      source asserts. ⚠️ 80/80 on the integer boundaries it was FITTED on is the
      shape to distrust — 52/54 is the independent score, and it includes the
      three D-CIRCOVF §6.1 rows the fit never saw, among them `arc_r700_a137`
      (r=700, ASPS=35, a different code path in both machines) byte-exact.
      Falsified by deletion: octant asymmetry removed **52→11**, `floor`→`round`
      **52→19**, `M=ceil(r/√2)` **52→32**, `M=r/2` **52→2**.
      🎯 **THE TWO ROWS IT MISSES ARE THE TWO OTHER FILED DEFECTS**, which is
      what says they are separate: `ctl_card_r95` model = **zerobas's own plane**
      (134 px e3e10d24) vs ref 135 — the near-cardinal nudge below; and
      `arc_big_r400` model and ref **both 97 px** with planes differing — the arc
      is right, only the deferred SPOKE endpoint is not.
      💰 **THE FIX IS DESIGNED AND SIMULATED EXACT — implementation is the
      remaining work.** `scratchpad/arcmask_asmsim2.py` runs the whole pipeline
      at tenant widths and scores **53/54 planes, 4/4 r=15 point sets, 7/7
      near-cardinal sweep, round-3 spoke** — everything the float model
      achieves (the 54th is the spoke-line row, a separate open item). The
      pipeline: **P1** round the angle to 6 BCD digits (half-up; knifed, 53→52
      without it) · **P2–P5** one fp_mul by 4/π, trunc to int16 `o`, subtract,
      one fp_mul by 16384, trunc to `u14` — replaces the (brad, sign_c, sign_s)
      marshalling and the three quadrant fp_cmp · **G1** `M=(r·46341)>>16` then
      `if 2M²>r²: M−=1` — **exact floor(r/√2) on ALL 32768 radii, verified
      exhaustively; the uncorrected multiply is wrong on 410 of them** ·
      **G2–G3** OM[o]=o·M table + `pos=(u·M)>>14` (gfx_mul16u32, once per
      boundary) · **G4** per point: octant is STATIC per mirror, step is the
      loop's own qx; keep iff `(OM[o]±qx − gs) mod 8M ≤ span`, 24-bit — replaces
      four 16×16→32 multiplies + two 32-bit compares per point · **G5** spoke
      endpoint = octant point at the boundary (walk the midpoint loop to step
      k), replacing the QTAB vector. Deletable once landed: QTAB+fold+lookup,
      bvec/bvec_mag/bvec_nudge, arcbig_calc, gfx_cross_ge0 (p0); the three
      quadrant constants (54 B), the sign tree, cpt_round, cpt_build_half (p1).
      Unpinned by the corpus (implement however the mathpack does): fp_mul
      round-vs-trunc, C14's last digit. `graphics_tenant` is **page-0** sub
      (3539 B free); net bytes look ≤0 but **price by editing, not by paper**
      — walk the callers of cross_ge0/mul16u32/cmp32 first. ⚠️ Closing this
      **also closes the arc-performance residual below** by construction.
      ✅ **CLOSED 2026-08-17, same slice, third pass** (docs §5.6): the
      step-index wedge SHIPPED — `gfx_circ_wedge_prep` + the pair-compare
      `gfx_circ_keep`, single-precision `(oct,u14)` marshalling, octant-point
      spokes; QTAB, the bvec family, `gfx_cross_ge0` and `gfx_circ_arcbig_calc`
      DELETED. Net **−120 B** (sub p0 +33, sub p1 −153). Verified: **18/18
      previously-red rows byte-identical** (`scratchpad/arcmask_verify.py`),
      `graphics-acceptance` **317/0** with seven new rows the gate now owns
      (incl. `arcmask_r200`, this residual's own row), `unit-test` 59/59 with
      the ported arc suite, three source knives cut as predicted
      (`scratchpad/arcmask_knives.md`; the misses are scored there).

- [x] 🔴 **THE REFERENCE EVALUATES THE ARC ANGLE IN SINGLE PRECISION — the
      "nudge defect" filed here earlier was MY WRONG DIAGNOSIS.** Filed
      2026-08-17 by D-ARCMASK (§4.3), REDIAGNOSED the same day (§5.4). The row:

          CIRCLE(128,96),95,15,0,1.5707963   ref 135 px 7babb12d / zb 134 px e3e10d24

      First diagnosis said the ±1 near-cardinal nudge had an unmeasured domain
      edge. Measured against the whole corpus, the actual mechanism is simpler
      and upstream: **1.5707963 differs from π/2 by 3×10⁻⁸, which a 6-digit
      single-precision evaluation cannot resolve** — round the angle to 6
      significant BCD digits (half-up) and the solved step-index rule keeps the
      axis point exactly as the reference does, **without any nudge at all**.
      Scored: 6-digit rounding takes the reference model from 52/54 to 53/54
      whole planes, holds all four r=15 point sets AND the near-cardinal
      1.50..1.60 sweep (the nudge's own pin), and its deletion is knifed at
      exactly the one row (53→52, `scratchpad/arcmask_asmsim2.py`).
      ✅ **CLOSED 2026-08-17**: shipped as P1 of `cpt_boundary_prep`;
      `ctl_card_r95` byte-identical (135 px `7babb12d` both machines), in the
      gate as `arcmask_card95`, unit teeth pin the round AND the carry chain,
      knife K-AM1 reddens exactly this row and restores zerobas-before's plane
      byte for byte.

- [x] 🔴 **ZEROBAS'S SPOKE ENDPOINT DIVERGES FROM THE REFERENCE AT NEAR-ZERO
      ANGLES — LATENT, measured from BANKED data, no gate row covers it.**
      Filed 2026-08-17 by D-ARCMASK (§5.4). The G4-arcbnd round-3 capture
      (`scratchpad/g4_arc_boundary_capture.json`, `PSET(75,60),9:`
      `CIRCLE(60,60),15,6,-0.01,1.57`) has colour 6 in the y=60 row of the
      (72..79) cell — the reference's spoke reaches **(75,60)**, i.e. endpoint
      = offset **(15,0), the OCTANT POINT at the boundary**. zerobas's
      `gfx_circ_bvec` at θ=0.01 rounds the sine magnitude to 0 and the nudge
      makes it **(15,−1)** — a different line. ⚠️ At r=400 the QTAB 255-cap
      also shortens today's endpoint to (1,−398) vs the octant point's
      (1,−400). ⚠️ **NEITHER explains `arc_big_r400`**: the simulated
      octant-point spoke still reproduces ZEROBAS's plane there (76352feb),
      not the reference's — that row's divergence is in the spoke LINE
      rasterisation or clipping at an off-screen endpoint, still open.
      ✅ **CLOSED 2026-08-17**: `gwp_spoke_vec` ships the octant point; the
      round-3 row is byte-identical and in the gate (`arcmask_spoke`); the
      QTAB 255-cap shortening at r=400 went with QTAB itself; unit rows pin
      six endpoints incl. `(1,-400)` at r=400. The `arc_big_r400` LINE
      divergence is a SEPARATE item, re-filed sharpened below.

- [x] 🔴 **THE REFERENCE'S SPOKE LINE ADVANCES ITS MINOR AXIS BEFORE THE
      MIDPOINT — the last `arc_big_r400` divergence, now isolated to the LINE
      RASTERISER.** Filed 2026-08-17 by D-ARCMASK (docs §5.6), the sharpened
      remainder of D-CIRCOVF §6.1's third row:

          CIRCLE(128,96),400,15,-1.57,0   ref 97 px cd7e5368 bbox (128,0,129,96)
                                          zb  97 px 76352feb bbox (128,0,128,96)

      Same pixel count, same endpoint (the octant point (1,−400) — verified:
      bvec, octant-point AND the shipped rewrite all produce the identical
      zerobas plane). The bboxes say what differs: drawing centre→(129,−304),
      the reference has pixels in column 129 INSIDE the visible band (y 0..96),
      i.e. its line steps x early; our Bresenham's midpoint rule crosses at
      y≈−104, off screen, so the visible run is all x=128. ⚠️ This is a
      **`gfx_line_op` tie/rounding question at an extreme slope with an
      off-screen endpoint** — nothing to do with arcs; LINE itself may show it
      with a bare `LINE (128,96)-(129,-304)` if the reference accepts that
      form, which would be the cheaper probe. 💰 Not priced. The G3 line was
      host-fit on on-screen segments only.
      ✅ **CLOSED 2026-08-17 by D-SPOKELINE**
      ([`docs/spokeline-msx1-characterization.md`](docs/spokeline-msx1-characterization.md))
      — and the diagnosis above was a CORNER of the real rule: **the reference
      CLAMPS BOTH endpoints of every line to the screen** (X→0..255, Y→0..191)
      before rasterising — LINE, spokes (the CENTRE clamps too) and box
      outlines alike. Solved offline from the banked sha1 (the ref plane is
      uniquely the y=47-seam pair, = clamp-then-draw), then measured on 23
      whole-plane rows over all four edges: `clamp_both` unique on nine,
      **a fully off-screen LINE lights exactly (255,191) on a VG-8020** — the
      pixel G3's `clip_alloff` band was blind to, and `clip_frac` is PROVABLY
      vacuous (all hypotheses one plane). Fix: `gfx_clamp_coords`, 52 B in sub
      p0, one call in `gfx_line_op`. All 23 rows byte-identical after;
      `graphics-acceptance` **323/0** with six new rows; knife K-SL1 restores
      the old planes byte for byte. 🔴 Two model errors owned on the way: the
      python line model's direction convention was wrong about BOTH machines
      (gfx_bres_init sorts the major axis ascending — direction was never a
      divergence), and the first zline transcription GUESSED the stepping rule
      and was refuted 8/16 by banked planes before being corrected to
      gfx_bres_next's actual accumulator form (then 16/16).

- [x] ⚠️ **`DRAW` WITH OFF-SCREEN COORDINATES IS UNMEASURED, AND THE CLAMP
      DOES NOT COVER IT.** Filed 2026-08-17 by D-SPOKELINE (§3.2).
      **CLOSED 2026-08-17 by D-DRAWCLAMP** —
      [`docs/drawclamp-msx1-characterization.md`](docs/drawclamp-msx1-characterization.md).
      **DRAW obeys LINE's rule exactly**: both endpoints clamp to the screen
      before rasterising, the ideal line is never clipped. 12 discriminating
      whole-plane rows, the reference matching `clamp_both` on every one and
      UNIQUELY on `dm_both_off` (the four-way row) and `dm_two_seg`; the
      absolute, relative, SCALED and ROTATED routes and the direction letters
      all clamp, and the clamp applies to the TRANSFORMED target, not the
      typed operand. Fix: one `call gfx_clamp_coords` in `gdrw_move_abs`
      (**3 B**). 🔴 **G6's "off-screen motion clips by masking" was never
      measured** — its only off-screen row, `clip_left`, is HORIZONTAL and
      therefore scores DISCRIMINATING POWER 1: clamp and clip give the same
      pixels for an axis-aligned segment. It is kept as `ctlD_clipleft`, the
      three-way control it always was.

- [x] ⚠️ **THE WORK AREA AFTER AN OFF-SCREEN LINE IS UNMEASURED.** Filed
      2026-08-17 by D-SPOKELINE (§4). **CLOSED 2026-08-17 by D-DRAWCLAMP** —
      answered by a direct PEEK of `GRPACX/GXPOS`, not inferred from a second
      segment. **The reference stores the RAW p2 and zerobas was already
      right**: nine rows agreeing on both machines, negatives reading back as
      65486/65506 and a fully off-screen LINE reading 400/400. **Zero bytes.**
      🔴 But the rows found an UNPREDICTED divergence in the *other* cell
      pair: `GXPOS/GYPOS` takes the **clamped** coordinate after a `DRAW` move
      (the greater-y endpoint rule SURVIVED, its coordinate did not) and the
      **clamped box's bottom-right** after a `BF` fill — while plain LINE and
      the `B` outline leave it raw. `gdrw_gxpos` retargeted (0 B) +
      `gfx_bf_gxpos` (35 B). I had predicted raw/raw for `draw_m_off`: a
      value-level miss inside a correctly-shaped row set.

- [x] 🔴 **A RE-RUN PROBE THAT BANKS TO A FIXED JSON PATH OVERWRITES ITS OWN
      PRE-FIX MEASUREMENT.** Filed 2026-08-17 by D-SPOKELINE (§6).
      **CLOSED 2026-08-17 by D-DRAWCLAMP**, in the pattern rather than in a
      note: `drawclamp_char.py` banks to a VERSIONED path
      (`.pre.json`/`.post.json`) and refuses to overwrite without `--force`,
      and all three `spokeline_char*.py` probes gained a `bank_guard(OUT)`
      before their write (`--force` to overwrite, `--out NAME.json` to
      version). The guard was falsified by EXERCISING it — re-running against
      an existing bank exits 3 — not by asserting it. ⚠️ The arcmask sweeps
      still write fixed paths and were left alone.

- [x] ⚠️ **`PSET(0,192)` HAS NO INSTRUMENT: A FAILED y-CLIP WRITES THE NAME
      TABLE, OUTSIDE THE PATTERN PLANE.** Filed 2026-08-17 by D-GATEBLIND (§4.1);
      **CLOSED 2026-08-17 by D-GATEBLIND round 2** (§11) — row `clip_noop_y192`,
      `SPRITE$(0)=STRING$(8,0):PSET(0,192)`, reading `$1800`/`$3800`. 🔴 **THE
      BLOCKER AS FILED NAMED THE WRONG OBSTACLE**: `band_segs()` is clamped, but
      it is phases C/D/E's instrument and **phase A never calls it** — phase A
      captures `paddr(x,y)` and `paddr(x,y)+$2000` as explicit one-byte segments,
      and `paddr(0,192)` is 6144 = `$1800` exactly. No new row shape was needed
      at all ([[a-filed-blocker-can-name-the-wrong-obstacle]]). What WAS missing
      is the pre-state: `$3800` is the sprite pattern generator, and
      `gfx_color_rmw` writes NOTHING when the plot colour equals the colour
      byte's low nibble, so a `$3800` whose low nibble was 15 would have left
      both captured cells unchanged and the new row as blind as the old one. The
      `SPRITE$` write pins it. Knife **K-Y192** (`gfx_in_range` `cp 192` →
      `cp 193`) exact: `80`/`f0` predicted and measured, the other 10 phase-A
      rows unmoved.

- [x] ⚠️ **232 OF 355 GATE ROWS WERE NOT REDDENED BY THE FIRST MUTATION
      BATTERY, AND THE BATTERY IS THE DENOMINATOR.** Filed 2026-08-17 by
      D-GATEBLIND (§2); **CLOSED 2026-08-17 by D-GATEBLIND round 2** (§7–§13):
      sixteen more mutations aimed at exactly the four named subsystems — sprite
      attribute/pattern addressing, the sprite size state, the VDP register write
      path, `VDP()`/`BASE()` argument handling. Battery of 21: **263 of 356 rows
      reddened, 93 never**; the sprite/VDP phases went **155 → 15**, with N and
      Q1 fully covered. Predictions **10 exact of 16**; 🔴 `M-VDPMIRR` predicted
      ~24 and measured **68** because `RG0SAV+1` for register 0 *is* `RG1SAV` and
      phase Q2 is **batched**, so one poisoned mirror desynchronised 44 later
      cases. Apparatus fixes: per-mutation file AND ROM (a `basic/` cut does not
      move `sub.rom`), and never-reddened rows now carry how many battery members
      actually contained them.

- [x] ⚠️ **78 GATE ROWS OUTSIDE THE SPRITE/VDP PHASES ARE STILL UNMEASURED BY
      ANY BATTERY.** Filed 2026-08-17 by D-GATEBLIND round 2; **SUPERSEDED
      2026-08-17 by round 3** (§14–§16), which added the missing dimension — **the
      error CODE itself**, never mutated by rounds 1–2 — and took the roster to
      **51 of 358**. Phase L went **25 → 5** on one cut (`gdrw_err5`'s `ld a,5`:
      the whole DRAW §5 table is one byte), J **9 → 2**, D **9 → 7**, B **3 → 2**.
      What remains is three NAMED classes, refiled below, not "the rest".

- [x] ⚠️ **THE 51-ROW RESIDUE IS ACCEPTANCE, THE WORK AREA, AND THE ERR 6 TAIL.**
      Filed 2026-08-17 by D-GATEBLIND round 3; **CLOSED 2026-08-17 by rounds 4–5**
      (§17–§20). Seven more cuts, one per class: `M-DRWSCALE` 34 rows,
      `M-OVFCHK` 12, `M-GRPAC` 5, `M-CIRCERR5` 3, `M-LINESYN` 2, `M-PSETOFF` 1,
      `M-GRPAC2` **0**. **Battery of 35: 325 of 358 reddened, 33 never**
      (232 → 93 → 51 → 33), and **every one of the 33 is now classified**.

- [x] 🔴 **THREE ROWS' ERROR SITE HAS PROVABLY NOT BEEN FOUND.** Filed 2026-08-17
      by D-GATEBLIND round 3; **CLOSED 2026-08-17 by round 4** (§17) — at the
      DESK, not by more cuts. Both sites were in files rounds 1–3 never opened:
      **CIRCLE's parse is a SUB-ROM TENANT with its own `cpt_err5`**
      (`sub/circleparse.asm`, a fourth error-code site) → `M-CIRCERR5` reddened
      exactly `G/rneg_err`, `F/aspect_neg_err`, `F/colour16_err`; and **LINE has
      its own `elg_syntax`** → `M-LINESYN` reddened exactly `D/badsuffix`,
      `D/nodash`. Both predictions exact. 🎯 **A code cut that reddens nothing you
      expected is a MAP: it says the raiser is elsewhere.** ⚠️ The same lesson
      repeated one round later on `F/ovf_radius`, whose overflow check is also the
      circle parse tenant's rather than `gfx_eval_int16`'s.

- [x] 🔴 **THE GATE HAS NO ROW THAT SEPARATES LINE'S *TWO* WORK-AREA WRITERS, SO
      NINE ROWS CANNOT BE REDDENED BY ANY SINGLE-SITE MUTATION.** Filed
      2026-08-17 by D-GATEBLIND round 5 (§19); **CLOSED THE SAME DAY** (§21) —
      two rows on the **ERROR path**, where the tenant never runs because
      `gfx_point_gate` is `call gfx_work_area` followed by the mode gate:
      `w_err_scr0` and `w_err_step` (gate **358 → 360/0**). They measure what
      nothing measured before — the work area holds the **raw p2 in all four
      cells even though ERR 5 was raised** (`W 300 250 300 250 5`), and a STEP
      target resolved against the staged p1 lands there too before the statement
      fails. Knives both **EXACT**: **K-GR3** (resident) reddens **7** — the two
      new rows plus M-GRPAC's five, with all nine drawn-path rows holding —
      and **K-GR4** (tenant) reddens **0 of 360**. ⚠️ A third case
      (`SCREEN0:LINE(0,0)-(300,250),15,BF`) was designed and **dropped before it
      shipped**: the gate fires before the box field is ever parsed, so its
      failure surface is byte-for-byte `w_err_scr0`'s.

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

- [ ] ⚠️ **NINE ACCEPTANCE ROWS STILL NEED A REFUSAL CUT, ONE PER PATH.** Filed
      2026-08-17 by D-GATEBLIND round 5 (§20). `M-PSETOFF` and `M-DRWSCALE` proved
      the shape works — an off-screen `PSET` made to raise reddens
      `pset_offscr_ok`, and a narrowed `S` bound reddens `scale255ok`/`scale0` —
      but each remaining acceptance row sits on its own path: `off_ok` (LINE),
      `clip_neg_ok` / `clip_offscr_ok` (CIRCLE), `border16_flood_ok` (PAINT),
      `bare_b` / `empty` / `offscreen` (DRAW), `arc_ovf_r260` /
      `arc_ovf_wrap300` (the arc mask). 💰 Six or seven cuts, one each; there is no
      shared site the way `gdrw_err5` was for phase L.

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

- [ ] ⚠️ **`M-SPRPBASE` AND `M-SPRSZAPL` EACH HAVE ONE ROW THAT *SHOULD* SEE THEM
      AND DOES NOT.** Filed 2026-08-17 by D-GATEBLIND round 2 (§9). `pat_8_empty`
      (`SPRITE$(0)=""`) writes eight zeros, so an 8-byte base shift leaves the
      read cell at 0 — the row cannot distinguish the right entry from the wrong
      one **for the empty string only**; and `put_pat63_16` compares the error
      outcome, which is "accepted" under both the 8×8 and 16×16 pattern rules.
      Neither is wrong as written, but neither is coverage of what its name
      suggests. 💰 Give `pat_8_empty` a non-zero neighbouring entry first.

- [x] 🔴 **A BOX FILL WRITES A FULLY-COVERED BYTE AS *BACKGROUND*, AND WE WROTE
      IT AS FOREGROUND — A VISIBLE DIVERGENCE, AND THE REASON WE WERE 23×
      SLOWER.** Filed 2026-08-17 by D-DRAWCLAMP as an unquantified performance
      note; measured by D-BFPERF; **CLOSED 2026-08-17 by D-BFBYTE** —
      `gbf_split` + `gbf_row` + a corner sort, **153 B** (priced 120–180),
      sub p0 3416→3263, `sub.rom` `aeed6276`, gate **355/0** with 11 new rows
      (9 discriminating + 2 splitter controls, and every discriminating one has
      a COLOUR twin because that is where the rule mostly lives). Host tests:
      19 new cases over `gbf_split`/`gbf_shr3`. Knives **3 predicted, 3 EXACT
      at the row level**. ⏱️ full screen **20040 → 560 ms**, now **0.65× the
      reference**; ⚠️ but `bf_1col` (1 px × 192 rows, no whole byte anywhere)
      went **120 → 145 ms** — a real 21% regression on the narrowest case,
      accepted against 35.8× on the common one. Simulated against all 11
      measured readings before any Z80 was written; first build green. The
      measurement that opened it —
      [`docs/bffill-msx1-characterization.md`](docs/bffill-msx1-characterization.md).
      When a fill covers all 8 pixels of a cell row the VG-8020 writes
      **pattern `$00` and the colour in the BACKGROUND nibble** (`fg` forced
      to 0): `…,15,BF` → `00`/`$0f`, `…,6,BF` → `00`/`$06` (two colours, so
      the encoding is pinned). Partial runs keep the per-pixel path and both
      machines agree. 👁️ **VISIBLE**: `LINE(0,0)-(7,7),15,BF:PSET(0,0),6`
      leaves ONE pixel in 6 on the reference and repaints **all eight** on
      zerobas — the clash differs because the storage differs.
      ⏱️ Timing, empty-loop control subtracted at every N: full screen
      **860 ms ref vs 20040 ms zb (23.3×)**, a filled scanline 15.0×, and
      **`line_diag` at 1.00×** — our segment rasteriser is exactly the
      reference's speed, so the entire gap is the fill.
      🔴 **`box_bf`, the gate's only BF row, CANNOT SEE IT**: `LINE(1,1)-(14,10)`
      spans 7 px in each of two cells, so **not one whole byte is covered**,
      and it is pattern-plane only. Third blind gate row found this week.
      The shipped shape is per scanline
      `[left partial][whole bytes][right partial]`, ends via `gfx_rmw_at`, the
      middle two blind writes and no reads. ⚠️ **Both halves of the split are
      16-BIT on purpose**: `xl+7` overflows a byte above 248 and `fr` reaches
      −1 below `xr=7`, so in 8 bits `LINE(255,0)-(255,0),,BF` would report 32
      whole bytes and blind-fill the whole scanline — one pixel asked for, 256
      destroyed. That row is now `bfbyte_x255` in the gate and `(255,255)` in
      the host tests.

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

- [x] ⚠️ **THE 32-BIT CROSS PRODUCT HAS NO GREEN ROW THAT CAN SEE IT.** Filed
      2026-08-16 by D-CIRCOVF (§5.2, and K-CO3 in
      [`scratchpad/circovf_knives.py`](scratchpad/circovf_knives.py)).
      `gfx_cross_ge0` was widened to `gfx_mul16u32` + `gfx_cmp32` because the
      slice makes its inputs reach 32767 and its products 2³⁰ — **forced by
      arithmetic, not by a measurement.** The rows that would exercise it (an
      arc, at a radius where the products pass 16 bits, with pixels on screen)
      are all red for the separate pre-existing reason filed above, so the two
      arc rows that DID go green (`arc_ovf_r260`, `arc_ovf_wrap300`) are blank
      on both machines and are one-sided regression detectors only.
      K-CO3 is declared `kind="nothing"` for exactly this reason and its
      scorecard line is the number that stands in for the missing row.
      💰 Zero bytes. Blocked on the arc-mask item above: close that first and
      these rows become available.
      ✅ **DISSOLVED 2026-08-17**: the arc-mask rewrite DELETED
      `gfx_cross_ge0` outright — there is no 32-bit cross compare left to be
      untested. `gfx_mul16u32`/`gfx_cmp32` survive as `gfx_circ_wedge_prep`'s
      once-per-CIRCLE init arithmetic, exercised by every arc row in the gate
      and by the unit M-battery. K-CO3's target no longer exists; the
      D-CIRCOVF knife runner's ROM-hash guard refuses `e4fbf667` by design.

- [x] ⚠️ **`ASPS` TRUNCATION IS MEASURED FOR `aspect < 1` ONLY.** Filed
      2026-08-16 by D-CIRCDOM (§5). The fix (`cpt_asp_scale256`:
      `call cpt_round` → `call flt_to_int16`, **0 B**) is backed by 3/3
      discriminating aspects and 2/2 byte-identical controls — **all of them
      `aspect < 1`**, i.e. the `cpt_asp_le1` branch where `minor_ratio = aspect`
      directly. The `aspect >= 1` branch computes `minor_ratio = 1/aspect`
      through `fp_div` FIRST, and no measured row distinguishes floor from
      round there: the gate's two such rows are `,,,2` (→ .5 → 128 exact) and
      `,,,3` (→ 1/3 → 85.33, floor == round). A discriminating row exists —
      `CIRCLE(128,96),128,15,,,1.7` gives `1/1.7*256 = 150.59`, floor 150 vs
      round 151 — and it would also say whether `fp_div`'s own precision
      matches the reference's, which is a *different* question the truncation
      fix does not answer. ⚠️ `graphics-acceptance`.
      💰 Zero bytes expected; the cost is two rows (one discriminator, one
      control). If it diverges, the cause is `fp_div`, not the rounding.
      ✅ **CLOSED 2026-08-16 by D-CIRCDOM round 3** (same slice, same day;
      §5.1 of the characterization). **0/5 divergences, prediction EXACT.**
      Three independent discriminators — `1.7`→150.59, `1.3`→196.92,
      `1.1`→232.73 — all measured **floor** (x-half **75 / 98 / 116**, where
      round-half-up gives 76 / 99 / 117), with two exact controls (`2`, `4`)
      byte-identical. So the truncation is right on the `aspect >= 1` branch
      too, **and** `fp_div`'s precision matches the reference at three
      non-trivial reciprocals — the second claim was riding along unmeasured
      and is now pinned. 🔴 It also measures something no earlier row could:
      the **pre-fix tree was wrong on this branch as well**, which K-CD1
      confirms by reddening these three alongside the three from §5. Five rows
      added to `graphics-acceptance`, **0 B**.

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

- [x] ⚠️ **`DRAW`'s mode gate was left alone, with a green row behind it.**
      Filed 2026-08-11 by D-LINERR; ✅ **CLOSED 2026-08-11 by D-DRAWERR**
      ([`docs/spec-basic-lineerr.md`](docs/spec-basic-lineerr.md) §11,
      `make lineerr-acceptance` **189 rows**).
      🎯 **THE DECLINE WAS RIGHT AND THE ROW BEHIND IT WAS STILL BLIND.**
      Measured: `DRAW 5` in SCREEN 0 is **ERR 5** on both references while the
      same statement in SCREEN 2 is ERR 13, so DRAW refuses the mode **BEFORE**
      evaluating its string expression — D-LINERR's five-verb ordering rule does
      **NOT** extend to it, and `ex_draw`'s opening `cp 2` was correct all along.
      `v.draw0` could never have said so: a string LITERAL raises nothing, so it
      reads ERR 5 whichever side of `str_eval` the gate sits on.
      🔴 **AND THE SWEEP FOUND TWO DEFECTS THE RESIDUAL WAS NOT ABOUT.**
      `ex_draw` had no `skip_spaces`, so **`DRAW A$` was `Type mismatch`** —
      DRAW took a string literal and nothing else (`ex_let_str` and `spr_assign`
      both skip; `ex_draw` was the only one of the three that did not, which is
      why the `SPRITE$` sibling row `n.sprdz` never diverged). And the tenant
      ignored whitespace only BETWEEN commands, so `DRAW"R 10"` — and every
      `STR$`, which emits a leading blank — refused. Both fixed: **+3 B** page 1,
      **−3 B** sub p0.

- [x] 🔴 **`SCREEN (1<5)` IS `Syntax error` HERE AND `Illegal function call` ON
      THE VG-8020.** Filed 2026-08-09 by D-STMTPEND; ✅ **CLOSED 2026-08-10 by
      D-SCRERR** ([`docs/spec-basic-screenerr.md`](docs/spec-basic-screenerr.md),
      `make screenerr-acceptance` **61/61 from 22/61**, both references agreeing
      on every row). Both range rejects replaced by the shared checked-byte
      coercion plus one `cp 4`.
      🎯 **"CHEAP — TWO `jp` TARGETS" WAS WRONG IN THE CHEAP DIRECTION**: it is
      **−6 B**, because `call eval` + two hand-rolled rejects is 14 B and the
      shared leaf is 8 B. A price that counts only what it INSERTS misses what it
      DISPLACES, in both directions.
      🎯 **"IT NEEDS ITS OWN ROWS" WAS EXACTLY RIGHT** — the domain held FOUR
      more divergences the item did not know about: `SCREEN 70000` silently set
      SCREEN 0 (no error at all), bare `SCREEN` / `SCREEN 2,` were silent no-ops
      where both references say `Missing operand`, the sprite size had no domain,
      and no trailing argument was range-checked.
      🔴 And closing it EXPOSED a fifth, older defect — `ex_screen` counted the
      argument slot at the VALUE, so an omitted argument was never counted and
      `SCREEN 1,,3` applied 3 as the SPRITE SIZE. Measured on the **base** ROM
      (`a.sprskip` reads ` 99 , 2 ` at `3dc1e7b`), i.e. it was shipping, not
      introduced by the fix. Fixed in the same slice, §4.

- [ ] 🔴 **`FIELD #(A$<5),1 AS Z$` IS `Type mismatch` HERE AND `Illegal function
      call` ON THE VG-8020.** Filed 2026-08-09 by D-STMTPEND. The reference
      evidently classifies the CHANNEL before it classifies the expression, i.e.
      the opposite order from `fch_check`'s. One row; the rest of the FIELD
      channel domain is `make badfnum-acceptance`'s.

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

- [x] ✅ **~~`loc_next`'S PARKED FRAME (`LOC_RET`) IS NOW UNNECESSARY, ~9 B, AND
      DELIBERATELY NOT TAKEN~~ — TAKEN 2026-08-21 as D-LOCPARK, and it is
      **−11 B**, not ~9.**
      [`docs/spec-basic-locarg.md`](docs/spec-basic-locarg.md) §11.
      **Main page 1: 2 B → 13 B**; low 22 B, sub p0 3299 B, sub p1 1619 B all
      unmoved. `locarg-acceptance` 45/45, `missing-acceptance` OK,
      `abort-acceptance` 49/49, `stmtpend-acceptance` 60/60, `onerr0` 24/24,
      `screenerr` 61/61, `width` 94/94, `penderr` 61/61, `tmfp` 50/50.
      🔴 **THE FILED ENTRY OVER-CLAIMED WHAT THE PARK DID.** It said the change
      moves the depth of `loc_more` and the apply-then-reject ordering as well as
      the domain check. It does not: both run in `ex_locate` AFTER `loc_next` has
      returned, so their depth is `ex_locate`'s in either world. Only
      `loc_missing` and `call eval_byte_checked` move, and both were already
      depth-independent — verified by reading BOTH arms of `raise_error_hl`, not
      one. Enumerating the three separately is what caught it.
      💰 **THE 11 BYTES ARE NOW THE PAGE-1 BUDGET** two other filed items were
      declined against: `VALTYP`'s 3 B cold init (D-VALTYP) and the
      `dsk-bloadmode` face (D-BLNF). Re-read the wall before quoting this.
      The original entry follows.
      ~~💰 Filed 2026-08-09 by D-LOCARG~~
      ([`docs/spec-basic-locarg.md`](docs/spec-basic-locarg.md) §3.1). The park
      exists because the abort chain used to PRINT AND RETURN; `4d35b6d` made
      aborts depth-independent (`fre_abort_low` resets `SP` from `SAVSTK`), which
      is what licensed the −29 B carve above. The same refutation licenses
      deleting `pop de` / `ld (LOC_RET),de` and `loc_ret`'s three-instruction
      re-push in favour of an ordinary `call`/`ret` — but that changes the depth
      of `loc_more`, `loc_missing` and the apply-then-reject ordering as well as
      the domain check, and **D-LOCARG deliberately moved one thing at a time**.
      📏 The instrument already exists: `make locarg-acceptance`'s 11 `u.*` rows
      run every abort class untrapped and read the whole screen tail, which is
      exactly the "two messages for one statement" failure the park prevents.
      💰 ~9 B, denominator already built, not scouted.

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

- [x] ✅ **`OPEN "X" FOR APPEND AS #1` ON A NON-EXISTENT FILE — MEASURED AND
      CLOSED 2026-08-20 (D-LOADERR), and BOTH filed columns were the readout
      lying.**
      [`docs/loaderr-msx1-characterization.md`](docs/loaderr-msx1-characterization.md).
      The reference does **not** print nothing: it raises **`File not found in
      10`** and stops. zerobas does **not** say `OK`: it prints **`load error`**
      and then runs on into the `[OK]`.
      🎯 **`<NO OUTPUT>` WAS `File not found` ALL ALONG** — the classifier simply
      did not know the name, so a real error fell through to the sentinel. The
      item said characterising it *"needs a SCREEN-TAIL readout, not a bracket
      span"*, and that was exactly right: the readout was the whole obstacle,
      and D-FNARG2's error-first `errface()` plus five error names in `ERRORS`
      is the entire fix to it. 🔴 **AND THE SAME BLINDNESS CORRUPTED THE OTHER
      COLUMN**: zerobas's `OK` was `bracket()` finding the `[` above the message.
      **One blind readout wrote both halves of a filed row, and neither was a
      reading** [[readout-blind-to-its-own-subject]].
      ⚠️ It is not an APPEND question at all. `FOR INPUT` on a missing file does
      exactly the same thing on both machines, and so do `LOAD`, `BLOAD`,
      `RUN"f"` and `MERGE` — it is the `load error` class, filed below with all
      six verbs measured.
      *Original filing:* — 🔴 **`OPEN "X" FOR APPEND AS #1` ON A NON-EXISTENT
      FILE: zerobas SAYS `OK`, THE CF-3300 PRINTS NOTHING AT ALL.** Filed
      2026-08-19 by D-FNARG
      ([`docs/fnarg-msx1-characterization.md`](docs/fnarg-msx1-characterization.md)
      §3), found by a CONTROL written to explain a different row's `<NO OUTPUT>`.
      ```
      OPEN"FB1.DAT"FOR APPEND AS #1 : CLOSE#1 : PRINT"[OK]"     (FB1.DAT absent)
          cf3300 -> <NO OUTPUT>        zb -> [OK]
      ```
      (row `f.applit`, `make namspc-acceptance`; DEFERRED, measured, printed.)
      🎯 **A LITERAL FILENAME — NOTHING TO DO WITH D-FNARG's SUBJECT.** Its twin
      `f.appvarx` (APPEND + variable + a file that EXISTS) reads `OK` on the
      CF-3300, which is what proves the mode-plus-missing-file pair is the
      variable here and not the argument form.
      🔴 **WHAT THE REFERENCE DOES IS UNMEASURED AND MUST NOT BE GUESSED.**
      `<NO OUTPUT>` means this row's readout could not capture it — an error
      that did not print, a hang, a prompt that never came back. It is **not**
      evidence that the reference errors. Characterising it needs a SCREEN-TAIL
      readout, not a bracket span
      ([[read-the-artifact-when-the-screen-cannot-witness]]), and that comes
      before any byte. 💰 Not scouted, not priced.
      ⚠️ ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express it).
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
      ⚠️ ONE REFERENCE (Disk BASIC; a diskless VG-8020 cannot express it).
- [x] ✅ **CLOSED 2026-08-21 (D-FNEXPR + D-FNEXPR2) — `OPEN A$ AS #1` IS `Syntax error` HERE AND `OK` ON THE CF-3300.**
      Filed 2026-08-08 by D-NAMSPC, found while measuring something else
      ([[readout-blind-to-its-own-subject]]). A **variable** filename in `OPEN`:
      ```
      10 A$="TS.DAT" : 20 OPEN A$ AS #1 : 30 CLOSE#1 : 40 PRINT"[OK]"
      cf3300 -> [OK]     zb -> Syntax error in 20
      ```
      ⚠️ **NOTHING TO DO WITH SPACES** and unaffected by D-NAMSPC — the `$`
      suffix terminates the name scan before the ` AS`, so this reads the same
      before and after. It is a filename-argument question (literal vs
      expression), and it is one row: **it needs its own denominator** —
      `OPEN` / `KILL` / `NAME` / `SAVE` / `LOAD` / `BLOAD` × (literal /
      variable / expression), plus whether the same holds for `FOR INPUT`/
      `OUTPUT`/`APPEND` forms. 💰 Not scouted and not priced.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, exactly as filed, down to the
      line number in the message**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.5): CF-3300 `[OK]`, zerobas `Syntax error in 20`, against an
      `OPEN"TS.DAT"AS #1` literal control reading `[OK]` on both.
      ✅ **THE DENOMINATOR IS BUILT AND THE RULE IS WIDER THAN `OPEN` —
      2026-08-19 (D-FNARG)**,
      [`docs/fnarg-msx1-characterization.md`](docs/fnarg-msx1-characterization.md),
      14 `f.*` rows in `basic_probe_namspc.py`, all DEFERRED.
      🎯 **WHEREVER THE REFERENCE ACCEPTS A FILENAME IT ACCEPTS A STRING
      EXPRESSION; zerobas accepts a LITERAL and nothing else.** Eight divergent
      rows, four green controls: `OPEN` bare / `FOR INPUT` / `FOR OUTPUT` /
      `FOR APPEND`, `KILL`, and `NAME` (both operands) all read `OK` on the
      CF-3300 with a variable and `Syntax error` here.
      🎯 **`f.expr` (`A$+".DAT"`) AND `f.paren` (`(A$)`) RULE OUT THE CHEAP
      FIX** — the reference EVALUATES an expression; "also accept a bare string
      variable" would close one row and leave the rule unmet.
      ✅ **THE OTHER FOUR VERBS ARE MEASURED — 2026-08-20 (D-FNARG2)**,
      [`docs/fnarg2-msx1-characterization.md`](docs/fnarg2-msx1-characterization.md).
      `SAVE`/`LOAD`/`BLOAD`/`FILES` were PREDICTED here and never driven; they
      are now 8 more deferred rows (`namspc-acceptance` 58/58, deferred 14 → 22).
      🎯 **THE RULE HOLDS AT ALL SEVEN VERBS AND THE FACE DOES NOT** — only
      `OPEN`/`KILL`/`NAME` RAISE. `SAVE`/`LOAD`/`BLOAD` print a non-raising
      `load error` and run on (filed separately); `FILES` reads a non-quote as
      *no filespec*, lists the whole directory, and derails later. One rule,
      three mechanisms — so *"all seven verbs diverge identically"* was the
      source reading, not the measurement.
      💰 **SCOUTED, NOT PRICED: ONE MECHANISM AT 11 SITES.** `do_open`
      is `cp '"'` / `jr nz,oo_synerr` and then reads the name **straight out of
      the program text** via `parse_disk_fcb`, whose cursor IS the interpreter's.
      So these are not seven bugs but one parser reached from **11
      `parse_disk_fcb` call sites** across five files (`files.asm` ×6,
      `save.asm` ×2, `cload.asm` ×2, `bload-body.inc` ×1), each behind its own
      literal-quote gate. The fix is a SECOND SOURCE for a shared parser plus a
      staging buffer — a design question, not an edit — and with main page 1 at
      22 B on 2026-08-19 it is not opened here.
      🔴 **THAT PRICE NAMES THE WRONG UNIT — CORRECTED 2026-08-21 (D-FNEXPR),
      AND IT WAS WALKED, NOT RE-READ.** The 11 `parse_disk_fcb` sites are real
      and are **not the change surface.** The sites that refuse an expression
      are the **QUOTE GATES** — ~13 opening and ~5 closing across five files,
      with **six** different error faces (`stmt_error`, `load_error`,
      `oo_synerr`, `bl_load_error`, `df_nofilespec`, and `RUN`'s bare-`RUN`
      fallthrough at [`basic/cload.asm:185`](basic/cload.asm:185), genuinely
      ambiguous with `RUN <lineno>`).
      🎯 **AND `parse_disk_fcb` NEEDS NO SECOND SOURCE.** It walks `(HL)` to a
      `"` and is already source-agnostic, so pointing it at a staged buffer cost
      **zero bytes and zero edits** — which is the expensive half of the filed
      design, and it was never needed.
      ✅ **THE RAISING HALF IS CLOSED — 2026-08-21 (D-FNEXPR)**,
      [`docs/spec-basic-fnexpr.md`](docs/spec-basic-fnexpr.md), **+26 B main
      page 1**. `fname_expr` ([`basic/files.asm`](basic/files.asm)) evaluates the
      filename with `str_eval` and stages it in `STRSCR`, parking the resume
      cursor in `FN_RESUME` ($E227 — the cell D-LOCPARK freed one day earlier
      and deliberately left NAMED). `OPEN` / `KILL` / `NAME` take a string
      EXPRESSION; **13 deferred rows graduated**, `namspc-acceptance` 62/62 →
      **75/75**, deferred 23 → 10.
      ✅ **AND THE `load error` FAMILY IS CLOSED TOO — 2026-08-21 (D-FNEXPR2)**,
      [`docs/spec-basic-fnexpr2.md`](docs/spec-basic-fnexpr2.md), **+36 B main
      page 1 RECOVERED** (14 B → 50 B; the fix is a CARVE, not a spend).
      `SAVE`/`BSAVE`/`LOAD`/`BLOAD`/`FILES` take a string EXPRESSION;
      `namspc-acceptance` 75/75 → **95/95**, deferred 10 → 5, and D-FILESIDE's
      `f.filesvarl` graduated with them (5 listed entries → 0).
      🔴 **AND THE PARAGRAPH ABOVE — the one this replaces — DESCRIBED A TREE
      THAT HAD ALREADY CHANGED.** It said the remainder was "a DIFFERENT
      MECHANISM": a PRINTED, non-raising `load error`. Re-read at `cffb34d`
      *before any edit*, `f.loadlit` and `f.bloadlit` BOTH already answered
      `File not found` on both sides — D-LOADERR-FIX (08-20) and D-BLNF (08-21)
      had retired the printed face at LOAD and BLOAD as a SIDE EFFECT. What
      actually remained was four rows and every one was the ARGUMENT SHAPE, i.e.
      D-FNEXPR's own rule at four more verbs. **A deferred row is a denominator
      only while somebody re-reads it** — the gap sweep's D-LINEMAX lesson, one
      week later, in the item the same sweep ranked FIRST.
      🎯 **AND THE NON-STRING FACE WAS MEASURED RATHER THAN CONVERGED BY
      ASSUMPTION.** `OPEN 5` / `KILL 5` / `SAVE 5` / `LOAD 5` / `BLOAD 5` /
      `FILES 5` are **`Type mismatch`** on the CF-3300 — one face at all six,
      where zerobas had three. That closes D-FNEXPR §3.3's filed question and
      shows its preserved `Syntax error` was wrong. 🔴 But `Type mismatch` is
      not the whole rule: `SAVE 1/0` is **`Division by zero`**, because the
      reference EVALUATES and the operand's own fault wins — D-MISS-1's `A$=1/0`
      rule at the filename position. 💰 **Cost of the correct face: ZERO
      BYTES**; `els_tc_common` (`basic/missing.asm`) already IS that tail and
      already had two entry points, so it took one changed jump target.

- [x] ✅ **THE RE-RAISE NAMED THE WRONG LINE WHEN THE TWO CONTEXTS DISAGREED ON
      *MODE* — CLOSED 2026-08-09 by D-LOCARG**
      ([`docs/spec-basic-locarg.md`](docs/spec-basic-locarg.md) §5), at
      **exactly the +7 B priced here**, funded by the −29 B `loc_next` carve
      above. `derive_directf` (basic/program.asm) is extracted from `rp_exec` and
      called from `oe_reraise`; `make onerr0-acceptance` is **24 rows / 24
      SCORED / 0 deferred** and its `DEFERRED` dict is EMPTY — emptied by fixing
      the rows, not by rescoring them. Knife **K-LA4** reddens exactly these two
      rows and nothing else, both rounds; **K-LA3** forces the constant this
      item says cannot serve and reddens exactly one, `d.dirtrap`.
      🔴 **AND THE FIRST PLACEMENT OF THE NEW ROUTINE DID NOT ASSEMBLE**: 14 B
      dropped inside the run loop pushed a backward `jr rp_lp` past −128 — the
      identical failure D-CONTR recorded two instructions below the same span,
      whose remedy costs 1 B. Siting the routine **outside** the span costs 0.
      **Where a routine goes is a price.**
      **The original filing, for the record:**

- [x] 💰 ~~**THE RE-RAISE NAMES THE WRONG LINE WHEN THE TWO CONTEXTS DISAGREE ON
      *MODE* — `DIRECTF` IS NEVER RE-DERIVED. Filed 2026-08-09 by D-ONERR0,
      PRICED AT +7 B AGAINST A 0 B WALL.**~~ Two rows, both references agreeing,
      failing in **opposite** directions:

      | row | shape | both references | zerobas |
      |---|---|---|---|
      | `d.instop` | handler SUSPENDED by `STOP`, `ON ERROR GOTO 0` **typed** at the prompt | `Out of memory in 20` | **`Out of memory`** |
      | `d.dirtrap` | the ERRORING statement was **typed**, the disarm is in a stored handler | `Out of memory` | **`Out of memory in 0`** |

      🎯 **THAT THEY FAIL IN OPPOSITE DIRECTIONS IS THE FINDING.** D-ONERR0's
      re-raise restores `CURLINE` and `SAVTXT` and aborts through `rerr_msg`,
      which never passes `rp_exec` — the **only** place that DERIVES `DIRECTF`
      from `CURLINE`'s high byte ([`basic/program.asm`](basic/program.asm), the
      `rpe_mode` block). So the mode cell keeps whatever the *re-raising*
      statement had. Forcing `DIRECTF := 0` fixes `d.instop` and breaks
      `d.dirtrap`; forcing `1` does the reverse — **so the answer is a derive,
      not a constant, and a 4-byte fix is refuted before it is written.**
      💰 **PRICE: +7 B.** Extract `rp_exec`'s six-instruction derive as a shared
      `derive_directf` (+14 B routine, −13 B inlined, +3 B call back = net +4)
      and `call` it from `oe_reraise` (+3). ⚠️ **MAIN PAGE 1 HAS 0 B FREE** after
      D-ONERR0, so this needs a carve first; the nearest funded one is the −29 B
      `loc_next` carve ([`docs/spec-basic-evalchk.md`](docs/spec-basic-evalchk.md)
      §6.6), which has its own denominator to build.
      ⚠️ `d.dirtrap`'s `in 0` is not garbage — it is the direct line's own
      lineno field, which `basic/program.asm`'s `dir_line` comment already says
      is a constant 0 precisely so a missed gate prints `in 0` rather than
      nonsense. Both readings were PREDICTED before the fix was measured and
      both landed exactly.
      📏 Measured by `make onerr0-characterize`, rows `d.instop` / `d.dirtrap`,
      DEFERRED in the gate (`21/23` scored, these two printed and not scored) —
      [`docs/spec-basic-onerr0.md`](docs/spec-basic-onerr0.md) §7,
      [`docs/onerr0-msx1-characterization.md`](docs/onerr0-msx1-characterization.md)
      §5.1.

- [x] ✅ **DONE 2026-08-09 (D-ONERR0) — `ON ERROR GOTO 0` INSIDE A HANDLER
      RE-RAISES. 13/23 → 21/23 (+2 deferred, priced above), +16 B, main page 1
      16 B → 0 B.** Spec [`docs/spec-basic-onerr0.md`](docs/spec-basic-onerr0.md),
      23 rows on three sides in
      [`docs/onerr0-msx1-characterization.md`](docs/onerr0-msx1-characterization.md),
      gate `make onerr0-acceptance`.
      🎯 **THE SCOPE CAME FROM A ROW NOBODY HAD FILED.** `ON ERROR GOTO <n>`
      inside a handler **RE-ARMS and runs on** (`r.rearm`, all three sides), so
      the rule is about `GOTO 0` and not about `ON ERROR` — which is what keeps
      the fix at one test on the existing disable arm.
      🔴 **THE CHEAPER DESIGN WAS REFUTED BY THE ROW WRITTEN TO TEST IT.**
      "Disarm, then RESUME" costs **+7 B instead of +16 B** and would have closed
      the two rows above as well, because returning through `rp_exec` re-derives
      `DIRECTF` for free. `r.reexec` (`PRINT"[X]";ASC("")`) prints `[X]` **once**
      on both references: the reference restores context and aborts, it does not
      re-execute. **Every other row in the battery answers both designs
      identically** — had the row set been frozen before the design, the cheap
      one would have shipped green.
      🔴 **`r.line` AGREED ON ITS ERROR TEXT FOR THE WRONG REASON** — zerobas ran
      on and raised a *fresh* error at the same line, same code, same message,
      same number; only the `[RANON]` prefix separated them
      ([[readout-blind-to-its-own-subject]]).
      🔴 **AND `e.reraise`'s `ERR`/`ERL` HALF WAS GREEN THROUGHOUT** the defect,
      because `ERRFLG`/`ERRLIN` were written at the original raise and nothing
      reset them. Read forwards, that is the proof the re-raise must **not**
      re-record `ERRLIN` — which is why the entry point is `rerr_msg`, past
      `record_errline`.
      *(original filing kept below for its measurements)*

- [x] ✅ *(superseded by D-ONERR0 above — the original filing, kept for its
      measurements)* 🔴 **`ON ERROR GOTO 0` INSIDE A HANDLER MUST RE-RAISE THE
      CURRENT ERROR, AND ZEROBAS RUNS ON. Filed 2026-08-08 by D-NXARY, found by
      a row that was measuring something else.** Both references agreeing:

      | program | both references | zerobas |
      |---|---|---|
      | `10 ON ERROR GOTO 50` / `20 FOR A=1 TO 2` / `30 NEXT A(1)` / `40 END` / `50 ON ERROR GOTO 0` / `60 DIM A(3)` / `70 PRINT"[OK]"` | **NEXT without FOR** | **`OK`** |

      🎯 **THE REFERENCE NEVER REACHES LINE 60.** `ON ERROR GOTO 0` executed
      *inside* an active handler disables trapping **and re-raises the error that
      entered the handler**, so the program stops with the original message.
      zerobas disarms and runs on, printing `[OK]` — an untrapped error that
      never surfaces, the same shape as a swallowed error.
      ⚠️ **This is the error-handling surface, not `FOR`/`NEXT`** — it was found
      because D-NXARY's first `a.autodim` used that idiom to disarm before a
      `DIM`, and the row read as a clean 3-side divergence while answering a
      question nobody asked ([[readout-blind-to-its-own-subject]]). Recorded in
      [`docs/nxary-msx1-characterization.md`](docs/nxary-msx1-characterization.md)
      §3.
      💰 Not scouted and not priced. ⚠️ Needs its own denominator first:
      `RESUME` vs falling off the end of a handler, `ERR`/`ERL` after the
      re-raise, and whether a *second* `ON ERROR GOTO n` inside a handler
      re-arms rather than re-raising.
      🔴 **RE-MEASURED 2026-08-09 — STILL LIVE, AND THE ZEROBAS READING ABOVE IS
      NOT**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.6). Both references still stop at **`NEXT without FOR in 30`**.
      zerobas no longer prints `OK` — it prints **`Redimensioned array in 60`**.
      🎯 **Both readings say the same thing about the RULE and different things
      about the PROGRAM.** The references never reach line 60; zerobas does. What
      moved underneath is **D-NXARY** (2026-08-08): `NEXT A(1)` now AUTO-DIMS
      `A(0..10)` at line 30, so line 60's `DIM A(3)` is a redimension. The
      swallow is intact — the handler disarmed and execution continued — it now
      trips a *different, wrong* error two lines later instead of running clean
      to `[OK]`.
      ⚠️ **SO IT IS NO LONGER A SILENT-SWALLOW ROW, AND A GATE WRITTEN AGAINST
      THE FILED `OK` WOULD FAIL ON AN UNCHANGED TREE.** Whoever builds the
      denominator must pick a payload after line 60 that D-NXARY's auto-DIM does
      not touch. The control that keeps this honest is the same program with
      `50 PRINT"[TRAPPED]"`: it reads `[TRAPPED]` then `No RESUME in 50` on all
      three sides, so the trap itself is not the variable — `ON ERROR GOTO 0`
      is.
      ✅ **CLOSED 2026-08-09 by D-ONERR0**, which took that warning: every
      program in its 23-row battery is ARRAY-FREE (the error comes from
      `ERROR n`), so no slice of the arrays arc can rot it again.
- [x] ✅ *(superseded — the original filing, kept for its measurements)*
      **`NEXT A(1)` — A `NEXT` OPERAND IS A FULL VARIABLE REFERENCE AND THE
      REFERENCE EVALUATES THE SUBSCRIPT. Filed 2026-08-08 by D-NXLIST, DECLINED
      WITH A PRICE, three rows measured on both references:**

      | row | program | both references | zerobas |
      |---|---|---|---|
      | `m.ary` | `FOR A=1 TO 2` / `NEXT A(1)` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
      | `m.ary9` | `FOR A=1 TO 2` / `NEXT A(99)` / `PRINT"[OK]"` | **Subscript out of range** | **Syntax error** |
      | `m.aryspc` | `FOR A=1 TO 2` / `NEXT A (1)` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |

      🎯 **`m.ary9` IS WHAT PRICED THE DECLINE, AND IT EXISTS ONLY BECAUSE THE
      CHEAP FIX WAS COSTED FIRST.** That fix is **8 B**: after `for_name`, a `(`
      in the cursor makes the parsed key unmatchable, `nx_scan` walks the stack
      out and `nx_nofor` raises ERR 1 — D-FORVAR's own `n.strnx` trick, and
      exactly `m.ary`'s answer. But 99 is outside an auto-DIMmed `0..10` and the
      references answer **Subscript out of range**, so they run a complete
      variable-reference parse *before* matching anything. The 8-byte fix would
      **trade one red row for another** ([[a-priced-decline-is-a-claim-about-a-design]]),
      and `m.aryspc` adds that the `(` is not even lexically contiguous, so the
      test would need `skip_spaces` too.
      **The faithful fix is an array-element reference parse in `ex_next`** — the
      D-ARYLV / lvalue family, not the LIST family. Unpriced: it needs a subscript
      evaluator at a site that today has none, and its own error-face rows (what
      does `NEXT A$(1)` answer? `NEXT A(B)` with `B` unset?).
      All three rows are **measured, printed and scored in NEITHER direction** by
      `nxlist-acceptance`; a deferred row that started agreeing would itself be a
      finding. 💰 Page 1 is at **15 B** after D-NXLIST, so this one is not blocked
      on bytes — it is blocked on being a different rule.
- [x] ✅ **`ex_let_arr_str`'s out-of-string-space — CLOSED 2026-08-20 by
      D-ARYOOS**, [`docs/aryoos-msx1-characterization.md`](docs/aryoos-msx1-characterization.md).
      Filed 2026-08-08 as *"SWALLOWS AN OUT-OF-STRING-SPACE AND THE PROGRAM RUNS
      ON"*. Shipped fix: **1 byte** (low region 23 → 22 B), `make
      clearpool-acceptance` **56/58 → 62/62**.

      🔴 **HALF THE FILED DEFECT HAD ALREADY BEEN CLOSED, BY A SLICE THAT NEVER
      CLAIMED IT, AND THE ITEM CARRIED A FALSE HEADLINE FOR ELEVEN DAYS.**
      zerobas does not swallow the error and the program does not run on: it
      answers `Out of memory in 50` — the right LINE, the wrong MESSAGE. The
      staleness sweep that re-read this row LIVE (`14dc44d`,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.7) is the commit IMMEDIATELY BEFORE `3dc1e7b`, D-STMTPEND, which fixed
      it the same day. D-STMTPEND's own header names this class — *"a fault
      raised by a driver that never calls `check_expr_errors` got silently
      discarded"* — and `ex_let_arr_str` ends `jp exec_stmt`, which is exactly
      that driver. Nobody re-ran §4.7.

      🎯 **WHAT SURVIVED WAS THE ITEM'S OWN TRAP PARAGRAPH, AND IT WAS RIGHT.**
      It predicted that the cheap check would land on `ARY_ERR=4` → `FPERR=6` →
      **ERR 7 `Out of memory`** where both references say **`Out of string
      space`** (ERR 14), *"green on any gate that only asks did-it-error"* —
      which is precisely the state D-STMTPEND left behind without adding a
      check. Every D-ARYOOS row is therefore scored on the MESSAGE.

      🎯 **THE SPLIT IS BY SITE, NOT BY TYPE — and the denominator row is what
      ruled out the cheap reading.** The item said the `DIM` half was
      UNMEASURED. Measured now, three-sided: `CLEAR 100:DIM A$(20000)` is a
      **string** array whose 3-byte slots will not fit VARIABLE space, and all
      three machines answer `Out of memory in 20`. So `aeng_copy_str`'s
      heap_alloc OOM gets its own `ARY_ERR=5` → `FPERR_STROOM` → ERR 14, while
      `ary_alloc`/`scv_alloc` keep 4 → ERR 7. `ld a,4`→`ld a,5` is free; the
      whole price is `ary_errmap`'s 5th entry.

      🔴 **THE ROW WRITTEN TO MEASURE THE SECOND SITE REFUTED ITSELF.**
      `basic/vars.asm`'s `tss_ary` (READ / INPUT / LINE INPUT / INPUT# / FIELD
      read) already checked the NZ, so only its message was wrong, and the same
      split fixes it. `READ A$(2)` was chosen to prove it and answered **`[OK]`
      on both references** — a stored `DATA` literal's descriptor points at the
      PROGRAM TEXT there and charges the pool nothing. The scalar twin
      `READ D$` diverges the same way, which is what proves it is S-CLP-5 body
      ownership and not this rule. `INPUT A$(2)` is the valid row (transient
      buffer, so the reference must copy) and agrees on all three sides after
      the fix. Residual filed below.

      🔴 **THREE DOC SITES ASSERTED "COPY_STR CANNOT FAIL"** and had been false
      since slice 4a made the copy heap-allocate: `ex_let_arr_str`'s
      `-> always Z (op=3 cannot fail)`, `sub/arrays.asm`'s tenant header, and
      `aeng_copy_str`'s own *"no main-ROM change was needed"* (true about
      SURFACING, false about the MESSAGE). All three corrected.

      🔴 **A BATTERY DECLARED UNMEASURABLE WAS THE CLEANEST AGREEMENT IN THE
      SLICE.** The four `arychg` pool-arithmetic rows were written
      reported-never-gated on the strength of the `share` battery's *"an alias
      charges twice there"* — a sentence about `B$=A$` that does not generalise
      to a store out of a temp. Three of the four predictions were wrong in the
      same direction; all four agree to the byte and are now GATED.

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
- [x] ✅ **~~THREE OF `tss_ary`'s FIVE CALLERS ARE UNMEASURED FOR THE ERR-14
      MESSAGE~~ — MEASURED 2026-08-21 (D-ARYSITE), ALL THREE AGREE, 0 ROM
      BYTES.** Five rows in `make inputary-acceptance` (**7/7 → 14/14**),
      [`docs/aryoos-msx1-characterization.md`](docs/aryoos-msx1-characterization.md)
      §6. `LINE INPUT A$(2)`, `INPUT#1,A$(2)` and `LINE INPUT#1,A$(2)` on a
      pool with ten bytes left all answer `Out of string space` on vg8020 /
      cf3300 / zerobas, with the scalar twins as controls and two `CLEAR 200`
      fit controls so the battery is not satisfied by a machine that errors at
      everything.
      🔴 **AND THE DENOMINATOR IN THIS ITEM WAS WRONG: THERE IS NO FIELD
      CALLER.** `tgt_store_str` has FOUR call sites by grep — READ, console
      INPUT, console LINE INPUT, and `INPUT#n`+`LINE INPUT#n` sharing
      [`basic/files.asm:781`](basic/files.asm). `basic/field.asm` reaches
      `tgt_parse_fld` → `tgt_parse` and never `tgt_store_str`: FIELD BINDS a
      descriptor into the record buffer and runs no `heap_alloc`, so this OOM
      cannot happen there. 🎯 **Half this item's filed cost was a `FIELD`+`GET`
      fixture for a caller that does not exist**, and one grep retired it. The
      source's own *"these FIVE store paths"* is right about VERBS; the
      characterization turned the fifth verb into a fifth SITE.
      🎯 **AND THE FILE ROWS WRITE NOTHING** — `HI.TXT` on `disk/test720.dsk` is
      a 24-character line, over the ten-byte headroom and under the 25 the
      console rows type, so no row needs a private disk copy.
      Knives 3/3 EXACT; K-AS3 (`tss_ary`'s `ld a,3` → `ld a,0`) reddens exactly
      the seven rows that go through the shared tail and leaves the numeric and
      scalar rows green, which is the measurement that "by construction" was
      standing in for.
- [x] ✅ **RE-RAN THE STALENESS SWEEP'S "LIVE" ROWS — DONE 2026-08-20, same
      day it was filed. 8 of 11 already closed by named slices, the other 3
      confirmed still live.** Detail below; the addendum is
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §7. Filed as *"one of them was fixed by the next commit and stayed filed
      for eleven days"*, which is true of §4.7 and of nothing else.
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      re-measured 17 items on 2026-08-09 at `14dc44d` and marked 11 LIVE. The
      VERY NEXT COMMIT, `3dc1e7b` (D-STMTPEND), closed half of §4.7 — the
      swallow half of the `ex_let_arr_str` finding — and D-PENDERR (`34a6efe`)
      and D-TMFP (`38becce`) landed in the same run of error-plumbing work.
      🎯 **A SWEEP READING IS STAMPED WITH A COMMIT, AND THE COMMIT AFTER IT CAN
      FALSIFY IT** — nothing in the apparatus notices, because a sweep writes
      prose and no gate reads prose.

      🔴 **THIS ITEM'S OWN FIRST DRAFT OVERSTATED ITS DENOMINATOR, AND ONE GREP
      REFUTED IT.** It said *"the other ten LIVE rows have never been re-read"*.
      Machine-checked against `TODO.md` at `ef50f4c` — resolve each §4.x claim to
      its ENCLOSING `- [ ]`/`- [x]` — the eleven LIVE rows are:

      | § | claim | today |
      |---|---|---|
      | 4.1 | `INPUT #n` parses one target | ✅ closed D-INPLIST |
      | 4.2 | `VARPTR(<unset>)` | ✅ closed D-VPTRDOM |
      | 4.3 | `FIELD overflow` vs record length | ✅ closed D-RECLEN |
      | 4.4 | `LOCATE` defer vs coercion | ✅ closed D-LOCARG |
      | 4.5 | `OPEN A$ AS #1` | 🔵 OPEN — **re-measured 2026-08-19 (D-FNARG)** |
      | 4.6 | `ON ERROR GOTO 0` re-raise | ✅ closed D-ONERR0 |
      | 4.7 | `ex_let_arr_str` | ✅ closed D-ARYOOS |
      | 4.8 | line store bounded by `TXTMAX` | 🔵 OPEN — last read 2026-08-09 |
      | 4.9 | `VALTYP $E0C8` = `$FF` cold | 🔵 OPEN — last read 2026-08-09 |
      | 4.10 | `RETURN` vs an open `FOR` | ✅ closed D-FORRET |
      | 4.11 | `DEFINT` stores other bytes | ✅ closed D-DEFINTTOK |

      🎯 **EIGHT OF ELEVEN WERE CLOSED BY NAMED SLICES WITH THEIR OWN GATES, so
      the pickup list was being worked, not rotting** — and §4.5 is not stale
      either: D-FNARG re-read it as 14 `f.*` rows, DEFERRED **inside a committed
      gate**, which is a live detector rather than prose and cannot go stale
      silently [[a-pinned-divergence-is-a-live-detector]]. 🔴 **Only §4.7 rotted,
      and it rotted for exactly one reason: its fix was a SIDE EFFECT of another
      slice, so no slice ever grepped the list for it.** That is the shape to
      guard — *"when a slice lands, grep the list for what it just shipped"*
      catches a slice's OWN subject and misses what it closed by accident.
      ➡️ **§4.8 and §4.9 were the two left to re-read, and both were re-read the
      same day: STILL LIVE, BYTE FOR BYTE**, four predictions written first and
      all four EXACT (` 148 `/` 148 `/` 646 `; the 32-byte line refused by both
      references and stored here; `VALTYP $E0C8` = `ff`). So the sweep's LIVE
      column now reads **8 closed / 3 live**, and every one of the three carries
      a 2026-08-19-or-later reading.

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
- [x] ✅ **~~`BLOAD` OF A FILE THAT EXISTS AND IS NOT BINARY IS `Bad file mode`
      THERE AND `load error` HERE — A FACE NO ARM IN THE TREE PRODUCES~~ —
      CLOSED 2026-08-21 as D-BLMODE, +1 B main page 1 (13 → 12 B) and +4 B sub
      page 1 (1619 → 1615 B).**
      [`docs/loaderr-fix-notes.md`](docs/loaderr-fix-notes.md) §7.
      `dskmsg-acceptance` **11 gated + 1 printed → 15 gated + 0 printed**; the
      holding pen is EMPTY and was emptied by fixing all seven.
      🔴 **THE FILED PRICE WAS WRONG IN BOTH HALVES, AND ONE GREP SAID SO.** This
      entry said zerobas "has neither the message nor an ERR code for it" and
      called the code **54**. `Bad file mode` is **ERR 61**; its text has shipped
      sub-hosted since D-MSGMIGRATE (`sub/errmsg.asm em_bad_filemode`) and three
      `FIELD`/`GET` sites already raise it. 54 in this tree is `File already
      open`. So the whole "new error face / message-table entry" half of the
      price was ALREADY PAID, and what was left was a jump target and a value.
      🎯 **AND THE FOURTH `BL_STAT` VALUE IS A *CODE*, NOT AN INDEX** — the cell
      is now 0 = loaded, 1 = printed `load error`, n = RAISE ERR n. The stub is
      `cp 1` for `dec a` and `jp raise_error` for `jp df_notfound`: **one byte**,
      where a fourth enumerated value would have been six.
      ✅ **THE DISPOSITION IS MEASURED, NOT ASSUMED** — the reference RAISES and
      STOPS, read as a stored program with a marker on the next line and
      calibrated in BOTH senses by `BLOAD"PROG.BIN"` (runs on) and
      `BLOAD"NOSUCH.BIN"` (stops). The divergence was TWO things, a message and a
      disposition, and every shipped row was blind to the second.
      🎯 A fourth row, `BLOAD"TEST.BIN"` (data with a `.BIN` name), is what makes
      it a rule about the **`$FE` marker** rather than the extension.
      Knives **3/3 EXACT** (K-BM1 the code, K-BM2 the stub's raise → print, which
      reproduces the filed pre-fix reading verbatim, K-BM3 probe-side → rc 2).
      ⚠️ NEW HAZARD, NAMED IN THREE PLACES: BLOAD can never raise ERR 1 through
      `BL_STAT`, because 1 means "printed". The original entry follows.
      ~~🔴 A FACE NO ARM IN THE TREE PRODUCES.~~
      Measured 2026-08-20 (D-LOADERR), still divergent at D-BLNF (2026-08-21):
      row `dsk-bloadmode` in `make dskmsg-acceptance`, PRINTED and not gated,
      `BLOAD"PROG.BAS"` → cf3300 `Bad file mode`, zb `load error`.
      🎯 **NOT A SMALLER VERSION OF THE NOT-FOUND ITEM ABOVE, AND D-BLNF DOES
      NOTHING FOR IT.** `fat_find` SUCCEEDS on this path; the reject is the `$FE`
      BSAVE-marker check in [`basic/bload-body.inc`](basic/bload-body.inc), so
      there is no mount/find boundary to read it off. The reference tells NOT
      FOUND apart from WRONG KIND with a THIRD message; zerobas has neither the
      message nor an ERR code for it. Shape: a fourth `BL_STAT` value plus a new
      error face, i.e. a message-table entry — the D-MSGSUB machinery exists.
      💰 **NOT PRICED, and the main-side half lands on a wall measured at 2 B on
      2026-08-21** — carve-scout before writing anything
      ([`tools/carve_scout.py`](tools/carve_scout.py)).
      ⚠️ Whether the reference raises it (stops) or prints it is NOT measured
      either; the D-LOADERR reading captured the message, not the disposition,
      and `Bad file mode` is a documented MSX ERR code (54), which makes "it
      raises" a plausible-and-therefore-dangerous assumption.
- [x] ✅ **CLOSED 2026-08-21 (D-FNEXPR2), 0 EXTRA BYTES — `FILES A$` LISTS THE
      WHOLE DIRECTORY BEFORE IT ERRORS.**
      [`docs/spec-basic-fnexpr2.md`](docs/spec-basic-fnexpr2.md) §3.2/§5.
      `do_files` tests for an ARGUMENT (end-of-statement or `:` = no filespec)
      instead of for a QUOTE, and hands anything else to `fname_expr`. `FILES A$`
      lists **0 entries** and raises `File not found`, exactly as the CF-3300
      does; `FILES 5` lists 0 and raises `Type mismatch`.
      🎯 **`f.filesvarl` IS THE ROW THAT PROVED THE FIX IS A FIX**, and it is
      D-FILESIDE's whole point cashed in: the FACE alone reads the same whether
      the machine refuses at the parse or lists five files first, so only the
      ENTRY COUNT (5 → 0) separates a fix from a no-op. It graduated from
      DEFERRED to a scored row in the same commit.
      🔴 **AND THE FIX OPENED A HAZARD ITS OWN COMMIT CLOSES**, filed here
      because the reasoning is worth keeping: `do_files` parked its dirverb op
      selector in `DISKOP_OP` at the STATEMENT HEAD — the only verb in the family
      that did — justified by a checked claim that `parse_disk_fcb`'s tenant
      "touches DISKOP_OP nowhere". Still true, and no longer sufficient once the
      filespec is an EXPRESSION: `str_eval` can run `INPUT$(n,#ch)`, which
      reaches the drive through `fatprim_bounce`, whose first instruction is
      `ld (DISKOP_OP),a`. The selector now rides the stack across the parse
      (+5 B) and is written where `do_kill` and `do_name` write theirs.
      *The original filing:* Measured
      2026-08-20 (D-FNARG2 §4.2), read off the screen:
      ```
      ZB20 FILES A$                          cf3300, same program:
      TEST    .BIN HI      .TXT PROG    .BIN
      PROG    .BAS PROG2   .BAS
      Syntax error in 20                     File not found in 20
      ```
      🎯 **THE ERROR AGREES WITH D-FNARG'S RULE BY COINCIDENCE OF FACE, NOT OF
      MECHANISM.** `FILES` does not refuse a non-quote:
      [`basic/files.asm:100`](basic/files.asm) reads it as *no filespec*
      (`jr nz,df_nofilespec`), lists everything, and only then derails on the
      unconsumed `A$`. So `f.filesvar` scores as a match for the argument rule
      while the machine has already done something the reference never does.
      ✅ **THE APPARATUS HALF IS DONE — 2026-08-21 (D-FILESIDE), 0 ROM BYTES.**
      Three rows and a third readout (`listface`) in
      [`probes/basic/basic_probe_namspc.py`](probes/basic/basic_probe_namspc.py):
      `f.filesbare` 🟢 (bare `FILES`) and `f.fileslitl` 🟢 (`FILES"FC*.*"`) are
      GATED with LITERAL wants, and `f.filesvarl` is PRINTED and never gated —
      cf3300 `0 entries + <File not found>`, zerobas **`5 entries +
      <Syntax error>`**. `namspc-acceptance` **58/58 → 60/60**, deferred 22 → 23.
      🔴 **A PROBE-SIDE BLINDNESS CANNOT BE CAUGHT BY A DIFFERENTIAL** — both
      columns run the same counter, so a counter that matches nothing reads
      `0 entries` on both sides and the row AGREES. That is why the two controls
      are pinned to literals rather than to cross-side agreement: a blind counter
      fails a positive control on a REFERENCE, which this probe reports as an
      instrument fault (exit 2), not as a regression.
      ➡️ **WHAT IS STILL OPEN IS THE ROM QUESTION, AND IT IS D-FNARG'S.** Whether
      `FILES A$` should refuse the non-quote is the argument-shape design
      question — unpriced, eleven `parse_disk_fcb` sites — and the main-side wall
      measured 2 B on 2026-08-21. 💰 Not priced. What changed is that a row can
      now tell a fix from a no-op.

**Own-design hazards carried out of closed slices**

- [ ] 🔴 **Two type-code namespaces share the value `1`** — the published `DEFTBL`
      string code and zerobas's own variable-chain string tag. D-DEFSTR fixed the
      three sites that crossed them (one was a live memory corruption) but the two
      namespaces still overlap on the numeric values, so the next site that feeds
      one into the other reintroduces the class. Collapse to ONE. Detail:
      *“`DEFTBL_STR` SHOULD BE `3`, NOT `1`”*, line 4072.

**Apparatus / gate limits (each is a stated limit, not a filed defect)**

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

- [x] ✅ **`injector-check` is still a TEXT classifier — CLOSED 2026-08-06 by
      D-INJJUDGE as a measured DECLINE + a denominator fix**,
      [`docs/spec-probe-injjudge.md`](docs/spec-probe-injjudge.md).
      🔴 **The filed fix has recall 0 and so does its maximal generalisation.**
      Walked the shipped rule over all **982** commits with the tool *imported*:
      a concatenation-folding predicate differs from the shipped one in **0**
      commits, and so does **literal soup** — every string literal in a module
      glued together with whitespace stripped, which subsumes the entire *"any
      spelling neither rule knows"* class. The residual's own premise (*"the six
      real copies were all verbatim"*) holds not just for the six but for every
      `.py` this repository has ever contained. The crude alternative was priced
      too: raw text with comments counting flags **12** files and is red in
      **486 of 982** commits, one of them `COMPOSES` on a compliant probe.
      🔴 **What was actually open was the DENOMINATOR, and the gate's headline
      was FALSE.** `SCAN_DIRS` listed three directory names, so **67 of the
      tree's 325** `.py` were never walked — and **three of them compose the
      pre-D-LATCH body**, one character-for-character the frozen
      `latch_check.OLD_KEY` that `make latch-check` row A requires to MANGLE.
      The shipped classifier scores all three `COMPOSES` the moment it is shown
      them: the rule was never at fault. They were invisible for **252, 237 and
      229** commits while the gate printed *"ALL PASS — one injector in the
      tree"*. Widening costs **0** false positives over 982 commits.
      They are **not repaired**: all three are frozen characterization scripts
      cited from `PROVENANCE.md` and two specs, and rewriting a provenance
      record makes it no longer the record. Landed: the denominator **derived**
      from the tree (258 → **325**), a `RECORD` class in
      `tools/injector-record-allow.txt` — two-directional, keyed by path so
      promotion goes stale, with both its claims machine-checked (a content
      digest for FROZEN, an import scan for UNREACHABLE) — an honest headline,
      `MIN_FILES = 300`, and `MIN_SELFTEST_ROWS = 4` plus a polarity bar,
      because **the self-test table could be emptied and still print
      `self-test PASS (rows A-D: …)` and exit 0**, naming four rows it had not
      run. K5 and K9 both read `rc 0` at `6270177`. §6.5 records the re-open
      bar.
- [ ] ⚠️ **`check_probe_preflight.py` carries the IDENTICAL `SCAN_DIRS`** — the
      denominator D-INJJUDGE derived for `injector-check` was left hand-listed
      here, and **6** out-of-scope `.py` launch openMSX. Same shape, different
      rule, and **that rule has not been walked**: widening it on the strength of
      the sibling's measurement is exactly [[a-borrowed-window-inherits-its-corpus]].
      Re-open by walking preflight's own rule over its subject's life first.
      Detail: `docs/spec-probe-injjudge.md` §3.6.
- [x] ✅ **CLOSED 2026-08-21 (D-SEEDPROSE), 15 days after it was filed and after
      it had already fired with a number — an asm label named in a `tools/*.py` or
      `sub/` comment is immune to the dead-code sweep.**
      [`docs/spec-deadcode-gate.md`](docs/spec-deadcode-gate.md) §10. The scrape
      now reads the CODE COLUMN, so prose does not seed and a seed count cannot
      drift on a sentence; the method this item asked for (re-run the closure
      without the seed and diff the live set) is what measured the class at
      **24 B** before the fix. 🔴 **This entry watched the mechanism fire in
      D-EDITVERB and filed the DRIFT rather than the BLINDNESS** — "the next slice
      to see 287 has no way to tell a real seed from a sentence" is the same fact
      as "a span is invisible while a sentence names it", and it took a second
      filing 15 days later, from a slice that lost 6 B to it, to be read that way.
      Original wording:
      ⚠️ **An asm label named in a `tools/*.py` or `sub/` comment is immune to the
      dead-code sweep** — `check_dead_code.py`'s `external_names` scans those
      directories *including comments*, so writing a label's name in prose seeds it
      as reachable. Every slice that edits `tools/` prose must predict the seed
      counts and treat movement as a finding. Detail: lines 2343 and 2579.
      🔴 **IT FIRED FOR THE FIRST TIME, WITH A NUMBER, IN D-EDITVERB (2026-08-06)**
      — main seeds **285 → 286**, the one gained seed being `list_num`, named in
      `sub/lineedit.asm`'s new report-loop comment. So the mechanism is not
      hypothetical and it is not confined to `tools/`: **`sub/` prose seeds too**,
      which is what this item's own title says and what
      [`docs/spec-basic-editverb.md`](docs/spec-basic-editverb.md) §4.4 predicted
      away regardless. That slice measured the cost rather than assuming it —
      dropping the seed leaves the live closure identical, 0 dead either way — so
      what is open is not a hole in the sweep but the fact that **a seed count can
      drift on prose alone**, and the next slice to see 287 has no way to tell a
      real seed from a sentence. §6.7.1 records the method for deciding: re-run the
      closure without the seed and diff the live set.
- [ ] ⚠️ **Three probe page-0 entry addresses stay HARDCODED** —
      `basic_probe_subrom_boot.py` (`$0040`), `basic_probe_subrom_inttest.py`
      (`$0049`), `basic_probe_graphics_floor.py` (`$0058`). All three ARE scored;
      deriving them from `sub/equates.inc` needs its own falsification because they
      inject raw bytes into a bare machine deliberately. Detail: line 2582.
- [ ] ⚠️ **`build/disk.rom` pad-only damage is invisible ON PURPOSE** — 9543 of
      16384 bytes (58.2 %) are `$00` pad in 252 runs. Closing it needs a whole-image
      digest, which would pin the ROM against every legitimate `disk/*.asm` change.
      Re-open only with an argument that answers that. Detail: line 2577.
- [x] ✅ **`make audit-citations` was RED at HEAD and nothing ran it — CLOSED
      2026-08-06 by D-CITEJUDGE**,
      [`docs/spec-audit-citations-gate.md`](docs/spec-audit-citations-gate.md).
      Green; a step of `make basic-reloc` and of CI; denominator **49 → 116**
      files. Two of the four filed claims were wrong.
- [x] ✅ **`audit_citations.py` does not scan `docs/` — CLOSED 2026-08-06 by
      D-DOCJUDGE as a measured DECLINE + a different gate**,
      [`docs/spec-audit-citations-docs.md`](docs/spec-audit-citations-docs.md).
      Scanning `docs/` with the **vocabulary** rule was declined: the quarantined
      text contains **zero** forbidden tokens (its *remediation* is what carries
      one), so recall on every recorded breach is **0**, at a cost of **26**
      affirmative false positives over 278 files — 16 inside the three documents
      that define and record the policy. The filed *"only recorded breach"* was
      wrong (four events; ~50 sites on 2026-07-07), and **6 of those sat in
      `disk/*.asm`, files the tool already scanned** — so it was never a scope
      problem. Landed instead: **check 5**, the decoded-listing shape, repo-wide
      (692 files), which found one **live unremediated** site the 2026-07-07
      full-verify missed in a file it edited. §3.1 records what a future slice
      must produce to re-open the vocabulary widening.
- [x] ✅ **Raw opcode-BYTE renderings — CLOSED 2026-08-06 by D-BYTEJUDGE as a
      measured DECLINE + one narrow gate**,
      [`docs/spec-audit-citations-bytes.md`](docs/spec-audit-citations-bytes.md).
      The class **is** uncovered — 20 offender lines from the two remediation
      commits carry a hex-byte run and checks 1 and 5 flag **0** of them, one of
      them in `disk/kernel.asm` which check 1 has scanned since day one. It is
      declined anyway, **on a proof rather than a threshold**: on
      `tier2-a3-spec.md:20` the offender and its hand-reviewed replacement are
      **byte-identical in the hex run** (only the decoded body was removed), so no
      line rule can separate them; 15 live lines attribute a hex run to the
      reference machine and all were read and KEPT by the 2026-07-07 sweep; and
      `allowed-sources.md` forbids proprietary bytes *"read as anything other than
      an oracle"* — **provenance, not text**. Cost of every variant: **393–1326**
      live lines over 692 files (the landed check 5 had 2). The filed third
      example was already covered: `probes/lib/latch_check.py` is an allowlisted
      check-5 finding already flagged for the human confirm. Landed instead:
      **check 6**, the hex-dump **ROW** — deliberately named for the shape and not
      the class, recall **1 of 20**, **0** hits over 692 files and over all 979
      commits except the range where a 16-byte loader dump actually lived. §3.1
      records what a future slice must produce to re-open the general rule.
- [ ] ⚠️ **The raw-byte class beyond the dump row has NO mechanical floor, by
      measurement** — check 6 covers 1 of the 20 residue lines. The other 19 are
      the human full-verify trail's job, exactly like the inline decoded form
      below. Re-open only with a discriminator scoring **0** on all three of the
      179-line replacement corpus, the **984-line kept-context corpus** (the new
      and harder bar) and the 15 live reference-attributed lines, while still
      firing on ≥1 residue line. Detail:
      `docs/spec-audit-citations-bytes.md` §3.1.
- [ ] ⚠️ **The INLINE decoded form is measured UNDECIDABLE, and that is a standing
      hole, not a closed item** — `$0246: LD A,(…) / AND A / CALL Z,…`. Every
      threshold that catches any of it fires on the hand-reviewed prose that
      replaced it, and on 25–464 honest lines (four variants measured). The human
      full-verify is the only backstop; re-open only with a discriminator that
      scores 0 on the 156-line replacement corpus. Detail:
      `docs/spec-audit-citations-docs.md` §2.2.
- [ ] ⚠️ **Both check-5 allowlist entries need a HUMAN paper-trail confirm** —
      `probes/lib/{omsx_repl,latch_check}.py` render C-BIOS instructions.
      `allowed-sources.md` grades C-BIOS **B/Conditional** ("we don't lift its
      code/expression"), which is a judgement `docs/clean-room-audit.md` reserves
      for a human; the tool deliberately does not make it. Reasons are written in
      `tools/citations-listing-allow.txt`. Detail:
      `docs/spec-audit-citations-docs.md` §2.6.
- [x] ✅ **The 7 `[REVIEW]` advisory headers — CLOSED 2026-08-06 by D-REVJUDGE, at
      3 entries, not 7**,
      [`docs/spec-audit-citations-review.md`](docs/spec-audit-citations-review.md).
      🔴 **Four of the seven were the instrument, not the tree**: they carry a
      document citation at offset 7, 10, 10 and 11 of their own uninterrupted
      comment block, and `SECTION_CITE_LOOKAHEAD = 6` could not reach it — the
      `HEADER_BLOCK_LINES = 45` defect of D-CITEJUDGE, one check over in the same
      file. Writing the 7 justifications as filed would have frozen that defect
      into a control that must keep matching. Measuring the block gives **3**, with
      no `.asm` edited. The 2026-07-04 triage recorded the refutation in its own
      voice (*"whose bodies carry full citations"*) and its own commit fixed the
      **vocabulary** half of the same defect (11 → 7) while triaging the
      **distance** half as genuine. Walked over all 980 commits: the set moved 10
      times (7 under the fixed rule) and has been unchanged since `5225a29`,
      2026-07-01 — **617** commits, and `disk/*.asm|inc` untouched for **300**. So
      recall alone did not justify the list; **what did** is that check 3 was the
      only check in the tool with no self-test, and deleting it outright leaves
      `rc 0` and a green `basic-reloc` (K0). Landed: the block rule, a 12-vector
      section self-test, and `tools/citations-advisory-allow.txt` — two independent
      controls, only removing both is silent (K1d). Promotion to GATING measured
      and declined: it would have been red in **918 of 980** commits.
- [x] ✅ **Check 3's missing negation window — CLOSED 2026-08-06 by D-NEGJUDGE as
      a measured DECLINE + a one-token vocabulary fix**,
      [`docs/spec-audit-citations-negation.md`](docs/spec-audit-citations-negation.md).
      🔴 **The filed fix has precision 0 over the whole history**: walked across
      all **981** commits, a 3-line negation window adds **38** findings the
      shipped rule does not make and **0 of the 38** lack a document citation,
      while disagreeing with the shipped rule in **760** commits. It fails
      structurally, not by tuning — `CLEAN-ROOM` is a `NEGATION` token *and* the
      prefix of this project's citation convention (*"CLEAN-ROOM: published CONST
      contract (map.grauw.nl); no oracle bytes"*), so the window discards the
      citation on every header written in house style; and `\bno\b` matches inside
      `NO-OP`, throwing away a `§5.3` for a hyphen. Check 1's own window was
      knifed first and **is** sound (109 hits, 109 suppressed, all 26
      lookback-only ones read and genuine) — it does not transfer because its
      vocabulary is rare and confined to attestations while check 3's is common
      and sits *next to* the negation. 🔴 **And the filed premise was wrong in
      both directions**: *"all three substantively attested, 0 real members"* is
      **2 of 3** — `runtime.asm:423` (`int_h_body`) cites no document at all and
      had been exempt on the word `VDP` in ordinary prose for **708** commits —
      and the negation window **does not catch that one**, while flagging the two
      that should stay exempt. The real axis was vocabulary: sweeping `CITATION`
      one alternative at a time shows **22 of 25** exempt nothing, and removing
      `VDP` alone scores **9 of 9** genuine over the same 981 commits. Landed:
      `VDP` dropped, a 2-vector class pin (self-test 12 → **14**), the 4th
      acknowledged entry, and a floor on **all four** self-test tables — because
      an emptied table printed `section self-test 0/0` and exited **0**.
      `map.grauw.nl` was measured and DECLINED: **0** changed verdicts in 981
      commits, and the "swap `oracle` for the URL" repair is byte-for-byte
      identical to the shipped fix at every commit.
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
- [ ] ⚠️ **`lof-acceptance` intermittent oracle drift — two sightings, nothing
      since.** Sighting 3 has not occurred across EIGHT consecutive slices
      (D-PINDATA, D-INJSINK, D-ROMJUDGE, D-DSKJUDGE, D-CITEJUDGE, D-DOCJUDGE,
      D-BYTEJUDGE, D-REVJUDGE — the last at 45 cases, 0 oracle drift, whole log
      captured, 59 lines). A third IS a finding to
      chase; capture the **whole** log (`> file 2>&1`), because sighting 1's row
      identity was lost to a `tail -6`. Detail: line 3678.

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

The per-item done-record for the committed loader-stub target. Kept for the
provenance / divergence trail; nothing here is outstanding.

### Tape — read + write parity with disk
- [x] **`CLOAD` / `LOAD"CAS:"` on-device load** — DONE. The hang was **not** a tape
      framing bug (oracle traces show `TAPIN` frames the `$00` run and `$0000`
      end-link fine at all bauds); it was a **link-word register clobber** in
      [`basic/cload.asm`](basic/cload.asm) `ctp_line`: `TAPIN` returns `C=0` (C is
      its bit-counter), but the old code stashed link-low in `C` across the second
      `TAPIN`, so the link word read as `$XX00` and the body-length math hung the
      loader. Fix = push/pop link-low across the second read (+ a stack-balanced
      error shim); the same latent clobber in the disk `dpl_line` was fixed too.
      `tape/` is unchanged. Verified: `basic_probe_cload_ondevice.py` ALL PASS
      (on `C-BIOS_MSX1_EU_TAPE` + `--cart`), disk LOAD/RUN + the 5 basic regression
      probes ALL PASS.
- [x] **Tape SAVE statements** — DONE. `CSAVE`/`SAVE"CAS:"` (tokenised program) and
      `BSAVE"CAS:",start,end[,exec]` (binary) write to cassette through the
      zerobas-tape **write** signal layer (`TAPOON`/`TAPOUT`/`TAPOOF`) + the cassette
      file format (`$D3`/`$D0` ×10 header block + 6-char name + data block). The disk
      `do_save`/`do_bsave` ([`basic/save.asm`](basic/save.asm)) now device-dispatch
      `"CAS:"` (non-destructive `dev_cas` peek, like the load side) to the new tape
      write path; `CSAVE` got its own oracle-locked token (`$9A`). All loop state
      lives in RAM (`TSV_*`) across every `TAPOUT` (the cassette BIOS clobbers
      everything — same discipline as `disk_putword`). Validated three ways:
      format byte-identical to `build_cas` (cas_decode), the reference VG-8020
      `CLOAD`s our recorded `.cas`, and self round-trips `CSAVE`→`CLOAD` /
      `BSAVE"CAS:"`→`BLOAD"CAS:"` (`basic_probe_tape_save.py` ALL PASS). Divergences:
      tokenised-only `SAVE"CAS:"` (`,A` ASCII → `load_error`, Phase 3); 6-char name
      truncation; bare `CSAVE` writes a 6-space name. This completes tape parity.

### Phase 1.5 — disk interface standardization (standard DSKIO + own FAT)

**Why.** On real MSX the BASIC interpreter and the disk ROM are *not* tied
together — they interoperate through **standardized** interfaces (the slot-scan +
INIT, the `$4010` DSKIO sector-I/O entry table, the `H.*` hooks), so disk
interfaces are interchangeable (plug a floppy cartridge into any MSX; swap disk
ROMs between makers). zerobas copies the *placement* faithfully (cassette in the
BIOS, disk in a slot) but swapped the BASIC↔disk *protocol* for a **private** one:
`zerobas-BASIC`'s disk verbs call zerobas-disk's `bdos_entry` via SYSTEM `$F37D`.
So only the matched pair works — a real/foreign disk ROM does **not** drop in, and
zerobas-disk is not reachable by real BASIC/DOS.

**Approach (research-spike-confirmed, 2026-06-21).** Drive the **standard `$4010`
DSKIO** sector interface and own the FAT12/dir logic loader-side. A spike on the
real **National CF-3300** Disk BASIC proved (black-box) that the drive-letter
loader path is *pure PHYDIO/DSKIO* — `BLOAD"A:"`/`SAVE"A:"` resolve the filename
internally (BPB/FAT/dir) and move bytes via `HPHYD ($FFA7)`→`DSKIO ($4010)`; the
BASIC **DEVICE/expansion mechanism is never called** for drive letters. There is
**no standard "open file by name" entry** to delegate to — a disk ROM's only
interchangeable interface is *sectors*; its filename logic is locked inside its
Disk BASIC. So the basic-side FAT is the **necessary price** of the universal
sector interface, **not** avoidable duplication. (True delegation — hosting the
disk ROM's Disk BASIC extension — is the charter-raising Phase-2 item.) Full pinned
contract: [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md).

- [x] **Host side (`zerobas-BASIC`)** — DONE. The FAT12 read+write engine is ported
      loader-side into [`basic/fat.asm`](basic/fat.asm) (from `disk/disk.asm`, our own
      clean-room code) and driven through the standard **`CALSLT $4010` (DSKIO)** entry
      with the MSX2-TH register convention (A=drive, B=#sec, C=media, DE=sector, HL=buf,
      **CY=read/write**); the slot is the INIT-scan `DISKSLOT` capture, the address the
      fixed `$4010` offset (NOT `bdos_entry`/`$F37D`). The four verbs are rewired:
      `do_disk_bload` ([`basic/bload.asm`](basic/bload.asm)) + `disk_prog_load`
      ([`basic/cload.asm`](basic/cload.asm)) use `fat_io_open`/`fat_io_getbyte`;
      `do_bsave`/`do_save` ([`basic/save.asm`](basic/save.asm)) use `fat_io_create`/
      `fat_io_putbyte`/`fat_io_close`. The private `bdos_entry`/FCB path is retired from
      the loader (dead RAM/BDOS equates removed from sysvars.inc). DSKIO + the on-disk
      BPB suffice (no GETDPB on the host side). **Oracle (both disk ROMs):**
      `BLOAD"A:"`/`LOAD"A:"`/`RUN"A:"`/`SAVE"A:"`/`BSAVE"A:"` ALL PASS under
      zerobas-BASIC with (i) our own `disk.rom` AND (ii) the foreign National
      **CF-3300** disk ROM in slot 3-1 — proving the host side disk-ROM-independent
      (CF-3300 failed every verb on the old `bdos_entry` path). See basic/PROVENANCE.md
      §disk DSKIO host engine. Sources: MSX2 TH / MSX Assembly Page DSKIO contract;
      no disassembly.
- [x] **Provider side (`zerobas-disk`)** — DONE. INIT now installs the standard
      **`HPHYD ($FFA7)`→DSKIO ($4010)** hook via the `RST 30h`/`CALLF` + slot-byte
      idiom (slot byte = A on INIT entry; oracle-confirmed `$87` = slot 3-1), and
      **`GETDPB ($4016)` is real** — it builds the DPB from the on-disk BPB and is
      **field-for-field byte-identical to a black-box CF-3300 GETDPB trace** on the
      720 KB image (`f9 00 02 0f 04 01 02 01 00 02 70 0e 00 ca 02 03 07 00`).
      (`bdos_entry`/FAT/BDOS stay as the internal implementation.) End-to-end
      provider read confirmed: `CALL $FFA7` (the installed hook) crosses into our
      DSKIO and reads the boot sector byte-identically. See disk/PROVENANCE.md
      §INIT + §DPB. The DPB field encoding was the one genuinely-new clean-room item.
- [x] **Oracle — disk-ROM independence, both directions** — committed scope DONE
      (host + Tier-1 provider). The Tier-2 sub-item below is carried to **Phase 2**.
      (a) **DONE (host):**
      `BLOAD"A:"`/`LOAD"A:"`/`RUN"A:"`/`SAVE"A:"`/`BSAVE"A:"` round-trip under
      `zerobas-BASIC` with zerobas-disk **and** with the foreign National CF-3300
      disk ROM in slot 3-1 — ALL PASS on both (machines built via
      `install-openmsx-machine.py --disk-rom <ROM>`; probes `disk_probe_bload_disk.py`
      / `disk_probe_save.py` / `disk_probe_load_disk.py` / `disk_probe_run_disk.py` /
      `disk_probe_load_embedded_nul.py`). (b) **Tier 1 DONE (provider):** an
      **organic real MSX1 BIOS** drives zerobas-disk through the standard hook/DSKIO
      path. On `National_CF-3300_ZEROBASDISK` (real CF-3300 BIOS in slot 0, zerobas-disk
      in slot 3-1; built via `install-openmsx-machine.py --real-bios-disk`), the
      genuine BIOS cold-boot scan calls our INIT → installs `H.PHYD ($FFA7)=F7 87 10
      40 C9`, and a **real BIOS `PHYDIO` ($0144)** call (entry from the MSX Assembly
      Page / MSX2 TH BIOS jump table — no disassembly) routes *through* that hook into
      our DSKIO: sector 0 byte-identical to the on-disk boot sector, `CY=0`, plus a
      CY=1 write+readback round trip. The no-injected-hook property is proven two
      ways — the hook bytes are read back after a clean cold boot *before* any stub
      runs, and a breakpoint on `$FFA7` is *hit* during the BIOS PHYDIO call (the hook
      is load-bearing, not bypassed). Harness:
      `probes/disk/disk_probe_provider_phydio.py` (ALL PASS). The earlier
      injected-hook `CALL $FFA7`, HPHYD-bytes, and CF-3300 GETDPB differential checks
      still stand under it. **Tier 2** — a real *filesystem* host (DOS/Disk-BASIC,
      which alone consumes GETDPB organically) — requires DOS-boot or Disk-BASIC
      hosting = **Phase 2**. See
      [`disk/docs/provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md).

**Outcome.** Both transports now sit on standard interfaces (tape uses the BIOS
cassette entries; disk uses DSKIO/`HPHYD`/`GETDPB`), and disk interoperates both
directions — the point of the whole basic/tape/disk split. The only piece not yet
exercised is the Tier-2 provider oracle, now part of Phase 2.

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
- [x] **Black-box the DEVICE/STATEMENT expansion + file-channel protocol** on the
      real **National CF-3300** Disk BASIC (boots to Disk BASIC; ROMs in
      `~/.openMSX/share/systemroms/`). The Phase-1.5 spike deliberately skipped this:
      it proved the *drive-letter loader* path is pure DSKIO and never touches the
      DEVICE expansion (`PROCNM $FD89` / `DEVICE $FD99` stay zero) — see
      [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md) §0/§5 — but
      the *file verbs* (`OPEN`/`PRINT#`/`INPUT#`/`FILES`/…) are exactly where that
      expansion fires. Observe (clean-room: BP on documented addresses + live register
      read-out; **never read/disassemble the reference ROM**):
        1. **Dispatch** — typing `FILES` / `OPEN"A:F"…`, how control reaches the disk
           ROM's STATEMENT (`$4004`) / DEVICE (`$4006`) handler; the request-code /
           work-area (`PROCNM`, `DEVICE`, file-number) contract.
        2. **File-channel I/O** — `OPEN`→`PRINT#`/`INPUT#`→`CLOSE`: the register-level
           open-by-name, sequential read/write, and close calls; the FCB / channel
           buffer structures; how bytes flow.
- [x] **DONE** — [`disk/docs/file-channel-protocol.md`](disk/docs/file-channel-protocol.md)
      + probe `diskbasic_probe_filechannel.py`. Headline: the **file I/O verbs move
      bytes through the SAME standard DSKIO+FAT12+FCB substrate as the loader path**
      (not a separate channel protocol); they are built-in tokens (STATEMENT/DEVICE
      expansion never fires). Result: **GO, and EXTEND** (layer the verbs on the
      existing `basic/fat.asm` engine; keep `fat.asm`, don't retire it).

### Step 0b — `CALL`-dispatched commands spike — ✅ DONE
- [x] **DONE** — `diskbasic_probe_format.py` on real CF-3300: `CALL FORMAT` writes
      `PROCNM ($FD89) = "FORMAT"` (confirming STATEMENT-expansion dispatch, unlike the
      zero-PROCNM file verbs) and drives `CHOICE ($4019)` (the `Drive name?` + format-
      type menu) → `DSKFMT ($401C)`. EXTEND-vs-DELEGATE for `CALL` commands documented
      (lean EXTEND: a `CALL`/`_` parser + own `CHOICE`/`DSKFMT`); the generic STATEMENT
      dispatcher is an optional follow-on. See file-channel-protocol.md §1a.

### Step 1 — architectural fork: RESOLVED (file verbs = EXTEND)
For the **file I/O verbs** the spike resolves it: **EXTEND** over the existing
`basic/fat.asm` engine; `fat.asm` is kept, not retired. (For `CALL`-dispatched
commands the documented expansion seam exists — fork still open, gated on Step 0b.)

### Step 2 — implement the verb surface (each oracle-validated vs CF-3300)
Full DOS1-class Disk BASIC vocabulary, grouped; **[in]** = recommended Phase-2,
**[?]** = scope to confirm, **[out]** = deferred. Build smallest end-to-end path
first (`FILES`, then `OPEN`+`INPUT#`+`CLOSE`), grow outward.
- [x] **Sequential file I/O [in]** — `OPEN`, `CLOSE`, `PRINT#`, `PRINT# USING`,
      `INPUT#`, `LINE INPUT#`, `INPUT$(n,#f)`. The spike-confirmed core. **DONE** —
      every sub-item below landed + oracle-validated. (`PRINT# USING` file form: a
      format-copy overrun corrupted it until 2026-07-18 — pu_deref_body clobbered the
      A holding the length, so the ldir count became the literal's pointer-low byte;
      fixed by preserving A. CF-3300 byte-validated, `disk_probe_printusing_file.py`.
      Root cause + fix: [docs/spec-print-hash-using.md](docs/spec-print-hash-using.md).)
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
      - [x] **`MAXFILES` + the multi-channel table** — DONE (basic/files.asm channel
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
- [x] **File/dir management [in]** — `FILES`✅, `KILL`✅, `NAME…AS…`✅, `MERGE`✅ — **DONE**
      (the `LOAD`/`SAVE`/`BLOAD`/`BSAVE`/`RUN"f"` already exist from Phase 1). `LFILES`
      is printer-bound (no device in zerobas) — deferred.
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
- [x] **File-position / info functions [in]** — `EOF`✅, `LOF`✅, `DSKF`✅ — **DONE**.
      `LOC`(deferred, unclear semantics), `VARPTR(#n)`(deferred) below.
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
- [x] **Config [in]** — `MAXFILES` (sizes the channel table) — DONE; see the
      sequential-I/O sub-item above + basic/PROVENANCE.md §MAXFILES.
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
- [x] **Random-access files [in → sub-phase 2c]** — `FIELD`✅, `GET`✅, `PUT`✅, `LSET`✅,
      `RSET`✅ + conversion fns `CVI`✅/`MKI$`✅ — **DONE** (sub-phase 2c complete). A
      heavier, self-contained record-file feature; built + oracle-validated as its
      **own sub-phase (2c)**. The float-conversion siblings `CVS`/`CVD`/`MKS$`/`MKD$`
      await Phase-3 floats — deferred.
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
- [x] **`CALL FORMAT`** — DONE (basic/format.asm). Writes a fresh empty 720 KB
      FAT12 filesystem on drive A, no prompts (zerobas-disk has one geometry, so its
      CHOICE offers nothing to ask). zerobas-BASIC lays the boot sector (BPB) + 2 FAT
      copies + empty root dir down ITSELF via the standard $4010 write_sector — not via
      zerobas-disk's DSKFMT stub (the Phase-1.5 "BASIC owns the filesystem" model).
      Geometry is parameterized (a GEOM_720K descriptor table) so 360 KB (CF-3300
      media $FD/720-sec/2-sec-per-FAT) is a clean later add + the CHOICE prompt. CALL
      token $CA; the device name after CALL/`_` is kept verbatim (a new tokeniser
      exception — oracle: `call format` keeps "FORMAT", not FOR+MAT). Structural BPB +
      FAT byte-identical to a CF-3300 "2 sides, double track" format, and a file
      round-trips on the fresh disk (disk_probe_format.py). Boot-code region + OEM are
      zerobas' own (documented divergence — won't copy ROM code; CF-3300 writes no
      $55AA either). See PROVENANCE §CALL FORMAT.
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

- [x] **Feasibility spike — DONE (2026-06-22).** Both prerequisites checked
      empirically (see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md)
      §7). (1) A real DOS1 system disk **exists (permanent)**:
      a local `test.dsk` boots the stock CF-3300 to
      `MSX-DOS version 1.03 … A>` (same image as the recorded BDOS oracle). (2) The
      gap is **pinned**: the *same* disk on the Tier-1 machine
      (`National_CF-3300_ZEROBASDISK`) falls through to **`MSX BASIC version 1.0`**,
      even though `H.PHYD` is installed — zerobas-disk's INIT installs the hook but
      **never reads the boot sector / chainloads the DOS**. Result: **GO**.
- [ ] **2-Tier2-a — DOS boot (steps 4–7).** Deeper than first scoped: a build attempt
      proved the boot is a **four-step environment hand-off** (MSX2 TH ch.3), not a
      one-call bridge — see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.
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
- [ ] **2-Tier2-c — regression.** Host-unit-test the sector-0 read + handoff setup;
      pin the `A>` screen in `disk_probe_provider_dosboot.py`.

**Charter note.** This raises the README's loader-stub charter toward "real MSX
BASIC" on the disk axis. That is the intended scope of Phase 2 — a conscious step
up, kept narrow to the disk/file story so it stays validatable.

### Phase 1 close-out — owed oracles (polish, non-blocking)
- [x] `basic_probe_clear.py` — CLEAR oracle done: the `<memory-top>` write to
      HIMEM (`$FC4A`) is byte-identical to the Philips VG-8020 reference, and all
      four syntax forms (`CLEAR`, `CLEAR n`, `CLEAR ,himem`, `CLEAR n,himem`)
      parse + continue the line. String-heap sysvars stay unmanaged by design
      (no heap in Phase 1). ALL PASS.
- [x] `USR` `DAC`/`VALTYP` calling-convention oracle done (`basic_probe_usr.py`,
      ALL PASS): the reference passes an integer USR argument in `DAC+2..3` (16-bit
      LE at offset 2 of the 8-byte DAC `$F7F6`), sets `VALTYP` (`$F663`) `=$02`, and
      leaves `HL`→DAC base; zerobas passes the argument directly in `HL` and leaves
      DAC/VALTYP untouched — the own-design integer-only divergence is now measured,
      not assumed.

Everything else for the committed target is done; the detailed done-record follows.

## Done — Phase 1 (loader-stub BASIC)

Complete and oracle-validated; kept below as the provenance / divergence record
(each item names where it lives and how it was validated). The typical loader
stub this supports: `CLEAR …,&Hxxxx : SCREEN n : BLOAD"…",R` or
`DEFUSR=&Hxxxx : BLOAD"…",R : A=USR(0)`.

### Statements
- [x] `CLEAR [strings][,himem]` — nearly every stub sets memory top before `BLOAD`
      (basic/clear.asm: full syntax parses; string-space accepted+ignored, himem
      recorded to HIMEM `$FC4A`. Oracle `basic_probe_clear.py` ALL PASS; see Phase-1 close-out above.)
- [x] `DEF USR[n]=addr` + `USR[n](x)` function — the non-`,R` jump into loaded code
      (basic/usr.asm: vectors in USRTAB `$F39A`; crunch byte-identical. USR calling
      convention is own-design integer-only — DAC/VALTYP convention now oracle-measured,
      `basic_probe_usr.py` ALL PASS; see Phase-1 close-out above.)
- [x] `CLOAD ["filename"]` — load a BASIC program from cassette; needed when a stub
      chain-loads a BASIC payload rather than a binary (complement to `BLOAD"CAS:"`)
      (basic/cload.asm: CLOAD=$9B / LOAD=$B5 crunch byte-identical; reads the $D3
      tokenised-BASIC tape image into the stored-program area at TXTBASE, relinks,
      makes it the current program. Optional filename parsed+ignored — own-design,
      no tape file catalogue. On-device functional load WORKS — the earlier
      in-harness hang was a `ctp_line` link-word register clobber (not a tape
      framing bug), now fixed; see the tape-parity section above. Validated by
      `basic_probe_cload_ondevice.py` ALL PASS, plus the reference-load format oracle.)
- [x] `LOAD "CAS:filename"` — MSX-BASIC unified tape-load form; shares cassette I/O
      path with `CLOAD` but uses the `OPEN`-style filename syntax
      (same basic/cload.asm path as CLOAD; LOAD=$B5, "CAS:" device parsed, filename
      ignored. Same zerobas-tape `$00`-run device-half blocker as CLOAD.)
- [x] `PRINT` (+ `;` `,` separators, string literals, `TAB`) — wire up the existing token
      (basic/print.asm: numeric + string-literal items, `;`/`,` zones, `?` abbrev;
      crunch byte-identical, output verified in openMSX. `TAB(`/`SPC(` + string
      vars/`CHR$` still to do — need the Phase-3 string engine.)
- [x] `ON expr GOTO/GOSUB` — `branch_lineno` extended with comma-list loop; `ex_on`/`eon_seek_nth` handler added; all 7 functional probes (A=1..N, N=0 fallthrough, N>count fallthrough) pass
- [x] `SCREEN`, `COLOR`, `CLS`, `KEY OFF`, `WIDTH` — pre-handoff screen setup (thin BIOS/VDP wrappers)
      (basic/screen.asm: thin wrappers over CHGMOD/CHGCLR/CLS/ERAFNK/DSPFNK; new `OFF`
      token $EB added; crunch byte-identical incl. all 7 verbs; 9/9 functional probes
      pass `basic_probe_screen.py`. Divergences: SCREEN's extra args evaluated+ignored;
      COLOR doesn't repaint drawn text; KEY only does OFF/ON, `KEY n,"str"`/`KEY LIST`
      error — all Phase-3 scope.)

### Expressions / variables
- [x] Multi-character variable names — single-letter only is a hard wall
      (basic/vars.asm: 2 significant chars, key store; crunch byte-identical incl.
      digit-in-name; 2-char round-trip verified in openMSX)
- [x] `/`, `\`, `MOD`, and `AND`/`OR`/`NOT`/`XOR` — address / poke math
      (basic/expr.asm: full precedence ladder; crunch byte-identical, all ops verified
      in openMSX. `/` is integer + division is unsigned — documented divergences from
      MSX signed/float arithmetic; div-by-zero → 0. `^` still deferred to Phase 3.)
- [x] `&O` / `&B` literals — `&O` octal now emitted + evaluated; `&B` descoped
      (basic/interp.asm: `tk_hex` generalised to dispatch `&H`/`&O` on a radix
      (16/8) + token ($0C/$0B) pair; `&O` crunches byte-identical to the VG-8020
      as `$0B,<value16 LE>`, full `0..&HFFFF`; `ev_f` decodes `$0B` like `$0C`;
      `detok` already rendered `&O`. Oracle showed the reference has NO `&B`
      binary token — it copies `&B…` verbatim as ASCII — so `&B` is a documented
      own-design descope (kept verbatim, byte-identical to the reference; marked
      quarantined in basic/PROVENANCE.md), not a fabricated token. Validated:
      crunch + 4 control-flow/loops/data/statements regressions ALL PASS;
      functional `&o17`→15, `&o12`→10, `&o400`→256, `&o177777`→65535 in openMSX.)
- [x] `VARPTR`, `VPOKE`/`VPEEK`/`BASE`, `INP`/`OUT` — common in pokes
      (basic/vdpio.asm: VPOKE/OUT statement handlers; basic/expr.asm: VPEEK/INP/
      VARPTR/BASE function factors. Tokens oracle-confirmed byte-identical via
      basic_probe_crunch.py: VPOKE=$C6, OUT=$9C, VPEEK=$FF$98, INP=$FF$90,
      VARPTR=$E7, BASE=$C9 (cross-checks MSX2 TH Table 2.20). VPOKE/VPEEK use
      WRTVRM $004D / RDVRM $004A; OUT/INP do raw Z80 `out (c),a` / `in a,(c)`.
      detok renders all six (table-driven, no new render code). Functional
      `basic_probe_vdpio.py` 6/6 PASS. Divergences: VARPTR returns zerobas's OWN
      variable-table value-cell address (its table layout is its own design, not
      the reference's variable-area map) — valid+writable, sufficient for loader
      pokes; BASE is descoped — argument parsed+evaluated but BASE(n) returns 0
      and sets ERRMARK (reproducing the reference's per-mode VDP table-base map
      would need a forbidden source). Both quarantined in basic/PROVENANCE.md.)
- [x] String literals / variables *enough for `PRINT`* (full string engine is Phase 3)
      (basic/strvar.asm + basic/vars.asm: a `$`-suffixed name is a string variable
      with its own minimal inline store [name0][name1][len][bytes:STRMAX=32]; LET
      assigns a `"literal"` or copies another string var (A$=B$); PRINT emits a
      string var's value, incl. alongside literals (PRINT "X=";A$). Oracle-confirmed
      `$` is part of the name — NO special string token; crunch already byte-identical
      (`a$="hi"` → `41 24 EF 22 68 69 22`). Own-design VALTYP/STRPTR value-type notion.
      6/6 functional probes pass basic_probe_strvar.py. NOT built (Phase 3): concat `+`,
      string functions (LEN/MID$/CHR$/…), string arrays/DIM, string DATA — all descoped.)

### Usability
- [x] `LIST` — display the stored program, de-tokenised
      (basic/list.asm: `ex_list` walks the line-link chain; `detok` is the reverse
      of the tokeniser — keyword (`detok_kw`/`detok_kw2`), operator, int/`&H`/`&O`,
      line-ref, string/REM/DATA verbatim, `:`ELSE / `'` folds. No new token; reuses
      `div10`/CHPUT. 8/8 functional probes pass `basic_probe_list.py` (VRAM screen
      decode); crunch + all regression probes still pass.)
- [x] ✅ **`LIST <range>` — LANDED 2026-08-02, D-LSTRNG.** `LIST n`, `LIST n-m`,
      `LIST n-`, `LIST -m` all implemented; the argument is no longer ignored.
      Spec [`docs/spec-basic-listrange.md`](docs/spec-basic-listrange.md),
      measurement
      [`docs/listrange-msx1-characterization.md`](docs/listrange-msx1-characterization.md).
      🔴 **`DELETE`'s RANGE RULES DO NOT TRANSFER, AND FIVE OF THE TWENTY MEASURED
      SHAPES WOULD HAVE BEEN WRONG IF THEY HAD BEEN ASSUMED TO.** D-DELETE
      measured, one week earlier with the same grammar and the same instrument,
      that the high end must name a stored line exactly, that a reversed range is
      ERR 5, and that an absent number is 0 on either end. LIST has **none** of
      those: `LIST 20-35` lists two lines, `LIST 30-20` lists nothing with ERR 0,
      and — sharpest — **an absent HIGH end is 65535**, so `LIST 20-` lists to the
      end of the program where `DELETE 20-` means `20-0` and raises.
      🔴 **A LATENT BUG THE FOURTH `LE_OP` EXPOSED**: the lineedit tenant selector
      read `dec a / jp nz,le_delrange` — *"anything that is not 1 is a delrange"* —
      so adding `LE_OP_LSTRANGE` would have routed `LIST` into `le_delrange` and
      **deleted the lines it was asked to print**. Now an explicit ladder.
      🔴 **`list_walk` HAS THREE CALLERS**: `ascii_save` and `cas_ascii_save` drive
      the same walk, so a `LIST` range had to be stopped from leaking into
      `SAVE",A"` (a `list_all` entry does it). Knife K6a proved a one-line
      regression there passes the dead-code gate AND the whole 34-row battery —
      the new `list 20` in `disk_probe_save_ascii.py` is the only thing that sees
      it. Cost 68 B of main page 1 (82 → **14 B free**); a fully resident design
      was measured at ~128 B and never fit. `.` excepted — its own item below.
- [x] `CONT`, Ctrl-STOP / break handling
      (basic/program.asm: the RUN loop polls BIOS `BREAKX` ($00B7) between
      statements/lines and on every FOR/NEXT iteration; a press branches to
      `do_break`, which saves the resume state and prints `break in <line>`. The
      `STOP` statement (`ex_stop`) records resume = the statement after STOP, then
      `do_break`; `CONT` (`ex_cont`) restores `CURLINE`/`RESUMEPTR` and re-enters
      the run loop via the existing `RESUMEFLAG` mid-line resume path. `CONTVALID`
      is cleared at RUN entry, on `store_line` (edit), and on `NEW`, so CONT after
      a clean/STOP-less completion or an edit gives `can't continue` (ERRMARK $C9).
      CONT token oracle-confirmed byte-identical via basic_probe_crunch.py
      (`cont`→$99, cross-checks MSX2 TH Table 2.20); BREAKX oracle-confirmed on
      C-BIOS_MSX1 (bios_probe_breakx.py — CF clear when not pressed, so no
      false-breaks). Functional `basic_probe_cont.py` 7/7 PASS on C-BIOS_MSX1:
      STOP halts, STOP→CONT resumes incl. across a line boundary, all three
      can't-continue cases, and a real Ctrl-STOP keyboard-matrix press breaking an
      infinite loop back to the REPL. Divergences: the resume-state RAM layout
      (CONTLINE/CONTPTR/CONTVALID) and lowercase `break in`/`can't continue`
      wording are own-design — zerobas's run loop is its own design, not the
      reference's CONTXT/OLDLIN sysvars — both quarantined in basic/PROVENANCE.md.)

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

- [x] **Floating point** — **ARC CONCLUDED** (F1+F2+F3 all landed on main;
      `%`/`!`/`#` typed vars + `DEFINT/DEFSNG/DEFDBL/DEFSTR` shipped, commits
      a1e77d3/2a7c1ce). Standing gate `make float-acceptance`.
      ([`docs/spec-basic-float-core.md`](docs/spec-basic-float-core.md), signed off
      2026-07-11): three slices, F1 literals+PRINT → F2 arithmetic+relationals+
      signed-int migration → F3 typed variables (`%`/`!`/`#`, unsuffixed=double).
      **F1 DONE 2026-07-11** (S1–S3, commits 223da0f/506381c/…): decimal float
      literals crunch to the real `$1D` (single, 4 B) / `$1F` (double, 8 B) BCD
      tokens byte-identically vs the VG-8020 — **decimal ≥ 32768 finally correct**
      (the old `$1C` wrap divergence retired) — and PRINT renders them
      reference-identically (fixed vs `E±nn` at dec_exp ∈ [-1,14]; `E` for BOTH
      precisions on this MSX1 reference). Oracle-pinned quirks reproduced: half-up
      rounding with the single-precision NON-renormalising carry (`9999995!` →
      1000000), suffix-after-exponent left unconsumed, `1e-65` underflow-to-zero
      with mantissa retained, crunch-time `overflow` rejection (own lowercase
      wording, D-F1-1). New `basic/float.asm` + repack-gated hooks; RAM `$F01A+`;
      lean `basic.rom` byte-identical. Interim seams (documented, F2/F3 resolve):
      no float arithmetic (`flt_guard` → ERRMARK, D-F1-3); a float in an int
      context rounds half-up into the −32768..65535 ADDRESS domain, outside → 0
      silently (D-F1-2 — the range widened in F1 review after `POKE 40000,n` /
      `HEX$(65535)` regressed under a strict-int16 cap); `LET` stores the rounded
      int. Standing gate **`make float-acceptance`** (LITERALS + FORMAT halves,
      60+ cases each) + host `tests/test_float.py`; spec §9 holds the full pinned
      contract; provenance `basic/PROVENANCE.md` → "Phase 3: math float pack, F1".
      Window after F1: 1844 B page-0 + 160 B tail ≈ 2.0 KB for F2+F3 (tight; next
      repack tranche is the fallback). Still out of scope (arc §1):
      `DEFINT/DEFSNG/DEFDBL/DEFSTR`, `^` + math functions, float
      `VAL`/`STR$`/`INPUT`/`FOR`, `MKS$/MKD$/CVS/CVD`, float `PRINT USING`.
      **F2 DONE 2026-07-11** (S2+S3, commits 781348f/dee70a9): `+ - * /`, the six
      relationals, promotion, and the **D-C signed-int migration** (`/` real
      division always; `\`/`MOD` MSX-signed; div-by-zero + Overflow are real
      statement aborts, lowercase wording D-F2-1) — **reference-identical,
      167/167** differential cases (spec §10 holds the full pinned contract).
      Headline oracle findings: ALL float arithmetic is DOUBLE (single =
      storage-only); guard-digit half-up rounding; PRE-normalisation
      overflow walls; float→int conversion TRUNCATES in two exclusive-bounds
      domains (F1's half-up `flt_to_int16` corrected); `-32768\-1` → +32768
      promoted; IF truthiness float-aware (§10.4a). New `basic/float-arith.asm`
      (unpacked-BCD 14+guard core) + FPERR abort wiring; the ARITH half joined
      `make float-acceptance`. Unblocking the window took the **D5 revision**
      (tape body `$3A72`→`$09EE`, all-variant gap-1 fill — flagged for user
      review; full tape battery re-run green). Interim seams: `LET` of a float
      TRUNCATES to int16 (F3 resolves); D-F2-2 = `OUT` + unwired int-arg
      statements/functions (e.g. `PEEK(100000.)`) still on the silent eager
      conversion. **Window now FULL** (2 B page-0 + 29 B tail); F3 needs a
      space lever — see the spec's D-G addendum (multi-region image / next
      repack tranche / heap-first).
      **F3 DONE (arc CONCLUDED)** — typed numeric variables (variable-width store,
      `%`/`!`/`#` suffixes, commit a1e77d3) and `DEFINT/DEFSNG/DEFDBL/DEFSTR`
      per-letter default types (`deftbl_lookup`, commit 2a7c1ce); `LET` of a float
      now stores at the variable's declared type (the F2 int16-truncate seam
      resolved). The `^`/math-functions and D-F2-2 int-arg items in the two lines
      above **also shipped** — see their own checkboxes below. Still genuinely
      deferred: float `MKS$/MKD$/CVS/CVD`, float-only `PRINT USING` specs. Spec §11
      (typed vars); provenance `basic/PROVENANCE.md` → "Phase 3: … F3".
- [x] **Full string engine** — **ARC CONCLUDED** (every string SURFACE form landed;
      standing gate `make string-acceptance`). **core + comparison landed 2026-07-10** (the first Phase-3
      feature and its follow-on): `+` concat + `LEN ASC VAL CHR$ STR$ LEFT$ RIGHT$ MID$`,
      then the six **relational operators** on strings (`=`/`<>`/`<`/`>`/`<=`/`>=` →
      -1/0, with a statement-level `type mismatch` abort) — all in the repack build
      (own-design temp ring + STRMAX clamp, no heap/GC; integer-only VAL). Specs
      [`docs/spec-basic-string-engine.md`](docs/spec-basic-string-engine.md) +
      [`docs/spec-basic-string-compare.md`](docs/spec-basic-string-compare.md), provenance
      [`basic/PROVENANCE.md`](basic/PROVENANCE.md) → "Phase 3: string engine" / "string
      comparison", gate `make string-acceptance` (crunch + execute + compare). **String
      functions slice DONE 2026-07-10** (S1–S3, commits d96dc67/6c46d2b/…): `INSTR HEX$ OCT$
      STRING$ SPACE$` — three integration shapes ($FF-prefixed HEX$/OCT$/SPACE$; single-byte
      STRING$ $E3 / INSTR $E5); spec [`docs/spec-basic-string-functions.md`](docs/spec-basic-string-functions.md),
      provenance `basic/PROVENANCE.md` → "Phase 3: string functions"; `string-acceptance` gained
      a fourth **functions** half (the execute+oracle gate caught two bugs the unit tests
      missed). **INKEY$ slice DONE 2026-07-10** (S1–S3, commits ee65487/dcac69d/…): the first
      keyboard-reading string verb — non-blocking single sample (empty / 1-char) via published
      BIOS `CHSNS`+`CHGET`; single-byte token `$EC`; temp-ring result; spec
      [`docs/spec-basic-inkey.md`](docs/spec-basic-inkey.md), provenance `basic/PROVENANCE.md` →
      "Phase 3: INKEY$"; `string-acceptance` gained a fifth **inkey** half (the first
      keyboard-injection acceptance; the live gate caught a `PRINT INKEY$`→type-mismatch
      `exp_loop` gap). **MID$-statement slice DONE 2026-07-10** (S1–S3, commits 6d88037/c915595/…):
      the assignment form `MID$(A$,n[,m])=B$` — overwrite a substring of A$ in place (`LEN(A$)`
      invariant, truncate-to-fit); zerobas's first lvalue-into-string-var path + first
      `$FF`-token-starting-a-statement; spec [`docs/spec-basic-mid-statement.md`](docs/spec-basic-mid-statement.md),
      provenance `basic/PROVENANCE.md` → "Phase 3: MID$ statement"; `string-acceptance` gained a
      sixth **mid-stmt** half + a host unit-test (`tests/test_mid_stmt.py`). Range errors →
      `syntax error` (no "Illegal function call", documented D-3 divergence). **Unparenthesized
      `PRINT A$<5` slice DONE 2026-07-11** (S1–S3, commits c3b626e/3c2137a/…): the bare comparison
      as a top-level PRINT item now works across all three string leads (var/literal/function +
      concat) — `exp_loop`'s peek-then-reparse dispatch (`relop_peek` + the `exp_strvar`/
      `exp_maybe_strfn` gates); `PRINT A$<5` aborts with `type mismatch`, printing nothing; spec
      [`docs/spec-basic-print-unparen-compare.md`](docs/spec-basic-print-unparen-compare.md),
      provenance → "Phase 3: string comparison" PRINT-lead subsection. **Console INPUT / LINE INPUT
      slice DONE 2026-07-11** (S1–S3, commits 50c231f/d362551/…): the keyboard forms
      `INPUT ["prompt"{;|,}] var[,var…]` and `LINE INPUT ["prompt";] A$` — fills the console stub
      the file `INPUT#`/`LINE INPUT#` forms left (`jp nz,stmt_error ; console INPUT = Phase 3`); the
      biggest missing interactivity primitive. Almost entirely composition — re-points the shipped
      `read_into_strscr` splitter at a new `linebuf_getbyte` source (shares the file forms' field
      split / STRMAX clamp / STRSCR); only new code is that vector, the strict `input_num_field`
      int16 validator, the prompt/var-list driver, and the D-2 re-prompt loop. Own lowercase
      `?redo from start` / `?extra ignored` (D-2 divergence). New `basic/input.asm`; standalone gate
      `make input-acceptance` (8 cases, keyboard-driven, reference-lock + zerobas==reference) + host
      `tests/test_input.py` (29 cases); spec [`docs/spec-basic-input.md`](docs/spec-basic-input.md),
      provenance `basic/PROVENANCE.md` → "Phase 3: console INPUT / LINE INPUT". Harness fix in
      `omsx_run.py` (`type --` so a negative-number response types verbatim). **Deferred items
      since RESOLVED by the arrays arc** (2026-07-17, see the Arrays + `DIM` entry below): the
      **real heap + descriptor model** (slice-4a compacting string heap), **string arrays/`DIM`**
      (slice 3), and **STRMAX→255** (slice-4a) all landed. **Still genuinely deferred:** floats in
      `VAL`/`STR$`, `INPUT$(n)` (no-echo n-key keyboard function), numeric `INPUT#` (out of MSX1
      charter) — tracked under the **I/O** item below.
- [x] **Arrays + `DIM`** (numeric and string, multi-dimensional) — **ARC CONCLUDED 2026-07-17** (all slices 1–4c shipped; faithful unified variable area). **slice 1 DONE
      2026-07-15** (numeric arrays: `DIM`, multi-dim, subscript rvalue/lvalue, auto-
      dim-to-10, base 0, `Subscript out of range`/`Illegal function call`/`Redimensioned
      array`/`Out of memory`). Dynamic-allocator model (real MSX `ARYTAB`→ceiling
      bounded by HIMEM); the array engine is a **sub-ROM page-0 tenant** (the first
      non-leaf feature to be split glue-in-main + pure-RAM-leaf-tenant — see
      [`docs/subrom-tenant-playbook.md`](docs/subrom-tenant-playbook.md)). Gate `make
      array-acceptance` (23 cases + adversarial regression); spec
      [`docs/spec-basic-arrays.md`](docs/spec-basic-arrays.md). `OPTION BASE` dropped
      (unsupported on MSX1). **Slice 2 = `ERASE` DONE 2026-07-15** (`ERASE
      A[,B%...]`; frees arrays → revert-to-undeclared + clean re-`DIM`; two-tier
      error surface — `syntax error` for malformed/paren forms, `Illegal function
      call` for an undeclared name; type-scoped; tenant `op=ERASE` compacts the
      descriptor list). Gate now `array-acceptance` **52 cases**; spec
      [`docs/spec-basic-arrays-slice2-erase.md`](docs/spec-basic-arrays-slice2-erase.md).
      Adversarial review caught F1 (`ERASE A$` freed the numeric `A` — `$` key
      collides with default-double at type 8; fixed via `var_str_type`→type-1).
      **Slice 3 = string arrays DONE**, **slice 4a = string HEAP (compacting,
      STRMAX→255) DONE 2026-07-17**, **slice 4b = numeric SCALAR relocation
      DONE 2026-07-17** (repack build only: numeric scalars move out of the
      fixed `VARTAB $E1C0..$E240` pool into the real-MSX contiguous chain
      `program text → scalars → arrays → free → string heap`, sharing arrays'
      own insert-and-shift/`FRETOP` collision/GC-once-retry mechanism; new
      `ARYTAB` live cell; fold into the `SUBROM_IDX_ARY` tenant as new
      `ARY_OP` codes 4/5 — no new sub-ROM leaf. `make array-acceptance`
      **127/127**; net **+64 B** main-ROM delta freed; lean build untouched.
      Spec [`docs/spec-basic-arrays-slice4b-scalar-reloc.md`](docs/spec-basic-arrays-slice4b-scalar-reloc.md)).
      **Slice 4c = string-SCALAR unification DONE 2026-07-17** (commits
      6d60540 impl → eeb9a8a Makefile SUB_PARTS fix → ea26bca gate/doc):
      string scalars relocated out of the fixed `STRTAB $E240..$E268` pool into
      the SAME unified variable chain — string find/alloc IS numeric find/alloc
      with type=1 once `scv_find`/`scv_alloc` stride routes through the slice-3
      `elsize_from_type` (type 1 → 3-byte `[len][ptr]` descriptor); GC root walk
      `sg_walk_strtab` → `sg_walk_scalars` (visit type==1 at descriptor entry+3);
      `str_get_key`/`str_set_key` → thin ARY_OP 4/5 glue; edit now clears ALL
      vars (resolves the 4b interim caveat). H1 hazard (fresh string STORE shifts
      arrays → stale SOURCE descriptor, `A$=S$(0)`) fixed via a temp-descriptor-
      stack source snapshot. `make array-acceptance` **138/138**; lean byte-
      identical; 9 B low / 19 B page-1 free. Spec
      [`docs/spec-basic-arrays-slice4c-string-scalar-unification.md`](docs/spec-basic-arrays-slice4c-string-scalar-unification.md).
      **🏁 The arrays/DIM arc is CONCLUDED — the faithful unified variable area is
      reached; no fixed variable pool remains.** Two follow-ups **SHIPPED
      2026-07-17** (commit d92c3da, +75fbe2b docs; Fable-reviewed clean):
      `VARPTR(A$)` now returns the string `[len][ptr]` descriptor (was a phantom
      numeric cell — `ev_f_varptr` passes type 1 for a `$` var); INPUT/LINE
      INPUT/INPUT# now surface the scalar-chain OOM as `Out of memory` (was a
      silent `""`; reused `check_expr_errors`/`_popbc`). Gate `array-acceptance`
      **140/140** + `input-acceptance` 16/16. **Array-element VARPTR SHIPPED
      2026-07-18** (spec [`docs/spec-basic-varptr-array-element.md`](docs/spec-basic-varptr-array-element.md)):
      `VARPTR(A(i))`/`VARPTR(S$(i))` now resolve the element address (was
      "syntax error") by reusing `ary_op0_resolve` (op=0 RESOLVE, auto-dim on
      read — the same resolver `ev_f_arr` uses) in `ev_f_varptr` when a `(`
      follows the name; numeric value-field / string `[len][ptr]` descriptor
      address, deferred `Subscript out of range`/`Illegal function call`/
      `syntax error` for bad subscripts — all reference-identical (VG-8020
      black-box-characterised). Repack-only; **self-funded** (the array branch's
      +23 B net against the old block was offset by collapsing `vptr_none`'s
      duplicated `)`-tail repack-only → net **+5 B** page-1, lean byte-frozen).
      Fable review clean (ship; 6 design claims + ~30-case injection battery);
      one byte-neutral follow-up (malformed-`)` VARPTR now surfaces the checked
      deferred syntax error, not a silent 0). Gate `array-acceptance` **150/150**.
      **`INPUT#` mid-statement FP-error ordering SHIPPED 2026-07-18** (the arc's
      last remaining faithfulness candidate): a mid-statement FP error in the
      channel-number expression (e.g. `INPUT#1+0*(1/0),B$`) now aborts BEFORE
      the field is read, matching the reference's abort-before-read ordering
      (was: swallowed until the post-read `check_expr_errors`, so the field got
      consumed anyway). Fix = a new `check_fperr_only` fall-in entry point in
      `check_expr_errors` (`basic/interp.asm`) — FPERR-only, not the full
      TMISMATCH+FPERR check, since a TMISMATCH channel expr already hard-zeroes
      to channel 0 and derails through `fch_valid` to `load error` (that
      pre-existing ordering is untouched); one 3-byte `call` site in
      `basic/files.asm`'s `ex_input`/`ex_line` shared channel-eval path
      (page-1 had only 3 B free, so a 3-byte call reusing the shared checker
      was required over a 7-byte inline check). Verified non-vacuous by hand
      (pre-fix: `B$` got the file's line despite the error; post-fix: `B$`
      stays empty) — this fix governs **ordering within the statement** (abort
      before vs after the field read), orthogonal to whether the RUN then
      continues. *(Wording corrected 2026-07-18, error-handling arc: an earlier
      version of this note claimed div-by-zero/Overflow are "non-fatal, the RUN
      continues to the next statement" — that was a MISREAD of zerobas's own
      pre-D-1 continue-bug as reference behaviour. Div-by-zero and Overflow are
      **fatal** on the reference (statement abort + RUN abort → `Ok`, matching
      the F2 entry above); the whole-RUN abort is fixed separately by the
      error-handling arc's S1 D-1. This ordering fix stays correct and
      non-vacuous after D-1: it decides whether the field was consumed before
      the abort.)*
      Gates green: `unit-test` 46/46, `input-acceptance` 16/16,
      `diskbasic-acceptance` 34/34 (`INPUT#` converged), `array-acceptance`
      150/150; lean `basic.rom` byte-identical (still pinned `e21f61fe…`).
      **Two adjacent channel-eval FP-error gaps SHIPPED 2026-07-18** (error-
      handling arc, spec §5.7): (gap 1) `INPUT#99999*99999,B$` — an out-of-int-
      range channel number now raises **Overflow** (`overflow in N`) instead of
      derailing to `load error`; (gap 2) `PRINT#1+0*(1/0),"X"` — the PRINT#
      channel `eval` now surfaces a deferred **Division-by-zero** (`division by
      zero in N`), the missing sibling of the INPUT# check above. Both fold into
      one shared low-region helper `eval_chan` (`basic/float-arith.asm`) = `eval`
      + numeric-channel `fac_to_int_addr` int-coercion + `check_fperr_only`, used
      by INPUT#/LINE INPUT# (`files.asm`) and PRINT# (`print.asm`); a TMISMATCH
      channel (`INPUT#A$`) skips the coercion and still derails to `load error`
      (verified unchanged). Folding INPUT#'s `eval`+`check_fperr_only` into one
      call **freed** page-1 (net 2→5 B free; low 20→3 B). This is the *targeted*
      channel-eval coercion; the broad D-F2-2 general float→int coercion stays a
      separate future item. Gates all green (unit/input/error/string/float/math/
      array-150/diskbasic-34-lean+repack); lean byte-identical.
      **SCOPED 2026-07-19 → [docs/spec-basic-df2-2-intarg-coercion.md] (DRAFT,
      awaiting sign-off).** Surface empirically pinned: ~8 divergent arg-sites in
      two groups — Group A (address domain: OUT/PEEK/INP, the fac_to_int_addr
      template already proven by POKE/VPOKE) and Group B (byte domain 0..255 via a
      shared get_byte_arg: STRING$×2/SPACE$/ON n/WIDTH). Already-faithful: POKE/
      VPOKE/HEX$/PRINT/DIM/subscript/TAB/SPC. Blocked by page-1 0 B free (funder =
      golf then format.asm eviction). Key open question Q1 = PEEK/INP FPERR
      propagation through a deferred boundary check.
- [x] **`^`** and the math functions
      `ABS SGN INT SQR SIN COS TAN ATN LOG EXP RND FIX CINT CSNG CDBL` — **MATH PACK
      ARC CONCLUDED.** `^`/`SIN`/`COS`/`TAN`/`ATN`/`LOG`/`EXP`/`RND` shipped as the
      transcendentals slice (documented-deviation framework, spec §13.1/§14.1/§15;
      page-1 sub-ROM tenant); `ABS`/`SGN`/`INT`/`SQR`/`FIX`/`CINT`/`CSNG`/`CDBL`
      shipped with the float pack. Standing gate `make math-acceptance`. Specs
      [`docs/spec-basic-math-pack.md`](docs/spec-basic-math-pack.md) +
      [`docs/spec-basic-mathpack-slice2.md`](docs/spec-basic-mathpack-slice2.md).
- [~] **I/O** — mostly shipped. ✅ console `INPUT` + `LINE INPUT` (DONE 2026-07-11,
      see the slice log above); ✅ `PRINT USING`; ✅ `GET`/`PUT`/`EOF`/`LOF` file I/O
      (Phase 2, random-access + sequential); ✅ `INPUT$(n,#f)` channel form; ✅ full
      tape verbs. **Still open:** `INPUT$(n)` (no-echo n-key *keyboard* function),
      numeric `INPUT#` (out of MSX1 charter), `LOC(#n)` (deferred — unclear CF-3300
      semantics, see Phase 2 §File-position).
- [~] **Graphics** (TMS9918, SCREEN 2) — arc live since 2026-07-21, spec
      [`docs/spec-basic-graphics.md`](docs/spec-basic-graphics.md) + per-slice addenda.
      ✅ G1 VDP floor · ✅ G2 `PSET`/`PRESET`/`POINT` · ✅ G3 `LINE` (+`,B`/`,BF`) ·
      ✅ G4 `CIRCLE` (aspect ellipse, arcs, spokes) · ✅ G5 `PAINT` ·
      ✅ **G6 `DRAW`** (2026-07-22, [`docs/spec-basic-graphics-g6.md`](docs/spec-basic-graphics-g6.md)):
      the full MML surface (`U D L R E F G H`, abs/rel `M`, `B`/`N`, `C`/`S`/`A`,
      `X <expr$>;`, `=<expr>;`), the measured scale arithmetic and its wraps, the
      angle's relative-only rotation, the S/A state that survives `RUN`, and the
      shared-`ATRBYT` colour rule (which also retro-fits `PSET`/`LINE`/`CIRCLE`/`PAINT`).
      Gate: `make graphics-acceptance` Phases K/L/M. ·
      ✅ **G7 sprites** (2026-07-22, [`docs/spec-basic-graphics-g7.md`](docs/spec-basic-graphics-g7.md)):
      `SPRITE$(n)=` and `A$=SPRITE$(n)` (8/32-byte entries, pad/truncate, the
      `& $3FFF` index wrap), `PUT SPRITE` (the `y,x,pattern,colour` entry, the
      early-clock rule for a negative x, coordinates stored mod 256, the ×4
      pattern scaling in 16×16, and "an omitted argument keeps the byte already
      there"), `SPRITE ON|OFF|STOP` as accepted no-ops, and **`SCREEN`'s
      sprite-size argument**, which used to be evaluated and discarded — including
      the mode-set init and the size's persistence across a later bare `SCREEN`.
      Gate: Phases N/O/P. Funded by the two-carve eviction
      [`docs/spec-eviction-g7-space.md`](docs/spec-eviction-g7-space.md).
      ✅ **G8 `VDP(n)` / `BASE(n)`** (2026-07-22, [`docs/spec-basic-graphics-g8.md`](docs/spec-basic-graphics-g8.md)):
      the VDP-register pseudo-array read AND write (`VDP(0..7)` = the RAM
      mirrors, `VDP(8)` = STATFL, the write reaching the chip), plus `BASE(n)=`
      with its per-slot value grain — **including the reference's SCREEN-1/2
      off-by-one**, where a BASE write reprograms R0..R6 from the NEXT group's
      table (signed-off D8-1, poison-tested). Also **retires the descoped
      `BASE(n)` stub**: our runtime's `$F3B3` table matches the reference byte
      for byte, so the read is an honest word fetch and a documented divergence
      goes away. Gate: Phase Q (state / grammar / the JIFFY-freeze teeth check).
      Funded from inside the arc — `circ_draw`'s spokes and `elg_draw`'s
      work-area writes folded into the tenant (~144 B), no outside eviction.
      **Still open:** `SCREEN 3` (multicolor, deferred) and the sprite COLLISION
      trap (`ON SPRITE GOSUB`), which belongs to the interrupt-trap item.
      **Residual found in passing (NOT graphics), since FIXED:** malformed
      statements raised a non-trappable abort instead of the reference's
      trappable ERR 2 — see the trap-class entry under Error handling below.
- [x] **Sound** (AY-3-8910) — `SOUND`✅, `PLAY` (MML)✅, `BEEP`✅ — **ARC CONCLUDED
      2026-07-21** (all repack-only, page-1 resident, direct-PSG, VG-8020-byte-faithful).
      `SOUND`/`PLAY`+live servicer landed earlier that day (commits baf…→f6bfe76); the
      **`BEEP` close-out slice** (spec [`docs/spec-basic-audio-beep.md`](docs/spec-basic-audio-beep.md))
      lands the last verb: single-byte token `$C0`, no args, one short tone-A blip
      (period 85, fixed vol 7, ~2-frame delay, then silence + mixer wiped to default
      `$b8`). Direct-PSG not `CALL $00C0` (C-BIOS's `$00C0` is silent on our runtime).
      Restore mixer is RECONSTRUCTED from the read-back I/O bits (`(read & $C0)|$38`),
      since R7's low 6 bits don't read back — same limitation SOUND's R7 path has;
      BEEP wipes a prior `SOUND 7` value and zeroes R8. Gates: `make beep-acceptance`
      (PSG-trace differential, 4 cases), `tests/test_beep.py` (host), crunch corpus.
      Adversarial pass caught a `beep_delay`-clobbers-`C` bug the differential was
      blind to (spec §5.2). Lean byte-identical; page-1 landmine (a downstream `jr`
      out of range) fixed with a ROM_BASE-conditional `jp` in `interp.asm`.
- [x] **Input devices** — the four device readers DONE 2026-07-23 (I1 + I2); the
      `KEY(n)` / `STRIG(n) ON/OFF/STOP` interrupt-trap surfaces stay with the item
      below. Spec [`docs/spec-basic-input-devices.md`](docs/spec-basic-input-devices.md).
      ✅ **I1 `STICK(n)` / `STRIG(n)`** (2026-07-23, commit b8a6a5b): the
      eight-way direction reader (0 = centred, 1..8 clockwise, an opposing pair
      cancelling to 0) and the 0/−1 trigger, as thin wrappers over the published
      BIOS entries `GTSTCK` `$00D5` / `GTTRIG` `$00D8` — which C-BIOS implements
      for real, keyboard row-8 scan *and* PSG joystick-port path, verified to
      match the VG-8020. Two-byte `$FF`-prefixed function tokens (`$FF $A2` /
      `$FF $A3`) on the existing `ev_f_ff` dispatch, so no statement token. The
      argument rule is truncate-toward-zero → int16 (`ERR 6` outside) then the
      device-domain check (`ERR 5` outside), reusing the D-F2-2 `get_byte_arg`
      machinery. Gate `make input-devices-acceptance` (31 cases) — whose
      load-bearing phase drives openMSX's `keymatrixdown`, since the REPL
      driver's KEYBUF injection bypasses the very matrix these functions scan
      and every other phase would pass equally well against a stubbed 0. That
      required a reusable harness addition (`omsx_repl` per-case matrix holds)
      the interrupt-trap arc will want for `ON KEY`/`ON STRIG`.
      Funded by an `ev_f_ff` dispatch golf (`cpir` set test, repack-only so the
      lean ROM stays byte-frozen) plus evicting **`BEEP`** to a page-0 sub-ROM
      tenant — chosen over two larger clean carves that are PLAY-servicer halves
      running from `H.TIMI`, since a `CALSLT` in the VBLANK handler is not worth
      50 B. Page-1 free 6 B → 17 B. **Residual fixed in passing:** a missing
      argument list (`PRINT PEEK`, `PEEK 100`, and the same for
      `VPEEK`/`INP`/`EOF`/`LOF`) evaluated silently to 0 where the reference
      raises `ERR 2` — a pre-existing divergence across the whole `ev_ff_arg`
      family, now deferred through `ev_f_empty`.
      ✅ **I2 `PDL(n)` / `PAD(n)`** (2026-07-23): real `GTPDL` `$00DE` (paddle)
      and `GTPAD` `$00DB` (touch panel) in the **zerobas-tape page-0 patch**
      (decision D-I-6 — C-BIOS shipped both as debug-*printing* stubs), plus two
      thin `ev_f_ff` wrappers (`$FF $A4` / `$FF $A5`; `PDL` 1..12, `PAD` 0..7).
      GTPDL times the paddle one-shot at exactly 36 T/iteration so a centred
      openMSX paddle lands on **128** (the rate itself is pinned, not just the
      polarity); GTPAD clocks the touch panel's NEC µPD7001 serial ADC and
      latches X/Y in the standard `PADX`/`PADY` work bytes. Two documented
      quirks reproduced **bug-for-bug** (user's call): X and Y read the same
      frame (the µPD7001 address phase is unrecoverable under our oracle, D-I-7),
      and the sticky contact-latch means an empty port 2's X/Y still report the
      last contacted reading. Funded by evicting the startup header
      (`show_title`) to a sub-ROM page-1 tenant (+71 B). Gate
      `make input-devices-acceptance` now **50 cases** (Phase D = the PDL matrix
      under paddle/touchpad in each port; Phase E = the PAD matrix under
      `arkanoidpad` — found only after trying every pluggable, since `touchpad`
      reads idle headless). Residual fixed in passing: `PDL("X")` reports the
      deferred type mismatch (ERR 13) rather than its ERR-5 domain check
      preempting it. **Still open:** `KEY(n)` and `STRIG(n) ON/OFF/STOP`, which
      are interrupt-trap surfaces and belong to the item below — the reference
      *accepts* `STRIG(1)ON`, so until that arc lands zerobas raises `ERR 2`
      there (documented divergence, decision D-I-5).
- [x] **Error handling** — `ON ERROR GOTO`, `RESUME`, `ERR`/`ERL`, `ERROR n`,
      numbered error messages — **ARC CLOSED 2026-07-19** (S1→S2a→S2b + `ERROR n`
      domain 1..255 + `ERR`-reset-on-`RESUME`, all landed on main; commits
      2551d1f→3496ce5). Full `RESUME`/`RESUME NEXT`/`RESUME <line>` family, trap
      branch, `SAVSTK`/`SAVTXT`. Standing gates `make error-acceptance` +
      `make error-trap-acceptance`. Specs
      [`docs/spec-basic-error-handling.md`](docs/spec-basic-error-handling.md) +
      the S2 packets. Known boundary: `ERROR 32768` → zerobas ERR 5 vs ref ERR 6
      (the D-F2-2 int-arg seam, documented).
      **Follow-up landed 2026-07-22 — statement syntax errors are TRAPPABLE.**
      `stmt_error` printed and aborted the RUN, so an `ON ERROR GOTO` program
      never saw a malformed statement; it now raises ERR 2 through
      `raise_error`, matching the VG-8020 for the whole class (bad `FOR` lvalue,
      bad `NEXT`, `SWAP`, unknown statement, bare word, juxtaposition, dangling
      `GOTO`), with the measured exceptions `FOR A$=` → ERR 13 and `NEXT 1` →
      ERR 2 (was ERR 1). 16 gated cases in `error-trap-acceptance`. The gap had
      been mis-reported as "silently accepted" — a probe artifact, since an
      aborting case never clears the screen and the tag regex then matched the
      echoed source line; `_outcome` in the graphics probe now detects aborts.
- [x] **Interrupt traps — ✅ ARC CONCLUDED 2026-07-26, all FIVE families landed and
      gated** (T1 `STOP`, T2 `STRIG`, T3 `KEY`, T4 `SPRITE`, T5 `INTERVAL`). Detail
      per slice below; the two later ones are recorded at the end of this item.
      ⚠️ It was declared concluded once at T4 and wasn't — `INTERVAL` turned out to
      be a fifth MSX1 family dropped on a false premise (see the reopening note
      below). `ON INTERVAL/KEY/SPRITE/STOP/STRIG GOSUB` + the arming
      statements (`INTERVAL/SPRITE/STOP ON/OFF/STOP`, `KEY(n)/STRIG(n) ON/OFF/STOP`).
      Closes the input-devices **D-I-5** handoff (`STRIG(n)/KEY(n) ON/OFF/STOP` → real,
      was documented-divergence ERR 2) and the graphics **D-G7-4** handoff (`SPRITE
      ON/OFF/STOP` no-op → real + `ON SPRITE GOSUB`). **Arc spec SIGNED OFF 2026-07-24**
      ([`docs/spec-basic-interrupt-traps.md`](docs/spec-basic-interrupt-traps.md)):
      slicing **T1→T2→T3→T4** by event-source mechanism (T1 core+INTERVAL → T2 STOP+STRIG
      → T3 KEY → T4 SPRITE). Reuse story: the `ON ERROR` trap-branch is the
      GOSUB-into-handler model, the PLAY servicer's H.TIMI hook is the per-frame poll
      seam, the input-devices matrix-hold harness is the gate. Own-design `ZTRAP` table
      in free VARTAB RAM (`$E1D1`, 18×3 B + interval counter); tri-state OFF/ON/STOP + a
      4th SERVICING state, re-enable-on-RETURN via a GSP-match service stack. **Byte
      budget is the dominant risk** — measured 2 B page-1 + 19 B page-0 low free; T1
      needs a ~70 B carve (funded by a `gosub_push` golf + evicting the INTERVAL parsers
      to a page-0 sub-ROM tenant).
      ✅ **T1 STOP LANDED** 2026-07-25 (4fef347): `ON STOP GOSUB` / `STOP ON|OFF|STOP`,
      the whole reusable skeleton (`ZTRAP`, the H.TIMI `event_poll` seam, `check_traps`,
      `set_state`, the RETURN re-enable), `make stop-trap-acceptance`. Spec
      [`docs/spec-traps-t1-stop-reslice.md`](docs/spec-traps-t1-stop-reslice.md).
      ✅ **T2 STRIG LANDED** 2026-07-25: `ON STRIG GOSUB <list>` (5 positional slots) +
      `STRIG(n) ON|OFF|STOP`, the first real **device** event source (`GTTRIG` edge
      detection in the VBLANK poll). **Closes half of D-I-5.** `make
      strig-trap-acceptance` — 25 cases / 51 assertions vs the VG-8020, including
      triggers 1..4 (a PSG-latch injection; openMSX has no joystick-button command).
      One deliberate deviation: a 6th handler slot raises a trappable ERR 2 where the
      reference crashes. Spec [`docs/spec-traps-t2-strig.md`](docs/spec-traps-t2-strig.md).
      **Note:** `INTERVAL` is MSX2 and out of charter, so it is NOT part of this arc —
      T3 = KEY, T4 = SPRITE remain. Page-1 free is down to 9 B, so **T3 needs a carve.**

      ✅ **T3 KEY LANDED** 2026-07-25: `ON KEY GOSUB <list>` (10 positional slots) +
      `KEY(n) ON|OFF|STOP`. **Closes the OTHER half of D-I-5, so D-I-5 is now fully
      closed.** KEY is a **delivery** trap, not an edge trap: it fires once per BIOS
      key-delivery — the initial make and every auto-repeat — and a trapped key is
      **diverted**, removed from the input stream before anything can read it. Neither
      published ISR hook can do that (both run *before* the keyboard scan), so the event
      source is a thin 5-byte C-BIOS seam, `H_ZKEY`
      ([`cbios-repack/key-trap-hook.patch`](cbios-repack/key-trap-hook.patch)), with all
      policy in [`basic/keytrap.asm`](basic/keytrap.asm). Auto-repeat is inherited from
      the host BIOS rather than replicated. `make key-trap-acceptance` — 28 cases /
      54 assertions vs the VG-8020. Spec
      [`docs/spec-traps-t3-key.md`](docs/spec-traps-t3-key.md).
      **Funding:** the BLOAD carve (page 1 9 B → 271 B) paid the page-1 half; the
      low-region half was paid by **promotion** — 74 B of boot-time-only sub-ROM
      plumbing moved up into the freed page 1
      ([`basic/subrom-boot.asm`](basic/subrom-boot.asm)), gated by the new
      [`tools/promote_scout.py`](tools/promote_scout.py). Walls now: low region 14 B
      free, page 1 62 B free.
      **The gate found a real, older, SHARED bug:** the ON…GOTO/GOSUB crunch in
      [`basic/tokenise.inc`](basic/tokenise.inc) abandoned the list at an EMPTY slot, so
      `ON KEY GOSUB 100,,600` (and T2's `ON STRIG GOSUB ,300`) died with a syntax error.
      Fixed repack-only — the 4 bytes overrun the byte-full lean cart, which keeps it.
      ~~**T4 = SPRITE is the only slice left in this arc.**~~
      🔴 **ARC REOPENED 2026-07-26 — `INTERVAL` is a FIFTH MSX1 trap family, and it
      was dropped on a FALSE PREMISE.** The 2026-07-24 finding "`INTERVAL` is MSX2,
      absent from MSX1" measured the right thing and drew the wrong conclusion:
      `INTERVAL ON` crunches to `FF 85 45 52 FF 94` (`INT` + literal `"ER"` + `VAL`)
      on both vendor ROMs because it is **not a keyword** — it is a reserved-word
      compound, the same shape as `MAXFILES` = `MAX`+`FILES`. It *works*: on the
      VG-8020 `ON INTERVAL=n GOSUB` + `INTERVAL ON` fires 16 / 33 / 8 times for
      n = 10 / 5 / 20 over ~160 jiffies (exact 1/n), `OFF`/`STOP` give 0, and `LIST`
      round-trips to `INTERVAL ON`. **"Absent from the keyword table" ≠ "absent from
      the language" — a crunch probe answers a tokenisation question, not a support
      question.** Happy consequence: **zerobas already crunches it byte-identically**
      (it has `INT` and `VAL`), so **T5 needs no token and no `kwtable` row** — only
      the parse + the `event_poll` counter stanza, both already specified in
      [`docs/spec-basic-interrupt-traps.md`](docs/spec-basic-interrupt-traps.md)
      §5/§6 (written for INTERVAL first, then orphaned). ~~**T5 is owed a packet.**~~

      ✅ **T4 SPRITE LANDED** 2026-07-26 (`85ac5f4`, cadence gate rebuilt `47f4999`):
      `ON SPRITE GOSUB` + `SPRITE ON|OFF|STOP`. **Closes the graphics D-G7-4
      handoff.** SPRITE is a **LEVEL** trap, one fire per frame — confirmed at the
      emulator level (300 latches over 300 frames) — and D-T-4 is to read `STATFL`.
      `make sprite-trap-acceptance` **123/123**. Spec
      [`docs/spec-traps-t4-sprite.md`](docs/spec-traps-t4-sprite.md).
      **The gate was wrong four times before the implementation was wrong once.**
      The original `F_cadence` measured the MAIN LOOP, not the trap: its "1.5
      jiffies/fire divergence" was the HANDLER'S OWN COST, and a handler taking
      >1 frame starves the main program completely — so the main program cannot be
      the instrument for a feature that can starve it. Rebuilt on emulator-counted
      fires. **A gate's DENOMINATOR must be measured, never computed by the thing
      under load.**

      ✅ **T5 INTERVAL LANDED** 2026-07-26 (`26f9251`): `ON INTERVAL=n GOSUB` +
      `INTERVAL ON|OFF|STOP`, **no token and no `kwtable` row needed** (the
      reserved-word compound above). `make interval-trap-acceptance` **149/149**.
      Spec [`docs/spec-traps-t5-interval.md`](docs/spec-traps-t5-interval.md).
      ⚠️ **It landed 14 B OVER the page-1 ceiling** (`f973e1c` corrected the
      as-built figure to 265 B): the SAVE-engine carve funded `TIME` *and* T5 —
      two of three, not three. The tree stayed red until the direct-mode
      control-flow slice reclaimed the bytes (`a5a3af2`; page-1 free now **8 B**).
      The overrun had hidden behind **warm-tree** builds reporting 55 B free —
      only `rm -rf build && make basic-reloc` measures the wall.
- [x] **`TIME` / `TIME=n` — ✅ LANDED 2026-07-26** (`1addfbc`), 81 B, gate
      `make time-acceptance` **105/105 both sides**. Retires the T3-era rule that
      banned `TIME` on the zerobas side of the acceptance harness.
      **Its gate surfaced the direct-mode `FOR` defect** that became
      [`docs/spec-basic-direct-ctrl.md`](docs/spec-basic-direct-ctrl.md): the write
      group shifted phase with a `FOR` pad, seven of eight phases errored, and the
      reduction **collapsed to one sample** while still printing a number — worse
      than no reduction. It now pads with statements instead.

      *Original entry, kept for the characterization record:* the software-clock
      pseudo-variable, standard MSX1
      BASIC and **was absent from zerobas entirely**: it is not in
      [`basic/kwtable.inc`](basic/kwtable.inc), so `TIME` parses as the *variable*
      `TI` and reads 0 forever, which makes `IF TIME-T<400 GOTO` an infinite loop —
      a **silent** divergence. Found as collateral during the T3 KEY slice
      (`20e04b4`); it is also why the acceptance harness still bans `TIME` on the
      zerobas side and sizes every observation window by iteration count.
      **Characterized 2026-07-26** against the VG-8020 — 45/45 assertions,
      [`probes/basic/basic_probe_time.py`](probes/basic/basic_probe_time.py):
      single-byte token `$CB`; the read is the **unsigned** word at `JIFFY`
      (`$FC9E`) promoted to a float (`A%=TIME` at 40000 → Overflow); the write uses
      the **house address-domain conversion zerobas already has** (`fac_to_int_addr`
      — wrap by −65536 above 32767, then truncate toward zero, ERR 6 outside
      −32768..65535); errors are ERR 13 / 24 / 6 / 2; the clock wraps mod 65536 with
      no error and its *rate* belongs to the host BIOS/VDP.
      Spec [`docs/spec-basic-time.md`](docs/spec-basic-time.md) — ~~awaiting
      sign-off; the one open decision is funding (~52–75 B, pure page 1, and page
      1 has 22 B free)~~ **signed off and implemented; funded by the SAVE
      write-engine carve** (+310 B page 1).
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
- [x] **`get_byte_arg`'s reject RETURNS INTO ITS CALLER — `WIDTH 300` corrupts
      the screen.** ✅ **FIXED 2026-07-28** (see the LANDED block at the end of
      this item). MEASURED 2026-07-27, found as the control while debugging
      LOCATE's error rows. `get_byte_arg` rejects with `jp raise_error`, and the
      abort chain PRINTS AND RETURNS — consuming the caller's own `call
      get_byte_arg` frame and landing back inside the caller just past the call,
      with **A = the error code**. So `ex_width` does `ld (LINLEN),a` with A=5
      and re-inits the screen: on the current build `CLS:WIDTH 300` prints **no
      error at all** and leaves the display unusable (measured against the
      reference's clean `Illegal function call`). `WIDTH 99999` (ERR 6, via
      `check_fperr_only`) does the same.
      ⚠️ Scope is wider than WIDTH: `get_byte_arg`'s other callers are
      `STRING$`, `SPACE$` and `ON n`, and each needs checking for the same
      shape — the bug is in the CALL CONVENTION, not in WIDTH.
      LOCATE does not use it for exactly this reason (basic/missing.asm
      `loc_next` inlines the two-stage check at the handler's own stack depth,
      where the same two `jp`s abort correctly). Not fixed here: the fix is
      per-caller frame discipline across four statements, each with its own
      gate, which is a slice rather than a drive-by.
      📋 **RE-MEASURED + SPEC WRITTEN 2026-07-28, awaiting sign-off (S-AD-1..5)**:
      [`docs/spec-basic-abort-depth.md`](docs/spec-basic-abort-depth.md). Two
      things in the paragraph above are now known to be wrong.
      **(a) The scope is nine sites, not four** — `ev_ff_arg`
      (basic/expr.asm) calls the same leaf for `STICK`/`STRIG`/`PDL`/`PAD`, and
      `get_vram_arg`/`fac_to_int_addr` reach the same abort for
      `VPEEK`/`PEEK`/`INP`. Measured untrapped: `PRINT STICK(9)` prints the
      error **and ` 0`**, `PRINT VPEEK(-1)` **and ` 32`**,
      `PRINT "[";SPACE$(99999);"]"` prints **`overflow` twice**,
      `PRINT "[";STRING$(-1,65);"]"` the error **plus `syntax error` twice**.
      **(b) Per-caller frame discipline is the expensive fix.** The TRAP branch
      of the same routine already solves the general case in four bytes
      (`ld sp,(SAVSTK)`, interp.asm) and the abort branch simply does not do
      it; §4 of the spec takes that instead, at +7…+14 B, repack-only.
      ⚠️ **The standing D-F2-2 gate is structurally blind to all of it** —
      `basic_probe_intarg.py`'s 36 asserted rows each arm `ON ERROR GOTO` and
      read `ERR`, which selects the trap path, i.e. the one path that unwinds
      correctly. It is green and would stay green with every defect above
      present. ⚠️ So is a right-stripped screen scrape: `SPACE$(-1)`'s junk is
      a run of *spaces*, and read as "clean" until the row was re-run
      bracket-delimited. **This slice is ordered BEFORE D-MISS-2**, whose fix
      is four more calls into this same convention.
      ✅ **LANDED 2026-07-28 — `make abort-acceptance` 23/23, falsified 6/23.**
      **Four bytes**, one instruction: `ld sp,(SAVSTK)` at the top of
      `fre_abort_low` ([`basic/arrays.asm`](basic/arrays.asm)). The estimate of
      +7…+14 B assumed the message tail had to be restructured so the reset
      could follow the print; it does not — the printing routines push and pop
      *below* the new `SP` and never touch the word *at* it, so the existing
      tail-jumps `ret` straight to the anchored address, which in **both** modes
      IS the run loop's own normal exit (`run_prog` and `dl_cmd` each store
      `SAVSTK` immediately before entering the loop). ⚠️ **The budget named the
      wrong wall**: `arrays.asm` is LOW REGION, so the 4 B came out of the low
      region's 11 B (→ **7 B free**), not page 1 (unchanged at 44 B) —
      **D-MISS-2 must budget from 7 B.** Repack-only; lean `basic.rom`
      byte-identical, `LEAN_SHA256` unmoved.
      Both open sign-off questions were answered by MEASUREMENT, not argument:
      **S-AD-2** — the `boot_first` row (an error as the very first statement
      after a cold boot) passes, so `SAVSTK` needs no boot init and the 5 B held
      in reserve were not spent. **S-AD-3** — the page-0 sub-ROM tenant rows
      pass, but the falsification shows they pass **with and without** the fix:
      `ary_engine` raises `Subscript out of range` at handler depth and was
      never part of this defect, so those rows are CONTROLS (the reset does not
      BREAK the tenant path), not evidence it repaired one.
      **The falsification is the load-bearing number**: comment the instruction
      out, rebuild from clean (low region goes back to 11 B, so it really is out
      of the image) and the gate reads **6/23** — and the six survivors are
      exactly the handler-depth rows, where the abort was already correct.
      Regressions: `make intarg-acceptance` ALL PASS, `make unit-test` 53/53,
      `make missing-acceptance` **214/214**.
      ⚠️ **`missing-acceptance` went RED first, for the right reason** — its own
      stale-marker check fired: three rows recorded as expected-divergent
      (`d2-string-neg`, `d2-string-256`, `d2-space-neg`) now AGREE with the
      reference, so the expected-divergent count drops **20 → 17**. Note what
      that does and does not mean: `STRING$`/`SPACE$` always HAD their domain
      check (`get_byte_arg`); what diverged was the abort SHAPE. **No part of
      D-MISS-2 is implemented by this slice** — the four `d2-chr-*` and the
      `LEFT$`/`RIGHT$`/`MID$` rows stay marked.
      Also newly visible in the falsified run, worse than anything in the
      original table: `PRINT "[";STRIG(9);"]"` printed **`-21821`** — the
      statement carried on with uninitialised memory as its value.
- [x] ✅ **~~The prompt does not open a fresh line~~ — MEASURED FALSE
      2026-08-09** by the TODO staleness sweep,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.6. Screen rows 0–1 after each line:

      | row | program | VG-8020 | CF-3300 | zerobas |
      |---|---|---|---|---|
      | `p.nofresh` | `CLS:PRINT "A";` | `A` ｜ `Ok` | `A` ｜ `Ok` | **`A` ｜ `ZB`** |
      | `p.ctl` 🟢 | `CLS:PRINT "A"` | `A` ｜ `Ok` | `A` ｜ `Ok` | `A` ｜ `ZB` |
      | `p.long` | `CLS:PRINT "AAAAAAAAAA";` | `AAAAAAAAAA` ｜ `Ok` | idem | **`AAAAAAAAAA` ｜ `ZB`** |

      The prompt is on the NEXT row on all three sides. `Azb>` on one row does
      not happen.
      🎯 **`p.ctl` IS WHAT MAKES THIS A MEASUREMENT AND NOT A COINCIDENCE.** With
      the `;` gone the cursor is already at column 0, so an *unconditional*
      newline would leave a BLANK ROW between the payload and the prompt. No
      side has one. Both the references and zerobas therefore emit the newline
      **conditionally** — which is this entry's own rule. Neither row alone can
      separate "conditional" from "always"
      ([[one-row-cannot-separate-two-rules]]); the 2×2 can. `p.long` exists so
      that a prompt painted at the cursor could not be mistaken for a
      one-column scrape offset.
      ⚠️ **This is the one stale entry that needed the machine.** Five of the
      other six were derivable from a document or a gate that already existed.
      **What was believed, kept as the record of why:** MEASURED 2026-07-27, found
      while gating `TRON`. **The reference emits a newline before its prompt
      whenever the cursor is not at column 0; zerobas prints its prompt where
      the cursor stands.** `CLS:PRINT "A";` is the whole reproducer: the
      reference paints `A` and then `Ok` on the *next* row, zerobas paints
      `Azb>` on one. No word under test is involved.
      Latent until now because almost everything zerobas prints ends with a
      newline — it took `TRON`, whose decoration deliberately emits no newline
      of its own, to leave the cursor mid-row often enough to notice. The
      `missing` probe's screen readout strips a trailing prompt on both sides
      (it already claimed to drop the prompt; it only did so for a prompt alone
      on a row), so this does not block that gate.
      ⚠️ Fixing it changes the screen output of every gate whose expectations
      were recorded against the current prompt, so it is its own slice, not a
      drive-by. Related to the screen-editor REPL item below but independent of
      it — this is one conditional CRLF, not a rewrite.
- [ ] **Screen-editor REPL** — real MSX BASIC does not use a sequential prompt
      loop; Enter reads the *current cursor line from VRAM* (not a dedicated
      input buffer), so the user can cursor-up to any visible output, edit it
      in place, and re-enter it. Needs cursor-key handling and VDP line-readback.
      Our `repl.asm` is a deliberate simplification; full replacement is Phase 3.
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

- [x] ✅ **`SAVE"CAS:name"` WROTE A TOKENISED TAPE; BOTH REFERENCES WRITE ASCII —
      CLOSED 2026-08-07 (D-CASSAVE) for 0 B.** Found 2026-08-03 by D-DOTGAPS
      ([`docs/dotgaps-msx1-characterization.md`](docs/dotgaps-msx1-characterization.md)
      §3.2) while measuring which SAVE forms write `.` — the row that looked like
      a cassette-specific `.` divergence was a **format** divergence, and the
      tape said so rather than an argument. On MSX1 `CSAVE` is the tokenised
      cassette write and `SAVE"CAS:"` is the ASCII one, `,A` or not.
      `basic/save.asm` `sav_is_cas`'s no-flag arm now `jp cas_ascii_save`: one
      absolute jump for another, **all four walls unmoved**.
      🔴 **A 0-BYTE FIX IS THE SHAPE THAT HIDES A CONFLATION**
      ([[a-filed-zero-byte-fix-can-hide-a-conflation]]), and here it was
      nameable: the fix makes `SAVE"CAS:x"` and `SAVE"CAS:x",A` **one code
      path**. A one-line diff cannot say whether that merged two behaviours that
      should stay apart — only decoding **both forms on both references** can,
      and `,A` had never been decoded. Same id, same name field, identical
      payload text: refuted, not assumed.
      🔴 **AND THE FILED READING WAS ONE MACHINE, on a SHIPPED format.** §3.2
      decoded the VG-8020 only. The CF-3300 now agrees on all twenty readings.
      🟢 **`CSAVE` is the control** — `$D3` on all three sides, untouched, which
      is what keeps *"`SAVE"CAS:"` is ASCII"* from becoming *"every cassette save
      is ASCII"*.
      ⚠️ **The tree carried a GREEN ORACLE FOR THE DEFECT**:
      `basic_probe_tape_save.py`'s `test_save_cas_format` asserted `10x$D3` for
      this very verb, and `basic/save.asm:12` documented it. Both corrected in
      the same commit. `lnblank`'s `csv-tok` pin ROTTED as designed and the row
      is **de-pinned into the scored set** — deleting a `KNOWN_DIVERGE` entry
      makes a row stricter, not weaker. Detail:
      [`docs/spec-basic-cassave.md`](docs/spec-basic-cassave.md),
      [`docs/cassave-msx1-characterization.md`](docs/cassave-msx1-characterization.md).

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

- [x] ✅ **~~`DIM Q(20000)` → `Out of memory`, reference says `Subscript out of
      range`~~ — MEASURED FALSE 2026-08-09** by the TODO staleness sweep,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.5:

      | row | program | VG-8020 | CF-3300 | zerobas |
      |---|---|---|---|---|
      | `dm.ctl` 🟢 | `DIM Q(10)` / `PRINT"[OK]"` | `OK` | `OK` | `OK` |
      | `dm.big` | `DIM Q(20000)` | `Subscript out of range` | idem | **`Subscript out of range`** |

      zerobas bounds the dimension BEFORE it allocates, which is the very thing
      the entry says it does not do.
      🎯 **AND THE GATE HAS SAID SO SINCE `9a9a4c7`.** This row is `oos-dim-huge`
      in `clearpool-acceptance`; it GRADUATED from *reported-never-gated* to
      *gated and passing* there, which is why that gate reads **52/52 (5 never
      gated)** and not 51/51 — a figure the `Makefile` header itself got wrong
      for two months and which is corrected in the same commit. Two records of
      one fact, both stale, neither noticed until the gate was RUN.
      **What was believed, kept as the record of why:**
      Found 2026-07-28 as a calibration row in the D-CLP matrix
      (`oos-vs-oom`), aimed at proving `Out of string space` was distinct — the
      **sixth consecutive slice** whose calibration turned up a live defect in
      code already marked implemented. The reference bounds a dimension
      **before** it tries to allocate; zerobas allocates until it runs out, so
      the error is right only by accident of size. An ARRAYS-arc divergence,
      NOT in D-CLP's scope. Recorded in
      [`docs/clearpool-vg8020-characterization.md`](docs/clearpool-vg8020-characterization.md)
      §3 so it is not "discovered" later by a red gate. Unmeasured: where the
      reference's dimension bound actually sits.
      ⚠️ **The row that found it was carrying TWO claims and has been SPLIT**
      (D-CLP landing, 2026-07-29). `oos-vs-oom` asserted both "out of string
      space is distinct from out of memory" (D-CLP's, and true) and "which
      non-string error a huge DIM gives" (this item, and divergent). The first
      is now gated on `DIM Q(5000)`, which overruns free variable space on BOTH
      machines; **this one lives on as `oos-dim-huge` in the probe's `arr`
      battery — reported, never gated.** It was not silenced to make D-CLP
      green: it is the standing record, and it will turn from `----` to a
      gateable row the day the ARRAYS arc fixes it.
      ✅ **CHARACTERISED 2026-07-29** —
      [`docs/arrdim-vg8020-characterization.md`](docs/arrdim-vg8020-characterization.md),
      probe [`probes/basic/basic_probe_arrdim.py`](probes/basic/basic_probe_arrdim.py),
      `make arrdim-characterize` — 49 rows, eight batteries, boot-per-case.
      **Baseline 27/46 gated** (3 reported-never-gated); **all 19 divergences are
      one root cause.** The rule: **`elsize × Π(boundₖ+1) > $FFFF` ⇒ `Subscript
      out of range`, raised before any allocation.** It is a **byte** count
      (the flip moves with element width — `%` 32766/32767, `!` 16382/16383,
      `#` 8190/8191, all at 65536 B; `Q%(32767)` has 32768 elements, which fit a
      word, and still raises), it **excludes the header** (`Q%(32766)` = 65534 B
      → `Out of memory`), it is strictly **`>`** (`Q$(21844)` = 21845×3 =
      `$FFFF` exactly is ACCEPTED — the only element width in the language that
      can land on the boundary, which also pins `elsize($) = 3`), and it is on
      the **product**, position-independent (`DIM Q%(200,200)` raises with no
      dimension near a ceiling). ⚠️ **It lives in the ALLOCATOR, not in `DIM`**:
      `Q(1,1,1,1)=1` on an *undeclared* array auto-dims to 10 per dimension =
      117128 B and raises, with neither `DIM` nor a large number in the line —
      so a check written into `ex_dim` would have satisfied every other row and
      left that one silently wrong.
      📋 **SPEC WRITTEN, awaiting sign-off (S-ARR-B-1..4)**:
      [`docs/spec-basic-arrdim.md`](docs/spec-basic-arrdim.md) — **est. +4 B,
      sub-ROM only, NO CARVE**: `sub/arrays.asm` already computes the quantity
      and already detects both overflows (`ary_count_elems`,
      `ary_mul16_checked`); the two carry paths just report `ARY_ERR=4` where
      the measurement says `1`. The other three carry checks are address-space
      wraps and stay `Out of memory`. Falsification is unusually surgical: the
      two sites catch **disjoint** row sets (site A = `dim-3d` alone, site B =
      the other 18).

- [x] ✅ **`MAXDIM = 4` was a divergence, not a cap — D-ARR-C LANDED 2026-07-29,
      65/65 gated, and it GAVE BACK 31 B.** Spec
      [`docs/spec-basic-arrdim-c.md`](docs/spec-basic-arrdim-c.md), measurement
      [`docs/arrdim-c-vg8020-characterization.md`](docs/arrdim-c-vg8020-characterization.md),
      gate `make arrdim-acceptance` (73 rows; 65 gated, 8 never-gated). Found as
      a calibration row in the D-ARR-B matrix — the seventh consecutive slice
      whose calibration turns up a live defect nobody was looking for.
      **There was no cap to match**: the reference answers `ERR`=0 at 4, 8, 16,
      32, 40, 42, 44, 64, 100 and **120** subscripts (a 249-character line), and
      it stores and reads an element back through 32 of them.
      ⚠️ **`ERR`=0 IS NOT ENOUGH** — a machine that accepts the line and drops
      every subscript past its own cap reads 0 too. The `use` battery is the
      round trip the dropped dimensions cannot forge.
      ⚠️ **THE PREMISE THE SLICE WAS SPLIT ON WAS WRONG.**
      [`spec-basic-arrdim.md`](docs/spec-basic-arrdim.md) §7a split it out
      because a pointer design "rewrites `ary_resolve`'s column-major
      element-address math, where a mistake is silent memory corruption". It
      does not: `ary_parse_subs` pushes subscript 0 FIRST, so it sits at the
      HIGH address — point the tenant there and walk DOWNWARD and every consumer
      keeps visiting k=0..n-1 in today's order. `inc ix` → `dec ix`, same size,
      offset math untouched. Same correction ran through the cost: §7a estimated
      −10…−15 B and it measured **−28 B** (low region 4 B → 32 B free).
      **Removing a constraint removes more than the line that states it** — the
      cap's unwind path, its skip-to-`)` recovery, the `_kt` shim and two
      callers' publish/pop tails all went with it.
      `MAXDIM` is gone; `ARY_IDX`'s 8-byte buffer is now `ARY_IDXP` (a pointer)
      + `ARY_CUR`, freeing 4 B of RAM in a span whose own header records "no
      slack for anything more".

- [x] ✅ **D-LINEMAX — the input line AND the crunched line. LANDED 2026-07-29,
      gate `make linemax-acceptance` 60/60 typed + 3/3 `--cas`.** `LINEMAX` 96 →
      255, the crunch bounded at 314 body bytes with `Line buffer overflow`
      (ERR 25), ASCII/tape path free. `arrdim-acceptance` **73/73** (its
      `NEVER_GATED` set is now EMPTY — all 8 rows promoted), `array-acceptance`
      149/151 (standing baseline), `clearpool-acceptance` 52/52, unit-test 53/53,
      lean byte-identical. Low region **9 B free**, page 1 **6 B free**.
      🔴 **THE SPEC COUNTED TWO BUFFERS AND THERE WERE THREE.** `DETOKBUF` (LIST's
      render target) is SIZED FROM `LINEMAX` — the wave-3 detok spec derives its
      512 B as `95×5=475` and explicitly dismissed the 255-char case because "the
      source line is capped at 96 bytes" — so R-1 would have turned a second,
      previously-safe unbounded buffer into a 1270-byte write into 512. Found
      while implementing, not while specifying; **one `grep` for `LINEMAX` would
      have found it.** Now 1280 B, and FALSIFIED before trusted (revert it and
      `list-max` reads `78`, a byte of the rendered text, through `$C100`).
      ⚠️ **COST 1792 B, NOT THE 768 SIGNED OFF** — measured `FRE(0)` 15667 →
      13875. Five `array-acceptance` rows reserved `CLEAR 14000`/`15000` and died;
      re-sized with sign-off (root counts, the actual subject, untouched).
      **The suite no longer proves a ~12 KB string workload runs.**
      ⚠️ **`TOKBUF` is 576 B, not 315:** the spec's single `tk_loop` test could not
      work — `tk_str_loop`/`tk_rem_rest`/`tk_data_rest` never re-enter `tk_loop`.
      The buffer ABSORBS the worst pass and `tk_end` adjudicates once, so the
      bound is PROVABLE from `LINEMAX` rather than audited emit site by emit site.
      ⚠️ **The `corrupt` battery was not boot-isolated and its own control agreed
      for the WRONG REASON:** `reset=("NEW",)` clears the program, not `ERRCODE`,
      so `code-ctl` read back the ` 25 ` `code-over` had just raised — on BOTH
      machines, so it PASSED while measuring nothing. Alone on a fresh boot: ` 0 `.
      Also fixed: a ONE-SIDED `rem` calibration (retargeted to the `rem-254`/`-255`
      pair, which admits `LINEMAX=255` and no other value), `--only` ignoring
      comma lists, and `make linemax-characterize`/`-acceptance` NOT EXISTING
      despite the previous commit citing them.
      Superseded detail below (kept for the route it records).

- [x] ✅ **~~D-LINEMAX — the input line AND the crunched line. SPEC WRITTEN,
      MEASURED, AWAITING SIGN-OFF~~ — SHIPPED; THE ENTRY WAS STALE, FOUND
      2026-08-21 by the gap sweep**
      ([`docs/gapsweep-2026-08-21.md`](docs/gapsweep-2026-08-21.md) §4).
      Measured at `cf0c4b6`, not inferred: `LINEMAX equ 255`
      ([`basic/sysvars.inc:807`](basic/sysvars.inc:807)), `TOKBUF equ $EC00` /
      `TOKBUFSZ 576` / `TOKMAX_BODY 314`
      ([`basic/sysvars.inc:847`](basic/sysvars.inc:847)), ERR 25 `Line buffer
      overflow` present in `err_msgtab`
      ([`basic/interp.asm:1209`](basic/interp.asm:1209), sub-hosted), and
      **`make linemax-acceptance` 60/60** — the `corrupt` rows, the ones with
      teeth, included. The 96-byte unbounded crunch survived only in the retired
      lean cart, which is gone.
      🔴 **THIS ENTRY WOULD HAVE BEEN RANKED FIRST ON ITS OWN TEXT** — 22/53 was
      the biggest red set in the file and the defect it names (a 27-character
      line writing 407 bytes into 96, over `ARYTAB`/`ZTRAP`/`POOLSIZE` into
      `STRTAB`, silently) is the worst class there is. Ranking on FILED TEXT
      rather than on a re-reading would have spent a slice re-implementing
      shipped code [[todo-staleness-sweep]].
      The original entry follows.
      ~~🔴 **D-LINEMAX — the input line AND the crunched line.**~~ Spec
      [`docs/spec-basic-linemax.md`](docs/spec-basic-linemax.md), measurement
      [`docs/linemax-vg8020-characterization.md`](docs/linemax-vg8020-characterization.md),
      probe [`probes/basic/basic_probe_linemax.py`](probes/basic/basic_probe_linemax.py)
      (seven batteries, 61 rows + 3 cassette rows; baseline **22/53** typed).
      Split out of D-ARR-C, which measured the input-line half
      ([`docs/arrdim-c-vg8020-characterization.md`](docs/arrdim-c-vg8020-characterization.md)
      §4) and could not reach it.
      ⚠️ **IT WAS FILED UNDER THE WRONG CAUSE FOR A WHOLE SLICE**, and then
      filed at the WRONG SIZE. `cap-64`/`cap-100` were carried as "MAXDIM=4"
      rows by the D-ARR-B commit; the cap is what hid the truncation. But the
      input line turns out to be the *smaller* half:
      * **Input line — one constant.** Reference **254** characters, zerobas
        **95**, and both already agree on what truncation MEANS (drop the tail,
        keep and store the line, raise nothing). `LINEMAX` 96 → **255**.
        The one-page low-byte idiom in both readers SURVIVES — it needs a
        page-aligned base and ≤ 256 bytes, not ≤ 96 — so no reader logic
        changes, and the G3/G4/G5 aliasing argument is RETIRED rather than
        re-proved.
      * 🔴 **Crunched line — a LIVE memory-corruption defect, today, at
        `LINEMAX=96`.** The crunch expands (`0#` = 2 chars → 9 bytes) and
        `TOKBUF` (96 B) is bounded NOWHERE. A **27-character** line overruns it;
        the worst case writes **407 bytes into 96** — over `ARYTAB`, the
        error-trap block, `ZTRAP`, `POOLSIZE`, into `STRTAB` — silently, and
        after it zerobas cannot execute `B=7`. The reference refuses at 315
        body bytes with **`Line buffer overflow`, ERR 25**. This is what
        actually sizes the slice.
      ⚠️ **THE APPARATUS HAD THE ANSWER HARD-CODED, AND IT WAS A GUESS.**
      `omsx_repl.MAX_BUF` was 250 and *refused to inject anything longer*, which
      is why §4 read the reference's ceiling as 250 — the harness's cap reported
      as the machine's. Fixed to 254, measured. Also fixed: an EMPTY capture was
      being discarded, collapsing "line refused" into "the machine never got
      there".
      ⚠️ **A BYTE-COMPARISON GATE CANNOT SEE THIS.** Every `lnum` row PASSES —
      both machines crunch identical bytes and only the one with a 96-byte
      buffer is harmed. **Agreement on what was produced is not agreement on
      whether it fit**; the `corrupt` rows, which read the damage, are the ones
      with teeth.
      Decisions taken (2026-07-29): **repack-only**, because the lean cart is
      retired (below); RAM funded by lowering `TXTMAX` 768 B, chosen **by
      measuring** — the reference funds its own buffers out of the same `FRE(0)`
      pool programs live in, so that is the faithful mechanism, and the
      alternative (dropping `MAXFILES` to 1) moves AWAY from a reference that
      supports 15. Message-string placement deferred to implementation.

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

- [x] **`GET(RDBLK)` IS AN INTERMITTENT GATE ROW — FIX THE ANCHOR — ✅ DONE 2026-07-30.**
      [`docs/spec-rdblk-anchor-flake.md`](docs/spec-rdblk-anchor-flake.md).
      Falsification battery **14/14** · repeatability `ONLY='GET(RDBLK)'` **10/10, 0
      retries** · standing gates **54/54 · 34/34 · 12/12 · 7/7** · ROMs byte-identical
      from clean, walls unchanged (low 80 B / page 1 49 B), dead-code sweep 0/0.
      🔴 **THE FILED DIAGNOSIS WAS WRONG ABOUT WHICH CLOCK.** `--settle`/`--keys-at` are
      openMSX **emulated** time, and the anchor is a breakpoint on `done` — so the
      readout was **already sentinel-gated** and the emulated timeline is
      bit-deterministic (ours 24.137504 / stock 24.450109, identical across every run
      measured). The elapsed-seconds gate that actually remained was the **host-side
      process deadline**: `run_job_raw` SIGKILLed openMSX **silently**, and to every
      caller that is indistinguishable from "this machine ran its whole timeline and
      never reached the anchor" — an APPARATUS event laundered into a SUBJECT-shaped
      verdict. Fixed with a `after realtime` **liveness heartbeat** (wait on PROGRESS,
      not elapsed seconds; kill on stall under the untouched ceiling; report the reason
      and the stall point), a **LOGICAL (exit 2) vs APPARATUS (exit 3)** split in
      `capture`, `reverse savereplay` on a logical miss, renested timeouts (they had
      been INVERTED: 220 s per boot inside a 240 s cap for a 6-boot probe), and a
      **bounded, PRINTED** retry on the apparatus class only — never on a logical miss.
      🔴 **THE G4 CONTROL CAUGHT A DEFECT IN THE FIX ITSELF.** The stall clock started
      at `t0`, i.e. before openMSX had launched, charging 0.21–0.82 s of spawn + XML +
      ROM/symbol load to the emulator: under load a HEALTHY run was stall-killed, and it
      did **not** reproduce standalone. Shipping it would have traded one intermittent
      row for a **corpus-wide** one. The clock now starts at the FIRST BEAT.
      🟢 **BIGGEST FIND, and it came from the user challenging a recorded belief:**
      testing "is the wedge really pty exhaustion?" (it is not — 7 pty holders against a
      511 limit, and openMSX allocates none) surfaced that the preamble left
      `sound_driver sdl`, so **every headless probe boot opened a CoreAudio device and
      ACTIVELY STREAMED** — ≈200 start/stop cycles per gate run, audible on the dev
      machine, and a candidate cause of [[openmsx-coreaudio-wedge]]. `sound_driver null`
      is **measured** neutral (zero drift on both machines, byte-identical captures) and
      removes the whole class. ⚠️ Deliberately NOT `mute`/`master_volume 0` — those
      silence the noise and leave the churn.
      ⚠️ **NOT PROVEN: the original trigger.** The flake never reproduced on demand, so
      nothing shows the 2026-07-30 event would now be caught as APPARATUS; and
      `sound_driver null` removes a candidate cause, not a demonstrated one.
      Left alone (noted §7): `WARNING: Var start is never used` in `rdblk_rt.asm` — a
      documentary label for `$0100`, zero emitted bytes, probe-side.

      **Original entry, for context.** (observed
      2026-07-30 during the dead-code-gate slice, which is NOT its cause).
      [`probes/disk/disk_probe_rdblk_roundtrip.py`](probes/disk/disk_probe_rdblk_roundtrip.py)
      failed once in a full `make diskbasic-acceptance` (33/34), then **passed
      standalone AND in a full re-run on the BYTE-IDENTICAL build** — so the subject
      is innocent and the APPARATUS is the defect.
      🟢 **THE PROBE DIAGNOSED ITSELF CORRECTLY, which is why this is a fix and not an
      investigation**: it printed `*** MISALIGNED — diff NOT meaningful ***` with
      `stock reached anchor: NO (looped / never hit occurrence #1)` /
      `ours reached anchor: YES`, and its own source calls this class
      "Anchor/keys/timing problem, not a `$27` result". **It refused to report a
      memory diff between two different logical points** — exactly the discipline
      [[width-domain-slice]] and [[traps-t2-strig-slice]] ask for. The bug is only
      that it can get there at all.
      **Cause to fix:** the capture uses FIXED WALL-CLOCK injection —
      `--keys "\rRDBLK\r" --keys-at 20 --settle 40` — so whether the STOCK side
      reaches `done` depends on host timing. ⚠️ **I speculated host contention from my
      own overlapping runs and then WITHDREW it: the timestamps do not support it**
      (diskbasic ran 12:44–13:15, after any overlap). Cause is unconfirmed; what is
      certain is that the anchor is time-based and therefore not deterministic.
      **Fix direction:** gate the readout on a `done` SENTINEL rather than elapsed
      seconds — the standing lesson [[traps-t3-key-slice]] ("gate every reading on a
      `done` sentinel"), which the rest of this corpus already follows. Failing that,
      retry-on-MISALIGNED with a bounded count and REPORT the retry (a silent retry
      turns a flaky gate into an invisible one).
      ⚠️ **DO NOT "fix" this by loosening the misalignment check.** That check is the
      only reason the flake was legible instead of a fabricated 0-byte diff.
      Also noticed in passing: `WARNING: Var start is never used on line 33 of
      probes/disk/rdblk_rt.asm` — probe-side, unrelated, and NOT covered by the new
      dead-code gate (which sweeps `basic/` + `sub/`, not `probes/`).

- [x] **LAND THE TRANSITIVE DEAD-CODE SWEEP AS A TOOL — ✅ DONE 2026-07-30.**
      [`docs/spec-deadcode-gate.md`](docs/spec-deadcode-gate.md).
      [`tools/check_dead_code.py`](tools/check_dead_code.py) +
      [`tools/deadcode-allow.txt`](tools/deadcode-allow.txt), a **HARD GATE** inside
      `make basic-reloc` over **BOTH** builds (user chose the hard gate over an
      advisory report), plus `make deadcode` for the report while writing a routine
      ahead of its caller. Standing state: **main 0 dead** (1544 spans, 264 seeds),
      **sub 0 non-allowlisted** (1375 spans, 98 seeds, 1 allowlisted). R1's walls
      UNCHANGED at low 80 B / page 1 49 B, `basic-reloc.rom` byte-identical.
      🟢 **ITS FIRST FINDING AS A GATE: 24 B in `sub/graphics.asm`.**
      `gfx_border_read` was orphaned when the empirical VG-8020 PAINT bug fix replaced
      it with `gfx_paint_read`, and sat unreferenced from G5 all the way to R1 —
      **with three comments still describing it as the live border reader** (lines
      1592, 1724, 1842, all corrected). Deleted; sub page-0 content `$302A -> $3012`,
      free 4054 -> 4078 B.
      🔴 **THE ALLOWLIST IS A CONTROL, NOT A SUPPRESSION LIST — this is the design
      point.** The gate asserts every allowlist entry is STILL DETECTED AS DEAD. The
      dangerous failure for this tool is not a false red, it is **going blind and
      reporting a clean tree forever** — an over-broad seed set, a broken span model
      or a path change all look exactly like success. `fmt_menu_text` (16 B, a
      DOCUMENTED deliberate keep preserving `format-body.inc`'s pre-eviction byte
      layout) is therefore a permanent canary: if it stops reading as dead, either it
      gained a caller or the sweep broke, and both must be looked at.
      **FALSIFIED THREE WAYS**, the third being the one the review's own scratchpad
      harness lacked: (A) inject a dead routine into EACH build -> both reported,
      exit 1; (control) give each one live caller -> 0 dead, exit 0; (B) `--blind`
      (seed every label) -> prints **"0 dead" for both builds**, which reads as
      success, **and the canary fires**, exit 1. Allowlist guards each verified to
      fire: missing reason, bad build name, entry that is not actually dead. Seed
      vacuity guards: `init` must resolve, every sub entry-table seed must resolve,
      and <20 parsed tenants is a hard error.
      ⚠️ **THE GATE HANGS OFF THE `basic-reloc` PHONY TARGET, NEVER OFF THE
      `$(RELOC_SYM)` FILE RULE** — it needs both `.sym` files, and `$(SUB_ROM)`
      already depends on `$(RELOC_SYM)` through `sub/basic-resident-abi.inc`, so the
      other wiring would close the build-graph cycle the Makefile is shaped to avoid.
      Not swept: `disk/` (its own build, its own seed problem, not wall-constrained).

      **Original entry, for context.** (filed 2026-07-30 by the ROM
      REGION STRUCTURE REVIEW, which built it in a scratchpad and threw it away).
      It found **122 B** where pasmo's per-symbol warnings showed 80, and it is the
      only instrument in the tree that can see a routine that IS referenced but only
      from code that is itself dead (`div_zero`, `var_find`). Worth `tools/`, with a
      standing gate that reports the dead set — the review's whole point is that this
      finding sat unread in ~230 lines of warning noise for months.
      ⚠️ **IT MUST KEEP ALL FOUR APPARATUS FIXES**, each of which produced a confident
      wrong row while missing: (1) the terminator test must use
      `check_tenant_closure.py`'s `_is_terminator` — a naive `^(ret|jp|jr)` matches
      `jp nc,x`/`ret nz` and falsely kills fallthrough-entered routines
      (`ei_set`/`spr_set`); (2) lines before a file's first label must be attributed
      to an always-live prologue span, or references made there are invisible
      (`sp_done`); (3) closure must follow **DATA** references (`ld hl,label`,
      `dw label`), not just call/jp/jr/djnz — this is the one that read
      `keytrap.asm`'s `$0038` hook as promotable; (4) 🔴 **"dead" is PER-BUILD** — a
      body `.inc` shared by main and sub has TWO answers, and `disk_putword` was dead
      in main, live in sub, with its only caller outside `main.asm`'s include closure.
      The tool should walk BOTH builds and report per-build, and `IF SUB_BUILD` is the
      sanctioned fix for the asymmetric case. Seed on build consumers only
      (`init` + `sub/` + `tools/`): seeding on `tests/`/`probes/` too hides the whole
      `vars.asm` block, because the ported tests still name it — that seed choice is
      the difference between 16 dead spans and 4. Falsify both ways (inject a dead
      routine; then give it one live caller).
      Also worth landing beside it: the **per-include byte-extent measurement** (inject
      zero-byte labels around all 111 `include` sites, recursively) whose own control
      is that both instrumented images assemble BYTE-IDENTICAL to the shipped ROMs —
      that is what produced every size in the review, and pasmo emits no listing file.

- [x] **ROM REGION STRUCTURE REVIEW — ✅ DONE 2026-07-30, and R1 LANDED.**
      [`docs/rom-region-structure-review.md`](docs/rom-region-structure-review.md) +
      [`docs/spec-rom-region-rebalance-r1.md`](docs/spec-rom-region-rebalance-r1.md).
      **THE WALLS ARE OFF ZERO FOR THE FIRST TIME IN THE ARC: low 0 B -> 80 B free,
      page 1 7 B -> 49 B free**, `sub.rom` byte-identical (`1dbbfe2f…`). All gates
      green incl. linemax 60/60 (ERR 25's string moved).
      🔴 **THE MAIN ROM'S PAGE-1 HALF HAS NO PLACEMENT CONTRACT AT ALL.** All 13
      sub-ROM page-0 tenants — 709 routines of closure — call **ZERO** main routines,
      so nothing in page 1 is contract-forced there; all 16377 B of it is
      pressure-placed. The `$4000` contract points ONE WAY (low-region code that
      page-1 tenants and the `$0038` ISR reach must stay low). Falsification control:
      re-seeding the same script with the page-1 tenant table finds 20 main callees,
      so the zero is a result, not a broken script. Consequence: **page-1 -> low moves
      are always legal** (only the low wall blocks them); low -> page-1 needs exactly
      one check, the forced set. 165 of 424 low-region labels are forced;
      `keytrap.asm` + `sprtrap-body.inc` forced WHOLE; `input.asm` (446 B) and the
      message pool pressure-placed WHOLE.
      🔴 **DE-EVICTION IS REFUTED BY MEASUREMENT — closed, do not spend a slice on
      it.** Largest resident stub is ~42 B (`dirverb`, the only tenant with two call
      sites, i.e. the case most likely to cross) against the SMALLEST body in the tree
      at 74 B. Every one of 35 tenants is on the right side by >=35 B. It buys
      simplification at a 35-155 B main-ROM **LOSS** against a 0 B wall.
      🔴 **THE CARVE WAS 122 B, NOT 80** — a TRANSITIVE sweep found two blocks
      pasmo's per-symbol warnings cannot see: `div_de_bc`/`mod_de_bc`/`div_zero`
      (26 B; **`div_zero` IS referenced — only from the other two**) and
      `disk_putword` (16 B). Sweep falsified both ways (an injected dead routine is
      found; the same routine with one live caller is not).
      ⚠️ **"DEAD" IS PER-BUILD, AND ONLY THE BUILD CAUGHT IT.** `disk_putword` is
      dead in MAIN and live in SUB: its definition is in the shared
      `basic/sv-diskwr.inc`, its only caller in `basic/sv-bsvdisk.inc`, which ONLY
      `sub/save.asm` includes — outside `main.asm`'s walked closure, so invisible.
      Deleting it failed the assembly. Now an `IF SUB_BUILD` gate (the second in the
      tree). **Nothing in the review's own apparatus could have found this.**
      ⚠️ **THE "128 B OF FREED RAM" THIS ITEM CARRIED FORWARD DOES NOT EXIST.** The
      `$E1C0..$E240` span was already spent by three later slices, each describing
      itself as homing in "the freed VARTAB window": `ARYTAB` `$E1C0`, `DIRECTF`
      `$E1C2`, `SAVSTK` `$E1C3`+`SAVTXT`, `ZTRAP` `$E1D1..$E207`. `sysvars.inc`'s own
      comment still claimed it was free — **corrected in place**. "`VAREND` must stay"
      was stale too (nothing references it; `STRTAB` is retired). R1 freed 122 ROM
      bytes and **0 RAM bytes**.
      ⚠️ **MY APPARATUS WAS WRONG FOUR TIMES BEFORE THE ANSWER WAS RIGHT ONCE**, and
      one row was actively dangerous: a call-graph-only closure missed
      `ld hl,zkey_hook` (a DATA reference), so **`keytrap.asm` — the `$0038` keyboard
      hook — read as PRESSURE-PLACED and would have been nominated for promotion into
      page 1**, where a page-1 tenant pages it out. There is now an assert on it.
      Also: a conditional `jp nc,`/`ret nz` read as an unconditional terminator
      (falsely killed `ei_set`/`spr_set`); lines before a file's first label belonged
      to no span (falsely killed `sp_done`).
      **NEXT TIER — ✅ ANSWERED 2026-08-05 by D-PINDATA, and the answer is DON'T.**
      [`docs/spec-rom-region-promote-input.md`](docs/spec-rom-region-promote-input.md).
      Re-measured from clean, instrument controlled by ROM byte-identity:
      **`input.asm` is 458 B, not the filed 446** (it grew 12 B), page 1 holds
      **301 B**, low holds **23 B** — so the promotion is **short by 157 B**, not by
      the 439 the stale note implies.
      🔴 **AND THE PREMISE IS INVERTED.** The item's rationale is that low is "the
      binding wall". Assembling every commit that touched `basic/` since the review
      landed (31 builds, pasmo is 0.1 s) says otherwise: **low moved 3 times, page 1
      moved 20+.** Low has sat at exactly 23 B for 25 of the 31 and never went below
      9; page 1 has ranged **5 B → 311 B** and spent **six consecutive commits at
      ≤ 8 B**. Promoting `input.asm` would drive **page 1 — the wall that actually
      binds — to zero** to add 458 B to the wall that sits. Structural reason, also
      measured: only **1643 B of the low region's 6126 B is contract-forced**, so
      "low free = 23 B" measures a PACKING CHOICE, not a contract, and the split can
      be re-cut on demand. **The promotion is DECLINED, not blocked** — that outlives
      the 157 B. Re-open only against a measured low-region need.
      🔴 **THE SAFETY CHECK FOUND A LIVE BLIND SPOT IN THE GATE, NOT IN `input.asm`.**
      The review's §0.1 error 3 fix (a call-graph-only closure missed
      `ld hl,zkey_hook`, a DATA reference) reached `check_dead_code.py` and **NOT**
      `tools/check_tenant_closure.py` — the gate that decides what may SHIP and the
      review's own named feasibility oracle — nor `tools/promote_scout.py`, the scout
      that decides what to ATTEMPT. Both matched only `call|jp|jr|djnz`. Measured
      instance: `tkf_ref32767/65535/32768` (15 B of bound tables at
      [`basic/float.asm:29`](basic/float.asm:29)) are reached by `ld de,tkf_ref32768`
      in `dcc_dexp5`, inside the closure of `flt_to_int16`, a **resident-ABI export**.
      `promote_scout` graded them **`PROMOTABLE` rc 0**; relocating them into page 1
      left the old gate printing **`OK … No page-1 escapes`, rc 0**. Fixed: a data
      pass on all three walks, on two rules that are each falsified — an `equ` is a
      VALUE (dropping that rule = **63** spurious page-0 escapes) and a data edge does
      NOT propagate control flow (dropping that = **482 B / 35 labels** over-pinned).
      🔴 **K1d PREDICTED RED AND MEASURED GREEN, and the green was the finding.** The
      tenant does NOT read those bytes at runtime: `cpt_round`
      ([`sub/circleparse.asm:345`](sub/circleparse.asm:345)) only ever converts
      `ratio*256` with `ratio <= 1`, so dexp <= 3 and the dexp==5 arm is **unreachable
      from the only tenant caller**. The pin is a CLOSURE-CONTRACT pin, not a live
      fault, and the spec says so. Separated by the K1/K1e knife PAIR, which also
      localised the real reader as main-side and corrected the probe's own row labels.
      New gate `make dexp5-pin` — **16/16 vs the VG-8020 in 6.0 s**, and the 15 bytes
      had **no gate at all** before (graphics CIRCLE corpus tops at coord 80 = dexp 2).
      ⚠️ **Naming an assembler label in a `tools/*.py` comment immunises it from the
      dead-code sweep** (`external_names` scans `tools/`; the main seed count moved
      283 → 284 on a comment mentioning `dcc_dexp5`). Nothing masked here — 0 dead
      before and after — but the hazard is real and unfixed. **WIDENED by D-EVLNO
      below: `sub/` is scanned too, and the trigger there was a comment naming two
      REJECTED candidates (284 → 285).**
      ✅ **RANK 4 OPENED AND COSTED 2026-08-05 — D-EVLNO**,
      [`docs/spec-rom-region-evict-lineno.md`](docs/spec-rom-region-evict-lineno.md).
      The tier's first per-file eviction, costed by BUILDING it as §7 demanded:
      `parse_lineno` (the D-LNBLANK line-number scanner, `basic/program.asm`) is now
      sub-ROM page-1 tenant index 23 (`sub/lineno.asm`). **73 B body out, 18 B stub
      back, 55 B NET** — main page 1 **301 -> 356 B free**, low unchanged at 23 B,
      sub page 1 2411 -> 2324 B. The 73 B body is **BYTE-IDENTICAL** at its new
      address, so the move is provably verbatim.
      🔴 **THE SUB PAGE-0 ENTRY TABLE IS FULL, AND THE REVIEW'S OWN RANK-4 RULE
      CONTRADICTS THAT.** 13 rows `$0010..$0036`, **ONE spare byte** before the fixed
      `$0038` IM1 vector (`$0037` = `FF`, `$0038` = `C3 0A F1`; measured, and
      `sub/sub.asm` + `sub/equates.inc` both already said so — nothing had connected
      it to "prefer page 0"). **A 14th page-0 tenant does not fit.** So a future
      rank-4 candidate that genuinely needs to call main page 1 is BLOCKED until
      `SUBROM_ENTRY_BASE_P0` is relocated past `$0038`. This candidate did
      not need it: the body calls **nothing at all**, so it is legal on either island
      and free bytes decided nothing — the *table* did.
      ✅ **DONE 2026-08-05 — D-P0BASE**, [`docs/spec-rom-region-p0base.md`](docs/spec-rom-region-p0base.md).
      `SUBROM_ENTRY_BASE_P0` is **`$0040`**, above the vector. **Index 13 is free and
      the table has no cap.** Cost **44 B of sub page 0** (3913 -> 3869); main walls
      unchanged (low 23 B, page 1 356 B), `sub.rom` page 1 **byte-identical**,
      `basic-reloc.rom` differs in **exactly 18 bytes** (every `ld ix` low byte,
      each +`$30`), and a relocation-aware page-0 diff explains **every** differing
      byte as a 16-bit operand moved by +`$2C` — **0 unexplained**.
      🔴 **AND THE REVIEW'S STATED JUSTIFICATION FOR "PREFER PAGE 0" IS THE WRONG
      ONE.** The visibility argument (a page-0 tenant may call main page 1) is worth
      **at most 95 B**, is claimed by **zero** candidates, lands on **sub**-ROM
      space rather than main, and is structurally unreachable: 777 of 1045 main
      page-1 labels are page-0-ILLEGAL, and all 268 legal ones are leaves, because
      anything reaching into main page 1 transitively reaches `eval` (low region) or
      `pchar` -> `CHPUT` (BIOS) and becomes illegal in the same step. The rule is
      right for a **capacity** reason nobody had measured: the table filled at
      `6c72931` (2026-07-29) and sub page 0 has been **frozen at 3913 B free for the
      last 9 commits** while page 1 absorbed **1015 B** — page 0 held **63 %** of the
      sub-ROM's free space and could accept no new tenant.
      🔴 **The filed justification was wrong twice.** "Free space starts at `$003B`"
      — no: `$003B..$0040` is `sub_p0_ping`, and basing the table there would have
      overwritten the tenant every boot gate calls. "Every call site is symbolic" —
      true of `basic/*.asm` (18 sites) and **false of the harness**: three probes
      carry the entry address as a hardcoded *byte* in injected machine code.
      ⚠️ **FOUR THINGS D-P0BASE FOUND — (a)+(b) CLOSED by D-ROMJUDGE, (c) UNFIXED,
      (d) fixed in-slice:**
      (a) 🔴 **`pasmo` answers a NEGATIVE `ds` count with a WARNING and EXIT 0**,
      writing a **zero-byte** file, and the whole `make basic-reloc` gate chain then
      passes the padded result at rc 0. `tools/pad_rom.py` now refuses an EMPTY
      input, which closes the total case — but a **partially truncated** ROM would
      still be laundered, and nothing bounds that.
      ✅ **DONE 2026-08-05 — D-ROMJUDGE**,
      [`docs/spec-rom-gate-judge.md`](docs/spec-rom-gate-judge.md).
      🔴 **AND THE FILED ROUTE WAS THE WRONG ONE.** A negative `ds` never produces a
      partial file — measured three source shapes, **all 0 bytes** — so that route
      was already closed. The reachable route is a **short assembly**: comment out
      `sub/sub.asm`'s final `ds $8000 - $, $FF` and pasmo emits **30444 B**,
      `pad_rom` invented the missing **2324** and printed a line indistinguishable
      from a healthy build, `make basic-reloc` rc 0, `subrom-acceptance` PASS. Also
      **74** such `ds <fixed> - $` sites in 8 files, not "at least three" —
      **68 of them under `disk/`**. Fixed: padding is now **opt-in** (`--pad`);
      every live caller measured **exact** (sub 32768/32768, disk 16384/16384,
      sub-unguarded 32768/32768), so the rule has zero slack.
      🔴 **AND K3 FOUND THE REAL DEFECT: a refusal that leaves the bad artifact on
      disk is DEFEATED BY RUNNING `make` TWICE.** First `make` refuses and leaves
      the 30444-byte file with a fresh mtime; the second says *"up to date"* and the
      chain passes at rc 0. **Same for D-P0BASE's one-day-old empty-input refusal**
      (0-byte artifact survives its own refusal). Closed with **`.DELETE_ON_ERROR:`**
      — one line, covering every rule in the Makefile. ⇒ **ask of any new refusal:
      what does the SECOND `make` do?**
      (b) 🔴 **`tools/check_kwtable_identity.py` PRINTS ITS OWN DENOMINATOR AND DOES
      NOT JUDGE IT.** On the all-`$00` sub.rom above it reported
      `OK: … the sole source (1 B)` against **1041 B** on a healthy tree. It needs a
      lower bound on the table size, falsified by shrinking the table.
      ✅ **DONE 2026-08-05 — D-ROMJUDGE.** 🔴 **A LOWER BOUND IS THE WRONG SHAPE**:
      one flipped byte moves the reported size **UP**, 1041 → **6140 B**, and a floor
      passes that ([[one-sided-bound-passes-a-runaway]] one slice later). The match
      is **EXACT** — size **and** `sha256`, pinned at `9bfcfb9`, a control that must
      keep matching. The walk is now **bounded** (an all-`$FF` image used to die of
      an `IndexError`, not a judgement), and the **`RELOC.rom` argument, which was
      read and never used**, became a real content check: the table's bytes must
      occur **0** times in the main image and **exactly 1** in the sub image — the
      gate's own "single-copy" name, finally measured.
      ⚠️ **AND IT STILL CANNOT CLOSE (a).** The table is **1041 of 32768 bytes
      (3.2 %)** at `$2CD2`, so a truncation at 50 % **or** 99 % leaves it intact and
      it reports its healthy 1041. Measured: **5 of 6** corrupted sub.roms passed the
      whole chain at rc 0 before this. The blind window for a short `sub.rom` is
      exactly the trailing pad length, **2324 B** — below that no gate anywhere can
      see it, which is why the length question is answered in `pad_rom`.
      🔴 **(b) ALSO FOUND A LIVE FALSE NEGATIVE IN (d)'s ONE-DAY-OLD FIX**:
      `subrom-inttest` on an **entirely-`$FF`** sub-ROM reads `delta = 57` — inside
      the new `1..64` band — and **PASSED**. `DELTA_MAX` was sized from a *partial*
      pad (255); a *total* pad reads 57. Fixed by asserting the **precondition** the
      harness already had and was discarding: **which capture path fired** (`bp` =
      the tenant returned, `net` = the 12 s safety net). Falsified both ways in one
      run each. Its comment's claim that the delta *"stays 0"* on that path is also
      wrong — a runaway `rst 38h` walks the stack and lands a **stack byte** in the
      result cell.
      ✅ **DONE 2026-08-05 — D-DSKJUDGE**,
      [`docs/spec-rom-gate-diskrom.md`](docs/spec-rom-gate-diskrom.md).
      🔴 **THE GATE IS DECLINED, MEASURED — and the filed claims were RIGHT but
      pointed at the wrong risk.** "No content-reading gate at all" is true of the
      HOST side (zero tools read `build/disk.rom`'s bytes and judge them; one reads
      all 16384 and only fingerprints them, `basic_probe_kwsweep.py:442`) and
      **irrelevant**, because `install-repack-machine.py` writes its absolute path
      into slot 3-1 and **four gate families execute every byte**. Corruption ×
      gate, six images: **6 of 6 caught**, every one by at least two gates — the
      inverse of D-ROMJUDGE's sub.rom result (5 of 6 passed at rc 0). `probe` is a
      DSKIO instrument (red on a flipped `$4010`, green on a flipped `$5006`);
      `bdos-acceptance` is the deep one (the only gate that catches a displaced
      `$5006` SNEXT, and the only one that catches a 43-byte truncation of
      `conout_emit_e`). **"68 of 74 `ds` sites" is confirmed exactly and is not a
      risk**: all 68 have positive slack (min **1 B**, max 3464 B) and a pad is
      SELF-ANCHORING — a body that grows shrinks the pad, and one that overruns
      gives a negative `ds` → 0 bytes → `pad_rom` EMPTY refusal. Falsified on the
      **disk** rule specifically, each knife run **twice**: short assembly → rc 2 +
      `Deleting file build/disk.rom` both times; negative `ds` at the tightest pad
      (`$4C29`, 1 B) → `pasmo` **exit 0**, **0 bytes**, refused both times. The one
      producer-blind edit — deleting a pad LINE, which displaces `snext` `$5006` →
      `$4FBB` while `pad_rom` still reports `16384 (exact)` — is caught by
      `bdos-acceptance` (10/12, the two dir-search captures MISALIGNED). Blind
      window for a short `disk.rom` = the trailing pad = **2 B** (vs sub.rom's
      2324); the image is full to its ceiling.
      🔴 **AND THE MEASUREMENT FOUND A LIVE FALSE NEGATIVE, in a gate nobody had
      named: `make fat-error-acceptance` reports `ALL PASS 8/8` on an entirely-`$00`
      `build/disk.rom`** — and on all five other corruptions. **Red in 0 of 6.** The
      battery's expected observable is an ERROR, so a dead disk subsystem satisfies
      every row for the wrong reason, and the directory check passes too (a machine
      that cannot write cannot create `NOSUCH.DAT`). ⚠️ **The probe's own comment
      already named this class and closed one INSTANCE of it** — D-APPMISS found it
      running with no disk mounted and fixed it by mounting one; but a dead disk
      ROM, an unhooked HPHYD and a `pageenv` regression all answer `load error` too.
      Fixed with the **PRECONDITION** the harness never had: a first batched row
      `FILES"A:HI.TXT"` that must print POSITIVE text (`HI` + `TXT`, not
      "no `load error`" — a broken tail returns SILENTLY, so absence-of-error is
      what a broken build reads as). Falsified both ways: real control on all-`$00`
      → **rc 2, "NOT MEASURED (precondition failed)"**; K2 (emission + call site
      intact, only `ctl_ok` gutted) → **rc 0, ALL PASS**, reproducing the defect
      exactly. **rc 2 ≠ rc 1**: the instrument was broken, not the disposition.
      Also DELETED: `tools/build_patches.py`'s `ensure_basic_rom()` +
      `_build_page1_retired()`, unreachable since the 2026-07-29 lean retirement —
      and it **would have failed if it ran**, padding a now-22510-byte
      `basic/main.asm` to the retired lean 16384. ROM-neutral, proved by hash (all
      six `build/*.rom` byte-identical to `fd58b3a`); dead-code seeds unmoved at
      **285**/**102**.
      ✅ **DONE 2026-08-06 — D-CITEJUDGE**,
      [`docs/spec-audit-citations-gate.md`](docs/spec-audit-citations-gate.md).
      The follow-up item this slice filed, and **two of its four claims were
      wrong.** 🔴 **The gate had been red for 144 commits, turned by `6f8ac0f`
      (2026-07-27), not by `40647bd`** — measured by walking *each commit's own
      tool over its own tree* across all **761** commits of the tool's life: red
      in **268 of 761 (35 %)**, five separate reds, the longest 90 commits, and
      **every green return came from a human happening to run it**. 🔴 **Check 1's
      precision over that whole life is 0 of 4** — all four findings it has ever
      produced are the same false positive, `byte[- ]?cop` matching across the
      boundary of a *qualified* `byte` ("a 65536-byte copy", "record/byte copy
      loop", "an independent 34-byte copy", "(18-byte copy)"). Two of them were
      already "fixed" once by REWORDING the prose (`4c14006`, 2026-07-04) and the
      class came straight back. So the filed *"(i) looks like a false positive"*
      is right and its reason is wrong: the distinction is not own-code-vs-
      reference (semantic, out of a regex's reach) but **lexical**, and one
      lookbehind decides it — `(?<![\w/-])byte[- ]?cop`, 99 → 96 token hits, 2 → 0
      affirmative, all six genuine-derivation forms still caught. 🔴 **And the
      denominator was blind to its own subject: 49 of 116 shipped first-party
      asm/inc files were scanned — the whole `sub/` tree and 30 shared `.inc`
      bodies were outside it**, not deliberately but because `sub/` was created a
      week *after* the scan list was last edited, and nothing recorded it. Widened
      to 116; check 4 also picks up `probes/**/*.asm` (0 findings). 🔴 **A second
      rule defect of the same shape, found by writing the fix:** the fixed
      45-line attestation window reported 9 files as unattested that carry a
      proper `CLEAN-ROOM:` line at lines 46–78 of their own header — measure the
      header BLOCK, not a magic 45, and 9 of 24 findings vanish without editing a
      file. 15 attestations written (2 of them into the GENERATORS, since the
      `.inc` would be overwritten by the next `make`). 🔴 **The filed *"the reason
      it is not in the corpus is not recorded anywhere"* is also wrong** — it is
      recorded twice, *"run it on demand / in CI"*, and both clauses are false:
      `ci.yml` did not run it and is `workflow_dispatch`-only. Now a step of
      `make basic-reloc` (0.27 s, beside `check_dead_code.py`) and of CI. The tool
      gained the two things that separate "clean tree" from "blind instrument",
      both **exit 2** not 1: a **rule self-test** pinned to the four historical
      false positives, and a per-target **file-count floor**. K2b/K5b are the
      controls — with either removed, a fully gutted rule and a 37-file-smaller
      sweep both report **exit 0 and "clean"**. ⚠️ K4 came back GREEN first and
      had not cut (that header attests TWICE, lines 56 and 61); ⚠️ and the knife
      script's `git checkout --` cleanup **restored from HEAD and destroyed the
      slice's own uncommitted tool edits**, so three knives silently scored the
      OLD tool. ROM-neutral, proved by hash (all four `build/*.rom` byte-identical
      to `0a9bd89`); dead-code seeds unmoved at **285**/**102** despite prose added
      to three files under `tools/`.
      ⚠️ **STILL OPEN, deliberately: pad-only damage stays invisible.** 9543 of
      `disk.rom`'s 16384 bytes (**58.2 %**) are `$00` pad in 252 runs; a corruption
      confined to them is caught by nothing. Closing it needs a whole-image digest,
      which would pin the ROM against every legitimate `disk/*.asm` change — every
      `ds`-anchored ROM here is *supposed* to move when its source moves.
      (c) ⚠️ **the three probe entry addresses stay HARDCODED** —
      `basic_probe_subrom_boot.py` (`$0040`), `basic_probe_subrom_inttest.py`
      (`$0049`), `basic_probe_graphics_floor.py` (`$0058`). They inject raw bytes
      into a bare machine deliberately, so deriving them from `sub/equates.inc`
      needs its own falsification. All three ARE now scored — note that the third
      is scored by **`graphics-floor-acceptance`**, NOT `graphics-acceptance`
      (which reaches the tenant through the symbolic main stub and is blind to a
      hardcoded probe address; D-P0BASE's K4a knife failed to cut until re-aimed).
      (d) 🔴 **`subrom-inttest` had a live FALSE NEGATIVE**: its assertion was
      `delta >= 1`, and with the CALSLT pointed at `$FF` pad it read
      `delta = 255` and **PASSED**. Its docstring claimed "there is no storm-or-hang
      path that still reports delta >= 1". FIXED here (`DELTA_MAX = 64`, measured
      28/28/28, falsified both ways) — recorded because it is the sixth filed
      justification checked in this arc and the sixth found wrong.
      🔴 **`tools/carve_scout.py` HAD THE SAME BLIND SPOT D-PINDATA FIXED IN ITS TWO
      SIBLINGS**, and it was a live wrong verdict, not a theoretical one: it graded
      `basic/playsvc.asm` **`page-0-tenant CLEAN`, 0 escapes** while
      `basic/playsvc.asm:59` does `ld hl,htimi_guard` (`$3C7E`, main low region) —
      the same shape as the `ld hl,zkey_hook` reference that made the review build a
      data-aware closure in the first place. It now reuses the SHIPPED pass
      (`build_datagraph`/`data_targets`) and a direct data escape downgrades the
      verdict to CONDITIONAL, because a table can move with the cluster and a HOOK
      ADDRESS cannot. Falsified both ways: playsvc CLEAN -> CONDITIONAL, and
      `parse_lineno` CLEAN -> CLEAN (the green control), three `NOT
      page-0-evictable` sets unchanged.
      🔴 **A KNIFE CAME BACK GREEN AND THE GREEN WAS THE FINDING.**
      `check_tenant_closure --page1` cannot see a sub tenant calling a **main-only**
      page-1 label (`call new_prog`): the closure grew 522 -> 523 so the edge WAS
      walked, but `new_prog` is absent from `build/sub.sym` so it is dropped at
      classification. **The ASSEMBLER is the gate for that case** (`ERROR: Symbol
      'new_prog' is undefined`), the same division of labour as `disk_putword` in §4.1
      above, arrived at from the other side and previously unwritten. A name that
      exists on BOTH sides (`call skip_spaces`) IS caught by the walk.
      ⚠️ **RANK 4 IS NOW COSTED AND THE TIER IS THIN.** A per-label closure sweep of
      all of page 1 leaves no other candidate that is both single-entry and free of
      interrupt/gate hazard: `play_service` (217 B) runs from H.TIMI (already rejected
      in `sub/beep.asm`'s header), `fat.asm`+`field.asm` (193 B) needs 9 stubs AND
      reaches a PAGE-1 tenant, `trap_return_check` (78 B) is measured in jiffies by
      T4/T5. The structural reason will not change: every statement-shaped entry
      reaches `eval` -> the float pack, every printing path reaches `pchar` -> CHPUT.
      ⚠️ **THE DEAD-CODE SWEEP'S SEED SET MOVES ON PROSE, AND `tools/` WAS TOO NARROW
      A FILING.** `external_names` scans `sub/` too, comments included: naming
      `fatprim_bounce` and `trap_return_check` in `sub/lineno.asm`'s header — while
      explaining why they were REJECTED — seeded both, and the main seed count went
      284 -> 285. Nothing masked (0 dead before and after). Widens the D-PINDATA
      filing below; still unfixed.
      Closed as answered: the 473 B duplication tax (**457 B contract-forced**), the
      split/ABI/three-gates question (**leave them alone** — the page-0 walk's vacuous
      pass is enforcement, not absent coverage), and merging the two regions (never on
      the table — `$4000` is a hardware contract).

      **Original entry, for context.**
      ✅ **S3 IS DONE, so this is UNBLOCKED**: the source now reads with no
      `IF ROM_BASE` wrappers obscuring which region anything is in.
      🟢 **FREE CARVE ALREADY IDENTIFIED, MEASURED, AND DELIBERATELY LEFT FOR THIS
      ITEM** (S3 had to stay byte-identical, so it could not be taken there):
      [`basic/vars.asm`](basic/vars.asm)'s `var_get_key` and `var_set_key` have
      **ZERO callers** anywhere in `basic/` or `sub/`, and `var_find` is called only
      by those two. They are the retired lean build's int-only fixed-pool scalar
      store; shipped scalars live in the contiguous chain the ARY sub-ROM tenant
      manages (arrays slice-4b). Their only remaining consumer was
      `tests/test_vars.py`, which S3 ported off them. **pasmo has been printing
      `Var var_get_key is never used` all along** — the finding was sitting in the
      build log, unread, which is its own lesson about warning noise (~230 lines of
      it). `VARTAB` / `VARENTSZ` / `VARSLOTS` in `sysvars.inc` are likewise read by
      nothing; `VAREND` must STAY (cells above it are placed relative to it), and its
      128-byte span `$E1C0..$E240` is freed RAM. **Measure the ROM saving before
      assuming it is large** — these are small routines, and page 1 is the 7 B wall.
      🔴 **THE FRAMING MEASUREMENT: the main ROM is jammed shut next to 7411 B of
      unused sub-ROM.** Measured at `4cdb69b`:

      | region | free |
      |---|---|
      | main low `$2812-$3FFF` | **0 B** (hard wall) |
      | main page 1 `$4000-$7FFF` | **7 B** |
      | sub-ROM page 0 `$0000-$3FFF` | **4054 B** |
      | sub-ROM page 1 `$4000-$7FFF` | **3357 B** |
      (⚠️ the sub-ROM pads with **`$FF`**, not `$00` — `ds $4000-$,$FF` /
      `ds $8000-$,$FF` in [`sub/sub.asm`](sub/sub.asm); a trailing-**zero** scan
      reports 0 B free and is WRONG.) **The structure is not full, it is
      UNBALANCED** — 22.6% of the sub image is unused while every main-ROM slice
      is costed against a 0 B wall.
      **What is NOT on the table: merging the two main regions.** The `$4000`
      boundary is a hardware contract, not an artifact — `CALSLT` switches only the
      called page, so a sub-ROM page-1 tenant runs with main page 1 switched OUT
      (callees must be `< $4000`) and a page-0 tenant runs with main page 0 switched
      OUT (callees must be `>= $4000`); `keytrap.asm` is low-region because the
      `$0038` ISR can fire while a page-1 tenant owns page 1. All three are already
      encoded in [`tools/check_tenant_closure.py`](tools/check_tenant_closure.py)'s
      walks, which are the FEASIBILITY ORACLE for this review — not the comments.
      **What IS on the table**, in scope order:
      (1) separate **CONTRACT-FORCED** placements from **PRESSURE-PLACED** ones.
      `main.asm`'s own comments repeatedly say a file "lands in the reclaimed low
      region rather than page 1 (page 1 is otherwise full to $7FFF)" — that is
      packing pressure, not a contract, and the two classes have never been
      separated systematically;
      (2) rank candidates by **bytes freed in the constrained region per resident
      byte spent**. ⚠️ **7411 B of headroom is NOT 7411 B of relief** — every
      eviction leaves a resident trampoline, and the arc history shows cost is
      dominated by SITING, not substance (`docs/`… D-FCH S-FCH-1: 43 -> 9 -> 5 B
      for the same fix). Every eviction so far was costed ONE AT A TIME (CIRCLE
      542 B, FAT shim +367 B, D-MSGENC, D-FCH); none against a known budget;
      ⚠️ **WEIGH DE-EVICTION EQUALLY (user, 2026-07-29).** The review must run in
      BOTH directions, and the reason is not symmetry-for-its-own-sake: a small
      tenant can cost MORE resident bytes than it saves. Its resident footprint is
      trampoline + dispatch-table entry + argument marshalling, which for a small
      routine can exceed the routine itself — so **the cost curve is not monotonic
      in size, and some existing tenants may be on the WRONG SIDE of it.**
      De-evicting those FREES main-ROM bytes (the trampoline goes) while shrinking
      the tenant count, the resident-ABI import list and the closure-gate surface —
      i.e. it is the one move that buys space and simplification together.
      Treat "should this be resident?" as the question for every routine on BOTH
      sides of the slot boundary, never as a one-way eviction hunt;
      (3) interrogate the split itself — whether the sub-ROM's page-0/page-1 tenant
      partition, the resident-ABI import (`tools/gen_resident_abi.py` ->
      `sub/basic-resident-abi.inc`) and the three closure gates could be unified or
      simplified.
      Output: a spec-ready candidate table with evidence per row. **No code changes
      in the review itself.**

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

- [x] **RETIRE THE LEAN 16 KB CART — ✅ DONE 2026-07-29 (S1 + S2 + S3).**
      [`docs/spec-lean-retire-s3-gates.md`](docs/spec-lean-retire-s3-gates.md).
      **S3 deleted all 284 `IF ROM_BASE` directives** (this entry's "311" was a grep
      count including 22 comment mentions and 7 in PROVENANCE.md), the `ROM_BASE`
      symbol, and `basic/main-reloc.asm`. `basic/main.asm` is the sole entry point and
      orgs at an unconditional `BASIC_ORG = $2812`; `$(ROM)` and its rule are gone, so
      `make build/basic.rom` no longer exists.
      ✅ **BYTE-IDENTICAL** across the whole change — `basic-reloc.rom`, `sub.rom`,
      `disk.rom` AND `zerobas-main-eu.rom`. Wall unchanged: **low 0 B, page 1 7 B.**
      🔴 **THE SUB-ROM DEFINED ITS OWN `ROM_BASE`.** `sub/sub.asm` set it to `$2812`
      and pulls in 20 shared `basic/*.inc` files, so a large share of the gates were
      evaluated TWICE. The brief scoped the edit to `basic/` and the gate to the main
      pair; **`build/sub.rom` had to join the byte-identity gate**, and falsifying that
      row (fold `sub/strheap.asm` the wrong way → `strheap_engine undefined`) is what
      proved it was instrumented rather than merely noted.
      🔴 **`make unit-test` WAS MEASURING THE RETIRED BUILD.** `msxtest.Machine`
      defaulted `rom_base=0x4000` — the lean org — so **18 of 54 test files** that
      built `basic/main.asm` without naming a base were asserting against LEAN, right
      through S2's "lean is no longer measured". Fixed the way S1 fixed probe machines:
      **`rom_base` is now MANDATORY**, named at all 74 call sites. Making it required
      found two consumers OUTSIDE `tests/` that no directory sweep would have —
      including **`probes/disk/bas_tokenise.py`, which tokenises the disk acceptance
      corpus's `.BAS` fixtures**, i.e. those fixtures were crunched by the LEAN
      tokeniser. `diskbasic-acceptance` still converges 34/34, now with the shipped one.
      8 of those tests could not just be re-pointed (they asserted on `STRTAB`, the
      fixed VARTAB pool, `[len][bytes]` descriptors, `ERRMARK` for `5/0`, or a
      sub-ROM-evicted routine) — **all 8 ported, 54/54 green.**
      🔴 **THE FALSIFICATION HARNESS WENT RED FOR THE WRONG REASON, TWICE**, both
      silently: `git checkout --` restored files to PRE-FOLD HEAD rather than to the
      folded tree, and `make build/basic-reloc.rom` is a **NO-OP FOLLOWER** target (the
      grouped-target workaround), so removing only the `.rom` left `@:` to run and the
      missing file read as "build failed". **A red falsification row reads as success**
      — the fix was a GREEN control row (comment-only edit → hash unchanged) plus making
      every row report its own reason.
      🔴 **F-R CAUGHT A SUCCESSOR THAT DOES NOT EXIST.** `basic_probe_readdata.py` was
      named from memory; the real successor is `tests/test_control_flow.py` — which this
      slice had to fix first. Retiring against a successor that was itself testing lean
      would have been a coverage loss dressed as a consolidation.
      Probes: **14 ported** to the repack machine, **6 retired** (`_data`, `_loops`,
      `_controlflow`, `_vdpio`, `_screen`, `_cload`) against verified successors. The S2
      margin hazard was **measured** (VG-8020 = 2, repack = 1) and applies only to
      VG-8020↔C-BIOS moves; no ported VRAM reader crosses that boundary, so no `_margin`
      fix was needed. The cassette corpus was ported but NOT end-to-end run (§6.1).
      Comment sweep (user chose targeted): the "388 lean mentions" figure was wrong —
      `grep -i lean` matches **"clean"**, and this tree says *clean-room* constantly.
      Real count **207**, swept to ~13 deliberate historical ones. `basic/PROVENANCE.md`
      got an APPENDED dated entry; its 7 in-history mentions are deliberately NOT
      rewritten (a provenance entry describes a date, a source comment describes the
      code beside it).
      ⚠️ **CARVE FOUND, NOT TAKEN:** `vars.asm`'s `var_get_key` / `var_set_key` have
      **ZERO callers**, and `var_find` is called only by those two — the retired build's
      int-only fixed-pool store, which pasmo has been reporting as unused all along.
      `VARTAB` / `VARENTSZ` / `VARSLOTS` are read by nothing. Left alone because S3 was
      byte-identical by contract; **folded into the ROM REGION STRUCTURE REVIEW below.**
      Lean's final hash, for the record:
      `defd6201b78bc922e3ba4db66134d2527c76ad9d81105440a6d667f12511be90` (16384 B). No
      tag, no frozen artifact — a future lean build is CHERRY-PICKED from the finished
      tree (user DIRECTION), not resurrected from that hash.

      **Original entry, for context.** It cannot be the
      charter target and has not been one for a long time: it excludes SEVEN
      whole source files (`str-engine`, `input`, `float`, `float-arith`,
      `arrays`, `keytrap`, `subromcall`) — so no strings, no `INPUT`, no floats,
      no arrays, no error codes, no KEY traps — costs **311 `IF ROM_BASE`
      gates** (`grep -rn 'IF ROM_BASE' basic/ | wc -l`; this entry said 276, it
      has drifted up by 35), and has **~68 free bytes** of its 16384. In an
      emulator both forms are equally easy to run and the repack build is
      strictly better.
      ✅ **S2 DONE 2026-07-29** — [`docs/spec-lean-retire-s2-switch.md`](docs/spec-lean-retire-s2-switch.md).
      **Lean is no longer built, shipped, or measured.** `zerobas-msx1.ips/.bps`
      are DELETED; the shipped BASIC is `zerobas-main-eu.ips/.bps` (user decision
      A1). `diskbasic-acceptance` IS the repack gate now (34/34) and
      `-repack` is an alias; `check_reloc.py`'s frozen-baseline check #4 and
      `LEAN_SHA256` are gone, **checks 1–3 and the `__MEAS_LOW_END`/
      `__MEAS_PAGE1_END` wall readout survive untouched** (falsified by
      corrupting `basic-reloc.rom` three ways, and the sym argument is now
      REQUIRED — an optional sym is how a wall readout silently stops printing).
      `make probe` runs `basic_probe_print.py --zb-machine` instead of the lean
      cart. `make all` no longer needs a C-BIOS checkout; `make release`
      regenerates the shipped pair.
      🔴 **MEASURED, and the source said otherwise:** a release machine with slot
      3-2 empty does not boot AT ALL (garbage screen, no prompt) — BASIC reaches
      its sub-ROM tenants during startup, so `--sub-rom` now defaults ON and a
      missing file is a hard error. The tenant map had read as "loses those verbs".
      ⚠️ **The lean build is now UNGATED** — `make build/basic.rom` still
      assembles for the ~20 historical `--cart` probes, but nothing asserts it.
      **S3 (next): delete the 311 `IF ROM_BASE` gates + the `ROM_BASE` machinery,
      collapse `main-reloc.asm` into `main.asm`, and port/retire that probe
      corpus.** Gate for it: `build/zerobas-main-eu.rom` byte-identical across the
      change.
      ⚠️ **S3 MUST STAY BYTE-IDENTICAL — do NOT fold any placement change into
      it.** Byte-identity is the strongest gate available for a 311-site mechanical
      edit, and moving even one routine destroys it. The structural rebalance is a
      SEPARATE item (see ROM REGION STRUCTURE REVIEW below), deliberately sequenced
      after S3 so it reads source with no `IF ROM_BASE` wrappers obscuring which
      region things are in.
      ✅ **S1 DONE 2026-07-29** — [`docs/spec-lean-retire-s1-explicit-machine.md`](docs/spec-lean-retire-s1-explicit-machine.md).
      Both gates now NAME their machine (`LEAN_MACHINE` / `REPACK_MACHINE`) and
      assert it with `--expect-build`, so the two can no longer collapse into one
      test; all 38 probe fallbacks are GONE (the machine is mandatory); the runner
      gained zerobas-side vacuity guards §3.1.3–§3.1.6. Retiring lean is now a
      two-line Makefile edit, not a hunt through 38 files. **It also found a live
      defect: [`disk_probe_format.py`](probes/disk/disk_probe_format.py) parsed
      `--machine` and threw it away, so CALL FORMAT had NEVER run on the repack
      build** — and the wiring guard passed it because the env-var name appeared
      in its source.
      ⚠️ **NOT A BLOCKER (dissolved by the DIRECTION below):**
      [`tools/check_reloc.py`](tools/check_reloc.py) proves the relocated image is
      a PURE RELOCATION by comparing the lean ROM against a frozen baseline. A
      DERIVED build needs no anti-drift proof, so this needs no replacement — but
      its other three checks and the `__MEAS_LOW_END`/`__MEAS_PAGE1_END` wall
      readout must survive, since every slice is costed against them.
      **DIRECTION (user, 2026-07-29): if a lean build is ever wanted again, CHERRY-
      PICK AND ASSEMBLE IT FROM THE FINISHED zerobas BUILD** rather than keeping a
      second build alive in parallel. This inverts the blocker above rather than
      solving it: the byte-identity baseline exists to prove a build that is
      CO-MAINTAINED never drifts, and a build that is DERIVED on demand does not
      need that proof at all — it is cut from the tree that is already gated. It
      also retires the 311 `IF ROM_BASE` gates as a *maintenance* cost rather than
      a *correctness* one, and it means findings like D-LINEMAX's lean `TOKBUF`
      overrun stop being defects-carried-forward: the derived build would inherit
      the fixed crunch, not the 96-byte one.
      Carry forward, do not fix: the lean crunch overruns `TOKBUF` via
      line-number references (`20 ONAGOTO1,1,1,…` — **57 characters** → 98 bytes
      into 96; 95 characters → 174, over the LIVE `VARTAB`; a variable set
      before it reads back 0). Measured, D-LINEMAX §2.2.

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

- [x] **`CLEAR`/`MAXFILES` inside a run do not suppress an armed `ON ERROR`
      handler** (reference: they do). Found 2026-07-29 while measuring S-FCH-2;
      **✅ FIXED the same day —
      [`docs/spec-basic-onelin-reset-scope.md`](docs/spec-basic-onelin-reset-scope.md).
      Net 0 BYTES** (the disarm MOVED out of `run_prog` into `vars_reset`);
      walls rebalanced low 6 → **0** B free, page 1 5 → **11** B free; lean
      byte-identical. 17 standing gate rows; three rejected builds assembled.
      **THE RULE, MEASURED (14 rows, each trigger unconfounded by an edit):** a
      handler is disarmed **exactly when the variable table is cleared** — `RUN`,
      `NEW`, `CLEAR` (direct-mode *and* in-run, so `MAXFILES`) and **every
      program EDIT**. `DIM`, string traffic, a plain direct statement, a
      `STOP`+`CONT` suspension and a `CLEAR` *before* the arm all keep it. That
      set is `vars_reset`'s five callers, 1:1 — which is why the zero lives
      there and not in `clear_vars` (a program edit never reaches `clear_vars`).
      🔴 **EVERY PREVIOUSLY-FILED ROW WAS CONFOUNDED FOR PLACEMENT** — each typed
      a program line BETWEEN the arm and the trigger, so "the EDIT disarmed it"
      and "`RUN`/`CLEAR` disarmed it" were indistinguishable. Armed LAST, with no
      edit in between: **`RUN` DOES disarm**, so this item's own warning that
      "`RUN` must not disarm" was false.
      🔴 **THE `ONELIN`-INVALIDATION-AT-RELINK MECHANISM THIS ITEM RECORDED IS
      WRONG.** It predicts that only an edit which MOVES the handler line
      disarms; the reference disarms on an **append that moves nothing**
      (`onelin_edit_append`), and on a same-length retype. The trigger is the
      EDIT, not the MOVE.
      🔴 **AND THE THREE `reset_scope_*` GATE ROWS WERE VACUOUS.** Their marker
      was the literal `R<LEAKED>`, which appears in each case's **own source
      echo**: the test read TRUE on every machine, in every build, since the day
      it landed. That is where the false "the reference DOES fire" claim in
      spec-basic-filechan-alloc.md §5d.5 came from — and that claim is what
      steered this item away from the variable-clear rule for a whole arc.
      **A wrong measurement is worse than none: it does not merely fail to
      inform, it actively STEERS.** All three now use the numeric marker and are
      oracle-locked. ⚠️ `NEW` still cannot be isolated (the retype it forces has
      already disarmed the handler) — unchanged, and now moot: `NEW` reaches
      `vars_reset` like everything else.
      Also closed: a **stale-pointer WILD BRANCH** — inserting a line before the
      erroring line moved the handler line, and zerobas followed its stale
      `ONELIN` into the moved text, reporting `syntax error in 4850`, a line that
      does not exist. Marker-wise that row AGREED with the reference while doing
      something far worse; it is now gated on the **abort line number**.
      `chancost-characterize`: 4 filed divergences → **1** (`err_badchan`,
      `mf_disarm`, `clr_disarm` all agree now).

- [x] **`CONT` that runs off the end of the program aborts with a nonexistent
      line number.** ✅ **FIXED 2026-07-29 —
      [`docs/spec-basic-cont-depth.md`](docs/spec-basic-cont-depth.md), 4 B
      (`ld sp,(SAVSTK)` at `ex_cont`), page 1 11 → 7 B free, lean
      byte-identical.** 8 standing `cont_*` rows in `abort-acceptance` (now
      31/31), **six of them "must not change"** — the fix DISCARDS a stack
      frame, so its risk is what else lived there, not whether the symptom
      goes away. Falsified twice: without the instruction `cont_falloff` is red,
      and with the one-character-different `ld (SAVSTK),sp` (anchor here rather
      than restore) it is **still** red. `10 STOP : 20 B=1 : 30 PRINT"…"` then `RUN`, `CONT` — the
      reference resumes, prints, and returns to `Ok`; zerobas prints, then
      reports `Illegal function call in 3346`. Found 2026-07-29 by D-ONELIN's
      `stop_cont` CONTROL (no `ON ERROR` anywhere — `ONELIN` is 0 throughout),
      and **verified PRE-EXISTING at `6ac2285`** against a parked pre-fix build.
      **✅ MECHANISM CHARACTERIZED 2026-07-29** (17-case battery, both machines,
      boot-per-case) — and it is the [[abort-chain-returns-into-caller]] class,
      a `ret` that only unwinds correctly at ONE depth:
      **`ex_cont` re-enters the run loop with a bare `jp rp_lp` from STATEMENT
      depth**, i.e. from inside the loop's own `call exec`, leaving a stale
      return frame beneath it. `dl_cmd` (the clean template) instead `jp rp_exec`s
      at REPL depth after `ld (SAVSTK),sp`, so ITS exit `ret` unwinds to the
      prompt. From `ex_cont`'s depth the exit `ret` lands back INSIDE the loop
      body, which then reads `ENDFLAG`:
      * exit via `END` -> `ENDFLAG`=1 -> the re-entry `ret`s again immediately.
        **Clean BY LUCK** (`x_cont_end` measured clean on both machines).
      * exit via the `$0000` link -> `ENDFLAG`=0 -> falls through to the
        next-line advance with `HL` still on the end marker -> parses garbage ->
        `Illegal function call in <the word after the marker>`.
      Controls that pin it: `x_run_tail` (plain `RUN`, clean) and `x_cont_goto`
      (a direct `GOTO` into the program, clean — dl_cmd's path is the one that
      works). ⚠️ A hypothesis that the `END` exit derails too, onto a benign
      byte, was **REFUTED by measurement**: `40 END:PRINT…` does NOT run its
      second statement after a `CONT` (`d_cont_after_end` agrees on both).
      Likely fix: `ld sp,(SAVSTK)` before the `jp rp_lp` (4 B, page 1) —
      `dl_cmd` sets `SAVSTK` for the CONT line itself, so it is fresh and is
      exactly the depth the loop's exit `ret` needs. **Not built; needs a spec
      + sign-off, and the two siblings below probably share it.**

- [x] **A stale `ONEFLG` survives the return to the REPL, so the NEXT error
      force-aborts instead of trapping.** Raised as S-FCH-2's open question by
      spec §5c; answered empirically 2026-07-29 **and ✅ FIXED the same day** —
      [`docs/spec-basic-oneflg-reset-scope.md`](docs/spec-basic-oneflg-reset-scope.md).
      **11 B (page 1 13 → 5 B free, low 9 → 6 B free), no carve, lean
      byte-identical.** The filed row was ONE of **six** divergent rows in a
      10-case battery; the fix closes all six.
      **The rule, measured both ways:** the reference clears `ONEFLG` on **any
      abort** — run-mode *and* direct-mode, even while a run is merely suspended
      — and on **any run TERMINATION** (`END`, running off the end); it does
      **NOT** clear on a `STOP`/Ctrl-STOP **SUSPENSION**, because `CONT` has to
      be able to resume *inside* the handler. Three sites: `fre_abort_low`
      (+3 B low), `ex_end` (+3 B), `rp_lp`'s `$0000`-link exit (+5 B — free,
      because `A` already holds 0 on that arm).
      🔴 **THE CHEAP FIX WAS 8 B AT ONE SITE AND IS THE WRONG FIX.** Clearing at
      the run-loop exit gated on `CONTVALID` reproduces every measured row — but
      only because zerobas's `END` leaves no CONT resume point, which is *itself*
      a divergence (see the new item below). A fix resting on a known bug
      regresses silently the day that bug is fixed. **Ask what the reference's
      RULE is, not which cheap predicate happens to fit today's rows.**
      🔴 **The over-clear guards are the load-bearing half of the gate.** Seven
      standing rows in `basic_probe_error_trap.py`; five say "must clear" and
      **two say "must NOT clear"** (`oneflg_keep`, `oneflg_suspend_resume`). A
      build with the rejected prompt-placement was assembled ON PURPOSE and
      passed all five and failed exactly those two. Each of the three sites was
      also deleted individually: **the site→row map is 1:1.**
      ⚠️ Round 1 of the battery scored a force-abort as a TRAP: the marker
      `PRINT"R<TRAP>"` matched its own **SOURCE ECHO**. Round 2's `PRINT"R<";1;">"`
      cannot collide (echo → `";1;"`, output → `1`).
      ⚠️ The first over-clear build **failed to assemble** (a 5 B insert pushed
      an unrelated `jr` out of range) **and the probe ran anyway, on the stale
      machine** — five red rows of pure noise. Chain build and probe with `&&`.

- [x] **ERR 21 `No RESUME` is never raised.** Found 2026-07-29 by the D-ONEFLG
      battery's c3b row, not aimed at; characterized 2026-07-29.
      **✅ FIXED 2026-07-31 as D-ERR21 —
      [`docs/spec-basic-err21-no-resume.md`](docs/spec-basic-err21-no-resume.md).**
      **+4 B page 1 (30 → 26 free), +57 B low region (80 → 23 free)** — both
      estimates exact to the byte, and no `jr` span broke this time.
      Gate **126/126** (`make error-trap-acceptance`, 24 new `e21_*` rows +
      `oneflg_falloff` upgraded from one zb-only row to a two-machine text
      differential), seven falsification builds.
      🔴 **THE FILED CHARACTERIZATION WAS WRONG IN TWO PLACES AND A THIRD DEFECT
      WAS HIDING BEHIND THE PLACEMENT QUESTION.**
      **(a)** The message and `ERL` name the **LAST EXECUTED LINE**, not the
      handler's — `in 110` with the handler at 100, `in 200` through
      `100 GOTO 200`. The filed `21 , 100` was taken on a program whose handler
      line WAS its last line, so the two readings were never discriminated.
      Falsification **F3 built the filed design** (`CURLINE := ONELIN`) and it
      prints `in 100` / `21 , 100` on every row — **the wrong implementation
      reproduces the filed measurement perfectly.**
      **(b)** The abort resume point is **NOT free from `ra_abort`**: `CONT`
      after this abort reprints NOTHING, so the point is the FALL-OFF position,
      not `SAVTXT`. The raiser records it itself, before it moves `CURLINE`.
      ⚠️ **F4 was caught by whole-screen occurrence COUNTS, not by the tail** —
      both tails were byte-identical to the want, because the re-printed marker
      lands after the `CONT`, outside the `RUN`-anchored tail.
      **(c)** D-ONEFLG **site C was causing a live defect nobody had measured**:
      a typed line ends by falling through `dir_line`'s own `$0000` link into
      this very exit, so a benign `PRINT 1` at a `Break in <handler>` prompt
      killed the handler context and the next `CONT` said `resume without error`.
      Deleting site C — which this slice does anyway — fixes it.
      ⚠️ `err_msgtab`'s entry 21 was a **HOLE**, not a working entry, so
      `ERROR 21` printed `unprintable error` too; wiring it is 0 B.
      🔴 **F6 CAME BACK GREEN AND THAT WAS THE FALSIFICATION'S FAULT.** It
      restored site C *after* the new `ONEFLG` test, where `A` is 0 by
      construction — a no-op. F6b restored its EFFECT on the arm that mattered
      and bit as designed. **A green falsification is a claim about the patch
      first and the code second.**
      ⚠️ `build/sub.rom` changes legitimately: the 57 B of low region shifts
      `vars_reset`, a resident-ABI address the sub-ROM links against.

- [x] **Probes streamed audio on every boot — `sound_driver null` had reached
      only ONE of 70 launch sites.** The 2026-07-30 fix landed in
      [`probes/disk/omsx_session.py`](probes/disk/omsx_session.py) alone; the
      other 69 — including [`probes/lib/omsx_repl.py`](probes/lib/omsx_repl.py),
      which EVERY BASIC acceptance gate boots through — still opened a real
      CoreAudio device and streamed. **✅ FIXED 2026-07-31, all 70.**
      **The denominator was the finding:** `renderer none` and the openMSX launch
      set coincided exactly (70 files reference `-machine`; 70 now set
      `sound_driver null`), so a single mechanical rule covered it — but nothing
      had ever counted the sites.
      **No probe needs a host sound driver, and the risky half of that is
      MEASURED, not argued:** PSG work reads the emulated chip via
      `debug read_block {PSG regs}` (`probes/lib/psgtrace.py`), and cassette
      recording writes the emulated cassette port — the same `CSAVE` produces a
      **byte-identical 128224-byte wav** under `sound_driver null` and `sdl`,
      decoding to the same tape bytes. Audio gates (sound/beep/play/play-trace)
      and the full standing suite are unchanged.
      ⚠️ NOT `mute`/`master_volume 0` — they silence the output and leave the
      driver churning. Convention now written down in
      [`probes/README.md`](probes/README.md) "Headless conventions".

- [x] ✅ **~~`fre_abort_low`'s header cites a `ret z` that no longer exists~~ —
      FIXED 2026-08-21 as D-RETZ, 0 ROM bytes, and the deliverable is the
      DENOMINATOR.** The conclusion was inverted, not the paragraph deleted: the
      depth argument is still true and still load-bearing, so only the
      instruction it names changed. `basic/arrays.asm` now says the exit is
      `jp cont_record`, a TAIL CALL whose own `ret` is the loop's exit `ret` at
      the identical depth.
      📏 **TWO SWEEPS KEYED ON OPPOSITE THINGS, AND THE SECOND FOUND WHAT THE
      FIRST COULD NOT.** Sweep A on the SYMBOL (`ret z` in a loop-exit context):
      **4 sites**, of which **2 stale** — this one and the identical sentence in
      [`docs/spec-basic-abort-depth.md`](docs/spec-basic-abort-depth.md)'s
      run-mode bullet; the third
      ([`docs/spec-basic-err21-no-resume.md`](docs/spec-basic-err21-no-resume.md)
      §8) was already correct, being the record that first noticed, and the
      fourth was this entry. Sweep B on the MECHANISM (`rp_lp`'s `$0000`-link
      exit, however spelled): **27 hits across ten files**, and it found a
      **THIRD** stale claim naming a different instruction —
      [`basic/sysvars.inc`](basic/sysvars.inc) still listed *"site C, rp_lp's
      `$0000`-link exit"* as a live `ONEFLG` clearing site, and D-ERR21 **deleted
      site C**. So: **3 stale of 27 mechanism hits; 2 of 4 symbol hits; sweep B
      found one sweep A structurally could not.**
      ⚠️ **NO EMULATOR ROW CAN SEE ANY OF THIS**, and saying so is part of the
      result rather than letting a green battery read as coverage. The gates that
      DO read these files are `make audit-citations` and `make deadcode`, both
      CLEAN, plus `unit-test` 59/59 and byte-identical ROMs.
      🔴 **AND THIS FINDING'S OWN LINE ANCHOR HAD DRIFTED** (`arrays.asm:111` →
      `:116`) with the file untouched — re-derived AFTER the last edit to that
      file, not before it. The original entry follows.
      ~~[`basic/arrays.asm`](basic/arrays.asm) — "the loop's own normal exit is a
      `ret` at that same depth (rp_lp's `ret z` on the `$0000` link)". D-CONTR
      replaced that `ret z` with `jp cont_record`, and D-ERR21 put a test above
      it. The DEPTH argument still holds (`cont_record`'s `ret` is the loop's
      exit `ret`); only the citation is stale. A comment that names a specific
      instruction is a CLAIM — cf. [[msgtab-bound-drift]].~~

- [x] **`CONT` after a plain `END` must continue.** Found 2026-07-29 by the
      D-ONEFLG battery's c7 row, not aimed at; characterized 2026-07-29;
      **✅ FIXED 2026-07-30 as D-CONTR —
      [`docs/spec-basic-cont-record.md`](docs/spec-basic-cont-record.md).**
      **+19 B, page 1 only (49 → 30 B free); low region untouched at 80 B.**
      Gate **49/49** (`make abort-acceptance`, 18 new rows, nine of them
      must-NOT-change), six falsification builds.
      **The rule, measured 34 boots deep both ways:** the run loop records a
      resume point at **every** run stop while in RUN mode — `STOP`/Ctrl-STOP,
      `END`, an untrapped abort, and running off the `$0000` link — and in
      DIRECT mode it records **nothing and invalidates nothing**. `CONT` never
      consumes the point; only `RUN`, `NEW` and an edit clear it. One shared
      `cont_record`; only the POSITION differs per stop.
      🔴 **THE FILED TITLE WAS THE SMALLEST PART OF IT.** Three things the item
      did not know, each pinned by a discriminating row: **(a)** `END` resumes
      **MID-LINE**, after its own token — `10 END:PRINT"[9]"` + `CONT` prints
      `[9]` *then* falls through to the next line. **(b)** An **untrapped abort
      records too**, at the FAILING STATEMENT (`SAVTXT`), not the line start —
      `CONT` re-raises the identical error, and `10 PRINT"[7]":B=ASC("")` does
      **not** reprint `[7]`. The forced (ERR 22) arm records as well.
      **(c)** `do_break`'s existing direct-mode gate was **ALSO wrong**: it
      *invalidated*. The reference KEEPS a live resume point across a typed
      `STOP`/`END`/error/line. The row that justified the old gate
      (`spec-basic-direct-ctrl.md` §5) was taken **with nothing live**, where
      invalidate and do-nothing are indistinguishable — it agreed for the wrong
      reason, and it stays green under the new rule.
      🔴 **F4 REFUTED THE SPEC'S OWN PREDICTION: the per-stop re-record ABSORBS
      the `CONT` consume.** Restoring the consume turned only `cont2_thrice`
      red, not `cont2_twice`/`cont2_err_twice` — the resumed run stops again and
      re-records, so a 2-deep battery would have scored dropping the consume as
      unnecessary. **Only the 3-deep row can see it.** ([[cont-depth-slice]]'s
      "what is ABSORBING the fault", one slice later.)
      🔴 **`make unit-test` went RED and the defect was in the TEST.**
      `test_poke.py`'s ERRMARK row read RAM *after* a call that reaches
      `ld sp,(SAVSTK)` with `SAVSTK`=0 in the zeroed harness — the tail `ret`
      popped `$0000` and the CPU ran away to msxtest's 2 M-step guard, which an
      `except: pass` swallowed. Re-sampled BOTH ways on ONE build: the old point
      reads `$DB` after the preceding cases and `$3A` alone; sampling AT
      `fre_abort_low` reads `$DD` with no runaway. Now trapped there, guard
      dropped. ⚠️ **Worth sweeping for siblings — see the new item below.**
      ⚠️ The first build **failed to assemble**: the 5 B added inside the run
      loop pushed `rp_goto`'s backward `jr rp_lp` past −128 (+1 B for a `jp`,
      the byte the estimate lacked). Build and probe were chained with `&&`, so
      unlike the D-ONEFLG incident nothing ran on a stale machine.
      Also retired: `probes/basic/basic_probe_cont.py` (wired into no target,
      `NameError` since the lean retirement, and one assertion now known wrong);
      its provenance citation in `basic/PROVENANCE.md` is corrected in place.

- [x] **Sweep `tests/` for rows that read RAM AFTER a runaway.** ✅ **DONE
      2026-07-31 — the class is EMPTY (0 of 5606 calls), so the deliverable is a
      permanent harness invariant instead of N row fixes.** Spec + all
      measurements: [`docs/spec-tests-runaway-sweep.md`](docs/spec-tests-runaway-sweep.md).
      0 ROM bytes; `tests/` only.
      🔴 **THE FILED RECIPE COULD NOT MEASURE THE CLASS.** It was a grep
      (`grep -n "except" tests/*.py`), but **a runaway does not have to raise**:
      wander into `PC=$FFFF` and it hits msxtest's sentinel, so `call()` returns
      *normally* — no exception, nothing to swallow, no `except` to grep for. So
      an instrument, not a pattern match: wrap `Z80.step` + `Machine.call` and
      record min/max SP per call (nested frames propagate, so the sub-ROM bridge
      cannot hide an inner excursion). Coverage is total — `grep "\.step(\|cpu\.pc *="`
      over `tests/test_*.py` finds **0** code sites, so every instruction the
      suite runs goes through `call()`.
      **DENOMINATOR, AS-RUN:** 54 files (53 execute Z80 at all;
      `test_msgenc.py` is a pure table reader), **5606 `Machine.call()`
      invocations, 0 SP-lost, 0 unbalanced returns, 0 exceptions.** The whole
      suite lives in `SP $F326…$F380` — a 90-byte excursion, 29 KB clear of the
      RAM floor — and **every** call returns with `exit_sp` exactly `$F380`. The
      `except` pass, for the record: 3 textual hits, **0 swallowing**. Exactly
      one test traps an abort funnel: the repaired poke row.
      🔴 **A DETECTOR WHOSE GREEN STATE IS "FOUND NOTHING" IS A CLAIM** — canary:
      the pre-fix poke row rebuilt synthetically gives `min_sp=0` + the 2 M
      runaway, so the detector cuts. **And it read `ERRMARK=$DD`, the value the
      old row asserted** — the wrong apparatus still reproduces the "right"
      answer ([[err21-no-resume-slice]] F3, in the test layer).
      **The fix:** an unconditional SP-band invariant in `msxtest.Machine.call`
      (`$8000 ≤ SP ≤ sp0`) raising `StackLost(RuntimeError)` that names
      `ld sp,(SAVSTK)` and the remedy, plus **new** `tests/test_harness_guard.py`
      — knife + GREEN control + the in-situ D-CONTR case. On the real path the
      failure moved from `runaway: 2000001 steps, PC=0xe1c6` (arbitrary, a
      symptom, *worth swallowing*) to `SP=0x0000 at PC=0x3d4a, step 325` —
      **6,154× earlier, at the `ld sp` itself**. `make unit-test` **55/55**,
      18.30 s vs an 18.16 s baseline (the per-step compare is free), per-file
      breakdown identical by NAME.
      🔴 **F2 REFUTED ITS OWN PREDICTION, AND ONLY THE ORACLE-LOCK COULD SEE IT.**
      Dropping the floor to `$0000` still turned R3 red — but at `SP=$FFFE`,
      337 steps: the runaway had **pushed at `SP=0` and wrapped**, tripping the
      *ceiling* 12 steps behind the floor. Because R3 asserts `sp == 0x0000` —
      the CAUSE — that read as RED. Had it asserted merely *"`StackLost` was
      raised"*, **F2 would have read GREEN and scored the floor as unnecessary**,
      shipping an invariant that caught the class late, by a wrapped SP, pointing
      at the wrong address. F4 also came back narrower than predicted: the
      `RuntimeError` base is **not** what makes a stack loss loud (`run.py` sees
      a nonzero exit either way) — it is what keeps the *rest of the file
      measuring* (3/3 cases reached vs dying on case 0).
      *Original filing (2026-07-30 by D-CONTR, not aimed at):*
      `test_poke.py`'s ERRMARK row had been
      asserting on *whatever a byte held after 2,000,000 steps of the CPU
      executing the ROM from an arbitrary entry point*, and it agreed for its
      whole life until an unrelated 19-byte page-1 shift moved where the runaway
      landed (`$DD` → `$DB`; and `$3A` when the same case runs alone on the same
      build). Fixed there by trapping the funnel and sampling at the moment the
      row is about.
      **The class:** any `msxtest` row that (a) calls a routine which can reach
      `ld sp,(SAVSTK)` — i.e. anything reaching `fre_abort_low`, `raise_error`'s
      abort arm, or the run loop — with `SAVSTK` unset in the zeroed harness,
      and (b) reads state AFTER the call rather than at a trap, and especially
      (c) wraps the call in `try/except: pass`. **The `except: pass` is the
      smell**: it converts "the CPU ran away" into "the row passed".
      Mechanical first pass: `grep -n "except" tests/*.py` for swallowed
      guards, and `grep -n "max_steps\|RuntimeError" tests/msxtest.py` for the
      guard itself. Each hit needs the same treatment: trap the routine the row
      is really about, sample there, and drop the guard so a real runaway is
      LOUD. See [`docs/spec-basic-cont-record.md`](docs/spec-basic-cont-record.md) §5.5.

- [x] ✅ **D-LOF — `LOF(#n)` reads −1 on a freshly-created OUTPUT channel.
      LANDED 2026-07-31, +6 B main page 1, 16/16 rows, falsified F1–F3.**
      Spec [`docs/spec-basic-lof-size-field.md`](docs/spec-basic-lof-size-field.md),
      characterization [`docs/lof-cf3300-characterization.md`](docs/lof-cf3300-characterization.md),
      gate `make lof-acceptance` (new). `make chancost-characterize` is now
      **39 cases / 0 filed** — its `KNOWN_DIVERGE` allowlist is EMPTY.
      🔴 **THE −1 WAS A STALE READING, NOT A SENTINEL, AND THE ROWS THAT PROVED
      IT WERE WRITTEN TO BE ABLE TO REFUTE THE FIX.** Open a known-size file,
      `CLOSE`, then create: zerobas printed **26** and **2048** — the previous
      file's size. `fat_find` writes `FAT_FILESIZE` only when a file is FOUND, so
      no create path wrote it at all and `LOF` returned whatever the previous
      tenant of the `FCH_STATE0` span left. `$FFFF` was just the cold-boot content
      of the cell; nothing ever stored it. Had either row also printed −1 the
      whole diagnosis would have been wrong.
      🔴 **THE DENOMINATOR WAS 3 SITES, NOT 1** — `fat_io_create` (OUTPUT, and
      APPEND-of-missing which jumps into it), `fat_rand_open`'s `fro_create`
      (RANDOM-of-missing), and `frnd_update_size` (a RANDOM `PUT` must GROW it).
      Only the first costs main ROM; the other two live in a sub-only body. F1–F3
      each deleted one edit and the other two rows stayed GREEN, so all three are
      independently load-bearing — and F3's `rand_put` fell to **0**, not −1,
      which is what showed (b) and (c) were separate facts.
      🔴 **THE ROW DESIGNED TO SEPARATE THE TWO CANDIDATE RULES FAILED; A
      DENOMINATOR ROW DID IT.** "0 on a new OUTPUT channel" is predicted equally
      by "the field is zeroed at OPEN" and by "`LOF` computes from the directory".
      `exist_out` (existing 26-byte file opened FOR OUTPUT) was written to split
      them and could not — the reference truncates the directory entry at OPEN
      too, so both rules predict 0 on both instruments. `rand_put` split them:
      the reference prints **`LOF` = 256 while its directory still holds 0**.
      🔴 **THE APPARATUS WAS WRONG THREE TIMES BEFORE THE SUBJECT WAS WRONG
      ONCE.** (1) At the chancost cadence the CF-3300 DROPPED keystrokes after
      any disk-busy line — `PRINT LOF(1)` arrived as `PRO)` and earned a
      completely real `Syntax error`, reported as two reference divergences; at
      9.0 s zerobas began DOUBLING the first character instead. (2) The echo guard
      written to catch that flagged **10 of 16 rows with perfect screens**: the
      name table is 32 cells but Disk BASIC boots SCREEN 1 at `linlen=$1d` = 29,
      so long lines WRAP. (3) Slicing rows to `linlen` was wrong too — the
      reference indents SCREEN 1 by a left margin of **2**. It is right only now
      that it assumes no geometry at all. **And the version that "worked" still
      passed a mangled row**: with whitespace squeezed out, `ZBPPRINT LOF(1)`
      *contains* `PRINTLOF(1)` — **a guard against DROPPED text is not a guard
      against INSERTED text.** It is prompt-anchored now, and was falsified RED on
      both bad captures and GREEN on five clean ones before being believed.
      A `MANGLED` row is fatal with or without `--gate`: two mangled sides compare
      equal and would otherwise print `agree`.

- [x] **✅ D-APPMISS — `OPEN … FOR APPEND` on a MISSING file REFUSES (was: created
      it), −2 B.** LANDED 2026-07-31,
      [`docs/spec-basic-append-missing-refuse.md`](docs/spec-basic-append-missing-refuse.md).
      One instruction: [`basic/fat.asm`](basic/fat.asm)'s `jp c,fat_io_create` →
      `ret c`, so a `fat_find` miss falls to `do_open`'s `oo_fail` → `load_error`
      exactly as `OPEN … FOR INPUT` of a missing file already did. **Main page 1
      20 → 22 B free**, low unchanged at 23 B; dead-code 0/0 both builds.
      `lof-acceptance` **18 cases, 0 unfiled** with `append_new` AGREEING on BOTH
      instruments and its `KNOWN_DIVERGE` entry DELETED; `fat-error-acceptance`
      **8/8 + directory check**.
      🔴 **THE ERROR CLASS WAS NOT THE ONE THE ITEM ASKED ME TO CONFIRM.** The
      filed text said to confirm `oo_fail`/`load_error` yields `File not found`.
      Traced, then measured: it yields zerobas's **`load error`** — and that is
      CORRECT, because `load error` is zerobas's pinned rendering of the whole
      file/channel family (PROVENANCE §74) and is precisely what the INPUT
      sibling already raises. The right question was not "is it `File not found`"
      but **"is it the SAME class as `open-missing`"**, which is a gate row, not
      an inspection.
      🔴 **THE ROW ADDED TO PROVE THE FIX WORKED FOUND A DIFFERENT DEFECT ONE
      LAYER DOWN.** `append_new_wr` (`PRINT #1,"X"` after the refused OPEN, no
      `LOF` typed) exists because `append_new` reads the LAST error on screen and
      so reads `File not open` from its own trailing `LOF` **whatever OPEN did** —
      it would have AGREED even if OPEN had raised `syntax error`. The new row
      showed `PRINT #` into an unopened channel raises `load error` where the
      reference raises ERR 59, while `lof_closed` proves zerobas HAS a real
      trappable ERR 59. Filed below as its own item, with `ctl_prwr_closed` (the
      same `PRINT #` with NO `OPEN` typed at all) as the ATTRIBUTION control, so
      "it was already like that" is measured rather than asserted.
      🔴 **`None` MEANT TWO OPPOSITE THINGS AND THE ROW COULD NOT FAIL.** Its
      first version left `load error` unclassified, so it read `None` pre-fix
      (the write was SILENTLY ACCEPTED) *and* `None` post-fix (the write was
      REFUSED). A regression back to silent acceptance would not have moved the
      value. Fixed by adding a `LOADERR` class — reversing this spec's own §5c
      sign-off answer, which was right for `append_new` and wrong for a row that
      did not exist when the question was asked.
      🔴 **THE SECOND INSTRUMENT WAS MEASURED, PRINTED AND NEVER COMPARED.** The
      `dir` column had been in `diskbasic_probe_lof.py` since D-LOF, but the
      verdict came from the LOF value alone — so "the reference makes NO directory
      entry", the central claim here, could not fail the gate. Both columns are in
      the verdict now (`DIR_EXPECT` / `DIR_DIVERGE`). It cut immediately:
      `rand_put` has AGREEING LOF columns and separates only on `dir` (filed
      below) — a row the old single-column verdict called `agree`.
      🔴 **AND THE GATE I ADDED FOR THE CLASS WAS GREEN OVER A PROVABLY BROKEN
      SUBJECT.** `fat-error-acceptance` ran with **NO DISK IN THE DRIVE**, so all
      seven pre-existing cases failed in `fat_mount` and never reached `fat_find`
      at all — the docstring claimed the find miss, the probe measured the mount
      miss, and the two are indistinguishable by their answer (`load error`
      either way). Caught ONLY by the knife: with the fix reverted, `append-missing`
      stayed **GREEN**. It now mounts a **/tmp COPY** of `test720.dsk` — mandatory,
      because a build where APPEND still creates actually WRITES `NOSUCH.DAT` into
      the image (measured) — and parses that image afterwards, so a build that
      printed `load error` and created the entry anyway cannot pass.
      Falsification RUN, not planned: with `ret c` reverted, `append_new` and
      `append_new_wr` go RED on BOTH instruments and `append-missing` goes RED on
      BOTH, while `append_exist` (26/26), `roundtrip`, `disk_probe_append.py`'s
      byte-identical Ctrl-Z round trip and the other seven fat-error rows stay
      GREEN. The knife was verified to CUT: `fia_walk` $6361↔$6363 and page-1 free
      22↔20 B moved with it.

- [x] ✅ **`PRINT#`/`INPUT#`/`LINE INPUT#` on a channel that is NOT OPEN raise a
      trappable ERR 59, not `load error`.** LANDED 2026-07-31, D-NOTOPEN,
      [`docs/spec-basic-chan-notopen-err59.md`](docs/spec-basic-chan-notopen-err59.md).
      **−8 B, main page 1 22 → 30 B free**, low unchanged at 23 B. Found
      2026-07-31 by D-APPMISS's `append_new_wr` row, not aimed at.
      🔴 **THE DEFECT WAS A HAND-INLINED COPY OF AN EXISTING ROUTINE WITH ONE
      INSTRUCTION MISSING.** `fch_mode_class` (was `ev_chan_hasfile`,
      [`basic/expr.asm`](basic/expr.asm)) already reads `FCH_MODES[E]` and raises
      ERR 59 when it is 0 — that is how `LOF(1)` on a closed channel already
      AGREED with the reference. `ex_print` and `input_common` had each copied its
      array read inline and **omitted the `or a`**, so a not-open channel matched
      no device mode, fell into the disk arm and derailed to `load_error`. So the
      fix was to DELETE the copies and `call` the original: two hunks, no new code
      path, and 4 bytes of page 1 back at each site.
      **Trappability was in scope and is the bigger half:** `load_error` is a
      `ret`-based print path that CONTINUES the program, so an armed
      `ON ERROR GOTO` never saw it. Measured under a handler that prints `ERR`
      (where `0` means "nothing was raised", keeping trapped / not-trapped /
      nothing-happened three distinct readings): reference **59**, zerobas
      `load error`; now **59 on both**.
      🔴 **THE PLANNED KNIFE NAMED TWO WITNESSES THAT COULD NOT MOVE.** The spec
      said `ex_print` and `input_common` must shift under the falsification. Both
      labels sit BEFORE the edited bytes and are invariant either way — a knife
      that silently failed to apply would still have passed two of three "cut
      verified" checks. Only `__MEAS_PAGE1_END` ($7FE2 ↔ $7FEA) and the page-1
      free number carried the cut. ⚠️ **A cut witness must be DOWNSTREAM of the
      edit;** "the addresses moved" is evidence only when they COULD have moved.
      Falsification RUN on the verified cut: `append_new_wr`, `ctl_prwr_closed`,
      `closed_input`, `closed_lineinp`, `trap_print_closed`, `trap_input_closed`
      all RED, while `trap_lof_closed` (59/59), `lof_closed`, `ctl_syntax`,
      `append_exist` 26/26, `roundtrip` 8/8 and the three filed-divergence rows
      stayed GREEN, 0 mangled.
      Gate: `diskbasic_probe_lof.py` 18 → **26 cases**; `KNOWN_DIVERGE`'s
      `append_new_wr` + `ctl_prwr_closed` entries **DELETED, not updated**, and
      replaced by three rows for the sites deliberately LEFT (below), so the list
      stays a control that must keep matching rather than an empty box.

- [x] ✅ **`GET`/`PUT`/`FIELD`/`INPUT$(n,#f)` answer the reference on the WHOLE
      channel-mode grid, not just the not-open column.** LANDED 2026-07-31,
      D-NOTOPEN2, [`docs/spec-basic-gpfi-notopen-err59.md`](docs/spec-basic-gpfi-notopen-err59.md).
      **Net −19 B: page 1 30 → 49 B free, low UNCHANGED at 23 B.**
      Filed as "these four answer `Syntax error`, the reference answers ERR 59";
      the filed measurement was the not-open COLUMN of a grid that turned out to
      have **five** reference codes.

      | `FCH_MODES` | `GET`/`PUT` | `FIELD` | `INPUT$` |
      |---|---|---|---|
      | 0 not open | **59** | **59** | **59** |
      | 1/2/3 disk, not RANDOM | **61** | **61** | **55** |
      | 4 RANDOM | *(works)* | *(works)* | **61** |
      | 5/6 `LPT:`/`CRT:` | **58** | **5** | **55** |

      🔴 **MEASURING THE NEIGHBOUR CHANGED THE ANSWER TWICE, AND THE SECOND TIME
      WAS AFTER I HAD ALREADY COSTED THE SLICE.** Battery 1 sampled modes 0/1/2/4
      and read two new codes (61, 55); I costed the sweep against that and called
      it unaffordable. Battery 2 added modes **3/5/6** — the ones nobody had typed —
      and the answer became five codes. ⚠️ **A grid sampled at three of its seven
      rows is not a denominator**, and the rows that were missing are exactly the
      ones that carried the exceptions (`LPT:` answers **58** to `GET` but **5** to
      `FIELD`; `INPUT$` is **61** on RANDOM and **55** on everything else).
      🔴 **`FIELD` ON A SEQUENTIAL CHANNEL WAS ACCEPTED SILENTLY** — the row read
      `0`, *nothing raised*, where the reference raises 61. Nobody was looking for
      it; it is a missing check, not a wrong code, and it is the severe half.
      🔴 **"IT DOES NOT FIT" WAS A CLAIM ABOUT TODAY'S BUDGET, NOT ABOUT THE
      CHANGE.** Costed at ~86 B against 53 B free, I proposed dropping to the
      not-open column. The override was right: `tools/clone_scout.py` found the
      funding in one run, in the same file. **The carve was −107 B:**
      `oo_parse_as_chan` — the `AS [#]n` clause hand-inlined **VERBATIM at THREE**
      OPEN arms (disk, `LPT:`/`CRT:`, `CAS:`), 47 identical bytes each (−84 B) —
      and `fch_modes_ptr`, the `&FCH_MODES[ch]` index hand-inlined at **TEN** sites
      (−23 B). ⚠️ Same shape as D-NOTOPEN's defect, three times over: **when a
      fragment appears at N sites, N is never the number you first counted.**
      ⚠️ `fch_modes_ptr` uses the 8-bit page-local form deliberately — the obvious
      `add hl,de` version clobbers DE, and TWO callers read `E` after the index.
      That version assembles clean and breaks `CLOSE` on a device channel.
      Placement: ERR 55/58/61 cost 72 B, and the low region had 23 B — so
      `rerr_sparse`'s tail became `jp rerr_sparse2` (**a 0-byte change to the low
      region**) and all 72 B landed in page 1, at the tail of the LAST include
      (inserting mid-page-1 breaks dense forward `jr`s — pasmo rejects it).
      Gate: `diskbasic_probe_lof.py` 26 → **41 cases**; `KNOWN_DIVERGE`'s
      `closed_get` + `closed_field` entries **DELETED, not updated**, leaving
      **exactly one** entry (`closed_ch2`, the ERR 52 item). The two rows that earn
      their keep are `wm_lpt_get`/`wm_lpt_fld` (same channel, 58 vs 5 — a fix that
      collapsed "device → one code" goes red on exactly one) and
      `wm_rnd_inpd`/`wm_out_inpd` (61 vs 55, `INPUT$`'s two rules). Plus two GREEN
      controls, `ok_in_inpd` and `ok_rnd_get`, both `0`/`0`: without them a fix
      that raised unconditionally would have turned every other new row green.
      ⚠️ APPARATUS: battery 2's first run read the zb column as **entirely `None`**.
      `rm -rf build && make basic-reloc` rebuilds neither `build/disk.rom` nor
      `build/zerobas-main-eu.rom`, and the machine XML names both by absolute path,
      so the house-rule clean wall measurement leaves the installed machine
      dangling. Caught only by `ctl_syntax`. **Clean measure, THEN
      `make repack-machine`, THEN probe.**

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

- [x] ✅ **A REJECTED channel number answers the reference's error class, on every
      verb.** LANDED 2026-07-31, D-BADFNUM,
      [`docs/spec-basic-badfnum-channel-class.md`](docs/spec-basic-badfnum-channel-class.md).
      **Net −14 B: page 1 49 → 63 B free, low UNCHANGED at 23 B.**
      Filed as three rows (`PRINT #2`, `INPUT #2`, `PRINT #0`) with the warning
      that they do not generalise. The warning was right and it was the smaller
      half: `fch_valid` had **NINE call sites routing to SIX dispositions**, so the
      filed rows walked 2 sites and 1 disposition. Swept as **12 channel-taking
      verbs × 6 channel classes**; **63 of the first 72 cells diverged.**

      The reference rule, measured, is ONE rule with two exceptions:

      | channel | reference | exceptions |
      |---|---|---|
      | `A$` (string) | **ERR 13** `Type mismatch` | none |
      | `#256` / `#-1` | **ERR 5** `Illegal function call` | none |
      | `#0` | **ERR 59** `File not OPEN` | `CLOSE #0` no-ops; `OPEN … AS #0` is **52** |
      | `1 … MAXF` | proceeds | |
      | `> MAXF` | **ERR 52** `Bad file number` | none |

      🔴 **THE TWO WORST CELLS WERE NOT IN THE FILED ITEM.** `EOF`/`LOF` on a
      rejected channel **raised nothing and returned a number** — `PRINT LOF(0)`
      printed ` 0`, an answer, not an error, and an armed handler never ran. And
      `CLOSE #2`/`#16`/`#256`/`#-1` **silently no-opped**. Same shape as
      D-NOTOPEN2's silently-accepted `FIELD`, one layer earlier.
      🔴 **THE SWEEP REFUTED MY OWN SAMPLE, TWICE.** Battery 1 took the last three
      classes on `PRINT#`/`GET`/`LOF`, read a uniform rule and looked settled — but
      it excluded `OPEN`, the one verb already known to differ at `#0`, and
      `OPEN … AS #256` is **ERR 5** on the reference where zerobas said 52.
      🔴 **AND THEN I MADE THE SAME MISTAKE INSIDE THE SPEC THAT ARGUES AGAINST
      IT.** The type-mismatch cells were written up as three "edge cells" rather
      than as a sixth CLASS with twelve rows. The signed-off design shipped a
      REGRESSION on them (a type mismatch hard-zeroes the channel to 0, so
      `fch_check`'s ERR 59 got there first), and the row that caught it —
      `PRINT LOF(A$)` — was in the gate **only because it already AGREED**.
      Sweeping that column found the reference uniform at `Type mismatch` and
      zerobas wrong on **8 of 12**, only two of them regressions. Cost: +7 B.
      ⚠️ **A CELL PINNED AS A CONTROL BECAUSE IT AGREES IS WHAT FINDS THE AXIS YOU
      DID NOT KNOW YOU WERE SAMPLING.**
      🔴 **A THIRD PROBE HAD ENCODED THE OLD BUG AS AN ORACLE.**
      `disk_probe_closelist.py` ran `CLOSE#1,#2,#3` at `MAXFILES=1` and its
      docstring called the out-of-range channels a "lenient no-op" — a zerobas-only
      claim with no reference column. Typed on the CF-3300: it answers **ERR 52**,
      **after flushing #1** (the directory column proves the flush; a screen
      reading would not). `5 MAXFILES=3` added, so the probe still tests the LIST
      PARSER without resting on a leniency the reference lacks. The §7 blast-radius
      grep could not have found it — the channel is only out of range if you
      already know `MAXF`.
      Fix: the nine sites (78 B) became one `fch_check` with two extra entry points
      for `CLOSE`'s and `OPEN`'s channel-0 exceptions (38 B + 35 B), and
      `fch_valid` is DELETED (−9 B). §6 also took a **0-byte** change —
      `eval_chan`'s tail `jp check_fperr_only` → `jp check_expr_errors` — whose
      independent value is proven by knife K5 and nothing else.
      Gate: NEW `probes/disk/diskbasic_probe_badfnum.py`, `make badfnum-acceptance`,
      **93 cases, 0 unfiled / 0 oracle drift / 0 mangled / 0 without an oracle
      lock.** `diskbasic_probe_lof.py`'s `closed_ch2` entry **DELETED, not
      updated**, leaving `KNOWN_DIVERGE` **EMPTY — asserted in words, not left as a
      dict with no lines in it.** Six knives RUN: K1/K2/K3/K4/K5 each red on their
      own rows with every control green (K1's four rows go red in four DIFFERENT
      ways; K5 leaves exactly the four `eval_chan` verbs green), and K0 — aimed at
      the spec's own `FCH_MODE` justification — **held**. ⚠️ K0's first cut read
      `DIR=7` on subject AND control and looked like a pass; both had fallen into
      their own handler (`RESUME without error`), so it could not separate "the
      trap fired and the write survived" from "line 20 did nothing".

- [x] ✅ **A RANDOM `PUT` stamps the on-disk directory size immediately — and the
      reference stamps it at `CLOSE`, to the SAME value.** MEASURED AND DECIDED
      2026-07-31, D-RNDDIR,
      [`docs/spec-basic-randput-dir-stamp.md`](docs/spec-basic-randput-dir-stamp.md).
      **Zero ROM bytes: apparatus + documentation, which is what the item asked
      for.** MSX-DOS 1 has no subdirectories — "the directory" throughout is the
      FAT12 **root** directory table, and the reading is the size field at offset
      28 of the file's 32-byte entry.

      🔴 **THE FILED SENTENCE WAS NOT LICENSED BY THE FILED MEASUREMENT.**
      `rand_put` exits with the channel STILL OPEN, so `ref dir = 0` only ever
      meant *"has not stamped it YET"* — **nobody had typed a `CLOSE`.** Three
      worlds reproduced that row identically (timing only / different values /
      never stamps). Four new rows separate them:

      | row | ref LOF | ref dir | zb LOF | zb dir | |
      |---|---|---|---|---|---|
      | `rnd_put_cl` | `File not open` | **256** | `File not open` | 256 | agree |
      | `rnd_put_rt` | **256** | 256 | 256 | 256 | agree |
      | `rnd_put_len` | **16** | 0 | 16 | 16 | diverges (`dir`) |
      | `rnd_put_big` | 2048 | 2048 | 2048 | 2048 | agree |

      The reference stamps at `CLOSE` with the same value, and the **round trip
      agrees**, so no BASIC program can observe the difference. It is a *when*,
      not a *what*. zerobas's `fat_rand_put` tails into `jp fat_dir_update`
      ([`basic/randio-body.inc:373`](basic/randio-body.inc:373)) and stamps on
      every `PUT`; the reference defers to `CLOSE`.
      🔴 **AND THE RULE ITSELF HAD BEEN AGREEING FOR TWO REASONS AT ONCE.** The
      characterization's `recno × reclen` rested on the single **256** — but
      `OPEN … AS #1` defaults reclen to 256, so `1 × 256 = 256` *and* a 256-byte
      sector is 256. `LEN=16` reads **16**: the formula holds, sector-granularity
      is refuted, and the number that had "confirmed" it could not tell them
      apart. `rnd_put_big` puts a 256-byte record into 2048-byte `TEST.BIN` and
      reads 2048 in all four columns — **no truncation, no data loss**. ⚠️ `max()`
      is pinned by the PAIR (`rand_put` grows 0 → 256, `rnd_put_big` does not
      shrink), by neither row alone.
      Decided per the spec's pre-committed §5(A): at a 23 B low wall a difference
      no program can observe buys no ROM bytes. `DIR_DIVERGE` therefore keeps
      `rand_put` and gains `rnd_put_len`, **rewritten from "filed, open" to
      "decided, permanent" with the round-trip rows named as the evidence** —
      the one entry in either list that is not an unbuilt item. ⚠️ Growing an
      allowlist is allowed only loudly: `rnd_put_len` is load-bearing, it is what
      shows the early stamp follows `recno × reclen` and not the sector size.
      Gate: `make lof-acceptance` **41 → 45 cases, 0 unfiled / 0 oracle drift /
      0 mangled**; `KNOWN_DIVERGE` still EMPTY. K1 CUT (a forced-wrong
      `DIR_EXPECT` reddens that row ALONE, so the `dir` column is live on the new
      rows and not merely in principle); K2 PASS (`rnd_put_cl`'s trailing
      `File not open` is the witness that the `CLOSE` actually ran — a row whose
      only reading is `dir` cannot tell "stamped 0" from "the line never
      arrived").
      ⚠️ **INTERMITTENT ORACLE DRIFT — SECOND SIGHTING 2026-08-05 (D-PINDATA
      corpus), AND THE DIAGNOSTIC WAS DESTROYED.** The run reported
      `45 cases, 0 unfiled divergence(s), 1 oracle drift(s), 0 mangled` and exited
      non-zero. **Four immediately following runs were all clean** (0 drifts,
      rc 0). Sighting 1 was `wm_app_put` (recorded 61, live `None`) during
      D-LATCH's corpus, then five clean. 🔴 **I cannot name the row this time: the
      gate was run through `| tail -6`, and the `ORACLE DRIFT (recorded …)` line
      is in the BODY.** ⇒ **a gate with a known intermittent must be captured in
      FULL, never tailed** — a rare finding has exactly one copy. Still a flake,
      still not written off; the next sighting needs the whole log.

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

- [x] ✅ **`diskbasic_probe_chancost.py` IS ECHO-GUARDED — LANDED 2026-07-31,
      39/39, falsified both ways.** Apparatus only, **0 ROM bytes**, walls
      UNCHANGED (low 23 B, page 1 63 B — no `basic/` or `sub/` file touched).
      Spec [`docs/spec-probe-chancost-echo-guard.md`](docs/spec-probe-chancost-echo-guard.md),
      results [`docs/chancost-cf3300-characterization.md`](docs/chancost-cf3300-characterization.md) §0.1.
      `echo_missing` + the per-side prompt (`""` ref / `"ZB"` zb) ported from
      [`diskbasic_probe_lof.py`](probes/disk/diskbasic_probe_lof.py), plus a
      `--line-delay` knob (default **4.5**, unchanged) so the guard can be shown
      to cut.

      🔴 **THE FILED REASON WAS THE WEAKER ONE.** The item said a mangled line
      would read as an `FRE(0)` finding. What mangling actually produces is a
      **`Syntax error`** — which is what **`ctl_syntax`, this probe's own harness
      control, is recorded as expecting.** A mangled `ctl_syntax` row reads
      `SYNTAX`, matches its oracle, compares equal across the machines and prints
      **`agree`**. ⚠️ **The control that proves the harness is typing fails toward
      "pass" when the harness stops typing** — it cannot measure its own class,
      the same shape as the filed grep in [[test-reads-ram-after-runaway]].
      Measured, not argued: K1's mangled rows land on `SYNTAX` on BOTH machines.
      🔴 **AND A MANGLED ROW WOULD HAVE PRINTED A HEADLINE.** The slope, the
      ceiling and `HEADLINE: reference charges 267 B per channel` are derived from
      the `mf*` ladder. `MANGLED` therefore **suppresses** the derivation rather
      than being reported beside it — a slope computed from a ladder that never
      received `MAXFILES=8` is a number the run never measured. Ordering is
      load-bearing twice over: `MANGLED` is checked BEFORE the oracle comparison,
      or a mangled *reference* row reports as `ORACLE DRIFT` and blames the
      CF-3300 for the typing.
      Falsified both halves. **K1 CUT** — the same three disk-touching cases at
      `--line-delay 3.1` go **3/3 MANGLED, exit 3**, reproducing D-LOF's failure
      mode inside this probe: `PRINT LOF(1)` arrives as **`RIT OF1)`** and
      `OPEN "ZQ.DAT" FOR OUTPUT AS #1` as **`PE "Q.AT FR UTUTAS#1`**, each earning
      a completely real `Syntax error`, with zerobas mangling in parallel — **both
      sides `SYNTAX`, i.e. EQUAL.** Control: the **identical command with the one
      flag removed** → exit 0, 0/0, 26/26, 23163/14799. **K2 8/8** on synthetic
      screens: a doubled-character row (`ZBPPRINT FRE(0)`) is RED (a substring
      test passes it — a guard against DROPPED text is not one against INSERTED
      text), while a clean row and a **wrapped** reference echo at margin 2 *and*
      margin 1 are GREEN, and a scrolled-off first line is RED. The wrap is
      confirmed on a REAL capture too: `err_badchan`'s 32-char line 30 wraps on
      the reference and passes.
      🔴 **AND THE NEW GATE IMMEDIATELY CAUGHT ONE MORE NON-READING WEARING A
      READING'S FACE — beyond the signed-off scope, fixed here rather than
      filed.** A full run came back `lof_new` ref = `None` → **`ORACLE DRIFT`**;
      re-run, a clean **0** on a perfect screen. The guard had not fired because
      `run_case`'s **TIMEOUT** and **NO CAPTURE** paths return BEFORE it, both
      returning `None` — the same value a clean screen with no number on it reads
      as. ⚠️ **A sentinel that also means "no reading" is not a measurement**: a
      run that never finished was being reported as the CF-3300 failing its own
      oracle, i.e. **the host blamed on the reference machine.** Both paths now
      return `TIMEOUT`/`NOCAPTURE`, handled like `MANGLED` (fatal, derivation
      suppressed) under the verdict `RUN FAILED`. **K3 CUT**: a bogus
      `ZEROBAS_BASIC_MACHINE` → `NOCAPTURE`, exit **3**; the identical command
      with the real machine → `0`, exit **0**. The 200 s deadline is left ALONE —
      which path fired is not known, and raising a timeout to fix an unattributed
      failure is a guess; the markers make the next occurrence name itself.
      ⚠️ §5 of the spec pre-committed what to do about red rows at the 4.5 s
      default. **None appeared** — the full run is clean on all 39 — so the
      cadence is unchanged and no rule was reached. The scroll-off risk flagged in
      §5.1 (ten cases type a 5-line program and then `RUN` it) did not materialise
      either; `err_badchan`'s six typed lines fit the 24-row screen.
      Gate: `make chancost-characterize` — **39 cases, 0 mangled, 0 oracle drift,
      0 unfiled divergence, `KNOWN_DIVERGE` EMPTY**, both machines per-channel and
      linear with ceiling 15, headline 267 B (ref) / 50 B (zb): **identical to the
      pre-change run**, which is the control on the change itself.

- [x] ✅ **The `MAXFILES` ARGUMENT DOMAIN — LANDED 2026-07-31, 53/53, falsified,
      NET −6 B.** Filed as "over-ceiling `MAXFILES` raises the wrong error
      class". **The filed item was already fixed** (`61e3a48` made `MAXFILES=16`
      raise ERR 5) — **and closing it on that would have shipped two live
      defects.** Spec [`docs/spec-basic-maxfiles-domain.md`](docs/spec-basic-maxfiles-domain.md),
      results [`docs/chancost-cf3300-characterization.md`](docs/chancost-cf3300-characterization.md) §11.
      Walls: page 1 **63 → 69 B**, low region **UNCHANGED at 23 B**.

      🔴 **THE FILED ROWS COULD NOT REACH THE DEFECT.** `mf16` and `mf255` both
      have a **zero high byte**, so both land on the same arm of `ex_maxfiles`'s
      domain test; `ld a,d / or a / jp nz,gb_illegal` had **never been executed
      by any test on either machine**, across 39 cases. "The class is right" had
      been concluded from two same-side samples.
      🔴 **AND THE SEVERE DEFECT WAS A SILENT ACCEPT.** `ex_maxfiles` took its
      argument through `eval`, not `get_byte_arg`; `eval`'s `flt_to_int16`
      **zeroes `DE`** for an out-of-int16 value (`basic/interp.asm`'s own header
      says so), so `MAXFILES=65536` and `=70000` arrived as `DE=0` and were
      accepted as an ordinary request for **zero channels — every file channel
      disabled, no error raised** — where the reference raises ERR 6 `Overflow`.
      🔴 **AND A SECOND DEFECT WAS INVISIBLE TO THE ROWS THAT FOUND THE FIRST.**
      `32768`/`-32769` *are* representable in 16 bits, so `DE` is non-zero and
      the old test **did** fire — with ERR 5 where the reference says ERR 6. The
      two rows that triggered the slice could not have exposed it; only the
      boundary rows could, and those were added to pin **the denominator of the
      FIX**, not of the defect. ⚠️ **Ask what a fix's own rule needs pinned, not
      just what the defect needed.**
      ⚠️ **THE PROBE WOULD HAVE SCORED THE SILENT ACCEPT AS `agree`.** `err_class`
      returns `None` for any message not in `ERR_CLASSES`, the number scan then
      also returns `None`, and `ERR_CLASSES` had **no entry for `Overflow`** —
      exactly what the reference answers here. Unclassified-error and no-number
      were the same value, so both sides read `None`, compared **equal**, and
      printed `agree`. Fixed FIRST (§0.2): `OVF`/`TM` added, an unreadable screen
      returns **`NOREAD`** and is fatal like `MANGLED`, and the derivation was
      lifted into `read_value()` so it is falsifiable without booting a machine.
      **K4 12/12** synthetic (4 RED / 8 GREEN); **K4b CUTS** — the old rule scores
      the reference-`Overflow`-vs-zerobas-silent-accept pair as `agree`. This is
      [[apparatus-is-part-of-the-measurement]] one layer *inside* where the
      previous session left it.
      ⚠️ **TWO OF MY OWN ROWS WERE WEAK AND WERE CORRECTED BEFORE THEY BECAME
      ORACLES.** `MAXFILES=1.5` read **23430 = `mf1`**, and **1 IS THE BOOT
      DEFAULT** — the cell could not separate "truncated to 1" from "the
      statement did nothing", the same hole the probe header already flags for
      `mf1`. And a fractional row read off `FRE(0)` is `COMPARE absfre`, i.e.
      *informational* — it would have gated **nothing on the machine under
      test**. Both now read out through the channel-number range (a class on
      both machines), with a paired integer control `mfd_frac_ctl`.
      **The reference's rule, measured across 14 rows and recorded BEFORE
      zerobas was run on any of them:** outside int16 → ERR 6 `Overflow`; inside
      int16 but outside `0..15` → ERR 5 (negatives included); fractional
      **TRUNCATES** (`15.9` accepted as 15, `2.5` → 2). ⚠️ The int16 boundary is
      the **RANGE −32768..32767, not the magnitude** — the asymmetry
      `get_byte_arg`'s header records for `CHR$` on the VG-8020, here **measured
      for `MAXFILES` on the CF-3300** rather than assumed to carry across verbs.
      **The fix REPLACES code:** `call eval` + five hand-inlined bytes →
      `call eval_byte_arg`, which *is* the reference rule. Nine bytes become
      three; the `FCH_CEIL` test stays because that bound is the statement's own.
      **Falsified:** reverting `basic/files.asm` alone → **4 RED, 10 GREEN**, red
      exactly `mfd_65536`/`mfd_70000`/`mfd_32768`/`mfd_n32769`, with `mfd_32767`
      and `mfd_n32768` — the *same* boundary, one step inside — staying green, so
      the knife is attributable to crossing int16. ⚠️ **The knife corrected my
      prediction**: I expected `32768` to be a silent accept too; it read `IFC`,
      and that is how the second defect got its name.
      Gate: `make chancost-characterize` — **53 cases, 0 mangled, 0 oracle drift,
      0 unfiled divergence, `KNOWN_DIVERGE` EMPTY**; every ladder reading
      byte-identical to the pre-change run, and both fractional rows held
      (`fac_to_int_strict` truncates like the reference — the live risk in
      routing the argument through a different converter). Full corpus green:
      unit 55/55, badfnum 93, lof 45, diskbasic 34/34, bdos 12/12, fat-error 8/8,
      error/stop-trap, abort 49/49, linemax 60/60, arrdim 73/73, clearpool 52/52,
      array 149/151 (standing `ifc.instr.zero`/`ifc.instr.neg`, confirmed BY NAME).

- [x] ✅ **STALE LEAN-CART CLAIMS SWEPT — 2026-07-31, docs only, 0 ROM bytes.**
      Flagged while landing D-MFDOM (`basic/PROVENANCE.md` §MAXFILES described the
      retired lean 16 KB cart as a LIVE constraint on channel-table work) and
      swept as its own item. **367 hits for `lean cart|lean 16|ROM_BASE`; 7 were
      stale; 360 were legitimate** and deliberately left alone.
      🔴 **THE SWEEP'S OWN PREMISE WAS MOSTLY WRONG, AND THE FILE SAID SO.**
      [`basic/PROVENANCE.md:3591`](basic/PROVENANCE.md:3591) carries an **explicit
      standing decision**: *"EARLIER ENTRIES IN THIS FILE ARE NOT REWRITTEN,
      DELIBERATELY … this file is a provenance log, not a description of the
      current tree."* Rewriting its 32 hits — or the 217 in dated per-slice specs,
      or the 48 in the retirement's OWN specs — would have **violated a documented
      decision** and destroyed the record of how the code got here. ⚠️ **Before
      mass-fixing a pattern, check whether the file already has a POLICY for it.**
      ⚠️ **But the same entry makes a CHECKABLE CLAIM — *"The source comments, by
      contrast, WERE swept"* — and that claim is what this item tested. It had
      SURVIVORS**: [`basic/sv-bsvcas.inc:13`](basic/sv-bsvcas.inc:13) (*"the lean
      16 KB cart **stays** byte-frozen"*), [`basic/bload.asm:71`](basic/bload.asm:71)
      (described an `ELSE` branch that no longer exists),
      [`Makefile:134`](Makefile:134) / [`Makefile:158`](Makefile:158) (*"the lean
      cart **keeps** …"*) and [`Makefile:628`](Makefile:628) (*"the lean cart
      **ships** without EQV/IMP"*, plus a `Repack-only` tag that is meaningless
      with one build). **A completeness claim in a doc is a claim, not a
      measurement.**
      ⚠️ §MAXFILES is NOT covered by the log policy even though it sits above the
      dated entry: PROVENANCE sections are **undated feature sections**, and that
      one is demonstrably LIVE-MAINTAINED (four `2026-07-31` updates). Rewritten
      as explicitly historical — which is what the policy itself prescribes.
      **Left alone on purpose:** [`README.md:213`](README.md:213) and the
      `Makefile` retirement notes (already past-tense and correct); the six
      `Makefile` SUB_PARTS entries saying *"the lean cart's inline copy"* — those
      are POSSESSIVE PROVENANCE identifying which body a `.inc` was carved from,
      not a claim the cart exists, and their staleness warning is unrelated to the
      cart and entirely current. One convention note added at the block head
      instead of six edits, so the block does not read inconsistently.
      **Verification proportionate to the change:** `make -n` parses, and
      `git diff` over `basic/` contains **zero non-comment lines** — provably
      byte-neutral, so no rebuild and no gate was run (they measure nothing about
      a comment).
      ⚠️ **Filed, not fixed:** the policy at `PROVENANCE.md:3591` says "earlier
      entries", but the file is genuinely MIXED — append-only log entries *and*
      live-maintained feature sections. That ambiguity is what made §MAXFILES
      arguable. Sharpening the policy wording is a decision for the owner, not a
      sweep.

- [x] ✅ **D-EXPBAD — A MALFORMED EXPONENT — LANDED 2026-07-31, 99/99, NET −8 B,
      falsified on five knives, and `KNOWN_DIVERGE` IS NOW EMPTY.**
      Spec [`docs/spec-basic-expbad.md`](docs/spec-basic-expbad.md), measurement
      [`docs/expbad-msx1-characterization.md`](docs/expbad-msx1-characterization.md)
      (18 rows, two oracle-lock rounds, VG-8020 and CF-3300 agree on every one).
      **Baseline 3/12 — the only three that agreed were the three controls.**
      🔴 **THE RULE IS THAT THE DIGITS ARE OPTIONAL.** The exponent grammar is
      `[EeDd] [+-]? digit*`, not `…digit+`, so there is **no failure case and no
      rollback** — which is why the fix REMOVES code. `tke_fail` and the two
      range tests that fed it are gone.
      🔴 **AND THE FILED ROWS WERE A SAMPLE, THREE WAYS** — every one of them is an
      `E` with one mantissa digit:
      * `20 A=1D` is a **DOUBLE**: the marker's PRECISION survives a failure that
        consumes no digits. No `E` row can distinguish "a marker was seen" from
        "*this* marker was seen", so a fix collapsing both to single would have
        passed all four filed rows.
      * `20 A=12345EX` is a **SINGLE**, where zerobas stored the two-byte INTEGER
        — the marker forces the literal off the int path, invisible at D=1.
      * `20 A=1E#` leaves the `#` **raw** (the suffix scan is skipped exactly as
        for a well-formed exponent), so `#` does not make it double and `%` does
        not make it integer.
      ⚠️ **The fix CREATED a cell that did not exist before it.** `20 A=1E X`
      keeps its blank and `20 A=1E -X` loses it — D-DECBLANK's cursor rule
      unchanged. Committing where the code stood (after `tkf_fetch` had already
      crossed the blank run) satisfies **every filed row** and silently eats that
      blank; only `dec-emarkblk` / `dec-esignblk` object.
      🔴 **KNIFE K2 REFUTED THE SPEC'S OWN PREDICTION**: the control it named went
      red, because clearing `has_exp` reaches the digitless case too. The real
      control is the `D` pair, making K1/K2 exact mirrors over the two flag bits.
      Corrected in the spec rather than dropped.
      **Cost: NET −8 B, all sub-ROM page 0** (4018 → 4026 B free); main page 1
      stayed at 8 B, low at 23 B, and both main ROMs came out **byte-identical**.
      It does NOT reach `branch_lineno` (`20 GOTO 1EX` keeps `EX` on both
      references) or a `DATA` body — measured, and pinned as controls.

      **As filed** (kept because the filed measurement is what the closed entry
      is measured against):
      ```
      20 A=1EX    ref -> A <EF> <1D>A<10><00><00> X     a SINGLE 1, the `E` EATEN
                  zb  -> A <EF> <12> E X                the INTEGER 1, `E` left
      20 A=1E+X   ref -> A <EF> <1D>A<10><00><00> X     the `+` eaten too
      ```
      ⚠️ **The `0` rows are why it was not D-DECBLANK**: `dec-expbad0` /
      `dec-expbadsg0` carried no blank and read identically to their blanked
      twins ([`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md) §3).
      All four were live in `make lnblank-acceptance` as `KNOWN_DIVERGE`, pinned
      to their exact bytes — and the allowlist reporting them as AGREEING is the
      message that closed them. **That allowlist is now EMPTY.**

- [x] ✅ **A BLANK DOES NOT BREAK A VARIABLE NAME — LANDED 2026-08-01,
      125/125 at `--repeat 2`, 12 B, all sub-ROM, five knives.** Filed as
      *"`&B` is not a radix on MSX1 — and zerobas half-crunches it anyway"*
      (`dec-bin`, informational, from D-DECBLANK's denominator).
      🔴 **The `&` was a RED HERRING, and one row says so positively rather than
      by argument:** `20 A=&1` reads `A<EF>&<12>` on **both** references — a digit
      directly behind the `&` is crunched there too. The filed row's real content
      is `B1 1`, in which `B1` is an ordinary **variable name**:
      ```
      20 A=B1 1  ref -> A<EF>B1 1     zb -> A<EF>B1 <12>    NO `&` ANYWHERE
      20 A=B 1   ref -> A<EF>B 1      zb -> A<EF>B <12>     a LETTER sets it too
      20 B1 1=5  ref -> B1 1<EF><16>  zb -> B1 <12><EF><16> LVALUE position
      ```
      **R-N1: a blank is COPIED but changes no tokeniser state**, so the
      in-a-name flag survives a run of blanks — `B1 1` is the identifier `B11`,
      and `20 B1 1=7` reads back through `B11` as 7 on both references.
      ⚠️ **`dec-oct` had been saying so since D-DECBLANK**: `20 A=&O1 7` crunches
      its `7` on the references too, because an octal *token* is not a name. Same
      shape as `dec-bin`, opposite reading, and the only difference is whether a
      **name** preceded the blank.
      🔴 **And the defect was bigger than one byte.** `20 A=B 1 0`: the reference
      stores the identifier `B10` verbatim; zerobas stored `B`, a blank, and **the
      single literal 10** — having lost the name it handed the run to the decimal
      scanner, which then applied D-DECBLANK's joining. Two rules compounding,
      visible in exactly one row of the battery.
      🔴 **A KNIFE FOUND A LIVE DEFECT IN THE FIX'S OWN FIRST CUT.** `tk_copy` is
      the fallthrough target of the `is_letter` test, so a `tk_blank` parked just
      before it put **every punctuation character** through a store of a register
      `match_kw` had already clobbered — and that build passed the differential
      29/31, clean *by luck*. K2 exposed it via `20 A=B$1`, a row with **no blank
      in it at all**. `nam-paren`/`nam-parenblk` were added and oracle-locked
      because of it.
      Spec [`docs/spec-basic-nameblank.md`](docs/spec-basic-nameblank.md),
      measurement [`docs/nameblank-msx1-characterization.md`](docs/nameblank-msx1-characterization.md).
      `dec-bin` and `lit-varname` are **gating** rows now, not informational.

- [x] ✅ **THE MSX WORK-AREA DENOMINATOR EXISTS — `make sysvarsweep`, LANDED
      2026-08-01.** 279 named entries over `$F380..$FFFE` (3199 B), three sides,
      `--repeat 2`, boot-per-case, jittered. NO `basic/`/`sub/` change: this
      slice ends with a LIST, by design. Spec
      [`docs/spec-basic-sysvar-denominator.md`](docs/spec-basic-sysvar-denominator.md),
      measurement [`docs/sysvar-msx1-coverage.md`](docs/sysvar-msx1-coverage.md).
      **Scoped to meaning (2)** — does a READ return the same value — signed off
      before the probe was written; (1) is unobservable except through (2) and
      (3) is not a fidelity question.
      🔴 **THE FILED ROW WAS THE SMALLEST PART, AND THE NO-ERROR CONTROL IS WHAT
      SAYS SO POSITIVELY.** 19 bytes diverge under `GOTO 99999`, and the obvious
      write-up — *"19 bytes of error state diverge"* — is wrong by ~4×:
      ```
      s1-err   DIVERGE  CSRY KBUF+1..6 BUF CONTXT CONSAV CONTYP CONLO LINTTB | ERRFLG ERRLIN ERRTXT
      s2-noerr DIVERGE  CSRY KBUF+1..2 BUF CONTXT CONSAV CONTYP CONLO LINTTB | (+TEMP/TEMP2/TEMP3)
               `A=1` RAISES NO ERROR and moves the SAME set --------^
      ```
      **Exactly THREE variables are error-specific**: `ERRFLG $F414`,
      `ERRLIN $F6B3`, `ERRTXT $F6B7`. `KBUF`/`BUF` and the `CONT` anchor
      `CONTXT`/`CONSAV`/`CONTYP`/`CONLO` are rewritten on **every direct-mode
      line** on both references and never on zerobas. The class is not "zerobas
      ignores `ERRFLG`" but *"zerobas keeps its BASIC bookkeeping in its own RAM
      window while the published addresses stay at power-on values."*
      🔴 **AND LAYER 0 FOUND EIGHT MORE, WITH NO EMULATOR AT ALL.** zerobas'
      `sysvars.inc` shares 46 names with the published map: 38 at the published
      address, **8 RE-HOMED** — `VALTYP` `FRETOP` `SAVTXT` `SAVSTK` `ONELIN`
      `ONEFLG` `ARYTAB` `DEFTBL`, all into the same freed `$E1Cx`/`$E2xx` window
      with the same "own choice" provenance. ⚠️ A **LOWER BOUND**: it matches on
      the NAME, so `ERRCODE`-vs-`ERRFLG` (different spellings) is invisible to it.
      **Measurable surface is not 3199**: 6 B VOLATILE (`SCNCNT` `REPCNT`
      `JIFFY` `INTCNT` — all clock-derived, all BIOS-owned), 311 B NO-ORACLE
      (the two references are structurally different machines), ~2626 B INERT.
      **66 named variables diverge somewhere: 45 BASIC-owned, 21 BIOS-owned.**
      At cold boot **256 B** differ where both references agree (114 BASIC-owned)
      — `USRTAB`'s ten `$475A` vectors, `CS120`/`CS240`, `ENDPRG`, `CURLIN`.
      ⚠️ **Whether `ERRFLG` should MOVE to `$F414` remains a SEPARATE design
      question** — zerobas' memory map is its own and relocating live error state
      is not a free edit. Deliberately not started.
      ⚠️ **Three apparatus defects, each caught by a control rather than by
      luck** (docs §8): the volatility control was **connected to nothing**
      (`cap_gap` is the gap AFTER the capture and this probe is boot-per-case, so
      it reported `VOLATILE=0` over the whole work area, JIFFY included, while
      looking like it worked — and had PUBLISHED a false `REPCNT` finding);
      C-INSTR failed on all three sides from the payload's **own echo** supplying
      a bracket pair; and the table parser silently dropped the 10 inline-
      commented entries, `JIFFY` among them, then mislabelled the most volatile
      byte in the work area `PADX+1`.

- [x] ✅ **THE RE-HOMING CLASS: TEN DECISIONS RECORDED, FIVE ADDRESSES HONOURED
      AT ZERO ROM COST — LANDED 2026-08-01.** Filed by the sysvar denominator as
      *"8 published names at private addresses, and NOBODY DECIDED THAT"*.
      Decisions: [`docs/sysvar-rehoming-decisions.md`](docs/sysvar-rehoming-decisions.md),
      spec [`docs/spec-basic-sysvar-rehoming.md`](docs/spec-basic-sysvar-rehoming.md),
      **recorded beside each equate in [`basic/sysvars.inc`](basic/sysvars.inc)** —
      which was the deliverable. Four paired stimulus states added to
      `make sysvarsweep` (5 → 13), oracle-locked on both references at
      `--repeat 2` **before zerobas ran on any of them** (new `--sides` filter,
      so the ordering is a mechanism and not a promise).
      🔴 **SEVEN OF THE TEN ARE MEASURABLY THE SAME VARIABLE.** Not ten designs
      placed for space — one design at a different address. `ERRFLG` `00→08`,
      `ERRLIN` `→FFFF` direct / `→20` from a stored line, `ONELIN` `→$8015`,
      `ARYTAB` byte-identical in all four direct-mode states, `DEFTBL` 25/26 B
      identical, `FRETOP` `SAME-DELTA` −4/−20; `ONEFLG` same role with a
      different sentinel.
      ✅ **HONOURED (zero ROM bytes each — every access was already symbolic, so
      an `equ` change is an assembler constant; low still 23 B, page 1 still
      8 B):** `ERRCODE`→**`ERRFLG $F414`**, `ERRLINE`→**`ERRLIN $F6B3`** (renamed
      too — the off-book spelling is *why* the static name-match could not see
      the pair that started this item; the layer now reports **43 honoured / 5
      re-homed**, was 38/8), `ONELIN $F6B9`, `ONEFLG $F6BB` (+ sentinel `1`→`$FF`,
      measured, control-flow-neutral), `DEFTBL $F6CA`.
      🔴 **MIRRORING WAS SIGNED OFF AND THEN REFUTED BY AN ALREADY-FILED ROW.**
      `POKE&HF414,0 : PRINT ERR` prints `0` on both references — `ERR` **reads**
      `$F414`, so a write-only mirror satisfies `PEEK` and **fails** `POKE`. The
      cheap way out of *"moving live error state is not a free edit"* was
      measurably insufficient, and the edit was free anyway.
      ❌ **REJECT-GROUP:** `ARYTAB` and `FRETOP` — both *SAME-VAR/SAME-DELTA* and
      still refused, because their consumers read a **chain**
      (`TXTTAB≤VARTAB≤ARYTAB≤STREND`; `FRETOP` against `MEMSIZ`/`STKTOP`) and
      zerobas has no stored `VARTAB`/`STREND`/`MEMSIZ`/`STKTOP`. Publishing one
      end of a subtraction yields a **confident wrong answer** where today a
      consumer gets `0−0` and an obviously dead reading.
      ❌ **REJECT-UNOBSERVABLE:** `VALTYP` (refs constant `$03` in all 9 states)
      and `SAVTXT` (refs pinned at `$F40F`) — 🔴 *"never moves"* here means the
      question could not be PUT, not that there is nothing to honour.
      ⏸ **DEFER:** `SAVSTK` — `NO-ORACLE` absolutely **and** `refsΔ=+0`; the
      settling measurement is named (capture INSIDE a running statement).
      🔴 **THE FILED TITLE WAS WRONG TWICE.** *"Nobody decided that"* is false for
      `VALTYP`: [`basic/usr.asm:19`](basic/usr.asm:19) already carried a
      **measured, oracle-locked** decision naming `$F663`. And *"per variable"* is
      the wrong unit — signed off as **decide per variable, reason per group**.
      🔴 **A knife on my own fix:** the new delta branch returned `DIFF-DELTA` for
      every one-sided movement, so `SAVSTK` read as *"zerobas moves it wrongly"*
      when the references never move it at all — the absolute branch had always
      said `ZB-ONLY` for that shape, and **the two branches were answering the
      same question differently**.
      🔴 **THREE OF THE APPARATUS' OWN CONTROLS WERE INVERTED BY THIS FIX, AND
      THE THIRD WAS MISSED — THE GATE CAUGHT IT, NOT THE AUTHOR.** `C-REPRO`
      (`$F414` must DIVERGE) and `C-REPRO-2` (the value must live at `$E1C5`)
      both asserted the state this slice deliberately ended, and were re-aimed at
      the new known answer — each **strictly stronger** than what it replaced,
      since the old `C-REPRO` passed whenever zerobas did *nothing at all* with
      `$F414`. **`C-PRIV` was pinned on `DEFTBL['A']` at `$F153` — an address
      this slice HONOURED away** — so it failed and voided the post-fix run,
      correctly. Re-anchored on `ARYTAB $E1C0`, chosen *because* its verdict is
      REJECT-GROUP and it therefore stays private by decision. ⚠️ The lesson was
      written down **earlier in this same slice** than the instance that proved
      it: a rule stated is not a rule applied.
      New controls, all now firing: **C-PRIV** (the private segments must be
      shown to MOVE), **C-REPRO-2**, and 🆕 **C-VACATED** — the five addresses the
      honoured variables moved OUT of must go QUIET, because a leftover store at
      an old address is a half-done relocation that every other check reports as
      green.

- [x] ✅ **`DEFTBL_STR` SHOULD BE `3`, NOT `1`.** Filed 2026-08-01 by D-REHOME,
      closed 2026-08-01 by **D-DEFSTR**
      ([`docs/spec-basic-deftbl-strcode.md`](docs/spec-basic-deftbl-strcode.md)).
      All 26 published `DEFTBL` bytes now match both references in every measured
      state. 🔴 **The filed reason was not the live hazard.** `1` was not an
      own-design sentinel colliding with the numeric *widths* `2/4/8`; it was an
      accidental collision with zerobas' **variable-chain string type tag, which
      is also `1`** — a second, own-design namespace that overlaps the published
      one on the numeric values. Three sites fed a published code straight into
      the chain, and one of them was a **live memory corruption**:
      `DEFSTR I:FOR I=1 TO 3` reached `var_store_fac` with type `1`, which is
      simultaneously the chain's string tag *and* an `ld c,a`+`ldir` byte count —
      so it allocated a real STRING entry and wrote one byte of FAC over its
      descriptor's `len`. PRINT then dumped arbitrary RAM. **The coincidence at
      `1` is what kept it quiet**, and changing the constant alone would have
      relocated the corruption into phantom `type=3` entries, not removed it.
      Every published→chain crossing is now checked (`deftbl_num_type` /
      `check_vartype_num`, low region). 16 of 18 measured rows now match both
      references, up from 12; **11 green controls held**. Cost −14 B low region,
      −3 B page 1, exactly as the spec predicted.
      🔴 And three rows that **agreed** agreed for the wrong reason: `B=S` is
      caught by `ev_rel`'s `str_eval` probe, which sits at the TOP of an operand
      only — `B=1+S` was not, and silently read 0 where both references raise
      ERR 13. Stopping at the top-level shape would have filed B1 as dead code.

- [x] ✅ **TWO ACCEPTANCE SUITES ARE STANDING-RED WITH NO EXPECTATION WRITTEN
      DOWN.** Filed 2026-08-01 by D-DEFSTR, **closed the same day by D-EXPKW** —
      [`docs/spec-basic-expkw.md`](docs/spec-basic-expkw.md), measurement
      [`docs/expkw-msx1-characterization.md`](docs/expkw-msx1-characterization.md).
      Neither suite was edited and neither was pinned: **both went green off one
      22-byte change**, because they were never two failures.
      🔴 **ALL THREE FILED CLAIMS WERE THE WRONG SUBJECT.**
      * *"`float-acceptance` → `reg.C.if_skip_over_float`, likely the `$0E`/`ELSE`
        class"* — not the `$0E` class, not `tok_skip`'s float stride (which
        strides `$1D` correctly, `basic/tokskip-body.inc:36`), not
        `if_skip_to_else`, **and not about floats**: the same line with an
        INTEGER literal breaks identically (`expk-ifelsei`, pinned as that
        battery's control and measured RED).
      * *"`logicops` → 50 rows, all `EQV`/`IMP`, both unimplemented"* — `EQV`/`IMP`
        **landed** in `ef098e9` at 156/156 (`basic/expr.asm:148`). Of the 49
        failing rows **every one contains `EQV`; not one fails on `IMP` alone.**
        `PRINT 0 EQV 0` printed three items: `0`, the variable `QV`, `0`.
      * *"two unrelated standing failures"* — **one defect.** `ELSE` and `EQV` are
        the only reserved words in the language beginning with `E`, and the
        literal scanner was eating that `E`.
      🔴 **AND IT WAS A REGRESSION, NOT A STATUS QUO.** `4b2202e` (D-EXPBAD)
      deleted the rollback on the finding *"THE DIGITS ARE OPTIONAL AND THERE IS
      NO FAILURE CASE"* — generalised from five rows (`1E`, `1E+`, `1D`, `1E#`,
      `12345EX`) **none of which puts a reserved word behind the marker.**
      ⚠️ D-DEFSTR's A/B could not have caught it: it stashed **`basic/`**, but
      `tkf_try_exponent` is in **`sub/tkfloat.asm`**. The A/B answered "not mine"
      correctly; the conclusion drawn from it — *"standing state, pin it"* — did
      not follow. **A NOT-MINE FALSIFICATION SAYS NOTHING ABOUT WHOSE IT IS.**
      Measured rule (76 rows, both references agree, oracle-locked first): an `E`
      marker is **not a marker when the next character — across blanks,
      case-folded — is `L` or `Q`**; `D` has no protected letter (26/26 eaten).
      It is a **LETTER** test, not a keyword match: `1 EQ`/`1 EL` keep the marker
      though neither is a word, `1 ERL`/`1 DIM` lose it though both are.

- [x] ✅ **`logicops-acceptance` WAS NOT IN THE DOCUMENTED CORPUS.** Filed and
      fixed 2026-08-01 by D-EXPKW. **This is the reason the regression above was
      invisible for two slices**: `make logicops-acceptance` (193 rows, ~40 s) is
      a standing gate of the same rank as `float-acceptance`, but no spec's
      "full corpus" list named it, so nothing ran it after `4b2202e`. It is a
      **required corpus member** from here on, alongside:
      `unit-test` 55/55 · dead-code gate 0/0 both builds ·
      **`lnblank-acceptance` 327/327 with `KNOWN_DIVERGE` EMPTY — note the target
      defaults to `--repeat 1`, so the corpus run is
      `make lnblank-acceptance REPEAT=2`** · **`logicops-acceptance` 193/193** ·
      `float-acceptance` (exits 0) · `array-acceptance` 149/151
      (`ifc.instr.zero`, `ifc.instr.neg` by name) · `arrdim` 73/73 ·
      `clearpool` 52/52 · `badfnum` 93 · `lof` 45 · `chancost-characterize` ·
      `diskbasic` 34/34 · `bdos` 12/12 · `fat-error` · `error-trap` ·
      `abort` 49/49 · `stop`/`strig`/`key`-trap · `linemax` 60/60 ·
      `sysvarsweep` exit 0 with all five controls green.
      ⚠️ **A GATE NOBODY RUNS IS NOT A GATE.** It was green at 193/193 when it
      landed and nothing re-read it; the suite reported its own failure honestly
      for two slices to an empty room.

- [ ] **`float-acceptance` HAS NO NAMED EXPECTED-FAILURE MECHANISM.** Filed
      2026-08-01 by D-EXPKW. The suite is green today, so this is not urgent —
      but it reports `371 PASS, 1 FAIL` and exits non-zero with **nothing naming
      the expected count**, which is exactly what made the D-EXPKW regression
      unreadable for a whole slice. `array-acceptance`'s 149/151 names
      `ifc.instr.zero`/`ifc.instr.neg`, and lnblank's `KNOWN_DIVERGE` pins each
      entry to its exact observed value so a row that silently starts passing
      breaks the gate. `float-acceptance` has neither. ⚠️ Give it the
      *control* shape, not the suppression shape.

- [x] ✅ **ZEROBAS HAS NO STRING `READ` — CLOSED 2026-08-07 by D-READVAR**,
      [`docs/spec-basic-readvar.md`](docs/spec-basic-readvar.md),
      [`docs/readvar-msx1-characterization.md`](docs/readvar-msx1-characterization.md),
      gate `make readvar-acceptance` (**22/22, 1 positive control, 2 deferred**).
      Filed 2026-08-01 by D-DEFSTR from rows aimed at the `DEFTBL_STR` sentinel;
      **scouted 2026-08-07 and the title under-claimed it by a factor of five** —
      `ex_read` did not merely lack a `$` path, it parsed its target with
      `var_get`/`var_set`, the single-letter int16 shim, while every other
      variable reference in the tree goes through `var_name_key`.
      **THE FIX:** `ex_read` is now `ex_input`'s shape routine for routine —
      `var_str_type` → `var_name_key` → (numeric: `var_store_fac`) / (string:
      `strscr_desc` → `str_set_key`) — and the READ/DATA page-0 tenant gained an
      item MODE: numeric parses an int16, string captures the item's RAW ASCII
      span into `STRSCR`. **+32 B main page 1 (158 → 126), −74 B sub p0
      (3843 → 3769)**; low and sub p1 unmoved. The +35…45 B scouted bound held.
      🎯 **`c.strnum` — THE ONE DIVERGENCE THAT POINTED THE OTHER WAY — CLOSED
      WITH THE OTHER 21, AND IT WAS SEPARATE WORK.** `DATA HELLO` / `READ A` is a
      **Syntax error** on both references; zerobas answered ` 0 ` because
      `data_parse_int` parsed no digits, yielded 0 and stored it silently.
      Re-routing the target parse does not touch that row: it is fixed in the
      DATA ENGINE, by giving `read_one_value` a third return status (the old
      contract was one carry bit, which is why the third answer had nowhere to
      go). Fixing the 21 loud rows and leaving the quiet one is the failure mode
      this project keeps recording, and it is the reason that status exists.
      🔴 **`b.trailsp` — the row that paid for having been measured.** `DATA
      PAD  ,X` reads back `'PAD  '` on **both references**: leading spaces are
      stripped, trailing ones are **not**. The symmetric rule is the obvious one
      and it is wrong; knife **K-RV4** builds it and reddens `b.trailsp` **alone**.
      That row exists only because the denominator was re-read for what it had
      not ASKED (22 rows → 24).
      🔴 **AND THE LEADING-SPACE RULE HAS NO ONE-ROW KNIFE, WHICH IS ITSELF THE
      FINDING.** It is implemented TWICE — `data_seek`'s `ds_sp` and the item
      capture's own `skip_spaces` — and every B row is its statement's FIRST
      item, so cutting the capture's skip alone reddens **nothing** (K-RV3a, a
      confirmed predicted MISS on a build whose ROMs demonstrably moved). Cutting
      both reddens **13 of the 22**, because `tk_data_rest` copies a `DATA` body
      verbatim from the character after the keyword and every unquoted item then
      gains a leading space. [[rule-gated-structurally-has-no-knife]]
      ➡️ **`READ A(1)` / `READ A$(1)` are DEFERRED and re-filed as their own open
      item** in §"Open — standing residuals", with their price and with the
      unmeasured question that decides how much the work is worth (`INPUT A(1)`).
      🔴 The scout's own first readout was **blind to its subject** — it scanned
      the whole screen, so when zerobas printed no output the `[` inside the ECHO
      of `30 PRINT"[";A$;"]"` matched and every zerobas row read `'";A$;"'`, an
      artifact shaped like a reading. Read the tail after `RUN`, never the screen.

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

- [x] ✅ **`20 GOTO 99999` — CLOSED BY D-LNREF 2026-08-01, and the "3 bytes"
      was a SPLIT.** Filed by D-REHOME from `s7-fired`'s `ONELIN`/`ARYTAB`
      pointers — a LENGTH, never the bytes — and its own note that this was
      "likely related" to the `$0E` item was right for the wrong reason.
      🔴 **The reference does not wrap, saturate or refuse: it SPLITS the digit
      run.** A line-number reference accumulates only while the value would stay
      **≤ 65529**, and the first digit that would exceed it starts a NEW
      reference, because the mode is still armed. `GOTO 99999` is
      `$0E,9999` `$0E,9`; `GOTO 65530` is `$0E,6553` `$0E,0`. Same constant as
      the LEADING line number's ceiling, different response.
      Both items were ONE mechanism. Spec
      [`docs/spec-basic-lnref.md`](docs/spec-basic-lnref.md) **R-V**,
      measurement [`docs/lnref-msx1-characterization.md`](docs/lnref-msx1-characterization.md) §2.

- [ ] **HOW MUCH OF THE 311-BYTE `NO-ORACLE` BUCKET IS A POINTER?** Filed
      2026-08-01 by D-REHOME. `FRETOP` sat in that bucket scored as *"no
      reading"* while all three sides agreed **perfectly** on the movement
      (−4/−20). The sweep now has a `SAME-DELTA` verdict, but it is only applied
      in the re-homing table — **the 3199-byte census still classifies every byte
      absolutely.** 🔴 `NO-ORACLE` is a verdict about the COMPARISON, not about
      the variable, and the bucket is an over-count by an unmeasured amount.
      ⚠️ A byte-wise delta pass needs a rule for what counts as a pointer PAIR;
      naive per-byte deltas on a 16-bit cell will agree by luck on the high byte.

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

- [x] ✅ **~~THE COLD-BOOT `FPERR` ZERO IS LOUDLY OBSERVABLE AND EVERY BATTERY
      IS BLIND TO IT~~ — CLOSED 2026-08-21 as D-COLDROW, 0 ROM bytes.**
      [`docs/valtyp-coldram-notes.md`](docs/valtyp-coldram-notes.md) §6.
      `probes/basic/basic_probe_stmtpend.py` gains a `b.*` family: `b.cold`
      boots, types `NEW` **without** `CLS`, enters `10 PRINT"[OK]" / 20
      PRINT"[TWO]"` and runs it; `b.warm` is the same program off the normal
      reset and is a POSITIVE CONTROL pinned to the LITERAL `[OK]|[TWO]`.
      `stmtpend-acceptance` **58/58 → 60/60**, every shipped row's value
      unchanged. Knife **K-CR1** (the K-VT1 cut) reddens **`b.cold` ALONE** at
      `Unprintable error in 10` — 59/60, two rounds, identical red sets;
      **K-CR2** (probe-side, the override label renamed) exits **2**, an
      INSTRUMENT FAULT, because `reset_selftest()` refuses to run a pair that no
      longer differs. That self-check was calibrated against four known
      positives before any green run was believed.
      ⚠️ `ERRFLG`/`DOT` are **still** uncovered and deliberately so: `$F414` and
      `$F6B5` sit inside the C-BIOS-cleared sysvar area, so cutting their stores
      is genuinely invisible on this emulator. A row claiming all three would be
      over-claiming; `b.cold` covers `FPERR $F069`.
      ⚠️ Also added: the missing `$(DISK_TEST_DSK)` dependency on both stmtpend
      targets — the THIRD such gap in three slices — and a correction to the
      REASON D-FILESIDE gave for `namspc`'s, which was wrong (see the new
      residual below). The original entry follows.
      ~~🔴 **MEASURED 2026-08-21 (D-VALTYP, knife K-VT1).**~~
      [`docs/valtyp-coldram-notes.md`](docs/valtyp-coldram-notes.md) §3/§4.
      Cut `ld (FPERR),a` from [`basic/interp.asm`](basic/interp.asm)'s cold hook
      and `$F069` stays at its power-on `$FF`, so `10 PRINT"[OK]"` answers
      **`Unprintable error in 10`**. On the same build `clearpool-acceptance` is
      **62/62** and `stmtpend-acceptance` — K-SP4's OWN battery — is **58/58**.
      🎯 **WHY, MEASURED NOT INFERRED:** the bogus error fires EXACTLY ONCE, and
      `CLS` is the statement that spends it (`NEW` alone does not). Every battery
      resets through `CLS`, so no scored row can ever see it.
      ➡️ **WHAT IS OPEN IS THE APPARATUS, NOT THE ROM** — the store is present
      and correct; what is missing is any row that boots and runs a program
      WITHOUT a `CLS`-bearing reset. Shape: one case in a battery that already
      boots per case, resetting with `NEW` only. 💰 Not priced.
      ⚠️ The same hole covers `ERRFLG` and `DOT`, whose cold stores are genuinely
      invisible here because `$F414`/`$F6B5` sit inside the C-BIOS-cleared sysvar
      area — a real-hardware-only argument that nothing in the tree can test.

- [x] ✅ **~~FORTY-EIGHT MAKE TARGETS BUILD THEIR DISK FIXTURE ONLY BY LUCK, AND
      HALF OF THEM FAIL SILENTLY IF IT IS ABSENT~~ — CLOSED 2026-08-21 as
      D-DISKDEP, AND THE SECOND HALF OF THE TITLE IS FALSE.**
      [`docs/spec-probe-diskdep.md`](docs/spec-probe-diskdep.md). **0 ROM bytes.**
      `$(DISK_TEST_DSK)` added to all **48** targets (0 remain), new gate
      `make diskdep-check` with `make diskdep-selftest` **4/4**, baseline 0.
      🔴 **THE FILED 19-LOUD / 16-SILENT SPLIT IS REFUTED BY MEASUREMENT: THERE IS
      NO SILENT HALF.** All seventeen candidates were run with the image moved
      aside on a fully built machine and **every one refused** — `omsx_preflight`
      rc 2 (6), an own guard rc 2 (3), a `shutil.copy` traceback rc 1 (5), the
      `<NO DISK FIXTURE>` sentinel rc 1 (1), a child probe's guard rc 1 (1).
      🎯 **THE REGEX BEHIND THE SPLIT KEYED ON A VARIABLE NAME** (`TEST_DSK`), so
      ten probes that copy through a local or spell it `SRC_DSK` read as silent.
      🎯 **AND THE SIX IT CLASSIFIED CORRECTLY ARE STILL NOT SILENT** — they hand
      `diska` straight to openMSX, and `omsx_preflight` (which `make
      preflight-check` proves covers EVERY launch in the tree) refuses first. The
      property that closes the class was already enforced by a gate nobody thought
      to cite here.
      🔴 **TWO READINGS WERE THROWN AWAY FOR MEASURING THE WRONG ABSENCE:** round 1
      ran on a `basic-reloc`-only tree, so `lptverb` and `msgexact` refused over
      **missing ROMs** — the preflight named them, the return code did not — and
      `diskbasic_acceptance` refused three times over `--machine`,
      `--expect-build` and an empty `--only` before it ever reached the disk.
      💰 The `<NO DISK FIXTURE>` sentinel is FILED as the shape to converge on, not
      taken: with the dependency in place the absence never occurs under `make`.
      The original entry follows.
      ~~⚠️ **FORTY-EIGHT MAKE TARGETS BUILD THEIR DISK FIXTURE ONLY BY LUCK.**~~
      Filed 2026-08-21 by
      D-COLDROW ([`docs/valtyp-coldram-notes.md`](docs/valtyp-coldram-notes.md)
      §6.6) after `stmtpend` became the THIRD target in three slices found
      without a `$(DISK_TEST_DSK)` dependency (`inputary` D-ARYSITE, `namspc`
      D-FILESIDE). `disk/test720.dsk` is **generated, not tracked** — it is not
      in `git ls-files` — so on a fresh clone every one of these targets depends
      on some earlier target having happened to build it.
      📏 **THE DENOMINATOR IS MACHINE-PRODUCED AND THE ENUMERATOR IS THE
      DELIVERABLE**, because the interesting split is not *which targets lack the
      dep* but *what absence LOOKS like*:

      ```
      python3 - <<'PY'
      import re, os
      mk = open("Makefile").read()
      for tgt, deps, recipe in re.findall(
              r'(?m)^([A-Za-z0-9_.-]+):([^\n]*)\n((?:\t[^\n]*\n)*)', mk):
          for p in set(re.findall(r'probes/\S+\.py', recipe)):
              if os.path.exists(p) and 'test720.dsk' in open(p).read():
                  src = open(p).read()
                  loud = bool(re.search(r'shutil\.copy2?\(\s*[A-Z_]*TEST_DSK', src))
                  print(('LOUD  ' if loud else 'SILENT'),
                        'DEP-OK' if 'DISK_TEST_DSK' in deps else 'NO-DEP',
                        tgt, p)
      PY
      ```

      **35** probes name the image. **19** copy it per case, so a missing image
      raises `FileNotFoundError` before openMSX launches — **measured**, by moving
      the file aside and running one row of `namspc` and one of `stmtpend`: rc 1,
      a traceback, no boot. **16** hand the path to openMSX, which boots with an
      empty drive and says nothing — that is the class that can AGREE while
      measuring nothing. **24 targets in each half lack the dependency.**
      ⚠️ **THE SILENT COUNT IS AN UPPER BOUND, NOT A ROSTER.** Five of the sixteen
      do not set `diska` at all (`disk_probe_dskio`, `diskbasic_acceptance`,
      `badfnum`, `chancost`, `lof`) and reach the drive some other way; each needs
      reading before it is called blind. That per-probe question is why this is a
      slice and not a line.
      🔴 **AND ONE JUSTIFICATION IN THE TREE WAS ALREADY WRONG ABOUT THIS** — the
      `namspc-acceptance` comment D-FILESIDE wrote on 2026-08-20 claimed the rows
      "would read `<NO OUTPUT>` on both disk sides and AGREE". They would not;
      `namspc` is in the LOUD half. Corrected in place by D-COLDROW. The
      dependency was right, only the reason for it was wrong —
      [[a-fix-falsifies-the-justification-beside-it]] with the fix and the false
      sentence one day apart.
      💰 0 ROM bytes, apparatus only. Cheapest honest shape: add the dependency to
      all 48, then delete the five unknowns from the silent roster by reading them.

- [x] ✅ **~~`dir-name` — A BLANK INSIDE A NAME IS NOT READ BACK IN DIRECT
      MODE~~ — MEASURED FALSE 2026-08-09** by the TODO staleness sweep,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.3. The entry's own payload, verbatim, with a no-blank control:

      | row | program | VG-8020 | CF-3300 | zerobas |
      |---|---|---|---|---|
      | `n.ctl` 🟢 | `B11=7 : PRINT"[";B11;"]"` | ` 7 ` | ` 7 ` | ` 7 ` |
      | `n.blank` | `B1 1=7 : PRINT"[";B11;"]"` | ` 7 ` | ` 7 ` | **` 7 `** |

      🎯 **CLOSED BY D-NAMSPC ON 2026-08-08**, whose rule is exactly this one — a
      space inside a variable NAME is insignificant at *every* reference, not
      just at the 9 lvalue targets ([`docs/spec-basic-namspc.md`](docs/spec-basic-namspc.md),
      `namspc-acceptance` 58/58). The residual predates it by a week and named
      the right mechanism (D-NAMBLANK's R-N1) without ever being re-run against
      HEAD — which its own ⚠️ below asked for.
      ⚠️ **THE SECOND HALF OF THIS ENTRY IS NOT CLOSED BY THAT ROW** and is
      re-filed below as its own item: the `--say` surface is still un-gated
      outside `ONLY=lnrd-`, and "ask what else the say pass says" was never
      answered. A payload that now agrees says nothing about the rows nobody
      looks at.
      **What was believed, kept as the record of why:**
      Surfaced 2026-08-01 by the first full `--say` pass across all three sides
      (D-CNAME ran one; nothing else does). Oracle-locked, both references agree:
      ```
      B1 1=7 : PRINT"[";B11;"]"    vg8020 -> 7    cf3300 -> 7    zb -> 0
      ```
      D-NAMBLANK's **R-N1** says a blank is copied but changes no tokeniser state,
      so `B1 1` is the identifier `B11` and the assignment must be readable back
      through it. The references do exactly that; zerobas reads **0**.
      ⚠️ **NOT caused by D-CNAME** — that change touches only `tk_call_name`,
      reachable solely from the `CALL` token dispatch and `tk_underscore`, and
      this payload has neither. Reachability argued, **not re-measured against
      HEAD**; do that first.
      🔴 **THE ROW HAS NEVER GATED ANYTHING.** `--say` rows are filtered out of
      `lnblank-acceptance` entirely, and the probe's own comment already recorded
      that it "was dormant, not green" for a *different* reason. So the whole
      `--say` surface is un-gated and this is what was hiding in it — the same
      shape as the SILENT-GAP class. **Ask what else the say pass says before
      fixing this one row.**
      ⚠️ **PARTLY ADDRESSED 2026-08-01 by D-LNREF: `make lnblank-say-acceptance`
      exists and gates `ONLY=lnrd-`.** It was added because that slice's
      load-bearing control (`lnrd-erl`) was itself sitting in this un-gated
      surface — knife K4 shows the regression it catches passing the MEMORY gate
      3/3 while the program raises `Syntax error`. The default is scoped to
      `lnrd-` precisely because THIS row is red, so a whole-surface default would
      ship a red target. **Widening that default is the fix for this item.**

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

- [x] ✅ **THE `CALL` DEVICE-NAME SCAN IS A RANGE TEST, NOT AN IDENTIFIER SCAN —
      LANDED 2026-08-01, 251/251 at `--repeat 2`, NET −10 B, all sub-ROM, seven
      knives.** Filed by D-LNLIST as *"the scan stops short — the reference
      reaches further"*, from three rows that were **all** written to ask a
      different question and had their digit eaten before they could ask it.
      🔴 **THE DIRECTION WAS RIGHT AND THE RULE WAS WRONG, IN BOTH DIRECTIONS.**
      The obvious rule from the filed rows — *copy identifier characters and
      blanks, drop everything else* — is refuted, and so is the narrow *"only the
      `+` is swallowed"*:
      ```
      20 CALL X+5   ref -> <CA> X5     the '+' is DROPPED
      20 CALL X;5   ref -> <CA> X;5    the ';' is KEPT and the scan RUNS ON
      20 CALL X:5   ref -> <CA> X:<16> the ':' TERMINATES
      ```
      🔴 **AND THE OPERATORS LAND ON BOTH SIDES.** `+ - * /` are dropped;
      `^ \ = < >` are kept. Nine operators split down the middle, so neither
      operator-ness nor the token byte separates them — the same interleaving
      shape D-LNLIST hit. What separates them is the **ASCII range**: once EOL,
      `:` and `(` are taken out, a character is discarded **iff `' ' < c < '0'`**.
      All fifteen characters of `$21..$2F` were walked contiguously, and every
      printable character at or above `$3B` that this harness can deliver — so
      both classes are denominators, not samples. **Three rows were structurally
      incapable of finding this**; each agrees with two different wrong rules.
      🔴 **THE FIX DELETES A SUB-ROM ROUTINE AND THE DEAD-CODE GATE FORCED IT.**
      `basic/vars.asm` is not included by `sub/sub.asm`, so the new range test
      orphaned the sub-local `is_ident_cont` clone — `make basic-reloc` failed the
      build rather than shipping 16 dead bytes. **Knife K6 is that argument turned
      into a measurement**: it restores the clone with no caller and the *build*
      goes red. NET **−10 B** (+6 loop, −16 clone), sub page 0 3998 → **4008 B**
      free; both main ROMs **byte-identical**, asserted by hash.
      ⚠️ **THE THREE `KNOWN_DIVERGE` ROWS RETIRE AND THE ALLOWLIST IS NOW EMPTY** —
      the fifth cohort to leave it that way, and not one has rotted.
      ⚠️ Three apparatus findings, each caught by a guard rather than by luck:
      `{` `|` `}` are **not deliverable** (the `}` row returned a stable,
      both-references-agreeing `<CA> X{5}` from a payload with neither brace — a
      perfect fake the echo guard killed); the echo guard's payload ceiling is the
      **display width**; and `cnm-lower` mangles **intermittently in a batch**,
      which `--repeat` cannot catch.
      Spec [`docs/spec-basic-cname.md`](docs/spec-basic-cname.md), measurement
      [`docs/cname-msx1-characterization.md`](docs/cname-msx1-characterization.md).

- [x] ✅ **A LINE-NUMBER LIST IS A MODE, NOT A LIST — LANDED 2026-08-01,
      NET +26 B, all sub-ROM, seven knives.** Filed by D-NAMDOT as *"a `.` does
      not end a line-number list"*, from the single `dot-goto` row.
      🔴 **THE FILED TITLE WAS REFUTED AND THE `.` WAS NEVER THE SUBJECT.** A
      dozen measured characters do the same thing:
      ```
      20 GOTO 1+5    ref -> <89> <0E><01><00><F1><0E><05><00>
      20 GOTO 1;5    ref -> <89> <0E><01><00>;<0E><05><00>
      20 GOTO 1.5.7  ref -> <89> <0E><01><00>.<0E><05><00>.<0E><07><00>
      ```
      After a branch keyword the reference is in a **MODE** that runs to the end
      of the **statement**: every digit run that would begin a numeric constant
      becomes `$0E,<line>` instead, whatever stands between them. Fixing it from
      the row that found it would have added `.` to a separator test and shipped
      a rule a dozen characters too narrow — **and `dot-goto` cannot tell the two
      rules apart**, because both predict its exact bytes.
      🔴 **WHAT DISARMS IT IS ALPHABETIC-vs-SYMBOLIC, AND THAT CANNOT BE TESTED
      AS A TOKEN VALUE.** `\` is `$FC` and *keeps* the mode; `MOD` is `$FB` and
      *clears* it; `PRINT` is `$91`, below both, and clears. The classes are
      interleaved, so no threshold or mask separates them — words and variable
      names clear, symbols and punctuation do not, and `:` clears.
      🔴 **THE FIX SHRINKS `branch_lineno`.** `bl_yes`' blank loop, `bl_num`'s
      comma test and `bl_list` are **deleted**: ordinary `tk_loop` already copies
      blanks, commas and punctuation, which is what they were hand-rolling. The
      empty-slot bug `bl_num`'s comment records is **dissolved** rather than
      re-fixed — `lnl-empty`/`lnl-empty2` (`ON KEY GOSUB 100,,600`,
      `ON STRIG GOSUB ,300`) match the reference byte-for-byte with the special
      case gone.
      ⚠️ **Two of my own rows were CONFOUNDED and are written up as such**:
      `lnl-colon` carries a *name* behind its colon (so it could not measure the
      colon at all — `lnl-colsep` does), and all three `CALL` rows had their
      digit eaten by the device-name scan (filed above; `lnl-callpar` got past it
      with a `(`). Seven knives, all run and reverted, each with a RED set **and**
      surviving GREEN controls.
      `dot-goto` **retired** from `KNOWN_DIVERGE` — the fourth cohort to leave it
      that way, and not one has rotted.
      Spec [`docs/spec-basic-lnlist.md`](docs/spec-basic-lnlist.md),
      measurement [`docs/lnlist-msx1-characterization.md`](docs/lnlist-msx1-characterization.md).


- [x] ✅ **`.` IS AN IDENTIFIER CHARACTER TO THE TOKENISER — LANDED 2026-08-01,
      148/148, NET −10 B, all sub-ROM.** Split out of D-NAMBLANK, which filed it
      from two rows and did not fix it. Spec
      [`docs/spec-basic-namedot.md`](docs/spec-basic-namedot.md), measurement
      [`docs/namedot-msx1-characterization.md`](docs/namedot-msx1-characterization.md).
      Two rules, both in one five-line dispatch arm:
      **R-D1** a `.` behind a LIVE name state continues the identifier;
      **R-D2** a `.` with the state DEAD begins a numeric constant **and the
      digit is OPTIONAL** — a bare `.` is the single literal 0.
      🔴 **THE FILED PRESCRIPTION WAS REFUTED BY MEASUREMENT, AND THAT WAS THE
      WHOLE SHAPE OF THE SLICE.** This item said in as many words that
      [`basic/vars.asm`](basic/vars.asm)'s run-time scan *"has to accept `.` as
      well, or the executor looks up a different variable than the tokeniser
      stored"*. **The reference does exactly that forbidden thing**: `B.5=7` and
      `A=B.5` both raise `Syntax error` (ERR=2) against a `B5=7` control reading
      ERR=0 — the crunch's identifier charset and the executor's are *different
      charsets* on MSX1. Knife **K4** made the prescribed change and turned both
      rows ERR 2 → 0, i.e. **the filed fix would have shipped a live divergence
      in the exact place the item pointed at**. So `vars.asm` was never touched,
      neither were `DEFINT`/`DEFSNG`/`DEFSTR`, `VARPTR`, `FOR` variables,
      `DIM`/array names or `INPUT`/`READ` targets, and the whole change is
      **sub-ROM only** — both main ROMs byte-identical to the parent commit,
      asserted by hash.
      🔴 **AND THE ROWS THAT FOUND R-D2 WERE WRITTEN TO BE CONTROLS.**
      `20 A=.B` and `20 .A=1` were filed as predicted-green two-sided cells and
      both refuted their own prediction: the reference stores `$1D,0,0,0,0`, so a
      `.`-led literal never needed its digit. That deleted the one-character
      lookahead instead of extending it — the correct rule was **smaller** than
      the wrong one, the D-EXPBAD shape.
      🔴 **A `<none>` READING ON BOTH REFERENCES WAS NOT AGREEMENT.** The first
      `dotd` payloads printed no closing `]` *because the behaviour under test
      aborted the statement*, so every side read `<none>` and compared EQUAL —
      the trap filed one item below. Reading the SCREEN found the `Syntax error`
      that became R-D3; the rows were re-asked through `ERR`, which prints its
      brackets whether or not the statement aborts.
      Five knives, all run and reverted: K1/K2 separate R-D1 from R-D2, **K3**
      separates R-D1 from *"a `.` is always an identifier char"* (a distinction
      neither filed row could make), K4 above, K5 shows the dot must **set** the
      name state. ⚠️ **K1 and K5 each refuted a predicted-GREEN control** —
      corrected in place, spec §7.1 — and a K1 `REFUSED` turned out to be a
      dropped keystroke that re-ran clean alone (§7.2).
      `nam-dot`/`nam-dot0` retired from `KNOWN_DIVERGE`; `dot-goto` filed above.

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

- [x] ✅ **DECIMAL LITERAL SCANNER AND EMBEDDED BLANKS — LANDED 2026-07-31,
      81/81, 39 B, all sub-ROM.** Split out of D-LNBLANK, where it was the
      *unfiled* half of the finding. Blank-transparency is **not** a property of
      the line-number scan;
      it is a property of the decimal number scanner, and the line number is one
      of its customers. Measured byte-exact on the VG-8020 **and** the CF-3300,
      which agree ([`docs/lnblank-msx1-characterization.md`](docs/lnblank-msx1-characterization.md) §1/§11 D):
      ```
      20 A=1 0     ref -> A <EF> <0F><0A>   (the single literal 10, = `A=10`)
      20 A=1 . 5   ref -> A <EF> <1D>A<15><00><00>   (1.5, across TWO blanks)
      20 A=1E 2    ref -> A <EF> <1D>C<10><00><00>   (100)
      ```
      ⚠️ **And it does NOT reach everywhere** — the bounding controls are already
      measured and must stay green: a **hex** literal does *not* skip
      (`&H1 F` → `&H1` then ` F`), nor a **string** literal (`"1 0"`), nor a
      **REM** tail, and a variable name keeps its blank (`A B` stores `A B`).
      A fix written as "make the crunch's digit fetch blank-transparent" is
      therefore **wrong**, and only the hex row says so.
      Spec [`docs/spec-basic-decblank.md`](docs/spec-basic-decblank.md),
      measurement [`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md)
      (32 new rows, four oracle-lock rounds, both machines agree on every one).
      **Baseline 9/29; the five `lit-` `KNOWN_DIVERGE` entries are RETIRED.**
      🔴 **THE FILED ROWS WERE A SAMPLE, AND THE DENOMINATOR MOVED THE FIX TWICE.**
      1. **`20 A=1 +2` KEEPS ITS BLANK** (and `1  +2` keeps both). Every row filed
         with the item put the blank *between two things that both belong to the
         number*, so none could tell "skips blanks" from "skips blanks and keeps
         the ones it did not use". The rule is **the cursor reported is one past
         the last character actually CONSUMED** — and it is *not* the line
         number's rule, which eats exactly one separator blank. "Copy
         `parse_lineno`" would have been wrong, and only a row with a NON-digit
         past the blanks says so.
      2. **A FIFTH SITE, IN THE OTHER FILE.** `20 A=. 5` is 0.5 on both
         references. That decision is taken in `tk_loop`'s `'.'` dispatch
         ([`basic/tokenise.inc`](basic/tokenise.inc)) *before* `tk_float` is
         entered, so no change inside the scanner could reach it.
      The rule also reaches further than the item said: the dot from **either**
      side, the exponent marker, its **sign**, its **own digit run**
      (`1E 2 3` = 1E23), and the type suffixes — `20 A=1 #` is a **DOUBLE** on the
      reference, i.e. the divergence was in the token's TYPE.
      **Cost: 39 B, ALL sub-ROM page 0** (4057 → 4018 B free); main page 1 stayed
      at 8 B and the low region at 23 B, and `basic-reloc.rom` came out
      **byte-identical** — the whole space worry was checkable in one hash.
      🔴 **AND THE FIRST CUT WAS CATASTROPHIC WHILE THE BUILD WAS GREEN**: `pop af`
      is how the saved cursor is discarded, but **it LOADS A**, so placed before
      the digit was extracted it fed the source pointer's high byte to the
      accumulator — `A=1` crunched to the integer **187** and `A=1E2` refused the
      line. Dead-code gate green, main ROM byte-identical, diff reads correctly.
      The first gate run caught it.
      Falsified on five knives (K1–K5), each with its own witness and each pairing
      a red row with a GREEN control.

- [x] ✅ **THE `$0E` LINE-NUMBER REFERENCE — CLOSED BY D-LNREF 2026-08-01.**
      Filed as *"missing for LIST/DELETE/AUTO/RENUM/ELSE"*.
      🔴 **THE FILED LIST WAS WRONG IN BOTH DIRECTIONS, and only a walk of all
      162 reserved words could say so.** The reference arms on **fourteen**
      words, not five. Three of the filed five (`DELETE` `AUTO` `RENUM`) have no
      zerobas token at all, so their rows diverge for a SECOND reason and can
      attribute nothing — they are the keyword-gap item below, not this one. And
      three the item never named DO arm: **`RETURN` (`$8E`)**, **`ERL` (`$E1`)**
      and `LLIST` (`$9E`) — the first two are tokens zerobas already emits, so
      they were this defect and nobody had looked at them.
      🔴 **It is a LIST, not a range or a threshold.** `IF` (`$8B`) sits
      *between* four arming tokens; `ERROR`/`RESUME`, `TO`/`THEN`, `ERR`/`ERL`,
      `RENUM`/`DEFSTR` are adjacent pairs split across the boundary.
      🔴 **And one missing arm was a LIVE RUNTIME DEFECT.** `IF 0 THEN 20 ELSE
      30` raised **`Syntax error`** — `if_false` has always tested
      `cp LINENO_TOKEN` after the `$A1`, so the feature was written, reachable,
      and had never fired.
      Landed: four arms (`LIST` `ELSE` `RETURN` `ERL`) **+28 B sub page 0**, and
      `ev_f` learned the `$0B..$0E` family at **NET −1 B on main page 1**
      (5 → 6 B free) — `ERL=<n>` puts a `$0E` inside an expression.
      Spec [`docs/spec-basic-lnref.md`](docs/spec-basic-lnref.md), measurement
      [`docs/lnref-msx1-characterization.md`](docs/lnref-msx1-characterization.md).

- [x] ✅ **`DELETE` / `AUTO` / `RENUM` / `LLIST` — THE TOKEN HALF CLOSED BY
      D-KWGAP4 2026-08-01.** Filed as *"they have no token — and whoever adds
      them must add the arming byte too."* That was right, and it was one half
      of the surface: a missing **token** and a missing **statement**. The token
      half is now byte-exact on all four verbs; the statement half is re-filed
      immediately below with its numbers.
      Landed: four equates, four `kwtable.inc` entries and four `branch_lineno`
      arms — **+48 B, ALL sub-ROM page 0** (3958 → 3910 B free), and
      `basic-reloc.rom` / `zerobas-main-eu.rom` **byte-identical**, which is the
      hard equality a sub-ROM-only change allows. Low **9 B** and page 1 **6 B**
      untouched.
      🔴 **THE SEVEN `KNOWN_DIVERGE` PINS D-LNREF SPENT ITS EMPTY ALLOWLIST ON
      FIRED EXACTLY AS DESIGNED, AND WERE DELETED RATHER THAN UPDATED.** Sixth
      cohort to retire that way, none has rotted; `lnblank-acceptance`'s
      allowlist is EMPTY again. `lna-renum3`/`-auto2`/`-delrng` also left
      `INFORMATIONAL` — their attribution argument was precisely what this
      closed.
      🔴 **ADDING A TOKEN FOR AN UNDISPATCHED STATEMENT CHANGED NOTHING AT RUN
      TIME, AND THAT WAS MEASURED ON BOTH SIDES OF THE CHANGE.** The filed
      hazard ("a token may turn a working garbage parse into a new error class")
      is real in general and empty here: all four already raised **ERR 2** by
      four *different* accidental parses (`DE`+`LET`+`E`, `AU`+`TO`,
      `RENUM` verbatim, `L`+`LIST`) and now raise it by one deliberate path
      (`es_noentry` → `stmt_error`). New batteries `kwgd` (5 rows, three sides)
      and `kwgz` (5 rows, **zerobas only** — `AUTO` is interactive and `LLIST`
      hangs an unplugged `LPTOUT`, so `SIDE_LOCK` refuses a reference).
      🔴 **AND THE ECHO GUARD HAD NEVER SEEN A `--say` PAYLOAD IN THIS PROBE.**
      `--echo` shared the measurement pass's `SAY_ONLY` filter, so
      `--echo --only lnrd-` answered *"no rows selected"* — D-LNREF's spec §6
      claim covered the 210 rows the filter left. Fixed; all seven `lnrd` rows
      now read `ECHOED` on three sides. `--echo --say` is refused (combined, the
      say pass won inside `run_side` and `main()` printed an echo-FAILURE banner
      over readings that were never echo verdicts).
      Six knives, each with a predicted RED set **and** predicted GREEN
      survivors, all matched — including two predicted-GREEN ones (K3 table
      order, K6 list-vs-range) and K5, which aims at the *justification* and
      measured the 3 B/entry figure the scope decision rests on.
      Spec [`docs/spec-basic-kwgap4.md`](docs/spec-basic-kwgap4.md), measurement
      [`docs/kwgap4-msx1-characterization.md`](docs/kwgap4-msx1-characterization.md).
      ⚠️ **`INPUT$` IS NOT ABSENT** — `20 INPUT$ 10` reads `<85>$ <0F><0A>` on
      all three sides. The reference has no distinct token either, so zerobas is
      already byte-exact and the coverage sweep's "34 genuinely absent" is one
      too many. The `INTERVAL` shape, found by D-LNREF's walk. Still open.

- [x] ✅ **`DELETE <range>` — LANDED 2026-08-02 (D-DELETE), 34/34, six knives,
      `kwgd-delete`'s pin RETIRED.** Filed 2026-08-01 by D-KWGAP4; spec
      [`docs/spec-basic-delete.md`](docs/spec-basic-delete.md), measurement
      [`docs/delete-msx1-characterization.md`](docs/delete-msx1-characterization.md).
      🔴 **THE TWO ENDS OF THE RANGE ARE NOT SYMMETRIC, AND ONLY A CONTIGUOUS
      WALK COULD SAY SO.** The HIGH end must name a stored line **exactly**; the
      LOW end need not name anything at all. `DELETE 15-30` deletes lines 20 and
      30 without complaint; `DELETE 20-35` deletes **NOTHING** and raises ERR 5 —
      the same shape with the missing number moved across the `-` (` 9  0 ` vs
      ` 15  5 `). Four more the filed one-line row could not have carried:
      * **the existence check runs BEFORE the first deletion** — `DELETE 20-35`
        leaves lines 20 *and* 30 standing, which an implementation that deleted
        as it walked could not do;
      * **a REVERSED range is a SECOND rule, not the same one.** `DELETE 30-20`
        is ERR 5 even though line 20 exists, so R-D2 passes and a machine
        deleting the empty range would read ` 15  0 ` (`dlt-rev`);
      * **a FAILED `DELETE` is a COMPLETE no-op** — variables and the `CONT`
        point both survive (`dlt-varsbad`/`dlt-contbad`). ⚠️ **No round-1 row
        could see this**: every failure row `RUN`s afterwards and `RUN` clears
        the variables itself. It took a round-2 cut;
      * **`DELETE` ENDS the line and the program.** Inside a `RUN` nothing
        further executes (`dlt-inprog`); in direct mode `DELETE 20:B=9` leaves B
        at 0 with **ERR 0** — the `:` is accepted and then abandoned, not
        rejected (`dlt-tail`, against `dlt-tailctl`'s ` 9  0 `).
      🔴 **AND `DELETE 10-65529` IS ERR 5** — the natural *"everything from line
      10 on"* idiom. Every round-1 high end that failed sat inside the program's
      span, so *"a line numbered exactly `hi` must exist"* and the far weaker
      *"`hi` must not be past the last line"* agreed on all of them;
      `dlt-hipast`/`dlt-hitop` are the round-2 rows that separate them.
      🔴 **A DEFECT IN `CONT`, NOT IN `DELETE`, AND THE ROW THAT SAYS WHOSE.**
      `dlt-cont` read ` 0  0 ` against ` 0  17 ` the first time zerobas had a
      handler. The obvious reading — "DELETE fails to invalidate CONT" — is
      refuted by its own `A` of 0, which proves the edit reset *did* run.
      `ex_cont_no` printed *can't continue* and **never set `ERRFLG`**;
      `err_msgtab` had mapped ERR 17 → `err_cont` all along. `dlt-contbare` (a
      bare `CONT`, no DELETE anywhere) is the attribution row. +5 B.
      Landed: 3 B `stmt_table` row + a **34 B** marshalling head on main page 1,
      the WHOLE verb (parse, both validations, the delete walk) as
      `LE_OP_DELRANGE` in `sub/lineedit.asm` — **194 B of sub page 1**, which had
      3339 B free. A resident parse would have cost ~88 B of page 1 against 34;
      knife K6 measured that claim rather than leaving it an estimate. Page 1
      **124 → 82 B**, low **23 B untouched**.
      ⚠️ **`.` — the CURRENT-LINE pseudo-line-number — is MEASURED and
      DECLINED**, not overlooked: `dlt-dotedit` says it is the line the editor
      **last touched** (not the highest — `dlt-dot` alone could not tell those
      apart). It is shared with `LIST`/`AUTO`/`RENUM`/`EDIT`, zerobas records
      nothing of the kind, and what `.` means after a `RUN` / an error / a `LIST`
      is unmeasured. Its own item is filed below; `dlt-dot`/`dlt-dotedit` are
      pinned so it cannot be forgotten.

- [x] ✅ **~~`AUTO` / `RENUM` / `LLIST` ARE STILL NOT EXECUTED~~ — MEASURED
      FALSE 2026-08-09** by the TODO staleness sweep,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.2. **All three execute.** The entry's OWN program, re-run on three
      sides:

      | row | program | VG-8020 | CF-3300 | zerobas |
      |---|---|---|---|---|
      | `e.ctl` 🟢 | `10 A=1` / `20 A=2:END` / `GOTO 20` / `PRINT"[";A;ERR;"]"` | ` 2  0 ` | ` 2  0 ` | ` 2  0 ` |
      | `e.renum` | …`RENUM 100` / `GOTO 110` / `PRINT"[";A;ERR;"]"` | ` 2  0 ` | ` 2  0 ` | **` 2  0 `** |
      | `e.renumlst` | …`RENUM 100` / `LIST` | `100 A=1｜110 A=2:END` | idem | **idem** |

      `AUTO` and `LLIST` cannot be put to a REFERENCE in this harness (see the
      ⚠️ at the foot of this entry), so they are settled by the gate that owns
      them: **`make editverb-acceptance` → 61/61 rows across 3 sides (2
      reference)**, run at `e2810c6`, eleven `aut-` rows and twelve `llt-`
      printer rows included.
      🔴 **AND ITS OWN CLOSURE HAS BEEN AT THE TOP OF THIS FILE SINCE
      2026-08-06.** D-EDITVERB's `- [x]` entry in §"Open — standing residuals"
      says *"`AUTO` / `RENUM` / `LLIST` — the STATEMENT half, CLOSED 2026-08-06
      … gated by `make editverb-acceptance` at 61/61 rows on three sides"*. The
      open item and its own closure coexisted for three days, in one document,
      because nothing re-reads the pickup list.
      **What was believed, kept as the record of why:** re-filed 2026-08-01
      by D-KWGAP4, narrowed 2026-08-02 by D-DELETE. The crunch is the
      reference's byte for byte; all three are a **Syntax error** at run time.
      Measured, both references agreeing:
      ```
      10 A=1 : 20 A=2:END : RENUM 100 : GOTO 110   refs -> A=2 ERR 0   zb -> A=0 ERR 8
      ```
      `kwgd-renum` is **pinned as `KNOWN_DIVERGE`** in the say gate, so the day a
      handler lands the gate says so.
      ⚠️ **THE WALL MOVED AND THE FILED VERDICT DID NOT.** D-KWGAP4 costed four
      dispatch rows at 3 B each (its knife K5 — still the right rate) against a
      page 1 with **6 B** free, and concluded the rows alone did not fit.
      D-RETLN's 160 B dead-instruction carve took page 1 to 124 B; D-DELETE spent
      42 of those and left **82 B**. Space is no longer the reason. **Re-measure
      from a clean build before citing any byte figure written before
      2026-08-02.**
      What still blocks each one is its own body: **`RENUM`** needs a two-pass
      old→new map over every line number *and* every `$0E` reference including
      `ON..GOTO` lists; **`AUTO`** must drive the line editor (a sub-ROM page-1
      tenant) from a main-ROM statement; **`LLIST`** is cheapest — a printer sink
      exists ([`basic/print.asm:401`](basic/print.asm:401), `PRDEST=1` →
      `LPTOUT`) and `ex_list` exists, so its handler is "set the sink, jump to
      `ex_list`" — but it would inherit the filed `ex_list`-ignores-its-argument
      defect below.
      🎯 **D-DELETE is the worked precedent for all three**: the whole verb goes
      into an existing sub-ROM page-1 tenant and main pays a ~34 B marshalling
      head, with `LE_STATUS` carrying the ERR code back
      ([`docs/spec-basic-delete.md`](docs/spec-basic-delete.md) §3.1).
      ⚠️ **`AUTO` and `LLIST` CANNOT BE PUT TO A REFERENCE IN THIS HARNESS** —
      interactive line-entry and an unplugged-`LSTOUT` hang, the same reasons the
      keyword sweep already files them among its 18 crunch-only holes. `omsx_repl`
      raises `SystemExit` at its 240 s cap, so such a row does not degrade a run,
      it kills it. Whoever implements them needs a plugged printer
      ([[openmsx-printer-pluggable]]) or a different instrument first.
      ✅ That last ⚠️ is the one clause of this entry that survived: D-EDITVERB
      resolved it rather than refuting it — openMSX's `plug printerport logger`
      reports READY unconditionally so `LLIST` cannot block, and Ctrl-STOP is a
      key-matrix combination `keymatrixdown` can deliver. Both verbs are now
      measured on both references, which is what the 61/61 is.

- [x] ✅ **D-LASTINJ — THE LAST INJECTOR COPY, AND THE SUITE NOBODY PRICED —
      LANDED 2026-08-04.** Spec
      [`docs/spec-probe-lastinj.md`](docs/spec-probe-lastinj.md),
      characterisation
      [`docs/lastinj-characterization.md`](docs/lastinj-characterization.md).
      **Apparatus only — one probe file, a new `tools/check_probe_injectors.py`,
      one Makefile target; no `basic/`, `sub/`, `disk/` or `tape/` source touched,
      no ROM rebuilt (`make -q build/zerobas-main-eu.rom` exit 0 throughout).**
      Closes the two items D-LATCH §6 filed and did not do.
      🔴 **BOTH FILED ITEMS RESTED ON A NUMBER OR A CLAIM NOBODY HAD CHECKED.**
      Item B's stated reason ("no Makefile target runs it") was FALSE — three
      structural readings falsify it without booting anything. Item A's stated
      cost (~3.5–4 h) was wrong by ~25× — the run is **8 min 58 s**. Two filed
      items, two justifications, neither measured, both wrong in the direction
      that deferred work.
      🎯 **204/204 gating rows agree**, exit 0, **zero** delivery announcements
      (stderr 0 bytes), and the guard was proven ARMED on say rows by a knife
      before that zero was read as a finding.
      🎯 **The copy was the frozen fault verbatim** — character-identical (after
      constant folding) to `latch_check.OLD_KEY`. Measured **latent, not
      harmless**: 0 of 16 slots at `$1197`, but slot 11 landed at `$119B` inside
      `chget`'s wait loop and the swallow law's precondition held **15/15**.
      🔴 **K2 says where `diskbasic-acceptance`'s sensitivity comes from.** With
      delivery mangled and only the probes' `== EXPECT` gutted, the runner reports
      `34/34`-shaped `ALL CONVERGED`, exit 0, over `records: []`. It checks an
      exit code and that `CF-3300` appeared; **all 34 registry rows inherit that**.
      🔴 **A knife of this slice's own failed to cut, and that was the finding**
      ([[knife-found-defect-in-own-fix]]): `injector-check`'s negative control
      emitted no `debug write memory` at all, so it was clean for a trivial reason
      and the "flag everything" half of its two-sided self-test was decorative.
      Rebuilt as a probe that pokes an unrelated address; both halves bite now.
      **K5's prediction was wrong in the safe direction** and is recorded as wrong
      rather than rewritten: gutting the verdict trips the frozen self-test first
      (`CANNOT JUDGE`, rc 2) instead of producing a green walk over a dirty tree.
      **Corpus:** unit 57/57 · preflight-check 0 unguarded · injector-check 0
      offenders · latch-check 9/9 · diskbasic-acceptance 34/34 ·
      lnblank-say-acceptance 204/204.

- [x] ✅ **D-LATCH — THE TRIGGER IS ONE INSTRUCTION WIDE — LANDED 2026-08-04.**
      Spec [`docs/spec-probe-latch.md`](docs/spec-probe-latch.md),
      characterisation
      [`docs/latch-trigger-characterization.md`](docs/latch-trigger-characterization.md).
      **Apparatus only — `probes/lib/omsx_repl.py`, a new
      `probes/lib/latch_check.py` and one Makefile target; no `basic/`, `sub/`,
      `disk/` or `tape/` source touched, no ROM rebuilt.** Closes D-DELIVER §9.1 /
      D-ECHO §6, the last open half of the delivery race.
      🎯 **The trigger is the instruction boundary at `$1197`** — between C-BIOS
      `chget`'s `ld hl,(GETPNT)` (`$1194`) and `ld de,(PUTPNT)`. An injector that
      moves GETPNT BACKWARDS is invisible to a CPU that latched it one
      instruction earlier, so `ld a,(hl)` reads the fresh buffer from
      `KEYBUF + N`. That is the swallow law, the alignment sensitivity, and why
      `step` "fixes" one case and not another, all from one register.
      **2039 slots across seven instrumented batches: 6 at `$1197`, 6
      mis-deliveries, none anywhere else.** Forced with a breakpoint at that
      address it mangles **every** time (4 predecessor lengths, 4 exact hits) and
      the three neighbouring boundaries deliver intact.
      🔴 **The hypothesis on file was inverted.** Nothing saves or restores a
      `GETPNT` — C-BIOS writes it in exactly three places and none of them is a
      restore. What survives the injection is a **register copy**. Right
      arithmetic, wrong object, and it would have sent the fix at a save site
      that does not exist ([[latch-trigger-is-a-register-not-a-save]]).
      🔴 **D-ECHO's "26-byte predecessor delivers clean" row was a PARTIAL
      READING.** It hits the trigger too (`HL = KEYBUF+26`); the swallow simply
      exceeds the payload, so the line arrives after garbage and the ECHO oracle
      cannot see it — the STORED oracle flags a spurious line `0`. The oracle
      that was asked was the blind one ([[readout-blind-to-its-own-subject]]).
      **Fixed at source:** `key_proc` writes at the current GETPNT and never
      moves it — immune by construction, not by alignment. Forced at `$1197`:
      100 % mangled → **0 %**. Phases O and Q2 go from 3 mis-deliveries to **0**.
      **`make latch-check` is the replacement positive control** and it is not
      optional: cross-oracle disagreement was the only live subject either
      delivery oracle had (D-ECHO §3.5), and fixing the race silences it forever
      ([[fixing-the-fault-silences-the-control]]).

- [x] ✅ **`lnblank-say-acceptance` WAS NOT RUN FOR D-LATCH — RUN 2026-08-04 BY
      D-LASTINJ, AND THE COST THAT DEFERRED IT WAS WRONG BY ~25×.**
      **204/204 gating rows agree** across `vg8020,cf3300,zb`, exit 0, and
      **zero** `MIS-ECHOED` / `MIS-DELIVERED` / `ORACLES DISAGREE` /
      `APPARATUS FAILURE` lines — stderr was **0 bytes**. No row moved, so the
      attribution path against `HEAD~1`'s injector was never needed. The D-LATCH
      injector change is priced across the last corpus member that had not seen
      it, and it costs nothing.
      🔴 **The zero was not accepted on its own.** This probe's own history is
      [[echo-guard-never-saw-say-rows]] — the `SAY_ONLY` filter once removed every
      one of these rows from the echo pass, so the guard reported zero BY
      CONSTRUCTION. With `key_proc` monkeypatched to swallow one byte per
      injection the same `--say --gate` rows produce `APPARATUS FAILURE` + five
      `MIS-ECHOED` announcements and rc 1; the identical unpatched subset is
      silent, rc 0. Knife fires, control silent, same session.
      🎯 **~3.5–4 h on file; 8 min 58 s measured**, `repack-machine` included —
      612 boot-per-case runs at ~0.9 s each. The figure predates the harness
      dropping sleep-polling and had never been re-measured. **A stale cost
      estimate is a standing argument for not running a gate**, and it won that
      argument once already: it is why D-LATCH skipped this suite. Corrected in
      [`Makefile`](Makefile) and here rather than left to be re-derived.

- [x] ⚠️ **THE SECOND LATCH WINDOW IS OPEN AND HAS NEVER BEEN OBSERVED.** A CPU
      inside C-BIOS `chget_char` (`$11A2`–`$119D`) holds an `HL` it is about to
      write back to `GETPNT`; an injection landing there advances GETPNT past the
      new payload by `HL - KEYBUF + 1`. It needs a NON-drained buffer, and the
      buffer was measured drained before **2039/2039** injections (D-LATCH) and
      490/490 (D-DELIVER) — but that is a measurement, not a proof, and it is why
      both delivery oracles stay armed after the fix
      ([`docs/spec-probe-latch.md`](docs/spec-probe-latch.md) §2.5).
      ✅ **CLOSED 2026-08-04 BY D-LATCH2**
      ([`docs/spec-probe-latch2.md`](docs/spec-probe-latch2.md),
      [`docs/latch2-window-characterization.md`](docs/latch2-window-characterization.md)).
      🔴 **THE WINDOW IS REAL AND `key_proc` WAS VULNERABLE TO IT.** Manufactured
      by breakpointing INSIDE `chget_char`, which the CPU enters **only** when
      `GETPNT != PUTPNT` — so the precondition and the force are ONE instrument,
      and the thing that made this unobservable for 2529 injections made it
      reproducible on demand. **44 of 46 predicted values hit exactly**; both
      misses were mine and both are recorded.
      🔴 **AND THREE FILED NUMBERS WERE WRONG.** (1) `$11A2`–`$119D` is not a
      range — it is `$11A3`–`$11AD`, and `$11A2` is on the SAFE side. (2)
      `HL - KEYBUF + 1` is the PRE-D-LATCH injector's swallow; the shipped one
      swallows **exactly 1, independent of k**, a number nothing on file
      predicted [[filed-justification-is-a-claim]]. (3) `latch-check`'s own
      *"~40 s"* is **2.05 s**, timed on HEAD — and that stale figure propagated
      straight into this slice's own ≈20 s estimate (measured **3.1 s** for 16
      rows) [[stale-cost-estimate-defers-gates]].
      🎯 **D-LATCH's fix OPENED a sub-window its predecessor could not reach**:
      `$11AA` (`ld hl,KEYBUF`) needs the consuming pointer to cross `KEYBUF+40`,
      which an injector that resets `GETPNT := KEYBUF` every time can never do.
      Fixed at source — `__key` will not write into a buffer the machine is
      still consuming (bounded deferral; the bound is **4× the buffer's own
      worst-case drain**, measured 10 retries / 20 ms for the maximum 39-byte
      pending line, and **10 % of `ECHO_GAP`**, past which the echo guard would
      judge a line that had not landed). `make latch-check` **16/16**, rows
      D/E/F, with THIS era's injector frozen as row D's subject
      [[fixing-the-fault-silences-the-control]] and row E scoring the deferral
      COUNT so the guard is green because it FIRED. Knives K2–K5 all cut
      (13/16 exit 1, or `CANNOT JUDGE`). New host pin `tests/test_key_drain_guard.py`
      — the D-LATCH invariant had **no** host-level test at all until now.

- [x] ⚠️ **`make injector-check` CLASSIFIES ITS OWN DETECTOR AS AN INJECTOR.**
      D-LATCH2's host test went red on it: the test emits no Tcl and boots
      nothing, but its `debug write memory` is the **needle of a regex** that
      asserts `key_proc()` does not write GETPNT, and it names the cursors
      because those are the addresses it checks. Closed for now as a fourth
      named structural exemption — the mechanism that gate provides — rather
      than by renaming the needle to slip past it, which would leave the next
      reader unable to tell evasion from innocence. **The open question is
      whether the classifier should distinguish a literal that is EMITTED from
      one that is MATCHED AGAINST**; it fails closed today, which is the right
      direction, but every future assertion-about-injectors file will need an
      exemption ([`docs/latch2-window-characterization.md`](docs/latch2-window-characterization.md) §10.1).
      ✅ **CLOSED 2026-08-05 BY D-INJSINK**
      ([`docs/spec-probe-injsink.md`](docs/spec-probe-injsink.md)).
      🔴 **BOTH filed claims were wrong, and the second one was hiding a live
      false negative.** The host test *could* be written non-evasively — the
      write format is `omsx_repl`'s to own, not the test's, and moving it to
      `omsx_repl.tcl_writes()` (a **bool**-returning predicate, so nothing can
      be composed out of it) leaves the test classifying `CLEAN` on the literal
      rule with zero residual occurrences (§2.1). Fourth filed justification
      running to be wrong [[filed-justification-is-a-claim]].
      🔴 **And "emitted vs matched against" is the wrong axis.** Measured
      (§2.3): the host test has **two** WRITE-bearing literals — the regex
      needle *and the docstring sentence beside it*. A per-literal sink
      whitelist clears the needle and not the prose, so it does not clear the
      file it was for; the all-uses rule that would clear prose is defeated by
      `return build([..., OLD_KEY])`, an ordinary probe shape. **No emit/match
      rule shipped**, and §2.3 says why in measurements rather than prose.
      🔴 **The real defect: the gate was blind across module boundaries.**
      `import latch_check; return latch_check.OLD_KEY` ships the pre-D-LATCH
      injector **verbatim** — the body `latch-check` row A requires to MANGLE —
      and the gate at `07e9c0a` scored that planted file **`ALL PASS`, 258
      files, 0 offenders, rc 0** (K3b). Closed by rule (b): naming a
      frozen-body symbol defined in another module IS the offence, no use
      analysis to fool. The registry is **generated** (5 symbols, 2 modules,
      basename-collision-free over 257 files) and **pinned** — an empty
      registry is `CANNOT JUDGE`, not a clean walk.
      🎯 **The exemption list does NOT shrink; it stops growing, and each entry
      now states a CLASS that is partly machine-checked** — `SHIPS` (1),
      `HOLDS` (2), `HANDLES` (1). A `HANDLES` file must carry no
      `debug write memory` literal of its own, and K5 shows the check bites:
      plant one back and the run is `BAD EXEMPTION`, rc 1; remove the
      validation and the identical plant scores `0 offenders`, rc 0.
      Self-test is now **four** frozen bodies, two per rule, each pair
      two-sided. Knives K1–K6 all cut, each with a GREEN control in the same
      session; **K1's prediction was wrong in its mechanism and is recorded as
      wrong** (§4bis.3). Corpus: `unit-test` **58/58** · `injector-check` 0
      offenders / 257 · `preflight-check` 0 unguarded · **`latch-check` 16/16**
      · **`diskbasic-acceptance` 34/34** · `deadcode` 0/0. `key_proc()` output
      **byte-identical** (730 B, sha `f936ab2a…`), so no probe's delivery
      alignment moved.

- [x] ✅ **`injector-check` IS STILL A TEXT CLASSIFIER — CLOSED 2026-08-06 by
      D-INJJUDGE** ([`docs/spec-probe-injjudge.md`](docs/spec-probe-injjudge.md)),
      as a measured DECLINE on the predicate plus a denominator fix. Over all
      **982** commits a folding predicate and a maximally eager literal-soup
      predicate each differ from the shipped rule in **0** commits, so the class
      below has never been exercised and no text rule improves on what shipped.
      What WAS open is one level out: `SCAN_DIRS` named three directories, and
      **three files outside them compose the pre-D-LATCH body** — invisible for
      252, 237 and 229 commits while this gate printed *"ALL PASS — one injector
      in the tree"*. See the index entry at the top of this file. The stated
      limits below stand as written; they are simply not the load-bearing ones.
      Original filing:
      ([`docs/spec-probe-injsink.md`](docs/spec-probe-injsink.md) §6).
      What passes, measured on the shipped gate rather than assumed:
      a **split literal** (`"debug write" + f" memory {G} 0"` → `CLEAN`), and any
      body that reaches the cursors by a spelling neither rule knows. Neither is
      a careless-author shape — the six real copies were all verbatim — so this
      is a stated limit, not a filed defect.
      🎯 What is NOT a hole, re-measured after the coverage note first claimed it
      was: a frozen body laundered through a local call
      (`return build([…, OLD_KEY])`) **is caught**, `HANDLES`, along with
      `import M as L`, `from M import N as K` and `from M import *`. Rule (b) is
      blunt on purpose — the offence is naming the body, not what happens to it
      afterwards.
      ⚠️ **An EXEMPT file is trusted by construction.** `HANDLES` is machine-
      checked (no write literal of its own); `SHIPS` and `HOLDS` are not, and
      cannot be — they exist to hold injector bodies. The mitigation is that
      there are three of them and each is a slice-sized decision
      [[exemption-as-a-checked-claim]].
      ⚠️ **Rule (b) resolves modules by BASENAME.** Collision-free across all 257
      files today, and measured so on every run; a future duplicate basename
      resolves to both, which is the eager direction.

- [ ] ⚠️ **THE DELIVERY GUARDS DO NOT COVER PROBES WITH THEIR OWN `build_tcl`.**
      Every `probes/disk/*` script and `basic_probe_printusing.py` build their own
      Tcl and never reach `omsx_repl._tcl`, so neither the stored-program oracle
      nor the echo oracle sees them. Not enumerated; not known to be affected.
      🔴 **D-LATCH promoted this from a COVERAGE item to a CORRECTNESS one.** A
      local copy of the pre-D-LATCH `__key` — write at `KEYBUF`, reset `GETPNT` —
      still has the race the shared injector no longer has, and still has no
      oracle that would notice.
      ✅ **The five trap probes are DONE** (`interval`, `key`, `sprite`, `strig`,
      `stop`): each held a byte-identical copy, each now calls
      `omsx_repl.key_proc()`, and all five gates were re-run green.
      ✅ **CLOSED 2026-08-04 BY D-LASTINJ**
      ([`docs/spec-probe-lastinj.md`](docs/spec-probe-lastinj.md),
      [`docs/lastinj-characterization.md`](docs/lastinj-characterization.md)).
      🔴 **AND "no Makefile target runs it" WAS FALSE.** `make diskbasic-acceptance`
      dispatches `disk_probe_getput.py` as registry row `GET/PUT`
      (`probes/disk/diskbasic_acceptance.py:81`), and a SECOND row (`OPEN(LEN=)`)
      imports its driver — so it was scored all along and sat inside D-LATCH's own
      corpus under the name `diskbasic`. The question asked was *"is there a target
      called `getput`?"*; the load-bearing question was *"is this file scored?"*
      ([[readout-blind-to-its-own-subject]] reached through a naming convention).
      Its `__inj` was **character-identical** (after constant folding) to
      `latch_check.OLD_KEY` — the body row A forces and requires to MANGLE.
      🎯 **Measured latent, not harmless:** 0 of 16 slots at the trigger, but slot
      11 landed at `$119B` INSIDE `chget`'s wait loop, and the swallow law's
      precondition held at **15/15** slots with a predecessor. Re-pointed at
      `key_proc()`; `2/2` before and after, `34/34` full gate.
      🔴 **`make injector-check` now GENERATES the list** instead of a reader
      maintaining it (`tools/check_probe_injectors.py`, spec §3.4): AST, not grep
      — a file offends when its STRING LITERALS emit `debug write memory` and it
      NAMES a type-ahead cursor. 256 files, 3 structural exemptions, fails CLOSED.
      It found the one copy that existed (exit 1) BEFORE it was allowed to report
      zero, and it scores its classifier against two frozen bodies on every run so
      that an empty walk cannot certify itself [[fixing-the-fault-silences-the-control]].
      `basic_probe_printusing.py` builds its own Tcl but injects nothing through
      KEYBUF, so it is not in this class — the new gate classifies it CLEAN
      independently.

- [x] ✅ **D-ECHO — A LINE THE MACHINE DID NOT ECHO WAS NOT DELIVERED — LANDED
      2026-08-03.** Spec [`docs/spec-probe-echo.md`](docs/spec-probe-echo.md),
      characterisation
      [`docs/echo-delivery-characterization.md`](docs/echo-delivery-characterization.md).
      **Apparatus only — `probes/lib/omsx_repl.py` and a new
      `tests/test_echo_oracle.py`; no `basic/`, `sub/`, `disk/` or `tape/` source
      touched, no ROM rebuilt.** Closes D-DELIVER §9.3: every injected line is now
      checked against what the machine ECHOED, so `direct` mode — 45 of the 53
      probe files — is guarded too, and `run_cases` re-runs a mangled case
      boot-per-case exactly as the stored oracle does.
      🎯 **Six standing corpus suites were mis-delivering a case on every run and
      were GREEN**: `logicops`, `float`, `math`, `str-domain`, `time` and
      `error-trap`, all `direct`-mode and all invisible to the stored oracle. They
      passed because `run_differential` self-heals a disagreement — the outcome
      was rescued, the cause unattributable, and a mangle leaving a plausible
      value both sides agree on was never protected at all.
      🔴 **The guard was WIRED IN AND SILENT on its first run**: `$__f` is a global
      and does not resolve inside a Tcl `proc`, so `__echo` errored and openMSX
      dropped the callback without a word — emission present, call site present,
      every slot recorded, nothing reported. The **cross-oracle `ORACLES DISAGREE`
      check** caught it, not any gate [[coverage-gate-cannot-see-a-gutted-guard]].
      🔴 **Four false-positive classes, all found by the CORPUS, not by
      inspection** — and two of them broke a green gate before they were found
      (`linemax` 60/60 → exit 2 on a payload whose `LIST` scrolls its own echo
      away; `missing` 59 fires on a payload that clears then prints). The fourth
      fired on the **reference**, which mis-delivers nothing, and was caught by
      the zero-RED control [[knife-that-reddens-nothing-is-the-finding]].
      🔴 **K6 reddened NOTHING and that was the finding**: a hard-coded screen
      margin degrades the guard to **blindness**, not to noise (`MANGLED` 1 → 0,
      zero false fires), because a margin wrong by one eats only the prompt and
      matters solely for a *wrapped* echo. The geometry therefore has no emulator
      knife; `tests/test_echo_oracle.py` is its only instrument, and exits 1 on
      four rows under that cut.
      ⚠️ **The stored-program oracle STAYS**, as a second opinion — each oracle is
      blind exactly where the other sees (spec §5), and the pair is the only
      positive control either has, since a batch of *identical* cases does not
      reproduce the race at all.

- [x] ✅ **D-DELIVER — A CASE WHOSE PROGRAM WAS NEVER STORED MAY NOT REPORT A
      VALUE — LANDED 2026-08-03.** Spec
      [`docs/spec-probe-delivery.md`](docs/spec-probe-delivery.md),
      characterisation
      [`docs/graphics-delivery-characterization.md`](docs/graphics-delivery-characterization.md).
      **Apparatus only — `probes/lib/omsx_repl.py` and nothing else; no `basic/`,
      `sub/`, `disk/` or `tape/` source touched, no ROM rebuilt.** Closes the two
      standing `graphics-acceptance` reds D-PREFLIGHT filed (§8.5) and the corpus
      question that came with them.
      **Neither row was about sprites or `BASE(n)`.** Boot-per-case, both machines
      answer identically (`ZE 5` / `ZE 5`, `ZK 6144` / `ZK 6144`). The batched
      delivery path was **losing a whole program line**: `put_pat64_16` lost
      `10 ON ERROR GOTO 40`, so its ERR 5 went UNTRAPPED and the RUN aborted with
      the machine still in SCREEN 2 — whose zeroed pattern table the SCREEN-0
      scrape reads as **960 bytes of `$00`**, i.e. `zb=None`; `rd_base_s0` lost its
      `PRINT"ZK"` line, fell through into the handler and printed the PREVIOUS
      case's `ERR`, which still held **5** from `rd_baseneg`.
      🎯 **D-PREFLIGHT's hunch that `'ZE 5'` was "the neighbouring row's answer" is
      LITERALLY TRUE — and its model was wrong.** Implementing against it would
      have aimed a fix at the readout and looked like it worked.
      **What landed:** `_tcl` emits `prog.<idx>=<line-number chain>` per stored
      case (a new `__lines` Tcl walk of the line-link chain from `TXTTAB`), read
      **before `RUN`** so a case's own `NEW` cannot erase the evidence;
      `run_cases(batch=True)` announces any mismatch on stderr and re-runs that
      case boot-per-case (the path measured immune); `run_batch` — which IS the
      boot-per-case path — has no fallback and raises `APPARATUS FAILURE` instead.
      `verify_delivery=False` is the opt-out; **no probe needs it** (measured: of
      the 8 files using `mode="stored"`, none drives line entry to refusal).
      🔴 **THE GUARD FOUND ROWS THE GATE COULD NOT.** The clean gate run announced
      **four** mis-deliveries, not two: `wr_v255fr` and the phase-M `SCREEN2:DRAW"B"`
      row had each lost their `ON ERROR GOTO 40` and **passed anyway**, being value
      rows that never raise [[gate-can-be-green-while-measuring-nothing]]. And on
      its first corpus run it fired in **`array-acceptance`** too (case 20,
      `DIM C(1,1,1,1)` lost) — this is not a graphics-probe curiosity.
      🔴 **COVERAGE IS NOT EFFICACY, AGAIN.** Knife K2 kept the `prog.N=` emission
      AND the call and only gutted the judgement: the filed reading returned
      **byte-identical** [[coverage-gate-cannot-see-a-gutted-guard]]. K1 (delete
      the emission) gave the same. K3 (detect, do not repair) turned it into an
      attributed refusal. K4 fired and repaired with all 30 verdicts unchanged. K5
      was a deliberate **zero-RED** knife on the reference and came back 0/0/0
      [[knife-that-reddens-nothing-is-the-finding]].
      🔴 **MY FIRST TWO INSTRUMENTED RUNS PROVED NOTHING** — they were clean, but I
      had not checked the fault reproduced in them. Re-run with a reproduction
      check in the same run before their result was used
      [[knife-runner-false-negatives]].
      ✅ **CORPUS DECISION: `graphics-acceptance` JOINS THE STANDING LIST** (§5, and
      [`docs/spec-basic-dotgaps.md`](docs/spec-basic-dotgaps.md) §9.2). 290 rows,
      **2 m 58 s**, on the `repack-machine` prerequisite every emulator gate
      already has. It is the only member ever red at admission; admission was
      conditional on it coming back 290/290, and it did.
      **Gates:** graphics **290/290** (was 2 FAIL; a row-by-row diff moves exactly
      those two rows and nothing else) · unit 56/56 · deadcode 0/0 ·
      preflight-check 0 unguarded · msgexact 55/55 · logicops 193/193 ·
      array 151/151 · linemax 60/60 · direct-ctrl 40/40 · diskbasic 34/34 ·
      bdos 12/12 · missing / width / string / error / error-trap / abort /
      stop-trap / arrdim / clearpool / float / input / input-devices / time /
      intarg / sound / play / beep / math ALL PASS.

- [x] ✅ **D-PREFLIGHT — A PROBE MAY NOT MEASURE A MACHINE IT CANNOT VOUCH FOR —
      LANDED 2026-08-03.** Spec
      [`docs/spec-probe-preflight.md`](docs/spec-probe-preflight.md).
      **Apparatus only — no `basic/`, `sub/`, `disk/` or `tape/` source touched,
      ROMs byte-identical throughout.** Closes the failure D-DOTGAPS §9.2
      recorded: a corpus script ran `rm -rf build && make basic-reloc` (which does
      NOT build `build/zerobas-main-eu.rom`) and then a probe by hand; openMSX
      booted against a machine XML whose absolute paths named a deleted file, and
      `msgexact --gate` reported **55 red rows including its own controls**. Second
      time this class has bitten ([[stale-machine-reads-as-unimplemented]],
      [[ips-rebuild-after-basic-change]]).
      **What landed:** [`probes/lib/omsx_preflight.py`](probes/lib/omsx_preflight.py)
      refuses (exit 2, `APPARATUS FAILURE`, names the file and the fix) before the
      first boot; 90 probe/tool files now spawn
      `omsx_preflight.guarded(argv)`;
      [`tools/check_probe_preflight.py`](tools/check_probe_preflight.py) is the
      coverage denominator (**178 spawn sites, 85 exempt by construction, 93
      required, 0 unguarded**, `make preflight-check`); `msgexact-gate` /
      `msgexact-relock` targets exist at last, both on `repack-machine`.
      **The freshness oracle is `make -q`**, not an mtime sweep: `build/disk.rom`
      depends on `disk/` only and `build/sub.rom` on `sub/` only, so the obvious
      "no ROM older than the newest file under basic/ sub/ disk/ tape/" rule would
      have **refused every ordinary BASIC slice**.
      **Reference machines are exempt STRUCTURALLY, not by name**: only ABSOLUTE
      `<filename>` paths outside every openMSX dir are checked, and
      `Philips_VG_8020` / `National_CF-3300` carry none (measured: 0 files
      checked). A name list would have been one edit from exempting the subject
      [[echo-guard-never-saw-say-rows]].
      🔴 **THE GUARD WAS WIRED IN AND FAILED OPEN, AND ITS OWN KNIFE MATRIX FOUND
      IT.** `except OSError` around the `make -q` call was too narrow: a test
      double's exception escaped `preflight` **after** a `MISSING` fault had been
      recorded and **before** it could be reported, and all 8 entry points read
      GREEN with the ROM deleted. Now `except BaseException` → "cannot judge" is a
      **fault**. A guard that cannot judge must say so (§8.1).
      🔴 **THE mtime-RACE CHECK CANNOT EXIST, AND K3 IS WHAT SAID SO.** GNU Make
      3.81 compares at **ONE-SECOND** granularity (measured: target 1 ns OLDER than
      its prerequisite → still "up to date"), so the hazard is any same-second
      pair, not the equal mtime [[make-mtime-race-skips-subrom]] records — and a
      same-second check **fires on a correct, just-built tree**, because
      `sub/basic-resident-abi.inc` is GENERATED by the build ([`Makefile:261`](Makefile:261))
      68 ms before `build/sub.rom`. Removed rather than shipped as a check that can
      only fire falsely; the race stays a knife-runner hashing problem (§8.2).
      🔴 **COVERAGE IS NOT EFFICACY.** Knife K6 gutted `guard_cmd` and
      `preflight-check` still reported **93/93 guarded, ALL PASS** while the
      incident returned verbatim. The coverage gate proves the call is *there*;
      only K1/K6 prove it *does* anything.
      🔴 **EVERY MACHINE CONFIG THIS TREE HAS EVER WRITTEN WAS INVALID XML** — one
      `--` inside an XML comment in `tools/install-repack-machine.py`, in all five
      installed `ZB_*`/`*_REPACK_*` machines. openMSX tolerates it; ElementTree
      refuses the whole file. Fixed; the preflight strips comments textually
      anyway (§5.2).
      ⚠️ **A live specimen was already installed**: `ZB_REPACK_BASE.xml` still
      points at `.claude/worktrees/brave-curie-382b17/build/*.rom`, deleted long
      ago — the 2026-07-26 traps-T5 incident, still bootable. Refused by name now.
      🔴 **FILED, NOT FIXED: `graphics-acceptance` has two standing red rows**
      (`put_pat64_16`, `rd_base_s0`) and is **in no spec's corpus list** — the
      exact shape `logicops-acceptance` was in before D-EXPKW. Attributed away
      from this slice twice: identical under `ZEROBAS_PREFLIGHT=off` **and**
      identical on the stashed pre-slice tree.
      ⚠️ **A HEURISTIC FOR "WILL THIS IMPORT RESOLVE?" IS NOT A SUBSTITUTE FOR
      RUNNING IT** — the codemod guessed from a substring, `omsx_session.py` got an
      unreachable import, and `diskbasic-acceptance` came back **30/34** for the
      import rather than the disk. `compileall` was clean and the coverage gate was
      green; only the gate found it. 34/34 after (§8.3).
      **Gates:** unit 56/56 · deadcode 0/0 · msgexact 55/55 · preflight-check
      0 unguarded · lnblank 536/536 `REPEAT=2` · lnblank-echo green · logicops
      193/193 · array 151/151 · diskbasic 34/34 · bdos 12/12 · linemax 60/60 ·
      direct-ctrl 40/40 · string/error/error-trap/abort/stop-trap/arrdim/clearpool/
      float/sound/play/beep/math/input/time/intarg ALL PASS.

- [x] ✅ **ERROR-MESSAGE CAPITALISATION — CLOSED 2026-08-02 by D-MSGEXACT**
      ([`docs/spec-basic-msgexact.md`](docs/spec-basic-msgexact.md), denominator
      [`docs/msgexact-msx1-characterization.md`](docs/msgexact-msx1-characterization.md)).
      Resolved as **reference-exact wording, tree-wide**. Page 1 **14 B → 39 B**:
      the policy was a **carve**, not a cost — the lowercase style was the only
      thing paying for two duplicated strings and `fp_runtime_error`'s two
      one-code-two-message special cases. Gate 45/45, five knives, corpus green.
      🔴 **THIS ITEM'S OWN EVIDENCE WAS WRONG IN BOTH HALVES, AND THAT IS THE
      LESSON.** (a) [`basic/arrays.asm:608`](basic/arrays.asm:608)'s claim is
      scoped to **syntax** errors and is TRUE; the same comment names Tier B as
      capitalised. The tree's inconsistency was deliberate documented policy
      (arrays §9.5), not a defect — which is why no gate ever caught it.
      (b) The two `array-acceptance` failures were **not** a message-case defect:
      D-MISS-2 folded INSTR's check into `eval_pos_arg`, whose reject path is
      `gb_illegal` → `raise_error(5)` → the capitalised string, deleting the
      lowercase route the probe still asserted. **149/151 → 151/151 with no
      `basic/` change.** A red row assumed stale is a row that measures nothing.
      🎯 The real finding was structural: [`error_acceptance.py`](probes/basic/error_acceptance.py)
      stated a policy of *not* comparing message text to the reference, so the
      **whole corpus was blind to wording** — every error class agreed
      numerically. `lst-comma` was the single visible pixel of that; it is
      retired.

- [x] ✅ **D-MSGSUB — THE 14 UNIMPLEMENTED ERROR MESSAGES, SUB-ROM-HOSTED —
      CLOSED 2026-08-02** ([`docs/spec-basic-msgsub.md`](docs/spec-basic-msgsub.md),
      denominator [`docs/msgexact-msx1-characterization.md`](docs/msgexact-msx1-characterization.md)).
      Codes 12/15/18/19/50/51/53/54/56/57/60/62/63/64 now print the reference's
      own text from sub-ROM page-1 tenant `SUBROM_IDX_ERRMSG` (`sub/errmsg.asm`),
      emitted through BIOS `CHPUT`. **`msgexact --gate` 33/49 → 50/50, zero
      holes left.** Main page 1 **39 B → 22 B**, low region **unchanged**, sub
      page 1 3067 → 2740 B.
      🎯 **THE WHOLE MAIN-SIDE COST OF THE TEXT IS ONE BYTE.** `err_subhosted` is
      a single `MSGESC_SUB` marker; the four dense `err_msgtab` holes and
      `rerr_unprintable` just point at it — five repoints, **zero bytes**. The
      +17 B is entirely the decoder arm and the dispatch stub. That is the
      mechanism the follow-on below rides.
      🎯 **THE SLICE DOES NOT REST ON "THE ABSENT CASE IS UNREACHABLE", AND IT
      SHOULD NOT HAVE.** D-MSGEXACT §4.2 argued you cannot type `ERROR 12`
      without a sub-ROM because `tokenise` is itself a tenant. **That argument
      has a hole** — a *tokenised* program can arrive from tape or disk. So
      `err_subhosted` is sited so `err_unprintable` is the very next byte, and an
      absent sub-ROM falls through to exactly what zerobas printed before.
      Knife K1 MEASURED it with a plain `POKE &HF107,0`, no rebuild.
      🔴 **TWO OF THE FIVE KNIVES LANDED ON THE SLICE ITSELF.**
      **K2** reddened nothing — and the reason was that `sub/errmsg.asm` was
      missing from the Makefile's `SUB_PARTS`, so `make` never rebuilt the
      sub-ROM. Nothing shipped wrong (clean builds force it), but the next
      incremental edit to the tenant would have silently shipped a **stale
      sub.rom** ([[makefile-subparts-stale-tenant]], met again by adding a new
      sub file). Caught only because a knife predicted RED and got green.
      **K3 refuted this spec's own headline measurement**: the `prd-*` rows were
      written into the spec AND the denominator as "the reading that settles
      CHPUT", and deleting `fre_abort_low`'s `ld (PRDEST),a` moved **neither**.
      `PRINT#` restores PRDEST at statement end, so an `ERROR n` on the next line
      never sees it set. Re-aimed at `mid-ifc` (the error raised *inside* the
      `PRINT#` argument list) the cut lands both ways — without the zero the
      screen is **empty** and the message is in the file. For the sub-hosted path
      the question is **bounded away, not measured**: `ERROR n` is a statement and
      cannot appear inside a `PRINT#`.
      ⚠️ **K5 corrected the spec too**: code 26 stays green when the sparse
      routing is reverted, because main's `Unprintable error` and the tenant's
      fallback are the same text. 26 is a control for the mechanism being
      *sound*, not *present*.
      ⚠️ **This fixes the TEXT, not the RAISERS.** No zerobas site raises any of
      the fourteen (verified by enumerating every `ld a,<n>` into `raise_error`);
      `ERROR n` is still the only way to reach them. "Should zerobas raise ERR 12
      for a direct-mode `INPUT`?" is a different question per code.

- [x] 🎯 **D-MSGMIGRATE ✅ — SIXTEEN MESSAGES MIGRATED; PAGE 1 22 B -> 311 B.**
      Done 2026-08-02, [`docs/spec-basic-msgmigrate.md`](docs/spec-basic-msgmigrate.md).
      🎯 **THE FILED CLAIM WAS REFUTED IN THE CHEAP DIRECTION.** D-MSGSUB §8 said
      five messages could not migrate because `rerr_sparse` reaches them "by its
      own `ld hl` -- a different key", and proposed a 2 B/message second selector.
      It is the SAME key: `rerr_sparse` OPENS with `ld a,(ERRFLG)`, and
      `raise_error_forced` / `ex_cont_no` / `dl_overflow` each store ERRFLG before
      loading their message. **No second selector was built.** Enumerating every
      print site is what said so, and it disagreed with the filed list in BOTH
      directions (five wrongly blocked, one wrongly cleared).
      🎯 **AND THE SELECTOR CODE ITSELF WAS DELETABLE**: once all five sparse
      messages pointed at `err_subhosted`, every arm of `rerr_sparse` and
      `rerr_sparse2` read `ld hl,err_subhosted / jp raise_error_hl` -- which is
      what `rerr_unprintable` already was. 50 B of dispatch gone, trap decision
      unchanged (`sparse-trap`, a row added mid-slice, is what measures that).
      Carve: 225 B of string + 50 B dispatch + 15 B of dead phrase table
      (`MSGESC_WITHOUT` had THREE users, not the two that were filed) + 7 B of
      collapsed branch, less 8 B for `pm_sub`'s register fence = **289 B**.
      Sub page 1 2740 -> 2428 B. `msgexact --gate` **54/54**, unit **56/56**,
      dead-code 0/0.
      🔴 **A DEFECT WAS FIXED TO GET THE LAST STRING, AND FIXING IT CARVED BYTES.**
      `dl_overflow`'s float arm stored no ERRFLG at all, so `PRINT ERR` after
      `20 A=1E99` read a stale code while its sibling arm read 25. Measured
      2026-08-02 on both refs (`fovf-lit` 6/6, zerobas 0; controls `fovf-ctl` 0
      everywhere and `fovf-arm` 6 everywhere). `TKOVF`'s own contract in
      `basic/tokenise.inc` already says "the reject reason IS the ERR code" --
      the float arm was the one arm not honouring it. Storing 6 made both arms
      symmetric, DELETED the branch, and only then was `err_overflow` migratable.
      🔴 **TWO FINDINGS IN APPARATUS, NEITHER IN THE MIGRATION.** (a) The host
      harness's page-1 sub-ROM island borrowed the caller's MEMORY but not its
      TRAPS, so a tenant's `call CHPUT` ran off the end -- invisible until
      `errmsg_tenant` became the first page-1 tenant a unit test reaches whose
      whole job is a BIOS call. (b) K1's own setup disabled its delivery path
      (`POKE &HF107,0` then typing `ERROR n` cannot tokenise), and the
      main-resident CONTROL is what said so.

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

- [x] ✅ **CLOSED 2026-08-21 (D-STRPAREN), −28 B main page 1 (39 → 11) —
      `(A$)` WAS REFUSED IN EVERY STRING CONTEXT.**
      [`docs/spec-basic-strparen.md`](docs/spec-basic-strparen.md).
      `str_eval_paren` (23 B) + a 5 B `(` peek in `basic/print.asm`.
      `strparen-acceptance` **16/16, DEFERRED EMPTY**; `namspc-acceptance`
      98/98 → **99/99** as `f.paren` — the one row D-FNEXPR's filename fix left
      red — graduates with them, through the string EVALUATOR exactly as that
      slice predicted.
      🎯 **THE `ret nc` IS THE DESIGN, NOT AN ERROR PATH.** The routine is
      written to be TRIED: on a non-string inside it RESTORES HL and returns CF
      clear, so a dispatcher that guessed wrong falls through to the numeric
      path with the cursor it would have had. That is what let PRINT offer the
      string path for 5 B without committing to it.
      🔴 **TEN ROWS CLOSED ON THE FIRST ARM — TWO MORE THAN PREDICTED — AND
      `p.left` CLOSING REFUTED THIS ITEM'S OWN ANALYSIS.** The characterization
      had read `LEFT$`'s `Syntax error` as *"a different refusal site, one rule
      at at least TWO mechanisms"*; one `(` arm closed it with the other nine.
      **A face is a claim about the LAST routine to run, not the first one to
      refuse** — D-FNARG2 established its three mechanisms by tracing paths, and
      that section read faces. Inverted in place, not deleted.
      🔴 **AND A PATCH THAT NEVER LANDED WAS CAUGHT BY THE ROM HASH, NOT BY THE
      PROBE.** The PRINT peek's `assert` failed (wrong anchor), the whole command
      was backgrounded so the traceback went unread, and the probe log looked
      like an honest measurement of an unfixed machine. **The wall was 16 B
      before and after: a 5 B edit that costs 0 B has not happened.** The rebuild
      script asserts the ROM MOVED now — the same guard D-FNEXPR2 put on its
      knife runner, which belongs on any edit that claims a byte cost.
      ⚠️ **MAIN PAGE 1 IS AT 11 B** (2026-08-21) — the next slice needs a carve;
      `clone_scout` offers 12 B / 10 B / 9 B on page 1, listed below.
      *The original filing:*
      🔴 **`(A$)` IS REFUSED IN EVERY STRING CONTEXT — `str_eval_one` HAS NO
      PARENTHESISED-SUBEXPRESSION CASE.** Filed 2026-08-21 by D-FNEXPR
      ([`docs/spec-basic-fnexpr.md`](docs/spec-basic-fnexpr.md) §4), found
      because it is the ONE row of fourteen that the filename fix did **not**
      close — and predicted to stay red BEFORE the run, by reading
      [`basic/strvar.asm`](basic/strvar.asm) rather than by watching it fail.
      ```
      B$=(A$)      cf3300 `Q`     zb `Type mismatch`
      PRINT (A$)   cf3300 `Q`     zb `Type mismatch`
      B$=A$    🟢  cf3300 `Q`     zb `Q`        <- the unparenthesised twin
      B=(A)    🟢  cf3300 ` 5 `   zb ` 5 `      <- NUMERIC parens WORK
      ```
      🎯 **THE TWO CONTROLS ARE THE FINDING.** Parentheses work for numbers, and
      the unparenthesised string works, so this is not "parens are unsupported"
      and not "strings are broken": `str_eval_one` dispatches on `"`, on the
      string-function tokens and on a letter, and simply has no `(` arm. It is a
      STRING-EVALUATOR hole, not a filename one, and charging it to the filename
      gate would price it against the wrong verb.
      ✅ **DENOMINATOR BUILT AND THE RULE HOLDS — 2026-08-21 (D-STRPAREN)**,
      [`docs/strparen-msx1-characterization.md`](docs/strparen-msx1-characterization.md),
      `make strparen-acceptance` (**3/3 scored, 11 DEFERRED**), 0 ROM bytes.
      The filing above rested on **two** ad-hoc readings never committed as rows;
      it now rests on **eleven contexts** — LET, `+` on either side, nested,
      a parenthesised EXPRESSION, a parenthesised LITERAL, PRINT, IF, and the
      arguments of `LEN` / `MID$` / `LEFT$` — with three 🟢 controls, **and no
      disk anywhere, so every row has TWO references** where `f.paren` has one.
      All eleven diverge; all three controls are green on all three sides.
      🔴 **AND THE ROWS CORRECT THE SHAPE OF THE FIX IN TWO WAYS.**
      (a) `p.lit` — `B$=("Z")`, a parenthesised LITERAL with no variable in it —
      is refused too, so the subject is the `(` and not string VARIABLES; a fix
      framed around variables closes ten rows and leaves that one.
      (b) `p.left` (`LEFT$((A$),1)`) answers **`Syntax error`** where the other
      ten answer `Type mismatch` — a DIFFERENT refusal site, so this is one rule
      at **at least two mechanisms**, the shape D-FNARG2 found for filenames.
      🎯 **IT IS A SPLIT-EVALUATOR QUESTION, NOT A MISSING `case` LABEL.** A `(`
      arm in `str_eval_one` closes `p.let`/`p.cat1`/`p.nest`/`p.inner`/`p.lit`;
      `p.print` never reaches `str_eval` at all (`basic/print.asm`'s `exp_loop`
      peeks for `"`, a string-function token or a `$`-suffixed letter, and a
      leading `(` falls through to `exp_num`, the NUMERIC evaluator), and `p.if`
      is the same story through `ev_rel`. zerobas picks its evaluator by PEEKING
      at the first byte; the reference has one type-polymorphic evaluator. **A
      leading `(` is the one operand shape a peek cannot classify** — so the fix
      is "try the string path, fall back to numeric" at each dispatcher, plus
      `LEFT$`'s own argument parse as its own site.
      ✅ **ITS FACE IS NO LONGER CONTEXT-DEPENDENT — UPDATED 2026-08-21
      (D-FNEXPR2).** This read: *"`Type mismatch` through LET/PRINT ... and
      `Syntax error` through `fname_expr`'s `jp nc,stmt_error`, so the row
      cannot be scored on the face either."* That exit is `els_tc_common` now —
      the very routine the LET mirror uses — so `OPEN(A$)AS #1` answers
      **`Type mismatch`** as well, and the three contexts agree with each other
      while disagreeing with the reference in ONE direction. The row is still
      DEFERRED, because the CF-3300 answers `OK` (it accepts the parenthesised
      subexpression) and only the evaluator can close that; but it is now one
      divergence to fix instead of two faces to reconcile.
      ⚠️ Row `f.paren` in [`basic_probe_namspc.py`](probes/basic/basic_probe_namspc.py)
      is DEFERRED with exactly this reason; it is the denominator, already built.
      💰 **SCOUTED, NOT YET PRICED WHOLE.** The `str_eval_one` arm hand-counts at
      ~25 B (a 5 B dispatch + a ~20 B routine that saves HL, recurses through
      `str_eval` so the `+` tail comes for free, requires `)`, and **restores HL
      and returns CF clear when the inside is not a string** — that last part is
      what lets a peeking dispatcher fall back to numeric). `p.print` adds a
      `(`-peek in `basic/print.asm`; `p.if` and `p.left` are unscouted.
      ⚠️ Main page 1 read **39 B** and page-0 LOW **22 B** on 2026-08-21 after
      D-FNRUN (`make basic-reloc`), so the first arm fits and the rest needs a
      carve. `tools/clone_scout.py --min 6 --members 2` offers 12 B
      (`sav_ascii_flag`/`sav_cas_flag`, page 1), 9 B (`ev_t_div`/`ev_t_mul`,
      page 1) and 12 B in `basic/str-engine.asm` (LOW), read 2026-08-21.

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

- [x] ✅ **`RETURN <line>` — LANDED 2026-08-02 (D-RETLN), 27/27, four knives,
      `lnrd-return`'s pin RETIRED.** Filed 2026-08-01 by D-LNREF; spec
      [`docs/spec-basic-retln.md`](docs/spec-basic-retln.md), measurement
      [`docs/retln-msx1-characterization.md`](docs/retln-msx1-characterization.md).
      The filed one-line description was right and **incomplete in four ways**,
      and the 27-row `lnrt` walk is what found them — both references agreeing on
      every row:
      * **the empty-stack check comes FIRST**, before the argument is parsed *or*
        resolved: `RETURN B` and `RETURN 99` on an empty stack are both ERR 3,
        not ERR 2 / ERR 8 (`lnrt-nogosbad`/`-nogosund`). The filed row could not
        have said so — its line existed and its argument was well formed;
      * **both failure modes POP THE FRAME BEFORE THEY RAISE.** ERR 8 *and* ERR 2
        leave the stack empty (`lnrt-undefp`/`lnrt-varp`, which read the STACK by
        making a handler's own bare `RETURN` report on what was left);
      * **the error is filed against the `RETURN`'s own line**, not the caller's
        (`lnrt-erlund`/`-erlvar`, ERL = 40). 🔴 This is what rules out the
        cheapest implementation — reusing the existing pop, whose
        `ld (CURLINE),de` would file it against the caller. No row reading only
        "where did control go" could see it;
      * **trailing junk is ERR 2** — `RETURN B` is a syntax error, `RETURN 0` is
        an ordinary failing lookup (ERR 8, no zero special case), and `:` after a
        bare `RETURN` is a terminator (`lnrt-bcolon`).
      ⚠️ **The filed warning "it must POP the frame *and* set the resume line —
      not a GOTO with extra steps" was WRONG.** It is exactly a GOTO with a pop
      in front: `RESUMEFLAG` is never set on the branch path, and setting it
      would be the bug (the run loop consults it *before* `GOTOFLAG`).
      🔴 **And MS-BASIC's documented use for `RETURN <line>` — leaving an
      `ON ERROR` handler — DOES NOT EXIST ON MSX.** Both references read ERR 3: a
      handler is entered without a GOSUB frame, so the empty-stack rule just
      fires (`lnrt-onerr`, with `lnrt-onerrctl`'s `RESUME 70` → ` 120  0 ` as the
      control proving the instrument can read the success case).
      Landed **+25 B main page 1**, funded by a measured 160 B carve (below).
      🔴 **A REGRESSION SHIPPED IN THE FIRST IMPLEMENTATION AND THE 28-ROW BATTERY
      COULD NOT SEE IT.** `trap_return_check` destroys `HL` unconditionally, which
      was free while `ex_return`'s next act was `ld hl,(GSP)` (HL dead across the
      call); making the token cursor live across it inherits that clobber contract
      silently ([[refactor-inherits-clobber-contracts]]). Caught by
      `stop-trap-acceptance` (`C2_press_in_handler_latches`), not by any `lnrt`
      row — all 28 `RETURN` out of ordinary code, so `TRAPSVC` is 0 in every one
      and the clobber cannot fire. Fixed by moving the `push hl` above the trap
      check, at **zero byte cost**.

- [x] ✅ **~~`RETURN` DOES NOT DISCARD AN OPEN `FOR`~~ — SHIPPED 2026-08-19
      (D-FORRET), AND THE ROW THAT FILED IT COULD NOT HAVE SPECIFIED THE FIX.**
      [`docs/spec-basic-forret.md`](docs/spec-basic-forret.md). The GOSUB frame
      grew 4 → **6 B** to record `(FSP)` at push time; `ret_frame` truncates the
      FOR stack back to it, and the no-frame arm clears the stack outright.
      **+23 B main page 1 (64 → 41 free), +16 B RAM, 0 B low, 0 B sub** — the RAM
      from the 72 B window D-FORVAR freed when it relocated the FOR stack, which
      now leaves 56 B. `lnrt-forret`'s `KNOWN_DIVERGE` pin is **DELETED**, not
      updated, so the row is back under ordinary cross-side scoring.
      🎯 **`lnrt-forret` IS THE CORNER WITH NO GOSUB FRAME AT ALL, and it is
      consistent with two different rules that need different code** — "a RETURN
      that finds no frame clears the FOR stack" (3 B in `ex_ret_under`) versus
      the real one, "a RETURN truncates the FOR stack back to its depth at GOSUB
      time" (a field in every frame). Four new rows with a real GOSUB frame
      underneath settled it BEFORE a byte was designed: `lnrt-forgsb`,
      `lnrt-forgdeep` (two frames — "entries" is plural and one frame cannot test
      it), `lnrt-forgline` (`RETURN <line>`, the second route through the same
      pop), and `lnrt-forgctl` (🟢 the FOR opened BEFORE the GOSUB, which must
      SURVIVE). **All four predictions written into the probe first, all four
      EXACT**, both references agreeing on every row.
      🔴 **THE DISCRIMINATOR IS `I`, NOT THE ERROR COUNT.** Both sides trap
      exactly once and so both read `A=1`; only the loop variable separates
      "found a live frame" from "found none". A row scored on *did it error*
      would have agreed on both sides and read GREEN.
      🔴 **AND THIS ITEM'S OWN PRESCRIPTION WAS HALF WRONG, refuted by the
      control it already carried.** It says closing this means teaching `RETURN`
      *"(and the error unwind)"* about the FOR stack — but `lnrt-forerr` reads
      ` 103  0  4 ` on all three sides, so an ordinary trap does not unwind the
      FOR stack on the reference either. **No error path was changed.**
      🔴 **`make unit-test` WENT RED AND WAS RIGHT TO**: `test_traps.py` asserted
      *"GSP advanced by 4"* as a literal. The dispatcher shares `gosub_push`, so
      a trap handler's RETURN now truncates the FOR stack too. The assertion now
      reads `GOSUB_FRAME` from the symbol table and gained a tooth that the
      frame's new field is actually recorded — a test that restates a constant
      can only rot into agreement with whatever it was last edited to match.

      **Filed 2026-08-02** by D-RETLN, found by the apparatus while it was testing
      something else. MS-BASIC keeps FOR and GOSUB frames on the **same** (Z80)
      stack, so `RETURN` discards the FOR entries it walks past looking for a
      GOSUB frame — with no GOSUB frame at all, that means the open `FOR`.
      zerobas keeps the two on **separate RAM stacks** (`GOSUB_STK` and the FOR
      stack), so nothing is walked past and the loop survives:
      ```
      10 ON ERROR GOTO 50 : 20 FOR I=1 TO 3:RETURN:NEXT
      30 A=A+100:END      : 50 A=A+1:RESUME NEXT
          both references -> A=102 ERR 0 I=1     zerobas -> A=103 ERR 0 I=4
      ```
      🔴 **My first attribution was "an error trap destroys the FOR frame", and
      its own control REFUTED it.** `lnrt-forerr` is the identical program with
      `ERROR 7` in place of `RETURN` and reads ` 103  0  4 ` on **all three
      sides** — an ordinary trap is not the variable, `RETURN` is. One row could
      not have separated those two rules ([[one-row-cannot-separate-two-rules]]).
      `lnrt-forret` is **pinned as `KNOWN_DIVERGE`** to zerobas' exact
      ` 103  0  4 `, with `lnrt-forerr` alongside it as the green control.
      ⚠️ **THAT PIN IS GONE** — deleted by D-FORRET above; everything in this
      body stands as filed and as measured, only its status changed.
      This is architectural, not a parse bug: closing it means making `RETURN`
      (and the error unwind) aware of the FOR stack, which is its own slice.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, both rows exactly as filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.10): ` 102  0  1 ` on both references and ` 103  0  4 ` here, with the
      `ERROR 7` control reading ` 103  0  4 ` on all three sides.

- [x] ✅ **~~135 MORE DEAD BYTES OF THE SAME SHAPE~~ — THE GATE THIS ITEM ASKED
      FOR EXISTS (D-LOADSWEEP, 2026-08-19), AND IT FOUND 35 B ON ITS FIRST RUN.**
      [`docs/spec-basic-loadsweep.md`](docs/spec-basic-loadsweep.md),
      `make redundant-load-check` ([`tools/redundant_load_sweep.py`](tools/redundant_load_sweep.py)).
      🎯 **THIS ITEM PREDICTED THE FIND THAT MADE IT URGENT.** It said "a
      redundant-load sweep is a two-line matcher, and there are certainly other
      idioms like it" on 2026-08-02 and was not taken. **Seventeen days later
      D-EVSPDUP found the identical idiom at `ev_sp` BY HAND** while scouting 5 B
      for something else — and carved only `basic/expr.asm`, leaving **NINE MORE
      SITES**: six in `basic/str-engine.asm`, three in `basic/usr.asm`. The sweep
      found them on its first run, with `bl_skip_spaces` (4) and
      `edt_skip_spaces` (4): **17 dead loads, 35 B**.
      💰 **Measured, clean: LOW 5 B → 23 B, page 1 41 B → 50 B**, sub p0
      3295 → 3299, sub p1 1627 → 1631.
      🔴 **THE PRICE WAS RIGHT ABOUT THE TOTAL AND WRONG ABOUT EVERY BYTE'S
      HOME.** Predicted "+27 B of main page 1" by resolving ONE symbol per file
      (`str_eval_one` `$498F`); `str-engine.asm` **spans both regions** and those
      six sites are in `ev_str_arg`/`ev_f_instr`/`ev_rel_str` at `$29F3`–`$2E8F`,
      the LOW region. 🎯 **And the miss landed in the scarcest currency** — the
      low region was the binding wall at 5 B ("5 B will not fund the next
      low-region slice") and is now **23 B**. The tool now resolves every site
      through its enclosing label and groups by REGION, not by path.
      🔴 **D-EVSPDUP's contract header said "24 CALL SITES DEPEND ON IT" and the
      tree has 36.** Its "72 B in this file alone" was honest about its scope —
      which is exactly why it read as complete. **A count true of one file reads
      like a count of the tree**, and the header is where anyone looks first.
      Corrected, and it no longer claims "there is no gate on a register
      contract", because there is one now.
      ✅ Two proven routines came back at **zero** dead loads — `skip_spaces`
      and `ldr_skipsp` — D-RETLN's 160 B carve still holding, MEASURED not
      assumed.
      ✅ **AND THE 28 CANDIDATES WERE READ THE SAME DAY — ALL 28 ARE LIVE, a
      MEASURED ZERO.** 🎯 **11 of them are the EXACT INVERSE of the carve class
      and look identical to it**: `fch_modes_ptr`, `pu_deref_body`,
      `ztrap_entry`, `tgt_desc_fix`, `gfx_pstk_addr`, `df_entptr` all **RETURN a
      computed pointer in HL**, so the following `ld a,(hl)` is not a reload —
      it is the dereference the call exists to enable, and deleting it would
      delete the point of the call. The other 17 clobber A with a value, a type
      or a flag. **That is why the sweep proves a SHAPE rather than
      pattern-matching one.** Verdicts recorded per callee in
      [`tools/redundant-load-reviewed.txt`](tools/redundant-load-reviewed.txt)
      as a **CONTROL, not a suppression list** — every candidate is still
      printed; an UNREVIEWED callee or a STALE entry FAILS the gate (K-LS2/K-LS3,
      both EXACT). ⚠️ **A verdict is one human's reading on one day and nothing
      re-checks the REASONING**, only that the callee still has sites — the
      tight-skip prover has no such hole, which is why it is the half that gates
      on bytes.
      📊 K-LS1 re-planted one dead load per region: exit 1, **EXACT**, including
      the `LOW $29F3` / `page1 $5347` split the author got wrong by hand.

      **Filed 2026-08-02**
      by D-RETLN, which carved all 160 as its funding — this entry records the
      *shape*, because the gate that should have found it cannot.
      `skip_spaces` ([`basic/interp.asm:574`](basic/interp.asm:574)) is
      `ld a,(hl) / cp ' ' / ret nz / inc hl / jr skip_spaces` — it returns **only**
      via `ret nz`, so `A = (hl)` on every exit. Every `call skip_spaces`
      immediately followed by `ld a,(hl)` therefore reloads a register that
      already holds that value: 1 dead byte, 160 times, `basic/graphics.asm` 27 ·
      `basic/files.asm` 26 · `basic/program.asm` 19 · `basic/save.asm` 15 · …
      Measured, clean `make basic-reloc`: page 1 free **6 B → 149 B**, low
      **9 B → 23 B**.
      🔴 **THE DEAD-CODE GATE REPORTS 0 DEAD AND IS RIGHT.** These are reachable
      instructions computing a value already held — not unreachable code — so
      `deadcode-gate` is structurally blind to them, and was while 160 B sat
      there through every slice that ever said "page 1 has 6 B free". ⚠️ **Every
      byte-budget claim made before 2026-08-02 was measured against a wall that
      had 143 B of slack in it.** The open question this leaves is not the 160 B
      (they are gone) but whether a gate should exist for the *shape*: a
      redundant-load sweep is a two-line matcher, and there are certainly other
      idioms like it. That is the item.

- [x] ✅ **~~`DEFINT` STORES DIFFERENT BYTES FROM THE REFERENCE~~ — BOTH HALVES
      FIXED**, `DEFINT` 2026-08-18 (D-DEFINTTOK, `7aadd36`) and the other three
      2026-08-19 (D-DEFTYPETOK, `840ed59`). All four DEF<type> verbs have
      whole-word [`basic/kwtable.inc`](basic/kwtable.inc) rows and the
      reference's own single-byte tokens now — `DEFSTR $AB`, `DEFINT $AC`,
      `DEFSNG $AD`, `DEFDBL $AE` — so `20 DEFINT 10` stores `AC 20 0F 0A 00` and
      `20 DEFSTR 10` stores `AB 20 0F 0A 00`: **both reference columns below,
      argument included.** 🎯 **THE TWO HALVES WERE ONE DEFECT.** The wider
      `DEFSTR` divergence this entry files as a second problem was never one:
      with no row of its own, `DEF` matched and `S`,`T`,`R` were copied as NAME
      letters, so the tokeniser's in-a-name state stayed SET and the digits
      behind the keyword CONTINUED the identifier instead of beginning a
      constant. A whole-word match leaves no name open, so one row per verb
      fixed the token byte and the argument TOGETHER
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.11, [`docs/lnref-msx1-characterization.md`](docs/lnref-msx1-characterization.md)
      §4). ⚠️ **THE PRESCRIPTION BELOW IS ALSO SUPERSEDED**: `ex_def_type` did
      not move off the ASCII mnemonic, it was MERGED with `ex_defint` into
      `ex_deftype` and the mnemonic parser DELETED — the tenant reads the token
      back from below the cursor instead (`0936943` corrected the comments and
      docs that still described the old mechanism). Everything below stands as
      filed and as measured; only its status changed.

      **Filed 2026-08-01**
      by D-LNREF's walk. `20 DEFINT 10` reads `<AC> <0F><0A>` on both references
      and `<97>INT <0F><0A>` on zerobas — [`basic/kwtable.inc:140`](basic/kwtable.inc:140)
      emits `DEF_TOKEN` + literal `"INT"` **on purpose** so `ex_def_type` sees
      the ASCII mnemonic, and `DEFSNG`/`DEFDBL`/`DEFSTR` have no entry at all.
      Deliberate, and still a byte-level divergence a `LIST` round-trip can see.
      Reference bytes now locked: `DEFSTR $AB`, `DEFINT $AC`, `DEFSNG $AD`,
      `DEFDBL $AE`. Closing it means moving `ex_def_type` off the ASCII
      mnemonic, so it is a slice and not a table edit.
      ✅ **RE-MEASURED 2026-08-09 — STILL LIVE, and WIDER than filed**
      ([`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §4.11). Body tokens from a `("stored_line", TXTTAB)` capture, after the
      4-byte header:

      | typed | both references | zerobas |
      |---|---|---|
      | `20 PRINT 10` 🟢 | `91 20 0F 0A 00` | `91 20 0F 0A 00` |
      | `20 DEFINT 10` | `AC 20 0F 0A 00` | **`97 49 4E 54 20 0F 0A 00`** |
      | `20 DEFSTR 10` | `AB 20 0F 0A 00` | **`97 53 54 52 20 31 30 00`** |

      🔴 **`DEFSTR` IS WORSE THAN THIS ENTRY SAYS.** The filed claim is only that
      `DEFSNG`/`DEFDBL`/`DEFSTR` have no `kwtable.inc` entry and work via
      `DEF_TOKEN` + ASCII. But the ARGUMENT diverges too: zerobas stores `10` as
      **ASCII `31 30`**, where `DEFINT` on the same tree crunches the identical
      argument to the integer literal `0F 0A`. So the divergence is not one
      substituted token — after `DEFSTR` the line is not being crunched at all,
      and a `LIST` round-trip is not the only thing that can see it. Whoever
      closes this owns both halves.

- [x] ✅ **~~`LIST <line>` / `LIST <from>-<to>` STILL LIST THE WHOLE PROGRAM~~ —
      MEASURED FALSE 2026-08-09** by the TODO staleness sweep,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.1. Program `10 A=1 / 20 B=2 / 30 C=3 / 40 D=4`, reading the screen
      between the echo and the prompt:

      | row | command | VG-8020 | CF-3300 | zerobas |
      |---|---|---|---|---|
      | `l.all` 🟢 | `LIST` | `10 A=1｜20 B=2｜30 C=3｜40 D=4` | idem | idem |
      | `l.line` | `LIST 20` | `20 B=2` | `20 B=2` | **`20 B=2`** |
      | `l.range` | `LIST 20-30` | `20 B=2｜30 C=3` | idem | **idem** |
      | `l.from` | `LIST 30-` | `30 C=3｜40 D=4` | idem | **idem** |

      🔴 **WHAT WAS BELIEVED, AND WHY IT WAS WRONG.** The entry says *"`ex_list`
      ignores its argument … the range is now sitting there crunched and
      unread"*. **`LIST <range>` shipped 2026-08-02 with D-LSTRNG**, and the
      Editor/program-management bucket 4000 lines further down this same file
      says so in as many words. The pin `lnrd-list` reads `1 0` on all three
      sides because it is about the CRUNCH, not the execution — a pin that
      cannot see the thing that changed. `make editverb-acceptance` corroborates
      from the printer side: `llt-one` / `llt-from` / `llt-upto` / `llt-range`
      all list a RANGE, 61/61 on three sides.

- [x] ✅ **LINE-NUMBER SCAN AND EMBEDDED BLANKS — LANDED 2026-07-31, 52/52,
      falsified on five knives.** Was 🔴 a silently wrapped line number shipping
      today. Found 2026-07-29 as a
      FAILING TWO-SIDED CONTROL in D-LINEMAX's `tok` battery — a confound there,
      a real divergence of its own. Byte-exact via the
      `("stored_line", TXTTAB)` capture:
      ```
      typed:      20 0#0#0#0#0#
      VG-8020 ->  line 200, body = 0x23 ('#') + four double literals
      zerobas ->  line 20,  body = five double literals
      ```
      The reference's line-number scan **skips the blank and keeps accumulating
      digits** (`20` + ` ` + `0` = 200); zerobas stopped at the space.
      Spec [`docs/spec-basic-lnblank.md`](docs/spec-basic-lnblank.md),
      characterization [`docs/lnblank-msx1-characterization.md`](docs/lnblank-msx1-characterization.md),
      gate `make lnblank-acceptance` (54 rows, five batteries). **Baseline 18/48.**
      **Cost: 61 B, all page 1 (69 B → 8 B free)**, low region untouched at 23 B;
      the crunch half rides the sub-ROM.
      ⚠️ **TWO ORACLES.** Every row was asked of the VG-8020 **and** the CF-3300,
      because the whole item rested on one row from one machine. They agree on
      all 54 rows byte for byte — so this is MSX-BASIC and not one ROM.
      🔴 **THE FILED TITLE WAS THE SMALLEST PART, in four directions:**
      * **`99999 REM` SILENTLY STORED LINE 34463.** The ceiling was unguarded and
        `parse_lineno` wrapped at 16 bits; both references refuse anything past
        65529 with `Syntax error` (`PRINT ERR` then reads 2; 65529 is accepted
        and leaves ERR at 0). Live *before* this slice and independent of blanks —
        but the blank fix widens its reach, so it landed here.
        ⚠️ **And the first cut of the fix did not catch it**: a ceiling tested on
        the *finished* value cannot see an accumulator that already wrapped, so
        `99999` passed a bound it was 34463 lower than. The overflow is now caught
        **where it happens** (any carry out of the `*10+digit` chain saturates to
        `$FFFF`), and knives C/D show the two halves are independent.
      * **THE BODY OFFSET HAS A RULE, and it is not the digit count.** The line
        number eats its digits plus exactly **one** blank — **none when its VALUE
        is zero**. `00 REMX` eats none and `01 REMX` eats one (same digit count,
        same leading digit); `0 0 REMX` reaches zero *through* a blank and still
        eats none. `skip_spaces` had been eating the whole run.
      * **A BLANK BEFORE AN `ON…GOTO` COMMA ENDED THE LIST**, so every later
        target crunched as a plain literal — the same failure `bl_num`'s own
        comment records for an *empty* slot, one character to the left of where
        that one was fixed. The blank rule does not explain it; `ref-oncomma`
        found it, and the fix is **two bytes cheaper** than the test it replaces.
      * **IT IS NOT THE LINE-NUMBER SCAN AT ALL** — it is the decimal *number*
        scanner (`A=1 0` → literal 10). Split out above, with the bounding
        controls (hex / string / REM / variable name) already measured.
      Sites fixed: `parse_lineno` + `dl_store`
      ([`basic/program.asm:200`](basic/program.asm:200)) and `bl_acc` + `bl_done`
      ([`basic/tokenise.inc:630`](basic/tokenise.inc:630)) — two copies of the
      same lookahead **on purpose**: they live in different ROMs (the crunch body
      is evicted to the sub-ROM), so no call could be shared. `mrg_storeline`
      ([`basic/files.asm:1620`](basic/files.asm:1620)) reaches the storage path
      through `dispatch_line` and is covered by construction.
      ⚠️ **A blank is only transparent when the run ENDS IN A DIGIT.** A greedy
      skip gives the right line number and the wrong body, which is why the scan
      looks ahead across the run before committing to it.
      ⚠️ **`num-zero` was labelled a two-sided CONTROL and it was RED.** The label
      was right about the blank rule and wrong as a claim about the row: it also
      exercises the body offset, which no rule in the spec covered when the label
      was assigned. **A control is a claim about which variables a row holds
      still**, and this one held fewer than its label said.
      ⚠️ **Apparatus: the standard echo guard would have been blind here.** The
      other probes squeeze runs of blanks so a wrapped echo still matches — and
      the blank *is* the subject, so squeezed, `2 0 REMX` and `20 REMX` are the
      same string and a dropped space reads as a clean echo. Not squeezing then
      reported `MANGLED` on **every row of both references** while the memory pass
      read them perfectly: the squeeze had been *hiding* a two-column screen
      margin, not tolerating it. `lstrip()` is no fix either (`num-lead` types a
      leading blank on purpose). The margin is now **measured per capture**.
      ⚠️ **And the `err` battery's control agreed for the wrong reason** — batched,
      it read back the `ERR 2` the previous row had just raised, because `reset`
      clears the program and not `ERRCODE`. Isolated it reads 0. That is
      [`probes/basic/basic_probe_linemax.py:276`](probes/basic/basic_probe_linemax.py:276)'s
      recorded trap, reappearing in a new probe within the hour — **and isolating
      the rows then broke them a second way**, because boot-per-case *ignores*
      `reset`, where the CF-3300's date-prompt CR lives.

- [x] ✅ **`WIDTH n`'s VALID DOMAIN — LANDED 2026-07-28, 76/76, falsified.**
      Was 🔴 FIVE silent screen-destroyers shipping today. The last residue of
      the abort-depth slice: [`docs/spec-basic-abort-depth.md`](docs/spec-basic-abort-depth.md)
      §7 deferred it in as many words — `4d35b6d` fixed how `WIDTH 300` *fails*
      and left open which `n` `WIDTH` should *accept*.
      Spec [`docs/spec-basic-width-domain.md`](docs/spec-basic-width-domain.md),
      characterization [`docs/width-vg8020-characterization.md`](docs/width-vg8020-characterization.md),
      gate `make width-acceptance` (76 rows, eight batteries). Baseline 36/62.
      **`ex_width` had no bound at all** — it ran the argument through
      `get_byte_arg` (domain 0..255) and then wrote `LINLEN` + a per-mode
      default + `CHGMOD` unconditionally. Measured on the VG-8020:
      **`SCREEN 1` accepts 1..32 and records `LINL32`; every other mode,
      GRAPHICS INCLUDED, accepts 1..40 and records `LINL40`** — so the old
      "any non-zero `SCRMOD` → `LINL32`" was wrong for `SCREEN 2`/`3`, visibly
      (`SCREEN 2:WIDTH 29:SCREEN 0` leaves the reference at 29 and zerobas at
      40). A reject writes NOTHING. Coercion truncates toward zero BEFORE the
      bound (`40.9` ok, `41.9` not), and **the domain check beats the deferred
      syntax error** (`WIDTH 41,` → ERR 5, not ERR 2) — the same ordering
      `MID$(A$,0,)` settled in D-MISS-2.
      🔴 **Two surfaces nobody had listed**, found by batteries written to cover
      the argument surface rather than to confirm the known defect — the fifth
      consecutive slice whose calibration turned up live defects in untested
      code: **`WIDTH "40"`/`WIDTH A$` must be `Type mismatch` (ERR 13)** and
      **bare `WIDTH` / `WIDTH :` / `X=1:WIDTH` must be `Missing operand`
      (ERR 24)** — zerobas silently took both as **width 0**.
      ⚠️ **THE SUBJECT UNDER TEST MOVES THE INSTRUMENT.** Every other probe
      reads the name table at a fixed 40-byte stride and `WIDTH`'s whole job is
      to change that stride, so the readout is numeric instead: capture
      `ERR` + `LINLEN`/`LINL40`/`LINL32` into variables, RESTORE
      `SCREEN 0`+`WIDTH 40`, and only then print. And **the instrument is pinned
      on every row** — unpinned, three controls that execute no `WIDTH` at all
      diverged on the boot width (37 vs 39) while their `ERR` codes agreed.
      ⚠️ These batteries **arm `ON ERROR` on purpose**, the opposite of
      `abort-acceptance`/`str-domain-acceptance`: those measure the unwind,
      which a handler hides; this measures the domain, and a trapped `ERR` read
      is the only readout that survives a statement that just destroyed the
      screen. The `unt` battery is the seam between the two gates.
      **Cost: 27 B, all page 1 (30 B → 3 B free)**, low region untouched at
      30 B, lean cart byte-identical. Cheap because `LINL40`/`LINL32` are
      ADJACENT (one `ld de` + a conditional `inc de` picks the slot and the
      bound rides the same test) and all three raisers already existed in
      page 1 — including `loc_missing`, the ERR 24 raiser `LOCATE` built.
      ⚠️ **3 B is not headroom — the next page-1 slice must open with a carve.**
      Falsified: neutering the bound reddens the two ordering rows while six
      unrelated `sx` rows survive; neutering the one-byte `inc de` reddens all
      11 `s1` rows. Standing gates re-run green: `unit-test` 53/53,
      `abort-acceptance` 23/23, `intarg-acceptance` ALL PASS,
      `str-domain-acceptance` 89/89.

- [x] ✅ **String-function ARGUMENT-DOMAIN checks — LANDED 2026-07-28, 89/89,
      falsified 51/89.** Was 🔴 SILENT wrong answers shipping today.
      Found by the MISSING-class calibration battery
      (D-MISS-2,
      [`docs/missing-vg8020-characterization.md`](docs/missing-vg8020-characterization.md)
      §8), which was not looking for it — the fourth slice running whose
      calibration turned up live defects in code that is not under test.
      `CHR$` / `LEFT$` / `RIGHT$` / `MID$` accept out-of-range arguments
      **silently and compute a wrong answer**:
      `LEN(CHR$(-1))`→`1`, `LEN(CHR$(256))`→`1`, `LEN(LEFT$("abc",-1))`→`3`,
      `LEN(MID$("abc",0))`→`3`, where the reference raises.
      Three things make this a slice rather than a one-liner:
      (a) **the family is inconsistent with itself** — `STRING$`/`SPACE$`/`ASC`
      DO check and are correct, so the mechanism exists and is reachable (the
      probe proves that with a control row before reading any other row as
      "zerobas cannot raise it"); (b) there are **TWO reference errors, not
      one** — `Illegal function call` inside byte range, but **`Overflow`**
      beyond int16 (`CHR$(32768)`, `CHR$(99999)`), raised by the argument
      coercion before the domain check runs, so an implementation that raises
      `Illegal function call` everywhere is wrong on half the domain;
      (c) **in-domain behaviour already agrees**, coercion included
      (`CHR$(65.7)`→`A`, `CHR$(64.5)`→`@`, i.e. truncation), so this is a domain
      check bolted onto correct code.
      **This is a different animal from the now-empty SILENT-GAP class** (absent
      reserved words), which is exactly why it survived it. Recommended as its
      own string-engine slice — see D-MC-2 in
      [`docs/decision-missing-class-slicing.md`](docs/decision-missing-class-slicing.md).
      ✅ **RE-MEASURED 2026-07-28 on a clean-built `73b4842`: all seven rows
      still reproduce**, boot-per-case, untrapped (`LEN(CHR$(-1))`→`1`,
      `LEN(CHR$(32768))`→`1` where the reference raises `Overflow`,
      `LEN(LEFT$("abc",-1))`→`3`, `LEN(MID$("abc",0))`→`3`).
      ⚠️ **ORDERED SECOND, behind D-CUR-D** (the abort-depth item above,
      signed off 2026-07-28): the natural implementation is four to five new
      `call get_byte_arg`s from inside the evaluator, i.e. four to five new
      members of a call convention that is measurably broken when untrapped.
      Landing that first would give the right ERR code under `ON ERROR` and
      trailing junk without it.
      ✅ **SPECCED + GATED 2026-07-28**, spec
      [`docs/spec-basic-str-domain.md`](docs/spec-basic-str-domain.md), gate
      `make str-domain-acceptance` (89 rows, six batteries). **41/89 diverge.**
      The measurement corrected this item on three counts:
      🔴 **THE FUNDING PREMISE BELOW WAS WRONG — there is nothing to fund.**
      Prototyped from clean: the low region goes **7 B → 30 B free (+23 B)** and
      page 1 **44 B → 30 B (−14 B)**. No promotion, no carve; lean cart
      byte-identical so `LEAN_SHA256` does not move. Two reasons the ≈45–50 B
      estimate missed: `get_int16_checked` already GUARDS HL so none of the
      assumed register-guard bytes exist, and `call eval` was ALREADY at every
      site — so a shared `eval_byte_arg`/`eval_pos_arg` pair in page 1 costs
      **zero bytes at the call site** and REPLACES rather than adds. The naive
      shape the estimate was costing was also built: +26 B, all low-region, a
      19 B overrun — 49 B worse on the wall that binds.
      🔴 **The `MID$` STATEMENT is a second broken surface**, not in this item:
      `MID$(A$,0)="X"` etc. give `syntax error` for seven reference errors, and
      **`MID$(A$,1,256)="X"` silently PERFORMS the assignment** while
      `MID$(A$,1,99999)="X"` silently does nothing.
      🔴 **`INSTR` is silently wrong too, and was on no list** —
      `INSTR(256,A$,"b")`→`0` where the reference raises; it hand-rolls half the
      rule (`p<1` only, no upper bound, no int16 stage). Found because S-SD-3
      was answered by RUNNING the probe instead of by argument. **Folding it in
      makes the slice 20 B CHEAPER** — its hand-rolled checks are deleted.
      Also measured: `MID$`'s position is the family's one **1-based** argument
      (1..255); the int16 gate is the RANGE −32768..32767, not `|x| ≤ 32767`
      (`CHR$(-32768)`→IFC, `CHR$(-32769)`→Overflow), and `get_byte_arg` already
      implements exactly that, proven via `STRING$(-32768,65)`.
      ⚠️ Three standing gates went red BECAUSE this closes a divergence they
      record, and all three were EDITED, not silenced: `missing-acceptance`'s 8
      stale `d2-*` markers (**XDIVERGENT's D-MISS-2 section is now EMPTY** —
      every `d2-*` row is gated), `basic_probe_mid_stmt.py`'s asserted
      divergence (now an asserted AGREEMENT, and it keeps earning its place by
      proving `A$` is unmutated by the rejected assignment), and
      `tests/test_str_fn.py`'s `INSTR(0,…)` — which the host harness
      structurally cannot model once the reject raises, exactly as D-F2-2 found
      for `SPACE$`/`STRING$`. **No host unit test can cover any row of this
      slice**; the openMSX differential is the only instrument, which is why the
      falsification below is load-bearing.
      ✅ **LANDED**: `make str-domain-acceptance` **89/89**; low region
      **7 B → 30 B free**, page 1 **44 → 30 B**, lean cart byte-identical
      (`LEAN_SHA256` unmoved); `unit-test` 53/53, `abort-acceptance` 23/23,
      `intarg-acceptance`/`string-acceptance`/`missing-acceptance` green.
      **FALSIFIED 89/89 → 51/89**: all eight call sites reverted to plain
      `call eval`, rebuilt from clean. ⚠️ **The wall does NOT move under this
      falsification** (30/30 either way) — `call eval` and `call eval_byte_arg`
      are both 3 B and the helpers stay assembled, so unlike D-CUR-D the
      "low region went back" check is NOT available as proof the code left the
      image. Every survivor is explainable: `ctl` 7/7 and `in` 23/23 survive by
      construction (in-domain rows pass with and without the checks, which is
      why they can never be the evidence and why they must be there), the
      surviving `bnd` rows are all `STRING$`/`SPACE$`, and **`ext-instr-0`/`-neg`
      PASSED in the true baseline but FAIL falsified** — the hand-rolled tests
      are deleted, so that asymmetry is what proves the call site rather than
      the deletion is doing the work.

- [x] ✅ **~~Numeric → string assignment raises the wrong error~~ — MEASURED
      FALSE 2026-08-09** by the TODO staleness sweep,
      [`docs/todo-staleness-sweep-2026-08.md`](docs/todo-staleness-sweep-2026-08.md)
      §3.4. **All seven forms answer `Type mismatch` on zerobas**, matching both
      references — `A$=1`, `A=5`/`A$=A`, `A$=1+1`, `A$=LEN("x")`, `A=5`/`LET
      A$=A`, `DIM Q$(3)`/`Q$(0)=1`, with `A$="x"` → `x` as the positive control
      and the already-correct mirror `A="x"` → `Type mismatch` alongside.
      🔴 **THE ENTRY CARRIED ITS OWN CLOSURE ON ITS LAST LINE** — *"✅ D-MC-2
      SIGNED OFF: folded into the MISSING-class slice"* — and the MISSING class
      is recorded EMPTY. The checkbox is the only thing that never moved. A
      `- [ ]` whose body ends in a ✅ is exactly the shape this sweep exists to
      find.
      **What was believed, kept as the record of why:** (D-MISS-1, same
      battery). `A$=1`, `A$=A`, `A$=1+1`, `A$=LEN("x")`, `LET A$=A`, `A$=A%` and
      `Q$(0)=1` all raise **`syntax error`** where the reference raises
      **`Type mismatch`** — so `ON ERROR` sees the wrong code. The numeric-lvalue
      **mirror is already correct** (`A=A$`, `A="x"`, `A=CHR$(65)`,
      `Q(0)="x"`), which localises it: the string-lvalue assignment path never
      type-checks its right-hand side and fails in the parser instead. Small and
      well-characterised. ✅ **D-MC-2 SIGNED OFF: folded into the MISSING-class
      slice** — see [`docs/spec-basic-missing-class.md`](docs/spec-basic-missing-class.md)
      §3.6 (surface) and §6.5 (the two paths to fix, `ex_let_str` and
      `ex_let_arr_str`).

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

### Disk (`disk/` → `disk.rom`, slot 3-1) — complete, read **and** write
The full FDC + FAT12 + BDOS stack, both directions, each layer
differential-confirmed against real hardware/software (strictly black-box, no
disassembly): WD2793 physical sector read **and** write vs the **National
CF-3300**, and the FCB BDOS file read **and** write (Open/SeqRead/Close +
Create/SeqWrite/Close, on a FAT12 read+write-back layer) vs real **MSX-DOS 1**.
The interpreter side lives in `basic/`: `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for
`"A:"`, the `init_ext_roms` slot-scan ([`basic/initext.asm`](basic/initext.asm))
that boots the disk ROM, and the cross-slot BDOS calls. See
[`disk/TODO.md`](disk/TODO.md) and [`disk/PROVENANCE.md`](disk/PROVENANCE.md) for
the per-item record and the documented divergences (FCB bookkeeping fields,
directory timestamps, the intentional GETDPB stub).

### Tape (`tape/` → zerobas-tape IPS patch) — device layer complete, read **and** write
The cassette signal layer C-BIOS lacks: `TAPION`/`TAPIN`/`TAPIOF` (read) and
`TAPOON`/`TAPOUT`/`TAPOOF` (write) — FSK leader detect + auto-baud + byte framing
and the write waveform, at 1200 and 2400 baud, round-trip validated on MSX1 /
MSX2 / MSX2+. See [`tape/DESIGN.md`](tape/DESIGN.md) and
[`tape/PROVENANCE.md`](tape/PROVENANCE.md). The **interpreter** side is now at full
parity — `BLOAD"CAS:",R`, `CLOAD` and `LOAD"CAS:"` load and `CSAVE`/`SAVE"CAS:"`/
`BSAVE"CAS:"` save on-device. (The CLOAD on-device fix turned out to be a
`basic/cload.asm` link-word register clobber, not a tape change; tape SAVE writes
the `$D3`/`$D0` cassette format through `TAPOON`/`TAPOUT`/`TAPOOF`. Both are
oracle-validated — see the now-checked items in the **Remaining** section above and
`basic_probe_tape_save.py` / `basic_probe_cload_ondevice.py`.)
