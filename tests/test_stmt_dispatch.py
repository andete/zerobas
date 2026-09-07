# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the exec_stmt statement dispatch (D-KW-2), no emulator.

WHY THIS EXISTS
===============
`exec_stmt` used to be a 69-entry linear `cp`/`jp z` chain; D-KW-2 replaced it
with a `db token, dw handler` table and a search loop, to buy back ~109 B of
page 1 for the MISSING-class slice (docs/decision-missing-class-slicing.md §4).

**A dispatch refactor that drops one statement is catastrophic and SILENT.** The
dropped statement does not crash — it falls through to `is_letter`, and a
statement token is not a letter, so it becomes `syntax error` on a program that
used to work. Nothing else in the tree would notice: the acceptance suites cover
most statements but not all, and `tests/README.md` recorded the dispatch as
`exec_stmt 4/79` — **the switch itself had never been executed by a test**,
because every other test calls the handlers directly.

So this test asserts the one property the refactor must preserve, for **every**
entry rather than a sample: *the token that used to reach handler X still
reaches handler X, and nothing else does.*

METHOD — and the version of it that did not work
=================================================
The first version of this test read its expectations out of the assembled table
and asserted that every entry present dispatched to the address written beside
it. It passed. It also passed with the PRINT entry DELETED and with CLS pointed
at `ex_color`, because both statements are true of a corrupt table: **the
expectation was a copy of the subject.** That is the standing trap in this tree
(a gate can be green while measuring nothing), and it was caught only by
deliberately breaking the code under test.

So the test has two halves, and it needs both:

  * **`EXPECTED` (below) is an INDEPENDENT expectation**, recovered mechanically
    from the pre-refactor `cp`/`jp z` chain in git rather than from the table.
    Comparing the ROM's table against it catches a dropped statement, an added
    one, and a re-pointed one — the three failure modes that matter and that the
    table cannot testify about itself.
  * **Every entry is then EXECUTED**: `exec_stmt` runs the real Z80 code with
    that token in the statement buffer and the handler is trapped, so arrival is
    the assertion. This catches what a byte comparison cannot — a search loop
    with the wrong stride, a misplaced $00 terminator — where the table bytes
    are perfect but unreachable.

`dw` targets are additionally resolved against the symbol file, so an address
that is not any `ex_*` label is reported rather than silently accepted.

This used to run TWICE, once per build, because D-KW-2 changed SHARED code and
so moved the frozen lean 16 KB cart too. That build is retired along with the
`IF ROM_BASE` gates that selected it (RETIRE THE LEAN 16 KB CART S3,
docs/spec-lean-retire-s3-gates.md), so there is one image and one column, and
EXPECTED no longer carries a per-entry guard field.

Oracle: the dispatch contract itself — a handler's `in:` is HL = the statement
cursor, and control arrives by jump, not call. No reference ROM is involved.

Run:  python3 tests/test_stmt_dispatch.py     (or `make unit-test`)
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# --- THE INDEPENDENT EXPECTATION ------------------------------------------
# Recovered MECHANICALLY from the pre-refactor `cp`/`jp z` chain (git HEAD at
# the time of the D-KW-2 commit), not retyped: the extraction walked the chain,
# paired each `cp <token>` with the `j[pr] z,<handler>` that followed it, and
# tracked the enclosing IF-guard.
#
# THIS LIST IS THE WHOLE POINT OF THE TEST, and the first version did not have
# it. Reading the expectation out of the assembled table -- the artifact under
# test -- made the gate green for a table with the PRINT entry DELETED and for
# a table with CLS pointed at ex_color, because "every entry present dispatches
# to the address written next to it" is true of a corrupt table too. Both
# mutations were caught only by deliberately making them (the standing rule:
# falsify by breaking the code under test). The gate now compares the ROM's
# table against this list, so a dropped, added or re-pointed statement fails.
#
# MAINTENANCE: adding a statement means adding a row here. That is deliberate --
# a new statement should not be able to appear in the dispatch without the gate
# being told about it.
EXPECTED = [
    ('COLON', 'ex_sep'),
    # D-WAIT 2026-09-07: WAIT is the one entry NOT recovered from the
    # pre-refactor chain, because it did not exist then — the statement was
    # missing from zerobas entirely (kwsweep's crunch layer read `wait 0,0` back
    # as the ASCII bytes of a VARIABLE). Added deliberately, and this file's own
    # failure message is what asked for the line.
    ('WAIT_TOKEN', 'ex_wait'),
    ('BLOAD_TOKEN', 'ex_bload'),
    ('CLOAD_TOKEN', 'ex_cload'),
    ('LOAD_TOKEN', 'ex_load'),
    ('RUN_TOKEN', 'ex_run'),
    ('BSAVE_TOKEN', 'ex_bsave'),
    ('SAVE_TOKEN', 'ex_save'),
    ('FILES_TOKEN', 'ex_files'),
    ('MERGE_TOKEN', 'ex_merge'),
    ('OPEN_TOKEN', 'ex_open'),
    ('INPUT_TOKEN', 'ex_input'),
    ('LINE_TOKEN', 'ex_line'),
    ('CLOSE_TOKEN', 'ex_close'),
    ('KILL_TOKEN', 'ex_kill'),
    ('NAME_TOKEN', 'ex_name'),
    ('MAX_TOKEN', 'ex_maxfiles'),
    ('FIELD_TOKEN', 'ex_field'),
    ('LSET_TOKEN', 'ex_lset'),
    ('RSET_TOKEN', 'ex_rset'),
    ('GET_TOKEN', 'ex_get'),
    ('PUT_TOKEN', 'ex_put'),
    ('CALL_TOKEN', 'ex_call'),
    ("'_'", 'ex_call_us'),
    ('CSAVE_TOKEN', 'ex_csave'),
    ('POKE_TOKEN', 'ex_poke'),
    ('VPOKE_TOKEN', 'ex_vpoke'),
    ('OUT_TOKEN', 'ex_out'),
    ('CLEAR_TOKEN', 'ex_clear'),
    ('DEF_TOKEN', 'ex_def'),
    # D-DEFINTTOK / D-DEFTYPETOK: the four DEF<type> verbs each crunch to their
    # OWN single byte ($AB..$AE, matching the reference) and SHARE one handler --
    # ex_deftype steps over the token and the sub-ROM tenant reads it back to
    # pick the DEFTBL type code. DEF_TOKEN ($97) above is DEF USR and nothing
    # else now; no DEF<type> verb reaches it as ASCII text any more.
    ('DEFSTR_TOKEN', 'ex_deftype'),
    ('DEFINT_TOKEN', 'ex_deftype'),
    ('DEFSNG_TOKEN', 'ex_deftype'),
    ('DEFDBL_TOKEN', 'ex_deftype'),
    ('PRINT_TOKEN', 'ex_print'),
    ('CLS_TOKEN', 'ex_cls'),
    ('SCREEN_TOKEN', 'ex_screen'),
    ('COLOR_TOKEN', 'ex_color'),
    ('WIDTH_TOKEN', 'ex_width'),
    ('KEY_TOKEN', 'ex_key'),
    ('LIST_TOKEN', 'ex_list'),
    ('REM_TOKEN', 'ex_rem'),
    ('DATA_TOKEN', 'ex_data'),
    ('READ_TOKEN', 'ex_read'),
    ('RESTORE_TOKEN', 'ex_restore'),
    ('GOTO_TOKEN', 'ex_goto'),
    ('GOSUB_TOKEN', 'ex_gosub'),
    ('ON_TOKEN', 'ex_on'),
    ('RETURN_TOKEN', 'ex_return'),
    ('FOR_TOKEN', 'ex_for'),
    ('NEXT_TOKEN', 'ex_next'),
    ('IF_TOKEN', 'ex_if'),
    ('END_TOKEN', 'ex_end'),
    ('STOP_TOKEN', 'ex_stop'),
    ('CONT_TOKEN', 'ex_cont'),
    ('ELSE_TOKEN', 'ex_rem'),
    ('LET_TOKEN', 'ex_letkw'),
    ('PEEK_PREFIX', 'ex_ff_stmt'),
    ('DIM_TOKEN', 'ex_dim'),
    ('ERASE_TOKEN', 'ex_erase'),
    ('ERROR_TOKEN', 'ex_error'),
    ('RESUME_TOKEN', 'ex_resume'),
    ('SOUND_TOKEN', 'ex_sound'),
    ('PLAY_TOKEN', 'ex_play'),
    ('BEEP_TOKEN', 'ex_beep'),
    ('PSET_TOKEN', 'ex_pset'),
    ('PRESET_TOKEN', 'ex_preset'),
    ('CIRCLE_TOKEN', 'ex_circle'),
    ('PAINT_TOKEN', 'ex_paint'),
    ('DRAW_TOKEN', 'ex_draw'),
    ('SPRITE_TOKEN', 'ex_sprite'),
    ('VDP_TOKEN', 'ex_vdp_assign'),
    ('BASE_TOKEN', 'ex_base_assign'),
    ('TIME_TOKEN', 'ex_time_assign'),
    # --- the MISSING class (docs/spec-basic-missing-class.md) ----------------
    # These were NEVER in the pre-refactor cp/jp z chain -- they are new
    # statements, not a re-expression of old ones, so unlike every entry above
    # they cannot be recovered from it. Added here deliberately, which is what
    # this test asked for when it flagged them as UNEXPECTED. Repack-only with
    # the rest of the class: the lean cart's entry count must stay 52.
    ('MOTOR_TOKEN', 'ex_motor'),
    ('TRON_TOKEN', 'ex_tron'),
    ('TROFF_TOKEN', 'ex_troff'),
    ('LOCATE_TOKEN', 'ex_locate'),
    # SWAP, 2026-07-28. It was split out of the class and gated at
    # SWAP_RESIDENT = 0, so it is the one MISSING word this list never carried.
    # ⚠️ THIS TEST WOULD HAVE CAUGHT THE MISSING DISPATCH ARM. The spec claimed
    # SWAP_RESIDENT already guarded a stmt_table row; it did not, and the arm had
    # to be written when the flag was flipped. Had the arm existed all along, this
    # list's absence of SWAP would have flagged it as UNEXPECTED on the first
    # repack build -- the inverse of the real failure, and the same alarm.
    ('SWAP_TOKEN', 'ex_swap'),
    # DELETE, 2026-08-02 (D-DELETE, docs/spec-basic-delete.md). The first of
    # D-KWGAP4's four editor verbs to get a handler; AUTO/RENUM/LLIST still have
    # tokens and no dispatch, so they must NOT appear here.
    # ⚠️ AND THIS TEST DID ITS JOB ON THE FIRST CORPUS RUN, flagging $A8 as
    # UNEXPECTED. That is the alarm SWAP's note above describes, fired in the
    # other direction: a new statement cannot reach the dispatch without this
    # list being told, which is exactly why adding the row here is a deliberate
    # act and not maintenance noise.
    ('DELETE_TOKEN', 'ex_delete'),
    # D-EDITVERB 2026-08-06: the other THREE editor verbs. 🔴 AND THIS TEST FIRED
    # AGAIN, on this slice's first corpus run, naming all three as UNEXPECTED --
    # the second cohort it has caught and the second time the alarm was the
    # correct behaviour rather than noise. Declaring them is the deliberate act.
    # The comment above ("AUTO/RENUM/LLIST still have tokens and no dispatch, so
    # they must NOT appear here") was true until this slice and is now the line
    # directly above these three; it is left standing as the record of what
    # changed.
    ('LLIST_TOKEN', 'ex_llist'),
    ('RENUM_TOKEN', 'ex_renum'),
    ('AUTO_TOKEN', 'ex_auto'),
    # D-LPTVERB 2026-08-06 (docs/spec-basic-lptverb.md): LPRINT, the statement
    # half of the printer surface. LPOS is NOT here and must not be -- it is an
    # $FF-prefixed FUNCTION dispatched from basic/expr.asm's ev_f_ff chain, and
    # its token value $9C is ALSO OUT_TOKEN in this statement alphabet. A row for
    # it here would assert the wrong table.
    ('LPRINT_TOKEN', 'ex_lprint'),
    # D-LFILES 2026-08-06 (docs/spec-basic-lfiles.md): the LAST word of the
    # printer surface. This row is where the previous slice's line "LFILES is not
    # here either: it has a token equate but NO kwtable entry and NO stmt_table
    # row -- page 1 came out at 7 B and it does not fit" used to stand; it is
    # replaced rather than left standing, because a comment that says a shipped
    # verb is absent is the stale-count defect this project has now paid for
    # twice (see basic/sysvars.inc's D-EDITVERB note).
    #
    # ⚠️ `ex_lfiles` IS NOT ITS OWN ROUTINE. It is a 2-byte `ld a,DISKOP_SEL_LFILES`
    # that falls into `do_files`, so this row asserts the DISPATCH and not the
    # body; what makes LFILES differ from FILES is the op byte those two entry
    # points load, and the lfl- battery is what reads that difference out.
    ('LFILES_TOKEN', 'ex_lfiles'),
]


BUF = 0xC000            # the statement buffer exec_stmt is pointed at
RELOC_BASE = 0x2812


def build(src_name, rom, sym):
    src = os.path.join(ROOT, "basic", src_name)
    subprocess.run(["pasmo", "--bin", src, rom, sym], check=True,
                   capture_output=True)


def read_table(m):
    """Decode stmt_table out of the assembled image: [(token, handler_addr)].

    Stops at the $00 terminator. Refuses to run away if the terminator is
    missing -- a table that never ends would otherwise be 'read' as thousands
    of junk entries and the per-entry assertions below would drown."""
    a = m.addr("stmt_table")
    out = []
    while True:
        tok = m.peek(a)[0]
        if tok == 0:
            break
        lo, hi = m.peek(a + 1, 2)
        out.append((tok, lo | (hi << 8)))
        a += 3
        if len(out) > 256:
            raise AssertionError("stmt_table has no $00 terminator within 256 "
                                 "entries -- the search loop would run off the "
                                 "end of the table into whatever follows it")
    return out


def handler_names(m):
    """address -> the ex_* label(s) at it, from the symbol file. An address with
    no label means the table points somewhere that is not a statement handler."""
    byaddr = {}
    for name, addr in m.sym.items():
        if name.startswith("ex_"):
            byaddr.setdefault(addr, []).append(name)
    return byaddr


def check_build(src_name, tag, rom_base):
    rom, sym = tp(f"zb_disp_{tag}.rom"), tp(f"zb_disp_{tag}.sym")
    build(src_name, rom, sym)
    m = Machine(rom, sym, rom_base=rom_base)
    table = read_table(m)
    names = handler_names(m)
    fails = []

    # --- the INDEPENDENT comparison: table vs the pre-refactor chain ------
    # Resolved by NAME through the symbol file, so this compares meanings
    # ("PRINT_TOKEN dispatches to ex_print") rather than two copies of the same
    # bytes. `'_'` is a character literal in the source and has no symbol.
    def tokval(name):
        if name.startswith("'") and len(name) == 3:
            return ord(name[1])
        return m.sym[name]

    # Until 2026-07-29 each entry carried a third field naming the `IF ROM_BASE
    # < $4000` guard it sat under, and this loop ran TWICE — once per build —
    # dropping the guarded entries from the lean column. The lean build and its
    # gates are retired (docs/spec-lean-retire-s3-gates.md), so every entry is
    # unconditionally resident and the whole table is expected in the one build.
    want = {tokval(tname): (tname, hname) for tname, hname in EXPECTED}
    got = {t: a for t, a in table}

    for tok, (tname, hname) in sorted(want.items()):
        if tok not in got:
            fails.append(f"MISSING from stmt_table: {tname} (${tok:02X}) -> "
                         f"{hname}. The statement is gone: it now falls through "
                         f"to is_letter and a program using it gets `syntax "
                         f"error`.")
        elif got[tok] != m.sym.get(hname):
            at = names.get(got[tok], [f"${got[tok]:04X}"])[0]
            fails.append(f"RE-POINTED: {tname} (${tok:02X}) should dispatch to "
                         f"{hname} but the table says {at}")
    for tok in sorted(set(got) - set(want)):
        at = names.get(got[tok], [f"${got[tok]:04X}"])[0]
        fails.append(f"UNEXPECTED entry ${tok:02X} -> {at}: not in the "
                     f"pre-refactor chain. If a statement was added on purpose, "
                     f"add it to EXPECTED in this file.")

    # --- structural: the table itself ------------------------------------
    toks = [t for t, _ in table]
    dupes = sorted({t for t in toks if toks.count(t) > 1})
    if dupes:
        fails.append(f"duplicate token(s) in stmt_table: "
                     f"{', '.join(f'${d:02X}' for d in dupes)} -- the second "
                     f"entry is unreachable (linear search takes the first)")
    if 0 in toks:
        fails.append("a $00 token is in the table; $00 is the terminator")
    unresolved = [(t, a) for t, a in table if a not in names]
    for t, a in unresolved:
        fails.append(f"token ${t:02X} -> ${a:04X}, which is not any ex_* label "
                     f"(stale or corrupt table entry)")

    # --- behavioural: every entry actually dispatches ---------------------
    for tok, addr in table:
        arrived, regs = [], []
        mm = Machine(rom, sym, rom_base=rom_base)

        def _at(_m, a=addr, _arr=arrived, _rg=regs):
            _arr.append(a)
            _rg.append({"a": _m.cpu.a, "hl": _m.cpu.hl, "f": _m.cpu.f})

        mm.trap(addr, _at)
        # A handler must never be entered by CALL: the dispatch jumps, so the
        # handler returns to exec_stmt's OWN caller. Any RET the handler would
        # do lands on the sentinel and ends the run -- which is what the trap
        # models. Fill the buffer with token + end-of-line.
        mm.poke(BUF, bytes([tok, 0x00]))
        try:
            mm.call("exec_stmt", hl=BUF)
        except RuntimeError as e:
            fails.append(f"token ${tok:02X} -> {names[addr][0] if addr in names else addr:}: {e}")
            continue
        if arrived != [addr]:
            got = "nothing" if not arrived else ", ".join(f"${x:04X}" for x in arrived)
            want = names.get(addr, [f"${addr:04X}"])[0]
            fails.append(f"token ${tok:02X} should reach {want} (${addr:04X}) "
                         f"but reached {got}")
        elif regs:
            # THE ENTRY REGISTER CONTRACT, which arrival alone cannot see.
            # The `cp`/`jp z` chain left A = the statement token, HL = the
            # cursor and Z set; a handler that reads A on entry would break
            # silently under a dispatch that clobbers it, and no test that stops
            # AT the handler would notice. This is the standing
            # clobber-contract trap, so the contract is asserted rather than
            # argued from a static scan of the handlers.
            r = regs[0]
            if r["a"] != tok:
                fails.append(f"token ${tok:02X} -> {names.get(addr,['?'])[0]}: "
                             f"entered with A=${r['a']:02X}, but the chain "
                             f"entered handlers with A = the statement token")
            if r["hl"] != BUF:
                fails.append(f"token ${tok:02X} -> {names.get(addr,['?'])[0]}: "
                             f"entered with HL=${r['hl']:04X}, want the cursor "
                             f"${BUF:04X}")
            if not (r["f"] & 0x40):
                fails.append(f"token ${tok:02X} -> {names.get(addr,['?'])[0]}: "
                             f"entered with Z clear; the chain arrived via "
                             f"`jp z` so Z was always set")

    # --- the two tails: not-a-token letter, and not-a-token non-letter ----
    # `A` (a bare letter) must reach ex_let; a non-letter, non-token byte must
    # reach stmt_error. These are the paths the table search falls THROUGH to,
    # and a search loop that never terminates would break them without
    # breaking any row above.
    for byte_, want in ((ord('A'), "ex_let"), (ord('+'), "stmt_error")):
        if byte_ in toks:
            fails.append(f"test bug: ${byte_:02X} is itself a table token")
            continue
        arrived = []
        mm = Machine(rom, sym, rom_base=rom_base)
        mm.trap(mm.addr(want), lambda _m: arrived.append(1))
        mm.poke(BUF, bytes([byte_, 0x00]))
        mm.call("exec_stmt", hl=BUF)
        if not arrived:
            fails.append(f"a non-token ${byte_:02X} ('{chr(byte_)}') did not "
                         f"reach {want} -- the table-search fallthrough is broken")

    # --- end of line must return without dispatching anything -------------
    mm = Machine(rom, sym, rom_base=rom_base)
    hit = []
    for _, addr in table:
        mm.trap(addr, lambda _m, a=addr: hit.append(a))
    mm.poke(BUF, bytes([0x00]))
    mm.call("exec_stmt", hl=BUF)
    if hit:
        fails.append(f"an empty statement dispatched to ${hit[0]:04X} instead "
                     f"of returning to the prompt")

    return table, fails


def main():
    total_fail = []
    for src_name, tag, base, label in (
            ("main.asm", "reloc", RELOC_BASE, "the BASIC image"),):
        table, fails = check_build(src_name, tag, base)
        print(f"{label}: {len(table)} table entries, "
              f"{len(table) - len([f for f in fails if 'token $' in f])} dispatch OK")
        for f in fails:
            print(f"  FAIL {f}")
        total_fail += fails

    if total_fail:
        print(f"\nFAILED: {len(total_fail)} problem(s)")
        return 1
    print("\nOK: every stmt_table entry dispatches to its handler; "
          "non-token letter -> ex_let, non-token symbol -> stmt_error, "
          "empty statement returns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
