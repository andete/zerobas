# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""probes/lib/probe_report.py -- the row grammar and, above all, its PARSER.

docs/spec-probe-rowshape.md §5.5. `parse()` exists to be a knife runner's guard
against reading a PREFIX of a report as a whole one, and that guard's failure
path is executed by nothing else in this tree -- no probe, no acceptance gate and
no green run ever calls it. A failure path nothing exercises is this whole
slice's subject, so it is exercised here.

The two faults these tests stand against, both measured 2026-08-07 (D-CASOPEN):

  * a runner's truncation guard fired on a COMPLETE 32-row report because the
    two shapes are indented differently -> `parse()` must not anchor on a column;
  * a runner diffing report LINES scored EVERY row as moved because the same
    reading prints two ways -> `parse()` must return VALUES, and a note must
    never contaminate one.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "lib"))
import probe_report                                              # noqa: E402


def _report(rows, n=None, scored=None):
    body = "\n".join(rows)
    n = len(rows) if n is None else n
    return body + "\n" + probe_report.footer(n, n if scored is None else scored,
                                             "test")


def test_row_is_one_grammar_whatever_the_tag():
    """I1: the label column does not move between tags."""
    a = probe_report.row("ok", "cas-run-hit", 22, {"zb": "ZQ9"})
    b = probe_report.row("DIFF", "cas-run-hit", 22, {"zb": "ZQ9"})
    c = probe_report.row("....", "cas-run-hit", 22, {"zb": "ZQ9"}, "  (not scored)")
    cols = {line.index("cas-run-hit") for line in (a, b, c)}
    assert len(cols) == 1, f"the label column moved between tags: {cols}"
    assert cols == {probe_report.TAG_W + 1}


def test_row_names_every_side_even_when_they_agree():
    """I2: one encoding. An `ok` row that shows ONE value asks the reader to
    TRUST that both sides gave it -- which is the fault, not the fix."""
    line = probe_report.row("ok", "lab", 10, {"cf3300": "X", "zb": "X"})
    assert "cf3300='X'" in line and "zb='X'" in line


def test_parse_recovers_values_not_lines():
    rows = [probe_report.row("ok", "one", 10, {"cf3300": "A", "zb": "A"}),
            probe_report.row("DIFF", "two", 10, {"cf3300": "A", "zb": "B"})]
    got = probe_report.parse(_report(rows))
    assert [r.label for r in got] == ["one", "two"]
    assert got[0].vals == {"cf3300": "A", "zb": "A"}
    assert got[1].vals["zb"] == "B"


def test_parse_ignores_indentation():
    """The D-CASOPEN abort, as a test: an indented report is still a report."""
    rows = ["  " + probe_report.row("....", "one", 10, {"zb": "A"},
                                    "  (not scored)")]
    got = probe_report.parse(_report(rows))
    assert len(got) == 1 and got[0].vals == {"zb": "A"}


def test_note_never_contaminates_a_value():
    line = probe_report.row("PIN", "lab", 10, {"zb": "A"}, "   [PINNED DIVERGENCE]")
    got = probe_report.parse(_report([line]))
    assert got[0].vals == {"zb": "A"}
    assert "PINNED" in got[0].note


def test_value_containing_equals_quotes_and_spaces_round_trips():
    """Why the grammar renders values with repr() at all (spec §3)."""
    nasty = "a=b 'c' \"d\"  e"
    got = probe_report.parse(_report([probe_report.row("ok", "l", 8, {"zb": nasty})]))
    assert got[0].vals["zb"] == nasty, got[0].vals


def test_empty_value_round_trips():
    got = probe_report.parse(_report([probe_report.row("ok", "l", 8, {"zb": ""})]))
    assert got[0].vals == {"zb": ""}


def test_a_missing_footer_RAISES():
    """A short list is indistinguishable from 'the knife moved nothing'."""
    line = probe_report.row("ok", "l", 8, {"zb": "A"})
    try:
        probe_report.parse(line)
    except probe_report.ReportTruncated:
        return
    raise AssertionError("a report with no terminator parsed as if it were whole")


def test_a_count_mismatch_RAISES():
    """The probe crashed mid-report: a PREFIX with a footer is still a prefix."""
    rows = [probe_report.row("ok", f"l{i}", 8, {"zb": "A"}) for i in range(3)]
    try:
        probe_report.parse(_report(rows, n=32))
    except probe_report.ReportTruncated as e:
        assert "32" in str(e) and "3" in str(e)
        return
    raise AssertionError("a 3-row prefix declaring 32 rows parsed as whole")


def test_a_continuation_line_is_not_a_row():
    """`ROTTED [...]` starts with the letters of the ROT tag and must not match;
    neither must the `PINNED:` banner."""
    rows = [probe_report.row("ROT", "l", 8, {"zb": "A"})]
    text = _report(rows).replace(
        "ROWS:", "      ROTTED [zb] pinned 'B', read 'A'\n"
                 "PINNED: the tape-search progress rows\nROWS:")
    got = probe_report.parse(text)
    assert len(got) == 1 and got[0].tag == "ROT"


def test_an_unknown_tag_is_refused_at_the_printing_end():
    try:
        probe_report.row("HUH", "l", 8, {"zb": "A"})
    except ValueError:
        return
    raise AssertionError("an off-grammar tag printed without complaint")


def test_the_four_migrated_probes_and_the_control_import_the_module():
    """The gate is static; this is the behavioural half of the same claim."""
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    want = ["probes/basic/basic_probe_castail.py",
            "probes/basic/basic_probe_cassave.py",
            "probes/basic/basic_probe_runtail.py",
            "probes/basic/basic_probe_dskmsg.py",
            "probes/disk/disk_probe_fat_error_disposition.py"]
    for rel in want:
        src = open(os.path.join(root, rel), encoding="utf-8").read()
        assert "import probe_report" in src, rel
        assert "probe_report.footer(" in src, f"{rel} prints no terminator"


def run():
    fails = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception as e:                       # noqa: BLE001
                fails.append(f"{name}: {e}")
    for f in fails:
        print(f"FAIL {f}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"probe_report: {n - len(fails)}/{n} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
