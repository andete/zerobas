#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PROSEPEND — comments that describe something as PENDING when it has landed.

No gate reads prose, and this session hit the class four times: a worklist sentence
saying "three left" when all five were done, a redundant-load entry asserting a
reload that no longer exists, and TWO ASM headers calling the power-of-two record
length "load-bearing" twenty lines above a body recording its removal.

🎯 THE HARD PART IS SEPARATING NARRATIVE FROM CLAIM. A first pass matched any
comment containing "until" near a landed slice name and returned 61 hits -- almost
all of them the HISTORY this tree deliberately keeps ("was X until D-FOO", "this
line read Y until 2026-08-27"). Those are correct and valuable. Filtering to
FORWARD-looking pendency ("pending the", "not yet", "until it is", "for now",
"once ... lands") and excluding past-tense markers cuts it to 25.

🔴 AND 25 IS NOT 25 FINDINGS EITHER. Most are structural: "the first digit
NOT yet consumed", "not yet packed" -- loop state, not project state. The output is
a READING LIST, and the check is per entry: does the named prerequisite still not
exist? Two were worth opening on 2026-09-09; ONE was stale (`dskchg`) and one was
still true (`SUB_PING` really is unreferenced by the main ROM).

So: a modest instrument with an honest hit rate, kept because the class keeps
recurring and nothing else looks for it.
"""
import os, re, subprocess
log = subprocess.run(['git','log','--oneline'], capture_output=True, text=True).stdout
landed = set(re.findall(r'\bD-[A-Z0-9]+', log))
FWD  = re.compile(r'(is deferred|pending the|not yet\b|cannot yet\b|until it is|until that lands|for now\b|once .* lands|until .* (?:can|lands))', re.I)
PAST = re.compile(r'(was |were |read "|stood |used to|had been|until 20\d\d-|corrected|struck|no longer|~~)', re.I)
DN   = re.compile(r'\bD-[A-Z0-9]+')
hits = []
for root in ('basic','sub','disk'):
    if not os.path.isdir(root):
        continue
    for dp, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(('.asm','.inc')):
                continue
            fp = os.path.join(dp, f)
            lines = open(fp, encoding='utf-8', errors='ignore').read().splitlines()
            for i, l in enumerate(lines):
                t = l.strip()
                if not t.startswith(';'):
                    continue
                if not FWD.search(t) or PAST.search(t):
                    continue
                ctx = " ".join(lines[max(0,i-3):i+4])
                names = sorted({n for n in DN.findall(ctx) if n in landed})
                hits.append((fp, i+1, names, t[:118]))
print("FORWARD-looking pendency in ASM comments: %d\n" % len(hits))
for fp, n, names, t in hits[:26]:
    tag = ("   [names LANDED: %s]" % "/".join(names)) if names else ""
    print("  %s:%d%s" % (fp, n, tag))
    print("      %s" % t)
