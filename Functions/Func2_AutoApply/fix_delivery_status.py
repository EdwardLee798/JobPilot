#!/usr/bin/env python3
"""
手动修复投递状态的工具
用于将实际已投递但数据库状态为"未投递"的记录更新为"已投递"
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "getjobs.db"


def show_pending_jobs():
    """显示所有未投递的岗位"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, company_name, job_name, salary, location, delivery_status, created_at
        FROM boss_data
        WHERE delivery_status = '未投递' OR delivery_status IS NULL OR delivery_status = ''
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("\n没有未投递的记录\n")
        return []

    print(f"\n共有 {len(rows)} 条未投递记录：")
    print(f"\n{'ID':<6} {'公司名称':<25} {'职位名称':<35} {'薪资':<15} {'地点':<10}")
    print("-" * 100)

    for row in rows:
        row_id = row[0]
        company = (row[1] or '')[:23]
        job = (row[2] or '')[:33]
        salary = (row[3] or '')[:13]
        location = (row[4] or '')[:8]
        print(f"{row_id:<6} {company:<25} {job:<35} {salary:<15} {location:<10}")

    print()
    return rows


def update_to_delivered(job_ids):
    """批量更新为已投递状态"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(job_ids))
    cursor.execute(f"""
        UPDATE boss_data
        SET delivery_status = '已投递',
            updated_at = datetime('now', 'localtime')
        WHERE id IN ({placeholders})
    """, job_ids)

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated


def update_all_pending():
    """将所有未投递的记录更新为已投递"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE boss_data
        SET delivery_status = '已投递',
            updated_at = datetime('now', 'localtime')
        WHERE delivery_status = '未投递' OR delivery_status IS NULL OR delivery_status = ''
    """)

    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return updated


def main():
    print("=" * 60)
    print("Boss直聘投递状态修复工具")
    print("=" * 60)

    # 显示所有未投递的记录
    pending_jobs = show_pending_jobs()

    if not pending_jobs:
        return

    print("请选择操作：")
    print("1. 按ID批量更新（例如：1,2,3,5-8）")
    print("2. 将所有未投递记录更新为已投递")
    print("3. 取消")

    choice = input("\n请输入选项 (1/2/3): ").strip()

    if choice == '1':
        print("\n输入要更新的ID，支持格式：")
        print("  - 单个ID: 5")
        print("  - 多个ID: 1,2,3,5")
        print("  - 范围: 5-10")
        print("  - 混合: 1,3,5-8,10")

        id_input = input("\n请输入ID: ").strip()

        # 解析ID输入
        job_ids = []
        for part in id_input.split(','):
            part = part.strip()
            if '-' in part:
                # 范围格式
                start, end = part.split('-')
                job_ids.extend(range(int(start), int(end) + 1))
            else:
                # 单个ID
                job_ids.append(int(part))

        if job_ids:
            confirm = input(f"\n确认将 {len(job_ids)} 条记录更新为已投递？(y/n): ")
            if confirm.lower() == 'y':
                updated = update_to_delivered(job_ids)
                print(f"\n✓ 已成功更新 {updated} 条记录为已投递状态\n")
            else:
                print("\n已取消\n")

    elif choice == '2':
        confirm = input(f"\n确认将所有 {len(pending_jobs)} 条未投递记录更新为已投递？(y/n): ")
        if confirm.lower() == 'y':
            updated = update_all_pending()
            print(f"\n✓ 已成功更新 {updated} 条记录为已投递状态\n")
        else:
            print("\n已取消\n")

    else:
        print("\n已取消\n")


if __name__ == "__main__":
    main()
