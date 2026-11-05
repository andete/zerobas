10 REM ** TEXT FORMATTER - wrap, justify, count words **
20 REM a paragraph from DATA is wrapped at a width, right-justified with
30 REM spaces, title-cased in place with MID$=, and its words counted and sorted
35 ON ERROR GOTO 900
40 CLEAR 1000:CLS:W=28:T$=""
50 READ L$:IF L$<>"*" THEN T$=T$+L$+" ":GOTO 50
60 DATA "the quick brown fox jumps over the lazy dog while"
70 DATA "the cat sleeps on a warm mat and the dog barks at"
80 DATA "the moon until the sun comes up over the hill","*"
90 LPRINT "CP 1";LEN(T$);INSTR(T$,"dog");INSTR(20,T$,"dog");INSTR(T$,"cow")
100 REM title case: MID$ assignment on the first letter of every word
110 U$=T$:MID$(U$,1,1)=CHR$(ASC(U$)-32)
120 P=INSTR(U$," ")
130 IF P=0 OR P>=LEN(U$) THEN 150 ELSE C=ASC(MID$(U$,P+1,1)):IF C>=97 AND C<=122 THEN MID$(U$,P+1)=CHR$(C-32)
140 P=INSTR(P+1,U$," "):GOTO 130
150 LPRINT "CP 2 ";LEFT$(U$,30)
160 REM wrap at W, then pad each line to W by widening gaps from the left
170 S=1:NL=0
180 IF S>LEN(T$) THEN 300
190 E=S+W:IF E>LEN(T$) THEN E=LEN(T$)+1:GOTO 220
200 IF MID$(T$,E,1)=" " THEN 220
210 E=E-1:IF E>S THEN 200
220 L$=MID$(T$,S,E-S):S=E+1
230 IF RIGHT$(L$,1)=" " THEN L$=LEFT$(L$,LEN(L$)-1):GOTO 230
240 G=W-LEN(L$):Q=1
250 IF G>0 THEN Q=INSTR(Q,L$," "):IF Q>0 THEN L$=LEFT$(L$,Q)+" "+MID$(L$,Q+1):G=G-1:Q=Q+2:GOTO 250 ELSE Q=1:IF INSTR(L$," ")>0 THEN 250
260 NL=NL+1:PRINT L$:LPRINT "CP 3";NL;LEN(L$);"|";L$;"|"
270 GOTO 180
300 REM words: split, count distinct, sort
310 DIM WD$(60),WC(60):NW=0:P=1
320 Q=INSTR(P,T$," "):IF Q=0 THEN 400
330 X$=MID$(T$,P,Q-P):P=Q+1:IF X$="" THEN 320
340 FOR I=1 TO NW:IF WD$(I)=X$ THEN WC(I)=WC(I)+1:GOTO 320
350 NEXT I:NW=NW+1:WD$(NW)=X$:WC(NW)=1:GOTO 320
400 FOR I=1 TO NW-1:FOR J=I+1 TO NW
410 IF WC(J)>WC(I) OR (WC(J)=WC(I) AND WD$(J)<WD$(I)) THEN SWAP WD$(I),WD$(J):SWAP WC(I),WC(J)
420 NEXT J,I
430 LPRINT "CP 4";NW;"DISTINCT"
440 FOR I=1 TO 5:LPRINT "CP 5 ";WD$(I);WC(I);STRING$(WC(I),"*");SPACE$(8-LEN(WD$(I)));"|":NEXT
450 LPRINT "CP 6 ";HEX$(NW*37);" ";OCT$(NW*37);" ";BIN$(NW);VAL(" 1 2 3");STR$(-NW);FRE("")>0
460 PRINT "DONE":END
900 LPRINT "CP E";ERR;ERL:RESUME NEXT
