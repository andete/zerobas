- [ ] 🙋 **THE LAST THREE UNATTRIBUTED KEYWORDS ARE AN APPARATUS PRICE, NOT A
      METHOD — `CLOAD`, `CSAVE`, `INKEY$`.** Joost's 2026-09-12 ruling drains the
      "no known gap" list to ZERO before TIER 4, and the drain has run from 114 to
      these three. Every one of them now needs APPARATUS rather than a cleverer
      row, and the ruling was about draining EVIDENCE — whether that evidence is
      worth this much apparatus is a different question.
      **Recount before reading any of this: `make tiers ARGS=--keywords`.**
      | word | what it needs | what already exists |
      |---|---|---|
      | `CLOAD` | 🟢 **NOTHING — THE ORACLE EXISTS.** The VG-8020 reads a clean-room `.cas` (`Found:ZQ`) in DIRECT mode; the earlier "no oracle" was a fixture that was itself the tape-write defect. A `NEEDS-TAPE:` rig is now a small job | the rig, `cas_encode.build_cas_basic`, `run_cases(cassette=…)` added this slice, and a screen-visible readback needing no capture |
      | `CSAVE` | a WAV-DECODE capture in kwsweep — its only output is the recording. 🔴 **AND ITS SUBJECT IS NOW A FILED TIER 1 DEFECT**, so the row should be written WITH that fix, not before it | the decode, in [`basic_probe_cassave.py`](probes/basic/basic_probe_cassave.py); `NEEDS-LOG:` is the precedent for a per-rig capture |
      | `INKEY$` | the key injector's TIMING exposed to a row — a HARNESS change | `omsx_repl.key_proc()`, race-immune and measured, driven by two trap probes |
      ⚠️ **THE `INKEY$` ONE IS THE ONE TO BE CAREFUL WITH**: the timing lives inside
      `run_cases` (`boot` + per-line `step`), a row cannot see it, and D-LATCH /
      D-LATCH2 are the races a change there must not reopen.
      🎯 **WHAT THE DRAIN HAS ALREADY BOUGHT, so the price is judged against
      something**: four TIER 1 defects came out of this list — `NEW`, `FILES`,
      `LFILES`, `MERGE` — plus `LOAD`, which only the `MERGE` sweep could have
      found. The hit rate on the cheap words was high; these three are the
      expensive tail.
      🎚️ STANDING — ruling
      🙋 NEEDS-JOOST — the question is "is the apparatus worth it", and three
      different pieces of it, so it is his call rather than a loop tick's.
