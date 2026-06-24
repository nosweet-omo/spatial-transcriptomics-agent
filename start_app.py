"""
启动Streamlit应用的脚本
"""
import subprocess
import sys
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(current_dir, "frontend", "app.py")

print(f"正在启动应用: {app_path}")
print("请在浏览器中访问: http://localhost:8501")
print("按 Ctrl+C 停止应用")
print("="*50)

# 启动Streamlit
subprocess.run([
    sys.executable, "-m", "streamlit", "run", app_path,
    "--server.headless", "true",
    "--server.port", "8501"
])
