#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TOKOVF / D-TOKLAG: how long does each machine keep the frame interrupt
WAITING while BASIC takes typed program lines -- and, on zerobas, WHERE?

WHY. D-TOKOVF's bound (~52 T-states per crunched character, <1 ms a line)
turned geteject-acceptance red by TYPING damage (`NNEW`, `0 PUT 1,20`: a key
doubled, a key lost) and fdcdi d8 red; a never-executed 9 B pad in the same
place stayed green (scratchpad/tokovf_ab2.py --v4). A cost that small cannot
exhaust a throughput margin; it moves a PHASE. So the hypothesis is masked
windows during line entry long enough for a key event of openMSX `type` to
fall inside unseen. The C-BIOS keyboard scan runs in the frame interrupt.

HOW (clean room: openMSX's own probes, registers, slot state -- no ROM byte):
  VDP.IRQvertical rising  -> note the time, PC, IFF and the slot state
  z80.acceptIRQ           -> latency = now - that rise
The workload is geteject's `put` program typed exactly as that probe types it
(one `type` of NEW + the lines, no RUN), from t=16 s, recorded to t=60 s.
Latencies are bucketed; every latency over 5 ms is listed with its PC, which
is symbolised against this build's .sym files (lowercase labels = code).

Prediction: the VG-8020 / CF-3300 accept every frame within ~1 ms; zerobas
shows latencies of tens of ms clustered in the line-store path (a CALSLT under
DI around a sub-ROM tenant, or the store itself), and frames lost outright.
"""
import bisect, os, re, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_preflight, probe_tmp                   # noqa: E402
import disk_probe_geteject as ge                   # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINES = ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK",
            "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
# --fdcdi: the WRITE workload of fdcdi-acceptance instead (disk machines only),
# recorded from its start mark (&HD000 = 1) to its end mark (= 2)
FDCDI = "--fdcdi" in sys.argv
if FDCDI:
    MACHINES = MACHINES[:2]


def run(machine):
    out = probe_tmp.tmp(f"irqlat_{machine}{FDCDI}.txt")
    if os.path.exists(out):
        os.remove(out)
    def q(s):
        for a, b in (("\\", "\\\\"), ('"', '\\"'), ("$", "\\$"), ("[", "\\["), ("]", "\\]")):
            s = s.replace(a, b)
        return s
    typed = "".join(q(l) + "\\r" for l in ["NEW"] + ge.prog("put"))
    if FDCDI:
        # fdcdi-acceptance's workload: 200 PRINT # + CLOSE, nothing typed during
        # it -- the latencies of the WRITE path itself, from its start mark
        typed = ('open\\"big.txt\\" for output as #1:poke \\&hd000,1:for i=1 to 200:'
                 'print#1,\\"abcdefghijklmnopqrs\\":next:close#1:poke \\&hd000,2\\r')
    disk = machine in ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK")
    tcl = f'''set throttle off
set f [open {{{out}}} w]
set ::on 0
set ::rise -1
set ::n 0
proc rise {{}} {{
  if {{!$::on}} return
  if {{[debug probe read VDP.IRQvertical] != 1}} return
  set ::rise [machine_info time]
  set ::rpc [reg PC]
  set ::riff [reg iff]
  set ::rsl [debug read ioports 0xA8]
  set ::rss [expr {{255 - [debug read memory 0xFFFF]}}]
}}
proc acc {{}} {{
  if {{!$::on || $::rise < 0}} return
  incr ::n
  set lat [expr {{int(([machine_info time] - $::rise) * 1000000)}}]
  puts $::f "L $lat [format %04x $::rpc] $::riff [format %02x $::rsl] [format %02x $::rss]"
  set ::rise -1
}}
debug probe set_bp VDP.IRQvertical {{}} rise
debug probe set_bp z80.acceptIRQ {{}} acc
after time 12 {{ type "\\r" }}
after time 14 {{ debug write memory 0xD000 0; {"" if FDCDI else "type " + chr(34) + "SCREEN 0:WIDTH 40" + chr(92) + "r" + chr(34)} }}
after time {14.01 if FDCDI else 16} {{ set ::on {0 if FDCDI else 1}; set ::t0 [machine_info time]; type "{typed}"; mark }}
proc mark {{}} {{
  if {{{1 if FDCDI else 0} && !$::on && [debug read memory 0xD000] == 1}} {{ set ::on 1; set ::t0 [machine_info time] }}
  if {{{1 if FDCDI else 0} && $::on && [debug read memory 0xD000] == 2}} {{ puts $::f "N $::n [expr {{[machine_info time] - $::t0}}]"; close $::f; exit }}
  after time 0.02 mark
}}
after time {300 if FDCDI else 60} {{ puts $f "N $::n [expr {{[machine_info time] - $::t0}}]"; close $f; exit }}
'''
    tf = probe_tmp.tmp(f"irqlat_{machine}.tcl")
    open(tf, "w").write(tcl)
    cmd = [OMSX, "-machine", machine]
    if disk:
        dsk = probe_tmp.tmp(f"irqlat_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        cmd += ["-diska", dsk]
    cmd += ["-command", "set renderer none; set sound_driver null; set save_settings_on_exit false",
            "-script", tf]
    subprocess.run(omsx_preflight.guarded(cmd), capture_output=True, timeout=900)
    return open(out).read() if os.path.exists(out) else ""


def syms():
    tabs = {}
    for name, f in (("main", "basic-reloc.sym"), ("sub", "sub.sym"),
                    ("sub2", "sub2.sym"), ("disk", "disk.sym")):
        pairs = []
        for ln in open(os.path.join(REPO, "build", f)):
            m = re.match(r"([a-z_][a-z0-9_]*)\s+EQU\s+0?([0-9A-F]+)H", ln)
            if m:
                pairs.append((int(m.group(2), 16), m.group(1)))
        pairs.sort()
        tabs[name] = pairs
    return tabs


def where(tabs, pc, a8, ss):
    page = pc >> 14
    prim = (a8 >> (2 * page)) & 3
    sub = (ss >> (2 * page)) & 3
    rom = {0: "main"}.get(prim)
    if prim == 3:
        rom = {1: "disk", 2: "sub", 3: "sub2"}.get(sub, f"3-{sub}")
    if prim == 1 or prim == 2:
        rom = f"slot{prim}"
    pairs = tabs.get(rom)
    if not pairs or pc >= 0xC000:
        return f"{rom or prim}:{pc:04X}" if pc < 0xC000 else f"RAM:{pc:04X}"
    i = bisect.bisect_right(pairs, (pc, "~")) - 1
    if i < 0:
        return f"{rom}:{pc:04X}"
    return f"{rom}:{pairs[i][1]}+{pc - pairs[i][0]}"


def main():
    tabs = syms()
    zb = lambda m: m.startswith("C-BIOS")
    for m in MACHINES:
        raw = run(m)
        lat = [l.split() for l in raw.splitlines() if l.startswith("L ")]
        tail = [l for l in raw.splitlines() if l.startswith("N ")]
        if not lat:
            print(f"=== {m}: NO READING")
            continue
        us = [int(l[1]) for l in lat]
        frames = float(tail[0].split()[2]) * 50 if tail else 0
        b = [sum(1 for x in us if lo <= x < hi) for lo, hi in
             ((0, 1000), (1000, 5000), (5000, 20000), (20000, 10**9))]
        print(f"=== {m}: {len(us)} accepted in ~{frames:.0f} frames; "
              f"max {max(us)} us; <1ms {b[0]}  1-5ms {b[1]}  5-20ms {b[2]}  >=20ms {b[3]}")
        if zb(m):
            big = sorted(((int(l[1]), l[2], l[3], l[4], l[5]) for l in lat if int(l[1]) >= 5000),
                         reverse=True)
            agg = {}
            for x, pc, iff, a8, ss in big:
                k = where(tabs, int(pc, 16), int(a8, 16), int(ss, 16))
                c, mx = agg.get(k, (0, 0))
                agg[k] = (c + 1, max(mx, x))
            for k, (c, mx) in sorted(agg.items(), key=lambda kv: -kv[1][1])[:25]:
                print(f"     {c:4d}x  max {mx:6d} us  PC at the rise: {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
