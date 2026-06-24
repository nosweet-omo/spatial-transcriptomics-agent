"""
前端UI组件模块

提供可复用的Streamlit UI组件。
"""

import os
import streamlit as st
from typing import Dict, Any, List, Optional

from frontend.utils import (
    save_uploaded_file,
    get_file_size,
    validate_h5ad_file,
    list_h5ad_files,
    get_output_dir,
)


def render_page_header():
    """渲染页面标题和描述"""
    st.set_page_config(
        page_title="空间转录组智能分析平台",
        page_icon="🧬",
        layout="wide"
    )

    st.title("🧬 空间转录组智能分析平台")
    st.markdown("""
    基于LangGraph的空间转录组数据分析Agent，支持自然语言驱动的完整分析流程。

    **功能特点**：
    - 自然语言输入，自动规划分析流程
    - 智能质量控制、预处理、聚类分析
    - 空间可视化和Marker基因分析
    - 细胞类型自动注释（CellTypist / 规则降级）
    - 支持多种预定义分析流程（Skill）
    """)


def render_file_uploader() -> Optional[str]:
    """
    渲染文件上传组件

    Returns:
        上传文件的路径，如果没有上传文件返回None
    """
    st.subheader("📁 数据上传")

    # 文件上传
    uploaded_file = st.file_uploader(
        "上传h5ad格式的空间转录组数据",
        type=["h5ad", "h5"],
        help="支持.h5ad和.h5格式的空间转录组数据文件"
    )

    if uploaded_file is not None:
        # 验证文件
        file_path = save_uploaded_file(uploaded_file)
        validation = validate_h5ad_file(file_path)

        if validation["is_valid"]:
            st.success(f"✅ 文件已上传: {uploaded_file.name}")
            st.info(f"📊 文件大小: {get_file_size(file_path)}")
            return file_path
        else:
            st.error(f"❌ 文件验证失败: {validation['error']}")
            return None

    # 显示已上传的文件列表
    existing_files = list_h5ad_files()
    if existing_files:
        st.info("📁 已上传的文件:")
        selected_file = st.selectbox(
            "选择已有文件",
            options=existing_files,
            format_func=lambda x: os.path.basename(x),
            key="existing_file_select"
        )
        if selected_file:
            return selected_file

    return None


def render_analysis_params() -> Dict[str, Any]:
    """
    渲染分析参数调整面板

    Returns:
        参数字典
    """
    st.subheader("⚙️ 分析参数")

    params = {}

    with st.expander("质量控制参数", expanded=False):
        params["min_genes"] = st.slider(
            "每细胞最少基因数",
            min_value=50,
            max_value=500,
            value=200,
            help="过滤掉基因数少于此值的细胞"
        )
        params["min_cells"] = st.slider(
            "每基因最少细胞数",
            min_value=1,
            max_value=20,
            value=3,
            help="过滤掉表达细胞数少于此值的基因"
        )
        params["max_pct_mito"] = st.slider(
            "最大线粒体基因比例(%)",
            min_value=5,
            max_value=50,
            value=20,
            help="过滤线粒体基因比例超过此值的细胞"
        )

    with st.expander("预处理参数", expanded=False):
        params["n_top_genes"] = st.slider(
            "高变基因数量",
            min_value=500,
            max_value=5000,
            value=2000,
            step=100,
            help="筛选的高变基因数量"
        )
        params["n_pcs"] = st.slider(
            "PCA主成分数量",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
            help="PCA降维的主成分数量"
        )

    with st.expander("聚类参数", expanded=False):
        params["cluster_method"] = st.selectbox(
            "聚类方法",
            options=["leiden", "louvain"],
            index=0,
            help="选择聚类算法"
        )
        params["resolution"] = st.slider(
            "聚类分辨率",
            min_value=0.1,
            max_value=3.0,
            value=1.0,
            step=0.1,
            help="分辨率越高，聚类数越多"
        )

    with st.expander("可视化参数", expanded=False):
        params["use_3d"] = st.checkbox(
            "使用3D可视化",
            value=True,
            help="如果数据包含z坐标，启用3D可视化"
        )

    with st.expander("细胞类型注释参数", expanded=False):
        params["cell_type_method"] = st.selectbox(
            "注释方法",
            options=["auto", "celltypist", "rule"],
            index=0,
            help="auto: 优先CellTypist，降级为规则; celltypist: 强制CellTypist; rule: 仅规则注释"
        )
        params["cell_type_model"] = st.selectbox(
            "CellTypist模型",
            options=["Immune_All_Low", "Immune_All_High", "Adult_Mouse_Brain"],
            index=0,
            help="选择CellTypist预训练模型（仅celltypist方法有效）"
        )

    return params


def render_skill_selector() -> Optional[str]:
    """
    渲染Skill选择器

    Returns:
        选择的Skill名称，如果没有选择返回None
    """
    st.subheader("🎯 分析流程")

    from agent.skills import list_skills

    skills = list_skills()

    skill_options = {skill["name"]: skill["description"] for skill in skills}

    selected_skill = st.selectbox(
        "选择预定义分析流程",
        options=["自定义"] + list(skill_options.keys()),
        format_func=lambda x: skill_options.get(x, x),
        help="选择预定义的分析流程，或使用自定义模式"
    )

    if selected_skill == "自定义":
        return None

    return selected_skill


def render_natural_language_input() -> str:
    """
    渲染自然语言输入框

    Returns:
        用户输入的文本
    """
    st.subheader("💬 分析请求")

    # 快捷命令
    st.info("💡 快捷命令:")
    col1, col2, col3, col4 = st.columns(4)

    quick_commands = []
    with col1:
        if st.button("🔍 快速预览", key="cmd_preview"):
            quick_commands.append("快速预览数据")
    with col2:
        if st.button("📊 完整分析", key="cmd_full"):
            quick_commands.append("帮我进行完整的空间转录组分析")
    with col3:
        if st.button("🧬 Marker基因", key="cmd_marker"):
            quick_commands.append("分析Marker基因")
    with col4:
        if st.button("🏷️ 细胞注释", key="cmd_celltype"):
            quick_commands.append("进行细胞类型注释")

    # 自然语言输入
    user_input = st.text_area(
        "输入您的分析请求",
        placeholder="例如：帮我分析这个空间转录组数据，进行质量控制、聚类分析和空间可视化",
        height=100,
        help="可以用自然语言描述您想要进行的分析"
    )

    # 如果点击了快捷命令，使用快捷命令
    if quick_commands:
        return quick_commands[0]

    return user_input


def render_progress_bar(progress: float, status: str):
    """
    渲染进度条

    Args:
        progress: 进度值 (0-1)
        status: 状态文本
    """
    st.progress(progress)
    st.text(status)


def render_chat_history(messages: List[Dict[str, str]]):
    """
    渲染对话历史

    Args:
        messages: 消息列表
    """
    st.subheader("💬 对话历史")

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "user":
            st.chat_message("user").markdown(content)
        else:
            st.chat_message("assistant").markdown(content)


def render_plot_gallery(plot_files: List[str]):
    """
    渲染图表画廊

    Args:
        plot_files: 图表文件路径列表
    """
    if not plot_files:
        st.info("暂无图表")
        return

    st.subheader(f"📊 生成的图表 ({len(plot_files)} 个)")

    # 过滤存在的文件
    existing_files = [f for f in plot_files if os.path.exists(f)]

    if not existing_files:
        st.warning("图表文件不存在")
        return

    # 以网格形式展示
    cols_per_row = 2
    for i in range(0, len(existing_files), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(existing_files):
                plot_file = existing_files[idx]
                with col:
                    st.image(
                        plot_file,
                        caption=os.path.basename(plot_file),
                        use_container_width=True
                    )


def render_analysis_summary(summary: str):
    """
    渲染分析摘要

    Args:
        summary: Markdown格式的分析摘要
    """
    st.subheader("📝 分析摘要")

    if summary:
        st.markdown(summary)
    else:
        st.info("暂无分析摘要")


def render_data_overview(data_summary: Dict[str, Any]):
    """
    渲染数据概览

    Args:
        data_summary: 数据摘要字典
    """
    st.subheader("📊 数据概览")

    if not data_summary:
        st.info("请先上传数据文件")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("细胞数", data_summary.get("n_cells", "N/A"))
    with col2:
        st.metric("基因数", data_summary.get("n_genes", "N/A"))
    with col3:
        st.metric("空间坐标", "✅" if data_summary.get("has_spatial") else "❌")


def render_download_button(summary: str, plot_files: List[str]):
    """
    渲染下载按钮

    Args:
        summary: 分析摘要
        plot_files: 图表文件路径列表
    """
    st.subheader("💾 下载结果")

    col1, col2 = st.columns(2)

    with col1:
        if summary:
            st.download_button(
                label="📄 下载分析报告",
                data=summary,
                file_name="analysis_report.md",
                mime="text/markdown"
            )

    with col2:
        if plot_files:
            st.info(f"共 {len(plot_files)} 个图表文件")
            # 这里可以添加打包下载功能
