"""
Spatial Visualization Module
空间可视化模块
"""

from pathlib import Path
from typing import List, Optional, Union
import numpy as np
from anndata import AnnData
import scanpy as sc
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logger = logging.getLogger(__name__)


def check_adata_valid(adata: AnnData, min_cells: int = 1) -> bool:
    """
    检查AnnData对象是否有效

    Args:
        adata: AnnData对象
        min_cells: 最小细胞数

    Returns:
        是否有效
    """
    if adata is None:
        logger.error("AnnData对象为None")
        return False
    if adata.shape[0] < min_cells:
        logger.error(f"细胞数不足: {adata.shape[0]} < {min_cells}")
        return False
    if adata.shape[1] == 0:
        logger.error("基因数为0")
        return False
    return True


def check_spatial_data(adata: AnnData) -> bool:
    """
    检查数据是否包含空间坐标

    Args:
        adata: AnnData对象

    Returns:
        是否包含空间坐标
    """
    # 检查多种可能的空间坐标键名
    if adata.obsm is None:
        logger.warning("数据中未找到空间坐标信息 (adata.obsm为空)")
        return False

    for key in ["spatial", "X_spatial", "spatial_coords"]:
        if key in adata.obsm:
            return True

    logger.warning("数据中未找到空间坐标信息")
    return False


def get_spatial_coords(adata: AnnData) -> Optional[np.ndarray]:
    """
    获取空间坐标

    Args:
        adata: AnnData对象

    Returns:
        空间坐标数组，如果没有则返回None
    """
    if adata.obsm is None:
        return None

    for key in ["spatial", "X_spatial", "spatial_coords"]:
        if key in adata.obsm:
            return adata.obsm[key]

    return None


def plot_spatial_distribution(
    adata: AnnData,
    output_dir: str,
    color: Optional[str] = None,
    size: float = 1.0,
    use_3d: bool = True,
) -> str:
    """
    绘制cell/spot空间分布图 (支持2D和3D)

    Args:
        adata: AnnData对象
        output_dir: 输出目录
        color: 着色依据 (列名)
        size: 点大小
        use_3d: 是否使用3D可视化

    Returns:
        生成的图表文件路径
    """
    if not check_adata_valid(adata):
        return ""
    if not check_spatial_data(adata):
        logger.error("无法绘制空间分布图：缺少空间坐标")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("正在绘制空间分布图...")

    # 获取空间坐标
    spatial_coords = get_spatial_coords(adata)

    # 检查是否有z坐标
    has_z = False
    z_coords = None

    if use_3d:
        # 方法1：检查X_spatial是否有3维
        if spatial_coords.shape[1] >= 3:
            has_z = True
            z_coords = spatial_coords[:, 2]
        # 方法2：检查obs中是否有z列
        elif "z" in adata.obs.columns:
            has_z = True
            z_coords = adata.obs["z"].values

    if has_z and use_3d:
        # 3D可视化
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        if color and color in adata.obs.columns:
            # 对分类变量进行编码
            if adata.obs[color].dtype.name == 'category' or adata.obs[color].dtype == object:
                unique_vals = adata.obs[color].unique()
                color_map = {val: i for i, val in enumerate(unique_vals)}
                color_encoded = adata.obs[color].map(color_map)
                scatter = ax.scatter(
                    spatial_coords[:, 0],
                    spatial_coords[:, 1],
                    z_coords,
                    c=color_encoded,
                    cmap="tab20",
                    s=size,
                    alpha=0.7,
                )
            else:
                scatter = ax.scatter(
                    spatial_coords[:, 0],
                    spatial_coords[:, 1],
                    z_coords,
                    c=adata.obs[color],
                    cmap="viridis",
                    s=size,
                    alpha=0.7,
                )
            plt.colorbar(scatter, ax=ax, label=color)
        else:
            ax.scatter(
                spatial_coords[:, 0],
                spatial_coords[:, 1],
                z_coords,
                c="steelblue",
                s=size,
                alpha=0.7,
            )

        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_zlabel("Z Coordinate")
        ax.set_title("3D Spatial Distribution of Cells/Spots")

        plot_path = output_path / "spatial_distribution_3d.png"
    else:
        # 2D可视化
        fig, ax = plt.subplots(figsize=(10, 10))

        if color and color in adata.obs.columns:
            scatter = ax.scatter(
                spatial_coords[:, 0],
                spatial_coords[:, 1],
                c=adata.obs[color],
                cmap="tab20",
                s=size,
                alpha=0.7,
            )
            plt.colorbar(scatter, ax=ax, label=color)
        else:
            ax.scatter(
                spatial_coords[:, 0],
                spatial_coords[:, 1],
                c="steelblue",
                s=size,
                alpha=0.7,
            )

        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_title("Spatial Distribution of Cells/Spots")
        ax.set_aspect("equal")

        plot_path = output_path / "spatial_distribution.png"

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"空间分布图已保存: {plot_path}")
    return str(plot_path)


def plot_cluster_spatial(
    adata: AnnData,
    output_dir: str,
    cluster_key: str = "leiden",
    size: float = 3.0,
    use_3d: bool = True,
) -> str:
    """
    绘制cluster空间分布图 (支持2D和3D)

    Args:
        adata: AnnData对象
        output_dir: 输出目录
        cluster_key: 聚类结果的列名
        size: 点大小
        use_3d: 是否使用3D可视化

    Returns:
        生成的图表文件路径
    """
    if not check_adata_valid(adata):
        return ""
    if not check_spatial_data(adata):
        logger.error("无法绘制cluster空间图：缺少空间坐标")
        return ""

    if cluster_key not in adata.obs.columns:
        logger.error(f"未找到聚类结果列: {cluster_key}")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"正在绘制{cluster_key}空间分布图...")

    # 获取空间坐标
    spatial_coords = get_spatial_coords(adata)

    # 检查是否有z坐标
    has_z = False
    z_coords = None

    if use_3d:
        if spatial_coords.shape[1] >= 3:
            has_z = True
            z_coords = spatial_coords[:, 2]
        elif "z" in adata.obs.columns:
            has_z = True
            z_coords = adata.obs["z"].values

    # 获取唯一的cluster及其颜色
    clusters = adata.obs[cluster_key].unique()
    n_clusters = len(clusters)

    # 使用更鲜明的颜色
    import matplotlib.colors as mcolors
    colors = list(mcolors.TABLEAU_COLORS.keys())[:n_clusters]
    color_map = {cluster: colors[i] for i, cluster in enumerate(sorted(clusters, key=lambda x: int(x) if x.isdigit() else x))}

    if has_z and use_3d:
        # 3D可视化
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        # 绘制每个cluster
        for cluster in sorted(clusters, key=lambda x: int(x) if x.isdigit() else x):
            mask = adata.obs[cluster_key] == cluster
            ax.scatter(
                spatial_coords[mask, 0],
                spatial_coords[mask, 1],
                z_coords[mask],
                c=[color_map[cluster]],
                s=size,
                alpha=0.7,
                label=f"Cluster {cluster}",
            )

        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_zlabel("Z Coordinate")
        ax.set_title(f"3D Spatial Distribution - {cluster_key}")
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", markerscale=3)

        plot_path = output_path / f"spatial_{cluster_key}_3d.png"
    else:
        # 2D可视化
        fig, ax = plt.subplots(figsize=(10, 10))

        # 绘制每个cluster
        for cluster in sorted(clusters, key=lambda x: int(x) if x.isdigit() else x):
            mask = adata.obs[cluster_key] == cluster
            ax.scatter(
                spatial_coords[mask, 0],
                spatial_coords[mask, 1],
                c=[color_map[cluster]],
                s=size,
                alpha=0.7,
                label=f"Cluster {cluster}",
            )

        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_title(f"Spatial Distribution - {cluster_key}")
        ax.set_aspect("equal")
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", markerscale=3)

        plot_path = output_path / f"spatial_{cluster_key}.png"

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Cluster空间图已保存: {plot_path}")
    return str(plot_path)


def plot_gene_spatial(
    adata: AnnData,
    gene: str,
    output_dir: str,
    size: float = 3.0,
    use_raw: bool = False,
    use_3d: bool = True,
) -> str:
    """
    绘制基因空间表达图 (支持2D和3D)

    Args:
        adata: AnnData对象
        gene: 基因名称
        output_dir: 输出目录
        size: 点大小
        use_raw: 是否使用原始数据
        use_3d: 是否使用3D可视化

    Returns:
        生成的图表文件路径
    """
    if not check_adata_valid(adata):
        return ""
    if not check_spatial_data(adata):
        logger.error("无法绘制基因空间图：缺少空间坐标")
        return ""

    if gene not in adata.var_names:
        logger.error(f"基因 {gene} 不在数据中")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"正在绘制基因 {gene} 的空间表达图...")

    # 获取空间坐标
    spatial_coords = get_spatial_coords(adata)

    # 获取基因表达量
    gene_idx = list(adata.var_names).index(gene)
    if use_raw and adata.raw is not None:
        gene_expr = adata.raw.X[:, gene_idx].toarray().flatten()
    else:
        gene_expr = adata.X[:, gene_idx]
        if hasattr(gene_expr, "toarray"):
            gene_expr = gene_expr.toarray().flatten()
        else:
            gene_expr = np.array(gene_expr).flatten()

    # 检查是否有z坐标
    has_z = False
    z_coords = None

    if use_3d:
        if spatial_coords.shape[1] >= 3:
            has_z = True
            z_coords = spatial_coords[:, 2]
        elif "z" in adata.obs.columns:
            has_z = True
            z_coords = adata.obs["z"].values

    if has_z and use_3d:
        # 3D可视化
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        scatter = ax.scatter(
            spatial_coords[:, 0],
            spatial_coords[:, 1],
            z_coords,
            c=gene_expr,
            cmap="viridis",
            s=size,
            alpha=0.7,
        )

        plt.colorbar(scatter, ax=ax, label=f"{gene} Expression", shrink=0.6)

        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_zlabel("Z Coordinate")
        ax.set_title(f"3D Spatial Expression - {gene}")

        plot_path = output_path / f"spatial_gene_{gene}_3d.png"
    else:
        # 2D可视化
        fig, ax = plt.subplots(figsize=(10, 10))

        scatter = ax.scatter(
            spatial_coords[:, 0],
            spatial_coords[:, 1],
            c=gene_expr,
            cmap="viridis",
            s=size,
            alpha=0.7,
        )

        plt.colorbar(scatter, ax=ax, label=f"{gene} Expression")

        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_title(f"Spatial Expression - {gene}")
        ax.set_aspect("equal")

        plot_path = output_path / f"spatial_gene_{gene}.png"

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"基因空间图已保存: {plot_path}")
    return str(plot_path)


def plot_embedding(
    adata: AnnData,
    basis: str = "umap",
    output_dir: str = "",
    color: Optional[Union[str, List[str]]] = None,
    size: float = 1.0,
) -> str:
    """
    绘制降维图

    Args:
        adata: AnnData对象
        basis: 降维方法 (umap, pca, tsne)
        output_dir: 输出目录
        color: 着色依据
        size: 点大小

    Returns:
        生成的图表文件路径
    """
    if not check_adata_valid(adata):
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"正在绘制{basis.upper()}图...")

    # 检查是否有对应的降维结果
    key = f"X_{basis}"
    if key not in adata.obsm:
        logger.error(f"未找到 {basis.upper()} 降维结果")
        return ""

    fig, ax = plt.subplots(figsize=(10, 8))

    # 使用scanpy绘图
    sc.pl.embedding(
        adata,
        basis=basis,
        color=color,
        ax=ax,
        show=False,
        title=f"{basis.upper()} Embedding",
    )

    plt.tight_layout()
    plot_path = output_path / f"{basis}_embedding.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"{basis.upper()}图已保存: {plot_path}")
    return str(plot_path)


def plot_spatial_comparison(
    adata: AnnData,
    gene1: str,
    gene2: str,
    output_dir: str,
    size: float = 3.0,
) -> str:
    """
    绘制两个基因的空间表达对比图

    Args:
        adata: AnnData对象
        gene1: 基因1名称
        gene2: 基因2名称
        output_dir: 输出目录
        size: 点大小

    Returns:
        生成的图表文件路径
    """
    if not check_spatial_data(adata):
        logger.error("无法绘制基因对比图：缺少空间坐标")
        return ""

    if gene1 not in adata.var_names or gene2 not in adata.var_names:
        logger.error(f"基因 {gene1} 或 {gene2} 不在数据中")
        return ""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"正在绘制基因 {gene1} vs {gene2} 的空间对比图...")

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # 获取空间坐标
    spatial_coords = get_spatial_coords(adata)

    # 获取基因表达量
    for ax, gene in zip(axes, [gene1, gene2]):
        gene_idx = list(adata.var_names).index(gene)
        gene_expr = adata.X[:, gene_idx]
        if hasattr(gene_expr, "toarray"):
            gene_expr = gene_expr.toarray().flatten()
        else:
            gene_expr = np.array(gene_expr).flatten()

        scatter = ax.scatter(
            spatial_coords[:, 0],
            spatial_coords[:, 1],
            c=gene_expr,
            cmap="viridis",
            s=size,
            alpha=0.7,
        )
        plt.colorbar(scatter, ax=ax, label=f"{gene} Expression")
        ax.set_xlabel("X Coordinate")
        ax.set_ylabel("Y Coordinate")
        ax.set_title(f"Spatial Expression - {gene}")
        ax.set_aspect("equal")

    plt.tight_layout()
    plot_path = output_path / f"spatial_compare_{gene1}_{gene2}.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"基因对比图已保存: {plot_path}")
    return str(plot_path)


def select_highly_expressed_genes(
    adata: AnnData,
    n_genes: int = 5,
    min_expr: float = 1.0,
    min_cells_pct: float = 0.5,
) -> List[str]:
    """
    自动选择高表达基因用于可视化

    Args:
        adata: AnnData对象
        n_genes: 返回的基因数量
        min_expr: 最小平均表达量
        min_cells_pct: 最小表达细胞比例

    Returns:
        高表达基因列表
    """
    # 计算每个基因的统计量
    if hasattr(adata.X, 'toarray'):
        X = adata.X.toarray()
    else:
        X = adata.X

    mean_expr = X.mean(axis=0)
    non_zero_cells = (X > 0).sum(axis=0)
    total_cells = adata.shape[0]

    # 筛选条件
    high_expr_mask = (
        (mean_expr > min_expr) &
        (non_zero_cells > total_cells * min_cells_pct)
    )

    # 按表达量排序，返回top N
    high_expr_idx = np.where(high_expr_mask)[0]
    if len(high_expr_idx) == 0:
        # 如果没有满足条件的基因，降低标准
        high_expr_idx = np.argsort(mean_expr)[-n_genes:][::-1]
    else:
        sorted_idx = high_expr_idx[np.argsort(mean_expr[high_expr_idx])[::-1]]
        high_expr_idx = sorted_idx[:n_genes]

    selected_genes = [adata.var_names[i] for i in high_expr_idx]

    logger.info(f"选择了 {len(selected_genes)} 个高表达基因: {selected_genes}")
    return selected_genes


def generate_spatial_plots(
    adata: AnnData,
    output_dir: str,
    cluster_key: str = "leiden",
    genes: Optional[List[str]] = None,
    use_3d: bool = True,
) -> List[str]:
    """
    生成所有空间可视化图表 (支持2D和3D)

    Args:
        adata: AnnData对象
        output_dir: 输出目录
        cluster_key: 聚类结果的列名
        genes: 要可视化的基因列表
        use_3d: 是否使用3D可视化

    Returns:
        生成的图表文件路径列表
    """
    plot_files = []

    # 1. 空间分布图
    spatial_dist_path = plot_spatial_distribution(adata, output_dir, use_3d=use_3d)
    if spatial_dist_path:
        plot_files.append(spatial_dist_path)

    # 2. Cluster空间图
    if cluster_key in adata.obs.columns:
        cluster_spatial_path = plot_cluster_spatial(adata, output_dir, cluster_key, use_3d=use_3d)
        if cluster_spatial_path:
            plot_files.append(cluster_spatial_path)

    # 3. 基因空间图
    if genes:
        for gene in genes:
            gene_path = plot_gene_spatial(adata, gene, output_dir, use_3d=use_3d)
            if gene_path:
                plot_files.append(gene_path)

    # 4. UMAP图 (2D)
    if "X_umap" in adata.obsm:
        umap_path = plot_embedding(adata, "umap", output_dir, color=cluster_key if cluster_key in adata.obs.columns else None)
        if umap_path:
            plot_files.append(umap_path)

    logger.info(f"共生成 {len(plot_files)} 个空间可视化图表")
    return plot_files
