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

# 导入agent
try:
    from .agent import invoke_agent, stream_agent
    agent_available = True
except Exception as e:
    print(f"Warning: Agent not available: {e}")
    agent_available = False

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_DIR = os.path.join(DATA_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'tracking.db')

# Func2自动投递数据库路径
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
FUNC2_DB_PATH = PROJECT_ROOT / "Func2_AutoApplication" / "db" / "getjobs.db"


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
            event_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES job_summary (job_id)
        )
    ''')
    
    # 检查并添加 updated_at 字段（用于旧数据库迁移）
    cursor.execute("PRAGMA table_info(application_status)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'updated_at' not in columns:
        # SQLite不支持ALTER TABLE ADD COLUMN with non-constant default
        # 先添加字段，然后更新现有记录
        cursor.execute('''
            ALTER TABLE application_status 
            ADD COLUMN updated_at TIMESTAMP
        ''')
        # 为现有记录设置updated_at为created_at
        cursor.execute('''
            UPDATE application_status 
            SET updated_at = created_at 
            WHERE updated_at IS NULL
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
                ast.id,
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
                    'id': row['id'],
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
        ''', (job_id, '已申请', time.time()))

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


@status_tracking_bp.route('/event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """删除单个事件记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否是首个事件（防止删除"开始流程跟踪"记录）
        cursor.execute('''
            SELECT job_id, 
                   (SELECT COUNT(*) FROM application_status WHERE job_id = a.job_id) as total_count
            FROM application_status a
            WHERE id = ?
        ''', (event_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': '事件不存在'}), 404
        
        job_id, total_count = result
        
        # 如果该职位只有一条记录，不允许删除
        if total_count <= 1:
            conn.close()
            return jsonify({'success': False, 'error': '不能删除初始记录'}), 400
        
        # 删除事件
        cursor.execute('DELETE FROM application_status WHERE id = ?', (event_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '事件已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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


@status_tracking_bp.route('/chat_stream', methods=['GET', 'POST'])
def chat_stream():
    """SSE流式对话接口"""
    if not agent_available:
        return jsonify({'error': 'Agent未初始化'}), 503
    
    try:
        if request.method == 'POST':
            data = request.get_json()
            message = data.get('message', '')
        else:
            message = request.args.get('message', '')
        
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
        
        def generate():
            try:
                final_content = ""
                
                for event in stream_agent(message, thread_id="user_session"):
                    event_type = event.get('type')
                    
                    if event_type == 'tool_call':
                        # 发送工具调用信息
                        tool_name = event.get('tool_name', '未知工具')
                        tool_args = event.get('tool_args', {})
                        
                        # 构建友好的工具调用描述
                        tool_desc = f"🔧 调用工具: {tool_name}"
                        if tool_args:
                            # 简化参数显示
                            args_str = ", ".join([f"{k}={v}" for k, v in list(tool_args.items())[:2]])
                            if len(tool_args) > 2:
                                args_str += "..."
                            tool_desc += f" ({args_str})"
                        
                        yield f"data: {json.dumps({'type': 'tool', 'message': tool_desc}, ensure_ascii=False)}\n\n"
                        time.sleep(0.1)
                    
                    elif event_type == 'content':
                        # 累积最终内容
                        content = event.get('content', '')
                        if content and content != final_content:
                            final_content = content
                    
                    elif event_type == 'error':
                        yield f"data: {json.dumps({'type': 'error', 'message': event.get('message')}, ensure_ascii=False)}\n\n"
                        return
                    
                    elif event_type == 'done':
                        # 按字符发送最终内容，实现打字机效果
                        if final_content:
                            for char in final_content:
                                yield f"data: {json.dumps({'type': 'char', 'char': char}, ensure_ascii=False)}\n\n"
                                time.sleep(0.02)  # 每个字符延迟20ms
                        
                        # 发送完成标记
                        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@status_tracking_bp.route('/merged_data', methods=['GET'])
def get_merged_data():
    """SSE流式推送合并后的投递数据（用于时间线展示）"""
    def generate():
        last_check = 0
        while True:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                query = '''
                    SELECT
                        js.job_id,
                        js.job_title,
                        js.company_name,
                        js.job_desc,
                        ast.id,
                        ast.status_update,
                        ast.event_time,
                        ast.created_at as timestamp
                    FROM job_summary js
                    LEFT JOIN application_status ast ON js.job_id = ast.job_id
                    ORDER BY js.job_id, ast.created_at ASC
                '''

                cursor.execute(query)
                rows = cursor.fetchall()
                conn.close()

                records = []
                for row in rows:
                    records.append({
                        'job_id': row['job_id'],
                        'job_title': row['job_title'],
                        'company_name': row['company_name'],
                        'job_desc': row['job_desc'],
                        'id': row['id'],
                        'status_update': row['status_update'],
                        'event_time': row['event_time'] if row['event_time'] else -100.0,
                        'timestamp': row['timestamp']
                    })

                payload = json.dumps(records, ensure_ascii=False)
                yield f"data: {payload}\n\n"

                time.sleep(2)  # 每2秒推送一次

            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(2)

    return Response(generate(), mimetype='text/event-stream')

def get_func2_connection():
    """获取Func2数据库连接"""
    conn = sqlite3.connect(str(FUNC2_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@status_tracking_bp.route('/delivery/stats', methods=['GET'])
def get_delivery_stats():
    """获取Func2自动投递的统计信息"""
    try:
        if not FUNC2_DB_PATH.exists():
            return jsonify({
                'success': True,
                'stats': {
                    'total': 0,
                    'delivered': 0,
                    'filtered': 0,
                    'pending': 0,
                    'boss': {'total': 0, 'delivered': 0},
                    'liepin': {'total': 0, 'delivered': 0}
                }
            })

        conn = get_func2_connection()
        cursor = conn.cursor()

        # Boss直聘统计
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN delivery_status = '已投递' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN delivery_status = '已过滤' THEN 1 ELSE 0 END) as filtered,
                SUM(CASE WHEN delivery_status = '未投递' THEN 1 ELSE 0 END) as pending
            FROM boss_data
        """)
        boss_stats = cursor.fetchone()

        # 猎聘统计（使用 delivered 字段：1=已投递，0=未投递）
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN delivered = 1 THEN 1 ELSE 0 END) as delivered,
                0 as filtered,
                SUM(CASE WHEN delivered = 0 THEN 1 ELSE 0 END) as pending
            FROM liepin_data
        """)
        liepin_stats = cursor.fetchone()

        conn.close()

        # 合计
        total_count = (boss_stats['total'] or 0) + (liepin_stats['total'] or 0)
        delivered_count = (boss_stats['delivered'] or 0) + (liepin_stats['delivered'] or 0)
        filtered_count = (boss_stats['filtered'] or 0) + (liepin_stats['filtered'] or 0)
        pending_count = (boss_stats['pending'] or 0) + (liepin_stats['pending'] or 0)

        return jsonify({
            'success': True,
            'stats': {
                'total': total_count,
                'delivered': delivered_count,
                'filtered': filtered_count,
                'pending': pending_count,
                'boss': {
                    'total': boss_stats['total'] or 0,
                    'delivered': boss_stats['delivered'] or 0,
                    'filtered': boss_stats['filtered'] or 0,
                    'pending': boss_stats['pending'] or 0
                },
                'liepin': {
                    'total': liepin_stats['total'] or 0,
                    'delivered': liepin_stats['delivered'] or 0,
                    'filtered': liepin_stats['filtered'] or 0,
                    'pending': liepin_stats['pending'] or 0
                }
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'获取统计失败: {str(e)}'}), 500


@status_tracking_bp.route('/delivery/records', methods=['GET'])
def get_delivery_records():
    """获取详细投递记录"""
    try:
        if not FUNC2_DB_PATH.exists():
            return jsonify({'success': True, 'records': []})

        # 获取过滤参数
        platform = request.args.get('platform', 'all')  # all, boss, liepin
        status = request.args.get('status', 'all')  # all, 已投递, 已过滤, 未投递
        limit = int(request.args.get('limit', 100))

        conn = get_func2_connection()
        cursor = conn.cursor()

        records = []

        # Boss直聘记录
        if platform in ['all', 'boss']:
            query = """
                SELECT
                    'boss' as platform,
                    company_name,
                    job_name,
                    salary,
                    location,
                    experience,
                    degree,
                    hr_name,
                    delivery_status,
                    job_url,
                    created_at,
                    updated_at
                FROM boss_data
            """
            if status != 'all':
                query += f" WHERE delivery_status = '{status}'"
            query += " ORDER BY updated_at DESC"

            cursor.execute(query)
            for row in cursor.fetchall():
                records.append(dict(row))

        # 猎聘记录（字段映射不同）
        if platform in ['all', 'liepin']:
            query = """
                SELECT
                    'liepin' as platform,
                    comp_name as company_name,
                    job_title as job_name,
                    job_salary_text as salary,
                    job_area as location,
                    job_exp_req as experience,
                    job_edu_req as degree,
                    hr_name,
                    CASE WHEN delivered = 1 THEN '已投递' ELSE '未投递' END as delivery_status,
                    job_link as job_url,
                    create_time as created_at,
                    update_time as updated_at
                FROM liepin_data
            """
            if status != 'all':
                if status == '已投递':
                    query += " WHERE delivered = 1"
                elif status == '未投递':
                    query += " WHERE delivered = 0"
                else:
                    query += " WHERE 1=0"  # 猎聘没有'已过滤'状态
            query += " ORDER BY update_time DESC"

            cursor.execute(query)
            for row in cursor.fetchall():
                records.append(dict(row))

        conn.close()

        # 按更新时间排序并限制数量
        records.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        records = records[:limit]

        return jsonify({
            'success': True,
            'records': records,
            'count': len(records)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'获取记录失败: {str(e)}'}), 500


@status_tracking_bp.route('/delivery/stats/stream')
def stream_delivery_stats():
    """SSE实时推送投递统计数据"""
    def generate():
        last_stats = None
        while True:
            try:
                if not FUNC2_DB_PATH.exists():
                    yield f"data: {json.dumps({'error': '数据库不存在'}, ensure_ascii=False)}\n\n"
                    time.sleep(3)
                    continue

                conn = get_func2_connection()
                cursor = conn.cursor()

                # Boss直聘统计
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN delivery_status = '已投递' THEN 1 ELSE 0 END) as delivered,
                        SUM(CASE WHEN delivery_status = '已过滤' THEN 1 ELSE 0 END) as filtered,
                        SUM(CASE WHEN delivery_status = '未投递' THEN 1 ELSE 0 END) as pending
                    FROM boss_data
                """)
                boss_stats = cursor.fetchone()

                # 猎聘统计
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN delivered = 1 THEN 1 ELSE 0 END) as delivered,
                        0 as filtered,
                        SUM(CASE WHEN delivered = 0 THEN 1 ELSE 0 END) as pending
                    FROM liepin_data
                """)
                liepin_stats = cursor.fetchone()

                conn.close()

                # 构建统计数据
                stats = {
                    'total': (boss_stats['total'] or 0) + (liepin_stats['total'] or 0),
                    'delivered': (boss_stats['delivered'] or 0) + (liepin_stats['delivered'] or 0),
                    'filtered': (boss_stats['filtered'] or 0) + (liepin_stats['filtered'] or 0),
                    'pending': (boss_stats['pending'] or 0) + (liepin_stats['pending'] or 0),
                    'boss': {
                        'total': boss_stats['total'] or 0,
                        'delivered': boss_stats['delivered'] or 0,
                        'filtered': boss_stats['filtered'] or 0,
                        'pending': boss_stats['pending'] or 0
                    },
                    'liepin': {
                        'total': liepin_stats['total'] or 0,
                        'delivered': liepin_stats['delivered'] or 0,
                        'filtered': liepin_stats['filtered'] or 0,
                        'pending': liepin_stats['pending'] or 0
                    },
                    'timestamp': time.time()
                }

                # 只有数据变化时才推送（避免重复推送）
                if stats != last_stats:
                    payload = json.dumps({'success': True, 'stats': stats}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                    last_stats = stats

                time.sleep(3)  # 每3秒检查一次

            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
                time.sleep(3)

    return Response(generate(), mimetype='text/event-stream')
