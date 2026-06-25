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

  2. PER-FILE CLEAN-ROOM ATTESTATION — every scanned .asm/.inc must declare its
     clean-room basis in its header block (a "no disassembly" / "clean-room"
     statement, or a pointer to its PROVENANCE.md basis).

  4. PRIVATE-REFERENCE SCAN — a public finding must resolve to a PUBLIC artifact.
     A citation that dead-ends in the private workbench (`msx-preservation`,
     "private workbench") breaks the chain for any public auditor. Scanned across
     every provenance-bearing file: the asm, the component PROVENANCE.md, and the
     probe sources — NOT the docs/ narrative (a pointer to a private investigation
     note is acceptable there) or the boundary-policy files (PUBLISHING.md etc.).

ADVISORY check (reported, does NOT affect exit code):

  3. SECTION-CITATION PRESENCE — disk.asm uses inline `; --- name (§cite) ---`
     section headers; basic/tape instead cite per-feature PROVENANCE.md sections,
     so this convention is disk-only. Headers here without an inline citation are
     surfaced as review candidates for the human auditor (some, e.g. the ROM
     skeleton / padding, legitimately have no provenance), not as failures.

Exit status: 0 = clean, 1 = gating findings, 2 = usage/IO error.

Usage:
  python3 tools/audit_citations.py [target ...]   # default: disk basic tape
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Component -> the source files that carry clean-room-bearing assembly.
TARGETS = {
    # disk.asm is split into included parts (*.asm/*.inc); the clean-room citations
    # live in the parts now, so scan all of them.
    "disk": sorted(
        str(p.relative_to(ROOT))
        for p in list((ROOT / "disk").glob("*.asm")) + list((ROOT / "disk").glob("*.inc"))
    ),
    "basic": sorted(
        str(p.relative_to(ROOT)) for p in (ROOT / "basic").glob("*.asm")
    ) + ["basic/sysvars.inc"],
    "tape": ["tape/tape.asm"],
}
# Components whose section headers carry inline citations (advisory check 3).
INLINE_CITE_TARGETS = {"disk"}

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
    claim is asserted, so every place a private-only citation is a break."""
    files = list(TARGETS[target])
    prov = ROOT / target / "PROVENANCE.md"
    if prov.exists():
        files.append(str(prov.relative_to(ROOT)))
    files += sorted(str(p.relative_to(ROOT))
                    for p in (ROOT / "probes" / target).glob("*.py"))
    return files

# --- check 1: forbidden-source vocabulary --------------------------------------
# Verbs/nouns of a forbidden *derivation method*. "byte-identical" is excluded on
# purpose — it names the legitimate oracle-match outcome, not a copy.
FORBIDDEN = re.compile(
    r"disassembl|byte[- ]?cop|reverse[- ]?engineer|red[- ]?book", re.I,
)
# A forbidden token is OK iff its sentence is a negation/attestation. We look at
# the matched line plus the two preceding lines (sentences wrap across comment
# lines, e.g. "Nothing is derived from any ... / disassembly.").
NEGATION = re.compile(
    r"\b(no|not|nothing|never|none|without|neither|nor|forbidden|instead|"
    r"rather than|avoid|free of|clean[- ]?room)\b|n't|✗|✘",
    re.I,
)

# --- check 2: per-file attestation ---------------------------------------------
ATTESTATION = re.compile(
    r"clean[- ]?room|no\s+disass|nothing is derived|no value is taken|"
    r"not derived from|own[- ]?design|provenance",
    re.I,
)
HEADER_BLOCK_LINES = 45  # how far down a file's top comment block may reach

# --- check 3: section-citation presence (advisory, disk-only) -------------------
SECTION_HDR = re.compile(r"^;\s*-{2,}\s*(.+?)\s*-{2,}\s*$")
CITATION = re.compile(
    r"§|PROVENANCE|provider-oracle|spec-|datasheet|data book|ECMA|FAT spec|"
    r"WD179|WD2793|MB887|Technical Handbook|MSX2 TH|Z80|TMS9918|"
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
        if FORBIDDEN.search(line):
            window = " ".join(lines[max(0, i - 2): i + 1])
            if not NEGATION.search(window):
                gating.append(
                    ("FORBIDDEN", i + 1,
                     f"forbidden-source token used affirmatively: {line.strip()!r}")
                )

    # check 2: per-file attestation in the header block (gating)
    head = "\n".join(lines[:HEADER_BLOCK_LINES])
    if not ATTESTATION.search(head):
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

    print("clean-room citation audit (mechanical half — not a full paper trail)\n")
    gating_total = advisory_total = 0
    for target in targets:
        print(f"== {target} ==")
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
