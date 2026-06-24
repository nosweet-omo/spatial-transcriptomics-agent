"""
Bioinformatics Engine Module
空间转录组分析计算引擎
"""

from .utils import validate_output_dir, get_file_size_str
from .data_loader import load_h5ad, get_data_summary, validate_data
from .qc import (
    calculate_qc_metrics,
    filter_cells,
    filter_mito,
    generate_qc_plots,
    run_qc_pipeline,
)
from .preprocessing import (
    normalize_data,
    log_transform,
    select_hvg,
    standardize_data,
    run_preprocessing_pipeline,
    generate_preprocessing_plots,
)
from .clustering import (
    run_pca,
    run_umap,
    run_clustering,
    suggest_cluster_annotation,
    generate_clustering_plots,
)
from .spatial_viz import (
    plot_spatial_distribution,
    plot_cluster_spatial,
    plot_gene_spatial,
    plot_embedding,
)
from .marker import (
    find_marker_genes,
    plot_marker_heatmap,
    plot_marker_dotplot,
    get_top_markers,
)
from .cell_type import (
    annotate_cell_types,
    annotate_cell_types_celltypist,
    annotate_cell_types_rule_based,
    plot_cell_type_composition,
    plot_cell_type_umap,
    run_cell_type_annotation,
)

__all__ = [
    # Utils
    "validate_output_dir",
    "get_file_size_str",
    # Data Loader
    "load_h5ad",
    "get_data_summary",
    "validate_data",
    # QC
    "calculate_qc_metrics",
    "filter_cells",
    "filter_mito",
    "generate_qc_plots",
    "run_qc_pipeline",
    # Preprocessing
    "normalize_data",
    "log_transform",
    "select_hvg",
    "standardize_data",
    "run_preprocessing_pipeline",
    # Clustering
    "run_pca",
    "run_umap",
    "run_clustering",
    "suggest_cluster_annotation",
    "generate_clustering_plots",
    # Spatial Visualization
    "plot_spatial_distribution",
    "plot_cluster_spatial",
    "plot_gene_spatial",
    "plot_embedding",
    # Marker Analysis
    "find_marker_genes",
    "plot_marker_heatmap",
    "plot_marker_dotplot",
    "get_top_markers",
    # Cell Type Annotation
    "annotate_cell_types",
    "annotate_cell_types_celltypist",
    "annotate_cell_types_rule_based",
    "plot_cell_type_composition",
    "plot_cell_type_umap",
    "run_cell_type_annotation",
]
