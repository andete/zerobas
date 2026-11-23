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
