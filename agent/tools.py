"""
Agent工具集模块

将engine层的公共函数封装为LangChain Tool，供Agent调用。
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from functools import wraps

from langchain_core.tools import tool

# 导入engine层模块
from engine import (
    # 数据读取
    load_h5ad,
    get_data_summary,
    validate_data,
    # 质量控制
    calculate_qc_metrics,
    filter_cells,
    filter_mito,
    run_qc_pipeline,
    # 预处理
    normalize_data,
    log_transform,
    select_hvg,
    standardize_data,
    run_preprocessing_pipeline,
    # 降维聚类
    run_pca,
    run_umap,
    run_clustering,
    suggest_cluster_annotation,
    generate_clustering_plots,
    # 空间可视化
    plot_spatial_distribution,
    plot_cluster_spatial,
    plot_gene_spatial,
    plot_embedding,
    # Marker基因
    find_marker_genes,
    get_top_markers,
    plot_marker_heatmap,
    plot_marker_dotplot,
)

logger = logging.getLogger(__name__)


def get_adata_from_state() -> Any:
    """
    从共享状态获取当前的AnnData对象
    """
    from agent.shared_state import get_adata
    return get_adata()


def set_adata_to_state(adata: Any) -> None:
    """设置共享状态中的AnnData对象"""
    from agent.shared_state import set_adata
    set_adata(adata)


# ============ 数据读取工具 ============

@tool
def load_data(file_path: str) -> str:
    """
    加载h5ad格式的空间转录组数据文件

    Args:
        file_path: h5ad文件的路径

    Returns:
        JSON格式的数据概览信息
    """
    try:
        adata = load_h5ad(file_path)

        # 验证数据有效性
        validation = validate_data(adata)
        if not validation.get("is_valid", True):
            errors = validation.get("errors", [])
            return json.dumps({
                "status": "error",
                "error": f"数据验证失败: {'; '.join(errors)}"
            }, ensure_ascii=False)

        set_adata_to_state(adata)

        summary = get_data_summary(adata)

        result = {
            "status": "success",
            "file_path": file_path,
            "summary": summary,
            "validation": validation
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)


@tool
def get_data_info() -> str:
    """
    获取当前加载数据的概览信息

    Returns:
        JSON格式的数据概览
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "没有加载数据"}, ensure_ascii=False)

    summary = get_data_summary(adata)
    return json.dumps(summary, ensure_ascii=False, indent=2)


# ============ 质量控制工具 ============

@tool
def run_qc(
    min_genes: int = 200,
    min_cells: int = 3,
    max_pct_mito: float = 20.0,
    output_dir: Optional[str] = None
) -> str:
    """
    执行质量控制分析，包括：
    1. 计算QC指标（线粒体基因比例等）
    2. 过滤低质量细胞和基因
    3. 生成QC图表

    Args:
        min_genes: 每个细胞最少基因数
        min_cells: 每个基因最少细胞数
        max_pct_mito: 最大线粒体基因比例(%)
        output_dir: 图表输出目录

    Returns:
        JSON格式的QC结果摘要
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        params = {
            "min_genes": min_genes,
            "min_cells": min_cells,
            "max_pct_mito": max_pct_mito
        }

        result = run_qc_pipeline(adata, params=params, output_dir=output_dir)
        set_adata_to_state(result["adata"])

        return json.dumps({
            "status": "success",
            "summary": result.get("summary", {}),
            "plot_files": result.get("plot_files", [])
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def calculate_qc() -> str:
    """
    仅计算QC指标，不进行过滤

    Returns:
        JSON格式的QC指标摘要
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = calculate_qc_metrics(adata)
        set_adata_to_state(adata)

        # 获取QC统计
        obs_cols = ["n_genes_by_counts", "total_counts", "pct_counts_mt"]
        stats = {}
        for col in obs_cols:
            if col in adata.obs.columns:
                stats[col] = {
                    "mean": float(adata.obs[col].mean()),
                    "median": float(adata.obs[col].median()),
                    "std": float(adata.obs[col].std())
                }

        return json.dumps({"status": "success", "stats": stats}, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ============ 预处理工具 ============

@tool
def run_preprocessing(
    n_top_genes: int = 2000,
    n_pcs: int = 50,
    target_sum: float = 1e4
) -> str:
    """
    执行数据预处理流程，包括：
    1. 归一化
    2. log转换
    3. 高变基因(HVG)筛选
    4. 数据标准化
    5. PCA降维

    Args:
        n_top_genes: 高变基因数量
        n_pcs: PCA主成分数量
        target_sum: 归一化目标总量

    Returns:
        JSON格式的预处理结果摘要
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        params = {
            "n_top_genes": n_top_genes,
            "n_pcs": n_pcs,
            "target_sum": target_sum
        }

        result = run_preprocessing_pipeline(adata, params=params)
        set_adata_to_state(result["adata"])

        return json.dumps({
            "status": "success",
            "summary": result.get("summary", {}),
            "plot_files": result.get("plot_files", [])
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def normalize(target_sum: float = 1e4) -> str:
    """
    数据归一化

    Args:
        target_sum: 归一化目标总量

    Returns:
        操作结果
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = normalize_data(adata, target_sum=target_sum)
        set_adata_to_state(adata)
        return json.dumps({"status": "success", "operation": "normalize"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def log_transform() -> str:
    """
    log1p转换

    Returns:
        操作结果
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = log_transform(adata)
        set_adata_to_state(adata)
        return json.dumps({"status": "success", "operation": "log_transform"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def select_highly_variable_genes(n_top_genes: int = 2000) -> str:
    """
    筛选高变基因(HVG)

    Args:
        n_top_genes: 要选择的高变基因数量

    Returns:
        操作结果
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = select_hvg(adata, n_top_genes=n_top_genes)
        set_adata_to_state(adata)

        n_hvg = adata.var["highly_variable"].sum() if "highly_variable" in adata.var.columns else 0
        return json.dumps({
            "status": "success",
            "operation": "select_hvg",
            "n_hvg": int(n_hvg)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def standardize() -> str:
    """
    数据标准化（scale）

    Returns:
        操作结果
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = standardize_data(adata)
        set_adata_to_state(adata)
        return json.dumps({"status": "success", "operation": "standardize"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ============ 降维聚类工具 ============

@tool
def run_clustering_analysis(
    method: str = "leiden",
    resolution: float = 1.0,
    n_pcs: int = 50,
    n_neighbors: int = 15,
    output_dir: Optional[str] = None
) -> str:
    """
    执行降维和聚类分析，包括：
    1. 邻域图构建
    2. UMAP降维
    3. Leiden/Louvain聚类
    4. 生成聚类图表

    Args:
        method: 聚类方法 ("leiden" 或 "louvain")
        resolution: 聚类分辨率
        n_pcs: PCA主成分数量
        n_neighbors: 邻域图邻居数
        output_dir: 图表输出目录

    Returns:
        JSON格式的聚类结果摘要
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        # 计算邻域图
        from engine.clustering import compute_neighbors
        adata = compute_neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)

        # UMAP降维
        adata = run_umap(adata)

        # 聚类
        adata = run_clustering(adata, method=method, resolution=resolution)

        # 获取注释建议
        annotation = suggest_cluster_annotation(adata)

        # 生成图表
        plot_files = []
        if output_dir:
            plot_files = generate_clustering_plots(adata, output_dir, cluster_key=method)

        set_adata_to_state(adata)

        return json.dumps({
            "status": "success",
            "method": method,
            "n_clusters": annotation.get("n_clusters", 0),
            "annotation": annotation,
            "plot_files": plot_files
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def reduce_dimensionality(
    n_pcs: int = 50,
    n_neighbors: int = 15
) -> str:
    """
    执行降维（PCA + UMAP），不进行聚类

    Args:
        n_pcs: PCA主成分数量
        n_neighbors: 邻域图邻居数

    Returns:
        操作结果
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        from engine.clustering import compute_neighbors
        adata = run_pca(adata, n_comps=n_pcs)
        adata = compute_neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)
        adata = run_umap(adata)
        set_adata_to_state(adata)

        return json.dumps({
            "status": "success",
            "operation": "reduce_dimensionality",
            "n_pcs": n_pcs,
            "n_neighbors": n_neighbors
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def cluster(method: str = "leiden", resolution: float = 1.0) -> str:
    """
    执行聚类分析（假设已完成降维）

    Args:
        method: 聚类方法 ("leiden" 或 "louvain")
        resolution: 聚类分辨率

    Returns:
        聚类结果摘要
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = run_clustering(adata, method=method, resolution=resolution)
        annotation = suggest_cluster_annotation(adata)
        set_adata_to_state(adata)

        return json.dumps({
            "status": "success",
            "method": method,
            "n_clusters": annotation.get("n_clusters", 0),
            "annotation": annotation
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ============ 可视化工具 ============

@tool
def generate_spatial_plots(
    cluster_key: str = "leiden",
    genes: Optional[List[str]] = None,
    use_3d: bool = True,
    output_dir: Optional[str] = None
) -> str:
    """
    生成空间可视化图表，包括：
    1. 细胞空间分布图
    2. Cluster空间分布图
    3. 基因空间表达图

    Args:
        cluster_key: 聚类结果的列名
        genes: 要可视化的基因列表（可选）
        use_3d: 是否使用3D可视化
        output_dir: 图表输出目录

    Returns:
        JSON格式的图表文件列表
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        plot_files = []

        # 空间分布图
        spatial_file = plot_spatial_distribution(
            adata, output_dir or "storage/results", use_3d=use_3d
        )
        if spatial_file:
            plot_files.append(spatial_file)

        # Cluster空间图
        if cluster_key in adata.obs.columns:
            cluster_file = plot_cluster_spatial(
                adata, output_dir or "storage/results",
                cluster_key=cluster_key, use_3d=use_3d
            )
            if cluster_file:
                plot_files.append(cluster_file)

        # 基因空间图
        if genes:
            for gene in genes[:5]:  # 最多5个基因
                gene_file = plot_gene_spatial(
                    adata, gene, output_dir or "storage/results",
                    use_3d=use_3d
                )
                if gene_file:
                    plot_files.append(gene_file)

        set_adata_to_state(adata)

        return json.dumps({
            "status": "success",
            "plot_files": plot_files,
            "n_plots": len(plot_files)
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def plot_umap(
    color: Optional[str] = None,
    basis: str = "umap",
    output_dir: Optional[str] = None
) -> str:
    """
    绘制UMAP降维散点图

    Args:
        color: 着色依据（obs列名）
        basis: 降维方法
        output_dir: 图表输出目录

    Returns:
        JSON格式的图表文件路径
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        plot_file = plot_embedding(
            adata, basis=basis, output_dir=output_dir or "",
            color=color
        )

        return json.dumps({
            "status": "success",
            "plot_file": plot_file
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def plot_gene_expression(gene: str, use_3d: bool = True, output_dir: Optional[str] = None) -> str:
    """
    绘制单个基因的空间表达图

    Args:
        gene: 基因名称
        use_3d: 是否使用3D可视化
        output_dir: 图表输出目录

    Returns:
        JSON格式的图表文件路径
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        plot_file = plot_gene_spatial(
            adata, gene, output_dir or "storage/results",
            use_3d=use_3d
        )

        return json.dumps({
            "status": "success",
            "gene": gene,
            "plot_file": plot_file
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ============ Marker基因工具 ============

@tool
def find_markers(
    cluster_key: str = "leiden",
    method: str = "wilcoxon",
    n_markers: int = 10
) -> str:
    """
    鉴定Marker基因（差异表达分析）

    Args:
        cluster_key: 聚类结果的列名
        method: 差异分析方法 ("wilcoxon", "t-test", "logreg")
        n_markers: 每个cluster返回的marker基因数量

    Returns:
        JSON格式的Marker基因列表
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        adata = find_marker_genes(
            adata, cluster_key=cluster_key,
            method=method, n_genes=n_markers * 10
        )
        set_adata_to_state(adata)

        # 获取top markers
        top_markers = get_top_markers(adata, cluster_key=cluster_key, n=n_markers)

        return json.dumps({
            "status": "success",
            "method": method,
            "top_markers": top_markers
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def get_markers(cluster_key: str = "leiden", n: int = 10) -> str:
    """
    获取每个cluster的top marker基因（需要先运行find_markers）

    Args:
        cluster_key: 聚类结果的列名
        n: 每个cluster返回的基因数量

    Returns:
        JSON格式的Marker基因列表
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        top_markers = get_top_markers(adata, cluster_key=cluster_key, n=n)
        return json.dumps({
            "status": "success",
            "top_markers": top_markers
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@tool
def plot_markers(
    cluster_key: str = "leiden",
    n_markers: int = 10,
    plot_type: str = "dotplot",
    output_dir: Optional[str] = None
) -> str:
    """
    绘制Marker基因图表

    Args:
        cluster_key: 聚类结果的列名
        n_markers: 绘制的marker基因数量
        plot_type: 图表类型 ("dotplot" 或 "heatmap")
        output_dir: 图表输出目录

    Returns:
        JSON格式的图表文件路径
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

    try:
        if plot_type == "dotplot":
            plot_file = plot_marker_dotplot(
                adata, cluster_key=cluster_key,
                n_markers=n_markers, output_dir=output_dir or ""
            )
        else:
            plot_file = plot_marker_heatmap(
                adata, cluster_key=cluster_key,
                n_markers=n_markers, output_dir=output_dir or ""
            )

        return json.dumps({
            "status": "success",
            "plot_type": plot_type,
            "plot_file": plot_file
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ============ 分析摘要工具 ============

@tool
def get_analysis_summary() -> str:
    """
    获取当前分析的完整摘要

    Returns:
        JSON格式的分析摘要
    """
    adata = get_adata_from_state()
    if adata is None:
        return json.dumps({"error": "没有加载数据"}, ensure_ascii=False)

    try:
        summary = get_data_summary(adata)

        # 添加聚类信息
        for key in ["leiden", "louvain"]:
            if key in adata.obs.columns:
                summary[f"n_{key}_clusters"] = adata.obs[key].nunique()

        # 添加HVG信息
        if "highly_variable" in adata.var.columns:
            summary["n_hvg"] = int(adata.var["highly_variable"].sum())

        # 添加Marker信息
        if "rank_genes_groups" in adata.uns:
            summary["has_markers"] = True
        else:
            summary["has_markers"] = False

        return json.dumps({
            "status": "success",
            "summary": summary
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ============ 工具注册 ============

def get_all_tools() -> List:
    """
    获取所有可用的工具列表

    Returns:
        Tool对象列表
    """
    return [
        # 数据读取
        load_data,
        get_data_info,
        # 质量控制
        run_qc,
        calculate_qc,
        # 预处理
        run_preprocessing,
        normalize,
        log_transform,
        select_highly_variable_genes,
        standardize,
        # 降维聚类
        run_clustering_analysis,
        reduce_dimensionality,
        cluster,
        # 可视化
        generate_spatial_plots,
        plot_umap,
        plot_gene_expression,
        # Marker基因
        find_markers,
        get_markers,
        plot_markers,
        # 分析摘要
        get_analysis_summary,
    ]


def get_tools_description() -> str:
    """
    获取所有工具的描述文本

    Returns:
        工具描述字符串
    """
    tools = get_all_tools()
    desc_lines = []
    for tool_func in tools:
        desc_lines.append(f"- {tool_func.name}: {tool_func.description}")
    return "\n".join(desc_lines)
