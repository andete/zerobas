10 REM putiny-acceptance: PRINT USING fixed fields with values PRINT shows in E form
20 FOR K=1 TO 300:NEXT
30 DATA -3.38081D-15,5D-6,4D-6,-6D-6,1.23D-10
40 FOR I=1 TO 5:READ D#:LPRINT USING "A +#.##### B ##.### C ###.#";D#;D#;D#:NEXT
50 S!=3.4E-15:LPRINT USING "D +#.##### ##.##";S!;S!:LPRINT USING "F #.#";1D-20;1D-60
60 LPRINT USING "G #######.###";5D-4;4.9999D-4;-5D-4
70 LPRINT USING "H **#.## $$#.## +#.##";-1D-9;-1D-9;-1D-9
80 LPRINT USING "I ####### J ##.##";1D+15;-2.5D+17
90 LPRINT USING "K +#### L ####- M **####.## N $$####";-2.5D+17;-2.5D+17;1D+16;-1D+16
100 LPRINT USING "O ################ P";1.2345678901234D+15
110 LPRINT USING "Q ####";1D+14
