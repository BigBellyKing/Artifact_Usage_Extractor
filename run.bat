@echo off
TITLE Genshin Artifact Manager

:: 1. Verify the virtual environment actually exists
IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Are you running this script from the correct folder?
    pause
    exit /b
)

echo Launching Genshin Artifact Manager...

:: 2. Execute the app using the isolated Python environment
".venv\Scripts\python.exe" App.py

:: 3. Keep the window open ONLY if the app crashes
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The application crashed. Read the traceback above to debug.
    pause
)