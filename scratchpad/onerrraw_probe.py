#!/usr/bin/env python3
r"""D-ONERRARM raw-screen check — does the reference print `Syntax error` or
`Syntax error in 30`?

🔴 WHY THIS EXISTS. `onerrarm_probe` reports the untrapped rows as
`<Syntax error>`, and that face comes from `basic_probe_deffn.ERRRE`, whose
alternation matches the message NAME ONLY -- any ` in <line>` suffix is outside
the capture group. So the existing table CANNOT distinguish:

  * a RUN-MODE ABORT   -> "Syntax error in 30"   (ra_abort, message + line)
  * a DIRECT-mode-style report -> "Syntax error" (no line suffix)

and a fix aimed at the first would be unfalsifiable against the second by that
probe. The suffix is the whole discriminator, so read the RAW screen.
[[readout-blind-to-its-own-subject]]
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import basic_probe_deffn as D
import omsx_repl

CASES = {
    'a.badtok':  ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO A',
                  '40 PRINT"[REACHED40]"', '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    'a.badstr':  ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO "X"',
                  '40 PRINT"[REACHED40]"', '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # 🟢 CONTROL: an untrapped abort of a DIFFERENT kind, same fixture. Whatever
    # the machine's abort text looks like, this row shows it -- so the subject's
    # format is compared against the machine's OWN abort, not against my guess.
    'c.abort':   ['10 CLS', '20 B=ASC("")', '30 PRINT"[REACHED30]"', 'RUN'],
    # 🟢 CONTROL: the same statement with a GOOD operand -> no error at all.
    'c.ok':      ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO 900',
                  '40 PRINT"[REACHED40]"', '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # 🎯 WHAT ARE ERR/ERL AFTER THE UNTRAPPED ABORT? This decides whether the
    # fix must call record_errline at all: that routine's only job is to set
    # ERRFLG/ERRLIN, and if the reference leaves them at 0 the call is wrong.
    # Read in DIRECT mode, after the run has already stopped.
    'e.errl':    ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO A',
                  '900 PRINT"[T]"', 'RUN', 'PRINT"[";ERR;ERL;"]"'],
    # 🟢 CONTROL: the SAME read after a known ordinary untrapped abort, so the
    # subject is compared against this machine's own convention, not my guess.
    'e.ctl':     ['10 CLS', '20 B=ASC("")', 'RUN', 'PRINT"[";ERR;ERL;"]"'],
    # 🔴 THE SECOND CAUSE AT THE SAME SITE, AND D-LSETTM JUST PAID FOR ASKING.
    # A fix that tests `cp LINENO_TOKEN` before req_lineno catches the operand
    # stage -- but "the operand is not a line number" and "there is NO operand"
    # are two different failures reaching one test. If the references TRAP the
    # empty one, a single untrapped exit is wrong for it.
    # [[two-rules-that-coincide-on-every-row-you-have]]
    'x.bare':    ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO',
                  '40 PRINT"[REACHED40]"', '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    'x.colon':   ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO :B=1',
                  '40 PRINT"[REACHED40]"', '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # and the ON ERROR-less sibling: does plain GOTO share the untrapped exit?
    'x.goto':    ['10 ON ERROR GOTO 900', '20 CLS', '30 GOTO A',
                  '40 PRINT"[REACHED40]"', '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # 🔴 A THIRD BEHAVIOUR AT THE SAME STAGE. x.bare/x.colon showed `ON ERROR
    # GOTO` with NO operand raises NOTHING on either reference -- execution
    # continues to line 40. So the operand stage has three outcomes, not two:
    #   operand is a line number      -> arm it
    #   operand present, not a lineno -> UNTRAPPED Syntax error
    #   operand ABSENT                -> no error at all
    # But "no error" does not say what happened to the HANDLER, and that is the
    # part a fix has to reproduce. These rows provoke a REAL error afterwards:
    # if the handler was disabled the run aborts untrapped at 40; if it is still
    # armed, 900 runs with ERR 5 / ERL 40.
    'h.bare':    ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO',
                  '40 B=ASC("")', '50 PRINT"[NOTRAP]"', '60 END',
                  '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    'h.colon':   ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO :B=1',
                  '40 B=ASC("")', '50 PRINT"[NOTRAP]"', '60 END',
                  '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # 🟢 CONTROL: handler left ALONE at 30 -- this is what "still armed" reads like.
    'h.ctl':     ['10 ON ERROR GOTO 900', '20 CLS', '30 REM',
                  '40 B=ASC("")', '50 PRINT"[NOTRAP]"', '60 END',
                  '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # 🟢 CONTROL: handler explicitly DISABLED at 30 -- this is what "disabled"
    # reads like. `ON ERROR GOTO 0` is the documented disable.
    'h.off':     ['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO 0',
                  '40 B=ASC("")', '50 PRINT"[NOTRAP]"', '60 END',
                  '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
    # 🔴 THE LAST UNKNOWN BEFORE ANY CODE MOVES. Routing the bare form to
    # `oe_disable` inherits D-ONERR0's special case: `ON ERROR GOTO 0` INSIDE an
    # active handler does not merely disarm, it RE-RAISES the error that entered
    # the handler, untrapped. That behaviour is measured for `GOTO 0`; for the
    # BARE form it is not. If the bare form only disarms, routing it to
    # oe_disable ships a wrong re-raise.
    'i.bare':    ['10 ON ERROR GOTO 900', '20 CLS', '30 B=ASC("")',
                  '40 PRINT"[AFTER40]"', '50 END', '900 ON ERROR GOTO',
                  '910 PRINT"[HANDLERRAN]"', '920 END', 'RUN'],
    # 🟢 CONTROL: `GOTO 0` in the same slot -- the documented re-raise.
    'i.zero':    ['10 ON ERROR GOTO 900', '20 CLS', '30 B=ASC("")',
                  '40 PRINT"[AFTER40]"', '50 END', '900 ON ERROR GOTO 0',
                  '910 PRINT"[HANDLERRAN]"', '920 END', 'RUN'],
    # 🟢 CONTROL: re-ARM in the same slot -- documented to run on.
    'i.rearm':   ['10 ON ERROR GOTO 900', '20 CLS', '30 B=ASC("")',
                  '40 PRINT"[AFTER40]"', '50 END', '900 ON ERROR GOTO 800',
                  '910 PRINT"[HANDLERRAN]"', '920 END', '800 END', 'RUN'],
    # does the statement AFTER a bare form on the same line still run?
    'j.colonrun':['10 ON ERROR GOTO 900', '20 CLS', '30 ON ERROR GOTO :B=7',
                  '40 PRINT"[B=";B;"]"', '50 END',
                  '900 PRINT"[TRAPPED";ERR;ERL;"]"', 'RUN'],
}
ALL = ['a.badtok', 'a.badstr', 'c.abort', 'c.ok', 'e.errl', 'e.ctl',
       'x.bare', 'x.colon', 'x.goto',
       'h.bare', 'h.colon', 'h.ctl', 'h.off',
       'i.bare', 'i.zero', 'i.rearm', 'j.colonrun']
ORDER = (sys.argv[2].split(",") if len(sys.argv) > 2 else ALL)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")

for s in sides:
    cfg = D.SIDES[s]
    print(f"\n{'='*70}\n== {s}  ({cfg['machine']})\n{'='*70}")
    for lab in ORDER:
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + CASES[lab])],
            batch=False, reset=(), boot=cfg["boot"], step=8.0,
            cap_gap=10.0, timeout=300.0)
        raw = caps[0] or ""
        txt = "".join(raw) if not isinstance(raw, str) else raw
        # the 24 rows come back concatenated with no newline; re-split on the
        # known 40-col stride so the message and its suffix stay on one row
        rows = [txt[i:i+40].rstrip() for i in range(0, len(txt), 40)]
        keep = [r for r in rows if r.strip()]
        print(f"\n  --- {lab} ---")
        for r in keep:
            print(f"      |{r}|")
