@echo off
REM Double-click this to start Job Copilot and open it in your browser.
REM No terminal typing needed. Close the black window to stop the server.
cd /d "%~dp0"

curl -s -o nul http://127.0.0.1:8765/ 2>nul
if %errorlevel%==0 (
    echo Job Copilot is already running - opening it in your browser.
    start http://127.0.0.1:8765/
    goto :eof
)

if not exist config.toml (
    copy config.example.toml config.toml >nul
    echo First run: created config.toml from the example.
    echo Edit it to add your own job boards, then re-run this.
)

echo Installing/checking dependencies ^(only slow the first time^)...
pip install -q -r requirements.txt

echo Starting Job Copilot...
start "Job Copilot server" /min cmd /c python run.py serve

set tries=0
:waitloop
timeout /t 1 /nobreak >nul
set /a tries+=1
curl -s -o nul http://127.0.0.1:8765/ 2>nul
if not %errorlevel%==0 if %tries% lss 40 goto waitloop

start http://127.0.0.1:8765/
echo.
echo Job Copilot is running at http://127.0.0.1:8765
echo It's running in a separate "Job Copilot server" window - close that
echo window (or use Task Manager) to stop it.
pause
