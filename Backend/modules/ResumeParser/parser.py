"""
简历解析核心功能 - 从 Func1_Parser 整合
"""

from pdfminer.high_level import extract_text
from docx import Document
import os
import json
from openai import OpenAI


# 初始化 OpenAI 客户端（千问API）
client = OpenAI(
    api_key="sk-f25e9dbbe22d4c53afc2d5da4a7ad7ca",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def parse_resume(file_path: str) -> str:
    """解析简历文件，返回纯文本"""
    ext = file_path.split(".")[-1].lower()
    if ext == "pdf":
        return parse_pdf(file_path)
    elif ext == "docx":
        return parse_docx(file_path)
    elif ext == "txt":
        return parse_txt(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def parse_pdf(file_path: str) -> str:
    """解析PDF文件"""
    try:
        text = extract_text(file_path)
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"PDF 解析失败: {e}")


def parse_docx(file_path: str) -> str:
    """解析DOCX文件"""
    try:
        docx = Document(file_path)
        return "\n".join([p.text for p in docx.paragraphs if p.text.strip()])
    except Exception as e:
        raise RuntimeError(f"DOCX 解析失败: {e}")


def parse_txt(file_path: str) -> str:
    """解析TXT文件"""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def extract_resume_info(text: str) -> dict:
    """
    使用LLM从文本中提取结构化信息
    返回符合统一Schema的JSON
    """
    prompt = f"""
        你是一名专业的简历解析助手，任务是从输入的简历文本中提取结构化信息。
        请严格遵守以下总体要求：
        1. 仅输出合法 JSON，不得包含任何额外说明或自然语言，不得使用 Markdown 或代码块语法。
        2. 所有字段必须存在。若缺失，请以空字符串 ""、空数组 [] 或 null 填充。
        3. 日期相关字段必须满足以下规范：
        - 所有单一日期字段（如 education.start, education.end）统一使用 "YYYY.MM"。
        - experience.period 必须是时间段形式，统一使用以下格式之一：
            - "YYYY.MM~YYYY.MM"
            - 若尚未结束，使用 "YYYY.MM~Present"
        - 严禁在 period 中使用 "/"、"\\"、"-" 或其他分隔符。
        4. 确保嵌套结构与字段名完全一致，不得增删字段。
        5. 尽可能在 JSON 中描述更详细、全面的信息，包括项目细节、职责、成果、技术栈等。

        目标 JSON Schema 如下：
        {{
        "user_id": "",
        "name": "",
        "headline": "",
        "contacts": {{
            "email": "",
            "phone": "",
            "wechat": "",
            "github": ""
        }},
        "summary": "",
        "education": [
            {{
            "school": "",
            "degree": "",
            "major": "",
            "start": "",
            "end": "",
            "note": ""
            }}
        ],
        "experience": [
            {{
            "type": "",
            "name": "",
            "location": "",
            "title": "",
            "role": "",
            "period": "",
            "description": ""
            }}
        ],
        "skills": [],
        "activities": [
            {{
            "org": "",
            "role": "",
            "period": "",
            "description": ""
            }}
        ],
        "certifications": []
        }}

        **experience 字段说明（非常重要）：**
        - type: 经历类型，如"项目经历"、"工作经历"、"实习经历"等
        - name: 项目名称或公司名称
        - location: 工作/项目地点
        - title: **项目/职位的标题或名称**，这是必填字段，必须从简历中提取项目标题、职位名称等信息填入此字段
        - role: 担任的具体角色或职位，如"软件工程师"、"项目负责人"等
        - period: 时间段，格式如"2023.01~2023.12"
        - description: 详细描述工作内容、项目职责、技术栈、成果等

        请根据以下简历文本内容，提取并生成尽可能完整的结构化信息。
        务必输出单一 JSON 对象，不要使用 Markdown 或代码块语法。

        简历文本如下：
        {text}
    """

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "你是一名结构化信息抽取专家。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    raw_output = response.choices[0].message.content.strip()

    # 提取JSON部分
    json_start = raw_output.find("{")
    json_end = raw_output.rfind("}") + 1
    if json_start == -1 or json_end <= 0:
        raise RuntimeError(f"解析失败：未检测到 JSON 对象。\n输出：{raw_output}")

    json_str = raw_output[json_start:json_end]

    try:
        data = json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"简历结构化解析失败：{e}\n输出内容：{raw_output}")

    return data


def save_resume_json(data: dict, save_path: str):
    """保存简历JSON数据"""
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
