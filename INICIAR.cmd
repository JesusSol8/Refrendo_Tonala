@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 bootstrap.py
  goto fin
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" bootstrap.py
  goto fin
)
python bootstrap.py
:fin
if errorlevel 1 echo No se pudo iniciar. Revisa el mensaje anterior y consulta README.md.
pause
