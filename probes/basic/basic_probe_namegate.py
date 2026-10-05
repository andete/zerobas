#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-NAMEGATE — the NAME operand rows, GATED, with their faces PINNED.

The rows lived only in a sweep instrument, so the row D-NAMEORD fixed
(`NAME"X.DAT"AS 5`, 2 -> 53) was unguarded against regression on the disk build.

🎯 AND THE PINS ARE FACES, NOT JUST ROW NAMES. Three filed faces rotted on
2026-09-04 -- the NAME rows themselves said `zb ERR 24` while reading 2 -- and
`filed_row_sweep` cannot see that class: a row that still diverges, but to a
DIFFERENT face, adjudicates as `known` and reads green. So `PINNED` records the
exact (reference, zerobas) pair and this gate goes RED on drift IN EITHER
DIRECTION, which is the shape basic_probe_nodisk.py already uses for 8 rows.
A row that gets FIXED reddens it too -- deliberately: that is the news, and an
un-updated pin is how a fixed row goes back to looking normal.

T-B42E11 closed "the face for a non-string filename" by measuring SIX verbs
(OPEN/KILL/SAVE/LOAD/BLOAD/FILES). Its own plan named THREE — OPEN, KILL and
**NAME** — and NAME is not among the six. `ex_name` calls `fname_expr` twice
(basic/files.asm:1567, 1586), so it inherits the fix structurally; what is
unmeasured is whether it SAYS so.

🔴 AND THE COMMENT ABOVE THE SECOND CALL STILL NAMES THE PRE-FIX FACE:
`NAME"x.dat"AS 5` is documented in basic/files.asm as "still `Syntax error`".
After D-FNEXPR2, `fname_expr` sends a non-string to `els_tc_common`, i.e.
ERR 13. This asks the machine which one it is.

ROUND 1 was zerobas-only (the claim under test was a comment about THIS
tree). It answered **24 `Missing operand`** at the new-name position -- a
THIRD face, neither the comment's ERR 2 nor the fix's ERR 13 -- so round 2
adds the CF-3300, which is the only machine that can say whether 24 is right.
ONE REFERENCE: `NAME` is Disk BASIC; a diskless VG-8020 cannot express it.

⚠️ ERR CODES, NOT MESSAGE TEXT — a code survives message drift and reads
unambiguously off a SCREEN-0 scrape.
"""
import os
import shutil
import sys
import tempfile

# ⚠️ ONE LEVEL DEEPER THAN THE SCRATCHPAD ORIGINAL: probes/basic/ -> repo root
# needs three dirnames, not two. The same slip cost basic_probe_pusing.py and
# basic_probe_namend.py a run each today.
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = _REPO
# ⚠️ A COPY, NOT THE TRACKED IMAGE. `NAME"HI.TXT"AS 5` asks the machine to
# RENAME a real directory entry; if any side gets further than expected it
# would mutate a tracked build input. Both sides drive the same scratch copy
# under /tmp/zerobas (`make temp-root-check`).
_SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")   # `diska` is a PATH, not a flag
TEST_DSK = os.path.join(tempfile.mkdtemp(prefix="namegate-"), "test720.dsk")
shutil.copyfile(_SRC_DSK, TEST_DSK)

# label, statement, what is expected and why
CASES = [
    ("name.as5",  'NAME"X.DAT"AS 5',  "THE SUBJECT. comment says ERR 2 Syntax; fix implies ERR 13"),
    ("name.old5", 'NAME 5 AS"X.DAT"', "the OLD-name position, fname_expr's first call"),
    ("ctl.kill5", 'KILL 5',           "CONTROL: D-FNEXPR2 measured ERR 13 vs the CF-3300"),
    ("ctl.open5", 'OPEN 5 AS #1',     "CONTROL: D-FNEXPR2 measured ERR 13 vs the CF-3300"),
    ("ctl.div0",  'KILL 1/0',         "CONTROL: the operand's own fault wins -> ERR 11, NOT 13"),
    ("ctl.wf",    'NAME"NOSUCH.DAT"AS"Y.DAT"', "CONTROL: well formed -> a FILE error (53), not a type one"),
    # 🎯 THE DISCRIMINATOR. `name.as5` uses an ABSENT old file, so a reference
    # answer of 53 has TWO sufficient causes: "the reference looks the old file
    # up BEFORE evaluating the new name", or "the reference never faults on the
    # new-name operand at all". `HI.TXT` EXISTS on test720.dsk, so the lookup
    # succeeds and only the second cause can still produce a non-type face.
    ("name.ex5",  'NAME"HI.TXT"AS 5', "DISCRIMINATOR: old file EXISTS -- separates lookup-first from never-faults"),
    # \U0001f3af THE SECOND DISCRIMINATOR, and it asks about the FIX rather than the
    # rule. name.ex5's ERR 2 is els_tc_common reporting "the re-drive found no
    # operand" -- but that has two causes too: `eval` never ran, or it ran and
    # parsed nothing. A DIVIDING operand separates them. `KILL 1/0` already
    # answers 11 on both machines (ctl.div0), so if this site's re-drive works at
    # all, `AS 1/0` must answer 11 here too; if it answers 2, the re-drive is not
    # reaching the operand and the cursor is the defect, not the face.
    ("name.exdiv", 'NAME"HI.TXT"AS 1/0',
     "does the SECOND fname_expr site re-drive the operand at all? 11 = yes, 2 = no"),
    # \U0001f3af IS THE SECOND SITE REACHED AT ALL? The rows above only ever see it
    # FAIL, and "declines wrongly" and "never runs" produce the same ERR. A
    # well-formed STRING operand on an EXISTING old file is the one shape that
    # must go all the way through. The probe renames HI.TXT to itself, on its own
    # temp COPY of the image, so the fixture is untouched either way.
    ("name.exok", 'NAME"HI.TXT"AS"HI.TXT"',
     "well formed, old file EXISTS, new name exists too: does the second site complete? 65 = yes (the existence check runs AFTER both names parse)"),
    # \U0001f3af CRUNCHED CONSTANT vs VARIABLE. `NAME 5 AS"X.DAT"` (name.old5) is the
    # SAME crunched numeric constant through the FIRST fname_expr site and it
    # answers 13, so a crunched constant is not inherently the problem -- but the
    # two sites differ in where HL comes from, and this says whether the operand's
    # SHAPE matters at the second one.
    ("name.exvar", 'NAME"HI.TXT"AS A',
     "a numeric VARIABLE, not a crunched constant, at the second site"),
    # \U0001f3af TRIANGULATING AN OFFSET. A crunched constant declines wrongly at the
    # second site and a VARIABLE does not, which no "wrong cursor" story explains
    # on its own: a cursor off by one would break the one-byte variable `A` too.
    # These four vary the operand's stored LENGTH and its leading whitespace, so
    # an offset shows up as a row that starts WORKING when the operand gets
    # longer, and a whitespace bug shows up on the double-space row alone.
    # Every one of them is ERR 13 on the reference -- a non-string operand -- so
    # the reference column is also the control.
    ("name.ex55", 'NAME"HI.TXT"AS 55',
     "TWO-digit constant: does a longer operand start working?"),
    ("name.exsp", 'NAME"HI.TXT"AS  5',
     "the same constant behind TWO spaces: is the skip the defect?"),
    ("name.exab", 'NAME"HI.TXT"AS AB',
     "a TWO-character variable: the variable side of the same length axis"),
    ("name.exneg", 'NAME"HI.TXT"AS -5',
     "a constant behind a unary minus: an operand whose first byte is a TOKEN"),
    # \U0001f3af THE DECLINE-ARM ROW. `(` is handled by str_eval_paren, a DIFFERENT
    # arm of str_eval_one from the fall-through that a bare constant takes, and it
    # declines a numeric subexpression too. If `(5)` works where `5` does not,
    # what differs is the ARM the decline leaves by -- not the operand.
    ("name.exparen", 'NAME"HI.TXT"AS (5)',
     "a constant in PARENTHESES: declines through str_eval_paren, not the tail"),
]


PINNED = {
    # 🟢 2026-10-05: ALL FOUR NAME PINS BELOW ARE GONE -- the rows agree. The
    # "cursor defect" the block explains was the evaluator refusing a factor that
    # starts on an ASCII digit (`AS 5` keeps the 5 ASCII after the name-like AS);
    # D-ASCIINUM (basic/expr.asm ev_f_nonlet) reads it, so eval reaches the operand
    # and 13 / 11 fall out exactly as predicted below. Kept as history.
    # row: (cf3300, zerobas) -- the CURRENT truth, measured 2026-09-04.
    # "name.ex5": ("13", "2"),   -- DELETED 2026-10-05, now agrees   # D-NAMEORD's open half: els_tc_common's re-drive
                               # reports "no operand" -> ERR 2 where 13 is due.
    # \U0001f534 THE SAME DEFECT, AND THIS ROW IS WHAT NAMES IT (2026-09-09).
    # `KILL 1/0` answers 11 on both machines, so the re-drive tail WORKS -- the
    # operand's own fault wins wherever `eval` actually reaches the operand.
    # Through NAME's SECOND fname_expr site the identical operand answers 2, so
    # `eval` is not reaching it at all. That makes this a CURSOR defect, not a
    # face defect: the fix is not "produce 13 here", it is "hand els_tc_common
    # the operand", after which 13 and 11 both fall out. One pin, one mechanism.
    # "name.exdiv": ("11", "2"),   -- DELETED 2026-10-05, now agrees
    # `name.exok` IS NO LONGER PINNED. It was ("65", "0"): the CF-3300 refuses a
    # rename onto an existing name with 65 `File already exists` and zerobas
    # performed it. D-NAMEEXIST (2026-09-28) added the check in hk_name and the
    # message in sub/errmsg.asm -- the two halves this pin's own note said a fix
    # would need -- and the row now agrees at 65. It still proves what it was
    # added for: 65 is raised only after the SECOND fname_expr site has parsed.
    # The same mechanism as name.ex5, at two more operand shapes. Pinned together
    # because they are ONE defect: see the block comment on name.ex5.
    # "name.ex55": ("13", "2"),   -- DELETED 2026-10-05, now agrees
    # "name.exsp": ("13", "2"),   -- DELETED 2026-10-05, now agrees
}


def main():
    cases = [(lab, ["10 ON ERROR GOTO 100",
                    f"20 {stmt}",
                    '30 PRINT"[";0;"]":END',
                    '100 PRINT"[";ERR;"]":END',
                    "RUN"])
             for lab, stmt, _ in CASES]
    sides = {"zb": dict(machine=ZB, boot=8.0, step=2.5, reset=("NEW", "CLS")),
             "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                            reset=("", "SCREEN 0", "NEW", "CLS"))}
    reads = {}
    for side, kw in sides.items():
        m = kw.pop("machine")
        reads[side] = omsx_repl.run_cases(m, cases, diska=TEST_DSK, **kw)
    # 🔴 READ THE SPAN AFTER THE `RUN` ECHO -- the first cut of this fixture
    # matched its own marker in the ECHO of line 30, so every row read the same
    # literal and it reported six-way agreement on a value no case produced.
    got, ref = {}, {}
    for (lab, _s, _e), r in zip(CASES, reads["zb"]):
        got[lab] = (omsx_repl.result_span_after_echo(r, "RUN") or "<none>").strip()
    for (lab, _s, _e), r in zip(CASES, reads["cf3300"]):
        ref[lab] = (omsx_repl.result_span_after_echo(r, "RUN") or "<none>").strip()

    blank = [l for l in ref if ref[l] in ("<none>", "")] + \
            [l for l in got if got[l] in ("<none>", "")]
    if blank:
        print(f"INSTRUMENT FAULT: no reading on {sorted(set(blank))} -- no verdict.")
        return 2

    print(f"{'row':10s} {'cf3300':>8s} {'zb':>8s}   verdict   statement")
    bad = []
    for lab, stmt, _exp in CASES:
        r, g = ref[lab], got[lab]
        if lab in PINNED:
            want = PINNED[lab]
            if (r, g) == want:
                tag = "known-divergent, pinned"
            else:
                bad.append(lab)
                tag = f"🔴 PIN DRIFT from {want}"
        elif r == g:
            tag = "ok"
        else:
            bad.append(lab)
            tag = "🔴 UNPINNED DIVERGENCE"
        print(f"{lab:10s} {r:>8s} {g:>8s}   {tag}   {stmt}")
    print(f"\nrows {len(CASES)}  pinned {len(PINNED)}  red {len(bad)}")
    if bad:
        print("  🔴 A PIN MOVED. If a row was FIXED that is good news and the pin "
              "must move WITH the filing that owns it -- an un-updated pin is how "
              "a fixed row goes back to looking normal.")
    print("NAMEGATE: PASS" if not bad else f"NAMEGATE: RED ({len(bad)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
