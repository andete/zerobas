#!/usr/bin/env python3
r"""D-MUSICF — does a PLAY that names FEWER voices stop a still-playing voice?

Found by code review (2026-08-31), not by a row: `pt_commit`
(sub/playparse.asm) publishes the new voice set with `ld (MUSICF),a` -- a
WHOLESALE STORE. A `PLAY "E"` issued while voice B is still sounding from an
earlier `PLAY "...","..."` would then clear B's MUSICF bit without ever
reaching psv_end (the only code that writes its amplitude to 0): the drain
stops, the channel keeps sounding, and PLAY(2) reports idle while the tone is
audibly on. The reference is expected to let unmentioned voices play on.

ROWS (one typed line per setup entry; L1 notes are ~2 s each at the default
T120, so an 8-note string is ~16 s of music -- far longer than the harness's
inter-line pacing, which is what makes "still playing" a stable reading):

  ctl.idle   no PLAY at all            -> PLAY(2) = 0 everywhere  🟢
  ctl.play2  PLAY on A+B               -> PLAY(2) = -1 everywhere 🟢
             (B mid-music when the expression runs)
  r.drop     PLAY on A+B, then PLAY"C" -> PLAY(2): the question. Reference
             expectation -1 (B plays on); the reviewed code would say 0.
  r.keep1    same setup, PLAY(1)       -> -1 both ways (voice A got the new
             string; L=1 PERSISTED from the first string, so "C" is ~2 s) 🟢

⚠️ NOT CONFUSABLE WITH THE FILED START-UP-WINDOW DIVERGENCE
(playfn_fixture_probe, tools/filed-row-known.txt): that one is about a voice
reading ACTIVE during PLAY's own start-up with NO string supplied for it, on a
~one-statement timescale. Here voice B is genuinely mid-music for ~16 s and the
reading is taken through a second statement -- the window cannot produce these
rows' difference.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

LONG = 'PLAY"L1CCCCCCCC","L1EEEEEEEE"'
CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

add('ctl.idle',  [],                 'PLAY(2)')
add('ctl.play2', [LONG],             'PLAY(2)')
add('r.drop',    [LONG, 'PLAY"C"'],  'PLAY(2)')
add('r.keep1',   [LONG, 'PLAY"C"'],  'PLAY(1)')
# 🟢 completion control: after the music has genuinely ended everywhere, all
# three read idle again -- the row that says the fixed drain still REACHES
# psv_end (the amp-0 writer) instead of holding the bit forever.
# 🔴 THE FIRST CUT OF THIS ROW USED THE 16 s FIXTURE + AN 18 s FOR LOOP, AND
# ALL THREE MACHINES "AGREED" ON THE STRING ';PLAY(2);' -- the probe's own
# typed line read back as a value (the trapsvc-echo-fence class): the delay
# outran the harness pacing on every side at once, and a three-way agreement
# on garbage is an agreement of silences, not a reading. This row runs on its
# OWN SHORT timescale so the completion question fits inside the pacing on
# EVERY side; r.drop keeps the 16 s fixture. (Second lesson from the same
# fence: 1500 iterations ~3.5 s cleared the references' pacing and STILL
# outran zerobas's shorter step -- one side's echo-fence is a DIFF that reads
# like a regression. The music is ~0.5 s, so ~0.9 s of delay is enough.)
add('r.done',    ['PLAY"L16CC","L16EE"', 'PLAY"C"',
                  'FORI=1TO400:NEXT'], 'PLAY(2)')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>12}" for s in sides) + "   verdict")
diff, blind = [], []
for l in ORDER:
    zb = str(res["zb"].get(l)) if "zb" in res else "-"
    refs = [str(res[s].get(l)) for s in sides if s != "zb"]
    same = all(r == zb for r in refs)
    if refs and not same:
        diff.append(l)
    if any("<NO OUTPUT>" in str(res[s].get(l)) or "<NO CAPTURE>" in str(res[s].get(l))
           for s in sides):
        blind.append(l)
    print(f"{l:<{w}}  " + "  ".join(f"{str(res[s].get(l)):>12}" for s in sides)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF vs references: {len(diff)}/{len(ORDER)}"
      + ("  " + " ".join(diff) if diff else ""))
if blind:
    print(f"🔴 {len(blind)} ROW(S) BLIND: " + " ".join(blind))
    raise SystemExit(2)
raise SystemExit(1 if diff else 0)
