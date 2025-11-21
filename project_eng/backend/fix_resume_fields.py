#!/usr/bin/env python3
"""
修复已存在的简历JSON文件字段
将 company -> name, title -> position，并生成 period 字段
"""

import json
import os
from pathlib import Path

def normalize_experience_fields(experience_list):
    """统一工作经历字段"""
    normalized = []
    for exp in experience_list:
        if not isinstance(exp, dict):
            continue

        normalized_item = {}

        # 复制所有字段
        for key, value in exp.items():
            # 跳过空值和undefined
            if value and value != 'undefined' and value != 'null' and str(value).strip():
                normalized_item[key] = value

        # 字段映射：company -> name
        if 'company' in normalized_item:
            normalized_item['name'] = normalized_item['company']
            if 'company' in normalized_item:
                del normalized_item['company']

        # 字段映射：title -> position
        if 'title' in normalized_item:
            normalized_item['position'] = normalized_item['title']
            if 'title' in normalized_item:
                del normalized_item['title']

        # 生成period字段
        if 'start_date' in normalized_item and 'end_date' in normalized_item:
            start = str(normalized_item.get('start_date', '')).strip()
            end = str(normalized_item.get('end_date', '')).strip()
            if start and end:
                normalized_item['period'] = f"{start} - {end}"
            elif start:
                normalized_item['period'] = f"{start} - 至今"
            elif end:
                normalized_item['period'] = f"至 {end}"

        # 确保必需字段存在
        if 'name' not in normalized_item or not normalized_item.get('name'):
            normalized_item['name'] = '某公司'
        if 'position' not in normalized_item or not normalized_item.get('position'):
            normalized_item['position'] = '职位名称'
        if 'period' not in normalized_item:
            normalized_item['period'] = '时间未知'

        normalized.append(normalized_item)

    return normalized


def fix_resume_file(file_path):
    """修复单个简历文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否有experience字段需要修复
        if 'experience' in data and isinstance(data['experience'], list):
            # 检查是否有company或title字段
            needs_fix = any(
                'company' in exp or 'title' in exp
                for exp in data['experience']
                if isinstance(exp, dict)
            )

            if needs_fix:
                print(f"修复文件: {file_path.name}")
                data['experience'] = normalize_experience_fields(data['experience'])

                # 备份原文件
                backup_path = file_path.with_suffix('.json.bak')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  已备份到: {backup_path.name}")

                # 保存修复后的文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  ✓ 修复完成")
                return True
            else:
                print(f"跳过文件（无需修复）: {file_path.name}")
                return False
        else:
            print(f"跳过文件（没有工作经历）: {file_path.name}")
            return False

    except Exception as e:
        print(f"处理文件失败 {file_path.name}: {e}")
        return False


def main():
    """主函数"""
    # 简历目录
    resume_dir = Path(__file__).parent / 'data' / 'resumes'

    if not resume_dir.exists():
        print(f"错误：简历目录不存在: {resume_dir}")
        return

    print(f"开始扫描简历目录: {resume_dir}")
    print("=" * 60)

    # 统计
    total_files = 0
    fixed_files = 0

    # 遍历所有JSON文件
    for json_file in resume_dir.glob('*.json'):
        # 跳过备份文件
        if json_file.suffix == '.bak':
            continue

        total_files += 1
        if fix_resume_file(json_file):
            fixed_files += 1

    print("=" * 60)
    print(f"\n总结:")
    print(f"  扫描文件: {total_files}")
    print(f"  修复文件: {fixed_files}")
    print(f"  跳过文件: {total_files - fixed_files}")
    print("\n✓ 所有文件处理完成！")


if __name__ == '__main__':
    main()
