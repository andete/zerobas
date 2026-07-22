#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 arc-hang dynamic localizer. Inject the hanging CIRCLE(...,1.57,3.14) case on
the repack machine, then sample reg PC (spin location), log z80.acceptIRQ PC/SP
(interrupt interaction + stack drift), and read the GFX_* octant loop state. Tells
us: is it a true spin (and WHERE in the tenant), or an early return; and whether the
stack (SP) is drifting under the EI-window interrupts. No ROM disassembly."""
import os, sys, subprocess, tempfile, time, signal, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl as R

MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"
CASE = os.environ.get("ZB_CASE", "CIRCLE(60,60),15,15,1.57,3.14")   # arc_hpi_pi (hangs)
# tenant symbol map (from sub.sym) for interpreting PC
SYMS = [("gfx_plot_cur",0x18F9),("gfx_abs16",0x1A63),("gfx_circle_op",0x1B4A),
        ("gco_loop",0x1B4E),("gfx_circ_next",0x1B7F),("gco_emit8",0x1BBE),
        ("gfx_circ_emit_point",0x1C2F),("gfx_circ_scale",0x1C6E),
        ("gfx_circ_keep",0x1C8B),("gfx_cross_ge0",0x1CE4),("gfx_mul16u",0x1D31),
        ("gfx_neg16_bc",0x1D43),("END",0x1D60)]

def routine(pc):
    r = "?"
    for name, a in SYMS:
        if pc >= a: r = name
        else: break
    return r if 0x1800 <= pc <= 0x1D60 else ("<page0 other>" if pc < 0x4000 else "<not-tenant>")

def build_tcl(out):
    inj = (
        'proc __key {s} { set n [string length $s]\n'
        '  for {set i 0} {$i < $n} {incr i} {\n'
        f'    debug write memory [expr {{{R.KEYBUF} + $i}}] [scan [string index $s $i] %c] }}\n'
        f'  debug write memory {R.GETPNT} [expr {{{R.KEYBUF} & 0xFF}}]\n'
        f'  debug write memory [expr {{{R.GETPNT}+1}}] [expr {{({R.KEYBUF} >> 8) & 0xFF}}]\n'
        f'  set p [expr {{{R.KEYBUF} + $n}}]\n'
        f'  debug write memory {R.PUTPNT} [expr {{$p & 0xFF}}]\n'
        f'  debug write memory [expr {{{R.PUTPNT}+1}}] [expr {{($p >> 8) & 0xFF}}] }}\n'
        'proc __inj {s} { append s "\\r"; __key $s }\n')
    dump = (
        'proc __rd16 {a} { return [expr {[debug read memory $a] + 256*[debug read memory [expr {$a+1}]]}] }\n'
        'proc __blk {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }\n'
        'set ::pc {}\n'
        'set ::sp {}\n'
        'proc __samp {n} { if {$n<=0} { __dump; return }\n'
        '  lappend ::pc [format %04X [reg PC]];\n'
        '  if {[expr {$n % 40}]==0} { lappend ::sp [format %04X [reg SP]] }\n'
        '  after time 0.0008 "__samp [expr {$n-1}]" }\n'
        'set ::irq {}\n'
        'debug probe set_bp z80.acceptIRQ {} {\n'
        '  if {[llength $::irq] < 30} { lappend ::irq "[format %04X [reg PC]]/SP[format %04X [reg SP]]" } }\n'
        'proc __dump {} {\n'
        '  puts $::f "PCSAMPLES=[join $::pc ,]"\n'
        '  puts $::f "IRQ=[join $::irq ,]"\n'
        '  puts $::f "QX=[__rd16 0xE139] QY=[__rd16 0xE13B] QD=[__rd16 0xE13D] ARCF=[debug read memory 0xE12F] ARCBIG=[debug read memory 0xE138]"\n'
        '  puts $::f "SP=[format %04X [reg SP]] PC=[format %04X [reg PC]] SPtrend=[join $::sp ,]"\n'
        '  puts $::f "ARGA=[__blk 0xF06A 18]"\n'
        '  puts $::f "ARGB=[__blk 0xF07C 18]"\n'
        '  puts $::f "FAC=[__blk 0xF01C 8]"\n'
        '  flush $::f; close $::f; exit }\n')
    body = (
        "set throttle off\n"
        f"set ::f [open {{{out}}} w]\n" + inj + dump +
        # STORED mode (match the acceptance gate): 10 SCREEN2:<case> / RUN
        'after time 6.0 { __inj {10 COLOR15,1,1:SCREEN2:CLS} }\n'
        f'after time 6.6 {{ __inj {{20 {CASE}}} }}\n'
        'after time 7.2 { __inj {RUN} }\n'
        'after time 8.6 { __samp 400 }\n'      # sample AFTER RUN starts the case
        'after time 12.0 { catch {__dump} }\n')  # safety
    return body

def main():
    out = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
    tcl = out + ".tcl"
    open(tcl, "w").write(build_tcl(out))
    if os.path.exists(out): os.unlink(out)
    binary = R.find_omsx(None)
    cmd = [binary, "-machine", MACHINE, "-command", "set renderer none", "-script", tcl]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    dl = time.time() + 90
    while p.poll() is None and time.time() < dl: time.sleep(0.1)
    if p.poll() is None: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    txt = open(out).read() if os.path.exists(out) else ""
    print(f"CASE: {CASE}\n")
    for ln in txt.splitlines():
        if ln.startswith("PCSAMPLES="):
            pcs = ln[10:].split(",") if ln[10:] else []
            hist = collections.Counter(routine(int(x,16)) for x in pcs if x)
            print(f"PC spin histogram ({len(pcs)} samples):")
            for rt, n in hist.most_common(): print(f"   {n:4d}  {rt}")
            uniq = collections.Counter(pcs)
            print("  hottest raw PCs:", ", ".join(f"{pc}({n})" for pc,n in uniq.most_common(6)))
        elif ln.startswith("IRQ="):
            irqs = ln[4:].split(",") if ln[4:] else []
            print(f"\nIRQ acceptances ({len(irqs)}):", ", ".join(irqs[:12]))
            sps = [int(x.split("SP")[1],16) for x in irqs if "SP" in x]
            if sps: print(f"  SP range at IRQ: ${min(sps):04X}..${max(sps):04X} (drift {max(sps)-min(sps)} B)")
        else:
            print(ln)
    for f in (out, tcl):
        if os.path.exists(f): os.unlink(f)

if __name__ == "__main__": main()
