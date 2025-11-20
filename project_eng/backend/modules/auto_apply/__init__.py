"""
自动投递模块 - Func2 功能包装层
作为 Flask 和 Java Spring Boot 服务之间的桥梁
"""

from flask import Blueprint, request, jsonify
import os
import json
from .java_service import (
    check_service_status,
    start_service,
    stop_service,
    configure_from_resume,
    get_boss_config,
    update_boss_config,
    call_api
)

auto_apply_bp = Blueprint('auto_apply', __name__)

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESUME_DIR = os.path.join(DATA_DIR, 'resumes')


@auto_apply_bp.route('/status', methods=['GET'])
def check_java_service():
    """检查Java服务状态"""
    is_running = check_service_status()
    return jsonify({
        'success': True,
        'status': 'running' if is_running else 'stopped',
        'message': '服务正常运行' if is_running else '服务未启动'
    })


@auto_apply_bp.route('/start-service', methods=['POST'])
def start_java_service():
    """启动Java服务"""
    result = start_service()
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


@auto_apply_bp.route('/stop-service', methods=['POST'])
def stop_java_service():
    """停止Java服务"""
    result = stop_service()
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


@auto_apply_bp.route('/config', methods=['GET'])
def get_config():
    """获取投递配置"""
    result = get_boss_config()
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


@auto_apply_bp.route('/config', methods=['POST'])
def update_config():
    """更新投递配置"""
    try:
        data = request.get_json()
        result = update_boss_config(data)

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({'error': f'更新配置失败: {str(e)}'}), 500


@auto_apply_bp.route('/start', methods=['POST'])
def start_apply():
    """启动自动投递任务"""
    try:
        data = request.get_json()
        platform = data.get('platform', 'boss')
        resume_id = data.get('resume_id')
        keywords = data.get('keywords', '')
        cities = data.get('cities', '')

        if not resume_id:
            return jsonify({'error': '缺少resume_id参数'}), 400

        # 检查服务状态
        if not check_service_status():
            return jsonify({
                'error': 'Java服务未启动',
                'help': '请先点击"启动服务"按钮'
            }), 503

        # 从resume_id读取简历数据并生成配置
        resume_json_path = os.path.join(RESUME_DIR, f"{resume_id}.json")

        if not os.path.exists(resume_json_path):
            return jsonify({'error': '简历文件不存在'}), 404

        # 配置投递参数（基于简历）
        config_result = configure_from_resume(resume_json_path)

        if not config_result.get('success'):
            return jsonify({
                'error': '配置简历信息失败',
                'detail': config_result.get('error')
            }), 500

        # 如果用户输入了关键词或城市，覆盖默认配置
        if keywords or cities:
            current_config = get_boss_config()
            if current_config.get('success'):
                config_data = current_config['config']

                # 更新关键词
                if keywords:
                    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
                    config_data['keywords'] = json.dumps(keyword_list, ensure_ascii=False)

                # 更新城市（直接使用城市名称）
                if cities:
                    # Boss系统支持城市名称，直接存储第一个城市
                    city_list = [c.strip() for c in cities.split(',') if c.strip()]
                    config_data['city_code'] = city_list[0] if city_list else '北京'

                # 更新配置到数据库
                update_boss_config(config_data)

        # 调用Java服务的API启动投递
        if platform == 'boss':
            api_result = call_api('/api/jobs/boss/execute', method='POST', data={
                'autoApply': True,
                'maxCount': data.get('max_count', 50)
            })
        elif platform == 'liepin':
            api_result = call_api('/api/liepin/start', method='POST', data={
                'autoApply': True,
                'maxCount': data.get('max_count', 50)
            })
        else:
            return jsonify({'error': f'不支持的平台: {platform}'}), 400

        if api_result.get('success'):
            return jsonify({
                'success': True,
                'message': f'{platform}平台投递任务已启动',
                'task_id': api_result.get('data', {}).get('taskId')
            })
        else:
            return jsonify({
                'error': '启动投递失败',
                'detail': api_result.get('error')
            }), 500

    except Exception as e:
        return jsonify({'error': f'启动失败: {str(e)}'}), 500


@auto_apply_bp.route('/stop', methods=['POST'])
def stop_apply():
    """停止投递任务"""
    try:
        data = request.get_json()
        platform = data.get('platform', 'boss')

        # 先检查Java服务是否在运行
        if not check_service_status():
            return jsonify({
                'success': True,
                'message': '服务未运行，无需停止'
            })

        # 调用Java服务的停止接口
        if platform == 'boss':
            result = call_api('/api/jobs/boss/stop', method='POST')
        elif platform == 'liepin':
            result = call_api('/api/liepin/stop', method='POST')
        else:
            return jsonify({'error': f'不支持的平台: {platform}'}), 400

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': '投递任务已停止'
            })
        else:
            return jsonify({'error': result.get('error')}), 500

    except Exception as e:
        return jsonify({'error': f'停止失败: {str(e)}'}), 500


@auto_apply_bp.route('/progress', methods=['GET'])
def get_progress():
    """获取投递进度"""
    try:
        # 检查服务状态
        if not check_service_status():
            return jsonify({
                'success': True,
                'progress': {
                    'total': 0,
                    'completed': 0,
                    'failed': 0,
                    'current': '服务未运行'
                }
            })

        # 从Java服务获取Boss和Liepin的状态
        boss_status = call_api('/api/jobs/boss/status', method='GET')

        progress_data = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'current': '无正在进行的任务'
        }

        if boss_status.get('success'):
            status = boss_status.get('data', {})
            if status.get('isRunning'):
                # 从状态中提取进度信息
                progress_data['current'] = 'Boss投递进行中'
                # 如果Java服务提供了更详细的统计，可以在这里解析

        return jsonify({
            'success': True,
            'progress': progress_data
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
