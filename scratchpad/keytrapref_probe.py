#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-KEYTRAPREF, measure first: how the VG-8020 keeps the function-key traps in the published cells.

Joost 2026-11-22: "do the key trap properly first, then rebase" -- replace zerobas's own-layout trap
table + the H_ZKEY C-BIOS hook by the reference's own mechanism on the published cells. The handbook
names FNKFLG ($FBCE, FNKSB's input) but gives no layout, so the layout is MEASURED: work-area RAM
contents only (FNKFLG + ONGSBF $FBCE-$FBD8, TRPTBL $FC4C-$FC99, PUTPNT / GETPNT, KEYBUF, INTFLG,
CURLIN), snapshotted by the probe at a moment the BASIC program chooses ($D003 := 1), or at a fixed
emulated time for the prompt cases. Function keys are pressed on the real matrix (row 6 bits 5/6/7,
row 7 bits 0/1), so the scan under test is the one that sees them. No ROM byte, no PC.

FNKSTR slot n is poked to "X" + NUL so a delivered key is one visible byte in KEYBUF.

    python3 -u scratchpad/keytrapref_probe.py [CASE ...] [--machine M]
"""
import os
import sys

os.environ["ZEROBAS_REFCACHE"] = "0"   # kt.run caches ITS capture file, not ours: never serve from the store
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import basic_probe_key_trap as kt          # noqa: E402  (run(), the matrix helpers)

SPANS = (("FNKFLG", 0xFBCE, 10), ("ONGSBF", 0xFBD8, 1), ("TRPTBL", 0xFC4C, 78),
         ("PUTPNT", 0xF3F8, 2), ("GETPNT", 0xF3FA, 2), ("KEYBUF", 0xFBF0, 40),
         ("INTFLG", 0xFC9B, 1), ("CURLIN", 0xF41C, 2), ("D0", 0xD000, 8))

FNK_X = "5 FOR I=0 TO 9:POKE &HF87F+16*I,88+I:POKE &HF880+16*I,0:NEXT"   # F1 'X', F2 'Y', F3 'Z' ...
DONE = "POKE &HD003,1"
WAIT = "GOTO 90"                      # park RUNNING (CURLIN 90) so the capture sees a live program
PARK = "90 GOTO 90"


def prog(*body):
    return ["NEW", FNK_X] + list(body) + [PARK]


CASES = {
    # THE BASELINE: no trap, no FNKFLG -- F1 MUST arrive as 'X' pending, or the run proves nothing
    "none_run": (prog(f"30 FOR I=1 TO 6000:NEXT:{DONE}:{WAIT}"), kt.tap(1, at=1.5)),
    # AT THE PROMPT: FNKFLG(3) set, the program ENDs, F3 pressed at "Ok" -- does the BIOS divert there too?
    # 'Z' (F3) appears in no typed line, so a 'Z' anywhere in KEYBUF means it was delivered at some time
    "fnkflg_prompt": (["NEW", FNK_X, "10 POKE &HFBD0,1:POKE &HD003,1:END"], kt.tap(3, at=1.5)),
    "none_prompt": (["NEW", FNK_X, "10 POKE &HD003,1:END"], kt.tap(3, at=1.5)),
    # a SECOND press while the handler runs (status 3 = ON + servicing): which bits does the scan set?
    "on_twice": (prog("10 ON KEY GOSUB 100:POKE &HD001,0", "20 KEY(1) ON",
                      f"30 FOR I=1 TO 9000:NEXT:{DONE}:{WAIT}",
                      "100 POKE &HD001,PEEK(&HD001)+1:FOR J=1 TO 2500:NEXT:RETURN"),
                 kt.tap(1, at=1.5) + kt.tap(1, at=3.0)),
    # the table after the statements alone, no key pressed
    "static": (prog("10 ON KEY GOSUB 100,100,100,100,100",
                    "20 KEY(1) ON:KEY(2) STOP:KEY(3) OFF:KEY(4) ON:KEY(4) OFF:KEY(5) STOP:KEY(5) ON",
                    f"30 {DONE}:{WAIT}", "100 RETURN"), []),
    # KEY(2) STOP, F2 pressed while the loop runs: pending, not run; was 'Y' buffered?
    "stop_press": (prog("10 ON KEY GOSUB 100,100", "20 KEY(2) STOP",
                        f"30 FOR I=1 TO 6000:NEXT:{DONE}:{WAIT}", "100 POKE &HD001,1:RETURN"),
                   kt.tap(2, at=1.5)),
    # KEY(1) ON, F1 pressed: the snapshot is taken INSIDE the handler
    "on_inside": (prog("10 ON KEY GOSUB 100", "20 KEY(1) ON",
                       "30 FOR I=1 TO 6000:NEXT:GOTO 90", f"100 {DONE}:GOTO 100"),
                  kt.tap(1, at=1.5)),
    # ... and after the handler returned
    "on_after": (prog("10 ON KEY GOSUB 100", "20 KEY(1) ON",
                      f"30 FOR I=1 TO 6000:NEXT:{DONE}:{WAIT}", "100 POKE &HD001,1:RETURN"),
                 kt.tap(1, at=1.5)),
    # the BIOS half: FNKFLG(1) poked, no ON KEY / KEY(1) ON at all, program running
    "fnkflg_run": (prog("10 POKE &HFBCE,1", f"30 FOR I=1 TO 6000:NEXT:{DONE}:{WAIT}"),
                   kt.tap(1, at=1.5)),
    # FNKFLG(1) poked $FF (KEY ON writes which value? 'static' says)
    "fnkflg_ff": (prog("10 POKE &HFBCE,255", f"30 FOR I=1 TO 6000:NEXT:{DONE}:{WAIT}"),
                  kt.tap(1, at=1.5)),
    # KEY(1) ON through BASIC, then FNKFLG(1) cleared behind its back: does the BIOS deliver?
    "on_fnk0": (prog("10 ON KEY GOSUB 100", "20 KEY(1) ON:POKE &HFBCE,0",
                     f"30 FOR I=1 TO 6000:NEXT:{DONE}:{WAIT}", "100 POKE &HD001,1:RETURN"),
                kt.tap(1, at=1.5)),
}


def capture_tcl(path):
    reads = " ".join(f'binary scan [debug read_block memory 0x{a:04X} {n}] H* h; puts $f "{nm}=$h";'
                     for nm, a, n in SPANS)
    return f"proc __cap {{}} {{ set f [open {{{path}}} w]; {reads} close $f; exit }}"


def run(machine, lines, events):
    """kt.run with a wider __cap: patch the module's capture proc text for this call."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="keytrapref_")
    os.close(fd)
    os.unlink(path)
    # kt.run builds its own __cap; we re-define it by appending ours as a key event at t=0
    # (a later `proc` wins), so the poll on $D003 still fires it.
    wpath = path + ".w"
    watch = ("set ::__wf {%s}; proc __w {} { set a $::wp_last_address; set f [open $::__wf a];"
             " puts $f \"[format %%.3f [machine_info time]] [format %%04X $a] [debug read memory $a]"
             " [expr {[debug read memory 0xF41C] | [debug read memory 0xF41D] << 8}]\"; close $f };"
             " debug set_watchpoint write_mem {0xFC4C 0xFC5A} {} {__w};"
             " debug set_watchpoint write_mem 0xFBD8 {} {__w}") % wpath
    ev = [(0.0, capture_tcl(path)), (0.0, watch)] + list(events)
    kt.run(machine, lines[1:] if lines[0] == "NEW" else lines, ev)
    global WATCH
    WATCH = open(wpath).read().split("\n") if os.path.exists(wpath) else []
    if os.path.exists(wpath):
        os.unlink(wpath)
    if not os.path.exists(path):
        return None
    out = {}
    for line in open(path):
        k, _, v = line.strip().partition("=")
        out[k] = v
    os.unlink(path)
    return out


def show(case, m, r):
    if r is None:
        print(f"{case:11s} {m[:12]:12s} NO READING", flush=True)
        return
    keybuf = bytes.fromhex(r["KEYBUF"])
    put = int.from_bytes(bytes.fromhex(r["PUTPNT"]), "little")
    get = int.from_bytes(bytes.fromhex(r["GETPNT"]), "little")
    tr = bytes.fromhex(r["TRPTBL"])
    ents = " ".join(f"{i}:{tr[3*i]:02X}/{tr[3*i+1] | tr[3*i+2] << 8:04X}" for i in range(26)
                    if tr[3*i] or tr[3*i+1] or tr[3*i+2])
    pend = bytes(keybuf[(i - 0xFBF0) % 40] for i in range(get, put)) if put >= get else b"?"
    seen = "".join(sorted({chr(b) for b in keybuf if b in b"XYZ"}))
    print(f"{case:13s} {m[:12]:12s} raw[{seen}] FNKFLG={r['FNKFLG']} ONGSBF={r['ONGSBF']} INTFLG={r['INTFLG']} "
          f"CURLIN={r['CURLIN']} D0={r['D0'][:8]} pending={pend!r} TRPTBL[{ents or '-'}]", flush=True)


WATCH = []


def main(argv):
    m = argv[argv.index("--machine") + 1] if "--machine" in argv else kt.REF_MACHINE
    names = [a for a in argv if a in CASES] or list(CASES)
    for c in names:
        lines, ev = CASES[c]
        show(c, m, run(m, lines, ev))
        if "--watch" in argv:
            for w in WATCH:
                if w.strip():
                    print("      write", w, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
