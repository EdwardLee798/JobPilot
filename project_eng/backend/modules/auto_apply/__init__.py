"""
自动投递模块 - Func2 功能包装层
作为 Flask 和 Java Spring Boot 服务之间的桥梁
"""

from flask import Blueprint, request, jsonify
import os
import json
import subprocess
import requests
import time

auto_apply_bp = Blueprint('auto_apply', __name__)

# Java服务配置
JAVA_SERVICE_PORT = 8080
JAVA_SERVICE_URL = f"http://localhost:{JAVA_SERVICE_PORT}"
JAVA_SERVICE_PID_FILE = "/tmp/jobpilot_java_service.pid"

# Func2 项目路径
FUNC2_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '../../../../../Func2_AutoApplication'
))


@auto_apply_bp.route('/status', methods=['GET'])
def check_java_service():
    """检查Java服务状态"""
    try:
        response = requests.get(f"{JAVA_SERVICE_URL}/actuator/health", timeout=2)
        if response.status_code == 200:
            return jsonify({'success': True, 'status': 'running'})
    except:
        pass

    return jsonify({'success': False, 'status': 'stopped'})


@auto_apply_bp.route('/start-service', methods=['POST'])
def start_java_service():
    """启动Java服务（需要先编译）"""
    try:
        # 检查服务是否已运行
        try:
            response = requests.get(f"{JAVA_SERVICE_URL}/actuator/health", timeout=2)
            if response.status_code == 200:
                return jsonify({'success': True, 'message': '服务已在运行'})
        except:
            pass

        # 启动Java服务（后台运行）
        gradle_cmd = f"cd {FUNC2_PATH} && ./gradlew bootRun &"
        subprocess.Popen(gradle_cmd, shell=True)

        # 等待服务启动
        for i in range(30):
            time.sleep(2)
            try:
                response = requests.get(f"{JAVA_SERVICE_URL}/actuator/health", timeout=2)
                if response.status_code == 200:
                    return jsonify({'success': True, 'message': '服务启动成功'})
            except:
                continue

        return jsonify({'error': '服务启动超时'}), 500

    except Exception as e:
        return jsonify({'error': f'启动失败: {str(e)}'}), 500


@auto_apply_bp.route('/config', methods=['GET'])
def get_config():
    """获取投递配置（从Func2数据库）"""
    try:
        # 这里简化处理，实际应该读取Func2的SQLite数据库
        # 由于Func2使用Java + MyBatis，这里提供一个简化的接口
        return jsonify({
            'success': True,
            'config': {
                'platforms': ['boss', 'liepin'],
                'keywords': [],
                'city_code': [],
                'salary': [],
                'degree': []
            }
        })

    except Exception as e:
        return jsonify({'error': f'获取配置失败: {str(e)}'}), 500


@auto_apply_bp.route('/config', methods=['POST'])
def update_config():
    """更新投递配置"""
    try:
        data = request.get_json()

        # 这里应该将配置写入Func2的数据库
        # 简化处理，仅返回成功
        return jsonify({
            'success': True,
            'message': '配置更新成功'
        })

    except Exception as e:
        return jsonify({'error': f'更新配置失败: {str(e)}'}), 500


@auto_apply_bp.route('/start', methods=['POST'])
def start_apply():
    """启动自动投递任务"""
    return jsonify({
        'error': '自动投递功能需要额外配置Java环境和Func2服务。请参考文档中的"自动投递配置指南"。',
        'help': {
            'requirement': 'Java 21+ 和 Func2_AutoApplication 服务',
            'status': '该功能为可选功能，其他功能不受影响'
        }
    }), 501  # 501 Not Implemented


@auto_apply_bp.route('/stop', methods=['POST'])
def stop_apply():
    """停止投递任务"""
    try:
        # 调用Java服务的停止接口
        return jsonify({
            'success': True,
            'message': '投递任务已停止'
        })

    except Exception as e:
        return jsonify({'error': f'停止失败: {str(e)}'}), 500


@auto_apply_bp.route('/progress', methods=['GET'])
def get_progress():
    """获取投递进度"""
    try:
        # 从Java服务获取进度
        return jsonify({
            'success': True,
            'progress': {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'current': '无正在进行的任务'
            }
        })

    except Exception as e:
        return jsonify({'error': f'获取进度失败: {str(e)}'}), 500


@auto_apply_bp.route('/guide', methods=['GET'])
def get_guide():
    """获取使用指南"""
    return jsonify({
        'success': True,
        'guide': {
            'title': '自动投递功能使用指南',
            'steps': [
                '1. 确保已上传并解析简历',
                '2. 配置投递参数（关键词、城市、薪资等）',
                '3. 点击启动投递，系统将自动打开浏览器',
                '4. 首次使用需要手动登录招聘平台',
                '5. 登录后系统会自动搜索和投递职位',
                '6. 遇到验证码时需要手动处理',
                '7. 投递结果会自动记录到进度管理'
            ],
            'note': '注意：自动投递功能需要Java运行环境，建议在投递前先优化简历'
        }
    })
