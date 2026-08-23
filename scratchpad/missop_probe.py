#!/usr/bin/env python3
"""D-MISSOP — is the silent `POKE addr,` write ONE VERB or ONE RULE?

`TODO.md` §"Language / verb surface": `POKE &HE000,` with the value omitted
COMPLETES on zerobas and writes **0**, where both references abort with
`Missing operand`. Filed 2026-08-22 by D-DUPSPAN2's closing demo, re-measured
pre-carve on `834c45b5` so it is not a carve artifact, and filed with an
instruction: **"likely one rule at several verbs — sweep the verbs that take a
trailing value BEFORE pricing."** This is that sweep.

🎯 THE ROOT, READ FROM THE SOURCE FIRST (basic/expr.asm). `ev_f` explicitly
catches an empty operand at `)` and `,` and defers FPERR=4 (`ev_f_empty`,
D-F2-3). It does NOT catch **end of statement**: A=0 falls past every `cp`,
reaches `ev_f_var`, fails `is_letter`, and lands on `ev_f_err` --

    ev_f_err:  ld a,$DD / ld (ERRMARK),a / ld de,0 / ret

-- which sets the ERRMARK landmark and returns a VALUE OF ZERO **without
calling penderr_set**. So `do_poke`'s own `ld a,(FPERR) / or a` check sees a
clean machine and the store proceeds. The mechanism is not missing from the
tree; the END-OF-STATEMENT case is missing from `ev_f`.

📏 THE MECHANICAL DENOMINATOR: 66 evaluator call sites reachable from statement
parsing -- 49 bare `call eval`, 7 `eval_addr`, 5 `eval_byte_checked`, 3
`eval_pos_arg`, 2 `eval_chan` -- across 19 files. Not all are reachable-empty
(many sit behind a delimiter check). ⚠️ THE ROWS BELOW ARE A HAND-LISTED
BASIC-SURFACE SAMPLE OF THAT SET, WHICH IS A SCOPE CLAIM, NOT A COVERAGE ONE
([[a-hand-listed-denominator-is-a-scope-claim]]).

READOUT: `[ERR R]`. `ERR` is 0 when the statement COMPLETED and the MSX error
code when it aborted -- so "did it abort, and with what?" needs no guessing at
the message wording. `R` is a read-back where the statement has an observable
side effect (the POKE'd byte), so a row can say the machine not only failed to
abort but WROTE. Rows with nothing to read print 0 there.

🔴 THE REFERENCES DECIDE. A row whose two reference machines disagree is not a
want and is reported as such.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}


def case(stmt, setup=None, read="0"):
    """One statement under ON ERROR, with a marker exit on both paths.

    ⚠️ `R` is read BEFORE the `SCREEN0:CLS`, because CLS clears VRAM and the
    VPOKE row reads it back. And `SCREEN0` precedes the print on BOTH exits
    because the graphics rows leave the machine in SCREEN 2, where a SCREEN-0
    scrape reads a zeroed pattern table as 960 blanks."""
    p = ["10 ONERRORGOTO900"]
    if setup:
        p.append(f"15 {setup}")
    p += [f"20 {stmt}",
          f'30 R={read}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
          f'900 R={read}:SCREEN0:CLS:PRINT"[";ERR;R;"]":END']
    return p


CASES = {
    # --- POSITIVE CONTROLS: the statement is well formed, or the omission is
    #     one the tree ALREADY catches. Without these a red subject row says
    #     nothing about whether the machine can pass at all. ------------------
    'poke.ok':     case("POKE&HE000,65", read="PEEK(&HE000)"),
    'poke.addr':   case("POKE,1"),              # missing ADDRESS: reaches poke_err
    'locate.addr': case("LOCATE,1"),            # the tree's own ERR 24 site
    'time.val':    case("TIME="),               # time.asm:62 raises ERR 24 by hand
    # --- THE SUBJECT: the value omitted after the comma / after `=` ----------
    'poke.val':    case("POKE&HE000,", setup="POKE&HE000,99", read="PEEK(&HE000)"),
    'vpoke.val':   case("VPOKE0,", setup="VPOKE0,99", read="VPEEK(0)"),
    'out.val':     case("OUT&H98,"),
    'color.val':   case("COLOR15,"),
    'sound.val':   case("SOUND0,"),
    'locate.val':  case("LOCATE1,"),
    'screen.val':  case("SCREEN0,"),
    'key.val':     case("KEY1,"),               # trailing arg is a STRING
    'let.val':     case("A="),
    'lets.val':    case("A$="),                 # missing.asm calls this Missing operand
    'base.val':    case("BASE(0)="),
    'defusr.val':  case("DEFUSR="),
    'midd.val':    case("MID$(A$,2)=", setup='A$="HELLO"'),
    # --- the graphics family (own colour argument), run in SCREEN 2 ----------
    'pset.val':    case("PSET(10,10),", setup="SCREEN2"),
    'line.val':    case("LINE(0,0)-(10,10),", setup="SCREEN2"),
    'circle.val':  case("CIRCLE(50,50),20,", setup="SCREEN2"),
    'sprite.val':  case("PUTSPRITE0,(10,10),", setup="SCREEN2"),
    # --- the same hole INSIDE an expression: a binary operator with no rhs,
    #     which `ev_f` catches at `)` and `,` but not at end of statement -----
    'print.val':   case("PRINT1+"),
    # --- THE DESIGN DISCRIMINATORS. `ev_f_err` is the SHARED tail for every
    #     byte that cannot start a factor, so a fix sited there gives ONE code
    #     to all of them. These four rows ask whether the reference agrees that
    #     they are one rule. -------------------------------------------------
    #   .plus   a binary operator with no operand after it -- reaches ev_f_err
    #           WITHOUT the cursor sitting at end of statement
    #   .paren  a ')' -- already caught, by ev_f_empty, as FPERR=4 -> ERR 2
    #   .colon  end of STATEMENT rather than end of LINE (the fix must catch
    #           both, and ev_f_err catches ':' for free)
    'poke.plus':   case("POKE&HE000,+", setup="POKE&HE000,99", read="PEEK(&HE000)"),
    'poke.paren':  case("POKE&HE000,)", setup="POKE&HE000,99", read="PEEK(&HE000)"),
    'poke.colon':  case("POKE&HE000,:X=1", setup="POKE&HE000,99", read="PEEK(&HE000)"),
    'let.plus':    case("A=+"),
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    """A fenced match that is not digits/spaces/dots/minus is the SOURCE echo,
    not the output -- see [[trapsvc-echo-fence]]. Report it as no reading."""
    if cap is None:
        return "<NO CAPTURE>"
    for m in BR.finditer("".join(cap)):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    return "<NO OUTPUT>"


def main():
    only, sides = None, ["vg8020", "cf3300", "zb"]
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        else:
            only = a.split(",")
    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = nagree = nblank = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only -- no reference column in this run)")
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED (blank reading, not a divergence)"
            nblank += 1
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"
            ndiff += 1
        else:
            note = ""
            nagree += 1
        print(line + note)
    print(f"\nROWS: {len(labels)} printed — {ndiff} DIFF, {nagree} agree, "
          f"{nblank} NOT MEASURED")


if __name__ == "__main__":
    main()
