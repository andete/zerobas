#!/usr/bin/env python3
"""Route hard-coded /tmp/*.{rom,sym,dsk,bin,lst} literals in tests/ through
tests/_tmp.tp() for parallel-safety. Idempotent. Pass --apply to write."""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIT = re.compile(r'"/tmp/([A-Za-z0-9_]+\.(?:rom|sym|dsk|bin|lst))"')
APPLY = "--apply" in sys.argv

changed = 0
for path in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))):
    src = open(path).read()
    if not LIT.search(src):
        continue
    new = LIT.sub(lambda m: f'tp("{m.group(1)}")', src)
    # ensure the import, right after the first `import os` line
    if "from _tmp import tp" not in new:
        lines = new.splitlines(keepends=True)
        for i, ln in enumerate(lines):
            if re.match(r"import os\b", ln):
                lines.insert(i + 1, "from _tmp import tp\n")
                break
        else:  # no bare `import os` -> put it after the last top-of-file import
            idx = 0
            for i, ln in enumerate(lines[:40]):
                if re.match(r"(import |from )", ln):
                    idx = i + 1
            lines.insert(idx, "from _tmp import tp\n")
        new = "".join(lines)
    if new != src:
        changed += 1
        n = len(LIT.findall(src))
        print(f"  {os.path.relpath(path, ROOT)}: {n} literal(s)")
        if APPLY:
            open(path, "w").write(new)

print(f"\n{changed} file(s) {'CHANGED' if APPLY else 'would change'}")
