#!/usr/bin/env python3
r"""pick_gates — which battery does THIS change need? (D-GATESCOPE)

🏗️ RULED BY JOOST, 2026-09-24: *"running the full battery takes a really long
time ... only running the full after genuinely large or risky fixes"* -> scoped
batteries, the full one on risk, **and at least every 5th commit**:

  change                              runs
  docs / TODO / scratchpad only       STATIC  -- the static tier
  probe or tool, no ROM change        SCOPED  -- static + the emulator suites whose
                                                 scripts IMPORT a changed file
  ROM change inside one handler       SCOPED  -- static + suites that mention that
                                                 keyword + a fixed CANARY set
  shared code / unknown blast radius  FULL    -- (+ the five excluded suites)
  --handoff, or the 5th commit since the last full green   FULL

🔴 WHY A BACKSTOP AT ALL: on 2026-08-26 a fix that was right by its own gate broke
a DIFFERENT suite three times, and a later one turned 32 other suites red. Each
was caught by a gate the change did not obviously touch. Scoping trades that
coverage for time; the every-5th rule and the shared-code list bound the trade.
⚠️ WHEN IN DOUBT, FULL: an asm change whose enclosing handler cannot be named is
an unknown blast radius, and is treated as shared.

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

EVERY_NTH = 5                  # Joost: "5 commits"
# Shared code: a change here can move any suite. Prefix entries end in "/".
SHARED = ("basic/interp.asm", "basic/expr.asm", "basic/sysvars.inc",
          "basic/main.asm", "basic/str-engine.asm", "sub/sub.asm",
          "disk/kernel.asm", "Makefile", "tools/run_gates.py",
          "probes/lib/")
ROM_TREES = ("basic/", "sub/", "disk/")
# Broad, FAST suites that exercise the interpreter core -- the canary for a
# handler-local ROM change (each measured well under a minute in the battery).
CANARY = ("error-acceptance", "string-acceptance", "runline-acceptance",
          "keystr-acceptance", "cursor-acceptance")
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
MODULE_DIRS = ("probes/lib", "probes/basic", "probes/disk", "tools", "scratchpad")
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


def mentions(files, word, read=None):
    if read is None:
        def read(p):
            try:
                return open(os.path.join(ROOT, p), errors="replace").read()
            except OSError:
                return ""
    pat = re.compile(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])")
    return any(pat.search(read(f)) for f in files)


def commits_since_full():
    try:
        import json
        with open(run_gates.LAST_GREEN) as fh:
            sha = json.load(fh).get("sha")
    except (OSError, ValueError):
        return None
    if not sha:
        return None
    n = git("rev-list", "--count", f"{sha}..HEAD").strip()
    return int(n) if n.isdigit() else None


def plan(changed, suites, handlers_of, since, handoff=False, read=None, own=None):
    """-> (mode, reasons, emulator suites, excluded-five suites).

    Pure: `suites` is target->files, `handlers_of(path)` the keyword set or None,
    `since` the commits since the last full green (None = unknown), `own` the
    suites' own scripts for the keyword match (default: `suites`)."""
    own = suites if own is None else own
    reasons, pick = [], set()
    disk_moved = any(f.startswith("disk/") for f in changed if f in GENERATED)
    changed = [f for f in changed if f not in GENERATED]
    rom = [f for f in changed if f.startswith(ROM_TREES)]
    shared = [f for f in changed if f in SHARED
              or any(f.startswith(s) for s in SHARED if s.endswith("/"))]
    code = [f for f in changed if f.endswith(".py") or f.endswith(".tcl")]
    if handoff:
        reasons.append("--handoff: every hand-off runs the full battery")
    if shared:
        reasons.append("shared code changed: " + " ".join(shared))
    kws = set()
    for f in rom:
        if f in shared:
            continue
        if f.endswith(".asm"):
            h = handlers_of(f)
            if h is None:
                reasons.append(f"{f}: a changed line has no enclosing ex_ handler "
                               "-- unknown blast radius, treated as shared")
            else:
                kws |= h
        else:
            reasons.append(f"{f}: a non-asm ROM input -- treated as shared")
    if not reasons and (rom or code) and (since is None or since >= EVERY_NTH - 1):
        reasons.append("the every-5th rule: "
                       + ("no full green on record with a sha" if since is None
                          else f"{since} commit(s) since the last full green"))
    if reasons:
        return "FULL", reasons, sorted(suites), sorted(
            EXCLUDED5 if (rom or shared) else ())
    if not rom and not code and not disk_moved:
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
    if rom:
        pick |= set(c for c in CANARY if c in suites)
        reasons.append("handler-local ROM change: " + " ".join(sorted(kws)))
    if code:
        reasons.append("probe/tool change: " + " ".join(code))
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
    arm("P4 NEGATIVE: an asm change outside any ex_ handler -> FULL (unknown radius)",
        m == "FULL" and x == sorted(EXCLUDED5))
    m, r, e, x = plan(["probes/lib/helper.py"], files, h_width, 0, read=rd)
    arm("P5 a probes/lib file is shared even when only one suite imports it",
        m == "FULL")
    m, r, e, x = plan(["probes/basic/basic_probe_math.py"], files, h_width, 0, read=rd)
    arm("P6 a probe change selects ITS suite and not an unrelated one",
        m == "SCOPED" and e == ["math-acceptance"])
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, EVERY_NTH - 1, read=rd)
    arm("P7 NEGATIVE: the 5th commit since the last full green -> FULL", m == "FULL")
    m, r, e, x = plan(["basic/screen.asm"], files, h_width, None, read=rd)
    arm("P8 NEGATIVE: no sha on record -> FULL, never 'assume recent'", m == "FULL")
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
    since = commits_since_full()
    mode, reasons, emu, x5 = plan(changed, suites, changed_handlers, since, handoff,
                                  own=own)
    print(f"GATE TIER: {mode}")
    for r in reasons:
        print(f"  why: {r}")
    print(f"  commits since the last full green: "
          f"{'unknown' if since is None else since} (full every {EVERY_NTH})")
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
        rc = rc or r.returncode
    print(f"GATE TIER RAN: {mode}" + (f" ({len(emu)} emulator suites)"
                                      if mode == "SCOPED" else ""))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
