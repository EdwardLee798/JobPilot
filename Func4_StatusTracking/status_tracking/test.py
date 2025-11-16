# from langchain.chat_models import init_chat_model
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
# from typing import Annotated
# from typing_extensions import TypedDict

import os
print(os.path.abspath('.env'))
load_dotenv(dotenv_path=os.path.abspath('.env'), override=True)
username = "Student"

# 1. define relevant schema and tools
class AppProcessCreaterSchema(BaseModel):
    job_title: str = Field(description="求职岗位的职位名称。")
    company_name: str = Field(description="求职岗位的公司名称。")
    job_description: str = Field(description="一段对岗位工作内容以及任职要求的详细描述。")
    tracking_method: str = Field(description="用户所提供的求职流程跟进方式，可以是手机号码、邮箱地址或其它方式。")

@tool(args_schema=AppProcessCreaterSchema)
def app_process_creater(job_title: str, company_name: str, job_description: str, tracking_method: str) -> str:
    """
    当用户新增一个需要跟踪的职位网申流程时，请调用该函数。
    该函数可以将用户输入中的岗位描述信息，以及求职流程跟进方式信息，以结构化的方式存储到记录该用户求职总览信息的CSV文件中，并创建一条求职流程记录存储到该用户求职流程信息的CSV文件中。
    :param job_title: 求职岗位的职位名称。
    :param company_name: 求职岗位的公司名称。
    :param job_description: 一段对岗位工作内容以及任职要求的详细描述。
    :param tracking_method: 用户所提供的求职流程跟进方式，可以是手机号码、邮箱地址或其它方式。
    :return: CSV保存结果。
    """
    try:
        file_root = Path("./tables")
        summary_file_name = f"{username}_job_tracking_summary.csv"
        summary_file = list(file_root.glob(summary_file_name))
        if summary_file:
            assert len(summary_file) == 1
            summary_file_path = str(summary_file[0])
            summary = pd.read_csv(summary_file_path, encoding="utf-8")
            last_line = summary.iloc[-1]
            job_id = last_line.job_id + 1
        else:
            summary_file_path = file_root.joinpath(summary_file_name)
            summary = pd.DataFrame(columns=["job_id", "job_title", "company_name", "job_desc", "tracking_method", "timestamp"])
            job_id = 1
        new_summary = pd.concat([summary, pd.DataFrame([[job_id, job_title, company_name, job_description, tracking_method, time.time()]], columns=summary.columns)], ignore_index=True)
        new_summary.to_csv(summary_file_path, index=False, encoding="utf-8")

        app_status_file_name = f"{username}_application_status.csv"
        app_status_file = list(file_root.glob(app_status_file_name))
        if app_status_file:
            assert len(app_status_file) == 1
            app_status_file_path = str(app_status_file[0])
            app_status = pd.read_csv(app_status_file_path, encoding="utf-8")
        else:
            app_status_file_path = file_root.joinpath(app_status_file_name)
            app_status = pd.DataFrame(columns=["job_id", "status_update", "event_time", "timestamp"])
        new_app_status = pd.concat([app_status, pd.DataFrame([[job_id, "已申请", time.time(), time.time()]], columns=app_status.columns)])
        new_app_status.to_csv(app_status_file_path, index=False, encoding="utf-8")

        return "网申信息已保存。"
    except Exception as e:
        return f"网申信息未正确保存：{e}"

def app_process_query(job_title: str | None = None, company_name: str | None = None, return_jd: bool = False) -> list:
    file_root = Path("./tables")
    app_status_file_name = f"{username}_application_status.csv"
    summary_file_name = f"{username}_job_tracking_summary.csv"
    app_status_file = list(file_root.glob(app_status_file_name))
    summary_file = list(file_root.glob(summary_file_name))
    if app_status_file and summary_file:
        summary_file_path = str(summary_file[0])
        app_status_file_path = str(app_status_file[0])
        summary = pd.read_csv(summary_file_path, encoding="utf-8")
        app_status = pd.read_csv(app_status_file_path, encoding="utf-8")
        join = pd.merge(summary, app_status, on=["job_id"])
        if return_jd:
            return_columns = ["company_name", "job_title", "status_update", "job_desc"]
        else:
            return_columns = ["company_name", "job_title", "status_update"]
        if job_title is None and company_name is None:
            return join[return_columns].values.tolist()
        elif job_title is None:
            return join[join.company_name == company_name][return_columns].values.tolist()
        elif company_name is None:
            join = pd.merge(summary, app_status, on=["job_id"])
            return join[join.job_title == job_title][return_columns].values.tolist()
        else:
            return join[(join.job_title == job_title) & (join.company_name == company_name)][return_columns].values.tolist()
    else:
        return []

class AppProcessReaderSchema(BaseModel):
    job_title: Optional[str] = Field(None, description="求职岗位的职位名称。")
    company_name: Optional[str] = Field(None, description="求职岗位的公司名称。")
    return_jd: bool = Field(False, description="是否查询职位描述。")

@tool(args_schema=AppProcessReaderSchema)
def app_process_reader(job_title: str | None = None, company_name: str | None = None, return_jd: bool = False) -> list:
    """
    当用户需要查询某个职位的申请流程时，请调用该函数。
    该函数可以从求职流程信息记录文件中获取该职位的。
    :param job_title: 求职岗位的职位名称。
    :param company_name: 求职岗位的公司名称。
    :param return_jd: 是否查询职位描述。
    :return: 返回查询结果，若 job_title 为 None，返回所有 company_name 的查询结果，若 company_name 为 None，返回所有 job_title 的查询结果，若都为 None，返回所有结果。
    """
    return app_process_query(job_title, company_name, return_jd)

@tool(args_schema=AppProcessReaderSchema)
def is_app_new(job_title: str | None = None, company_name: str | None = None) -> bool:
    """
    当需要区分用户输入的职位是新申请的还是后续更新的时，请调用该函数。
    该函数可以在求职流程信息记录文件中查询该职位是否有记录。
    :param job_title: 求职岗位的职位名称。
    :param company_name: 求职岗位的公司名称。
    :return: 返回该职位是否不在已记录的职位中，False表示有记录，True表示没有记录。
    """
    if app_process_query(job_title, company_name):
        return False
    else:
        return True

current_year = datetime.now().year
class AppProcessUpdaterSchema(BaseModel):
    job_title: str = Field(description="求职岗位的职位名称。")
    company_name: str = Field(description="求职岗位的公司名称。")
    event: str = Field(description="求职岗位的申请进度事件，如笔试、面试、一面、二面、三面、hr面、主管面等。")
    event_time: Optional[float] = Field(None, description=f"求职岗位进行笔试或面试的时间戳，若流程终止则为None")

@tool(args_schema=AppProcessUpdaterSchema)
def app_process_updater(job_title: str, company_name: str, event: str, event_time: float | None = None) -> str:
    """
    当用户输入某个职位申请的后续流程时，请先调用调用`is_app_new`工具判断用户需要记录的职位是新申请的还是后续更新的，若`is_app_new`返回 True 则调用`app_process_creater`函数，若`is_app_new`返回 False 则调用该函数。
    该函数可以在求职流程信息记录文件中新增该职位当前的申请进度。
    :param job_title: 求职岗位的职位名称。
    :param company_name: 求职岗位的公司名称。
    :param event: 求职岗位的申请进度事件，如笔试、面试、一面、二面、三面、hr面、主管面等。
    :param event_time: 求职岗位进行笔试或面试的时间戳，若 `event` 解析的含义是流程终止则为None。
    :return: 返回记录结果。
    """
    if event_time is not None:
        # print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event_time)))
        if event_time < time.time():
            event_time = datetime.fromtimestamp(event_time) + timedelta(days=365 * (current_year - 2024))
            event_time = event_time.timestamp()
        # print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event_time)))
    else:
        event_time = -100.0
    
    if event_time == -100.0:
        event = "流程终止"

    file_root = Path("./tables")
    app_status_file_name = f"{username}_application_status.csv"
    summary_file_name = f"{username}_job_tracking_summary.csv"
    app_status_file = list(file_root.glob(app_status_file_name))
    summary_file = list(file_root.glob(summary_file_name))
    if app_status_file and summary_file:
        summary_file_path = str(summary_file[0])
        app_status_file_path = str(app_status_file[0])
        summary = pd.read_csv(summary_file_path, encoding="utf-8")
        app_status = pd.read_csv(app_status_file_path, encoding="utf-8")
        job_id = summary[(summary.job_title == job_title) & (summary.company_name == company_name)].iloc[0].job_id
        if app_status[(app_status.job_id == job_id) & (app_status.status_update == event)].shape[0] > 0:
            idx = app_status[(app_status.job_id == job_id) & (app_status.status_update == event)].index[-1]
            app_status.loc[idx, "event_time"] = event_time
            app_status.loc[idx, "timestamp"] = time.time()
            # print(app_status[app_status.job_id == job_id])
        else:
            new_status = pd.DataFrame([[job_id, event, event_time, time.time()]], columns=app_status.columns)
            app_status = pd.concat([app_status, new_status])
        app_status.to_csv(app_status_file_path, index=False, encoding="utf-8")
        return "成功更新职位状态。"
    else:
        "更新失败：尚未创建网申记录。"


# system prompt
prompt = """
你是一名经验丰富的职位网申流程管理师，擅长帮助用户高效完成以下任务：

1. **新增网申流程跟踪：**
   - 当用户新增一个需要跟踪的职位网申流程时，请先调用调用`is_app_new`工具判断用户需要记录的职位是新申请的还是后续更新的，若`is_app_new`返回 True 则调用`app_process_creater`工具，若`is_app_new`返回 False 则调用`app_process_updater`工具。
   - 你需要根据用户提供的信息抽取出求职岗位的职位名称，公司名称，职位描述，网申流程的跟进方式，输入到`app_process_creater`中即可。
   - 注意在抽取职位名称和公司名称时不要加入空格。
   
2. **网申流程状态查询：**
   - 当用户查询某个职位的申请流程时，请调用`app_process_reader`工具。
   - 你需要根据用户提供的信息抽取出求职岗位的职位名称，公司名称，输入到`app_process_reader`中即可。
   - 注意在抽取职位名称和公司名称时不要加入空格。

3. **网申流程状态更新：**
   - 当用户输入某个职位申请的后续流程时，请先调用调用`is_app_new`工具判断用户需要记录的职位是新申请的还是后续更新的，若`is_app_new`返回 True 则调用`app_process_creater`工具，若`is_app_new`返回 False 则调用`app_process_updater`工具。
   - 你需要根据用户提供的信息抽取出求职岗位的职位名称，公司名称，申请进度事件，再根据申请进度事件是否是笔面试判断是否需要解析出笔面试的时间戳参数（如果申请状态的内容是流程终止则不需要解析这个参数），输入到`app_process_updater`中即可。
   - 注意在抽取职位名称和公司名称时不要加入空格；
   - 注意申请进度事件尽量解析为简明扼要的事件，如笔试、面试、一面、二面、三面、hr面、主管面、线下笔试等。
   
4. **根据网申查询到的网申状态为用户生成排期规划：**
   - 当用户需要规划某个岗位（或某个公司的所有岗位或所有已记录岗位）后续的笔面试流程时，请调用`app_process_reader`工具，注意在调用时将:param return_jd:参数设为True，根据返回的笔面试日期和岗位描述生成详细合理的日程规划。

**回答要求：**
- 所有回答均使用**简体中文**，清晰、礼貌、简洁。
- 如果调用工具返回结构化JSON数据，你应提取其中的关键信息简要说明，并展示主要结果。
- 若需要用户提供更多信息，请主动提出明确的问题。

**风格：**
- 专业、简洁、以数据驱动。
- 不要编造不存在的工具或数据。

请根据以上原则为用户提供精准、高效的协助。
"""

# init model
# model = init_chat_model(model="deepseek-chat", model_provider="deepseek")
model = ChatTongyi(
    model="qwen-plus",
)

# create tool list
tools = [app_process_creater, app_process_reader, is_app_new, app_process_updater]

# create agent
# memory = MemorySaver()
# agent = create_agent(model=model, tools=tools, system_prompt=prompt, checkpointer=memory, debug=True)
agent = create_agent(model=model, tools=tools, system_prompt=prompt, debug=True)


config = RunnableConfig(configurable={"thread_id": username})

if __name__ == "__main__":
    while True:
        message = input("输入：")
        if message == "exit":
            print("本轮对话结束，期待再次为您服务！")
            break
        response = agent.invoke(
            input={"messages": [("user", message)]},
            config=config
        )
        print(response['messages'][-1].content)

# class State(TypedDict):
#     messages: Annotated[list, add_messages]

# graph_builder = StateGraph(State)

# def chatBotNode(s: State) -> State:
#     return {"messages": [model.invoke(s["messages"])]}

# graph_builder.add_node("chatbot", chatBotNode)

# graph_builder.add_edge(START, "chatbot")
# graph_builder.add_edge("chatbot", END)

# graph = graph_builder.compile()
# graph_image = Image(graph.get_graph(xray=True).draw_mermaid_png())
# with open("output_image.jpg", "wb") as f:
#     f.write(graph_image.data)

# mesg = {"messages": ["你好，请介绍一下自己。"]}
# response = graph.invoke(mesg)
# print(response)
# # print(response.content)

# 我申请了 Name of company/institution: 上海阶跃星辰智能科技有限公司 Position: 大语言模型预训练算法研究员 Job Description: 1. 参与大语言模型的算法研究和开发工作，包括但不限于模型架构设计、优化和 改进； 2. 负责大语言模型的预训练和调优，包括数据预处理、模型训练和评估等； 3. 参与大语言模型的评测和分析工作，包括建立 in-house 的测评集、编写评测代 码、分析评测结果等； 4. 参与大语言模型的应用开发工作，包括编写应用代码、优化应用性能等； 5. 参与撰写相关技术报告和论文。 Requirements: 1. 熟练掌握 Python 编程语言，熟悉机器学习和深度学习的基本原理和算法； 2. 熟悉自然语言处理的基本原理和算法，有相关项目经验者优先； 3. 熟悉大语言模型的原理和应用，了解当前大语言模型的最新进展； 4. 有良好的团队合作精神和沟通能力，能够与团队成员密切合作，共同推进项目 进展。跟踪方式： 邮箱。
# 我申请了 Name of company/institution: 国家集成电路创新中心 NICIC Position: 软件-图像算法工程师 (Intern) Job Description: Work with chip design engineers to design image classification, recognition, and tracking algorithm models that are compatible with efficient edge hardware. For example, we tailored models such as YOLO and OS Track, split the unit operations of these operators, and evaluated and improved the performance of these operators (speed and hardware resource usage). Needed: 1. Hardworking 2. Self-driven 3. Good expressive skills. Training and Guidance: A mentor will be assigned and basic training and reference documents will be provided in the first two weeks. Key Domain(s)/Skills Category: Multimedia Computing, Artificial Intelligence, Programming, Algorithms and Machine Learning Other Domain(s)/Skills: Python Programming, Office Word/EXCEL/PPT, Thesis Writing。跟踪方式： 手机。
# 我申请了 Name of company/institution: 上海阶跃星辰智能科技有限公司 Position: 语音（多模态）算法研究员 Job Description: 1. 参与语音合成模型的调优和性能分析，协助发现和解决实际应用中的技术问题； 2. 进行大规模语音数据的预处理、标注和数据增强工作，支持模型的训练和评估； 3. 快速学习并应用最新的研究成果，开展实验，发表高质量学术论文。 Requirements: 1. 在读本科或研究生，计算机科学、电子工程、信息科学、信号处理或相关专业； 2. 熟悉机器学习和深度学习的基本原理，有使用深度学习框架如 TensorFlow, PyTorch 的经验； 3. 熟练掌握 Python，有良好的编程习惯和代码风格； 4. 积极主动，具有较强的学习能力和解决问题的能力； 5. 良好的团队合作和沟通能力，能够在导师的指导下进行研究和开发工作。跟踪方式： 邮箱。
# 我申请了 Name of company/institution: ONERWAY Position: 数据分析实习生 Job Description: 1. 协助日常数据分析事项：对业务数据进⾏探索和分析，发现潜在规律、趋势和 问题点，并定期向团队汇报分析结果； 2. 协助建模：在导师指导下，参与算法模型的搭建、验证和初步应用工作（如客 户分群、预测模型等），从而提升分析效率； 3. 协助风控运营：负责日常交易风险监控和异常处理，优化告警规则，配置风控 调整策略； 4. 参与数据平台建设：使⽤SUPERSET 工具制作全英文的可视化看板； 5. 其他数据支持事项：包括使用 SQL 等工具从公司数据库中提取数据，业务数据 答疑等。 Key Domain(s)/Skills Category: /跟踪方式： 手动。
# 我申请了 Name of company/institution: 广发基金 Position: 量化研究实习生 (深度学习、机器学习、强化学习方向） Job Description: 利用 AI 技术对金融市场数据进行深入分析，构建预测市场价格、波动性、情绪等的模 型（如 Transformer、GCN、多任务等）；能够诊断模型问题（如过拟合、欠拟合、 梯度问题、收敛性）并运用合适技术解决；设计模型评估方案（IC、IR、收益、稳定 性、解释性等），并推动模型诊断与迭代。 Requirements: 1. 计算机科学、数学、物理、统计学相关专业硕士或以上学历（在读），拥有扎 实的数学基础和计算机编程能力； 2. 熟悉深度学习算法和模型，具备创新研究能力； 3. 良好的逻辑思维、沟通协调和自我学习能力，主动负责，严谨细致，勤奋踏实。跟踪方式： 手动。
# 我申请了 Name of company/institution: ONERWAY Position: AI 应用开发实习生 Job Description: 1. 开发内部通用场景的 AI 应用，包括但不限于：基于 RAG 的知识库检索及后端 数据的离线链路，为合规/运营/审核使用的 AI 提效工具等； 2. 负责自研的基于 React 框架下的多 AGENT 交互框架； 3. 整合优化内部已有的 AI 应用，基于公有云搭建公司的 AI 应用生态，建立完整的 架构支持长期的 AI 应用迭代。跟踪方式： 手动。