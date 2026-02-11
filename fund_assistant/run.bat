@echo off
echo Starting Fund Assistant...

:: Check if .venv exists in current or parent directory
if exist "..\.venv\Scripts\python.exe" (
    set PYTHON_EXE=..\.venv\Scripts\python.exe
    set STREAMLIT_EXE=..\.venv\Scripts\streamlit.exe
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    set STREAMLIT_EXE=.venv\Scripts\streamlit.exe
) else (
    set PYTHON_EXE=python
    set STREAMLIT_EXE=streamlit
)

echo Using Python: %PYTHON_EXE%

echo Installing dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt

echo Starting Streamlit App...
"%PYTHON_EXE%" -m streamlit run app.py

pause
