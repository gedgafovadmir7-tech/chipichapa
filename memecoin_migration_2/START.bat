@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Ustanavlivayu duckdb...
python -m pip install --quiet duckdb
echo.
python filter_snapshots.py
echo.
echo Gotovo. Skopiruy vsyo, chto napisano vyshe, i otprav Claude.
pause
