"""
LLM对话模块

提供基于LLM的智能对话功能，用于解释分析结果。
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def get_llm():
    """获取LLM实例"""
    try:
        from langchain_openai import ChatOpenAI

        # 优先从 Streamlit secrets 读取（云端部署）
        api_key = None
        base_url = None
        model = None

        try:
            import streamlit as st
            if hasattr(st, 'secrets'):
                api_key = st.secrets.get("LLM_API_KEY")
                base_url = st.secrets.get("LLM_BASE_URL", "https://api.openai.com/v1")
                model = st.secrets.get("LLM_MODEL", "gpt-4")
        except Exception:
            pass

        # 降级到环境变量（本地开发）
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("LLM_API_KEY")
            base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("LLM_MODEL", "gpt-4")

        if not api_key:
            return None

        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.7,
            timeout=30
        )
        return llm
    except Exception as e:
        logger.warning(f"LLM初始化失败: {e}")
        return None


def create_analysis_explainer_prompt(analysis_summary: str, plot_files: List[str]) -> str:
    """
    创建分析结果解释的Prompt

    Args:
        analysis_summary: 分析摘要
        plot_files: 生成的图表文件列表

    Returns:
        Prompt字符串
    """
    plot_list = "\n".join([f"- {f}" for f in plot_files[:10]])  # 最多显示10个

    return f"""你是一个空间转录组数据分析专家。请基于以下分析结果，用简洁清晰的语言解释分析发现。

## 分析摘要
{analysis_summary}

## 生成的图表
{plot_list}

## 要求
1. 用通俗易懂的语言解释主要发现
2. 说明每个图表代表什么
3. 指出数据的质量和可靠性
4. 不要编造生物学结论，只基于数据说话
5. 如果发现异常，指出可能的原因

请用中文回答，格式清晰，使用适当的emoji增强可读性。"""


def create_qa_prompt(question: str, context: str) -> str:
    """
    创建问答Prompt

    Args:
        question: 用户问题
        context: 分析上下文

    Returns:
        Prompt字符串
    """
    return f"""你是一个空间转录组数据分析专家。请基于以下分析上下文回答用户的问题。

## 分析上下文
{context}

## 用户问题
{question}

## 回答要求
1. 基于数据分析事实回答
2. 不要编造生物学结论
3. 如果信息不足，诚实说明
4. 用中文回答，简洁明了"""


def explain_analysis(analysis_summary: str, plot_files: List[str]) -> str:
    """
    使用LLM解释分析结果

    Args:
        analysis_summary: 分析摘要
        plot_files: 生成的图表文件列表

    Returns:
        解释文本
    """
    llm = get_llm()

    if llm is None:
        # 如果LLM不可用，返回基于规则的解释
        return generate_rule_based_explanation(analysis_summary, plot_files)

    try:
        from langchain_core.messages import HumanMessage

        prompt = create_analysis_explainer_prompt(analysis_summary, plot_files)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        logger.warning(f"LLM解释失败: {e}")
        return generate_rule_based_explanation(analysis_summary, plot_files)


def generate_rule_based_explanation(analysis_summary: str, plot_files: List[str]) -> str:
    """
    基于规则的解释（LLM不可用时的备选方案）

    Args:
        analysis_summary: 分析摘要
        plot_files: 图表文件列表

    Returns:
        解释文本
    """
    explanation = "## 📊 分析结果解读\n\n"

    # 解析摘要中的关键信息
    if "细胞" in analysis_summary or "cells" in analysis_summary.lower():
        explanation += "### 📈 数据规模\n"
        explanation += "数据包含一定数量的细胞和基因，适合进行空间转录组分析。\n\n"

    if "质量控制" in analysis_summary or "qc" in analysis_summary.lower():
        explanation += "### 🔍 质量控制\n"
        explanation += "经过质量控制过滤，去除了低质量细胞和基因，确保后续分析的可靠性。\n\n"

    if "聚类" in analysis_summary or "cluster" in analysis_summary.lower():
        explanation += "### 🎯 聚类分析\n"
        explanation += "通过降维聚类识别出不同的细胞群体，每个群体可能代表不同的细胞类型或状态。\n\n"

    if "空间" in analysis_summary or "spatial" in analysis_summary.lower():
        explanation += "### 🗺️ 空间分布\n"
        explanation += "空间可视化展示了细胞在组织中的分布模式，有助于理解组织结构。\n\n"

    # 图表说明
    if plot_files:
        explanation += "### 📁 生成的图表\n"
        explanation += "共生成了多个可视化图表，包括：\n"

        categories = {
            "qc": "质量控制图表",
            "clustering": "降维聚类图表",
            "spatial": "空间分布图表",
            "marker": "Marker基因图表"
        }

        for category, desc in categories.items():
            category_files = [f for f in plot_files if category in f.lower()]
            if category_files:
                explanation += f"- **{desc}**: {len(category_files)} 张\n"

        explanation += "\n"

    explanation += "---\n"
    explanation += "💡 **提示**: 以上解释基于数据分析结果，如需更深入的生物学解读，请咨询相关领域专家。"

    return explanation


def answer_question(question: str, context: str) -> str:
    """
    回答用户关于分析结果的问题

    Args:
        question: 用户问题
        context: 分析上下文

    Returns:
        回答文本
    """
    llm = get_llm()

    if llm is None:
        return "⚠️ LLM服务未配置。请在.env文件中设置LLM_API_KEY以启用智能问答功能。"

    try:
        from langchain_core.messages import HumanMessage

        prompt = create_qa_prompt(question, context)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        logger.warning(f"LLM问答失败: {e}")
        return f"❌ 问答失败: {str(e)}"


def create_chat_context(result: dict) -> str:
    """
    从分析结果创建对话上下文

    Args:
        result: Agent返回的结果

    Returns:
        上下文字符串
    """
    context_parts = []

    # 添加分析摘要
    if result.get("summary"):
        context_parts.append(f"## 分析摘要\n{result['summary']}")

    # 添加执行计划
    if result.get("plan"):
        context_parts.append("## 执行步骤")
        for step in result["plan"]:
            status = step.get("status", "pending")
            func = step.get("function", "")
            desc = step.get("description", "")
            context_parts.append(f"- [{status}] {desc} ({func})")

    # 添加关键结果
    if result.get("results"):
        context_parts.append("## 关键结果")
        for key, value in result["results"].items():
            if isinstance(value, dict):
                if "n_cells" in value:
                    context_parts.append(f"- 细胞数: {value['n_cells']}")
                if "n_clusters" in value:
                    context_parts.append(f"- 聚类数: {value['n_clusters']}")

    # 添加图表列表
    if result.get("plot_files"):
        context_parts.append(f"## 图表\n共生成 {len(result['plot_files'])} 个图表")

    return "\n\n".join(context_parts)
