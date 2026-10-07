1000 'BEGIN & INLEZEN GEGEVENS
1010 DEFINT A-Z:DIMA$(121):MSX=PEEK(0)=243
1020 SCREEN 0,0:COLOR 15,4,4
1030 LOCATE,,0:PVV=939:AA$=CHR$(27)+CHR$(76):HS=0
1040 LOCATE 15,10:PRINT"MOMENT":SC=0
1050 RESTORE 2510
1060 FOR A=1 TO 120
1070  READ A$(A)
1080 NEXT A
1090 RESTORE 1130
1100 FOR A=3568-256*MSX TO 2703-256*MSX
1110  READ B$:VPOKE A,VAL("&h"+B$)
1120 NEXT A
1130 DATA 00,74,fc,fc,fc,44,0c,04;'a
1140 DATA 00,b8,fc,fc,fc,88,c0,80;'b
1150 DATA 00,00,70,88,80,88,70,00:'c
1160 DATA 30,78,fc,fc,fc,fc,78,30:'d
1170 DATA 00,00,70,88,f8,80,70,00:'e
1180 DATA 00,40,e0,f0,f8,fc,7c,30:'f
1190 DATA 30,7c,fc,f8,f0,e0,40,00:'g
1200 DATA 00,08,1c,3c,7c,fc,f8,30:'h
1210 DATA 30,f8,fc,7c,3c,1c,08,00:'i
1220 DATA 18,3c,8c,7c,3c,1c,0c,04:'j
1230 DATA 00,08,1c,3c,3c,1c,08,00:'k
1240 DATA fc,fc,fc,cc,cc,fc,fc,fc:'l
1250 DATA cc,cc,cc,cc,cc,cc,cc,cc:'m
1260 DATA fc,fc,fc,00,00,fc,fc,fc:'n
1270 DATA 00,00,70,88,88,88,70,00:'o
1280 DATA 00,40,e0,f0,f0,e0,40,00:'p
1290 DATA 60,f0,f8,f8,f0,e0,c0,80:/q
1300 :
1310 'BEGIN EIGENLIJKE SPEL
1320 CLS:WIDTH 40:COLOR,4
1330 ON STOP GOSUB 1280:STOP ON
1340 PRINT"m   V L E E R M U I S   m SCOREL000000 m"
1350 PRINT"lnnnnnnnnnnnnnnnnnnnnnnnlnnnnnnnnnnnnnnl"
1360 LOCATE 0,2:PRINT AA$;
1370 FOR A=3 TO 23
1380  PRINT"m                                      m"
1390 NEXT A
1400 :
1410 'INSTRUCTIESCHERM
1420 IF SC>HS THEN HS=SC
1430 FOR A=21 TO 1 STEP -1
1440  LOCATE 0,2:PRINT AA$;
1450  PRINT A$(A);
1460 NEXT A
1470 SC$=RIGHT$(STR$(SC),LEN(STR$(SC))-1)
1480 LOCATE 27-LEN(SC$),20
1490 PRINT SC$
1500 HS$=RIGHT$(STR$(HS),LEN(STR$(HS))-1)
1510 LOCATE 27-LEN(HS$),21
1520 PRINT HS$
1530 :
1540 'WACHTEN OP INVOER
1550 FOR A=1 TO 5
1560  KEY (A) ON
1570 NEXT A
1580 ON KEY GOSUC 1620,1630,1640,1650,2460,1590,1590,1590,1590
1590 GOTO 1590
1600 :
1610 'VIA F-TOETEN SNELHEID BEPAALD
1620 SNEL=45:RETURN 1680
1630 SNEL=30:RETURN 1680
1640 SNEL=15:RETURN 1680
1650 SNEL=0: RETURN 1680
1660 :
1670 'BEGIN SPELSCHERM
1680 FOR A=1 TO 5: KEY(A) OFF: NEXT
1690 SC=0:LV=5:SV=SN
1700 FOR A=1 TO 21
1710  LOCATE 0,2:PRINT AA$;
1720  PRINT"m                                      m";
1730 NEXT A
1740 :
1750 'SPELROUTINE
1760 COLOR,4
1770 FOR C=1 TO 14
1780  FOR A=22 TO 120
1790   FOR AA=0 TO SNEL:NEXT
1800   LOCATE 0,2:PRINT AA$;
1810   PRINT A$(A);
1820   GOTO 1950
1830   VPOKE PVV,65+32*MSX:VPOKE PVV+1,66+32*MSX
1840   SC=SC+1
1850   SC$=RIGHT$(STR$(SC),LEN(STR$(SC))-1)
1860   LOCATE 38-LEN(SC$),0
1870   PRINT SC$
1880  NEXT
1890  COLOR,C
1900 NEXT C
1910 SNEL=SNEL-10:IF SNEL<0 THEN SNEL=0
1920 GOTO 1770
1930 ;
1940 'INVOER JOYSTICK AFHANDELEN
1950 JOY=STICK(0) OR STICK(1)
1960 ON JOY GOTO 2030,2030,1980,2030,2030,2030,2000,2030
1970 GOTO 2030
1980 PVV=PVV+1:IF PVV>957 THEN PVV=957
1990 GOTO 2030
2000 PVV=PVV-1:IF PVV<921 THEN PVV=921
2010 :
2020 'TEGEN ROTS OP GEBOTST ?
2030 VL=VPEEK(PVV)-32*MSX:VR=VPEEK(PVV+1)-32*MSX
2040 IF VL=74 THEN 2430
2050 IF (VL=81) AND (VR=0) THEN 2430
2060 IF VR=81 THEN 2430
2070 IF (VR=74) AND (VL=0) THEN 2430
2080 IF (VL= 0) AND (VR=0) THEN 1830
2090 ;
2100 'ZO JA DAN KNAL EN LEVEN MINDER
2110 SOUND 7,&B110111:SOUND 6,31
2120 SOUND 8,16:SOUND 11,0:SOUND 12,30
2130 SOUND 13,0
2140 LV=LV-1:IF LV=0 THEN 2260
2150 LOCATE 13, 9
2160 PRINT"lnnnnnnnnnnnl"
2170 LOCATE 13,10
2180 PRINT"m  OPGELET  m"
2190 LOCATE 13,11
2200 PRINT"lnnnnnnnnnnnl"
2210 FOR A=1 TO 1000: NEXT
2220 SN=SV:PVV=939
2230 GOTO 1700
2240 :
2250 'GEEN LEVENS MEER -> SPEL STOPT
2260 LOCATE 12, 9
2270 PRINT"lnnnnnnnnnnnnnl":FOR AA=1 TO 200
2280 LOCATE 12,10
2290 PRINT"m  GAME OVER  m":FOR AA=1 TO 200
2300 LOCATE 12,11
2310 PRINT"lnnnnnnnnnnnnnl":FOR AA=1 TO 200
2320 FOR A=1 TO 20
2330  FOR AA=1 TO 15
2340   COLOR AA
2350  NEXT
2360 NEXT
2370 FOR A=1 TO 1000:NEXT A
2380 IF SC>HS THEN HS=SC
2390 PVV=939
2400 GOTO 1310
2410 :
2420 'HARTJE OPGEHAALD
2430 SOUND 7,&B111000: SOUND 6,0: SOUND 8.16
2440 SOUND 1,1: SOUND 13,4
2450 SC=SC+20:GOTO 1830
2460 :
2470 'EINDE
2480 SCREEN 0,0: COLOR 15,4,5: LOCATE,,1
2490 WIDTH 39: END
2500 :
2510 DATA "m                                      m"
2520 DATA "m                                      m"
2530 DATA "m   F1 : LANGZAAM                      m"
2540 DATA "m                     VLEERMUIS ab     m"
2550 DATA "m   F2 : SNEL                          m"
2560 DATA "m                     ROTSBLOK  d      m"
2570 DATA "m   F3 : SNELLER                       m"
2580 DATA "m                     HARTJE    jq     m"
2590 DATA "m   F3 : SNELST                        m"
2600 DATA "m                                      m"
2610 DATA "m                                      m"
2620 DATA "m   F5 : STOPPEN                       m"
2630 DATA "m                                      m"
2640 DATA "m                                      m"
2650 DATA "m   VLIEG DOOR DE GROT EN HAAL HARTJES m"
2670 DATA "m   OP.VLIEG VOORAL NIET TEGEN ROTS-   m"
2680 DATA "m   BLOKKEN OP. SUCCES .               m"
2680 DATA "m                                      m"
2690 DATA "m    LAATSTE SCORE : 000000            m"
2700 DATA "m         HI-SCORE : 000000            m"
2710 DATA "m                                      m"
2720 DATA "mdg                                  idm"
2730 DATA "mdddg                              idddm"
2740 DATA "mdddddg                          idddddm"
2750 DATA "mdddddddg                      idddddddm"
2760 DATA "mdddddddf                      hdddddddm"
2770 DATA "mddddddf   ig              ig   hddddddm"
2780 DATA "mdddddf   idddg          idddg   hdddddm"
2790 DATA "mddddf   iddddddp      kddddddg   hddddm"
2800 DATA "mddddg   hdddddf        hdddddf   iddddm"
2810 DATA "mdddddg   hdddf    ig    hdddf   idddddm"
2820 DATA "mddddddg   hdf    iddg    hdf   iddddddm"
2830 DATA "mddddddf   if    iddddg    hg   hddddddm"
2840 DATA "mdddddf   if    kddddddp    hg   hdddddm"
2850 DATA "mdddddg          hddddf          idddddm"
2860 DATA "mddddddg          hddf          iddddddm"
2870 DATA "mdddddddg jq hg jq hd jq hg jq kdddddddm"
2880 DATA "mddddddddg    hg    hg    hg    hddddddm"
2890 DATA "mdddddddddg    hg    hg    hg    hdddddm"
2900 DATA "mddddddddddg    hg    hg    hg    hddddm"
2910 DATA "mdddddddddddp    dp    dp    dp    ddddm"
2920 DATA "mddddddddddf    if    if    if    iddddm"
2930 DATA "mdddddddddf    if    if    if    idddddm"
2940 DATA "mddddddddf    if    if    if    iddddddm"
2950 DATA "mdddddddd    if    id    if    idddddddm"
2960 DATA "mddddddddg        iddg        iddddddddm"
2970 DATA "mdddddddddg      iddddg      idddddddddm"
2980 DATA "mddddddddddg    iddddddg    iddddddddddm"
2990 DATA "mdddddddddddpjqkddddddddpjqkdddddddddddm"
3000 DATA "mddddddddddf    hddddddf    hddddddddddm"
3010 DATA "mdddddddddf      hddddf      hdddddddddm"
3020 DATA "mddddddddf   hg   hddf   if   hddddddddm"
3030 DATA "mdddddddf     hg   hf   if     hdddddddm"
3040 DATA "mddddddd       hg      if      ddddddddm"
3050 DATA "mddddddf   if   dp    kd   hg   hddddddm"
3060 DATA "mdddddf   if   if      hg   hg   hdddddm"
3070 DATA "mddddf   id   id   hg   hg   hg   hddddm"
3080 DATA "mdddf   iddg   hg   hg   hg   hg   hdddm"
3090 DATA "mddf   iddddg   hg   hg   hg   hg   hddm"
3100 DATA "mdd                                  ddm"
3110 DATA "mdd                                  ddm"
3120 DATA "mdd                                  ddm"
3130 DATA "mdd     jq     jq     jq     jq      ddm"
3140 DATA "mddg jq    jq     jq     jq     jq  iddm"
3150 DATA "mdddg    hg   hg   hg   hg   hg    kdddm"
3160 DATA "mddddg    hg   hg   hg   hg   hg    hddm"
3170 DATA "mdddddg    hg   hg   hg   hg   hg    hdm"
3180 DATA "mddddddp    dp   dp   dp   dp   dp    dm"
3190 DATA "mdddddf    if   if   if   if   if    idm"
3200 DATA "mddddd    kd   kd   kd   kd   kd    kddm"
3210 DATA "mdddddg    hg   hg   hg   hg   hg    hdm"
3220 DATA "mddddddg    hg   hg   hg   hg   hg    dm"
3230 DATA "mdddsdddp    dp   dp   dp   dp   dp   dm"
3240 DATA "mdsddddf    if   if   if   if   if    dm"
3250 DATA "mdddddf    if   if   if   if   if    idm"
3260 DATA "mddddf    if   if   if   if   if    iddm"
3270 DATA "mdddf    if   if   if   if   if    idddm"
3280 DATA "mddf    if   if   if   if   if    iddddm"
3290 DATA "mdf    if   if   if   if   if    idddddm"
3300 DATA "md    kd   kd   kd   kd   kd    kddddddm"
3310 DATA "mdgjq  hgjq hgjq hgjq hgjq hgjq  hdddddm"
3320 DATA "mddg    hg   hg   hg   hg   hg    hddddm"
3330 DATA "mdddp    hg   hg   hg   hg   hg    hdddm"
3340 DATA "mddf                                hddm"
3350 DATA "mdf                                  hdm"
3360 DATA "md jq        jq          jq        jq dm"
3370 DATA "mdg          ig          ig          idm"
3380 DATA "mddg        iddg        iddg        iddm"
3390 DATA "mdddg      iddddg      iddddg      idddm"
3400 DATA "mddddg    iddddddg    iddddddg    iddddm"
3410 DATA "mdddddgjqiddddddddpjqkddddddddpjqkdddddm"
3420 DATA "mddddf    hddddddf    hddddddf    hddddm"
3430 DATA "mdddf      hddddf      hddddf      hdddm"
3440 DATA "mddf   ig   hddf   ig   hddf   ig   hddm"
3450 DATA "mdd   kddp   hf   kddp   hf   kddp   ddm"
3460 DATA "mddg   hf          hf          hf   iddm"
3470 DATA "mdddp     jq    jq    jq    jq     kdddm"
3480 DATA "mddf   ig          ig          ig   hddm"
3490 DATA "mdd   kddp   ig   kddp   ig   kddp   ddm"
3500 DATA "mddg   hf   iddg   hf   iddg   hf   iddm"
3510 DATA "mdddg      iddddg      iddddg      idddm"
3520 DATA "mddddg    iddddddg    iddddddg    iddddm"
3530 DATA "mdddddpjqkddddddddpjqkddddddddpjqldddddm"
3540 DATA "mddddf    hddddddf    hddddddf    hddddm"
3550 DATA "mdddf      hddddf      hddddf      hdddm"
3560 DATA "mddf        hddf        hddf        hddm"
3570 DATA "mdf          hf          hf          hdm"
3580 DATA "md                                    dm"
3590 DATA "mdg jq hg jq hg jq hg jq hg jq kdddddddm"
3600 DATA "mddg    hg    hg    hg    hg    hddddddm"
3610 DATA "mdddg    hg    hg    hg    hg    hdddddm"
3620 DATA "mddddp    hg    hg    hg    hg    dddddm"
3630 DATA "mdddf    if    if    if    if    idddddm"
3640 DATA "mddf    if    if    if    if    iddddddm"
3650 DATA "mdf    if    if    if    if    kdddddddm"
3660 DATA "md jq iddjq iddjq iddjq iddjq   iddddddm"
3670 DATA "mdp jq B  jq O  jq N  jq U  jq S idddddm"
3680 DATA "md   jq    jq    jq    jq    jq   iddddm"
3690 DATA "mdp   jq    jq    jq    jq    jq   idddm"
3700 DATA "md     jq    jq    jq    jq    jq   iddm"
3710 DATA "mdg     jq    jq    jq    jq    jq   idm"
3720 END
