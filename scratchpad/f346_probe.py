# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-F346 (Joost, 2026-10-23: "if you boot into basic and not into dos first, if
you do poke &hf346,1 you can do call system"): does CALL SYSTEM go by the work-area
cell &HF346, and when is that cell set?

  data_peek   boot a data disk (test720) -> PEEK(&HF346)
  dos_peek    boot the MSX-DOS disk, A>BASIC -> PEEK(&HF346)
  late_poke   boot test720, insert the MSX-DOS disk, POKE &HF346,1:CALL SYSTEM, DIR
  late_plain  the same without the POKE (the control: Illegal function call)
  dos_zero    boot the MSX-DOS disk, A>BASIC, POKE &HF346,0:CALL SYSTEM

Built on scratchpad/callsystem_swap.py (it swaps the disk mid-session, which
omsx_repl cannot). A data disk asks the date at power-on on every machine here
(D-STEP7DATE), so those cases answer it first. Clean-room: typed keys in, the text
screen and documented work-area cells out.

usage: f346_probe.py DOSDISK [cf|eu|zb ...] [-- case ...]
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import callsystem_swap as cs                        # noqa: E402
import probe_tmp                                    # noqa: E402

MACHINES = {"cf": ("National_CF-3300", []),
            "eu": ("Philips_VG_8020", ["-ext", "Philips_NMS_1200"]),
            "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}
SLOW = {"eu": 1.8}
S0 = "SCREEN 0:WIDTH 40"
DATA_BOOT = [("type", "", 14), ("type", S0, 6)]                       # the date, then text
DOS_BOOT = [("type", "", 14), ("type", "", 4), ("type", "BASIC", 4), ("type", S0, 10)]


def slow(steps, k):
    """Every wait times k: the VG-8020 + NMS 1200 boots DOS slower than these waits
    (its first run read blank screens on the DOS rows)."""
    return [(kind, arg, wait * k) for kind, arg, wait in steps]


def cases(data, dosc):
    return {
        "data_peek": (data, DATA_BOOT + [("type", "PRINT PEEK(&HF346)", 4)]),
        "dos_peek": (dosc, DOS_BOOT + [("type", "PRINT PEEK(&HF346)", 4)]),
        "late_poke": (data, DATA_BOOT + [("type", "PRINT PEEK(&HF346)", 4), ("disk", dosc, 4),
                                         ("type", "POKE &HF346,1:CALL SYSTEM", 2),
                                         ("type", "", 10), ("type", "", 4),
                                         ("type", "MODE 40", 4), ("type", "DIR MSXDOS.SYS", 4)]),
        "late_plain": (data, DATA_BOOT + [("disk", dosc, 4), ("type", "CALL SYSTEM", 2),
                                          ("type", "", 10), ("type", "", 4),
                                          ("type", "PRINT 12345", 4)]),
        "dos_zero": (dosc, DOS_BOOT + [("type", "POKE &HF346,0:CALL SYSTEM", 2),
                                       ("type", "PRINT 12345", 10)]),
    }


def main():
    dos = sys.argv[1]
    args = sys.argv[2:]
    names = args[args.index("--") + 1:] if "--" in args else []
    keys = [a for a in (args[:args.index("--")] if "--" in args else args)] or list(MACHINES)
    data = probe_tmp.tmp("f346_test720.dsk")
    dosc = probe_tmp.tmp("f346_dos.dsk")
    for key in keys:
        machine, extra = MACHINES[key]
        cs.OMSX_EXTRA = extra
        for name, (boot, steps) in cases(data, dosc).items():
            steps = slow(steps, SLOW.get(key, 1.0))
            if names and name not in names:
                continue
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), data)
            shutil.copyfile(dos, dosc)
            print(f"== {name} {key} {machine}", flush=True)
            for r in cs.run(machine, boot, steps, f"f346_{key}_{name}"):
                print(f"   |{r}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
