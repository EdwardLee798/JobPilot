#!/usr/bin/env python3
"""
跨平台的Job Application系统管理脚本
支持 Windows/macOS/Linux
替代 job-app.sh
"""

import subprocess
import sys
import time
import platform
import signal
from pathlib import Path

# 配置
PORT = 8888
IS_WINDOWS = platform.system() == 'Windows'


def check_port(port):
    """检查端口是否被占用"""
    try:
        import psutil
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    except ImportError:
        # 没有psutil，使用系统命令
        if IS_WINDOWS:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True
            )
            return f':{port}' in result.stdout
        else:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0


def start_service():
    """启动服务"""
    print("正在启动Job Application服务...")

    if check_port(PORT):
        print(f"⚠️  服务已在运行（端口{PORT}被占用）")
        return

    # 选择正确的gradlew命令
    if IS_WINDOWS:
        gradlew = "gradlew.bat"
    else:
        gradlew = "./gradlew"

    # 启动服务
    try:
        if IS_WINDOWS:
            # Windows: 使用 start /b 后台运行
            subprocess.Popen(
                [gradlew, "bootRun"],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            # Unix: 使用 nohup
            subprocess.Popen(
                [gradlew, "bootRun"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

        print("✓ 服务正在启动...")
        print(f"  端口: {PORT}")
        print("  日志: logs/app.log")

    except Exception as e:
        print(f"✗ 启动失败: {e}")
        sys.exit(1)


def stop_service():
    """停止服务"""
    print("正在停止Job Application服务...")

    try:
        import psutil

        # 查找Java进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline())
                if 'java' in proc.name().lower() and 'bootRun' in cmdline:
                    print(f"找到Java进程 (PID: {proc.pid})")
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                        print("✓ 服务已停止")
                    except:
                        proc.kill()
                        print("✓ 服务已强制停止")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        print("⚠️  未找到运行中的Java服务")

    except ImportError:
        # 没有psutil，使用系统命令
        print("⚠️  建议安装psutil以获得更好的进程管理: pip install psutil")

        if IS_WINDOWS:
            # Windows: 使用taskkill
            subprocess.run(["taskkill", "/F", "/IM", "java.exe"])
        else:
            # Unix: 使用pkill
            subprocess.run(["pkill", "-f", "bootRun"])

        print("✓ 已发送停止信号")


def status():
    """检查服务状态"""
    print("检查服务状态...")

    if check_port(PORT):
        print(f"✓ 服务正在运行（端口{PORT}）")

        # 尝试获取PID
        try:
            import psutil
            for conn in psutil.net_connections():
                if conn.laddr.port == PORT:
                    print(f"  PID: {conn.pid}")
                    break
        except:
            pass
    else:
        print(f"✗ 服务未运行")


def show_help():
    """显示帮助信息"""
    print("""
Job Application 系统管理脚本

用法:
    python job_app.py <command>

命令:
    start    启动服务
    stop     停止服务
    status   查看状态
    help     显示此帮助

示例:
    python job_app.py start
    python job_app.py stop
    python job_app.py status

注意:
    - 需要Java 21+环境
    - 建议安装psutil以获得更好的进程管理: pip install psutil
    """)


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        start_service()
    elif command == "stop":
        stop_service()
    elif command == "status":
        status()
    elif command == "help" or command == "--help" or command == "-h":
        show_help()
    else:
        print(f"未知命令: {command}")
        print("使用 'python job_app.py help' 查看帮助")
        sys.exit(1)


if __name__ == "__main__":
    main()
