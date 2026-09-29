"""D-ERRKEEP2 remainder: does a LOAD's disk-READ error survive an OPEN file?

`hk_claim_status` (disk.rom) keeps a pending DISKOP_ERR alive past chan_gate's
restore, which re-stages the open channel and so clears the code on a
successful read. KILL, NAME, COPY and SAVE end in it; LOAD's hooks (`hk_dpload`
and the ASCII arm) still end on their own. The hole can only show on a READ
failure inside the file being loaded while the open file's own sector still
reads -- so this builds a crafted copy of disk/test720.dsk with one extra root
entry, `BAD.BAS`, whose first cluster lies PAST THE END OF THE DISK. Both
machines get the same image, the same failing read.

Cases (direct mode, one boot each, a private image each; ERR read back after):
  plain    LOAD "BAD.BAS"                         -- nothing open: the control
  open     OPEN "Z.TXT" FOR OUTPUT AS #1, LOAD "BAD.BAS", then PRINT #1 --
           ERR says whether the code survived, the PRINT # whether LOAD
           closed the channel (59 = closed) -- a separate fact both ways
"""
import os
import re
import shutil
import struct
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

BAD_CLUSTER = 0x7F0   # far past a 720 KB volume's last cluster


def crafted_image() -> str:
    img = bytearray(open(os.path.join(REPO, "disk", "test720.dsk"), "rb").read())
    bps, spc, rsv, nf, nroot, _, _, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    root = (rsv + nf * spf) * bps
    for i in range(nroot):
        off = root + 32 * i
        if img[off] in (0x00, 0xE5):
            e = bytearray(32)
            e[0:11] = b"BAD     BAS"
            struct.pack_into("<H", e, 26, BAD_CLUSTER)
            struct.pack_into("<I", e, 28, 1000)
            img[off:off + 32] = e
            break
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="zb_errkeep3_")
    os.write(fd, bytes(img))
    os.close(fd)
    return path


RD = 'PRINT CHR$(91);ERR;"]"'
CASES = {
    # round 2: zerobas raised NOTHING for the bad LOAD, open file or not, where the
    # CF-3300 says `Disk offline` (70). Driver or loader? Read the same sector
    # range directly, and LIST what the "load" left behind.
    "dski": ['A$=DSKI$(0,4000)', RD],
    "list": ['LOAD "BAD.BAS"', RD, "LIST"],
    "plain": ['LOAD "BAD.BAS"', RD],
    "open": ['OPEN "Z.TXT" FOR OUTPUT AS #1', 'LOAD "BAD.BAS"', RD,
             'PRINT #1,"X"', RD],
}


def main():
    only = sys.argv[1:] or list(CASES)
    for m, cf in (("National_CF-3300", True), ("C-BIOS_MSX1_EU_REPACK_DISK", False)):
        for k in only:
            raw = omsx_repl.run_cases(m, [("direct", CASES[k])], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=crafted_image(), step=8.0, cap_gap=30.0)[0] or ""
            rows = [raw[r * 40:(r + 1) * 40].rstrip() for r in range(24)]
            said = [r.strip() for r in rows if r.strip() and not r.lstrip().startswith(
                ("LOAD", "OPEN", "PRINT", "color"))]
            errs = re.findall(r"\[\s*(-?\d+)\s*\]", raw)
            print(f"{m[:10]:10} {k:6} ERR={errs}  screen={said[-6:]}")


if __name__ == "__main__":
    main()
