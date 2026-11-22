#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""play_trace -- the background music player, black-box: probes/bios/play/xplay1.asm on each machine named, every
PSG write and every frame logged, printed as one line per frame per scenario.

    python3 -u probes/bios/play_trace.py [MACHINE ...]      (default: Philips_VG_8020, C-BIOS_MSX1_EU_REPACK_NODISK)
    python3 -u probes/bios/play_trace.py --compare A B      exit 1 when A's and B's traces differ (scenario by scenario)

A frame line: `f<k>  [MUSICF PLYCNT | words A B C | put/get A B C]  writes`. The state is read when the VDP raises
its frame interrupt (before that frame's service); the writes are those made from that moment until the next one,
as `R<reg>=<value>` in order. Frame 0 is the first frame interrupt after the scenario's SCEN write.
CLEAN-ROOM: only our program's effects are read: PSG port writes (an openMSX I/O watch) and work-area RAM.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import omsx_preflight  # noqa: E402
import openmsx_paths  # noqa: E402
import probe_tmp  # noqa: E402,F401

ASM = os.path.join(HERE, "play", "xplay1.asm")
STATE = "0xFB3F 2 0xFB41 2 0xFB66 2 0xFB8B 2 0xF959 2 0xF95F 2 0xF965 2"


def build(td):
    rom = os.path.join(td, "xplay1.rom")
    r = subprocess.run(["pasmo", "--bin", ASM, rom], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"pasmo failed:\n{r.stdout}{r.stderr}")
    return rom


def run(machine, rom, td, timeout=60):
    log = os.path.join(td, machine + ".log")
    tcl = os.path.join(td, machine + ".tcl")
    snap = " ".join(f"[debug read_block memory {a} {n}]" for a, n in
                    zip(STATE.split()[::2], STATE.split()[1::2]))
    open(tcl, "w").write(
        "set throttle off\n"
        f"set ::log [open {{{log}}} w]\n"
        "set ::preg 0\n"
        "debug set_watchpoint write_io 0xA0 {} {set ::preg $::wp_last_value}\n"
        "debug set_watchpoint write_io 0xA1 {} {puts $::log \"W [machine_info time] $::preg $::wp_last_value\"}\n"
        "debug set_watchpoint write_mem 0xE010 {} {puts $::log \"S [machine_info time] $::wp_last_value\"}\n"
        "debug set_watchpoint write_mem 0xE013 {} {puts $::log \"G [machine_info time] $::wp_last_value\"}\n"
        "proc frm {} {\n"
        "  if {[debug probe read VDP.IRQvertical] == 0} return\n"
        f"  binary scan [string cat {snap}] H* v\n"
        "  puts $::log \"F [machine_info time] $v\"\n}\n"
        "debug probe set_bp VDP.IRQvertical {} frm\n"
        "proc poll {} {\n"
        f"  if {{[debug read memory 0xE000] == 0xA5 || [machine_info time] > {timeout}}} {{\n"
        "    puts $::log \"END [debug read memory 0xE000]\"; close $::log; exit\n  }\n"
        "  after time 0.2 poll\n}\n"
        "after time 1 poll\n")
    subprocess.run(omsx_preflight.guarded(
        [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-cart", rom,
         "-command", "set renderer none; set sound_driver null", "-script", tcl]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    return open(log).read().splitlines() if os.path.exists(log) else None


def frames(lines):
    """{scenario: [("pre", writes after STRTMS before frame 0), (state hex, writes), ...]}: frame 0 = the first frame
    interrupt after the GO write; R14 / R15 (the joystick port, the BIOS's own scan) are left out"""
    out, scen, cur = {}, None, None
    for ln in lines:
        p = ln.split()
        if p[0] == "S":
            scen, cur = int(p[2]), None
        elif p[0] == "G" and scen and int(p[2]) == scen and scen < 100:
            out[scen] = [("pre", [])]
            cur = out[scen][-1][1]
        elif p[0] == "F" and cur is not None:
            out[scen].append((p[2], []))
            cur = out[scen][-1][1]
        elif p[0] == "W" and cur is not None and int(p[2]) < 14:
            cur.append((int(p[2]), int(p[3])))
    return out


def fmt_state(h):
    if h == "pre":
        return "pre (right after STRTMS)"
    b = bytes.fromhex(h)
    w = [b[2] | b[3] << 8, b[4] | b[5] << 8, b[6] | b[7] << 8]
    return (f"M{b[0]:02X} P{b[1]} | w {w[0]:4} {w[1]:4} {w[2]:4} | q "
            f"{b[8]:02X}/{b[9]:02X} {b[10]:02X}/{b[11]:02X} {b[12]:02X}/{b[13]:02X}")


def show(machine, fr):
    print(f"===== {machine} =====")
    for s in sorted(fr):
        print(f"-- scenario {s}")
        for k, (st, w) in enumerate(fr[s]):
            ws = " ".join(f"R{r}={v:02X}" for r, v in w)
            print(f"  f{k - 1:<3} {fmt_state(st):48} {ws}")


def main(argv):
    td = tempfile.mkdtemp(prefix="play_trace_")
    rom = build(td)
    cmp = argv[:1] == ["--compare"]
    ms = (argv[1:] if cmp else argv) or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]
    res = {}
    for m in ms:
        lines = run(m, rom, td)
        if not lines or lines[-1] != "END 165":
            print(f"NO READING on {m} ({lines[-1] if lines else 'no log'})")
            return 2
        res[m] = frames(lines)
        show(m, res[m])
    if cmp:
        a, b = (res[m] for m in ms[:2])
        bad = 0
        for s in sorted(set(a) | set(b)):
            sa, sb = a.get(s, []), b.get(s, [])
            if sa != sb:
                bad += 1
                k = next((i for i in range(min(len(sa), len(sb))) if sa[i] != sb[i]), min(len(sa), len(sb)))
                print(f"DIFF scenario {s}: first at f{k - 1}: {ms[0]} {sa[k] if k < len(sa) else '-'}  "
                      f"{ms[1]} {sb[k] if k < len(sb) else '-'}")
        print(f"===== play_trace: {'SAME' if not bad else f'{bad} scenario(s) DIFFER'} =====")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
