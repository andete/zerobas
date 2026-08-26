#!/usr/bin/env python3
"""Reproduce the shared-`settings.xml` race, and A/B the fix.

🔴 DRAFT 1 OF THIS FILE CAME BACK 0/96 ON BOTH ARMS -- a falsification with no
teeth, which is a claim about the EXPERIMENT before it is one about the code.
It started N processes in synchronised waves, so they all READ at the same
moment and all REWROTE at the same moment; the dangerous overlap is a START
against somebody else's EXIT, which waves never produce. Waiting for the real
coincidence is hopeless arithmetic too: the battery shows roughly one event in
~2500 starts, so observing five needs ~12 500 starts per arm.

🎯 SO DRIVE THE MECHANISM INSTEAD OF WAITING FOR IT. A writer thread rewrites
the shared settings file NON-ATOMICALLY, exactly as openMSX does on exit, while
processes start against it. That makes the window wide instead of rare, and the
fix does not depend on the rate: isolation removes the shared file from the
read path altogether.

⚠️ THE USER'S OWN `~/.openMSX/share/settings.xml` IS NEVER TOUCHED. Both arms
run against a COPY in a temp dir -- arm A shares that copy (today's behaviour),
arm B gives each process its own (the fix).

🔴 DRAFT 2 WAS WORSE THAN DRAFT 1, AND IT PASSED. Its ISOLATED arm copied from
the PRISTINE source while the writer tore a different file -- so it exercised a
fix that had not been written, reported 0/40, and the real code (which copies
from the file being torn) went on to flake twice in the next battery. **A
falsification must call the code, not a model of it.** Arm B now goes through
`omsx_repl._settings_read()` itself, pointed at the torn file, so the two can
never diverge again.
"""
import concurrent.futures as cf, os, shutil, subprocess, sys, tempfile, threading, time
sys.path.insert(0, "probes/lib")
import omsx_repl

BIN = omsx_repl.find_omsx(None)
MACH = "C-BIOS_MSX1_EU_REPACK_DISK"
SRC = omsx_repl.OMSX_SETTINGS
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
TMP = tempfile.mkdtemp(prefix="zb_flake_")
SHARED = os.path.join(TMP, "settings.xml")
shutil.copyfile(SRC, SHARED)
BODY = open(SRC).read()

stop = threading.Event()


def torn_writer():
    """What openMSX does on exit: rewrite the file in place, not atomically."""
    while not stop.is_set():
        with open(SHARED, "w") as f:
            for chunk in (BODY[i:i + 64] for i in range(0, len(BODY), 64)):
                f.write(chunk)
                f.flush()
                time.sleep(0.0005)
        time.sleep(0.002)


def one(isolated, i):
    tcl = os.path.join(TMP, f"r{i}.tcl")
    open(tcl, "w").write("set throttle off\nafter time 2 { exit }\n")
    st = SHARED
    if isolated:
        # 🔴 THROUGH THE REAL CODE, and pointed at the file being TORN -- which
        # is what the shipped path actually reads.
        omsx_repl.OMSX_SETTINGS = SHARED
        blob = omsx_repl._settings_read()
        if blob is None:
            # 🔴 AND THIS BRANCH IS WHY 0/40 COULD BE VACUOUS. If validation
            # never succeeded, arm B would omit the flag every time and report a
            # perfect score for a fix it never exercised. COUNT IT.
            return 0, "__FELLBACK__"
        st = tcl + ".settings.xml"
        open(st, "w").write(blob)
    cmd = [BIN, "-machine", MACH, "-setting", st,
           "-command", "set renderer none; set sound_driver null", "-script", tcl]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if isolated:
        try: os.unlink(st)
        except OSError: pass
    msg = ""
    if p.returncode:
        blob = (p.stdout + p.stderr).strip().splitlines()
        msg = blob[0][:120] if blob else "(no message)"
    return p.returncode, msg


print(f"a writer is tearing {SHARED} while {N} starts race it, per arm\n")
w = threading.Thread(target=torn_writer, daemon=True)
w.start()
try:
    for label, isolated in (("SHARED   (today)", False),
                            ("ISOLATED (the fix)", True)):
        bad, msgs, fell = 0, {}, 0
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for rc, msg in ex.map(lambda i: one(isolated, i), range(N)):
                if msg == "__FELLBACK__":
                    fell += 1
                    continue
                if rc:
                    bad += 1
                    msgs[msg] = msgs.get(msg, 0) + 1
        print(f"{label:20}  {bad:3d} / {N} starts FAILED ({100.0*bad/N:5.1f}%)"
              + (f"   [{fell} read(s) never validated -> flag omitted; those "
                 f"prove NOTHING]" if fell else
                 ("   [every read validated -- the score is not vacuous]"
                  if isolated else "")))
        for m, c in sorted(msgs.items(), key=lambda kv: -kv[1]):
            print(f"                        {c:3d}x  {m}")
finally:
    stop.set()
    w.join(timeout=2)
    shutil.rmtree(TMP, ignore_errors=True)
