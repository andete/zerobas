10 REM ** JUKEBOX - TUNES WITH PLAY, A DRUM WITH SOUND, AND A CLOCK WITH ON INTERVAL **
20 SCREEN 0:WIDTH 40:KEY OFF:CLS
25 REM every tune is timed by TIME until the queue is empty and checked within 4
26 REM jiffies against the length the VG-8020 measured; no note is shorter than L16 at
27 REM T120 (shorter ones are D-PLAYRATE)
30 REM 1: a tune in one voice: 8 eighths at T120
40 A$="T120O4L8CDEFGABO5C":W=100:GOSUB 500:LPRINT "CP 1";W;OK;PLAY(0)
50 REM 2: lengths, dots, rests and octave changes at T150 (no < >: ERR 5)
60 A$="T150O4C4.D8E2R4O3GO4C1":W=193:GOSUB 500:LPRINT "CP 2";W;OK
70 REM 3: a phrase kept in a variable and played twice with X, notes by number
80 P$="CEG":A$="T120L16XP$;XP$;N60N64N67":W=57:GOSUB 500:LPRINT "CP 3";W;OK
90 REM 4: three voices, and PLAY(n) for each while they run
100 TIME=0:PLAY "T120L4CDEF","T120L2EG","T120L1C"
110 S1=PLAY(1):S2=PLAY(2):S3=PLAY(3)
120 IF PLAY(0) THEN 120
130 LPRINT "CP 4";ABS(TIME-104)<5;S1;S2;S3;PLAY(1);PLAY(2);PLAY(3)
140 REM 5: tempo and length from variables (=n;), volume and envelope
150 T=120:L=8:V=12:A$="T=T;L=L;V=V;CDEC":W=50:GOSUB 500:LPRINT "CP 5";W;OK
160 A$="S8M2000L4CDE":W=77:GOSUB 500:LPRINT "CP 6";W;OK
170 REM 6: an ON INTERVAL clock running while a tune plays
180 N=0:ON INTERVAL=10 GOSUB 700:INTERVAL ON
190 A$="T120O4L4CEGO5C":W=102:GOSUB 500:INTERVAL OFF:LPRINT "CP 7";W;OK;N\4
200 REM 7: a drum hit with SOUND on the noise channel, half a second by the clock
210 SOUND 6,15:SOUND 7,&B10110111:SOUND 8,16:SOUND 12,8:SOUND 13,0:TIME=0
220 IF TIME<25 THEN 220
230 SOUND 8,0:SOUND 7,&B10111000:LPRINT "CP 8 DRUM";TIME\5
240 REM 8: a song table in DATA, each line one bar at T120, PLAYed one after another --
241 REM they queue (D-PLAYQUEUE: here they replaced each other, and only the last bar played)
250 RESTORE 800:TIME=0:FOR B=1 TO 4:READ M$:PLAY "T120O4"+M$:NEXT
260 IF PLAY(0) THEN 260
270 LPRINT "CP 9";ABS(TIME-395)<7;LEN(M$)
280 BEEP:LPRINT "CP 10 END":END
500 TIME=0:PLAY A$
510 IF PLAY(0) THEN 510
520 OK=ABS(TIME-W)<5:RETURN
700 N=N+1:RETURN
800 DATA "L8EDCDEEE4","L8DDD4EGG4","L8EDCDEEEE","L8DDEDC2"
