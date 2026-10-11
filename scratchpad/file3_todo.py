#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""File D-AUTORUN, D-KEYSHIFT and D-RESETBOOT (Joost's three reports,
2026-10-11) above D-BLDS, and point the 2026-09-26 SHIFT note at D-KEYSHIFT.
Anchored on text; refuses on a missing or non-unique anchor."""
import sys

P = "TODO.md"
s = open(P, encoding="utf-8").read()

NEW = """- [ ] 📼 **D-AUTORUN — openMSX's TAPE AUTORUN NEVER FIRES: zerobas CALLS NEITHER H.READ
      ($FF07) NOR H.MAIN ($FF0C) (Joost, 2026-10-11; measured the same day)**
      🎚️ TIER 1 — happy path: inserting a tape with openMSX's autorun on is how
      most people load one.
      🤖 **AUTONOMOUS** — the VG-8020 settles the order.
      openMSX's autorun (its own Tcl, in the binary's strings) sets a breakpoint
      at H.READ and, when it fires, types `RUN"CAS:"` (ASCII), `BLOAD"CAS:",R`
      (binary) or `CLOAD` (tokenised); for CLOAD it then waits on the NEXT
      H.MAIN to type `RUN` ("H_READ isn't called after CLOAD, but H_MAIN is").
      zerobas's source names neither hook, so the breakpoint never fires.
      📏 [`autorun_hook_probe.py`](scratchpad/autorun_hook_probe.py) →
      [`.out`](scratchpad/autorun_hook_probe.out): RAM counters behind both
      hooks read **2 2 on the VG-8020, 0 0 on zerobas**. 🔮 Predicted: HIT.
      📏 [`autorun_order_probe.py`](scratchpad/autorun_order_probe.py) →
      [`.out`](scratchpad/autorun_order_probe.out), a tag log with markers:
      VG-8020 `RM1RMRM2RMM` -- every return to the prompt (program END, a typed
      line, an error) calls **H.READ, then H.MAIN**; after **CLOAD, H.MAIN
      only**. ⚠️ Its zerobas row is void: the log sits at `$E030`, inside
      zerobas's own workspace above `$DB00` (D-HIMEMLIE's ruled divergence), so
      the run hung; a zerobas-side order probe must log below `$DB00`.
      🔧 The fix: `call H_READ` then `call H_MAIN` where the ready prompt is
      printed, `call H_MAIN` alone on CLOAD's return; ~6-9 B of main (page 1
      10 B, low 19 B on 2026-10-11). Check first whether the CF-3300's disk ROM
      claims either cell (scratchpad/hookscan_probe.py) -- a claimed hook is
      the disk BASIC's business at the prompt and the disk build must match it.
      ✅ Proof is end-to-end: openMSX with `autoruncassettes on` and each of the
      three tape types, on the VG-8020 and both builds -- the program runs.

- [ ] 🖥️ **D-KEYSHIFT — AT THE PROMPT, HOLDING SHIFT SHOWS THE F6..F10 LABELS; zerobas
      KEEPS F1..F5 (Joost, 2026-10-11; measured the same day)**
      🎚️ TIER 1 — happy path: the key line is on screen in every session.
      🤖 **AUTONOMOUS** — the VG-8020 settles it.
      📏 [`keyidle_probe.py`](scratchpad/keyidle_probe.py) →
      [`.out`](scratchpad/keyidle_probe.out) (openMSX driven directly, read
      WHILE the key is held -- omsx_repl releases it before its capture, which
      is why 2026-09-26 could not see this): VG-8020 at rest `color auto goto
      list run`, FNKSWI 1; **SHIFT held `color cload" cont list. run`, FNKSWI
      0**; released, back. CTRL (control): nothing. zerobas: nothing in any
      row. 🔮 Predicted: HIT. With 2026-09-26's reading (a busy program with
      SHIFT held does NOT switch, `scratchpad/keyshift_run.out`) the switch
      lives in the key-WAIT path, not the timer interrupt.
      ➡️ Measure before building: INPUT / LINE INPUT / INPUT$ / INKEY$ in a
      running program with SHIFT held (which wait switches), KEY OFF (nothing
      drawn -- does FNKSWI still flip?), SCREEN 1. Then: in the wait loop,
      compare SHIFT (row 6 bit 0) with FNKSWI and redraw the labels on a
      change. ⚠️ A page-1 tenant must not wait: the poll belongs in main's
      wait loop or on the C-BIOS side.

- [ ] 🔁 **D-RESETBOOT — AFTER A RESET THE MACHINE DOES NOT BOOT BACK INTO BASIC
      (Joost, 2026-10-11; NOT YET MEASURED)**
      🎚️ TIER 1 — happy path: a reset is ordinary use.
      🤖 **AUTONOMOUS** — measure first.
      Joost: *"when resetting the msx machine it doesn't boot back to basic"*.
      ➡️ Measure: openMSX `reset` on the VG-8020 and both builds -- at the
      prompt, with a program in memory, during a run -- and read what is on
      screen and where PC settles (registers are readable). Hypotheses to TEST,
      not believe: a RAM cell that survives the reset steers the boot (a
      warm-boot flag, the H.TIMI seam or another hook left installed, the
      sub-ROM scan's state), or the repack boot path assumes cold RAM.

"""

A1 = "- [ ] 🔍 **D-BLDS — ON TAPE"
if s.count(A1) != 1:
    sys.exit(f"anchor 1 count {s.count(A1)}")
s = s.replace(A1, NEW + A1)

A2 = "      The same probe found D-KEYCLS (below).\n"
if s.count(A2) != 1:
    sys.exit(f"anchor 2 count {s.count(A2)}")
s = s.replace(A2, A2 + "      📏 **THE IDLE PROMPT, MEASURED 2026-10-11: IT *DOES* SWITCH** -- "
              "SHIFT held at the\n      prompt shows F6..F10 and FNKSWI 0 on the "
              "VG-8020; filed as D-KEYSHIFT.\n")
open(P, "w", encoding="utf-8").write(s)
print("filed 3 items; amended the 2026-09-26 note")
