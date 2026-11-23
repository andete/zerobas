- [x] 🧹 **A TRACKED `scratchpad/` SCRIPT CAN HARDCODE THE AUTHOR'S ABSOLUTE
      PATH, AND NOTHING CHECKS IT.** Filed 2026-08-26 by D-CITEPATH, which found
      `cd /Users/joost/projects/zerobas` inside one of the four `.sh` battery
      wrappers it was triaging. That one is gitignored, so it does not matter —
      **but the class is not about `.sh`**: `scratchpad/*.py` IS tracked and
      shipped, and a tracked script with an absolute home directory in it
      resolves in a fresh clone and then does the wrong thing, which is worse
      than dangling. 🎯 The new citation gate proves the PATH exists; nothing
      asks whether the file it points at can RUN anywhere else. Unmeasured: the
      denominator over `scratchpad/**` + `probes/**` + `tools/**` has not been
      taken, and some hits will be legitimate (a C-BIOS checkout default). Cheap
      to sweep, a judgement to remediate.
      📏 **SWEPT AND FIXED 2026-08-26. THE DENOMINATOR IS 511 EXECUTABLE TRACKED
      FILES** (`.py`/`.sh`/`.asm`/`.inc`/Makefile under those three trees).
      ⚠️ **`.log` AND `.out` CAPTURES ARE EXCLUDED ON PURPOSE** — they hold 343
      of the 372 raw hits, and an absolute path inside a captured log is
      *evidence of what ran*, not a portability bug. Sweeping them in is how a
      372-hit number gets quoted for a 25-hit problem.
      🟢 **`/opt/homebrew/bin/openmsx` (44 files) IS NOT A HIT.** It is the last
      term of `os.environ.get("OPENMSX") or shutil.which("openmsx") or …`, and
      guarded after by `if not isfile: OMSX = "openmsx"`. It resolves on any
      host. Read before counting.
      🔴 **THE REAL CLASS WAS 25 ASSIGNMENTS IN 24 FILES** — `ROOT`/`REPO` set
      to the literal `/Users/joost/projects/zerobas`. **11 of the 24 are knife
      runners**, which CUT SOURCE FILES: in a fresh clone they would compute the
      wrong root and cut nothing, or the wrong file.
      ✅ **REMEDIATION WAS NOT A JUDGEMENT AFTER ALL — THE TREE HAD ALREADY
      VOTED 190 TO 25** for `dirname(dirname(abspath(__file__)))`. All 24
      conformed, **0 remain**, and each rewrite was PROVEN value-preserving:
      the new expression is evaluated with that file's `__file__` and must equal
      the old literal exactly — **24/24 did**, so no instrument changed what it
      reads. (My first pass skipped 9 of them by testing `^import pathlib$`
      against files that say `import hashlib, os, pathlib, re, subprocess, sys`.)
      ✅ **CHECKER SHIPPED 2026-08-26 as rule ROOT of `make chokepoint-check`**
      ([`docs/spec-chokepoint-gate.md`](docs/spec-chokepoint-gate.md)).
      Denominator **495 files**.
      🔴 **AND IT IMMEDIATELY FOUND ONE THE FIX HAD MISSED.** The sweep above
      reported *zero remaining*; `scratchpad/runline_knives.py` still hardcoded
      it. The sweep's regex required exactly one space before `=` and the file
      says `ROOT  = pathlib.Path(...)`. **The AST does not care about
      whitespace, and that is the whole argument for it.** Now 0, checked.
      ✅ **DONE** — swept, fixed, and gated.
