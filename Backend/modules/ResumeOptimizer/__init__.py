"""
简历优化模块 - 整合 Func3 功能
基于JD匹配简历并生成优化版本
"""

from flask import Blueprint, request, jsonify, send_file
import os
import json
import uuid
from datetime import datetime
from .optimizer import optimize_resume_with_jd, generate_pdf_resume

resume_optimizer_bp = Blueprint('resume_optimizer', __name__)

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESUME_DIR = os.path.join(DATA_DIR, 'resumes')
GENERATED_DIR = os.path.join(DATA_DIR, 'generated')


@resume_optimizer_bp.route('/analyze', methods=['POST'])
def analyze_jd():
    """分析JD并匹配简历经历"""
    try:
        data = request.get_json()
        resume_id = data.get('resume_id')
        jd_text = data.get('jd_text')

        if not resume_id or not jd_text:
            return jsonify({'error': '缺少resume_id或jd_text参数'}), 400

        # 读取简历JSON
        json_path = os.path.join(RESUME_DIR, f"{resume_id}.json")
        if not os.path.exists(json_path):
            return jsonify({'error': '简历不存在'}), 404

        with open(json_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)

        # 分析JD并优化简历
        optimized_data = optimize_resume_with_jd(resume_data, jd_text)

        return jsonify({
            'success': True,
            'data': optimized_data
        })

    except Exception as e:
        return jsonify({'error': f'分析失败: {str(e)}'}), 500


@resume_optimizer_bp.route('/generate', methods=['POST'])
def generate_resume():
    """生成优化后的简历PDF"""
    try:
        data = request.get_json()
        resume_id = data.get('resume_id')
        jd_text = data.get('jd_text')
        language = data.get('language', 'zh')  # zh 或 en

        if not resume_id or not jd_text:
            return jsonify({'error': '缺少resume_id或jd_text参数'}), 400

        # 读取简历JSON
        json_path = os.path.join(RESUME_DIR, f"{resume_id}.json")
        if not os.path.exists(json_path):
            return jsonify({'error': '简历不存在'}), 404

        with open(json_path, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)

        # 优化简历
        optimized_data = optimize_resume_with_jd(resume_data, jd_text)

        # 生成PDF
        generated_id = str(uuid.uuid4())
        pdf_filename = f"{generated_id}.pdf"
        pdf_path = os.path.join(GENERATED_DIR, pdf_filename)

        generate_pdf_resume(optimized_data, pdf_path, language)

        # 保存优化后的JSON
        json_filename = f"{generated_id}.json"
        json_save_path = os.path.join(GENERATED_DIR, json_filename)
        with open(json_save_path, 'w', encoding='utf-8') as f:
            json.dump(optimized_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'generated_id': generated_id,
            'pdf_url': f'/api/optimize/download/{generated_id}',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': f'生成失败: {str(e)}'}), 500


@resume_optimizer_bp.route('/download/<generated_id>', methods=['GET'])
def download_resume(generated_id):
    """下载生成的简历HTML"""
    html_path = os.path.join(GENERATED_DIR, f"{generated_id}.html")

    if not os.path.exists(html_path):
        return jsonify({'error': '文件不存在'}), 404

    return send_file(html_path, as_attachment=False, download_name='optimized_resume.html')


@resume_optimizer_bp.route('/list', methods=['GET'])
def list_generated():
    """列出所有生成的简历"""
    try:
        generated = []
        for filename in os.listdir(GENERATED_DIR):
            if filename.endswith('.json'):
                generated_id = filename.replace('.json', '')
                json_path = os.path.join(GENERATED_DIR, filename)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    generated.append({
                        'generated_id': generated_id,
                        'name': data.get('header', {}).get('name', ''),
                        'timestamp': os.path.getmtime(json_path)
                    })

        generated.sort(key=lambda x: x['timestamp'], reverse=True)
        return jsonify({'success': True, 'generated': generated})
    except Exception as e:
        return jsonify({'error': f'获取列表失败: {str(e)}'}), 500
