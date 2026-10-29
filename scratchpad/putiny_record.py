#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PUTINY's measurements, recorded: each scratchpad/putiny_*.bas program on the
VG-8020 and zerobas's diskless target, printer log into putiny_<name>.out."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs as rp                            # noqa: E402

for name in sys.argv[1:]:
    text = open(os.path.join(REPO, "scratchpad", f"putiny_{name}.bas")).read()
    with open(os.path.join(REPO, "scratchpad", f"putiny_{name}.out"), "w") as f:
        f.write(f"# scratchpad/putiny_{name}.bas\n")
        for m in [rp.REF, "C-BIOS_MSX1_EU_REPACK_NODISK"]:
            r = rp.run(m, f"putiny_{name}", text)
            f.write(f"== {m} {r[0]}\n{r[1].replace(chr(13), '')}\n")
    print("recorded", name)
