#!/usr/bin/env python3
"""Make the TAPIN study's 2400-baud tape ON THE REFERENCE: the VG-8020 CLOADs
tapin_margin.py's program from its .cas, then `CSAVE"PROG",2` (2400 baud) into a
fresh openMSX recording. The WAV is written to OUT; scratchpad/cas_decode.py's
decoder is baud-agnostic and reports what it holds.

    python3 -u scratchpad/tapin_wav2400.py OUT.wav
"""
import os, shutil, subprocess, sys, tempfile, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "scratchpad"), os.path.join(REPO, "probes", "lib"),
                os.path.join(REPO, "probes", "disk")]
import tapin_margin as T  # noqa: E402
import omsx_preflight  # noqa: E402
from cas_encode import build_cas_basic_csave  # noqa: E402
from bas_tokenise import make_multiline_program  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"


def main():
    out = os.path.abspath(sys.argv[1])
    td = tempfile.mkdtemp(prefix="wav2400_")
    cas = os.path.join(td, "p.cas")
    open(cas, "wb").write(build_cas_basic_csave("PROG", make_multiline_program(T.LINES, 0x8001)))
    if os.path.exists(out):
        os.unlink(out)
    tcl = os.path.join(td, "t.tcl")
    open(tcl, "w").write("\n".join([
        "set throttle off",
        "after time 8 { type {CLOAD} }", 'after time 9 { type "\\r" }',
        # the .cas plays fast; CLOAD is done well before 60 s
        f"after time 60 {{ cassetteplayer new {{{out}}} }}",
        'after time 62 { type {CSAVE"PROG",2} }', 'after time 63 { type "\\r" }',
        "after time 160 { cassetteplayer eject; exit }",
    ]) + "\n")
    p = subprocess.Popen(omsx_preflight.guarded([OMSX, "-machine", "Philips_VG_8020",
                         "-cassetteplayer", cas, "-command", "set renderer none; set sound_driver null",
                         "-script", tcl]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < 600:
        time.sleep(0.5)
    if p.poll() is None:
        p.terminate(); p.wait()
    print(f"wrote {out}: {os.path.getsize(out) if os.path.exists(out) else 'NOTHING'} bytes")
    shutil.rmtree(td)


if __name__ == "__main__":
    main()
