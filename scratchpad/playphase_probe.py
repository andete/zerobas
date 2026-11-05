# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRAPCOST round 3: playqueue_gate's block-point spacing went 98 -> 99/97/98 on a
pure interpreter speed-up. Prints each blocked PLAY's ABSOLUTE return TIME on the
VG-8020 and both zerobas targets (scratchpad/playphase.bas). Clean-room: a tape in,
the printer port out."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs  # noqa: E402

# playphase.bas by default; playphase_q.bas (QUETAB put/get at each return ->
# playphase_q.out) and playdrain.bas (the drain's GET steps -> playdrain.out) too.
bas = sys.argv[1] if len(sys.argv) > 1 else "playphase.bas"
text = open(os.path.join(REPO, "scratchpad", bas)).read()
for m in [run_programs.REF] + list(run_programs.ZB)[:1]:
    r = run_programs.run(m, "playphase", text)
    print(f"{m:30} {r[0]}  {r[1].strip()!r}")
