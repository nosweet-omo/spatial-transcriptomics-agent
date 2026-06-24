@echo off
echo ========================================
echo   空间转录组智能分析平台 - 启动脚本
echo ========================================
echo.
echo 正在启动应用...
echo 请在浏览器中访问: http://localhost:8501
echo 按 Ctrl+C 停止应用
echo.

cd /d e:\swagent
python start_app.py

pause
