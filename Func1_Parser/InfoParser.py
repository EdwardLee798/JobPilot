

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
    聚合简历信息（核心函数）

    输入：当前档案 + 新输入
    输出：更新后的档案 + 缺失字段 + 分析 + 下一个问题
    由 LLM 直接判断用户是否表达了终止意图（user_stop_intent: bool），
    以及当前信息是否足够生成简历（can_finalize: bool）。
    """
    system_msg = (
        "你是一名专业的简历信息收集助手。"
        "你的任务是：基于当前的简历档案，合并用户的新输入，"
        "识别仍然缺失的关键信息，判断是否可以结束信息收集，并提出下一个问题。"
        "你需要根据用户的自然语言理解其意图：如果用户表示“就这些了”“没有更多信息”"
        "或其他表明想结束补充的说法，你需要将 user_stop_intent 设为 true。"
        "user_stop_intent 必须完全基于你对用户自然语言的语义理解，而不是机械匹配关键词。"
    )

    user_prompt = f"""
[当前简历档案]
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

[用户本轮输入]
{new_input_text}

请完成以下任务：
1. 从新输入中提取并更新档案信息（姓名、联系方式、教育经历、工作/实习经历、技能、活动、证书等）。
2. 保留已有的正确信息，如果新信息更准确或更完整则更新。
3. 根据更新后的档案，判断当前信息是否“已经足够生成一份可用的简历”（而不是完美简历）。
   - 判断时可以考虑但不限于以下因素：
     - 是否有姓名。
     - 是否有至少一种有效联系方式（邮箱/手机/微信）。
     - 是否有至少一条教育经历或工作/实习经历。
     - 是否有期望职位方向或个人简介（可以从 summary / headline / 经验中推断）。
4. 识别仍然缺失的重要字段（must_have）和可选字段（nice_to_have）。
   - must_have：建议继续补充，否则简历质量明显受影响的字段。
   - nice_to_have：有会更好，但缺失也能生成简历。
5. 你需要根据用户的自然语言，判断本轮用户是否明确表达了“想结束补充”的意图：
   - 例如“就这些了”“没有更多信息了”“先这样吧”“帮我生成简历”等，
     以及语义等价的表达（不限于这些例子）。
   - 这是一个语义层面的判断，请综合上下文，不要只做关键词匹配。
6. 根据以上分析，决定是否还需要继续追问用户：
   - 如果仍然建议继续补充：给出一个友好、具体的 next_question。
   - 如果已经可以结束，或者用户明确表达要结束：不要再强行让用户补充，可以将 next_question 设为空字符串或给出简短的总结性话语。

请严格输出JSON格式（不要有额外文字、解释或前后缀）：
{{
  "updated_profile": {{"完整的简历档案，结构与输入保持一致"}},
  "missing_fields": {{
    "must_have": ["字段A", "字段B"],
    "nice_to_have": ["字段C"]
  }},
  "analysis": {{
    "can_finalize": true,
    "reason": "说明为什么可以/不可以结束（例如：联系方式缺失、至少有一段教育/工作经历等）",
    "user_stop_intent": false
  }},
  "next_question": "如果需要继续补充时，要问的下一个问题；如果可以结束或用户要结束，可以为空字符串或简短总结。"
}}
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

    # 提取JSON
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"模型返回内容无法解析为JSON：{raw}")

    data = json.loads(raw[start:end])
    return data

# 4. 一个最简单的 CLI 交互循环示例 

def build_profile_interactively():
    """
    简单终端版 Demo：
    - 用户可以输入文字；
    - 也可以在每一轮输入一个文件路径（报告/论文/证明等），自动解析并融入档案；
    - 终止逻辑：
        * LLM 判断 can_finalize == True，认为信息已足够，可提示用户确认结束；
        * 或 LLM 判断 user_stop_intent == True（用户自然语言表示不再补充），则直接结束。
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
        missing = result.get("missing_fields", {}) or {}
        must_have = missing.get("must_have", []) or []
        nice_to_have = missing.get("nice_to_have", []) or []
        analysis = result.get("analysis", {}) or {}

        can_finalize = bool(analysis.get("can_finalize", False))
        user_stop = bool(analysis.get("user_stop_intent", False))
        reason = analysis.get("reason", "")

        print("\n当前仍缺的重要字段(must_have)：", must_have)
        print("当前可选补充字段(nice_to_have)：", nice_to_have)
        if reason:
            print("模型分析：", reason)

        # 用户自然语言终止：LLM 判断 user_stop_intent == True
        if user_stop:
            print("\n检测到你表示不再补充信息，我会基于目前的信息生成简历。")
            break

        # 模型认为信息已经足够，可以结束，由用户确认
        if can_finalize:
            print("\n根据当前信息，已经可以生成一份可用的简历。")
            confirm = input("是否结束并生成 JSON 档案？(y/n)：").strip().lower()
            if confirm == "y":
                break

        # 继续对话：下一轮要问的问题
        next_question = result.get("next_question", "请继续补充你认为重要的经历或技能。")
        if not next_question.strip():
            # 如果模型没有给出明确下一问题，则给一个兜底提示
            next_question = "如果你还有想补充的经历、技能或成就，可以继续告诉我。"

    # 结束：保存 JSON
    save_path = input("请输入最终 JSON 保存路径（默认 output_profile.json）：").strip()
    if not save_path:
        save_path = "output_profile.json"

    save_resume_json(profile, save_path)
    print(f"\n已保存结构化档案到：{save_path}")


if __name__ == "__main__":
    build_profile_interactively()
    