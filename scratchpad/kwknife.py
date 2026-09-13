#!/usr/bin/env python3
"""🔪 IS THIS ROW LOAD-BEARING? Break the keyword and see whether its row notices.

Joost ruled 2026-09-13 that every keyword is TIER 0 — no tier established — because
a `SUPPORTED` verdict is ONE AGREEMENT POINT and agreement can be vacuous. This is
the non-vacuity half of what establishing a tier needs: disable a statement's
handler in the BUILT ROM and re-run only its kwsweep row. A row still SUPPORTED
with the handler dead is BLIND, and its keyword's evidence is worth nothing.

⚠️ A KNIFE CAN BE SILENTLY INERT because the plant never happened, and it reports
that the same way a keyword with no defect reports (TODO.md: 13 runners lacked the
guard). So the plant is VERIFIED here: the ROM bytes are read back after writing,
and the run refuses if they are not what was written.

The statement dispatch is a table (`db token / dw handler`), so a knife is a
two-byte write to one entry — no rebuild, and no risk of hitting a handler some
OTHER keyword shares, which is why the table entry is cut and not the handler.
"""
import io, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import knife_guard  # D-KNIFEROM: prove the cut reached the INSTALLED images
ROM = os.path.join(ROOT, "build", "zerobas-main-eu.rom")
SYM = os.path.join(ROOT, "build", "basic-reloc.sym")

def syms():
    out = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out

def token_of(name):
    """The token byte for a statement keyword, from sysvars.inc's own equate."""
    src = io.open(os.path.join(ROOT, "basic", "sysvars.inc"), encoding="utf-8").read()
    m = re.search(r"^%s_TOKEN\s+equ\s+\$([0-9A-Fa-f]+)" % name, src, re.M)
    if not m:
        sys.exit(f"knife: no {name}_TOKEN equate — nothing was measured")
    return int(m.group(1), 16)

DEADTOK = 0xFE          # matches no kwtable entry, so a `cp` against it never fires


def plant_fn(tok):
    """Cut a FUNCTION selector by changing the COMPARISON OPERAND, not the target.

    🔴 THE STATEMENT CUT DOES NOT REACH THESE. `$FF`-prefixed selectors dispatch
    through a `cp <TOK>` / `jp z,<handler>` chain in expr.asm (plus the
    `ev_ff_argtab` cpir set), not through stmt_table — which is exactly why VDP,
    BASE and MAX came back unconnected from the statement sweep: their ROWS use the
    function form and the knife had cut the statement entry. The wrong path being
    cut is not the row being blind.
    🎯 PATCHING THE OPERAND rather than the jump target works for `jp z` and `jr z`
    alike (a `jr` to the error tail would usually be out of range), and it fails
    SAFELY: the selector simply never matches and the chain falls through to its own
    error path.
    ⚠️ AMBIGUITY IS REFUSED, NOT GUESSED: `FE <tok>` can occur by accident in data
    or inside another instruction's operand, so a site counts only if a conditional
    jump follows it, and the run stops unless EXACTLY ONE site qualifies."""
    rom = bytearray(io.open(ROM, "rb").read())
    # 🔴 THE JUMP TARGET MUST RESOLVE TO A KNOWN `ev_*` SYMBOL. Matching `cp <tok>`
    # followed by any conditional jump found 2-3 sites per keyword -- the token byte
    # recurs in the tokeniser, the detokeniser and by coincidence inside other
    # operands. Requiring the target to be a named evaluator entry cuts each to
    # exactly one, and a keyword with NO such site is reported rather than guessed
    # at (MAX has none: it is not dispatched this way at all).
    byaddr = {}
    for line in io.open(SYM, errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m:
            byaddr[int(m.group(2), 16)] = m.group(1)
    hits = []
    for i in range(len(rom) - 4):
        if rom[i] == 0xFE and rom[i + 1] == tok and rom[i + 2] == 0xCA:
            nm = byaddr.get(rom[i + 3] | (rom[i + 4] << 8), "")
            if nm.startswith("ev_"):
                hits.append(i)
    if len(hits) != 1:
        return None, f"{len(hits)} `cp ${tok:02X}` site(s) with an ev_* target — refusing"
    off = hits[0] + 1
    orig = bytes(rom[off:off + 1])
    rom[off] = DEADTOK
    io.open(ROM, "wb").write(bytes(rom))
    if io.open(ROM, "rb").read()[off] != DEADTOK:
        sys.exit("knife: the function plant did NOT take — nothing was measured")
    return (off, orig), None


def plant(tok, dead):
    """Point the statement's table entry at `dead`. Returns (offset, original)."""
    s = syms()
    base = s["stmt_table"]
    rom = bytearray(io.open(ROM, "rb").read())
    for i in range(0, 3 * 120, 3):
        if rom[base + i] == tok:
            off = base + i + 1
            orig = bytes(rom[off:off + 2])
            rom[off] = dead & 0xFF
            rom[off + 1] = dead >> 8
            io.open(ROM, "wb").write(bytes(rom))
            # 🔴 READ IT BACK: an unplanted knife and a keyword with no defect
            # report identically, so the plant is proved before the run.
            back = io.open(ROM, "rb").read()[off:off + 2]
            if back != bytes([dead & 0xFF, dead >> 8]):
                sys.exit("knife: the plant did NOT take — nothing was measured")
            return off, orig
    sys.exit(f"knife: token ${tok:02X} is not in stmt_table — nothing was measured")

def install(before=None):
    """Re-install, and PROVE the images moved when a cut is in place.

    🔴 Verifying the bytes I wrote is not enough: the probe reads the INSTALLED
    machine, and an install that silently did not happen reports exactly like a
    keyword with nothing to find. `knife_guard.hashes()` is the shared
    implementation the tree already uses for this, and `knife-guard-check` refuses
    a runner that invokes repack-machine without it -- it refused THIS one, and was
    right [[a-knife-can-be-inert-because-the-build-did-not-happen]]."""
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "install-repack-machine.py"),
                    "--merged", ROM, "--disk-rom", os.path.join(ROOT, "build", "disk.rom"),
                    "--sub-rom", os.path.join(ROOT, "build", "sub.rom")],
                   check=True, capture_output=True)
    after = knife_guard.hashes()
    if before is not None and not knife_guard.moved(before, after):
        sys.exit("knife: the installed images did NOT move -- nothing was measured")
    return after

SWEEP_PIN = os.path.join(ROOT, "build", "kwsweep-verdicts.json")


def run_row(row):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "probes", "basic", "basic_probe_kwsweep.py"),
                        "--zb-machine", "C-BIOS_MSX1_EU_REPACK_DISK", "--only", row],
                       capture_output=True, text=True)
    for line in r.stdout.split("\n"):
        if line.startswith(("SUPPORTED", "DIVERGENT", "MISSING", "SILENT-GAP", "UNREADABLE")):
            return line.split()[0]
    return "NO-VERDICT"

WEAK = {}
PIN = os.path.join(ROOT, "build", "kwknife-connected.json")


def record(kw, row, verdict, mode):
    """MERGE this keyword's reading into build/kwknife-connected.json.

    🔴 A PIN, NOT A PARSE OF MY OWN CONSOLE OUTPUT. `tier_table` reads
    build/kwsweep-verdicts.json the same way, and a reader that scrapes a report's
    prose breaks the moment the report is reworded — the tree has been bitten by
    instruments that re-implement a consumer's parser. MERGED rather than
    overwritten so a statement sweep and a later `--fn` run accumulate instead of
    replacing one another.
    ⚠️ The ROM fingerprint rides along: a pin whose fingerprint no longer matches
    the built ROM describes a machine that no longer exists, and the reader says so
    rather than quietly reporting stale connectedness."""
    import json, time
    try:
        pin = json.load(open(PIN, encoding="utf-8"))
    except (OSError, ValueError):
        pin = {"rows": {}}
    pin["written"] = time.strftime("%Y-%m-%d %H:%M:%S")
    pin["rom_fingerprint"] = knife_guard.hashes()
    pin.setdefault("rows", {})[kw] = {
        "row": row, "verdict": verdict, "mode": mode,
        "connected": verdict != "SUPPORTED", "weak": bool(WEAK.get(row))}
    os.makedirs(os.path.dirname(PIN), exist_ok=True)
    json.dump(pin, open(PIN, "w", encoding="utf-8"), indent=1, sort_keys=True)


def enumerate_targets():
    """Every statement keyword in stmt_table, paired with the kwsweep row that
    claims it -- read from the TABLE and from the SWEEP, never hand-listed.

    🔴 THE KEYWORD-PER-ROW MAPPING IMPORTS `tier_table.stmt_keyword`, the
    CONSUMER'S OWN parser. An ad-hoc regex here would be silent-failure mode 4:
    the last one admitted a bare `A` as a keyword and hid a real miss. The table
    ends at a $00 token, which `es_scan` itself uses as its sentinel."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
    import tier_table
    import basic_probe_kwsweep as sweep
    kwset = set(tier_table.kwtable_keywords())
    # 🔴 TOKEN BYTES COLLIDE between statement tokens and the $FF-prefixed FUNCTION
    # selectors, so scanning sysvars.inc's `<NAME>_TOKEN equ` lines maps a byte to
    # whichever equate comes first -- the dry run listed EXP, SIN, ATN and ASC as
    # statements. kwtable.inc is authoritative and says which is which: an entry
    # `db len,"NAME",1,TOK` is a ONE-BYTE statement token, while `db len,"NAME",2,
    # PEEK_PREFIX,TOK` is a function.
    eq = {}
    for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9A-Fa-f]+)",
                         io.open(os.path.join(ROOT, "basic", "sysvars.inc"),
                                 encoding="utf-8").read(), re.M):
        eq[m.group(1)] = int(m.group(2), 16)
    tok2kw = {}
    for m in re.finditer(r'db\s+\d+,"([^"]+)",1,(\w+)',
                         io.open(os.path.join(ROOT, "basic", "kwtable.inc"),
                                 encoding="utf-8").read()):
        t = eq.get(m.group(2))
        if t is not None:
            tok2kw[t] = m.group(1)
    # keyword -> the row that is ABOUT it. Several rows can credit one keyword --
    # `PRINT TAB(..)` credits PRINT -- so prefer a row whose KEY names the keyword
    # and fall back to the first crediting row, rather than taking sweep order.
    kw2row, kw2any = {}, {}
    for row in sweep.SWEEP:
        key, body = row[0], row[1]
        if row[2] is None:                      # crunch-only: nothing to knife
            continue
        kw = tier_table.stmt_keyword(body, kwset)
        if not kw:
            continue
        # 🔴 A `WEAK:` ROW IS ALREADY EXCLUDED FROM THE SWEEP'S OWN TALLY, so the
        # knife must not report it as a discovery. Measured 2026-09-13: the `time`
        # row came back SUPPORTED under the knife and its note ALREADY said why --
        # "absent => variable TI, always 0, and `0>=0` is STILL true". The knife
        # rediscovering a documented weakness is a good sign for the knife and NOT
        # a new finding; labelling it BLIND would double-count a known one.
        note = row[4] if len(row) > 4 else ""
        WEAK[key] = note.startswith("WEAK:")
        kw2any.setdefault(kw, key)
        base = kw.lower().rstrip("$")
        if kw not in kw2row and (key == base or key.startswith(base)):
            kw2row[kw] = key
    for kw, key in kw2any.items():
        kw2row.setdefault(kw, key)
    rom = io.open(ROM, "rb").read()
    base = syms()["stmt_table"]
    out, i = [], 0
    while True:
        tok = rom[base + i * 3]
        if tok == 0:
            break
        kw = tok2kw.get(tok)
        if kw and kw in kw2row:
            # 🔴 CARRY THE TOKEN. It was re-derived later from the keyword NAME as
            # `<NAME>_TOKEN`, which cannot work for `DSKO$` / `DSKI$` / `ATTR$` --
            # the `$` is not an identifier character -- and the run EXITED on the
            # first one instead of skipping it, losing the remaining 51 keywords.
            # The enumeration already resolved the byte; nothing should look it up
            # a second time by a different route.
            out.append((kw, kw2row[kw], tok))
        i += 1
    return out, i

FNMODE = "--fn" in sys.argv
if FNMODE:
    sys.argv = [a for a in sys.argv if a != "--fn"]
TARGETS = None
if len(sys.argv) > 1 and sys.argv[1] == "--list":
    tg, n = enumerate_targets()
    print(f"stmt_table holds {n} entries; {len(tg)} have a kwsweep row to knife\n")
    for kw, row, tok in tg:
        print("   %-10s %-12s $%02X" % (kw, row, tok))
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == "--all":
    TARGETS, _ = enumerate_targets()
elif len(sys.argv) > 1:
    TARGETS = [tuple(a.split(":")) for a in sys.argv[1:]]
else:
    TARGETS = [("POKE", "pokekw", 0x98), ("VPOKE", "vpoke", 0xC6)]
if TARGETS and len(TARGETS[0]) == 2:        # explicit KW:row pairs on the command line
    TARGETS = [(k, r, token_of(k)) for k, r in TARGETS]

# 🔴 THE KNIFE DESTROYS THE PIN IT DEPENDS ON, unless this guard exists. Each cut
# runs `basic_probe_kwsweep --only <row>`, and the sweep WRITES
# build/kwsweep-verdicts.json every run — so a single-row invocation replaces the
# whole-battery pin with ONE row. Measured 2026-09-13: after a knife session the
# pin held exactly `vdpkw`, and `tier_table` (which reads that pin for evidence)
# silently lost every other keyword's verdict. The pin is saved before the first
# cut and restored after the last, whatever happens in between.
_sweep_pin_backup = None
if os.path.exists(SWEEP_PIN):
    _sweep_pin_backup = io.open(SWEEP_PIN, "rb").read()
import atexit
@atexit.register
def _restore_sweep_pin():
    if _sweep_pin_backup is not None:
        io.open(SWEEP_PIN, "wb").write(_sweep_pin_backup)


@atexit.register
def _force_clean_rom():
    """🔴 A KNIFE'S WRITE DEFEATS `make`'s UP-TO-DATE CHECK, and that is worse than
    it sounds. Writing build/zerobas-main-eu.rom makes the artifact NEWER than its
    sources, so a later `make repack-machine` does nothing and the tree keeps a
    KNIFED machine while every command reports success. Measured 2026-09-13: after
    an interrupted run the installed main ROM was 63721706 where a clean build
    gives e3dbed36, and `make repack-machine` would not replace it. The battery's
    own fingerprint line was the only thing that showed it.
    So the ROM is DELETED and rebuilt at exit -- once per session, not per cut --
    and the machine re-installed from those canonical bytes."""
    try:
        os.remove(ROM)
    except OSError:
        pass
    subprocess.run(["make", "repack-machine"], cwd=ROOT, capture_output=True)

dead = syms()["stmt_error"]
print("knife: statement handlers -> stmt_error $%04X; a row still SUPPORTED is BLIND\n" % dead)
for kw, row, tok in TARGETS:
    before = knife_guard.hashes()
    if FNMODE:
        res, why = plant_fn(tok)
        if res is None:
            print("  %-8s row %-10s %s" % (kw, row, why)); continue
        off, orig = res
    else:
        off, orig = plant(tok, dead)
    try:
        install(before)
        v = run_row(row)
    finally:
        rom = bytearray(io.open(ROM, "rb").read())
        rom[off:off + 2] = orig
        io.open(ROM, "wb").write(bytes(rom))
        install()
    record(kw, row, v, "fn" if FNMODE else "stmt")
    flag = ("LOAD-BEARING" if v != "SUPPORTED"
            else "WEAK (already excluded)" if WEAK.get(row) else "🔴 BLIND")
    print("  %-8s row %-10s knifed -> %-12s %s" % (kw, row, v, flag))
    sys.stdout.flush()
