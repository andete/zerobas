"""D-DISKERRS, the open-file shapes: KILL of an OPEN file, and OPEN of a busy channel.

T6 batch 8 (scratchpad/t6enum_b8_zb.out) found `KILL` of a file open FOR OUTPUT
raising 64 File still open on the CF-3300 and SUCCEEDING on zerobas, and a second
OPEN on channel #1 raising 54 File already open there and succeeding here. Both
can lose data. Before a rule is written, the shapes around them are asked, one
boot per case, the CF-3300 against zerobas's DISK build, a private disk image
each, trapped by ON ERROR:

  k_out     K1 open FOR OUTPUT on #1; KILL K1                      -> 64 (batch 8)
  k_in      K1 written, open FOR INPUT on #1; KILL K1              is INPUT open too?
  k_nonact  K1 on #1, K2 on #2 (so #1 is NOT the live channel); KILL K1
  k_wild    K1 open on #1, K2 closed; KILL "K*.TXT"                does a wildcard see it?
  k_closed  K1 opened and CLOSEd; KILL K1                          control: 0
  c_out     A open FOR OUTPUT, "HELLO" printed; KILL a DIFFERENT file B; CLOSE;
            read A back                                            must read HELLO
  c_in      A ("HELLO") open FOR INPUT; KILL B; INPUT #1           must read HELLO
  o_busy    OPEN X2 AS #1; OPEN X3 AS #1                          -> 54 (batch 8)
  o_same    OPEN X2 FOR OUTPUT AS #1; the same file AS #2         second open of one file
  o_samein  X2 written; OPEN it FOR INPUT AS #1 and AS #2         the same, for INPUT

The handler prints A$ so the clobber cases show what was read.

    python3 -u scratchpad/killopen_probe.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

TAIL = ['90 PRINT"[";A$;ERR;ERL;"]":END', "RUN"]
W = lambda n, s: f'OPEN "{n}.TXT" FOR OUTPUT AS #1:PRINT #1,"{s}":CLOSE'


def prog(*body):
    return ["NEW", "10 ON ERROR GOTO 90"] + list(body) + TAIL


CASES_R1 = {
    "k_out": prog('20 OPEN "K1.TXT" FOR OUTPUT AS #1', '30 KILL "K1.TXT":PRINT"[OK]":END'),
    "k_in": prog("20 " + W("K1", "X") + ':OPEN "K1.TXT" FOR INPUT AS #1',
                 '30 KILL "K1.TXT":PRINT"[OK]":END'),
    "k_nonact": prog('20 OPEN "K1.TXT" FOR OUTPUT AS #1:OPEN "K2.TXT" FOR OUTPUT AS #2',
                     '30 KILL "K1.TXT":PRINT"[OK]":END'),
    "k_wild": prog("20 " + W("K2", "X") + ':OPEN "K1.TXT" FOR OUTPUT AS #1',
                   '30 KILL "K*.TXT":PRINT"[OK]":END'),
    "k_closed": prog('20 OPEN "K1.TXT" FOR OUTPUT AS #1:CLOSE', '30 KILL "K1.TXT":PRINT"[OK]":END'),
    "c_out": prog("20 " + W("B", "X") + ':OPEN "A.TXT" FOR OUTPUT AS #1:PRINT #1,"HELLO"',
                  '30 KILL "B.TXT":CLOSE:OPEN "A.TXT" FOR INPUT AS #1:INPUT #1,A$',
                  '40 PRINT"[";A$;"OK]":END'),
    "c_in": prog("20 " + W("B", "X") + ":" + W("A", "HELLO") + ':OPEN "A.TXT" FOR INPUT AS #1',
                 '30 KILL "B.TXT":INPUT #1,A$', '40 PRINT"[";A$;"OK]":END'),
    "o_busy": prog('20 OPEN "X2.TXT" FOR OUTPUT AS #1', '30 OPEN "X3.TXT" FOR OUTPUT AS #1:PRINT"[OK]":END'),
    "o_same": prog('20 OPEN "X2.TXT" FOR OUTPUT AS #1', '30 OPEN "X2.TXT" FOR OUTPUT AS #2:PRINT"[OK]":END'),
    "o_samein": prog("20 " + W("X2", "X") + ':OPEN "X2.TXT" FOR INPUT AS #1',
                     '30 OPEN "X2.TXT" FOR INPUT AS #2:PRINT"[OK]":END'),
}
CASES = dict(CASES_R1)
CASES.update({
    # --- round 2: k_nonact / o_same / o_samein read 52 at the #2 on BOTH
    # machines in round 1 -- MAXFILES defaults to 1, so channel 2 did not exist
    # and those rows never reached their subject. The same three, with 2 channels.
    "k_nonact2": ["NEW", "5 MAXFILES=2"] + CASES_R1["k_nonact"][1:],
    "o_same2": ["NEW", "5 MAXFILES=2"] + CASES_R1["o_same"][1:],
    "o_samein2": ["NEW", "5 MAXFILES=2"] + CASES_R1["o_samein"][1:],
    # --- round 3 (after D-KILLOPEN): the two disk modes rounds 1-2 did not ask.
    "k_rand": prog('20 OPEN "K1.DAT" AS #1 LEN=16', '30 KILL "K1.DAT":PRINT"[OK]":END'),
    "k_app": prog("20 " + W("K1", "X") + ':OPEN "K1.TXT" FOR APPEND AS #1',
                  '30 KILL "K1.TXT":PRINT"[OK]":END'),
    # --- round 4: the error CODE a disk.rom hook reports is wiped when a channel
    # is open -- chan_gate's restore re-stages the live channel's sector, and
    # every successful read writes DISKOP_ERR = 0. NAME's 65, with a file open:
    "n_open": prog("20 " + W("N1", "X") + ":" + W("N2", "X") + ':OPEN "Z.TXT" FOR OUTPUT AS #1',
                   '30 NAME "N1.TXT" AS "N2.TXT":PRINT"[OK]":END'),
    # --- round 5 (after D-ERRKEEP): the channel is still USABLE after the refusal.
    # hk_claim_status leaves no channel live on status 2, deferring the reload to
    # the channel's next use; this writes, is refused, writes again, reads back.
    "k_after": ["NEW", "10 ON ERROR GOTO 90",
                '20 OPEN "K1.TXT" FOR OUTPUT AS #1:PRINT #1,"AB"', '30 KILL "K1.TXT"',
                '40 PRINT #1,"CD":CLOSE:OPEN "K1.TXT" FOR INPUT AS #1:INPUT #1,A$:INPUT #1,B$',
                '50 PRINT"[";A$;B$;E;"OK]":END', "90 E=ERR:RESUME NEXT", "RUN"],
})


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
