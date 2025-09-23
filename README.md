# JobPilot: An LLM-Based Agent for Job Application Management

## 项目简介
**JobPilot** 是一款基于大语言模型 (LLM) 的智能代理应用，旨在自动化求职流程，帮助用户完成简历解析、表单填写和申请进度管理。  
项目目标是通过 **语义理解 + 自动执行**，提升求职效率，减少重复性操作，优化简历与岗位的匹配度:contentReference[oaicite:0]{index=0}。

---

## 核心功能
- **简历解析与档案构建**  
  - 上传 PDF/DOC 简历，自动抽取信息，生成候选人档案  
- **自动化表单填写**  
  - 基于候选人档案和网页表单字段，调用自动化工具完成填写  
- **岗位分析与简历优化**  
  - 分析岗位 JD，计算匹配度，生成定制化简历/建议  
- **申请进度管理**  
  - 统一面板记录申请信息  
  - 自然语言输入更新进度（如“我完成了公司 X 的测评”）  
  - 自然语言查询申请状态（如“查看腾讯的申请进度”）:contentReference[oaicite:1]{index=1}

---

## 技术方案
- **后端**：Python + LLM 应用框架（LangChain / Langflow）  
- **模型接入**：调用外部 API（ChatGPT, Gemini, Qwen 等）或本地部署  
- **前端**：Web 框架（Vue / React）  
- **工具**：Playwright / Selenium 用于网页自动化  
- **数据存储**：向量数据库 (Pinecone / MongoDB 等) + SQLite  

---

## 团队成员
- LJH HHF LRW CZJ LZH    

---

## 后续改进方向
- 多智能体（Multi-Agent）协作机制  
- 简历优化与推荐策略增强  
- 支持更多招聘平台与表单格式  
- 增加跨平台移动端支持  

---

## 参考资料
更多细节请见项目文档：  
**[COMP7607A Group Project Proposal](./COMP7607A%20Group%20Project%20Proposal.pdf)**
