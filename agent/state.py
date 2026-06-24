"""
Agent状态定义模块

定义LangGraph工作流中使用的AgentState类型。
"""

from typing import TypedDict, Optional, List, Dict, Any
from anndata import AnnData


class PlanStep(TypedDict):
    """执行计划中的单个步骤"""
    step: int                    # 步骤序号
    function: str                # 要调用的函数名
    params: Dict[str, Any]       # 函数参数
    status: str                  # pending / running / completed / failed
    result: Optional[str]        # 执行结果
    error: Optional[str]         # 错误信息


class AgentState(TypedDict):
    """
    Agent全局状态

    在LangGraph工作流中，所有节点共享并修改此状态。
    """
    # ============ 用户输入 ============
    user_input: str                          # 用户的自然语言请求

    # ============ 数据状态 ============
    file_path: Optional[str]                 # 数据文件路径
    adata: Optional[AnnData]                 # AnnData对象（内存中）

    # ============ 分析配置 ============
    params: Dict[str, Any]                   # 分析参数
    output_dir: str                          # 输出目录

    # ============ 执行状态 ============
    current_step: str                        # 当前步骤名称
    completed_steps: List[str]               # 已完成的步骤列表
    plan: List[PlanStep]                     # 执行计划
    current_plan_index: int                  # 当前执行到的计划索引

    # ============ 结果 ============
    results: Dict[str, Any]                  # 各步骤的执行结果
    plot_files: List[str]                    # 生成的图表文件路径
    summary: str                             # 分析结果摘要

    # ============ 错误处理 ============
    error: Optional[str]                     # 当前错误信息
    retry_count: int                         # 当前重试次数
    max_retries: int                         # 最大重试次数

    # ============ 对话历史 ============
    messages: List[Dict[str, str]]           # 对话历史记录


def create_initial_state(
    user_input: str,
    file_path: Optional[str] = None,
    output_dir: str = "storage/results",
    params: Optional[Dict[str, Any]] = None
) -> AgentState:
    """
    创建初始状态

    Args:
        user_input: 用户输入的自然语言请求
        file_path: 数据文件路径（可选）
        output_dir: 输出目录
        params: 分析参数（可选）

    Returns:
        初始化的AgentState
    """
    return AgentState(
        # 用户输入
        user_input=user_input,

        # 数据状态
        file_path=file_path,
        adata=None,

        # 分析配置
        params=params or {},
        output_dir=output_dir,

        # 执行状态
        current_step="init",
        completed_steps=[],
        plan=[],
        current_plan_index=0,

        # 结果
        results={},
        plot_files=[],
        summary="",

        # 错误处理
        error=None,
        retry_count=0,
        max_retries=3,

        # 对话历史
        messages=[{"role": "user", "content": user_input}]
    )
