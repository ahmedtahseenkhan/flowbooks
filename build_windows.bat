@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  FlowBooks – Windows .exe build script
REM  Produces dist\FlowBooks.exe (one-file, no console window).
REM ─────────────────────────────────────────────────────────────────────────────

setlocal
cd /d "%~dp0"

set PY=.venv\Scripts\python.exe
if not exist "%PY%" (
    echo [build] Python venv not found at %PY%
    echo [build] Create one with:  python -m venv .venv
    exit /b 1
)

echo [build] Cleaning previous artifacts...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
if exist FlowBooks.spec del /q FlowBooks.spec

echo [build] Running PyInstaller...
"%PY%" -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name FlowBooks ^
    --paths app ^
    --paths . ^
    --collect-submodules forms ^
    --collect-submodules licensing ^
    app\main.py

if errorlevel 1 (
    echo [build] PyInstaller failed.
    exit /b 1
)

echo.
echo [build] Done. Executable: dist\FlowBooks.exe
endlocal
