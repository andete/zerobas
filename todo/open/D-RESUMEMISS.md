- [ ] 🐛 **`RESUME 99` TO A MISSING LINE HANGS ZEROBAS (NO PROMPT EVER COMES BACK); THE VG-8020 STOPS WITH `Undefined line number in 100` (D-RESUMEMISS,
      found 2026-11-25 by D-KWSPEC's errors region, the ERROR / RESUME unit).**
      🎚️ TIER 3 — common errors: a mistyped RESUME line number in a handler HANGS zerobas -- the screen capture ends at `RUN`, no prompt.
      🤖 **AUTONOMOUS** — [`kerr.py`](../../probes/basic/spec/kerr.py) -> [`KER_run1.out`](../../scratchpad/KER_run1.out)
      KER FX 25, `10 ON ERROR GOTO 100` / `20 X=1/0` / `100 RESUME 99` / `RUN`: the reference raises 8 in the handler's
      line -- untrapped, since the handler is still active -- and prints `Undefined line number in 100`; zerobas never
      returns to the prompt (rule R-RESUME-FORMS).
