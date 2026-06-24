"""
Engine Utility Functions
引擎层工具函数
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def validate_output_dir(output_dir: str, create: bool = True) -> bool:
    """
    验证输出目录是否可写

    Args:
        output_dir: 输出目录路径
        create: 如果目录不存在是否创建

    Returns:
        目录是否可用
    """
    if not output_dir:
        logger.warning("未指定输出目录")
        return False

    try:
        path = Path(output_dir)

        # 如果目录不存在，尝试创建
        if not path.exists():
            if create:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"创建输出目录: {output_dir}")
            else:
                logger.error(f"输出目录不存在: {output_dir}")
                return False

        # 检查是否可写
        test_file = path / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
            return True
        except PermissionError:
            logger.error(f"输出目录不可写: {output_dir}")
            return False

    except Exception as e:
        logger.error(f"验证输出目录失败: {e}")
        return False


def get_file_size_str(size_bytes: int) -> str:
    """
    将字节大小转换为可读字符串

    Args:
        size_bytes: 字节数

    Returns:
        格式化的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"
