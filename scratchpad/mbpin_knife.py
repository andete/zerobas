#!/usr/bin/env python3
"""K-MB1 (D-DISKRUN mb.dsk, 2026-10-27): put disk/kernel.asm back as it was
(scratchpad/ctrlram_knife.py's runner, boot5e10-acceptance) (the commit given, default HEAD), rebuild, run the
trace battery (repacked first) and read its rc, then restore the files and
rebuild CLEAN; all five images must hash as before (knife_guard).

🔴 WHY THE RESTORE IS A CLEAN BUILD. The first cut of this runner hashed the MAIN ROM
only, restored with a plain `make repack-machine`, and printed BYTE-IDENTICAL -- while
sub2.rom was still the CUT build's: make 3.81 compares whole seconds, a source written
in the same second as a build output reads as up to date, and $(RELOC_SYM) (hence
sub/basic-resident-abi.inc, hence sub2) was skipped while the main ROM's own rule
still rebuilt. kwknife then pinned that half-restored machine, and tiers-md-check
refused the pin. Five hashes catch it; `rm -rf build` prevents it.

    python3 -u scratchpad/mbpin_knife.py [REV]
"""
import os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard  # noqa: E402

FILES = ["disk/kernel.asm"]
TMP = "/tmp/mbpin_knife"


def main():
    rev = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    keep = {f: open(f).read() for f in FILES}
    base = knife_guard.hashes()
    g = None
    try:
        for f in FILES:
            open(f, "w").write(subprocess.run(["git", "show", f"{rev}:{f}"], capture_output=True,
                                              text=True, check=True).stdout)
        ok, cut, rc = knife_guard.build(f"{TMP}/mk_cut.log", base, clean=True)
        print(knife_guard.report("K-MB1", ok, base, cut, rc, f"{TMP}/mk_cut.log"), flush=True)
        if ok and not rc:
            g = subprocess.run("make boot5e10-acceptance", shell=True,
                               capture_output=True, text=True)
    finally:
        for f, body in keep.items():
            open(f, "w").write(body)
        _, back, rc2 = knife_guard.build(f"{TMP}/mk_back.log", None, clean=True)
    same = back == base
    print(f"restore: {base} -> {back}  build rc={rc2}  {'BYTE-IDENTICAL (all five)' if same else 'DRIFT'}")
    if g is None:
        print("K-MB1: NOT SCORED -- the cut did not reach the ROM")
        sys.exit(2)
    print(f"K-MB1: gate rc={g.returncode}")
    for line in (g.stdout + g.stderr).splitlines():
        if line.startswith(("FAIL", "---")) or "boot5e10" in line:
            print(line)
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
