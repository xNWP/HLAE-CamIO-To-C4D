ECHO OFF
cls

SET "ProjDir="C:\xCode\HLAE_CamIO_To_C4D_Cam""
SET "PluginFolder=hlaecamio2c4d"
SET "Cinema4DPluginDir="C:\Program Files\MAXON\CINEMA 4D R17\plugins\%PluginFolder%""

CD %ProjDir%

RMDIR /S /Q %Cinema4DPluginDir%

MKDIR %Cinema4DPluginDir%
cls

XCOPY /S %PluginFolder% %Cinema4DPluginDir%

ECHO.
ECHO Plugin Pushed.
pause > nul