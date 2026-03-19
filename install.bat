@echo off
echo Installing Backend Requirements...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

echo.
echo Training Dummy Models for Local Run...
python train_dummy_models.py

echo.
echo Installing Frontend Requirements...
cd ../frontend
npm install axios lucide-react
npm install

echo.
echo Installation Complete! You can now run the app by clicking 'start.bat'
pause
