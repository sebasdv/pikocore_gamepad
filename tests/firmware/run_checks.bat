@echo off
rem Host checks for the firmware's pure logic (doth/ headers), with MSVC.
rem Run from anywhere; each check_*.c is compiled and run, exit 1 on the
rem first failure. From Git Bash:  cmd //c "$(cygpath -w tests/firmware/run_checks.bat)"
rem goto and not "|| exit /b 1": inside a for block under cmd /c, the latter
rem stops the loop but the process still exits 0.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d %~dp0
for %%f in (check_*.c) do (
  cl /nologo /W4 /WX /std:c11 /I..\..\doth %%f /Fe:"%TEMP%\%%~nf.exe" /Fo:"%TEMP%\%%~nf.obj" || goto :fail
  "%TEMP%\%%~nf.exe" || goto :fail
  echo %%~nf OK
)
exit /b 0
:fail
echo FAILED
exit /b 1
