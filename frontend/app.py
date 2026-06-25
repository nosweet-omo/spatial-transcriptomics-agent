"""
空间转录组智能分析平台 - Streamlit主应用

基于LangGraph的空间转录组数据分析Agent，支持自然语言驱动的完整分析流程。
"""

import sys
import os
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.components import (
    render_page_header,
    render_file_uploader,
    render_analysis_params,
    render_skill_selector,
    render_natural_language_input,
    render_progress_bar,
    render_chat_history,
    render_plot_gallery,
    render_analysis_summary,
    render_data_overview,
    render_download_button,
)
from frontend.utils import get_output_dir
from frontend.chat import explain_analysis, answer_question, create_chat_context

from agent.graph import run_agent
from agent.skills import list_skills, get_skill
from engine import get_data_summary, load_h5ad


@st.cache_resource
def load_data_cached(file_path: str):
    """缓存加载的h5ad数据，避免重复读取"""
    return load_h5ad(file_path)


def initialize_session_state():
    """初始化Streamlit会话状态"""
    if "file_path" not in st.session_state:
        st.session_state.file_path = None
    if "data_summary" not in st.session_state:
        st.session_state.data_summary = None
    if "result" not in st.session_state:
        st.session_state.result = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = None


def run_analysis(user_input: str, file_path: str, params: dict, skill_name: str = None):
    """
    运行分析

    Args:
        user_input: 用户输入
        file_path: 文件路径
        params: 分析参数
        skill_name: Skill名称
    """
    # 准备参数
    analysis_params = {
        "run_qc": {
            "min_genes": params.get("min_genes", 200),
            "min_cells": params.get("min_cells", 3),
            "max_pct_mito": params.get("max_pct_mito", 20.0),
        },
        "run_preprocessing": {
            "n_top_genes": params.get("n_top_genes", 2000),
            "n_pcs": params.get("n_pcs", 50),
        },
        "run_clustering_analysis": {
            "method": params.get("cluster_method", "leiden"),
            "resolution": params.get("resolution", 1.0),
        },
        "generate_spatial_plots": {
            "use_3d": params.get("use_3d", True),
        },
        "annotate_cell_types": {
            "method": params.get("cell_type_method", "auto"),
            "model_name": params.get("cell_type_model", "Immune_All_Low"),
        }
    }

    # 运行Agent
    result = run_agent(
        user_input=user_input,
        file_path=file_path,
        output_dir=get_output_dir(),
        params=analysis_params,
        skill_name=skill_name
    )

    return result


def render_chat_section():
    """渲染LLM对话区域"""
    st.subheader("💬 智能问答")

    # 显示对话历史
    if st.session_state.messages:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 用户输入
    if prompt := st.chat_input("问我关于分析结果的问题..."):
        # 添加用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成回答
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                if st.session_state.chat_context:
                    response = answer_question(prompt, st.session_state.chat_context)
                else:
                    response = "⚠️ 请先运行分析，然后才能提问。"
                st.markdown(response)

        # 添加助手消息
        st.session_state.messages.append({"role": "assistant", "content": response})


def main():
    """主函数"""
    # 注意：set_page_config 已在 streamlit_app.py 中调用，这里不再调用

    # 初始化会话状态
    initialize_session_state()

    # 渲染页面标题
    render_page_header()

    # 侧边栏
    with st.sidebar:
        st.header("设置")

        # 文件上传
        file_path = render_file_uploader()
        if file_path:
            st.session_state.file_path = file_path

        # 数据概览（使用缓存避免重复加载）
        if st.session_state.file_path:
            try:
                adata = load_data_cached(st.session_state.file_path)
                st.session_state.data_summary = get_data_summary(adata)
            except Exception as e:
                st.error(f"加载数据失败: {e}")

        # 显示数据概览
        render_data_overview(st.session_state.data_summary)

        # 分析参数
        params = render_analysis_params()

        # Skill选择
        skill_name = render_skill_selector()

    # 主区域 - 使用标签页
    tab1, tab2 = st.tabs(["🔬 分析工作区", "💬 智能问答"])

    with tab1:
        st.header("分析工作区")

        # 自然语言输入
        user_input = render_natural_language_input()

        # 运行按钮
        if st.button("🚀 运行分析", type="primary", use_container_width=True):
            if not st.session_state.file_path:
                st.error("请先上传数据文件")
            elif not user_input:
                st.error("请输入分析请求")
            else:
                # 添加用户消息到历史
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"🔬 分析请求: {user_input}"
                })

                # 运行分析
                with st.spinner("🤖 Agent正在分析..."):
                    try:
                        result = run_analysis(
                            user_input=user_input,
                            file_path=st.session_state.file_path,
                            params=params,
                            skill_name=skill_name
                        )

                        st.session_state.result = result

                        # 创建对话上下文
                        st.session_state.chat_context = create_chat_context(result)

                        # 使用LLM解释分析结果
                        if result and result.get("summary"):
                            with st.spinner("📝 正在生成分析解读..."):
                                explanation = explain_analysis(
                                    result.get("summary", ""),
                                    result.get("plot_files", [])
                                )

                            # 添加助手消息到历史
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": explanation
                            })

                        st.success("✅ 分析完成！")

                    except Exception as e:
                        st.error(f"❌ 分析失败: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        # 显示结果
        if st.session_state.result:
            result = st.session_state.result

            # 对话历史
            if st.session_state.messages:
                render_chat_history(st.session_state.messages)

            # 图表展示
            plot_files = result.get("plot_files", [])
            render_plot_gallery(plot_files)

            # 分析摘要
            summary = result.get("summary", "")
            render_analysis_summary(summary)

            # 下载按钮
            render_download_button(summary, plot_files)

            # 显示执行计划（可选）
            with st.expander("📋 执行计划详情", expanded=False):
                plan = result.get("plan", [])
                if plan:
                    for step in plan:
                        status = step.get("status", "pending")
                        function = step.get("function", "")
                        description = step.get("description", "")

                        if status == "completed":
                            st.success(f"✅ {step.get('step', '')}. {description}")
                        elif status == "failed":
                            st.error(f"❌ {step.get('step', '')}. {description}: {step.get('error', '')}")
                        elif status == "skipped":
                            st.warning(f"⏭️ {step.get('step', '')}. {description}: {step.get('error', '')}")
                        else:
                            st.info(f"⏳ {step.get('step', '')}. {description}")

    with tab2:
        render_chat_section()

    # 页脚
    st.divider()
    st.caption("空间转录组智能分析平台 | Powered by LangGraph + Streamlit")


if __name__ == "__main__":
    main()
