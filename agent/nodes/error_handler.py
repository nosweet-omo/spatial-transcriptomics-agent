"""
ErrorHandler节点实现

负责处理执行异常，决定重试、跳过或终止。
"""

import json
import logging
import copy
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()

from agent.state import AgentState
from agent.tools import get_adata_from_state
from agent.prompts import ERROR_HANDLER_SYSTEM_PROMPT, ERROR_HANDLER_USER_PROMPT

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


def analyze_error(error_msg: str, step_name: str) -> Dict[str, Any]:
    """
    分析错误类型并给出处理建议

    Args:
        error_msg: 错误信息
        step_name: 步骤名称

    Returns:
        包含action和reason的字典
    """
    error_lower = error_msg.lower()

    # 文件不存在（不可恢复）
    if "filenotfound" in error_lower or "文件不存在" in error_msg or "no such file" in error_lower:
        return {
            "action": "abort",
            "reason": "数据文件不存在，请检查文件路径"
        }

    # 内存不足（可跳过）
    if "memoryerror" in error_lower or "内存" in error_msg or "out of memory" in error_lower:
        return {
            "action": "skip",
            "reason": "内存不足，跳过此步骤"
        }

    # 参数错误（可重试）
    if "typeerror" in error_lower or "valueerror" in error_lower or "参数" in error_msg:
        return {
            "action": "retry",
            "reason": "参数类型或值错误，尝试使用默认参数重试",
            "suggested_params": {}
        }

    # 列名/键不存在（可跳过）
    if "keyerror" in error_lower or "not found" in error_lower or "不存在" in error_msg:
        return {
            "action": "skip",
            "reason": "所需的数据列或键不存在，跳过此步骤"
        }

    # 数据为空（不可恢复）
    if "empty" in error_lower or "空" in error_msg or "shape[0] == 0" in error_lower:
        return {
            "action": "abort",
            "reason": "数据为空，无法继续分析"
        }

    # 权限错误（不可恢复）
    if "permission" in error_lower or "权限" in error_msg:
        return {
            "action": "abort",
            "reason": "权限不足，无法访问文件或目录"
        }

    # 超时错误（可重试）
    if "timeout" in error_lower or "超时" in error_msg:
        return {
            "action": "retry",
            "reason": "操作超时，尝试重试",
            "suggested_params": {}
        }

    # 连接错误（可重试）
    if "connection" in error_lower or "连接" in error_msg:
        return {
            "action": "retry",
            "reason": "网络连接失败，尝试重试",
            "suggested_params": {}
        }

    # 默认：重试一次
    return {
        "action": "retry",
        "reason": "未知错误，尝试重试",
        "suggested_params": {}
    }


def handle_with_llm(step_name: str, error: str, data_summary: str) -> Dict[str, Any]:
    """
    使用LLM分析错误并给出处理建议

    Args:
        step_name: 步骤名称
        error: 错误信息
        data_summary: 数据摘要

    Returns:
        包含action和reason的字典
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        from langchain_core.output_parsers import JsonOutputParser
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

        user_prompt = ERROR_HANDLER_USER_PROMPT.format(
            step_name=step_name,
            error=error,
            data_summary=data_summary
        )

        messages = [
            SystemMessage(content=ERROR_HANDLER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        response = llm.invoke(messages)

        # 解析响应
        content = response.content
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            json_str = content

        return json.loads(json_str)

    except Exception as e:
        logger.warning(f"LLM错误分析失败: {e}")
        return None


def error_handler_node(state: AgentState) -> AgentState:
    """
    ErrorHandler节点

    处理执行异常，决定重试、跳过或终止。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== ErrorHandler节点开始执行 ===")

    error = state.get("error", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    plan = state.get("plan", [])
    current_index = state.get("current_plan_index", 0)

    if not plan or current_index >= len(plan):
        new_state = state.copy()
        new_state["current_step"] = "error_handled"
        return new_state

    # 获取当前步骤
    current_step = plan[current_index]
    step_name = current_step["function"]

    logger.error(f"步骤 {step_name} 执行失败: {error}")

    # 分析错误
    data_summary = get_data_summary()

    # 尝试使用LLM分析
    error_analysis = handle_with_llm(step_name, error, data_summary)

    # 如果LLM失败，使用规则分析
    if not error_analysis:
        error_analysis = analyze_error(error, step_name)

    action = error_analysis.get("action", "skip")
    reason = error_analysis.get("reason", "未知原因")

    logger.info(f"错误分析结果: action={action}, reason={reason}")

    # 根据action决定下一步
    new_state = state.copy()

    if action == "retry" and retry_count < max_retries:
        # 重试
        logger.info(f"重试步骤 {step_name} (第{retry_count + 1}次)")

        # 如果有建议参数，更新步骤参数（使用深拷贝避免污染原始状态）
        suggested_params = error_analysis.get("suggested_params", {})
        if suggested_params:
            new_plan = copy.deepcopy(plan)
            new_plan[current_index]["params"].update(suggested_params)
            new_state["plan"] = new_plan

        new_state["current_step"] = f"retry_{step_name}"
        new_state["error"] = None

        # 更新对话历史
        messages = state.get("messages", []).copy()
        messages.append({
            "role": "assistant",
            "content": f"[错误处理] {reason}，正在重试..."
        })
        new_state["messages"] = messages

    elif action == "skip":
        # 跳过当前步骤
        logger.info(f"跳过步骤 {step_name}")

        new_plan = copy.deepcopy(plan)
        new_plan[current_index]["status"] = "skipped"
        new_plan[current_index]["error"] = reason
        new_state["plan"] = new_plan

        new_state["current_plan_index"] = current_index + 1
        new_state["current_step"] = f"skipped_{step_name}"
        new_state["error"] = None
        new_state["retry_count"] = 0

        # 更新摘要
        old_summary = state.get("summary", "")
        new_summary = f"{old_summary}\n\n## 跳过: {step_name}\n原因: {reason}"
        new_state["summary"] = new_summary

        # 更新对话历史
        messages = state.get("messages", []).copy()
        messages.append({
            "role": "assistant",
            "content": f"[错误处理] 跳过步骤 {step_name}: {reason}"
        })
        new_state["messages"] = messages

    else:
        # 终止
        logger.info(f"终止分析流程")

        new_state["current_step"] = "aborted"
        new_state["error"] = f"分析终止: {reason}"

        # 更新摘要
        old_summary = state.get("summary", "")
        new_summary = f"{old_summary}\n\n## 分析终止\n原因: {reason}"
        new_state["summary"] = new_summary

        # 更新对话历史
        messages = state.get("messages", []).copy()
        messages.append({
            "role": "assistant",
            "content": f"[错误处理] 分析终止: {reason}"
        })
        new_state["messages"] = messages

    return new_state
