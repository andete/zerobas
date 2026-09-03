#!/usr/bin/env python3
r"""D-GICINI — the PLAY queue state byte, read the same way on all three machines.

⚠️ NAMED D-GICINI, NOT D-MUSICF, AND THIS FILE IS NOT `musicf_probe.py`. That
name was already taken by a DIFFERENT slice (commit 3764e23: "does a PLAY naming
fewer voices stop a still-playing voice?"), and this file was written straight
over it before anyone looked. Restored from git; the two investigations share a
sysvar and nothing else.

WHY THIS ROW SET EXISTS. `basic/sound.asm:10` defers a GICINI-equivalent init to
"Slice 2" and justifies it in a parenthesis:

    "(there are no PLAY queues / MUSICF to zero yet, and C-BIOS's own boot GICINI
     already leaves the PSG quiet -- amplitudes 0 -- so a fresh SOUND works with
     no init of ours)"

🔴 THE FIRST HALF OF THAT PARENTHESIS IS FALSE TODAY. PLAY queues ship
(basic/play.asm) and so does the live drain (basic/playsvc.asm, arc slice 3).
This is the exact class D-DEFERSWEEP was built for, and the exact class that hid
D-PUSING and D-PLAYFN: a promise whose trigger has fired.
[[a-justification-parenthesis-is-an-unrun-claim]]

⚠️ IT IS A LEAD, NOT A DEFECT. The sweep "does not pretend to decide"; this is
the deciding step. Nothing in `basic/*.asm` silences the PSG or zeroes MUSICF on
ANY event (grep: no psg_silence / no gicini / no play_reset), so the question is
whether the references DO -- and that is a measurement, not a reading.

🎯 THE INSTRUMENT IS `PEEK(&HFB3F)`, AND IT IS CROSS-MACHINE BY CONSTRUCTION.
MUSICF is a published MSX work-area address, and zerobas deliberately places it
there (`basic/sysvars.inc:2993` names "a program that PEEKs MUSICF" as the
faithfulness reason). So the same expression names the same thing on the
VG-8020, the CF-3300 and zerobas -- unlike a RAM address this project chose,
which would be a layout row and not gateable at all.

🟢 CONTROLS. `m.ctl0` (no PLAY anywhere) must read 0 on all three or the address
is not what I think it is; `m.sound` says the SOUND statement does not set it;
`m.drain` says the servicer CLEARS it (without that row, a nonzero everywhere is
equally consistent with "MUSICF is never cleared", which is a different defect).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

# 🔴 `L1CDEFGAB` (~16 s) WAS TOO SHORT AND THE CONTROLS SAID SO. `e.nop`/`e.nop2`
# -- a HARMLESS direct statement in the same position as the subject's event --
# read 0 on all three, which means `e.errdir`, `e.new` and `e.cont` were not
# measuring NEW or the error path at all: omsx_repl types one line per 8 s slot,
# so any row with two slots after the PLAY simply outlives the queue. Four rows
# would have been reported as "zerobas already matches" on a timing artefact.
# T32 is the slowest MSX tempo: a whole note is 7.5 s, so these eight notes run
# ~60 s and outlive every fixture below. Note count is UNCHANGED (a longer MML
# string would fill the 128 B ring and make PLAY BLOCK, which is a different
# fixture again). [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
LONG = 'T32L1CDEFGAB'       # ~60 s: outlives the fixture's 8 s-per-line typing

# --- 🟢 CONTROLS -----------------------------------------------------------
add('m.ctl0',   [],                        'PEEK(&HFB3F)')
add('m.sound',  ['SOUND 8,15'],            'PEEK(&HFB3F)')
add('m.drain',  ['PLAY"L64C"', 'FOR I=1 TO 900:NEXT'], 'PEEK(&HFB3F)')

# --- the queue-active bitmask, one bit per voice ---------------------------
add('m.one',    [f'PLAY"{LONG}"'],                         'PEEK(&HFB3F)')
add('m.two',    [f'PLAY"{LONG}","{LONG}"'],                'PEEK(&HFB3F)')
add('m.three',  [f'PLAY"{LONG}","{LONG}","{LONG}"'],       'PEEK(&HFB3F)')
add('m.skipb',  [f'PLAY"{LONG}",,"{LONG}"'],               'PEEK(&HFB3F)')
add('m.voiceb', [f'PLAY,"{LONG}"'],                        'PEEK(&HFB3F)')

# --- degenerate strings: does an empty/rest queue still latch? -------------
add('m.empty',  ['PLAY""'],                'PEEK(&HFB3F)')
add('m.rest',   ['PLAY"R1"'],              'PEEK(&HFB3F)')

# --- the actual GICINI question: does an EVENT clear the queue? ------------
# A TRAPPED error, then RESUME to the read. If the reference's error path runs a
# GICINI-equivalent, this row is 0 there and nonzero here.
add('m.err',    [f'PLAY"{LONG}"', 'ON ERROR GOTO 50', 'ERROR 5', 'RESUME 60'],
                'PEEK(&HFB3F)')
# CLEAR / a fresh dimension: the reference's CLEAR resets a lot of work area.
add('m.clear',  [f'PLAY"{LONG}"', 'CLEAR'],                'PEEK(&HFB3F)')
# 🔴 ROUND 1's `SCREEN 1` ROW WAS VACUOUS AND SAID SO: all three read
# `<NO OUTPUT>` -- agreement that carries no information, because the scrape face
# reads SCREEN 0 text. Restoring the mode before the read is what turns it into a
# row that can fail. [[a-coverage-row-whose-geometry-cannot-reach-the-case]]
add('m.screen', [f'PLAY"{LONG}"', 'SCREEN 1:SCREEN 0'],    'PEEK(&HFB3F)')
add('m.beep',   [f'PLAY"{LONG}"', 'BEEP'],                 'PEEK(&HFB3F)')
add('m.width',  [f'PLAY"{LONG}"', 'WIDTH 32'],             'PEEK(&HFB3F)')
# --- ROUND 3: BOUND THE SET. `m.beep` went DIFF, so the question is no longer
# "does an abort clear it" but "WHICH statements do". These are the cheap
# neighbours of BEEP (another PSG writer), and of the abort seam.
add('m.sound2', [f'PLAY"{LONG}"', 'SOUND 8,15'],           'PEEK(&HFB3F)')
add('m.sound7', [f'PLAY"{LONG}"', 'SOUND 7,63'],           'PEEK(&HFB3F)')
add('m.cls',    [f'PLAY"{LONG}"', 'CLS'],                  'PEEK(&HFB3F)')
add('m.keyoff', [f'PLAY"{LONG}"', 'KEY OFF'],              'PEEK(&HFB3F)')
add('m.beep2',  ['BEEP'],                                  'PEEK(&HFB3F)')

# --- the OTHER published readout for the same fact -------------------------
add('m.playfn', [f'PLAY"{LONG}"'],         'PLAY(0)')
add('m.playfn0',[],                        'PLAY(0)')

# --- 🎯 THE ROWS THE PROGRAM FORM CANNOT REACH: RETURN TO THE `Ok` PROMPT ----
# A GICINI-equivalent, if the reference ran one, would most plausibly run on the
# way BACK to direct mode -- which is exactly where a `10..60 / RUN` fixture
# cannot look, because line 60 never executes. These are DIRECT rows: type the
# program, RUN it into its ending, then read MUSICF from the prompt.
DIRECT = {
  'e.ctl'   : ['CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.direct': [f'PLAY"{LONG}"', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.end'   : [f'10 PLAY"{LONG}"', '20 END', 'RUN', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.untrap': [f'10 PLAY"{LONG}"', '20 ERROR 5', 'RUN', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.stop'  : [f'10 PLAY"{LONG}"', '20 STOP', 'RUN', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  # is it the ERROR, or any abort? and is `ERROR 5` a fair stand-in for a
  # naturally-raised one? `e.errnat` raises Undefined line number for real.
  'e.errnat': [f'10 PLAY"{LONG}"', '20 GOSUB 999', 'RUN', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  # a DIRECT-mode error at the prompt, with no program running at all.
  'e.errdir': [f'PLAY"{LONG}"', 'GOSUB 999', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  # after a break, CONT resumes the program -- does the music come back? (it
  # cannot; this row says whether the queue was DESTROYED or merely paused)
  'e.cont'  : [f'10 PLAY"{LONG}"', '20 STOP', '30 END', 'RUN', 'CONT', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  # 🟢 THE ROWS THAT SAY `e.errdir` / `e.new` AGREE FOR THE RIGHT REASON. Both
  # read 0 on zerobas too -- but so would any row whose extra TYPED LINE simply
  # gave the queue time to drain. These two insert a harmless direct statement
  # in the same position and must read 1; if they read 0, the two agreeing rows
  # above are timing artefacts and say nothing about NEW or the error path.
  # [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
  'e.nop'   : [f'PLAY"{LONG}"', 'X=1', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.nop2'  : [f'PLAY"{LONG}"', 'PRINT', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  # 🔴 THESE TWO FIRST USED `PLAY"T32L1C"` -- ONE whole note, 7.5 s, which drains
  # inside the fixture's own 8 s slot. They read 0 on all three and would have
  # been recorded as "the replay behaves identically" while measuring nothing:
  # the SAME artefact §4 of the spec is about, caught a second time in the same
  # session because the control row for it was already written down.
  # 🎯 THE ROW THAT SAYS THE FIX DID NOT MERELY PAPER OVER. Silencing the PSG and
  # zeroing MUSICF stops the drain; it says nothing about whether the queue is
  # left in a state a LATER `PLAY` can use. If the ring pointers are stale, this
  # row goes wrong in a way none of the six divergent rows can see.
  'e.replay': [f'10 PLAY"{LONG}"', '20 STOP', 'RUN', f'PLAY"{LONG}"', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.replayfn': [f'10 PLAY"{LONG}"', '20 STOP', 'RUN', f'PLAY"{LONG}"', 'CLS:PRINT"[";PLAY(0);"]"'],
  'e.new'   : [f'10 PLAY"{LONG}"', 'RUN', 'NEW', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
  'e.runagain': [f'10 PLAY"{LONG}"', 'RUN', 'RUN', 'CLS:PRINT"[";PEEK(&HFB3F);"]"'],
}
D.DIRECT.update(DIRECT); ORDER.extend(DIRECT)

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides) + "   verdict")
diff = []
for l in ORDER:
    vals = [str(res[s].get(l)) for s in sides]
    same = len(set(vals)) == 1
    if not same: diff.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{v:>18}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(ORDER)}  " + " ".join(diff))
print("done")
