'''
Functionality 1：简历抓取与解析/用户个人信息提取
    情景2：用户没有个人简历，仅有一些个人信息以及文件（例如某篇论文，某个项目的结题报告书，某次实习的实习报告等），
    用户直接上传上述所有的这些信息、文件，由LLM进行读取和总结，并尽可能涵盖更全面的内容，便于后续制作简历时挑选契合的部分。
    该部分同样把用户上传的所有个人信息提取出来，提前整合好存成json文件，后续直接读json文件就行了。
'''



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
输出：输出格式符合统一的 Resume JSON Schema。
"""

client = OpenAI(
    api_key="sk-f25e9dbbe22d4c53afc2d5da4a7ad7ca",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def extract_resume_info(text: str) -> dict:
    """
    使用 大语言模型 基于获得的文本字符串，提取结构化信息，输出符合统一 Schema 的 JSON。
    """
    prompt = f"""
        你是一名专业的简历解析助手，任务是从输入的简历文本中提取结构化信息。

        请严格遵守以下要求：
        1. 仅输出**合法 JSON**，不得包含任何额外说明或自然语言。
        2. 所有字段必须存在。若缺失，请以空字符串 ""、空数组 [] 或 null 填充。
        3. 日期格式统一为 "YYYY-MM" 或 "YYYY.MM"。
        4. 确保嵌套结构与字段名完全一致，不得增删字段。
        5.尽可能在 JSON 中**描述更详细、全面的信息**，包括项目细节、职责、成果、技术栈等，  
   目的是方便后续在生成不同工作方向简历时，从完整的个人信息中挑选出最匹配的部分。

        目标 JSON Schema：
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
              "type": "",          // 可为 project / internship / research / job
              "name": "",
              "company": "",
              "dept": "",
              "organization": "",
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
          "certifications": [],
          "raw_files": [
            {{
              "uri": "",
              "type": "",
              "sha256": ""
            }}
          ],
          "last_updated": ""
        }}

        请根据以下简历文本内容，提取并生成尽可能完整的结构化信息。  
        务必输出 **单一 JSON 对象**，不要使用 Markdown 或代码块语法。
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
    pdf_path = "sample/中文简历.pdf"
    json_path = "output/CV1.json"

    text = parse_resume(pdf_path)
    print("解析后文本前500字：")
    print(text[:500])  # 调试输出

    if len(text) < 100:
        print("警告：PDF 解析结果为空，可能是扫描版或编码异常。")

    data = extract_resume_info(text)
    save_resume_json(data, json_path)
    print(f"已保存到: {json_path}")
