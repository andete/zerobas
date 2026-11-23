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
      🎚️ APPARATUS — capture sentinel
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (both halves differentialled 2026-08-26; the standing gate remains).
