"""
空间转录组智能分析平台 - 主入口

选择进入Agent智能前端或手动操作前端。
"""

import sys
import os
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="空间转录组智能分析平台",
    page_icon="🧬",
    layout="wide"
)

st.title("🧬 空间转录组智能分析平台")
st.markdown("---")

# 初始化会话状态
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

# 如果已选择模式，直接运行对应版本
if st.session_state.app_mode == "agent":
    from frontend.app import main
    main()
    st.stop()
elif st.session_state.app_mode == "simple":
    from frontend.simple_app import main
    main()
    st.stop()

# 选择界面
st.subheader("请选择前端版本")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("### 🤖 Agent智能前端")
        st.markdown("""
        **基于LangGraph Agent的完整版本**

        - 🗣️ 自然语言输入，自动规划分析流程
        - 🎯 6个预定义Skill分析流程
        - 🔍 Planner → Executor → Reviewer 自动编排
        - 💬 分析完成后支持智能问答
        - 📊 参数自动推荐

        **适合**：体验Agent智能分析、作业演示
        """)
        if st.button("🚀 进入Agent前端", type="primary", use_container_width=True):
            st.session_state.app_mode = "agent"
            st.rerun()

with col2:
    with st.container(border=True):
        st.markdown("### 🔬 手动操作前端")
        st.markdown("""
        **标签页逐步操作版本**

        - 📑 7个标签页，逐步操作每个分析步骤
        - ⚙️ 高级参数可调（侧边栏折叠面板）
        - 🔬 直接调用引擎函数，透明可控
        - 📈 每步独立查看结果和图表

        **适合**：学习分析流程、调试参数、了解底层实现
        """)
        if st.button("🔬 进入手动前端", use_container_width=True):
            st.session_state.app_mode = "simple"
            st.rerun()

st.markdown("---")
st.caption("两个版本共享同一套生信计算引擎（engine/），分析结果一致。")
st.caption("项目地址：https://github.com/nosweet-omo/spatial-transcriptomics-agent")
