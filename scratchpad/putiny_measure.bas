10 REM PRINT USING with values far below the field's last digit
20 FOR K=1 TO 300:NEXT
30 DATA -3.38081D-15,3.38081D-15,1D-6,4D-6,5D-6,6D-6,1.23D-10,-5D-7,5.5D-6,-6D-6
40 FOR I=1 TO 10:READ D#:LPRINT USING "A +#.##### B ##.### C ###.#";D#;D#;D#:NEXT
50 S!=3.4E-15:LPRINT USING "D +#.##### ##.##";S!;S!
60 S!=-4E-7:LPRINT USING "E +#.##### ##.######";S!;S!
70 LPRINT USING "F #.#";1D-20;1D-60;-1D-60
80 LPRINT "G";COS(4*ATN(1#)/2)
