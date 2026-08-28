#!/usr/bin/env python3
r"""D-POPRAISE: witness each of the four `jp fp_runtime_error` discard-tails
SEPARATELY, before merging them into one.

`scratchpad/popraise_sweep.py` prices the merge at 13 B of main page 1:
cee_abort_fp / cepb_abort_fp / elas_abort_fp / ela_abort_fp are 18 B of
"discard k words, then jp fp_runtime_error" with k in {1,2}.

🔴 THE MERGE CANNOT BE FALSIFIED BY A KNIFE ON THE POPS. D-MIDOP's K-MD2 already
deleted both pops at `ems_typecheck` and moved 0 rows of 9 -- raise_error resets
SP, so the discards are UNOBSERVABLE by construction. A knife that changes the
pop count, or the register, reddens nothing, and a merge "verified" that way is
verified by an arm that never fires.

So the witness is the TARGET instead: knife one tail's `jp fp_runtime_error` to
`jp stmt_error` and the ERR code its callers report changes (11/6 -> 2). Each
tail knifed alone must redden a DISTINCT row set; a tail whose knife reddens
NOTHING is unwitnessed, and merging it is unverifiable rather than safe.

Rows carry candidates for each tail rather than asserting the mapping -- which
row witnesses which tail is MEASURED by the four knives, not declared here.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

OVF = 'HEX$(65536.)'              # a DEFERRED FPERR inside a string RHS (D-F2-1)
NEW = {
    # --- candidates for cee_abort_fp (check_expr_errors / check_fperr_only)
    'f.print'   : (['PRINT 1/0'],            '"OK"'),
    'f.if'      : (['IF 1/0 THEN 40'],       '"OK"'),
    'f.clear'   : (['CLEAR 1/0'],            '"OK"'),
    'f.poke'    : (['POKE 1/0,0'],           '"OK"'),
    # --- candidates for cepb_abort_fp (check_expr_errors_popbc / cepb_fp)
    'f.let'     : (['A=1/0'],                '"OK"'),
    'f.letstr'  : ([f'A$={OVF}'],            '"OK"'),
    # --- candidate for ela_abort_fp (ex_let_arr, arrays.asm:854)
    'f.ary'     : (['DIM A(3)', 'A(1)=1/0'], '"OK"'),
    # --- candidate for elas_abort_fp (ex_let_arr_str, arrays.asm:1026)
    'f.arystr'  : (['DIM A$(3)', f'A$(1)={OVF}'], '"OK"'),
    # --- GREEN CONTROLS on the same apparatus: rows that must NOT move under
    # any of the four knives. Without these a knife that breaks the harness
    # reads as "everything reddened", which is the wrong finding.
    'f.ctl'     : (['A=2'],                  'A'),
    'f.ctlstr'  : (['A$="hi"'],              'A$'),
    'f.ctlary'  : (['DIM A(3)', 'A(1)=7'],   'A(1)'),
}
D.CASES.update(NEW)
labels = sorted(NEW)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, labels) for s in sides}
w = max(len(l) for l in labels)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
for l in labels:
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>22}" for s in sides))
print()
if len(sides) > 1 and "zb" in sides:
    refs = [s for s in sides if s != "zb"]
    diff = [l for l in labels
            if any(res["zb"].get(l) != res[r].get(l) for r in refs)]
    print(f"DIFF vs references: {len(diff)}/{len(labels)}"
          + ("  " + " ".join(diff) if diff else ""))
