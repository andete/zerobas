#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-VERBCLASS: of rung 3's 258 B, how much can actually LEAVE main page 1?

Joost approved option 3 of the disk-BASIC relocation -- `COPY`, `FILES`/`LFILES`,
`KILL`, `NAME` into `disk.rom` -- against `verbpartition.py`'s **258 B**. But that
is the SPAN each verb occupies, and a span is not a budget: a verb body that
PARSES ITS OWN ARGUMENTS out of the program text cannot leave the interpreter,
because the statement cursor, the expression evaluator and `stmt_error` all live
main-side.

So this classifies every label inside the four verb spans into three buckets, by
what the label's own source text DOES:

  STAY      it touches the statement cursor, evaluates an expression, parses a
            keyword out of the text, or raises a BASIC error. `fname_expr`,
            `skip_spaces`, `upcase`, `eval`, `stmt_error`, `exec_stmt`,
            `raise_error`, `FN_RESUME`, `chan_gate` (which BECOMES the
            call-through and therefore stays by construction).
  MOVE      disk work with no interpreter contact -- a candidate to relocate.
  TENANT    it only marshals into `dirverb_op` / `subrom_call`: the real work is
            ALREADY in the sub ROM, so moving the marshalling buys the bytes of
            the marshalling and nothing else.

⚠️ THIS IS A SOURCE-TEXT CLASSIFIER, NOT A DISASSEMBLER. It reads what each
label's lines mention; a label that merely NAMES one of these in a comment would
be misfiled, so comments are stripped before matching. The byte SIZES come from
`build/basic-reloc.sym` exactly as `verbpartition.py` takes them, so the totals
reconcile with `basic-reloc`.
"""
import io, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sym = {}
for line in io.open(os.path.join(REPO, "build", "basic-reloc.sym"), errors="replace"):
    m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
    if m:
        sym[m.group(1)] = int(m.group(2), 16)

SRC = io.open(os.path.join(REPO, "basic", "files.asm"),
              encoding="utf-8", errors="replace").read()
# label -> its source lines, comments stripped (a comment that NAMES `stmt_error`
# must not classify the label as interpreter-touching)
bodies, cur = {}, None
for raw in SRC.splitlines():
    m = re.match(r"^([A-Za-z_][\w]*):", raw)
    if m:
        cur = m.group(1)
        bodies.setdefault(cur, [])
    line = raw.split(";", 1)[0].rstrip()
    if cur and line.strip():
        bodies.setdefault(cur, []).append(line)

# \U0001f534 `exec_stmt` AND `raise_error` ARE NOT REASONS TO STAY, AND THE FIRST CUT
# OF THIS CLASSIFIER SAID THEY WERE. `jp exec_stmt` is the UNIVERSAL STATEMENT
# EPILOGUE -- every handler in the tree ends that way, and a relocated body ends
# with a cross-slot return instead; `raise_error`/`load_error`/`disk_error` are an
# ERROR INTERFACE a moved body satisfies by returning a status, which is exactly
# what `DISKOP_STATUS` already does for the sub-ROM tenant. Counting them as
# blockers put `kill_status` (14 B) and `df_nofilespec` (28 B) in STAY on the
# strength of their last instruction, and inflated the verdict.
# What genuinely cannot leave is reading the PROGRAM TEXT: the statement cursor,
# the expression evaluator, and a syntax error raised while parsing.
STAY = ("fname_expr", "fname_fcb", "skip_spaces", "upcase", "eval", "stmt_error",
        "FN_RESUME", "chan_gate", "inc_skip",
        "skip_comma", "eval_byte_arg", "read_into_strscr", "pdfcb_resume")
TENANT = ("dirverb_op", "subrom_call", "DISKOP_OP", "DISKOP_SEL")

VERBS = ["ex_copy", "ex_files", "ex_kill", "ex_name"]
# \U0001f534 THE CUT POINTS ARE **ALL** OF `verbpartition.py`'s REGION HEADS, not just
# the four being priced. Bounding `ex_files` by the next FAT-LIGHT verb instead
# let its span run through `ex_open`, `ex_line`, `ex_close` and
# `init_filechan` -- 1190 B where the verb is 95 -- and the classifier then
# reported 1578 B for a 258 B question. A span is only a verb's if the NEXT
# region head closes it.
CUTS = ["chan_gate", "ex_copy", "disk_error", "ex_files", "ex_open", "ex_line",
        "ex_close", "init_filechan", "ex_kill", "ex_name", "ex_maxfiles",
        "ex_merge"]


def main() -> int:
    known = sorted(((a, n) for n, a in sym.items() if n in bodies), key=lambda t: t[0])
    size = {}
    for i, (a, n) in enumerate(known):
        size[n] = (known[i + 1][0] - a) if i + 1 < len(known) else 0
    starts = {v: sym[v] for v in VERBS if v in sym}
    bounds = sorted(sym[c] for c in CUTS if c in sym)
    tot = {"STAY": 0, "MOVE": 0, "TENANT": 0}
    for v in VERBS:
        a0 = starts[v]
        after = [a for a in bounds if a > a0]
        a1 = after[0] if after else 10 ** 9
        print("===", v)
        sub = 0
        for a, n in known:
            if not (a0 <= a < a1):
                continue
            txt = "\n".join(bodies.get(n, ()))
            cls = ("STAY" if any(k in txt for k in STAY) else
                   "TENANT" if any(k in txt for k in TENANT) else "MOVE")
            s = size[n]
            sub += s
            tot[cls] += s
            print("   %-20s %4d B  %s" % (n, s, cls))
        print("   %-20s %4d B" % ("-- span", sub))
    print()
    print("TOTAL  STAY %d B   TENANT %d B   MOVE %d B   (sum %d)"
          % (tot["STAY"], tot["TENANT"], tot["MOVE"], sum(tot.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
