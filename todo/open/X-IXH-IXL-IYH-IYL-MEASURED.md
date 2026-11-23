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
      🎚️ BUDGET — ROM/speed idiom
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended.
