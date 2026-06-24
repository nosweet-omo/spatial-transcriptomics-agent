# 快速开始指南

## 🚀 在线演示（推荐）

**👉 [点击访问在线演示](https://spatial-transcriptomics-agent-6l5dgpweekkappxkbv4cvd2.streamlit.app/)**

无需安装，直接在浏览器中体验完整功能！

---

## 1. 本地环境准备

### 安装Python依赖

```bash
pip install -r requirements.txt
```

### 配置LLM API（可选，用于智能对话功能）

创建 `.env` 文件：

```bash
# .env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

---

## 2. 获取示例数据

项目使用 Stereo-seq 空间转录组数据：

**数据来源**: Digital reconstruction of full embryos during early mouse organogenesis
- GEO: GSE278603
- DOI: https://doi.org/10.1016/j.cell.2025.05.035

**下载地址**:
```bash
# 使用wget下载（示例）
wget https://ftp.ncbi.nlm.nih.gov/geo/series/GSE278nnn/GSE278603/suppl/GSE278603_Embryo_E7.5_stereo_rep1.h5ad.gz
gunzip GSE278603_Embryo_E7.5_stereo_rep1.h5ad.gz
```

或从Google Drive手动下载后放入 `examples/sample_data/` 目录。

---

## 3. 运行方式

### 方式1: Agent自动分析（推荐）

```bash
# 自动演示
PYTHONIOENCODING=utf-8 python run_agent_demo.py --auto

# 交互式
PYTHONIOENCODING=utf-8 python run_agent_demo.py
```

### 方式2: Streamlit前端

```bash
python -m streamlit run frontend/simple_app.py
```

浏览器访问: http://localhost:8501

### 方式3: 运行测试

```bash
python -m pytest tests/ -v
```

---

## 4. 项目结构

```
swagent/
├── engine/              # 生信计算引擎
├── agent/               # Agent编排层 (LangGraph)
├── frontend/            # 前端界面 (Streamlit)
├── tests/               # 测试 (61个用例)
├── examples/            # 示例数据
├── requirements.txt     # 依赖
├── README.md           # 说明文档
└── API.md              # API文档
```

---

## 5. 常见问题

**Q: 运行测试报错?**
A: 确保已安装所有依赖: `pip install -r requirements.txt`

**Q: Streamlit无法启动?**
A: 检查端口是否被占用: `netstat -ano | grep 8501`

**Q: LLM对话不工作?**
A: 需要配置 `.env` 文件中的 `LLM_API_KEY`

---

## 6. 联系方式

如有问题，请提交GitHub Issue。
