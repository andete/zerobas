#!/usr/bin/env python3
"""D-DISKCONTRACT gap 11 (2026-11-17): BDOSXT measured -- SDATE SAME, STIME's range check
MISSING (filed D-STIMERANGE, TIER 6). Gate BDOSXT with the 4 STIME bytes pinned at ours.
Refuses on a bad anchor."""
import sys


def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)}: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))


G = "probes/disk/disk_bdos_acceptance.py"
edit(G, '''    ("BDOSXE", "build_bdosxe_disk.py"),
''', '''    ("BDOSXE", "build_bdosxe_disk.py"),
    # BDOSXT (D-DISKCONTRACT gap 11, 2026-11-17): SDATE / STIME with valid and invalid input,
    # each read back by GDATE / GTIME -- 13 ten-byte rows.
    ("BDOSXT", "build_bdosxt_disk.py"),
''')
edit(G, '''    "BDOSX8": {
        # Item 5''', '''    "BDOSXT": {
        # D-STIMERANGE (TODO, TIER 6): STIME takes any time -- A = 0 where the CF-3300
        # answers $FF for hour 25, minute 60, second 60 and hundredths 100. OURS pinned
        # (scratchpad/XT_stock.out, XT_ours.out).
        0x0392: (0x00, "row 8 STIME 25:00:00's A (D-STIMERANGE; the CF-3300 $FF)"),
        0x039C: (0x00, "row 9 STIME 12:60:00's A (D-STIMERANGE)"),
        0x03A6: (0x00, "row 10 STIME 12:34:60's A (D-STIMERANGE)"),
        0x03B0: (0x00, "row 11 STIME hundredths 100's A (D-STIMERANGE)"),
    },
    "BDOSX8": {
        # Item 5''')
open("tools/probe-reach-allow.txt", "a").write(
    "build_bdosxt_disk  ⚠️ RUN BY bdos-acceptance (its EXERCISERS list, 2026-11-17 D-DISKCONTRACT gap 11) -- by "
    "name, which this check does not follow; it needs `--dos-disk`, a real MSX-DOS image the repo does not ship.\n")

T = "TODO.md"
edit(T, '''      💰 **D-DISKCARVE6 STEP 1 (2026-11-17): a 61 B hole at $7568''', '''      🔴 **(11) SDATE / STIME INVALID INPUT, 2026-11-17 -- STIME's RANGE CHECK MISSING, FILED D-STIMERANGE.** New exerciser
      BDOSXT (probes/disk/bdosxt.asm, in bdos-acceptance): 13 cases, each followed by GDATE / GTIME. SDATE is the SAME on
      every row (valid 0; month 13, Feb 30, 1979, 2100, month 0 all $FF and the date kept; the leap day valid). STIME:
      the CF-3300 answers $FF for hour 25, minute 60, second 60, hundredths 100; ours 0 every time
      ([`XT_stock.out`](scratchpad/XT_stock.out), [`XT_ours.out`](scratchpad/XT_ours.out)). Those 4 bytes are pinned at ours in the gate. 🔮 "the CF-3300 keeps the time STIME set": MISS --
      its GTIME reads 00:00:00 throughout, as ours (no clock on an MSX1). Left: (12) VERIFY, (5) Ctrl-P / C / S, (6) > $30.
      💰 **D-DISKCARVE6 STEP 1 (2026-11-17): a 61 B hole at $7568''')
edit(T, '''- [ ] **D-SLACK — A NEW FILE'S NEVER-WRITTEN RECORDS HOLD DIFFERENT GARBAGE**''', '''- [ ] **D-STIMERANGE — BDOS STIME TAKES ANY TIME: A = 0 WHERE THE CF-3300 ANSWERS $FF FOR AN OUT-OF-RANGE ONE**
      🎚️ TIER 6 — every error (a program passing hour 25 / minute 60 / second 60 / hundredths 100; filed 2026-11-17).
      🤖 **AUTONOMOUS** — BDOSXT in bdos-acceptance, its 4 STIME bytes pinned at ours (D-DISKCONTRACT gap 11:
      [`XT_stock.out`](scratchpad/XT_stock.out), [`XT_ours.out`](scratchpad/XT_ours.out)). stime_body ($4E7E) is `xor a / ld b,h / ld c,l / ret`; the fix checks H < 24,
      L < 60, D < 60, E < 100 -> else A = $FF (~+20 B; the clock itself keeps nothing on either machine). Bytes: the disk
      ROM's hole has 2 B -- after D-DOSDRVB's parts (TIER 3) in the next carve. When it lands, drop the 4 pins.

- [ ] **D-SLACK — A NEW FILE'S NEVER-WRITTEN RECORDS HOLD DIFFERENT GARBAGE**''')
print("ok")
