# JobPilot 智能求职助手

JobPilot 是一个集成简历解析、智能优化、自动投递和进度管理的完整求职解决方案。通过整合四大核心功能模块，为求职者提供从简历准备到投递跟踪的全流程智能化支持。

## 核心功能

### 1. 简历解析与管理
- 支持 PDF、DOCX、TXT 格式简历上传
- 智能提取结构化信息（基本信息、教育背景、工作经历、技能等）
- 使用阿里云千问大模型进行语义理解和信息抽取
- 统一的 JSON 数据格式，便于后续处理

### 2. 简历智能优化
- 基于职位描述（JD）分析简历匹配度
- 使用向量余弦相似度计算经历与JD的相关性
- 自动重排经历顺序，突出最相关内容
- 使用大模型优化经历描述，强化关键成果
- 一键生成针对性优化简历PDF

### 3. 自动化投递
- 支持Boss直聘、猎聘等主流招聘平台
- 使用 Playwright 实现浏览器自动化
- 智能搜索和筛选职位
- 自动填写表单和投递简历
- 支持黑名单过滤和自定义配置

### 4. 投递进度管理
- 集中记录所有投递信息
- 多状态跟踪（已申请、笔试、面试、offer等）
- 实时更新投递状态
- 统计分析投递数据
- 直观的时间线展示

## 技术架构

### 后端技术栈
- **Flask**: Web框架
- **SQLite**: 轻量级数据库
- **OpenAI SDK**: 调用阿里云千问大模型
- **Playwright**: 浏览器自动化
- **pdfminer/python-docx**: 文档解析

### 前端技术栈
- **原生 HTML/CSS/JavaScript**: 简洁高效
- **响应式设计**: 适配不同屏幕尺寸
- **SSE (Server-Sent Events)**: 实时数据推送

### AI 能力
- **阿里云千问 (qwen-plus)**: 简历解析和信息抽取
- **阿里云千问 (qwen3-coder-flash)**: 简历优化和内容生成
- **text-embedding-v3**: 文本向量化和相似度计算

## 项目结构

```
JobPilot/
├── backend/                    # Flask 后端
│   ├── app.py                 # 主应用入口
│   ├── modules/               # 功能模块
│   │   ├── resume_parser/     # Func1: 简历解析
│   │   ├── resume_optimizer/  # Func3: 简历优化
│   │   ├── auto_apply/        # Func2: 自动投递
│   │   └── status_tracking/   # Func4: 进度管理
│   ├── data/                  # 数据存储
│   │   ├── resumes/          # 上传的简历
│   │   ├── generated/        # 生成的简历
│   │   └── database/         # SQLite数据库
│   ├── requirements.txt       # Python依赖
│   ├── start.sh              # 启动脚本
│   └── README.md             # 后端说明
├── frontend/                  # 前端静态文件
│   ├── index.html            # 主页面
│   ├── css/
│   │   └── style.css         # 样式文件
│   └── js/
│       └── app.js            # 前端逻辑
└── README.md                  
```

## 快速开始

### 环境要求
- Python 3.8+
- 现代浏览器（Chrome、Firefox、Safari等）
- （可选）Java 21+ - 用于自动投递功能

### 安装步骤

#### 1. 进入后端目录
```bash
cd project_eng/backend
```

#### 2. 使用启动脚本（推荐）
```bash
chmod +x start.sh
./start.sh
```

启动脚本会自动完成以下操作：
- 创建Python虚拟环境
- 安装所有依赖包
- 安装Playwright浏览器
- 启动Flask服务

#### 3. 手动安装（可选）
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium

# 启动应用
python app.py
```

### 访问应用
打开浏览器访问：http://localhost:5000

## 使用指南

### 工作流程建议

```
1. 简历解析
   ↓ 上传简历（PDF/DOCX/TXT）
   ↓ 查看解析结果
   ↓
2. 简历优化
   ↓ 选择简历
   ↓ 粘贴目标JD
   ↓ 分析匹配度
   ↓ 生成优化简历
   ↓
3. 自动投递
   ↓ 配置投递参数
   ↓ 启动自动投递
   ↓ 监控投递进度
   ↓
4. 进度管理
   ↓ 查看投递记录
   ↓ 更新状态
   ↓ 统计分析
```

### 详细操作

#### 简历解析
1. 切换到"简历解析"标签
2. 点击"选择文件"上传简历
3. 点击"上传并解析"
4. 查看解析后的结构化信息
5. 点击已解析的简历可查看详情

#### 简历优化
1. 切换到"简历优化"标签
2. 从下拉菜单选择已上传的简历
3. 在文本框粘贴目标职位的JD
4. 点击"分析匹配度"查看经历相关性
5. 点击"生成优化简历"创建定制化简历
6. 点击"下载PDF简历"获取文件

#### 自动投递
1. 切换到"自动投递"标签
2. 阅读使用须知
3. 选择要投递的简历
4. 选择投递平台（Boss直聘/猎聘）
5. 配置搜索关键词和目标城市
6. 点击"启动投递"
7. 首次使用需在弹出的浏览器中登录
8. 系统将自动搜索和投递职位
9. 遇到验证码时手动处理
10. 点击"停止投递"结束任务

#### 进度管理
1. 切换到"进度管理"标签
2. 点击"+ 添加新投递"手动添加记录
3. 填写公司、职位等信息
4. 查看所有投递记录和时间线
5. 点击"刷新"更新最新状态
6. 查看统计信息

## API 接口

### 简历解析 (/api/resume)
- `POST /upload` - 上传并解析简历
- `GET /parse/:id` - 获取解析结果
- `GET /list` - 列出所有简历
- `DELETE /delete/:id` - 删除简历

### 简历优化 (/api/optimize)
- `POST /analyze` - 分析JD匹配度
- `POST /generate` - 生成优化简历
- `GET /download/:id` - 下载简历PDF

### 进度管理 (/api/tracking)
- `GET /jobs` - 获取所有投递记录
- `POST /job` - 创建投递记录
- `PUT /job/:id` - 更新投递状态
- `GET /stats` - 获取统计信息
- `GET /events` - SSE实时推送

### 自动投递 (/api/apply)
- `POST /start` - 启动投递任务
- `POST /stop` - 停止投递任务
- `GET /progress` - 获取投递进度

## 数据流向

```
用户上传简历
    ↓
【Func1 简历解析】
    ├─ 文档解析 (PDF/DOCX/TXT)
    ├─ LLM信息抽取
    └─ JSON数据存储
    ↓
【Func3 简历优化】
    ├─ 读取简历JSON
    ├─ 输入JD文本
    ├─ 向量相似度计算
    ├─ 经历重排序
    ├─ LLM优化描述
    └─ 生成PDF简历
    ↓
【Func2 自动投递】
    ├─ 读取优化后简历
    ├─ Playwright自动化
    ├─ 投递到招聘平台
    └─ 记录投递结果
    ↓
【Func4 进度管理】
    ├─ SQLite数据库
    ├─ 状态更新
    ├─ SSE实时推送
    └─ 可视化展示
```

## 注意事项

### 1. API密钥配置
- 项目内置了阿里云千问API密钥，仅供测试使用
- 生产环境请替换为自己的密钥
- 密钥位置：
  - `backend/modules/resume_parser/parser.py`
  - `backend/modules/resume_optimizer/optimizer.py`

### 2. 自动投递功能
- 需要Java 21+运行环境
- 首次使用需要手动登录招聘平台
- 建议在投递前先优化简历
- 遇到验证码需要手动处理
- 投递过程中不要关闭浏览器窗口

### 3. 数据安全
- 所有简历数据存储在本地
- 不会上传到第三方服务器
- LLM调用使用阿里云千问API
- 建议定期备份data目录

### 4. 性能优化
- 简历优化功能较慢，需要等待1-2分钟
- 自动投递速度取决于网络和平台响应
- 建议不要同时处理大量简历

## 故障排除

### 问题1：Playwright安装失败
```bash
# 手动安装浏览器
playwright install chromium
```

### 问题2：PDF生成失败
```bash
# 确保已安装Playwright
pip install playwright
playwright install chromium
```

### 问题3：LLM调用失败
- 检查网络连接
- 确认API密钥有效
- 查看阿里云账户余额

### 问题4：自动投递无法启动
- 确保已安装Java 21+
- 检查Func2目录是否存在
- 查看后端日志输出

## 开发说明

### 添加新功能
1. 在 `backend/modules/` 创建新模块
2. 实现Flask蓝图
3. 在 `app.py` 中注册蓝图
4. 更新前端界面和逻辑

### 修改AI模型
- 编辑 `optimizer.py` 中的模型配置
- 支持切换到其他OpenAI兼容API

### 自定义前端样式
- 修改 `frontend/css/style.css`
- 样式采用响应式设计

## 原功能模块说明

本项目整合了以下原有功能模块：

- **Func1_Parser**: 简历解析模块
- **Func2_AutoApplication**: 自动投递模块（Spring Boot + Playwright）
- **Func3_Optimizer**: 简历优化模块（LangChain + LLM）
- **Func4_StatusTracking**: 进度管理模块（Flask + CSV）

整合后的版本：
- 统一使用Flask作为后端框架
- 简化了Func2的调用方式
- 优化了Func3的处理流程
- 将Func4的CSV存储改为SQLite
- 提供了统一的Web界面

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，请联系项目维护者。

---

**JobPilot** - 让求职更智能，让机会更精准！
