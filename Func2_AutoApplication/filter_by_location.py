#!/usr/bin/env python3
"""
按地点筛选已投递记录
只保留指定城市的已投递记录，删除其他城市的
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "db" / "getjobs.db"


def show_delivered_by_location():
    """显示已投递记录按城市统计"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n========== Boss直聘已投递记录（按城市） ==========")
    cursor.execute("""
        SELECT location, COUNT(*) as count
        FROM boss_data
        WHERE delivery_status = '已投递'
        GROUP BY location
        ORDER BY count DESC
    """)
    boss_by_city = cursor.fetchall()
    for city, count in boss_by_city:
        print(f"  {city}: {count}条")

    print("\n========== 猎聘已投递记录（按城市） ==========")
    cursor.execute("""
        SELECT job_area, COUNT(*) as count
        FROM liepin_data
        WHERE delivered = 1
        GROUP BY job_area
        ORDER BY count DESC
    """)
    liepin_by_city = cursor.fetchall()
    for city, count in liepin_by_city:
        print(f"  {city}: {count}条")

    conn.close()
    print()


def preview_deletion(city):
    """预览将要删除的记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Boss直聘非指定城市的记录
    cursor.execute("""
        SELECT company_name, job_name, location
        FROM boss_data
        WHERE delivery_status = '已投递'
        AND location NOT LIKE ?
    """, (f'%{city}%',))
    boss_to_delete = cursor.fetchall()

    # 猎聘非指定城市的记录
    cursor.execute("""
        SELECT comp_name, job_title, job_area
        FROM liepin_data
        WHERE delivered = 1
        AND job_area NOT LIKE ?
    """, (f'%{city}%',))
    liepin_to_delete = cursor.fetchall()

    conn.close()

    if not boss_to_delete and not liepin_to_delete:
        print(f"\n✓ 所有已投递记录都在{city}，无需删除\n")
        return False

    print(f"\n========== 将要删除的记录（非{city}） ==========\n")

    if boss_to_delete:
        print(f"【Boss直聘】将删除 {len(boss_to_delete)} 条：")
        for company, job, location in boss_to_delete[:10]:
            print(f"  - {company} | {job} | {location}")
        if len(boss_to_delete) > 10:
            print(f"  ... 还有 {len(boss_to_delete) - 10} 条")
        print()

    if liepin_to_delete:
        print(f"【猎聘】将删除 {len(liepin_to_delete)} 条：")
        for company, job, location in liepin_to_delete[:10]:
            print(f"  - {company} | {job} | {location}")
        if len(liepin_to_delete) > 10:
            print(f"  ... 还有 {len(liepin_to_delete) - 10} 条")
        print()

    print(f"合计将删除：{len(boss_to_delete) + len(liepin_to_delete)} 条记录\n")
    return True


def delete_non_city_records(city):
    """删除非指定城市的已投递记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 删除Boss直聘非指定城市的记录
    cursor.execute("""
        DELETE FROM boss_data
        WHERE delivery_status = '已投递'
        AND location NOT LIKE ?
    """, (f'%{city}%',))
    boss_deleted = cursor.rowcount

    # 删除猎聘非指定城市的记录
    cursor.execute("""
        DELETE FROM liepin_data
        WHERE delivered = 1
        AND job_area NOT LIKE ?
    """, (f'%{city}%',))
    liepin_deleted = cursor.rowcount

    conn.commit()
    conn.close()

    return boss_deleted, liepin_deleted


def main():
    print("=" * 60)
    print("按地点筛选已投递记录")
    print("=" * 60)

    # 显示当前统计
    show_delivered_by_location()

    city = input("请输入要保留的城市名称（例如：深圳）: ").strip()

    if not city:
        print("\n城市名称不能为空！")
        return

    # 预览将要删除的记录
    has_records_to_delete = preview_deletion(city)

    if not has_records_to_delete:
        return

    confirm = input(f"确认删除非{city}的已投递记录？(y/n): ")

    if confirm.lower() == 'y':
        boss_deleted, liepin_deleted = delete_non_city_records(city)

        print(f"\n✓ 删除完成：")
        print(f"  - Boss直聘：{boss_deleted} 条")
        print(f"  - 猎聘：{liepin_deleted} 条")
        print(f"  - 合计：{boss_deleted + liepin_deleted} 条")
        print(f"\n现在只保留{city}的已投递记录\n")

        # 显示删除后的统计
        show_delivered_by_location()
    else:
        print("\n已取消\n")


if __name__ == "__main__":
    main()
