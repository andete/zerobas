"""D-ERRKEEP2: does a disk verb's error CODE survive when a file is OPEN?

D-ERRKEEP (2026-09-28) found KILL's 64 and NAME's 65 arriving in main as ERR 0
whenever a channel was open: chan_gate's restore re-stages the live channel after
the hook returns, and every successful sector read writes DISKOP_ERR = 0, so the
code the hook left there is gone before disk_error reads it -- and load_error
prints and carries on. KILL and NAME were fixed; this asks the OTHER verbs.

The error is forced with a WRITE-PROTECTED disk: a private copy of the fixture
image made read-only on the host, which the emulator mounts write-protected.
HI.TXT is on the fixture, so it can be opened FOR INPUT (a read works) before a
verb that must WRITE fails. One boot per case, the CF-3300 against zerobas's
DISK build, trapped by ON ERROR:

  wp_ctl    SAVE "X.BAS", nothing open        control: write protect works (68)
  wp_save   HI.TXT open FOR INPUT; SAVE "X.BAS"
  wp_asave  HI.TXT open FOR INPUT; SAVE "X.BAS",A
  wp_bsave  HI.TXT open FOR INPUT; BSAVE "X.BIN",&HC000,&HC010
  wp_copy   HI.TXT open FOR INPUT; COPY "HI.TXT" TO "HJ.TXT"
  wp_name   HI.TXT open FOR INPUT; NAME "HI.TXT" AS "HJ.TXT"   (fixed by D-ERRKEEP?)
  wp_out    MAXFILES=2; HI.TXT open FOR INPUT; OPEN "Y.TXT" FOR OUTPUT AS #2

    python3 -u scratchpad/errkeep2_probe.py [case ...]
"""
import os, re, stat, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

TAIL = ['90 PRINT"[";ERR;ERL;"]":END', "RUN"]
OPN = '20 OPEN "HI.TXT" FOR INPUT AS #1'


def prog(*body, pre=()):
    return ["NEW"] + list(pre) + ["10 ON ERROR GOTO 90"] + list(body) + TAIL


CASES = {
    "wp_ctl": prog('30 SAVE "X.BAS":PRINT"[OK]":END'),
    "wp_save": prog(OPN, '30 SAVE "X.BAS":PRINT"[OK]":END'),
    "wp_asave": prog(OPN, '30 SAVE "X.BAS",A:PRINT"[OK]":END'),
    "wp_bsave": prog(OPN, '30 BSAVE "X.BIN",&HC000,&HC010:PRINT"[OK]":END'),
    "wp_copy": prog(OPN, '30 COPY "HI.TXT" TO "HJ.TXT":PRINT"[OK]":END'),
    "wp_name": prog(OPN, '30 NAME "HI.TXT" AS "HJ.TXT":PRINT"[OK]":END'),
    "wp_out": prog(OPN, '30 OPEN "Y.TXT" FOR OUTPUT AS #2:PRINT"[OK]":END', pre=("5 MAXFILES=2",)),
}
# --- round 2: every wp_* row put a `:` statement after the verb, and zerobas's
# trace (scratchpad/wpsave_trace.py) showed SAVE going to load_error BEFORE
# reaching the drive -- do_save reads any byte after the name as "trailing
# junk". So on a WRITABLE disk: is `SAVE "X.BAS":<more>` itself broken?
RW = {
    "sv_colon": prog('30 SAVE "X.BAS":PRINT"[OK]":END'),
    "sv_line": prog('30 SAVE "X.BAS"', '40 PRINT"[OK]":END'),
    "bs_colon": prog('30 BSAVE "X.BIN",&HC000,&HC010:PRINT"[OK]":END'),
    "sa_colon": prog('30 SAVE "X.BAS",A:PRINT"[OK]":END'),
}


def ro_image():
    p = t._disk_image()
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return p


def main():
    only = sys.argv[1:] or list(CASES)
    table = dict(CASES, **RW)
    got = {}
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k in only:
            raw = omsx_repl.run_cases(m, [("direct", table[k])], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=t._disk_image() if k in RW else ro_image(),
                                      step=8.0, cap_gap=20.0)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':9} {'CF-3300':>16} {'zerobas':>16}")
    for k in only:
        a, b = got[("National_CF-3300", k)], got[("C-BIOS_MSX1_EU_REPACK_DISK", k)]
        print(f"{'  ' if a == b else '✗ '}{k:9} {a:>16} {b:>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
