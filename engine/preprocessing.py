"""
Preprocessing Module
数据预处理模块
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import numpy as np
from anndata import AnnData
import scanpy as sc
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)


def normalize_data(
    adata: AnnData,
    target_sum: Optional[float] = 1e4,
) -> AnnData:
    """
    归一化数据

    Args:
        adata: AnnData对象
        target_sum: 目标总表达量

    Returns:
        归一化后的AnnData对象
    """
    logger.info("正在进行归一化...")

    # 保存原始计数（仅在不存在时保存，避免重复运行时覆盖）
    if "counts" not in adata.layers:
        adata.layers["counts"] = adata.X.copy()
    else:
        logger.info("counts layer已存在，跳过保存")

    # 归一化
    sc.pp.normalize_total(adata, target_sum=target_sum)

    logger.info("归一化完成")
    return adata


def log_transform(adata: AnnData) -> AnnData:
    """
    log转换

    Args:
        adata: AnnData对象

    Returns:
        log转换后的AnnData对象
    """
    logger.info("正在进行log转换...")

    sc.pp.log1p(adata)

    # 记录使用的转换方法
    adata.uns["log1p"] = {"base": None}

    logger.info("log转换完成")
    return adata


def select_hvg(
    adata: AnnData,
    n_top_genes: int = 2000,
    flavor: str = "seurat",
) -> AnnData:
    """
    筛选高变基因 (Highly Variable Genes)

    Args:
        adata: AnnData对象
        n_top_genes: 选择的高变基因数量
        flavor: HVG选择方法

    Returns:
        添加了HVG信息的AnnData对象
    """
    logger.info(f"正在筛选Top {n_top_genes} 高变基因...")

    # 确保数据已经归一化和log转换
    if "log1p" not in adata.uns:
        logger.warning("数据可能未经过log转换，建议先执行log_transform")

    # 计算高变基因
    sc.pp.highly_variable_genes(
        adata,
        n_top_genes=n_top_genes,
        flavor=flavor,
        batch_key=None,
    )

    n_hvg = adata.var["highly_variable"].sum()
    logger.info(f"筛选出 {n_hvg} 个高变基因")

    return adata


def standardize_data(adata: AnnData) -> AnnData:
    """
    数据标准化（缩放到方差为1）

    Args:
        adata: AnnData对象

    Returns:
        标准化后的AnnData对象
    """
    logger.info("正在进行数据标准化...")

    # 对所有基因进行标准化
    sc.pp.scale(adata, max_value=10)

    logger.info("数据标准化完成")
    return adata


def apply_pca(
    adata: AnnData,
    n_comps: int = 50,
    use_highly_variable: bool = True,
) -> AnnData:
    """
    应用PCA降维（预处理步骤）

    Args:
        adata: AnnData对象
        n_comps: 主成分数量
        use_highly_variable: 是否只使用高变基因

    Returns:
        添加了PCA结果的AnnData对象
    """
    logger.info(f"正在进行PCA降维 (n_comps={n_comps})...")

    # 确定使用的基因
    if use_highly_variable and "highly_variable" in adata.var.columns:
        use_rep = adata[:, adata.var["highly_variable"]]
    else:
        use_rep = adata

    # 执行PCA
    sc.tl.pca(use_rep, n_comps=n_comps, svd_solver="arpack")

    # 将PCA结果复制到主对象
    adata.obsm["X_pca"] = use_rep.obsm["X_pca"]
    adata.uns["pca"] = use_rep.uns["pca"]
    adata.varm["PCs"] = np.zeros((adata.shape[1], n_comps))
    if "highly_variable" in adata.var.columns:
        hvg_mask = adata.var["highly_variable"]
        adata.varm["PCs"][hvg_mask] = use_rep.varm["PCs"]

    logger.info("PCA降维完成")
    return adata


def run_preprocessing_pipeline(
    adata: AnnData,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    完整的预处理流程

    Args:
        adata: AnnData对象
        params: 预处理参数

    Returns:
        包含预处理后数据和信息的字典
    """
    if params is None:
        params = {}

    target_sum = params.get("target_sum", 1e4)
    n_top_genes = params.get("n_top_genes", 2000)
    n_pcs = params.get("n_pcs", 50)

    logger.info("开始预处理流程...")

    # 记录原始数据形状
    original_shape = adata.shape

    # 1. 归一化
    adata = normalize_data(adata, target_sum=target_sum)

    # 2. log转换
    adata = log_transform(adata)

    # 3. 筛选高变基因
    adata = select_hvg(adata, n_top_genes=n_top_genes)

    # 4. 标准化
    adata = standardize_data(adata)

    # 5. PCA降维
    adata = apply_pca(adata, n_comps=n_pcs)

    # 6. 生成预处理图表
    plot_files = generate_preprocessing_plots(adata, output_dir=params.get("output_dir", "storage/results"))

    # 生成预处理摘要
    summary = {
        "original_shape": original_shape,
        "final_shape": adata.shape,
        "n_hvg": int(adata.var["highly_variable"].sum()) if "highly_variable" in adata.var.columns else 0,
        "n_pcs": n_pcs,
        "steps": [
            "归一化 (Normalize Total)",
            "log转换 (Log1p)",
            "高变基因筛选 (HVG Selection)",
            "数据标准化 (Scale)",
            "PCA降维",
        ],
    }

    logger.info("预处理流程完成")

    return {
        "adata": adata,
        "summary": summary,
        "plot_files": plot_files,
    }


def generate_preprocessing_plots(
    adata: AnnData,
    output_dir: str = "storage/results",
) -> List[str]:
    """
    生成预处理相关图表

    包括：
    1. HVG筛选结果图（dispersion vs mean expression）
    2. 基因表达分布图（归一化后）

    Args:
        adata: 预处理后的AnnData对象
        output_dir: 图表输出目录

    Returns:
        生成的图表文件路径列表
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    plot_files = []

    # 1. HVG筛选结果图
    if "highly_variable" in adata.var.columns:
        try:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))

            # 获取HVG信息
            hvg_col = "highly_variable"
            mean_expr = adata.var["means"].values if "means" in adata.var.columns else None
            dispersions = adata.var["dispersions"].values if "dispersions" in adata.var.columns else None

            if mean_expr is not None and dispersions is not None:
                is_hvg = adata.var[hvg_col].values

                # 绘制散点图
                ax.scatter(mean_expr[~is_hvg], dispersions[~is_hvg],
                          c="gray", alpha=0.3, s=5, label="Non-HVG")
                ax.scatter(mean_expr[is_hvg], dispersions[is_hvg],
                          c="red", alpha=0.5, s=10, label=f"HVG (n={is_hvg.sum()})")

                ax.set_xlabel("Mean Expression")
                ax.set_ylabel("Dispersion")
                ax.set_title("Highly Variable Gene Selection")
                ax.set_xscale("log")
                ax.legend()
                ax.grid(True, alpha=0.3)
            else:
                # 简化版：只显示HVG比例
                n_hvg = adata.var[hvg_col].sum()
                n_total = len(adata.var)
                ax.bar(["HVG", "Non-HVG"], [n_hvg, n_total - n_hvg], color=["red", "gray"])
                ax.set_ylabel("Number of Genes")
                ax.set_title(f"Gene Selection: {n_hvg}/{n_total} HVG")
                for i, v in enumerate([n_hvg, n_total - n_hvg]):
                    ax.text(i, v + 10, str(v), ha="center", fontweight="bold")

            plt.tight_layout()
            plot_file = str(output_path / "preprocessing_hvg.png")
            fig.savefig(plot_file, dpi=150, bbox_inches="tight")
            plt.close(fig)
            plot_files.append(plot_file)
            logger.info(f"HVG筛选图已保存: {plot_file}")

        except Exception as e:
            logger.warning(f"HVG筛选图生成失败: {e}")
            plt.close("all")

    # 2. 基因表达分布图（归一化后）
    try:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 左图：基因表达量分布
        if hasattr(adata.X, "toarray"):
            expr_data = np.array(adata.X.mean(axis=0)).flatten()
        else:
            expr_data = np.array(adata.X.mean(axis=0)).flatten()

        # 过滤零值
        expr_data = expr_data[expr_data > 0]

        if len(expr_data) > 0:
            axes[0].hist(np.log1p(expr_data), bins=50, color="steelblue", alpha=0.7, edgecolor="white")
            axes[0].set_xlabel("log1p(Mean Expression)")
            axes[0].set_ylabel("Number of Genes")
            axes[0].set_title("Gene Expression Distribution (Normalized)")
            axes[0].grid(True, alpha=0.3)

        # 右图：每细胞UMI分布
        if hasattr(adata.X, "sum"):
            cell_counts = np.array(adata.X.sum(axis=1)).flatten()
        else:
            cell_counts = np.array(adata.X.sum(axis=1)).flatten()

        axes[1].hist(cell_counts, bins=50, color="coral", alpha=0.7, edgecolor="white")
        axes[1].set_xlabel("Total UMI Counts per Cell")
        axes[1].set_ylabel("Number of Cells")
        axes[1].set_title("UMI Count Distribution (Normalized)")
        axes[1].grid(True, alpha=0.3)

        plt.suptitle("Preprocessing Results Overview", fontsize=14, fontweight="bold")
        plt.tight_layout()
        plot_file = str(output_path / "preprocessing_distribution.png")
        fig.savefig(plot_file, dpi=150, bbox_inches="tight")
        plt.close(fig)
        plot_files.append(plot_file)
        logger.info(f"表达分布图已保存: {plot_file}")

    except Exception as e:
        logger.warning(f"表达分布图生成失败: {e}")
        plt.close("all")

    return plot_files
