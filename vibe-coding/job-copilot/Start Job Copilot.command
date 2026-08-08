#!/bin/bash
# Double-click this in Finder to start Job Copilot and open it in your browser.
# No terminal typing needed. Close this window to stop the server.
set -e
cd "$(dirname "$0")"

# Already running from an earlier double-click? Just open it, don't start a
# second copy (which would fail on the port anyway).
if curl -s -o /dev/null http://127.0.0.1:8765/; then
    echo "Job Copilot is already running — opening it in your browser."
    open http://127.0.0.1:8765/
    exit 0
fi

if [ ! -f config.toml ]; then
    cp config.example.toml config.toml
    echo "First run: created config.toml from the example."
    echo "Edit it to add your own job boards, then re-run this."
fi

echo "Installing/checking dependencies (only slow the first time)..."
pip3 install -q -r requirements.txt

echo "Starting Job Copilot..."
python3 run.py serve &
SERVER_PID=$!

# Wait for it to come up, then open the browser automatically.
for i in $(seq 1 40); do
    sleep 0.3
    if curl -s -o /dev/null http://127.0.0.1:8765/; then
        open http://127.0.0.1:8765/
        break
    fi
done

echo ""
echo "Job Copilot is running at http://127.0.0.1:8765"
echo "Close this window (or press Ctrl+C) to stop it."
wait $SERVER_PID
