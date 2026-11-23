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
