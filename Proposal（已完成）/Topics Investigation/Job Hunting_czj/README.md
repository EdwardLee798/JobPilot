# JobAgent（基于豆包api）求职助手使用文档

## 项目简介
JobSeekingAgent 是基于 Python 开发的自动化求职工具，通过 Selenium 爬取远程职位 与 火山方舟豆包 API 结合，实现「职位搜索→简历优化→能力分析」全流程自动化，助力 IT 求职者提升求职效率。

## 功能清单
- 远程职位爬取：基于关键词获取 weworkremotely.com 职位信息（名称、公司、详情链接）
- 简历智能优化：按目标岗位定制简历，突出技能匹配度与项目成果
- 能力分析报告：生成技能差距、学习路径及面试题预测

## 环境搭建（Conda 版）

### 1. 系统与基础要求
- 系统：Windows 10+/macOS 10.15+/Linux
- 已安装 Conda（Anaconda/Miniconda）
- 已安装 Chrome 浏览器（88.0+）
- 网络可访问互联网

### 2. 步骤 1：创建 Conda 环境
打开终端 / 命令提示符，执行以下命令创建并激活名为 jobagent 的 Python 3.10 环境：
```bash
# 创建环境
conda create -n jobagent python=3.10 -y

conda activate jobagent
```

### 3. 步骤 2：安装依赖包
在激活的 jobagent 环境中，执行命令安装核心依赖：
```bash
pip install openai==1.35.10 selenium==4.21.0 webdriver-manager==4.0.1 beautifulsoup4==4.12.3
```

### 4. 步骤 3：火山方舟 API 配置

#### 4.1 获取密钥与接入点
1. 登录 [火山方舟控制台](https://console.volcengine.com/ark/)
2. 「API 密钥管理」→ 创建密钥，复制 ARK_API_KEY
3. 「模型市场」→ 选择「豆包」→ 创建推理接入点，复制接入点 ID（如 doubao-seed-1-6-250615）

#### 4.2 设置环境变量
```bash
# Windows（CMD）
set ARK_API_KEY="你的火山方舟API密钥"
# macOS/Linux
export ARK_API_KEY="你的火山方舟API密钥"
```

### 5. 步骤 4：简历文件准备
确保 resume.txt 存放于路径：  
`/Users/zijiancai/Desktop/hkucs files/comp7607/find_job_agent/resume.txt`  
文件内容需包含「基本信息、教育背景、项目经历、技能清单」（UTF-8 编码）。

## 代码模块解析

| 模块                | 核心功能                                                                 |
|---------------------|--------------------------------------------------------------------------|
| API 配置模块        | 初始化火山方舟客户端，封装 call_ark_doubao_api() 实现豆包模型调用       |
| JobSeekingAgent 类  | 工具核心类，整合所有功能：<br>- load_resume()：读取指定路径简历<br>- tool_search_jobs()：Selenium 爬取职位<br>- tool_optimize_resume()：AI 优化简历<br>- tool_supplement_materials()：生成能力分析报告<br>- run()：串联全流程 |
| 主程序入口          | 初始化工具，执行职位搜索（默认关键词 "Python Developer"）                 |

## 运行步骤
1. 确认：jobagent 环境已激活、ARK_API_KEY 已设置、简历路径正确
2. 进入项目目录，执行启动命令：
   ```bash
   python job_agent_doubao.py  # Windows/macOS/Linux 通用
   ```

3. 输出示例：
   ```
   🤖 求职Agent已启动
   📄 简历加载成功
   🔍 正在搜索 'Python+Developer' 职位...
   ✅ 找到 5 个职位
   🎯 目标职位：【Senior Python Developer】 at 【ABC Company】
   ...（简历优化+能力分析报告）
   ```

## 常见问题

| 问题现象                          | 解决方法                                                                 |
|-----------------------------------|--------------------------------------------------------------------------|
| 报错 "ARK_API_KEY 未找到"         | 重新执行环境变量设置命令，核对密钥拼写                                   |
| 报错 "model not found"            | 替换 call_ark_doubao_api() 中的 model 参数为正确的火山方舟接入点 ID   |
| 简历加载失败 "文件未找到"         | 核对 load_resume() 中的 resume_path 与实际文件路径一致               |
| Chrome 驱动启动失败               | 升级 Chrome 到最新版本，重新运行（驱动会自动匹配）                       |

## 自定义扩展
- 改搜索关键词：修改主程序 `agent.run("Frontend Developer")` 中的关键词
- 调职位数量：`tool_search_jobs(num_jobs=10)`（默认 5 个）
- 换简历路径：修改 `load_resume(resume_path="新路径/resume.txt")`