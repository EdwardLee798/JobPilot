"""
Agent工具函数和配置
整合自Func4_StatusTracking
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
import pandas as pd
import time
from datetime import datetime, timedelta
import os
import sqlite3

# 加载环境变量
load_dotenv()

# 配置路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_DIR = os.path.join(DATA_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'tracking.db')

username = "Student"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# 1. 定义Schema和工具函数
class AppProcessCreaterSchema(BaseModel):
    job_title: str = Field(description="求职岗位的职位名称。")
    company_name: str = Field(description="求职岗位的公司名称。")
    job_description: str = Field(description="一段对岗位工作内容以及任职要求的详细描述。")
    tracking_method: str = Field(description="用户所提供的求职流程跟进方式，可以是手机号码、邮箱地址或其它方式。")


@tool(args_schema=AppProcessCreaterSchema)
def app_process_creater(job_title: str, company_name: str, job_description: str, tracking_method: str) -> str:
    """
    当用户新增一个需要跟踪的职位网申流程时，请调用该函数。
    该函数可以将用户输入中的岗位描述信息，以及求职流程跟进方式信息，以结构化的方式存储到数据库中。
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 插入到job_summary
        cursor.execute('''
            INSERT INTO job_summary (job_title, company_name, job_desc, tracking_method)
            VALUES (?, ?, ?, ?)
        ''', (job_title, company_name, job_description, tracking_method))
        
        job_id = cursor.lastrowid
        
        # 插入初始状态
        cursor.execute('''
            INSERT INTO application_status (job_id, status_update, event_time)
            VALUES (?, ?, ?)
        ''', (job_id, "已申请", time.time()))
        
        conn.commit()
        conn.close()
        
        return "网申信息已保存。"
    except Exception as e:
        return f"网申信息未正确保存：{e}"


def app_process_query(job_title: str | None = None, company_name: str | None = None, return_jd: bool = False) -> list:
    """查询申请流程"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if return_jd:
            query = '''
                SELECT s.company_name, s.job_title, a.status_update, a.event_time, s.job_desc
                FROM job_summary s
                JOIN application_status a ON s.job_id = a.job_id
            '''
        else:
            query = '''
                SELECT s.company_name, s.job_title, a.status_update, a.event_time
                FROM job_summary s
                JOIN application_status a ON s.job_id = a.job_id
            '''
        
        conditions = []
        params = []
        
        if job_title:
            conditions.append("s.job_title = ?")
            params.append(job_title)
        if company_name:
            conditions.append("s.company_name = ?")
            params.append(company_name)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        # 格式化结果
        formatted = []
        for row in results:
            row_list = list(row)
            # 格式化时间
            if row_list[3] and row_list[3] > 0:
                row_list[3] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row_list[3]))
            else:
                row_list[3] = "N/A"
            formatted.append(row_list)
        
        return formatted
    except Exception as e:
        return []


class AppProcessReaderSchema(BaseModel):
    job_title: Optional[str] = Field(None, description="求职岗位的职位名称，可以为空。")
    company_name: Optional[str] = Field(None, description="求职岗位的公司名称，可以为空。")
    return_jd: bool = Field(False, description="是否查询职位描述。")


@tool(args_schema=AppProcessReaderSchema)
def app_process_reader(job_title: str | None = None, company_name: str | None = None, return_jd: bool = False) -> list:
    """
    当需要查询某个公司的某个职位、或某个公司的、或所有的申请流程时，请调用该函数。
    该函数可以从数据库中获取职位的申请流程信息。
    """
    return app_process_query(job_title, company_name, return_jd)


@tool(args_schema=AppProcessReaderSchema)
def is_app_new(job_title: str | None = None, company_name: str | None = None) -> bool:
    """
    当需要区分用户输入的职位是新申请的还是后续更新的时，请调用该函数。
    该函数可以在数据库中查询该职位是否有记录。
    """
    results = app_process_query(job_title, company_name)
    return len(results) == 0


current_year = datetime.now().year


class AppProcessUpdaterSchema(BaseModel):
    job_title: str = Field(description="求职岗位的职位名称。")
    company_name: str = Field(description="求职岗位的公司名称。")
    event: str = Field(description="求职岗位的申请进度事件，如笔试、面试、一面、二面、三面、hr面、主管面等。")
    not_end: bool = Field(True, description=f"求职岗位的申请进度事件是否是流程终止，若是流程终止则为False")
    event_time_year: Optional[float] = Field(current_year, description=f"求职岗位进行笔试或面试的年份，若流程终止则为None")
    event_time_month: Optional[float] = Field(1, description=f"求职岗位进行笔试或面试的月份，若流程终止则为None")
    event_time_day: Optional[float] = Field(1, description=f"求职岗位进行笔试或面试的日期，若流程终止则为None")
    event_time_hour: Optional[float] = Field(8, description=f"求职岗位进行笔试或面试的时间，具体到小时，若流程终止则为None")
    event_time_minute: Optional[float] = Field(0, description=f"求职岗位进行笔试或面试的时间，具体到分钟，若流程终止则为None")


@tool(args_schema=AppProcessUpdaterSchema)
def app_process_updater(job_title: str, 
                        company_name: str, 
                        event: str, 
                        not_end: bool = True,
                        event_time_year: float | None = current_year,
                        event_time_month: float | None = 1,
                        event_time_day: float | None = 1,
                        event_time_hour: float | None = 8,
                        event_time_minute: float | None = 0) -> str:
    """
    当用户输入某个职位申请的后续流程时，请先调用`is_app_new`工具判断用户需要记录的职位是新申请的还是后续更新的，
    若`is_app_new`返回 True 则调用`app_process_creater`函数，若`is_app_new`返回 False 则调用该函数。
    该函数可以在数据库中新增该职位当前的申请进度。
    """
    try:
        if not_end:
            event_time = datetime(
                year=int(event_time_year) if event_time_year >= current_year else current_year,
                month=int(event_time_month),
                day=int(event_time_day),
                hour=int(event_time_hour),
                minute=int(event_time_minute),
            ).timestamp()
        else:
            event_time = -100.0
        
        if event_time == -100.0:
            event = "流程终止"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取job_id
        cursor.execute('''
            SELECT job_id FROM job_summary
            WHERE job_title = ? AND company_name = ?
        ''', (job_title, company_name))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return "更新失败：尚未创建网申记录。"
        
        job_id = result['job_id']
        
        # 检查是否已存在该状态
        cursor.execute('''
            SELECT id FROM application_status
            WHERE job_id = ? AND status_update = ?
        ''', (job_id, event))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute('''
                UPDATE application_status
                SET event_time = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (event_time, existing['id']))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO application_status (job_id, status_update, event_time)
                VALUES (?, ?, ?)
            ''', (job_id, event, event_time))
        
        conn.commit()
        conn.close()
        
        return "成功更新职位状态。"
    except Exception as e:
        return f"更新失败：{e}"


# System Prompt
SYSTEM_PROMPT = """
你是一名经验丰富的职位网申流程管理师，擅长帮助用户高效完成以下任务：

1. **新增网申流程跟踪：**
   - 当用户新增一个需要跟踪的职位网申流程时，请先调用`is_app_new`工具判断用户需要记录的职位是新申请的还是后续更新的，若`is_app_new`返回 True 则调用`app_process_creater`工具，若`is_app_new`返回 False 则调用`app_process_updater`工具。
   - 你需要根据用户提供的信息抽取出求职岗位的职位名称，公司名称，职位描述，网申流程的跟进方式，输入到`app_process_creater`中即可。
   - 注意在抽取职位名称和公司名称时不要加入空格。
   
2. **网申流程状态查询：**
   - 当用户查询某个职位的申请流程时，请调用`app_process_reader`工具。
   - 你需要根据用户提供的信息抽取出求职岗位的职位名称，公司名称，输入到`app_process_reader`中即可。
   - 注意在抽取职位名称和公司名称时不要加入空格。

3. **网申流程状态更新：**
   - 当用户输入某个职位申请的后续流程时，请先调用`is_app_new`工具判断用户需要记录的职位是新申请的还是后续更新的，若`is_app_new`返回 True 则调用`app_process_creater`工具，若`is_app_new`返回 False 则调用`app_process_updater`工具。
   - 你需要根据用户提供的信息抽取出求职岗位的职位名称，公司名称，申请进度事件，再根据申请进度事件是否是笔面试判断是否需要解析出笔面试的时间参数（如果申请状态的内容是流程终止则不需要解析这个参数），输入到`app_process_updater`中即可。
   - 注意在抽取职位名称和公司名称时不要加入空格；
   - 注意申请进度事件尽量解析为简明扼要的事件，如笔试、面试、一面、二面、三面、hr面、主管面、线下笔试等。
   
4. **根据网申查询到的网申状态为用户生成排期规划：**
   - 当用户需要规划某个岗位（或某个公司的所有岗位或所有已记录岗位）后续的笔面试流程时，请调用`app_process_reader`工具，注意在调用时将return_jd参数设为True，根据返回的笔面试日期和岗位描述生成详细合理的日程规划。

5. **为用户进行排期规划：**
   - 当用户需要进行排期规划时，请调用`app_process_reader`工具，查看未来申请流程的时间安排，根据用户需要规划的时间段生成合理的规划。
   
**回答要求：**
- 所有回答均使用**简体中文**，清晰、礼貌、简洁。
- 如果调用工具返回结构化JSON数据，你应提取其中的关键信息简要说明，并展示主要结果。
- 若需要用户提供更多信息，请主动提出明确的问题。

**风格：**
- 专业、简洁、以数据驱动。
- 不要编造不存在的工具或数据。

请根据以上原则为用户提供精准、高效的协助。
"""

# 初始化模型和Agent
try:
    model = ChatOpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus",
        max_retries=3,
        api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
        extra_body={"enable_search": True}
    )
    
    tools = [app_process_creater, app_process_reader, is_app_new, app_process_updater]
    agent = create_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, debug=False)
    
except Exception as e:
    print(f"Warning: Failed to initialize agent: {e}")
    agent = None


def invoke_agent(message: str, thread_id: str = "default") -> dict:
    """调用agent处理用户消息"""
    if not agent:
        return {"error": "Agent未初始化"}
    
    try:
        config = RunnableConfig(configurable={"thread_id": thread_id})
        response = agent.invoke(
            input={"messages": [("user", message)]},
            config=config
        )
        return {
            "content": response['messages'][-1].content,
            "success": True
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }


def stream_agent(message: str, thread_id: str = "default"):
    """流式调用agent，返回中间步骤和最终结果"""
    if not agent:
        yield {"type": "error", "message": "Agent未初始化"}
        return
    
    try:
        config = RunnableConfig(configurable={"thread_id": thread_id})
        
        for chunk in agent.stream(
            {"messages": [("user", message)]},
            config=config,
            stream_mode="values"
        ):
            latest_message = chunk["messages"][-1]
            
            # 如果是工具调用
            if hasattr(latest_message, 'tool_calls') and latest_message.tool_calls:
                for tool_call in latest_message.tool_calls:
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_call.get('name', '未知工具'),
                        "tool_args": tool_call.get('args', {})
                    }
            
            # 如果是文本内容
            elif hasattr(latest_message, 'content') and latest_message.content:
                yield {
                    "type": "content",
                    "content": latest_message.content
                }
        
        yield {"type": "done"}
        
    except Exception as e:
        yield {"type": "error", "message": str(e)}
