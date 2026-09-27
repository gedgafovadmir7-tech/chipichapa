@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Ustanavlivayu duckdb...
python -m pip install --quiet --disable-pip-version-check duckdb
echo.
python filter_snapshots.py
if errorlevel 1 (
  echo.
  echo OSHIBKA. Sdelay skrin etogo okna i otprav Claude.
) else (
  echo.
  echo GOTOVO. Sdelay skrin etogo okna i otprav Claude vmeste s failom snapshots_filtered.parquet
)
pause
