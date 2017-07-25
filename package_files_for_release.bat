ECHO OFF
CLS

DEL /P *.7z *.zip
CLS

SET "sevzip="C:\Program Files\7-Zip\7z.exe""
SET "version=v1"
SET "filelist=hlaecamio2c4d INSTALLATION.txt"

%sevzip% a -t7z HLAE_CAMIO_2_C4D_Cam_%version%.7z %filelist%
%sevzip% a -tzip HLAE_CAMIO_2_C4D_Cam_%version%.zip %filelist%

ECHO.
ECHO Packaged.
PAUSE > nul