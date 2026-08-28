#!/usr/bin/env python3
r"""K-CT-FR3: re-create D-FNRUN's knife and check castail-acceptance SCORES it.

The item (TODO.md, filed 2026-08-21) says castail-acceptance "cannot score its own
knives": K-FR3 cut `dr_cas_close`'s `ld hl,(FN_RESUME)` -> `ld hl,(STRPTR)`,
`cas-run-hit` went `ZQ9` -> `<load-failed>`, and because that row is a POSITIVE
CONTROL the probe printed "33 printed, 0 scored -- NOT MEASURED" and exited 2.

D-CASTAILCTL limits the fatal control check to REFERENCE sides. This re-runs the
founding knife to show the probe now SCORES the break instead of voiding the run.
The knife is not tracked anywhere, so it is re-created here rather than cited.

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): the original is held IN MEMORY and put
back by try/finally AND atexit, so a kill between the write and the restore cannot
leave the tree cut and invisible to the ROM-hash guard.
"""
import atexit, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM: prove the cut reached the ROM

SRC = "basic/cload.asm"
# 🔴 THE INSTRUCTION ALONE IS NOT THE SITE. `ld hl,(FN_RESUME) ; D-FNRUN: resume
# past the EXPRESSION` appears TWICE in this file -- the DISK path (:231, whose
# comment continues `--`) and the cassette path -- so the bare line matched both as
# a prefix and the guard refused to cut. Anchored on the LABEL, which is what makes
# it dr_cas_close's. [[a-shared-tail-is-not-a-decision]]
OLD = ("dr_cas_close:\n"
       "                ld      hl,(FN_RESUME)      ; D-FNRUN: resume past the EXPRESSION")
NEW = ("dr_cas_close:\n"
       "                ld      hl,(STRPTR)         ; K-CT-FR3 CUT (restored on exit)")


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def main():
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print(f"KNIFE BROKEN: anchor not unique in {SRC} ({orig.count(OLD)})")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    # 🔴 NOT `os.environ["TMPDIR"]` -- on macOS that is the per-user
    # /var/folders/... directory and the first cut leaked this knife's logs there,
    # outside the one temp root everything zerobas writes lives under (D-TEMPROOT).
    tmp = "/tmp/zerobas"
    os.makedirs(tmp, exist_ok=True)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        print("K-CT-FR3 planted; rebuilding...")
        _before = knife_guard.hashes()
        _moved, _after, _rc = knife_guard.build(f"{tmp}/ctknife_build.out", _before)
        print(knife_guard.report("K-CT", _moved, _before, _after))
        if not _moved and not _rc:
            print("  -> refusing to score an INERT cut"); return 1
        if _rc:
            print("BUILD FAILED with the knife in -- see ctknife_build.out")
            return 2
        rc = sh("make castail-acceptance", f"{tmp}/ctknife_probe.out")
    finally:
        restore()
        atexit.unregister(restore)
    sh("make repack-machine", f"{tmp}/ctknife_restore.out")

    out = open(f"{tmp}/ctknife_probe.out", errors="replace").read()
    scored = "NOT MEASURED" not in out
    print(f"\ncastail-acceptance rc={rc}")
    for line in out.splitlines():
        if "ROWS:" in line or "scored readings" in line or "NOT MEASURED" in line:
            print("   ", line.strip()[:110])
    print()
    print("  VERDICT:", "SCORED the knife (the fix works)" if scored
          else "🔴 STILL VOIDED THE RUN -- the fix did not take")
    print("  (the rc above is MAKE's -- GNU make exits 2 on any failed target. The"
          " PROBE's\n   own exit is what carries the meaning: 2 = instrument broken,"
          " 1 = a scored\n   divergence, and the log names the rows.)")
    return 0 if scored else 1


if __name__ == "__main__":
    sys.exit(main())
