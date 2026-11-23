- [x] ✅ **`.` — THE CURRENT-LINE PSEUDO-LINE-NUMBER — LANDED 2026-08-02
      (D-DOTLINE). Four pins RETIRED, none added; `lnblank-say-acceptance`
      108 -> 181 rows with 6 -> 2 pins; `lnblank-acceptance` 530 -> 536,
      allowlist still EMPTY. 16 corpus targets green, six knives scored.** Spec
      [`docs/spec-basic-dotline.md`](docs/spec-basic-dotline.md), measurement
      [`docs/dotline-msx1-characterization.md`](docs/dotline-msx1-characterization.md).
      Filed by D-DELETE, confirmed on a second verb by D-LSTRNG, both of which
      measured `.` and DECLINED it rather than ship a rule one verb wide.
      🔴 **THEY WERE RIGHT, AND FOR A BIGGER REASON THAN EITHER GAVE.** The four
      filed rows measured ONE writer — storing a line — and ONE argument
      position. The 77-row walk found **four writers and eleven measured
      NON-writers**, and three of the four would have been implemented WRONGLY
      from a `DELETE`- or `LIST`-shaped reading:
      * **`LIST` writes it**, to the LAST LINE IT PRINTED — not the argument,
        not either end — and a `LIST` that prints nothing writes nothing
        (`cln-listrng` 30, `cln-listbare` 40, `cln-listmiss` unchanged; the
        filed `LIST 40` row could not separate four candidate rules);
      * 🔴 **an ASCII `SAVE` WRITES IT TOO (40) and a tokenised one does not
        (20)**, because both drive the same walk.
        ⚠️ **THIS IS THE EXACT MIRROR OF THE HAZARD D-LSTRNG §3.3 HAD TO FIX IN
        THAT VERY ROUTINE** — a `LIST` range leaking into `SAVE",A"` was a
        data-loss bug — so reasoning by analogy says keep `DOT` OUT of the
        shared `list_walk` for ~16 B. The measurement says put it IN for 4 B.
        Same routine, two shared-code questions, **opposite answers**;
      * 🔴 **a DIRECT-MODE error writes NOTHING** — it does not take `ERRLIN`'s
        measured 65535 sentinel, so the two cells are written by the same event
        under different rules and the obvious shared tail (4 B cheaper) is
        wrong;
      * 🔴 **the `DELETE` VERB does not write it** even though the
        bare-line-number delete does. Two ways to remove a line, same visible
        effect on the program, different effect on `.`;
      * 🔴 **`RESUME` IS NOT A WRITER — AND THIS SLICE SHIPPED ONE BEFORE ITS
        OWN KNIFE FOUND IT.** `cln-trap` alone reads the HANDLER's line and
        would have been written up as "a trapped error records where control
        went"; `clp-trapend` (`50 END`) reads the ERRORING line, and
        `clp-onerr`/`-goto`/`-gosub` kill the rival "a line LOOKUP is the
        writer" reading. What replaced them — "a RESUME records the line it is
        IN" — was **implemented, ~12 B of page 1, and wrong**. Knife K5 cut it
        and moved **ZERO of 139 rows**: every supporting row had TWO SUFFICIENT
        CAUSES, because `RESUME NEXT` resumes into line 30 which then FALLS
        INTO line 50 again, raising ERR 22 *in line 50*. `clp-resend`
        (`30 A=A+4:END`, so line 50 is never re-entered) reads **20** on both
        references against the shipped build's 50. Withdrawn, **14 B
        recovered**; the slice costs 10 B of page 1, not 24
        [[knife-that-reddens-nothing-is-the-finding]];
      * **`NEW` does NOT reset it**, which `LIST .` is structurally blind to.
      🎯 **THE PUBLISHED WORK AREA NAMES THE VARIABLE — `DOT $F6B5`, "line
      number of last used (changed, listed, added) line"** (C-BIOS
      `systemvars.asm`, the same allowed source the sysvar denominator is
      generated from). Claimed at the published address under the published
      name for **zero ROM bytes**, D-REHOME's sixth honoured cell and the first
      that was never re-homed — it did not exist before. PUB-FREE measured
      first: zerobas' byte there read 0 in all 24 swept states.
      🎯 **AND THAT CELL IS WHY THE COLD MACHINE AND `NEW` ARE MEASURED AT ALL.**
      `LIST .` cannot ask either — on a cold machine, and after a `NEW`, the
      program is EMPTY, so nothing is listed whatever the cell holds and every
      reading compares EQUAL on every side. Every one of the 24 `clp` PEEK rows
      has a behavioural twin and **every twin agrees**, which is what makes the
      PEEK evidence about `.` and not about a byte.
      ⚠️ **AN APPARATUS FAULT OF THE FAIL-BY-AGREEING KIND, CAUGHT ONLY BY AN
      ASYMMETRY.** The first cell readout was 38 characters — inside the 40-byte
      KEYBUF cap, which is why it looked safe — but the screen's two-column
      margin pushed its closing quote onto the next row, so `_echo_idx` found no
      row carrying the command and the reader returned `<none>`, a sentinel that
      also means "no reading". It did that on vg8020 and zb but NOT cf3300,
      whose Disk BASIC lays the prompt out differently; had cf3300 wrapped too,
      all three sides would have reported THREE-WAY AGREEMENT on nothing. The
      value was on screen the whole time. **The binding constraint is COLS minus
      the margin, not the KEYBUF cap.**
      Landed **+10 B main page 1** (311 -> 301 free) and **+17 B sub page 1**;
      one resolver in `ldr_num`, the single site both `le_delrange` and
      `le_lstrange` read a line number from, so `AUTO`/`RENUM` get `.` free the
      day they are dispatched.
      ⚠️ **STILL UNMEASURED, and recorded as choices rather than readings**:
      whether an ASCII LOAD/MERGE writes `.` per line (zerobas' `cload.asm`
      reaches `store_line`, so it inherits writer (a) either way); whether an
      OOM store writes it; and the ASCII-SAVE reading is **cf3300 only** —
      `SAVE"CAS:",A` would give a second reference and needs cassette support
      this probe does not have.
