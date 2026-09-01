#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-FMTTAIL — is `CALL FORMAT`'s name-tail / argument skip sloppy-accept on the
REFERENCE too, or only here?  (TODO.md item, filed by the review tier.)

Reading `basic/format.asm`: `fmt_match_format` matches the six chars "FORMAT"
and never checks that the next character is a delimiter, so `CALL FORMATX`
matches; `exc_skip` then swallows everything to ':'/EOL and is QUOTE-BLIND, so
`_FORMAT("A:")` stops at the colon INSIDE the quotes. Both are readings of our
source. What the reference does is unmeasured.

🎯 THE MEASUREMENT NEEDS NO FORMATTING AT ALL. If a row is rejected, the error
lands BEFORE anything happens; if it is accepted, the CF-3300 stops at its
interactive format prompt. So the comparable observable is
**REJECTED (an error appears) vs ACCEPTED (it proceeds)** — read off the screen,
with the prompt never answered. Nothing is formatted on the reference.

⚠️ ZEROBAS HAS NO PROMPT: a single geometry means an accepted row formats
immediately. Every side therefore gets its own scratch COPY of the disk, per
row, and the committed image is never opened.

🔴 f.bad IS THE ARM THAT MAKES THE REST MEAN ANYTHING. `CALL FORMA` must be
REJECTED on both machines. Without a row that is known-rejected, "no error
anywhere" is indistinguishable from an instrument that cannot see an error at
all [[readout-blind-to-its-own-subject]].
"""
from __future__ import annotations
import os, shutil, signal, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                            # noqa: E402,F401
import omsx_preflight                                       # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
SRC_DSK = os.path.join(ROOT, "disk", "test720.dsk")
SIDES = {"cf3300": "National_CF-3300",
         "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}

ROWS = [
    ("f.ctl",   "CALL FORMAT"),        # control: the supported spelling
    ("f.us",    "_FORMAT"),            # control: the underscore spelling
    ("f.bad",   "CALL FORMA"),         # 🔴 NEGATIVE CONTROL — must be REJECTED
    ("f.tail",  "CALL FORMATX"),       # name-tail: 6 chars matched, no delimiter check
    ("f.tail2", "CALL FORMATFOO"),
    ("f.arg",   "CALL FORMAT X"),      # argument skip
    ("f.quote", '_FORMAT("A:")'),      # quote-blind skip (the D-DATACOLON class)
    # 🟢 THE OVER-REJECTION GUARD. A fix that requires the statement to END
    # after the name must still allow it to end with ':' and chain. Without this
    # row, tightening the tail to `or a / jr z` alone would pass every row above
    # and silently break `CALL FORMAT:<next statement>`
    # [[two-rules-that-coincide-on-every-row-you-have]].
    ("f.colon", "CALL FORMAT:PRINT 1"),
]

T_DATE, T_LINE, T_ENTER, T_SNAP, T_QUIT = 12.0, 16.0, 19.0, 26.0, 28.0


def tcl_quote(s: str) -> str:
    out = []
    for ch in s:
        out.append("\\r" if ch == "\r" else ("\\" + ch if ch in '"\\[]$' else ch))
    return '"' + "".join(out) + '"'


def build_tcl(out_path: str, line: str) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         "proc __hexv {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __snap {} {",
         "  global __f",
         # 🔴 THE TWO MACHINES PUT THEIR NAME TABLE AT DIFFERENT ADDRESSES --
         # measured, not guessed: the CF-3300 at $1800, zerobas at $0000, both
         # with a stride of 40. ($F3B3 reads 0000 on BOTH, so it is not the
         # discriminator; the older CALL FORMAT spike renders $1800 at 32.)
         # The first cut captured both and picked "whichever has more non-blank
         # rows", which is how the PATTERN GENERATOR won: two different typed
         # lines produced BYTE-IDENTICAL "screens" and every row read ACCEPTED,
         # including the one that must be rejected.
         # 🎯 SO THE PLANE IS CHOSEN BY THE ONE THING THAT PROVES IT IS THE
         # SCREEN: it must contain the ECHO of the line we typed. A readout that
         # cannot show its own subject is refused rather than reported
         # [[readout-blind-to-its-own-subject]].
         '  puts $__f "P0000=[__hexv 0x0000 960]"',
         '  puts $__f "P1800=[__hexv 0x1800 960]"',
         "  flush $__f",
         "}",
         f"after time {T_DATE} {{ type {tcl_quote(chr(13))} }}",
         f"after time {T_LINE} {{ type {tcl_quote(line)} }}",
         f"after time {T_ENTER} {{ type {tcl_quote(chr(13))} }}",
         f"after time {T_SNAP} {{ __snap }}",
         f"after time {T_QUIT} {{ close $__f; exit }}"]
    return "\n".join(L) + "\n"


def render(hexv: str, width: int) -> list[str]:
    """FULL-WIDTH rows, never rstripped.

    🔴 THE SCREEN WRAPS MID-WORD AND rstrip() BREAKS THE ONLY STRING THAT
    MATTERS. `CALL FORMA` puts "Syntax" in the last six columns of one row and
    " error" in the first six of the next; stripping the rows and joining them
    with a space yields "Syntax  error", which matches no error name -- so the
    NEGATIVE CONTROL read ACCEPTED on a machine that had plainly printed a
    Syntax error. Concatenating the untouched 40-column rows reconstructs the
    text exactly, because the wrap point carries its own spacing."""
    d = bytes.fromhex(hexv)
    return ["".join(chr(c) if 32 <= c < 127 else " " for c in d[r*width:(r+1)*width])
            for r in range(len(d) // width)]


def run(side: str, line: str, keep: str | None) -> list[str]:
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix="fmttail_",
                                      delete=False).name
    shutil.copy(SRC_DSK, dsk)                    # a scratch copy, always
    out = tempfile.NamedTemporaryFile(suffix=".txt", prefix="fmttail_",
                                      delete=False).name
    tcl = out + ".tcl"
    open(tcl, "w").write(build_tcl(out, line))
    # 🔴 WITHOUT `renderer none` OPENMSX NEVER GETS AHEAD OF REAL TIME and the
    # `after time` deadlines never arrive -- the first cut hung for 180 s and
    # produced no capture at all. The existing CALL FORMAT spike already passed
    # these flags; copying the launch, not just the Tcl, is the lesson.
    argv = [OMSX, "-machine", SIDES[side], "-diska", dsk,
            "-command", "set renderer none; set sound_driver null",
            "-script", tcl]
    proc = subprocess.Popen(omsx_preflight.guarded(argv),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + 130
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    screens = {}
    if os.path.exists(out):
        for l in open(out):
            k, _, v = l.strip().partition("=")
            if v:
                screens[k] = v
    best, chosen = [], None
    for k in ("P0000", "P1800"):
        if k not in screens:
            continue
        r = render(screens[k], 40)
        if line.upper() in "".join(r).upper():      # the echo: this IS the screen
            best, chosen = r, k
            break
    if keep:
        open(keep, "a").write(f"\n===== {side} :: {line}  (plane {chosen}) =====\n"
                              + "\n".join(r.rstrip() for r in best
                                           if r.strip()) + "\n")
    os.unlink(dsk)
    return best


ERRS = ("Syntax error", "Illegal function call", "Type mismatch",
        "Undefined line", "Bad file", "Device I/O error")


def verdict(rows: list[str]) -> str:
    if not rows or not "".join(rows).strip():
        return "<NO SCREEN>"
    txt = "".join(rows)                      # NOT " ".join -- see render()
    for e in ERRS:
        if e in txt:
            return f"REJECTED ({e})"
    # the CF-3300 stops on a prompt; zerobas just returns to Ok having formatted
    for cue in ("Strike", "STRIKE", "Drive name", "DRIVE NAME", "format", "FORMAT?"):
        if cue in txt:
            return "ACCEPTED (at the format prompt)"
    return "ACCEPTED (no error)"


def main() -> int:
    sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
    keep = os.environ.get("FMTTAIL_SCREENS")
    res = {}
    for lab, line in ROWS:
        for s in sides:
            res[(lab, s)] = verdict(run(s, line, keep))
    w = max(len(l) for l, _ in ROWS)
    print(f"{'row':<{w}}  {'typed':<16}  " + "  ".join(f"{s:>34}" for s in sides))
    diff, blind = [], []
    for lab, line in ROWS:
        cells = [res[(lab, s)] for s in sides]
        if any("<NO SCREEN>" in c for c in cells):
            blind.append(lab)
        kind = [c.split(" (")[0] for c in cells]
        if len(set(kind)) > 1:
            diff.append(lab)
        print(f"{lab:<{w}}  {line:<16}  " + "  ".join(f"{c:>34}" for c in cells))
    print(f"\nDIFF (accept-vs-reject) : {len(diff)}/{len(ROWS)}"
          + ("  " + " ".join(diff) if diff else ""))
    neg = [res[(lab, s)] for lab, _ in ROWS if lab == "f.bad" for s in sides]
    print("🔴 NEGATIVE CONTROL f.bad (`CALL FORMA`) must be REJECTED on every "
          f"side: {neg}")
    if blind:
        print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
        return 2
    if not all(v.startswith("REJECTED") for v in neg):
        print("🔴 THE INSTRUMENT NEVER SAW A REJECTION — every other row's "
              "'ACCEPTED' is unfalsifiable. Nothing below is a finding.")
        return 2
    return 1 if diff else 0


if __name__ == "__main__":
    raise SystemExit(main())
