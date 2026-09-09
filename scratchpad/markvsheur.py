#!/usr/bin/env python3
"""classify_open's DERIVED bucket vs the marker actually in TODO.md.

The file says "the MARKERS in this file are what the loop reads"; the
classifier's headline re-derives one. Nothing compares them.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, "tools")
import check_todo_markers as M

subprocess.run([sys.executable, "tools/todo_inventory.py", "--json",
                "/tmp/zerobas/inv_cmp.json"], capture_output=True)
inv = {x["id"]: x for x in json.load(open("/tmp/zerobas/inv_cmp.json"))
       if x["depth"] == 0 and x["state"] == "open"}
buckets = json.load(open("scratchpad/open_buckets.json"))
L = open("TODO.md", encoding="utf-8").read().splitlines()

NAME = {"\U0001f916": "🤖 AUTONOMOUS", "\U0001f52d": "🔭 SCOUT-THEN-ASK",
        "\U0001f64b": "🙋 NEEDS-JOOST", "⛔": "⛔ BLOCKED",
        "\U0001f501": "🔁 STANDING"}
dis = 0
for tid, x in inv.items():
    body = "\n".join(L[x["start"] - 1:x["end"]])
    hit = [NAME[m] for m, rx in M.MARKER.items() if rx.search(body)]
    derived = buckets.get(tid, {}).get("bucket", "?")
    marker = hit[0] if len(hit) == 1 else f"({len(hit)} markers)"
    if marker != derived:
        dis += 1
        h = re.sub(r"[*`~]", "", x["headline"])[:62]
        print(f"  {tid}  file={marker:<18} heuristic={derived:<18} {h}")
print(f"{len(inv)} open items; {dis} where the heuristic disagrees with the MARKER")
