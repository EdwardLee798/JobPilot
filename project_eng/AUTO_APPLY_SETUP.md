# 自动投递功能配置指南

## 功能说明

自动投递功能基于原有的 Func2_AutoApplication 模块（Java + Playwright），可以自动在Boss直聘、猎聘等平台搜索和投递职位。

**注意**：该功能为可选功能，不影响其他三个核心功能（简历解析、简历优化、进度管理）的使用。

## 为什么需要额外配置？

1. **技术栈差异**：自动投递基于 Java + Spring Boot，而主应用基于 Python + Flask
2. **浏览器自动化**：需要 Playwright 控制浏览器，配置较复杂
3. **平台限制**：招聘网站有反爬虫机制，需要手动登录和验证码处理

## 配置步骤

### 1. 安装 Java 环境

```bash
# macOS
brew install openjdk@21

# 配置环境变量
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH=$JAVA_HOME/bin:$PATH

# 验证安装
java -version  # 应显示 21.x.x
```

### 2. 准备 Func2 服务

Func2_AutoApplication 服务位于项目根目录：

```bash
cd /Users/zijiancai/Desktop/hkucsfiles/comp7607/JobPilot/Func2_AutoApplication

# 构建项目
./gradlew build

# 启动服务
./gradlew bootRun
```

服务默认运行在 `http://localhost:8080`

### 3. 配置数据库

Func2 使用 SQLite 数据库存储配置：

```bash
# 数据库文件位置
Func2_AutoApplication/db/getjobs.db

# 主要配置表
- boss_config: Boss直聘配置
- liepin_config: 猎聘配置
- cookie: 登录状态
```

### 4. 集成到主应用

编辑 `project_eng/backend/modules/auto_apply/__init__.py`，取消注释相关代码：

```python
@auto_apply_bp.route('/start', methods=['POST'])
def start_apply():
    # 检查Java服务是否运行
    try:
        response = requests.get('http://localhost:8080/actuator/health', timeout=2)
        if response.status_code != 200:
            return jsonify({'error': 'Java服务未启动'}), 503
    except:
        return jsonify({'error': 'Java服务未启动，请先运行 Func2 服务'}), 503

    # 调用Java服务API
    # ... 实现投递逻辑
```

## 使用流程

### 首次使用

1. 启动 Func2 服务
2. 访问 http://localhost:8080
3. 手动登录Boss直聘/猎聘
4. 配置搜索参数（关键词、城市等）
5. 通过主应用启动自动投递

### 日常使用

1. 确保 Func2 服务运行
2. 在主应用中选择简历
3. 配置投递参数
4. 点击"启动投递"
5. 监控投递进度

## 常见问题

### Q1: 为什么不直接集成到主应用？

A: 技术栈不同，Java 服务迁移成本高，且功能复杂。独立运行更稳定。

### Q2: 可以不配置自动投递吗？

A: 可以！其他三个功能完全独立可用：
- 简历解析：上传简历提取信息
- 简历优化：生成针对性简历
- 进度管理：记录投递状态

### Q3: 有没有替代方案？

A: 推荐工作流程：
1. 使用"简历优化"生成针对性简历
2. 手动在招聘平台投递（更可控）
3. 使用"进度管理"记录状态

## 技术架构

```
主应用 (Flask)
    ↓ HTTP请求
Java服务 (Spring Boot)
    ↓ 控制
Playwright浏览器
    ↓ 操作
招聘平台网站
```

## 安全提示

1. **账号安全**：建议使用测试账号
2. **投递频率**：避免频繁操作被封号
3. **验证码处理**：需要手动介入
4. **数据隐私**：简历数据仅存储在本地

## 如果不想配置

如果您不需要自动投递功能，可以：

1. **隐藏该标签**：编辑 `frontend/index.html`，注释掉自动投递标签
2. **专注核心功能**：简历解析 + 优化 + 进度管理已经覆盖主要需求
3. **手动投递**：使用优化后的简历手动投递，质量更可控

---

**结论**：自动投递是增强功能，不是必需功能。建议优先使用其他三个模块。
