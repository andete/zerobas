#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Gate: every `TODO.md:NNN (T-xxxxxx)` citation still points at that block.

A line number into a file that gets edited is a rotting citation, and this repo
had 42 of them. The 2026-08-26 archive split repointed all 42 and gave each one
the block's CONTENT-DERIVED id as well -- the id from `tools/todo_inventory.py`,
a digest of the headline, which survives reflow, renumbering and moving the
block to another file. That is exactly what makes this checkable:

    the LINE is for a human's click; the ID is what the check trusts.

RED when a cited line no longer sits inside the block whose id the citation
names. `--fix` rewrites the line number from the id, so the repair is mechanical
rather than a hunt.

⚠️ AN ID-LESS CITATION IS ONLY WEAKLY CHECKED -- the line must exist, and that is
all a bare line number can support. Those are counted and named in the summary
rather than passed over silently, because a check that reports 100 % while a
third of its subject is uncheckable is the 0/0-ALL-CONVERGED shape.

Usage:  python3 tools/check_todo_citations.py            (gate; rc 1 = RED)
        python3 tools/check_todo_citations.py --fix
        python3 tools/check_todo_citations.py --selftest  (rc 2 = instrument fault)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import todo_inventory                                            # noqa: E402
import probe_tmp                                                 # noqa: E402

# Matches `../TODO.md:<n> (T-4AC4B2)` and the `TODO-done.md:<n>` spelling; the
# id group is optional. (The forms are described rather than written out: a
# literal example in this file is a citation this check would then try to
# resolve, and it would be right to fail it.)
CITE = re.compile(r"(?<![-\w])((?:\.\./)?TODO(?:-done)?\.md):(\d+)"
                  r"(?:\s*\((T-[0-9A-F]{6}(?:\.\d+)?)\))?")
SCAN_EXT = (".md", ".py", ".asm", ".inc")

# 🔴 A SYNTHETIC TEST VECTOR IS NOT A CITATION, AND --fix REWROTE ONE
# (2026-08-31, D-FILEDROT). `tools/split_todo_archive.py`'s own self-test feeds
# its regex the string `../TODO.md:668 (T-6FE392)` and asserts the `../` form is   NOT-A-CITATION
# NOT matched. This check read that STRING LITERAL as a live citation and
# re-anchored 668 -> 703. The assertion survived (it asserts `== []`, so any
# number passes) -- which is exactly why nobody would have noticed: the vector's
# MEANING was corrupted while every test stayed green, and the rewrite recurred
# on every TODO.md edit, churning a tool file and forcing the emulator tier to
# re-run for nothing.
# This file's header already names the hazard for ITS OWN literals; the marker
# generalises that to any file. Same shape as audit_citations.py's `_DUMP_VEC`,
# whose invented bytes are recorded rather than worked around.
NOCITE = "NOT-A-CITATION"


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True)
    if out.returncode != 0:
        sys.exit(2)
    return [f for f in out.stdout.split()
            if f.endswith(SCAN_EXT) or os.path.basename(f) == "Makefile"]


def resolve(citing_rel: str, spelled: str, root=ROOT) -> str | None:
    """Repo-relative path of the file a citation in `citing_rel` names.

    ⚠️ RELATIVE FIRST, THEN REPO ROOT. A `../TODO.md` in `docs/` is relative;
    a bare `TODO.md` in a `scratchpad/` docstring means the repo's TODO.md, not
    a sibling that has never existed. The first cut resolved relative ONLY and
    reddened five citations that were perfectly correct -- the check was wrong
    about the convention, not the repo."""
    for cand in (os.path.normpath(os.path.join(os.path.dirname(citing_rel), spelled)),
                 os.path.normpath(spelled.replace("../", ""))):
        if os.path.exists(os.path.join(root, cand)):
            return cand
    return None


_CACHE: dict[str, list] = {}


def blocks_of(rel: str):
    if rel not in _CACHE:
        _CACHE[rel] = todo_inventory.blocks(os.path.join(ROOT, rel))
    return _CACHE[rel]


def block_at(rel, line):
    """The DEEPEST block covering `line`. A nested `- [x]` has an id too, and
    restricting this to depth 0 left 12 citations permanently uncheckable --
    they point INTO nested items, which is exactly where the detail lives."""
    hit = [b for b in blocks_of(rel) if b["start"] <= line <= b["end"]]
    return max(hit, key=lambda b: b["depth"]) if hit else None


def block_by_id(rel, bid):
    for b in blocks_of(rel):
        if b["id"] == bid:
            return b
    return None


def scan(files, root=ROOT):
    """-> list of findings (rel, lineno, spelled, line, bid, verdict, detail)."""
    out = []
    for rel in files:
        path = os.path.join(root, rel)
        try:
            text = open(path).read()
        except (OSError, UnicodeDecodeError):
            continue
        if "TODO" not in text:
            continue
        for n, src in enumerate(text.splitlines(), 1):
            if NOCITE in src:       # a synthetic vector, not a reference
                continue
            for m in CITE.finditer(src):
                spelled, line, bid = m.group(1), int(m.group(2)), m.group(3)
                tgt = resolve(rel, spelled)
                if tgt is None:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"names {spelled}, which does not exist"))
                    continue
                nlines = len(open(os.path.join(root, tgt)).read().splitlines())
                href = src[:m.start()].endswith("](")
                if line < 1 or line > nlines:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"{tgt} has {nlines} lines; :{line} is past the end"))
                    continue
                if href:
                    # 🔴 THE TWO HALVES OF A MARKDOWN LINK MUST AGREE. The
                    # 2026-08-26 repoint rewrote labels and skipped hrefs on
                    # its first pass, leaving a link whose label named one line
                    # and whose target named another -- it reads right and goes
                    # somewhere else. (Spelled in prose: a literal example would
                    # be read by this very check as a live citation.) The id
                    # belongs on the LABEL (a `](path (T-x))` is not a URL), so
                    # an href is checked against the label beside it instead.
                    lab = list(CITE.finditer(src[:m.start()]))
                    if not lab:
                        out.append((rel, n, spelled, line, bid, "RED",
                                    "link target with no label citation to agree with"))
                    elif (lab[-1].group(1), lab[-1].group(2)) != (spelled, str(line)):
                        out.append((rel, n, spelled, line, bid, "RED",
                                    f"the link's two halves disagree: label says "
                                    f"{lab[-1].group(1)}:{lab[-1].group(2)}, "
                                    f"target says {spelled}:{line}"))
                    else:
                        out.append((rel, n, spelled, line, bid, "PAIR", ""))
                    continue
                if bid is None:
                    here = block_at(tgt, line)
                    out.append((rel, n, spelled, line, bid, "WEAK",
                                f"no block id -- annotatable as "
                                f"({here['id']})" if here else
                                "no block id, and the line is in no block at all"))
                    continue
                here = block_at(tgt, line)
                if here is not None and here["id"] == bid:
                    out.append((rel, n, spelled, line, bid, "OK", ""))
                    continue
                want = block_by_id(tgt, bid)
                if want is None:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"{bid} is in no block of {tgt} "
                                f"(headline edited, or moved to the other file?)"))
                else:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"{bid} is at {tgt}:{want['start']}, not :{line}"))
    return out


# --- D-CITESUBJ: the same sentence must not name two different blocks --------
# 🔴 THE HOLE THIS CLOSES (TODO.md, filed 2026-09-05 by D-EXPBAND). Every check
# above asks "does the id match the line?", so a citation whose line and id agree
# is self-consistent NO MATTER WHICH BLOCK IT NAMES. Four citations were found
# pointing at unrelated subjects, and the fourth was **GREEN and in the
# "verified" category** at the moment it was read.
#
# 🎯 THE STRUCTURAL SIGNAL, NOT A SEMANTIC ONE. Three of the four were the SAME
# sentence in three sibling docs (`RETIRE THE LEAN 16 KB CART`) resolving to
# THREE DIFFERENT blocks. That is a contradiction inside the tree — at most one
# can be right — and it needs no guess about meaning to detect.
#
# ⚠️ THE SEMANTIC VERSION IS A MEASURED NEGATIVE, AND THAT IS WHY THIS IS NOT IT.
# The filed suggestion was to flag a citation sharing no distinctive token with
# the cited block. Measured 2026-09-05 over the live corpus: comparing against
# the HEADLINE flags **30 of 46**; against the WHOLE BLOCK, **21 of 46** — and
# since the four known-bad citations are already repointed, every one of those is
# a false positive. A 46% advisory is one nobody reads
# [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]. Not shipped;
# recorded so the next person does not re-derive it.
#
# ⚠️ 2026-09-09: THE PREMISE OF THAT FALSE-POSITIVE RATE TOOK TWO MORE.
# "The four known-bad citations are already repointed" is what makes every flag
# above a false positive, and the set was not closed: closing the D-TRAPSVC item
# renamed its block, and the rename exposed TWO citations that had been pointing
# at it while talking about something else entirely -- scratchpad/evferr_probe.py
# (subject: ev_f_err's seven jump sites, really T-52206B in docs/TODO-done.md)
# and docs/spec-basic-graphics.md (subject: the Phase-3 graphics charter item,
# really T-E40465 there). Both were repointed in the same commit.
# 🎯 THE MECHANISM IS THIS FILE'S OWN --annotate: it attaches an id FROM THE
# BLOCK AT THAT LINE, so a citation whose line had already drifted -- and every
# line drifted in 2026-08-27's 12577 -> 3874 archive split -- gets a CONFIDENT
# WRONG ID, after which --fix keeps rewriting the line to match it. A stale
# citation is laundered into a precise one, and from then on nothing can see it:
# the id resolves, the line agrees, and only a human reading both ends notices.
# 🔴 SO THE 46% WAS MEASURED AGAINST A CORPUS ASSUMED CLEAN. The count is not
# re-derived here -- two more known-bad out of 46 does not make a 46% advisory
# readable -- but the reason for NOT shipping it is now weaker than it reads
# above, and the next person weighing it should re-measure the denominator first
# rather than inherit this paragraph [[a-ranked-candidate-rots-like-a-wall]].
SUBJ_TOK = re.compile(r"`[^`\n]{2,40}`|\"[^\"\n]{2,40}\"|\b[A-Z][A-Z0-9_$]{3,}\b")


def _sentence(src_line: str) -> str | None:
    """The citing sentence, normalised, or None if it cannot carry a subject.

    The citation's own machinery is stripped: a `TODO.md:NNN (T-XXXXXX)` is not
    evidence of what the sentence is ABOUT. What is left must be long enough to
    be a claim AND carry at least one distinctive token (a backticked
    identifier, a quoted string, a CAPITALISED word) — otherwise two unrelated
    items could share it honestly and the check would be measuring boilerplate.
    """
    bare = CITE.sub("", src_line)
    if not SUBJ_TOK.search(bare):
        return None
    norm = " ".join(re.sub(r"[^A-Za-z0-9`$#\"'()/. ]+", " ", bare).split()).lower()
    return norm if len(norm) >= 25 else None


def subject_conflicts(findings, root=ROOT):
    """-> [(sentence, [(citing, target, id), ...])] where one sentence names
    two or more DIFFERENT blocks."""
    seen = {}
    for rel, n, spelled, line, bid, verdict, _ in findings:
        if verdict not in ("OK", "PAIR"):
            continue
        tgt = resolve(rel, spelled)
        if tgt is None:
            continue
        blk = block_at(tgt, line)
        if blk is None:
            continue
        try:
            src = open(os.path.join(root, rel), encoding="utf-8",
                       errors="replace").read().splitlines()
        except OSError:
            continue
        key = _sentence(src[n - 1]) if n <= len(src) else None
        if key is None:
            continue
        seen.setdefault(key, []).append((f"{rel}:{n}", tgt, blk["id"]))
    return [(k, v) for k, v in seen.items()
            if len({(t, i) for _, t, i in v}) > 1]


def apply_fix(findings, root=ROOT):
    """Rewrite drifted line numbers from the id. Only touches repairable REDs."""
    by_file: dict[str, list] = {}
    for f in findings:
        if f[5] == "RED" and f[4]:
            tgt = resolve(f[0], f[2])
            if tgt and block_by_id(tgt, f[4]):
                by_file.setdefault(f[0], []).append(f)
    n = 0
    for rel, fs in by_file.items():
        path = os.path.join(root, rel)
        lines = open(path).read().splitlines(keepends=True)
        for rel_, lineno, spelled, line, bid, _, _ in fs:
            tgt = resolve(rel_, spelled)
            new = block_by_id(tgt, bid)["start"]
            lines[lineno - 1] = lines[lineno - 1].replace(
                f"{spelled}:{line}", f"{spelled}:{new}")
            n += 1
        open(path, "w").writelines(lines)
    return n


def annotate(weak, root=ROOT):
    """Attach `(T-xxxxxx)` to an id-less citation from the block at that line."""
    by_file: dict[str, list] = {}
    for w in weak:
        by_file.setdefault(w[0], []).append(w)
    n = 0
    for rel, ws in by_file.items():
        path = os.path.join(root, rel)
        lines = open(path).read().splitlines(keepends=True)
        for rel_, lineno, spelled, line, _, _, _ in ws:
            tgt = resolve(rel_, spelled)
            b = block_at(tgt, line) if tgt else None
            if not b:
                continue
            lines[lineno - 1] = lines[lineno - 1].replace(
                f"{spelled}:{line}", f"{spelled}:{line} ({b['id']})", 1)
            n += 1
        open(path, "w").writelines(lines)
    return n


def selftest():
    """🔬 FALSIFY BY PLANTING. Both senses required: a drifted citation must go
    RED, and the SAME apparatus must be GREEN on the same citation undrifted.
    A red arm that passes because it never fired is not an arm."""
    import shutil
    real = scan(tracked())
    ok = [f for f in real if f[5] == "OK"]
    if not ok:
        print("SELFTEST rc 2: no OK citation to plant against -- the apparatus "
              "has nothing to prove it can pass.")
        return 2
    # the selftest copies the tree; probe_tmp owns the directory and gives it
    # back at exit (`make temp-root-check`), so a failed run leaves nothing.
    tmp = probe_tmp.tmp("todocite-selftest")
    os.makedirs(tmp, exist_ok=True)
    for rel in {"TODO.md", "docs/TODO-done.md", ok[0][0]}:
        d = os.path.join(tmp, os.path.dirname(rel))
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(tmp, rel))
    rel, lineno, spelled, line, bid, _, _ = ok[0]
    _CACHE.clear()
    green = scan([rel], root=tmp)
    g = [f for f in green if f[1] == lineno and f[4] == bid]
    if not (g and g[0][5] == "OK"):
        print(f"SELFTEST rc 2: the GREEN control did not pass on the copy "
              f"({g[0][5] if g else 'citation not found'}). The apparatus is "
              f"reading something other than its subject.")
        return 2
    # plant the drift: same id, a line number one block away
    p = os.path.join(tmp, rel)
    txt = open(p).read().splitlines(keepends=True)
    txt[lineno - 1] = txt[lineno - 1].replace(f"{spelled}:{line}",
                                              f"{spelled}:{line + 400}")
    open(p, "w").writelines(txt)
    _CACHE.clear()
    red = scan([rel], root=tmp)
    r = [f for f in red if f[1] == lineno and f[4] == bid]
    _CACHE.clear()
    if not (r and r[0][5] == "RED"):
        print(f"SELFTEST rc 2: the planted drift did NOT go red "
              f"({r[0][5] if r else 'citation not found'}). The check cannot "
              f"detect the thing it exists to detect.")
        return 2
    # --- S-NOCITE: the opt-out marker suppresses, and ONLY when present ------
    # 🔬 The same red/green discipline: an exemption that never fires is not an
    # exemption, and one that fires unconditionally is a hole. Both directions
    # are checked on the SAME line of the SAME file.
    txt = open(p).read().splitlines(keepends=True)
    txt[lineno - 1] = txt[lineno - 1].replace(f"{spelled}:{line + 400}",
                                              f"{spelled}:{line}")
    open(p, "w").writelines(txt)
    _CACHE.clear()
    before = [f for f in scan([rel], root=tmp) if f[1] == lineno]
    txt[lineno - 1] = txt[lineno - 1].rstrip("\n") + f"  {NOCITE}\n"
    open(p, "w").writelines(txt)
    _CACHE.clear()
    after = [f for f in scan([rel], root=tmp) if f[1] == lineno]
    _CACHE.clear()
    if not before:
        print("SELFTEST rc 2: the un-marked control found NO citation, so the "
              "marker arm below would pass on an empty set.")
        return 2
    if after:
        print(f"SELFTEST rc 2: {NOCITE} did NOT suppress the citation on "
              f"{rel}:{lineno} -- the opt-out does not work.")
        return 2
    # --- D-CITESUBJ arms: the sibling-conflict check, both senses -----------
    # 🔴 THIS CHECK HAS NO LIVE TRUE POSITIVE — the four citations that motivated
    # it are already repointed, and it reads 0 on the tree. So its ONLY evidence
    # that it can detect anything is here, reconstructing the historical shape:
    # three sibling docs carrying the SAME sentence and resolving to DIFFERENT
    # blocks. Without this arm it would be a check that has never fired, which is
    # indistinguishable from a check that cannot [[a-case-that-agrees-can-agree-
    # for-the-wrong-reason]].
    _CACHE.clear()
    tb = [b for b in blocks_of("TODO.md") if b["id"]][:2]
    if len(tb) < 2:
        print("SELFTEST rc 2: fewer than two identified blocks to point at.")
        return 2
    sent = "RETIRE THE LEAN 16 KB CART — the parent item"
    os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
    def _plant(l0, l1):
        for name, blk in (("s_a.md", l0), ("s_b.md", l1)):
            with open(os.path.join(tmp, "docs", name), "w") as fh:
                fh.write(f"{sent} (../TODO.md:{blk['start']} ({blk['id']}))\n")
        _CACHE.clear()
        found = scan(["docs/s_a.md", "docs/s_b.md"], root=tmp)
        return subject_conflicts(found, root=tmp), found
    conf, found = _plant(tb[0], tb[1])
    if len(found) != 2 or any(f[5] != "OK" for f in found):
        print(f"SELFTEST rc 2: the D-CITESUBJ fixture's own citations are not "
              f"OK ({[f[5] for f in found]}) — the arm would score nothing.")
        return 2
    if len(conf) != 1:
        print(f"SELFTEST rc 2: two docs naming DIFFERENT blocks with one "
              f"sentence gave {len(conf)} conflict(s), want 1. The check "
              f"cannot detect the shape it exists for.")
        return 2
    same, _ = _plant(tb[0], tb[0])
    if same:
        print(f"SELFTEST rc 2: two docs naming the SAME block gave "
              f"{len(same)} conflict(s), want 0 — it fires on agreement.")
        return 2
    # a sentence with no distinctive token cannot carry a subject and must be
    # skipped rather than grouped: generic boilerplate ("Detail: see below.")
    # honestly appears under unrelated items.
    if _sentence("detail is recorded in the section below for the reader") is not None:
        print("SELFTEST rc 2: a sentence with no distinctive token was accepted "
              "as a subject; boilerplate would collide.")
        return 2
    if _sentence("the `LOAD\"CAS:\"` tokenised-tape item, parent of this step") is None:
        print("SELFTEST rc 2: a sentence WITH a distinctive token was rejected; "
              "the check would see nothing.")
        return 2
    _CACHE.clear()

    print(f"selftest: GREEN control passes and a planted drift goes RED "
          f"on {rel}:{lineno} ({bid}); {NOCITE} suppresses "
          f"{len(before)} citation(s) there and nothing else; D-CITESUBJ fires "
          f"on two docs naming different blocks and not on agreement ✅")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--annotate", action="store_true",
                    help="attach the block id to id-less citations, from the "
                         "block that is at that line NOW (idempotent)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rc = selftest()
    if rc:
        return 2
    _CACHE.clear()
    f = scan(tracked())
    red = [x for x in f if x[5] == "RED"]
    weak = [x for x in f if x[5] == "WEAK"]
    ok = [x for x in f if x[5] == "OK"]
    pair = [x for x in f if x[5] == "PAIR"]
    if a.annotate and weak:
        n = annotate(weak)
        print(f"--annotate: attached {n} block id(s); re-run to confirm")
        return 0
    if a.fix and red:
        n = apply_fix(f)
        print(f"--fix: rewrote {n} line number(s) from the block id; re-run to confirm")
        return 0
    print(f"todo-citations: {len(f)} citation(s) into TODO.md / docs/TODO-done.md "
          f"across {len({x[0] for x in f})} file(s)")
    print(f"  {len(ok):3d} verified against the block id")
    print(f"  {len(pair):3d} link targets agreeing with their label")
    print(f"  {len(weak):3d} id-less (line existence only -- NOT verified):")
    for x in weak:
        print(f"        {x[0]}:{x[1]} -> {x[2]}:{x[3]}")
    conflicts = subject_conflicts(f)
    print(f"  {len(conflicts):3d} sentence(s) naming MORE THAN ONE block "
          f"(D-CITESUBJ: at most one can be right)")
    for key, hits in conflicts:
        print(f'        "{key[:76]}"')
        for citing, tgt, bid in hits:
            print(f"           {citing} -> {tgt} ({bid})")
    if red or conflicts:
        print(f"  {len(red):3d} RED:")
        for x in red:
            print(f"        {x[0]}:{x[1]} -> {x[2]}:{x[3]} "
                  f"{'(' + x[4] + ') ' if x[4] else ''}{x[6]}")
        if red:
            print("\n  fix mechanically with: python3 tools/check_todo_citations.py --fix")
        if conflicts:
            print("\n  \U0001f534 a conflict is NOT mechanically fixable: read the "
                  "sentence and decide which block it is about.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
