#!/usr/bin/env python3
r"""pick_gates — which battery does THIS change need? (D-GATESCOPE)

🏗️ RULED BY JOOST, 2026-09-24: *"running the full battery takes a really long
time ... only running the full after genuinely large or risky fixes"* -> scoped
batteries, the full one on risk, and at least every 5th commit.
⏱ RE-RULED BY JOOST, 2026-10-13 (*"yes, do 1 and 2, it is a tradeoff allowing to
move faster"*): the FULL battery runs **once a day** and at every hand-off, and
per commit only when RAM ADDRESSES MOVE; kwtime / kwram left the per-ROM canary
(they run in FULL). A day can now carry a commit that only FULL would catch.

  change                              runs
  docs / TODO / scratchpad only       STATIC  -- the static tier
  probe or tool, no ROM change        SCOPED  -- static + the emulator suites whose
                                                 scripts IMPORT a changed file
  ROM change (any handler, shared     SCOPED  -- static + suites that mention the
    code, unknown blast radius)                  keyword + a fixed CANARY (kwsweep)
  a RAM address added or moved        FULL    -- (+ the five excluded suites)
  the gate harness itself             FULL    -- an instrument change cannot be
                                                 vouched for by a scoped run of it
  --handoff, or 24 h since the last full green   FULL

🔴 WHY A BACKSTOP AT ALL: on 2026-08-26 a fix that was right by its own gate broke
a DIFFERENT suite three times, and a later one turned 32 other suites red. Each
was caught by a gate the change did not obviously touch. Scoping trades that
coverage for time; the every-5th rule and the shared-code list bound the trade.
⏱ Since 2026-10-13 the bound is a DAY, not five commits, and an unknown blast
radius runs the canary (kwsweep included) instead of everything -- Joost chose
the speed knowing a breakage can sit on public main until the daily FULL. What
still runs FULL at once is the class that breaks ANYTHING ANYWHERE: a RAM
address added or moved (layout_moves) -- D-ARYCUR's hang was one cell landing
on another.

    python3 tools/pick_gates.py              # print the plan
    python3 tools/pick_gates.py --run        # run it (`make gates-scoped`)
    python3 tools/pick_gates.py --handoff    # force FULL (session end)
    python3 tools/pick_gates.py --selftest
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import run_gates  # noqa: E402  -- EMULATOR, SCRIPT_REF, _make_n, LAST_GREEN
import probe_tmp  # noqa: E402  -- the temp root run_gates keeps flake logs under

DAILY_HOURS = 24               # Joost 2026-10-13: the full battery once a day
# The gate HARNESS: a change here changes the instrument, so it runs FULL.
# Prefix entries end in "/". (Until 2026-10-13 this list also held the
# interpreter's shared files -- interp/expr/str-engine/main/sub/kernel and
# sysvars.inc; those are planned like any ROM file now, and a RAM-address move
# in sysvars.inc is caught by layout_moves() instead.)
SHARED = ("Makefile", "tools/run_gates.py", "tools/pick_gates.py", "probes/lib/")
ROM_TREES = ("basic/", "sub/", "disk/")
# Broad, FAST suites that exercise the interpreter core -- the canary for a
# handler-local ROM change (each measured well under a minute in the battery).
CANARY = ("error-acceptance", "string-acceptance", "runline-acceptance",
          "keystr-acceptance", "cursor-acceptance",
          # D-STATICEMU (2026-10-08): the keyword sweeps left the STATIC tier, so
          # a ROM change gets them HERE -- they are the keyword-level net.
          # ⏱ kwtime / kwram left 2026-10-13 (daily, in FULL): only kwsweep stays.
          "kwsweep")
EXCLUDED5 = ("input-devices-acceptance", "lnblank-say-acceptance",
             "diskbasic-acceptance", "bdos-acceptance", "fat-error-acceptance")
# 🔴 GENERATED FILES ARE NOT INPUTS. `disk/basic-resident-abi.inc` is regenerated
# whenever a main-ROM address moves -- i.e. on almost EVERY handler change -- so
# counting it as a ROM input made every commit FULL (found replaying D-WIDTHKEEP's
# own diff through this tool). It does mean disk.rom was rebuilt against new
# addresses, which `diskrom-abi-check` (static) verifies agree; the three disk
# suites ride along as a DISK CANARY rather than forcing the whole battery.
GENERATED = tuple(run_gates.REGENERATED) + ("disk/basic-resident-abi.inc",)
DISK_CANARY = ("diskbasic-acceptance", "bdos-acceptance", "fat-error-acceptance")
MODULE_DIRS = ("probes/lib", "probes/basic", "probes/disk", "probes/programs", "tools",
               "scratchpad")
# 🔴 D-PLANDATA (2026-10-29): a BASIC program a suite RUNS is an input too, and no
# `import` names it. Two shapes, both found the day the program ladder gained two
# programs and the plan ran ZERO emulator suites:
#   * the ladder: run_programs.py GLOBS probes/programs/L*.bas -- a changed program
#     there plans every suite whose OWN script is run_programs.py;
#   * a literal path: basic_probe_catcopy.py names "scratchpad/catcopy_temp.bas" --
#     a changed .bas named that way in a suite's closure plans that suite.
# `.bas` only: a broader "a probe reads this file" rule would catch
# kwsweep-rig-carry.json, which changes in nearly every commit, and drag the
# 10-minute sweep into every plan. (`probes/programs` above: gcdi-acceptance
# imports run_programs, and the closure could not resolve it.)
LADDER_DIR, LADDER_RUNNER = "probes/programs/", "probes/programs/run_programs.py"
DATA_EXT = (".bas",)
IMPORT = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", re.M)
# 🔴 D-PLANCHILD (2026-09-27): an acceptance WRAPPER can run its child probes
# as SUBPROCESSES, by path -- `STRING = os.path.join(HERE, "basic_probe_string.py")`
# in string_acceptance.py -- which no `import` names. The closure missed every
# such child, so an edit to basic_probe_string.py planned ZERO emulator suites
# while string-acceptance runs it. A quoted `<name>.py` literal that resolves to
# a local module is followed too; over-inclusion only widens scope.
PYLIT = re.compile(r"""["']([A-Za-z_]\w*)\.py["']""")
HANDLER = re.compile(r"^ex_(\w+):", re.M)


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True,
                          text=True).stdout


def changed_files():
    """Tracked files changed against HEAD, staged or not (a staged ADD counts)."""
    return sorted({l for l in git("diff", "--name-only", "HEAD").splitlines() if l})


def module_file(name):
    for d in MODULE_DIRS:
        p = os.path.join(d, name + ".py")
        if os.path.exists(os.path.join(ROOT, p)):
            return p
    return None


def closure(script, read=None, resolve=None):
    """`script` plus every local module it imports, transitively."""
    resolve = resolve or module_file
    if read is None:
        def read(p):
            try:
                return open(os.path.join(ROOT, p), errors="replace").read()
            except OSError:
                return ""
    seen, todo = set(), [script]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        src = read(p)
        for m in IMPORT.findall(src) + PYLIT.findall(src):
            f = resolve(m)
            if f and f not in seen:
                todo.append(f)
    return seen


def suite_files(targets):
    """-> (target -> every file its recipe runs, imports included,
           target -> ONLY the scripts its recipe names).

    🔴 TWO SETS, BECAUSE THEY ANSWER TWO QUESTIONS. A changed FILE is matched
    against the whole import closure; a changed KEYWORD only against the suite's
    OWN scripts. The first cut matched keywords over the closure, and 81 of 90
    suites "mentioned WIDTH" -- through omsx_repl.py's comments, which every
    suite imports -- so a WIDTH fix scoped to nearly the whole battery."""
    out, own = {}, {}
    for t in targets:
        recipe = run_gates._make_n(t) or ""
        files, mine = set(), set()
        for ref in run_gates.SCRIPT_REF.findall(recipe):
            ref = ref.lstrip("./")
            if os.path.exists(os.path.join(ROOT, ref)):
                mine.add(ref)
                files |= closure(ref)
        out[t], own[t] = files, mine
    return out, own


def changed_handlers(path, text=None, hunks=None):
    """The keywords (from `ex_<name>:` labels) whose bodies a change touches in an
    asm file -- or None when some changed line has no enclosing handler (then the
    blast radius is unknown and the caller must treat it as shared)."""
    if text is None:
        try:
            text = open(os.path.join(ROOT, path), errors="replace").read()
        except OSError:
            return None
    if hunks is None:
        hunks = []
        for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@",
                             git("diff", "-U0", "HEAD", "--", path), re.M):
            start, n = int(m.group(1)), int(m.group(2) or 1)
            hunks.append((start, max(n, 1)))
    lines = text.splitlines()
    kws = set()
    for start, n in hunks:
        for ln in range(start, start + n):
            owner = None
            for i in range(min(ln, len(lines)) - 1, -1, -1):
                lab = re.match(r"^([A-Za-z_]\w*):", lines[i])
                if lab:
                    h = HANDLER.match(lines[i])
                    if h:
                        owner = h.group(1).upper()
                        break
                    # a local label: keep walking up to its handler
            if owner is None:
                return None
            kws.add(owner)
    return kws


def _text(p):
    try:
        return open(os.path.join(ROOT, p), errors="replace").read()
    except OSError:
        return ""


def mentions(files, word, read=None):
    if read is None:
        def read(p):
            try:
                return open(os.path.join(ROOT, p), errors="replace").read()
            except OSError:
                return ""
    pat = re.compile(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])")
    return any(pat.search(read(f)) for f in files)


def hours_since_full():
    """Hours since the last FULL, fully green battery (run_gates.LAST_GREEN's
    `when`, local time), or None when there is no record."""
    try:
        import json
        import time
        with open(run_gates.LAST_GREEN) as fh:
            when = json.load(fh).get("when")
        return (time.time() - time.mktime(time.strptime(when, "%Y-%m-%d %H:%M:%S"))) / 3600
    except (OSError, ValueError, TypeError):
        return None


EQU = re.compile(r"^\s*([A-Za-z_]\w*)\s*:?\s+equ\s+([^;]*)", re.I)


def layout_moves(diff=None, value_of=None):
    """Names whose `equ` line was ADDED or CHANGED in this diff and whose value is
    a RAM address ($8000+) -- a RAM layout move, which runs FULL (Joost
    2026-10-13). A comment-only edit, a constant (`GFX_DFCAP equ 8`) and a removed
    cell are not moves. `diff` / `value_of` are injectable for the selftest."""
    if diff is None:
        diff = git("diff", "-U0", "HEAD", "--", *ROM_TREES)
    old, new = {}, {}
    for ln in diff.splitlines():
        if ln.startswith(("---", "+++")) or not ln[:1] in "+-":
            continue
        m = EQU.match(ln[1:])
        if m:
            (old if ln[0] == "-" else new)[m.group(1)] = m.group(2).strip()
    cand = sorted(n for n, e in new.items() if old.get(n) != e)
    if not cand:
        return []
    if value_of is None:
        import ram_map
        maps = [ram_map.Map(c, 0, 0x10000, use_sym=False) for c in ("basic", "disk")]
        value_of = lambda n: next((m.vals[n] for m in maps if n in m.vals), None)
    return [n for n in cand if (value_of(n) or 0) >= 0x8000]


def plan(changed, suites, handlers_of, since, handoff=False, read=None, own=None,
         layout=()):
    """-> (mode, reasons, emulator suites, excluded-five suites).

    Pure: `suites` is target->files, `handlers_of(path)` the keyword set or None,
    `since` the HOURS since the last full green (None = unknown), `own` the
    suites' own scripts for the keyword match (default: `suites`), `layout` the
    RAM-address moves (layout_moves())."""
    own = suites if own is None else own
    reasons, pick = [], set()
    disk_moved = any(f.startswith("disk/") for f in changed if f in GENERATED)
    changed = [f for f in changed if f not in GENERATED]
    rom = [f for f in changed if f.startswith(ROM_TREES)]
    shared = [f for f in changed if f in SHARED
              or any(f.startswith(s) for s in SHARED if s.endswith("/"))]
    code = [f for f in changed if f.endswith(".py") or f.endswith(".tcl")]
    data = [f for f in changed if f.endswith(DATA_EXT)]
    if handoff:
        reasons.append("--handoff: every hand-off runs the full battery")
    if shared:
        reasons.append("the gate harness changed: " + " ".join(shared))
    if layout:
        reasons.append("RAM addresses added or moved: " + " ".join(layout[:8])
                       + (f" (+{len(layout) - 8})" if len(layout) > 8 else ""))
    kws, unknown = set(), []
    for f in rom:
        if f.endswith(".asm"):
            h = handlers_of(f)
            if h is None:
                unknown.append(f)        # ⏱ SCOPED with the canary since 2026-10-13
            else:
                kws |= h
        else:
            unknown.append(f)
    if not reasons and (rom or code) and (since is None or since >= DAILY_HOURS):
        reasons.append("the once-a-day rule: "
                       + ("no full green on record" if since is None
                          else f"{since:.0f} h since the last full green"))
    if reasons:
        return "FULL", reasons, sorted(suites), sorted(
            EXCLUDED5 if (rom or shared) else ())
    if not rom and not code and not data and not disk_moved:
        return "STATIC", ["no ROM, probe or tool change"], [], []
    if disk_moved:
        pick |= set(DISK_CANARY)
        reasons.append("disk.rom rebuilt against a regenerated ABI: the disk canary")
    for t, files in suites.items():
        hit = [f for f in code if f in files]
        if hit:
            pick.add(t)
        if kws and any(mentions(own.get(t, ()), k, read) for k in kws):
            pick.add(t)
        for f in data:   # D-PLANDATA
            if f.startswith(LADDER_DIR) and LADDER_RUNNER in own.get(t, ()):
                pick.add(t)
            elif any(f in (read(g) if read else _text(g)) for g in files):
                pick.add(t)
    if rom:
        pick |= set(c for c in CANARY if c in suites)
        if kws:
            reasons.append("ROM change in handler(s): " + " ".join(sorted(kws)))
        if unknown:
            reasons.append("ROM change with no enclosing ex_ handler (canary only, "
                           "the daily FULL backs it): " + " ".join(unknown))
    if code:
        reasons.append("probe/tool change: " + " ".join(code))
    if data:
        reasons.append("program (data) change: " + " ".join(data))
    emu = sorted(t for t in pick if t not in EXCLUDED5)
    x5 = sorted(t for t in pick if t in EXCLUDED5)
    return "SCOPED", reasons, emu, x5


def selftest():
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and cond
    files = {"width-acceptance": {"probes/basic/basic_probe_width.py", "probes/lib/omsx_repl.py"},
             "math-acceptance": {"probes/basic/basic_probe_math.py", "probes/lib/helper.py"},
             "error-acceptance": {"probes/basic/basic_probe_error.py"},
             "diskbasic-acceptance": {"probes/disk/diskbasic_acceptance.py"}}
    text = {"probes/basic/basic_probe_width.py": 'rows = ["WIDTH 37"]',
            "probes/basic/basic_probe_math.py": "SQR(4) and COLOR in a comment",
            "probes/basic/basic_probe_error.py": "ERROR 7",
            "probes/disk/diskbasic_acceptance.py": "FILES"}
    rd = lambda p: text.get(p, "")
    h_width = lambda f: {"WIDTH"}
    m, r, e, x = plan(["TODO.md", "docs/a.md"], files, h_width, 0, read=rd)
    arm("P1 docs-only -> STATIC, no emulator suite", m == "STATIC" and e == [])
    m, r, e, x = plan(["probes/lib/omsx_repl.py"], files, h_width, 0, read=rd)
    arm("P2 NEGATIVE: the harness is shared -> FULL", m == "FULL")
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, 0, read=rd)
    arm("P3 a WIDTH-handler change -> SCOPED: the WIDTH suite + the canary, "
        "not math", m == "SCOPED" and "width-acceptance" in e
        and "error-acceptance" in e and "math-acceptance" not in e)
    m, r, e, x = plan(["basic/screen.asm"], files, lambda f: None, 0, read=rd)
    arm("P4 an asm change outside any ex_ handler -> SCOPED with the canary "
        "(⏱ 2026-10-13: was FULL; the daily FULL backs it)",
        m == "SCOPED" and "error-acceptance" in e and "math-acceptance" not in e)
    m, r, e, x = plan(["basic/interp.asm"], files, lambda f: None, 0, read=rd)
    arm("P4b interpreter shared code with no RAM move -> SCOPED (⏱ was FULL)",
        m == "SCOPED")
    m, r, e, x = plan(["basic/sysvars.inc"], files, lambda f: None, 0, read=rd,
                      layout=["FSECTOR_BUF"])
    arm("P4c NEGATIVE: a RAM-address move -> FULL with the five excluded suites",
        m == "FULL" and x == sorted(EXCLUDED5))
    _diff = ("--- a/basic/sysvars.inc\n+++ b/basic/sysvars.inc\n"
             "-FSECTOR_BUF     equ     $E5C0   ; buf\n+FSECTOR_BUF     equ     $E36A   ; buf\n"
             "-GFX_DFCAP       equ     8\n+GFX_DFCAP       equ     9\n"
             "-ISRCH_B         equ     ISRCH_A + 2 ; $E3E3\n+ISRCH_B         equ     ISRCH_A + 2 ; $E7E3\n"
             "+NEW_CELL        equ     $EB46   ; new (2)\n-OLD_CELL        equ     $EB2F   ; gone\n")
    _vals = {"FSECTOR_BUF": 0xE36A, "GFX_DFCAP": 9, "NEW_CELL": 0xEB46}.get
    arm("P15 layout_moves: a changed RAM literal and an ADDED cell are moves; a "
        "constant, a comment-only edit and a REMOVED cell are not",
        layout_moves(_diff, _vals) == ["FSECTOR_BUF", "NEW_CELL"])
    m, r, e, x = plan(["probes/lib/helper.py"], files, h_width, 0, read=rd)
    arm("P5 a probes/lib file is shared even when only one suite imports it",
        m == "FULL")
    m, r, e, x = plan(["probes/basic/basic_probe_math.py"], files, h_width, 0, read=rd)
    arm("P6 a probe change selects ITS suite and not an unrelated one",
        m == "SCOPED" and e == ["math-acceptance"])
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, float(DAILY_HOURS), read=rd)
    arm("P7 NEGATIVE: 24 h since the last full green -> FULL", m == "FULL")
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, DAILY_HOURS - 0.5, read=rd)
    arm("P7b 23.5 h since the last full green -> still SCOPED", m == "SCOPED")
    m, r, e, x = plan(["TODO.md"], files, h_width, 99.0, read=rd)
    arm("P7c a docs-only change never triggers the daily FULL by itself", m == "STATIC")
    # D-PLANDATA: a program a suite runs is an input
    fl = dict(files, **{"programs-acceptance": {"probes/programs/run_programs.py"},
                        "catcopy-acceptance": {"probes/basic/basic_probe_catcopy.py",
                                               "probes/programs/run_programs.py"}})
    ow = dict(files, **{"programs-acceptance": {"probes/programs/run_programs.py"},
                        "catcopy-acceptance": {"probes/basic/basic_probe_catcopy.py"}})
    tx = dict(text, **{"probes/basic/basic_probe_catcopy.py": '"scratchpad/catcopy_temp.bas"'})
    rdx = lambda p: tx.get(p, "")
    m, r, e, x = plan(["probes/programs/L9_new.bas"], fl, h_width, 0, read=rdx, own=ow)
    arm("P16 a new ladder program -> SCOPED with programs-acceptance only (the "
        "catcopy probe IMPORTS the runner but does not run the ladder)",
        m == "SCOPED" and e == ["programs-acceptance"])
    m, r, e, x = plan(["scratchpad/catcopy_temp.bas"], fl, h_width, 0, read=rdx, own=ow)
    arm("P16b a .bas a probe names by path -> that suite",
        m == "SCOPED" and e == ["catcopy-acceptance"])
    m, r, e, x = plan(["scratchpad/kwsweep-rig-carry.json"], fl, h_width, 0, read=rdx, own=ow)
    arm("P16c NEGATIVE: a non-.bas data file plans nothing (STATIC)", m == "STATIC")
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, None, read=rd)
    arm("P8 NEGATIVE: no full green on record -> FULL, never 'assume recent'",
        m == "FULL")
    sw = dict(files, kwsweep={"probes/basic/basic_probe_kwsweep.py"},
              kwtime={"probes/basic/basic_probe_kwtime.py"},
              kwram={"probes/basic/basic_probe_kwram.py"})
    m, r, e, x = plan(["basic/screen.asm"], sw, h_width, 0, read=rd)
    arm("P-STATICEMU a handler-local ROM change schedules kwsweep -- and NOT "
        "kwtime / kwram (⏱ daily since 2026-10-13)",
        m == "SCOPED" and "kwsweep" in e and not {"kwtime", "kwram"} & set(e))
    m, r, e, x = plan(["TODO.md", "docs/a.md"], sw, h_width, 0, read=rd)
    arm("P-STATICEMU NEGATIVE: a docs-only plan schedules NO emulator unit, sweeps "
        "included", m == "STATIC" and e == [])
    m, r, e, x = plan(["probes/basic/basic_probe_math.py"], sw, h_width, 0, read=rd)
    arm("P-STATICEMU a probe-only change does not drag the sweeps in",
        m == "SCOPED" and e == ["math-acceptance"])
    m, r, e, x = plan(["TODO.md"], files, h_width, 0, handoff=True, read=rd)
    arm("P9 --handoff forces FULL even on docs", m == "FULL")
    arm("P10 the handler walk: a local label inside ex_width belongs to WIDTH",
        changed_handlers("x.asm", "ex_width:\n  nop\nwid_bound:\n  cp b\n", [(4, 1)])
        == {"WIDTH"})
    arm("P11 NEGATIVE: a line above every ex_ label has no handler -> None",
        changed_handlers("x.asm", "helper:\n  nop\nex_cls:\n  ret\n", [(2, 1)]) is None)
    _src = {"a.py": "import b", "b.py": "from c import x", "c.py": "", "d.py": ""}
    _res = {"b": "b.py", "c": "c.py", "d": "d.py"}.get
    arm("P12 the closure follows imports TRANSITIVELY (a -> b -> c) and adds "
        "nothing unimported (NEGATIVE: d)",
        closure("a.py", read=lambda p: _src.get(p, ""), resolve=_res)
        == {"a.py", "b.py", "c.py"})
    _src2 = {"w.py": 'CHILD = os.path.join(HERE, "kid.py")\nimport os',
             "kid.py": "", "other.py": ""}
    _res2 = {"kid": "kid.py", "other": "other.py"}.get
    arm("P12b a child run BY PATH (a quoted `kid.py`) is in the closure "
        "(D-PLANCHILD); NEGATIVE: an unnamed module is not",
        closure("w.py", read=lambda p: _src2.get(p, ""), resolve=_res2)
        == {"w.py", "kid.py"})
    _own = {t: {f for f in fs if not f.startswith("probes/lib/")} for t, fs in files.items()}
    text["probes/lib/omsx_repl.py"] = "a comment naming WIDTH"
    files["math-acceptance"] |= {"probes/lib/omsx_repl.py"}
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, 0, read=rd, own=_own)
    arm("P14 NEGATIVE: a keyword named only in a SHARED LIBRARY's comment does not "
        "select the suite (the 81-of-90 fault)", m == "SCOPED"
        and "width-acceptance" in e and "math-acceptance" not in e)
    m, r, e, x = plan(["basic/screen.asm", "disk/basic-resident-abi.inc",
                       "zerobas-main-eu.bps", "tools/kwforms.py"], files, h_width, 1, read=rd)
    arm("P13 D-WIDTHKEEP's real shape (a handler + the regenerated ABI + patches) "
        "is SCOPED with the disk canary, not FULL",
        m == "SCOPED" and "width-acceptance" in e and set(DISK_CANARY) <= set(x))
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 2


def main(argv):
    if "--selftest" in argv:
        return selftest()
    handoff = "--handoff" in argv
    changed = changed_files()
    targets = list(run_gates.EMULATOR) + list(EXCLUDED5)
    suites, own = suite_files(targets)
    since = hours_since_full()
    layout = layout_moves()
    mode, reasons, emu, x5 = plan(changed, suites, changed_handlers, since, handoff,
                                  own=own, layout=layout)
    print(f"GATE TIER: {mode}")
    for r in reasons:
        print(f"  why: {r}")
    print(f"  hours since the last full green: "
          f"{'unknown' if since is None else f'{since:.1f}'} (full once a day, "
          f"at every hand-off, and on a RAM-address move)")
    if mode == "SCOPED":
        print(f"  emulator suites ({len(emu)}): {' '.join(emu) or '-'}")
    if x5:
        print(f"  excluded-five suites: {' '.join(x5)}")
    if "--run" not in argv:
        return 0
    # ⚠️ LIST LITERALS, NOT A `cmd` VARIABLE: `preflight-check` cannot prove a
    # variable argv is not an openMSX launch, and caught this file's first cut.
    if mode == "STATIC":
        rc = subprocess.run(["python3", "tools/run_gates.py", "--static"],
                            cwd=ROOT).returncode
    elif mode == "FULL":
        rc = subprocess.run(["python3", "tools/run_gates.py", "--full"],
                            cwd=ROOT).returncode
    else:
        skip = ",".join(t for t in run_gates.EMULATOR if t not in emu)
        rc = subprocess.run(["python3", "tools/run_gates.py", "--full",
                             "--exclude", skip], cwd=ROOT).returncode
    for t in x5:
        r = subprocess.run(["make", t], cwd=ROOT, capture_output=True, text=True)
        print(f"{t} exit={r.returncode}")
        # 🔴 D-X5LOG (2026-09-30): a failing suite's output used to be DROPPED.
        # bdos-acceptance exited 2 in a FULL run and was 12/12 green alone, and
        # the failing run had left nothing to read -- "read the log before
        # believing any red" had no log. Keep it whenever the exit is non-zero.
        if r.returncode:
            log = os.path.join(probe_tmp.ROOT, "gate_flakes", f"x5-{t}.log")
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "w", encoding="utf-8") as fh:
                fh.write(r.stdout + r.stderr)
            print(f"  log kept: {log}")
        rc = rc or r.returncode
    print(f"GATE TIER RAN: {mode}" + (f" ({len(emu)} emulator suites)"
                                      if mode == "SCOPED" else ""))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
