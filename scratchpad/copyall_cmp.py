"""D-COPYALL: compare copymulti_probe.py reports -- zerobas vs the CF-3300.
Per case: the root directory after the run (name, size, first bytes; clusters
ignored) and the LAST screen snapshot with the prompt (Ok / ZB), the key row and
the cursor line dropped. usage: copyall_cmp.py ZB.out REF.out [REF2.out ...]"""
import re, sys

def parse(paths):
    cases = {}
    for p in paths:
        cur = None
        for l in open(p, errors="replace"):
            m = re.match(r"^=== (\S+) ===", l)
            if m:
                cur = m.group(1); cases[cur] = {"dir": [], "screen": [], "snap": []}
                continue
            if cur is None:
                continue
            c = cases[cur]
            m = re.match(r"^\s+# *\d+ (\S+)\s+(\d+) B clus=\S+\s+(.*)$", l)
            if m:
                c["dir"].append((m.group(1), m.group(2), m.group(3).replace("  <-- NEW", "").strip()))
                continue
            if re.match(r"^\s+\[[^\]]+\] emu=", l):
                if c["snap"]:
                    c["screen"] = c["snap"]
                c["snap"] = []
                c["_in"] = True
                continue
            m = re.match(r"^\s+(\d+)\|(.*)$", l)   # CF: "| text", zerobas: "|  text"
            if m and int(m.group(1)) != 23:
                t = m.group(2).strip()
                if t not in ("Ok", "ZB", ".", ""):
                    c["snap"].append(t)
        for c in cases.values():
            if c["snap"]:
                c["screen"] = c["snap"]
    return cases

zb = parse([sys.argv[1]])
ref = parse(sys.argv[2:])
same = diff = 0
for k in zb:
    if k not in ref:
        print(f"{k:16} NO REF"); continue
    a, b = zb[k], ref[k]
    ok_dir = a["dir"] == b["dir"]
    # the probe sets no WIDTH: the CF-3300 wraps at 39 columns, zerobas at 37 --
    # compare the screen TEXT, not where it wraps
    ok_scr = "".join(a["screen"]).replace(" ", "") == "".join(b["screen"]).replace(" ", "")
    if ok_dir and ok_scr:
        same += 1; print(f"{k:16} SAME")
    else:
        diff += 1; print(f"{k:16} DIFF dir={'ok' if ok_dir else 'X'} screen={'ok' if ok_scr else 'X'}")
        if not ok_scr:
            print("    ref:", b["screen"]); print("    zb :", a["screen"])
        if not ok_dir:
            print("    ref:", [(n, s) for n, s, _ in b["dir"]]); print("    zb :", [(n, s) for n, s, _ in a["dir"]])
            for x, y in zip(a["dir"], b["dir"]):
                if x != y: print("      ", y, "->", x)
print(f"SAME {same} DIFF {diff}")
