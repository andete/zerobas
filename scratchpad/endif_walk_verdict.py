#!/usr/bin/env python3
r"""D-ENDIFWALK: the CORRECTED terminator verdict, and how many edges it changes.

The scout measured the denominator: 68 span pairs whose last source line is an
assembler DIRECTIVE, not an instruction -- 32 `endif`, 22 `if`, 13 `include`,
1 `else`. The item named only ENDIF; the other 36 are the same defect unnamed.

THE CORRECT ANSWER PER SHAPE:
  ENDIF     the construct terminates iff EVERY ARM does. `_is_terminator` is
            fine; what it must be asked about is each arm's last instruction.
  IF cond   the span's own code ends BEFORE the directive, and the label that
            follows lives INSIDE the conditional -- so the predecessor's status
            is its last real instruction above the `IF`.
  ELSE      same, for the arm that just closed.
  include   the last code line is, recursively, the last code line of the
            INCLUDED FILE.

A wrong "does not terminate" adds a fallthrough edge that should not exist, which
in check_dead_code makes the next label reachable -- the direction that HIDES
dead code. That is a gate going quiet, not one crying wolf, which is why it is
worth measuring rather than assuming it "cost nothing".
"""
import os, re, sys
sys.path.insert(0, "tools")
import check_dead_code as cdc
import check_tenant_closure as ctc

LBL = re.compile(r"^\w+:$")
INC = re.compile(r'^include\s+"([^"]+)"', re.I)
IFD = re.compile(r"^if(?:def|ndef)?\b", re.I)
ELSED = re.compile(r"^else\b", re.I)
ENDIFD = re.compile(r"^endif\b", re.I)
DIRECTIVE = re.compile(
    r"^(endif|else|endm|end|if|ifdef|ifndef|macro|local|proc|endp|public|"
    r"module|endmodule|align|org|include|incbin|rept|endr|\.\w+)\b", re.I)


def file_lines(path):
    try:
        return [ln.split(';', 1)[0] for ln in open(path)]
    except OSError:
        return []


def terminates(lines, depth=0):
    """Does this line list end in an unconditional flow break?

    Returns True/False, or None when it cannot be decided (an unresolved
    include, a construct that does not close) -- NEVER guess, because a guessed
    True deletes a real edge and a guessed False keeps a phantom one.
    """
    if depth > 6:
        return None
    # walk backwards to the last meaningful line
    i = len(lines) - 1
    while i >= 0:
        t = lines[i].strip()
        if not t or LBL.match(t):
            i -= 1
            continue
        m = INC.match(t)
        if m:
            for cand in (m.group(1), os.path.join("basic", m.group(1)),
                         os.path.join("sub", m.group(1))):
                if os.path.exists(cand):
                    return terminates(file_lines(cand), depth + 1)
            return None
        if ENDIFD.match(t):
            # collect the arms of this conditional and require ALL to terminate
            arms, cur, lvl = [], [], 0
            j = i - 1
            while j >= 0:
                s = lines[j].strip()
                if ENDIFD.match(s):
                    lvl += 1
                elif IFD.match(s):
                    if lvl == 0:
                        break
                    lvl -= 1
                elif ELSED.match(s) and lvl == 0:
                    arms.append(list(reversed(cur)))
                    cur = []
                    j -= 1
                    continue
                cur.append(lines[j])
                j -= 1
            if j < 0:
                return None                      # never found the opening IF
            arms.append(list(reversed(cur)))
            vs = [terminates(a, depth + 1) for a in arms]
            if any(v is None for v in vs):
                return None
            return all(vs)
        if IFD.match(t) or ELSED.match(t):
            i -= 1                               # the span's code ends above it
            continue
        if DIRECTIVE.match(t):
            i -= 1
            continue
        return ctc._is_terminator(t)
    return False                                 # nothing but directives/labels


changed = same = undecided = 0
rows = []
for top, build in (("basic/main.asm", "main"), ("sub/sub.asm", "sub")):
    sp = cdc.Spans(top, build)
    for order in sp.seq.values():
        for a, b in zip(order, order[1:]):
            lines = sp.nodes.get(a, [])
            last = cdc.Spans._last_code(lines)
            if not last or not DIRECTIVE.match(last.strip()):
                continue
            old = ctc._is_terminator(last)
            new = terminates(lines)
            if new is None:
                undecided += 1
                rows.append((build, sp.owner.get(a, "?"), a, b, last.strip(),
                             old, "UNDECIDED"))
            elif new != old:
                changed += 1
                rows.append((build, sp.owner.get(a, "?"), a, b, last.strip(),
                             old, new))
            else:
                same += 1
print(f"68 directive-ending pairs: {changed} VERDICT CHANGES, {same} agree, "
      f"{undecided} undecided")
print()
for build, f, a, b, last, old, new in rows:
    tag = ("PHANTOM EDGE REMOVED — the span DOES terminate"
           if new is True else
           "undecidable, edge KEPT (never guess)" if new == "UNDECIDED" else
           "edge ADDED — the span does NOT terminate")
    print(f"  [{build}] {f}: {a} -> {b}")
    print(f"      last line {last!r}: was terminator={old}, corrected={new}")
    print(f"      => {tag}")
