"""
前端工具函数模块

提供文件处理、路径转换等辅助功能。
"""

import os
import shutil
from typing import Optional, List, Dict, Any
from pathlib import Path


# ============ 路径常量 ============

PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_DIR = PROJECT_ROOT / "storage" / "uploads"
RESULTS_DIR = PROJECT_ROOT / "storage" / "results"


def ensure_directories():
    """确保必要的目录存在"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============ 文件处理函数 ============

def save_uploaded_file(uploaded_file, filename: Optional[str] = None) -> str:
    """
    保存上传的文件

    Args:
        uploaded_file: Streamlit上传的文件对象
        filename: 自定义文件名（可选）

    Returns:
        保存后的文件路径
    """
    ensure_directories()

    if filename is None:
        filename = uploaded_file.name

    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(file_path)


def get_file_size(file_path: str) -> str:
    """
    获取文件大小（格式化为可读字符串）

    Args:
        file_path: 文件路径

    Returns:
        格式化的文件大小字符串
    """
    if not os.path.exists(file_path):
        return "文件不存在"

    size_bytes = os.path.getsize(file_path)

    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_plot_files_from_results(results: Dict[str, Any]) -> List[str]:
    """
    从分析结果中提取图表文件路径

    Args:
        results: AgentState中的results字典

    Returns:
        图表文件路径列表
    """
    plot_files = []

    for step_name, step_result in results.items():
        if isinstance(step_result, dict):
            # 从QC步骤提取
            if "plot_files" in step_result:
                plot_files.extend(step_result["plot_files"])

            # 从聚类步骤提取
            if "plot_files" in step_result:
                plot_files.extend(step_result["plot_files"])

    return plot_files


def validate_h5ad_file(file_path: str) -> Dict[str, Any]:
    """
    验证h5ad文件

    Args:
        file_path: 文件路径

    Returns:
        验证结果字典
    """
    result = {
        "is_valid": False,
        "error": None,
        "file_path": file_path
    }

    if not os.path.exists(file_path):
        result["error"] = "文件不存在"
        return result

    if not file_path.endswith((".h5ad", ".h5")):
        result["error"] = "文件格式不支持，请上传.h5ad或.h5格式文件"
        return result

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        result["error"] = "文件为空"
        return result

    result["is_valid"] = True
    return result


def get_output_dir() -> str:
    """
    获取输出目录路径

    Returns:
        输出目录的绝对路径
    """
    ensure_directories()
    return str(RESULTS_DIR)


def list_h5ad_files() -> List[str]:
    """
    列出uploads目录中的所有h5ad文件

    Returns:
        h5ad文件路径列表
    """
    ensure_directories()

    h5ad_files = []
    for file in UPLOAD_DIR.iterdir():
        if file.is_file() and file.suffix in [".h5ad", ".h5"]:
            h5ad_files.append(str(file))

    return h5ad_files
