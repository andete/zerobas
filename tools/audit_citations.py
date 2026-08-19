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

  6. HEX-DUMP-ROW SCAN — a run of consecutive 8-hex-character groups (not all
     identical) is a hex DUMP of somebody's binary. Deliberately narrow, and
     deliberately NOT named "raw opcode bytes": docs/spec-audit-citations-bytes.md
     measures that the general raw-byte class is UNDECIDABLE from text. The
     offender and the hand-reviewed replacement of the 2026-07-07 sweep carry the
     same bytes on the same line (§2.2), and the ✗ rule itself forbids proprietary
     bytes "read as anything other than an oracle" — i.e. it turns on the
     PROVENANCE of the reading, which no text scanner can see (§2.4). Every
     variant that catches the class fires on 393-1326 honest lines of our own.
     What IS decidable is the dump ROW: 0 hits over the whole tree and over all
     979 commits, except the one commit range where a 16-byte dump of a
     proprietary loader actually lived. Recall against the class is 1 of 20 and
     the check says so; the rest of the class is the human full-verify's job.

ADVISORY check (reported, does NOT affect exit code):

  3. SECTION-CITATION PRESENCE — disk.asm uses inline `; --- name (§cite) ---`
     section headers; basic/tape instead cite per-feature PROVENANCE.md sections,
     so this convention is disk-only (measured: the same rule over basic + sub
     would report 348 headers against disk's 3). Headers here without an inline
     citation are surfaced as review candidates for the human auditor (some, e.g.
     the ROM skeleton / padding, legitimately have no provenance), not failures.
     The FINDING is advisory; the SET is pinned by citations-advisory-allow.txt,
     and a set that no longer matches what was triaged exits 2. Until 2026-08-06
     the rule scanned a fixed 6 comment lines below a header and 4 of the 7 it
     reported were compliant sections whose citation sat at offset 7-11; those
     four had stood for 617 commits and through a human triage. See
     docs/spec-audit-citations-review.md.

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


# --- check 6: hex-dump rows ------------------------------------------------------
# ⚠️ THIS CHECK IS NARROWER THAN THE CLASS IT COMES FROM, ON PURPOSE, AND ITS NAME
# SAYS SO. The residual it closes asked for "raw opcode-BYTE renderings".
# docs/spec-audit-citations-bytes.md measures why that cannot be a rule:
#
#   * the class IS uncovered -- 20 offender lines from the two remediation
#     commits carry a hex-byte run and checks 1 and 5 flag 0 of them, one of them
#     in disk/kernel.asm which check 1 has scanned since day one (§2.1);
#   * and it is still undecidable, by proof rather than by threshold. On
#     tier2-a3-spec.md:20 the remediation KEPT the row's leading three bytes
#     byte-for-byte and removed only the mnemonics that decoded the target
#     routine's body. Offender and hand-reviewed innocent are lexically identical
#     in the hex run, so no line rule can separate them (§2.2);
#   * 15 live lines attribute a hex run to the reference machine and all 15 were
#     read and KEPT by the 2026-07-07 sweep; 2 of them are in this tool's own
#     governance documents (§2.3);
#   * allowed-sources.md forbids proprietary bytes "read as anything other than an
#     oracle" -- provenance, not text. clean-room-audit.md:508 adjudicates a
#     5-byte hex run as legal because it was OBSERVED output (§2.4);
#   * and the lexical class cannot even tell hex from decimal: "10, 20, 30, 40"
#     is a run of hex byte pairs (§2.5).
#
# What survives is the DUMP row. "Not all groups identical" is not fitting: it
# drops a uniform fill ("00000000 00000000 ...", our own empty region annotated as
# such), which carries no information about anyone's code.
#
# ⚠️ UNLIKE LISTING_LINE THIS IS NOT ANCHORED AT LINE START -- a dump lives inside
# a markdown table cell. That is why the rule cannot go genre-blind the way check
# 5's first cut did (no prefix class to get wrong), and ALSO why this check's own
# self-test vector is a hit on this file. See DUMP_ALLOW below: that is turned
# into the canary rather than worked around.
DUMP_GROUPS = re.compile(
    r"(?<![0-9A-Za-z])[0-9A-Fa-f]{8}(?:\s+[0-9A-Fa-f]{8})+(?![0-9A-Za-z])")


def dump_hits(lines):
    """(lineno, matched_text) for each hex-dump row. Extracted so the self-test
    exercises the SAME code path the sweep does."""
    out = []
    for i, line in enumerate(lines):
        for m in DUMP_GROUPS.finditer(line):
            if len({g.upper() for g in m.group(0).split()}) > 1:
                out.append((i + 1, m.group(0)))
                break
    return out


# The single synthetic vector. INVENTED bytes -- no provenance, no derivation, so
# writing it down forbids nothing ([[a-selftest-vector-can-be-the-forbidden-artifact]]:
# a real positive here would BE the artifact, and this check would find its own
# source). It is the only line in this repo that carries a dump run, which is
# exactly what makes it a usable canary.
_DUMP_VEC = "a1b2c3d4 e5f60718 293a4b5c"

# Positives cover every genre the check claims, built by PREFIXING the one vector
# so the genre coverage is auditable and only one source line is a hit
# ([[a-rule-for-two-corpora-must-be-knifed-in-both]] -- check 5 shipped with all
# five positives drawn from one genre and was blind to the other).
# Negatives are REAL forms from our own prose: digests, uniform fills, decimal
# case-index lists, a lone group.
DUMP_SELFTEST = [
    (_DUMP_VEC, True),                                   # bare prose
    (f"; {_DUMP_VEC}", True),                            # asm comment
    (f"# {_DUMP_VEC}", True),                            # python comment
    (f"| `$50A9` | `{_DUMP_VEC}` | note |", True),       # markdown table cell
    (f"    {_DUMP_VEC}  ; trailing comment", True),      # indented + suffixed
    ("2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27  build/disk.rom",
     False),                                             # a sha256 + a path
    ("probes/lib/latch_check.py  5565467e6422  C-BIOS, same window", False),
    ("| Tier-1 | `00000000 00000000 00000000 00000000` (empty) | 6 |", False),
    ("the pad reads FFFFFFFF FFFFFFFF to the end of the region", False),
    ("inserting 10, 20, 30, 40 in that order and re-listing", False),
    ("#    12 15 18 19 50 51 53 54 56 57 60 62 63 64", False),
    ("SIG2 = \"7ef5237dfe18200321f0fb22faf3f1d1e1c9\"", False),  # one long group
]


def dump_selftest_failures():
    bad = []
    for text, want in DUMP_SELFTEST:
        got = bool(dump_hits([text]))
        if got != want:
            bad.append((text, want, got))
    return bad


DUMP_ALLOW = ROOT / "tools" / "citations-dump-allow.txt"


def parse_listing_allow(path=None):
    """(digest -> (relpath, reason)), or an error string.

    🔴 THIS IS A CONTROL, NOT A SUPPRESSION LIST -- the same idea as
    tools/deadcode-allow.txt. Every entry must STILL be produced by the sweep. An
    entry that stops matching is either stale (delete the line) or proof the sweep
    has gone blind, and both exit 2. Entries are anchored on the DIGEST of the
    run's text, never on a line number: line numbers rot, and a path-level entry
    would blind the whole file to a second, real listing."""
    path = path or LISTING_ALLOW
    out = {}
    if not path.exists():
        return out
    for n, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            return f"{path.name}:{n}: need '<path> <digest> <reason>'"
        rel, digest, reason = parts
        out[digest] = (rel, reason)
    return out


# --- check 3: section-citation presence (advisory, disk-only) -------------------
SECTION_HDR = re.compile(r"^;\s*-{2,}\s*(.+?)\s*-{2,}\s*$")
# ⚠️ THIS RULE EXEMPTS ON A TOKEN AND HAS NO NEGATION WINDOW, DELIBERATELY.
# Check 1 has one; borrowing it here was filed as a residual and MEASURED, over
# all 981 commits, in docs/spec-audit-citations-negation.md:
#
#   * a 3-line NEGATION window adds 38 findings the shipped rule does not make,
#     and 0 of the 38 lack a document citation -- precision 0, over the whole
#     history of the tree;
#   * it fails structurally, not by tuning. CLEAN-ROOM is a NEGATION token AND
#     the prefix of this project's citation convention ("CLEAN-ROOM: published
#     CONST contract (map.grauw.nl) + CHSNS; no oracle bytes"), so the window
#     discards the citation on every header that follows the house style; and
#     \bno\b matches inside NO-OP, which throws away a §5.3 for a hyphen;
#   * check 1's window IS sound where it lives -- 109 hits, 109 suppressed, all
#     26 lookback-only suppressions read individually and all genuine. It does
#     not transfer because check 1's vocabulary is rare and confined to
#     attestations, while this one's is common and sits NEXT TO the negation.
#
# What the residual was really about is VOCABULARY, and one token carried all of
# it. Sweeping this regex one alternative at a time (the D-REVJUDGE distance
# sweep, on the other axis) shows 22 of the 25 alternatives exempt nothing at
# all; only §, "oracle" and "VDP" are load-bearing. VDP -- a subsystem
# abbreviation, ordinary English in a sentence about what an implementation must
# do -- was single-handedly exempting one uncited header for 708 commits, so it
# is gone. Removing it adds 9 findings over the same 981 commits and 9 of 9 are
# genuine: they are that one header, tracked across its moves and its rename.
#
# Z80/TMS9918/WD2793 STAY: they are part numbers whose datasheets are
# chain-terminating sources per docs/clean-room-audit.md, not prose. PSG stays
# too -- it has never exempted anything in any commit, so removing it would be a
# rule change with no observable effect. Adding map.grauw.nl was measured as
# EXACTLY that: 0 changed verdicts in 981 commits (negation spec §2.7).
CITATION = re.compile(
    r"§|PROVENANCE|provider-oracle|spec-|-spec\.md|tier2-|datasheet|data book|"
    r"ECMA|FAT spec|WD179|WD2793|MB887|Technical Handbook|MSX2 TH|Z80|TMS9918|"
    r"oracle|own[- ]?design|own[- ]?choice|own code|hardware fact|PSG|"
    r"Microsoft FAT",
    re.I,
)
# Structural / layout headers that name no derived behaviour — never expected to
# carry a provenance citation.
STRUCTURAL_HDR = re.compile(r"skeleton|pad to|ROM header|cartridge|entry.?point",
                            re.I)
ADVISORY_ALLOW = ROOT / "tools" / "citations-advisory-allow.txt"


def is_comment(line: str) -> bool:
    return line.lstrip().startswith(";")


def section_findings(lines):
    """(lineno, name, verdict) for every `; --- name ---` header in one file.

    verdict is one of:
      "rule"       a bare divider — names nothing, so nothing to cite
      "structural" STRUCTURAL_HDR — layout, never expected to carry provenance
      "on-header"  the citation is on the header line itself
      "cited"      the citation is in the header's own comment block
      "REVIEW"     no citation anywhere in that block — a review candidate

    🔴 THERE IS DELIBERATELY NO LINE CAP. This scanned a fixed 6 comment lines
    until 2026-08-06 (D-REVJUDGE), which is the same magic-number defect as
    check 2's old HEADER_BLOCK_LINES = 45: FOUR of the seven headers it reported
    carry a proper document citation at offset 7, 10, 10 and 11 of their own
    uninterrupted comment block. Those four had been reported for 617 commits and
    survived a human triage that wrote down, in docs/clean-room-audit.md, that
    their "bodies carry full citations". The block is bounded by the code that
    follows it, not by a constant — measure the block, never guess its length.
    See docs/spec-audit-citations-review.md §2.2.

    The scan stops at the NEXT section header too, so a header can never borrow
    the citation belonging to the section below it. Blank lines do not stop it:
    a `;` header block is routinely broken by bare `;` and by empty lines.

    Extracted so the self-test, the sweep and any historical walker exercise the
    SAME code path — the reason check 5 has listing_runs()."""
    out = []
    for i, line in enumerate(lines):
        m = SECTION_HDR.match(line)
        if not m:
            continue
        name = m.group(1)
        if not name or set(name) <= {"-", "=", " "}:
            out.append((i + 1, name, "rule"))
            continue
        if STRUCTURAL_HDR.search(name):
            out.append((i + 1, name, "structural"))
            continue
        if CITATION.search(line):
            out.append((i + 1, name, "on-header"))
            continue
        verdict = "REVIEW"
        for j in range(i + 1, len(lines)):
            if SECTION_HDR.match(lines[j]):
                break                       # next section — no borrowing
            if not is_comment(lines[j]) and lines[j].strip():
                break                       # code before a cite
            if CITATION.search(lines[j]):
                verdict = "cited"
                break
        out.append((i + 1, name, verdict))
    return out


def advisory_digest(rel: str, name: str) -> str:
    """Anchor for the acknowledged list: the header's NAME, never its line number.

    Line numbers rot on every edit above them, and a path-level entry would blind
    a whole file to a second, real uncited header."""
    return run_digest([f"{rel}|{name}"])


# The control check 3 never had. Checks 1, 5 and 6 all self-test; this one did
# not, and its green state is "here are N things, all fine" — a reading that is
# identical whether the rule works or not, which is exactly how the line-cap
# defect above survived 617 commits (docs/spec-audit-citations-review.md §2.4).
#
# Unlike check 5's, these positive vectors are safe to write down: check 3
# refuses a PROPERTY (no citation present), not a KIND OF TEXT, so a positive
# vector is just a header with nothing to cite. They are synthetic anyway —
# pinning real tree text would make them rot on every comment edit, and one
# vector per SHAPE is cheaper than one per instance.
def _hdr(name):
    return f"; --- {name} " + "-" * max(2, 60 - len(name))


_FILL = ["; this line carries no citation of any kind",
         "; nor does this one, it is only continuation prose",
         "; still nothing citable here",
         "; more of the same",
         "; and more",
         "; and yet more",
         "; padding continues",
         "; padding continues further",
         "; nearly there now",
         "; last of the filler"]

SECTION_SELFTEST = [
    # (label, lines, expected verdicts in order)
    ("cite at offset 1",
     [_hdr("fdc reset"), "; grounded on the WD2793 datasheet, table 4", "  xor a"],
     ("cited",)),
    ("cite at offset 6 — the old cap's boundary",
     [_hdr("media byte")] + _FILL[:5] + ["; see PROVENANCE.md for the derivation"],
     ("cited",)),
    ("cite at offset 7 — the class the 6-line cap could not see",
     [_hdr("media byte")] + _FILL[:6] + ["; see PROVENANCE.md for the derivation"],
     ("cited",)),
    ("cite at offset 11 — the deepest real case in the tree",
     [_hdr("media byte")] + _FILL[:10] + ["; see PROVENANCE.md for the derivation"],
     ("cited",)),
    ("blank and bare-; lines do not break the block",
     [_hdr("sector map"), ";", "", "; prose", ";",
      "; derived from the FAT spec, section 3"],
     ("cited",)),
    ("cite on the header line itself",
     [_hdr("boot record (Microsoft FAT spec §3.1)"), "; prose", "  ld a,1"],
     ("on-header",)),
    ("structural header needs no citation",
     [_hdr("ROM skeleton"), "  org $4000"],
     ("structural",)),
    ("no cite, then code",
     [_hdr("write path"), "; prose", "; more prose", "; still more", "  ld a,b"],
     ("REVIEW",)),
    ("code on the very next line",
     [_hdr("stub table"), "  ret"],
     ("REVIEW",)),
    ("must not borrow the NEXT section's citation",
     [_hdr("write path"), "; prose",
      _hdr("read path (PROVENANCE.md §FDC)"), "; prose", "  ld a,b"],
     ("REVIEW", "on-header")),
    ("a bare divider names nothing",
     ["; " + "-" * 70, "  nop"],
     ("rule",)),
    ("an ordinary comment is not a section header",
     ["; write path — an ordinary comment, not a header", "  ld a,b"],
     ()),
    # D-NEGJUDGE. The pair that pins the vocabulary edge: a subsystem
    # abbreviation used as an ordinary noun is NOT a citation, but a real
    # hardware document still is. Re-adding VDP to CITATION fails the first;
    # over-applying the removal to `datasheet` fails the second.
    ("a bare subsystem abbreviation in prose is not a citation",
     [_hdr("interrupt shim"),
      "; a bare VDP ack is not enough here: the caller needs the timer hooks",
      "; too, which only the main BIOS runs.", "  ei"],
     ("REVIEW",)),
    ("a real hardware document still exempts",
     [_hdr("interrupt shim"),
      "; timing grounded on the TMS9918 datasheet, section 2.1", "  ei"],
     ("cited",)),
]


def section_selftest_failures():
    bad = []
    for label, lines, want in SECTION_SELFTEST:
        got = tuple(v for _, _, v in section_findings(lines))
        if got != want:
            bad.append((label, want, got))
    return bad


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
        for ln, name, verdict in section_findings(lines):
            if verdict == "REVIEW":
                advisory.append(
                    ("REVIEW", ln, f"section header without inline citation: {name!r}",
                     advisory_digest(rel, name))
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


# --- the control on the controls ------------------------------------------------
# 🔴 EVERY SELF-TEST TABLE PRINTED "0/0" AND EXITED 0 WHEN EMPTIED, until
# D-NEGJUDGE measured it. `section self-test 0/0` in the header line reads exactly
# like `12/12` to anyone scanning the output, and none of the four tables had a
# floor. That is the "0/0 tally printed ALL CONVERGED" shape, and it is the same
# defect MIN_FILES closes one level out: a collapsed denominator reads as success.
#
# The acknowledged list does NOT cover it. Emptying a table blinds the CONTROL,
# not the RULE -- the findings are unchanged, so every allowlist entry still
# matches and the run is green. What goes unnoticed is the NEXT rule change.
#
# ⚠️ WHAT THIS DOES NOT CATCH, STATED: trimming 14 vectors to 9 still passes. The
# failure mode closed here is a blinded control reading as green, not vector
# attrition. Attrition's defence is that each vector is here because a knife or a
# measurement put it there -- see docs/spec-audit-citations-negation.md §3.4.
MIN_SELFTEST_ROWS = 8


def selftest_table_failures():
    """Tables too small, or missing a whole sense. Both mean the control is not
    controlling anything, which is an INSTRUMENT verdict (exit 2), not a tree one."""
    bad = []
    tables = [
        ("check 1 rule", RULE_SELFTEST,
         [w for _, w in RULE_SELFTEST], [True, False]),
        ("check 5 listing", LISTING_SELFTEST,
         [w for _, w in LISTING_SELFTEST], [True, False]),
        ("check 6 dump", DUMP_SELFTEST,
         [w for _, w in DUMP_SELFTEST], [True, False]),
        # check 3 classifies into verdicts, not booleans: it must keep at least
        # one vector that must be FLAGGED and one that must be EXEMPTED.
        ("check 3 section", SECTION_SELFTEST,
         [v for _, _, want in SECTION_SELFTEST for v in want],
         ["REVIEW", "cited"]),
    ]
    for label, table, senses, needed in tables:
        if len(table) < MIN_SELFTEST_ROWS:
            bad.append(f"{label}: {len(table)} vector(s), floor "
                       f"{MIN_SELFTEST_ROWS} — a gutted table classifies "
                       f"nothing and still prints N/N.")
        missing = [s for s in needed if s not in senses]
        if missing:
            bad.append(f"{label}: no vector expecting {missing} — a table of one "
                       f"sense passes however the rule is broken in the other.")
    return bad


def main(argv):
    targets = argv[1:] or ["disk", "basic", "tape"]
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        print(f"unknown target(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"known: {', '.join(TARGETS)}", file=sys.stderr)
        return 2

    bad = selftest_table_failures()
    if bad:
        print("INSTRUMENT NOT WORKING — a self-test table has been gutted:",
              file=sys.stderr)
        for msg in bad:
            print(f"  {msg}", file=sys.stderr)
        print("Nothing below this was measured. Restore the vectors.",
              file=sys.stderr)
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

    bad = dump_selftest_failures()
    if bad:
        print("INSTRUMENT NOT WORKING — check 6's hex-dump self-test misclassified:",
              file=sys.stderr)
        for text, want, got in bad:
            print(f"  expected {'FLAG' if want else 'pass'}, got "
                  f"{'FLAG' if got else 'pass'}: {text!r}", file=sys.stderr)
        print("Nothing below this was measured. Fix DUMP_GROUPS.", file=sys.stderr)
        return 2

    bad = section_selftest_failures()
    if bad:
        print("INSTRUMENT NOT WORKING — check 3's section self-test misclassified:",
              file=sys.stderr)
        for label, want, got in bad:
            print(f"  {label}: expected {want}, got {got}", file=sys.stderr)
        print("Nothing below this was measured. Fix section_findings().",
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

    adv_allow = parse_listing_allow(ADVISORY_ALLOW)
    if isinstance(adv_allow, str):
        print(f"INSTRUMENT NOT WORKING — {adv_allow}", file=sys.stderr)
        return 2

    print("clean-room citation audit (mechanical half — not a full paper trail)")
    print(f"rule self-test {len(RULE_SELFTEST)}/{len(RULE_SELFTEST)}, "
          f"listing self-test {len(LISTING_SELFTEST)}/{len(LISTING_SELFTEST)}, "
          f"dump self-test {len(DUMP_SELFTEST)}/{len(DUMP_SELFTEST)}, "
          f"section self-test {len(SECTION_SELFTEST)}/{len(SECTION_SELFTEST)}\n")
    gating_total = advisory_total = 0
    adv_unacked, adv_seen = [], set()
    for target in targets:
        print(f"== {target} == ({len(TARGETS[target])} files scanned, "
              f"{len(provenance_files(target))} provenance-bearing)")
        t_gate = t_adv = 0
        for rel in TARGETS[target]:
            gating, advisory = audit_file(rel, target in INLINE_CITE_TARGETS)
            for sev, ln, msg in gating:
                print(f"  [{sev}] {rel}:{ln}: {msg}")
                t_gate += 1
            for sev, ln, msg, digest in advisory:
                adv_seen.add(digest)
                if digest in adv_allow:
                    print(f"  [acknowledged] {rel}:{ln}: {msg} ({digest}) — "
                          f"{adv_allow[digest][1]}")
                else:
                    print(f"  [{sev}] {rel}:{ln}: {msg} ({digest}) — NOT "
                          f"acknowledged. Triage it, then record the judgement in "
                          f"{ADVISORY_ALLOW.name}.")
                    adv_unacked.append((rel, ln, digest))
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

    # check 6: hex-dump rows — same sweep (so MIN_SWEEP_FILES already guards it).
    dump_allow = parse_listing_allow(DUMP_ALLOW)
    if isinstance(dump_allow, str):
        print(f"INSTRUMENT NOT WORKING — {dump_allow}", file=sys.stderr)
        return 2
    print(f"== hex-dump rows == ({len(swept)} files swept, "
          f"{len(dump_allow)} allowlisted)")
    dump_gate = 0
    seen_dump = set()
    for rel in swept:
        try:
            lines = (ROOT / rel).read_text(errors="replace").splitlines()
        except OSError as e:
            print(f"  [ERROR] {rel}: cannot read: {e}")
            dump_gate += 1
            continue
        for lineno, text in dump_hits(lines):
            digest = run_digest([text])
            seen_dump.add(digest)
            if digest in dump_allow:
                print(f"  [allowed] {rel}:{lineno}: hex-dump row ({digest}) — "
                      f"{dump_allow[digest][1]}")
                continue
            print(f"  [DUMP] {rel}:{lineno}: a run of 8-hex-character groups — a "
                  f"hex dump of a binary. If it dumps a proprietary binary "
                  f"(reference ROM / MSXDOS.SYS / COMMAND.COM) it is ✗ and must be "
                  f"regrounded on the black-box observation it rests on; if it is "
                  f"ours or an admissible source, allowlist it with a reason in "
                  f"{DUMP_ALLOW.name} (digest {digest}).")
            dump_gate += 1
    stale = [d for d in dump_allow if d not in seen_dump]
    if stale:
        print("INSTRUMENT NOT WORKING — allowlisted hex-dump row(s) no longer "
              "detected:", file=sys.stderr)
        for d in stale:
            print(f"  {dump_allow[d][0]} ({d}) — either the text changed (delete "
                  f"the line) or the sweep has gone blind.", file=sys.stderr)
        return 2
    if dump_gate == 0:
        print("  clean — no unallowlisted hex-dump rows  (narrow by design: this "
              "is the dump ROW only, not the raw-byte class — "
              "docs/spec-audit-citations-bytes.md §3.1)")
    gating_total += dump_gate
    print()

    # The acknowledged advisory set. The FINDING stays advisory — the tool still
    # makes no judgement about whether an uncited header is a defect, which is a
    # call docs/clean-room-audit.md reserves for a human. What is pinned is the
    # SET: it must still be exactly what was triaged. Both directions exit 2, not
    # 1, because a moved set means "nothing below was measured against a current
    # triage", not "the tree regressed".
    #
    # ⚠️ Checking BOTH directions is what keeps a missing allowlist FILE loud.
    # D-BYTEJUDGE's K3b found check 6 degrading to rc 1 when its file is deleted,
    # because "no entries" reads as "nothing to be stale about". Here the entries
    # then read as unacknowledged instead, which is still 2.
    if INLINE_CITE_TARGETS <= set(targets):
        stale = [d for d in adv_allow if d not in adv_seen]
        if stale:
            print("INSTRUMENT NOT WORKING — acknowledged advisory header(s) no "
                  "longer reported:", file=sys.stderr)
            for d in stale:
                print(f"  {adv_allow[d][0]} ({d}) — either the header gained a "
                      f"citation (delete the line) or check 3 has gone blind.",
                      file=sys.stderr)
            return 2
    if adv_unacked:
        print("INSTRUMENT NOT WORKING — the advisory set no longer matches what "
              "was triaged:", file=sys.stderr)
        for rel, ln, d in adv_unacked:
            print(f"  {rel}:{ln} ({d}) — a section header with no inline citation "
                  f"that nobody has judged. Triage it against "
                  f"docs/clean-room-audit.md's chain, then record the judgement "
                  f"in {ADVISORY_ALLOW.name}.", file=sys.stderr)
        return 2

    if advisory_total:
        print(f"ADVISORY: {advisory_total} section header(s) without an inline "
              "citation, all acknowledged — review candidates for the human paper "
              "trail, not gate failures. The SET is pinned "
              f"({ADVISORY_ALLOW.name}); the judgement is not.\n")

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
