"""
Agent模块

空间转录组智能分析平台的Agent层。

核心设计思想：
1. 节点设计：不同节点承担不同功能
2. 边与流程控制：根据任务状态决定下一步
3. 状态管理：维护分析过程中的所有上下文
4. 循环机制：支持"规划—执行—检查—修正"的多步流程
"""

from agent.state import AgentState, create_initial_state
from agent.graph import create_agent_graph, run_agent, run_agent_interactive
from agent.tools import get_all_tools, get_tools_description
from agent.skills import (
    Skill,
    SkillStep,
    get_skill,
    list_skills,
    get_skills_description,
    skill_to_plan,
    parse_skill_from_natural_language,
    execute_skill,
)

__all__ = [
    # 状态
    "AgentState",
    "create_initial_state",
    # 图
    "create_agent_graph",
    "run_agent",
    "run_agent_interactive",
    # 工具
    "get_all_tools",
    "get_tools_description",
    # Skill
    "Skill",
    "SkillStep",
    "get_skill",
    "list_skills",
    "get_skills_description",
    "skill_to_plan",
    "parse_skill_from_natural_language",
    "execute_skill",
]
