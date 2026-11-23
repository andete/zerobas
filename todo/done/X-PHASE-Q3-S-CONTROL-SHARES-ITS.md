- [x] 🔴 **PHASE Q3's CONTROL SHARES ITS SUBJECT'S STATEMENT, SO THE PAIR CANNOT
      ✅ **CLOSED 2026-09-05.** The control is honest about its own cell, re-verified under `M-G8PAREN` — the very mutation that exposed it — with `ie_off` FAILing and `control` PASSing where both used to move. Nothing outstanding.
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
