@echo off
cd /d %~dp0
call venv\Scripts\activate
python -m streamlit run calendar_app.py
pause