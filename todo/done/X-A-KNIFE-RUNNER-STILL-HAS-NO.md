- [x] ⚠️ **A KNIFE RUNNER STILL HAS NO SHARED WAY TO SCOPE A CUT TO ONE
      ✅ **CLOSED 2026-09-05 — the helper exists, is SHARED, and the "where should
      it live" question is answered by the gate that already collects it.**
      [`scratchpad/knife_guard.py`](../../scratchpad/knife_guard.py) `cut(text, anchor,
      repl, *, routine=None)`: `_region()` scopes to a routine's span, the
      occurrence count must be exactly 1, and `CutError` is raised otherwise —
      the mechanical remedy this entry specified, verbatim.
      🔬 **FIVE ARMS, AND THE FIRST IS THIS ENTRY'S OWN FAILURE**, re-run today:

          cut refuses a repeated anchor when unscoped   <- K-PS1's exact bug
          cut scoped to a routine hits THAT copy
          cut refuses an unknown routine
          cut refuses an anchor absent from the routine
          cut still takes a unique unscoped anchor

      ➡️ **AND "WHERE IT LIVES" IS SETTLED BY USE, NOT BY ARGUMENT**: knife
      runners stay throwaway, but the helper does not — it sits beside them and
      `make knife-guard-check` collects it (`0 violation(s)` today, with 4 files
      it names as rebuilding-but-not-cutting rather than passing them silently).
      Two knives have already used it: K-SE5 (D-SPRCOVER) and K-LA5 (D-ZEROSEED).
      ROUTINE.** Filed 2026-08-11 by D-PAINTSEED
      ([`docs/spec-basic-lineerr.md`](../../docs/spec-basic-lineerr.md) §9.6). K-PS1's
      first runner did `src.replace("call gfx_point_gate  ; BC/DE/HL preserved",
      …, 1)` — a line that occurs THREE times in `basic/graphics.asm` — and cut
      `gfx_plot_stmt`'s copy, i.e. the probe's own `PSET(7,4)` seed. It was
      caught only because the runner read the report TAG. `docs/dev-workflow.md`
      §Knives has eight rules about how a runner reads a report and none about
      how it makes a cut. The mechanical remedy is one helper — scope to the
      routine's region, assert the occurrence count is 1 — but knife runners are
      deliberately throwaway (`spec-probe-injjudge.md` §1.3), so where it should
      live is the open question, not what it should do.
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (no his-decision signal found).
