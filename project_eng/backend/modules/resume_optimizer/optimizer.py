"""
简历优化核心功能 - 简化整合版本
基于JD分析和LLM优化简历内容
"""

import os
import json
import numpy as np
from openai import OpenAI
from jinja2 import Template

# 初始化LLM客户端
client = OpenAI(
    api_key="sk-c73e767ea8264d91bff717d150041c87",
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

EMBED_MODEL = "text-embedding-v3"
LLM_MODEL = "qwen3-coder-flash"


def embed_texts(texts: list) -> np.ndarray:
    """将文本列表转换为向量"""
    try:
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=texts,
            dimensions=512
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings)
    except Exception as e:
        raise RuntimeError(f"文本向量化失败: {e}")


def cosine_scores(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """计算余弦相似度"""
    return doc_vecs @ query_vec.T


def optimize_resume_with_jd(resume_data: dict, jd_text: str) -> dict:
    """
    基于JD优化简历
    1. 计算经历与JD的相似度
    2. 重排序经历
    3. 优化经历描述
    """
    # Step 1: 提取所有经历
    experiences = resume_data.get('experience', [])
    activities = resume_data.get('activities', [])

    # Step 2: 构建经历文本
    exp_texts = []
    exp_objects = []

    for exp in experiences:
        text = f"{exp.get('name', '')} {exp.get('description', '')} {exp.get('role', '')}"
        exp_texts.append(text)
        exp_objects.append({'source': 'experience', 'data': exp})

    for act in activities:
        text = f"{act.get('org', '')} {act.get('role', '')} {act.get('description', '')}"
        exp_texts.append(text)
        exp_objects.append({'source': 'activities', 'data': act})

    if not exp_texts:
        raise ValueError("简历中没有经历数据")

    # Step 3: 计算相似度
    jd_vec = embed_texts([jd_text])[0]
    exp_vecs = embed_texts(exp_texts)
    scores = cosine_scores(jd_vec, exp_vecs)

    # Step 4: 排序并筛选
    sorted_indices = np.argsort(-scores)  # 降序
    scored_experiences = []

    for idx in sorted_indices:
        scored_experiences.append({
            'score': float(scores[idx]),
            'source': exp_objects[idx]['source'],
            'data': exp_objects[idx]['data']
        })

    # Step 5: 选取Top经历并优化描述
    top_experiences = scored_experiences[:8]  # 选择前8条经历

    optimized_experiences = []
    for item in top_experiences:
        if item['score'] < 0.3:  # 过滤低相关经历
            continue

        exp_data = item['data']
        optimized_desc = optimize_experience_description(
            exp_data.get('name', ''),
            exp_data.get('description', ''),
            jd_text,
            item['score']
        )

        optimized_exp = exp_data.copy()
        optimized_exp['optimized_description'] = optimized_desc
        optimized_exp['match_score'] = item['score']
        optimized_experiences.append(optimized_exp)

    # Step 6: 构建最终输出
    optimized_resume = {
        'header': {
            'name': resume_data.get('name', ''),
            'contact': format_contact(resume_data.get('contacts', {}))
        },
        'summary': generate_summary(resume_data, jd_text),
        'education': resume_data.get('education', []),
        'experience': optimized_experiences,
        'skills': ', '.join(resume_data.get('skills', [])),
        'certifications': resume_data.get('certifications', [])
    }

    return optimized_resume


def optimize_experience_description(name: str, description: str, jd_text: str, score: float) -> str:
    """使用LLM优化经历描述"""
    prompt = f"""
你是一名专业的简历优化专家。请根据以下职位描述（JD）优化这段经历的描述。

职位描述：
{jd_text}

经历名称：{name}
原始描述：{description}
匹配度分数：{score:.2f}

要求：
1. 突出与JD相关的技能和成果
2. 使用量化数据和具体成果
3. 保持简洁专业，3-5句话
4. 使用STAR法则（情境、任务、行动、结果）
5. 用<strong>标签强调关键词和数据

请直接输出优化后的描述，不要输出其他内容。
"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一名专业的简历优化专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"优化描述失败: {e}")
        return description  # 失败时返回原描述


def generate_summary(resume_data: dict, jd_text: str) -> str:
    """生成针对JD的个人总结"""
    prompt = f"""
基于以下简历信息和职位描述，生成一段专业的个人总结（2-3句话）。

职位描述：
{jd_text}

简历信息：
姓名：{resume_data.get('name', '')}
标题：{resume_data.get('headline', '')}
原总结：{resume_data.get('summary', '')}
技能：{', '.join(resume_data.get('skills', [])[:10])}

要求：突出与职位最相关的背景、技能和优势。
请直接输出总结，不要输出其他内容。
"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一名专业的简历优化专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成总结失败: {e}")
        return resume_data.get('summary', '')


def format_contact(contacts: dict) -> str:
    """格式化联系方式"""
    parts = []
    if contacts.get('email'):
        parts.append(contacts['email'])
    if contacts.get('phone'):
        parts.append(contacts['phone'])
    if contacts.get('github'):
        parts.append(contacts['github'])
    return ' | '.join(parts)


def generate_pdf_resume(resume_data: dict, output_path: str, language: str = 'zh'):
    """生成HTML简历（用户可在浏览器中打印为PDF）"""
    html_template = """<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <title>{{ header.name }} - Resume</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: "Arial", "Helvetica", "SimSun", sans-serif;
            font-size: 12px;
            line-height: 1.6;
        }
        @media print {
            body { margin: 0; }
        }
        body {
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            background: white;
        }
        .header {
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }
        .header h1 {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .contact {
            font-size: 11px;
            color: #555;
        }
        .section {
            margin-bottom: 20px;
            page-break-inside: avoid;
        }
        .section-title {
            font-size: 16px;
            font-weight: bold;
            border-bottom: 1px solid #666;
            margin-bottom: 10px;
            padding-bottom: 5px;
        }
        .experience-item {
            margin-bottom: 15px;
        }
        .exp-header {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .exp-description {
            margin-left: 15px;
            text-align: justify;
        }
        strong {
            font-weight: bold;
            color: #000;
        }
        .education-item {
            margin-bottom: 10px;
        }
        .print-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        @media print {
            .print-btn { display: none; }
        }
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">打印/保存为PDF</button>

    <div class="header">
        <h1>{{ header.name }}</h1>
        <div class="contact">{{ header.contact }}</div>
    </div>

    <div class="section">
        <div class="section-title">个人总结 / Professional Summary</div>
        <p>{{ summary }}</p>
    </div>

    <div class="section">
        <div class="section-title">教育背景 / Education</div>
        {% for edu in education %}
        <div class="education-item">
            <strong>{{ edu.school }}</strong> - {{ edu.degree }} in {{ edu.major }} ({{ edu.start }} - {{ edu.end }})
            {% if edu.note %}<br>{{ edu.note }}{% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="section">
        <div class="section-title">工作经历 / Experience</div>
        {% for exp in experience %}
        <div class="experience-item">
            <div class="exp-header">{{ exp.name }} ({{ exp.period }})</div>
            <div class="exp-description">{{ exp.optimized_description | safe }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="section">
        <div class="section-title">技能 / Skills</div>
        <p>{{ skills }}</p>
    </div>

    {% if certifications %}
    <div class="section">
        <div class="section-title">证书与荣誉 / Certifications & Awards</div>
        <ul>
        {% for cert in certifications %}
            <li>{{ cert }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
</body>
</html>
"""

    # 渲染HTML
    template = Template(html_template)
    html_content = template.render(**resume_data, language=language)

    # 保存HTML文件（改为.html后缀）
    html_path = output_path.replace('.pdf', '.html')
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except Exception as e:
        raise RuntimeError(f"HTML生成失败: {e}")
