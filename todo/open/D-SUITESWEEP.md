- [ ] 🔬 **WHICH GATE SUITES EARN THEIR TIME? A CENSUS, THEN A MUTATION SWEEP (D-SUITESWEEP, Joost
      2026-11-01: "I have a feeling 90% of our test suite is wasted time" -- the sweep: "yes").**
      🎚️ APPARATUS — every commit pays for the batteries (a FULL run is ~25-29 min today).
      🤖 **AUTONOMOUS** — the OUTPUT is a LIST for Joost to rule on (drop / merge / move to a
      daily sweep, as kwtime / kwram were); nothing is removed automatically.
      📏 **STEP 1, THE CENSUS (2026-11-01, zero emulator time):**
      [`suite_census.py`](scratchpad/suite_census.py) ->
      [`suite_census.out`](scratchpad/suite_census.out). Of 252 suites with >= 20 logged gate
      runs (1777 logs), 157 never went red in one (a red that came back green on its serial
      retry counts as a flake) -- 48% of the summed suite seconds. 27 of the most expensive
      never went red ANYWHERE recorded, knife and iteration logs included: kwram (already
      out of the batteries), ctrlkeys (~8.5 min), math, ifsem, width, six lineerr shards,
      arrdim, nodisk, intarg, string, inputary, sound and more. ⚠️ CANDIDATES, not a verdict:
      saved logs are the runs someone kept; some knife scripts print their own red rows
      instead of failing through make; never red can mean "guards something nobody broke".
      📏 **STEP 2a, DONE 2026-11-01 -- EVERY MEASURED SUITE CATCHES A KNIFE IN ITS OWN
      SUBJECT: 18 / 18** ([`suitesweep_knives.py`](scratchpad/suitesweep_knives.py) ->
      [`suitesweep_knives.out`](scratchpad/suitesweep_knives.out); one same-length instruction
      per suite, designed by a read-only study, every anchor unique, every plant moved the
      ROM hashes, base restored byte-identical): math, ifsem, width, lineerr, arrdim, nodisk,
      dout, intarg, pulong, catterm, basicint, inputary, string, binfre, instr128, loaddi,
      caswbrk, sound -- all RED. NO READING for ctrlkeys and biosregs: their subjects live only
      in cbios-repack/*.patch, and the edited patch failed the main-ROM build (unexamined).
      🔮 MISS: predicted ~16 / 20 with caswbrk / loaddi / nodisk the likely misses -- all
      three caught. ➡️ **So "never red" here means STABLE, not BLIND**: the census alone
      would have been read the wrong way. The waste question becomes CADENCE and
      REDUNDANCY, which is Joost's call: (a) move long, stable suites to the daily sweep
      (as kwtime / kwram) -- the costliest never-red ones are ctrlkeys (~8.5 min), screenerr,
      lnblank, programs, the lineerr shards; (b) STEP 2b, which cheaper suites catch the same
      18 knives (redundancy) -- a whole battery per knife, ~7-8 h for all 18.
      🏗️ **RULED (Joost, 2026-11-01): "run the long stable suites daily".** DONE the same day:
      tools/run_gates.py `DAILY_SUITES` -- the never-red-in-a-gate-run suites averaging >= 60 s
      (ctrlkeys, screenerr, lnblank, math, ifsem, deffn-strict, deffn, width, lineerr (8
      shards), arrdim, castail, nodisk, pusing, penderr) leave every battery, FULL included;
      a SCOPED plan still RUNS one it picks for what changed (`--keep`, passed by
      pick_gates.py); `make gates-sweeps` runs them with kwtime / kwram, and a green run
      writes a `daily_suites.stamp` beside the kept sweep pins (run_gates.SLOW_PIN_KEEP; not
      committed -- it is per-machine state), which gates-plan reads for its "due"
      line. Step 2b (redundancy) stays open, for a quiet day / overnight.
      📏 **SIDE FINDING (same day): a docs-only commit is SCOPED, not STATIC, because every
      TODO edit rewrites cited line numbers inside scratchpad/missop3_probe.py,
      playop_probe.py and revertsweep.py** -- the planner then schedules their emulator
      suites (~9 min) for a comment change. Every TODO commit today paid it. ✅ **FIXED
      2026-11-01**: tools/pick_gates.py `drop_citation_only` -- a .py / .tcl whose diff
      against HEAD is only `TODO(-done).md:<n>` numbers (removed == added once normalised)
      is not a change; selftest P17 / P17b (a real change beside it still counts) / P17c.

      - [x] 🔧 **D-P1CLOSURE: `check_tenant_closure.py --page1` NEVER WALKS THE PAGE-1 TENANTS
        PAST INDEX 13 (found 2026-11-03 by step 2a).** 🎚️ APPARATUS — it stops at the retired
        index 13's `ret / nop / nop`, so grpprt, edctrl, frelive and now loadsave are never
        closure-checked. 🤖 **AUTONOMOUS** -- walk the whole table (skip retired rows), and
        teach the gate p1cb's IX-target class (the 46 `p0_*` names) and CLPRIM ($F38C, RAM).
        Run by hand with ls_tenant + p1cb as seeds on 2026-11-03: no call into sub page 0,
        sub2 or main page 1.
        🔴 **AND THE PAGE-0 WALK HAS THE SAME HOLE (found 2026-11-04 by step 2e):** its seed
        scrape stops at index 11's retired `ret`, so indexes 13-19 (lrsetst, deffn, pusign,
        puemit, lofu32, keystr, filestmt) were never closure-checked. A seeded walk from
        file_tenant: 70 labels, no rst, outside callees only CLPRIM (RAM) and two direct main
        page-1 calls. The fixed gate must accept CLPRIM, p0cb / p1cb IX targets and asserted
        direct page-1 calls (keystr's pchar / print_crlf too).
        ✅ **FIXED 2026-11-04 (tools/check_tenant_closure.py only).** The scrape reads each table to
        the next label, accepts only `jp <tenant>` or the exact retired `ret / nop / nop`, checks
        each row's index comment, and the row count against the built symbols (page 0 20 rows,
        page 1 35). The hole was bigger than filed: page 1 had skipped ALL 21 rows from 14 to 34.
        Named allowances, each with a RED negative arm: CLPRIM at $F38C (RAM, by name AND
        address); H_ERRP via CALLF on page 1 only (errmsg's disk-ROM offer); `p0_*` names judged per
        site -- an IX target consumed by p0cb / p1cb, a DE continuation, a call-back argument; a
        direct page-0 -> main page-1 call only behind an `IF name < $4000` assert, with main's
        code behind it walked to stay in page 1; a page-1 direct `p0_*` call only when main's
        code stays below $4000. Selftest W1-W7 / A1-A5 / B1-B9 / C1-C6 / D1-D4 / L2 green; each rule
        broken in a temp copy reddens its arm. Real tree: page 0 18 tenants, page 1 34, NO
        escape ([`p1closure.out`](scratchpad/p1closure.out)).
      - [x] 🔢 **D-EXPWRAP (suspected 2026-11-03, UNMEASURED): `1E65540` may crunch as `1E4`.**
        🎚️ TIER 6 — every error, until measured. 🤖 **AUTONOMOUS** -- batch 3's tkfloat reviewer read
        `tke_dloop` as multiplying the exponent by 10 mod 65536 BEFORE its 9999 clamp, so a
        running value of 6554..9999 wraps below 9999 (6554 * 10 = 65540 -> 4). Measure first:
        type `PRINT 1E65540` and `A=1E65540` on zerobas and both references.
        ✅ **MEASURED AND FIXED 2026-11-04.** VG-8020: `1E65540`, `1E65536`, `1E-65540`, `1D65540`,
        `-1E65540` and `A=1E65540` are all `Overflow`, like `1E64` / `1E99999` / `1E-99`; `1E-65` is 0.
        zerobas printed `10000` / `1` / `1E-04` / `10000` / `-10000` for the first five (the
        exponent's x10 wrapped mod 65536) and agreed on every edge. 🔮 "references Overflow,
        zerobas 1E+04" -- HIT (zerobas printed it as `10000`). sub/tkfloat.asm tke_dloop now
        saturates BEFORE the multiply (DE > 999 -> 9999; +8 B sub page 0). Gate `make
        expwrap-acceptance` (probes/basic/basic_probe_expwrap.py: a control, 5 wrap rows, 4
        edges; VG-8020, zerobas DISK and NODISK): 10/10 after
        ([`expwrap_after.out`](scratchpad/expwrap_after.out)); knifed back to HEAD's loop, the 5
        wrap rows RED and the edges green ([`expwrap_knife.out`](scratchpad/expwrap_knife.out)).
        Docs: docs/concepts/numbers.md. (The CF-3300 needs a boot disk; not run -- the VG-8020
        is the preferred reference.)
      - [x] ✅ **D-MULHANG (2026-11-03): NOT A HANG -- lvfix's disk rows were read 2.5 s after
        `RUN`, and the run takes ~3 s.** `ary_mul16_checked`'s reorder leaves every register
        and flag as before, yet lvfix's f.ary2d (`INPUT #1,A$(1,1)` after `DIM A$(2,2)`) read
        the program and `RUN`, then nothing. Bisected to that hunk; padding the bytes back kept
        it red, a `nop` in the old loop kept it green -- which read as "the faster loop exposes
        a hang". It was not: PC sampled under the probe's OWN timeline (registers only) shows
        the program at the prompt again at ~36 s, while the screen is read at a fixed 35.5 s
        (`RUN` + `step`; `cap_gap` does not move it, `run_gap` does). Four file operations on
        a floppy take ~3 s, and a few cycles anywhere can move a sector request past the head
        and cost a revolution. Fix: the probe's disk rows take `run_gap=8.0`
        (probes/basic/basic_probe_lvfix.py); lvfix 22/22 with the reorder back in, sub page 0
        722 -> 729 B free ([`mulhang_reloc.out`](scratchpad/mulhang_reloc.out)). Contract-diff
        ([`mulhang_contract.out`](scratchpad/mulhang_contract.out)): one `broken` row,
        `pu_to_field [main]`, against a main ROM that is BYTE-IDENTICAL to HEAD (sha 54cc8a2e
        both) -- the analyser's view of that routine follows the sub ROM's layout (it was the
        "inferred unknown" `wider_in` row one commit earlier). 🔭 The CLASS is open: any probe
        row that runs disk I/O and is read `step` after `RUN` has the same thin window --
        D-DISKWINDOW below.
      - [x] ✅ **D-REFBYPASS + D-REFSONLY (2026-11-03): THE REFERENCE MACHINES ARE MEASURED
        ONCE, NOT ON EVERY RUN.** Joost, asked why a VG-8020 run is not a fixed result:
        *"do it before the sub2 rereads, it'll save time every next test run"*. Two holes:
        29 probes launched openMSX THEMSELVES, past run_cases' reference cache (ctrlkeys, the
        five trap probes, the tape / boot probes, and everything through omsx_run.py); and
        tools/run_gates.py forced the cache OFF for every battery (spec-refcache §6: a warm
        store once let a gate pass on zerobas readings it never measured). Fixed:
        `cached_run` (probes/lib/probe_refcache.py) keys a direct launch on the machine's
        bytes, the script with per-run paths as placeholders, every input file's hash and the
        harness; omsx_run.py goes through it; 12 probes wrapped. 🏗️ **JOOST, same day: "References
        only"** -- batteries now run `ZEROBAS_REFCACHE=refs`: a REFERENCE reading is replayed,
        zerobas (decided by its ROM bytes, name as a cross-check) is measured on every run and
        never replayed, and a served zerobas reading stops the run (spec-refcache §6.1).
        Measured: ctrlkeys 515 -> 0.3 s and the trap probes 35-105 -> ~0.5 s on a repeat in mode 1;
        interval-trap-acceptance in `refs` mode 96 s -> 44 s (42 references replayed, 42 zerobas
        boots, the same rows); verify mode 0 mismatches on six probes; probe_refcache selftest 78
        arms green. The first battery under `refs` re-measures every reference once.
        🔴 **AND THE NEXT FULL STILL MISSED 718 REFERENCE READINGS (2026-11-03): run_cases keyed a
        disk / tape / cart argument by its PATH**, and the disk and tape probes copy their image
        to a fresh temp file per run, so every run was a new key (905 replayed, 718 re-stored).
        Now a media parameter is keyed by its bytes (`_param_key`, selftest KM1 / KM2).
        Measured, refs mode twice: wszero 85 -> 40 s (74 / 74 replayed), namspc 91 -> 36 s
        (201 / 201), zerobas measured on every run of both.
        🔴 **AND THE FIX OPENED THE NEXT HOLE (2026-11-04): a disk-writing call has TWO results.**
        Once media was keyed by bytes, the six disk-write suites (savedate, diskfull, asavechan,
        asavedev, putdir, wcache) began to HIT -- and read "INSTRUMENT FAULT: the CF-3300 wrote
        nothing", because a hit replayed the screen and never the disk the probe reads back.
        Now an entry carries every media file the run changed (compressed) and a hit writes it
        back; media-carrying keys moved to version 2 so no older entry is served (selftest KM3;
        savedate in refs mode twice: both PASS, the second from the store).
      - [ ] 🔭 **D-DISKWINDOW: SWEEP THE PROBES FOR DISK ROWS READ `step` AFTER `RUN` (found by
        D-MULHANG, 2026-11-03).** 🎚️ APPARATUS -- a row that passes by less than a disk
        revolution goes red on any unrelated carve and reads as a ROM defect. 🤖
        **AUTONOMOUS** -- for each `run_cases(... diska=...)` caller without `run_gap` /
        `sentinel`, measure the RUN-to-prompt time on zerobas and the references (PC at the
        prompt's key wait, registers only) and give the thin ones a budget.
      ➡️ Byte-level rereading cannot close it (D-REREAD stopped at ~2 B / routine); the
      routes are structural: D-REREAD-EDGES (below, in D-REREAD's block), tenant merges,
      main / sub duplicate removal.
      ⏩ **Second half, TIER 5 (speed is paused for ROM space):** promote HOT tenants into
      main page 0 / 1 once the walls allow. The 2026-07-30 de-eviction refutation priced
      BYTES at a 0 B wall; this prices TIME: count each tenant's entries over the program
      ladder (a trampoline watchpoint -- registers / RAM only), x the round-trip cost, / the
      main bytes the move costs; promote from the top, re-rank after each move. Suspect #1:
      ary_engine (scalar lookups share it, the hot path). Only into page 1 unless a low
      label's forced set allows it; nothing a tenant calls back into.
