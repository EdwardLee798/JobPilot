"""
Func2 Java服务管理器
负责启动、停止和检查Java自动投递服务
跨平台支持：Windows/macOS/Linux
"""

import subprocess
import requests
import time
import os
import json
import signal
import sqlite3
import sys
import platform
from pathlib import Path

# 检测操作系统
IS_WINDOWS = platform.system() == 'Windows'

# Func2项目路径 - 使用相对路径（跨平台）
# 从当前文件位置向上4层，然后进入Func2_AutoApplication
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent.parent.parent.parent
FUNC2_DIR = PROJECT_ROOT / "Func2_AutoApplication"

FUNC2_DB = FUNC2_DIR / "db" / "getjobs.db"
CONFIG_SCRIPT = FUNC2_DIR / "config_from_json.py"
JAVA_SERVICE_PORT = 8888
JAVA_SERVICE_URL = f"http://localhost:{JAVA_SERVICE_PORT}"

# PID文件路径 - 跨平台
if IS_WINDOWS:
    PID_FILE = Path(os.getenv('TEMP', 'C:\\Temp')) / "jobpilot_java_service.pid"
else:
    PID_FILE = Path("/tmp/jobpilot_java_service.pid")


def check_service_status():
    """检查Java服务是否运行"""
    try:
        # 使用boss/config端点检查（与job-app.sh一致）
        response = requests.get(f"{JAVA_SERVICE_URL}/api/boss/config", timeout=3)
        return response.status_code == 200
    except:
        return False


def start_service():
    """启动Java服务 - 跨平台实现"""
    if check_service_status():
        return {"success": True, "message": "服务已在运行"}

    try:
        # 根据操作系统选择启动命令
        if IS_WINDOWS:
            # Windows: 使用gradlew.bat
            gradlew_cmd = str(FUNC2_DIR / "gradlew.bat")
            # Windows下需要使用shell=True或完整路径
            process = subprocess.Popen(
                [gradlew_cmd, "bootRun"],
                cwd=str(FUNC2_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
                shell=False
            )
        else:
            # Unix: 使用job-app.sh或gradlew
            job_app_script = FUNC2_DIR / "job-app.sh"
            if job_app_script.exists():
                process = subprocess.Popen(
                    [str(job_app_script), "start"],
                    cwd=str(FUNC2_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            else:
                # 备用方案：直接使用gradlew
                process = subprocess.Popen(
                    ["./gradlew", "bootRun"],
                    cwd=str(FUNC2_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )

        # 保存PID
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))

        # 等待服务启动（最多30秒）
        for i in range(30):
            time.sleep(2)
            if check_service_status():
                return {
                    "success": True,
                    "message": "服务启动成功",
                    "url": JAVA_SERVICE_URL
                }

        return {"success": False, "error": "服务启动超时"}

    except Exception as e:
        return {"success": False, "error": f"启动失败: {str(e)}"}


def find_process_by_port(port):
    """跨平台查找占用指定端口的进程PID"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                connections = proc.net_connections()
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except ImportError:
        # 如果没有psutil，尝试使用系统命令
        if IS_WINDOWS:
            # Windows: 使用netstat
            try:
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        return int(parts[-1])
            except:
                pass
        else:
            # Unix: 使用lsof
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout.strip():
                    return int(result.stdout.strip())
            except:
                pass
    return None


def stop_service():
    """停止Java服务 - 跨平台实现"""
    try:
        # 先停止所有投递任务（这会关闭浏览器窗口）
        if check_service_status():
            try:
                print("正在停止投递任务...")
                call_api('/api/jobs/boss/stop', method='POST')
                call_api('/api/liepin/stop', method='POST')

                # 等待10秒让投递任务自然结束并关闭浏览器
                # stopDelivery()只是设置标志，需要等待投递循环检测并退出
                print("等待投递任务结束和浏览器关闭（10秒）...")
                time.sleep(10)
            except Exception as e:
                print(f"停止投递任务出错: {e}")

        # 找到并停止Java进程 - 跨平台方式
        try:
            pid = find_process_by_port(JAVA_SERVICE_PORT)

            if pid:
                print(f"正在停止Java服务 (PID: {pid})...")
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    proc.terminate()  # 优雅停止
                    proc.wait(timeout=5)  # 等待进程退出
                except ImportError:
                    # 没有psutil，使用系统命令
                    if IS_WINDOWS:
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], timeout=5)
                    else:
                        subprocess.run(["kill", str(pid)], timeout=5)
                    time.sleep(1)
            else:
                print("未找到运行中的Java服务")

        except Exception as e:
            print(f"停止进程失败: {e}")

        # 删除PID文件
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

        return {"success": True, "message": "服务已停止"}

    except Exception as e:
        return {"success": False, "error": f"停止失败: {str(e)}"}


def configure_from_resume(resume_json_path):
    """
    从简历JSON生成投递配置
    调用config_from_json.py脚本
    """
    try:
        # 复制简历JSON到Func2目录
        func2_resume_path = FUNC2_DIR / "resume.json"

        with open(resume_json_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)

        with open(func2_resume_path, 'w', encoding='utf-8') as f:
            json.dump(resume_data, f, ensure_ascii=False, indent=2)

        # 运行配置脚本
        result = subprocess.run(
            ["python3", str(CONFIG_SCRIPT)],
            cwd=str(FUNC2_DIR),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": "配置已更新",
                "output": result.stdout
            }
        else:
            return {
                "success": False,
                "error": f"配置失败: {result.stderr}"
            }

    except Exception as e:
        return {"success": False, "error": f"配置失败: {str(e)}"}


def get_boss_config():
    """获取Boss直聘配置"""
    try:
        conn = sqlite3.connect(str(FUNC2_DB))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM boss_config LIMIT 1")
        row = cursor.fetchone()

        if row:
            columns = [desc[0] for desc in cursor.description]
            config = dict(zip(columns, row))
            conn.close()
            return {"success": True, "config": config}
        else:
            conn.close()
            return {"success": False, "error": "配置不存在"}
    except Exception as e:
        return {"success": False, "error": f"读取配置失败: {str(e)}"}


def update_boss_config(config_data):
    """更新Boss直聘配置"""
    try:
        conn = sqlite3.connect(str(FUNC2_DB))
        cursor = conn.cursor()

        # 检查是否存在配置
        cursor.execute("SELECT COUNT(*) FROM boss_config")
        exists = cursor.fetchone()[0] > 0

        if exists:
            # 更新现有配置
            update_fields = []
            values = []
            for key, value in config_data.items():
                if key != 'id':
                    update_fields.append(f"{key} = ?")
                    if isinstance(value, (list, dict)):
                        values.append(json.dumps(value, ensure_ascii=False))
                    else:
                        values.append(value)

            query = f"UPDATE boss_config SET {', '.join(update_fields)}"
            cursor.execute(query, values)
        else:
            # 插入新配置
            columns = list(config_data.keys())
            placeholders = ['?'] * len(columns)
            values = []
            for val in config_data.values():
                if isinstance(val, (list, dict)):
                    values.append(json.dumps(val, ensure_ascii=False))
                else:
                    values.append(val)

            query = f"INSERT INTO boss_config ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(query, values)

        conn.commit()
        conn.close()

        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        return {"success": False, "error": f"更新配置失败: {str(e)}"}


def call_api(endpoint, method="GET", data=None):
    """调用Java服务的API"""
    try:
        url = f"{JAVA_SERVICE_URL}{endpoint}"

        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        else:
            return {"success": False, "error": f"不支持的方法: {method}"}

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {
                "success": False,
                "error": f"API调用失败: {response.status_code}",
                "detail": response.text
            }

    except Exception as e:
        return {"success": False, "error": f"API调用失败: {str(e)}"}
