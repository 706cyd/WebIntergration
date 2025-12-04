@echo off
cd /d "D:\BUAA\Lab\Digital twin\Codes\PocknetCNC_TWIN"
start python run_server.py
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000"