"""
下载示例数据脚本

从GEO数据库下载Stereo-seq空间转录组数据。
"""

import os
import subprocess
import sys


# 示例数据信息
SAMPLE_DATA = {
    "GSM9046243_Embryo_E7.5_stereo_rep1.h5ad": {
        "size": "195MB",
        "description": "小鼠E7.5期胚胎 Stereo-seq数据"
    },
    "GSM9046244_Embryo_E7.5_stereo_rep2.h5ad": {
        "size": "31MB",
        "description": "小鼠E7.5期胚胎 Stereo-seq数据 (重复2)"
    },
    "GSM9046245_Embryo_E7.75_stereo_rep1.h5ad": {
        "size": "344MB",
        "description": "小鼠E7.75期胚胎 Stereo-seq数据"
    },
    "GSM9046246_Embryo_E7.75_stereo_rep2.h5ad": {
        "size": "93MB",
        "description": "小鼠E7.75期胚胎 Stereo-seq数据 (重复2)"
    },
    "GSM9046247_Embryo_E8.0_stereo_rep1.h5ad": {
        "size": "36MB",
        "description": "小鼠E8.0期胚胎 Stereo-seq数据"
    },
    "GSM9046248_Embryo_E8.0_stereo_rep2.h5ad": {
        "size": "103MB",
        "description": "小鼠E8.0期胚胎 Stereo-seq数据 (重复2)"
    }
}


def download_file(url: str, output_path: str) -> bool:
    """下载文件"""
    try:
        print(f"正在下载: {os.path.basename(output_path)}")

        # 尝试使用wget
        try:
            subprocess.run(["wget", "-O", output_path, url], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # 尝试使用curl
        try:
            subprocess.run(["curl", "-L", "-o", output_path, url], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # 使用Python的urllib
        import urllib.request
        urllib.request.urlretrieve(url, output_path)
        return True

    except Exception as e:
        print(f"下载失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("空间转录组示例数据下载工具")
    print("=" * 60)
    print()

    # 创建数据目录
    data_dir = os.path.join(os.path.dirname(__file__), "sample_data")
    os.makedirs(data_dir, exist_ok=True)

    print("数据来源: GSE278603")
    print("DOI: https://doi.org/10.1016/j.cell.2025.05.035")
    print()

    # 显示可用数据
    print("可用的示例数据:")
    print("-" * 60)
    for i, (filename, info) in enumerate(SAMPLE_DATA.items(), 1):
        exists = os.path.exists(os.path.join(data_dir, filename))
        status = "✅ 已存在" if exists else "❌ 未下载"
        print(f"{i}. {filename}")
        print(f"   大小: {info['size']} | {info['description']}")
        print(f"   状态: {status}")
        print()

    # 选择下载
    print("请选择操作:")
    print("1. 下载所有数据 (约800MB)")
    print("2. 选择下载单个文件")
    print("3. 退出")

    choice = input("\n请输入选项 (1-3): ").strip()

    if choice == "1":
        print("\n开始下载所有数据...")
        # 这里需要实际的下载链接，GEO数据需要从NCBI网站获取
        print("\n⚠️  请手动从以下地址下载数据:")
        print("https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE278603")
        print(f"\n下载后将文件放入: {data_dir}")

    elif choice == "2":
        files = list(SAMPLE_DATA.keys())
        print("\n可选文件:")
        for i, f in enumerate(files, 1):
            print(f"{i}. {f}")

        try:
            file_idx = int(input("\n请输入文件编号: ")) - 1
            if 0 <= file_idx < len(files):
                filename = files[file_idx]
                print(f"\n⚠️  请手动下载 {filename}")
                print(f"下载地址: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE278603")
                print(f"下载后放入: {data_dir}")
            else:
                print("无效的编号")
        except ValueError:
            print("无效的输入")

    print("\n" + "=" * 60)
    print("下载完成后，可以在Streamlit界面中选择文件进行分析")
    print("=" * 60)


if __name__ == "__main__":
    main()
