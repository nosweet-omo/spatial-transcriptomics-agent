"""
LangGraph图定义模块

定义Agent的工作流程图，体现以下核心设计思想：
1. 节点设计：不同节点承担不同功能（任务理解、分析规划、工具调用、结果解释、错误处理）
2. 边与流程控制：根据用户输入、任务状态或工具返回结果决定下一步执行路径
3. 状态管理：维护当前任务、数据路径、分析步骤、已生成结果、错误信息等状态
4. 循环机制：实现"规划—执行—检查—修正"的多步执行流程
"""

import json
import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    planner_node,
    executor_node,
    reviewer_node,
    error_handler_node,
)
from agent.skills import parse_skill_from_natural_language, get_skill, skill_to_plan

logger = logging.getLogger(__name__)


# ============ 条件判断函数 ============

def should_continue_after_executor(state: AgentState) -> Literal["result_checker", "error_handler"]:
    """
    Executor执行后判断下一步

    流程控制逻辑：
    - 如果执行成功 → 进入结果检查
    - 如果执行失败 → 进入错误处理

    Args:
        state: 当前状态

    Returns:
        "result_checker" 或 "error_handler"
    """
    if state.get("error"):
        logger.info("检测到错误，进入ErrorHandler")
        return "error_handler"

    logger.info("执行成功，进入结果检查")
    return "result_checker"


def should_continue_after_checker(state: AgentState) -> Literal["executor", "reviewer", "planner", "__end__"]:
    """
    ResultChecker执行后判断下一步

    流程控制逻辑：
    - 如果需要修正 → 返回planner重新规划
    - 如果被终止 → 结束
    - 如果还有下一步 → 直接去executor执行
    - 如果所有步骤完成 → 进入reviewer总结

    Args:
        state: 当前状态

    Returns:
        "executor", "reviewer", "planner" 或 "__end__"
    """
    current_step = state.get("current_step", "")

    # 检查是否需要修正（result_checker设置的标志）
    if current_step.startswith("need_adjust_"):
        logger.info("结果检查发现问题，需要调整计划")
        return "planner"

    # 检查是否被终止
    if current_step == "aborted":
        logger.info("分析流程已终止")
        return "__end__"

    # 检查是否还有下一步
    plan = state.get("plan", [])
    current_index = state.get("current_plan_index", 0)

    if current_index >= len(plan):
        logger.info("所有步骤已完成，进入结果审查")
        return "reviewer"

    # 还有下一步，直接去executor执行（不经过reviewer，避免跳步）
    logger.info(f"继续执行下一步: {current_index + 1}/{len(plan)}")
    return "executor"


def should_continue_after_reviewer(state: AgentState) -> Literal["final_reviewer", "__end__"]:
    """
    Reviewer执行后判断下一步

    Reviewer现在只在所有步骤完成后调用，用于总结分析结果。
    之后进入final_reviewer生成最终报告。

    Args:
        state: 当前状态

    Returns:
        "final_reviewer" 或 "__end__"
    """
    # 检查是否被终止
    if state.get("current_step") == "aborted":
        logger.info("分析流程已终止")
        return "__end__"

    # Reviewer已完成总结，进入最终审查
    logger.info("分析总结完成，进入最终审查")
    return "final_reviewer"


def should_continue_after_final_review(state: AgentState) -> Literal["planner", "__end__"]:
    """
    FinalReviewer执行后判断下一步

    流程控制逻辑：
    - 如果用户要求调整 → 返回planner重新规划（多轮交互）
    - 如果分析完成 → 结束

    Args:
        state: 当前状态

    Returns:
        "planner" 或 "__end__"
    """
    # 检查是否有用户的新请求（通过messages判断）
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if last_message.get("role") == "user":
            # 用户有新请求，返回planner
            logger.info("检测到用户新请求，返回规划阶段")
            return "planner"

    logger.info("分析完成")
    return "__end__"


def should_continue_after_error(state: AgentState) -> Literal["executor", "planner", "__end__"]:
    """
    ErrorHandler执行后判断下一步

    流程控制逻辑：
    - 如果是重试 → 返回executor
    - 如果是跳过 → 返回executor继续下一步
    - 如果需要重新规划 → 返回planner
    - 如果终止 → 结束

    Args:
        state: 当前状态

    Returns:
        "executor", "planner" 或 "__end__"
    """
    current_step = state.get("current_step", "")

    # 如果被终止
    if current_step == "aborted":
        return "__end__"

    # 如果是重试
    if current_step.startswith("retry_"):
        return "executor"

    # 如果是跳过，继续下一步
    if current_step.startswith("skipped_"):
        return "executor"

    # 如果需要重新规划
    if current_step.startswith("replan_"):
        return "planner"

    return "__end__"


# ============ 新增节点 ============

def result_checker_node(state: AgentState) -> AgentState:
    """
    结果检查节点

    检查当前步骤的执行结果是否满足预期：
    1. 检查数据是否有效
    2. 检查结果是否完整
    3. 检查是否需要调整参数

    这是"规划—执行—检查—修正"循环中的"检查"环节。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== ResultChecker节点开始执行 ===")

    plan = state.get("plan", [])
    current_index = state.get("current_plan_index", 0)

    if not plan or current_index >= len(plan):
        new_state = state.copy()
        new_state["current_step"] = "checked"
        return new_state

    # 获取当前步骤
    current_step = plan[current_index]
    step_name = current_step.get("function", "unknown")
    result = current_step.get("result")

    logger.info(f"检查步骤 {step_name} 的结果")

    # 结果检查逻辑
    needs_adjustment = False
    adjustment_reason = ""

    if result is None:
        needs_adjustment = True
        adjustment_reason = "步骤未返回结果"
    elif isinstance(result, dict):
        status = result.get("status", "")

        # 检查是否有错误
        if status == "error":
            needs_adjustment = True
            adjustment_reason = f"执行错误: {result.get('error', '未知错误')}"

        # 检查结果是否为空
        elif status == "success":
            # 根据不同步骤检查结果质量
            if "load_data" in step_name:
                summary = result.get("summary", {})
                n_cells = summary.get("n_cells", 0)
                if n_cells == 0:
                    needs_adjustment = True
                    adjustment_reason = "加载的数据为空"

            elif "qc" in step_name:
                # QC后应该有数据，检查是否过滤后为空
                summary = result.get("summary", {})
                n_cells = summary.get("n_cells", 0)
                if n_cells == 0:
                    needs_adjustment = True
                    adjustment_reason = "QC过滤后数据为空（所有细胞被过滤）"

            elif "clustering" in step_name:
                n_clusters = result.get("n_clusters", 0)
                if n_clusters == 0:
                    needs_adjustment = True
                    adjustment_reason = "未识别出任何cluster"

            elif "marker" in step_name:
                top_markers = result.get("top_markers", {})
                if not top_markers:
                    needs_adjustment = True
                    adjustment_reason = "未找到marker基因"

            elif "spatial" in step_name or "plot" in step_name:
                plot_files = result.get("plot_files", [])
                if not plot_files:
                    # 可视化失败不是严重问题，只是警告
                    logger.warning("未生成可视化图表")

    # 更新状态
    new_state = state.copy()

    # 确保plot_files被保留（state.copy()是浅拷贝，但显式更安全）
    if "plot_files" not in new_state:
        new_state["plot_files"] = state.get("plot_files", []).copy()

    if needs_adjustment:
        logger.info(f"需要调整: {adjustment_reason}")
        new_state["current_step"] = f"need_adjust_{step_name}"
        new_state["error"] = adjustment_reason

        # 记录调整原因
        messages = state.get("messages", []).copy()
        messages.append({
            "role": "assistant",
            "content": f"[检查] 步骤 {step_name} 需要调整: {adjustment_reason}"
        })
        new_state["messages"] = messages
    else:
        logger.info(f"步骤 {step_name} 结果检查通过")
        new_state["current_step"] = f"checked_{step_name}"
        new_state["error"] = None

        # 移动到下一步
        new_state["current_plan_index"] = current_index + 1

        # 更新摘要
        old_summary = state.get("summary", "")
        if result and isinstance(result, dict):
            # 添加检查通过的信息
            new_summary = f"{old_summary}\n\n[检查通过] {step_name}"
            new_state["summary"] = new_summary

    return new_state


def final_reviewer_node(state: AgentState) -> AgentState:
    """
    最终审查节点

    在所有步骤完成后，收集所有图表并生成最终分析报告。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== FinalReviewer节点开始执行 ===")

    from pathlib import Path

    # 收集所有图表文件：从state中获取 + 扫描输出目录
    plot_files = list(state.get("plot_files", []))

    # 扫描常见输出目录，收集所有png图表
    output_dirs = [
        "storage/results",
        "storage/results/demo",
        "qc_results",
        "clustering_results",
        "spatial_plots",
        "marker_results",
        "storage/results/qc",
        "storage/results/clustering",
        "storage/results/spatial",
        "storage/results/marker",
    ]
    seen = set(plot_files)
    for d in output_dirs:
        p = Path(d)
        if p.exists():
            for png in sorted(p.glob("*.png")):
                path_str = str(png)
                if path_str not in seen:
                    plot_files.append(path_str)
                    seen.add(path_str)

    # 也从results字典中收集plot_files
    results = state.get("results", {})
    for step_result in results.values():
        if isinstance(step_result, dict):
            for key in ["plot_files", "plot_file"]:
                val = step_result.get(key)
                if val:
                    if isinstance(val, list):
                        for f in val:
                            if f and str(f) not in seen:
                                plot_files.append(str(f))
                                seen.add(str(f))
                    elif isinstance(val, str) and val not in seen:
                        plot_files.append(val)
                        seen.add(val)

    logger.info(f"共收集到 {len(plot_files)} 个图表文件")

    # 生成最终报告
    summary = state.get("summary", "")
    final_report = f"""# 空间转录组分析报告

## 分析概览

{summary}

## 生成的图表

"""
    for plot_file in plot_files:
        final_report += f"- {plot_file}\n"

    final_report += f"""

## 分析完成

共生成 {len(plot_files)} 个图表文件。所有分析步骤已完成。如需进一步分析或调整参数，请告诉我。
"""

    # 更新状态
    new_state = state.copy()
    new_state["current_step"] = "completed"
    new_state["plot_files"] = plot_files
    new_state["summary"] = final_report

    # 更新对话历史
    messages = state.get("messages", []).copy()
    messages.append({
        "role": "assistant",
        "content": f"分析已完成！共生成 {len(plot_files)} 个图表。\n\n{final_report}"
    })
    new_state["messages"] = messages

    return new_state


def planner_adjuster_node(state: AgentState) -> AgentState:
    """
    计划调整节点

    根据结果检查的反馈，调整执行计划。

    这是"规划—执行—检查—修正"循环中的"修正"环节。

    Args:
        state: 当前AgentState

    Returns:
        更新后的AgentState
    """
    logger.info("=== PlannerAdjuster节点开始执行 ===")

    error = state.get("error", "")
    plan = state.get("plan", [])
    current_index = state.get("current_plan_index", 0)

    logger.info(f"根据反馈调整计划: {error}")

    # 调整策略
    new_state = state.copy()

    if current_index < len(plan):
        current_step = plan[current_index]
        step_name = current_step["function"]

        # 根据错误类型决定调整策略
        if "空" in error or "未找到" in error:
            # 数据为空，可能需要检查前置步骤
            logger.info("数据为空，回退到前置步骤")
            new_state["current_plan_index"] = max(0, current_index - 1)
            new_state["current_step"] = f"replan_{step_name}"
        else:
            # 其他错误，跳过当前步骤
            logger.info("跳过当前步骤，继续下一步")
            new_plan = plan.copy()
            new_plan[current_index]["status"] = "skipped"
            new_plan[current_index]["error"] = error
            new_state["plan"] = new_plan
            new_state["current_plan_index"] = current_index + 1
            new_state["current_step"] = f"replan_{step_name}"
    else:
        new_state["current_step"] = "completed"

    # 更新对话历史
    messages = state.get("messages", []).copy()
    messages.append({
        "role": "assistant",
        "content": f"[计划调整] 根据检查结果调整执行计划"
    })
    new_state["messages"] = messages

    return new_state


# ============ 图定义 ============

def create_agent_graph() -> StateGraph:
    """
    创建Agent工作流图

    体现LangGraph的核心设计思想：

    1. 节点设计：
       - planner: 任务理解与规划
       - executor: 工具调用
       - result_checker: 结果检查
       - reviewer: 结果解释
       - final_reviewer: 最终报告生成
       - planner_adjuster: 计划修正
       - error_handler: 错误处理

    2. 边与流程控制：
       - 根据执行结果决定下一步
       - 支持条件分支和循环

    3. 循环机制：
       - planner → executor → result_checker → (planner | reviewer) 循环
       - executor → error_handler → executor 重试循环

    流程图：
    ```
    planner → executor → result_checker → executor → ... → result_checker → reviewer → final_reviewer → END
                  |              |                                                    |
                  v              v                                                    v
           error_handler    planner                                            planner (多轮)
                  |
                  v
               executor (retry)
    ```

    Returns:
        编译后的StateGraph
    """
    # 创建图
    workflow = StateGraph(AgentState)

    # ============ 添加节点 ============
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("result_checker", result_checker_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("final_reviewer", final_reviewer_node)
    workflow.add_node("planner_adjuster", planner_adjuster_node)
    workflow.add_node("error_handler", error_handler_node)

    # ============ 设置入口 ============
    workflow.set_entry_point("planner")

    # ============ 定义边 ============

    # planner -> executor
    workflow.add_edge("planner", "executor")

    # executor -> result_checker 或 error_handler
    workflow.add_conditional_edges(
        "executor",
        should_continue_after_executor,
        {
            "result_checker": "result_checker",
            "error_handler": "error_handler"
        }
    )

    # result_checker -> executor, reviewer, planner 或 end
    workflow.add_conditional_edges(
        "result_checker",
        should_continue_after_checker,
        {
            "executor": "executor",
            "reviewer": "reviewer",
            "planner": "planner",
            "__end__": END
        }
    )

    # reviewer -> final_reviewer 或 end
    workflow.add_conditional_edges(
        "reviewer",
        should_continue_after_reviewer,
        {
            "final_reviewer": "final_reviewer",
            "__end__": END
        }
    )

    # final_reviewer -> planner 或 end（支持多轮交互）
    workflow.add_conditional_edges(
        "final_reviewer",
        should_continue_after_final_review,
        {
            "planner": "planner",
            "__end__": END
        }
    )

    # error_handler -> executor, planner 或 end
    workflow.add_conditional_edges(
        "error_handler",
        should_continue_after_error,
        {
            "executor": "executor",
            "planner": "planner",
            "__end__": END
        }
    )

    # planner_adjuster -> planner
    workflow.add_edge("planner_adjuster", "planner")

    # 编译图
    graph = workflow.compile()

    logger.info("Agent图创建完成（包含循环和条件控制）")

    return graph


# ============ 主入口函数 ============

def run_agent(
    user_input: str,
    file_path: str = None,
    output_dir: str = "storage/results",
    params: dict = None,
    skill_name: str = None
) -> AgentState:
    """
    运行Agent

    支持两种模式：
    1. 自然语言模式：用户输入自然语言，Agent自动规划和执行
    2. Skill模式：指定使用某个预定义的Skill

    体现Agent的核心能力：
    - 理解用户意图（Planner）
    - 自动选择和执行工具（Executor）
    - 检查结果质量（ResultChecker）
    - 生成易懂的报告（Reviewer）
    - 错误处理和恢复（ErrorHandler）
    - 支持多轮交互（FinalReviewer）

    Args:
        user_input: 用户输入的自然语言请求
        file_path: 数据文件路径
        output_dir: 输出目录
        params: 分析参数
        skill_name: 指定使用的Skill名称（可选）

    Returns:
        最终的AgentState
    """
    from agent.state import create_initial_state

    # 创建初始状态
    initial_state = create_initial_state(
        user_input=user_input,
        file_path=file_path,
        output_dir=output_dir,
        params=params
    )

    # 如果指定了Skill，使用Skill生成计划
    if skill_name:
        skill = get_skill(skill_name)
        if skill:
            initial_state["current_step"] = f"using_skill_{skill_name}"
            logger.info(f"使用预定义Skill: {skill_name}")

    # 创建图
    graph = create_agent_graph()

    # 运行
    logger.info(f"开始运行Agent: {user_input}")

    final_state = None
    for step in graph.stream(initial_state, stream_mode="values"):
        # stream_mode="values"返回完整状态字典，直接赋值
        final_state = step

    # 收集所有生成的图表文件
    from pathlib import Path
    all_plot_files = list(final_state.get("plot_files", [])) if final_state else []
    seen = set(all_plot_files)

    # 扫描所有可能的输出目录
    scan_dirs = [
        "storage/results", "storage/results/demo",
        "qc_results", "clustering_results", "spatial_plots", "marker_results",
        "storage/results/qc", "storage/results/clustering",
        "storage/results/spatial", "storage/results/marker",
    ]
    for d in scan_dirs:
        p = Path(d)
        if p.exists():
            for png in sorted(p.glob("*.png")):
                path_str = str(png)
                if path_str not in seen:
                    all_plot_files.append(path_str)
                    seen.add(path_str)

    # 从results字典中补充
    if final_state:
        results = final_state.get("results", {})
        for step_result in results.values():
            if isinstance(step_result, dict):
                for key in ["plot_files", "plot_file"]:
                    val = step_result.get(key)
                    if val:
                        if isinstance(val, list):
                            for f in val:
                                if f and str(f) not in seen:
                                    all_plot_files.append(str(f))
                                    seen.add(str(f))
                        elif isinstance(val, str) and val not in seen:
                            all_plot_files.append(val)
                            seen.add(val)

        final_state["plot_files"] = all_plot_files

    logger.info(f"Agent运行完成，共收集 {len(all_plot_files)} 个图表文件")

    return final_state


def run_agent_interactive() -> None:
    """
    交互式运行Agent

    支持多轮对话，用户可以随时提出新的分析需求。
    """
    from agent.state import create_initial_state

    print("\n🧬 空间转录组智能分析平台 - Agent交互模式")
    print("=" * 60)
    print("输入分析请求，Agent将自动规划并执行。")
    print("输入 'quit' 退出。")
    print("=" * 60 + "\n")

    current_state = None

    while True:
        try:
            user_input = input("\n🔹 请输入分析请求: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\n👋 再见！")
                break

            # 创建或更新状态
            if current_state is None:
                current_state = create_initial_state(user_input=user_input)
            else:
                # 多轮交互：在现有状态上添加新请求
                messages = current_state.get("messages", [])
                messages.append({"role": "user", "content": user_input})
                current_state["messages"] = messages
                current_state["user_input"] = user_input

            # 创建图并运行
            graph = create_agent_graph()

            print("\n🤖 Agent正在分析...\n")

            for step in graph.stream(current_state):
                for node_name, node_output in step.items():
                    current_state = node_output
                    print(f"  ✓ {node_name} 完成")

            # 显示结果
            if current_state.get("summary"):
                print("\n📊 分析结果:")
                print(current_state["summary"][:1000])

            if current_state.get("plot_files"):
                print("\n📁 生成的图表:")
                for f in current_state["plot_files"]:
                    print(f"  - {f}")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except EOFError:
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
