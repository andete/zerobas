#!/usr/bin/env python3
"""🔬 FOUR TIMING AXES NOW MATCH THE REFERENCE AND THE DATA BLOCK STILL FAILS
(D-CASDUTY), so the next suspect is not WHEN the bits are emitted but WHICH bits
are emitted. The VG-8020 loads a clean-room `.cas` of the same program happily,
so that image is the oracle for CONTENT the way its recorded tape was for timing.

Decode the bytes zerobas actually puts on the tape and lay them beside the `.cas`
logical image: header block, filename, and above all the DATA block's length and
tail, where a missing terminator or a short flush would look exactly like a load
that never returns.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode, cas_decode
from bas_tokenise import make_multiline_program

PROG = make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)
ref = cas_encode.build_cas_basic("ZQ", PROG)
tmp = tempfile.mkdtemp(prefix="casbytes_")

def show(label, b):
    print("%-22s %4d bytes" % (label, len(b)))
    for off in range(0, min(len(b), 96), 16):
        chunk = b[off:off+16]
        print("    %04X  %-47s |%s|" % (off, " ".join("%02X" % c for c in chunk),
              "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)))
    if len(b) > 96:
        print("    ...   last 16: %s" % " ".join("%02X" % c for c in b[-16:]))

# The .cas sync marker separates the logical blocks; it is a LEADER, not data.
sync = cas_encode.CAS_SYNC
parts = ref.split(sync)
print("=== clean-room .cas: %d block(s) after %d sync marker(s)"
      % (len(parts) - 1, ref.count(sync)))
for i, p in enumerate(parts[1:]):
    show("  .cas block %d" % i, p)
print("=== the tokenised program image the .cas carries")
show("  program", PROG)

# 🎯 THE REFERENCE MACHINE IS THE ORACLE FOR THE TAIL, exactly as it was for the
# timing: record ITS OWN CSAVE and count what it writes after the program image.
for side in ("zb", "vg8020"):
    cfg = probe_sides.sides(side)[side]
    wav = os.path.join(tmp, side + ".wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"',
                                                    'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=150.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{wav}}}",))
    got = cas_decode.decode_file(wav, stop_bits=1)
    b = bytes(got) if not isinstance(got, tuple) else bytes(got[0])
    show("  %s wrote" % side, b)
    tail = len(b) - (len(b.rstrip(b"\x00")))
    print("      trailing $00 bytes after the last non-zero: %d" % tail)
    print("      program image is %d bytes, so the TAIL is %d beyond it"
          % (len(PROG), len(b) - 16 - len(PROG)))
    sys.stdout.flush()
