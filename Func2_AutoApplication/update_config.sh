#!/bin/bash
# Boss直聘配置修改脚本

DB_PATH="./db/getjobs.db"

echo "=========================================="
echo "  Boss直聘配置修改工具"
echo "=========================================="

# 显示当前配置
echo -e "\n📋 当前配置："
sqlite3 "$DB_PATH" "SELECT
  '关键词: ' || keywords,
  '城市: ' || city_code,
  '薪资: ' || salary,
  '经验: ' || experience
FROM boss_config WHERE id = 1;"

echo -e "\n"
read -p "是否要修改配置？(y/n): " answer

if [ "$answer" != "y" ]; then
    echo "未做任何修改"
    exit 0
fi

# 修改关键词
echo -e "\n1️⃣ 修改职位关键词"
read -p "输入关键词（逗号分隔，如：数据分析,Python,机器学习）: " keywords
if [ ! -z "$keywords" ]; then
    # 将逗号分隔转换为JSON数组
    keywords_json="[\"$(echo $keywords | sed 's/,/","/g')\"]"
    sqlite3 "$DB_PATH" "UPDATE boss_config SET keywords = '$keywords_json' WHERE id = 1;"
    echo "✓ 关键词已更新"
fi

# 修改城市
echo -e "\n2️⃣ 修改城市"
read -p "输入城市（如：北京、上海、深圳）: " city
if [ ! -z "$city" ]; then
    sqlite3 "$DB_PATH" "UPDATE boss_config SET city_code = '$city' WHERE id = 1;"
    echo "✓ 城市已更新"
fi

# 修改薪资
echo -e "\n3️⃣ 修改薪资范围"
read -p "输入薪资范围（如：15-30K）: " salary
if [ ! -z "$salary" ]; then
    sqlite3 "$DB_PATH" "UPDATE boss_config SET salary = '[$salary]' WHERE id = 1;"
    echo "✓ 薪资范围已更新"
fi

# 修改期望薪资
echo -e "\n4️⃣ 修改期望薪资（用于过滤）"
read -p "最低期望（单位K，如：15）: " min_salary
read -p "最高期望（单位K，如：30）: " max_salary
if [ ! -z "$min_salary" ] && [ ! -z "$max_salary" ]; then
    sqlite3 "$DB_PATH" "UPDATE boss_config SET expected_salary_min = $min_salary, expected_salary_max = $max_salary WHERE id = 1;"
    echo "✓ 期望薪资已更新"
fi

# 修改打招呼语
echo -e "\n5️⃣ 修改打招呼语"
read -p "输入打招呼语（直接回车跳过）: " sayhi
if [ ! -z "$sayhi" ]; then
    sqlite3 "$DB_PATH" "UPDATE boss_config SET say_hi = '$sayhi' WHERE id = 1;"
    echo "✓ 打招呼语已更新"
fi

# 显示最终配置
echo -e "\n=========================================="
echo "✅ 配置已更新！"
echo "=========================================="
sqlite3 "$DB_PATH" "SELECT
  '关键词: ' || keywords,
  '城市: ' || city_code,
  '薪资: ' || salary,
  '期望: ' || expected_salary_min || 'K-' || expected_salary_max || 'K',
  '打招呼: ' || substr(say_hi, 1, 30) || '...'
FROM boss_config WHERE id = 1;"

echo -e "\n提示：修改配置后，请重新启动投递任务"
