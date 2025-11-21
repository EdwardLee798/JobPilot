"""
交互式简历生成器 - 基于对话的简历信息收集
跨平台支持
"""
import json
from openai import OpenAI

# 初始化 LLM 客户端（与 InfoParser Demo 保持一致）
client = OpenAI(
    api_key="sk-f25e9dbbe22d4c53afc2d5da4a7ad7ca",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def init_empty_profile() -> dict:
    """按照统一的简历 Schema，初始化一个空档案"""
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


def get_initial_question() -> str:
    """获取初始问题（与 Demo 保持一致）"""
    return "先简单介绍一下你自己吧，比如姓名、目前身份（学生/在职）、所在城市，以及你手头有哪些相关文档可以提供？"


def _calc_completion_percentage(profile: dict, missing_must_have: list, is_complete_by_llm: bool) -> int:
    """
    根据已填字段和 must_have 数量粗略估算完成度
    该数值主要用于前端进度展示，对功能逻辑不构成强依赖。
    """
    # 基于关键字段打分
    total_slots = 6
    score = 0

    if profile.get("name"):
        score += 1
    contacts = profile.get("contacts") or {}
    if any(contacts.values()):
        score += 1
    if profile.get("education"):
        score += 1
    if profile.get("experience"):
        score += 1
    if profile.get("skills"):
        score += 1
    if profile.get("summary") or profile.get("headline"):
        score += 1

    completion = int(score / total_slots * 100) if total_slots > 0 else 0

    # 没有 must_have 且 LLM 认为可以结束 / 用户明确想结束，直接拉满
    if (not missing_must_have and is_complete_by_llm) and completion < 100:
        completion = 100

    # 合理下限，避免一直显示 0
    if completion < 10:
        completion = 10

    return completion


def process_user_input(session_id: str, user_text: str, file_content: str = "") -> dict:
    """
    处理用户输入

    Args:
        session_id: 会话ID（用于多用户隔离）
        user_text: 用户文字输入
        file_content: 可选的文件内容

    Returns:
        {
            "assistant_reply": "助手回复或下一问题/总结语",
            "current_profile": {...},
            "is_complete": False,
            "completion_percentage": 60,
            "missing_fields": {...},
            "analysis": {...}
        }
    """
    # 简易会话存储（生产环境建议改为 Redis/DB）
    if not hasattr(process_user_input, "_sessions"):
        process_user_input._sessions = {}

    if session_id not in process_user_input._sessions:
        process_user_input._sessions[session_id] = init_empty_profile()

    current_profile = process_user_input._sessions[session_id]

    # 合并文字和文件内容
    combined_input = user_text or ""
    if file_content:
        combined_input += f"\n\n[本轮文档内容]\n{file_content}"

    # 调用聚合函数
    try:
        result = aggregate_profile(current_profile, combined_input)
    except Exception as e:
        return {
            "assistant_reply": f"抱歉，处理出错了：{str(e)}。请稍后重试或换一种说法描述。",
            "current_profile": current_profile,
            "is_complete": False,
            "completion_percentage": 0,
            "missing_fields": {},
            "analysis": {
                "can_finalize": False,
                "reason": f"LLM 调用异常：{str(e)}",
                "user_stop_intent": False
            }
        }

    # 更新会话
    updated_profile = result.get("updated_profile") or current_profile
    process_user_input._sessions[session_id] = updated_profile

    missing = result.get("missing_fields") or {}
    analysis = result.get("analysis") or {}

    must_have = missing.get("must_have") or []
    can_finalize = bool(analysis.get("can_finalize", False))
    user_stop = bool(analysis.get("user_stop_intent", False))

    # 是否可以认为本轮已经“完成”
    is_complete = can_finalize or user_stop or (len(must_have) == 0)

    # 完成度估算
    completion = _calc_completion_percentage(
        updated_profile,
        must_have,
        can_finalize or user_stop
    )

    # LLM 给出的下一问题 / 总结
    next_question = result.get("next_question") or ""
    if not next_question.strip():
        if is_complete:
            next_question = "好的，基于目前的信息已经可以生成一份可用的简历。如果你愿意，也可以继续补充一些亮点经历。"
        else:
            next_question = "如果你还有想补充的经历、技能或成就，可以继续告诉我。"

    return {
        "assistant_reply": next_question,
        "current_profile": updated_profile,
        "is_complete": is_complete,
        "completion_percentage": completion,
        "missing_fields": missing,
        "analysis": analysis,
    }


def finalize_resume(session_id: str) -> dict:
    """完成简历生成并返回"""
    if not hasattr(process_user_input, "_sessions") or session_id not in process_user_input._sessions:
        return None

    profile = process_user_input._sessions[session_id]

    # 清理会话
    del process_user_input._sessions[session_id]

    return profile


def reset_session(session_id: str):
    """重置会话"""
    if hasattr(process_user_input, "_sessions") and session_id in process_user_input._sessions:
        del process_user_input._sessions[session_id]
