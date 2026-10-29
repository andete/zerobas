10 REM PRINT USING fixed format: negative values that PRINT shows in E form
20 FOR K=1 TO 300:NEXT
30 X#=-2.5D+17:Y!=-1E+15:LPRINT USING "A ####### B ##.##";X#;Y!
40 LPRINT X#;Y!:LPRINT USING "C +####";X#:LPRINT USING "D ####-";X#
50 Z#=1D+14:LPRINT USING "E ####";Z#:LPRINT Z#
60 LPRINT USING "F **####.## $$####";1D+16;-1D+16
