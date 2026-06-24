"""
前端模块

空间转录组智能分析平台的Streamlit前端交互层。
"""

from frontend.utils import (
    save_uploaded_file,
    get_file_size,
    validate_h5ad_file,
    list_h5ad_files,
    get_output_dir,
)

from frontend.components import (
    render_page_header,
    render_file_uploader,
    render_analysis_params,
    render_skill_selector,
    render_natural_language_input,
    render_chat_history,
    render_plot_gallery,
    render_analysis_summary,
    render_data_overview,
    render_download_button,
)

__all__ = [
    # 工具函数
    "save_uploaded_file",
    "get_file_size",
    "validate_h5ad_file",
    "list_h5ad_files",
    "get_output_dir",
    # UI组件
    "render_page_header",
    "render_file_uploader",
    "render_analysis_params",
    "render_skill_selector",
    "render_natural_language_input",
    "render_chat_history",
    "render_plot_gallery",
    "render_analysis_summary",
    "render_data_overview",
    "render_download_button",
]
