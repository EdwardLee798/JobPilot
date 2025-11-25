#!/usr/bin/env python3
"""
同步投递记录到状态跟踪模块的独立脚本
"""
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# 数据库路径
FUNC2_DB = Path(__file__).parent / "db" / "getjobs.db"
TRACKING_DB = Path(__file__).parent.parent / "project_eng" / "backend" / "data" / "database" / "tracking.db"


def parse_timestamp(created_at):
    """解析时间戳"""
    try:
        if created_at:
            if isinstance(created_at, str):
                # 尝试解析多种时间格式
                for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(created_at, fmt)
                        return dt.timestamp()
                    except:
                        continue
            else:
                return float(created_at) if created_at else time.time()
        return time.time()
    except:
        return time.time()


def get_delivered_jobs():
    """获取已投递的岗位"""
    conn = sqlite3.connect(str(FUNC2_DB))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT job_name, company_name, job_description, delivery_status, created_at
        FROM boss_data
        WHERE delivery_status = '已投递'
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        jobs.append({
            'job_name': row[0] or '',
            'company_name': row[1] or '',
            'job_description': row[2] or '',
            'delivery_status': row[3] or '',
            'created_at': row[4] or ''
        })

    return jobs


def get_pending_jobs():
    """获取待投递的岗位"""
    conn = sqlite3.connect(str(FUNC2_DB))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT job_name, company_name, job_description, salary, location, created_at
        FROM boss_data
        WHERE delivery_status = '未投递' OR delivery_status IS NULL OR delivery_status = ''
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        jobs.append({
            'job_name': row[0] or '',
            'company_name': row[1] or '',
            'job_description': row[2] or '',
            'salary': row[3] or '',
            'location': row[4] or '',
            'created_at': row[5] or ''
        })

    return jobs


def sync_to_tracking(sync_pending=True):
    """同步到状态跟踪模块"""
    # 确保tracking数据库目录存在
    TRACKING_DB.parent.mkdir(parents=True, exist_ok=True)

    # 连接状态跟踪数据库
    tracking_conn = sqlite3.connect(str(TRACKING_DB))
    tracking_cursor = tracking_conn.cursor()

    delivered_synced = 0
    pending_synced = 0
    skipped_count = 0

    print("\n开始同步...")

    # 1. 同步已投递的岗位
    print("\n[1/2] 同步已投递记录...")
    delivered_jobs = get_delivered_jobs()
    print(f"找到 {len(delivered_jobs)} 条已投递记录")

    for job in delivered_jobs:
        job_title = job.get('job_name', '').strip()
        company_name = job.get('company_name', '').strip()
        job_description = job.get('job_description', '').strip()
        created_at = job.get('created_at', '')

        if not job_title or not company_name:
            skipped_count += 1
            continue

        # 检查是否已存在
        tracking_cursor.execute('''
            SELECT job_id FROM job_summary
            WHERE job_title = ? AND company_name = ?
        ''', (job_title, company_name))

        existing = tracking_cursor.fetchone()
        if existing:
            skipped_count += 1
            continue

        # 插入job_summary
        tracking_cursor.execute('''
            INSERT INTO job_summary (job_title, company_name, job_desc, tracking_method)
            VALUES (?, ?, ?, ?)
        ''', (job_title, company_name, job_description, 'Boss直聘'))

        job_id = tracking_cursor.lastrowid

        # 解析时间戳
        event_time = parse_timestamp(created_at)

        # 插入状态：已申请
        tracking_cursor.execute('''
            INSERT INTO application_status (job_id, status_update, event_time)
            VALUES (?, ?, ?)
        ''', (job_id, '已申请', event_time))

        delivered_synced += 1
        print(f"  ✓ {company_name} - {job_title}")

    # 2. 同步待投递的岗位
    if sync_pending:
        print(f"\n[2/2] 同步待投递记录...")
        pending_jobs = get_pending_jobs()
        print(f"找到 {len(pending_jobs)} 条待投递记录")

        for job in pending_jobs:
            job_title = job.get('job_name', '').strip()
            company_name = job.get('company_name', '').strip()
            job_description = job.get('job_description', '').strip()
            salary = job.get('salary', '').strip()
            location = job.get('location', '').strip()
            created_at = job.get('created_at', '')

            if not job_title or not company_name:
                skipped_count += 1
                continue

            # 检查是否已存在
            tracking_cursor.execute('''
                SELECT job_id FROM job_summary
                WHERE job_title = ? AND company_name = ?
            ''', (job_title, company_name))

            existing = tracking_cursor.fetchone()
            if existing:
                skipped_count += 1
                continue

            # 拼接更详细的描述
            full_description = f"薪资：{salary}\n地点：{location}\n\n{job_description}"

            # 插入job_summary
            tracking_cursor.execute('''
                INSERT INTO job_summary (job_title, company_name, job_desc, tracking_method)
                VALUES (?, ?, ?, ?)
            ''', (job_title, company_name, full_description, 'Boss直聘'))

            job_id = tracking_cursor.lastrowid

            # 解析时间戳
            event_time = parse_timestamp(created_at)

            # 插入状态：待投递
            tracking_cursor.execute('''
                INSERT INTO application_status (job_id, status_update, event_time)
                VALUES (?, ?, ?)
            ''', (job_id, '待投递', event_time))

            pending_synced += 1
            print(f"  ✓ {company_name} - {job_title} ({salary} | {location})")

    tracking_conn.commit()
    tracking_conn.close()

    total_synced = delivered_synced + pending_synced

    print(f"\n" + "=" * 60)
    print("同步完成！")
    print("=" * 60)
    print(f"已投递记录：{delivered_synced} 条")
    print(f"待投递记录：{pending_synced} 条")
    print(f"跳过重复：{skipped_count} 条")
    print(f"总计同步：{total_synced} 条")
    print("=" * 60 + "\n")

    return {
        'delivered_synced': delivered_synced,
        'pending_synced': pending_synced,
        'skipped_count': skipped_count,
        'total_synced': total_synced
    }


def main():
    print("=" * 60)
    print("同步投递记录到状态跟踪模块")
    print("=" * 60)

    # 检查数据库是否存在
    if not FUNC2_DB.exists():
        print(f"\n错误：找不到Func2数据库: {FUNC2_DB}")
        return

    # 执行同步
    try:
        result = sync_to_tracking(sync_pending=True)

        if result['total_synced'] > 0:
            print("✓ 所有记录已成功同步到状态跟踪模块！")
            print(f"  数据库位置：{TRACKING_DB}\n")
        else:
            print("ℹ 没有需要同步的新记录\n")

    except Exception as e:
        print(f"\n✗ 同步失败: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
