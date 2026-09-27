@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install --quiet --disable-pip-version-check duckdb
python make_dataset.py
if errorlevel 1 (
  echo.
  echo OSHIBKA. Sdelay skrin etogo okna i otprav Claude.
) else (
  echo.
  echo GOTOVO. Sdelay skrin etogo okna i otprav Claude.
)
pause
