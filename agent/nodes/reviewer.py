"""
Reviewer节点实现

负责检查执行结果，生成用户可读的解释。
"""

import json
import logging
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()

from agent.state import AgentState
from agent.tools import get_adata_from_state
from agent.prompts import REVIEWER_SYSTEM_PROMPT, REVIEWER_USER_PROMPT

logger = logging.getLogger(__name__)


def get_data_summary() -> str:
    """获取数据摘要"""
    adata = get_adata_from_state()
    if adata is None:
        return "未加载数据"

    try:
        from engine import get_data_summary as engine_get_summary
        summary = engine_get_summary(adata)
        return json.dumps(summary, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"获取摘要失败: {str(e)}"


def format_step_result(step_name: str, result: Any) -> str:
    """
    格式化步骤结果

    Args:
        step_name: 步骤名称
        result: 执行结果

    Returns:
        格式化后的文本
    """
    if result is None:
        return "无结果"

    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2)

    return str(result)


def generate_review_with_llm(step_name: str, result: str, data_summary: str) -> str:
    """
    使用LLM生成结果解读

    Args:
        step_name: 步骤名称
        result: 执行结果
        data_summary: 数据摘要

    Returns:
        LLM生成的解读文本
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        import os

        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("LLM_MODEL", "gpt-4")

        if not api_key:
            return None

        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0,
            timeout=30  # 30秒超时
        )

        user_prompt = REVIEWER_USER_PROMPT.format(
            step_name=step_name,
            result=result,
            data_summary=data_summary
        )

        messages = [
            SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        response = llm.invoke(messages)
        return response.content

    except Exception as e:
        logger.warning(f"LLM解读失败: {e}")
        return None


def generate_review_without_llm(step_name: str, result: Any) -> str:
    """
    不使用LLM生成简单的结果解读

    Args:
        step_name: 步骤名称
        result: 执行结果

    Returns:
        简单的解读文本
    """
    if not result or not isinstance(result, dict):
        return f"步骤 {step_name} 已完成"

    status = result.get("status", "unknown")

    if status == "error":
        return f"步骤 {step_name} 执行失败: {result.get('error', '未知错误')}"

    # 根据不同步骤生成不同的解读
    if "load_data" in step_name:
        summary = result.get("summary", {})
        n_cells = summary.get("n_cells", "未知")
        n_genes = summary.get("n_genes", "未知")
        return f"数据加载成功。共 {n_cells} 个细胞，{n_genes} 个基因。"

    elif "qc" in step_name:
        summary = result.get("summary", {})
        return f"质量控制完成。过滤后的数据统计: {json.dumps(summary, ensure_ascii=False)[:200]}"

    elif "preprocessing" in step_name:
        summary = result.get("summary", {})
        n_hvg = summary.get("n_hvg", "未知")
        return f"数据预处理完成。筛选出 {n_hvg} 个高变基因。"

    elif "clustering" in step_name:
        n_clusters = result.get("n_clusters", "未知")
        return f"降维聚类完成。发现 {n_clusters} 个细胞cluster。"

    elif "marker" in step_name:
        top_markers = result.get("top_markers", {})
        n_clusters = len(top_markers)
        sample_markers = {}
        for k, v in list(top_markers.items())[:2]:
            sample_markers[k] = v[:3]
        return f"Marker基因分析完成。为 {n_clusters} 个cluster鉴定了marker基因。示例: {json.dumps(sample_markers, ensure_ascii=False)}"

    elif "spatial" in step_name or "plot" in step_name:
        plot_files = result.get("plot_files", [])
        return f"可视化生成完成。共生成 {len(plot_files)} 个图表文件。"

    elif "summary" in step_name:
        return f"分析摘要: {json.dumps(result, ensure_ascii=False)[:500]}"

    else:
        return f"步骤 {step_name} 已完成。"


def reviewer_node(state: AgentState) -> AgentState:
    """
    Reviewer节点

    在所有步骤完成后，总结所有分析结果，生成用户可读的报告。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== Reviewer节点开始执行 ===")

    plan = state.get("plan", [])
    results = state.get("results", {})
    data_summary = get_data_summary()

    # 汇总所有步骤的结果
    summary_parts = []
    for step in plan:
        step_name = step["function"]
        result = step.get("result")
        status = step.get("status", "pending")

        if status == "completed" and result:
            review = generate_review_without_llm(step_name, result)
            summary_parts.append(f"### {step_name}\n{review}")
        elif status == "skipped":
            summary_parts.append(f"### {step_name}\n跳过: {step.get('error', '未知原因')}")
        elif status == "failed":
            summary_parts.append(f"### {step_name}\n失败: {step.get('error', '未知错误')}")

    # 组合摘要
    if summary_parts:
        new_summary = "## 分析结果总结\n\n" + "\n\n".join(summary_parts)
    else:
        new_summary = "## 分析结果\n\n未找到已完成的步骤结果。"

    logger.info(f"生成了分析总结，包含 {len(summary_parts)} 个步骤")

    # 更新状态
    new_state = state.copy()
    new_state["summary"] = new_summary
    new_state["current_step"] = "reviewed"

    # 更新对话历史
    messages = state.get("messages", []).copy()
    messages.append({
        "role": "assistant",
        "content": f"[分析总结] 已完成 {len(summary_parts)} 个分析步骤"
    })
    new_state["messages"] = messages

    # 清除错误状态
    new_state["error"] = None
    new_state["retry_count"] = 0

    return new_state
