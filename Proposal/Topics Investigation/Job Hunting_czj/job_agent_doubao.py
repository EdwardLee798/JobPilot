# -*- coding: utf-8 -*-
"""
Job Seeking Agent (Version 5.0 - 火山方舟豆包API版)
适配火山方舟平台豆包API，实现职位搜索、简历优化和能力分析
"""

import os
import textwrap
from openai import OpenAI
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 火山方舟API配置
ARK_API_KEY = os.getenv("ARK_API_KEY")
if not ARK_API_KEY:
    raise ValueError("请设置 'ARK_API_KEY' 环境变量")

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=ARK_API_KEY
)

def call_ark_doubao_api(prompt, model="doubao-seed-1-6-250615", temperature=0.7):
    """调用火山方舟豆包模型生成内容"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"调用失败: {str(e)}"


class JobSeekingAgent:
    def __init__(self):
        self.resume_text = ""
        self.job_postings = []
        print("🤖 求职Agent已启动")

    def load_resume(self, resume_path="/Users/zijiancai/Desktop/hkucs files/comp7607/find_job_agent/resume.txt"):
        try:
            with open(resume_path, 'r', encoding='utf-8') as f:
                self.resume_text = f.read()
            print("📄 简历加载成功")
        except FileNotFoundError:
            print(f"错误: 简历文件 {resume_path} 未找到")
            exit()

    def tool_search_jobs(self, query: str, num_jobs: int = 5) -> list:
        query = query.replace(' ', '+')
        url = f"https://weworkremotely.com/remote-jobs/search?term={query}"
        print(f"\n🔍 正在搜索 '{query}' 职位...")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/108.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = None
        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.jobs li")))
            page_html = driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')

        except TimeoutException:
            print("❌ 页面加载超时")
            if driver:
                driver.save_screenshot("debug_screenshot.png")
                with open("debug_page_source.html", "w", encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("ℹ️ 已保存调试信息")
                driver.quit()
            return []
        except Exception as e:
            print(f"❌ Selenium 错误: {e}")
            if driver:
                driver.quit()
            return []

        scraped_jobs = []
        jobs_list_container = soup.find('section', class_='jobs')
        if jobs_list_container:
            job_items = jobs_list_container.select('li.new-listing-container')
            for item in job_items[:num_jobs]:
                title_element = item.select_one('h3.new-listing__header__title')
                company_element = item.select_one('p.new-listing__company-name')
                link_element = item.select_one('a[href*="/remote-jobs/"]')
                if title_element and company_element and link_element:
                    title = title_element.text.strip()
                    company = company_element.text.strip()
                    job_link = "https://weworkremotely.com" + link_element['href']
                    scraped_jobs.append({
                        "title": title,
                        "company": company,
                        "description": f"职位: {title}\n公司: {company}\n详情: {job_link}"
                    })
        
        if not scraped_jobs:
            print("未解析出职位信息，可能需要更新CSS选择器")
        else:
            print(f"✅ 找到 {len(scraped_jobs)} 个职位")
            
        self.job_postings = scraped_jobs
        driver.quit()
        return scraped_jobs
        
    def tool_optimize_resume(self, job_description: str) -> str:
        print("\n✨ 生成简历优化建议...")
        prompt = f"""
        你是IT职业规划师，请按岗位描述优化简历：
        1. 精准匹配技术关键词
        2. 成果导向（用数字量化）
        3. 突出相关亮点
        4. 直接输出优化后简历

        ---
        岗位描述:
        {job_description}
        ---
        原始简历:
        {self.resume_text}
        ---
        """
        return call_ark_doubao_api(prompt)

    def tool_supplement_materials(self, job_description: str) -> str:
        print("\n🔬 分析技能短板...")
        prompt = f"""
        你是软件工程师面试官，请生成能力提升报告：
        1. 技能差距分析
        2. 知识强化路径
        3. 核心面试题预测

        ---
        岗位要求:
        {job_description}
        ---
        求职者简历:
        {self.resume_text}
        ---
        """
        return call_ark_doubao_api(prompt)

    def run(self, job_query: str):
        self.load_resume()
        self.tool_search_jobs(job_query)
        if not self.job_postings:
            print("未找到职位，程序退出")
            return

        target_job = self.job_postings[0]
        print(f"\n🎯 目标职位：【{target_job['title']}】 at 【{target_job['company']}】")
        print("-------------------- 职位描述 --------------------")
        print(textwrap.fill(target_job['description'], width=80))
        print("--------------------------------------------------\n")

        optimized_resume = self.tool_optimize_resume(target_job['description'])
        print("\n\n=============== 优化后的简历 ================")
        print(optimized_resume)
        print("============================================\n\n")

        gap_analysis_report = self.tool_supplement_materials(target_job['description'])
        print("=============== 能力提升报告 ================")
        print(gap_analysis_report)
        print("=============================================")

if __name__ == '__main__':
    agent = JobSeekingAgent()
    agent.run("Python Developer")