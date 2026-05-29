@echo off
cd /d "%~dp0"
start "" "http://localhost:8765/choice_practice_demo.html"
python app_server.py --port 8765
pause
