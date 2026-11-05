10 REM D-CONCAT3: the least free string space T$=T$+L$+" " needs (T$ 51, L$ 50 from DATA)
20 CLEAR 700:DEFINT I-N:READ L$,M$:ON ERROR GOTO 200
30 FOR K=60 TO 400
40 A$="":B$="":C$="":T$="":Q=FRE(""):N=Q-K-51
50 IF N>255 THEN A$=SPACE$(255):N=N-255
60 IF N>255 THEN B$=SPACE$(255):N=N-255
70 C$=SPACE$(N):T$=L$+" ":F=FRE("")
80 T$=T$+L$+" ":LPRINT "A";K;F;LEN(T$):GOTO 120
90 NEXT K
100 LPRINT "A none":GOTO 120
120 FOR K=60 TO 400
130 A$="":B$="":C$="":T$="":Q=FRE(""):N=Q-K-51
140 IF N>255 THEN A$=SPACE$(255):N=N-255
150 IF N>255 THEN B$=SPACE$(255):N=N-255
160 C$=SPACE$(N):T$=L$+" ":F=FRE("")
170 T$=T$+M$:LPRINT "B";K;F;LEN(T$):END
180 NEXT K:LPRINT "B none":END
200 IF ERL<120 THEN RESUME 90 ELSE RESUME 180
300 DATA "the quick brown fox jumps over the lazy dog while","the cat sleeps on a warm mat and the dog barks at"
