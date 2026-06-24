"""
Executor节点实现

负责按计划执行分析步骤，调用对应的工具函数。
"""

import json
import logging
from typing import Dict, Any, Callable

from agent.state import AgentState, PlanStep
from agent.tools import (
    set_adata_to_state,
    load_data,
    run_qc,
    run_preprocessing,
    run_clustering_analysis,
    find_markers,
    generate_spatial_plots,
    get_analysis_summary,
    # 引擎层函数（供lambda直接调用，避免StructuredTool问题）
    find_marker_genes,
    get_top_markers,
    generate_clustering_plots,
    get_data_summary,
)
from engine.preprocessing import normalize_data, log_transform, select_hvg, standardize_data
from engine.clustering import run_pca, run_umap, run_clustering
from engine.spatial_viz import plot_embedding, plot_gene_spatial
from agent.shared_state import get_adata, set_adata

logger = logging.getLogger(__name__)


# 工具函数映射表
# 注意：lambda中不能直接调用@tool装饰的StructuredTool对象，
# 需要使用engine层的原始函数或通过.invoke()调用
TOOL_MAP: Dict[str, Callable] = {
    "load_data": load_data,
    "get_data_info": get_analysis_summary,
    "run_qc": run_qc,
    "calculate_qc": run_qc,
    "run_preprocessing": run_preprocessing,
    "normalize": run_preprocessing,
    "log_transform": run_preprocessing,
    "select_highly_variable_genes": run_preprocessing,
    "standardize": run_preprocessing,
    "run_clustering_analysis": run_clustering_analysis,
    "reduce_dimensionality": run_clustering_analysis,
    "cluster": run_clustering_analysis,
    "generate_spatial_plots": generate_spatial_plots,
    "plot_umap": generate_spatial_plots,
    "plot_gene_expression": generate_spatial_plots,
    "find_markers": find_markers,
    "get_markers": find_markers,
    "plot_markers": find_markers,
    "get_analysis_summary": get_analysis_summary,
}

# 原子步骤 → engine层函数映射（避免重复执行完整流水线）
# 这些函数直接操作adata，不经过LangChain Tool包装
ATOMICTO_ENGINE = {
    "normalize": normalize_data,
    "log_transform": log_transform,
    "select_highly_variable_genes": select_hvg,
    "standardize": standardize_data,
    "reduce_dimensionality": run_pca,
    "cluster": run_clustering,
    "plot_umap": plot_embedding,
    "plot_gene_expression": plot_gene_spatial,
}


def execute_step(step: PlanStep, state: AgentState) -> PlanStep:
    """
    执行单个分析步骤

    Args:
        step: 要执行的步骤
        state: 当前状态

    Returns:
        更新后的步骤（包含结果或错误）
    """
    func_name = step["function"]
    params = step["params"].copy()

    # 自动注入output_dir（如果工具需要但计划中未提供）
    if "output_dir" not in params:
        output_dir = state.get("output_dir", "")
        if output_dir:
            params["output_dir"] = output_dir

    logger.info(f"执行步骤 {step['step']}: {func_name}")

    # 同步AgentState中的adata到共享状态
    if state.get("adata") is not None:
        set_adata(state["adata"])

    # 特殊处理load_data，需要从state中获取file_path
    if func_name == "load_data":
        file_path = state.get("file_path") or params.get("file_path")
        if not file_path:
            result = json.dumps({"status": "error", "error": "未指定数据文件路径"})
            return PlanStep(
                step=step["step"],
                function=step["function"],
                description=step.get("description", ""),
                params=step["params"],
                status="failed",
                result=None,
                error="未指定数据文件路径"
            )
        params["file_path"] = file_path

    # 获取工具函数
    tool_func = TOOL_MAP.get(func_name)
    if not tool_func:
        return PlanStep(
            step=step["step"],
            function=step["function"],
            description=step.get("description", ""),
            params=step["params"],
            status="failed",
            result=None,
            error=f"未知的函数: {func_name}"
        )

    try:
        # 智能路由：原子步骤直接调用engine函数，避免重复执行完整流水线
        if func_name in ATOMICTO_ENGINE:
            engine_func = ATOMICTO_ENGINE[func_name]
            current_adata = state.get("adata")
            if current_adata is not None:
                # 直接调用engine函数，传入adata和参数
                result_adata = engine_func(current_adata, **params)
                # 更新共享状态
                set_adata(result_adata)
                result_str = json.dumps({"status": "success", "function": func_name})
            else:
                result_str = json.dumps({"status": "error", "error": "没有加载数据"})
        # 调用工具函数（支持LangChain Tool对象和普通函数）
        elif hasattr(tool_func, 'invoke'):
            # LangChain Tool对象，使用invoke方法
            result_str = tool_func.invoke(params)
        else:
            # 普通函数，直接调用
            result_str = tool_func(**params)

        # 解析结果
        try:
            result = json.loads(result_str)
        except json.JSONDecodeError:
            result = {"raw_output": result_str}

        # 判断是否成功
        if isinstance(result, dict) and result.get("status") == "error":
            return PlanStep(
                step=step["step"],
                function=step["function"],
                description=step.get("description", ""),
                params=step["params"],
                status="failed",
                result=result,
                error=result.get("error", "执行失败")
            )

        return PlanStep(
            step=step["step"],
            function=step["function"],
            description=step.get("description", ""),
            params=step["params"],
            status="completed",
            result=result,
            error=None
        )

    except Exception as e:
        logger.error(f"步骤执行失败: {e}")
        return PlanStep(
            step=step["step"],
            function=step["function"],
            description=step.get("description", ""),
            params=step["params"],
            status="failed",
            result=None,
            error=str(e)
        )


def executor_node(state: AgentState) -> AgentState:
    """
    Executor节点

    按计划执行当前步骤。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== Executor节点开始执行 ===")

    plan = state.get("plan", [])
    current_index = state.get("current_plan_index", 0)

    if not plan or current_index >= len(plan):
        logger.warning("没有待执行的步骤")
        new_state = state.copy()
        new_state["current_step"] = "completed"
        return new_state

    # 获取当前步骤
    current_step = plan[current_index]

    # 执行步骤
    updated_step = execute_step(current_step, state)

    # 更新计划
    new_plan = plan.copy()
    new_plan[current_index] = updated_step

    # 更新状态
    new_state = state.copy()
    new_state["plan"] = new_plan
    new_state["current_step"] = f"executed_{updated_step['function']}"

    # 同步共享状态中的adata到AgentState
    shared_adata = get_adata()
    if shared_adata is not None:
        new_state["adata"] = shared_adata

    # 更新已完成步骤列表
    completed_steps = state.get("completed_steps", []).copy()
    if updated_step["status"] == "completed":
        completed_steps.append(updated_step["function"])
    new_state["completed_steps"] = completed_steps

    # 存储结果
    results = state.get("results", {}).copy()
    results[updated_step["function"]] = updated_step["result"]
    new_state["results"] = results

    # 更新plot_files
    if updated_step["result"] and isinstance(updated_step["result"], dict):
        new_plot_files = state.get("plot_files", []).copy()
        if "plot_files" in updated_step["result"]:
            new_plot_files.extend(updated_step["result"]["plot_files"])
        if "plot_file" in updated_step["result"] and updated_step["result"]["plot_file"]:
            new_plot_files.append(updated_step["result"]["plot_file"])
        new_state["plot_files"] = new_plot_files

    # 处理错误
    if updated_step["status"] == "failed":
        new_state["error"] = updated_step["error"]
        new_state["retry_count"] = state.get("retry_count", 0) + 1
    else:
        new_state["error"] = None
        new_state["retry_count"] = 0

    # 更新对话历史
    messages = state.get("messages", []).copy()
    messages.append({
        "role": "assistant",
        "content": f"执行步骤 {updated_step['step']}: {updated_step['function']} - {updated_step['status']}"
    })
    new_state["messages"] = messages

    return new_state
