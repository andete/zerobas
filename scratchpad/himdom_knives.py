#!/usr/bin/env python3
"""D-HIMDOM knives -- two size-neutral cuts on the COERCION WIDTH.

The claim under test is narrow and precise: `clr_himem` must coerce its argument
in the MSX **ADDRESS** domain (-32768..65535, `eval_addr`), not as a signed int16
and not as a byte. Each knife replaces that one 3-byte call with a different
3-byte call and predicts exactly which rows change.

🎯 K-HD1'S PREDICTIONS ARE MEASURED, NOT GUESSED. It restores
`eval_int16_checked` -- which is precisely the build D-CLRFIX shipped -- so the
predicted faces are read off `scratchpad/himdom_before.out`, a real run of that
ROM, rather than reasoned out. That also makes it a standing regression detector
for the exact defect this slice fixes.

⚠️ A THIRD KNIFE WAS DESIGNED AND NOT RUN, ON PURPOSE. Replacing
`call check_expr_errors` with a no-op would show the guard is load-bearing, but
its predicted HIMEM values are not derivable without reading
`domain_convert_core` to find what DE holds after a FAILED conversion. A knife
whose predicted values I would have to guess is a knife that scores my guess.
The guard is already pinned by D-CLRFIX's K-CF1 on the same instruction.

Rules obeyed: size-neutral value cuts, `rm -rf build` before EVERY build,
RESTORE BY WRITING THE BYTES, assert WHICH image moved (a `basic/*.asm` edit
moves basic-reloc.rom AND the merged image, NOT sub.rom).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/clear.asm"

BASE = {
    'd.50000': '0 ->50000', 'd.40000': '0 ->40000', 'd.32768': '0 ->32768',
    'd.32767': '0 ->32767', 'd.65535': '0 ->65535', 'd.65536': '6 SAME',
    'd.70000': '6 SAME',    'd.hffff': '0 ->65535', 'd.neg1':  '0 ->65535',
    'd.h8000': '0 ->32768', 'd.hd000': '0 ->53248', 'd.zero':  '0 ->0',
    'd.one':   '0 ->1',     'd.h4000': '0 ->16384', 'd.h8050': '0 ->32848',
}

CALL = "                call    eval_addr           ; DE = -32768..65535, FPERR=1 past it\n"

# |x| > 32767 -> ERR 6 before the store. NOTE which rows are NOT here:
# &HD000, &H8000 and &H8050 are hex literals >= &H8000, which MSX BASIC reads as
# NEGATIVE (-12288 / -32768 / -32688), so they sit inside the signed range and
# survive. That is exactly why D-CLRFIX's row set could not see the defect.
INT16_REJECTS = ('d.50000', 'd.40000', 'd.32768', 'd.65535')
# the byte stage additionally rejects anything whose high byte is non-zero
BYTE_REJECTS = ('d.32767', 'd.hffff', 'd.neg1', 'd.h8000', 'd.hd000',
                'd.h4000', 'd.h8050')

KNIVES = [
    dict(name="K-HD1",
         what="eval_addr -> eval_int16_checked: THE REGRESSION, re-created. This "
              "is the exact build D-CLRFIX shipped, so every predicted face is "
              "read off scratchpad/himdom_before.out rather than reasoned",
         old=CALL,
         new="                call    eval_int16_checked  ; K-HD1\n",
         moves={r: '6 SAME' for r in INT16_REJECTS}),
    dict(name="K-HD2",
         what="eval_addr -> eval_byte_checked: the domain narrowed as far as it "
              "goes, so every accepted ceiling must redden -- the control knife",
         old=CALL,
         new="                call    eval_byte_checked   ; K-HD2\n",
         moves={**{r: '6 SAME' for r in INT16_REJECTS},
                **{r: '5 SAME' for r in BYTE_REJECTS}}),
]

IMAGES = ["build/basic-reloc.rom", "build/sub.rom", "build/zerobas-main-eu.rom"]


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def hashes():
    return [hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]
            if os.path.exists(p) else "ABSENT" for p in IMAGES]


def build(tag):
    assert sh("rm -rf build", f"scratchpad/hdknife_{tag}_rm.log") == 0
    return sh("make repack-machine", f"scratchpad/hdknife_{tag}_build.log")


def zb_faces(tag):
    log = f"scratchpad/hdknife_{tag}_probe.out"
    sh("python3 scratchpad/himdom_probe.py --sides=zb", log)
    faces = {}
    for line in open(log):
        if line.startswith("  ran zb "):
            parts = line.split(None, 3)
            faces[parts[2]] = parts[3].strip().strip("'")
    return faces


def main():
    original = open(SRC).read()
    for k in KNIVES:
        assert original.count(k["old"]) == 1, f"{k['name']}: anchor not unique"

    print("=== baseline ===", flush=True)
    assert build("base") == 0, "baseline build failed"
    base_h = hashes()
    print("baseline roms=" + " / ".join(base_h), flush=True)
    base_faces = zb_faces("base")
    assert set(base_faces) == set(BASE), (
        f"row set mismatch: missing {sorted(set(BASE) - set(base_faces))}, "
        f"extra {sorted(set(base_faces) - set(BASE))}")
    for row, want in BASE.items():
        assert base_faces[row] == want, \
            f"baseline row {row}: {base_faces[row]!r} != documented {want!r}"
    print(f"baseline {len(base_faces)} rows match scratchpad/himdom_after2.out",
          flush=True)

    exact = 0
    for k in KNIVES:
        name = k["name"]
        open(SRC, "w").write(original.replace(k["old"], k["new"]))
        assert build(name) == 0, f"{name}: build failed -- see the log"
        h = hashes()
        assert h[0] != base_h[0], f"{name}: basic-reloc.rom did NOT move"
        assert h[2] != base_h[2], f"{name}: merged image did NOT move"
        assert h[1] == base_h[1], f"{name}: sub.rom moved -- wrong image"
        print(f"\n{name}  roms={' / '.join(h)}", flush=True)
        print(f"  cut: {k['what']}", flush=True)
        faces = zb_faces(name)
        want = dict(BASE); want.update(k["moves"])
        bad = {r: (faces.get(r), want[r]) for r in want if faces.get(r) != want[r]}
        moved = {r: faces.get(r) for r in BASE if faces.get(r) != BASE[r]}
        print(f"  moved {len(moved)} rows: "
              + ", ".join(f"{r}={v!r}" for r, v in sorted(moved.items())), flush=True)
        if bad:
            print("  NOT EXACT: "
                  + ", ".join(f"{r} got {g!r} want {w!r}" for r, (g, w) in sorted(bad.items())),
                  flush=True)
        else:
            exact += 1
            print(f"  EXACT -- {len(k['moves'])} predicted, {len(moved)} moved", flush=True)
        open(SRC, "w").write(original)          # RESTORE BY WRITING THE BYTES

    assert build("restore") == 0, "restore build failed"
    rh = hashes()
    print(f"\nrestored roms={' / '.join(rh)}", flush=True)
    assert rh == base_h, f"restore did not reproduce the baseline: {rh} != {base_h}"
    print(f"{exact}/{len(KNIVES)} knife rows EXACT")
    return 0 if exact == len(KNIVES) else 1


if __name__ == "__main__":
    sys.exit(main())
