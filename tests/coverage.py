# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Code-coverage measurement for the host-side unit tests — no core changes.

Coverage is a pure test-harness concern, so we monkeypatch Z80.step here to log
every executed opcode address; the production core (z80.py) is untouched. We run
each test group in-process, accumulate the executed addresses, then bucket them
against the pasmo symbol table to report, per labelled region, whether it was
ENTERED by any test. That automates the "what's covered?" audit.

Two metrics are reported:

  1. BLOCK ENTRY (≈ basic-block): a region [label_i, label_{i+1}) is covered iff
     some executed opcode address fell in it. Finer than routine coverage (every
     loop/branch label is a region), coarser than line coverage.
  2. INSTRUCTION / LINE: exact executed-instructions / total-instructions. The
     numerator is _PCS (every executed opcode address); the denominator comes
     from a small Z80 instruction-length decoder (below) that enumerates every
     opcode start, re-syncing at each label so a data byte can't desync it. This
     also exposes PARTIALLY covered blocks — the untaken branch/error paths that
     block entry can't see.

Data tables in the code image (kwtable, dispatch, banners) are isolated as their
own regions and excluded from both metrics; UPPERCASE EQU constants whose value
lands in the code range are not treated as positions at all.

Run: `python3 tests/coverage.py`  (or `make coverage`).
"""

import bisect
import contextlib
import importlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import z80                              # noqa: E402
from msxtest import load_symbols        # noqa: E402

# --- instrument: log each executed opcode address (no z80.py change) ---------
_PCS = set()
_orig_step = z80.Z80.step


def _traced_step(self):
    _PCS.add(self.pc)                   # PC here = the opcode about to run
    return _orig_step(self)


z80.Z80.step = _traced_step

# --- test groups: (label, modules, source, load-base) ------------------------
GROUPS = [
    ("BASIC", [
        "test_tokenise", "test_expr", "test_vars", "test_strvar", "test_print",
        "test_list", "test_screen", "test_vdpio", "test_poke", "test_usr",
        "test_program", "test_control_flow", "test_repl", "test_statements",
    ], "basic/main.asm", 0x4000),
    ("tape", ["test_tape"], "tape/tape.asm", 0x00E1),
    ("disk", ["test_getdpb", "test_gdate", "test_fat_next_cluster",
              "test_fat_write_fat_entry", "test_fat_find"],
     "disk/disk.asm", 0x4000),
]

# Data tables that live in the code image (lowercase, so not caught by the
# constant filter) and legitimately never execute as code.
DATA_LABELS = {"kwtable", "dispatch", "disptab", "verbtab", "banner_text",
               "prompt_text"}


def is_position_label(name):
    """A real position in the image (code OR data table), not an EQU constant.
    Convention here: positions are lowercase; constants (CHPUT, CAS_FLATMAX,
    DSKIO_ENTRY) are UPPERCASE — a constant's *value* could otherwise land in
    the code range and masquerade as a routine. Data tables ARE positions and so
    stay region boundaries (isolating the table); they're dropped from the
    *metrics* by is_data_label, not absorbed into the preceding code block."""
    return any(c.islower() for c in name)


def is_data_label(name):
    return name in DATA_LABELS


def code_extent(rom_path, base):
    """[lo, hi) of real content: trim the trailing $00 padding."""
    data = open(rom_path, "rb").read()
    hi = len(data)
    while hi > 0 and data[hi - 1] == 0:
        hi -= 1
    return base, base + hi


def regions(sym_path, lo, hi):
    """Code regions [label_i, label_{i+1}) — boundaries from code labels only,
    so constants/data don't split or inflate the routine map."""
    syms = load_symbols(sym_path)
    code = sorted((a, n) for n, a in syms.items()
                  if lo <= a < hi and is_position_label(n))
    out = []
    for i, (a, n) in enumerate(code):
        end = code[i + 1][0] if i + 1 < len(code) else hi
        if end > a:
            out.append((n, a, end))
    return out


# --- Z80 instruction-length decoder (for true line/instruction coverage) -----
# Lengths of the unprefixed main opcodes. Default 1; +imm bytes below. This only
# needs to compute *lengths*, never execute — so it's a few bytes of tables, not
# a second CPU. Re-synced at every code label, so a mis-decoded data byte can't
# desync more than one region.
_MAIN_LEN = [1] * 256
for _op in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,   # LD r,n / (HL),n
            0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE,   # ALU A,n
            0x10, 0x18, 0x20, 0x28, 0x30, 0x38,               # DJNZ / JR (cc)
            0xD3, 0xDB):                                       # OUT/IN (n)
    _MAIN_LEN[_op] = 2
for _op in (0x01, 0x11, 0x21, 0x31, 0x22, 0x2A, 0x32, 0x3A,   # LD rr,nn / (nn)
            0xC3, 0xCD,                                        # JP / CALL nn
            0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA,   # JP cc,nn
            0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC):  # CALL cc,nn
    _MAIN_LEN[_op] = 3
_ED_LONG = {0x43, 0x4B, 0x53, 0x5B, 0x63, 0x6B, 0x73, 0x7B}    # LD (nn),rr / rr,(nn)


def _idx_needs_disp(op):
    """Does the DD/FD-prefixed main opcode `op` carry an (IX/IY+d) displacement
    byte? Same rule the core's _idx uses (the (HL)=reg-code-6 slots)."""
    return ((0x40 <= op <= 0x7F and (op & 7) == 6) or
            (0x40 <= op <= 0x7F and ((op >> 3) & 7) == 6) or
            (0x80 <= op <= 0xBF and (op & 7) == 6) or
            ((op & 0xC7) in (0x04, 0x05, 0x06) and ((op >> 3) & 7) == 6))


def inst_len(byte_at, addr):
    """Length in bytes of the instruction at `addr`. `byte_at(x)` returns the
    code byte at absolute address x."""
    op = byte_at(addr)
    if op == 0xCB:
        return 2
    if op == 0xED:
        return 4 if byte_at(addr + 1) in _ED_LONG else 2
    if op in (0xDD, 0xFD):
        op2 = byte_at(addr + 1)
        if op2 == 0xCB:
            return 4                                   # DD CB d op
        return 1 + _MAIN_LEN[op2] + (1 if _idx_needs_disp(op2) else 0)
    return _MAIN_LEN[op]


def enum_instructions(rom, base, lo, hi, a, e):
    """Opcode-start addresses in region [a, e), by linear decode from the label
    (which re-syncs alignment at every region)."""
    def byte_at(x):
        off = x - base
        return rom[off] if 0 <= off < len(rom) else 0
    out = []
    addr = a
    while addr < e:
        out.append(addr)
        addr += inst_len(byte_at, addr)
    return out


def measure(label, mods, src, base):
    _PCS.clear()
    for mname in mods:
        mod = importlib.import_module(mname)
        with contextlib.redirect_stdout(io.StringIO()):
            fails = mod.run()
        if fails:
            print(f"  !! {mname} reported {fails} failing check(s)")

    rom_path, sym = "/tmp/cov_group.rom", "/tmp/cov_group.sym"
    # The source may be split across included parts (disk/*.asm, basic/*.asm)
    # resolved relative to its own directory, so -I that directory — matching how
    # each test_*.py assembles its own ROM. Harmless for single-file sources.
    src_dir = os.path.dirname(os.path.join(ROOT, src))
    subprocess.run(["pasmo", "-I", src_dir, "--bin", os.path.join(ROOT, src),
                    rom_path, sym],
                   check=True, capture_output=True)
    rom = open(rom_path, "rb").read()
    lo, hi = code_extent(rom_path, base)
    regs = regions(sym, lo, hi)

    # Bucket executed opcode addresses into their regions.
    starts = [a for _, a, _ in regs]
    exec_by_region = [set() for _ in regs]
    executed_code = {pc for pc in _PCS if lo <= pc < hi}
    for pc in executed_code:
        i = bisect.bisect_right(starts, pc) - 1
        if 0 <= i < len(regs) and regs[i][1] <= pc < regs[i][2]:
            exec_by_region[i].add(pc)

    # Per region: block-entry + instruction coverage. The instruction set is the
    # static decode UNION the executed addresses, so a minor data mis-decode can
    # never drop a genuinely-executed instruction (it only adds phantom-uncovered
    # ones — conservative).
    n_blocks = sum(1 for n, _, _ in regs if not is_data_label(n))
    n_entered = 0
    line_cov = line_tot = 0
    partial = []                         # (name, executed, total) entered < 100%
    not_entered = []
    for (name, a, e), ex in zip(regs, exec_by_region):
        if is_data_label(name):          # data table — not code, exclude entirely
            continue
        instrs = set(enum_instructions(rom, base, lo, hi, a, e)) | ex
        tot = len(instrs)
        cov = len(ex)
        line_cov += cov
        line_tot += tot
        if cov:
            n_entered += 1
            if cov < tot:
                partial.append((name, cov, tot))
        else:
            not_entered.append(name)

    bpct = 100.0 * n_entered / n_blocks if n_blocks else 0.0
    lpct = 100.0 * line_cov / line_tot if line_tot else 0.0
    print(f"\n=== {label}  [code {lo:#06x}..{hi:#06x}] ===")
    print(f"  blocks:       {n_entered}/{n_blocks} entered ({bpct:.0f}%)")
    print(f"  instructions: {line_cov}/{line_tot} executed ({lpct:.0f}%)")

    if not_entered:
        print(f"  not entered ({len(not_entered)} blocks):")
        ln = "    "
        for nm in not_entered:
            if len(ln) + len(nm) + 2 > 78:
                print(ln)
                ln = "    "
            ln += nm + "  "
        if ln.strip():
            print(ln)
    if partial:
        partial.sort(key=lambda t: t[2] - t[1], reverse=True)
        shown = partial[:8]
        print(f"  partially covered ({len(partial)} blocks; top by missed "
              f"instr) — untaken branches/error paths:")
        for nm, c, t in shown:
            print(f"    {nm:<22} {c}/{t} instr ({t - c} missed)")
    return n_entered, n_blocks, line_cov, line_tot


def main():
    print("Host unit-test coverage — block-entry AND instruction (line)")
    print("(data tables / UPPERCASE constants excluded)")
    tb_cov = tb_all = tl_cov = tl_all = 0
    for label, mods, src, base in GROUPS:
        bc, bt, lc, lt = measure(label, mods, src, base)
        tb_cov += bc
        tb_all += bt
        tl_cov += lc
        tl_all += lt
    bpct = 100.0 * tb_cov / tb_all if tb_all else 0.0
    lpct = 100.0 * tl_cov / tl_all if tl_all else 0.0
    print(f"\nOVERALL blocks:       {tb_cov}/{tb_all} ({bpct:.0f}%)")
    print(f"OVERALL instructions: {tl_cov}/{tl_all} ({lpct:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
