- [ ] ⚠️ **NINE ACCEPTANCE ROWS STILL NEED A REFUSAL CUT, ONE PER PATH.** Filed
      2026-08-17 by D-GATEBLIND round 5 (§20). `M-PSETOFF` and `M-DRWSCALE` proved
      the shape works — an off-screen `PSET` made to raise reddens
      `pset_offscr_ok`, and a narrowed `S` bound reddens `scale255ok`/`scale0` —
      but each remaining acceptance row sits on its own path: `off_ok` (LINE),
      `clip_neg_ok` / `clip_offscr_ok` (CIRCLE), `border16_flood_ok` (PAINT),
      `bare_b` / `empty` / `offscreen` (DRAW), `arc_ovf_r260` /
      `arc_ovf_wrap300` (the arc mask). ~~💰 Six or seven cuts, one each; there is no
      shared site the way `gdrw_err5` was for phase L.~~
      🔴 **THE COST ESTIMATE IS WRONG, MEASURED 2026-09-05 by walking every site.
      ONE of the nine has a retargetable branch; two are miscategorised; six
      would need a check SYNTHESISED, not a jump retargeted.**
      | row(s) | verb | reads | arm |
      |---|---|---|---|
      | `border16_flood_ok` | PAINT | **pixels** | ✅ **DONE** — `M-PAINTBDOM` |
      | `arc_ovf_r260`, `arc_ovf_wrap300` | arc | **pixels** | ⚠️ not acceptance rows at all |
      | `off_ok` | LINE | error code | ❌ nothing to retarget |
      | `clip_offscr_ok`, `clip_neg_ok` | CIRCLE | error code | ❌ nothing to retarget |
      | `offscreen`, `empty`, `bare_b` | DRAW | error code | ❌ nothing to retarget |
      🎯 **WHY `M-PSETOFF` WORKED AND THESE CANNOT.** PSET's off-screen decision
      is a BRANCH IN THE RESIDENT (`basic/graphics.asm:101`,
      `jp nc,exec_stmt`), where `gfx_err5` is reachable — so the cut is one
      retarget. LINE/CIRCLE/DRAW do not decide off-screen at all: they clip in
      the TENANT, at `gfx_plot_cur`'s three bare `ret`s (`sub/graphics.asm:665`
      /`669`/`672`), deep inside plotting loops that cannot raise. And `empty` /
      `bare_b` are accepted by the **absence** of any test — the only exit they
      share is `gdo_done`, which EVERY `DRAW` takes, so a cut there reddens the
      whole verb and isolates nothing. **These six rows read only the error code,
      so no cut that changes what is DRAWN can move them; the arm has to make the
      statement RAISE, which means writing a bounds check that does not exist.**
      ⚠️ **AND TWO WERE NEVER ACCEPTANCE ROWS.** `arc_ovf_r260` /
      `arc_ovf_wrap300` are documented IN THE PROBE as *"ONE-SIDED DETECTORS…
      blank on BOTH machines now, and a both-blank row is vacuous"*. Their arm is
      "make the mask paint again", not "make it refuse" — they belong to the
      arc-mask residual, not this one.
      ✅ **`M-PAINTBDOM` LANDED** (`ep_b_dom`: SCREEN 2's border domain narrowed
      from 0..255 to the nibble, so `PAINT(5,5),9,16` raises). PAINT's border is
      the one argument here that is genuinely domain-checked, which is why it has
      a branch. Measured: 2 rows red, ROM restored byte-identical.
      🔴 My prediction said "`border16_flood_ok` ONLY" and was one row too
      narrow. `b_s2_16_comma` moved too (`ref='E 2'` → `zb='E 5'`) — it is the
      row that races this domain against the grammar's trailing-comma ERR 2, and
      it is the reason the check sits ABOVE the fill, so a domain cut cannot help
      moving it. **A prediction can be too narrow because it forgot which row
      exists to pin the check's PLACEMENT.**
      💰 **REVISED: 1 done. 6 need a synthesised check each (not a retarget) —
      genuinely more expensive than filed, and worth asking whether an
      error-code-only acceptance row is the right shape before writing six of
      them.** 2 to be re-filed under the arc mask.
      🔬 **M-PLOTCLIP, 2026-09-10: THE ONE ARM 35 MUTATIONS NEVER TRIED — CUT
      THE CLIP SO IT STOPS CLIPPING**
      ([`scratchpad/plotclip_knife.py`](../../scratchpad/plotclip_knife.py),
      [`.out`](../../scratchpad/plotclip_knife.out)). `gfx_plot_cur`'s three bare `ret`s
      become `nop`s, so an off-screen coordinate is plotted instead of dropped.
      Of the 35 arms in [`scratchpad/gate_blindness.json`](../../scratchpad/gate_blindness.json)
      only `M-YBOUND` touches that routine, and it NARROWS the bound (`cp 192` →
      `cp 191`) — narrowing keeps off-screen plots clipped, so a row asserting
      "off-screen draws nothing" correctly never moved. `M-CLAMPX`/`M-CLAMPY`
      sound like the site and are not: they cut `gfx_clamp_coords`.
      🟢 **RESULT 1 — THE SIX ERROR-CODE ROWS HELD, 6 of 6.** `off_ok`,
      `clip_offscr_ok`, `clip_neg_ok`, `empty`, `bare_b`, `offscreen` all unmoved
      under the strongest cut available at their own clip site. **The "needs a
      check SYNTHESISED" verdict above is now MEASURED rather than inferred from
      walking the code** — removing the clip changes what is drawn and raises
      nothing, and a row that reads only the error code cannot see it.
      🔴 **RESULT 2 — MY PREDICTION FAILED, 0 of 4, AND THAT IS THE USEFUL HALF.**
      I predicted the four PIXEL clip rows (`clip_noop_x300`, `clip_noop_xneg`,
      `clip_noop_y192`, `clip_alloff`) would move, reasoning that they read the
      pixel plane and assert an off-screen plot changes nothing. They did not.
      **So they are not about `gfx_plot_cur` at all**: their coordinates are
      refused earlier, by the RESIDENT's own off-screen decision
      ([`basic/graphics.asm:101`](../../basic/graphics.asm:101)), and never reach the
      tenant. ➡️ Their arm is a cut that makes an off-screen PSET **plot** — not
      one that makes it raise, which is why `M-PSETOFF` left them quiet too
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
      🎯 **RESULT 3 — `arc_ovf_r260` AND `arc_ovf_wrap300` MOVED, WHICH REFUTES
      THE PARAGRAPH ABOVE.** This entry records them as *"ONE-SIDED DETECTORS…
      blank on BOTH machines now, and a both-blank row is vacuous"*. The battery
      is green at base, so a moved row went PASS → FAIL: **they detect this
      mutation, so they are not vacuous** and do not belong in the re-file pile on
      that ground. 13 further rows moved (`circ_ovf_*`, `ell_ovf_*`, `clampS_*`),
      so the arm is emphatically not inert; ROM restored byte-identical.
      🟢 **M-PSETPLOT, SAME DAY — EXACT, AND IT ARMS THREE MORE NEVER-REDDENED
      ROWS** ([`scratchpad/psetplot_knife.py`](../../scratchpad/psetplot_knife.py),
      [`.out`](../../scratchpad/psetplot_knife.out)). M-PLOTCLIP's failed prediction
      said where to look, and `basic/graphics.asm`'s own comment said it outright:
      the resident's `jp nc,exec_stmt` *"IS WHAT MAKES GFX_OP=1'S ALIASED
      MARSHALLING SAFE"* — the tenant's op-1 arm reads `GXPOS`/`GYPOS` **LOW
      BYTE** on the guarantee that this branch already refused everything else.
      Remove it and an off-screen `PSET` plots at the wrapped coordinate, which is
      exactly the address these rows read (`PSET(300,100)` → (44,100)).

          predicted MOVE  clip_noop_x300 clip_noop_xneg clip_noop_y192   3/3 ✅
          predicted HOLD  clip_alloff off_ok clip_offscr_ok clip_neg_ok
                          empty bare_b offscreen pset_offscr_ok          8/8 ✅
          rows moved in total                                            3

      🎯 **THE STRUCTURAL FACT, AND IT IS WHY 35 ARMS MISSED THEM: PSET AND
      LINE/CIRCLE/DRAW CLIP IN DIFFERENT PLACES.** PSET is refused in the
      RESIDENT, before the tenant is called; the others are clipped inside it at
      `gfx_plot_cur`. **A cut at one site cannot move rows that belong to the
      other**, and every one of the 35 aimed at neither
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
      🟢 **AND THE BRANCH NOW HAS A ROW THAT NOTICES WHEN IT GOES.** Its own
      comment calls it *"an invariant one instruction wide"* and warns "DO NOT
      MOVE THE TENANT CALL ABOVE THIS TEST" — until today nothing in the battery
      would have caught its removal.
      🔴 **CORRECTION, SAME DAY: THERE IS NO THIRD SITE, AND `clip_alloff` NEEDS
      NO ARM AT ALL.** I wrote that its holding under both cuts pointed at "a
      whole-segment line clipper — the next arm". **Wrong: LINE does not CLIP, it
      CLAMPS** (`gfx_line_op` → `gfx_clamp_coords`, D-SPOKELINE), so
      `LINE(300,300)-(400,400)` lights exactly **(255,191)** — and `clip_alloff`
      reads the **(0,24)×(0,24) top-left band**. The pixel is in the opposite
      corner from the row's window.
      🎯 **THE PROBE ALREADY SAYS SO, TWO LINES BELOW THE ROW**: *"a fully off
      screen LINE lights exactly (255,191) — the pixel `clip_alloff`'s top-left
      band was blind to since G3"*, and `sub/graphics.asm`'s own header records
      the same, "measured twice". I reached for a knife before reading the two
      files that had already answered it.
      🟢 **AND ITS LIVE TWIN IS ALREADY COVERED FOUR TIMES OVER.**
      `clampL_corner` is the SAME statement (`LINE(300,300)-(400,400),15`) with
      the RIGHT band (232..255 × 168..191), and
      [`scratchpad/gate_blindness.json`](../../scratchpad/gate_blindness.json) records
      it reddened by **M-CLAMPX, M-CLAMPY, M-COLOUR and M-YBOUND**. So the
      statement's behaviour is gated; only the blind band is not, and it cannot be.
      ⚠️ **NO SINGLE-SITE MUTATION CAN MOVE `clip_alloff`, BY CONSTRUCTION**:
      clamping puts the pixel bottom-right, and REMOVING the clamp sends the
      segment off-screen where `gfx_plot_cur` drops it — neither writes the top
      left. It belongs in the "geometry cannot reach the case" class, not in this
      entry's refusal-cut list
      [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
      💰 **REVISED AGAIN: the nine are 1 done + 6 measured-hard + 2 that are LIVE
      detectors after all.** The six remain the open question this entry already
      asked — whether an error-code-only acceptance row is worth six synthesised
      checks — now with evidence that no cheaper arm exists at the clip site.
      🎚️ APPARATUS — refusal cuts
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
