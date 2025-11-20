"""
Func2 Java服务管理器
负责启动、停止和检查Java自动投递服务
"""

import subprocess
import requests
import time
import os
import json
import signal
import sqlite3
from pathlib import Path

# Func2项目路径
FUNC2_DIR = Path("/Users/zijiancai/Desktop/hkucsfiles/comp7607/JobPilot/Func2_AutoApplication")
FUNC2_DB = FUNC2_DIR / "db" / "getjobs.db"
CONFIG_SCRIPT = FUNC2_DIR / "config_from_json.py"
JAVA_SERVICE_PORT = 8888
JAVA_SERVICE_URL = f"http://localhost:{JAVA_SERVICE_PORT}"
PID_FILE = "/tmp/jobpilot_java_service.pid"


def check_service_status():
    """检查Java服务是否运行"""
    try:
        # 使用boss/config端点检查（与job-app.sh一致）
        response = requests.get(f"{JAVA_SERVICE_URL}/api/boss/config", timeout=3)
        return response.status_code == 200
    except:
        return False


def start_service():
    """启动Java服务"""
    if check_service_status():
        return {"success": True, "message": "服务已在运行"}

    try:
        # 使用job-app.sh启动服务
        job_app_script = FUNC2_DIR / "job-app.sh"

        # 后台启动服务
        process = subprocess.Popen(
            [str(job_app_script), "start"],
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


def stop_service():
    """停止Java服务"""
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

        # 找到并kill Java进程
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{JAVA_SERVICE_PORT}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.stdout.strip():
                pid = result.stdout.strip()
                print(f"正在停止Java服务 (PID: {pid})...")
                subprocess.run(["kill", pid], timeout=5)
                time.sleep(1)  # 等待进程退出
            else:
                print("未找到运行中的Java服务")

        except Exception as e:
            print(f"Kill进程失败: {e}")

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
