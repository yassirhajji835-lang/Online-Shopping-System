@echo off
cd /d "%~dp0"
echo Opening Online Shopping System...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Install Python and check your internet connection.
  pause
  exit /b 1
)
python app.py
pause
