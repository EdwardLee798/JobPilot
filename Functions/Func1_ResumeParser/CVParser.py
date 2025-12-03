'''
Functionality 1：简历抓取与解析/用户个人信息提取
    情景1：用户上传pdf/docx形式的简历，调用LLM的文档读取API，读取文件中的个人信息，并保存在后台。
    在上传阶段就把用户的个人数据提取出来，提前整合好存成json文件，后续直接读json文件就行了。
'''



"""简历解析服务模块 - 输入：PDF、DOCX、TXT 格式。输出：纯文本字符串。"""

from pdfminer.high_level import extract_text
from docx import Document
import os
import json
from openai import OpenAI


def parse_resume(file_path: str) -> str:
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
    """解析PDF文件，提取文本内容"""
    try:
        text = extract_text(file_path)
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"PDF 解析失败: {e}")


def parse_docx(file_path: str) -> str:
    """解析DOCX文件，提取段落文本"""
    try:
        docx = Document(file_path)
        return "\n".join([p.text for p in docx.paragraphs if p.text.strip()])
    except Exception as e:
        raise RuntimeError(f"DOCX 解析失败: {e}")


def parse_txt(file_path: str) -> str:
    """解析TXT文件，读取文本内容"""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


"""
调用千问api从原始文本中提取结构化信息。
输入：解析后的纯文本字符串
输出：输出格式符合统一的 CV JSON Schema。
"""

client = OpenAI(
    api_key="sk-f25e9dbbe22d4c53afc2d5da4a7ad7ca",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def extract_resume_info(text: str) -> dict:
    """
    基于获得的文本字符串，让LLM提取结构化信息，输出符合统一 Schema 的 JSON。
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
        - 严禁在 period 中使用 "/"、"\\\\"、"-" 或其他分隔符。
        4. 确保嵌套结构与字段名完全一致，不得增删字段。
        5. 尽可能在 JSON 中描述更详细、全面的信息，包括项目细节、职责、成果、技术栈等，
        目的是方便后续在生成不同工作方向简历时，从完整的个人信息中挑选出最匹配的部分。

        关于各字段的具体要求：
        [1] 基本信息与总体概括
        - "user_id": 始终输出空字符串 ""，不要尝试从简历内容中推断或生成。
        - "headline":
            - 必须根据简历整体内容主动生成，即使简历中没有明确写出。
            - 用 10~30 个汉字，或 5~15 个英文单词，概括候选人的身份和方向。
            - 示例："Backend & Distributed Systems Engineer", "Software Engineering Student | Backend & Systems".
        - "summary":
            - 必须根据简历内容生成 2~4 句完整的话，总结候选人的背景、技术栈和优势。
            - 应做适度抽象和概括，避免简单复制 experience 中的原句。
            - 可以包含：教育背景、实习/项目类型、擅长技术栈、亮点成果等。

        [2] contacts 说明
            - 从简历中提取 email、phone、wechat、github 等联系信息：
            - 若没有则填空字符串 ""。
            - github 可以是 "github.com/xxx" 或完整 URL，保持与原文一致即可。
            - 允许对 phone 进行轻微规范化，例如仅保留数字、空格和 "+"。

        [3] education 字段
            - education 为数组，每一项必须包含：
            - "school": 学校名称。
            - "degree": 学位，例如 "Bachelor of Engineering"。
            - "major": 专业名称。
            - "start": 入学时间，格式为 "YYYY.MM"。
            - "end": 毕业或预计毕业时间，格式同上；若仍在读可根据简历信息合理填写。
            - "note": 可写平均分、GPA、主修课程等补充信息。
            - 若简历中有多段教育经历，请全部列出，按时间倒序排列。

        [4] experience 统一结构（实习 / 科研 / 项目 / 工作）
        - 所有实习、科研、项目、全职工作经历，都必须统一放入 experience 数组，
        并通过 "type" 字段区分：
            - "internship": 实习经历
            - "project": 课程项目、个人项目、工程项目等
            - "research": 科研、实验室、研究助理等
            - "job": 正式全职工作

        - experience 中每一项必须尽量补全如下字段：
            - "type": 以上枚举之一。
            - "name": 该经历的名称，例如项目名称、课题名称、岗位名称等。
            - "location":
                - 这是一个宽泛的“地点/归属组织”字段，用于统一描述本段经历发生的机构。
                - 若为实习或正式工作（type 为 "internship" 或 "job"）：location 应包含 公司全称 + 部门或团队 信息（若有），例如："Neusoft Education Technology Group, Healthcare R&D Department"。
                - 若为科研经历（type 为 "research"）：location 应为 学校全称 + 学院/实验室名称，例如："Northeastern University, Software Engineering Lab"。
                - 若为课程项目或在校项目（type 为 "project" 且在学校完成）：location 一般为 学校全称，必要时可附带课程名称，例如："Northeastern University, Software Engineering Program"。
                - 若为个人独立项目且无机构背景：location 可以填 "Personal Project" 或类似描述。
        - "title":
            - 对于实习 / 工作，填职位名称，例如 "Backend Development Intern"、"Software Engineer Intern"。
            - 对于科研 / 项目，可填 "Research Assistant"、"Developer" 等角色名称。
            - 若简历中未明确给出，但可根据描述合理推断，请进行合理推断后填入。
        - "role":
            - 用简短短语概括角色定位，例如 "Backend developer", "Embedded systems developer"，"Full-stack developer", "Research assistant" 等。
            - 若确实无法判断再留空。
        - "period":
            - 必须按照前述日期规则使用时间段格式："YYYY.MM~YYYY.MM" 或 "YYYY.MM~Present"。
            - 若简历中仅给出年份或部分时间，请作合理补全；确实无法补全时，用能确定的部分加 "~Present"。
        - "description":
            - 用多句话详细描述工作 / 项目内容、职责、技术栈和关键成果。
            - 建议包含：使用到的技术、负责的模块、性能/效率提升、稳定性提升、架构设计亮点等。
            - 可以适度将条目式描述整合为多句自然语言，但不得凭空添加不存在的经历。
        [5] skills 字段
            - skills 为字符串数组。
            - 列出所有在简历中出现的编程语言、框架、数据库、中间件、工具、以及语言能力等。
            - 可以适度合并类似项，但不得凭空添加简历中没有体现的技能。

        [6] activities 与 certifications 的区分
        - "activities" 用于学生工作、社团活动、志愿者经历等，数组中的每一项包含：
        {{
            "org": "",
            "role": "",
            "period": "",
            "description": ""
        }}
        说明：
        - "org": 组织或社团名称，例如 "Student Union", "Class 2022 Software Engineering"。
        - "role": 所担任职位，如 "Class Monitor", "Mental Health Representative"。
        - "period": 时间段，格式与 experience.period 完全相同。
        - "description": 具体职责和贡献，至少 1~2 句。
        - "certifications" 用于：
        - 竞赛奖项（如数学建模、编程竞赛、ACM 等）
        - 奖学金（如 National Merit Scholarship 等）
        - 证书类荣誉（如英语等级证书等）
        - 可以使用简单字符串列表，每个元素描述一个奖项或证书。
        - 若简历中某些荣誉既可以视为活动又可以视为奖项，请优先放入 certifications，
        学生干部/职务类内容则放入 activities。

        目标 JSON Schema 如下（字段名和结构必须完全一致）：
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

    # 从模型输出中截取 JSON 部分，以防模型输出json以外的内容
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

# 保存
def save_resume_json(data: dict, save_path: str):
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    pdf_path = "JobPilot/Func1_Parser/sample/Orig_CV/英文简历1.docx"
    json_path = "JobPilot/Func1_Parser/sample/Json_CV/英文简历1.json"

    text = parse_resume(pdf_path)
    print("解析后文本前500字：")
    print(text[:500])  # 调试输出

    if len(text) < 10:
        print("警告：PDF 解析结果为空，可能是扫描版或编码异常。")

    data = extract_resume_info(text)
    save_resume_json(data, json_path)
    print(f"已保存到: {json_path}")
