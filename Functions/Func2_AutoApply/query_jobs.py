#!/usr/bin/env python3
"""
便捷查询Func2投递记录的工具脚本
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "getjobs.db"


def query_by_status(status=None, limit=20):
    """按投递状态查询"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if status:
        query = """
            SELECT company_name, job_name, salary, location, delivery_status, created_at
            FROM boss_data
            WHERE delivery_status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        cursor.execute(query, (status, limit))
    else:
        query = """
            SELECT company_name, job_name, salary, location, delivery_status, created_at
            FROM boss_data
            ORDER BY created_at DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))

    rows = cursor.fetchall()
    conn.close()
    

    print(f"\n{'公司名称':<20} {'职位名称':<30} {'薪资':<15} {'地点':<10} {'状态':<10} {'时间':<20}")
    print("-" * 120)

    for row in rows:
        company = (row[0] or '')[:18]
        job = (row[1] or '')[:28]
        salary = (row[2] or '')[:13]
        location = (row[3] or '')[:8]
        status_str = row[4] or ''
        time_str = (row[5] or '')[:19]
        print(f"{company:<20} {job:<30} {salary:<15} {location:<10} {status_str:<10} {time_str:<20}")

    print(f"\n共 {len(rows)} 条记录\n")


def get_statistics():
    """获取统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM boss_data")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM boss_data WHERE delivery_status = '已投递'")
    delivered = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM boss_data WHERE delivery_status = '已过滤'")
    filtered = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM boss_data WHERE delivery_status = '未投递' OR delivery_status IS NULL OR delivery_status = ''")
    pending = cursor.fetchone()[0]

    conn.close()

    print("\n========== 投递统计 ==========")
    print(f"总记录数: {total}")
    print(f"已投递: {delivered}")
    print(f"已过滤: {filtered}")
    print(f"未投递: {pending}")
    print("==============================\n")


def clear_old_records(keep_days=7):
    """清理旧记录（保留最近N天）"""
    from datetime import datetime, timedelta

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 计算截止日期
    cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime('%Y-%m-%d')

    # 删除旧的未投递记录
    cursor.execute("""
        DELETE FROM boss_data
        WHERE (delivery_status = '未投递' OR delivery_status IS NULL OR delivery_status = '')
        AND created_at < ?
    """, (cutoff_date,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"\n已清理 {deleted} 条旧的未投递记录（保留最近{keep_days}天）\n")


def main():
    if len(sys.argv) < 2:
        print("使用说明:")
        print("  python query_jobs.py stats           - 查看统计信息")
        print("  python query_jobs.py all [数量]      - 查看所有记录（默认20条）")
        print("  python query_jobs.py delivered [数量] - 查看已投递记录")
        print("  python query_jobs.py filtered [数量]  - 查看已过滤记录")
        print("  python query_jobs.py pending [数量]   - 查看未投递记录")
        print("  python query_jobs.py clean [天数]    - 清理旧的未投递记录（默认保留7天）")
        sys.exit(1)

    command = sys.argv[1]

    if command == "stats":
        get_statistics()

    elif command == "all":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        query_by_status(None, limit)

    elif command == "delivered":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        query_by_status("已投递", limit)

    elif command == "filtered":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        query_by_status("已过滤", limit)

    elif command == "pending":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        query_by_status("未投递", limit)

    elif command == "clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        get_statistics()
        confirm = input(f"确认清理{days}天前的未投递记录？(y/n): ")
        if confirm.lower() == 'y':
            clear_old_records(days)
            get_statistics()
        else:
            print("已取消")

    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
