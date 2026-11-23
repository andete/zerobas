- [ ] ⚠️ **A probe with an honest `rc` that NO battery collects is not an oracle.**
      Opened 2026-08-27 by D-WALLIT,
      [`docs/spec-wall-literals.md`](../../docs/spec-wall-literals.md) §3.1.
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
      [`docs/spec-probe-reach.md`](../../docs/spec-probe-reach.md)): 204 probes — 89
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
      [`docs/spec-casin-settle.md`](../../docs/spec-casin-settle.md)): `probes/tape/`
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
      🎚️ APPARATUS — uncollected probes
      🔁 **RULED (Joost, 2026-09-10): stays as classed** — not before TIERS 1–4 unless it
      blocks a keyword tier; still his call when it is picked.
      🤖 AUTONOMOUS — 🏗️ **RULED BY JOOST 2026-10-27**: *"You pick, under a budget"* -- rank the 104 by what each catches that the battery does not, collect the best into ~+120 s; (a) is done; (b) was which of the 104 earn a battery slot, a
      runtime-budget call and the measuring in front of it is finished.
