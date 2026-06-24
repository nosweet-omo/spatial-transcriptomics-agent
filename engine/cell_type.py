"""
细胞类型自动注释模块

使用CellTypist进行基于参考数据集的自动细胞类型注释。
如果CellTypist不可用，降级为基于Marker基因关键词匹配的规则注释。
"""

import os
import logging
from typing import Dict, Any, List, Optional

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def _check_celltypist_available() -> bool:
    """检查CellTypist是否可用"""
    try:
        import celltypist
        return True
    except ImportError:
        return False


def annotate_cell_types_celltypist(
    adata,
    model_name: str = "Immune_All_Low",
    cluster_key: str = "leiden",
    layer: Optional[str] = None,
    majority_voting: bool = False,
) -> Any:
    """
    使用CellTypist进行细胞类型注释

    Args:
        adata: AnnData对象
        model_name: CellTypist模型名称
            常用模型:
            - "Immune_All_Low" - 免疫细胞（低分辨率）
            - "Immune_All_High" - 免疫细胞（高分辨率）
            - "Adult_Mouse_Brain" - 小鼠脑组织
            - "Adult_Human_Brain" - 人脑组织
        cluster_key: 聚类结果的列名
        layer: 使用哪个layer的数据（None则使用X）
        majority_voting: 是否使用majority voting后处理

    Returns:
        注释后的AnnData对象（cell_type列写入adata.obs）
    """
    import celltypist
    from celltypist import annotate

    logger.info(f"使用CellTypist模型 {model_name} 进行细胞类型注释")

    # 准备数据：CellTypist要求基因名为小写首字母大写格式
    adata_for_annot = adata.copy()

    # 基因名格式转换：将基因名转为CellTypist期望的格式
    # CellTypist模型通常使用首字母大写的基因名（如 Epcam, Pecam1）
    gene_names = adata_for_annot.var_names.tolist()
    # 尝试将Ensembl ID转换为基因名（如果有的话）
    if hasattr(adata_for_annot.var, 'gene_name') and 'gene_name' in adata_for_annot.var.columns:
        new_names = adata_for_annot.var['gene_name'].tolist()
        # 用gene_name替换，保留原始名称作为备份
        adata_for_annot.var['original_gene_name'] = adata_for_annot.var_names.copy()
        adata_for_annot.var_names = [str(n) if n and str(n) != 'nan' else orig
                                      for n, orig in zip(new_names, gene_names)]

    # 去除重复基因名
    _, unique_mask = np.unique(adata_for_annot.var_names, return_index=True)
    adata_for_annot = adata_for_annot[:, unique_mask].copy()

    # 执行注释
    try:
        if layer:
            predictions = annotate(
                adata_for_annot,
                model=model_name,
                layer=layer,
                majority_voting=majority_voting,
                mode='best match'
            )
        else:
            predictions = annotate(
                adata_for_annot,
                model=model_name,
                majority_voting=majority_voting,
                mode='best match'
            )

        # 将预测结果写入adata.obs
        pred_df = predictions.predicted_labels
        adata.obs['cell_type'] = pred_df.iloc[:, 0].values.astype(str)
        adata.obs['cell_type_confidence'] = pred_df.iloc[:, 1].values if pred_df.shape[1] > 1 else 1.0

        # 如果有聚类信息，统计每个cluster的主要细胞类型
        if cluster_key in adata.obs.columns:
            cluster_celltype = adata.obs.groupby(cluster_key)['cell_type'].agg(
                lambda x: x.value_counts().index[0] if len(x) > 0 else 'Unknown'
            ).to_dict()
            adata.uns['cluster_celltype_mapping'] = cluster_celltype
            logger.info(f"Cluster-细胞类型映射: {cluster_celltype}")

        logger.info(f"CellTypist注释完成，共 {adata.obs['cell_type'].nunique()} 种细胞类型")
        return adata

    except Exception as e:
        logger.error(f"CellTypist注释失败: {e}")
        raise


def annotate_cell_types_rule_based(
    adata,
    cluster_key: str = "leiden",
) -> Any:
    """
    基于规则的细胞类型注释（降级方案）

    利用Marker基因的已知生物学知识进行简单的关键词匹配注释。
    主要针对小鼠胚胎发育数据（如E7.5期）。

    Args:
        adata: AnnData对象（需要已运行Marker基因分析）
        cluster_key: 聚类结果的列名

    Returns:
        注释后的AnnData对象
    """
    logger.info("使用基于规则的细胞类型注释（降级方案）")

    # 自动检测cluster_key（兼容leiden/louvain）
    if cluster_key not in adata.obs.columns:
        for key in ["leiden", "louvain"]:
            if key in adata.obs.columns:
                cluster_key = key
                break

    if "rank_genes_groups" not in adata.uns:
        logger.warning("未找到Marker基因结果，无法进行规则注释")
        adata.obs['cell_type'] = 'Unknown'
        adata.uns['cluster_celltype_mapping'] = {}
        return adata

    # 小鼠胚胎发育相关的细胞类型Marker基因字典（扩大覆盖范围）
    CELL_TYPE_MARKERS = {
        'Epiblast': ['Pou5f1', 'Sox2', 'Nanog', 'Klf4', 'Esrrb', 'Fgf4', 'Tfcp2l1'],
        'Primitive Endoderm': ['Gata6', 'Sox17', 'Pdgfrb', 'Col4a1', 'Lama1', 'Fn1'],
        'Visceral Endoderm': ['Afp', 'Apoa1', 'Cyp26a1', 'Hand1', 'Ttr', 'Apoa2'],
        'Ectoderm': ['Otx2', 'Pax6', 'Sox1', 'Zic1', 'Fgf5', 'Cer1'],
        'Mesoderm': ['Tbxt', 'Mixl1', 'Eomes', 'Nodal', 'Wnt3', 'Msgn1'],
        'Endoderm': ['Sox17', 'Foxa2', 'Gata4', 'Cer1', 'Sox7', 'Foxq1'],
        'Neural Crest': ['Sox10', 'Foxd3', 'Ap2a1', 'Pax3', 'Ednrb', 'Phox2b'],
        'Hemogenic Endothelium': ['Tal1', 'Lmo2', 'Runx1', 'Tek', 'Etv2', 'Ldb1'],
        'Cardiac Mesoderm': ['Nkx2-5', 'Tbx5', 'Mef2c', 'Gata4', 'Hand2', 'Isl1'],
        'Somite': ['Tbx6', 'Msgn1', 'Pax1', 'Pax3', 'Dll1', 'Mesp2'],
        'Neural': ['Nes', 'Sox1', 'Pax6', 'Hes5', 'Neurog2', 'Tubb3'],
        'Placental': ['Cdx2', 'Eomes', 'Gata3', 'Elf5', 'Cyp19a1'],
    }

    # 获取每个cluster的top marker基因
    try:
        result = adata.uns['rank_genes_groups']
        groups = result['names'].dtype.names
    except Exception as e:
        logger.error(f"解析Marker基因结果失败: {e}")
        adata.obs['cell_type'] = 'Unknown'
        adata.uns['cluster_celltype_mapping'] = {}
        return adata

    cluster_annotations = {}
    for group in groups:
        # 获取该cluster的top 30 marker基因（扩大搜索范围）
        top_genes = [str(g) for g in result['names'][group][:30].tolist()]

        # 与已知Marker基因字典匹配（不区分大小写）
        top_genes_lower = [g.lower() for g in top_genes]
        best_match = 'Unknown'
        best_score = 0

        for cell_type, markers in CELL_TYPE_MARKERS.items():
            markers_lower = [m.lower() for m in markers]
            overlap = len(set(top_genes_lower) & set(markers_lower))
            if overlap > best_score:
                best_score = overlap
                best_match = cell_type

        # 降低阈值：至少匹配1个marker即可分配类型
        if best_score < 1:
            best_match = f'Cluster_{group}'

        cluster_annotations[group] = best_match
        logger.info(f"Cluster {group}: {best_match} (匹配 {best_score} 个marker)")

    # 写入adata.obs
    adata.obs['cell_type'] = adata.obs[cluster_key].map(cluster_annotations).astype(str)
    adata.obs['cell_type'] = adata.obs['cell_type'].fillna('Unknown')
    adata.uns['cluster_celltype_mapping'] = cluster_annotations

    return adata


def annotate_cell_types(
    adata,
    method: str = "auto",
    model_name: str = "Immune_All_Low",
    cluster_key: str = "leiden",
    **kwargs,
) -> Dict[str, Any]:
    """
    细胞类型注释的统一入口

    Args:
        adata: AnnData对象
        method: 注释方法
            - "auto": 自动选择（优先CellTypist，降级为规则）
            - "celltypist": 使用CellTypist
            - "rule": 使用基于规则的注释
        model_name: CellTypist模型名称（仅method="celltypist"时使用）
        cluster_key: 聚类结果的列名
        **kwargs: 传递给具体注释方法的额外参数

    Returns:
        包含注释结果的字典
    """
    logger.info(f"开始细胞类型注释 (method={method})")

    try:
        if method == "auto":
            if _check_celltypist_available():
                logger.info("CellTypist可用，使用CellTypist注释")
                adata = annotate_cell_types_celltypist(
                    adata, model_name=model_name, cluster_key=cluster_key, **kwargs
                )
                annotation_method = "celltypist"
            else:
                logger.info("CellTypist不可用，降级为基于规则的注释")
                adata = annotate_cell_types_rule_based(adata, cluster_key=cluster_key)
                annotation_method = "rule_based"

        elif method == "celltypist":
            if not _check_celltypist_available():
                raise ImportError("CellTypist未安装，请运行: pip install celltypist")
            adata = annotate_cell_types_celltypist(
                adata, model_name=model_name, cluster_key=cluster_key, **kwargs
            )
            annotation_method = "celltypist"

        elif method == "rule":
            adata = annotate_cell_types_rule_based(adata, cluster_key=cluster_key)
            annotation_method = "rule_based"

        else:
            raise ValueError(f"不支持的注释方法: {method}")

        # 统计结果
        cell_type_counts = adata.obs['cell_type'].value_counts().to_dict()
        n_types = len(cell_type_counts)

        # 获取cluster映射
        cluster_mapping = adata.uns.get('cluster_celltype_mapping', {})

        # 生成摘要
        summary = {
            "method": annotation_method,
            "model_name": model_name if annotation_method == "celltypist" else "N/A",
            "n_cell_types": n_types,
            "cell_type_distribution": cell_type_counts,
            "cluster_mapping": cluster_mapping,
        }

        logger.info(f"细胞类型注释完成: {n_types} 种细胞类型")
        return {
            "adata": adata,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"细胞类型注释失败: {e}")
        # 降级：如果CellTypist失败，尝试规则注释
        if method != "rule":
            logger.info("尝试降级为基于规则的注释")
            try:
                adata = annotate_cell_types_rule_based(adata, cluster_key=cluster_key)
                return {
                    "adata": adata,
                    "summary": {
                        "method": "rule_based (fallback)",
                        "n_cell_types": adata.obs['cell_type'].nunique(),
                        "cell_type_distribution": adata.obs['cell_type'].value_counts().to_dict(),
                        "cluster_mapping": adata.uns.get('cluster_celltype_mapping', {}),
                    },
                }
            except Exception as e2:
                logger.error(f"规则注释也失败: {e2}")

        raise


def plot_cell_type_composition(
    adata,
    cluster_key: str = "leiden",
    cell_type_key: str = "cell_type",
    output_dir: str = "",
) -> Optional[str]:
    """
    绘制细胞类型组成图（堆叠柱状图）

    展示每个cluster中各细胞类型的占比。

    Args:
        adata: AnnData对象
        cluster_key: 聚类结果列名
        cell_type_key: 细胞类型列名
        output_dir: 输出目录

    Returns:
        图表文件路径
    """
    if cell_type_key not in adata.obs.columns:
        logger.warning(f"未找到 {cell_type_key} 列，请先运行细胞类型注释")
        return None

    try:
        import pandas as pd

        # 构建交叉表
        ct = pd.crosstab(adata.obs[cluster_key], adata.obs[cell_type_key], normalize='index')

        fig, ax = plt.subplots(figsize=(12, 6))
        ct.plot(kind='bar', stacked=True, ax=ax, colormap='tab20', edgecolor='white', linewidth=0.5)

        ax.set_xlabel('Cluster', fontsize=12)
        ax.set_ylabel('Proportion', fontsize=12)
        ax.set_title('Cell Type Composition by Cluster', fontsize=14)
        ax.legend(title='Cell Type', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

        plt.tight_layout()

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, "cell_type_composition.png")
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close(fig)
            logger.info(f"细胞类型组成图已保存: {filepath}")
            return filepath
        else:
            plt.close(fig)
            return None

    except Exception as e:
        logger.error(f"绘制细胞类型组成图失败: {e}")
        plt.close('all')
        return None


def plot_cell_type_umap(
    adata,
    cell_type_key: str = "cell_type",
    output_dir: str = "",
) -> Optional[str]:
    """
    在UMAP图上按细胞类型着色

    Args:
        adata: AnnData对象
        cell_type_key: 细胞类型列名
        output_dir: 输出目录

    Returns:
        图表文件路径
    """
    if cell_type_key not in adata.obs.columns:
        return None

    if "X_umap" not in adata.obsm:
        logger.warning("未找到UMAP嵌入，请先运行降维分析")
        return None

    try:
        import scanpy as sc

        fig, ax = plt.subplots(figsize=(10, 8))
        sc.pl.umap(adata, color=cell_type_key, ax=ax, show=False,
                    title='Cell Type Annotation (UMAP)')

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, "cell_type_umap.png")
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close(fig)
            logger.info(f"细胞类型UMAP图已保存: {filepath}")
            return filepath
        else:
            plt.close(fig)
            return None

    except Exception as e:
        logger.error(f"绘制细胞类型UMAP图失败: {e}")
        plt.close('all')
        return None


def run_cell_type_annotation(
    adata,
    method: str = "auto",
    model_name: str = "Immune_All_Low",
    cluster_key: str = "leiden",
    output_dir: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """
    编排函数：执行细胞类型注释并生成所有相关图表

    Args:
        adata: AnnData对象
        method: 注释方法
        model_name: CellTypist模型名称
        cluster_key: 聚类结果列名
        output_dir: 输出目录
        **kwargs: 额外参数

    Returns:
        包含adata、summary和plot_files的字典
    """
    logger.info("=== 开始细胞类型注释流程 ===")

    # 1. 执行注释
    result = annotate_cell_types(
        adata,
        method=method,
        model_name=model_name,
        cluster_key=cluster_key,
        **kwargs,
    )

    annotated_adata = result["adata"]
    summary = result["summary"]
    plot_files = []

    # 2. 生成图表
    if output_dir:
        # 细胞类型组成图
        comp_plot = plot_cell_type_composition(
            annotated_adata, cluster_key=cluster_key, output_dir=output_dir
        )
        if comp_plot:
            plot_files.append(comp_plot)

        # 细胞类型UMAP图
        umap_plot = plot_cell_type_umap(
            annotated_adata, output_dir=output_dir
        )
        if umap_plot:
            plot_files.append(umap_plot)

    logger.info(f"=== 细胞类型注释完成，生成 {len(plot_files)} 个图表 ===")

    return {
        "adata": annotated_adata,
        "summary": summary,
        "plot_files": plot_files,
    }
