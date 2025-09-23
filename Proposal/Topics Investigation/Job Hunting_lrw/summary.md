1. 现有方案调研：现有的相关平台案例有 [魔方简历](https://magicv.art/zh), [求职方舟](https://www.qiuzhifangzhou.com/), [鼠鼠求职](https://www.shushuqiuzhi.com/) 等。魔方简历包含功能：模板使用、AI润色、PDF导出；求职方舟包含功能：自动填简历，专岗简历美化，智能记忆填写；鼠鼠求职包含功能：职位搜索推荐，简历优化。现有平台的功能比较单一，比较有竞争力的亮点如鼠鼠求职的求职辅导，但该求职辅导为该平台的人工vip服务，估计也是平台的主要收入来源。

2. LangChain 教程
    https://python.langchain.ac.cn/docs/tutorials/  
    **构建agent**: https://python.langchain.ac.cn/docs/tutorials/agents/  
    自定义工具：https://python.langchain.ac.cn/docs/how_to/custom_tools/  
    LangGraph：https://github.langchain.ac.cn/langgraph/concepts/why-langgraph/

3. 预期功能：
    1. 根据输入简历或提示信息定制化推荐岗位 *[定义 职位信息搜索tool]*
    1. 根据推荐的岗位进行简历优化，实现精准化投递 *[定义 简历优化tool]*
    1. 简历优化后根据岗位信息源自动投递或填网申 *[定义 自动投递tool]*
    1. 根据输入简历和岗位要求分析求职者的短板，针对相应短板为用户补充提供强化资料，进行**求职辅导**（提供八股参考/leetcode）*[定义 资料补充tool]*

- 3.1 职位信息搜索：爬虫，爬取招聘平台信息（反爬机制）或者在各厂的招聘界面直接爬取。招聘界面直接爬取应该更容易操作。可以将得到的信息存储为csv，包括字段：company_name, job_title, base, job_desc, source_url, post_time, 然后通过 rag 进行检索推荐；也可以通过自定义 tools 将招聘信息爬取功能封装成 tools (https://python.langchain.ac.cn/docs/how_to/custom_tools/)，加入模型工具链 (https://python.langchain.ac.cn/docs/tutorials/agents/#define-tools)

- 测试 rag 检索推荐 https://python.langchain.ac.cn/docs/tutorials/rag/ ： test.ipynb


......