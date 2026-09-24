@echo off
cd /d "d:\Projects\freedom_blocker"

echo ===================================================
echo Starting Freedom Blocker Apps...
echo ===================================================

echo Starting Commercial Freedom App...
start "" "C:\Program Files (x86)\Freedom\FreedomBlocker.exe"

echo Starting Custom Freedom Blocker App...
start "" "d:\Projects\freedom_blocker\dist\FreedomBlocker_v15.exe" --hidden

echo ===================================================
echo Both applications launched successfully!
echo ===================================================
timeout /t 3
