- [x] 🐛 **`RESUME 99` TO A MISSING LINE HANGS ZEROBAS (NO PROMPT EVER COMES BACK); THE VG-8020 STOPS WITH `Undefined line number in 100` (D-RESUMEMISS,
      found 2026-11-25 by D-KWSPEC's errors region, the ERROR / RESUME unit).**
      🎚️ TIER 3 — common errors: a mistyped RESUME line number in a handler HANGS zerobas -- the screen capture ends at `RUN`, no prompt.
      🤖 **AUTONOMOUS** — [`kerr.py`](../../probes/basic/spec/kerr.py) -> [`KER_run1.out`](../../scratchpad/KER_run1.out)
      KER FX 25, `10 ON ERROR GOTO 100` / `20 X=1/0` / `100 RESUME 99` / `RUN`: the reference raises 8 in the handler's
      line -- untrapped, since the handler is still active -- and prints `Undefined line number in 100`; zerobas never
      returns to the prompt (rule R-RESUME-FORMS).
      ✅ **FIXED 2026-11-25** (basic/interp.asm, ex_resume's `RESUME <line>` arm): `call goto_resolve` -- which raises
      8 while the handler is still active, untrapped -- then `jr res_ctx` to leave it. Size-neutral (6 B, a `nop` pad;
      main page 1, no symbol moved). KER FX 25 now reads the reference's `Undefined line number in 100` (AE_ker_run3.out).
