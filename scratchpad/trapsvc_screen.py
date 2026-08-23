#!/usr/bin/env python3
"""Dump the RAW screen for one row on one side -- READ THE SCREEN before
believing a red row ([[deterministic-mangle-is-still-a-mangle]])."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl, trapsvc_probe as T
side, label = sys.argv[1], sys.argv[2]
cfg = T.SIDES[side]
caps = omsx_repl.run_cases(cfg["machine"],
                           [("direct", list(cfg["reset"]) + T.CASES[label] + ["RUN"])],
                           batch=False, boot=cfg["boot"], step=5.0, cap_gap=45.0,
                           timeout=600.0)
print(f"=== {side} {label} ===")
print(caps[0] if caps[0] is None else "\n".join(
    caps[0][i:i+40] for i in range(0, len(caps[0]), 40)))
print(f"--- face: {T.face(caps[0])!r}")
