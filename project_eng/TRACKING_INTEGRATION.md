# 进度管理模块整合说明

## 概述

已将 `Func4_StatusTracking` 的完整功能整合到 `project_eng` 的进度管理模块中，包括：

- ✅ **智能对话管理**：通过Agent助手进行自然语言交互，管理申请进度
- ✅ **时间线可视化**：横向卡片展示每个职位的申请流程，支持流程终止状态标记
- ✅ **日历视图**：直观查看面试和笔试日程，点击日期可跳转到对应职位卡片
- ✅ **统计面板**：实时显示总投递数、进行中和已终止的职位数量

## 功能特性

### 1. 时间线视图

- **职位卡片**：每个职位显示为独立卡片，包含公司名、职位名
- **横向时间线**：时间节点横向排列，清晰展示申请流程
- **职位描述悬浮**：鼠标悬停在职位标题上可查看完整职位描述
- **流程终止标记**：已终止的职位卡片自动变灰，取消悬浮效果
- **实时更新**：通过SSE实时推送最新的申请进度

### 2. 智能助手对话

- **自然语言交互**：
  - "我申请了阶跃星辰的大语言模型预训练算法研究员岗位"
  - "帮我查询所有的申请进度"
  - "阶跃星辰的一面安排在下周二上午10点"
  - "阶跃星辰的流程终止了"
  
- **Agent工具函数**：
  - `app_process_creater`：创建新的申请记录
  - `app_process_reader`：查询申请进度
  - `is_app_new`：判断是新申请还是更新
  - `app_process_updater`：更新申请进度

- **流式响应**：支持SSE流式输出，实时显示Agent回复

### 3. 日历视图

- **月份切换**：
  - 点击左右箭头切换月份
  - 鼠标滚轮上下滑动切换月份
  - 3D翻页动画效果（0.4秒持续时间）
  
- **事件标记**：有面试/笔试安排的日期显示小圆点标记
- **点击跳转**：点击有事件的日期，自动切换到时间线视图并滚动到对应职位卡片
- **高亮效果**：跳转后卡片背景短暂高亮

### 4. UI设计风格

完全继承 `project_eng` 的设计规范：

- **紫色渐变主题**：`linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **卡片阴影效果**：悬停时阴影加深并上浮
- **圆角设计**：统一使用8-12px圆角
- **响应式布局**：适配不同屏幕尺寸

## 技术实现

### 后端 (Flask)

**文件结构：**
```
project_eng/backend/modules/status_tracking/
├── __init__.py          # 主路由，SSE端点
├── agent.py             # Agent工具函数和配置
```

**API端点：**
- `GET /api/tracking/jobs` - 获取所有职位记录
- `POST /api/tracking/job` - 创建新职位记录
- `PUT /api/tracking/job/<id>` - 更新职位状态
- `DELETE /api/tracking/job/<id>` - 删除职位记录
- `GET /api/tracking/stats` - 获取统计信息
- `GET /api/tracking/merged_data` - SSE推送合并数据
- `POST /api/tracking/chat_stream` - SSE流式聊天

**数据库设计：**
```sql
-- 职位总览表
job_summary (
    job_id INTEGER PRIMARY KEY,
    job_title TEXT,
    company_name TEXT,
    job_desc TEXT,
    tracking_method TEXT,
    created_at TIMESTAMP
)

-- 申请状态表
application_status (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    status_update TEXT,
    event_time REAL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### 前端 (Vanilla JS)

**文件结构：**
```
project_eng/frontend/
├── index.html           # 进度管理Tab HTML
├── css/style.css        # 样式（已整合tracking样式）
├── js/
│   ├── app.js          # 主应用逻辑
│   └── tracking.js     # 进度管理专用逻辑
└── assets/
    ├── agent.jpg       # Agent头像
    └── student.jpg     # 用户头像
```

**核心类：**
- `TrackingManager`：管理时间线、日历、聊天的核心类
  - `renderTimeline()` - 渲染职位卡片和时间线
  - `renderCalendar()` - 渲染日历网格
  - `sendChatMessage()` - 发送聊天消息
  - `connectSSE()` - 建立SSE连接
  - `animateMonthSwitch()` - 日历翻页动画

## 使用方法

### 1. 启动后端

```bash
cd project_eng/backend
python app.py
```

应用将在 http://localhost:5000 启动

### 2. 访问前端

打开浏览器访问 http://localhost:5000

点击"进度管理"Tab，即可看到：
- 左侧：时间线视图/聊天视图（可切换）
- 右侧：日历视图

### 3. 添加测试数据

可以使用测试脚本：
```bash
cd project_eng/backend
python test_tracking.py
```

或通过Agent对话添加：
```
我申请了阶跃星辰的大语言模型预训练算法研究员岗位，
跟进方式是邮箱，职位描述：参与大语言模型的算法研究和开发工作...
```

### 4. 与Agent对话示例

**创建新申请：**
```
我申请了国家集成电路创新中心的图像算法工程师实习岗位，
跟进方式是手机号，负责图像分类、识别和跟踪算法模型设计
```

**更新进度：**
```
阶跃星辰的一面安排在11月25日下午2点
```

**查询进度：**
```
帮我查询所有的申请进度
```

**终止流程：**
```
阶跃星辰的流程终止了
```

## 配置要求

### 环境变量

需要在 `.env` 文件中配置：
```
DASHSCOPE_API_KEY=your_api_key_here
```

### Python依赖

已在 `requirements.txt` 中包含：
- langchain-openai
- langchain-community
- langgraph
- pydantic

安装命令：
```bash
pip install -r requirements.txt
```

## 注意事项

1. **Agent初始化**：首次使用需要确保API密钥配置正确
2. **数据库位置**：SQLite数据库位于 `project_eng/backend/data/database/tracking.db`
3. **静态资源**：头像图片位于 `project_eng/frontend/assets/`
4. **SSE连接**：时间线视图会自动建立SSE连接，切换到聊天视图时断开

## 与原Func4的差异

| 功能 | Func4_StatusTracking | project_eng整合版 |
|------|---------------------|-------------------|
| 数据存储 | CSV文件 | SQLite数据库 |
| UI风格 | 蓝色主题 | 紫色渐变主题 |
| 模块化 | 独立应用 | 整合到JobPilot |
| 静态服务 | 独立serve.py | 整合到Flask app |
| 配置管理 | 独立配置 | 共享配置 |

## 开发者指南

### 添加新的Agent工具

在 `agent.py` 中定义新的工具函数：

```python
@tool(args_schema=YourSchema)
def your_tool_function(param1: str, param2: int) -> str:
    """工具描述"""
    # 实现逻辑
    return "结果"

# 将工具添加到tools列表
tools = [app_process_creater, app_process_reader, is_app_new, app_process_updater, your_tool_function]
```

### 自定义UI样式

在 `style.css` 中的进度管理区块修改：

```css
/* 修改卡片颜色 */
.job-card {
    background: your-color;
}

/* 修改时间线颜色 */
.timeline-dot {
    border-color: your-color;
}
```

### 调试技巧

1. **查看SSE连接**：打开浏览器开发者工具 -> Network -> EventStream
2. **查看Agent日志**：终端会输出tool调用详情（debug=True）
3. **数据库查询**：使用SQLite工具查看 `tracking.db`

## 未来改进

- [ ] 支持多用户管理
- [ ] 导出申请记录为PDF
- [ ] 邮件/微信提醒面试日程
- [ ] 申请进度数据分析和图表展示
- [ ] 与简历优化模块联动

## 反馈与贡献

如有问题或建议，请联系开发团队或提交Issue。
