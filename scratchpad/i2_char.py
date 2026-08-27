#!/usr/bin/env python3
"""I2 characterization -- what does the VG-8020 reference return for PDL(n)/PAD(n)
under each openMSX joyport configuration?

Reuses omsx_repl's batch driver but prepends `plug` commands to the generated Tcl
(the driver has no prologue hook yet -- that is a harness addition I2 will need).
"""
from __future__ import annotations
import os, re, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl as R
from omsx_run import find_omsx

REF = "Philips_VG_8020"


def run(machine: str, cases, prologue: list[str], *, boot=8.0, step=2.5,
        cap_gap=2.5, reset=("CLS",), timeout=600.0):
    binary = find_omsx(None)
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="i2_", delete=False).name
    tcl = out + ".tcl"
    body = R._tcl(out, cases, boot, step, cap_gap, reset, "screen", None, 12.0)
    with open(tcl, "w") as f:
        f.write("\n".join(prologue) + "\n" + body)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [binary, "-machine", machine, "-command", "set renderer none",
           "-script", tcl]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.05)
    if proc.poll() is None:
        import signal
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    caps = {}
    if os.path.exists(out):
        for ln in open(out):
            m = re.match(r"case\.(\d+)=([0-9a-f]*)", ln.strip())
            if m and m.group(2):
                data = bytes.fromhex(m.group(2))
                caps[int(m.group(1))] = "".join(
                    chr(b) if 32 <= b < 127 else " " for b in data)
        os.unlink(out)
    os.unlink(tcl)
    return [caps.get(i) for i in range(len(cases))]


def span(raw):
    if raw is None:
        return None
    m = re.findall(r"\[([^\]]*)\]", raw)
    return m[-1].strip() if m else None


# one case per read, tagged, error-trapped
CASES = []
LABELS = []
for n in range(0, 14):
    CASES.append(("stored", ["ON ERROR GOTO 40",
                             f'PRINT"[";PDL({n});"]"', "END",
                             'PRINT"[E";ERR;"]":END']))
    LABELS.append(f"PDL({n})")
for n in range(0, 9):
    CASES.append(("stored", ["ON ERROR GOTO 40",
                             f'PRINT"[";PAD({n});"]"', "END",
                             'PRINT"[E";ERR;"]":END']))
    LABELS.append(f"PAD({n})")

CONFIGS = {
    "none": [],
    "paddleA": ["plug joyporta paddle"],
    "paddleAB": ["plug joyporta paddle", "plug joyportb paddle"],
    "touchpadA": ["plug joyporta touchpad"],
    "joystickA": ["plug joyporta msxjoystick1"],
}

want = sys.argv[1:] or list(CONFIGS)
for name in want:
    print(f"=== config {name}: {CONFIGS[name]}", flush=True)
    outs = run(REF, CASES, CONFIGS[name])
    for lab, raw in zip(LABELS, outs):
        print(f"  {lab:9s} -> {span(raw)!r}", flush=True)
