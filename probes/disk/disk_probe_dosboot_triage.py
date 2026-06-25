#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Boot-triage oracle: classify the DOS-boot end-state in ONE run.

The Tier-2 DOS-boot work keeps hitting the same handful of failure shapes, and
each one used to cost a fresh batch of ad-hoc probes to re-identify. This folds
that triage into a single instrument: boot, let it settle, sample (PC,SP) for a
window, and classify:

  OK     - control is back in the main BIOS (PC < $4000) with a healthy, stable
           stack: a booted MSX-DOS idling at its prompt/keyboard loop.
  STORM  - an interrupt vector ($0030-$003F) recurs while SP marches DOWN: an
           un-acked interrupt re-firing (the handler never clears its source).
           The $0038 jp-chain is auto-traced so the offending handler is named.
  SLIDE  - PC advances by +1 across most of the window: runaway execution
           sweeping memory as NOP-padding (derailed control transfer upstream).
  SPIN   - a small PC cycle with a stable stack, but OUTSIDE the main BIOS
           (e.g. stuck in our $Dxxx kernel): a poll whose exit never comes.

Black-box: PC/SP sampling + a jp-chain memory read of a booting proprietary DOS.
No disassembly of our ROM or of MSXDOS.SYS/COMMAND.COM.

    python3 probes/disk/disk_probe_dosboot_triage.py --dos-disk /tmp/dos.dsk
    python3 probes/disk/disk_probe_dosboot_triage.py --dos-disk /tmp/dos.dsk --stock
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
STOCK_MACHINE = "National_CF-3300"
OURS_MACHINE = "National_CF-3300_ZEROBASDISK"

MAIN_BIOS_TOP = 0x4000   # PC below this == back in the main BIOS (our ROM is $4000+)
HEALTHY_SP = 0xC000      # a booted DOS idles with its stack high in RAM


def run(machine: str, dsk: str, settle: float, n: int, timeout: float) -> list[str]:
    out = tempfile.mktemp(suffix=".cap")
    tcl_path = tempfile.mktemp(suffix=".tcl")
    tcl = f"""set throttle off
set renderer none
after time {settle:.1f} {{
  set ::seq {{}}
  debug set_condition {{1}} {{
    lappend ::seq [format "%04X %04X" [reg PC] [reg SP]]
    if {{[llength $::seq] >= {n}}} {{
      set f [open {{{out}}} w]
      # trace the maskable-interrupt jp-chain from $0038 (up to 5 hops)
      set a 0x0038
      for {{set h 0}} {{$h < 5}} {{incr h}} {{
        set op [debug read memory $a]
        if {{$op == 0xC3}} {{
          set t [expr {{[debug read memory [expr {{$a+1}}]] | ([debug read memory [expr {{$a+2}}]] << 8)}}]
          puts $f [format "CHAIN %04X: C3 -> %04X" $a $t]
          set a $t
        }} else {{
          puts $f [format "CHAIN %04X: %02X (not a jp; chain ends)" $a $op]
          break
        }}
      }}
      puts $f "SEQ"
      puts $f [join $::seq "\\n"]
      close $f
      exit
    }}
  }}
}}
after time [expr {{{settle:.1f} + 40}}] {{ set f [open {{{out}}} w]; puts $f "NO-SETTLE"; close $f; exit }}
"""
    open(tcl_path, "w").write(tcl)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        if not os.path.exists(out):
            sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit("no capture")
    lines = open(out).read().splitlines()
    os.unlink(out)
    os.unlink(tcl_path)
    return lines


def classify(seq: list[tuple[int, int]]) -> tuple[str, list[str]]:
    pcs = [p for p, _ in seq]
    sps = [s for _, s in seq]
    facts = []
    distinct = len(set(pcs))
    top, topn = Counter(pcs).most_common(1)[0]
    # period of the loop top
    idxs = [i for i, p in enumerate(pcs) if p == top]
    period = idxs[1] - idxs[0] if len(idxs) >= 2 else 0
    # SP trend over the window
    sp_drop = sps[0] - sps[-1]
    sp_min, sp_max = min(sps), max(sps)
    # linear-run fraction (PC == prev+1)
    lin = sum(1 for i in range(1, len(pcs)) if pcs[i] == (pcs[i - 1] + 1) & 0xFFFF)
    lin_frac = lin / max(1, len(pcs) - 1)
    # interrupt-vector recurrence ($0030-$003F)
    intvec = sum(1 for p in pcs if 0x0030 <= p <= 0x003F)

    facts.append(f"distinct PCs={distinct}  loop-top={top:04X} (x{topn}, period {period})")
    facts.append(f"PC range {min(pcs):04X}-{max(pcs):04X}  linear-frac={lin_frac:.2f}")
    facts.append(f"SP {sps[0]:04X}->{sps[-1]:04X} (drop {sp_drop:+d}, range {sp_min:04X}-{sp_max:04X})  "
                 f"int-vec hits={intvec}")

    if lin_frac > 0.5:
        return "SLIDE", facts
    if intvec > 0 and sp_drop > 64:
        return "STORM", facts
    if distinct < 200 and abs(sp_drop) <= 64:
        if top < MAIN_BIOS_TOP and sp_min >= HEALTHY_SP:
            return "OK", facts
        return "SPIN", facts
    return "MIXED", facts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", required=True)
    ap.add_argument("--stock", action="store_true")
    ap.add_argument("--machine")
    ap.add_argument("--settle", type=float, default=24.0)
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--timeout", type=float, default=160.0)
    args = ap.parse_args()
    machine = args.machine or (STOCK_MACHINE if args.stock else OURS_MACHINE)
    if not os.path.exists(args.dos_disk):
        sys.exit(f"DOS disk not found: {args.dos_disk}")
    work = tempfile.mktemp(suffix=".dsk")
    shutil.copy(args.dos_disk, work)
    lines = run(machine, work, args.settle, args.n, args.timeout)
    os.unlink(work)

    if lines and lines[0] == "NO-SETTLE":
        print(f"=== boot triage on {machine} ===\n  VERDICT: NO-SETTLE (never reached the sample window)")
        return 0
    chain = [ln for ln in lines if ln.startswith("CHAIN ")]
    seq = []
    in_seq = False
    for ln in lines:
        if ln == "SEQ":
            in_seq = True
            continue
        if in_seq and ln:
            a, b = ln.split()
            seq.append((int(a, 16), int(b, 16)))
    verdict, facts = classify(seq)

    # Post-storm fingerprint: a SLIDE whose frozen SP is parked just below the
    # $0038 jp-chain's first target is the AFTERMATH of an interrupt storm (the
    # un-acked IRQ marched SP down to the vector, then execution derailed).
    note = ""
    first_tgt = None
    if chain and "->" in chain[0]:
        first_tgt = int(chain[0].split("->")[1].strip(), 16)
    if verdict == "SLIDE" and first_tgt is not None:
        sp = seq[-1][1]
        if 0 <= (first_tgt - sp) < 0x40:
            note = (f"post-INTERRUPT-STORM: SP parked at {sp:04X} (= int vector "
                    f"{first_tgt:04X} - {first_tgt - sp}); an un-acked IRQ marched it here")

    print(f"=== boot triage on {machine} ({len(seq)} samples, settle {args.settle:g}s) ===")
    print(f"  VERDICT: {verdict}" + (f"  [{note}]" if note else ""))
    for f in facts:
        print(f"    {f}")
    if verdict in ("STORM", "SLIDE") or chain:
        print("  $0038 interrupt jp-chain:")
        for c in chain:
            print(f"    {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
