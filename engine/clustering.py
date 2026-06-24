"""
Clustering Module
降维与聚类模块
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from anndata import AnnData
import scanpy as sc
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logger = logging.getLogger(__name__)


def run_pca(
    adata: AnnData,
    n_comps: int = 50,
    use_highly_variable: bool = True,
) -> AnnData:
    """
    PCA降维

    Args:
        adata: AnnData对象
        n_comps: 主成分数量
        use_highly_variable: 是否只使用高变基因

    Returns:
        添加了PCA结果的AnnData对象
    """
    logger.info(f"正在进行PCA降维 (n_comps={n_comps})...")

    # 检查是否已经做过PCA
    if "X_pca" in adata.obsm and adata.obsm["X_pca"].shape[1] >= n_comps:
        logger.info("检测到已有PCA结果，跳过PCA步骤")
        return adata

    # 确定使用的基因
    if use_highly_variable and "highly_variable" in adata.var.columns:
        use_rep = adata[:, adata.var["highly_variable"]].copy()
    else:
        use_rep = adata.copy()

    # 执行PCA
    sc.tl.pca(use_rep, n_comps=n_comps, svd_solver="arpack")

    # 将PCA结果复制到主对象
    adata.obsm["X_pca"] = use_rep.obsm["X_pca"]
    adata.uns["pca"] = use_rep.uns["pca"]

    # 存储方差解释率
    if "variance_ratio" in use_rep.uns["pca"]:
        adata.uns["pca_variance_ratio"] = use_rep.uns["pca"]["variance_ratio"]

    logger.info("PCA降维完成")
    return adata


def compute_neighbors(
    adata: AnnData,
    n_neighbors: int = 15,
    n_pcs: int = 50,
) -> AnnData:
    """
    计算邻域图

    Args:
        adata: AnnData对象
        n_neighbors: 邻居数量
        n_pcs: 使用的PC数量

    Returns:
        添加了邻域图的AnnData对象
    """
    logger.info(f"正在计算邻域图 (n_neighbors={n_neighbors})...")

    sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)

    logger.info("邻域图计算完成")
    return adata


def run_umap(
    adata: AnnData,
    min_dist: float = 0.5,
    spread: float = 1.0,
) -> AnnData:
    """
    UMAP降维

    Args:
        adata: AnnData对象
        min_dist: 最小距离参数
        spread: 扩展参数

    Returns:
        添加了UMAP结果的AnnData对象
    """
    logger.info("正在进行UMAP降维...")

    # 检查是否已经计算了邻域图
    if "neighbors" not in adata.uns:
        logger.warning("未检测到邻域图，先计算邻域图")
        adata = compute_neighbors(adata)

    sc.tl.umap(adata, min_dist=min_dist, spread=spread)

    logger.info("UMAP降维完成")
    return adata


def run_clustering(
    adata: AnnData,
    method: str = "leiden",
    resolution: float = 1.0,
) -> AnnData:
    """
    聚类分析

    Args:
        adata: AnnData对象
        method: 聚类方法 (leiden 或 louvain)
        resolution: 分辨率参数

    Returns:
        添加了聚类结果的AnnData对象
    """
    logger.info(f"正在进行{method}聚类 (resolution={resolution})...")

    # 检查是否已经计算了邻域图
    if "neighbors" not in adata.uns:
        logger.warning("未检测到邻域图，先计算邻域图")
        adata = compute_neighbors(adata)

    # 执行聚类
    if method.lower() == "leiden":
        sc.tl.leiden(adata, resolution=resolution, flavor="igraph", n_iterations=2)
        cluster_key = "leiden"
    elif method.lower() == "louvain":
        sc.tl.louvain(adata, resolution=resolution)
        cluster_key = "louvain"
    else:
        raise ValueError(f"不支持的聚类方法: {method}")

    n_clusters = adata.obs[cluster_key].nunique()
    logger.info(f"聚类完成，识别出 {n_clusters} 个cluster")

    return adata


def suggest_cluster_annotation(adata: AnnData, cluster_key: str = "leiden") -> Dict[str, Any]:
    """
    Cluster注释建议

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名

    Returns:
        注释建议字典
    """
    logger.info("正在生成Cluster注释建议...")

    if cluster_key not in adata.obs.columns:
        logger.warning(f"未找到聚类结果列: {cluster_key}")
        return {}

    suggestions = {
        "cluster_key": cluster_key,
        "n_clusters": adata.obs[cluster_key].nunique(),
        "clusters": {},
    }

    # 对每个cluster计算特征
    for cluster in adata.obs[cluster_key].unique():
        cluster_mask = adata.obs[cluster_key] == cluster
        cluster_data = adata[cluster_mask]

        # 计算该cluster的平均表达量
        mean_expr = np.array(cluster_data.X.mean(axis=0)).flatten()

        # 找到表达最高的基因
        top_gene_indices = np.argsort(mean_expr)[-10:][::-1]
        top_genes = [adata.var_names[i] for i in top_gene_indices]

        suggestions["clusters"][str(cluster)] = {
            "n_cells": int(cluster_mask.sum()),
            "top_genes": top_genes,
            "mean_n_genes": float(cluster_data.obs["n_genes"].mean()) if "n_genes" in cluster_data.obs.columns else None,
            "mean_n_counts": float(cluster_data.obs["n_counts"].mean()) if "n_counts" in cluster_data.obs.columns else None,
        }

    logger.info("Cluster注释建议生成完成")
    return suggestions


def generate_clustering_plots(
    adata: AnnData,
    output_dir: str,
    cluster_key: str = "leiden",
) -> List[str]:
    """
    生成聚类图表

    Args:
        adata: AnnData对象
        output_dir: 输出目录
        cluster_key: 聚类结果的列名

    Returns:
        生成的图表文件路径列表
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plot_files = []

    # 设置绘图风格
    plt.style.use("seaborn-v0_8-whitegrid")

    # 1. PCA方差解释率
    # 检查两种可能的键名
    variance_ratio = None
    if "pca_variance_ratio" in adata.uns:
        variance_ratio = adata.uns["pca_variance_ratio"]
    elif "pca" in adata.uns and "variance_ratio" in adata.uns["pca"]:
        variance_ratio = adata.uns["pca"]["variance_ratio"]

    if variance_ratio is not None:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(range(len(variance_ratio)), variance_ratio)
        ax.set_xlabel("Principal Component")
        ax.set_ylabel("Variance Explained Ratio")
        ax.set_title("PCA Variance Explained")
        ax.set_xlim(0, min(50, len(variance_ratio)))

        plt.tight_layout()
        pca_path = output_path / "pca_variance.png"
        plt.savefig(pca_path, dpi=150, bbox_inches="tight")
        plt.close()
        plot_files.append(str(pca_path))

    # 2. UMAP图（按聚类着色）
    if "X_umap" in adata.obsm and cluster_key in adata.obs.columns:
        fig, ax = plt.subplots(figsize=(10, 8))

        # 使用更鲜明的颜色
        import matplotlib.colors as mcolors
        colors = list(mcolors.TABLEAU_COLORS.keys())[:adata.obs[cluster_key].nunique()]

        sc.pl.umap(
            adata,
            color=cluster_key,
            ax=ax,
            show=False,
            title=f"UMAP - {cluster_key}",
            palette=colors,
            frameon=False,
        )
        plt.tight_layout()
        umap_cluster_path = output_path / "umap_cluster.png"
        plt.savefig(umap_cluster_path, dpi=150, bbox_inches="tight")
        plt.close()
        plot_files.append(str(umap_cluster_path))

    # 3. UMAP图（按n_counts着色）
    # scanpy可能使用不同的列名
    counts_col = "total_counts" if "total_counts" in adata.obs.columns else "n_counts"
    if "X_umap" in adata.obsm and counts_col in adata.obs.columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        sc.pl.umap(
            adata,
            color=counts_col,
            ax=ax,
            show=False,
            title="UMAP - UMI Counts",
            cmap="viridis",  # 使用彩色颜色映射
            frameon=False,
        )
        plt.tight_layout()
        umap_counts_path = output_path / "umap_counts.png"
        plt.savefig(umap_counts_path, dpi=150, bbox_inches="tight")
        plt.close()
        plot_files.append(str(umap_counts_path))

    # 4. UMAP图（按n_genes着色）
    genes_col = "n_genes_by_counts" if "n_genes_by_counts" in adata.obs.columns else "n_genes"
    if "X_umap" in adata.obsm and genes_col in adata.obs.columns:
        fig, ax = plt.subplots(figsize=(10, 8))
        sc.pl.umap(
            adata,
            color=genes_col,
            ax=ax,
            show=False,
            title="UMAP - Genes per Cell",
            cmap="plasma",  # 使用彩色颜色映射
            frameon=False,
        )
        plt.tight_layout()
        umap_genes_path = output_path / "umap_genes.png"
        plt.savefig(umap_genes_path, dpi=150, bbox_inches="tight")
        plt.close()
        plot_files.append(str(umap_genes_path))

    logger.info(f"生成 {len(plot_files)} 个聚类图表")
    return plot_files


def run_clustering_pipeline(
    adata: AnnData,
    params: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    完整的降维聚类流程

    Args:
        adata: AnnData对象
        params: 参数配置
        output_dir: 输出目录

    Returns:
        包含结果的字典
    """
    if params is None:
        params = {}

    n_pcs = params.get("n_pcs", 50)
    n_neighbors = params.get("n_neighbors", 15)
    method = params.get("method", "leiden")
    resolution = params.get("resolution", 1.0)

    logger.info("开始降维聚类流程...")

    # 1. PCA降维
    adata = run_pca(adata, n_comps=n_pcs)

    # 2. 计算邻域图
    adata = compute_neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)

    # 3. UMAP降维
    adata = run_umap(adata)

    # 4. 聚类
    adata = run_clustering(adata, method=method, resolution=resolution)

    # 5. 生成注释建议
    cluster_key = "leiden" if method == "leiden" else "louvain"
    annotation_suggestions = suggest_cluster_annotation(adata, cluster_key)

    # 6. 生成图表
    plot_files = []
    if output_dir:
        plot_files = generate_clustering_plots(adata, output_dir, cluster_key)

    # 生成摘要
    summary = {
        "n_pcs": n_pcs,
        "n_neighbors": n_neighbors,
        "clustering_method": method,
        "resolution": resolution,
        "n_clusters": adata.obs[cluster_key].nunique(),
        "cluster_sizes": adata.obs[cluster_key].value_counts().to_dict(),
        "annotation_suggestions": annotation_suggestions,
    }

    logger.info("降维聚类流程完成")

    return {
        "adata": adata,
        "summary": summary,
        "plot_files": plot_files,
    }
