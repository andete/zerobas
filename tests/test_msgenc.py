# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-MSGENC phrase-encoded error messages decode to their literal text.

docs/spec-basic-msgenc-carve.md §7. The slice re-spells 25 user-visible message
strings as escape sequences over a shared phrase table, so the ONE invariant that
matters is that the decoded bytes are unchanged. The emulator differentials cover
a handful of them end-to-end (error-trap's ERROR 23..26, fat-error's 'load error',
arrays' 'Illegal function call'); this is the cheap layer that covers ALL of them,
including the ones no acceptance row happens to print.

⚠️ WHAT MAKES THIS TEST REAL, per docs/... and the recurring arc lesson: it
DECODES THE ROM IMAGE, it does not re-derive the expected text from the same
source line that produced it. The expected strings below are typed out
independently, so a wrong phrase-table entry, a wrong escape constant, a wrong
phrase ORDER, or a stray baked CRLF all fail here.

FALSIFIED (spec §7): corrupt any msg_phrase_tab entry -- e.g. change " error" to
" errer" in basic/program.asm -- and every message using MSGESC_ERROR fails this
test. Swap two phrases in the table and the same happens. Verified by doing it,
2026-07-29; without that check a table read that silently returned b"" would let
every row "agree" on the empty string.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ROM = "/tmp/zb_msgenc_reloc.rom"
SYM = "/tmp/zb_msgenc_reloc.sym"
LOW = 0x2812                    # basic/main-reloc.asm ROM_BASE: image offset origin

# The decoded text every message MUST still produce, typed independently of the
# `db` lines that encode them. Capitalisation is load-bearing: the arrays arc's
# §9.5 pins its four strings to the reference's capitalised wording, while the
# D-2 house strings are lowercase, and MSGESC_UTOF/MSGESC_ILLFN are shared
# ACROSS that split (each message spells its own first letter).
EXPECT = {
    "err_type_mismatch":    "Type mismatch",
    "err_fp_divzero":       "Division by zero",
    "err_illegal_fn":       "Illegal function call",
    "err_resume_noerr":     "RESUME without error",
    "err_unprintable":      "Unprintable error",
    "err_line":             "Undefined line number",
    "err_io":               "load error",
    "err_verify":           "Verify error",
    "err_cont":             "Can't CONTINUE",
    "err_mem":              "Out of memory",
    "err_noret":            "RETURN without GOSUB",
    "err_nofor":            "NEXT without FOR",
    "err_data":             "Out of DATA",
    "err_missing_operand":  "Missing operand",
    "err_too_complex":      "String formula too complex",
    "err_out_of_str":       "Out of string space",
    "msg_redo":             "?Redo from start",
    "msg_extra":            "?Extra ignored",
    "err_subscript":        "Subscript out of range",
    "err_redim":            "Redimensioned array",
    "err_illegal_fn_arr":   "Illegal function call",
    "err_mem_arr":          "Out of memory",
    "err_syntax":           "Syntax error",
    "err_linebuf_overflow": "Line buffer overflow",
    "err_overflow":         "Overflow",
    # S-FCH-2's two disk-range codes (52 / 59). They are the reason MSGESC_FILE
    # exists, and they are the only two messages that share it -- so if the fifth
    # phrase is wrong, ONLY these two rows fail, which is exactly the signal.
    "err_bad_filenum":      "Bad file number",
    "err_file_notopen":     "File not OPEN",
}

# The aliases must still resolve to the SAME address as their target -- the D-2
# self-funding dedup this slice must not silently undo.
ALIASES = {
    "err_stack":         "err_mem",
    "err_prog_mem":      "err_mem",
    "err_subrom_absent": "err_illegal_fn",
}


def build():
    r = subprocess.run(["pasmo", "--bin", "basic/main.asm", ROM, SYM],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("pasmo failed")
    return open(ROM, "rb").read(), load_syms(SYM)


def load_syms(path):
    """pasmo .sym rows look like `msg_phrase_tab\tEQU 077DFH`."""
    syms = {}
    for ln in open(path):
        parts = ln.split()
        if len(parts) >= 3 and parts[1].upper() == "EQU":
            tok = parts[2].rstrip("Hh")
            try:
                syms[parts[0]] = int(tok, 16)
            except ValueError:
                pass
    return syms


def read_phrases(rom, syms):
    """The phrase table as the DECODER sees it: NUL-terminated, in escape order.

    ⚠️ The COUNT is taken from the ROM's own MSGESC_HI, not hardcoded. The
    decoder is bounded by that constant (`cp MSGESC_HI + 1`), so reading a fixed
    four entries would have let S-FCH-2's fifth phrase land with the bound
    un-bumped -- the exact "one fact in two places" drift that left err_msgtab's
    ERR 25 entry dead for a whole arc (basic/interp.asm, msgtab-bound-drift).
    Now the table and the bound are read from the same build and must agree.
    """
    at = syms["msg_phrase_tab"] - LOW
    phrases = []
    for _ in range(syms["MSGESC_HI"] - syms["MSGESC_LO"] + 1):
        end = rom.index(b"\0", at)
        phrases.append(rom[at:end].decode("latin-1"))
        at = end + 1
    return phrases


def decode(rom, addr, phrases):
    out, at = [], addr - LOW
    while rom[at] != 0:
        b = rom[at]
        if 1 <= b <= len(phrases):
            out.append(phrases[b - 1])
        elif b < 0x20:
            raise AssertionError(f"raw control byte {b} at ${addr:04X} "
                                 f"(a baked CR/LF, or an out-of-range escape)")
        else:
            out.append(chr(b))
        at += 1
    return "".join(out)


def main():
    rom, syms = build()
    phrases = read_phrases(rom, syms)

    fails = []
    # Guard the instrument before trusting a single row: a table read that
    # returned empty strings would make every message "decode" to its literal
    # residue and quietly pass. (gate-can-be-green-while-measuring-nothing)
    if [p for p in phrases if not p]:
        raise SystemExit(f"phrase table read empty entries: {phrases!r}")
    print(f"phrase table: {phrases!r}")

    for lbl, want in sorted(EXPECT.items()):
        if lbl not in syms:
            fails.append(f"{lbl}: absent from the sym file")
            continue
        got = decode(rom, syms[lbl], phrases)
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {lbl:22} {got!r}")
        if not ok:
            fails.append(f"{lbl}: got {got!r}, want {want!r}")

    for alias, target in sorted(ALIASES.items()):
        if syms.get(alias) != syms.get(target):
            fails.append(f"{alias} no longer aliases {target} "
                         f"(${syms.get(alias, 0):04X} vs ${syms.get(target, 0):04X})")
        else:
            print(f"PASS  alias {alias:20} == {target}")

    # 🔴 INVERTED BY D-MSGEXACT: THIS USED TO ASSERT THE OVERLAP, NOW IT FORBIDS IT.
    # ERR 25's text used to END with ERR 6's, so err_overflow was a pointer 12 B
    # INTO err_linebuf_overflow -- 21 B for both. Exact wording makes that
    # arithmetically impossible: measured on both references, ERR 6 is `Overflow`
    # (capital) and ERR 25 is `Line buffer overflow` (lowercase tail), and one blob
    # cannot spell a letter two ways.
    # Kept as a LIVE control rather than deleted, because the pull to re-share is
    # real -- it is worth exactly 9 B, and knife K5 measured that by restoring the
    # overlap and watching ERR 25 print `Line buffer Overflow`. A future carve hunt
    # that "spots" the 9 B would silently corrupt ERR 25; this row is what stops it.
    # --- D-MSGSUB control 1: the new escape must stay OUTSIDE the phrase range --
    # read_phrases() above reads exactly MSGESC_HI - MSGESC_LO + 1 entries out of
    # msg_phrase_tab. MSGESC_SUB is not a phrase -- it has no table entry -- so
    # folding it into the range (the obvious "tidy-up": MSGESC_HI equ MSGESC_SUB)
    # would make that read run one entry PAST the table and compare every message
    # against whatever bytes follow it. That fails by producing plausible garbage,
    # not by going red, which is the failure shape this tree keeps meeting.
    if syms["MSGESC_SUB"] <= syms["MSGESC_HI"]:
        fails.append(
            f"MSGESC_SUB ({syms['MSGESC_SUB']}) is inside the phrase range "
            f"(MSGESC_LO..MSGESC_HI = {syms['MSGESC_LO']}..{syms['MSGESC_HI']}). "
            f"It has no msg_phrase_tab entry, so read_phrases() would overrun the "
            f"table -- and print_msg_stopcr's `cp MSGESC_HI + 1` would stop "
            f"reaching the pm_sub arm. See basic/sysvars.inc.")
    else:
        print("PASS  escape   MSGESC_SUB is outside the phrase range")

    # --- D-MSGSUB control 2: the ABSENT-sub-ROM fall-through ------------------
    # err_subhosted is one byte (MSGESC_SUB) sited so that err_unprintable is the
    # VERY NEXT byte. When there is no sub-ROM, subrom_call returns CF=1 without
    # calling and pm_sub resumes the decode loop right there -- so the machine
    # prints `Unprintable error`, exactly what it printed before D-MSGSUB,
    # instead of nothing. That degradation is the reason the slice does not have
    # to rest on "you cannot type ERROR 12 without the sub-ROM" (which is false
    # for a program loaded already-tokenised from tape or disk).
    # Same shape as the err_overflow control below, and for the same reason: the
    # pull to relocate or "tidy up" a one-byte string is real, and nothing else
    # in the tree would notice. Knife K1 measures the live behaviour.
    subgap = syms["err_unprintable"] - syms["err_subhosted"]
    if subgap != 1:
        fails.append(
            f"err_unprintable is no longer the byte AFTER err_subhosted "
            f"(gap {subgap}, want 1). The absent-sub-ROM fall-through in "
            f"print_msg_stopcr's pm_sub arm now decodes whatever sits between "
            f"them -- see basic/interp.asm and docs/spec-basic-msgsub.md §3.1.")
    else:
        print("PASS  adjacent err_unprintable directly follows err_subhosted")

    gap = syms["err_overflow"] - syms["err_linebuf_overflow"]
    if gap != len("Line buffer overflow") + 1:
        fails.append(
            f"err_overflow/err_linebuf_overflow are no longer INDEPENDENT strings "
            f"(gap {gap}, want {len('Line buffer overflow') + 1}). A gap of "
            f"{len('Line buffer ')} means the overlap was re-shared, which makes "
            f"ERR 25 print `Line buffer Overflow` -- see D-MSGEXACT knife K5.")
    else:
        print("PASS  split    err_overflow is independent of err_linebuf_overflow")

    if fails:
        print("\n" + "\n".join(fails))
        return 1
    print(f"\nALL {len(EXPECT)} messages decode to their literal text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
