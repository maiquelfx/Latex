@echo off
set msg=inicio das verificacoes
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm-ss"') do set dt=%%i

C:\msys64\usr\bin\bash.exe -lc "cd /home/Win/git/latex/latex/IC-UFF && git add . && git commit -m '%msg% %dt%' && git push"

pause