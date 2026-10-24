#!/usr/bin/env python3
"""Run scratchpad/tapin_margin.py against builds that delay CLOAD's byte loop.

Each variant plants a delay at the top of ctp_body (basic/cload.asm, once per
program byte), rebuilds with `make repack-machine`, hashes the main ROM (a cut
that did not reach the ROM is reported, never scored), runs the probe, and
restores the source; the last build is the restored tree, hashed again.

    [TAPIN_TAPE=x.wav] python3 -u scratchpad/tapin_margin_knives.py [--wide | --b2400 | --b2400hi]
"""
import hashlib, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "basic", "cload.asm")
ROM = os.path.join(REPO, "build", "zerobas-main-eu.rom")
ANCHOR = "ctp_body:\n                ld      a,d\n"


def delay(n, reps):
    body = "".join(f"                ld      b,{n}\n                djnz    $\n" for _ in range(reps))
    return f"ctp_body:\n                push    bc                  ; TAPIN-MARGIN knife\n{body}                pop     bc\n                ld      a,d\n"


# run 1 (--wide): 64 / 255 / 510 / 1020 passes; run 2 (the default): the 64..255 bisection
WIDE = [("d64", delay(64, 1)), ("d255", delay(255, 1)), ("d510", delay(255, 2)),
        ("d1020", delay(255, 4))]
NARROW = [("d96", delay(96, 1)), ("d128", delay(128, 1)), ("d160", delay(160, 1)),
          ("d192", delay(192, 1))]
# run 3 (--b2400, with TAPIN_TAPE set to the VG-8020's 2400-baud recording)
B2400 = [("d0", ANCHOR), ("d32", delay(32, 1)), ("d48", delay(48, 1)), ("d64", delay(64, 1)),
         ("d96", delay(96, 1))]
# run 4 (--b2400hi): all of run 3 held, so where does the 2400-baud tape break?
B2400HI = [("d112", delay(112, 1)), ("d128", delay(128, 1)), ("d160", delay(160, 1))]
VARIANTS = (WIDE if "--wide" in sys.argv else B2400 if "--b2400" in sys.argv
            else B2400HI if "--b2400hi" in sys.argv else NARROW)


def h():
    return hashlib.sha256(open(ROM, "rb").read()).hexdigest()[:8]


def build():
    return subprocess.run("make repack-machine", shell=True, cwd=REPO,
                          capture_output=True, text=True).returncode


def main():
    orig = open(SRC).read()
    assert orig.count(ANCHOR) == 1, "anchor not unique"
    base = h()
    print(f"base ROM {base}", flush=True)
    try:
        for tag, repl in VARIANTS:
            open(SRC, "w").write(orig.replace(ANCHOR, repl))
            rc = build()
            now = h()
            if rc or (now == base and repl != ANCHOR):
                print(f"{tag}: build rc={rc} ROM {now} -- DID NOT REACH THE ROM, not scored", flush=True)
                continue
            out = subprocess.run([sys.executable, "-u", os.path.join(REPO, "scratchpad", "tapin_margin.py"), tag],
                                 cwd=REPO, capture_output=True, text=True).stdout
            print(f"ROM {now}  " + next((l for l in out.splitlines() if l.startswith(tag + ":")), tag + ": NO LINE"), flush=True)
    finally:
        open(SRC, "w").write(orig)
        build()
        print(f"restore: {base} -> {h()}  {'BYTE-IDENTICAL' if h() == base else 'DRIFT'}", flush=True)


if __name__ == "__main__":
    main()
