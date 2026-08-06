# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""audit_citations.py — the mechanical half of the clean-room paper-trail audit.

This is NOT the whole audit. It mechanizes the cheap, bounded checks that
docs/clean-room-audit.md calls "the precondition that keeps paper trail cheap"
plus the forbidden-source scan — so they cannot silently lapse between the
manual, agent-driven paper-trail passes. It deliberately does NOT make the one
judgement call the audit doc reserves for a human: "is this probe genuinely
black-box?". A green run here means the citation scaffolding is intact and no
forbidden-source line slipped in unattested; it does NOT certify provenance.

GATING checks (a finding => exit 1):

  1. FORBIDDEN-SOURCE SCAN — every line naming a forbidden derivation method
     (disassembly, byte-COPYING, reverse-engineering, the Red Book) must sit in
     a NEGATION/attestation context ("nothing is derived from ... disassembly").
     A forbidden token used affirmatively is the highest-severity finding.
     NOTE: "byte-identical" is NOT forbidden — producing output byte-identical to
     an oracle by *observing* it (e.g. our GETDPB vs the CF-3300) is the
     gold-standard clean-room result, the opposite of a byte-copy.
     NOTE: a QUALIFIED "byte" is a unit, not a method name — see the pattern.
     The rule carries a SELF-TEST (see the table below it) that must keep
     classifying correctly; a misclassification exits 2, not 1.

  2. PER-FILE CLEAN-ROOM ATTESTATION — every scanned .asm/.inc must declare its
     clean-room basis in its header block (a "no disassembly" / "clean-room"
     statement, or a pointer to its PROVENANCE.md basis).

  4. PRIVATE-REFERENCE SCAN — a public finding must resolve to a PUBLIC artifact.
     A citation that dead-ends in the private workbench (`msx-preservation`,
     "private workbench") breaks the chain for any public auditor. Scanned across
     every provenance-bearing file: the asm, the component PROVENANCE.md, and the
     probe sources (.py AND the harness's .asm fixtures) — NOT the docs/ narrative
     (a pointer to a private investigation note is acceptable there) or the
     boundary-policy files (PUBLISHING.md etc.).

ADVISORY check (reported, does NOT affect exit code):

  3. SECTION-CITATION PRESENCE — disk.asm uses inline `; --- name (§cite) ---`
     section headers; basic/tape instead cite per-feature PROVENANCE.md sections,
     so this convention is disk-only. Headers here without an inline citation are
     surfaced as review candidates for the human auditor (some, e.g. the ROM
     skeleton / padding, legitimately have no provenance), not as failures.

Exit status: 0 = clean, 1 = gating findings, 2 = the INSTRUMENT is not working
(usage/IO error, the rule self-test misclassifying, or a scan list that has
collapsed below its floor). The two are deliberately distinct: 1 says the tree
regressed, 2 says nothing below it was measured at all.

Usage:
  python3 tools/audit_citations.py [target ...]   # default: disk basic tape
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _glob(*specs) -> list[str]:
    out = set()
    for d, pat in specs:
        out.update(str(p.relative_to(ROOT)) for p in (ROOT / d).glob(pat))
    return sorted(out)


# Component -> the source files that carry clean-room-bearing assembly.
#
# ⚠️ THE SCAN LIST IS THE DENOMINATOR, AND IT ONCE SILENTLY STOPPED CONTAINING ITS
# SUBJECT. Until D-CITEJUDGE (2026-08-06) this was three narrow globs written on
# 2026-06-24: "basic" meant basic/*.asm plus ONE hand-listed .inc (added after a
# finding in that one file, never generalised), and the whole sub-ROM tree did not
# exist yet -- it was created a week after this file was last edited. The result
# was a provenance sweep reporting a clean tree over 49 of the 116 shipped
# first-party asm/inc files, with every derived numeric routine in the project
# outside it. A missing directory reads exactly like a cleaner tree, which is why
# MIN_FILES below is a hard error and not a warning.
TARGETS = {
    # disk.asm is split into included parts (*.asm/*.inc); the clean-room citations
    # live in the parts now, so scan all of them.
    "disk": _glob(("disk", "*.asm"), ("disk", "*.inc")),
    # "basic" is the whole shipped BASIC deliverable: the main ROM, the shared
    # bodies assembled into BOTH images, and the sub-ROM (which IS the BASIC
    # sub-ROM, so it belongs to this target rather than one of its own).
    "basic": _glob(("basic", "*.asm"), ("basic", "*.inc"),
                   ("sub", "*.asm"), ("sub", "*.inc")),
    "tape": ["tape/tape.asm"],
}
# Components whose section headers carry inline citations (advisory check 3).
INLINE_CITE_TARGETS = {"disk"}

# Vacuity floor. A glob that stops matching (a renamed directory, a moved tree, a
# typo) produces FEWER findings, i.e. it reads as success. These are hard minima,
# comfortably under the counts at the time of writing (8 / 107 / 1) so ordinary
# file churn does not trip them; a collapsed list exits 2.
MIN_FILES = {"disk": 6, "basic": 100, "tape": 1}

# --- check 4: private-reference scan (the public/provenance line) ---------------
# A public finding must resolve to a PUBLIC artifact. A citation that dead-ends in
# the private workbench (`msx-preservation`) breaks the chain for any public
# auditor. We scan the provenance-BEARING files only — the asm, the component
# PROVENANCE.md, and the probe sources — never the docs/ narrative (where a
# pointer to a private *investigation note* is acceptable) or the boundary-policy
# files (PUBLISHING.md / probes/README.md, whose job is to describe the split).
PRIVATE_REF = re.compile(r"private[- ]?workbench|msx-preservation|\(private\)", re.I)


def provenance_files(target: str) -> list[str]:
    """asm + component PROVENANCE.md + probe sources — every place a provenance
    claim is asserted, so every place a private-only citation is a break.

    Probe sources include the harness's own .asm fixtures. They are NOT shipped
    source, so they are outside checks 1-2 (the per-file attestation convention is
    for the deliverable); but a citation asserted in one is a chain break exactly
    like a citation asserted in a .py, so they are inside check 4."""
    files = list(TARGETS[target])
    prov = ROOT / target / "PROVENANCE.md"
    if prov.exists():
        files.append(str(prov.relative_to(ROOT)))
    files += sorted(str(p.relative_to(ROOT))
                    for p in (ROOT / "probes" / target).glob("*.py"))
    files += sorted(str(p.relative_to(ROOT))
                    for p in (ROOT / "probes" / target).rglob("*.asm"))
    return files

# --- check 1: forbidden-source vocabulary --------------------------------------
# Verbs/nouns of a forbidden *derivation method*. "byte-identical" is excluded on
# purpose — it names the legitimate oracle-match outcome, not a copy.
#
# ⚠️ THE LOOKBEHIND ON "byte" IS LOAD-BEARING, AND IT IS WHY THIS RULE IS NOT A
# NUISANCE. Over its first 761 commits this check produced four findings and all
# four were the same false positive: "a 65536-byte copy that sprayed the RAM map",
# "record/byte copy loop", "an independent 34-byte copy of the same body",
# "target := source (18-byte copy)". In every one of them "byte" is bound to what
# precedes it -- a size, or a granularity -- so it is a UNIT and "copy" is the
# ordinary English noun. The forbidden compound is "byte-copy" with nothing in
# front of it. Two of the four were once "fixed" by rewording the prose instead
# (2026-07-04); the class came straight back, because a project that measures
# everything in bytes cannot stop writing "an N-byte copy". Teaching the rule is
# one lookbehind; rewording is a tax per instance, forever.
FORBIDDEN = re.compile(
    r"disassembl|(?<![\w/-])byte[- ]?cop|reverse[- ]?engineer|red[- ]?book", re.I,
)
# A forbidden token is OK iff its sentence is a negation/attestation. We look at
# the matched line plus the two preceding lines (sentences wrap across comment
# lines, e.g. "Nothing is derived from any ... / disassembly.").
NEGATION = re.compile(
    r"\b(no|not|nothing|never|none|without|neither|nor|forbidden|instead|"
    r"rather than|avoid|free of|clean[- ]?room)\b|n't|✗|✘",
    re.I,
)


def forbidden_hit(lines, i):
    """check 1's whole decision for line i: the matched token, or None.

    Extracted so the self-test below exercises the SAME code path the sweep does
    -- a self-test against a re-implementation of the rule proves nothing."""
    m = FORBIDDEN.search(lines[i])
    if not m:
        return None
    window = " ".join(lines[max(0, i - 2): i + 1])
    return None if NEGATION.search(window) else m.group(0)


# The control. A gate whose green state is "found nothing affirmative" cannot tell
# a clean tree from a broken pattern, so the rule is pinned to a table it must
# keep classifying correctly. The False rows are the four real false positives
# above, verbatim, plus the legitimate oracle outcome; the True rows are the forms
# that must never stop being caught. A miss here exits 2 -- the instrument is not
# working, which is a different disposition from "the tree regressed".
RULE_SELFTEST = [
    ("; derived by byte-copy of the reference DPB table",            True),
    ("; this table is a byte copy of the reference ROM",             True),
    ("; values bytecopied out of the Red Book listing",              True),
    ("; produced by disassembly of a proprietary binary",            True),
    ("; reverse-engineered from the CF-3300 kernel",                 True),
    ("; an independent 34-byte copy of the same body",               False),
    ("; record/byte copy loop, unchanged since M21b",                False),
    ("; a 65536-byte copy that sprayed the whole RAM map",           False),
    ("; target := source (18-byte copy)",                            False),
    ("; our GETDPB output is byte-identical to the CF-3300's",       False),
]


def selftest_failures():
    """Rows of RULE_SELFTEST that the rule classifies wrongly."""
    bad = []
    for text, want in RULE_SELFTEST:
        got = forbidden_hit([text], 0) is not None
        if got != want:
            bad.append((text, want, got))
    return bad

# --- check 2: per-file attestation ---------------------------------------------
ATTESTATION = re.compile(
    r"clean[- ]?room|no\s+disass|nothing is derived|no value is taken|"
    r"not derived from|own[- ]?design|provenance",
    re.I,
)

def header_block(lines):
    """The file's OWN header comment block: the contiguous run of comment lines
    that follows the copyright/SPDX preamble.

    ⚠️ THIS WAS A FIXED 45-LINE WINDOW, AND THE WINDOW WAS THE FINDING. Nine of
    the files the D-CITEJUDGE denominator exposed carry a properly worded
    CLEAN-ROOM attestation inside their header -- at lines 46, 51, 56, 58, 59,
    63, 64, 78 -- and were reported as having none, because a header longer than
    45 lines is ordinary in this tree (one is 153). The docstring always said
    "in its header block"; 45 was an approximation of that, and the
    approximation, not the source, was what failed. Measuring the block exactly
    costs one loop and removes nine false findings without editing a file."""
    i = 0
    while i < len(lines) and (lines[i].startswith(";") and
                              ("Copyright" in lines[i] or "SPDX" in lines[i])):
        i += 1
    while i < len(lines) and not lines[i].startswith(";"):
        i += 1
    start = i
    while i < len(lines) and lines[i].startswith(";"):
        i += 1
    return "\n".join(lines[start:i])

# --- check 3: section-citation presence (advisory, disk-only) -------------------
SECTION_HDR = re.compile(r"^;\s*-{2,}\s*(.+?)\s*-{2,}\s*$")
CITATION = re.compile(
    r"§|PROVENANCE|provider-oracle|spec-|-spec\.md|tier2-|datasheet|data book|"
    r"ECMA|FAT spec|WD179|WD2793|MB887|Technical Handbook|MSX2 TH|Z80|TMS9918|"
    r"oracle|own[- ]?design|own[- ]?choice|own code|hardware fact|PSG|VDP|"
    r"Microsoft FAT",
    re.I,
)
# Structural / layout headers that name no derived behaviour — never expected to
# carry a provenance citation.
STRUCTURAL_HDR = re.compile(r"skeleton|pad to|ROM header|cartridge|entry.?point",
                            re.I)
SECTION_CITE_LOOKAHEAD = 6  # comment lines under a header that may hold the cite


def is_comment(line: str) -> bool:
    return line.lstrip().startswith(";")


def audit_file(rel: str, check_sections: bool):
    """Return (gating, advisory) finding lists for one file.

    Each finding is (severity, lineno, message).
    """
    path = ROOT / rel
    gating, advisory = [], []
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError as e:
        return [("ERROR", 0, f"cannot read: {e}")], []

    # check 1: forbidden-source scan (gating)
    for i, line in enumerate(lines):
        if forbidden_hit(lines, i):
            gating.append(
                ("FORBIDDEN", i + 1,
                 f"forbidden-source token used affirmatively: {line.strip()!r}")
            )

    # check 2: per-file attestation in the header block (gating)
    if not ATTESTATION.search(header_block(lines)):
        gating.append(
            ("NO-ATTEST", 1,
             "no clean-room / no-disassembly / PROVENANCE attestation in header")
        )

    # check 3: section-citation presence (advisory, disk-style headers only)
    if check_sections:
        for i, line in enumerate(lines):
            m = SECTION_HDR.match(line)
            if not m:
                continue
            name = m.group(1)
            if not name or set(name) <= {"-", "=", " "}:
                continue
            if STRUCTURAL_HDR.search(name) or CITATION.search(line):
                continue
            cited = False
            for j in range(i + 1, min(len(lines), i + 1 + SECTION_CITE_LOOKAHEAD)):
                if not is_comment(lines[j]) and lines[j].strip():
                    break  # code before a cite
                if CITATION.search(lines[j]):
                    cited = True
                    break
            if not cited:
                advisory.append(
                    ("REVIEW", i + 1, f"section header without inline citation: {name!r}")
                )

    return gating, advisory


def audit_private(rel: str):
    """check 4: a private-only citation in a provenance-bearing file (gating)."""
    findings = []
    try:
        lines = (ROOT / rel).read_text(errors="replace").splitlines()
    except OSError as e:
        return [("ERROR", 0, f"cannot read: {e}")]
    for i, line in enumerate(lines):
        if PRIVATE_REF.search(line):
            findings.append(
                ("PRIVATE-REF", i + 1,
                 f"provenance cites a private artifact (must resolve public): "
                 f"{line.strip()!r}")
            )
    return findings


def main(argv):
    targets = argv[1:] or ["disk", "basic", "tape"]
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        print(f"unknown target(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"known: {', '.join(TARGETS)}", file=sys.stderr)
        return 2

    bad = selftest_failures()
    if bad:
        print("INSTRUMENT NOT WORKING — check 1's rule self-test misclassified:",
              file=sys.stderr)
        for text, want, got in bad:
            print(f"  expected {'FLAG' if want else 'pass'}, got "
                  f"{'FLAG' if got else 'pass'}: {text!r}", file=sys.stderr)
        print("Nothing below this was measured. Fix FORBIDDEN/NEGATION.",
              file=sys.stderr)
        return 2

    short = [(t, len(TARGETS[t]), MIN_FILES[t]) for t in targets
             if len(TARGETS[t]) < MIN_FILES.get(t, 0)]
    if short:
        print("INSTRUMENT NOT WORKING — a scan list collapsed below its floor:",
              file=sys.stderr)
        for t, n, floor in short:
            print(f"  {t}: {n} file(s), floor {floor} — a glob stopped matching, "
                  "so a smaller sweep would have read as a cleaner tree.",
                  file=sys.stderr)
        return 2

    print("clean-room citation audit (mechanical half — not a full paper trail)")
    print(f"rule self-test {len(RULE_SELFTEST)}/{len(RULE_SELFTEST)}\n")
    gating_total = advisory_total = 0
    for target in targets:
        print(f"== {target} == ({len(TARGETS[target])} files scanned, "
              f"{len(provenance_files(target))} provenance-bearing)")
        t_gate = t_adv = 0
        for rel in TARGETS[target]:
            gating, advisory = audit_file(rel, target in INLINE_CITE_TARGETS)
            for sev, ln, msg in gating:
                print(f"  [{sev}] {rel}:{ln}: {msg}")
                t_gate += 1
            for sev, ln, msg in advisory:
                print(f"  [{sev}] {rel}:{ln}: {msg}")
                t_adv += 1
        # check 4: private-reference scan across all provenance-bearing files
        for rel in provenance_files(target):
            for sev, ln, msg in audit_private(rel):
                print(f"  [{sev}] {rel}:{ln}: {msg}")
                t_gate += 1
        if t_gate == 0:
            print("  clean — attestations present, no unattested forbidden source"
                  + ("" if t_adv == 0 else f"  ({t_adv} advisory review candidate(s))"))
        gating_total += t_gate
        advisory_total += t_adv
        print()

    if advisory_total:
        print(f"ADVISORY: {advisory_total} section header(s) without an inline "
              "citation — review candidates for the human paper trail, not gate "
              "failures.\n")

    if gating_total:
        print(f"GATING FINDINGS: {gating_total}. Mechanical floor breached — fix "
              "before the next paper trail. A clean result here still needs the "
              "human black-box probe judgement (docs/clean-room-audit.md).")
        return 1
    print("CLEAN (gating checks). The non-mechanical hop — 'is each cited probe "
          "genuinely black-box?' — still requires a human paper-trail pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
