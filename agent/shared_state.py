"""
共享状态模块

管理Agent工具之间的共享数据（AnnData对象等）。
使用threading.local()实现线程安全，支持多用户并发。
"""

import threading
from typing import Any, Optional


class SharedState:
    """线程安全的全局共享状态，每个线程维护独立的adata引用"""

    def __init__(self):
        self._local = threading.local()

    @property
    def adata(self) -> Optional[Any]:
        return getattr(self._local, 'adata', None)

    @adata.setter
    def adata(self, value: Any):
        self._local.adata = value

    @property
    def file_path(self) -> Optional[str]:
        return getattr(self._local, 'file_path', None)

    @file_path.setter
    def file_path(self, value: str):
        self._local.file_path = value


# 全局单例（线程安全）
_shared_state = SharedState()


def get_shared_state() -> SharedState:
    """获取全局共享状态"""
    return _shared_state


def get_adata() -> Optional[Any]:
    """获取当前线程的AnnData对象"""
    return _shared_state.adata


def set_adata(adata: Any) -> None:
    """设置当前线程的AnnData对象"""
    _shared_state.adata = adata


def get_file_path() -> Optional[str]:
    """获取当前线程的文件路径"""
    return _shared_state.file_path


def set_file_path(file_path: str) -> None:
    """设置当前线程的文件路径"""
    _shared_state.file_path = file_path
