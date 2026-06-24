# 启动指南

## 快速启动

### 方法1：双击批处理文件
直接双击 `start_app.bat` 文件

### 方法2：命令行启动

打开Windows命令提示符(CMD)或PowerShell，运行：

```bash
cd e:\swagent
python start_app.py
```

### 方法3：直接运行Streamlit

```bash
cd e:\swagent
streamlit run frontend/app.py
```

## 启动后

1. 浏览器会自动打开 **http://localhost:8501**
2. 如果没有自动打开，请手动在浏览器中访问该地址

## 使用流程

1. **上传数据**：在左侧边栏点击"选择文件"上传.h5ad格式数据
2. **调整参数**（可选）：展开参数面板调整分析参数
3. **选择流程**（可选）：选择预定义的分析流程
4. **输入请求**：在主界面输入自然语言分析请求
5. **运行分析**：点击"运行分析"按钮
6. **查看结果**：在下方查看生成的图表和分析摘要

## 示例请求

- "帮我分析这个空间转录组数据"
- "进行质量控制和聚类分析"
- "分析Marker基因"
- "生成空间可视化图表"

## 注意事项

1. 首次启动可能需要较长时间加载
2. 确保已安装所有依赖：`pip install -r requirements.txt`
3. 如果遇到端口占用错误，可以尝试更换端口：
   ```bash
   streamlit run frontend/app.py --server.port 8502
   ```

## 停止应用

在命令行窗口中按 `Ctrl+C` 停止应用
