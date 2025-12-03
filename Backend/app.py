"""
JobPilot 主应用入口
整合简历解析、简历优化、自动投递和进度管理四大功能
"""

from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__, static_folder='../frontend')
CORS(app)

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESUME_DIR = os.path.join(DATA_DIR, 'resumes')
GENERATED_DIR = os.path.join(DATA_DIR, 'generated')
DB_DIR = os.path.join(DATA_DIR, 'database')

# 确保目录存在
for directory in [RESUME_DIR, GENERATED_DIR, DB_DIR]:
    os.makedirs(directory, exist_ok=True)

# 导入功能模块
from modules.resume_parser import resume_parser_bp
from modules.resume_optimizer import resume_optimizer_bp
from modules.status_tracking import status_tracking_bp
from modules.auto_apply import auto_apply_bp

# 注册蓝图
app.register_blueprint(resume_parser_bp, url_prefix='/api/resume')
app.register_blueprint(resume_optimizer_bp, url_prefix='/api/optimize')
app.register_blueprint(status_tracking_bp, url_prefix='/api/tracking')
app.register_blueprint(auto_apply_bp, url_prefix='/api/apply')


@app.route('/')
def index():
    """主页"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/demo')
def realtime_demo():
    """实时监控演示页面"""
    return send_file('realtime_demo.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件服务"""
    return send_from_directory(app.static_folder, path)


@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'modules': {
            'resume_parser': True,
            'resume_optimizer': True,
            'status_tracking': True,
            'auto_apply': True
        }
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Internal error: {error}')
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info('Starting JobPilot application...')
    logger.info(f'Data directory: {DATA_DIR}')
    logger.info(f'Resume directory: {RESUME_DIR}')
    logger.info(f'Generated directory: {GENERATED_DIR}')
    logger.info(f'Database directory: {DB_DIR}')
    logger.info('')
    logger.info('=' * 60)
    logger.info('实时监控功能已启用')
    logger.info('  - 每5秒自动检测Boss投递的新记录')
    logger.info('  - 自动同步到状态跟踪模块')
    logger.info('  - 访问 http://localhost:5000/demo 查看实时演示')
    logger.info('=' * 60)
    logger.info('')

    app.run(host='0.0.0.0', port=5000, debug=True)
