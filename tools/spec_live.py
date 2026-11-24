#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""spec_live -- a BIOS or keyword spec page AS a gate (docs/spec-method.md §8 step 2: "spec and test are one table").

    python3 -u tools/spec_live.py [probes/bios/spec/NAME_rules.py ...]   (default: every rules module, the BIOS
       pages' and the keyword pages' -- probes/basic/spec/)

For each page's rules module:
  1. run its cases() once, recording which committed run files (scratchpad/*.out) it reads;
  2. re-run ZEROBAS ONLY for each of them on the current build -- the probe and the row are named in the
     run file's own header line -- and write a live copy: the committed file with its `CAP ours` line
     replaced. The reference's side stays the page's MEASURED values (the committed `CAP ref` line); the
     reference is never re-run, so a gate pays for zerobas's boots only;
  3. evaluate the page's rules on the live copies with tools/spec_rules.py's own `run()`;
  4. require that the rules zerobas fails are EXACTLY the rules the page's "Differences from the
     reference" table names. A rule failing that the page does not list is a REGRESSION; a listed rule
     that now holds is a STALE PAGE (a fix whose page was not updated). Both exit 1.

    python3 -u tools/spec_live.py --keywords [...]   -- the KEYWORD pages (probes/basic/spec/*_rules.py) instead:
       their run files hold one `===== GROUP` section per typed program (probes/basic/spec/ramrec.py); each group is
       re-typed on zerobas only by the probe whose `RUN` names the file, and its `CAP zb  :` line replaced.

    python3 -u tools/spec_live.py --refresh [...]   -- also WRITE each live copy back over its committed run
       file (only zerobas's `CAP ours` / `PRN ours` lines change; the reference's are never touched): after a
       change that moves zerobas's answers on purpose, e.g. D-CBIOS032's rebase on a new C-BIOS. Then
       `tools/spec_rules.py M --write` regenerates the page's tables, and its Differences list is edited.

Exit 0: every page agrees; 1: a disagreement; 2: a probe gave no reading or a run file could not be used.
CLEAN-ROOM: only our probes' capture blocks are read back (probes/bios/biosl_run.py's harness).
"""
import builtins
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "bios"))
sys.path.insert(0, os.path.join(ROOT, "probes", "bios", "spec"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp  # noqa: E402,F401  -- tempfile under the project's temp root (temp-root-check)
import spec_rules  # noqa: E402
import biosl_run  # noqa: E402

SCRATCH = os.path.join(ROOT, "scratchpad")
HEADER = re.compile(r"^===== (\S+\.asm) (nodisk|disk|cf3300|nms8250): ")
# rows that are REFERENCE-ONLY (a further reference machine; tools/spec_rules.py's c.ref_only): no rule reads their
# `CAP ours`, so they are NOT re-run -- the committed line stays (D-DISKFORCBIOS (b): the NMS 8250's drive)
REF_ONLY_ROWS = {"nms8250"}
CAP_OURS = re.compile(r"^  CAP ours: [0-9a-fA-F]+$", re.M)
KW_SPEC = os.path.join(ROOT, "probes", "basic", "spec")
KW_GROUP = re.compile(r"^===== (\w+)$")
KW_CAP_ZB = re.compile(r"^  CAP zb  : (\w+)$")
RULE_ID = re.compile(r"\bR\d?-[A-Z0-9][A-Z0-9-]*[A-Z0-9]\b")


def _with_open(redirect, record):
    """builtins.open, recording every scratchpad/*.out read and redirecting the live ones"""
    real = builtins.open

    def op(path, *a, **k):
        p = os.path.abspath(path) if isinstance(path, str) else path
        if isinstance(p, str) and p.startswith(SCRATCH + os.sep) and p.endswith(".out"):
            record.add(p)
            if p in redirect:
                return real(redirect[p], *a, **k)
        return real(path, *a, **k)
    return real, op


def evaluate(path, redirect):
    """(module, {rule id: [zb failing case ids]}, run files read)"""
    record = set()
    real, op = _with_open(redirect, record)
    for name in [n for n in sys.modules if n.endswith("_cases") or n.endswith("_model")]:
        del sys.modules[name]              # a fresh model module per evaluation (they cache loads)
    builtins.open = op
    try:
        mod = spec_rules.load(path)
        out, _, _ = spec_rules.run(mod)
    finally:
        builtins.open = real
    return mod, {r.id: zb_bad for r, _, _, zb_bad in out}, record


def page_listed(mod):
    page = os.path.join(ROOT, mod.PAGE)
    text = open(page).read()
    m = re.search(r"^## Differences from the reference\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        return set()
    listed = set()
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2 and not set(cells[1]) <= set("-"):
            listed |= set(RULE_ID.findall(cells[1]))
    # a keyword page lists its differences as bullets; a rule that DIFFERS is cited as "rule R-X-Y" / "rules R-X-Y,
    # R-X-Z" (a run of one keyword's rules may be shortened after the first: "rules R-RND-VALUE, -SEED / -REPEAT");
    # a bare id is context ("its own result agrees (R-ABS-ODD)", "both machines hold R-ATN-NEAR") and is not listed
    rid = r"R\d?-[A-Z0-9]+-[A-Z0-9][A-Z0-9-]*[A-Z0-9]"
    prose = "\n".join(l for l in m.group(1).splitlines() if not l.lstrip().startswith("|"))
    # ... and inside a parenthesis that opens with "rule" / "rules", every rule cited counts, case references between
    # them: "(rule R-ABS-INT, KMA MI ABS -32768; R-ABS-FORMS, KMA FX 16)"
    for par in re.finditer(r"\(rules?\s((?:[^()]|\([^()]*\))*)\)", prose):  # one nested level: `ABS(&H8000)`
        prefix = None
        for tok in re.findall(rf"{rid}|(?<=[,/]\s)-[A-Z][A-Z0-9-]*[A-Z0-9]", par.group(1)):
            if tok.startswith("R"):
                listed.add(tok)
                prefix = re.match(r"R\d?-[A-Z0-9]+", tok).group(0)
            elif prefix:
                listed.add(prefix + tok)
    for run in re.finditer(rf"\brules?\s+({rid}(?:\s*(?:,|/|and)\s*(?:{rid}|-[A-Z][A-Z0-9-]*[A-Z0-9]))*)",
                           prose):
        prefix = None
        for tok in re.findall(rf"{rid}|-[A-Z][A-Z0-9-]*[A-Z0-9]", run.group(1)):
            if tok.startswith("R"):
                listed.add(tok)
                prefix = re.match(r"R\d?-[A-Z0-9]+", tok).group(0)
            elif prefix:
                listed.add(prefix + tok)
    return listed


def live_run(run_file, td):
    """a live copy of run_file with zerobas's CAP re-measured on the current build, row by row (a
    file may hold a nodisk and a disk section, each a header line and one `CAP ours` line)"""
    import time
    text = open(run_file).read()
    lines = text.splitlines(keepends=True)
    heads = [i for i, l in enumerate(lines) if HEADER.search(l)]
    caps = [i for i, l in enumerate(lines) if CAP_OURS.match(l.rstrip("\n"))]
    if not heads or len(caps) != len(heads) or any(not (h < c) for h, c in zip(heads, caps)):
        raise SystemExit(f"spec-live: {os.path.relpath(run_file, ROOT)}: {len(heads)} header(s), {len(caps)} "
                         f"`CAP ours` line(s) -- not one per row; cannot re-run it")
    for h, c in zip(heads, caps):
        m = HEADER.search(lines[h])
        asm, row = m.group(1), m.group(2)
        if row in REF_ONLY_ROWS:
            sys.stdout.write(f"  live {os.path.basename(run_file)} {row}: reference-only row, not re-run\n")
            continue
        st = biosl_run.settings(open(os.path.join(ROOT, asm)).read())
        rom = biosl_run.build(os.path.join(ROOT, asm), td)
        t0 = time.time()
        zb = biosl_run.run(biosl_run.ROWS[row][1], rom, st, td, disk=(row != "nodisk"))
        if not zb or zb.get("DONE") != "165":
            sys.stdout.write(f"  NO READING: {asm} {row} (DONE {zb and zb.get('DONE')})\n")
            return None
        b = bytes.fromhex(zb["CAP"])
        cap = b[:max(32, len(b.rstrip(b"\0")))].hex()
        same = lines[c].split(":", 1)[1].strip() == cap
        if st["printer"]:
            pl = [lines[i] for i in range(c, next((i for i in heads if i > c), len(lines)))
                  if lines[i].startswith("  PRN ours:")]
            same = same and bool(pl) and pl[0].split(":", 1)[1].strip() == zb["PRN"]
        # one write per line: the pool's threads would otherwise run two lines together (print writes the newline
        # on its own)
        sys.stdout.write(f"  live {os.path.basename(run_file)} {row}: {os.path.basename(asm)} {time.time() - t0:.1f} s, "
                         f"zerobas {'as committed' if same else 'CHANGED since the committed run'}\n")
        lines[c] = f"  CAP ours: {cap}\n"
        if st["printer"]:                  # the section's `PRN ours:` line, re-measured too
            end = next((i for i in heads if i > c), len(lines))
            p = [i for i in range(c, end) if lines[i].startswith("  PRN ours:")]
            if len(p) != 1:
                raise SystemExit(f"spec-live: {os.path.relpath(run_file, ROOT)} {row}: @printer but "
                                 f"{len(p)} `PRN ours` line(s)")
            lines[p[0]] = f"  PRN ours: {zb['PRN']}\n"
    live = os.path.join(td, os.path.basename(run_file))
    with open(live, "w") as f:
        f.write("".join(lines))
    return live


def kw_probes():
    """{run file basename: probe module} -- each keyword probe names its run file in `RUN = "..."`"""
    out = {}
    for f in sorted(os.listdir(KW_SPEC)):
        if not (f.startswith("k") and f.endswith(".py")) or f.endswith(("_model.py", "_controls.py")):
            continue
        m = re.search(r'^RUN = "([^"]+)"', open(os.path.join(KW_SPEC, f)).read(), re.M)
        if m:
            out[m.group(1)] = f[:-3]
    return out


def kw_groups(run_file):
    """the `===== GROUP` sections of a keyword run file, in file order"""
    return [m.group(1) for m in (KW_GROUP.match(l.rstrip("\n")) for l in open(run_file)) if m]


def is_kw_run(run_file):
    return os.path.basename(run_file) in kw_probes()


def kw_live_group(run_file, group):
    """zerobas's capture of one group of a keyword run file, re-typed on the current build (hex), or None"""
    import importlib
    import time
    if KW_SPEC not in sys.path:
        sys.path.insert(0, KW_SPEC)
    probe = importlib.import_module(kw_probes()[os.path.basename(run_file)])
    import ramrec
    lines, cases = probe.program(group)[:2]
    rec = probe.REC[group] if isinstance(probe.REC, dict) else probe.REC
    t0 = time.time()
    cap = ramrec.measure(lines, len(cases), rec, probe.GAPS[group], machines=(("zb", ramrec.ZB),))["zb"]
    recs, why = ramrec.frame(cap, len(cases), rec)
    sys.stdout.write(f"  live {os.path.basename(run_file)} {group}: {len(cases)} cases, {time.time() - t0:.1f} s"
                     f"{'' if recs is not None else ', NO READING: ' + why}\n")
    return cap if recs is not None else None


def kw_assemble(run_file, caps, td):
    """the live copy of a keyword run file: each group's `CAP zb  :` line replaced by caps[group]"""
    out, group, changed = [], None, []
    for line in open(run_file):
        m = KW_GROUP.match(line.rstrip("\n"))
        if m:
            group = m.group(1)
        c = KW_CAP_ZB.match(line.rstrip("\n"))
        if c and group in caps:
            if c.group(1) != caps[group]:
                changed.append(group)
            line = f"  CAP zb  : {caps[group]}\n"
        out.append(line)
    sys.stdout.write(f"  live {os.path.basename(run_file)}: zerobas "
                     f"{'CHANGED since the committed run in ' + ', '.join(changed) if changed else 'as committed'}\n")
    live = os.path.join(td, os.path.basename(run_file))
    with open(live, "w") as f:
        f.write("".join(out))
    return live


def main(argv):
    refresh = "--refresh" in argv
    keywords = "--keywords" in argv
    argv = [a for a in argv if a not in ("--refresh", "--keywords")]
    # default: every BIOS page AND every keyword page; --keywords: the keyword pages only
    sdirs = [KW_SPEC] if keywords else [os.path.join(ROOT, "probes", "bios", "spec"), KW_SPEC]
    mods = argv or [os.path.join(d, f) for d in sdirs for f in sorted(os.listdir(d)) if f.endswith("_rules.py")]
    td = tempfile.mkdtemp(prefix="spec_live_")
    redirect, rc = {}, 0
    try:
        # ⏱ D-SUITEWIN (2026-11-22): every run file's zerobas re-run is independent, so they run on a small pool
        # (SPEC_LIVE_JOBS, default 4; 1 = one at a time) -- 193 s in f6ad987d's FULL battery. Each file gets its OWN
        # temp dir: a probe's run 1 and run 2 (disk / cf3300) build the same .asm, which one shared dir would mix.
        # evaluate() swaps builtins.open, so collecting the files and judging the pages stay serial.
        files_of, order = {}, []
        for path in mods:
            _, _, files = evaluate(path, {})
            files_of[path] = files
            for f in sorted(files):
                if f not in order:
                    order.append(f)
        import concurrent.futures
        jobs = max(1, int(os.environ.get("SPEC_LIVE_JOBS") or 4))
        dirs = {f: os.path.join(td, str(i)) for i, f in enumerate(order)}
        for d in dirs.values():
            os.makedirs(d)
        # a keyword run file is re-typed GROUP by group (one boot each), so its groups are the pool's tasks
        tasks = [(f, g) for f in order if is_kw_run(f) for g in kw_groups(f)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
            kw = dict(zip(tasks, ex.map(lambda t: kw_live_group(*t), tasks)))
            bios = [f for f in order if not is_kw_run(f)]
            lives_of = dict(zip(bios, ex.map(lambda f: live_run(f, dirs[f]), bios)))
        for f in order:
            if is_kw_run(f):
                caps = {g: kw[(f, g)] for g in kw_groups(f)}
                lives_of[f] = None if any(v is None for v in caps.values()) else kw_assemble(f, caps, dirs[f])
        lives = [lives_of[f] for f in order]
        for f, live in zip(order, lives):
            if live is None:
                rc = 2
            else:
                redirect[f] = live
                if refresh and open(live).read() != open(f).read():
                    shutil.copyfile(live, f)
                    sys.stdout.write(f"  REFRESHED {os.path.relpath(f, ROOT)}\n")
        for path in mods:
            files = files_of[path]
            mod, fails, _ = evaluate(path, redirect)
            failing = {r for r, bad in fails.items() if bad}
            listed = page_listed(mod)
            regress = sorted(failing - listed)
            stale = sorted(listed & set(fails) - failing)
            tag = "OK  " if not (regress or stale) else "FAIL"
            print(f"{tag} {mod.PAGE}: {len(fails)} rules, {len(failing)} failing on zerobas "
                  f"(live, {len(files)} run file(s))")
            for r in regress:
                print(f"     REGRESSION {r}: fails on zerobas ({', '.join(fails[r][:4])}) but the page lists "
                      f"no difference for it")
            for r in stale:
                print(f"     STALE PAGE {r}: the page lists it as a difference, but it holds on zerobas")
            if regress or stale:
                rc = max(rc, 1)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print(f"===== spec-live: {'ALL PAGES AGREE' if rc == 0 else 'DISAGREEMENT' if rc == 1 else 'NO READING'} =====")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
