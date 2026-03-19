@echo off
echo Starting IntelliCare Backend Server...
start "Backend" cmd /k "cd backend & set PYTHONUNBUFFERED=1 & venv\Scripts\python.exe app.py || echo Python backend crashed! & pause"

echo Starting IntelliCare Frontend...
start "Frontend" cmd /k "cd frontend & npm run dev"

echo Both services are starting! Check the open terminal windows.
