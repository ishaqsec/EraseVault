@echo off
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0EraseVault.pyw" %*
) else (
    start "" /B python "%~dp0main.py" %*
)
exit
