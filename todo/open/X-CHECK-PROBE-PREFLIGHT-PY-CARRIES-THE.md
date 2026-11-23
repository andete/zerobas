- [ ] ⚠️ **`check_probe_preflight.py` carries the IDENTICAL `SCAN_DIRS`** — the
      denominator D-INJJUDGE derived for `injector-check` was left hand-listed
      here, and **6** out-of-scope `.py` launch openMSX. Same shape, different
      rule, and **that rule has not been walked**: widening it on the strength of
      the sibling's measurement is exactly [[a-borrowed-window-inherits-its-corpus]].
      Re-open by walking preflight's own rule over its subject's life first.
      Detail: `docs/spec-probe-injjudge.md` §3.6.
      🟢 **WALKED 2026-09-05 (D-PREWIDEN,
      [`scratchpad/preflight_widen.py`](../../scratchpad/preflight_widen.py)), IN
      PREFLIGHT'S OWN TERMS** — `scan_file()` imported and applied verbatim to
      every tracked `.py` outside `SCAN_DIRS`, so the verdicts are the checker's
      and not a heuristic's:

          tracked .py 808 — inside the window 345, outside 463
          outside, by preflight's own rule:
            EXEMPT (argv proves no -machine)     50
            REQUIRED                            127
              of which UNGUARDED                123   in 109 files

      🔴 **SO THE FILED "6" IS OFF BY A FACTOR OF TWENTY.** Widening `SCAN_DIRS`
      would turn **123 sites in 109 files** red on the next `make gates` — a
      109-file edit, not a tidy-up, and the figure is what changes the shape of
      the decision.
      🎯 **AND THE TREE ALREADY HAS A POSITION ON THIS EXACT TRADE.** Knife
      runners are deliberately throwaway (`spec-probe-injjudge.md` §1.3), and the
      `/tmp` literals item reached the same fork with the same arithmetic — 124
      sites in 69 files — and chose **containment plus a gate over a bulk edit it
      could not verify**, on the ground that a mechanical sweep whose blast radius
      cannot be checked breaks invariants its own rule cannot see
      [[a-mechanical-fix-can-break-a-different-invariant]]. The consistent answer
      here is the same one: **do not widen; guard opportunistically when touching
      a runner anyway.**
      🎚️ APPARATUS — preflight
      🔭 SCOUT-THEN-ASK — the walk this entry asked for is DONE and the number is
      123/109, not 6; whether a throwaway knife runner ought to preflight at all
      is a scope call, and it is his.
