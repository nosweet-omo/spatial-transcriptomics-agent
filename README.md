# 空间转录组智能分析平台

## Spatial Transcriptomics Intelligent Analysis Platform

一个基于LangGraph的空间转录组数据分析Agent，支持.h5ad格式数据的完整分析流程。

---

## 🚀 在线演示

**👉 [点击访问Agent智能前端](https://spatial-transcriptomics-agent-gesd97k4pterpeyl5sutcw.streamlit.app/)**

无需安装，直接在浏览器中体验完整功能！

---

## 项目架构

本项目采用四层分离架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    前端交互层 (Streamlit)                      │
│  • 多模态输入 (自然语言 + 交互式配置)                           │
│  • 富文本结果渲染 (图表 + 解释文案)                             │
│  • 文件上传/下载                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Agent编排层 (LangGraph Core)                  │
│  • State: AgentState (全局状态管理)                            │
│  • Nodes: Planner → Executor → Reviewer → Error Handler      │
│  • Edges: 条件分支 + 错误重试Loop                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              生信计算引擎 (Scanpy/Squidpy)                    │
│  • 基础模块: DataLoader, QC, Preprocessing, Clustering        │
│  • 可视化模块: SpatialViz, MarkerAnalysis                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 数据与持久化层                                 │
│  • 文件管理: uploads/, cache/, results/                       │
│  • 结果库: plots/, reports/, exports/                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 功能特性

### ✅ 已完成功能

| 模块 | 功能 | 说明 |
|------|------|------|
| **数据读取** | .h5ad文件加载 | 支持Stereo-seq等空间转录组数据 |
| **质量控制** | QC分析 | 细胞/基因过滤、线粒体过滤、QC图表 |
| **数据预处理** | 标准流程 | 归一化、log转换、HVG筛选、PCA |
| **降维聚类** | 聚类分析 | UMAP可视化、Leiden/Louvain聚类 |
| **空间可视化** | 空间分布图 | 2D/3D细胞分布、聚类分布、基因表达 |
| **Marker基因** | 差异分析 | 热图、点图、小提琴图、排名图 |
| **Agent层** | 智能分析 | 自然语言驱动、自动规划、错误处理 |
| **前端界面** | 交互式分析 | Streamlit界面、参数调整、结果展示 |

### 🎯 Agent能力

- **Planner**: 理解用户意图，生成执行计划
- **Executor**: 自动选择和执行工具
- **ResultChecker**: 检查结果质量
- **Reviewer**: 生成易懂的分析报告
- **ErrorHandler**: 错误处理和恢复
- **Skill系统**: 6个预定义分析流程

---

## 安装与运行

### 环境要求

- Python >= 3.9
- pip

### 安装步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd swagent
```

2. **创建虚拟环境（推荐）**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置LLM API（可选）**
```bash
# 创建.env文件
cp .env.example .env

# 编辑.env文件，添加API密钥
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 运行方式

#### 方式1: Streamlit前端（推荐）

启动后选择进入Agent智能前端或手动操作前端：

```bash
python -m streamlit run streamlit_app.py
```

**🤖 Agent智能前端**：自然语言输入、Skill选择、自动规划、智能问答

**🔬 手动操作前端**：标签页逐步操作、高级参数可调、透明可控

两个版本共享同一套生信计算引擎，分析结果一致。

#### 方式2: Agent命令行演示

```bash
# 自动演示模式
PYTHONIOENCODING=utf-8 python run_agent_demo.py --auto

# 交互式模式
PYTHONIOENCODING=utf-8 python run_agent_demo.py
```

#### 方式3: 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行引擎测试
python tests/test_engine.py

# 运行真实数据测试
python tests/test_real_data.py
```

---

## 使用示例

### 示例1: 完整分析流程

```python
from agent.graph import run_agent

result = run_agent(
    user_input="帮我分析这个空间转录组数据，进行完整的分析流程",
    file_path="examples/sample_data/GSM9046243_Embryo_E7.5_stereo_rep1.h5ad",
    skill_name="basic_analysis_workflow"
)

print(f"分析完成，生成 {len(result['plot_files'])} 个图表")
```

### 示例2: 快速预览

```python
from agent.graph import run_agent

result = run_agent(
    user_input="快速预览这个数据",
    file_path="examples/sample_data/GSM9046243_Embryo_E7.5_stereo_rep1.h5ad",
    skill_name="quick_preview_skill"
)
```

### 示例3: 使用预定义Skill

```python
from agent.skills import list_skills, get_skill

# 列出所有可用的Skill
skills = list_skills()
print(skills)

# 获取特定Skill的详情
qc_skill = get_skill("quality_control_skill")
print(qc_skill)
```

---

## 项目结构

```
swagent/
├── engine/                          # 生信计算引擎
│   ├── __init__.py
│   ├── data_loader.py               # 数据读取与概览
│   ├── qc.py                        # 质量控制
│   ├── preprocessing.py             # 数据预处理
│   ├── clustering.py                # 降维聚类
│   ├── spatial_viz.py               # 空间可视化
│   ├── marker.py                    # Marker基因分析
│   └── utils.py                     # 工具函数
│
├── agent/                           # Agent编排层
│   ├── __init__.py
│   ├── state.py                     # AgentState定义
│   ├── shared_state.py              # 共享状态（线程安全）
│   ├── tools.py                     # 19个LangChain Tool
│   ├── skills.py                    # 6个预定义Skill
│   ├── prompts.py                   # Prompt模板
│   ├── graph.py                     # LangGraph工作流图
│   └── nodes/                       # 节点实现
│       ├── __init__.py
│       ├── planner.py               # 任务规划节点
│       ├── executor.py              # 工具调用节点
│       ├── reviewer.py              # 结果审查节点
│       └── error_handler.py         # 异常处理节点
│
├── frontend/                        # 前端交互层
│   ├── __init__.py
│   ├── app.py                       # Agent智能前端（LangGraph + Skill + 自然语言）
│   ├── simple_app.py                # 手动操作前端（标签页逐步操作）
│   ├── components.py                # UI组件
│   ├── chat.py                      # LLM对话模块
│   └── utils.py                     # 工具函数
│
├── tests/                           # 测试
│   ├── test_agent.py                # Agent层测试（29个用例）
│   ├── test_engine.py               # 引擎层测试
│   └── test_real_data.py            # 真实数据测试
│
├── examples/                        # 示例数据
│   └── sample_data/                 # 6个.h5ad示例文件
│
├── run_agent_demo.py                # Agent交互演示
├── run_full_pipeline.py             # 完整流程脚本
├── requirements.txt                 # 依赖配置
├── config.py                        # 配置文件
├── .env                             # 环境变量（LLM API配置）
└── README.md                        # 本文件
```

---

## 示例数据

项目包含6个.h5ad格式的空间转录组数据文件：

| 文件名 | 说明 | 大小 |
|--------|------|------|
| GSM9046243_Embryo_E7.5_stereo_rep1.h5ad | 小鼠E7.5期胚胎 | 195MB |
| GSM9046244_Embryo_E7.5_stereo_rep2.h5ad | 小鼠E7.5期胚胎 | 31MB |
| GSM9046245_Embryo_E7.75_stereo_rep1.h5ad | 小鼠E7.75期胚胎 | 344MB |
| GSM9046246_Embryo_E7.75_stereo_rep2.h5ad | 小鼠E7.75期胚胎 | 93MB |
| GSM9046247_Embryo_E8.0_stereo_rep1.h5ad | 小鼠E8.0期胚胎 | 36MB |
| GSM9046248_Embryo_E8.0_stereo_rep2.h5ad | 小鼠E8.0期胚胎 | 103MB |

数据来源: Digital reconstruction of full embryos during early mouse organogenesis
- DOI: https://doi.org/10.1016/j.cell.2025.05.035
- GEO: GSE278603

---

## 技术栈

- **AI Agent**: LangGraph, LangChain
- **生信分析**: Scanpy, AnnData
- **前端**: Streamlit
- **可视化**: Matplotlib, Seaborn

---

## 开发计划

### ✅ Sprint 1: 底层基建
- [x] 生信工具库封装
- [x] 测试脚本

### ✅ Sprint 2: Agent大脑构建
- [x] LangGraph核心图
- [x] State定义
- [x] Node实现（Planner/Executor/Reviewer/ErrorHandler）
- [x] Edge和循环控制
- [x] Tool和Skill系统

### ✅ Sprint 3: 前端交互与整合
- [x] Streamlit界面（Agent智能版 + 手动操作版）
- [x] 文件上传
- [x] 结果展示
- [x] 参数调整

### ✅ Sprint 4: 质量优化
- [x] 错误处理优化（P1-P4）
- [x] 线程安全
- [x] 超时保护
- [x] 数据验证

---

## 许可证

MIT License

---

## 联系方式

如有问题，请提交Issue或联系项目维护者。
