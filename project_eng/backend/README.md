# JobPilot Backend

## 安装说明

### 1. 创建虚拟环境（推荐）

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Playwright浏览器

```bash
playwright install chromium
```

## 运行应用

### 使用启动脚本（推荐）

```bash
chmod +x start.sh
./start.sh
```

### 手动启动

```bash
python app.py
```

应用将在 http://localhost:5000 启动

## 目录结构

```
backend/
├── app.py                 # 主应用入口
├── modules/              # 功能模块
│   ├── resume_parser/    # 简历解析
│   ├── resume_optimizer/ # 简历优化
│   ├── auto_apply/       # 自动投递
│   └── status_tracking/  # 进度管理
├── data/                 # 数据存储
│   ├── resumes/         # 上传的简历
│   ├── generated/       # 生成的简历
│   └── database/        # SQLite数据库
└── requirements.txt      # Python依赖
```

## API文档

### 简历解析模块 (/api/resume)

- `POST /upload` - 上传并解析简历
- `GET /parse/:id` - 获取解析结果
- `GET /list` - 列出所有简历
- `DELETE /delete/:id` - 删除简历

### 简历优化模块 (/api/optimize)

- `POST /analyze` - 分析JD匹配度
- `POST /generate` - 生成优化简历
- `GET /download/:id` - 下载简历PDF
- `GET /list` - 列出生成的简历

### 进度管理模块 (/api/tracking)

- `GET /jobs` - 获取所有投递记录
- `POST /job` - 创建投递记录
- `PUT /job/:id` - 更新投递状态
- `DELETE /job/:id` - 删除记录
- `GET /stats` - 获取统计信息
- `GET /events` - SSE实时推送

### 自动投递模块 (/api/apply)

- `GET /status` - 检查Java服务状态
- `POST /start` - 启动投递任务
- `POST /stop` - 停止投递任务
- `GET /progress` - 获取投递进度

## 注意事项

1. 首次运行需要安装 Playwright 浏览器
2. 自动投递功能需要 Java 21+ 运行环境
3. 所有API密钥已内置，仅供测试使用
4. 生产环境请修改API密钥配置
