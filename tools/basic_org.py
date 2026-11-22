# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""basic_org -- the relocated BASIC image's base address, read from basic/main.asm's BASIC_ORG.

One definition for every tool that needs it (D-CBIOS032, 2026-11-22: the base moved from $2781 to $2BAF when the
repack was rebased on C-BIOS fff98e8, and seven tools had $2781 written into them).

    from basic_org import BASIC_ORG
"""
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_M = re.search(r"^BASIC_ORG:\s+equ\s+\$([0-9A-Fa-f]+)",
               open(os.path.join(_ROOT, "basic", "main.asm")).read(), re.M)
if not _M:
    raise SystemExit("basic_org: no `BASIC_ORG: equ $XXXX` line in basic/main.asm")
BASIC_ORG = int(_M.group(1), 16)
