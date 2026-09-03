#!/usr/bin/env python3
r"""D-HOOKDIFF — WHICH BASIC hooks does a disk ROM actually install?

🧭 Joost, 2026-09-03: the disk keywords' implementation "should probably be in
the disk rom ... and work via the officially documented hooks". Before any of
that is built, the hook SET has to be established — and it must not come from
recall.

🎯 IT IS MEASURABLE WITHOUT ANY DOCUMENT. The MSX BASIC hooks are RAM cells that
a cartridge's INIT fills in at boot. So: read the hook region on a machine with
NO disk ROM (Philips VG-8020) and on one WITH (National CF-3300), and the cells
that DIFFER are exactly the hooks disk BASIC claims. That is an observation of an
interface boundary -- the same class as the already-published HPHYD -> DSKIO
vector this project documents -- and needs no disassembly of anything.

⚠️ WHAT THIS DOES *NOT* DO. It reads the hook CELLS (which hooks are claimed),
never the code they point INTO. The target addresses are printed as addresses
only, because "which slot/where" is interface information; the bodies behind them
are reference ROM and stay untouched. Nothing here is derived from stock code.

🟢 CONTROLS. `zb-disk` and `zb-nodisk` are read too: zerobas installs NO BASIC
hooks today (it reaches files through the BDOS SYSTEM vector instead), so its two
builds should differ from each other in FAR fewer cells than the references do --
and that difference is the size of the gap this migration has to close.

The published hook region is $FD9A..$FFE7 (MSX Technical Handbook system-hook
table). Each hook is 5 bytes: either `C9 ...` (RET = unclaimed) or a jump/call
stub installed by a cartridge.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

HOOK_LO, HOOK_HI = 0xFD9A, 0xFFE7          # published system-hook region
STRIDE = 5                                  # 5 bytes per hook slot

SIDES = {
    "vg8020":    ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300":    ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb-disk":   ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW",)),
    "zb-nodisk": ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0, ("NEW",)),
}


def read_hooks(side):
    """PEEK the hook region in chunks, via a BASIC loop that prints hex bytes."""
    machine, boot, reset = SIDES[side]
    out = {}
    # 🔴 ROUND 1 USED step=64 AND WAS 90% BLIND. 64 bytes prints as 128 hex
    # characters, and SCREEN 0 is 40 columns -- so every chunk wrapped across
    # several screen lines and the single-line `<...>` fence could not match it.
    # Nine of ten chunks per side returned NOTHING, and the only one that worked
    # was the short final chunk (6 bytes). It still printed a verdict -- "3 hooks
    # claimed" -- off a table that was almost entirely absent, which is exactly
    # the shape of an instrument handing back a plausible answer from an input it
    # misread. 16 bytes = 32 characters, comfortably inside one line.
    step = 16
    for base in range(HOOK_LO, HOOK_HI + 1, step):
        n = min(step, HOOK_HI + 1 - base)
        prog = ['10 ON ERROR GOTO 90', '20 PRINT"<";',
                f'30 FOR I=0 TO {n - 1}',
                f'40 A=PEEK({base}+I):PRINT RIGHT$("0"+HEX$(A),2);',
                '50 NEXT', '60 PRINT">":END', '90 PRINT"<ERR";ERR;">"', 'RUN']
        raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                                  batch=False, reset=(), boot=boot, step=5.0,
                                  cap_gap=12.0, timeout=300.0)[0] or ""
        m = re.findall(r"<([0-9A-Fa-f]*)>", "".join(raw))
        hexs = m[-1] if m else ""
        if len(hexs) != n * 2:
            print(f"  🔴 {side} ${base:04X}: got {len(hexs)//2} of {n} bytes"
                  " -- THIS CHUNK IS UNREAD, not zero")
        for i in range(min(n, len(hexs) // 2)):
            out[base + i] = int(hexs[i * 2:i * 2 + 2], 16)
    return out


sides = (sys.argv[1] if len(sys.argv) > 1
         else "vg8020,cf3300,zb-disk,zb-nodisk").split(",")
data = {}
for s in sides:
    print(f"reading {s} ...")
    data[s] = read_hooks(s)

print(f"\nhook region ${HOOK_LO:04X}..${HOOK_HI:04X}, {STRIDE} B per slot\n")
print(f"{'slot':>8}  " + "  ".join(f"{s:>14}" for s in sides) + "   verdict")
claimed = []
for base in range(HOOK_LO, HOOK_HI + 1, STRIDE):
    cells = {}
    for s in sides:
        b = [data[s].get(base + k) for k in range(STRIDE)]
        cells[s] = "".join("??" if x is None else f"{x:02X}" for x in b)
    ref_differs = ("vg8020" in cells and "cf3300" in cells
                   and cells["vg8020"] != cells["cf3300"])
    zb_differs = ("zb-disk" in cells and "zb-nodisk" in cells
                  and cells["zb-disk"] != cells["zb-nodisk"])
    if not (ref_differs or zb_differs):
        continue
    tag = []
    if ref_differs:
        tag.append("DISK ROM CLAIMS IT"); claimed.append(base)
    if zb_differs:
        tag.append("zerobas differs too")
    print(f"  ${base:04X}  " + "  ".join(f"{cells[s]:>14}" for s in sides)
          + "   " + " / ".join(tag))
miss = sum(1 for s_ in sides
           for a in range(HOOK_LO, HOOK_HI + 1) if data[s_].get(a) is None)
if miss:
    print(f"\n🔴 {miss} CELL(S) UNREAD ACROSS ALL SIDES -- the table below is "
          "INCOMPLETE and no hook verdict from it is usable. Fix the readout "
          "before reading the result.")
print(f"\nhooks the reference disk ROM claims: {len(claimed)}"
      + ("  ⚠️ UNRELIABLE: see the unread-cell count above" if miss else ""))
print("  " + " ".join(f"${a:04X}" for a in claimed))
print("done")
