"""
Planner节点实现

负责解析用户自然语言请求，生成执行计划。
"""

import json
import logging
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()

from agent.state import AgentState, PlanStep
from agent.tools import get_tools_description, get_adata_from_state
from agent.prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT
)

# 有效的工具函数名列表（来自executor的TOOL_MAP和ATOMICTO_ENGINE）
VALID_FUNCTION_NAMES = {
    "load_data", "get_data_info", "run_qc", "calculate_qc",
    "run_preprocessing", "normalize", "log_transform",
    "select_highly_variable_genes", "standardize",
    "run_clustering_analysis", "reduce_dimensionality", "cluster",
    "generate_spatial_plots", "plot_umap", "plot_gene_expression",
    "find_markers", "get_markers", "plot_markers",
    "get_analysis_summary",
}

logger = logging.getLogger(__name__)


def get_data_info() -> str:
    """获取当前数据的信息摘要"""
    adata = get_adata_from_state()
    if adata is None:
        return "未加载数据"

    try:
        from engine import get_data_summary
        summary = get_data_summary(adata)
        return json.dumps(summary, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"获取数据信息失败: {str(e)}"


def parse_plan_from_llm_response(response: str) -> list:
    """
    从LLM响应中解析执行计划

    Args:
        response: LLM的响应文本

    Returns:
        解析后的PlanStep列表
    """
    try:
        # 尝试直接解析JSON
        if "```json" in response:
            # 提取JSON块
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response

        data = json.loads(json_str)

        if "plan" in data:
            plan_data = data["plan"]
        else:
            plan_data = data

        # 转换为PlanStep列表（验证函数名有效性）
        plan = []
        for i, step in enumerate(plan_data):
            func_name = step.get("function", "")
            if func_name not in VALID_FUNCTION_NAMES:
                logger.warning(f"LLM生成了无效的函数名: {func_name}，跳过该步骤")
                continue
            plan.append(PlanStep(
                step=step.get("step", i + 1),
                function=func_name,
                description=step.get("description", ""),
                params=step.get("params", {}),
                status="pending",
                result=None,
                error=None
            ))

        return plan

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return []
    except Exception as e:
        logger.error(f"计划解析失败: {e}")
        return []


def create_default_plan(user_input: str) -> list:
    """
    创建默认分析计划（不使用LLM时）

    Args:
        user_input: 用户输入

    Returns:
        默认的PlanStep列表
    """
    # 检查是否包含关键词
    user_input_lower = user_input.lower()

    # 基础计划
    plan = [
        PlanStep(
            step=1,
            function="load_data",
            description="加载数据文件",
            params={},
            status="pending",
            result=None,
            error=None
        ),
        PlanStep(
            step=2,
            function="run_qc",
            description="质量控制",
            params={},
            status="pending",
            result=None,
            error=None
        ),
        PlanStep(
            step=3,
            function="run_preprocessing",
            description="数据预处理",
            params={},
            status="pending",
            result=None,
            error=None
        ),
        PlanStep(
            step=4,
            function="run_clustering_analysis",
            description="降维聚类分析",
            params={},
            status="pending",
            result=None,
            error=None
        ),
        PlanStep(
            step=5,
            function="find_markers",
            description="Marker基因分析",
            params={},
            status="pending",
            result=None,
            error=None
        ),
        PlanStep(
            step=6,
            function="generate_spatial_plots",
            description="空间可视化",
            params={},
            status="pending",
            result=None,
            error=None
        ),
    ]

    return plan


def planner_node(state: AgentState) -> AgentState:
    """
    Planner节点

    解析用户请求，生成执行计划。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== Planner节点开始执行 ===")

    user_input = state.get("user_input", "")

    # 获取数据信息
    data_info = get_data_info()

    # 尝试使用LLM生成计划
    llm = None
    try:
        from langchain_openai import ChatOpenAI
        import os

        # 从环境变量读取配置
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("LLM_MODEL", "gpt-4")

        if api_key:
            llm = ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=0,
                timeout=30  # 30秒超时
            )
    except Exception as e:
        logger.warning(f"LLM初始化失败，使用默认计划: {e}")

    if llm:
        # 使用LLM生成计划
        try:
            tools_desc = get_tools_description()
            system_prompt = PLANNER_SYSTEM_PROMPT.format(tools_description=tools_desc)
            user_prompt = PLANNER_USER_PROMPT.format(
                user_input=user_input,
                data_info=data_info
            )

            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = llm.invoke(messages)
            plan = parse_plan_from_llm_response(response.content)

            if not plan:
                logger.warning("LLM返回的计划解析失败，使用默认计划")
                plan = create_default_plan(user_input)
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            plan = create_default_plan(user_input)
    else:
        # 使用默认计划
        plan = create_default_plan(user_input)

    logger.info(f"生成了 {len(plan)} 个执行步骤")

    # 更新状态
    new_state = state.copy()
    new_state["plan"] = plan
    new_state["current_plan_index"] = 0
    new_state["current_step"] = "planned"
    new_state["messages"] = state.get("messages", []) + [
        {"role": "assistant", "content": f"已生成分析计划，共{len(plan)}个步骤"}
    ]

    return new_state
