

import os
import json
from openai import OpenAI

# 复用现有的文件解析逻辑
from CVParser import parse_resume, save_resume_json

# 1. 初始化 LLM 客户端

client = OpenAI(
    api_key="sk-f25e9dbbe22d4c53afc2d5da4a7ad7ca",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 2. 统一的简历 JSON 模板 

def init_empty_profile() -> dict:
    """按照原有的简历 Schema，初始化一个空档案"""
    return {
        "user_id": "",
        "name": "",
        "headline": "",
        "contacts": {
            "email": "",
            "phone": "",
            "wechat": "",
            "github": ""
        },
        "summary": "",
        "education": [],
        "experience": [],
        "skills": [],
        "activities": [],
        "certifications": []
    }

# 3. 单轮聚合：老 JSON + 新输入 → 新 JSON + 下一问题 

def aggregate_profile(current_profile: dict, new_input_text: str) -> dict:
    """
    输入：
        current_profile: 当前已经收集到的完整 JSON
        new_input_text: 本轮新信息（用户文字 + 文档解析文本拼在一起）
    输出：
        {
          "updated_profile": {...},
          "missing_fields": {
            "must_have": [...],
            "nice_to_have": [...]
          },
          "next_question": "..."
        }
    """

    system_msg = (
        "你是一名简历信息聚合助手。"
        "你的任务是：在已有的用户档案 JSON 基础上，合并新输入中的信息，"
        "并告诉还缺哪些重要字段，以及下一步要问什么问题。"
    )

    user_prompt = f"""
[当前用户档案 JSON]
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

[新输入文本]
{new_input_text}

请你根据以上信息，完成以下任务：
1. 尽量从新输入中补全或纠正档案中的字段（如姓名、联系方式、教育经历、实习/项目/科研/工作经历、技能、活动、证书等）。
2. 不要删掉已有的正确信息；如果新信息更具体或更可信，可以覆盖旧值。
3. 标出当前档案中仍然缺失的重要字段（must_have），以及可选但有助于制作更好简历的字段（nice_to_have）。
4. 给出下一轮应该向用户提出的问题，问题要清晰地说明：
   - 还缺的关键信息是什么；
   - 用户可以选择用“文字回答”，或者“上传相关文档（如项目报告、论文、证明材料）”。

请严格输出一个 JSON 对象，格式如下（字段名必须一致）：
{{
  "updated_profile": <完整的用户档案 JSON>,
  "missing_fields": {{
    "must_have": ["字段A", "字段B", ...],
    "nice_to_have": ["字段C", ...]
  }},
  "next_question": "用中文给用户提的下一问题"
}}
不要输出任何多余说明或注释。
"""

    resp = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    raw = resp.choices[0].message.content.strip()

    # 防御性：只截取第一个合法 JSON 段
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == -1:
        raise ValueError(f"模型返回内容无法解析为 JSON：{raw}")

    data = json.loads(raw[start:end])
    return data

# 4. 一个最简单的 CLI 交互循环示例 

def build_profile_interactively():
    """
    简单终端版 Demo：
    - 用户可以输入文字；
    - 也可以在每一轮输入一个文件路径（报告/论文/证明等），自动解析并融入档案；
    - 当缺失的 must_have 字段为空时，认为收集完成。
    """

    profile = init_empty_profile()

    print("【交互建档模式】")
    print("说明：你可以直接用文字描述自己的情况，也可以在某一轮输入文档路径（PDF/DOCX/TXT），我会自动抽取信息。")
    print("例如：/path/to/project_report.pdf\n")

    # 第一轮先主动问一个开场问题
    next_question = "先简单介绍一下你自己吧，比如姓名、目前身份（学生/在职）、所在城市，以及你手头有哪些相关文档可以提供？"

    while True:
        print(f"\n助手：{next_question}")
        user_text = input("你：").strip()

        # 让用户有机会在这一轮提供一个文件路径（可选）
        file_path = input("如果本轮有相关文件路径（PDF/DOCX/TXT），请输入；没有请直接回车：").strip()
        file_text = ""
        if file_path:
            try:
                file_text = parse_resume(file_path)
                print(f"已解析文件，长度约 {len(file_text)} 字。")
            except Exception as e:
                print(f"解析文件失败：{e}")

        combined_text = user_text + "\n\n[本轮文档内容]\n" + file_text

        # 调用聚合函数
        try:
            result = aggregate_profile(profile, combined_text)
        except Exception as e:
            print(f"调用聚合模型失败：{e}")
            continue

        profile = result.get("updated_profile", profile)
        missing = result.get("missing_fields", {})
        must_have = missing.get("must_have", [])
        nice_to_have = missing.get("nice_to_have", [])

        print("\n当前仍缺的重要字段(must_have)：", must_have)
        print("当前可选补充字段(nice_to_have)：", nice_to_have)

        # 停止条件：没有 must_have 了，认为关键信息已齐
        if not must_have:
            print("\n关键信息已经基本齐全。")
            confirm = input("是否结束并生成 JSON 档案？(y/n)：").strip().lower()
            if confirm == "y":
                break

        # 下一轮要问的问题
        next_question = result.get("next_question", "请继续补充你认为重要的经历或技能。")

    # 结束：保存 JSON
    save_path = input("请输入最终 JSON 保存路径（默认 output_profile.json）：").strip()
    if not save_path:
        save_path = "output_profile.json"

    save_resume_json(profile, save_path)
    print(f"\n已保存结构化档案到：{save_path}")


if __name__ == "__main__":
    build_profile_interactively()
