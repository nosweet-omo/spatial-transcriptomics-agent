"""
Quality Control Module
质量控制模块
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from anndata import AnnData
import scanpy as sc
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import logging

logger = logging.getLogger(__name__)


def calculate_qc_metrics(adata: AnnData) -> AnnData:
    """
    计算QC指标 (使用scanpy标准方法)

    参考: https://scanpy.readthedocs.io/en/stable/tutorials/basics/quality-control.html

    Args:
        adata: AnnData对象

    Returns:
        添加了QC指标的AnnData对象
    """
    logger.info("正在计算QC指标...")

    # 使用scanpy标准函数计算QC指标
    # adata.var_names用于识别线粒体基因
    adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
    # 核糖体基因
    adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL", "rps", "rpl"))
    # 血红蛋白基因
    adata.var["hb"] = adata.var_names.str.contains(("^HB[^(P)]"), case=False)

    # 使用scanpy标准函数计算QC指标
    sc.pp.calculate_qc_metrics(
        adata,
        qc_vars=["mt", "ribo", "hb"],
        percent_top=None,
        log1p=False,
        inplace=True,
    )

    logger.info(f"QC指标计算完成:")
    logger.info(f"  - 检测到 {adata.var['mt'].sum()} 个线粒体基因")
    logger.info(f"  - 检测到 {adata.var['ribo'].sum()} 个核糖体基因")
    logger.info(f"  - 检测到 {adata.var['hb'].sum()} 个血红蛋白基因")

    return adata


def filter_cells(
    adata: AnnData,
    min_genes: int = 200,
    min_cells: int = 3,
    min_counts: int = None,
) -> AnnData:
    """
    过滤细胞和基因 (使用scanpy标准方法)

    参考: https://scanpy.readthedocs.io/en/stable/tutorials/basics/quality-control.html

    Args:
        adata: AnnData对象
        min_genes: 每个细胞最少基因数 (默认200)
        min_cells: 每个基因最少细胞数 (默认3)
        min_counts: 每个细胞最少UMI数 (可选)

    Returns:
        过滤后的AnnData对象
    """
    n_cells_before = adata.shape[0]
    n_genes_before = adata.shape[1]

    # 使用scanpy标准函数过滤细胞
    sc.pp.filter_cells(adata, min_genes=min_genes)
    logger.info(f"过滤基因数 < {min_genes} 的细胞: {n_cells_before} -> {adata.shape[0]}")

    # 可选：过滤低UMI数细胞
    if min_counts is not None:
        n_cells_before2 = adata.shape[0]
        sc.pp.filter_cells(adata, min_counts=min_counts)
        logger.info(f"过滤UMI数 < {min_counts} 的细胞: {n_cells_before2} -> {adata.shape[0]}")

    # 使用scanpy标准函数过滤基因
    n_genes_before2 = adata.shape[1]
    sc.pp.filter_genes(adata, min_cells=min_cells)
    logger.info(f"过滤细胞数 < {min_cells} 的基因: {n_genes_before2} -> {adata.shape[1]}")

    return adata


def filter_mito(adata: AnnData, max_pct: float = 20.0) -> AnnData:
    """
    过滤线粒体基因比例过高的细胞

    Args:
        adata: AnnData对象
        max_pct: 最大线粒体基因比例

    Returns:
        过滤后的AnnData对象
    """
    # scanpy使用不同的列名
    mito_col = "pct_counts_mt" if "pct_counts_mt" in adata.obs.columns else "pct_mito"

    if mito_col not in adata.obs.columns:
        logger.warning("未找到线粒体比例列，跳过线粒体过滤")
        return adata

    n_before = adata.shape[0]
    adata = adata[adata.obs[mito_col] <= max_pct].copy()
    logger.info(f"过滤线粒体比例 > {max_pct}% 的细胞: {n_before} -> {adata.shape[0]}")

    return adata


def generate_qc_plots(adata: AnnData, output_dir: str) -> List[str]:
    """
    生成QC图表

    Args:
        adata: AnnData对象
        output_dir: 输出目录

    Returns:
        生成的图表文件路径列表
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plot_files = []

    # 设置绘图风格
    plt.style.use("seaborn-v0_8-whitegrid")
    sns.set_palette("husl")

    # scanpy使用不同的列名
    genes_col = "n_genes_by_counts" if "n_genes_by_counts" in adata.obs.columns else "n_genes"
    counts_col = "total_counts" if "total_counts" in adata.obs.columns else "n_counts"
    mito_col = "pct_counts_mt" if "pct_counts_mt" in adata.obs.columns else "pct_mito"

    # 1. QC指标 violin plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 基因数分布
    sns.violinplot(y=adata.obs[genes_col], ax=axes[0], inner="box")
    axes[0].set_title("Genes per Cell")
    axes[0].set_ylabel("Number of Genes")

    # UMI数分布
    sns.violinplot(y=adata.obs[counts_col], ax=axes[1], inner="box")
    axes[1].set_title("UMI Counts per Cell")
    axes[1].set_ylabel("Number of UMIs")

    # 线粒体比例分布
    if mito_col in adata.obs.columns:
        sns.violinplot(y=adata.obs[mito_col], ax=axes[2], inner="box")
        axes[2].set_title("Mitochondrial Percentage")
        axes[2].set_ylabel("% Mitochondrial")

    plt.tight_layout()
    violin_path = output_path / "qc_violin.png"
    plt.savefig(violin_path, dpi=150, bbox_inches="tight")
    plt.close()
    plot_files.append(str(violin_path))

    # 2. QC指标 scatter plots
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 基因数 vs UMI数
    axes[0].scatter(
        adata.obs[genes_col],
        adata.obs[counts_col],
        c=adata.obs.get(mito_col, np.zeros(adata.shape[0])),
        cmap="viridis",
        alpha=0.6,
        s=10,
    )
    axes[0].set_xlabel("Number of Genes")
    axes[0].set_ylabel("Number of UMIs")
    axes[0].set_title("Genes vs UMIs")

    # 基因数 vs 线粒体比例
    if mito_col in adata.obs.columns:
        axes[1].scatter(
            adata.obs[genes_col],
            adata.obs[mito_col],
            c=adata.obs[counts_col],
            cmap="viridis",
            alpha=0.6,
            s=10,
        )
        axes[1].set_xlabel("Number of Genes")
        axes[1].set_ylabel("% Mitochondrial")
        axes[1].set_title("Genes vs Mito %")

    plt.tight_layout()
    scatter_path = output_path / "qc_scatter.png"
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    plot_files.append(str(scatter_path))

    # 3. 基因表达分布
    fig, ax = plt.subplots(figsize=(10, 5))
    gene_counts = np.array(adata.X.sum(axis=0)).flatten()
    ax.hist(gene_counts, bins=50, edgecolor="black", alpha=0.7)
    ax.set_xlabel("Total Expression per Gene")
    ax.set_ylabel("Number of Genes")
    ax.set_title("Gene Expression Distribution")
    ax.axvline(x=np.median(gene_counts), color="red", linestyle="--", label="Median")
    ax.legend()

    plt.tight_layout()
    hist_path = output_path / "qc_gene_histogram.png"
    plt.savefig(hist_path, dpi=150, bbox_inches="tight")
    plt.close()
    plot_files.append(str(hist_path))

    logger.info(f"生成 {len(plot_files)} 个QC图表")
    return plot_files


def get_qc_summary(adata: AnnData) -> Dict[str, Any]:
    """
    获取QC摘要信息

    Args:
        adata: AnnData对象

    Returns:
        QC摘要字典
    """
    # scanpy使用不同的列名
    genes_col = "n_genes_by_counts" if "n_genes_by_counts" in adata.obs.columns else "n_genes"
    counts_col = "total_counts" if "total_counts" in adata.obs.columns else "n_counts"
    mito_col = "pct_counts_mt" if "pct_counts_mt" in adata.obs.columns else "pct_mito"

    summary = {
        "n_cells": adata.shape[0],
        "n_genes": adata.shape[1],
        "n_genes_stats": {
            "mean": float(adata.obs[genes_col].mean()),
            "median": float(adata.obs[genes_col].median()),
            "std": float(adata.obs[genes_col].std()),
            "min": float(adata.obs[genes_col].min()),
            "max": float(adata.obs[genes_col].max()),
        },
        "n_counts_stats": {
            "mean": float(adata.obs[counts_col].mean()),
            "median": float(adata.obs[counts_col].median()),
            "std": float(adata.obs[counts_col].std()),
            "min": float(adata.obs[counts_col].min()),
            "max": float(adata.obs[counts_col].max()),
        },
    }

    if mito_col in adata.obs.columns:
        summary["pct_mito_stats"] = {
            "mean": float(adata.obs[mito_col].mean()),
            "median": float(adata.obs[mito_col].median()),
            "std": float(adata.obs[mito_col].std()),
            "min": float(adata.obs[mito_col].min()),
            "max": float(adata.obs[mito_col].max()),
        }

    return summary


def run_qc_pipeline(
    adata: AnnData,
    params: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    完整的QC流程 (使用scanpy标准方法)

    参考: https://scanpy.readthedocs.io/en/stable/tutorials/basics/quality-control.html

    Args:
        adata: AnnData对象
        params: QC参数
        output_dir: 输出目录

    Returns:
        包含过滤后数据和QC结果的字典
    """
    if params is None:
        params = {}

    # 使用更合理的默认参数（参考scanpy官方教程）
    min_genes = params.get("min_genes", 200)
    min_cells = params.get("min_cells", 3)
    max_pct_mito = params.get("max_pct_mito", 20.0)
    min_counts = params.get("min_counts", None)

    logger.info("开始QC流程...")
    logger.info(f"参数设置:")
    logger.info(f"  - min_genes: {min_genes}")
    logger.info(f"  - min_cells: {min_cells}")
    logger.info(f"  - max_pct_mito: {max_pct_mito}%")
    if min_counts:
        logger.info(f"  - min_counts: {min_counts}")

    # 计算QC指标
    adata = calculate_qc_metrics(adata)

    # 记录原始数据大小
    n_cells_before = adata.shape[0]
    n_genes_before = adata.shape[1]

    # 过滤细胞和基因
    adata = filter_cells(adata, min_genes=min_genes, min_cells=min_cells, min_counts=min_counts)

    # 过滤线粒体
    adata = filter_mito(adata, max_pct=max_pct_mito)

    # 生成图表
    plot_files = []
    if output_dir:
        plot_files = generate_qc_plots(adata, output_dir)

    # 获取摘要
    summary = get_qc_summary(adata)
    summary["filtering_stats"] = {
        "cells_before": n_cells_before,
        "cells_after": adata.shape[0],
        "genes_before": n_genes_before,
        "genes_after": adata.shape[1],
        "cells_removed": n_cells_before - adata.shape[0],
        "genes_removed": n_genes_before - adata.shape[1],
    }

    logger.info("QC流程完成")

    return {
        "adata": adata,
        "summary": summary,
        "plot_files": plot_files,
    }
