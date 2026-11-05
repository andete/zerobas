10 REM D-CONCAT3: the least free string space each chain needs, per case (T$ 50, L$ 49, M$ 49)
20 CLEAR 700:DEFINT I-N:READ L$,M$:ON ERROR GOTO 300
30 FOR C=1 TO 6:FOR K=40 TO 420 STEP 2
40 A$="":B$="":C$="":T$="":Q=FRE(""):N=Q-K-51
50 IF N>255 THEN A$=SPACE$(255):N=N-255
60 IF N>255 THEN B$=SPACE$(255):N=N-255
70 C$=SPACE$(N):T$=L$+" ":F=FRE("")
80 IF C=1 THEN T$=T$+L$+M$+" ":GOTO 95
81 IF C=2 THEN T$=LEFT$(L$,40)+M$+" ":GOTO 95
82 IF C=3 THEN T$=T$+MID$(L$,1,30)+" ":GOTO 95
83 IF C=4 THEN T$=" "+T$+" ":GOTO 95
84 IF C=5 THEN X=LEN(T$+L$+M$):GOTO 96
85 T$=T$+L$
95 X=LEN(T$)
96 LPRINT C;K;F;X:GOTO 200
190 NEXT K:LPRINT C;"none"
200 NEXT C:END
300 RESUME 190
400 DATA "the quick brown fox jumps over the lazy dog while","the cat sleeps on a warm mat and the dog barks at"
