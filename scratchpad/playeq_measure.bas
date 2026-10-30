10 REM PLAY =var; : which commands take it, how a fraction rounds, the errors
20 FOR K=1 TO 300:NEXT:ON ERROR GOTO 900
30 I%=4:A!=8.4:B!=8.6:C#=8.5:D!=7.5:N=-1:S$="X":E%=255:F!=65535:G!=65536
40 DATA "T=I%;","V=I%;","N=I%;","O=I%;","L=I%;","S=I%;","M=I%;","R=I%;","C=I%;","C#=I%;"
50 DATA "O=A!;","O=B!;","O=C#;","O=D!;","V=N;","V=S$;","V=I%","V=ZZ;","V=I% ;","V= I%;"
60 DATA "M=E%;","M=F!;","M=G!;","N=A!;","L=B!;","T=1E2;","V=I%(1);","O=A;","XS$;","V=(I%);"
70 FOR R=1 TO 30:READ P$:E=0:PLAY P$:LPRINT USING "## \          \ ";R;P$;:LPRINT E;PLAY(0):NEXT
80 FOR I=1 TO 2000:NEXT:LPRINT "Z END":END
900 E=ERR:RESUME NEXT
