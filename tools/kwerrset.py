#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWT6 — the T6 DENOMINATOR: which errors the REFERENCE raises, per keyword form.

🏗️ JOOST'S RULING (2026-09-27): a keyword proves T6 ("handles the exhaustive
error set") when, FOR EACH DOCUMENTED SYNTAX FORM, it has one row per DISTINCT
error the reference raises for that form -- wrong type, out of range, missing
argument, illegal direct, ... -- each matching the reference's error CODE and
LINE. Finite per keyword, enumerable by probing the reference.

This file is that denominator. `tools/tier_table.py` ticks T6 for a keyword only
when:
  * the keyword is knife-proven CONNECTED (the rule every rung above T1 keeps);
  * EVERY form `tools/kwforms.py` authors for it has an entry here -- a form
    whose error set was never measured leaves the keyword UNRATED, not satisfied;
  * the entries hold at least one code in total (a zero denominator proves
    nothing -- the `kwcover` lesson);
  * every (form, code) pair here has a SUPPORTED kwsweep row declaring
    `PROVES-T6:<code>` with that `FORM:` tag. Those rows run in `stored` mode,
    so the reference's ` in <line>` is part of what is compared.

🔴 AN ENTRY IS A MEASUREMENT, NOT AN OPINION. Each one is written from a probe run
against the reference (never from our own handler -- the `kwforms` circularity
rule: a keyword implemented too simply would get a smaller denominator) and
carries its provenance: the probe, its output file and the date.

⚠️ ABSENCE IS NOT AN EMPTY SET. A keyword missing here has no measured error set
yet and cannot reach T6.
"""
from __future__ import annotations

# keyword -> form -> the error codes the reference raised for that form, and
# where that was measured (PROVENANCE); only a probe run writes an entry.
# 📏 BATCH 1, MEASURED 2026-09-27 (D-KWT6 S2): ten one-form functions already at
# level 3. The battery per argument: wrong type, missing, one extra, and the range
# edges named in the probe. zerobas matched the reference on all 48 cases.
ERRSETS: dict[str, dict[str, frozenset[int]]] = {
    "ABS": {"magnitude": frozenset({2, 13})},
    "SGN": {"sign": frozenset({2, 13})},
    "INT": {"floor": frozenset({2, 13})},
    "SQR": {"square-root": frozenset({2, 5, 13})},
    "LOG": {"logarithm": frozenset({2, 5, 13})},
    "EXP": {"exponential": frozenset({2, 6, 13})},
    "ASC": {"code-of": frozenset({2, 5, 13})},
    "CHR$": {"code-to-char": frozenset({2, 5, 6, 13})},
    "LEN": {"length": frozenset({2, 13})},
    "PEEK": {"address-read": frozenset({2, 6, 13})},
}

PROVENANCE: dict[str, str] = {k: "scratchpad/t6enum_probe.py -> scratchpad/t6enum_run.out (EXP: t6enum_exp.out), VG-8020, 2026-09-27"
                              for k in ERRSETS}


def errset_for(kw: str):
    """{form: frozenset(codes)} for a keyword, or None when never measured."""
    return ERRSETS.get(kw)
