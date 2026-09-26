"""D-RIGFW: why `onstrig_rig` read 0 on both machines, measured on the VG-8020.

The board PULSES trigger 1 (rigfw.Pulser, ~2 Hz) around one boot-per-case run
with rigfw.prologue("pulse+trig1") -- which turns openMSX's throttle back ON.
  A  counts STRIG(1) transitions in a 120-frame wait (presses land in the run)
  B  ON STRIG GOSUB 60,80 + STRIG(1) ON: trigger 1 is list slot 1 -> 2
  C  ON STRIG GOSUB ,60: the only handler, in slot 1 -> 7
Unthrottled (the harness default) A read 0 and the whole run took 1.8 s of
wall time: a frame wait passes in milliseconds and no press can land in it.
Usage: ZEROBAS_REFCACHE=0 rigfw_trap_probe.py [machine]   (default Philips_VG_8020)
⚠️ Run it with the reference cache OFF: a cache hit replays the stored answer
without booting, and the pulser then reports `presses 0` beside real values.
"""
import sys
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, rigfw
port = rigfw.find(); assert port
M = sys.argv[1] if len(sys.argv) > 1 else "Philips_VG_8020"
CASES = [
 ("A", 'C=0:P=0:T=TIME:W$="WWWWWWWWWWWWWWWWWWWWWWWWWW":Q=STRIG(1):IF Q<>P THEN C=C+1:P=Q:V$="VVVV":IF TIME-T<120 THEN 20:PRINT"[9a";C;"]"'),
 ("B", 'C=0:ON STRIG GOSUB 60,80:STRIG(1) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<600 THEN 40:PRINT"[9b";C;"]":END:W$="WWWWWWWWWWW":C=1:RETURN:U$="UUUUUUUUUUUUUUUUUUUUUUUUUUU":C=2:RETURN'),
 ("C", 'C=0:ON STRIG GOSUB ,60:STRIG(1) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<600 THEN 40:PRINT"[9c";C;"]":END:W$="WWWWWWWWWWW":C=7:RETURN'),
]
for k, line in CASES:
    print(k, omsx_repl.as_stored(line))
rigfw.set_state(port, "centre")
with rigfw.Pulser(port, ("trig1",)) as p:
    got = omsx_repl.run_cases(M, [("stored", omsx_repl.as_stored(l)) for _k, l in CASES], batch=False,
                              prologue=rigfw.prologue("pulse+trig1"),
                              reset=("NEW", "CLS"), capture="screen", boot=10.0)
print("presses", p.presses)
import re
for (k, _), g in zip(CASES, got):
    print(k, re.findall(r"\[9[abc][^\"]{0,10}\]", "".join((g or "").split("\n"))) or (g or "")[-200:])
