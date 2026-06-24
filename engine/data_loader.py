"""
Data Loader Module
数据读取与概览模块
"""

from pathlib import Path
from typing import Dict, Any, Optional
import anndata as ad
from anndata import AnnData
import scanpy as sc
import logging

logger = logging.getLogger(__name__)


def load_h5ad(file_path: str) -> AnnData:
    """
    读取.h5ad格式的空间转录组数据文件

    Args:
        file_path: h5ad文件路径

    Returns:
        AnnData对象

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不支持
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if path.suffix.lower() not in [".h5ad", ".h5"]:
        raise ValueError(f"不支持的文件格式: {path.suffix}")

    logger.info(f"正在读取文件: {file_path}")

    try:
        adata = ad.read_h5ad(file_path)
        logger.info(f"成功读取数据: {adata.shape[0]} cells, {adata.shape[1]} genes")
        return adata
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        raise


def get_data_summary(adata: AnnData, show_obs: bool = True, show_var: bool = True) -> Dict[str, Any]:
    """
    获取数据集概览信息

    Args:
        adata: AnnData对象
        show_obs: 是否显示obs数据内容
        show_var: 是否显示var数据内容

    Returns:
        包含数据集基本信息的字典
    """
    summary = {
        "n_cells": adata.shape[0],
        "n_genes": adata.shape[1],
        "shape": adata.shape,
        "obs_columns": list(adata.obs.columns),
        "var_columns": list(adata.var.columns),
        "obs_names": list(adata.obs_names[:10]),  # 前10个细胞名称
        "var_names": list(adata.var_names[:10]),  # 前10个基因名称
    }

    # 添加obs和var的数据内容
    if show_obs:
        summary["obs_data"] = adata.obs.head(10).to_dict()  # 前10行数据
        summary["obs_dtypes"] = {col: str(dtype) for col, dtype in adata.obs.dtypes.items()}

    if show_var:
        summary["var_data"] = adata.var.head(10).to_dict()  # 前10行数据
        summary["var_dtypes"] = {col: str(dtype) for col, dtype in adata.var.dtypes.items()}

    # 检查是否有空间信息
    # 检查多种可能的空间坐标键名
    spatial_key = None
    if adata.obsm is not None:
        for key in ["spatial", "X_spatial", "spatial_coords"]:
            if key in adata.obsm:
                spatial_key = key
                break

    if spatial_key:
        summary["has_spatial"] = True
        spatial_coords = adata.obsm[spatial_key]
        summary["spatial_key"] = spatial_key
        summary["spatial_shape"] = spatial_coords.shape
        summary["spatial_bounds"] = {
            "x_min": float(spatial_coords[:, 0].min()),
            "x_max": float(spatial_coords[:, 0].max()),
            "y_min": float(spatial_coords[:, 1].min()),
            "y_max": float(spatial_coords[:, 1].max()),
        }
    else:
        summary["has_spatial"] = False

    # 检查是否有聚类信息
    if "cluster" in adata.obs.columns or "leiden" in adata.obs.columns:
        cluster_key = "cluster" if "cluster" in adata.obs.columns else "leiden"
        summary["n_clusters"] = adata.obs[cluster_key].nunique()
        summary["cluster_column"] = cluster_key

    # 检查是否有细胞类型注释
    if "cell_type" in adata.obs.columns:
        summary["n_cell_types"] = adata.obs["cell_type"].nunique()
        summary["cell_types"] = list(adata.obs["cell_type"].unique())

    return summary


def validate_data(adata: AnnData) -> Dict[str, Any]:
    """
    数据验证

    Args:
        adata: AnnData对象

    Returns:
        验证结果字典
    """
    validation = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
    }

    # 检查数据是否为空
    if adata.shape[0] == 0:
        validation["errors"].append("数据集为空（无细胞）")
        validation["is_valid"] = False

    if adata.shape[1] == 0:
        validation["errors"].append("数据集为空（无基因）")
        validation["is_valid"] = False

    # 检查是否有表达矩阵
    if adata.X is None:
        validation["errors"].append("缺少表达矩阵")
        validation["is_valid"] = False

    # 检查是否有空间坐标
    if adata.obsm is None or "spatial" not in adata.obsm:
        validation["warnings"].append("缺少空间坐标信息")

    # 检查是否有足够的细胞进行分析
    if adata.shape[0] < 100:
        validation["warnings"].append(f"细胞数量较少: {adata.shape[0]}")

    # 检查是否有足够的基因进行分析
    if adata.shape[1] < 100:
        validation["warnings"].append(f"基因数量较少: {adata.shape[1]}")

    # 检查表达矩阵是否包含NaN
    if hasattr(adata.X, "toarray"):
        import numpy as np
        x_array = adata.X.toarray()
        if np.isnan(x_array).any():
            validation["warnings"].append("表达矩阵包含NaN值")
    else:
        import numpy as np
        if np.isnan(adata.X).any():
            validation["warnings"].append("表达矩阵包含NaN值")

    return validation


def save_adata(adata: AnnData, file_path: str) -> None:
    """
    保存AnnData对象到h5ad文件

    Args:
        adata: AnnData对象
        file_path: 保存路径
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"正在保存数据到: {file_path}")
    adata.write_h5ad(file_path)
    logger.info(f"成功保存数据")


def create_sample_data() -> AnnData:
    """
    创建示例数据用于测试

    Returns:
        AnnData对象
    """
    import numpy as np
    import pandas as pd

    # 创建随机表达矩阵
    n_cells = 500
    n_genes = 1000
    np.random.seed(42)

    X = np.random.poisson(2, size=(n_cells, n_genes)).astype(np.float32)

    # 创建obs和var
    obs = pd.DataFrame(
        {
            "cell_id": [f"cell_{i}" for i in range(n_cells)],
            "n_genes": np.random.randint(100, 500, n_cells),
            "n_counts": np.random.randint(500, 5000, n_cells),
            "pct_mito": np.random.uniform(0, 30, n_cells),
        },
        index=[f"cell_{i}" for i in range(n_cells)],
    )

    var = pd.DataFrame(
        {
            "gene_id": [f"gene_{i}" for i in range(n_genes)],
            "n_cells": np.random.randint(10, 200, n_genes),
        },
        index=[f"gene_{i}" for i in range(n_genes)],
    )

    # 创建空间坐标
    spatial = np.random.uniform(0, 100, size=(n_cells, 2))

    # 创建AnnData对象
    adata = AnnData(X=X, obs=obs, var=var)
    adata.obsm["spatial"] = spatial

    # 添加聚类信息
    from sklearn.cluster import KMeans

    kmeans = KMeans(n_clusters=5, random_state=42)
    adata.obs["cluster"] = kmeans.fit_predict(X).astype(str)

    logger.info(f"创建示例数据: {adata.shape[0]} cells, {adata.shape[1]} genes")
    return adata
