"""Is a channel SWITCH inside a FOR/GOSUB safe? (found reading sh_chan_addr,
2026-09-29, while pricing D-FCBSHAPE S1)

sh_chan_addr (sub/strheap.asm, op 18) derives a channel block's address from
strheap_varceil(), and strheap_varceil returns min(ceiling, CSP) -- the control
pool's live FRONTIER. With a FOR or GOSUB frame standing, CSP is below the
ceiling, so the block address would move with the frames -- and a save
(fch_save_active, on every channel switch) would write 306 B over the newest
frame. Hypothesis, not a finding: ask the machines.

Cases alternate two OUTPUT channels inside a loop, close, and read both files
back; one boot per case, a private image each, CF-3300 vs zerobas:
  forloop   FOR I=1 TO 4: PRINT#1,I: PRINT#2,I*10: NEXT
  gosub     the same writes from inside a GOSUB, called 3 times
  nested    two FOR levels around the switch
  control   the same writes with NO frame standing (straight-line)

    python3 -u scratchpad/chanloop_probe.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

OPEN2 = '20 OPEN "A.TXT" FOR OUTPUT AS #1:OPEN "B.TXT" FOR OUTPUT AS #2'
READ = ['70 CLOSE:OPEN "A.TXT" FOR INPUT AS #1:OPEN "B.TXT" FOR INPUT AS #2',
        '75 A$="":B$=""',
        '80 IF EOF(1) THEN 85 ELSE INPUT #1,X:A$=A$+STR$(X):GOTO 80',
        '85 IF EOF(2) THEN 90 ELSE INPUT #2,X:B$=B$+STR$(X):GOTO 85',
        '90 PRINT CHR$(91);A$;"|";B$;"|";E;CHR$(93):END',
        '95 E=ERR:RESUME 90', "RUN"]


def prog(*body):
    return ["NEW", "5 MAXFILES=2", "10 ON ERROR GOTO 95", OPEN2] + list(body) + READ


CASES = {
    "forloop": prog("30 FOR I=1 TO 4:PRINT #1,I:PRINT #2,I*10:NEXT", "40 GOTO 70"),
    "gosub": prog("30 FOR J=1 TO 3:GOSUB 50:NEXT:GOTO 70", "50 PRINT #1,J:PRINT #2,J*10:RETURN"),
    "nested": prog("30 FOR I=1 TO 2:FOR K=1 TO 2:PRINT #1,I*K:PRINT #2,I+K:NEXT K,I", "40 GOTO 70"),
    "control": prog("30 PRINT #1,1:PRINT #2,10:PRINT #1,2:PRINT #2,20", "40 GOTO 70"),
    # --- round 2: `control` itself failed on zerobas ([|| 13]) and on the pre-S0
    # build too, so the frame hypothesis is not what this measures yet. Split it:
    "one": ["NEW", "5 MAXFILES=2", "10 ON ERROR GOTO 95",
            '20 OPEN "A.TXT" FOR OUTPUT AS #1:PRINT #1,1:PRINT #1,2:CLOSE',
            '30 OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,X,Y:CLOSE',
            '90 PRINT CHR$(91);X;Y;E;CHR$(93):END', '95 E=ERR:RESUME 90', "RUN"],
    # round 3: `one` failed too -- is it MAXFILES=2, or numeric INPUT #?
    "one1": ["NEW", "10 ON ERROR GOTO 95",
             '20 OPEN "A.TXT" FOR OUTPUT AS #1:PRINT #1,1:PRINT #1,2:CLOSE',
             '30 OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,X,Y:CLOSE',
             '90 PRINT CHR$(91);X;Y;E;CHR$(93):END', '95 E=ERR:RESUME 90', "RUN"],
    "one1s": ["NEW", "10 ON ERROR GOTO 95",
              '20 OPEN "A.TXT" FOR OUTPUT AS #1:PRINT #1,1:PRINT #1,2:CLOSE',
              '30 OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,X$,Y$:CLOSE',
              '90 PRINT CHR$(91);X$;"/";Y$;E;CHR$(93):END', '95 E=ERR:RESUME 90', "RUN"],
    "one2s": ["NEW", "5 MAXFILES=2", "10 ON ERROR GOTO 95",
              '20 OPEN "A.TXT" FOR OUTPUT AS #1:PRINT #1,1:PRINT #1,2:CLOSE',
              '30 OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,X$,Y$:CLOSE',
              '90 PRINT CHR$(91);X$;"/";Y$;E;CHR$(93):END', '95 E=ERR:RESUME 90', "RUN"],
    "seq": ["NEW", "5 MAXFILES=2", "10 ON ERROR GOTO 95", OPEN2,
            '30 PRINT #1,1:PRINT #1,2:PRINT #2,10:PRINT #2,20:CLOSE',
            '40 OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,X,Y:CLOSE',
            '50 OPEN "B.TXT" FOR INPUT AS #1:INPUT #1,P,Q:CLOSE',
            '90 PRINT CHR$(91);X;Y;P;Q;E;CHR$(93):END', '95 E=ERR:RESUME 90', "RUN"],
    "alt": ["NEW", "5 MAXFILES=2", "10 ON ERROR GOTO 95", OPEN2,
            '30 PRINT #1,1:PRINT #2,10:PRINT #1,2:PRINT #2,20:CLOSE',
            '40 OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,X,Y:CLOSE',
            '50 OPEN "B.TXT" FOR INPUT AS #1:INPUT #1,P,Q:CLOSE',
            '90 PRINT CHR$(91);X;Y;P;Q;E;CHR$(93):END', '95 E=ERR:RESUME 90', "RUN"],
}


def main():
    only = sys.argv[1:] or list(CASES)
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k in only:
            raw = omsx_repl.run_cases(m, [("direct", CASES[k])], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=t._disk_image(), step=8.0, cap_gap=20.0)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':8} {'CF-3300':>32} {'zerobas':>32}")
    for k in only:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:8} {a:>32} {b:>32}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
