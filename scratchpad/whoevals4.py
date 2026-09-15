import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
# CONTROL FIRST: did the redirect actually TAKE?  Read the 5 cell bytes back
# after poking, before trusting any verdict built on it.
REF, KW = "National_CF-3300", dict(boot=14.0, reset=("", "SCREEN 0"))
cells = ":".join("PRINT PEEK(%d);" % a for a in range(65147, 65152))
CASES = [
    ("before", [ 'PRINT"<";', cells, 'PRINT">":END' ]),
    ("after",  [ "POKE 65148,131", "POKE 65149,207", "POKE 65150,255",
                 'PRINT"<";', cells, 'PRINT">":END' ]),
    ("target", [ 'PRINT"<";PEEK(65487);PEEK(65488);">":END' ]),
]
raws = omsx_repl.run_cases(REF, [("stored", l) for _, l in CASES],
                           batch=False, cap_gap=10.0, **KW)
for (n, _), raw in zip(CASES, raws):
    t = " ".join("".join(raw or "").split()); r = t.rfind("RUN")
    tail = t[r+3:] if r >= 0 else t
    i = tail.find("<"); j = tail.find(">", i+1) if i >= 0 else -1
    print(f"  {n:7} {(tail[i:j+1] if i>=0 and j>i else '?'+tail[:45])!r}", flush=True)
