#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""stubinl-check -- every inline-index tenant call is well formed (D-STUBINL).

basic/subromcall.asm's sc_inl0 / sc_inl1 / sr_inl0 / sr_inl1 read the byte that
FOLLOWS their call as the tenant's entry (space plan B-11). That is a new call
shape with a failure no emulator gate can name: a site that forgets its `db`
runs the next opcode as the index and calls some OTHER tenant. So this reads the
source and refuses:

  R1  a stub reached by anything but an unconditional `call` -- a `jp`/`jr`
      leaves no return address to read the byte through, and a conditional
      `call` that is NOT taken falls into the `db` and executes it;
  R2  a `call <stub>` whose next code line is not `db low (SUBROM_ENTRY_BASE_Pn
      + ...)`;
  R3  a db naming the OTHER table (`sc_inl0` with `..._P1`, or the reverse) --
      the stub supplies the high byte, so the low byte would index the wrong one;
  R4  a label on that db line -- something could jump to it;
  R5  a stub used in a basic/ file that sub/ or disk/ also assembles -- the
      stubs exist only in the main ROM;
  R6  (degenerate input) no site at all while the stubs are defined: a scan
      that matched nothing is not a pass.

    python3 tools/check_stub_inline.py [--selftest]
Exit 0 clean, 1 a violation, 2 the scan refused its own input.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUBS = ("sc_inl0", "sc_inl1", "sr_inl0", "sr_inl1")
DEF_FILE = "basic/subromcall.asm"
REF = re.compile(r"^(?P<label>[A-Za-z_]\w*:)?\s*(?P<op>call|jp|jr)\s+(?:(?P<cc>n?z|n?c|p[oe]?|m)\s*,\s*)?"
                 r"(?P<stub>" + "|".join(STUBS) + r")\b", re.I)
DB = re.compile(r"^(?P<label>[A-Za-z_]\w*:)?\s*db\s+low\s*\(\s*SUBROM_ENTRY_BASE_P(?P<pg>[01])\s*\+\s*3\s*\*\s*\w+\s*\)",
                re.I)


def code_lines(text):
    """(1-based line number, line without its comment) for every line."""
    for i, ln in enumerate(text.split("\n"), 1):
        yield i, ln.split(";", 1)[0].rstrip()


def scan(files, shared):
    """files: {rel: text}. -> (sites, problems)."""
    sites, bad = 0, []
    for rel, text in sorted(files.items()):
        if rel == DEF_FILE:
            continue
        lines = list(code_lines(text))
        for k, (n, ln) in enumerate(lines):
            m = REF.match(ln)
            if not m:
                continue
            stub = m.group("stub")
            where = f"{rel}:{n}"
            if rel in shared:
                bad.append(f"R5 {where}: {stub} in a body that sub/ or disk/ also assembles")
            if m.group("op").lower() != "call" or m.group("cc"):
                bad.append(f"R1 {where}: `{ln.strip()}` -- only an unconditional `call` may reach {stub}")
                continue
            nxt = next(((j, l) for j, l in lines[k + 1:] if l.strip()), (None, ""))
            d = DB.match(nxt[1])
            if not d:
                bad.append(f"R2 {where}: `call {stub}` is not followed by its `db low (SUBROM_ENTRY_BASE_Pn + ...)`"
                           f" (next code line: {nxt[1].strip()!r})")
                continue
            if d.group("pg") != stub[-1]:
                bad.append(f"R3 {where}: {stub} names table P{stub[-1]} but its db names P{d.group('pg')}")
            if d.group("label"):
                bad.append(f"R4 {rel}:{nxt[0]}: the inline db carries a label ({d.group('label')})")
            sites += 1
    return sites, bad


def tree():
    files = {}
    for p in glob.glob(os.path.join(ROOT, "basic", "*.asm")) + glob.glob(os.path.join(ROOT, "basic", "*.inc")):
        files[os.path.relpath(p, ROOT)] = open(p, encoding="utf-8", errors="replace").read()
    shared = set()
    for p in (glob.glob(os.path.join(ROOT, "sub", "*.asm")) + glob.glob(os.path.join(ROOT, "sub", "*.inc"))
              + glob.glob(os.path.join(ROOT, "disk", "*.asm")) + glob.glob(os.path.join(ROOT, "disk", "*.inc"))):
        for m in re.finditer(r'^\s*include\s+"(basic/[^"]+)"', open(p, encoding="utf-8", errors="replace").read(), re.M):
            shared.add(m.group(1))
    return files, shared


def main():
    files, shared = tree()
    defined = DEF_FILE in files and all(re.search(rf"^{s}:", files[DEF_FILE], re.M) for s in STUBS)
    sites, bad = scan(files, shared)
    if defined and sites == 0:
        print("stubinl-check: REFUSED -- the stubs are defined but the scan found NO call site; "
              "a scan that matched nothing is not a pass")
        return 2
    for b in bad:
        print("  " + b)
    if bad:
        print(f"stubinl-check: 🔴 {len(bad)} violation(s) over {sites} well-formed site(s)")
        return 1
    print(f"stubinl-check: 🟢 {sites} inline-index tenant call(s), every one `call` + its own-table `db`")
    return 0


def selftest():
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)

    good = "x:\n    call    sc_inl1   ; c\n    db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_A)\n    ret\n"
    arm("S1 a well-formed site passes", scan({"basic/a.asm": good}, set()) == (1, []))
    arm("S2 comment lines between the call and the db are allowed",
        scan({"basic/a.asm": "    call sc_inl0\n    ; why\n\n    db low (SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_A)\n"},
             set())[1] == [])
    r = scan({"basic/a.asm": "    call sc_inl1\n    ret\n"}, set())[1]
    arm("S3 NEGATIVE: a missing db is R2", len(r) == 1 and r[0].startswith("R2"))
    r = scan({"basic/a.asm": "    call sc_inl0\n    db low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_A)\n"}, set())[1]
    arm("S4 NEGATIVE: the other table's db is R3", len(r) == 1 and r[0].startswith("R3"))
    r = scan({"basic/a.asm": "    jp sr_inl1\n    db low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_A)\n"}, set())[1]
    arm("S5 NEGATIVE: a jp to a stub is R1", len(r) == 1 and r[0].startswith("R1"))
    r = scan({"basic/a.asm": "    call nz,sc_inl1\n    db low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_A)\n"}, set())[1]
    arm("S6 NEGATIVE: a CONDITIONAL call is R1 (not taken, it executes the db)",
        len(r) == 1 and r[0].startswith("R1"))
    r = scan({"basic/a.asm": "    call sc_inl1\nhere: db low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_A)\n"}, set())[1]
    arm("S7 NEGATIVE: a label on the db is R4", len(r) == 1 and r[0].startswith("R4"))
    r = scan({"basic/b-body.inc": good}, {"basic/b-body.inc"})[1]
    arm("S8 NEGATIVE: a stub in a shared body is R5", any(x.startswith("R5") for x in r))
    arm("S9 a stub NAME inside a comment is not a site",
        scan({"basic/a.asm": "    nop   ; call sc_inl1 here\n"}, set()) == (0, []))
    arm("S10 the definitions file itself is not scanned",
        scan({DEF_FILE: "sc_inl1:\n    ld a,1\n"}, set()) == (0, []))
    print(f"selftest: {'GREEN' if ok else '🔴 RED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
