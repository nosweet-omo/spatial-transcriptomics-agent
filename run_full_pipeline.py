"""
完整分析流程
从数据读取到Marker基因分析的完整流程
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from engine.data_loader import load_h5ad, get_data_summary
from engine.qc import run_qc_pipeline
from engine.preprocessing import run_preprocessing_pipeline
from engine.clustering import run_clustering_pipeline
from engine.spatial_viz import generate_spatial_plots, select_highly_expressed_genes
from engine.marker import run_marker_analysis


def main():
    """主函数"""
    # 数据路径
    data_path = "examples/sample_data/GSM9046243_Embryo_E7.5_stereo_rep1.h5ad"
    output_base = Path("storage/results/GSM9046243_Embryo_E7.5_stereo_rep1")

    print("=" * 70)
    print("空间转录组分析 - 完整流程")
    print("=" * 70)
    print(f"数据: {data_path}")
    print(f"输出: {output_base}")
    print()

    # ============================================
    # 步骤1: 数据读取与概览
    # ============================================
    print("[1/7] 数据读取与概览")
    print("-" * 40)

    adata = load_h5ad(data_path)
    summary = get_data_summary(adata)

    print(f"  细胞数: {summary['n_cells']}")
    print(f"  基因数: {summary['n_genes']}")
    print(f"  空间坐标: {summary['has_spatial']}")
    if summary['has_spatial']:
        print(f"  坐标键名: {summary['spatial_key']}")
        print(f"  X范围: {summary['spatial_bounds']['x_min']:.2f} - {summary['spatial_bounds']['x_max']:.2f}")
        print(f"  Y范围: {summary['spatial_bounds']['y_min']:.2f} - {summary['spatial_bounds']['y_max']:.2f}")
    print()

    # ============================================
    # 步骤2: 质量控制 (QC)
    # ============================================
    print("[2/7] 质量控制 (QC)")
    print("-" * 40)

    qc_output = output_base / "qc"
    qc_output.mkdir(parents=True, exist_ok=True)

    qc_result = run_qc_pipeline(
        adata,
        params={
            'min_genes': 200,
            'min_cells': 3,
            'max_pct_mito': 20.0,
        },
        output_dir=str(qc_output),
    )

    adata = qc_result['adata']
    qc_summary = qc_result['summary']

    print(f"  过滤前: {qc_summary['filtering_stats']['cells_before']} cells, {qc_summary['filtering_stats']['genes_before']} genes")
    print(f"  过滤后: {qc_summary['filtering_stats']['cells_after']} cells, {qc_summary['filtering_stats']['genes_after']} genes")
    print(f"  移除: {qc_summary['filtering_stats']['cells_removed']} cells, {qc_summary['filtering_stats']['genes_removed']} genes")
    print(f"  生成图表: {len(qc_result['plot_files'])} 个")
    print()

    # ============================================
    # 步骤3: 基础预处理
    # ============================================
    print("[3/7] 基础预处理")
    print("-" * 40)

    preprocess_result = run_preprocessing_pipeline(
        adata,
        params={
            'target_sum': 1e4,
            'n_top_genes': 2000,
            'n_pcs': 50,
        },
    )

    adata = preprocess_result['adata']
    preprocess_summary = preprocess_result['summary']

    print(f"  高变基因: {preprocess_summary['n_hvg']}")
    print(f"  PCA主成分: {preprocess_summary['n_pcs']}")
    print(f"  处理步骤: {len(preprocess_summary['steps'])} 个")
    print()

    # ============================================
    # 步骤4: 降维与聚类
    # ============================================
    print("[4/7] 降维与聚类")
    print("-" * 40)

    clustering_output = output_base / "clustering"
    clustering_output.mkdir(parents=True, exist_ok=True)

    clustering_result = run_clustering_pipeline(
        adata,
        params={
            'n_pcs': 50,
            'n_neighbors': 15,
            'method': 'leiden',
            'resolution': 1.0,
        },
        output_dir=str(clustering_output),
    )

    adata = clustering_result['adata']
    clustering_summary = clustering_result['summary']

    print(f"  聚类方法: {clustering_summary['clustering_method']}")
    print(f"  聚类数量: {clustering_summary['n_clusters']}")
    print(f"  Cluster大小: {clustering_summary['cluster_sizes']}")
    print(f"  生成图表: {len(clustering_result['plot_files'])} 个")
    print()

    # ============================================
    # 步骤5: 空间可视化
    # ============================================
    print("[5/7] 空间可视化")
    print("-" * 40)

    spatial_output = output_base / "spatial"
    spatial_output.mkdir(parents=True, exist_ok=True)

    # 选择高表达基因进行可视化
    high_genes = select_highly_expressed_genes(adata, n_genes=5)
    print(f"  选择的基因: {high_genes}")

    # 生成3D空间可视化
    spatial_plots = generate_spatial_plots(
        adata,
        str(spatial_output),
        cluster_key='leiden',
        genes=high_genes,
        use_3d=True,
    )

    print(f"  生成图表: {len(spatial_plots)} 个")
    print()

    # ============================================
    # 步骤6: Marker基因分析
    # ============================================
    print("[6/7] Marker基因分析")
    print("-" * 40)

    marker_output = output_base / "marker"
    marker_output.mkdir(parents=True, exist_ok=True)

    marker_result = run_marker_analysis(
        adata,
        cluster_key='leiden',
        method='wilcoxon',
        n_markers=10,
        output_dir=str(marker_output),
        plot_type='dotplot',
    )

    print(f"  聚类数量: {marker_result['summary']['n_clusters']}")
    print(f"  Top markers (示例):")
    for cluster, markers in list(marker_result['top_markers'].items())[:3]:
        print(f"    Cluster {cluster}: {markers[:5]}")
    print(f"  生成图表: {len(marker_result['plot_files'])} 个")
    print()

    # ============================================
    # 步骤7: 保存最终结果
    # ============================================
    print("[7/7] 保存最终结果")
    print("-" * 40)

    from engine.data_loader import save_adata

    final_data_path = output_base / "final_data.h5ad"
    save_adata(adata, str(final_data_path))

    # 统计所有生成的图表
    all_plots = list(output_base.rglob("*.png"))

    print(f"  最终数据: {final_data_path}")
    print(f"  总图表数: {len(all_plots)} 个")
    print()

    # ============================================
    # 完成总结
    # ============================================
    print("=" * 70)
    print("分析完成！")
    print("=" * 70)
    print()
    print("生成的文件:")
    for plot in sorted(all_plots):
        print(f"  - {plot}")
    print()
    print("目录结构:")
    print(f"  {output_base}/")
    print(f"    ├── qc/           # QC图表")
    print(f"    ├── clustering/   # 聚类图表")
    print(f"    ├── spatial/      # 空间可视化图表")
    print(f"    ├── marker/       # Marker基因图表")
    print(f"    └── final_data.h5ad  # 最终数据")


if __name__ == "__main__":
    main()
