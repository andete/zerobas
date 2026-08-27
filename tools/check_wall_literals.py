#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""A wall figure hardcoded OUTSIDE TODO.md is unpoliced by design. This polices it.

D-DUPSPAN2 §5.2 found `LOW_CEILING = 0x3FE5` in tools/gen_resident_abi.py under a
comment naming `__MEAS_LOW_END` -- a label the build MEASURES on every run. The
literal had never tracked it and was 65 B stale, weakening the guard by exactly
that much. `make wall-assertion-check` could not see it: that tool scopes itself
to TODO.md's `- [ ]` items by design (its §SCOPE), because that is where a stale
figure misleads the next SLICE. A stale figure inside a GATE, a PROBE or a source
comment misleads the GATE instead, and nobody reads it.

D-WALLIT (2026-08-27) swept the class. It was not empty:

  probes/basic/basic_probe_cas_verbs.py  STRSCR = $E360, but the build says $E26D
      -- 243 B into the buffer instead of at its header. BOTH STRSCR cases read
      all-$FF and had been FAILING; the probe is README-listed but in NO battery,
      so nothing ever read its rc. Corrected: 4 FAIL/2 PASS -> 6/6 PASS, and the
      BASIC was right all along.
  probes/basic/basic_probe_clear.py      FOUR of six sysvars pointed at the wrong
      cell ($F691/$F693/$FC4C dead, $FC48 not the ceiling). Case 3 reported two
      DEAD cells as `SAME` -- agreement produced by two zeroes.
  basic/sysvars.inc                      the GFX_SPATN..GFX_SFLAGS chain carried
      hand-copied addresses 2 B high, and a host-buffer comment said basic-core
      RAM "tops out at STRSCR $E360..$E380" -- wrong span AND wrong cell.

TWO RULES, each with its own denominator. Both compare a HAND COPY against the
value the assembler actually resolved, read from the sym files the build writes.

  A  PY-BINDING   `NAME = <literal>` in tools/ or probes/, where NAME is a build
                  symbol.                          93 anchored of 626 assignments
  B  ASM-COMMENT  `NAME equ <expr>   ; $XXXX...` -- the house convention where the
                  comment annotates THIS row's resolved address.     64 rows

⚠️ THOSE TWO NUMBERS ARE THIS TOOL'S, NOT THE SCOUT'S. The D-WALLIT scout
(scratchpad/wall_literal_sweep.py) reports `960 anchored of 1464` for a WIDER
rule -- asm `equ` rows as well as Python, and an anchor allowed to be a symbol
NAMED IN THE COMMENT rather than the assigned name. That wider anchor is what
produced the noise this tool declines to inherit; quoting its denominator here
would describe a rule the gate does not run.

Rule B takes only a LEADING `$XXXX` (`; $E419: ...`). A `$XXXX` anywhere else in
the comment is a VALUE or a neighbour's address, not a claim about this row: over
the 888 commented `equ` rows the loose form gave 16 DIFFER of which 12 were that,
the tight form gives 65 rows and 1 -- a span (`; $E9C9..$E9FA = 50 bytes`), which
the `..` test below excludes. That is the whole difference between a gate people
believe and one they learn to ignore.

🔴 RULE A EXEMPTIONS ARE NOT A CONVENIENCE LIST. Each is a shape where the two
values are BOTH correct, and each is decided mechanically, not by name:

  PER-BUILD   the two sym tables disagree about the name, so there is no single
              value to check against (`SUB_BUILD` is 1 in sub, 0 in basic).
  CONDITIONAL the asm source defines the name more than once, under an assembler
              IF -- only one arm is live and the text carries both
              (`FPERR_STROOM`/`FPERR_MISSOP` under `IF CLEARPOOL`).
  PUBLISHED   the probe means the PUBLISHED MSX work-area address while the ROM
              has an internal label of the same name. This is the two-namespaces
              hazard filed separately in TODO.md; it is listed by name in
              tools/wall-literal-allow.txt with the reason, because no mechanical
              test separates it -- and D-WALLIT MEASURED both entries on a
              VG-8020 rather than accepting them (scratchpad/sysvar_addr_probe.py).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM = {"basic": "build/basic-reloc.sym", "sub": "build/sub.sym"}
ALLOW = "tools/wall-literal-allow.txt"


def load_syms(path):
    syms, pat = {}, re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.I)
    with open(path) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                syms.setdefault(m.group(1), int(m.group(2), 16))
    return syms


def asm_files(root):
    out = []
    for d in ("basic", "sub"):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        for dp, _, fns in os.walk(p):
            for fn in sorted(fns):
                if fn.endswith((".asm", ".inc")):
                    out.append(os.path.relpath(os.path.join(dp, fn), root))
    return out


def py_files(root):
    out = []
    for d in ("tools", "probes"):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        for dp, _, fns in os.walk(p):
            for fn in sorted(fns):
                if fn.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(dp, fn), root))
    return out


DEF = re.compile(r"^\s*([A-Za-z_.][A-Za-z0-9_.]*)\s*:?\s+equ\s", re.I)
PY_ASSIGN = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"(?:0x([0-9A-Fa-f]{1,4})|\$([0-9A-Fa-f]{1,4})|([0-9A-Fa-f]{1,4})[hH]|(\d{1,5}))"
    r"\s*(?:#.*)?$")
# NAME equ <expr>  ; $XXXX...   -- leading, and NOT the start of a `$XXXX..$YYYY` span
ASM_CMT = re.compile(
    r"^\s*([A-Za-z_.][A-Za-z0-9_.]*)\s*:?\s+equ\s+([^;]+?)\s*;\s*\$([0-9A-Fa-f]{4})(?!\.\.)",
    re.I)


def multi_defined(root, files):
    """Names the asm source defines MORE THAN ONCE -- an assembler IF carries both."""
    seen, multi = set(), set()
    for rel in files:
        for line in open(os.path.join(root, rel), errors="replace"):
            m = DEF.match(line)
            if m:
                n = m.group(1)
                if n in seen:
                    multi.add(n)
                seen.add(n)
    return multi


def load_allow(root):
    allow, path = {}, os.path.join(root, ALLOW)
    if not os.path.exists(path):
        return allow
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, why = line.partition("#")
        allow[key.strip()] = why.strip()
    return allow


def check(root, verbose=False):
    tables, missing = {}, []
    for tag, rel in SYM.items():
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            missing.append(rel)
        else:
            tables[tag] = load_syms(p)
    if missing:
        print("GATE-SKIPPED: check_wall_literals.py: no sym file(s) yet: "
              + ", ".join(missing) + " -- build first (`make repack-machine`). "
              "This is a SKIP, not a pass: nothing was compared.")
        return 0

    asm = asm_files(root)
    conditional = multi_defined(root, asm)
    allow = load_allow(root)
    fails, stats = [], {}

    # ---- Rule A: a Python literal bound to a name the build resolves ----
    scanned = anchored = 0
    for rel in py_files(root):
        for i, line in enumerate(
                open(os.path.join(root, rel), errors="replace").read().splitlines()):
            m = PY_ASSIGN.match(line)
            if not m:
                continue
            scanned += 1
            name = m.group(1)
            hx = m.group(2) or m.group(3) or m.group(4)
            val = int(hx, 16) if hx else int(m.group(5))
            vals = {t: tb[name] for t, tb in tables.items() if name in tb}
            if not vals:
                continue
            anchored += 1
            if len(set(vals.values())) > 1:
                continue                                   # PER-BUILD
            if name in conditional:
                continue                                   # CONDITIONAL
            if val in vals.values():
                continue
            key = f"{rel}:{name}"
            if key in allow:
                continue                                   # PUBLISHED
            got = " ".join(f"{t}=${v:04X}" for t, v in vals.items())
            fails.append(
                f"  {rel}:{i+1}: {name} = ${val:04X}, but the build resolves "
                f"{name} to {got}. Either read the sym file, or -- if these are "
                f"two different namespaces -- pin it in {ALLOW} with the reason.")
    stats["A"] = (scanned, anchored)

    # ---- Rule B: an asm comment annotating this row's resolved address ----
    rows = 0
    for rel in asm:
        for i, line in enumerate(
                open(os.path.join(root, rel), errors="replace").read().splitlines()):
            m = ASM_CMT.match(line)
            if not m:
                continue
            name, claimed = m.group(1), int(m.group(3), 16)
            vals = {t: tb[name] for t, tb in tables.items() if name in tb}
            if not vals or name in conditional:
                continue
            rows += 1
            if claimed in vals.values():
                continue
            got = " ".join(f"{t}=${v:04X}" for t, v in vals.items())
            fails.append(
                f"  {rel}:{i+1}: the comment on `{name}` claims ${claimed:04X}, "
                f"but the assembler resolved {got}. The expression is "
                f"authoritative; the comment is a hand copy.")
    stats["B"] = rows

    print(f"wall-literal check: rule A {stats['A'][1]} anchored of "
          f"{stats['A'][0]} assignments; rule B {stats['B']} annotated `equ` rows; "
          f"{len(conditional)} conditional name(s) exempt, {len(allow)} pinned.")
    if fails:
        print("FAIL: a hand-copied figure disagrees with the value the build "
              "resolved:")
        for f in fails:
            print(f)
        return 1
    print("PASS: every hand copy agrees with the build.")
    return 0


def selftest(root):
    """RED arms with a GREEN control, on the real tree, restoring on every exit."""
    import atexit
    print("--- selftest: the gate must redden on a planted drift ---")
    if check(root) != 0:
        print("SELFTEST ABORTED: the tree is already RED, so a planted drift "
              "proves nothing. Fix the tree first.")
        return 1

    plants = [
        ("A", "probes/basic/basic_probe_clear.py",
         "TXTTAB       = 0xF676", "TXTTAB       = 0xF670"),
        ("B", "basic/sysvars.inc",
         "GFX_SPATN       equ     GFX_SC + 2      ; $E419:",
         "GFX_SPATN       equ     GFX_SC + 2      ; $E4F9:"),
    ]
    rc = 0
    for tag, rel, old, new in plants:
        p = os.path.join(root, rel)
        orig = open(p).read()
        if orig.count(old) != 1:
            print(f"  [rule {tag}] SELFTEST BROKEN: anchor not unique in {rel}")
            rc = 1
            continue
        # The original is held IN MEMORY, not in a temp file: nothing to place
        # under the temp root, nothing to leak, and the restore cannot fail
        # because a backup path went missing. Registered with atexit as well as
        # try/finally -- D-KNIFEGUARD: a runner that exits between the write and
        # the restore leaves the tree CUT and invisible to the ROM-hash guard.
        restore = lambda p=p, orig=orig: open(p, "w").write(orig)
        atexit.register(restore)
        try:
            open(p, "w").write(orig.replace(old, new))
            got = check(root)
        finally:
            restore()
            atexit.unregister(restore)
        print(f"  [rule {tag}] planted drift in {rel}: "
              f"{'RED (correct)' if got else '🔴 STAYED GREEN -- the rule is blind'}")
        if got == 0:
            rc = 1

    print("  [control] tree restored:", end=" ")
    back = check(root)
    print("GREEN (correct)" if back == 0 else "🔴 STILL RED -- restore failed")
    return rc or back


if __name__ == "__main__":
    root = ROOT
    if "--selftest" in sys.argv:
        raise SystemExit(selftest(root))
    raise SystemExit(check(root))
