10 REM ** C4 - PROJECT EULER 16 25 48 92 39, ALL SCALED DOWN (SAID AT EACH) **
20 KEY OFF:CLS:DEFINT I-N:DEFDBL A-H,O-Z:DIM W(20),U(20),V(20),M%(250),C%(120)
30 REM P16 for 2^100 (not 2^1000): its digit sum, by doubling base-10000 limbs
40 FOR I=1 TO 20:W(I)=0:NEXT:W(1)=1:NL=1
50 FOR K=1 TO 100:CY=0:FOR I=1 TO NL:V0=W(I)*2+CY:CY=INT(V0/10000):W(I)=V0-CY*10000:NEXT:IF CY THEN NL=NL+1:W(NL)=CY
60 NEXT:S=0:FOR I=1 TO NL:V0=W(I):FOR J=1 TO 4:S=S+V0-INT(V0/10)*10:V0=INT(V0/10):NEXT J,I:LPRINT "P16<2^100>";S
70 REM P25 for 50 digits (not 1000): the index of the first Fibonacci term that long
80 FOR I=1 TO 20:U(I)=0:V(I)=0:NEXT:U(1)=1:V(1)=1:NL=1:N=2
90 N=N+1:CY=0:FOR I=1 TO NL:T=U(I)+V(I)+CY:CY=INT(T/10000):U(I)=V(I):V(I)=T-CY*10000:NEXT:IF CY THEN NL=NL+1:U(NL)=0:V(NL)=CY
100 D=(NL-1)*4+LEN(STR$(V(NL)))-1:IF D<50 THEN 90
110 LPRINT "P25<50 digits>";N
120 REM P48 for 1..100, last 5 digits (not 1..1000, 10): sum of n^n, products in doubles
130 S=0:FOR N=1 TO 100:R=1:B=N:E=N
140 IF E-INT(E/2)*2=1 THEN R=R*B:R=R-INT(R/100000#)*100000#
150 B=B*B:B=B-INT(B/100000#)*100000#:E=INT(E/2):IF E>0 THEN 140
160 S=S+R:S=S-INT(S/100000#)*100000#:NEXT:LPRINT "P48<100>";S
170 REM P92 below 1000 (not 10000000): square-digit chains that arrive at 89, memoised
180 FOR I=1 TO 250:M%(I)=0:NEXT:M%(1)=1:M%(89)=89:C=0
190 FOR N=1 TO 999:K=N:GOSUB 500:IF K>243 THEN 210 ELSE J=K
200 IF M%(J)=0 THEN K=J:GOSUB 500:J=K:GOTO 200
210 IF M%(J)=89 THEN C=C+1
220 IF N<=243 THEN M%(N)=M%(J)
230 NEXT:LPRINT "P92<1000>";C
240 REM P39 for p <= 120 (not 1000): the perimeter with the most right triangles, by
245 REM Euclid's formula: m>n, coprime, m-n odd, perimeter 2m(m+n), and its multiples
250 FOR M=2 TO 7:FOR N=1 TO M-1:IF (M-N) MOD 2=0 THEN 258
252 I=M:J=N
254 IF J THEN K=I MOD J:I=J:J=K:GOTO 254
256 L=2*M*(M+N):IF I=1 AND L<=120 THEN FOR K=L TO 120 STEP L:C%(K)=C%(K)+1:NEXT K
257 REM (the L<=120 test matters: a FOR body runs once even when L is past 120)
258 NEXT N,M:BP=0:BC=0:FOR K=1 TO 120:IF C%(K)>BC THEN BC=C%(K):BP=K
270 NEXT:LPRINT "P39<120>";BP;BC
280 LPRINT "CP 9 END":END
500 REM K = the sum of the squares of K's digits
510 T=0
520 T=T+(K MOD 10)^2:K=K\10:IF K THEN 520
530 K=T:RETURN
