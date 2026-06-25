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
from engine.cell_type import run_cell_type_annotation
from engine.clustering import compute_neighbors
from frontend.utils import save_uploaded_file, get_file_size, validate_h5ad_file, list_h5ad_files
from frontend.chat import explain_analysis, answer_question, create_chat_context


def main():
    """主函数"""
    # 注意：set_page_config 已在 streamlit_app.py 中调用，这里不再调用

    st.title("🧬 空间转录组智能分析平台")
    st.markdown("基于Scanpy的空间转录组数据分析工具，支持完整的分析流程。")

    # 初始化会话状态
    if "adata" not in st.session_state:
        st.session_state.adata = None
    if "file_path" not in st.session_state:
        st.session_state.file_path = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    # ============ 侧边栏 ============
    with st.sidebar:
        st.header("📁 数据上传")

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

        # 高级参数（折叠面板，默认收起）
        with st.expander("⚙️ 高级参数（可选）", expanded=False):
            st.caption("以下参数已按经验设好默认值，通常无需修改。")

            st.markdown("**质量控制**")
            qc_min_genes = st.slider("每细胞最少基因数", 50, 500, 200, key="qc_min_genes")
            qc_min_cells = st.slider("每基因最少细胞数", 1, 20, 3, key="qc_min_cells")
            qc_max_mito = st.slider("最大线粒体比例(%)", 5, 50, 20, key="qc_max_mito")

            st.markdown("**预处理**")
            pp_n_hvg = st.slider("高变基因数量", 500, 5000, 2000, step=100, key="pp_n_hvg")
            pp_n_pcs = st.slider("PCA主成分数", 10, 100, 50, step=5, key="pp_n_pcs")

            st.markdown("**聚类**")
            cl_method = st.selectbox("聚类方法", ["leiden", "louvain"], key="cl_method")
            st.caption("leiden更常用；louvain需要额外安装包，不可用时自动降级为leiden")

    # ============ 主区域 ============
    if st.session_state.adata is None:
        st.info("请在左侧边栏上传并加载数据文件")
        return

    adata = st.session_state.adata

    # 创建标签页
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🔍 质量控制",
        "⚙️ 预处理",
        "📊 降维聚类",
        "🧬 Marker基因",
        "🗺️ 空间可视化",
        "🏷️ 细胞注释",
        "💬 智能问答"
    ])

    # ---- 标签页1：质量控制 ----
    with tab1:
        st.subheader("🔍 质量控制")
        st.caption("过滤低质量细胞和基因，生成QC统计图表。使用侧边栏「高级参数」可调整过滤阈值。")

        if st.button("▶️ 运行质量控制", key="run_qc", type="primary"):
            with st.spinner("正在进行质量控制..."):
                try:
                    os.makedirs("storage/results/qc", exist_ok=True)
                    result = run_qc_pipeline(
                        adata,
                        params={
                            "min_genes": qc_min_genes,
                            "min_cells": qc_min_cells,
                            "max_pct_mito": qc_max_mito
                        },
                        output_dir="storage/results/qc"
                    )
                    st.session_state.adata = result["adata"]
                    st.success(f"✅ 质量控制完成！过滤前 {adata.shape[0]} 细胞 → 过滤后 {result['adata'].shape[0]} 细胞")

                    for plot_file in result.get("plot_files", []):
                        if os.path.exists(plot_file):
                            st.image(plot_file, caption=os.path.basename(plot_file))

                    st.session_state.analysis_result = {
                        "summary": f"质量控制完成。过滤前细胞数: {adata.shape[0]}，过滤后细胞数: {result['adata'].shape[0]}",
                        "plot_files": result.get("plot_files", [])
                    }
                except Exception as e:
                    st.error(f"❌ 质量控制失败: {e}")

    # ---- 标签页2：预处理 ----
    with tab2:
        st.subheader("⚙️ 数据预处理")
        st.caption("归一化、log转换、高变基因筛选、PCA降维。使用侧边栏「高级参数」可调整HVG数量和PCA主成分数。")

        if st.button("▶️ 运行预处理", key="run_preprocessing", type="primary"):
            with st.spinner("正在进行预处理..."):
                try:
                    result = run_preprocessing_pipeline(
                        adata,
                        params={"n_top_genes": pp_n_hvg, "n_pcs": pp_n_pcs}
                    )
                    st.session_state.adata = result["adata"]
                    n_hvg = result['summary'].get('n_hvg', 'N/A')
                    st.success(f"✅ 预处理完成！筛选出 {n_hvg} 个高变基因，使用 {pp_n_pcs} 个PCA主成分")

                    for plot_file in result.get("plot_files", []):
                        if os.path.exists(plot_file):
                            st.image(plot_file, caption=os.path.basename(plot_file))

                    st.session_state.analysis_result = {
                        "summary": f"预处理完成。筛选出 {n_hvg} 个高变基因，使用 {pp_n_pcs} 个PCA主成分。",
                        "plot_files": result.get("plot_files", [])
                    }
                except Exception as e:
                    st.error(f"❌ 预处理失败: {e}")

    # ---- 标签页3：降维聚类 ----
    with tab3:
        st.subheader("📊 降维聚类分析")
        st.caption("UMAP降维 + Leiden/Louvain聚类。聚类方法在侧边栏「高级参数」中设置。")

        resolution = st.slider(
            "聚类分辨率",
            0.1, 3.0, 1.0, step=0.1,
            help="值越大，分出的cluster越多。建议从1.0开始，根据结果调整。"
        )

        if st.button("▶️ 运行聚类", key="run_clustering", type="primary"):
            with st.spinner("正在进行降维聚类..."):
                try:
                    adata = compute_neighbors(adata)
                    adata = run_umap(adata)
                    adata = run_clustering(adata, method=cl_method, resolution=resolution)

                    actual_key = cl_method
                    if cl_method not in adata.obs.columns:
                        for key in ["leiden", "louvain"]:
                            if key in adata.obs.columns:
                                actual_key = key
                                break

                    st.session_state.adata = adata
                    n_clusters = adata.obs[actual_key].nunique()

                    if actual_key != cl_method:
                        st.success(f"✅ 聚类完成！{cl_method}不可用，已降级为{actual_key}。识别出 {n_clusters} 个clusters")
                    else:
                        st.success(f"✅ 聚类完成！识别出 {n_clusters} 个clusters")

                    os.makedirs("storage/results/clustering", exist_ok=True)
                    plot_files = generate_clustering_plots(adata, "storage/results/clustering", cluster_key=actual_key)

                    for plot_file in plot_files:
                        if os.path.exists(plot_file):
                            st.image(plot_file, caption=os.path.basename(plot_file))

                    st.session_state.analysis_result = {
                        "summary": f"降维聚类完成。使用{actual_key}方法，分辨率{resolution}，识别出 {n_clusters} 个clusters。",
                        "plot_files": plot_files
                    }
                except Exception as e:
                    st.error(f"❌ 聚类失败: {e}")

    # ---- 标签页4：Marker基因 ----
    with tab4:
        st.subheader("🧬 Marker基因分析")
        st.caption("鉴定每个cluster的特征基因，用于细胞类型推断。")

        actual_cluster_key = None
        for key in ["leiden", "louvain"]:
            if key in adata.obs.columns:
                actual_cluster_key = key
                break

        if actual_cluster_key is None:
            st.warning("⚠️ 请先运行聚类分析")
        else:
            n_markers = st.slider("展示Top Marker基因数", 5, 50, 10, key="n_markers_slider")

            if st.button("▶️ 查找Marker基因", key="find_markers", type="primary"):
                with st.spinner("正在查找Marker基因..."):
                    try:
                        adata = find_marker_genes(adata, cluster_key=actual_cluster_key, n_genes=n_markers * 10)
                        st.session_state.adata = adata
                        st.success("✅ Marker基因分析完成！")

                        top_markers = get_top_markers(adata, cluster_key=actual_cluster_key, n=n_markers)
                        markers_summary = ""
                        for cluster, genes in top_markers.items():
                            st.write(f"**{cluster}**: {', '.join(genes[:10])}")
                            markers_summary += f"Cluster {cluster}: {', '.join(genes[:5])}\n"

                        os.makedirs("storage/results/markers", exist_ok=True)
                        plot_file = plot_marker_dotplot(adata, cluster_key=actual_cluster_key, n_markers=n_markers, output_dir="storage/results/markers")

                        if plot_file and os.path.exists(plot_file):
                            st.image(plot_file, caption="Marker基因点图")

                        st.session_state.analysis_result = {
                            "summary": f"Marker基因分析完成。\n{markers_summary}",
                            "plot_files": [plot_file] if plot_file else []
                        }
                    except Exception as e:
                        st.error(f"❌ Marker基因分析失败: {e}")

    # ---- 标签页5：空间可视化 ----
    with tab5:
        st.subheader("🗺️ 空间可视化")
        st.caption("在组织空间坐标上展示细胞分布和cluster定位。")

        use_3d = st.checkbox("使用3D可视化", value=True, key="use_3d")

        if st.button("▶️ 生成空间分布图", key="plot_spatial", type="primary"):
            with st.spinner("正在生成空间可视化..."):
                try:
                    os.makedirs("storage/results/spatial", exist_ok=True)
                    plot_files = []

                    plot_file = plot_spatial_distribution(adata, "storage/results/spatial", use_3d=use_3d)
                    if plot_file and os.path.exists(plot_file):
                        st.image(plot_file, caption="细胞空间分布图")
                        plot_files.append(plot_file)

                    actual_cluster_key = None
                    for key in ["leiden", "louvain"]:
                        if key in adata.obs.columns:
                            actual_cluster_key = key
                            break

                    if actual_cluster_key:
                        plot_file = plot_cluster_spatial(adata, "storage/results/spatial", cluster_key=actual_cluster_key, use_3d=use_3d)
                        if plot_file and os.path.exists(plot_file):
                            st.image(plot_file, caption="Cluster空间分布图")
                            plot_files.append(plot_file)

                    st.success(f"✅ 空间可视化完成！生成了 {len(plot_files)} 个图表")

                    st.session_state.analysis_result = {
                        "summary": f"空间可视化完成。生成了 {len(plot_files)} 个空间分布图。",
                        "plot_files": plot_files
                    }
                except Exception as e:
                    st.error(f"❌ 空间可视化失败: {e}")

    # ---- 标签页6：细胞类型注释 ----
    with tab6:
        st.subheader("🏷️ 细胞类型自动注释")
        st.caption("基于CellTypist参考数据集或Marker基因规则，自动推断细胞类型。")

        actual_cluster_key = None
        for key in ["leiden", "louvain"]:
            if key in adata.obs.columns:
                actual_cluster_key = key
                break

        if actual_cluster_key is None:
            st.warning("⚠️ 请先运行聚类分析")
        else:
            col1, col2 = st.columns(2)
            with col1:
                ct_method = st.selectbox(
                    "注释方法",
                    options=["auto", "celltypist", "rule"],
                    index=0,
                    help="auto: 优先CellTypist，降级为规则; rule: 仅规则注释"
                )
            with col2:
                ct_model = st.selectbox(
                    "CellTypist模型",
                    options=["Immune_All_Low", "Immune_All_High", "Adult_Mouse_Brain"],
                    index=0,
                    help="选择参考数据集（仅celltypist方法有效）"
                )

            if st.button("▶️ 运行细胞类型注释", key="run_celltype", type="primary"):
                with st.spinner("正在进行细胞类型注释..."):
                    try:
                        os.makedirs("storage/results/cell_type", exist_ok=True)
                        result = run_cell_type_annotation(
                            adata,
                            method=ct_method,
                            model_name=ct_model,
                            output_dir="storage/results/cell_type"
                        )
                        st.session_state.adata = result["adata"]

                        summary = result.get("summary", {})
                        st.success(f"✅ 细胞类型注释完成！共识别 {summary.get('n_cell_types', 'N/A')} 种细胞类型（方法: {summary.get('method', 'N/A')}）")

                        cluster_mapping = summary.get("cluster_mapping", {})
                        if cluster_mapping:
                            st.write("**Cluster → 细胞类型映射:**")
                            for cluster, cell_type in cluster_mapping.items():
                                st.write(f"  - Cluster {cluster}: **{cell_type}**")

                        for plot_file in result.get("plot_files", []):
                            if os.path.exists(plot_file):
                                st.image(plot_file, caption=os.path.basename(plot_file))

                        st.session_state.analysis_result = {
                            "summary": f"细胞类型注释完成。方法: {summary.get('method', 'N/A')}，共 {summary.get('n_cell_types', 'N/A')} 种细胞类型。",
                            "plot_files": result.get("plot_files", [])
                        }
                    except Exception as e:
                        st.error(f"❌ 细胞类型注释失败: {e}")

    # ---- 标签页7：智能问答 ----
    with tab7:
        st.subheader("💬 智能问答")
        st.info("💡 基于LLM的智能问答，可以解释分析结果、回答关于数据的问题。")

        if st.session_state.messages:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("问我关于分析结果的问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    if st.session_state.analysis_result:
                        context = create_chat_context(st.session_state.analysis_result)
                        response = answer_question(prompt, context)
                    else:
                        response = "⚠️ 请先运行一些分析，然后才能提问。"
                    st.markdown(response)

            st.session_state.messages.append({"role": "assistant", "content": response})

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
