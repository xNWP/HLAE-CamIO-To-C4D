@ECHO OFF
ECHO Deleting existing archives...
DEL /P *.7z *.zip
ECHO Done.

SET sevzip="C:\Program Files\7-Zip\7z.exe"
SET filelist=hlaecamio2c4d INSTALLATION.txt

SET /P versionMajor="Major Version: "
SET /P versionMinor="Minor Version: "
SET archName="HLAE-CamIO-To-C4D_%versionMajor%_%versionMinor%"

%sevzip% a -t7z %archName%.7z %filelist%
%sevzip% a -tzip %archName%.zip %filelist%

ECHO.
ECHO Packaged.