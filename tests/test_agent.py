"""
Agent层单元测试

测试Agent的各个组件。
"""

import sys
import os
import json
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.state import AgentState, create_initial_state, PlanStep
from agent.tools import get_all_tools, get_tools_description
from agent.prompts import PLANNER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT
from agent.nodes.planner import create_default_plan, parse_plan_from_llm_response
from agent.nodes.executor import execute_step, TOOL_MAP
from agent.nodes.reviewer import generate_review_without_llm
from agent.nodes.error_handler import analyze_error
from agent.skills import (
    Skill,
    SkillStep,
    get_skill,
    list_skills,
    get_skills_description,
    skill_to_plan,
    parse_skill_from_natural_language,
    BASIC_ANALYSIS_WORKFLOW,
    QUALITY_CONTROL_SKILL,
    SKILL_REGISTRY,
)


class TestAgentState(unittest.TestCase):
    """测试AgentState"""

    def test_create_initial_state(self):
        """测试创建初始状态"""
        state = create_initial_state(
            user_input="分析这个h5ad文件",
            file_path="test.h5ad"
        )

        self.assertEqual(state["user_input"], "分析这个h5ad文件")
        self.assertEqual(state["file_path"], "test.h5ad")
        self.assertIsNone(state["adata"])
        self.assertEqual(state["current_step"], "init")
        self.assertEqual(state["completed_steps"], [])
        self.assertEqual(state["plan"], [])
        self.assertEqual(state["retry_count"], 0)
        self.assertEqual(state["max_retries"], 3)

    def test_plan_step(self):
        """测试PlanStep"""
        step = PlanStep(
            step=1,
            function="load_data",
            description="加载数据",
            params={"file_path": "test.h5ad"},
            status="pending",
            result=None,
            error=None
        )

        self.assertEqual(step["step"], 1)
        self.assertEqual(step["function"], "load_data")
        self.assertEqual(step["status"], "pending")


class TestPlanner(unittest.TestCase):
    """测试Planner节点"""

    def test_create_default_plan(self):
        """测试创建默认计划"""
        plan = create_default_plan("分析这个文件")

        self.assertEqual(len(plan), 6)
        self.assertEqual(plan[0]["function"], "load_data")
        self.assertEqual(plan[1]["function"], "run_qc")
        self.assertEqual(plan[2]["function"], "run_preprocessing")
        self.assertEqual(plan[3]["function"], "run_clustering_analysis")
        self.assertEqual(plan[4]["function"], "find_markers")
        self.assertEqual(plan[5]["function"], "generate_spatial_plots")

    def test_parse_plan_from_json(self):
        """测试从JSON解析计划"""
        response = """
```json
{
    "plan": [
        {"step": 1, "function": "load_data", "params": {}},
        {"step": 2, "function": "run_qc", "params": {"min_genes": 100}}
    ]
}
```
"""
        plan = parse_plan_from_llm_response(response)

        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["function"], "load_data")
        self.assertEqual(plan[1]["function"], "run_qc")
        self.assertEqual(plan[1]["params"]["min_genes"], 100)


class TestExecutor(unittest.TestCase):
    """测试Executor节点"""

    def test_tool_map_exists(self):
        """测试工具映射表存在"""
        self.assertIn("load_data", TOOL_MAP)
        self.assertIn("run_qc", TOOL_MAP)
        self.assertIn("run_preprocessing", TOOL_MAP)
        self.assertIn("run_clustering_analysis", TOOL_MAP)
        self.assertIn("find_markers", TOOL_MAP)
        self.assertIn("generate_spatial_plots", TOOL_MAP)

    def test_execute_unknown_function(self):
        """测试执行未知函数"""
        step = PlanStep(
            step=1,
            function="unknown_function",
            description="未知函数",
            params={},
            status="pending",
            result=None,
            error=None
        )

        state = create_initial_state("测试")
        result = execute_step(step, state)

        self.assertEqual(result["status"], "failed")
        self.assertIn("未知的函数", result["error"])


class TestReviewer(unittest.TestCase):
    """测试Reviewer节点"""

    def test_generate_review_without_data(self):
        """测试无数据时的解读"""
        review = generate_review_without_llm("load_data", None)
        self.assertIn("已完成", review)

    def test_generate_review_with_error(self):
        """测试有错误时的解读"""
        result = {"status": "error", "error": "文件不存在"}
        review = generate_review_without_llm("load_data", result)
        self.assertIn("失败", review)
        self.assertIn("文件不存在", review)

    def test_generate_review_with_success(self):
        """测试成功结果的解读"""
        result = {
            "status": "success",
            "n_clusters": 7,
            "plot_files": ["plot1.png", "plot2.png"]
        }
        review = generate_review_without_llm("generate_spatial_plots", result)
        self.assertIn("2", review)  # 2个图表


class TestErrorHandler(unittest.TestCase):
    """测试ErrorHandler节点"""

    def test_analyze_file_not_found(self):
        """测试分析文件不存在错误"""
        analysis = analyze_error("FileNotFoundError: file.h5ad", "load_data")
        self.assertEqual(analysis["action"], "abort")

    def test_analyze_memory_error(self):
        """测试分析内存错误"""
        analysis = analyze_error("MemoryError: out of memory", "run_clustering")
        self.assertEqual(analysis["action"], "skip")

    def test_analyze_value_error(self):
        """测试分析参数错误"""
        analysis = analyze_error("ValueError: invalid parameter", "run_qc")
        self.assertEqual(analysis["action"], "retry")

    def test_analyze_key_error(self):
        """测试分析列名不存在错误"""
        analysis = analyze_error("KeyError: 'column_name'", "run_clustering")
        self.assertEqual(analysis["action"], "skip")


class TestTools(unittest.TestCase):
    """测试工具集"""

    def test_get_all_tools(self):
        """测试获取所有工具"""
        tools = get_all_tools()
        self.assertEqual(len(tools), 19)

    def test_get_tools_description(self):
        """测试获取工具描述"""
        desc = get_tools_description()
        self.assertIn("load_data", desc)
        self.assertIn("run_qc", desc)
        self.assertIn("run_preprocessing", desc)


class TestPrompts(unittest.TestCase):
    """测试Prompt模板"""

    def test_planner_prompt(self):
        """测试Planner Prompt"""
        prompt = PLANNER_SYSTEM_PROMPT.format(tools_description="test tools")
        self.assertIn("test tools", prompt)
        self.assertIn("空间转录组", prompt)

    def test_reviewer_prompt(self):
        """测试Reviewer Prompt"""
        self.assertIn("中文", REVIEWER_SYSTEM_PROMPT)
        self.assertIn("生物学意义", REVIEWER_SYSTEM_PROMPT)


class TestSkills(unittest.TestCase):
    """测试Skill/Workflow模块"""

    def test_basic_analysis_workflow_exists(self):
        """测试基础分析Workflow存在"""
        self.assertIsNotNone(BASIC_ANALYSIS_WORKFLOW)
        self.assertEqual(BASIC_ANALYSIS_WORKFLOW.name, "basic_analysis_workflow")
        self.assertEqual(len(BASIC_ANALYSIS_WORKFLOW.steps), 6)

    def test_quality_control_skill_exists(self):
        """测试质量控制Skill存在"""
        self.assertIsNotNone(QUALITY_CONTROL_SKILL)
        self.assertEqual(QUALITY_CONTROL_SKILL.name, "quality_control_skill")

    def test_get_skill(self):
        """测试获取Skill"""
        skill = get_skill("basic_analysis")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, "basic_analysis_workflow")

        skill = get_skill("nonexistent")
        self.assertIsNone(skill)

    def test_list_skills(self):
        """测试列出所有Skill"""
        skills = list_skills()
        self.assertGreater(len(skills), 0)
        self.assertIn("name", skills[0])
        self.assertIn("description", skills[0])

    def test_get_skills_description(self):
        """测试获取Skill描述"""
        desc = get_skills_description()
        self.assertIn("basic_analysis", desc)
        self.assertIn("quality_control", desc)

    def test_skill_to_plan(self):
        """测试将Skill转换为执行计划"""
        plan = skill_to_plan(BASIC_ANALYSIS_WORKFLOW)

        self.assertEqual(len(plan), 6)
        self.assertEqual(plan[0]["function"], "load_data")
        self.assertEqual(plan[1]["function"], "run_qc")
        self.assertEqual(plan[2]["function"], "run_preprocessing")
        self.assertEqual(plan[3]["function"], "run_clustering_analysis")
        self.assertEqual(plan[4]["function"], "find_markers")
        self.assertEqual(plan[5]["function"], "generate_spatial_plots")

    def test_skill_to_plan_with_params(self):
        """测试带参数的Skill转换"""
        params = {"run_qc": {"min_genes": 100}}
        plan = skill_to_plan(BASIC_ANALYSIS_WORKFLOW, params)

        self.assertEqual(plan[1]["params"]["min_genes"], 100)

    def test_parse_skill_from_natural_language(self):
        """测试从自然语言解析Skill"""
        self.assertEqual(
            parse_skill_from_natural_language("快速预览数据"),
            "quick_preview"
        )
        self.assertEqual(
            parse_skill_from_natural_language("进行质量控制分析"),
            "quality_control"
        )
        self.assertEqual(
            parse_skill_from_natural_language("分析基因空间表达"),
            "gene_spatial"
        )
        self.assertEqual(
            parse_skill_from_natural_language("解释聚类结果"),
            "cluster_annotation"
        )
        self.assertEqual(
            parse_skill_from_natural_language("运行完整分析"),
            "basic_analysis"
        )

    def test_skill_registry(self):
        """测试Skill注册表"""
        self.assertIn("basic_analysis", SKILL_REGISTRY)
        self.assertIn("quality_control", SKILL_REGISTRY)
        self.assertIn("gene_spatial", SKILL_REGISTRY)
        self.assertIn("cluster_annotation", SKILL_REGISTRY)
        self.assertIn("quick_preview", SKILL_REGISTRY)

    def test_skill_step(self):
        """测试SkillStep"""
        step = SkillStep(
            name="test_step",
            tool_name="load_data",
            description="测试步骤",
            params={},
            required=True
        )

        self.assertEqual(step.name, "test_step")
        self.assertEqual(step.tool_name, "load_data")
        self.assertTrue(step.required)


class TestGraphStructure(unittest.TestCase):
    """测试图结构"""

    def test_graph_creation(self):
        """测试图创建"""
        from agent.graph import create_agent_graph

        graph = create_agent_graph()
        self.assertIsNotNone(graph)

    def test_graph_has_all_nodes(self):
        """测试图包含所有节点"""
        from agent.graph import create_agent_graph

        graph = create_agent_graph()
        # 检查图是否可以正常编译
        self.assertIsNotNone(graph)


if __name__ == "__main__":
    unittest.main()
