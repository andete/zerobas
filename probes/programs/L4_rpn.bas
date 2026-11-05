10 REM ** RPN CALCULATOR - a tokenizer, a value stack, trapped faults **
20 REM each DATA line is evaluated as reverse Polish; faults are trapped and the
30 REM line is skipped with RESUME 300, the way a user's calculator would recover
40 CLS:DIM S(20):DEFINT I-N:ON ERROR GOTO 800
50 L=0
60 READ E$:IF E$="END" THEN 700
70 L=L+1:SP=0:P=1:E$=E$+" "
80 Q=INSTR(P,E$," "):IF Q=0 THEN 250
90 T$=MID$(E$,P,Q-P):P=Q+1:IF T$="" THEN 80
100 K=INSTR("+-*/^NQ",T$):IF LEN(T$)>1 THEN K=0
110 IF K=0 THEN SP=SP+1:S(SP)=VAL(T$):GOTO 80
120 ON K GOTO 130,140,150,160,170,180,190
130 S(SP-1)=S(SP-1)+S(SP):SP=SP-1:GOTO 80
140 S(SP-1)=S(SP-1)-S(SP):SP=SP-1:GOTO 80
150 S(SP-1)=S(SP-1)*S(SP):SP=SP-1:GOTO 80
160 S(SP-1)=S(SP-1)/S(SP):SP=SP-1:GOTO 80
170 S(SP-1)=S(SP-1)^S(SP):SP=SP-1:GOTO 80
180 S(SP)=-S(SP):GOTO 80
190 S(SP)=SQR(S(SP)):GOTO 80
250 IF SP<>1 THEN LPRINT "CP";L;"STACK";SP:GOTO 60
260 LPRINT "CP";L;:LPRINT USING "########.####";S(1):PRINT E$;"=";S(1):GOTO 60
300 LPRINT "CP";L;"SKIPPED":GOTO 60
700 LPRINT "CP END";L;FRE(0)>0:END
800 LPRINT "CP";L;"ERR";ERR;"AT";ERL:RESUME 300
900 DATA "3 4 +","5 1 2 + 4 * + 3 -","2 3 ^ 2 /","1 0 /","9 Q 3 *"
910 DATA "1E30 1E30 * 1E30 *","2 N 3 ^","1 2 3","12.5 .5 - 4 *","16 Q Q N"
920 DATA "100 3 / 3 *","7 2 ^ 1 -","END"
