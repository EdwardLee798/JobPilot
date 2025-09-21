import sys
import subprocess
import os

print("--- Python 环境诊断脚本 ---")

# 1. 打印当前正在运行的Python解释器的路径
print(f"\n[1] Python 解释器路径:")
print(f"    -> {sys.executable}")

# 2. 尝试导入 httpx 并打印其版本和位置
try:
    import httpx
    print("\n[2] httpx 库信息:")
    print(f"    -> 成功导入 httpx。")
    print(f"    -> 版本 (Version): {httpx.__version__}")
    print(f"    -> 文件路径 (Location): {httpx.__file__}")
except ImportError:
    print("\n[2] httpx 库信息:")
    print("    -> 错误：无法导入 httpx。这个库没有为当前的Python解释器安装。")
except Exception as e:
    print(f"\n[2] 导入 httpx 时发生未知错误: {e}")

# 3. 使用与当前Python关联的pip命令，检查httpx的安装信息
print("\n[3] 'pip' 命令分析:")
# 构建与当前Python解释器在同一个目录下的pip命令的路径
pip_executable = os.path.join(os.path.dirname(sys.executable), 'pip')

if not os.path.exists(pip_executable):
    print(f"    -> 错误：在这个路径下找不到 'pip' 命令: {pip_executable}")
    pip_executable = 'pip' # Fallback to system pip
    print(f"    -> 尝试使用系统默认的 'pip' 命令...")

try:
    # 运行 'pip show httpx'
    result = subprocess.run(
        [pip_executable, "show", "httpx"],
        capture_output=True,
        text=True,
        check=True,
        encoding='utf-8'
    )
    print("    -> 'pip show httpx' 的输出信息:\n")
    # 格式化输出
    for line in result.stdout.strip().split('\n'):
        print(f"        {line}")
    
except (subprocess.CalledProcessError, FileNotFoundError):
    print("    -> 'pip show httpx' 命令执行失败。")
    print("    -> 这表明根据 pip 的记录，httpx 库未安装，或者 pip 命令本身有问题。")


print("\n--- 诊断结束 ---")