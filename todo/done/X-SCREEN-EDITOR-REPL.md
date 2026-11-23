- [x] **Screen-editor REPL** — real MSX BASIC does not use a sequential prompt
      loop; Enter reads the *current cursor line from VRAM* (not a dedicated
      input buffer), so the user can cursor-up to any visible output, edit it
      in place, and re-enter it. Needs cursor-key handling and VDP line-readback.
      Our `repl.asm` is a deliberate simplification; full replacement is Phase 3.
      📏 **SCOUTED 2026-08-26 (D-EDITSCOUT)**,
      [`docs/spec-basic-editscout.md`](../../docs/spec-basic-editscout.md) — placement
      only, nothing priced. **The feature is measured, not inferred**: the
      reference's counter payload reads **1 → 2 → 3** as re-entries accumulate,
      and entering from EITHER row of a wrapped line re-executes the whole
      LOGICAL LINE, so the reader must walk back to its start and forward through
      its continuations.
      🟢 **C-BIOS's `CHPUT` ALREADY HONOURS THE CURSOR-MOTION CODES ON THE
      ZEROBAS MACHINE** (`PRINT CHR$(31);CHR$(31);"Z"` moves Z +2 rows on BOTH
      sides), so the OUTPUT half is present and free. What is missing is the
      INPUT half: `read_line`'s `cp 32 / jr c,rl_loop` throws `$1C`–`$1F` away
      before `CHPUT` ever sees them.
      🎯 **THE PER-KEYSTROKE SUB-ROM-CROSSING WORRY IS REFUTED**: the
      per-keystroke path is `CHPUT`, and the novel work is ONE act per Enter —
      `lineedit_tenant`'s exact granularity. The "in-window 0.6–0.9 KB"
      classification in `docs/decision-phase3-space-strategy.md` §3 was signed
      off **2026-07-11, before the sub-ROM tenant architecture existed**; sub
      page 1 has 1622 B free and sub page 0 has 2464 B. ⚠️ **The byte cost is
      still NOT measured**, nor how the reader finds a logical line's START
      (the reference keeps per-row continuation bookkeeping; zerobas has none),
      nor `INS`/`HOME`/`CTRL` keys, and **`CF-3300` was not run**.
      🔴 **THE FIRST RE-ENTRY ROW WAS BLIND BY CONSTRUCTION** — `PRINT"AAA"`
      re-entered reprints `AAA` over the `AAA` already there, so a WORKING
      re-entry leaves the screen byte-identical to none. It read as "no feature".
      The wrong-row control (cursor-up ×1 onto an `Ok` row → `Syntax error`) is
      the only row that saw anything, and it had been written to rule out a
      different hypothesis.
      🟢 **TWO OF THE SCOUT'S UNPRICED BULLETS ARE NOW MEASURED (2026-09-07,
      D-EDITLINE, [`scratchpad/editline_probe.py`](../../scratchpad/editline_probe.py)) —
      AND THE BOUNDARY ONE WENT THE EXPENSIVE WAY.**
      | row | | vg8020 | cf3300 | zb |
      |---|---|---|---|---|
      | `x.plain` | POSITIVE CONTROL: re-enter an ordinary line | `2` | `2` | `1` |
      | `x.noup` | baseline, nothing re-entered | `0` | `0` | `0` |
      | `x.reenter` | payload row under a **PRINT-wrapped** full row | `0` | `0` | `0` |
      | `x.vpoke` | payload row under a **VPOKE-written** full row | **`1`** | **`1`** | `0` |
      (`A` = how many times the payload executed, read from a fresh
      `PRINT"ZQ";A;"QZ"` line after the re-entry.)
      🎯 **THE BOUNDARY CANNOT BE INFERRED FROM THE SCREEN.** `x.reenter` and
      `x.vpoke` put the SAME shape on the display — 40 apostrophes filling the row
      directly above the payload row — and get OPPOSITE answers. Where the fill was
      produced by a `PRINT` that wrapped, the machine walks back and takes both
      rows as one logical line, so the leading `'` REMs the payload (`0`); where
      the identical fill was written straight into the name table with `VPOKE`, it
      stops at the row start and executes the payload alone (`1`). **Both
      references agree**, so this is MSX1, not one machine.
      ➡️ **SO THE CHEAP RULE IS REFUTED.** The scout asked *"whether it can infer
      the boundary (a predecessor row filled to `LINLEN`)"*; it cannot. The
      reference keeps **continuation state the screen does not carry**, and a
      zerobas reader must keep its own — per-row bookkeeping written where the
      wrap happens, i.e. in the output path, not only in the reader. That is a
      cost the placement scout did not price and it is not zero.
      ⚠️ **WHAT THIS DOES *NOT* ESTABLISH IS THE MECHANISM.** "CHPUT recorded a
      wrap" is the obvious reading and it is NOT asserted — one pair of rows shows
      that the screen is insufficient, not what the sufficient thing is
      [[a-mechanism-inferred-from-one-observation]]. Any third rule that separates
      a wrapped `PRINT` from a `VPOKE` would fit these rows equally.
      🟢 **AND THE `CF-3300` BULLET IS CLOSED**: the scout ran ONE reference and
      said so. All five rows here run on both, and both agree on every one —
      including `x.plain`, which is D-EDITSCOUT's own re-entry row and reads `2`
      on the CF-3300 too. The screen editor is an MSX1 property, not a VG-8020 one.
      🔴 **THE FIRST CUT OF THIS PROBE WAS BLIND THE WAY §3 WARNS, AND ITS
      DOCSTRING CLAIMED IT WAS NOT.** It read the SCREEN and argued a REM'd
      re-entry would look different from no re-entry; it does not — the editor does
      not re-echo a line already on screen, and `Ok` reprints over the `Ok` already
      there, so `x.reenter` came back BYTE-IDENTICAL to `x.noup` on both
      references. Reading a VARIABLE on a fresh row is what made the rows say
      anything [[an-unnamed-outcome-reads-as-no-outcome]].
      🔴 **AND THE WIDTH WAS AN ASSUMPTION THAT MEASURED WRONG**: `STRING$(40,…)`
      was picked to fill a row exactly, and the first run showed **35** apostrophes
      per row on the VG-8020 and **39** on the CF-3300 — the two references were
      not running the same construction, and on one of them the payload row began
      with a stray `'`. Every side now sets `WIDTH 40` first.
      ⚠️ **STILL UNPRICED, UNCHANGED BY THIS:** the byte cost of the VRAM reader,
      `INS`/`HOME`/`CTRL`+key and the r23 function-key row, and whether a tenant may
      read VRAM from inside. The 0.6–0.9 KB figure remains the 2026-07-11 estimate.
      ✅ **THE HAPPY PATH SHIPPED 2026-09-11 (D-SCREDIT, [`docs/spec-basic-screditor.md`](../../docs/spec-basic-screditor.md),
      `make screditor-acceptance`, 10 rows, three sides).** The scout's one
      "not zero" cost measured ZERO: the reference's per-row continuation
      bookkeeping is the published `LINTTB` table ($FBB2: zero = the row
      continues), and **C-BIOS's `CHPUT` already keeps it on the zerobas
      machine** — zero on a wrapped `PRINT` row, non-zero on a `VPOKE`d one,
      shifted with every scroll — except for the wrap that itself scrolls the
      screen, where C-BIOS drops the mark (the reference keeps it); the reader
      writes that one mark when a typed character wraps on the bottom row.
      Two new faces the gate carries besides D-EDITLINE's rows: **`e.left`** —
      `A=1`, cursor-left, `2`, Enter reads `A=2` on both references and `12`
      here (a typo fixed with the cursor: the everyday case) — and **`e.csr`**,
      a two-row line that prints `CSRLIN` when re-entered from its first row:
      `2` everywhere, the cursor moved below its LAST row before it ran.
      🔴 **A CURSOR-UP COUNT FROM THE PROMPT IS NOT MACHINE-NEUTRAL** — zerobas's
      `ZB` prompt costs one row per typed line where the references' `Ok` costs
      two, so `↑↑` lands on different lines; the gate builds its screens from a
      program and navigates with HOME + DOWN × n (spec §2). Here: `read_line`
      waits in main and calls `readline_tenant` (sub page 1, index 25) once per
      key; the tenant echoes the cursor
      keys through `CHPUT`, records the row/column where input began (the
      `FSTPOS` rule — zerobas's `ZB` prompt, `INPUT`'s `? ` and `AUTO`'s number
      are excluded on that row; a re-entered REPL row skips its `ZB`), follows
      the start row up through scrolls, and on Enter walks `LINTTB` to the
      logical line's first row, reads it row by row out of the name table
      (`RDVRM`), strips trailing blanks and moves the cursor below its last row.
      `INPUT` with a wrapped answer at the bottom row (`i.wrap`, 45 chars, the
      prompt excluded) agrees on all three sides before and after. Cost: main
      page 1 5 → 11 B (the eviction funded itself), sub page 1 496 → 135 B, 7 B
      of RAM from the D-FORVAR band.
      🔴 **A PAGE-1 TENANT MUST NOT WAIT**: the first cut blocked in `CHGET`, and
      `htimi_guard` skips the PLAY/trap seam while a page-1 tenant is mapped —
      music stopped at the prompt (`play-trace` red on every row). The wait is in
      main now — INSIDE `CHGET`, as it always was, so the harness's injector
      latch (`latch-check`) still sees the wait it models — and the tenant is
      handed one key per call in `RL_KEY`.
      🔴 **A FIRST READING WAS TAKEN INSIDE A `PRINT` THAT HAD SCROLLED THE SCREEN
      AGAIN** — the `LINTTB` values after a bottom-row wrap were off by a row and
      said both machines dropped the mark; captured into variables first, the
      reference keeps it and only C-BIOS drops it. The apparatus is part of the
      measurement, again.
      🔴 **AND THE SAME BLIND SPOT POISONS OLDER ROWS**: every output line that
      wraps at the row above the bottom and then scrolls leaves a stale
      "continues" mark that C-BIOS's shift then walks UP the screen, so the
      prompt row after a screen-filling `LIST` read as part of the listing
      (`linemax`'s `list-max`). The prompt always opens a fresh line, so
      `read_line` now sets the two stale entries to "ends" at entry when the
      cursor is on the bottom row; rows further up can still carry stale marks —
      re-entering an OLD line that once wrapped at the bottom may join a
      neighbour (TIER 5, filed below; the faithful cure is bookkeeping in the
      output path, exactly the cost the scout named and only for those two rows).
      🎯 **AND THE PROMPT AFTER A GRAPHICS PROGRAM READS ITS LINE IN SCREEN 0** —
      measured on both references (the prompt after `SCREEN 2:END`, and `INPUT`
      inside SCREEN 2, both read in mode 0 with a wrapping line intact); zerobas
      stayed in SCREEN 2, where C-BIOS's rows are 32 wide and a wrapped line read
      back garbled (graphics phase M lost a line). `txt_mode` (`INITXT` when
      `SCRMOD` ≠ 0) runs before the prompt and at `read_line` entry.
      🎯 **AND ONE TIMING RACE SURFACED ELSEWHERE (D-PLAYEMPTY):** `gicini`'s
      `m.empty` — `PLAY""` then `PEEK(&HFB3F)` in the same program — read 1 where
      the references read 0. `PLAY` set the voice's `MUSICF` bit for an EMPTY
      string and only the next ISR tick cleared it; the row had been green
      because `RUN`'s dispatch left a tick pending at the PLAY tenant's `EI`, and
      the editor's own tenant call now consumes that tick first. A write-
      watchpoint on `$FB3F` (set at the tenant, cleared at `psv_end`) and a
      `JIFFY` check (interrupts live at RUN time) separated the two readings.
      `pt_vloop` drops a voice with an empty string from the commit mask: no
      queue, no bit — which is what the reference's immediate 0 says.
      🔴 **C-BIOS's SCROLL NEVER REWRITES THE LAST TWO `LINTTB` ENTRIES** (a
      write-watchpoint showed the reader's own wrap mark at [22] copied into
      [21] by every scroll and never replaced), so from the first wrapped line
      typed at the bottom on, every Enter spliced the row above the prompt into
      the read — ten battery suites red at once, each from its eighth case on.
      `rl_botfix` writes the two stale entries after each scroll the reader
      causes. A whole class failing identically was, again, one cell.
      🔴 **AND `sub/readline.asm` WAS NOT IN `SUB_PARTS`** — two builds shipped the
      first tenant unchanged; the wall reading that could not have stayed the same
      (sub page 1: 144 B twice) was the tell, exactly as D-PUDOT's note warned.
      🔁 **2026-10-03: EACH OF THESE IS NOW ITS OWN OPEN ITEM** (above), because
      a note inside a CLOSED item is invisible to the tier scan. `INS` mode and
      `DEL` mid-row were already done by D-INSMODE, the function-key ROW by
      D-DSPFNK. Open: D-LINTTBWRAP, D-LINTTBSTALE (D-EDCTRL, D-EDFKEY and
      D-EDINPUTCSR closed 2026-10-05/06).
      ⚠️ Later tiers, filed here: `INS` mode, `DEL` mid-row, `CTRL`+key, the
      function-key row and `SELECT`; a program `PRINT` that wraps on the bottom
      row loses its continuation mark on C-BIOS (re-entering it takes the last
      row alone), and older rows can carry stale "continues" marks after scrolls
      (D-LINTTBSTALE: the two entries C-BIOS never rewrites, and their upward walk); cursor keys inside `INPUT` across rows.
      🎚️ TIER 1 — happy path: the SCREEN EDITOR — typing, fixing a line with the cursor, re-entering a visible line — shipped 2026-09-11
      🎯 **RULED (Joost, 2026-09-10): *"the basic line and screen editor should also be in
      the list"* — explicitly on the TIER 1 pick list.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
