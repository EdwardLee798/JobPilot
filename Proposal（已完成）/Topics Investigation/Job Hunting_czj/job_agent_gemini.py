# -*- coding: utf-8 -*-

"""
Job Seeking Agent (Version 4.0 - Final Fix)

此版本根据 debug_page_source.html 的内容，
更新了 BeautifulSoup 的 CSS 选择器，以匹配网站最新的 HTML 结构。
这是网页抓取中非常常见的维护步骤。
"""

import os
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import textwrap
import time

# --- 用于 Selenium 网页自动化的库 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- 1. 配置 AI 模型 ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("请设置 'GOOGLE_API_KEY' 环境变量。")
genai.configure(api_key=api_key)
llm = genai.GenerativeModel('gemini-pro')

# --- 2. 创建一个虚拟简历文件 (用于演示) ---
resume_content = """
王小明
电话: 138-0013-8000 | 邮箱: xiaoming.wang@email.com | GitHub: github.com/xiaomingw

### 教育背景
- 华南科技大学, 计算机科学与技术学士 (2018 - 2022)
  - GPA: 3.7/4.0
  - 相关课程: 数据结构、算法、操作系统、计算机网络

### 项目经历
1. **个人博客系统 (2021)**
   - 使用 Python Django 框架和 SQLite 数据库开发了一个功能完整的博客平台。
   - 实现了文章发布、评论、用户认证等基本功能。
   - 通过这个项目熟悉了 Web 开发的基本流程和 MVC 设计模式。

2. **校园二手书交易平台 (课程设计, 2022)**
   - 一个简单的Web应用，允许学生发布和搜索二手书籍信息。
   - 我负责后端开发，使用 Flask 框架和 SQLAlchemy。
   - 学习了 RESTful API 的基本设计原则。

### 技能清单
- **编程语言**: 精通 Python, 熟悉 Java 和 C++
- **Web框架**: 熟悉 Django 和 Flask
- **数据库**: 了解 SQL, 使用过 SQLite 和 MySQL
- **工具**: Git, Docker (初级)
"""
with open("resume.txt", "w", encoding='utf-8') as f:
    f.write(resume_content)

# -----------------------------------------------------------------------------
# Agent 主类
# -----------------------------------------------------------------------------
class JobSeekingAgent:
    def __init__(self, llm_model):
        self.llm = llm_model
        self.resume_text = ""
        self.job_postings = []
        print("🤖 求职Agent已启动！")

    def load_resume(self, resume_path="resume.txt"):
        try:
            with open(resume_path, 'r', encoding='utf-8') as f:
                self.resume_text = f.read()
            print("📄 简历加载成功。")
        except FileNotFoundError:
            print(f"错误: 简历文件 {resume_path} 未找到。")
            exit()

    # -----------------------------------------------------------------------------
    # Tool 1: 职位信息搜索 (Selenium Version) - 最终修正版
    # -----------------------------------------------------------------------------
    def tool_search_jobs(self, query: str, num_jobs: int = 5) -> list:
        query = query.replace(' ', '+')
        url = f"https://weworkremotely.com/remote-jobs/search?term={query}"
        print(f"\n🔍 [Selenium] 正在启动浏览器并搜索 '{query}' 的职位...")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = None
        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            
            # 等待职位列表容器 section.jobs 出现
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.jobs li")))
            
            page_html = driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')

        except TimeoutException:
            print("❌ 页面加载超时或未找到职位列表容器。")
            if driver:
                driver.save_screenshot("debug_screenshot.png")
                with open("debug_page_source.html", "w", encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("ℹ️ 已保存截图和页面源码供分析。")
                driver.quit()
            return []
        except Exception as e:
            print(f"❌ Selenium 运行时发生错误: {e}")
            if driver:
                driver.quit()
            return []

        # --- 【关键修改: 更新解析逻辑以匹配新HTML结构】---
        scraped_jobs = []
        jobs_list_container = soup.find('section', class_='jobs')
        
        if jobs_list_container:
            # 选择所有 class 包含 'new-listing-container' 的 <li> 标签
            job_items = jobs_list_container.select('li.new-listing-container')

            for item in job_items[:num_jobs]:
                # 根据新的HTML结构提取信息
                title_element = item.select_one('h3.new-listing__header__title')
                company_element = item.select_one('p.new-listing__company-name')
                # 职位详情链接是 li 标签下的第二个 a 标签
                link_element = item.select_one('a[href*="/remote-jobs/"]')
                
                if title_element and company_element and link_element:
                    title = title_element.text.strip()
                    company = company_element.text.strip()
                    job_link = "https://weworkremotely.com" + link_element['href']
                    
                    scraped_jobs.append({
                        "title": title,
                        "company": company,
                        "description": f"职位: {title}\n公司: {company}\n详情请访问: {job_link}\n(注意: 为提高效率, 未爬取详细描述, AI将基于此信息进行分析)"
                    })
        
        if not scraped_jobs:
            print("成功访问网站，但在页面上未解析出任何职位信息。可能是CSS选择器需要再次更新。")
        else:
            print(f"✅ [Selenium] 成功找到 {len(scraped_jobs)} 个相关职位。")
            
        self.job_postings = scraped_jobs
        driver.quit()
        return scraped_jobs
        
    def tool_optimize_resume(self, job_description: str) -> str:
        # ... (此函数及后续函数无需修改) ...
        print("\n✨ 正在为您生成定制化简历优化建议...")
        prompt = f"""
        你是一位顶级的IT职业规划师和简历优化专家。
        请严格按照下面的【岗位描述】，优化这份【原始简历】。

        你的任务是：
        1.  **精准匹配**: 修改【原始简历】中的项目经历和技能描述，使其语言风格和技术关键词与【岗位描述】高度对齐。
        2.  **成果导向**: 将项目经历中的描述从“做了什么”改为“取得了什么成就”。如果可以，尝试用数字来量化成果（例如：将处理效率提升了15%）。
        3.  **突出亮点**: 根据【岗位描述】的要求，将简历中最相关的技能和项目经验调整到更突出的位置。
        4.  **直接输出优化后的简历**: 不要说“以下是优化后的简历”之类的话，直接给我优化后的完整简历文本。

        ---
        【岗位描述】:
        {job_description}
        ---
        【原始简历】:
        {self.resume_text}
        ---

        请输出优化后的简历全文：
        """
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"调用AI模型失败: {e}"

    def tool_supplement_materials(self, job_description: str) -> str:
        # ... (此函数无需修改) ...
        print("\n🔬 正在分析您的技能短板并提供学习建议...")
        prompt = f"""
        你是一位资深的软件工程师面试官。请深入对比分析下面的【求职者简历】和【岗位要求】，以帮助这位求职者准备面试。

        你的任务是生成一份详细的【求职者能力提升和面试准备报告】，包含以下三个部分，并严格使用Markdown格式化输出：

        **1. 技能差距分析 (Gap Analysis):**
           - 明确列出【岗位要求】中提到，但【求职者简历】中完全没有体现或体现不足的关键技能点。
           - 对每个技能点进行简要说明，解释为什么它对这个岗位很重要。

        **2. 知识强化路径 (Learning Path):**
           - 针对每一个短板，提供一个具体的、可执行的学习计划。
           - 例如：推荐需要学习的特定技术库、值得看的在线课程（只需说出课程主题和平台，如 Coursera 上的 "Advanced Python"），或建议完成的实战项目类型。

        **3. 核心面试题预测 (Interview Prep):**
           - 列出3-5个针对该岗位最可能被问到的核心技术问题（“八股文”）。
           - 为每个问题提供一个简洁但精准的回答思路或要点。

        ---
        【岗位要求】:
        {job_description}
        ---
        【求职者简历】:
        {self.resume_text}
        ---

        请开始生成报告：
        """
        try:
            response = self.llm.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"调用AI模型失败: {e}"

    def run(self, job_query: str):
        # ... (此函数无需修改) ...
        self.load_resume()
        self.tool_search_jobs(job_query)
        if not self.job_postings:
            print("未能找到相关职位，程序退出。")
            return

        target_job = self.job_postings[0]
        print(f"\n🎯 已锁定目标职位：【{target_job['title']}】 at 【{target_job['company']}】")
        print("-------------------- 职位描述预览 --------------------")
        print(textwrap.fill(target_job['description'], width=80))
        print("----------------------------------------------------\n")

        optimized_resume = self.tool_optimize_resume(target_job['description'])
        print("\n\n=============== 🚀 优化后的简历建议 ================")
        print(optimized_resume)
        print("====================================================\n\n")

        gap_analysis_report = self.tool_supplement_materials(target_job['description'])
        print("=============== 💡 个人能力提升报告 ================")
        print(gap_analysis_report)
        print("====================================================")


# --- 主程序入口 ---
if __name__ == '__main__':
    agent = JobSeekingAgent(llm_model=llm)
    agent.run("Python Developer")