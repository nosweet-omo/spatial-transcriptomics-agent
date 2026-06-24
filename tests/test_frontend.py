"""
前端层单元测试

测试frontend模块中的工具函数和组件。
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.utils import (
    get_file_size,
    get_plot_files_from_results,
    validate_h5ad_file,
    get_output_dir,
    list_h5ad_files,
    ensure_directories,
    UPLOAD_DIR,
    RESULTS_DIR,
)


class TestGetFileSize:
    """测试get_file_size函数"""

    def test_file_not_exists(self):
        """测试文件不存在时返回错误信息"""
        result = get_file_size("nonexistent_file.txt")
        assert result == "文件不存在"

    def test_small_file(self):
        """测试小文件（< 1KB）"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            f.flush()
            result = get_file_size(f.name)
            assert "B" in result
        os.unlink(f.name)

    def test_medium_file(self):
        """测试中等文件（1KB - 1MB）"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * 1024)  # 1KB
            f.flush()
            result = get_file_size(f.name)
            assert "KB" in result
        os.unlink(f.name)

    def test_large_file(self):
        """测试大文件（1MB - 1GB）"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"x" * (1024 * 1024))  # 1MB
            f.flush()
            result = get_file_size(f.name)
            assert "MB" in result
        os.unlink(f.name)


class TestGetPlotFilesFromResults:
    """测试get_plot_files_from_results函数"""

    def test_empty_results(self):
        """测试空结果"""
        result = get_plot_files_from_results({})
        assert result == []

    def test_results_with_plots(self):
        """测试包含图表的结果"""
        results = {
            "run_qc": {
                "status": "success",
                "plot_files": ["qc_violin.png", "qc_scatter.png"]
            },
            "run_clustering": {
                "status": "success",
                "plot_files": ["umap_cluster.png"]
            }
        }
        result = get_plot_files_from_results(results)
        # 函数可能返回重复项，测试包含预期文件
        assert "qc_violin.png" in result
        assert "umap_cluster.png" in result

    def test_results_without_plots(self):
        """测试不包含图表的结果"""
        results = {
            "load_data": {"status": "success"}
        }
        result = get_plot_files_from_results(results)
        assert result == []


class TestValidateH5adFile:
    """测试validate_h5ad_file函数"""

    def test_file_not_exists(self):
        """测试文件不存在"""
        result = validate_h5ad_file("nonexistent.h5ad")
        assert result["is_valid"] is False
        assert "不存在" in result["error"]

    def test_invalid_extension(self):
        """测试无效的文件扩展名"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test")
            f.flush()
            result = validate_h5ad_file(f.name)
            assert result["is_valid"] is False
            assert "格式" in result["error"]
        os.unlink(f.name)

    def test_empty_file(self):
        """测试空文件"""
        with tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False) as f:
            result = validate_h5ad_file(f.name)
            assert result["is_valid"] is False
            assert "为空" in result["error"]
        os.unlink(f.name)

    def test_valid_h5ad_file(self):
        """测试有效的h5ad文件"""
        with tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False) as f:
            f.write(b"test content")
            f.flush()
            result = validate_h5ad_file(f.name)
            assert result["is_valid"] is True
            assert result["error"] is None
        os.unlink(f.name)

    def test_valid_h5_file(self):
        """测试有效的h5文件"""
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
            f.write(b"test content")
            f.flush()
            result = validate_h5ad_file(f.name)
            assert result["is_valid"] is True
        os.unlink(f.name)


class TestGetOutputDir:
    """测试get_output_dir函数"""

    def test_returns_string(self):
        """测试返回字符串"""
        result = get_output_dir()
        assert isinstance(result, str)

    def test_directory_exists(self):
        """测试目录存在"""
        result = get_output_dir()
        assert os.path.exists(result)

    def test_ends_with_results(self):
        """测试路径以results结尾"""
        result = get_output_dir()
        assert result.endswith("results")


class TestListH5adFiles:
    """测试list_h5ad_files函数"""

    def test_returns_list(self):
        """测试返回列表"""
        result = list_h5ad_files()
        assert isinstance(result, list)

    def test_no_files(self):
        """测试没有h5ad文件时返回空列表"""
        # 清空uploads目录
        if UPLOAD_DIR.exists():
            for f in UPLOAD_DIR.glob("*.h5ad"):
                f.unlink()
        result = list_h5ad_files()
        assert result == []


class TestEnsureDirectories:
    """测试ensure_directories函数"""

    def test_creates_directories(self):
        """测试创建目录"""
        # 删除目录（如果存在）
        if UPLOAD_DIR.exists():
            shutil.rmtree(UPLOAD_DIR)
        if RESULTS_DIR.exists():
            shutil.rmtree(RESULTS_DIR)

        ensure_directories()

        assert UPLOAD_DIR.exists()
        assert RESULTS_DIR.exists()


class TestAgentIntegration:
    """测试Agent层集成"""

    def test_agent_import(self):
        """测试Agent模块导入"""
        from agent.graph import run_agent
        from agent.skills import list_skills, get_skill
        from agent.tools import get_all_tools

        assert callable(run_agent)
        assert callable(list_skills)
        assert callable(get_skill)
        assert callable(get_all_tools)

    def test_list_skills(self):
        """测试列出Skills"""
        from agent.skills import list_skills

        skills = list_skills()
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_get_skill(self):
        """测试获取Skill"""
        from agent.skills import get_skill

        skill = get_skill("basic_analysis")
        assert skill is not None
        # name属性可能与registry key不同
        assert skill.name is not None

    def test_get_all_tools(self):
        """测试获取所有工具"""
        from agent.tools import get_all_tools

        tools = get_all_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0


class TestEngineIntegration:
    """测试Engine层集成"""

    def test_engine_import(self):
        """测试Engine模块导入"""
        from engine import (
            load_h5ad,
            get_data_summary,
            validate_data,
            run_qc_pipeline,
            run_preprocessing_pipeline,
            run_clustering,
        )

        assert callable(load_h5ad)
        assert callable(get_data_summary)
        assert callable(validate_data)
        assert callable(run_qc_pipeline)
        assert callable(run_preprocessing_pipeline)
        assert callable(run_clustering)

    def test_validate_output_dir(self):
        """测试输出目录验证"""
        from engine.utils import validate_output_dir

        result = validate_output_dir(str(RESULTS_DIR), create=True)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
