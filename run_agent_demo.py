"""
Agent交互式演示脚本

提供命令行交互界面，测试Agent的自然语言分析功能。
"""

import sys
import os
import json
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.graph import run_agent, create_agent_graph
from agent.state import create_initial_state
from agent.tools import set_adata_to_state, get_adata_from_state

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator():
    """打印分隔线"""
    print("\n" + "="*60 + "\n")


def print_state_summary(state):
    """打印状态摘要"""
    print("\n📊 当前状态:")
    print(f"  - 当前步骤: {state.get('current_step', 'N/A')}")
    print(f"  - 已完成: {len(state.get('completed_steps', []))} 步")
    print(f"  - 生成图表: {len(state.get('plot_files', []))} 个")

    if state.get("error"):
        print(f"  - ⚠️  错误: {state.get('error')}")

    if state.get("summary"):
        print("\n📝 分析摘要:")
        print(state["summary"][:500] + "..." if len(state.get("summary", "")) > 500 else state.get("summary", ""))


def run_interactive_mode():
    """运行交互模式"""
    print("\n🧬 空间转录组智能分析平台 - Agent演示")
    print("="*60)
    print("\n可用命令:")
    print("  analyze <文件路径>  - 分析h5ad文件")
    print("  demo              - 使用示例数据运行演示")
    print("  status            - 查看当前状态")
    print("  quit              - 退出程序")
    print()

    # 存储当前状态
    current_state = None
    current_file = None

    while True:
        try:
            user_input = input("\n🔹 请输入命令: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\n👋 再见！")
                break

            if user_input.lower() == "status":
                if current_state:
                    print_state_summary(current_state)
                else:
                    print("  还没有运行任何分析")
                continue

            if user_input.lower() == "demo":
                # 使用示例数据
                print("\n🚀 使用示例数据运行演示...")
                sample_dir = os.path.join(os.path.dirname(__file__), "examples", "sample_data")
                sample_files = [f for f in os.listdir(sample_dir) if f.endswith(".h5ad")] if os.path.exists(sample_dir) else []
                if sample_files:
                    current_file = os.path.join(sample_dir, sample_files[0])
                    print(f"  📂 使用: {sample_files[0]}")
                else:
                    current_file = None
                user_input_text = "帮我分析这个空间转录组数据，进行完整的分析流程"
                print(f"\n📝 用户请求: {user_input_text}")

            elif user_input.lower().startswith("analyze "):
                # 分析指定文件
                current_file = user_input[8:].strip()
                if not os.path.exists(current_file):
                    print(f"  ❌ 文件不存在: {current_file}")
                    continue

                user_input_text = f"分析文件 {current_file}"
                print(f"\n📝 用户请求: {user_input_text}")

            else:
                # 自然语言输入
                user_input_text = user_input
                print(f"\n📝 处理请求: {user_input_text}")

            print_separator()
            print("🤖 Agent开始工作...")
            print_separator()

            # 运行Agent
            try:
                current_state = run_agent(
                    user_input=user_input_text,
                    file_path=current_file,
                    output_dir="storage/results/demo"
                )

                print_separator()
                print("✅ Agent运行完成！")
                print_separator()

                print_state_summary(current_state)

                if current_state.get("plot_files"):
                    print("\n📁 生成的图表文件:")
                    for f in current_state["plot_files"]:
                        print(f"  - {f}")

            except Exception as e:
                print(f"\n❌ Agent运行出错: {e}")
                logger.exception("Agent运行错误")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except EOFError:
            break


def run_automated_demo():
    """运行自动化演示"""
    print("\n🧬 空间转录组智能分析平台 - 自动演示")
    print("="*60)

    # 自动选择示例数据
    sample_dir = os.path.join(os.path.dirname(__file__), "examples", "sample_data")
    sample_files = [f for f in os.listdir(sample_dir) if f.endswith(".h5ad")] if os.path.exists(sample_dir) else []
    if sample_files:
        file_path = os.path.join(sample_dir, sample_files[0])
        print(f"\n📂 使用示例数据: {sample_files[0]}")
    else:
        file_path = None
        print("\n⚠️ 未找到示例数据，将尝试使用create_sample_data")

    # 使用示例数据演示
    user_input = "帮我分析这个空间转录组数据，进行完整的分析流程，包括质量控制、预处理、聚类和可视化"

    print(f"\n📝 用户请求: {user_input}")
    print_separator()

    # 运行Agent
    final_state = run_agent(
        user_input=user_input,
        file_path=file_path,
        output_dir="storage/results/demo"
    )

    print_separator()
    print("✅ 演示完成！")
    print_separator()

    print_state_summary(final_state)

    if final_state.get("plot_files"):
        print("\n📁 生成的图表文件:")
        for f in final_state["plot_files"]:
            print(f"  - {f}")


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        run_automated_demo()
    else:
        run_interactive_mode()


if __name__ == "__main__":
    main()
