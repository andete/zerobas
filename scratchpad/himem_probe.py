"""D-HIMEMLIE step 1: what does `CLEAR 200,<addr>` do at, above and below the
boot HIMEM -- on the two references and on both zerobas builds?

zerobas's HIMEM ($FC4A) reads $F380 while zerobas occupies $DB00..$F37F
(scratchpad/ramlayout_probe.py). Before the cell is changed, the reference's
CLEAR address rule is measured: which addresses it accepts, which error it
raises for the rest, and what HIMEM and FRE(0) read after a legal one.

Each case is ONE typed line on a fresh boot: `CLEAR 200,<addr>` then a fenced
print of HIMEM and FRE(0). An error prints its message instead of the fence.
Clean room: typed BASIC, the documented HIMEM cell, screen text. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

PAIRS = [("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"),
         ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK")]
# the boot HIMEM of each reference (ramlayout_run.out), and the addresses to try
BOOT = {"Philips_VG_8020": 0xF380, "National_CF-3300": 0xDE77}
SHOW = 'PRINTCHR$(91);HEX$(PEEK(&HFC4A)+256*PEEK(&HFC4B));FRE(0);CHR$(93)'


def addrs(himem):
    return [("himem", himem), ("himem+1", himem + 1), ("F380", 0xF380),
            ("DB00", 0xDB00), ("DB01", 0xDB01), ("D000", 0xD000)]


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    for r in reversed(rows):
        if r.startswith("[") and r.endswith("]"):
            return r
        if "error" in r.lower() or "illegal" in r.lower() or "out of" in r.lower():
            return r
    return None


def key(ans):
    return ans.split()[0] if ans.startswith("[") else ans


def main():
    bad = total = 0
    for ref, zb in PAIRS:
        cases = [(k, f"CLEAR200,&H{a:04X}:" + SHOW) for k, a in addrs(BOOT[ref])]
        specs = [("direct", [line]) for _k, line in cases]
        got = {m: omsx_repl.run_cases(m, specs, batch=False,
                                      reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                      capture="screen")
               for m in (ref, zb)}
        print(f"== {ref} vs {zb}")
        for i, (k, line) in enumerate(cases):
            r, z = answer(got[ref][i] or ""), answer(got[zb][i] or "")
            # FRE(0) differs by the known layout gap on EVERY row, so the
            # compared reading is the error text, or the HIMEM hex alone.
            same = r is not None and z is not None and key(r) == key(z)
            total += 1
            bad += not same
            print(f"{'SAME' if same else 'DIFF'} {ref.split('_')[-1]}:{k:8s} {line.split(':')[0]}")
            print(f"   ref: {r or '<NO OUTPUT>'}")
            print(f"   zb : {z or '<NO OUTPUT>'}")
    print(f"\nDIFF: {bad}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
