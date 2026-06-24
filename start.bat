@echo off
echo Starting Streamlit App...
echo Open browser: http://localhost:8501
echo Press Ctrl+C to stop
echo.

cd /d e:\swagent
python -m streamlit run frontend/simple_app.py --server.port 8501

pause
