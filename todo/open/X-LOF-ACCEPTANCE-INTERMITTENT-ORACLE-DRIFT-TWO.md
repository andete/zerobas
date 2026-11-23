- [ ] ⚠️ **`lof-acceptance` intermittent oracle drift — two sightings, nothing
      since.** Sighting 3 has not occurred across EIGHT consecutive slices
      (D-PINDATA, D-INJSINK, D-ROMJUDGE, D-DSKJUDGE, D-CITEJUDGE, D-DOCJUDGE,
      D-BYTEJUDGE, D-REVJUDGE — the last at 45 cases, 0 oracle drift, whole log
      captured, 59 lines). A third IS a finding to
      chase; capture the **whole** log (`> file 2>&1`), because sighting 1's row
      identity was lost to a `tail -6`. Detail: line 3678.
      📏 **STILL NOTHING, AND THE DENOMINATOR IS MUCH LARGER NOW: +24 FULL GREEN
      BATTERIES ON 2026-09-05..06 ALONE** (counted from the run logs that carry
      `recorded: this full green battery`, filtered by mtime — not from memory),
      every one of which runs `lof-acceptance`, with **zero** oracle drift in any
      of them. So the watch stands at eight slices plus twenty-four batteries.
      ⚠️ **A LONGER QUIET RUN IS NOT EVIDENCE OF ABSENCE FOR AN INTERMITTENT** —
      it raises the bar for what a third sighting would have to be, and the
      instruction to capture the WHOLE log is what makes the third one usable
      when it comes.
      🎚️ APPARATUS — oracle flake
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
