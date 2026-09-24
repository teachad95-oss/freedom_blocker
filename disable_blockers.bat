@echo off
:: Ensure we run in the correct directory
cd /d "d:\Projects\freedom_blocker"

echo ===================================================
echo Disabling and Cleaning Blocker Apps...
echo ===================================================

:: Run python cleanup script (now that shell is elevated, this runs directly)
"C:\Users\ARISE\.conda\envs\freedom_app\python.exe" stop_and_clean_blocker.py

:: Remove startup registry keys (doing HKCU from here just in case)
echo Deleting startup registry keys...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Freedom /f
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v FreedomBlocker /f

:: Double check process killing
echo Ensuring all blocker processes are terminated...
taskkill /f /im FreedomBlocker.exe 2>nul
taskkill /f /im FreedomBlocker_v15.exe 2>nul
taskkill /f /im FreedomProxy.exe 2>nul

echo ===================================================
echo Blocker apps have been disabled successfully!
echo ===================================================
pause
