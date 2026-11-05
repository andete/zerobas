10 REM ** PARTS LIST - records in parallel arrays, sorted, a column report **
20 CLS:DIM N$(20),Q%(20),P!(20):C=0
30 READ A$:IF A$="*" THEN 60
40 C=C+1:N$(C)=A$:READ Q%(C),P!(C):GOTO 30
50 DATA "BOLT M6",120,.15,"NUT M6",200,.05,"WASHER",500,.02,"HINGE",12,2.4
55 DATA "SPRING",40,.75,"AXLE",8,6.5,"BEARING",16,3.99,"CLAMP",30,1.2,"*"
60 LPRINT "CP 1";C;FRE(0)>0
70 REM insertion sort by name
80 FOR I=2 TO C:K$=N$(I):KQ%=Q%(I):KP!=P!(I):J=I-1
90 IF J>=1 THEN IF N$(J)>K$ THEN N$(J+1)=N$(J):Q%(J+1)=Q%(J):P!(J+1)=P!(J):J=J-1:GOTO 90
100 N$(J+1)=K$:Q%(J+1)=KQ%:P!(J+1)=KP!:NEXT I
110 T=0:FOR I=1 TO C:V=Q%(I)*P!(I):T=T+V
120 LPRINT USING "CP 2 \        \ #### ###.## ####.##";N$(I);Q%(I);P!(I);V:NEXT I
130 LPRINT USING "CP 3 TOTAL ######.##";T
140 REM delete every part worth under 10, compact the arrays
150 D=0:FOR I=1 TO C:IF Q%(I)*P!(I)<10 THEN D=D+1 ELSE N$(I-D)=N$(I):Q%(I-D)=Q%(I):P!(I-D)=P!(I)
160 NEXT I:C=C-D:LPRINT "CP 4";C;D
170 FOR I=1 TO C:LPRINT "CP 5 ";LEFT$(N$(I)+SPACE$(10),10);"|";RIGHT$("    "+STR$(Q%(I)),5):NEXT I
180 M$="":FOR I=1 TO C:M$=M$+LEFT$(N$(I),1):NEXT:LPRINT "CP 6 ";M$;" ";INSTR(M$,"H");ASC(M$)
190 END
