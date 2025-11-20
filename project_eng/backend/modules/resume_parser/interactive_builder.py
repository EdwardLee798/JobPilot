"""
交互式简历生成器 - 基于对话的简历信息收集
跨平台支持
"""

import os
import json
import sys
from pathlib import Path
from openai import OpenAI

# 从Func1复用解析逻辑 - 使用相对路径（跨平台）
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent.parent.parent.parent
FUNC1_DIR = PROJECT_ROOT / "Func1_Parser"

# 动态添加Func1路径
sys.path.insert(0, str(FUNC1_DIR))
from CVParser import parse_resume

# 初始化LLM客户端
client = OpenAI(
    api_key="sk-f25e9dbbe22d4c53afc2d5da4a7ad7ca",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def init_empty_profile() -> dict:
    """初始化空的简历档案"""
    return {
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


def aggregate_profile(current_profile: dict, new_input_text: str) -> dict:
    """
    聚合简历信息
    输入：当前档案 + 新输入
    输出：更新后的档案 + 缺失字段 + 下一个问题
    """
    system_msg = (
        "你是一名专业的简历信息收集助手。"
        "你的任务是：基于当前的简历档案，合并用户的新输入，"
        "识别仍然缺失的关键信息，并提出下一个问题。"
    )

    user_prompt = f"""
[当前简历档案]
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

[用户本轮输入]
{new_input_text}

请完成以下任务：
1. 从新输入中提取并更新档案信息（姓名、联系方式、教育经历、工作/实习经历、技能、活动、证书等）
2. 保留已有的正确信息，如果新信息更准确则更新
3. 列出仍然缺失的重要字段（must_have）和可选字段（nice_to_have）
4. 生成下一个问题，引导用户补充关键信息
   - 问题要友好、具体
   - 提示用户可以文字描述或上传相关文档

请严格输出JSON格式（不要有额外文字）：
{{
  "updated_profile": {{完整的简历档案}},
  "missing_fields": {{
    "must_have": ["字段A", "字段B"],
    "nice_to_have": ["字段C"]
  }},
  "next_question": "下一个问题",
  "completion_percentage": 75
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


def get_initial_question() -> str:
    """获取初始问题"""
    return "你好！我是智能简历助手，我会通过对话帮你生成一份完整的简历。首先，请简单介绍一下你自己：姓名、目前身份（学生/在职）、联系方式（邮箱、手机），以及你期望的职位方向是什么？"


def process_user_input(session_id: str, user_text: str, file_content: str = "") -> dict:
    """
    处理用户输入

    Args:
        session_id: 会话ID（用于多用户隔离）
        user_text: 用户文字输入
        file_content: 可选的文件内容

    Returns:
        {
            "assistant_reply": "助手回复",
            "current_profile": {...},
            "is_complete": False,
            "completion_percentage": 60,
            "missing_fields": {...}
        }
    """
    # 简化版：这里用内存存储会话，实际应该用数据库或Redis
    # 为了演示，我们先用全局变量（仅支持单用户）
    global _current_session

    if not hasattr(process_user_input, '_sessions'):
        process_user_input._sessions = {}

    if session_id not in process_user_input._sessions:
        process_user_input._sessions[session_id] = init_empty_profile()

    current_profile = process_user_input._sessions[session_id]

    # 合并文字和文件内容
    combined_input = user_text
    if file_content:
        combined_input += f"\n\n[文档内容]\n{file_content}"

    # 调用聚合函数
    try:
        result = aggregate_profile(current_profile, combined_input)
    except Exception as e:
        return {
            "assistant_reply": f"抱歉，处理出错了：{str(e)}。请重新描述一下。",
            "current_profile": current_profile,
            "is_complete": False,
            "completion_percentage": 0,
            "missing_fields": {}
        }

    # 更新会话
    updated_profile = result.get("updated_profile", current_profile)
    process_user_input._sessions[session_id] = updated_profile

    missing = result.get("missing_fields", {})
    must_have = missing.get("must_have", [])

    # 判断是否完成
    is_complete = len(must_have) == 0

    # 计算完成度
    completion = result.get("completion_percentage", 50)

    return {
        "assistant_reply": result.get("next_question", "请继续补充你的经历和技能。"),
        "current_profile": updated_profile,
        "is_complete": is_complete,
        "completion_percentage": completion,
        "missing_fields": missing
    }


def finalize_resume(session_id: str) -> dict:
    """完成简历生成并返回"""
    if not hasattr(process_user_input, '_sessions') or session_id not in process_user_input._sessions:
        return None

    profile = process_user_input._sessions[session_id]

    # 清理会话
    del process_user_input._sessions[session_id]

    return profile


def reset_session(session_id: str):
    """重置会话"""
    if hasattr(process_user_input, '_sessions') and session_id in process_user_input._sessions:
        del process_user_input._sessions[session_id]
