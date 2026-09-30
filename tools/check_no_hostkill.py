#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PKILLGATE -- no unit the gate pool runs may kill what it did not start.

🔴 WHY THIS EXISTS (2026-09-30, D-PKILL). `eofcas-acceptance` was built from a
scratchpad probe whose rig began `subprocess.run(["pkill", "-9", "openmsx"])`.
Standalone that is harmless. In the PARALLEL pool it killed every emulator on
the host, so kwtime read 51 and then 32 rows HANG in two FULL batteries. The red
surfaced two units away from its cause and was first blamed on host load.

For every unit in tools/run_gates.py's lists (the same parse
check_battery_membership uses), the Makefile recipe's `python3 <file>.py`
scripts are read, plus every in-repo module they import, transitively.
A host-wide kill -- `pkill`, `killall`, or a `kill` of a pid list from pgrep --
in CODE, not a comment, is refused. Killing the process group of a child you
started (os.killpg on your own Popen) is the sanctioned form and is not matched.

  python3 tools/check_no_hostkill.py            # the check
  python3 tools/check_no_hostkill.py --selftest # a planted pkill must be caught
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir
from check_battery_membership import battery      # noqa: E402

KILL = re.compile(r"""["'](pkill|killall)["']|os\.system\(\s*["'](pkill|killall)\b|\bpgrep\b.*\bkill\b""")
SEARCH = ("probes/lib", "probes/basic", "probes/disk", "probes", "tools", "scratchpad")
MIN_UNITS = 40          # a smaller battery means the parse broke


def recipes(mk: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    target = None
    for line in mk.splitlines():
        m = re.match(r"^([A-Za-z0-9_./-]+):", line)
        if m and not line.startswith("\t"):
            target = m.group(1)
            out.setdefault(target, [])
        elif line.startswith("\t") and target:
            out[target].append(line)
    return out


def code_lines(path: str):
    for n, raw in enumerate(open(path, errors="replace"), 1):
        s = raw.split("#", 1)[0] if not raw.lstrip().startswith(("'", '"')) else raw
        yield n, s


def local_module(name: str, root: str, here: str):
    for d in (os.path.dirname(here),) + tuple(os.path.join(root, s) for s in SEARCH):
        p = os.path.join(d, name + ".py")
        if os.path.exists(p):
            return p
    return None


def closure(script: str, root: str) -> set[str]:
    seen, todo = set(), [script]
    while todo:
        p = todo.pop()
        if p in seen or not os.path.exists(p):
            continue
        seen.add(p)
        for _, s in code_lines(p):
            for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w., ]+))", s):
                names = [m.group(1)] if m.group(1) else [x.strip().split(" ")[0] for x in m.group(2).split(",")]
                for nm in names:
                    q = local_module(nm.split(".")[0], root, p)
                    if q:
                        todo.append(q)
    return seen


def scan(root: str, units: set[str]) -> list[str]:
    mk = open(os.path.join(root, "Makefile")).read()
    rec = recipes(mk)
    bad = []
    for u in sorted(units):
        for line in rec.get(u, []):
            for rel in re.findall(r"python3\s+(?:-u\s+)?([\w./-]+\.py)", line):
                for f in sorted(closure(os.path.join(root, rel), root)):
                    # this checker NAMES the pattern (its docstring and its planted
                    # fixture); registered as a unit, it read itself as a finding
                    if os.path.basename(f) == os.path.basename(__file__):
                        continue
                    for n, s in code_lines(f):
                        if KILL.search(s):
                            bad.append(f"{u}: {os.path.relpath(f, root)}:{n}: {s.strip()}")
    return sorted(set(bad))


def check(root=ROOT) -> int:
    units = battery(open(os.path.join(root, "tools", "run_gates.py")).read())
    if len(units) < MIN_UNITS:
        print(f"🔴 check_no_hostkill: only {len(units)} battery units parsed -- the parse broke")
        return 2
    bad = scan(root, units)
    if bad:
        print("🔴 A BATTERY UNIT KILLS PROCESSES IT DID NOT START (D-PKILLGATE):")
        for b in bad:
            print("   ", b)
        print("  Kill your OWN child's process group (os.killpg on its Popen), never by name.")
        return 1
    print(f"no-hostkill: {len(units)} battery units, their scripts and in-repo imports -- no host-wide kill")
    return 0


def selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="hostkill_")
    os.makedirs(os.path.join(tmp, "probes", "lib"))
    open(os.path.join(tmp, "probes", "lib", "helper.py"), "w").write(
        'import subprocess\nsubprocess.run(["pkill", "-9", "openmsx"])\n')
    open(os.path.join(tmp, "probes", "lib", "clean.py"), "w").write(
        '# pkill is only mentioned in this comment\nimport os\n')
    open(os.path.join(tmp, "probes", "a.py"), "w").write("import helper\n")
    open(os.path.join(tmp, "probes", "b.py"), "w").write("import clean\n")
    open(os.path.join(tmp, "Makefile"), "w").write(
        "a-acceptance:\n\tpython3 probes/a.py\n\nb-acceptance:\n\tpython3 probes/b.py\n")
    hit = scan(tmp, {"a-acceptance"})
    miss = scan(tmp, {"b-acceptance"})
    shutil.rmtree(tmp, ignore_errors=True)
    ok = bool(hit) and "helper.py" in hit[0] and not miss
    print(f"selftest: planted pkill via an import {'CAUGHT' if hit else 'MISSED'}; "
          f"a comment-only mention {'passed' if not miss else 'FLAGGED'} -- "
          f"{'✅' if ok else '🔴'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else check())
