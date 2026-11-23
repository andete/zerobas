- [ ] 🔎 **D-S16PREEXIST -- THREE DIFFERENCES THE S16 ROWS FOUND, PRESENT ON HEAD'S ROM TOO
      (2026-10-16)**
      🎚️ TIER 6 — provisional, until each is isolated (the first may be higher).
      🤖 AUTONOMOUS — measure, isolate, then tier each.
      Found by the first cuts of the S16 behaviour rows, identical before S16
      ([`wszero_s16_rows_head.out`](scratchpad/wszero_s16_rows_head.out)), and
      narrowed out of those rows:
      (1) **A$ reads `DDDD` on the VG-8020 and `AQCD` on zerobas** after
      `A$="AB"+"CD":B$=LEFT$(A$,3)+MID$(A$,2,2):C$=STRING$(3,"*")+SPACE$(2)+CHR$(65)`,
      `D$=HEX$(255)+OCT$(8)+BIN$(5):MID$(A$,2,1)="Q":I=INSTR(A$,"C"):E=(A$<B$):F$=A$`,
      `V=VAL("1.5"):READ N:X=FRE(""):Y=FRE(0)`, under `CLEAR 300,&HE000`, ON ERROR,
      after a window BLOAD (the s16sh program before its narrowing). NOT
      reproduced by five reductions -- MID$ alone, then FRE(""), with a copy
      before or after, a literal -- which all agree on AQCD
      ([`midfre_probe.py`](scratchpad/midfre_probe.py)): a missed prediction
      (the shared body + GC). ➡️ Bisect the original program's statements.
      (2) **The ERL of a READ error after `RESTORE 40`**: `READ C` refusing `12X`
      in line 30 (ERL 30 on both), then `RESTORE 40:READ D` refusing `1E99` in line
      40 -- VG-8020 ERL 30, zerobas 20 (the READ's line). The CF-3300 not run.
      (3) **`FRE(0)=FRE(2)` in ONE expression is 0 on the VG-8020, -1 on zerobas**
      (after `A$="ABC"+"D"`); split into two statements both answer 0.
