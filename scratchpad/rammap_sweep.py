#!/usr/bin/env python3
"""D-DEFFN RAM HUNT — where is the BASIC workspace actually free?

🔴 THE REASON THIS IS A TOOL AND NOT A READING. `basic/sysvars.inc` said
*"-> top $E3E8, well below the disk WBUF wall at $E560 (376 B spare)"* and TEN
bytes were free; three later slices had spent the window while the header still
advertised it. **A free-space figure in a comment is a reading with a date on
it, and RAM figures have NO GATE** -- `make wall-assertion-check` polices ROM
claims only. So the map gets WALKED, never read.

WHAT IT DOES. Resolves every `NAME equ <expr>` in the component's `.inc` files
(including `X equ Y + N*M` chains, iteratively to a fixed point), keeps those
landing in a RAM window, sorts them, and prints the DELTA to the next name.

🔴 EVERY GAP IS A CANDIDATE, NOT FREE SPACE -- and this is the tool's whole
caveat. An address tells you where a cell STARTS and never how long it is, so a
delta of N bytes is *"the previous cell plus whatever follows it"*, not N free
bytes. `GFX_PSTK equ $E3F2` is followed by nothing until `$E560` and is **360
bytes of live span stack**. The tool CANNOT know that; only the `_CAP`/`_END`
arithmetic beside it can, and only a reader can connect the two. Treat a big
delta as *"go read this"*.

🔴 AND OVERLAP IS DESIGNED HERE, NOT A BUG. This tree deliberately aliases
windows between mutually-exclusive execution contexts (the standalone disk ROM's
`SECTOR_BUF` over basic-core's string pool; DRAW's frame buffer over PAINT's
span stack). So the same address legitimately carries several names from
different components, and a hole in ONE component's map can be solidly occupied
in another's. `--all` prints every component together for exactly that reason.

⚠️ CALIBRATION: `--selftest` plants a synthetic pair with a known gap and
asserts the walk reports THAT gap, so "no holes" is a statement about the map
rather than about a walk that finds nothing by construction. It also plants an
`X equ Y+N` chain, because a resolver that silently dropped arithmetic would
under-report occupancy -- which is the failure direction that costs RAM.
"""
from __future__ import annotations
import glob
import re
import sys

EQU = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+(.+?)\s*(?:;.*)?$",
                 re.IGNORECASE)

# The BASIC workspace this project owns, below the standard MSX sysvar block.
DEFAULT_LO, DEFAULT_HI = 0xE000, 0xF380

# ⚠️ `--basic` drops disk/equates.inc. That is not a convenience: the standalone
# MSX1 disk ROM (slot 3-1) only ever runs while booting/driving MSX-DOS, NEVER
# while the BASIC interpreter is live, and this tree ALREADY aliases across that
# boundary deliberately (basic-core's string pool sits over disk's SECTOR_BUF;
# PAINT's span stack sits over disk's BDOS scratch). So a hole that exists only
# in BASIC's own map is a REAL candidate for BASIC-resident state, and merging
# the two components hides it. Run BOTH and read the difference.
BASIC_FILES = sorted(glob.glob("basic/*.inc")) + sorted(glob.glob("sub/*.inc"))
FILES = BASIC_FILES + sorted(glob.glob("disk/*.inc"))


def parse(paths):
    """name -> (raw expression, file, line)."""
    raw = {}
    for p in paths:
        try:
            lines = open(p).readlines()
        except OSError:
            continue
        for i, ln in enumerate(lines, 1):
            m = EQU.match(ln.rstrip("\n"))
            if m:
                raw.setdefault(m.group(1), (m.group(2).strip(), p, i))
    return raw


def resolve(raw):
    """Iterate to a fixed point: `X equ Y+N*M` needs Y resolved first."""
    vals, expr = {}, {}
    for n, (e, f, i) in raw.items():
        expr[n] = (e, f, i)
    for _ in range(24):
        progress = False
        for n, (e, f, i) in expr.items():
            if n in vals:
                continue
            s = e.replace("$", "0x")
            # a bare hex literal with an H suffix, and & forms
            s = re.sub(r"\b([0-9A-Fa-f]+)H\b", r"0x\1", s)
            s = s.replace("&H", "0x").replace("&h", "0x")
            # 🔴 STRIP HEX LITERALS BEFORE SCANNING FOR NAMES. `0xE3E8` yields
            # the identifier `xE3E8` to a bare [A-Za-z_]\w* scan, so every
            # literal reads as an unresolved symbol and the whole map resolves
            # to nothing. The --selftest caught this; a run without it would
            # have printed "0 land in the window" and looked like an answer.
            bare = re.sub(r"0x[0-9A-Fa-f]+", " ", s)
            names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", bare))
            if names - set(vals):
                continue
            try:
                v = eval(s, {"__builtins__": {}}, dict(vals))  # noqa: S307
            except Exception:
                continue
            if isinstance(v, int):
                vals[n] = v
                progress = True
        if not progress:
            break
    return vals, expr


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    selftest = "--selftest" in sys.argv
    lo = int(args[0], 16) if len(args) > 0 else DEFAULT_LO
    hi = int(args[1], 16) if len(args) > 1 else DEFAULT_HI

    raw = parse(BASIC_FILES if "--basic" in sys.argv else FILES)
    if selftest:
        # 🔴 PLANT INSIDE A STRETCH THE MAP ITSELF SAYS IS EMPTY. The first cut
        # planted at a hand-picked $E7A0..$E7F0 and the walk reported a 24 B gap
        # instead of 72 -- because a REAL name sits at $E7C0, between the two
        # plants. The walk was right and the FIXTURE was wrong, which is the
        # same shape as a knife whose green row is a claim about its fixture.
        # So: resolve the real map first, take its largest gap, and plant well
        # inside that.
        real, _ = resolve(dict(raw))
        ra = sorted({v for n, v in real.items() if lo <= v < hi})
        span = max(zip(ra, ra[1:]), key=lambda t: t[1] - t[0])
        base = span[0] + 8
        raw["__PLANT_BASE"] = (f"${base:04X}", "<plant>", 0)
        raw["__PLANT_STEP"] = ("__PLANT_BASE + 4*2", "<plant>", 0)
        raw["__PLANT_FAR"] = (f"${base + 24:04X}", "<plant>", 0)

    vals, expr = resolve(raw)
    inwin = sorted((v, n) for n, v in vals.items() if lo <= v < hi)
    nfiles = len(BASIC_FILES if "--basic" in sys.argv else FILES)
    print(f"  denominator: {len(raw)} equ definitions in {nfiles} .inc "
          f"files; {len(vals)} resolved; {len(inwin)} land in "
          f"[{lo:04X},{hi:04X})")

    # group names sharing an address -- deliberate aliasing shows up here
    byaddr: dict[int, list[str]] = {}
    for v, n in inwin:
        byaddr.setdefault(v, []).append(n)
    addrs = sorted(byaddr)

    if selftest:
        want_step = vals["__PLANT_BASE"] + 8
        ok_chain = vals.get("__PLANT_STEP") == want_step
        gap = next((b - a for a, b in zip(addrs, addrs[1:]) if a == want_step),
                   None)
        ok_gap = gap == 16
        print(f"  SELFTEST: arithmetic chain resolved = {ok_chain} "
              f"(want ${want_step:04X}, got "
              f"${vals.get('__PLANT_STEP', 0):04X})")
        print(f"  SELFTEST: planted gap found = {ok_gap} (want 16, got {gap})")
        return 0 if (ok_chain and ok_gap) else 1

    gaps = []
    for a, b in zip(addrs, addrs[1:]):
        gaps.append((b - a, a, b))
    gaps.sort(reverse=True)
    print(f"\n  LARGEST DELTAS -- 🔴 each is 'the cell at the low address PLUS "
          f"whatever follows', NEVER free space. Go read the source.\n")
    for d, a, b in gaps[:20]:
        names = "/".join(byaddr[a])
        _, f, i = expr[byaddr[a][0]]
        print(f"  {d:5d} B  ${a:04X}..${b:04X}  {names}")
        print(f"            {f}:{i}")
    tail = hi - addrs[-1] if addrs else 0
    print(f"\n  (last name ${addrs[-1]:04X} {'/'.join(byaddr[addrs[-1]])}, "
          f"{tail} B to the ${hi:04X} window top)")
    print(f"  {len(addrs)} distinct addresses, "
          f"{sum(1 for a in addrs if len(byaddr[a]) > 1)} carrying more than "
          f"one name (deliberate aliasing is normal here -- see the header)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
