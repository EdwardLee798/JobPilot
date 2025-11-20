"""
投递进度管理模块 - 整合 Func4 功能
提供投递记录管理和实时更新推送
"""

from flask import Blueprint, request, jsonify, Response
import json
import time
import sqlite3
import os
from datetime import datetime

status_tracking_bp = Blueprint('status_tracking', __name__)

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_DIR = os.path.join(DATA_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'tracking.db')


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 创建职位总览表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_summary (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT NOT NULL,
            company_name TEXT NOT NULL,
            job_desc TEXT,
            tracking_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建申请状态表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            status_update TEXT NOT NULL,
            event_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES job_summary (job_id)
        )
    ''')

    conn.commit()
    conn.close()


# 初始化数据库
init_database()


@status_tracking_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """获取所有职位记录及其状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                js.job_id,
                js.job_title,
                js.company_name,
                js.job_desc,
                js.tracking_method,
                js.created_at,
                ast.status_update,
                ast.event_time,
                ast.created_at as status_timestamp
            FROM job_summary js
            LEFT JOIN application_status ast ON js.job_id = ast.job_id
            ORDER BY js.job_id DESC, ast.created_at ASC
        '''

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        # 组织数据
        jobs_dict = {}
        for row in rows:
            job_id = row['job_id']
            if job_id not in jobs_dict:
                jobs_dict[job_id] = {
                    'job_id': job_id,
                    'job_title': row['job_title'],
                    'company_name': row['company_name'],
                    'job_desc': row['job_desc'],
                    'tracking_method': row['tracking_method'],
                    'created_at': row['created_at'],
                    'statuses': []
                }

            if row['status_update']:
                jobs_dict[job_id]['statuses'].append({
                    'status': row['status_update'],
                    'event_time': row['event_time'],
                    'timestamp': row['status_timestamp']
                })

        jobs = list(jobs_dict.values())
        return jsonify({'success': True, 'jobs': jobs})

    except Exception as e:
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@status_tracking_bp.route('/job', methods=['POST'])
def create_job():
    """创建新投递记录"""
    try:
        data = request.get_json()
        job_title = data.get('job_title')
        company_name = data.get('company_name')
        job_desc = data.get('job_desc', '')
        tracking_method = data.get('tracking_method', '')

        if not job_title or not company_name:
            return jsonify({'error': '缺少必要参数'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 插入职位记录
        cursor.execute('''
            INSERT INTO job_summary (job_title, company_name, job_desc, tracking_method)
            VALUES (?, ?, ?, ?)
        ''', (job_title, company_name, job_desc, tracking_method))

        job_id = cursor.lastrowid

        # 创建初始状态
        cursor.execute('''
            INSERT INTO application_status (job_id, status_update, event_time)
            VALUES (?, ?, ?)
        ''', (job_id, '已申请', datetime.now().isoformat()))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': '投递记录创建成功'
        })

    except Exception as e:
        return jsonify({'error': f'创建失败: {str(e)}'}), 500


@status_tracking_bp.route('/job/<int:job_id>', methods=['PUT'])
def update_job_status(job_id):
    """更新投递状态"""
    try:
        data = request.get_json()
        status_update = data.get('status')
        event_time = data.get('event_time')

        if not status_update:
            return jsonify({'error': '缺少状态参数'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查job是否存在
        cursor.execute('SELECT job_id FROM job_summary WHERE job_id = ?', (job_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': '职位不存在'}), 404

        # 插入新状态
        cursor.execute('''
            INSERT INTO application_status (job_id, status_update, event_time)
            VALUES (?, ?, ?)
        ''', (job_id, status_update, event_time))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '状态更新成功'
        })

    except Exception as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500


@status_tracking_bp.route('/events')
def events():
    """SSE实时推送投递记录变化"""
    def generate():
        last_check = 0
        while True:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # 获取最新记录
                cursor.execute('''
                    SELECT
                        js.job_id,
                        js.job_title,
                        js.company_name,
                        ast.status_update,
                        ast.event_time,
                        ast.created_at as timestamp
                    FROM job_summary js
                    LEFT JOIN application_status ast ON js.job_id = ast.job_id
                    WHERE strftime('%s', ast.created_at) > ?
                    ORDER BY ast.created_at DESC
                ''', (last_check,))

                rows = cursor.fetchall()
                conn.close()

                if rows:
                    records = [dict(row) for row in rows]
                    payload = json.dumps(records, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                    last_check = time.time()

                time.sleep(2)  # 每2秒检查一次

            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(2)

    return Response(generate(), mimetype='text/event-stream')


@status_tracking_bp.route('/job/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """删除投递记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 删除状态记录
        cursor.execute('DELETE FROM application_status WHERE job_id = ?', (job_id,))

        # 删除职位记录
        cursor.execute('DELETE FROM job_summary WHERE job_id = ?', (job_id,))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '删除成功'})

    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@status_tracking_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 总职位数
        cursor.execute('SELECT COUNT(*) as total FROM job_summary')
        total = cursor.fetchone()['total']

        # 各状态数量
        cursor.execute('''
            SELECT status_update, COUNT(DISTINCT job_id) as count
            FROM application_status
            WHERE (job_id, created_at) IN (
                SELECT job_id, MAX(created_at)
                FROM application_status
                GROUP BY job_id
            )
            GROUP BY status_update
        ''')

        status_counts = {row['status_update']: row['count'] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'by_status': status_counts
            }
        })

    except Exception as e:
        return jsonify({'error': f'获取统计失败: {str(e)}'}), 500
