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

  5. DECODED-LISTING SCAN — a run of consecutive `<address>  <mnemonic>` lines is
     a rendered instruction listing. Check 1 cannot see this class at all: a
     decoded listing contains none of its vocabulary, and the prose around the
     one the project actually shipped said "byte-identical", which check 1
     deliberately exempts. Repo-wide (prose AND asm comments), because the
     2026-07-07 full-verify found the class in both. Allowlisted entries are
     content-anchored and must KEEP matching; see the allowlist file.

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

import hashlib
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

# --- check 5: decoded-instruction listings --------------------------------------
# ⚠️ THIS CHECK EXISTS BECAUSE CHECK 1 IS STRUCTURALLY BLIND TO ITS CLASS, NOT
# BECAUSE ITS DENOMINATOR WAS TOO SMALL. Measured over the project's whole
# provenance record (docs/spec-audit-citations-docs.md §2.1): every recorded
# decoded-code breach contains ZERO forbidden-vocabulary tokens -- an address
# column plus mnemonics names no method -- so check 1's recall on the class is 0
# of 4. The prose around the one shipped in 2026-07 even said "byte-identical",
# which check 1 exempts on purpose. Widening check 1 to docs/ was measured and
# DECLINED: 0 recall, 26 affirmative false positives over 278 files, 16 of them
# inside the three documents that define and record the clean-room policy itself.
#
# What IS decidable is the SHAPE. A run of consecutive `<addr>  <mnemonic>` lines
# is a rendered listing whatever it says, and over all 978 commits of this repo's
# history the shape appears in exactly three files -- twice as a genuine breach of
# the forbidden class, once as an admissible peer source. The inline variant
# ("$0246: LD A,($F340) / AND A / CALL Z,$0317") is NOT decidable and is a stated
# coverage limit: every threshold that catches any of it also fires on the
# hand-reviewed prose that replaced it, and on 25-464 honest lines of our own.
#
# The threshold of 2 is not arbitrary. It is the 2026-07-07 remediation's own
# rubric: single call/branch TARGETS stay allowed, multi-instruction bodies do
# not. Two is a multi-instruction body.
LISTING_MNEM = (
    r"ld|ldir|lddr|ldi|ldd|jp|jr|call|ret|reti|retn|push|pop|inc|dec|add|adc|"
    r"sub|sbc|and|or|xor|cp|cpir|cpdr|cpi|cpd|rst|ex|exx|out|in|bit|set|res|"
    r"rlc|rrc|rla|rra|rlca|rrca|rl|rr|sla|sra|srl|neg|cpl|scf|ccf|daa|djnz|im|"
    r"rrd|rld|ini|ind|outi|otir|nop|halt|di|ei"
)
# An address column, then a mnemonic. The prefix class absorbs indentation, the
# markdown a listing is usually pasted inside, AND the comment leaders `; # //`.
#
# ⚠️ THE COMMENT LEADERS ARE LOAD-BEARING AND WERE MISSING FROM THE FIRST CUT.
# Without them this rule could not see a listing in an .asm comment -- i.e. it was
# blind to exactly the half of the corpus that justified building it (6 of the ~50
# sites the 2026-07-07 full-verify remediated were comments in disk/*.asm, files
# check 1 had scanned all along). Knife K1b caught it by planting there and
# getting a green. Cost of the fix, measured over all 692 files: one additional
# finding, and it is genuine.
LISTING_LINE = re.compile(
    rf"^[\s>|*`;#/]*\$?[0-9A-Fa-f]{{4}}[:.]?\s+({LISTING_MNEM})\b", re.I)
LISTING_MIN_RUN = 2

# The files swept. Verified equal to `git ls-files` filtered to these suffixes
# (690 files, zero difference either way), so the sweep cannot drift away from
# what is actually tracked without the floor below noticing.
SWEEP_EXTS = (".md", ".asm", ".inc", ".py", ".tcl", ".txt", ".bas", ".yml")
SWEEP_SKIP = {"build", "scratchpad", ".git", ".claude", "__pycache__", ".vscode"}
MIN_SWEEP_FILES = 600
LISTING_ALLOW = ROOT / "tools" / "citations-listing-allow.txt"


def sweep_files() -> list[str]:
    out = []
    for p in ROOT.rglob("*"):
        if p.suffix not in SWEEP_EXTS or not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if SWEEP_SKIP & set(rel.parts):
            continue
        out.append(str(rel))
    return sorted(out)


def listing_runs(lines):
    """Maximal runs of >= LISTING_MIN_RUN consecutive listing-shaped lines.

    Returns (first_lineno, run_lines). Extracted so the self-test exercises the
    SAME code path the sweep does."""
    runs, cur, first = [], [], 0
    for i, line in enumerate(lines):
        if LISTING_LINE.match(line):
            if not cur:
                first = i + 1
            cur.append(line)
        else:
            if len(cur) >= LISTING_MIN_RUN:
                runs.append((first, cur))
            cur = []
    if len(cur) >= LISTING_MIN_RUN:
        runs.append((first, cur))
    return runs


def run_digest(run_lines) -> str:
    return hashlib.sha256("\n".join(run_lines).encode()).hexdigest()[:12]


# The control. Check 1 pins its four historical false positives VERBATIM; this
# check cannot -- its true-positive vectors ARE the forbidden artifact, and
# quoting a real one here would reproduce a proprietary listing in a second file
# and make this tool its own first finding. So the positive vectors are INVENTED:
# synthetic address/mnemonic runs with no provenance at all. The negative vectors
# are real forms from our own honest prose that must never fire. Each vector is
# one SOURCE line, so this table is not itself a listing run.
LISTING_SELFTEST = [
    (["1234  ld a,($5678)", "1237  or a", "1238  jr z,$1240"], True),
    (["$A100  push af", "$A101  inc hl"], True),                    # the >=2 boundary
    (["> C000: call $C123", "> C003: ret nz"], True),               # markdown-quoted
    (["  9000.  xor a", "  9001.  ld (hl),a", "  9002.  inc hl"], True),
    (["`B200  di`", "`B201  halt`"], True),                         # backticked
    (["; 7000  ld a,($7A10)", "; 7003  or a"], True),               # an ASM COMMENT (K1b)
    (["4010  jp $4020"], False),                                    # ONE branch target
    (["the handler must set a flag and or it in", "before it can ret"], False),
    (["ary_alloc:  ld a,(hl)", "            inc hl"], False),       # our own asm source
    (["the window is $11A3..$11AD, 10 bytes", "and both ends are published"], False),
    (["1234  ld a,($5678)", "some prose in between", "1238  jr z,$1240"], False),
]


def listing_selftest_failures():
    bad = []
    for lines, want in LISTING_SELFTEST:
        got = bool(listing_runs(lines))
        if got != want:
            bad.append((lines, want, got))
    return bad


def parse_listing_allow():
    """(digest -> (relpath, reason)), or an error string.

    🔴 THIS IS A CONTROL, NOT A SUPPRESSION LIST -- the same idea as
    tools/deadcode-allow.txt. Every entry must STILL be produced by the sweep. An
    entry that stops matching is either stale (delete the line) or proof the sweep
    has gone blind, and both exit 2. Entries are anchored on the DIGEST of the
    run's text, never on a line number: line numbers rot, and a path-level entry
    would blind the whole file to a second, real listing."""
    out = {}
    if not LISTING_ALLOW.exists():
        return out
    for n, raw in enumerate(LISTING_ALLOW.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            return f"{LISTING_ALLOW.name}:{n}: need '<path> <digest> <reason>'"
        rel, digest, reason = parts
        out[digest] = (rel, reason)
    return out


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

    bad = listing_selftest_failures()
    if bad:
        print("INSTRUMENT NOT WORKING — check 5's listing self-test misclassified:",
              file=sys.stderr)
        for lines, want, got in bad:
            print(f"  expected {'FLAG' if want else 'pass'}, got "
                  f"{'FLAG' if got else 'pass'}: {lines!r}", file=sys.stderr)
        print("Nothing below this was measured. Fix LISTING_LINE.", file=sys.stderr)
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
    print(f"rule self-test {len(RULE_SELFTEST)}/{len(RULE_SELFTEST)}, "
          f"listing self-test {len(LISTING_SELFTEST)}/{len(LISTING_SELFTEST)}\n")
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

    # check 5: decoded-instruction listings — repo-wide, never per-target, because
    # the class was found in shipped asm comments AND in prose by the same sweep.
    allow = parse_listing_allow()
    if isinstance(allow, str):
        print(f"INSTRUMENT NOT WORKING — {allow}", file=sys.stderr)
        return 2
    swept = sweep_files()
    if len(swept) < MIN_SWEEP_FILES:
        print("INSTRUMENT NOT WORKING — the listing sweep collapsed below its "
              f"floor: {len(swept)} file(s), floor {MIN_SWEEP_FILES}. A glob "
              "stopped matching, so a smaller sweep would have read as a cleaner "
              "tree.", file=sys.stderr)
        return 2

    print(f"== listing shape == ({len(swept)} files swept, "
          f"{len(allow)} allowlisted)")
    listing_gate = 0
    seen_digests = set()
    for rel in swept:
        try:
            lines = (ROOT / rel).read_text(errors="replace").splitlines()
        except OSError as e:
            print(f"  [ERROR] {rel}: cannot read: {e}")
            listing_gate += 1
            continue
        for start, run in listing_runs(lines):
            digest = run_digest(run)
            seen_digests.add(digest)
            if digest in allow:
                print(f"  [allowed] {rel}:{start}: {len(run)}-line listing "
                      f"({digest}) — {allow[digest][1]}")
                continue
            print(f"  [LISTING] {rel}:{start}: {len(run)} consecutive "
                  f"<address> <mnemonic> lines — a rendered instruction listing. "
                  f"If this is our own or an admissible source, allowlist it with "
                  f"a reason in {LISTING_ALLOW.name} (digest {digest}); if it "
                  f"decodes a proprietary binary, reground it on the black-box "
                  f"observation it rests on.")
            listing_gate += 1
    # The allowlist as canary: an entry that stops matching is a stale entry OR a
    # blind sweep, and both are the instrument, not the tree.
    stale = [d for d in allow if d not in seen_digests]
    if stale:
        print("INSTRUMENT NOT WORKING — allowlisted listing(s) no longer detected:",
              file=sys.stderr)
        for d in stale:
            print(f"  {allow[d][0]} ({d}) — either the text was regrounded "
                  f"(delete the line) or the sweep has gone blind.", file=sys.stderr)
        return 2
    if listing_gate == 0:
        print("  clean — no unallowlisted decoded-instruction listings")
    gating_total += listing_gate
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
