"""
Test Script for Real Data
测试真实数据集
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.data_loader import load_h5ad, get_data_summary, validate_data
from engine.qc import run_qc_pipeline
from engine.preprocessing import run_preprocessing_pipeline
from engine.clustering import run_clustering_pipeline
from engine.spatial_viz import generate_spatial_plots
from engine.marker import run_marker_analysis


# 获取示例数据路径
_sample_data_dir = Path(__file__).parent.parent / "examples" / "sample_data"
_h5ad_files = list(_sample_data_dir.glob("*.h5ad")) if _sample_data_dir.exists() else []
_sample_file_path = str(_h5ad_files[0]) if _h5ad_files else None


@pytest.fixture(scope="module")
def file_path():
    """示例数据文件路径"""
    if _sample_file_path is None:
        pytest.skip("No .h5ad files found in examples/sample_data/")
    return _sample_file_path


@pytest.fixture(scope="module")
def adata(file_path):
    """加载示例数据"""
    return load_h5ad(file_path)


@pytest.fixture(scope="module")
def sample_name(file_path):
    """样本名称"""
    return Path(file_path).stem


def test_single_sample(file_path: str):
    """测试单个样本"""
    print(f"\n{'='*70}")
    print(f"测试文件: {Path(file_path).name}")
    print(f"{'='*70}")

    # 1. 加载数据
    print("\n[1/6] 加载数据...")
    try:
        adata = load_h5ad(file_path)
        print(f"  [OK] 成功加载: {adata.shape[0]} cells, {adata.shape[1]} genes")
    except Exception as e:
        print(f"  [FAIL] 加载失败: {e}")
        return None

    # 2. 查看数据概览
    print("\n[2/6] 数据概览...")
    summary = get_data_summary(adata)
    print(f"  [OK] 细胞数: {summary['n_cells']}")
    print(f"  [OK] 基因数: {summary['n_genes']}")
    print(f"  [OK] 有空间坐标: {summary['has_spatial']}")
    if summary['has_spatial']:
        print(f"  [OK] 空间坐标范围: {summary['spatial_bounds']}")
    print(f"  [OK] obs列: {summary['obs_columns'][:5]}...")
    print(f"  [OK] var列: {summary['var_columns'][:5]}...")

    # 3. 数据验证
    print("\n[3/6] 数据验证...")
    validation = validate_data(adata)
    if validation['is_valid']:
        print(f"  [OK] 数据验证通过")
    else:
        print(f"  [FAIL] 数据验证失败: {validation['errors']}")
        return None
    if validation['warnings']:
        print(f"  [WARN] 警告: {validation['warnings']}")

    return adata


def test_full_pipeline(adata, sample_name: str):
    """测试完整流程"""
    # 创建输出目录
    output_base = Path("storage/results") / sample_name
    output_base.mkdir(parents=True, exist_ok=True)

    # 1. 质量控制
    print("\n[4/6] 执行质量控制...")
    try:
        qc_output = output_base / "qc"
        qc_result = run_qc_pipeline(
            adata,
            params={"min_genes": 100, "min_cells": 3, "max_pct_mito": 30},
            output_dir=str(qc_output),
        )
        adata = qc_result["adata"]
        print(f"  [OK] QC完成: {qc_result['summary']['filtering_stats']['cells_after']} cells remaining")
        print(f"  [OK] 生成 {len(qc_result['plot_files'])} 个QC图表")
    except Exception as e:
        print(f"  [FAIL] QC失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 2. 数据预处理
    print("\n[5/6] 执行数据预处理...")
    try:
        preprocess_result = run_preprocessing_pipeline(
            adata,
            params={"target_sum": 1e4, "n_top_genes": 2000, "n_pcs": 50},
        )
        adata = preprocess_result["adata"]
        print(f"  [OK] 预处理完成")
        print(f"  [OK] 高变基因数: {preprocess_result['summary']['n_hvg']}")
    except Exception as e:
        print(f"  [FAIL] 预处理失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 3. 降维与聚类
    print("\n[6/6] 执行降维与聚类...")
    try:
        clustering_output = output_base / "clustering"
        clustering_result = run_clustering_pipeline(
            adata,
            params={"n_pcs": 50, "n_neighbors": 15, "method": "leiden", "resolution": 1.0},
            output_dir=str(clustering_output),
        )
        adata = clustering_result["adata"]
        print(f"  [OK] 聚类完成: {clustering_result['summary']['n_clusters']} clusters")
        print(f"  [OK] 生成 {len(clustering_result['plot_files'])} 个聚类图表")
    except Exception as e:
        print(f"  [FAIL] 聚类失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 4. 空间可视化
    print("\n[bonus] 生成空间可视化图表...")
    try:
        spatial_output = output_base / "spatial"
        spatial_plots = generate_spatial_plots(
            adata,
            str(spatial_output),
            cluster_key="leiden",
        )
        print(f"  [OK] 生成 {len(spatial_plots)} 个空间可视化图表")
    except Exception as e:
        print(f"  [WARN] 空间可视化失败: {e}")

    # 5. Marker基因分析（可选，数据量大时可能较慢）
    print("\n[bonus] 执行Marker基因分析...")
    try:
        marker_output = output_base / "marker"
        marker_result = run_marker_analysis(
            adata,
            cluster_key="leiden",
            method="wilcoxon",
            n_markers=10,
            output_dir=str(marker_output),
        )
        print(f"  [OK] Marker分析完成")
        print(f"  [OK] 生成 {len(marker_result['plot_files'])} 个Marker图表")
    except Exception as e:
        print(f"  [WARN] Marker分析失败: {e}")

    # 保存最终数据
    from engine.data_loader import save_adata
    final_data_path = output_base / "final_data.h5ad"
    save_adata(adata, str(final_data_path))
    print(f"\n  [OK] 最终数据已保存到: {final_data_path}")

    return adata


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("空间转录组分析引擎 - 真实数据测试")
    print("="*70)

    # 获取所有h5ad文件
    data_dir = Path("examples/sample_data")
    h5ad_files = list(data_dir.glob("*.h5ad"))

    if not h5ad_files:
        print("\n未找到.h5ad文件，请将数据放到 examples/sample_data/ 目录下")
        return 1

    print(f"\n找到 {len(h5ad_files)} 个数据文件:")
    for f in h5ad_files:
        print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")

    # 选择第一个文件进行测试（避免内存问题）
    test_file = h5ad_files[0]
    sample_name = test_file.stem

    print(f"\n将测试第一个文件: {test_file.name}")

    # 测试加载数据
    adata = test_single_sample(str(test_file))

    if adata is None:
        print("\n数据加载失败，测试终止")
        return 1

    # 测试完整流程
    result = test_full_pipeline(adata, sample_name)

    if result is None:
        print("\n流程测试失败")
        return 1

    # 统计结果
    print("\n" + "="*70)
    print("[OK] 测试完成！")
    print("="*70)

    output_base = Path("storage/results") / sample_name
    all_plots = list(output_base.rglob("*.png"))
    print(f"\n共生成 {len(all_plots)} 个图表文件:")
    for plot in sorted(all_plots)[:10]:  # 只显示前10个
        print(f"  - {plot}")
    if len(all_plots) > 10:
        print(f"  ... 还有 {len(all_plots) - 10} 个文件")

    print(f"\n所有结果已保存到: {output_base}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
