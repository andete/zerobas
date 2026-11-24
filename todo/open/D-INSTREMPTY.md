- [ ] 🐛 **`INSTR` WITH AN EMPTY STRING TO FIND, AND A START PAST THE END: 0 ON THE VG-8020, `LEN(a$)+1` (OR THE START) HERE
      (D-INSTREMPTY, found 2026-11-24 by D-KWSPEC's strings probe).**
      🎚️ TIER 1 — `INSTR(P,A$,"")` is ordinary typed BASIC and answers a different number, no error anywhere.
      🤖 **AUTONOMOUS** — measured by [`kstr.py`](../../probes/basic/spec/kstr.py) ->
      [`KST_run1.out`](../../scratchpad/KST_run1.out), rule R-INSTR-EMPTY on [INSTR.md](../../docs/keywords/INSTR.md):
      the VG-8020 returns the start when it is within a$ (start <= LEN(a$)) and 0 otherwise; zerobas returns
      min(start, LEN(a$)+1). 34 of the 75 empty-needle cases differ: `INSTR(7,"ABCABC","")` is 0 there and 7 here,
      `INSTR(200,"ABCABC","")` 0 there and 7 here, and `INSTR("","")` -- no start at all -- 0 there and 1 here
      (every start on an empty a$ is 1 here). The rest of INSTR agrees: 750 non-empty finds, 330 start errors.
      ➡️ When picked up: the empty-needle branch of zerobas's INSTR (str-engine.asm) needs the "start > LEN(a$) -> 0"
      test that the non-empty search already gets; the rule and its control (`kstr_controls.py`, which runs zerobas's
      rule over the reference's cases: FALSE on 34) are the acceptance.
