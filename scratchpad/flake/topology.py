#!/usr/bin/env python3
"""What process does the harness actually hold, and does its exit code mean
anything? A SIGKILLed emulator reported `exit 0`, which is either a wrapper in
the way or a `pkill` that missed -- and the answer decides whether `rc` belongs
in the diagnosis at all."""
import os, subprocess, sys, time, signal
sys.path.insert(0, "probes/lib")
import omsx_repl, omsx_preflight, tempfile

binary = omsx_repl.find_omsx(None)
out = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
tcl = out + ".tcl"
open(tcl, "w").write("set throttle off\nafter time 4000 { exit }\n")
cmd = [binary, "-machine", "C-BIOS_MSX1_EU_REPACK_DISK",
       "-command", "set renderer none; set sound_driver null", "-script", tcl]
proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, start_new_session=True)
print("direct child pid:", proc.pid)
time.sleep(3)
ps = subprocess.run(["ps", "-o", "pid,ppid,pgid,comm"], capture_output=True,
                    text=True).stdout
rows = [l for l in ps.splitlines() if "openmsx" in l.lower()]
print("processes matching openmsx:")
for r in rows:
    print("   ", r)
print("pgrep -x openmsx ->",
      subprocess.run(["pgrep", "-x", "openmsx"], capture_output=True,
                     text=True).stdout.split())
print("killing the DIRECT CHILD with SIGKILL ...")
os.kill(proc.pid, signal.SIGKILL)
print("proc.wait() ->", proc.wait())
for p in (out, tcl):
    try: os.unlink(p)
    except OSError: pass
