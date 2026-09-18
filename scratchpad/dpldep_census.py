#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DPLDEP: what does step 9 ACTUALLY have to move, and what may not go?

Step 9 of `disk/docs/spec-diskcode-eviction.md` §6.2 moves the tokenised `LOAD`
loop (`dpl_*`) into `disk.rom`, beside the FAT cursor it calls per byte. §6.2c
measured WHY (a per-byte inter-slot crossing costs 1.72x our LOAD). This tool
answers WHAT -- and the first answer is that the name lies.

\U0001F534 **THE `dpl_` PREFIX IS NOT A DEVICE.** `basic/cload.asm`'s own header
says so out loud, and it is the reason this is a tool and not a `grep dpl_`:

    "\U0001F534 dpl_err IS SHARED WITH THE WHOLE CASSETTE PATH (do_tape_prog above,
     nine `jp c,dpl_err` sites) AND THAT IS WHY THE NOT-FOUND TEST IS NOT HERE."

Moving everything spelled `dpl_*` would therefore move a CASSETTE tail into
`disk.rom` -- where a diskless build cannot reach it at all, and where every tape
failure would cross a slot to report itself. [[a-shared-tail-is-not-a-decision]]
is the standing lesson: a fix sited on a shared tail serves ALL its jumps, so the
unit of decision is the CALL SITE, never the symbol.

WHAT IT MEASURES. The transitive `include` closure of `basic/main.asm` -- what
the MAIN ROM actually assembles -- then, for every symbol in the block:

  IN-EDGES   every `call`/`jp`/`jr` to it, attributed to the ENCLOSING ROUTINE
             and classified TAPE / DISK / SHARED / OTHER from that routine's
             name. This is what decides move-vs-stay-vs-duplicate.
  OUT-EDGES  every symbol the block itself reaches, which is what would become
             a call-back across the slot after the move.

⚠️ IT REFUSES RATHER THAN GUESS. If any in-edge's enclosing routine does not
match a known prefix the tool prints it as UNCLASSIFIED and returns non-zero: an
unattributed call site is exactly the one that would be moved by accident. The
heuristic is named in PREFIX below so a reader can disagree with it row by row.

🔴 IT ALSO COUNTS FALLTHROUGH, BECAUSE THE FIRST CUT DID NOT AND THE
HEADLINE WAS WRONG BY THE MOST IMPORTANT EDGE. `dpl_line` reported ONE in-edge --
its own back-edge from `dpl_body` -- which reads as a nearly-unreferenced
routine. It is in fact the ENTRY POINT of the whole tokenised load, reached by
FALLTHROUGH from `disk_prog_load`, and no `call`/`jp` scan can see that.
[[dupspan-slice]] is the standing lesson: fallthrough and `jr` reach are exactly
what a span sweep cannot see. The terminator test is
`check_tenant_closure._is_terminator`, NOT a regex, for the same reason that file
gives.

⚠️ AND THE ALIASES ARE NOT CODE. Three `dpl_*` names are `equ` aliases of
another routine (D-DUPSPAN2 / D-NGRAM12 de-duplication), so "moving" them is not
a copy but a decision about the routine they alias -- which lives on the TAPE
path for two of the three. The tool prints the alias target and never counts an
alias as bytes.
"""
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import check_tenant_closure as ctc                            # noqa: E402

ROOT = "basic/main.asm"

# The block, as `basic/cload.asm` defines it. Split by WHAT THEY ARE, because an
# `equ` alias and a body are different decisions.
BODIES = ("dpl_line", "dpl_body", "dpl_eof", "dpl_get_store", "dpl_oom_pop",
          "dpl_err", "dpl_nf", "dpl_oom")
ALIASES = ("dpl_link_err", "dpl_err_pop", "dpl_done")
BLOCK = BODIES + ALIASES

# 🎯 THE HEURISTIC, NAMED SO IT CAN BE DISAGREED WITH. A routine's PREFIX says
# which device path it belongs to; anything else is UNCLASSIFIED and refused.
PREFIX = [
    ("ctp_", "TAPE"), ("cas_", "TAPE"), ("do_tape_", "TAPE"),
    ("tape_", "TAPE"), ("cload", "TAPE"), ("csave", "TAPE"),
    ("dpl_", "DISK"), ("disk_", "DISK"), ("ascii_load", "DISK"),
    ("fat", "DISK"), ("df_", "DISK"),
    ("load_", "SHARED"), ("ex_load", "SHARED"), ("ex_run", "SHARED"),
    ("ex_merge", "SHARED"), ("merge", "SHARED"), ("run_", "SHARED"),
]

INC_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.I)
LBL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:")
EQU_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+(\S+)", re.I)
REF_RE = re.compile(r"\b(call|jp|jr)\b[^;]*?\b(%s)\b" % "|".join(BLOCK), re.I)
OUT_RE = re.compile(r"\b(call|jp|jr)\s+(?:[a-z]+\s*,\s*)?([A-Za-z_][A-Za-z0-9_]*)",
                    re.I)
# 🔴 A DIRECTIVE IS NOT AN INSTRUCTION, AND THE FIRST CUT COUNTED IT AS ONE.
# `dpl_done equ load_commit_prog` has no colon, so it read as a code line; it does
# not terminate, so EVERY label after an `equ` was reported as a FALLTHROUGH
# target. Three of the five fallthrough edges in the first run were false that
# way -- a plausible table from an input the tool misread
# [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]. Only lines that
# can actually TRANSFER CONTROL may set the fallthrough predecessor.
DIRECTIVE = re.compile(
    r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"
    r"(equ|ds|db|dw|defb|defw|defs|org|include|incbin|if|ifdef|ifndef|else|"
    r"endif|macro|endm|end|public|extern|module|align)\b", re.I)


def closure(root, base=None):
    """Every file the ROM at `root` actually assembles, transitively."""
    base = base or REPO
    seen, stack = [], [root]
    while stack:
        f = stack.pop(0)
        if f in seen:
            continue
        p = os.path.join(base, f)
        if not os.path.exists(p):
            continue
        seen.append(f)
        for ln in open(p, errors="replace"):
            m = INC_RE.match(ln)
            if m and m.group(1) not in seen:
                stack.append(m.group(1))
    return seen


def classify(routine):
    for pre, cls in PREFIX:
        if routine.startswith(pre):
            return cls
    return "UNCLASSIFIED"


def scan(files, base=None):
    """(in_edges, out_edges, alias_of) over the whole main closure."""
    base = base or REPO
    ins, outs, alias = [], [], {}
    for f in files:
        p = os.path.join(base, f)
        if not os.path.exists(p):
            continue
        cur, prev_code, prev_lbl = "(file prologue)", "", None
        for i, ln in enumerate(open(p, errors="replace"), 1):
            code = ln.split(";")[0]
            m = LBL_RE.match(code)
            if m:
                # 🔴 FALLTHROUGH IS AN IN-EDGE. If the last CODE line before
                # this label does not terminate, control arrives here from the
                # routine above -- invisible to any call/jp scan.
                if (m.group(1) in BLOCK and prev_code
                        and not ctc._is_terminator(prev_code)):
                    ins.append((f, i, m.group(1), prev_lbl or "(above)",
                                classify(prev_lbl or ""), "(FALLTHROUGH from %s)"
                                % (prev_lbl or "?")))
                cur = m.group(1)
                prev_lbl = m.group(1)
            elif code.strip() and not DIRECTIVE.match(code):
                prev_code = code
            e = EQU_RE.match(code)
            if e and e.group(1) in BLOCK:
                alias[e.group(1)] = e.group(2)
                cur = e.group(1)
            for mm in REF_RE.finditer(code):
                ins.append((f, i, mm.group(2), cur, classify(cur),
                            " ".join(code.split())))
            if cur in BLOCK:
                for mm in OUT_RE.finditer(code):
                    t = mm.group(2)
                    if t not in BLOCK and not t.lower() in ("c", "nc", "z", "nz"):
                        outs.append((f, i, cur, t, " ".join(code.split())))
    return ins, outs, alias


def selftest():
    """\U0001F534 THE ARM THAT MATTERS IS THE SHARED TAIL, so it is planted."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="dpldep_")
    try:
        os.makedirs(os.path.join(d, "basic"))
        os.makedirs(os.path.join(d, "sub"))
        open(os.path.join(d, "basic/main.asm"), "w").write(
            '                include "basic/leaf.inc"\n')
        open(os.path.join(d, "basic/leaf.inc"), "w").write(
            "ctp_body:\n"
            "                jp      c,dpl_err\n"          # a TAPE in-edge
            "dpl_line:\n"                                  # <- FALLTHROUGH target
            "                call    fat_io_getbyte\n"      # an OUT-edge
            "                jp      dpl_done\n"            # terminates ->
            "dpl_body:\n"                                  #    NO fallthrough
            "                ret\n"
            "dpl_done        equ     load_commit_prog\n"
            "dpl_nf:\n"                                    # after an `equ`:
            "                ret\n"                        #    NOT a fallthrough
            "wibble_thing:\n"
            "                call    dpl_err\n")            # UNCLASSIFIED
        open(os.path.join(d, "sub/only.asm"), "w").write(
            "                call    dpl_line\n")
        files = closure("basic/main.asm", d)
        ins, outs, alias = scan(files, d)
        ok1 = any(r[2] == "dpl_err" and r[4] == "TAPE" for r in ins)
        print("%s S1 a TAPE routine's edge into the block is seen AND classed "
              "TAPE" % ("PASS" if ok1 else "FAIL"))
        ok2 = any(r[4] == "UNCLASSIFIED" for r in ins)
        print("%s S2 an unknown caller is UNCLASSIFIED, not silently bucketed"
              % ("PASS" if ok2 else "FAIL"))
        ok3 = alias.get("dpl_done") == "load_commit_prog"
        print("%s S3 an `equ` alias records its TARGET (got %r)"
              % ("PASS" if ok3 else "FAIL", alias.get("dpl_done")))
        ok4 = any(r[3] == "fat_io_getbyte" for r in outs)
        print("%s S4 the block's OUT-edges are collected"
              % ("PASS" if ok4 else "FAIL"))
        ok5 = not any(r[0].startswith("sub/") for r in ins)
        print("%s S5 a file only sub/ assembles is NOT in main's closure"
              % ("PASS" if ok5 else "FAIL"))
        # 🔴 THE ARM THE FIRST CUT LACKED, and the reason the headline was
        # wrong: `dpl_line` follows a CONDITIONAL jump, so control falls into it.
        ok6 = any(r[2] == "dpl_line" and "FALLTHROUGH" in r[5] for r in ins)
        print("%s S6 a label after a NON-terminating line gets a FALLTHROUGH "
              "in-edge" % ("PASS" if ok6 else "FAIL"))
        # ⚠️ AND ITS NEGATIVE CONTROL, without which S6 passes on a tool that
        # simply calls EVERY label a fallthrough.
        ok7 = not any(r[2] == "dpl_body" and "FALLTHROUGH" in r[5] for r in ins)
        print("%s S7 a label after an UNCONDITIONAL `jp` gets NO fallthrough "
              "edge" % ("PASS" if ok7 else "FAIL"))
        # 🔴 THE `equ` ARM. Without it three false fallthrough edges shipped.
        ok8 = not any(r[2] == "dpl_nf" and "FALLTHROUGH" in r[5] for r in ins)
        print("%s S8 a label after an `equ` DIRECTIVE gets NO fallthrough edge "
              "(the directive is not an instruction)"
              % ("PASS" if ok8 else "FAIL"))
        return 0 if all((ok1, ok2, ok3, ok4, ok5, ok6, ok7, ok8)) else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    files = closure(ROOT)
    ins, outs, alias = scan(files)
    print("main.asm assembles %d file(s)\n" % len(files))

    print("=== WHAT THE BLOCK IS ===\n")
    print("| symbol | kind | note |")
    print("|---|---|---|")
    for s in BLOCK:
        if s in alias:
            print("| `%s` | **ALIAS** | `equ %s` -- not bytes; the decision is "
                  "about the TARGET |" % (s, alias[s]))
        else:
            print("| `%s` | body | |" % s)

    print("\n=== IN-EDGES: WHO REACHES THE BLOCK, AND FROM WHICH DEVICE PATH "
          "===\n")
    per = {}
    for f, i, tgt, rout, cls, code in ins:
        per.setdefault(tgt, []).append((f, i, rout, cls, code))
    tally = {}
    for tgt in BLOCK:
        rows = per.get(tgt, [])
        cls = sorted({r[3] for r in rows})
        tally[tgt] = cls
        print("**`%s`** -- %d in-edge(s)%s"
              % (tgt, len(rows), "  <- %s" % "/".join(cls) if cls else ""))
        for f, i, rout, c, code in rows:
            print("    %-9s %-28s %s:%d  %s" % (c, rout, f, i, code))
        print()

    print("=== OUT-EDGES: WHAT THE BLOCK REACHES (call-backs after the move) "
          "===\n")
    tgts = {}
    for f, i, rout, t, code in outs:
        tgts.setdefault(t, []).append(rout)
    for t in sorted(tgts):
        print("  %-22s from %s" % (t, ", ".join(sorted(set(tgts[t])))))

    print("\n=== THE VERDICT PER SYMBOL ===\n")
    print("| symbol | in-edges | classes | step 9 |")
    print("|---|---|---|---|")
    bad = 0
    for s in BLOCK:
        rows, cls = per.get(s, []), tally[s]
        if "UNCLASSIFIED" in cls:
            verdict, bad = "\U0001F534 **REFUSED -- an unattributed call site**", bad + 1
        elif s in alias:
            verdict = "alias of `%s` -- decide there, not here" % alias[s]
        elif "TAPE" in cls and "DISK" in cls:
            verdict = "\U0001F534 **SHARED tape+disk -- STAYS, or is duplicated**"
        elif "TAPE" in cls:
            verdict = "\U0001F534 **TAPE reaches it -- it may NOT move**"
        elif cls in (["DISK"], []):
            verdict = "\U0001F7E2 disk-only -- moves"
        else:
            verdict = "SHARED caller -- becomes an entry point"
        print("| `%s` | %d | %s | %s |"
              % (s, len(rows), "/".join(cls) or "-", verdict))

    movable = [s for s in BODIES
               if tally[s] and set(tally[s]) <= {"DISK"}]
    stuck = [s for s in BODIES if "TAPE" in tally[s]]
    print("\n\U0001F7E2 MOVES: %s" % (", ".join("`%s`" % s for s in movable) or "(none)"))
    print("\U0001F534 CANNOT MOVE WHOLE (tape reaches it): %s"
          % (", ".join("`%s`" % s for s in stuck) or "(none)"))
    print("⚠️ ALIASES, decided at their target: %s"
          % ", ".join("`%s`->`%s`" % (s, alias.get(s, "?")) for s in ALIASES))
    if bad:
        print("\n\U0001F534 %d symbol(s) have an UNCLASSIFIED caller. Refusing a "
              "headline: an unattributed call site is exactly the one that "
              "would be moved by accident." % bad)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
