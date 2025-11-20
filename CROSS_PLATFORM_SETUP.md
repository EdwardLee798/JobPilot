# JobPilot 跨平台配置指南

## 概述

JobPilot 现已支持在 Windows、macOS 和 Linux 系统上运行。本文档说明如何在不同平台上配置和运行项目。

## 系统要求

### 所有平台通用要求

- **Python**: 3.8 或更高版本
- **Java**: JDK 21 或更高版本
- **Node.js**: 14.0 或更高版本（如需前端开发）

### 平台特定要求

#### Windows
- Windows 10/11
- PowerShell 或 CMD
- 推荐安装 Python 和 Java 到 PATH 环境变量

#### macOS
- macOS 10.15 (Catalina) 或更高版本
- 已安装 Xcode Command Line Tools

#### Linux
- Ubuntu 20.04+ / Debian 10+ / CentOS 8+ 或其他主流发行版
- 已安装 build-essential (Ubuntu/Debian) 或 Development Tools (CentOS)

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd JobPilot
```

### 2. 安装 Python 依赖

所有平台使用相同的命令：

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r project_eng/backend/requirements.txt
```

**关键依赖说明**：
- `psutil>=5.9.0`: 跨平台进程管理，用于启动/停止 Java 服务
- `Flask==3.0.0`: Web 框架
- `openai>=1.30.0`: AI 功能（简历生成、优化）
- `pdfminer.six`, `python-docx`: 简历解析

### 3. 配置 Java 服务

确保 Java 21+ 已安装并在 PATH 中：

```bash
# 验证 Java 版本
java -version
```

### 4. 启动服务

#### 方式 1: 使用 Python 脚本（推荐，跨平台）

```bash
# 启动 Java 自动投递服务
cd Func2_AutoApplication
python job_app.py start

# 启动 Flask 后端
cd project_eng/backend
python app.py
```

#### 方式 2: 手动启动（仅限 Unix 系统）

```bash
# 启动 Java 服务
cd Func2_AutoApplication
./job-app.sh start

# 启动 Flask 后端
cd project_eng/backend
python app.py
```

### 5. 访问应用

打开浏览器访问：`http://localhost:5000`

## 跨平台改动说明

为了实现跨平台兼容，我们对以下文件进行了修改：

### 1. `backend/modules/auto_apply/java_service.py`

**改动**：
- 移除硬编码的 macOS 路径
- 使用 `pathlib.Path` 和相对路径
- 添加平台检测（`platform.system()`）
- 实现跨平台进程管理（psutil + 系统命令回退）

**关键变化**：
```python
# 旧代码（仅 macOS）:
FUNC2_DIR = "/Users/zijiancai/Desktop/.../Func2_AutoApplication"
subprocess.run(["lsof", "-ti", f":{port}"])

# 新代码（跨平台）:
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent.parent.parent.parent
FUNC2_DIR = PROJECT_ROOT / "Func2_AutoApplication"

# 跨平台进程查找
if IS_WINDOWS:
    subprocess.run(["netstat", "-ano"])
else:
    subprocess.run(["lsof", "-ti", f":{port}"])
```

### 2. `backend/modules/resume_parser/interactive_builder.py`

**改动**：
- 移除硬编码的 Func1_Parser 路径
- 使用相对路径动态导入

**关键变化**：
```python
# 旧代码:
sys.path.append('/Users/zijiancai/Desktop/.../Func1_Parser')

# 新代码:
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent.parent.parent
FUNC1_DIR = PROJECT_ROOT / "Func1_Parser"
sys.path.insert(0, str(FUNC1_DIR))
```

### 3. `Func2_AutoApplication/job_app.py`（新增）

**目的**：替代 Unix 专用的 `job-app.sh` 脚本

**功能**：
- 跨平台启动/停止 Java 服务
- 检查服务状态
- 端口占用检测

**使用方法**：
```bash
python job_app.py start   # 启动服务
python job_app.py stop    # 停止服务
python job_app.py status  # 查看状态
python job_app.py help    # 显示帮助
```

### 4. `backend/requirements.txt`（更新）

**新增依赖**：
```txt
psutil>=5.9.0  # 跨平台进程管理
```

## 平台特定说明

### Windows 注意事项

#### 1. 路径分隔符
项目已使用 `pathlib.Path`，会自动处理路径分隔符（`/` vs `\`）

#### 2. Gradlew 命令
Windows 上自动使用 `gradlew.bat` 而不是 `./gradlew`

#### 3. 进程管理
- 优先使用 `psutil`（跨平台）
- 回退到 `netstat` 和 `taskkill`（Windows 命令）

#### 4. 权限问题
如果遇到权限错误，尝试以管理员身份运行 PowerShell/CMD

#### 5. Python 命令
某些 Windows 系统可能需要使用 `python` 而不是 `python3`：
```bash
python --version
# 如果不存在，尝试:
python3 --version
```

### macOS 注意事项

#### 1. 安全和隐私
首次运行可能需要在"系统偏好设置 > 安全性与隐私"中允许 Java 和 Python

#### 2. Homebrew 安装 Java
```bash
brew install openjdk@21
```

#### 3. 文件权限
确保脚本有执行权限：
```bash
chmod +x job-app.sh
chmod +x gradlew
```

### Linux 注意事项

#### 1. Java 安装
Ubuntu/Debian:
```bash
sudo apt update
sudo apt install openjdk-21-jdk
```

CentOS/RHEL:
```bash
sudo yum install java-21-openjdk-devel
```

#### 2. Python 虚拟环境
某些发行版可能需要额外安装：
```bash
sudo apt install python3-venv  # Ubuntu/Debian
```

#### 3. 端口占用
如果端口 5000 或 8888 被占用：
```bash
# 查找占用进程
sudo lsof -i :5000
sudo lsof -i :8888

# 停止进程
sudo kill -9 <PID>
```

## 服务端口

| 服务 | 端口 | 说明 |
|-----|------|------|
| Flask 后端 | 5000 | Web UI 和 API |
| Java 自动投递服务 | 8888 | Boss直聘/猎聘自动投递 |

## 故障排除

### 问题 1: `psutil` 安装失败

**症状**：
```
error: Microsoft Visual C++ 14.0 or greater is required (Windows)
```

**解决方案（Windows）**：
1. 安装 Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. 或者下载预编译的 wheel 文件：
   ```bash
   pip install psutil --only-binary :all:
   ```

**解决方案（Linux）**：
```bash
sudo apt install python3-dev gcc  # Ubuntu/Debian
sudo yum install python3-devel gcc  # CentOS
pip install psutil
```

### 问题 2: Java 服务启动失败

**检查步骤**：
1. 确认 Java 版本：
   ```bash
   java -version  # 应该是 21+
   ```

2. 检查端口占用：
   ```bash
   # Windows:
   netstat -ano | findstr :8888
   # Unix:
   lsof -i :8888
   ```

3. 查看 Java 服务日志：
   ```bash
   cd Func2_AutoApplication
   cat logs/app.log  # Unix
   type logs\app.log  # Windows
   ```

### 问题 3: 模块导入错误

**症状**：
```
ModuleNotFoundError: No module named 'CVParser'
```

**解决方案**：
1. 确认项目结构完整（Func1_Parser, Func2_AutoApplication 等目录存在）
2. 检查 Python 路径是否正确
3. 确认从正确的目录运行脚本

### 问题 4: Flask 无法启动

**检查步骤**：
1. 确认所有依赖已安装：
   ```bash
   pip list | grep Flask
   pip list | grep openai
   ```

2. 检查端口 5000 是否被占用
3. 查看错误日志输出

### 问题 5: 权限错误（Unix）

**症状**：
```
Permission denied: './gradlew'
```

**解决方案**：
```bash
chmod +x gradlew
chmod +x job-app.sh
```

## 开发建议

### 1. 使用虚拟环境

始终使用 Python 虚拟环境来隔离项目依赖：

```bash
# 创建
python -m venv venv

# 激活（每次开发前）
# Windows:
venv\Scripts\activate
# Unix:
source venv/bin/activate

# 停用
deactivate
```

### 2. 路径处理

在代码中始终使用 `pathlib.Path` 而不是字符串拼接：

```python
# 推荐
from pathlib import Path
config_file = Path(__file__).parent / "config.json"

# 避免
config_file = "/absolute/path/config.json"  # 不跨平台
config_file = os.path.join(path, "config.json")  # pathlib 更现代
```

### 3. 进程管理

优先使用 `psutil`，提供系统命令作为回退：

```python
try:
    import psutil
    # psutil 实现
except ImportError:
    if IS_WINDOWS:
        # Windows 命令
    else:
        # Unix 命令
```

### 4. 测试多平台

在不同平台测试你的更改：
- 主要开发平台：macOS/Linux
- 定期在 Windows 上测试
- 使用 Docker 进行隔离测试

## 环境变量配置

### OpenAI API Key（必需）

项目使用通义千问 API（兼容 OpenAI 格式），需要配置 API Key。

**方式 1：修改代码（不推荐，仅用于测试）**

编辑 `backend/modules/resume_parser/interactive_builder.py`:
```python
client = OpenAI(
    api_key="your-api-key-here",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
```

**方式 2：使用环境变量（推荐）**

Windows:
```cmd
set OPENAI_API_KEY=your-api-key-here
set OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

macOS/Linux:
```bash
export OPENAI_API_KEY=your-api-key-here
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 卸载/清理

### 停止所有服务

```bash
# 停止 Java 服务
cd Func2_AutoApplication
python job_app.py stop

# Flask 服务在前台运行，直接 Ctrl+C 停止
```

### 删除虚拟环境

```bash
# Windows:
rmdir /s venv
# Unix:
rm -rf venv
```

### 清理临时文件

```bash
# Python 缓存
find . -type d -name "__pycache__" -exec rm -r {} +  # Unix
# Windows 使用文件管理器手动删除 __pycache__ 目录

# Gradle 缓存
cd Func2_AutoApplication
./gradlew clean  # Unix
gradlew.bat clean  # Windows
```

## 常见问题 (FAQ)

### Q: 项目可以在 ARM64 (Apple Silicon) Mac 上运行吗？

A: 可以。确保安装 ARM64 版本的 Java 和 Python。使用 Homebrew 安装：
```bash
brew install openjdk@21
brew install python@3.11
```

### Q: 可以使用 Conda 环境吗？

A: 可以。创建 Conda 环境并安装依赖：
```bash
conda create -n jobpilot python=3.11
conda activate jobpilot
pip install -r project_eng/backend/requirements.txt
```

### Q: Windows 上 gradlew.bat 执行很慢？

A: 这是正常的，Gradle 首次运行会下载依赖。后续运行会更快。可以考虑：
1. 使用国内 Gradle 镜像
2. 增加 Gradle JVM 内存（编辑 `gradle.properties`）

### Q: 项目是否支持 Docker 部署？

A: 当前版本专注于本地开发。Docker 支持可以作为未来改进。参考项目中的方案3（Docker容器化）建议。

### Q: 如何更新依赖？

```bash
pip install --upgrade -r project_eng/backend/requirements.txt
```

## 技术支持

遇到问题？请检查：

1. **本文档的故障排除部分**
2. **项目 README.md**
3. **相关模块的文档**：
   - 对话式简历生成：`INTERACTIVE_RESUME_GUIDE.md`
   - 实现细节：`INTERACTIVE_RESUME_IMPLEMENTATION.md`

## 版本历史

| 版本 | 日期 | 说明 |
|-----|------|------|
| 1.0 | 2025-11-21 | 初始跨平台支持（Windows/macOS/Linux） |

## 贡献者

- 跨平台改造：Claude AI Assistant
- 原始项目：JobPilot Team

---

**最后更新**: 2025-11-21
**文档版本**: v1.0
