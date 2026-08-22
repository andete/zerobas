#!/usr/bin/env python3
"""D-DUPSPAN2 + D-XREG — real MSX BASIC at sites these carves ALIASED.

Every row below reaches a label that stopped being its own bytes and became an
`equ` onto another one. The claim of a funding slice is that nothing observable
moved, and the eleven acceptance batteries say so at scale; this is the same
claim in a form a person can read, on the SHIPPING ROM, against both references.

⚠️ THESE ARE NOT A SUBSTITUTE FOR THE PER-SITE ROW SET THE SLICE OWES
(docs/spec-basic-dupspan2.md §5.1). They are a demonstration, not coverage: no
knife cuts a canonical here, so a row that agrees is not thereby a row that
could have disagreed.
"""
from __future__ import annotations
import os, re, sys
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}

# 🔴 THE FIRST DRAFT OF THIS FILE READ `<empty>` ON EVERY NON-ERROR ROW, ON ALL
# THREE MACHINES, AND SCORED THEM ALL AS AGREEING. The fall-through report line
# was `PRINT"[";:PRINT"]"` -- a marker with NOTHING IN IT, so `PRINT 1.5<2.5`
# went to the screen where nothing read it and the capture matched by being
# equally blank everywhere. A readout blind to its own subject fails by
# AGREEING. Every row now puts its VALUE inside the brackets, and the rows whose
# answer is an ERROR say so through the handler instead.
#
# label -> (the aliased SITE this reaches, program lines, report-in-handler?)
CASES = [
    ("cmp.lt",   "dcm_lt equ c16_lt",             ['PRINT"[";1.5<2.5;2.5<1.5;"]"']),
    ("cmp.gt",   "fcmp_a_gt2 equ c16_gt",         ['PRINT"[";2.5>1.5;1.5>2.5;"]"']),
    ("ok.pu",    "pu_emit_str0 equ print_string", ['PRINT"[";:PRINT USING"&";"zerobas";:PRINT"]"']),
    ("err.on",   "oe_undef equ ers_undef",        ["ON ERROR GOTO 999"]),
    ("err.log",  "evmc_log_err equ evmc_sqr_err", ["PRINT LOG(0)"]),
    ("err.loc",  "loc_missing equ g8_missing",    ["LOCATE ,"]),
    ("err.paint","gfx_typeerr equ pl_typeerr",    ["SCREEN 2", 'PAINT(10,10),"x"']),
    ("err.gosub","gosub_stk_over (the CANONICAL)",["GOSUB 20"]),
    # 🔴 SEPARATED, because the first run made it look like a carve divergence and
    # it cannot be one: poke_err and ex_let_err are the SAME TWO INSTRUCTIONS
    # (`pop bc / jp stmt_error`) and the alias cannot change which error a POKE
    # raises. Three rows: the trailing comma, the missing address, and a POKE
    # that must simply WORK.
    ("poke.tail","poke_err equ ex_let_err",       ["POKE 1,"]),
    ("poke.head","poke_err equ ex_let_err",       ["POKE ,1"]),
    ("poke.ok",  "poke_err equ ex_let_err (ctl)", ["POKE &HE000,65",
                                                   'PRINT"[";PEEK(&HE000);"]"']),
    # --- D-XREG: the aliases that CROSS the low <-> page-1 boundary ---------
    ("x.strprt", "exps_print equ ems_print",       ['PRINT"[";"ab"+"cd";"]"']),
    ("x.numprt", "exps_fallback equ ems_fallback", ['PRINT"[";1+2;"]"']),
    ("x.int",    "flt_int_result equ evsgn_settype",['PRINT"[";INT(2.7);"]"']),
    ("x.intvar", "vsf_wb_int equ asw_wb_int",      ["A%=1234", 'PRINT"[";A%;"]"']),
    ("x.close",  "dc_finish equ ed_done",          ["CLOSE", 'PRINT"[";9;"]"']),
    ("x.defusr", "ex_def_err equ ee_synerr_pop",   ["DEF USR=&HC000",
                                                    'PRINT"[";1;"]"']),
]
BR = re.compile(r"\[([^\]]*)\]")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search(cap)
    return (" ".join(m.group(1).split()) or "<empty>") if m else "<NO OUTPUT>"


def main() -> int:
    step = float(os.environ.get("DUPSPAN2_STEP", "4.0"))
    agree = same = 0
    for label, site, prog in CASES:
        body = ["10 ON ERROR GOTO 900", "15 SCREEN 0"]
        body += [f"{20+10*k} {ln}" for k, ln in enumerate(prog)]
        # 🔴 AND THE SECOND DRAFT WAS STILL BLIND. With the value printed AND a
        # `[NONE]` fall-through marker, the marker is what the bracket regex
        # found and every value row read 'NONE' on all three machines --
        # agreeing, again, for a reason that has nothing to do with the subject.
        # The fall-through line prints NOTHING now: a row that reaches it and
        # printed no value of its own reads `<NO OUTPUT>`, which is a missing
        # measurement and says so.
        body += ['890 END',
                 '900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        row = {}
        for sd, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=step, cap_gap=10.0,
                timeout=300.0)
            row[sd] = face(caps[0])
        ok_refs = row["vg8020"] == row["cf3300"]
        ok_zb = row["zb"] == row["vg8020"]
        agree += ok_refs
        same += ok_zb
        print(f"  {label:10s} {'refs-agree' if ok_refs else 'REFS DIFFER':12s} "
              f"{'zb=same' if ok_zb else 'zb=DIFF':8s} "
              f"vg={row['vg8020']!r} cf={row['cf3300']!r} zb={row['zb']!r}"
              f"   [{site}]", flush=True)
    print(f"\n  {same} of {len(CASES)} zerobas readings match the VG-8020; "
          f"{agree} of {len(CASES)} references agree with each other", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
