"""
Marker Gene Analysis Module
Marker基因分析模块
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from anndata import AnnData
import scanpy as sc
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logger = logging.getLogger(__name__)


def find_marker_genes(
    adata: AnnData,
    cluster_key: str = "leiden",
    method: str = "wilcoxon",
    n_genes: int = 100,
    use_raw: bool = True,
) -> AnnData:
    """
    鉴定Marker基因

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        method: 差异分析方法 (wilcoxon, t-test, logreg)
        n_genes: 每个cluster返回的基因数量
        use_raw: 是否使用原始数据

    Returns:
        添加了rank_genes_groups结果的AnnData对象
    """
    if cluster_key not in adata.obs.columns:
        logger.error(f"未找到聚类结果列: {cluster_key}")
        return adata

    logger.info(f"正在使用 {method} 方法鉴定Marker基因...")

    # 确保使用归一化后的数据
    if use_raw and adata.raw is not None:
        adata_to_use = adata.raw.to_adata()
    else:
        adata_to_use = adata.copy()

    # 执行差异分析
    sc.tl.rank_genes_groups(
        adata_to_use,
        groupby=cluster_key,
        method=method,
        n_genes=n_genes,
        use_raw=False,
    )

    # 将结果复制到原始对象
    adata.uns["rank_genes_groups"] = adata_to_use.uns["rank_genes_groups"]

    n_clusters = adata.obs[cluster_key].nunique()
    logger.info(f"Marker基因鉴定完成，共 {n_clusters} 个cluster")

    return adata


def get_top_markers(
    adata: AnnData,
    cluster_key: str = "leiden",
    n: int = 10,
) -> Dict[str, List[str]]:
    """
    获取每个cluster的top markers

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        n: 返回的基因数量

    Returns:
        字典，key为cluster名称，value为top marker基因列表
    """
    if "rank_genes_groups" not in adata.uns:
        logger.error("未找到Marker基因结果，请先运行find_marker_genes")
        return {}

    logger.info(f"正在获取每个cluster的Top {n} markers...")

    # 获取结果
    result = adata.uns["rank_genes_groups"]
    groups = result["names"].dtype.names

    top_markers = {}
    for group in groups:
        genes = result["names"][group][:n]
        top_markers[group] = list(genes)

    logger.info("Top markers获取完成")
    return top_markers


def get_markers_dataframe(
    adata: AnnData,
    cluster_key: str = "leiden",
    n_genes: int = 20,
) -> pd.DataFrame:
    """
    获取Marker基因结果的DataFrame

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        n_genes: 每个cluster返回的基因数量

    Returns:
        Marker基因结果DataFrame
    """
    if "rank_genes_groups" not in adata.uns:
        logger.error("未找到Marker基因结果")
        return pd.DataFrame()

    result = adata.uns["rank_genes_groups"]
    groups = result["names"].dtype.names

    data = []
    for group in groups:
        for i in range(n_genes):
            data.append({
                "cluster": group,
                "gene": result["names"][group][i],
                "score": result["scores"][group][i],
                "logfoldchange": result["logfoldchanges"][group][i],
                "pval": result["pvals"][group][i],
                "pval_adj": result["pvals_adj"][group][i],
            })

    df = pd.DataFrame(data)
    return df


def plot_marker_heatmap(
    adata: AnnData,
    cluster_key: str = "leiden",
    n_markers: int = 10,
    output_dir: str = "",
    use_raw: bool = None,
) -> str:
    """
    绘制Marker基因热图

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        n_markers: 每个cluster显示的基因数量
        output_dir: 输出目录
        use_raw: 是否使用原始数据 (None表示自动检测)

    Returns:
        生成的图表文件路径
    """
    if "rank_genes_groups" not in adata.uns:
        logger.error("未找到Marker基因结果")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("正在绘制Marker基因热图...")

    # 自动检测是否有raw数据
    if use_raw is None:
        use_raw = adata.raw is not None

    # 获取top markers
    top_markers = get_top_markers(adata, cluster_key, n_markers)
    genes = []
    for cluster in sorted(top_markers.keys(), key=lambda x: int(x) if x.isdigit() else x):
        genes.extend(top_markers[cluster])

    # 去重
    genes = list(dict.fromkeys(genes))

    # 使用scanpy绘图 (使用dotplot代替heatmap，效果更好)
    # 如果坚持用heatmap，需要设置show_gene_labels=False
    try:
        sc.pl.rank_genes_groups_heatmap(
            adata,
            n_genes=n_markers,
            groupby=cluster_key,
            show=False,
            use_raw=use_raw,
            show_gene_labels=False,  # 避免基因标签重叠
        )
        plot_path = output_path / "marker_heatmap.png"
    except Exception as e:
        logger.warning(f"热图生成失败，改用点图: {e}")
        # 改用点图
        sc.pl.dotplot(
            adata,
            var_names=genes[:30],  # 限制基因数量
            groupby=cluster_key,
            show=False,
            use_raw=use_raw,
        )
        plot_path = output_path / "marker_heatmap.png"  # 保存为同一文件名

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Marker热图已保存: {plot_path}")
    return str(plot_path)


def plot_marker_dotplot(
    adata: AnnData,
    cluster_key: str = "leiden",
    n_markers: int = 5,
    output_dir: str = "",
    use_raw: bool = None,
) -> str:
    """
    绘制Marker基因点图

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        n_markers: 每个cluster显示的基因数量
        output_dir: 输出目录
        use_raw: 是否使用原始数据 (None表示自动检测)

    Returns:
        生成的图表文件路径
    """
    if "rank_genes_groups" not in adata.uns:
        logger.error("未找到Marker基因结果")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("正在绘制Marker基因点图...")

    # 自动检测是否有raw数据
    if use_raw is None:
        use_raw = adata.raw is not None

    fig, ax = plt.subplots(figsize=(12, 8))

    # 获取top markers
    top_markers = get_top_markers(adata, cluster_key, n_markers)
    genes = []
    for cluster in sorted(top_markers.keys(), key=lambda x: int(x) if x.isdigit() else x):
        genes.extend(top_markers[cluster])

    # 去重
    genes = list(dict.fromkeys(genes))

    # 使用scanpy绘图
    sc.pl.dotplot(
        adata,
        var_names=genes,
        groupby=cluster_key,
        show=False,
        use_raw=use_raw,
    )

    plt.tight_layout()
    plot_path = output_path / "marker_dotplot.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Marker点图已保存: {plot_path}")
    return str(plot_path)


def plot_marker_violin(
    adata: AnnData,
    genes: List[str],
    cluster_key: str = "leiden",
    output_dir: str = "",
    use_raw: bool = None,
) -> str:
    """
    绘制Marker基因小提琴图

    Args:
        adata: AnnData对象
        genes: 基因列表
        cluster_key: 聚类结果的列名
        output_dir: 输出目录
        use_raw: 是否使用原始数据 (None表示自动检测)

    Returns:
        生成的图表文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("正在绘制Marker基因小提琴图...")

    # 自动检测是否有raw数据
    if use_raw is None:
        use_raw = adata.raw is not None

    n_genes = len(genes)
    if n_genes == 0:
        logger.warning("没有提供基因，跳过小提琴图绘制")
        return ""

    n_cols = min(3, n_genes)
    n_rows = (n_genes + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
    if n_genes == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    for i, gene in enumerate(genes):
        if gene in adata.var_names:
            sc.pl.violin(
                adata,
                gene,
                groupby=cluster_key,
                ax=axes[i],
                show=False,
                use_raw=use_raw,
            )
            axes[i].set_title(gene)

    # 隐藏多余的子图
    for j in range(n_genes, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()
    plot_path = output_path / "marker_violin.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Marker小提琴图已保存: {plot_path}")
    return str(plot_path)


def plot_marker_rank_genes(
    adata: AnnData,
    cluster_key: str = "leiden",
    n_genes: int = 10,
    output_dir: str = "",
) -> str:
    """
    绘制Marker基因排名图

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        n_genes: 显示的基因数量
        output_dir: 输出目录

    Returns:
        生成的图表文件路径
    """
    if "rank_genes_groups" not in adata.uns:
        logger.error("未找到Marker基因结果")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("正在绘制Marker基因排名图...")

    fig, ax = plt.subplots(figsize=(12, 8))

    sc.pl.rank_genes_groups(
        adata,
        n_genes=n_genes,
        sharey=False,
        show=False,
    )

    plt.tight_layout()
    plot_path = output_path / "marker_rank_genes.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Marker排名图已保存: {plot_path}")
    return str(plot_path)


def run_marker_analysis(
    adata: AnnData,
    cluster_key: str = "leiden",
    method: str = "wilcoxon",
    n_markers: int = 10,
    output_dir: Optional[str] = None,
    plot_type: str = "dotplot",
) -> Dict[str, Any]:
    """
    完整的Marker基因分析流程

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果的列名
        method: 差异分析方法
        n_markers: 每个cluster的marker数量
        output_dir: 输出目录
        plot_type: 图表类型 ("dotplot" 或 "heatmap")

    Returns:
        包含分析结果的字典
    """
    logger.info("开始Marker基因分析...")

    # 1. 鉴定Marker基因
    adata = find_marker_genes(adata, cluster_key, method)

    # 2. 获取Top markers
    top_markers = get_top_markers(adata, cluster_key, n_markers)

    # 3. 获取DataFrame
    markers_df = get_markers_dataframe(adata, cluster_key, n_markers)

    # 4. 生成图表
    plot_files = []
    if output_dir:
        # 点图 (推荐)
        if plot_type == "dotplot":
            dotplot_path = plot_marker_dotplot(adata, cluster_key, n_markers, output_dir)
            if dotplot_path:
                plot_files.append(dotplot_path)

        # 热图 (备选)
        if plot_type == "heatmap":
            heatmap_path = plot_marker_heatmap(adata, cluster_key, n_markers, output_dir)
            if heatmap_path:
                plot_files.append(heatmap_path)

        # 排名图
        rank_path = plot_marker_rank_genes(adata, cluster_key, n_markers, output_dir)
        if rank_path:
            plot_files.append(rank_path)

    # 生成摘要
    summary = {
        "cluster_key": cluster_key,
        "method": method,
        "n_markers": n_markers,
        "n_clusters": len(top_markers),
        "top_markers": top_markers,
        "plot_type": plot_type,
    }

    logger.info("Marker基因分析完成")

    return {
        "adata": adata,
        "summary": summary,
        "top_markers": top_markers,
        "markers_df": markers_df,
        "plot_files": plot_files,
    }
