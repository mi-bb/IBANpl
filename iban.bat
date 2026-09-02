@echo off
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python -O iban.py %*
) else (
    echo Could not find Python interpreter.
    pause
)
