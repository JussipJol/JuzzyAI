@echo off
echo [1/3] Installing dependencies...
pip install pyinstaller rich

echo [2/3] Building juzzyai.exe...
pyinstaller --onefile --name juzzyai --icon=NONE ^
    --add-data "commands;commands" ^
    --add-data "core;core" ^
    --add-data "utils;utils" ^
    main.py

if not exist "dist\juzzyai.exe" (
    echo ERROR: Build failed.
    exit /b 1
)

echo [3/3] Building installer...
makensis installer.nsi

if exist "JuzzyAI-Setup.exe" (
    echo.
    echo Done! JuzzyAI-Setup.exe is ready.
) else (
    echo ERROR: makensis failed. Make sure NSIS is installed: https://nsis.sourceforge.io
)
