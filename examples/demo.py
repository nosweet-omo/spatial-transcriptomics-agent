"""
Demo Script
示例脚本：演示如何使用生信计算引擎
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.data_loader import create_sample_data, save_adata, load_h5ad, get_data_summary
from engine.qc import run_qc_pipeline
from engine.preprocessing import run_preprocessing_pipeline
from engine.clustering import run_clustering_pipeline
from engine.spatial_viz import generate_spatial_plots
from engine.marker import run_marker_analysis


def main():
    """主演示函数"""
    print("=" * 70)
    print("空间转录组分析引擎 - 演示脚本")
    print("=" * 70)

    # 创建输出目录
    output_base = Path("storage/results/demo")
    output_base.mkdir(parents=True, exist_ok=True)

    # 1. 创建或加载数据
    print("\n[1/6] 准备数据...")
    adata = create_sample_data()
    print(f"  ✓ 创建示例数据: {adata.shape[0]} cells, {adata.shape[1]} genes")

    # 保存原始数据
    data_path = output_base / "raw_data.h5ad"
    save_adata(adata, str(data_path))
    print(f"  ✓ 原始数据已保存到: {data_path}")

    # 2. 质量控制
    print("\n[2/6] 执行质量控制...")
    qc_output = output_base / "qc"
    qc_result = run_qc_pipeline(
        adata,
        params={"min_genes": 100, "min_cells": 3, "max_pct_mito": 30},
        output_dir=str(qc_output),
    )
    adata = qc_result["adata"]
    print(f"  ✓ QC完成: {qc_result['summary']['filtering_stats']['cells_after']} cells remaining")
    print(f"  ✓ 生成 {len(qc_result['plot_files'])} 个QC图表")

    # 3. 数据预处理
    print("\n[3/6] 执行数据预处理...")
    preprocess_result = run_preprocessing_pipeline(
        adata,
        params={"target_sum": 1e4, "n_top_genes": 500, "n_pcs": 30},
    )
    adata = preprocess_result["adata"]
    print(f"  ✓ 预处理完成")
    print(f"  ✓ 高变基因数: {preprocess_result['summary']['n_hvg']}")

    # 4. 降维与聚类
    print("\n[4/6] 执行降维与聚类...")
    clustering_output = output_base / "clustering"
    clustering_result = run_clustering_pipeline(
        adata,
        params={"n_pcs": 30, "n_neighbors": 10, "method": "leiden", "resolution": 0.8},
        output_dir=str(clustering_output),
    )
    adata = clustering_result["adata"]
    print(f"  ✓ 聚类完成: {clustering_result['summary']['n_clusters']} clusters")
    print(f"  ✓ 生成 {len(clustering_result['plot_files'])} 个聚类图表")

    # 5. 空间可视化
    print("\n[5/6] 生成空间可视化图表...")
    spatial_output = output_base / "spatial"
    spatial_plots = generate_spatial_plots(
        adata,
        str(spatial_output),
        cluster_key="leiden",
        genes=["gene_0", "gene_1", "gene_2"],
    )
    print(f"  ✓ 生成 {len(spatial_plots)} 个空间可视化图表")

    # 6. Marker基因分析
    print("\n[6/6] 执行Marker基因分析...")
    marker_output = output_base / "marker"
    marker_result = run_marker_analysis(
        adata,
        cluster_key="leiden",
        method="wilcoxon",
        n_markers=10,
        output_dir=str(marker_output),
    )
    print(f"  ✓ Marker分析完成")
    print(f"  ✓ 生成 {len(marker_result['plot_files'])} 个Marker图表")

    # 保存最终数据
    final_data_path = output_base / "final_data.h5ad"
    save_adata(adata, str(final_data_path))
    print(f"\n  ✓ 最终数据已保存到: {final_data_path}")

    # 统计结果
    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)

    all_plots = list(output_base.rglob("*.png"))
    print(f"\n总共生成 {len(all_plots)} 个图表文件:")
    for plot in sorted(all_plots):
        print(f"  - {plot}")

    print(f"\n所有结果已保存到: {output_base}")


if __name__ == "__main__":
    main()
