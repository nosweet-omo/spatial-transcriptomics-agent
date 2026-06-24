"""
空间转录组智能分析平台 - 简化版Streamlit应用

直接使用engine层函数，避免Agent层的共享状态问题。
包含LLM对话功能。
"""

import sys
import os
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import (
    load_h5ad,
    get_data_summary,
    run_qc_pipeline,
    run_preprocessing_pipeline,
    run_pca,
    run_umap,
    run_clustering,
    generate_clustering_plots,
    find_marker_genes,
    get_top_markers,
    plot_marker_dotplot,
    plot_spatial_distribution,
    plot_cluster_spatial,
)
from engine.clustering import compute_neighbors
from frontend.utils import save_uploaded_file, get_file_size, validate_h5ad_file, list_h5ad_files
from frontend.chat import explain_analysis, answer_question, create_chat_context


def main():
    """主函数"""
    st.set_page_config(
        page_title="空间转录组智能分析平台",
        page_icon="🧬",
        layout="wide"
    )

    st.title("🧬 空间转录组智能分析平台")
    st.markdown("""
    基于Scanpy的空间转录组数据分析工具，支持完整的分析流程。

    **功能特点**：
    - 数据质量控制
    - 数据预处理
    - 降维聚类分析
    - 空间可视化
    - Marker基因分析
    - 💬 LLM智能问答
    """)

    # 初始化会话状态
    if "adata" not in st.session_state:
        st.session_state.adata = None
    if "file_path" not in st.session_state:
        st.session_state.file_path = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    # 侧边栏
    with st.sidebar:
        st.header("📁 数据上传")

        # 文件上传
        uploaded_file = st.file_uploader(
            "上传h5ad格式的空间转录组数据",
            type=["h5ad", "h5"],
            help="支持.h5ad和.h5格式的空间转录组数据文件"
        )

        if uploaded_file is not None:
            file_path = save_uploaded_file(uploaded_file)
            validation = validate_h5ad_file(file_path)

            if validation["is_valid"]:
                st.success(f"✅ 文件已上传: {uploaded_file.name}")
                st.info(f"📊 文件大小: {get_file_size(file_path)}")

                if st.button("📥 加载数据", type="primary"):
                    with st.spinner("正在加载数据..."):
                        try:
                            adata = load_h5ad(file_path)
                            st.session_state.adata = adata
                            st.session_state.file_path = file_path
                            st.success("✅ 数据加载成功！")
                        except Exception as e:
                            st.error(f"❌ 加载失败: {e}")
            else:
                st.error(f"❌ 文件验证失败: {validation['error']}")

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
            if st.button("📥 加载选中文件"):
                with st.spinner("正在加载数据..."):
                    try:
                        adata = load_h5ad(selected_file)
                        st.session_state.adata = adata
                        st.session_state.file_path = selected_file
                        st.success("✅ 数据加载成功！")
                    except Exception as e:
                        st.error(f"❌ 加载失败: {e}")

        # 数据概览
        if st.session_state.adata is not None:
            st.subheader("📊 数据概览")
            summary = get_data_summary(st.session_state.adata)
            st.metric("细胞数", summary.get("n_cells", "N/A"))
            st.metric("基因数", summary.get("n_genes", "N/A"))
            st.metric("空间坐标", "✅" if summary.get("has_spatial") else "❌")

    # 主区域
    if st.session_state.adata is None:
        st.info("请在左侧边栏上传并加载数据文件")
        return

    adata = st.session_state.adata

    # 创建标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔍 质量控制",
        "⚙️ 预处理",
        "📊 降维聚类",
        "🧬 Marker基因",
        "🗺️ 空间可视化",
        "💬 智能问答"
    ])

    # 标签页1：质量控制
    with tab1:
        st.subheader("🔍 质量控制")

        col1, col2 = st.columns(2)
        with col1:
            min_genes = st.slider("每细胞最少基因数", 50, 500, 200)
        with col2:
            max_pct_mito = st.slider("最大线粒体基因比例(%)", 5, 50, 20)

        if st.button("运行质量控制", key="run_qc"):
            with st.spinner("正在进行质量控制..."):
                try:
                    os.makedirs("storage/results/qc", exist_ok=True)
                    result = run_qc_pipeline(
                        adata,
                        params={"min_genes": min_genes, "max_pct_mito": max_pct_mito},
                        output_dir="storage/results/qc"
                    )
                    st.session_state.adata = result["adata"]
                    st.success("✅ 质量控制完成！")

                    # 显示图表
                    for plot_file in result.get("plot_files", []):
                        if os.path.exists(plot_file):
                            st.image(plot_file, caption=os.path.basename(plot_file))

                    # 保存分析结果用于问答
                    st.session_state.analysis_result = {
                        "summary": f"质量控制完成。过滤前细胞数: {adata.shape[0]}，过滤后细胞数: {result['adata'].shape[0]}",
                        "plot_files": result.get("plot_files", [])
                    }

                except Exception as e:
                    st.error(f"❌ 质量控制失败: {e}")

    # 标签页2：预处理
    with tab2:
        st.subheader("⚙️ 数据预处理")

        col1, col2 = st.columns(2)
        with col1:
            n_top_genes = st.slider("高变基因数量", 500, 5000, 2000, step=100)
        with col2:
            n_pcs = st.slider("PCA主成分数量", 10, 100, 50, step=5)

        if st.button("运行预处理", key="run_preprocessing"):
            with st.spinner("正在进行预处理..."):
                try:
                    result = run_preprocessing_pipeline(
                        adata,
                        params={"n_top_genes": n_top_genes, "n_pcs": n_pcs}
                    )
                    st.session_state.adata = result["adata"]
                    st.success("✅ 预处理完成！")
                    st.info(f"筛选出 {result['summary'].get('n_hvg', 'N/A')} 个高变基因")

                    # 保存分析结果
                    st.session_state.analysis_result = {
                        "summary": f"预处理完成。筛选出 {result['summary'].get('n_hvg', 'N/A')} 个高变基因，使用 {n_pcs} 个PCA主成分。",
                        "plot_files": result.get("plot_files", [])
                    }

                except Exception as e:
                    st.error(f"❌ 预处理失败: {e}")

    # 标签页3：降维聚类
    with tab3:
        st.subheader("📊 降维聚类分析")

        col1, col2 = st.columns(2)
        with col1:
            cluster_method = st.selectbox("聚类方法", ["leiden", "louvain"])
        with col2:
            resolution = st.slider("聚类分辨率", 0.1, 3.0, 1.0, step=0.1)

        if st.button("运行聚类", key="run_clustering"):
            with st.spinner("正在进行降维聚类..."):
                try:
                    # 计算邻域图
                    adata = compute_neighbors(adata)

                    # UMAP降维
                    adata = run_umap(adata)

                    # 聚类
                    adata = run_clustering(adata, method=cluster_method, resolution=resolution)

                    st.session_state.adata = adata
                    n_clusters = adata.obs[cluster_method].nunique()
                    st.success("✅ 聚类完成！")
                    st.info(f"识别出 {n_clusters} 个clusters")

                    # 生成图表
                    os.makedirs("storage/results/clustering", exist_ok=True)
                    plot_files = generate_clustering_plots(adata, "storage/results/clustering", cluster_key=cluster_method)

                    for plot_file in plot_files:
                        if os.path.exists(plot_file):
                            st.image(plot_file, caption=os.path.basename(plot_file))

                    # 保存分析结果
                    st.session_state.analysis_result = {
                        "summary": f"降维聚类完成。使用{cluster_method}方法，分辨率{resolution}，识别出 {n_clusters} 个clusters。",
                        "plot_files": plot_files
                    }

                except Exception as e:
                    st.error(f"❌ 聚类失败: {e}")

    # 标签页4：Marker基因
    with tab4:
        st.subheader("🧬 Marker基因分析")

        if "leiden" not in adata.obs.columns and "louvain" not in adata.obs.columns:
            st.warning("请先运行聚类分析")
        else:
            cluster_key = "leiden" if "leiden" in adata.obs.columns else "louvain"
            n_markers = st.slider("Marker基因数量", 5, 50, 10)

            if st.button("查找Marker基因", key="find_markers"):
                with st.spinner("正在查找Marker基因..."):
                    try:
                        adata = find_marker_genes(adata, cluster_key=cluster_key, n_genes=n_markers * 10)
                        st.session_state.adata = adata
                        st.success("✅ Marker基因分析完成！")

                        # 显示top markers
                        top_markers = get_top_markers(adata, cluster_key=cluster_key, n=n_markers)
                        st.write("**各Cluster的Top Marker基因：**")
                        markers_summary = ""
                        for cluster, genes in top_markers.items():
                            st.write(f"**{cluster}**: {', '.join(genes[:10])}")
                            markers_summary += f"Cluster {cluster}: {', '.join(genes[:5])}\n"

                        # 绘制图表
                        os.makedirs("storage/results/markers", exist_ok=True)
                        plot_file = plot_marker_dotplot(adata, cluster_key=cluster_key, n_markers=n_markers, output_dir="storage/results/markers")

                        if plot_file and os.path.exists(plot_file):
                            st.image(plot_file, caption="Marker基因点图")

                        # 保存分析结果
                        st.session_state.analysis_result = {
                            "summary": f"Marker基因分析完成。\n{markers_summary}",
                            "plot_files": [plot_file] if plot_file else []
                        }

                    except Exception as e:
                        st.error(f"❌ Marker基因分析失败: {e}")

    # 标签页5：空间可视化
    with tab5:
        st.subheader("🗺️ 空间可视化")

        use_3d = st.checkbox("使用3D可视化", value=True)

        if st.button("生成空间分布图", key="plot_spatial"):
            with st.spinner("正在生成空间可视化..."):
                try:
                    os.makedirs("storage/results/spatial", exist_ok=True)
                    plot_files = []

                    # 空间分布图
                    plot_file = plot_spatial_distribution(adata, "storage/results/spatial", use_3d=use_3d)
                    if plot_file and os.path.exists(plot_file):
                        st.image(plot_file, caption="细胞空间分布图")
                        plot_files.append(plot_file)

                    # Cluster空间图
                    if "leiden" in adata.obs.columns or "louvain" in adata.obs.columns:
                        cluster_key = "leiden" if "leiden" in adata.obs.columns else "louvain"
                        plot_file = plot_cluster_spatial(adata, "storage/results/spatial", cluster_key=cluster_key, use_3d=use_3d)
                        if plot_file and os.path.exists(plot_file):
                            st.image(plot_file, caption="Cluster空间分布图")
                            plot_files.append(plot_file)

                    st.success("✅ 空间可视化完成！")

                    # 保存分析结果
                    st.session_state.analysis_result = {
                        "summary": f"空间可视化完成。生成了 {len(plot_files)} 个空间分布图。",
                        "plot_files": plot_files
                    }

                except Exception as e:
                    st.error(f"❌ 空间可视化失败: {e}")

    # 标签页6：智能问答
    with tab6:
        st.subheader("💬 智能问答")
        st.info("💡 基于LLM的智能问答，可以解释分析结果、回答关于数据的问题。")

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
                    if st.session_state.analysis_result:
                        context = create_chat_context(st.session_state.analysis_result)
                        response = answer_question(prompt, context)
                    else:
                        response = "⚠️ 请先运行一些分析，然后才能提问。"
                    st.markdown(response)

            # 添加助手消息
            st.session_state.messages.append({"role": "assistant", "content": response})

        # 快捷问题按钮
        st.subheader("📌 快捷问题")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📊 解释分析结果"):
                if st.session_state.analysis_result:
                    with st.spinner("正在生成解读..."):
                        context = create_chat_context(st.session_state.analysis_result)
                        response = answer_question("请解释这次分析的主要结果", context)
                        st.session_state.messages.append({"role": "user", "content": "解释分析结果"})
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()
                else:
                    st.warning("请先运行分析")

        with col2:
            if st.button("🔍 数据质量如何"):
                if st.session_state.analysis_result:
                    with st.spinner("正在分析..."):
                        context = create_chat_context(st.session_state.analysis_result)
                        response = answer_question("这次分析的数据质量如何？有哪些需要注意的地方？", context)
                        st.session_state.messages.append({"role": "user", "content": "数据质量如何"})
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()
                else:
                    st.warning("请先运行分析")

        with col3:
            if st.button("📈 下一步建议"):
                if st.session_state.analysis_result:
                    with st.spinner("正在思考..."):
                        context = create_chat_context(st.session_state.analysis_result)
                        response = answer_question("基于当前分析结果，下一步可以做什么分析？", context)
                        st.session_state.messages.append({"role": "user", "content": "下一步建议"})
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()
                else:
                    st.warning("请先运行分析")


if __name__ == "__main__":
    main()
