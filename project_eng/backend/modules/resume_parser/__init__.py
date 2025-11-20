"""
简历解析模块 - 整合 Func1 功能
提供简历上传、解析和信息提取API
"""

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime
from .parser import parse_resume, extract_resume_info, save_resume_json

resume_parser_bp = Blueprint('resume_parser', __name__)

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESUME_DIR = os.path.join(DATA_DIR, 'resumes')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@resume_parser_bp.route('/upload', methods=['POST'])
def upload_resume():
    """上传简历文件并解析"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式，仅支持 PDF, DOCX, TXT'}), 400

    try:
        # 生成唯一ID
        resume_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # 保存原始文件
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{resume_id}.{ext}"
        file_path = os.path.join(RESUME_DIR, saved_filename)
        file.save(file_path)

        # 解析简历文本
        text = parse_resume(file_path)

        # 提取结构化信息
        resume_data = extract_resume_info(text)
        resume_data['user_id'] = resume_id

        # 保存JSON
        json_path = os.path.join(RESUME_DIR, f"{resume_id}.json")
        save_resume_json(resume_data, json_path)

        return jsonify({
            'success': True,
            'resume_id': resume_id,
            'filename': filename,
            'timestamp': timestamp,
            'data': resume_data
        })

    except Exception as e:
        return jsonify({'error': f'解析失败: {str(e)}'}), 500


@resume_parser_bp.route('/parse/<resume_id>', methods=['GET'])
def get_resume(resume_id):
    """获取已解析的简历数据"""
    json_path = os.path.join(RESUME_DIR, f"{resume_id}.json")

    if not os.path.exists(json_path):
        return jsonify({'error': '简历不存在'}), 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'error': f'读取失败: {str(e)}'}), 500


@resume_parser_bp.route('/list', methods=['GET'])
def list_resumes():
    """列出所有已上传的简历"""
    try:
        resumes = []
        for filename in os.listdir(RESUME_DIR):
            if filename.endswith('.json'):
                resume_id = filename.replace('.json', '')
                json_path = os.path.join(RESUME_DIR, filename)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    resumes.append({
                        'resume_id': resume_id,
                        'name': data.get('name', ''),
                        'headline': data.get('headline', ''),
                        'timestamp': os.path.getmtime(json_path)
                    })

        # 按时间倒序排列
        resumes.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify({'success': True, 'resumes': resumes})
    except Exception as e:
        return jsonify({'error': f'获取列表失败: {str(e)}'}), 500


@resume_parser_bp.route('/delete/<resume_id>', methods=['DELETE'])
def delete_resume(resume_id):
    """删除简历"""
    try:
        # 删除JSON文件
        json_path = os.path.join(RESUME_DIR, f"{resume_id}.json")
        if os.path.exists(json_path):
            os.remove(json_path)

        # 删除原始文件
        for ext in ['pdf', 'docx', 'txt']:
            file_path = os.path.join(RESUME_DIR, f"{resume_id}.{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)

        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500
