"""D-FCBSHAPE step 1: which bytes of the reference's FCB header does a program see?

D-FCBSHAPE (TIER 4, Joost's ruling: adopt the MSX FCB layout) starts by
measuring the 9-byte header that VARPTR(#n) points at on the reference --
reading work-area RAM, which the clean-room rule allows. zerobas has no
`VARPTR(#n)` yet (Syntax error), so this reads the VG-8020 only.

Each row opens `CRT:` (a sequential OUTPUT channel every MSX has, disk or not)
and prints `VARPTR(#n)` and the header bytes +0..+8 plus the first 4 record
bytes +9..+12, in hex, at one of:
  open        right after OPEN "CRT:" FOR OUTPUT AS #1
  printed     after PRINT #1,"AB";  (the record should hold A B, a counter move)
  chan2       #2 opened on CRT: too: its header, for the per-channel stride
  d_open / d_print / d_print3   the same on the CF-3300, a DISK file (buffered:
                                these show whether a position counter moves)
Diskless VG-8020 and the CF-3300 with a private copy of the test image, fresh
boot per row. Clean room: RAM contents via PEEK.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF = "Philips_VG_8020"
DUMP = ('F=VARPTR(#{n}):PRINT"<";HEX$(F);":";:FOR K=0 TO 12:'
        'PRINT RIGHT$("0"+HEX$(PEEK(F+K)),2);:NEXT:PRINT">"')
CASES = [
    ("open", ["10 MAXFILES=2:OPEN\"CRT:\" FOR OUTPUT AS #1", "20 " + DUMP.format(n=1),
              "30 CLOSE:END"]),
    ("printed", ["10 MAXFILES=2:OPEN\"CRT:\" FOR OUTPUT AS #1:PRINT #1,\"AB\";",
                 "20 " + DUMP.format(n=1), "30 CLOSE:END"]),
    ("chan2", ["10 MAXFILES=2:OPEN\"CRT:\" FOR OUTPUT AS #1:OPEN\"CRT:\" FOR OUTPUT AS #2",
               "20 " + DUMP.format(n=2), "30 CLOSE:END"]),
]


def val(raw):
    m = re.findall(r"<([0-9A-F]+):([0-9A-F]{26})>", "".join((raw or "").split()))
    return m[-1] if m else None


DISK = "National_CF-3300"
DISK_CASES = [
    ("d_open", ["10 MAXFILES=2:OPEN\"A:FCBT.TXT\" FOR OUTPUT AS #1", "20 " + DUMP.format(n=1),
                "30 CLOSE:END"]),
    ("d_print", ["10 MAXFILES=2:OPEN\"A:FCBT.TXT\" FOR OUTPUT AS #1:PRINT #1,\"AB\";",
                 "20 " + DUMP.format(n=1), "30 CLOSE:END"]),
    ("d_print3", ["10 MAXFILES=2:OPEN\"A:FCBT.TXT\" FOR OUTPUT AS #1:PRINT #1,\"ABC\";",
                  "20 " + DUMP.format(n=1), "30 CLOSE:END"]),
]


def disk_image():
    import shutil, tempfile
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
    fh.close()
    shutil.copy(os.path.join(REPO, "disk", "test720.dsk"), fh.name)
    return fh.name


def show(cases, got):
    for (k, _l), raw in zip(cases, got):
        v = val(raw)
        if not v:
            print(f"{k:8} UNREADABLE")
            continue
        addr, hx = v
        hdr = " ".join(hx[i:i + 2] for i in range(0, 18, 2))
        rec = " ".join(hx[i:i + 2] for i in range(18, 26, 2))
        print(f"{k:8} VARPTR={addr}  header +0..+8: {hdr}   record +9..+12: {rec}")


def main():
    specs = [("direct", ["NEW"] + lines + ["RUN"]) for _k, lines in CASES]
    show(CASES, omsx_repl.run_cases(REF, specs, batch=False, reset=("CLS",), boot=8.0,
                                    capture="screen"))
    # the same on the disk reference, with a WRITABLE private copy of the test image
    img = disk_image()
    try:
        specs = [("direct", ["NEW"] + lines + ["RUN"]) for _k, lines in DISK_CASES]
        # the CF-3300 boots SCREEN 1 and needs kwsweep's MACH_RESET_PRE / MACH_BOOT
        # (an Enter, SCREEN 0; 14 s) -- the harness refused a run without them
        show(DISK_CASES, omsx_repl.run_cases(DISK, specs, batch=False, reset=("", "SCREEN 0", "CLS"),
                                             boot=14.0, capture="screen", diska=img,
                                             step=8.0, cap_gap=20.0))
    finally:
        os.remove(img)
    return 0


if __name__ == "__main__":
    sys.exit(main())
