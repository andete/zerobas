#!/usr/bin/env python3
# Per-frame PSG register trace harness (audio Slice-3 characterization).
# Samples the 14 PSG registers on every VBLANK (VDP.IRQvertical raised edge) while
# a PLAY statement's music drains. The reference's $0038 ISR drains the PLAY queue
# once per VBLANK, so the frame-by-frame PSG state IS the drain behavior we must
# reproduce in play_service.
import argparse, os, subprocess, sys, tempfile, signal, time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.dirname(_zbo.path.abspath(__file__)))
import omsx_preflight  # noqa: E402

DEFAULT_OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")

TCL = r'''
set throttle off
proc __hex {{dbg addr len}} {{
  binary scan [debug read_block $dbg $addr $len] H* h; return $h
}}
set ::armed 0
set ::left 0
set ::rows {{}}
proc __sample {{}} {{
  if {{$::armed == 0}} return
  if {{[debug probe read VDP.IRQvertical] == 0}} return
  if {{$::left <= 0}} {{
    set f [open {{{out}}} w]
    foreach r $::rows {{ puts $f $r }}
    close $f
    exit
  }}
  incr ::left -1
  lappend ::rows "[machine_info VDP_frame_count] [__hex {{PSG regs}} 0 14]"
}}
debug probe set_bp VDP.IRQvertical {{}} {{ __sample }}
after time {tp} {{ type -- "{stmt}\r" }}
after time {arm} {{ set ::armed 1; set ::left {n} }}
after time {deadline} {{ puts stderr "DEADLINE left=$::left"; exit }}
'''


def trace(machine, stmt, out, n=400, tp=5.0, arm=5.6, deadline=45.0, omsx=None):
    omsx = omsx or DEFAULT_OMSX
    tcl = TCL.format(n=n, out=os.path.abspath(out), tp=tp, arm=arm,
                     deadline=deadline, stmt=stmt.replace('"', '\\"'))
    fd, tclp = tempfile.mkstemp(suffix=".tcl", prefix="psgtrace_")
    os.write(fd, tcl.encode()); os.close(fd)
    cmd = [omsx, "-machine", machine, "-command", "set renderer none; set sound_driver null", "-script", tclp]
    try:
        p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        dl = time.time() + deadline + 30
        while p.poll() is None and time.time() < dl:
            time.sleep(0.1)
        if p.poll() is None:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            print("TIMEOUT", file=sys.stderr)
    finally:
        os.unlink(tclp)


def parse(path):
    """-> list of (frame_count, [14 reg ints]); dedup consecutive identical frame#."""
    rows = []
    seen = set()
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line[0] not in "0123456789":
                continue
            fc_s, hexs = line.split()
            fc = int(fc_s)
            if fc in seen:
                continue
            seen.add(fc)
            rows.append((fc, list(bytes.fromhex(hexs))))
    return rows


def note_segments(rows, voice=0):
    """Collapse a trace into (start_frame, dur_frames, tone_period, amp) segments
    for one voice, keyed on (tone_period, amp) changes."""
    lo, hi, amp = voice * 2, voice * 2 + 1, 8 + voice
    segs = []
    prev = None
    start = None
    for fc, r in rows:
        tp = r[lo] | (r[hi] << 8)
        sig = (tp, r[amp] & 0x1F)
        if sig != prev:
            if prev is not None:
                segs.append((start, fc - start, prev[0], prev[1]))
            prev = sig
            start = fc
    return segs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", default="Philips_VG_8020")
    ap.add_argument("--stmt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--tp", type=float, default=5.0)
    ap.add_argument("--arm", type=float, default=5.6)
    ap.add_argument("--deadline", type=float, default=45.0)
    ap.add_argument("--voice", type=int, default=0)
    a = ap.parse_args()
    trace(a.machine, a.stmt, a.out, a.n, a.tp, a.arm, a.deadline)
    rows = parse(a.out)
    print(f"{len(rows)} frames; {a.stmt}")
    for st, dur, tp, amp in note_segments(rows, a.voice):
        print(f"  f{st:5} dur={dur:3} tp={tp:4} amp={amp:2}")
