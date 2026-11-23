- [x] ⚠️ **`CLEARPOOL=0` IS UNTESTED AND CANNOT BE ADDED TO
      `switch-build-check`.** 2026-08-23, D-MISSOPFIX. `FPERR_MISSOP` is equated
      inside the `IF CLEARPOOL` in `basic/sysvars.inc` (12 with, 11 without)
      because `fperr_to_err` is a **dense** table whose next free index moves
      with the switch — and an off-by-one is SILENT: it reads a neighbouring
      byte and reports some other error. The `ELSE` arm has never been
      assembled. `tools/check_switch_builds.py` cannot cover it: its scope claim
      is *"no switch is read outside `basic/`"* and **CLEARPOOL is read from
      `sub/arrays.asm` and `sub/strheap.asm`**, so adding it to `SWITCHES` trips
      the tool's own `scope_holds()` check. Widening the tool to two-ROM builds
      is the fix; unpriced.
      ✅ **BOTH DONE 2026-08-26: THE ARM IS ASSEMBLED *AND* THE GATE COVERS IT.**
      ```
      CLEARPOOL=1   main+sub assemble   FPERR_MISSOP=12   fperr_to_err[12]=24
      CLEARPOOL=0   main+sub assemble   FPERR_MISSOP=11   fperr_to_err[11]=24
      ```
      The `ELSE` arm builds — **both ROMs** — and in each arm the dense table's
      slot holds **24**, so the equate and the table have not drifted. The
      feared silent off-by-one does not exist today
      ([`scratchpad/clearpool_off.py`](../../scratchpad/clearpool_off.py)).
      🎯 **THE SCOPE CLAIM WAS THE PROBLEM, SO THE SCOPE IS NOW PER-SWITCH.**
      `SWITCHES` is a dict of *switch → trees it is read from*, and `assemble()`
      builds every tree the switch declares. **A global claim of "no switch is
      read from `sub/`" had excluded the one switch that most needed covering** —
      a scope that excludes its hardest case has chosen its own denominator.
      `CLEARPOOL` is in the gate now: **7 of 7, `(basic+sub)`.**
      🔴 **AND ASSEMBLING IS THE EASY HALF.** The failure this item was FILED for
      *builds*: a wrong index reads a neighbouring byte and raises some other
      error. A switch may now declare a **POSTCHECK** read back out of the
      assembled image; `CLEARPOOL`'s asserts `fperr_to_err[FPERR_MISSOP] == 24`,
      and the baseline must satisfy it too or the run refuses.
      🔬 **FALSIFIED BY PLANTING, TWICE, EACH RESTORED BYTE-IDENTICALLY.** A
      break visible only in the OFF arm → `FAIL CLEARPOOL`, 6 of 7. And an
      off-by-one that **assembles perfectly** (`FPERR_MISSOP equ 10`) →
      *"fperr_to_err[FPERR_MISSOP=10] is 13, want 24 — the equate and the dense
      table have DRIFTED APART, and a raise there would report ERR 13"*. Without
      the postcheck that second plant is a clean PASS.
      🔴 **MY OWN FIRST TABLE READ WAS A FALSE RED**: it fell back to a default
      org of `0x4000` when it found no `MAIN_ORG` symbol (there is none — it is
      `BASIC_ORG`, `$2812`) and reported bytes **32** and **67** on a tree that
      is fine. An offset computed from a default is not a reading.
