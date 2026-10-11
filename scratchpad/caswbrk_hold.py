#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASWBRK: what happens to a Ctrl-STOP STILL HELD when a broken tape write
reaches its ON ERROR handler? The VG-8020 printed `[E 19 15 ..]`; zerobas, with
the write now broken, read `Break in 90` -- the held key broke the handler.

Ctrl-STOP is pressed `HOLD_LEAD` s after RUN (inside a 2 KB BSAVE's data) and
held `HOLD` s (an `@BREAK` with the harness's BREAK_HOLD raised; a first cut
through `holds=` released the key BEFORE pressing it -- hold_lead > hold_secs). A watchpoint logs the emulated time of every cassette edge
(PPI $AB BSR 0x0A/0x0B) and every VDP data write ($98). Read:
  t_abort  the last cassette edge (the write stopped)
  t_vdp    the first VDP write after it (the handler printing)
so t_vdp - t_abort ~ 0 means the handler ran with the key still down, ~HOLD
that it waited for the release. The screen says what the handler did.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

REF = "Philips_VG_8020"
OURS = os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
HOLD_LEAD = 12.0
HOLD = float(os.environ.get("CASWHOLD_HOLD", "6.0"))
CASE = ["NEW", "10 ON ERROR GOTO 90", '15 BSAVE"CAS:X",&H8000,&H87FF',
        '30 PRINT"[N]":END',
        '90 PRINT"[E";ERR;ERL;"]":T=TIME:FOR I=1 TO 300:NEXT:PRINT"[X";TIME-T;"]":END',
        "RUN", f"@WAIT{HOLD_LEAD}", "@BREAK", "@WAIT12"]
omsx_repl.BREAK_HOLD = HOLD        # the @BREAK pair held HOLD s (harness default 0.4)


def run(machine):
    wav = probe_tmp.tmp(f"caswhold_{machine[:6]}.wav")
    log = probe_tmp.tmp(f"caswhold_{machine[:6]}.log")
    for p in (wav, log):
        if os.path.exists(p):
            os.remove(p)
    pro = (f"cassetteplayer new {{{wav}}}",
           f"set ::cst [open {{{log}}} w]",
           "fconfigure $::cst -buffering line",
           "debug set_watchpoint write_io 0xAB {} "
           "{if {$::wp_last_value == 10 || $::wp_last_value == 11} "
           "{puts $::cst \"C [machine_info time]\"}}",
           "debug set_watchpoint write_io 0x98 {} "
           "{puts $::cst \"V [machine_info time]\"}",
           # ⚠️ NOT a `rename keymatrixdown` wrapper to timestamp the keys: tried,
           # and the presses then never reached either machine (both wrote to
           # the end). The key times are the harness's schedule: with
           # BREAK_HOLD = h, CTRL down at T, STOP down T+0.5, STOP up T+1.0+h,
           # CTRL up T+1.5+h.
           # INTFLG ($FC9B): the interrupt's Ctrl-STOP latch (work-area RAM)
           "debug set_watchpoint write_mem 0xFC9B {} "
           "{puts $::cst \"I [machine_info time] $::wp_last_value\"}")
    raw = omsx_repl.run_cases(machine, [("direct", CASE)], batch=False,
                              reset=("", "SCREEN 0"), prologue=pro,
                              cap_gap=4.0)[0] or ""
    ev = []
    if os.environ.get("CASWHOLD_KEEP"):
        import shutil
        shutil.copy(log, os.environ["CASWHOLD_KEEP"] + f".{machine[:6]}.log")
    for ln in open(log):
        p = ln.split()
        if len(p) == 2:
            ev.append((p[0], float(p[1])))
        elif len(p) == 3 and p[0] == "I":
            ev.append((f"I={p[2]}", float(p[1])))
        elif len(p) == 3 and p[0] == "K":
            ev.append((f"K{p[2]}", float(p[1])))
    cas = [t for k, t in ev if k == "C"]
    t_abort = cas[-1] if cas else None
    after = [t for k, t in ev if k == "V" and t_abort is not None and t > t_abort]
    t_vdp = after[0] if after else None
    flat = re.sub(r"\s+", " ", raw)
    tail = flat[flat.rfind("RUN"):] if "RUN" in flat else flat[-120:]
    if os.environ.get("CASWHOLD_RAW"):
        print(raw)
    gap = None if t_vdp is None else round(t_vdp - t_abort, 3)
    if t_abort is not None:
        near = [(k, round(t - t_abort, 4)) for k, t in ev
                if (k.startswith("I=3") or k.startswith("K"))
                and -2.0 < t - t_abort < 3.0]
        tail += f"  INTFLG writes (s from abort): {near}"
    return t_abort, gap, tail


def main():
    for name, m in (("VG-8020", REF), ("OURS", OURS)):
        t_abort, gap, tail = run(m)
        print(f"== {name:8s} t_abort={t_abort} vdp_after_abort={gap}s  screen: {tail}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
