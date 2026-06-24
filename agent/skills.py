"""
Skill/Workflow封装模块

将多个工具组合成可复用的分析能力模块。
每个Skill包含一系列有序的步骤，可以作为一个整体执行。
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SkillStep:
    """Skill中的单个步骤"""
    name: str                    # 步骤名称
    tool_name: str               # 调用的工具名
    description: str             # 步骤描述
    params: Dict[str, Any]       # 参数
    required: bool = True        # 是否必须执行
    skip_on_error: bool = False  # 出错时是否跳过


@dataclass
class Skill:
    """可复用的分析能力模块"""
    name: str                    # Skill名称
    description: str             # Skill描述
    steps: List[SkillStep]       # 执行步骤
    prerequisites: List[str]     # 前置条件（需要先完成的步骤）
    output_description: str      # 输出描述


# ============ 预定义的Skill/Workflow ============

# 1. 基础分析流程（完整流程）
BASIC_ANALYSIS_WORKFLOW = Skill(
    name="basic_analysis_workflow",
    description="空间转录组基础分析完整流程，包含从数据加载到可视化的所有步骤",
    steps=[
        SkillStep(
            name="load_data",
            tool_name="load_data",
            description="加载h5ad格式的空间转录组数据",
            params={},
            required=True
        ),
        SkillStep(
            name="quality_control",
            tool_name="run_qc",
            description="质量控制，过滤低质量细胞和基因",
            params={"min_genes": 200, "min_cells": 3, "max_pct_mito": 20.0},
            required=True
        ),
        SkillStep(
            name="preprocessing",
            tool_name="run_preprocessing",
            description="数据预处理：归一化、log转换、HVG筛选、PCA",
            params={"n_top_genes": 2000, "n_pcs": 50},
            required=True
        ),
        SkillStep(
            name="clustering",
            tool_name="run_clustering_analysis",
            description="降维聚类分析：UMAP + Leiden聚类",
            params={"method": "leiden", "resolution": 1.0},
            required=True
        ),
        SkillStep(
            name="marker_analysis",
            tool_name="find_markers",
            description="Marker基因分析，鉴定各cluster的特征基因",
            params={"n_markers": 10},
            required=True
        ),
        SkillStep(
            name="spatial_visualization",
            tool_name="generate_spatial_plots",
            description="生成空间可视化图表",
            params={"use_3d": True},
            required=True
        ),
    ],
    prerequisites=[],
    output_description="完整的分析结果，包括QC报告、聚类结果、Marker基因列表和空间可视化图表"
)

# 2. 质量控制分析Skill
QUALITY_CONTROL_SKILL = Skill(
    name="quality_control_skill",
    description="专注于数据质量控制的分析流程",
    steps=[
        SkillStep(
            name="load_data",
            tool_name="load_data",
            description="加载数据",
            params={},
            required=True
        ),
        SkillStep(
            name="calculate_qc_metrics",
            tool_name="calculate_qc",
            description="计算QC指标",
            params={},
            required=True
        ),
        SkillStep(
            name="run_qc",
            tool_name="run_qc",
            description="执行质量控制过滤",
            params={"min_genes": 200, "min_cells": 3, "max_pct_mito": 20.0},
            required=True
        ),
        SkillStep(
            name="get_summary",
            tool_name="get_analysis_summary",
            description="获取QC结果摘要",
            params={},
            required=True
        ),
    ],
    prerequisites=[],
    output_description="质量控制报告，包括过滤前后的细胞/基因数量统计"
)

# 3. 基因空间表达分析Skill
GENE_SPATIAL_ANALYSIS_SKILL = Skill(
    name="gene_spatial_analysis_skill",
    description="专注于基因在空间上表达模式的分析",
    steps=[
        SkillStep(
            name="load_data",
            tool_name="load_data",
            description="加载数据",
            params={},
            required=True
        ),
        SkillStep(
            name="preprocessing",
            tool_name="run_preprocessing",
            description="数据预处理",
            params={"n_top_genes": 2000},
            required=True
        ),
        SkillStep(
            name="spatial_plots",
            tool_name="generate_spatial_plots",
            description="生成基因空间表达图",
            params={"use_3d": True},
            required=True
        ),
    ],
    prerequisites=[],
    output_description="基因空间表达可视化图表"
)

# 4. 聚类结果解释Skill
CLUSTER_ANNOTATION_SKILL = Skill(
    name="cluster_annotation_skill",
    description="对聚类结果进行生物学解释和注释",
    steps=[
        SkillStep(
            name="get_markers",
            tool_name="get_markers",
            description="获取各cluster的Marker基因",
            params={"n": 20},
            required=True
        ),
        SkillStep(
            name="plot_markers",
            tool_name="plot_markers",
            description="绘制Marker基因图表",
            params={"n_markers": 10, "plot_type": "dotplot"},
            required=True
        ),
        SkillStep(
            name="get_summary",
            tool_name="get_analysis_summary",
            description="获取聚类结果摘要",
            params={},
            required=True
        ),
    ],
    prerequisites=["clustering"],  # 需要先完成聚类
    output_description="聚类注释报告，包括各cluster的Marker基因和可能的细胞类型"
)

# 5. 降维分析Skill
DIMENSIONALITY_REDUCTION_SKILL = Skill(
    name="dimensionality_reduction_skill",
    description="专注于数据降维和可视化",
    steps=[
        SkillStep(
            name="load_data",
            tool_name="load_data",
            description="加载数据",
            params={},
            required=True
        ),
        SkillStep(
            name="preprocessing",
            tool_name="run_preprocessing",
            description="数据预处理（包含PCA）",
            params={"n_pcs": 50},
            required=True
        ),
        SkillStep(
            name="clustering",
            tool_name="run_clustering_analysis",
            description="UMAP降维和聚类",
            params={"method": "leiden"},
            required=True
        ),
        SkillStep(
            name="plot_umap",
            tool_name="plot_umap",
            description="绘制UMAP图",
            params={},
            required=True
        ),
    ],
    prerequisites=[],
    output_description="UMAP降维图和聚类结果"
)

# 6. 快速预览Skill（轻量级分析）
QUICK_PREVIEW_SKILL = Skill(
    name="quick_preview_skill",
    description="快速预览数据，只进行基本的QC和降维",
    steps=[
        SkillStep(
            name="load_data",
            tool_name="load_data",
            description="加载数据",
            params={},
            required=True
        ),
        SkillStep(
            name="get_info",
            tool_name="get_data_info",
            description="获取数据基本信息",
            params={},
            required=True
        ),
        SkillStep(
            name="quick_qc",
            tool_name="run_qc",
            description="快速QC",
            params={"min_genes": 100, "min_cells": 3},
            required=True
        ),
    ],
    prerequisites=[],
    output_description="数据概览和基本QC结果"
)


# ============ Skill注册表 ============

SKILL_REGISTRY: Dict[str, Skill] = {
    "basic_analysis": BASIC_ANALYSIS_WORKFLOW,
    "quality_control": QUALITY_CONTROL_SKILL,
    "gene_spatial": GENE_SPATIAL_ANALYSIS_SKILL,
    "cluster_annotation": CLUSTER_ANNOTATION_SKILL,
    "dimensionality_reduction": DIMENSIONALITY_REDUCTION_SKILL,
    "quick_preview": QUICK_PREVIEW_SKILL,
}


# ============ Skill操作函数 ============

def get_skill(name: str) -> Optional[Skill]:
    """
    获取指定的Skill

    Args:
        name: Skill名称

    Returns:
        Skill对象，如果不存在返回None
    """
    return SKILL_REGISTRY.get(name)


def list_skills() -> List[Dict[str, str]]:
    """
    列出所有可用的Skill

    Returns:
        Skill信息列表
    """
    return [
        {
            "name": skill.name,
            "description": skill.description,
            "n_steps": len(skill.steps)
        }
        for skill in SKILL_REGISTRY.values()
    ]


def get_skills_description() -> str:
    """
    获取所有Skill的描述文本

    Returns:
        格式化的描述字符串
    """
    lines = ["可用的分析Skill/Workflow：\n"]
    for name, skill in SKILL_REGISTRY.items():
        lines.append(f"**{name}**: {skill.description}")
        lines.append(f"  - 步骤数: {len(skill.steps)}")
        lines.append(f"  - 步骤: {' → '.join([s.name for s in skill.steps])}")
        lines.append("")
    return "\n".join(lines)


def skill_to_plan(skill: Skill, base_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    将Skill转换为执行计划

    Args:
        skill: Skill对象
        base_params: 基础参数，会覆盖Skill中的默认参数

    Returns:
        执行计划列表
    """
    base_params = base_params or {}

    plan = []
    for i, step in enumerate(skill.steps):
        # 合并参数
        params = step.params.copy()
        if step.tool_name in base_params:
            params.update(base_params[step.tool_name])

        plan.append({
            "step": i + 1,
            "function": step.tool_name,
            "description": step.description,
            "params": params,
            "status": "pending",
            "result": None,
            "error": None,
            "skill_step": step.name,
            "required": step.required,
            "skip_on_error": step.skip_on_error
        })

    return plan


def parse_skill_from_natural_language(user_input: str) -> Optional[str]:
    """
    从自然语言中解析应该使用哪个Skill

    Args:
        user_input: 用户输入

    Returns:
        Skill名称，如果无法识别返回None
    """
    user_input_lower = user_input.lower()

    # 关键词匹配
    if any(kw in user_input_lower for kw in ["快速", "预览", "简单", "概览"]):
        return "quick_preview"

    if any(kw in user_input_lower for kw in ["质量", "qc", "过滤"]):
        return "quality_control"

    if any(kw in user_input_lower for kw in ["基因", "空间表达", "表达模式"]):
        return "gene_spatial"

    if any(kw in user_input_lower for kw in ["注释", "解释", "marker", "特征基因"]):
        return "cluster_annotation"

    if any(kw in user_input_lower for kw in ["降维", "umap", "可视化"]):
        return "dimensionality_reduction"

    if any(kw in user_input_lower for kw in ["完整", "全部", "全流程", "分析"]):
        return "basic_analysis"

    # 默认使用基础分析
    return "basic_analysis"


def execute_skill(
    skill: Skill,
    tool_executor: Callable,
    file_path: str = None,
    params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    执行一个Skill（用于直接调用，不经过LangGraph）

    Args:
        skill: 要执行的Skill
        tool_executor: 工具执行函数
        file_path: 数据文件路径
        params: 额外参数

    Returns:
        执行结果
    """
    results = []
    errors = []
    completed_steps = []

    # 转换为计划
    plan = skill_to_plan(skill, params or {})

    # 设置文件路径
    if file_path and plan:
        plan[0]["params"]["file_path"] = file_path

    logger.info(f"开始执行Skill: {skill.name} ({len(plan)} 步)")

    for step in plan:
        step_name = step["function"]
        logger.info(f"执行步骤: {step['description']}")

        try:
            result = tool_executor(step_name, step["params"])
            step["status"] = "completed"
            step["result"] = result
            completed_steps.append(step_name)
            results.append({"step": step_name, "result": result})

        except Exception as e:
            logger.error(f"步骤 {step_name} 执行失败: {e}")
            step["status"] = "failed"
            step["error"] = str(e)
            errors.append({"step": step_name, "error": str(e)})

            if step.get("required") and not step.get("skip_on_error"):
                logger.error("必要步骤失败，终止执行")
                break

    return {
        "skill_name": skill.name,
        "completed_steps": completed_steps,
        "results": results,
        "errors": errors,
        "success": len(errors) == 0
    }
