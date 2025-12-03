import json
import re
from jinja2 import Template
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableSequence
from langchain_openai import ChatOpenAI
from playwright.sync_api import sync_playwright
import pdfplumber

# -------------------------- 配置参数 --------------------------
API_KEY = "sk-c73e767ea8264d91bff717d150041c87"  # 请替换为有效API_KEY
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen3-coder-flash"
RESUME_JSON_PATH = "zh1_DataAnalysis.json"  # 新输入：结构化JSON文件（需放在同目录）
OUTPUT_PDF_PATH = "generated_resume_from_json.pdf"

# -------------------------- 核心Schema（仅保留模板所需最终结构） --------------------------
# 仅用于最终渲染校验，不强制中间数据适配，避免LLM混淆
FINAL_RENDER_SCHEMA = {
    "type": "object",
    "required": ["header", "summary", "education", "sections", "skills", "hobbies"],
    "properties": {
        "header": {
            "type": "object",
            "required": ["name", "contact"],
            "properties": {
                "name": {"type": "string"},
                "contact": {"type": "string"}
            }
        },
        "summary": {"type": "string"},
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["school", "major", "degree"],
                "properties": {
                    "school": {"type": "string"},
                    "major": {"type": "string"},
                    "degree": {"type": "string"},
                    "gpa": {"type": "string"},
                    "core_courses": {"type": "string"}
                }
            }
        },
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["section_title", "blocks"],
                "properties": {
                    "section_title": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["block_header", "block_subheader", "projects"],
                            "properties": {
                                "block_header": {"type": "string"},
                                "block_subheader": {"type": "string"},
                                "projects": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["project_title", "sub_title", "structured_content"],
                                        "properties": {
                                            "project_title": {"type": "string"},
                                            "sub_title": {"type": "string"},
                                            "structured_content": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "skills": {"type": "string"},
        "hobbies": {"type": "string"}
    }
}

# 经历分层Schema（仅存储完整经历对象，不涉及分数阈值）
STRATIFICATION_SCHEMA = {
    "type": "object",
    "required": ["core_experiences", "secondary_experiences", "irrelevant_experiences", "judgment_basis"],
    "properties": {
        "core_experiences": {"type": "array", "items": {"type": "object"}},
        "secondary_experiences": {"type": "array", "items": {"type": "object"}},
        "irrelevant_experiences": {"type": "array", "items": {"type": "object"}},
        "judgment_basis": {"type": "array", "items": {"type": "string"}}
    }
}

# 原有核心Schema保留（仅用于解析器初始化，不强制中间数据适配）
TITLE_EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["project_title", "sub_title"],
    "properties": {
        "project_title": {"type": "string"},
        "sub_title": {"type": "string"}
    }
}

CONTENT_STRUCT_SCHEMA = {
    "type": "object",
    "required": ["details"],
    "properties": {
        "details": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "content"],
                "properties": {
                    "label": {"type": "string", "minLength": 2, "maxLength": 4},
                    "content": {"type": "string"}
                }
            }
        }
    }
}

CLUSTER_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["section_title", "blocks"],
        "properties": {
            "section_title": {"type": "string"},
            "blocks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["block_header", "block_subheader", "projects"],
                    "properties": {
                        "block_header": {"type": "string"},
                        "block_subheader": {"type": "string"},
                        "projects": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "project_title": {"type": "string"},
                                    "sub_title": {"type": "string"},
                                    "structured_content": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# HTML模板（完全保留原有样式，无任何修改）
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ header.name }} - 简历</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: "KaiTi", "SimKai", serif;
            font-size: 12px;
            line-height: 1.5;
        }
        body {
            max-width: 650px;
            margin: 2rem auto;
            padding: 0 1.2rem;
        }
        .header {
            text-align: center;
            margin-bottom: 1.2rem;
            position: relative;
        }
        .header h1 {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .contact {
            font-size: 12px;
            margin-bottom: 0.3rem;
        }
        .photo-placeholder {
            width: 60px;
            height: 80px;
            border: 1px solid #ccc;
            background: #f5f5f5;
            position: absolute;
            top: 0;
            right: 0;
        }
        .summary {
            text-align: center;
            margin-bottom: 1.5rem;
            font-size: 14px;
            font-weight: bold;
        }
        .section-title {
            font-size: 14px;
            font-weight: bold;
            margin: 1.5rem 0 0.8rem 0;
            border-bottom: 1px solid #000;
            padding-bottom: 0.3rem;
        }
        .education-item {
            margin-bottom: 0.5rem;
        }
        .company-block {
            margin-bottom: 1rem;
        }
        .company-header {
            display: flex;
            justify-content: space-between;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .project {
            margin: 0.8rem 0 1rem 0;
        }
        .project-title {
            font-weight: bold;
            margin-bottom: 0.3rem;
        }
        .project-subtitle {
            font-style: italic;
            color: #555;
            margin-bottom: 0.3rem;
        }
        .structured-content {
            white-space: pre-line;
            margin-left: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ header.name }}</h1>
        <div class="contact">{{ header.contact }}</div>
        <div class="photo-placeholder"></div>
    </div>

    <div class="summary">{{ summary }}</div>

    <div class="section-title">教育经历</div>
    {% for edu in education %}
    <div class="education-item">
        {{ edu.school }} {{ edu.major }} | {{ edu.degree }}
        {% if edu.gpa %} | GPA {{ edu.gpa }}{% endif %}
        {% if edu.core_courses %} | 核心课程：{{ edu.core_courses }}{% endif %}
    </div>
    {% endfor %}

    {% for section in sections %}
    <div class="section-title">{{ section.section_title }}</div>
        {% for block in section.blocks %}
        <div class="company-block">
            <div class="company-header">
                <span>{{ block.block_header }}</span>
                <span>{{ block.block_subheader }}</span>
            </div>

            {% for project in block.projects %}
            <div class="project">
                <div class="project-title">{{ project.project_title }}</div>
                {% if project.sub_title %}
                <div class="project-subtitle">{{ project.sub_title }}</div>
                {% endif %}
                <div class="structured-content">{{ project.structured_content | safe }}</div>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    {% endfor %}

    <div class="section-title">技能&英语能力</div>
    <div class="company-role">{{ skills }}</div>

    <div class="section-title">兴趣爱好</div>
    <div class="company-role">{{ hobbies }}</div>
</body>
</html>"""


# -------------------------- 核心功能实现 --------------------------
class ResumeGenerator:
    def __init__(self):
        print("===== 初始化简历生成器 =====")
        self.llm = ChatOpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            model_name=MODEL_NAME,
            temperature=0.05
        )
        print(f"已加载大模型：{MODEL_NAME}")

        # 初始化解析器（仅保留必要解析器，减少冗余）
        self.stratification_parser = JsonOutputParser(schema=STRATIFICATION_SCHEMA)
        self.title_extract_parser = JsonOutputParser(schema=TITLE_EXTRACTION_SCHEMA)
        self.content_struct_parser = JsonOutputParser(schema=CONTENT_STRUCT_SCHEMA)
        self.cluster_parser = JsonOutputParser(schema=CLUSTER_SCHEMA)
        self.final_render_parser = JsonOutputParser(schema=FINAL_RENDER_SCHEMA)

        # 初始化处理链（核心修改：分层Prompt移除所有分数阈值）
        self.stratification_chain = self._init_stratification_chain()
        self.title_extract_chain = self._init_title_extract_chain()
        self.core_content_chain = self._init_core_content_chain()
        self.secondary_content_chain = self._init_secondary_content_chain()
        self.cluster_chain = self._init_cluster_chain()
        print("所有处理链初始化完成\n")

    # 1. 经历分层链（关键修改：移除分数阈值，让LLM自主融合匹配度+含金量）
    def _init_stratification_chain(self):
        prompt = ChatPromptTemplate.from_template("""
        任务：结合岗位匹配度分数和经历含金量，对结构化经历进行智能分层筛选
        输入信息：每个经历包含"name"（名称）、"description"（详情）、"match_score"（岗位匹配度，0-1区间，越高越匹配）、"type"（类型）

        分层定义（无分数阈值，仅作定性参考）：
        1. 核心经历：与岗位高度契合，且含金量极高（如头部公司核心岗位实习、国家级/重大项目主导、核心算法开发/落地、量化成果突出、权威奖项）；
        2. 次要经历：与岗位相关度中等或较高，且有一定含金量（如常规项目参与、校级奖项、非核心但关键的执行工作、有明确成果但规模较小）；
        3. 无关经历：与岗位关联度低，或含金量极低（如基础性事务性工作、无明确成果的参与、与岗位方向无关的经历）。

        筛选核心原则：
        - 不按分数排序截断，不设置任何分数门槛，完全基于"匹配度+含金量"双重维度综合判断；
        - 保证经历类型均衡（实习/科研/项目/校园活动合理搭配，避免单一类型过度堆砌）；
        - 同一主题/同一机构的延伸经历合并为1条（如同一项目的不同阶段、同一公司的不同任务）；
        - 核心+次要经历总数控制在6-8条（简历黄金数量，避免冗长）；
        - 优先保留"高匹配+高含金量"，其次是"高匹配+中含金量"或"中匹配+高含金量"，最后补充类型均衡所需经历；
        - 禁止因匹配度高但含金量极低的经历进入核心/次要层，也禁止因匹配度略低但含金量极高的关键经历被遗漏。

        输出要求：
        1. 保留每条经历的完整信息（不修改任何字段），仅按分层归类；
        2. 严格包含4个字段，返回纯JSON，无其他冗余内容；
        3. judgment_basis需说明每条核心/次要经历的入选理由（结合匹配度和含金量）。

        输出格式：
        {{
            "core_experiences": [完整经历对象1, 完整经历对象2, ...],
            "secondary_experiences": [完整经历对象1, 完整经历对象2, ...],
            "irrelevant_experiences": [完整经历对象1, 完整经历对象2, ...],
            "judgment_basis": [
                "核心经历-XXX：匹配度较高（分数XXX），且为头部公司核心实习/重大项目，含金量极高",
                "次要经历-XXX：匹配度中等（分数XXX），为常规项目执行，有明确成果，补充经历类型",
                ...
            ]
        }}

        输入经历列表：{experiences_with_score}
        """)
        return RunnableSequence(prompt | self.llm | self.stratification_parser)

    # 2. 标题提取链（最小修改：适配结构化经历输入）
    def _init_title_extract_chain(self):
        prompt = ChatPromptTemplate.from_template("""
        任务：为以下结构化经历生成简洁的项目标题和具体方向子标题，确保无重复。
        要求：
        1. project_title：简洁概括项目核心（如“跨境电商智能选品平台开发”）；
        2. sub_title：明确技术/业务方向（如“基于LightGBM的热销商品预测与竞品监控”）；
        3. 禁止重复标题，若多条经历属于同一项目/主题需合并描述。

        仅返回纯JSON，无其他内容：
        {{
            "project_title": "...", 
            "sub_title": "..."
        }}

        输入经历：
        名称：{exp_name}
        详情：{exp_desc}
        """)
        return RunnableSequence(prompt | self.llm | self.title_extract_parser)

    # 3. 核心经历内容结构化链（无修改，保留原有优化）
    def _init_core_content_chain(self):
        prompt = ChatPromptTemplate.from_template("""
        任务：将以下核心经历结构化表达，转化为带加粗标签的详情列表。
        要求：
        1. details：数组，每个元素含label（2-6字标签）和content；label数量≤5个，严禁超量；
        2. label和content有两种表示方法，自行判断后在下面选择一种类型进行结构化描述：
           项目类型：建议用STAR法则（label用背景、目标、动作、结果）或其他结构化表达方式。应该构成一个完整的、逻辑闭环的、通顺的项目故事。
           描述类型：将经历进行分类，如label用专题分析、看板搭建、模型构建、指标监控等（严禁直接搬用这里的例子），应该从不同角度描述职责。
        3. 标签（label）用<strong>加粗</strong>，关键量化成果（数字、百分比、奖项等级等）也需加粗，禁止用*text*进行加粗。
        4. 语言专业化，禁止口语化，禁止使用“我”；
        5. 详细保留所有亮眼细节与量化结果，同时保持高度结构化。

        仅返回纯JSON：
        {{
            "details": [
                {{"label": "...", "content": "..."}}
            ]
        }}

        输入经历：{exp_desc}
        """)
        return RunnableSequence(prompt | self.llm | self.content_struct_parser)

    # 4. 次要经历内容结构化链（完整保留原有逻辑）
    def _init_secondary_content_chain(self):
        prompt = ChatPromptTemplate.from_template("""
        任务：将以下次要经历结构化表达，转化为带加粗标签的详情列表。
        要求：
        1. details：数组，每个元素含label（2-6字标签，如背景、动作、结果）和content；label数量≤3个，严禁超量；
        2. label和content有两种表示方法，自行判断后在下面选择一种类型进行结构化描述：
           项目类型：建议用STAR法则（label用背景、动作、结果）或其他结构化表达方式。应该构成一个完整的、逻辑闭环的、通顺的项目故事。每个label允许且仅允许生成一次，绝对禁止”给经历里每句话贴标签“式的生成。
           描述类型：将经历进行分类，如label用专题分析、看板搭建、模型构建、指标监控等（严禁直接搬用这里的例子），应该从不同角度描述职责。
        3. 标签（label）用<strong>加粗</strong>，关键量化成果（数字、百分比）也需加粗，禁止用*text*进行加粗。
        4. 语言专业化，禁止口语化，简洁呈现核心信息；
        5. 保留关键成果，避免冗余描述。

        仅返回纯JSON：
        {{
            "details": [
                {{"label": "...", "content": "..."}}
            ]
        }}

        输入经历：{exp_desc}
        """)
        return RunnableSequence(prompt | self.llm | self.content_struct_parser)

    # 5. 经历聚类链（适配结构化经历输入，保留原有聚类逻辑）
    def _init_cluster_chain(self):
        prompt = ChatPromptTemplate.from_template("""
        任务：将以下结构化经历按关联性聚类为模块（如“实习经历”“科研项目”"校园活动"），确保标题无重复。
        要求：
        1. section_title：模块名称简洁规范（如"实习经历"、"科研项目"、"个人项目"、"校园活动"）；
        2. 每个block包含block_header（机构/项目所属主体）、block_subheader（时间周期）、projects数组；
        3. projects数组保留原始的project_title、sub_title、structured_content字段，不新增/修改字段；
        4. 同一模块内按时间倒序排列（最新经历在前），同一机构/主体的经历合并为一个block；
        5. 禁止重复模块标题，确保聚类逻辑清晰（按经历类型+关联度划分）。
        6. 同一经历只能属于一个模块，禁止出现在多个模块中。

        仅返回纯JSON，无其他冗余内容：
        [
            {{
                "section_title": "实习经历",
                "blocks": [
                    {{
                        "block_header": "阿里巴巴国际数字商业集团",
                        "block_subheader": "2025.06~2025.09",
                        "projects": [
                            {{
                                "project_title": "跨境电商智能选品平台开发",
                                "sub_title": "基于LightGBM的热销商品预测与竞品监控",
                                "structured_content": "<strong>背景</strong>：...<strong>结果</strong>：..."
                            }}
                        ]
                    }}
                ]
            }}
        ]

        输入结构化经历：{structured_experiences}
        """)
        return RunnableSequence(prompt | self.llm | self.cluster_parser)

    # 读取结构化JSON简历数据
    def read_resume_json(self):
        print(f"===== 读取结构化简历数据（{RESUME_JSON_PATH}） =====")
        try:
            with open(RESUME_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 校验数据结构完整性
            if not data.get("results") or len(data["results"]) == 0:
                raise ValueError("JSON数据中无有效results字段")

            resume_data = data["results"][0].get("reordered_resume")
            sorted_blocks = data["results"][0].get("sorted_blocks", [])

            if not resume_data:
                raise ValueError("JSON数据中无有效reordered_resume字段")

            print(
                f"读取成功：姓名={resume_data.get('name', '未知')}，经历总数={len(resume_data.get('experience', [])) + len(resume_data.get('activities', []))}")
            print(f"匹配度分数列表：{[{'name': b['name'], 'score': b['score']} for b in sorted_blocks[:3]]}...\n")
            return resume_data, sorted_blocks
        except Exception as e:
            raise RuntimeError(f"读取JSON简历失败：{str(e)}")

    # 数据预处理：合并经历+绑定匹配度分数
    def preprocess_experiences(self, resume_data, sorted_blocks):
        print("===== 预处理经历数据 =====")
        # 合并所有经历（experience + activities）
        all_experiences = []

        # 处理experience字段
        for exp in resume_data.get("experience", []):
            all_experiences.append({
                "name": exp.get("name", ""),
                "description": exp.get("description", ""),
                "type": exp.get("type", "project"),
                "location": exp.get("location", ""),
                "period": exp.get("period", ""),
                "match_score": 0.0  # 初始化为0，后续绑定
            })

        # 处理activities字段
        for act in resume_data.get("activities", []):
            act_name = f"{act.get('org', '')}-{act.get('role', '')}"
            all_experiences.append({
                "name": act_name,
                "description": act.get("description", ""),
                "type": "activity",
                "location": act.get("org", ""),
                "period": act.get("period", ""),
                "match_score": 0.0  # 初始化为0，后续绑定
            })

        # 绑定匹配度分数（通过名称模糊匹配，兼容字段差异）
        sorted_block_dict = {b["name"].lower(): b["score"] for b in sorted_blocks}
        for exp in all_experiences:
            exp_name_lower = exp["name"].lower()
            # 模糊匹配（处理名称细微差异）
            matched_score = 0.0
            for block_name, score in sorted_block_dict.items():
                if block_name in exp_name_lower or exp_name_lower in block_name:
                    matched_score = score
                    break
            exp["match_score"] = matched_score

        print(
            f"预处理完成：合并后经历总数={len(all_experiences)}，成功绑定分数的经历数={len([e for e in all_experiences if e['match_score'] > 0])}\n")
        return all_experiences

    # 步骤1：经历分层（核心+次要+无关）
    def process_experience_stratification(self, preprocessed_experiences):
        print("===== 步骤1/6：经历分层 =====")
        try:
            # 转换为JSON字符串传入链中
            experiences_json = json.dumps(preprocessed_experiences, ensure_ascii=False)
            result = self.stratification_chain.invoke({"experiences_with_score": experiences_json})

            # 确保字段存在且为数组
            for field in ["core_experiences", "secondary_experiences", "irrelevant_experiences", "judgment_basis"]:
                if field not in result or not isinstance(result[field], list):
                    result[field] = []

            print(
                f"分层完成：核心{len(result['core_experiences'])}条，次要{len(result['secondary_experiences'])}条，无关{len(result['irrelevant_experiences'])}条")
            print(f"判断依据：{result['judgment_basis'][:2]}...\n")
            return result["core_experiences"], result["secondary_experiences"]
        except Exception as e:
            raise RuntimeError(f"经历分层失败：{str(e)}")

    # 步骤2：处理核心经历（标题提取+内容结构化）
    def process_core_experiences(self, core_experiences):
        print("===== 步骤2/6：处理核心经历 =====")
        structured_cores = []
        for i, exp in enumerate(core_experiences, 1):
            try:
                exp_name = exp.get("name", f"核心经历{i}")
                exp_desc = exp.get("description", "").strip()
                if not exp_desc:
                    print(f"核心经历{i}：描述为空，跳过")
                    continue
                print(f"处理核心经历{i}：{exp_name[:30]}...")

                # 提取标题
                title_data = self.title_extract_chain.invoke({
                    "exp_name": exp_name,
                    "exp_desc": exp_desc
                })

                # 内容结构化
                content_data = self.core_content_chain.invoke({"exp_desc": exp_desc})
                details_text = "\n".join(
                    [f"<strong>{item['label']}</strong>：{item['content']}" for item in content_data["details"]]
                )

                # 组装结构化结果（包含聚类所需字段）
                structured_core = {
                    "project_title": title_data.get("project_title", exp_name),
                    "sub_title": title_data.get("sub_title", ""),
                    "structured_content": details_text,
                    "location": exp.get("location", ""),
                    "period": exp.get("period", "")
                }
                structured_cores.append(structured_core)
                print(f"核心经历{i}处理成功：{structured_core['project_title']}\n")
            except Exception as e:
                print(f"核心经历{i}处理失败（跳过）：{str(e)}\n")
        return structured_cores

    # 步骤3：处理次要经历（标题提取+内容结构化）
    def process_secondary_experiences(self, secondary_experiences):
        print("===== 步骤3/6：处理次要经历 =====")
        structured_secondaries = []
        for i, exp in enumerate(secondary_experiences, 1):
            try:
                exp_name = exp.get("name", f"次要经历{i}")
                exp_desc = exp.get("description", "").strip()
                if not exp_desc:
                    print(f"次要经历{i}：描述为空，跳过")
                    continue
                print(f"处理次要经历{i}：{exp_name[:30]}...")

                # 提取标题
                title_data = self.title_extract_chain.invoke({
                    "exp_name": exp_name,
                    "exp_desc": exp_desc
                })

                # 内容结构化
                content_data = self.secondary_content_chain.invoke({"exp_desc": exp_desc})
                details_text = "\n".join(
                    [f"<strong>{item['label']}</strong>：{item['content']}" for item in content_data["details"]]
                )

                # 组装结构化结果（包含聚类所需字段）
                structured_secondary = {
                    "project_title": title_data.get("project_title", exp_name),
                    "sub_title": title_data.get("sub_title", ""),
                    "structured_content": details_text,
                    "location": exp.get("location", ""),
                    "period": exp.get("period", "")
                }
                structured_secondaries.append(structured_secondary)
                print(f"次要经历{i}处理成功：{structured_secondary['project_title']}\n")
            except Exception as e:
                print(f"次要经历{i}处理失败（跳过）：{str(e)}\n")
        return structured_secondaries

    # 步骤4：经历聚类（合并核心+次要经历，生成模块）
    def process_cluster(self, structured_cores, structured_secondaries):
        print("===== 步骤4/6：经历聚类 =====")
        # 合并核心和次要经历，添加类型标识
        all_structured = []
        for exp in structured_cores:
            all_structured.append({**exp, "experience_level": "核心"})
        for exp in structured_secondaries:
            all_structured.append({**exp, "experience_level": "次要"})

        if not all_structured:
            print("无有效结构化经历，聚类结果为空\n")
            return []

        try:
            cluster_input = json.dumps(all_structured, ensure_ascii=False)
            cluster_result = self.cluster_chain.invoke({"structured_experiences": cluster_input})

            print(f"聚类完成：生成{len(cluster_result)}个模块")
            print(f"模块名称：{[section['section_title'] for section in cluster_result]}\n")
            return cluster_result
        except Exception as e:
            raise RuntimeError(f"经历聚类失败：{str(e)}")

    # 步骤5：构建最终渲染数据（适配HTML模板字段）
    def build_final_render_data(self, resume_data, cluster_result):
        print("===== 步骤5/6：构建最终渲染数据 =====")
        try:
            # 1. 个人信息（header）
            contacts = resume_data.get("contacts", {})
            contact_list = []
            if contacts.get("email"):
                contact_list.append(f"邮箱：{contacts['email']}")
            if contacts.get("phone"):
                contact_list.append(f"电话：{contacts['phone']}")
            if contacts.get("github"):
                contact_list.append(f"GitHub：{contacts['github']}")
            contact_str = " | ".join(contact_list) if contact_list else ""

            header = {
                "name": resume_data.get("name", "未知姓名"),
                "contact": contact_str
            }

            # 2. 亮点总结（summary）
            summary = resume_data.get("summary", "")
            # 按原代码规则优化总结（≤15字，最多1个逗号）
            if len(summary) > 15 or summary.count('，') > 1:
                summary = summary[:15].rsplit('，', 1)[0].strip()
            print(f"优化后亮点总结：{summary}")

            # 3. 教育经历（education）
            education = []
            for edu in resume_data.get("education", []):
                # 提取GPA（从note字段中解析）
                gpa = ""
                note = edu.get("note", "")
                if "GPA" in note or "gpa" in note:
                    gpa_match = re.search(r'GPA[:：]\s*([0-9.]+/[0-9.]+)', note)
                    if gpa_match:
                        gpa = gpa_match.group(1)

                education.append({
                    "school": edu.get("school", ""),
                    "major": edu.get("major", ""),
                    "degree": edu.get("degree", ""),
                    "gpa": gpa,
                    "core_courses": ""  # 新数据中无核心课程，留空
                })

            # 4. 技能（skills）
            skills_list = resume_data.get("skills", [])
            skills_str = "、".join(skills_list) if skills_list else "无"

            # 5. 爱好（hobbies）
            # 从经历描述中提取（新数据无直接hobbies字段）
            hobbies_str = "数据科学研究、算法优化、项目实践"  # 合理默认值，可根据需求调整

            # 组装最终数据（严格匹配HTML模板字段）
            final_data = {
                "header": header,
                "summary": summary,
                "education": education,
                "sections": cluster_result,
                "skills": skills_str,
                "hobbies": hobbies_str
            }

            # 校验最终数据结构
            self.final_render_parser.parse(json.dumps(final_data, ensure_ascii=False))
            print("最终渲染数据构建完成，结构校验通过\n")
            return final_data
        except Exception as e:
            raise RuntimeError(f"构建最终渲染数据失败：{str(e)}")

    # 步骤6：HTML渲染与PDF生成（完全保留原逻辑）
    def render_and_generate_pdf(self, final_data):
        print("===== 步骤6/6：渲染HTML并生成PDF =====")
        try:
            # 渲染HTML
            html = Template(HTML_TEMPLATE).render(**final_data)
            print(f"HTML渲染完成，长度：{len(html)}字符")

            # HTML转PDF
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                page = browser.new_page()
                page.set_content(html)
                page.pdf(
                    path=OUTPUT_PDF_PATH,
                    format='A4',
                    margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                    print_background=True
                )
                browser.close()
            print(f"PDF生成完成：{OUTPUT_PDF_PATH}")

            # 校验PDF页数
            with pdfplumber.open(OUTPUT_PDF_PATH) as pdf:
                page_count = len(pdf.pages)
                print(f"PDF页数校验：{page_count}页")
                if page_count == 1:
                    return True
                else:
                    print("⚠️ 警告：PDF页数不为1页（简历建议1页）")
                    return False
        except Exception as e:
            raise RuntimeError(f"HTML渲染或PDF生成失败：{str(e)}")

    # 主运行流程
    def run(self):
        try:
            # 1. 读取JSON数据
            resume_data, sorted_blocks = self.read_resume_json()

            # 2. 数据预处理（合并经历+绑定匹配度）
            preprocessed_experiences = self.preprocess_experiences(resume_data, sorted_blocks)

            # 3. 经历分层
            core_exps, secondary_exps = self.process_experience_stratification(preprocessed_experiences)

            # 4. 处理核心/次要经历
            structured_cores = self.process_core_experiences(core_exps)
            structured_secondaries = self.process_secondary_experiences(secondary_exps)

            # 5. 经历聚类
            cluster_result = self.process_cluster(structured_cores, structured_secondaries)

            # 6. 构建最终渲染数据
            final_render_data = self.build_final_render_data(resume_data, cluster_result)

            # 7. 渲染HTML并生成PDF
            success = self.render_and_generate_pdf(final_render_data)

            if success:
                print("\n✅ 简历PDF生成成功！文件路径：", OUTPUT_PDF_PATH)
            else:
                print("\n⚠️ 简历PDF生成完成，但存在页数警告，请检查文件")

        except Exception as e:
            print(f"\n❌ 简历生成失败：{str(e)}")

if __name__ == "__main__":
    # 确保依赖安装提示（首次运行用）
    print("⚠️  运行前请确保已安装依赖：")
    print("pip install langchain-core langchain-openai jinja2 playwright pdfplumber openai")
    print("playwright install chromium\n")

    generator = ResumeGenerator()
    generator.run()