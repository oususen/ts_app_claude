@echo off
echo ========================================
echo MySQL版シミュレーション実行
echo ========================================
echo.

REM 仮想環境をアクティベート
call venv\Scripts\activate.bat

REM Pythonスクリプトを実行
python test_simulation_mysql.py

echo.
echo ========================================
echo 完了
echo ========================================
pause
