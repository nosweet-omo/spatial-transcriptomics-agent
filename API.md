# API 接口文档

## 目录

- [Agent层 API](#agent层-api)
- [Engine层 API](#engine层-api)
- [工具函数 API](#工具函数-api)
- [Skill系统 API](#skill系统-api)

---

## Agent层 API

### run_agent

```python
def run_agent(
    user_input: str,
    file_path: str = None,
    output_dir: str = "",
    params: dict = None,
    skill_name: str = None
) -> dict:
```

**功能**: 运行Agent进行空间转录组数据分析

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| user_input | str | 是 | 用户的自然语言请求 |
| file_path | str | 否 | 数据文件路径（.h5ad格式） |
| output_dir | str | 否 | 输出目录 |
| params | dict | 否 | 分析参数 |
| skill_name | str | 否 | 预定义Skill名称 |

**返回值**: dict
```python
{
    "current_step": "completed",      # 当前状态
    "completed_steps": [...],         # 已完成步骤列表
    "plan": [...],                    # 执行计划
    "results": {...},                 # 各步骤结果
    "plot_files": [...],              # 生成的图表文件路径
    "summary": "...",                 # 分析摘要
    "messages": [...]                 # 对话历史
}
```

**示例**:
```python
from agent.graph import run_agent

# 完整分析
result = run_agent(
    user_input="帮我分析这个空间转录组数据",
    file_path="examples/sample_data/GSM9046243_Embryo_E7.5_stereo_rep1.h5ad"
)

# 使用预定义Skill
result = run_agent(
    user_input="快速预览数据",
    file_path="data.h5ad",
    skill_name="quick_preview_skill"
)
```

---

## Engine层 API

### 数据读取

#### load_h5ad

```python
def load_h5ad(file_path: str) -> AnnData:
```

**功能**: 加载.h5ad格式的空间转录组数据

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| file_path | str | h5ad文件路径 |

**返回值**: AnnData对象

---

#### get_data_summary

```python
def get_data_summary(adata: AnnData) -> dict:
```

**功能**: 获取数据概览信息

**返回值**:
```python
{
    "n_cells": 13168,
    "n_genes": 17172,
    "n_genes_stats": {"mean": 634.9, "median": 603.0, ...},
    "n_counts_stats": {"mean": 591.1, "median": 456.0, ...},
    "has_spatial": True,
    "spatial_key": "spatial"
}
```

---

#### validate_data

```python
def validate_data(adata: AnnData) -> dict:
```

**功能**: 验证数据有效性

**返回值**:
```python
{
    "is_valid": True,
    "warnings": ["..."],
    "errors": []
}
```

---

### 质量控制

#### run_qc_pipeline

```python
def run_qc_pipeline(
    adata: AnnData,
    params: dict = None
) -> dict:
```

**功能**: 运行完整的QC流程

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| adata | AnnData | 输入数据 |
| params | dict | QC参数 |

**params字段**:
```python
{
    "min_genes": 200,        # 最少基因数
    "min_cells": 3,          # 最少细胞数
    "max_pct_mito": 20.0     # 最大线粒体比例(%)
}
```

**返回值**:
```python
{
    "status": "success",
    "summary": {
        "n_cells": 13168,
        "n_genes": 15486,
        ...
    },
    "plot_files": ["qc_violin.png", "qc_scatter.png", ...]
}
```

---

### 数据预处理

#### run_preprocessing_pipeline

```python
def run_preprocessing_pipeline(
    adata: AnnData,
    params: dict = None
) -> dict:
```

**功能**: 运行完整的预处理流程

**params字段**:
```python
{
    "n_top_genes": 2000,     # 高变基因数量
    "n_pcs": 50,             # PCA主成分数
    "target_sum": 1e4        # 归一化目标总和
}
```

**返回值**:
```python
{
    "status": "success",
    "n_hvg": 2000,
    "n_pcs": 50,
    "plot_files": ["preprocessing_hvg.png", ...]
}
```

---

#### 单步预处理函数

```python
def normalize_data(adata: AnnData, target_sum: float = 1e4) -> AnnData
def log_transform(adata: AnnData) -> AnnData
def select_hvg(adata: AnnData, n_top_genes: int = 2000) -> AnnData
def standardize_data(adata: AnnData, n_pcs: int = 50) -> AnnData
```

---

### 降维聚类

#### run_clustering

```python
def run_clustering(
    adata: AnnData,
    method: str = "leiden",
    resolution: float = 1.0
) -> AnnData:
```

**功能**: 执行聚类分析

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| method | str | 聚类方法 ("leiden" 或 "louvain") |
| resolution | float | 聚类分辨率 |

---

#### run_umap

```python
def run_umap(adata: AnnData) -> AnnData:
```

**功能**: 计算UMAP降维

---

#### run_pca

```python
def run_pca(adata: AnnData, n_pcs: int = 50) -> AnnData:
```

**功能**: 计算PCA降维

---

### 空间可视化

#### plot_spatial_distribution

```python
def plot_spatial_distribution(
    adata: AnnData,
    output_dir: str,
    color: str = None,
    size: float = 1.0,
    use_3d: bool = True
) -> str:
```

**功能**: 绘制细胞空间分布图

**返回值**: 生成的图表文件路径

---

#### plot_cluster_spatial

```python
def plot_cluster_spatial(
    adata: AnnData,
    output_dir: str,
    cluster_key: str = "leiden",
    size: float = 3.0,
    use_3d: bool = True
) -> str:
```

**功能**: 绘制聚类空间分布图

---

#### plot_gene_spatial

```python
def plot_gene_spatial(
    adata: AnnData,
    gene: str,
    output_dir: str,
    size: float = 3.0,
    use_raw: bool = False,
    use_3d: bool = True
) -> str:
```

**功能**: 绘制基因空间表达图

---

#### plot_embedding

```python
def plot_embedding(
    adata: AnnData,
    basis: str = "umap",
    output_dir: str = "",
    color: str = None,
    size: float = 1.0
) -> str:
```

**功能**: 绘制降维图（UMAP/PCA/t-SNE）

---

### Marker基因分析

#### find_marker_genes

```python
def find_marker_genes(
    adata: AnnData,
    cluster_key: str = "leiden",
    method: str = "wilcoxon",
    n_genes: int = 100,
    use_raw: bool = True
) -> AnnData:
```

**功能**: 鉴定Marker基因

---

#### get_top_markers

```python
def get_top_markers(
    adata: AnnData,
    cluster_key: str = "leiden",
    n_genes: int = 10
) -> dict:
```

**功能**: 获取每个聚类的Top Marker基因

**返回值**:
```python
{
    "0": ["T", "Nkx1-2", "Grsf1", ...],
    "1": ["Gene2", "Gene3", ...],
    ...
}
```

---

#### 绘图函数

```python
def plot_marker_heatmap(adata, cluster_key, n_markers, output_dir) -> str
def plot_marker_dotplot(adata, cluster_key, n_markers, output_dir) -> str
def plot_marker_violin(adata, genes, cluster_key, output_dir) -> str
def plot_marker_rank_genes(adata, cluster_key, n_genes, output_dir) -> str
```

---

## 工具函数 API

Agent层工具函数定义在 `agent/tools.py` 中，封装了Engine层函数供Agent调用。

### 数据工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| load_data | 加载h5ad文件 | file_path |
| get_data_info | 获取数据概览 | 无 |

### QC工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| run_qc | 运行QC分析 | min_genes, min_cells, max_pct_mito |
| calculate_qc | 计算QC指标 | 无 |

### 预处理工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| run_preprocessing | 运行预处理 | n_top_genes, n_pcs |
| normalize | 归一化 | target_sum |
| log_transform | log转换 | 无 |
| select_highly_variable_genes | 筛选HVG | n_top_genes |
| standardize | 标准化 | n_pcs |

### 聚类工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| run_clustering_analysis | 运行聚类 | method, resolution |
| reduce_dimensionality | 降维 | n_pcs |
| cluster | 聚类 | method, resolution |

### 可视化工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| generate_spatial_plots | 生成空间图 | use_3d |
| plot_umap | 绘制UMAP | color |
| plot_gene_expression | 绘制基因表达 | gene |

### Marker工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| find_markers | 鉴定Marker | cluster_key, method |
| get_markers | 获取Marker | cluster_key, n_genes |
| plot_markers | 绘制Marker图 | cluster_key |

---

## Skill系统 API

### 预定义Skill

| Skill名称 | 功能 | 步骤数 |
|-----------|------|--------|
| basic_analysis_workflow | 完整分析流程 | 6 |
| quality_control_skill | 质量控制分析 | 3 |
| gene_spatial_analysis_skill | 基因空间分析 | 4 |
| cluster_annotation_skill | 聚类注释 | 3 |
| dimensionality_reduction_skill | 降维分析 | 3 |
| quick_preview_skill | 快速预览 | 4 |

### Skill函数

```python
def list_skills() -> list:
    """列出所有可用的Skill"""

def get_skill(skill_name: str) -> Skill:
    """获取指定Skill的详情"""

def parse_skill_from_natural_language(text: str) -> str:
    """从自然语言中解析匹配的Skill"""

def skill_to_plan(skill: Skill, params: dict = None) -> list:
    """将Skill转换为执行计划"""
```

### Skill数据结构

```python
@dataclass
class SkillStep:
    tool_name: str           # 工具名称
    description: str         # 步骤描述
    params: dict = None      # 参数

@dataclass
class Skill:
    name: str                # Skill名称
    description: str         # 描述
    steps: List[SkillStep]   # 步骤列表
    keywords: List[str]      # 匹配关键词
```

---

## 配置参数

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| LLM_API_KEY | LLM API密钥 | 无 |
| LLM_BASE_URL | LLM API地址 | https://api.openai.com/v1 |
| LLM_MODEL | LLM模型名称 | gpt-4 |

### 分析参数

```python
params = {
    "run_qc": {
        "min_genes": 200,
        "min_cells": 3,
        "max_pct_mito": 20.0
    },
    "run_preprocessing": {
        "n_top_genes": 2000,
        "n_pcs": 50
    },
    "run_clustering_analysis": {
        "method": "leiden",
        "resolution": 1.0
    },
    "generate_spatial_plots": {
        "use_3d": True
    }
}
```

---

## 错误处理

### 错误类型

| 错误类型 | 处理方式 | 说明 |
|----------|----------|------|
| FileNotFoundError | 终止 | 数据文件不存在 |
| MemoryError | 跳过 | 内存不足 |
| ValueError | 重试 | 参数错误 |
| KeyError | 跳过 | 数据列不存在 |
| 权限错误 | 终止 | 无法访问文件 |
| 超时错误 | 重试 | 操作超时 |

### 错误响应格式

```python
{
    "status": "error",
    "error": "错误描述信息"
}
```
