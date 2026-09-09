#!/usr/bin/env python3
"""D-MARKGATE: append the missing pick-up marker to each unmarked open block."""
import re, sys
L = open("TODO.md", encoding="utf-8").read().splitlines(True)

MARK = {
 1552: ["      \U0001f501 STANDING — a ruling of Joost's, kept open so it stays visible. "
        "NOT\n",
        "      pickable work: the /loop reads it, it does not do it.\n"],
 1574: ["      \U0001f501 STANDING — a ruling of Joost's, kept open so it stays visible. "
        "NOT\n",
        "      pickable work; what it re-orders is marked on the items themselves.\n"],
 2513: ["      \U0001f64b NEEDS-JOOST — everything the fix needs is measured; what is left is "
        "the\n",
        "      ~7 B of main page 1, which is a spend, and spends are his "
        "(its own \U0001f52d line above\n",
        "      says exactly this and was invisible to the old marker readout).\n"],
 2917: ["      \U0001f64b NEEDS-JOOST — partition vs merge is his call, in the block's own "
        "words.\n"],
 2947: ["      \U0001f916 AUTONOMOUS — the charter half is ANSWERED (the STANDING sequencing "
        "of\n",
        "      2026-09-02: speed is a real defect), so what remains under it is measurable "
        "work.\n",
        "      ⚠️ **RANKED LAST BY THAT SAME RULING** — every open DIVERGENCE "
        "outranks it, so\n",
        "      being \U0001f916 makes it pickable, not next.\n"],
 4181: ["      \U0001f64b NEEDS-JOOST — (a) is done; (b), which of the 104 earn a battery "
        "slot, is a\n",
        "      runtime-budget call and the measuring in front of it is finished.\n"],
 4834: ["      \U0001f916 AUTONOMOUS — the references settle every row and the message table "
        "already\n",
        "      has the slot.\n",
        "      \U0001f534 **AND THIS ENTRY'S OWN PREMISE IS FALSIFIED**: *\"zerobas has no "
        "`Missing\n",
        "      operand` message at all\"* was true when filed and is not true now —\n",
        "      [`sub/errmsg.asm`](sub/errmsg.asm):231 carries "
        "`em_missing_operand: db \"Missing\n",
        "      operand\",0 ; ERR 24`, reached by "
        "[`sub/circleparse.asm`](sub/circleparse.asm)'s\n",
        "      `cpt_err24`. So the WORDING half may already be closed and the only "
        "measured\n",
        "      divergence left is `A$=+` reading ERR 2 against 24. "
        "**Run the three verbs before\n",
        "      pricing anything** [[a-justification-parenthesis-is-an-unrun-claim]].\n"],
 4975: ["      \U0001f916 AUTONOMOUS — \U0001f4b0 0 ROM bytes; it is a row, and the "
        "references settle it.\n"],
}

def block_end(start):
    i = start          # 1-based line of `- [ ] `
    while i < len(L) and not (i > start and re.match(r"- \[[ x]\] ", L[i])):
        i += 1
    while i > start and L[i - 1].strip() == "":
        i -= 1
    return i           # insert BEFORE this 0-based index == after last content line

ins = sorted(((block_end(s), lines) for s, lines in MARK.items()), reverse=True)
for at, lines in ins:
    L[at:at] = lines
open("TODO.md", "w", encoding="utf-8").write("".join(L))
print(f"inserted markers on {len(MARK)} blocks")
