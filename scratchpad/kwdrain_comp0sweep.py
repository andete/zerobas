#!/usr/bin/env python3
"""CAS_BITCOMP sweep. At 12 the VG-8020 stopped HANGING and started DECODING —
`Skip :  @ @@` instead of silence, i.e. the leader lock works and a header was
read, but the NAME still garbles, so a few bits are still misread.

T-state arithmetic on the two tails puts the real cost near 13 djnz iterations
('1' path ~168 T, '0' path ~175 T, one iteration = 13 T), so 12 under-compensates.
Sweep it and judge on BOTH readings: the histogram outliers between the tones, and
the only criterion that matters — does the reference READ the tape.
"""
import collections, os, re, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
TAPE = os.path.join(ROOT, "tape", "tape.asm")
orig = open(TAPE, encoding="utf-8").read()

def build(comp):
    s = re.sub(r"(CAS_BITCOMP0:\s+equ\s+)\d+", r"\g<1>%d" % comp, orig)
    open(TAPE, "w", encoding="utf-8").write(s)
    return subprocess.run(["make", "repack-machine"], cwd=ROOT,
                          capture_output=True, text=True).returncode

def run(side, lines, gap=150.0, **kw):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"], step=5.0,
                               cap_gap=gap, timeout=1800.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return [r.strip() for r in rows if r.strip()]

try:
    for comp in [int(a) for a in sys.argv[1:]] or [13]:
        if build(comp) != 0:
            print("comp=%-3d BUILD FAILED" % comp); continue
        tmp = tempfile.mkdtemp(prefix="comp_")
        wav = os.path.join(tmp, "t.wav")
        run("zb", ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'],
            prologue=(f"cassetteplayer new {{{wav}}}",))
        s_, fr = cas_decode.read_samples(wav)
        hp = cas_decode.half_periods(cas_decode.zero_crossings(s_))
        h = collections.Counter(x for x in hp if x <= 40)
        mid = sum(h[d] for d in (11, 12, 13, 14, 15, 16, 17))
        rows = run("vg8020", ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'], cassette=wav)
        tail = " | ".join(rows[-2:])
        read = "[P9]" in " | ".join(rows) and "Found:ZQ" in " | ".join(rows)
        print("comp=%-3d between-tone half-periods=%-4d  VG %s  %s"
              % (comp, mid, "READS" if read else "no   ", tail[-46:]))
        sys.stdout.flush()
finally:
    open(TAPE, "w", encoding="utf-8").write(orig)
    subprocess.run(["make", "repack-machine"], cwd=ROOT, capture_output=True)
    print("tape.asm restored to CAS_BITCOMP=12 and rebuilt")
