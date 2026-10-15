#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.D's second measurement: what H.DGET ($FE80) RECEIVES on the reference.

scratchpad/getputhook_run.out showed GET and PUT entering $FE80 (H.DGET,
claimed by the CF-3300's disk ROM) once per record, plus $FE4E (H.GETP) and the
bare $FE53. This logs, at every entry to those RAM hook cells: the registers, the
top 8 stack words, PTRFIL ($F864), VALTYP ($F663), DAC ($F7F6, 8 B), the 9-byte
BASIC FCB header at PTRFIL (D-FCBSHAPE: mode +0, work-area pointer +1..+2) and
37 bytes of the disk FCB that header points at. EVERY read is guarded to
address >= $8000 (RAM): a zero or ROM-range pointer prints `--`, never a byte.
Never the hook's target, nothing stepped.

Cases (16-byte records unless LEN says otherwise, a 640-byte RAND.DAT):
  get1/get3   the record carrier (register, DAC, or disk FCB +33 pre-set)
  put1        the GET/PUT discriminator
  get0        does the hook fire before ERR 5?
  get300      past EOF: does ERR 55 come after the hook?   getm1  `,-1`
  getn        bare GET after `,2`: is D-RECAUTO resolved before the hook?
  ch2         #2 with #1 open: the channel/FCB carrier
  len100      LEN=100: is RS the length, does +33 count records or bytes?
  unopen      GET on an unopened #2: does the hook fire before ERR 52/59?
PREDICTED, before the run: the hook fires only after main's checks (no entry
for get0 / unopen); A or the stack word distinguishes GET from PUT; the record
number is already in the disk FCB's random-record field (+33) or DE, 0-based;
PTRFIL points at the channel's BASIC FCB; getn passes record 3.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl                                              # noqa: E402
import loadrun_probe as LR                                    # noqa: E402

REF = "National_CF-3300"
RESET = ("", "SCREEN 0", "CLOSE", "NEW", "CLS")
BOOT, STEP, CAP_GAP = 14.0, 25.0, 8.0
RAND = bytes((i % 26) + 65 for i in range(640))
PRE = 'OPEN"RAND.DAT"AS#1 LEN=16:FIELD#1,16 AS A$:'
CASES = {
    "get1": PRE + "GET#1,1:CLOSE",
    "get3": PRE + "GET#1,3:CLOSE",
    "put1": PRE + 'LSET A$="Q":PUT#1,1:CLOSE',
    "get0": PRE + "GET#1,0:CLOSE",
    "get300": PRE + "GET#1,300:CLOSE",
    "getm1": PRE + "GET#1,-1:CLOSE",
    "getn": PRE + "GET#1,2:GET#1:CLOSE",
    "ch2": PRE + 'OPEN"RAND.DAT"AS#2 LEN=16:GET#2,2:CLOSE',
    "len100": 'OPEN"RAND.DAT"AS#1 LEN=100:FIELD#1,100 AS A$:GET#1,2:CLOSE',
    "unopen": "GET#2,1",
    # MAXFILES defaults to 1, so ch2 / unopen above stop at "Bad file number"
    # before any hook (measured 2026-10-15) -- these two ask the real questions:
    "ch2m": "MAXFILES=2:" + PRE + 'OPEN"B.DAT"AS#2 LEN=16:GET#2,2:CLOSE',   # B.DAT: a 2nd open of RAND.DAT is "File already open"
    "unop1": "GET#1,1",
}
CELLS = (0xFE80, 0xFE4E, 0xFE53)


def prologue(path):
    # rd: a RAM-guarded byte read -- anything below $8000 prints `--`.
    return (
        "set ::dn 0\n"
        "proc __rd {a} { if {$a < 0x8000 || $a > 0xFFFF} { return -- }; "
        "return [format %02X [debug read memory $a]] }\n"
        "proc __rw {a} { if {$a < 0x8000 || $a > 0xFFFE} { return ---- }; "
        "return [format %04X [expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]}]] }\n"
        "proc __rs {a n} { set o {}; for {set i 0} {$i < $n} {incr i} "
        "{ lappend o [__rd [expr {$a+$i}]] }; return [join $o {}] }\n"
        "proc __dg {cell} {\n"
        "  if {$::dn > 30} return\n"
        "  incr ::dn\n"
        "  set sp [reg SP]; set st {}\n"
        "  for {set i 0} {$i < 16} {incr i 2} { lappend st [__rw [expr {$sp+$i}]] }\n"
        "  set pf [__rw 0xF864]\n"
        "  set pfa [expr {$pf eq {----} ? 0 : \"0x$pf\"}]\n"
        "  set hdr [__rs $pfa 9]\n"
        "  set dw [expr {$pfa ? [__rw [expr {$pfa+1}]] : {----}}]\n"
        "  set dwa [expr {$dw eq {----} ? 0 : \"0x$dw\"}]\n"
        "  set dfcb [__rs $dwa 37]\n"
        f"  set h [open {{{path}}} a]\n"
        "  puts $h \"cell=[format %04X $cell] AF=[format %04X [reg AF]] BC=[format %04X [reg BC]] "
        "DE=[format %04X [reg DE]] HL=[format %04X [reg HL]] IX=[format %04X [reg IX]] "
        "IY=[format %04X [reg IY]] SP=[format %04X $sp] stack=$st\"\n"
        "  puts $h \"    PTRFIL=$pf VALTYP=[__rd 0xF663] DAC=[__rs 0xF7F6 8] hdr=$hdr\"\n"
        "  puts $h \"    dfcb@$dw=$dfcb\"\n"
        "  close $h\n"
        "}\n"
        + "".join(f"debug set_bp {c} {{}} {{__dg {c}}}\n" for c in CELLS)
    )


def main():
    only = sys.argv[1:] or list(CASES)
    tmpd = tempfile.mkdtemp(prefix="dget-")
    for tag in only:
        dsk = os.path.join(tmpd, f"{tag}.dsk")
        LR.write_files(dsk, {"RAND    DAT": RAND, "B       DAT": RAND})
        fd, path = tempfile.mkstemp(prefix=f"dget-{tag}-", suffix=".txt")
        os.close(fd)
        scr = omsx_repl.run_cases(REF, [("direct", [CASES[tag]])], batch=False, reset=RESET,
                                  boot=BOOT, step=STEP, cap_gap=CAP_GAP, diska=dsk,
                                  capture="screen", prologue=(prologue(path),))[0]
        err = ""
        if scr:
            r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
            err = " | ".join(x for x in r if x and x != "Ok" and "GET" not in x)
        print(f"== {tag}: {CASES[tag]}   screen: [{err}]", flush=True)
        for ln in open(path):
            print("  " + ln.rstrip(), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
