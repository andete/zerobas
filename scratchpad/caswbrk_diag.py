#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASWBRK diagnostic: does the @BREAK rig land during a tape write at all?

caswbrk_probe.py read `no error` on BOTH machines for CSAVE / BSAVE / OPEN FOR
OUTPUT broken a second in, and no reading for SAVE. Before believing either,
time the writes (TIME=0 before, TIME after, no break) and break a plain FOR
loop as the rig's control (it must read `Break in 20` on both).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")


def prog(verb, tail):
    return ["NEW", "10 ON ERROR GOTO 90", f"15 TIME=0:{verb}",
            '30 PRINT"[N";TIME;"]":END', '90 PRINT"[E";ERR;ERL;TIME;"]":END',
            "RUN"] + tail


NB = ["@WAIT25"]
CASES = {
    "loopbrk": prog("FOR I=1 TO 30000:NEXT", ["@WAIT1", "@BREAK", "@WAIT4"]),
    "csave_t": prog('CSAVE"X"', NB),
    "bsave_t": prog('BSAVE"CAS:X",&H9000,&H90FF', NB),
    "open_t": prog('OPEN"CAS:X"FOR OUTPUT AS#1', NB),
    "save_t": prog('SAVE"CAS:X"', NB),
    "csave_b0": prog('CSAVE"X"', ["@BREAK", "@WAIT6"]),
    "csave_b3": prog('CSAVE"X"', ["@WAIT3", "@BREAK", "@WAIT6"]),
}
# when does each write FINISH? capture at increasing delays, no break.
for _v, _verb in (("csave", 'CSAVE"X"'), ("save", 'SAVE"CAS:X"'),
                  ("open", 'OPEN"CAS:X"FOR OUTPUT AS#1')):
    for _w in ("0.5", "1.5", "3", "6", "12", "40"):
        CASES[f"{_v}_w{_w}"] = prog(_verb, [f"@WAIT{_w}"])
# a Ctrl-STOP STORM: eight presses spread over ~30 s, covering the whole write.
STORM = ["@WAIT0.3"] + ["@BREAK", "@WAIT0.5"] * 8 + ["@WAIT4"]
for _v, _verb in (("csave", 'CSAVE"X"'), ("bsave", 'BSAVE"CAS:X",&H9000,&H90FF'),
                  ("open", 'OPEN"CAS:X"FOR OUTPUT AS#1'),
                  ("print", 'OPEN"CAS:X"FOR OUTPUT AS#1:FOR J=1 TO 40:PRINT#1,STRING$(200,65):NEXT:CLOSE')):
    CASES[f"{_v}_storm"] = prog(_verb, STORM)
# big DATA blocks: the header is ~6 s of a small write; presses must land in DATA.
REMS = [f"{n} REM " + "X" * 200 for n in range(1, 9)]
CASES["bsave_big"] = prog('BSAVE"CAS:X",&H8000,&H87FF', STORM)
CASES["csave_big"] = REMS[:] + prog('CSAVE"X"', STORM)[1:]
CASES["csave_big"].insert(0, "NEW")
CASES["print_long"] = prog('OPEN"CAS:X"FOR OUTPUT AS#1:FOR J=1 TO 40:PRINT#1,STRING$(200,65):NEXT:CLOSE', ["@WAIT150"])
CASES["print_late"] = prog('OPEN"CAS:X"FOR OUTPUT AS#1:FOR J=1 TO 40:PRINT#1,STRING$(200,65):NEXT:CLOSE',
                           ["@WAIT15", "@BREAK", "@WAIT0.5", "@BREAK", "@WAIT100"])
for _w in ("10", "15", "20"):
    CASES[f"csave_w{_w}"] = prog('CSAVE"X"', [f"@WAIT{_w}"])


# STOP ALONE vs CTRL+STOP: an 8 KB BSAVE (~75 s of data at 1200 baud) with the
# key pressed from the Tcl prologue every 4 s from 20 s to 140 s emulated --
# wherever the RUN lands, presses land in the DATA.
BIG8 = 'BSAVE"CAS:X",&H8000,&H9FFF'
CASES["bsave8_stop"] = prog(BIG8, ["@WAIT120"])
CASES["bsave8_ctrlstop"] = prog(BIG8, ["@WAIT120"])
PRESS = {"bsave8_stop": ((7, 0x10),), "bsave8_ctrlstop": ((6, 0x02), (7, 0x10))}


def presses(keys):
    out = []
    for t0 in range(20, 141, 4):
        for row, mask in keys:
            out.append(f"after time {t0} {{ keymatrixdown {row} {mask} }}")
        for row, mask in keys:
            out.append(f"after time {t0 + 0.4} {{ keymatrixup {row} {mask} }}")
    return tuple(out)


def reading(machine, name):
    wav = probe_tmp.tmp(f"caswdiag_{name}_{machine[:6]}.wav")
    if os.path.exists(wav):
        os.remove(wav)
    raw = omsx_repl.run_cases(machine, [("direct", CASES[name])], batch=False,
                              reset=("", "SCREEN 0"),
                              prologue=(f"cassetteplayer new {{{wav}}}",)
                              + presses(PRESS.get(name, ())))[0] or ""
    flat = re.sub(r"\s+", " ", raw)
    tail = flat[-160:]
    return tail


def main():
    only = sys.argv[1:] or list(CASES)
    for n in only:
        for t, m in (("VG-8020", REF), ("OURS", OURS)):
            print(f"== {n:9s} {t:8s} ...{reading(m, n)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
