10 REM D-PLAYQUEUE: queue bytes each MML element costs (voice A held by a long note;
11 REM QUETAB's first entry: +0 PUTPNT, +1 GETPNT -- documented work-area RAM)
20 FOR I=1 TO 16:READ A$
30 PLAY "T32L1V0C":FOR W=1 TO 20:NEXT:P=PEEK(&HF959):G=PEEK(&HF95A)
40 PLAY A$:Q=PEEK(&HF959):LPRINT I;(Q-P+128) MOD 128;G;PEEK(&HF95A);A$
50 BEEP:SOUND 8,0:NEXT:END
60 DATA "C","C8","C8.","CC","CDE","N60","R","R8","O4","L8","T120","V8","S1","M100","C#","O4L8T120C"
