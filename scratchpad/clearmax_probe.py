"""D-FCBSHAPE S1+S2 design input: where is each machine's memory TOP, and how
high will `CLEAR ,addr` go?

S2 needs a home for the disk-engine state (up to 16 x 50 B, ruled (a): a fixed
table, the reference's shape). zerobas's workspace has no 800 B span, so on a
disk machine it would come off the top of BASIC RAM -- and then `CLEAR ,addr`
must not be allowed above it. How the references bound that is the question.

Per machine, one boot per case, work-area RAM only (clean room):
  boot   HIMEM ($FC4A, published) and FRE(0) straight after boot
  cN     `CLEAR 200,<addr>` for a ladder of addresses -> ERR (0 = accepted) and
         HIMEM afterwards

    python3 -u scratchpad/clearmax_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

MACHINES = [("Philips_VG_8020", False), ("National_CF-3300", True),
            ("C-BIOS_MSX1_EU_REPACK_NODISK", False), ("C-BIOS_MSX1_EU_REPACK_DISK", True)]
ADDRS = ["&HD000", "&HDB00", "&HDC00", "&HDE00", "&HE000", "&HE800", "&HF000", "&HF100", "&HF200", "&HF380"]
H = "PEEK(&HFC4A)+256*PEEK(&HFC4B)"


def cases():
    out = [("boot", ["NEW", f'10 PRINT CHR$(91);"B";{H};FRE(0);CHR$(93)', "RUN"])]
    for a in ADDRS:
        out.append((a, ["NEW", "10 ON ERROR GOTO 30", f"20 CLEAR 200,{a}:E=0:GOTO 40",
                        "30 E=ERR:RESUME 40", f'40 PRINT CHR$(91);"C";E;{H};CHR$(93)', "RUN"]))
    return out


def main():
    cs = cases()
    got = {}
    for m, disk in MACHINES:
        cf = m == "National_CF-3300"
        for k, prog in cs:
            raw = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen", step=3.0,
                                      **({"diska": t._disk_image()} if disk else {}))[0] or ""
            r = re.findall(r"\[[BC]([^\]\"]*)\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':8} " + " ".join(f"{m[:22]:>24}" for m, _ in MACHINES))
    for k, _ in cs:
        print(f"{k:8} " + " ".join(f"{got[(m, k)]:>24}" for m, _ in MACHINES))
    print("boot: HIMEM FRE(0) | cN: ERR (0 = accepted) and HIMEM after")
    return 0


if __name__ == "__main__":
    sys.exit(main())
