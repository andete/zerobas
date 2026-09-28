"""D-DISKERRS, the Input-past-end shape: WHEN does a sequential read raise 55?

T6 batch 8 (scratchpad/t6enum_b8_zb.out) found `INPUT #1,A$` and
`A$=INPUT$(1,#1)` on an EMPTY file raising 55 Input past end on the CF-3300 and
returning nothing, no error, on zerobas. Before a rule is written, the shapes
around it are asked, one boot per case, the CF-3300 against zerobas's DISK
build, a private disk image each, trapped by ON ERROR. The handler prints A$ too,
so a read that fails part-way shows whether the target was assigned:

  empty     empty file; INPUT #1,A$                          -> 55 (batch 8)
  second    "HI"+CRLF; INPUT twice                            the 2nd read at EOF
  noterm    "HI" with NO CRLF; INPUT once, then EOF(1)        a field ended BY the EOF
  line2     "HI"+CRLF; LINE INPUT twice                       LINE INPUT at EOF
  dol_part  "HI"+CRLF (4 B); INPUT$(5,#1)                     EOF inside an INPUT$
  dol_all   "HI"+CRLF; INPUT$(4,#1) then INPUT$(1,#1)         INPUT$ exactly at EOF
  list2     "HI"+CRLF; INPUT #1,A$,B$                         EOF inside one statement
  comma     "HI,"+CRLF; INPUT #1,A$,B$                        an empty last field

    python3 -u scratchpad/ipe_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

W_HI = '20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"HI":CLOSE:OPEN "F.TXT" FOR INPUT AS #1'
TAIL = ['90 PRINT"[";A$;"|";B$;ERR;ERL;"]":END', "RUN"]


def prog(*body):
    return ["NEW", "10 ON ERROR GOTO 90"] + list(body) + TAIL


CASES = {
    "empty": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                  '30 INPUT #1,A$:PRINT"[";A$;"|OK]":END'),
    "second": prog(W_HI, '30 INPUT #1,A$', '40 INPUT #1,B$:PRINT"[";A$;"|";B$;"OK]":END'),
    "noterm": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"HI";:CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                   '30 INPUT #1,A$:B$=STR$(EOF(1)):PRINT"[";A$;"|";B$;"OK]":END'),
    "line2": prog(W_HI, '30 LINE INPUT #1,A$', '40 LINE INPUT #1,B$:PRINT"[";A$;"|";B$;"OK]":END'),
    "dol_part": prog(W_HI, '30 A$="X":A$=INPUT$(5,#1):PRINT"[";LEN(A$);"|OK]":END'),
    "dol_all": prog(W_HI, '30 A$=INPUT$(4,#1)', '40 B$="Y":B$=INPUT$(1,#1):PRINT"[";LEN(A$);"|";B$;"OK]":END'),
    "list2": prog(W_HI, '30 B$="Y":INPUT #1,A$,B$:PRINT"[";A$;"|";B$;"OK]":END'),
    # --- round 2: what is Ctrl-Z to a sequential read? -----------------------
    # zerobas's CLOSE writes a $1A after the data and its reads count it as data
    # (dol_part read 5 bytes of a 4-byte file). These ask the reference.
    "z_len": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"HI";:CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                  '30 INPUT #1,A$:B$=STR$(LEN(A$))+STR$(LOF(1)):PRINT"[";A$;"|";B$;"OK]":END'),
    "z_eofcr": prog(W_HI, '30 INPUT #1,A$:B$=STR$(EOF(1))+STR$(LOF(1)):PRINT"[";A$;"|";B$;"OK]":END'),
    "z_mid": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"A"+CHR$(26)+"B";:CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                  '30 A$=INPUT$(1,#1):B$=STR$(EOF(1))+STR$(LOF(1))',
                  '40 C$=INPUT$(1,#1):B$=B$+STR$(ASC(C$)):PRINT"[";A$;"|";B$;"OK]":END'),
    "z_midin": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"A"+CHR$(26)+"B";:CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                    '30 INPUT #1,A$:B$=STR$(LEN(A$))+STR$(EOF(1)):PRINT"[";A$;"|";B$;"OK]":END'),
    # --- round 3: the LF after a CR, and the textbook read loop --------------
    # z_eofcr read EOF(1) = -1 on the reference right after INPUT read "HI" --
    # with the LF (and the Ctrl-Z) still unread on zerobas. Does INPUT swallow
    # the LF after its CR, or does EOF look past an LF?
    "lf_swal": prog(W_HI, '30 INPUT #1,A$:C$="Z":C$=INPUT$(1,#1):B$=STR$(ASC(C$)):PRINT"[";A$;"|";B$;"OK]":END'),
    "lf_line": prog(W_HI, '30 LINE INPUT #1,A$:C$="Z":C$=INPUT$(1,#1):B$=STR$(ASC(C$)):PRINT"[";A$;"|";B$;"OK]":END'),
    "lf_eof": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"A"+CHR$(10);:CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                   '30 A$=INPUT$(1,#1):B$=STR$(EOF(1)):PRINT"[";A$;"|";B$;"OK]":END'),
    "loop": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"L1":PRINT #1,"L2":CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                 '30 IF EOF(1) THEN 50', '40 LINE INPUT #1,C$:N=N+1:A$=A$+C$:GOTO 30',
                 '50 B$=STR$(N):PRINT"[";A$;"|";B$;"OK]":END'),
    "comma": prog('20 OPEN "F.TXT" FOR OUTPUT AS #1:PRINT #1,"HI,":CLOSE:OPEN "F.TXT" FOR INPUT AS #1',
                  '30 B$="Y":INPUT #1,A$,B$:PRINT"[";A$;"|";B$;"OK]":END'),
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
    print(f"{'case':9} {'CF-3300':>20} {'zerobas':>20}")
    for k in only:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:9} {a:>20} {b:>20}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
