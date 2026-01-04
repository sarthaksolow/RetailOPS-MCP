@echo off
echo ========================================
echo Installing RetailOps Client Dependencies
echo ========================================
echo.

cd client
pip install -r requirements.txt

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next step: Run test_client.py
pause
