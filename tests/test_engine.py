"""
Test Script for Bioinformatics Engine
测试生信工具库
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.data_loader import create_sample_data, get_data_summary, validate_data, save_adata
from engine.qc import run_qc_pipeline
from engine.preprocessing import run_preprocessing_pipeline
from engine.clustering import run_clustering_pipeline
from engine.spatial_viz import generate_spatial_plots
from engine.marker import run_marker_analysis


@pytest.fixture(scope="module")
def adata():
    """创建测试用的AnnData对象（所有测试共享）"""
    return create_sample_data()


def test_data_loader():
    """测试数据读取模块"""
    print("=" * 60)
    print("测试数据读取模块")
    print("=" * 60)

    # 创建示例数据
    adata = create_sample_data()
    print(f"✓ 创建示例数据: {adata.shape[0]} cells, {adata.shape[1]} genes")

    # 获取数据概览
    summary = get_data_summary(adata)
    print(f"✓ 数据概览:")
    print(f"  - 细胞数: {summary['n_cells']}")
    print(f"  - 基因数: {summary['n_genes']}")
    print(f"  - 有空间坐标: {summary['has_spatial']}")

    # 数据验证
    validation = validate_data(adata)
    print(f"✓ 数据验证: {'通过' if validation['is_valid'] else '失败'}")
    if validation["warnings"]:
        print(f"  - 警告: {validation['warnings']}")

    # 保存数据
    output_dir = Path("storage/cache")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_adata(adata, str(output_dir / "test_data.h5ad"))
    print(f"✓ 数据已保存到: {output_dir / 'test_data.h5ad'}")

    return adata


def test_qc(adata):
    """测试质量控制模块"""
    print("\n" + "=" * 60)
    print("测试质量控制模块")
    print("=" * 60)

    output_dir = "storage/results/qc"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 运行QC流程
    result = run_qc_pipeline(
        adata,
        params={"min_genes": 100, "min_cells": 3, "max_pct_mito": 30},
        output_dir=output_dir,
    )

    print(f"✓ QC流程完成")
    print(f"  - 过滤前: {result['summary']['filtering_stats']['cells_before']} cells")
    print(f"  - 过滤后: {result['summary']['filtering_stats']['cells_after']} cells")
    print(f"  - 生成图表: {len(result['plot_files'])} 个")

    return result["adata"]


def test_preprocessing(adata):
    """测试预处理模块"""
    print("\n" + "=" * 60)
    print("测试预处理模块")
    print("=" * 60)

    # 运行预处理流程
    result = run_preprocessing_pipeline(
        adata,
        params={"target_sum": 1e4, "n_top_genes": 500, "n_pcs": 30},
    )

    print(f"✓ 预处理流程完成")
    print(f"  - 原始形状: {result['summary']['original_shape']}")
    print(f"  - 最终形状: {result['summary']['final_shape']}")
    print(f"  - 高变基因数: {result['summary']['n_hvg']}")
    print(f"  - 处理步骤: {result['summary']['steps']}")

    return result["adata"]


def test_clustering(adata):
    """测试降维聚类模块"""
    print("\n" + "=" * 60)
    print("测试降维聚类模块")
    print("=" * 60)

    output_dir = "storage/results/clustering"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 运行降维聚类流程
    result = run_clustering_pipeline(
        adata,
        params={"n_pcs": 30, "n_neighbors": 10, "method": "leiden", "resolution": 0.8},
        output_dir=output_dir,
    )

    print(f"✓ 降维聚类流程完成")
    print(f"  - 聚类方法: {result['summary']['clustering_method']}")
    print(f"  - 聚类数量: {result['summary']['n_clusters']}")
    print(f"  - Cluster大小: {result['summary']['cluster_sizes']}")
    print(f"  - 生成图表: {len(result['plot_files'])} 个")

    return result["adata"]


def test_spatial_viz(adata):
    """测试空间可视化模块"""
    print("\n" + "=" * 60)
    print("测试空间可视化模块")
    print("=" * 60)

    output_dir = "storage/results/spatial"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 生成空间可视化图表
    plot_files = generate_spatial_plots(
        adata,
        output_dir,
        cluster_key="leiden",
        genes=["gene_0", "gene_1", "gene_2"],
    )

    print(f"✓ 空间可视化完成")
    print(f"  - 生成图表: {len(plot_files)} 个")

    return plot_files


def test_marker_analysis(adata):
    """测试Marker基因分析模块"""
    print("\n" + "=" * 60)
    print("测试Marker基因分析模块")
    print("=" * 60)

    output_dir = "storage/results/marker"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 运行Marker基因分析
    result = run_marker_analysis(
        adata,
        cluster_key="leiden",
        method="wilcoxon",
        n_markers=10,
        output_dir=output_dir,
    )

    print(f"✓ Marker基因分析完成")
    print(f"  - 聚类数量: {result['summary']['n_clusters']}")
    print(f"  - Top markers示例:")
    for cluster, markers in list(result["top_markers"].items())[:2]:
        print(f"    Cluster {cluster}: {markers[:5]}...")
    print(f"  - 生成图表: {len(result['plot_files'])} 个")

    return result


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("空间转录组分析引擎 - 功能测试")
    print("=" * 60 + "\n")

    try:
        # 1. 测试数据读取
        adata = test_data_loader()

        # 2. 测试质量控制
        adata = test_qc(adata)

        # 3. 测试预处理
        adata = test_preprocessing(adata)

        # 4. 测试降维聚类
        adata = test_clustering(adata)

        # 5. 测试空间可视化
        spatial_plots = test_spatial_viz(adata)

        # 6. 测试Marker基因分析
        marker_result = test_marker_analysis(adata)

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

        # 统计生成的所有图表
        all_plots = []
        for dir_path in ["storage/results/qc", "storage/results/clustering", "storage/results/spatial", "storage/results/marker"]:
            if Path(dir_path).exists():
                all_plots.extend(list(Path(dir_path).glob("*.png")))

        print(f"\n共生成 {len(all_plots)} 个图表文件:")
        for plot in all_plots:
            print(f"  - {plot}")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
