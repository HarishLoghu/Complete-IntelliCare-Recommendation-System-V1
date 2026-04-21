@echo off
setlocal
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%venv\Scripts\python.exe"
set "VENV_STREAMLIT=%ROOT%venv\Scripts\streamlit.exe"
set "BACKEND_PY=python"
set "STREAMLIT_CMD=streamlit"

if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import flask" >nul 2>&1
    if not errorlevel 1 (
        set "BACKEND_PY=""%VENV_PY%"""
    )
)

if exist "%VENV_STREAMLIT%" (
    "%VENV_PY%" -c "import streamlit" >nul 2>&1
    if not errorlevel 1 (
        set "STREAMLIT_CMD=""%VENV_STREAMLIT%"""
    )
)

echo Starting IntelliCare Backend Server...
start "Backend" cmd /k "cd /d ""%ROOT%backend"" && set PYTHONUNBUFFERED=1 && %BACKEND_PY% app.py || echo Python backend crashed! && pause"

echo Starting IntelliCare Frontend...
start "Frontend" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"

echo Starting Medicine Verifier...
start "Medicine Verifier" cmd /k "cd /d ""%ROOT%backend"" && %STREAMLIT_CMD% run medicine_verifier.py || echo Streamlit crashed! && pause"

echo All services are starting. Check the open terminal windows.
