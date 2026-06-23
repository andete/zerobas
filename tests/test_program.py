# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: stored-program line-link editor in basic/program.asm, no emulator.

Tests the core line-link editor routines: new_prog, store_line, relink, and
the delete path (via store_line with an empty body). All assertions are
derived from the documented line-link format and address constants:

  Line format (program.asm header):
      [link:2 LE][lineno:2 LE][crunched tokens...][00]

  The program ends with a link word of $0000 at TXTBASE.
  PRGEND holds the address of the $0000 end-of-program marker.
  TXTBASE ($8001) is the text base (oracle: sysvars.inc §Step B).

Oracle basis:
  - Layout and address constants from sysvars.inc and program.asm comments.
  - Link word = absolute address of the NEXT line's link field (program.asm
    `relink` comment: "A line's link = the address of the following line's link
    field"; the last line's link = address of the $0000 end marker = PRGEND).
  - Line size = 4 (link+lineno) + body length including the $00 terminator
    (program.asm store_line comment: "line size = 4 (link+lineno) + body length
    (incl 00)").

Stubs:
  - CHPUT is trapped to suppress console output from any error path.
  - BREAKX is trapped (returns Cy=0 = not pressed) as a safety net; none of
    the routines under test call it, but the trap is cheap insurance.
  - CHGET is NOT called by any tested routine; no stub needed.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM  = "/tmp/zb_prog.rom"
SYM  = "/tmp/zb_prog.sym"
TOKBUF_SCRATCH = 0xE160  # TOKBUF from sysvars.inc (safe scratch area)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(
        ["pasmo", "--bin", src, ROM, SYM],
        check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_machine():
    """Fresh Machine with safe stubs for CHPUT and BREAKX."""
    m = Machine(ROM, SYM)
    # CHPUT: trap and discard (print_string calls it on every error path)
    m.trap("CHPUT", lambda m: None)
    # BREAKX ($00B7): return Cy=0 (not pressed) — insurance; none of the
    # routines under test call it, but run_prog does if we ever call it.
    m.trap("BREAKX", lambda m: setattr(m.cpu, "f", m.cpu.f & ~0x01))
    return m


def body(token_bytes):
    """Build a token body: token_bytes + b'\\x00' terminator, at TOKBUF_SCRATCH.

    Returns (pointer, full_bytes) where pointer is the TOKBUF_SCRATCH address
    and full_bytes is what was poked into RAM. The caller must poke this into
    the Machine before calling store_line.
    """
    data = bytes(token_bytes) + b"\x00"
    return TOKBUF_SCRATCH, data


def place_body(m, token_bytes):
    """Poke a token body into TOKBUF_SCRATCH and return its address."""
    ptr, data = body(token_bytes)
    m.poke(ptr, data)
    return ptr


def call_new_prog(m):
    m.call("new_prog")


def call_store_line(m, lineno, token_bytes):
    """Store a line. BC=lineno, HL=TOKBUF_SCRATCH (pointing at token body)."""
    ptr = place_body(m, token_bytes)
    m.call("store_line", bc=lineno, hl=ptr)


def call_delete_line(m, lineno):
    """Delete a line: store_line with empty body (first byte = 0x00)."""
    # An empty body is just the $00 terminator; store_line detects (hl)==0
    # and jumps to sl_delete (program.asm:347 "empty body -> delete only").
    ptr = place_body(m, [])  # places [0x00] at TOKBUF_SCRATCH
    m.call("store_line", bc=lineno, hl=ptr)


# ---------------------------------------------------------------------------
# Chain walker
# ---------------------------------------------------------------------------

def walk_chain(m):
    """Walk the link chain from TXTBASE.

    Returns a list of dicts, one per stored line:
      { 'link_addr': <absolute address of the link field>,
        'link_word': <value of the link word (LE)>,
        'lineno':    <line number (LE)>,
        'body':      <bytes of token body, including the $00 terminator> }

    Stops when the link word is $0000 (the end-of-program sentinel).
    Raises AssertionError if the chain is obviously corrupt (infinite loop
    guard: more than 4096 lines).
    """
    s = m.sym
    base = s["TXTBASE"]  # 0x8001
    entries = []
    addr = base
    for _ in range(4096):
        link_lo = m.mem[addr]
        link_hi = m.mem[addr + 1]
        link_word = link_lo | (link_hi << 8)
        if link_word == 0x0000:
            break          # end-of-program sentinel
        lineno_lo = m.mem[addr + 2]
        lineno_hi = m.mem[addr + 3]
        lineno = lineno_lo | (lineno_hi << 8)
        # collect body bytes (everything from addr+4 up to and including the
        # $00 terminator); walk token-aware (but we trust relink to have been
        # called, so we can just scan for the $00 — our bodies have no
        # embedded zeros).
        body_start = addr + 4
        body_bytes = []
        p = body_start
        while True:
            b = m.mem[p]
            body_bytes.append(b)
            p += 1
            if b == 0x00:
                break
        entries.append({
            'link_addr': addr,
            'link_word': link_word,
            'lineno':    lineno,
            'body':      bytes(body_bytes),
        })
        addr = link_word   # follow the link to the next line
    else:
        raise AssertionError("chain walk limit exceeded — corrupt link chain")
    return entries


# ---------------------------------------------------------------------------
# Oracle: expected link values
# ---------------------------------------------------------------------------

def expected_link_word(entries, idx, prgend_addr):
    """The link word at entries[idx] must equal the address of the NEXT line's
    link field (program.asm relink: 'A line's link = the address of the
    following line's link field'). For the last line that is PRGEND."""
    if idx + 1 < len(entries):
        return entries[idx + 1]['link_addr']
    return prgend_addr


def line_size(token_bytes):
    """Full on-disk size of a line in bytes.

    program.asm store_line: 'line size = 4 (link+lineno) + body length
    (incl 00)'. Body length = len(token_bytes) + 1 (for the $00 terminator).
    """
    return 4 + len(token_bytes) + 1


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

# A trivial single-byte token body: digit-1 token ($12 = INT_DIGIT_BASE + 1).
# tok_skip treats this as a plain byte (no operand), so skip_to_eol correctly
# advances HL past it to the $00 terminator. Body bytes = [0x12].
BODY_1 = [0x12]   # DIGIT 1 token — INT_DIGIT_BASE + 1 ($11 + 1)
BODY_2 = [0x13]   # DIGIT 2 token
BODY_3 = [0x14]   # DIGIT 3 token
BODY_NEW = [0x15] # DIGIT 4 token (replacement body)


def test_new_prog_empty(m, fails):
    """new_prog: TXTBASE holds $0000, PRGEND = TXTBASE, TXTTAB = TXTBASE.

    Oracle: program.asm new_prog:
      ld  hl,TXTBASE       ; HL = $8001
      ld  (TXTTAB),hl      ; TXTTAB sysvar <- $8001
      ld  (PRGEND),hl      ; PRGEND <- $8001
      ld  hl,0
      ld  (TXTBASE),hl     ; RAM[$8001] = $0000 end marker
    """
    call_new_prog(m)
    s = m.sym
    base = s["TXTBASE"]   # the CONSTANT 0x8001, also the RAM address

    # 1a. $0000 end marker at TXTBASE address
    end_marker = m.mem[base] | (m.mem[base + 1] << 8)
    ok = (end_marker == 0x0000)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  new_prog: RAM[TXTBASE] = 0x0000 end marker "
          f"(got {end_marker:#06x})")

    # 1b. PRGEND = TXTBASE (points at the end marker)
    prgend = m.mem[s["PRGEND"]] | (m.mem[s["PRGEND"] + 1] << 8)
    ok = (prgend == base)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  new_prog: PRGEND = TXTBASE = "
          f"{base:#06x} (got {prgend:#06x})")

    # 1c. TXTTAB = TXTBASE (keep real sysvar consistent)
    txttab = m.mem[s["TXTTAB"]] | (m.mem[s["TXTTAB"] + 1] << 8)
    ok = (txttab == base)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  new_prog: TXTTAB = TXTBASE = "
          f"{base:#06x} (got {txttab:#06x})")

    # 1d. chain walk sees zero lines
    entries = walk_chain(m)
    ok = (len(entries) == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  new_prog: chain has 0 lines (got {len(entries)})")

    # 1e. CONTVALID cleared
    cv = m.mem[s["CONTVALID"]]
    ok = (cv == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  new_prog: CONTVALID = 0 (got {cv})")

    return fails


def test_insert_ordering(m, fails):
    """store_line + relink: lines inserted out-of-order appear sorted ascending.

    Oracle: program.asm prog_find_del walks the chain and inserts at the FIRST
    slot whose stored line number >= target, so inserting 20, 10, 30 (in that
    order) must produce the chain 10 -> 20 -> 30, with each link word pointing
    at the next line's link field and the final link = $0000 (PRGEND).

    Each line's link word after relink equals the ABSOLUTE ADDRESS of the
    following line's link field (program.asm relink comment: 'A line's link =
    the address of the following line's link field').
    """
    call_new_prog(m)
    call_store_line(m, lineno=20, token_bytes=BODY_2)
    call_store_line(m, lineno=10, token_bytes=BODY_1)
    call_store_line(m, lineno=30, token_bytes=BODY_3)

    s = m.sym
    prgend = m.mem[s["PRGEND"]] | (m.mem[s["PRGEND"] + 1] << 8)
    entries = walk_chain(m)

    # 2a. Three lines present
    ok = (len(entries) == 3)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  insert: chain has 3 lines (got {len(entries)})")

    # 2b. Ascending order: 10, 20, 30
    if len(entries) == 3:
        nos = [e['lineno'] for e in entries]
        ok = (nos == [10, 20, 30])
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  insert: line numbers ascending [10,20,30] "
              f"(got {nos})")

        # 2c. Link words are structurally correct:
        #     entries[0].link_word = entries[1].link_addr  (line 10 -> line 20)
        #     entries[1].link_word = entries[2].link_addr  (line 20 -> line 30)
        #     entries[2].link_word = PRGEND                (line 30 -> end marker)
        for i, e in enumerate(entries):
            want = expected_link_word(entries, i, prgend)
            ok = (e['link_word'] == want)
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'}  insert: line {e['lineno']} "
                  f"link_word = {want:#06x} "
                  f"(got {e['link_word']:#06x})")

        # 2d. Physical layout: TXTBASE holds line 10 first
        first_lineno = entries[0]['lineno']
        ok = (first_lineno == 10)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  insert: first line in RAM is line 10 "
              f"(got {first_lineno})")

        # 2e. PRGEND points exactly past the last line's $00 terminator
        #     Each line occupies: link(2) + lineno(2) + body_len_incl_term bytes.
        #     line 10: body=[BODY_1, 0x00] = 2 bytes, line size = 4+2 = 6
        #     line 20: body=[BODY_2, 0x00] = 2 bytes, line size = 6
        #     line 30: body=[BODY_3, 0x00] = 2 bytes, line size = 6
        #     PRGEND = TXTBASE + 6 + 6 + 6 = TXTBASE + 18
        expected_prgend = s["TXTBASE"] + line_size(BODY_1) + line_size(BODY_2) + line_size(BODY_3)
        ok = (prgend == expected_prgend)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  insert: PRGEND = {expected_prgend:#06x} "
              f"(got {prgend:#06x})")

    return fails


def test_replace_line(m, fails):
    """store_line with existing line number replaces it; chain stays consistent.

    Oracle: program.asm prog_find_del: 'stored >= target ... exact match? ...
    same number -> delete then reuse slot'; open_gap then writes the new body.
    After relink the chain must still be correct (predecessor links past the
    old line to the new one at the same slot position).
    """
    call_new_prog(m)
    call_store_line(m, lineno=10, token_bytes=BODY_1)
    call_store_line(m, lineno=20, token_bytes=BODY_2)
    call_store_line(m, lineno=30, token_bytes=BODY_3)

    # Replace line 20 with BODY_NEW (different length: same 1-byte body here,
    # but we assert the body content changed).
    call_store_line(m, lineno=20, token_bytes=BODY_NEW)

    s = m.sym
    prgend = m.mem[s["PRGEND"]] | (m.mem[s["PRGEND"] + 1] << 8)
    entries = walk_chain(m)

    # 3a. Still 3 lines
    ok = (len(entries) == 3)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  replace: chain still has 3 lines (got {len(entries)})")

    if len(entries) == 3:
        nos = [e['lineno'] for e in entries]
        # 3b. Order preserved
        ok = (nos == [10, 20, 30])
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  replace: order [10,20,30] preserved "
              f"(got {nos})")

        # 3c. Line 20 body is now BODY_NEW + $00
        want_body = bytes(BODY_NEW) + b"\x00"
        got_body = entries[1]['body']
        ok = (got_body == want_body)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  replace: line 20 body = "
              f"{want_body.hex()} (got {got_body.hex()})")

        # 3d. Links structurally correct after replace
        for i, e in enumerate(entries):
            want = expected_link_word(entries, i, prgend)
            ok = (e['link_word'] == want)
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'}  replace: line {e['lineno']} "
                  f"link_word = {want:#06x} "
                  f"(got {e['link_word']:#06x})")

        # 3e. Chains are reachable (walk reaches all 3 without corruption)
        ok = (len(entries) == 3 and nos == [10, 20, 30])
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  replace: all 3 lines reachable via chain")

    return fails


def test_delete_line(m, fails):
    """store_line with empty body deletes the line; predecessor links past it.

    Oracle: program.asm store_line 'sl_delete' path:
      'empty body -> delete only'; calls prog_find_del which calls delete_at.
    delete_at: 'Shifts the rest of the program (including the end marker) down
    over it and shrinks PRGEND'. After relink the chain skips the deleted line.
    """
    call_new_prog(m)
    call_store_line(m, lineno=10, token_bytes=BODY_1)
    call_store_line(m, lineno=20, token_bytes=BODY_2)
    call_store_line(m, lineno=30, token_bytes=BODY_3)

    # Delete the middle line (20)
    call_delete_line(m, lineno=20)

    s = m.sym
    prgend = m.mem[s["PRGEND"]] | (m.mem[s["PRGEND"] + 1] << 8)
    entries = walk_chain(m)

    # 4a. Now 2 lines
    ok = (len(entries) == 2)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  delete: chain has 2 lines after deleting 20 "
          f"(got {len(entries)})")

    if len(entries) == 2:
        nos = [e['lineno'] for e in entries]
        # 4b. Lines 10 and 30 remain; 20 is gone
        ok = (nos == [10, 30])
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  delete: remaining lines [10,30] "
              f"(got {nos})")

        # 4c. Link words structurally correct: 10 -> 30 -> PRGEND
        for i, e in enumerate(entries):
            want = expected_link_word(entries, i, prgend)
            ok = (e['link_word'] == want)
            fails += not ok
            print(f"{'PASS' if ok else 'FAIL'}  delete: line {e['lineno']} "
                  f"link_word = {want:#06x} "
                  f"(got {e['link_word']:#06x})")

        # 4d. PRGEND shrank: now TXTBASE + line10_size + line30_size
        expected_prgend = s["TXTBASE"] + line_size(BODY_1) + line_size(BODY_3)
        ok = (prgend == expected_prgend)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  delete: PRGEND = {expected_prgend:#06x} "
              f"(got {prgend:#06x})")

        # 4e. Line 20 bytes are no longer in the program image
        #     (PRGEND is the end marker; the 2 bytes at prgend must be $0000)
        end_lo = m.mem[prgend]
        end_hi = m.mem[prgend + 1]
        ok = (end_lo == 0 and end_hi == 0)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  delete: end marker at PRGEND = $0000 "
              f"(got {end_lo:#04x} {end_hi:#04x})")

    # 4f. Delete a non-existent line is a no-op (chain unchanged)
    entries_before = walk_chain(m)
    call_delete_line(m, lineno=99)
    entries_after = walk_chain(m)
    nos_before = [e['lineno'] for e in entries_before]
    nos_after = [e['lineno'] for e in entries_after]
    ok = (nos_before == nos_after)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  delete: deleting non-existent line 99 is a no-op "
          f"(before={nos_before}, after={nos_after})")

    return fails


def test_relink_standalone(m, fails):
    """relink recomputes every link word from scratch.

    Strategy: manually write a two-line program with WRONG link words (e.g.
    $0000 for both), then call relink and assert the link words are corrected
    to the oracle values (next line's link_addr for all but the last; PRGEND
    for the last).

    Oracle: program.asm relink: 'A line's link = the address of the following
    line's link field'; walks from TXTBASE until HL == PRGEND.
    """
    call_new_prog(m)
    s = m.sym
    base = s["TXTBASE"]  # 0x8001

    # Manually construct a 2-line program with BODY_1 and BODY_2:
    #   Line 10 at base: link=0000(placeholder), lineno=10, body=BODY_1+$00
    #   Line 20 follows: link=0000(placeholder), lineno=20, body=BODY_2+$00
    #   End marker $0000 after line 20
    line10_body = bytes(BODY_1) + b"\x00"
    line20_body = bytes(BODY_2) + b"\x00"
    line10_size = 4 + len(line10_body)   # = 4 + 2 = 6
    line20_size = 4 + len(line20_body)   # = 4 + 2 = 6

    line10_addr = base
    line20_addr = line10_addr + line10_size
    prgend_addr = line20_addr + line20_size

    # Write line 10 with deliberate wrong link ($0000)
    m.mem[line10_addr + 0] = 0x00   # link lo (wrong)
    m.mem[line10_addr + 1] = 0x00   # link hi (wrong)
    m.mem[line10_addr + 2] = 10     # lineno lo
    m.mem[line10_addr + 3] = 0      # lineno hi
    for i, b in enumerate(line10_body):
        m.mem[line10_addr + 4 + i] = b

    # Write line 20 with deliberate wrong link ($0000)
    m.mem[line20_addr + 0] = 0x00   # link lo (wrong)
    m.mem[line20_addr + 1] = 0x00   # link hi (wrong)
    m.mem[line20_addr + 2] = 20     # lineno lo
    m.mem[line20_addr + 3] = 0      # lineno hi
    for i, b in enumerate(line20_body):
        m.mem[line20_addr + 4 + i] = b

    # Write end marker at prgend_addr
    m.mem[prgend_addr + 0] = 0x00
    m.mem[prgend_addr + 1] = 0x00

    # Set PRGEND to point at the end marker
    m.poke_w(s["PRGEND"], prgend_addr)

    # Call relink
    m.call("relink")

    # Now read back the link words
    link10_lo = m.mem[line10_addr]
    link10_hi = m.mem[line10_addr + 1]
    link10 = link10_lo | (link10_hi << 8)

    link20_lo = m.mem[line20_addr]
    link20_hi = m.mem[line20_addr + 1]
    link20 = link20_lo | (link20_hi << 8)

    # 5a. Line 10's link = line20_addr
    ok = (link10 == line20_addr)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  relink: line 10 link = line20_addr "
          f"= {line20_addr:#06x} (got {link10:#06x})")

    # 5b. Line 20's link = prgend_addr (last line -> end marker)
    ok = (link20 == prgend_addr)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  relink: line 20 link = prgend_addr "
          f"= {prgend_addr:#06x} (got {link20:#06x})")

    # 5c. End marker at prgend_addr is still $0000
    end = m.mem[prgend_addr] | (m.mem[prgend_addr + 1] << 8)
    ok = (end == 0x0000)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  relink: end marker at PRGEND still $0000 "
          f"(got {end:#06x})")

    # 5d. Chain walk now sees 2 lines with correct order
    entries = walk_chain(m)
    ok = (len(entries) == 2 and [e['lineno'] for e in entries] == [10, 20])
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  relink: chain walk sees [10,20] after relink "
          f"(got {[e['lineno'] for e in entries]})")

    return fails


def test_new_prog_invalidates_cont(m, fails):
    """new_prog clears CONTVALID.

    Oracle: program.asm new_prog: 'xor a / ld (CONTVALID),a' — NEW wipes the
    program -> no CONT resume'. Editing the program (store_line / NEW) clears
    CONTVALID so CONT errors 'Can't CONTINUE' (sysvars.inc CONTVALID comment).
    """
    call_new_prog(m)
    s = m.sym
    # Set CONTVALID to 1 (pretend a STOP was executed)
    m.poke(s["CONTVALID"], 1)
    # Call new_prog again
    call_new_prog(m)
    cv = m.mem[s["CONTVALID"]]
    ok = (cv == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  new_prog: CONTVALID cleared to 0 "
          f"(got {cv})")
    return fails


def test_store_line_invalidates_cont(m, fails):
    """store_line clears CONTVALID.

    Oracle: program.asm store_line: 'xor a / ld (CONTVALID),a — editing the
    program invalidates CONT'.
    """
    call_new_prog(m)
    s = m.sym
    # Set CONTVALID to 1
    m.poke(s["CONTVALID"], 1)
    call_store_line(m, lineno=10, token_bytes=BODY_1)
    cv = m.mem[s["CONTVALID"]]
    ok = (cv == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  store_line: CONTVALID cleared to 0 "
          f"(got {cv})")
    return fails


def test_empty_program_chain(m, fails):
    """After new_prog, the program is truly empty: walk_chain returns [].

    Oracle: new_prog writes $0000 at TXTBASE (the end marker), so the first
    link word seen by walk_chain is $0000, and the loop terminates immediately.
    """
    call_new_prog(m)
    entries = walk_chain(m)
    ok = (len(entries) == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  empty: chain empty after new_prog "
          f"(got {len(entries)} lines)")
    return fails


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run():
    build()
    m = make_machine()
    s = m.sym  # noqa: F841 (used inside tests via m.sym)
    fails = 0

    print("=== new_prog: empty program ===")
    fails = test_new_prog_empty(m, fails)
    print()

    m = make_machine()
    print("=== new_prog: CONTVALID cleared ===")
    fails = test_new_prog_invalidates_cont(m, fails)
    print()

    m = make_machine()
    print("=== store_line: CONTVALID cleared ===")
    fails = test_store_line_invalidates_cont(m, fails)
    print()

    m = make_machine()
    print("=== store_line: insert ordering (20, 10, 30 -> chain 10,20,30) ===")
    fails = test_insert_ordering(m, fails)
    print()

    m = make_machine()
    print("=== store_line: replace existing line ===")
    fails = test_replace_line(m, fails)
    print()

    m = make_machine()
    print("=== store_line + delete: remove middle line ===")
    fails = test_delete_line(m, fails)
    print()

    m = make_machine()
    print("=== relink: standalone (wrong links corrected) ===")
    fails = test_relink_standalone(m, fails)
    print()

    m = make_machine()
    print("=== empty program chain ===")
    fails = test_empty_program_chain(m, fails)
    print()

    if not fails:
        print("ALL PASS — line-link editor matches the documented format")
    else:
        print(f"{fails} CHECK(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
