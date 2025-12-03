# 🚀 Automated Job Application System

An intelligent, fully automated job application system that automatically submits resumes to **Boss Zhipin** and **Liepin** recruitment platforms with AI-powered personalized greetings.

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Monitoring](#-monitoring)
- [Troubleshooting](#-troubleshooting)
- [API Reference](#-api-reference)
- [Important Notes](#-important-notes)

---

## ✨ Features

- **🤖 Fully Automated**: Automatically searches, filters, and applies to relevant job positions
- **🧠 AI-Powered**: Uses LLM to generate personalized greetings based on job descriptions (optional)
- **📋 Resume-Driven**: Automatically extracts keywords and preferences from your `resume.json`
- **🎯 Smart Filtering**: Filters inactive HRs, headhunters, and unsuitable positions
- **📊 Real-time Monitoring**: Track application progress in real-time
- **🔄 Persistent Login**: Saves login cookies for seamless re-use
- **🚫 Blacklist Management**: Automatically maintains blacklist of unsuitable companies
- **Multi-Platform**: Supports Boss Zhipin and Liepin

---

## ⚡ Quick Start

### Unified Script (Recommended)

All functionality is now unified in `job-app.sh`:

```bash
# Check system requirements
./job-app.sh check

# Setup from resume.json
./job-app.sh setup

# Start the system
./job-app.sh start

# Check status
./job-app.sh status

# Stop everything
./job-app.sh stop

# View logs
./job-app.sh logs

# Show all commands
./job-app.sh help
```

### Classic 3-Step Setup

Or use the traditional shortcuts:

```bash
# Step 1: Verify system requirements
./check_setup.sh

# Step 2: Configure from your resume
./quick_setup.sh

# Step 3: Start the system
./auto_start.sh
```

That's it! The system will:
1. ✅ Start the application
2. ✅ Open browser for login
3. ✅ Wait for you to login (WeChat QR code)
4. ✅ Automatically start applying to jobs

---

## 📋 Prerequisites

### Required

- **JDK 21** (Java Development Kit)
- **Python 3** (for configuration scripts)
- **macOS/Linux** (tested on macOS, should work on Linux)

### Install JDK 21

```bash
# macOS
brew install openjdk@21

# Verify installation
java -version  # Should show 21.x.x
```

### Optional

- **AI API Key** (for personalized greetings)
  - OpenAI, Anthropic, or compatible API
  - Works fine without it (uses default greetings)

---

## 🔧 Installation

### 1. Prepare Your Resume

Edit `resume.json` with your information:

```json
{
  "name": "Your Name",
  "contacts": {
    "email": "your@email.com",
    "phone": "13800138000"
  },
  "skills": ["Python", "Java", "Machine Learning", "Data Analysis"],
  "experience": [
    {
      "company": "Tech Company",
      "title": "Software Engineer",
      "role": "Backend Developer",
      "period": "2020-2023"
    }
  ],
  "education": [
    {
      "school": "University Name",
      "degree": "Master",
      "major": "Computer Science"
    }
  ]
}
```

### 2. Configure AI (Optional)

Create/edit `.env`:

```bash
# AI API Configuration
BASE_URL=https://api.openai.com
API_KEY=sk-your-api-key-here
MODEL=gpt-4o-mini

# Enterprise WeChat Webhook (optional)
HOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
```

### 3. Run Setup

```bash
./quick_setup.sh
```

This will:
- Check your resume.json
- Initialize database
- Auto-configure search criteria from your resume

---

## 🎮 Usage

### Option 1: Fully Automated (Recommended)

```bash
./auto_start.sh
```

**What happens:**
1. Application starts automatically
2. Browser opens (Boss Zhipin)
3. You login via WeChat QR code (first time only)
4. System detects login and starts Boss delivery
5. System asks if you want to start Liepin delivery
6. If yes: stops Boss, waits for Liepin login, starts Liepin delivery

### Option 2: Manual Control

```bash
# Terminal 1: Start application
./gradlew bootRun

# Terminal 2: Start delivery manually
curl -X POST http://localhost:8888/api/jobs/boss/execute    # Boss
curl -X POST http://localhost:8888/api/liepin/start         # Liepin
```

### Stop the System

```bash
./stop.sh
```

Or manually:

```bash
curl -X POST http://localhost:8888/api/jobs/boss/stop
curl -X POST http://localhost:8888/api/liepin/stop
```

---

## ⚙️ Configuration

### Auto-Configuration from Resume

```bash
# Extract keywords, experience, and preferences from resume.json
python3 config_from_json.py
```

This automatically:
- Extracts skills as search keywords
- Determines experience level from work history
- Generates personalized greeting message
- Updates Boss and Liepin configurations in database

### Manual Configuration

```bash
# Open database
sqlite3 db/getjobs.db

# Update search keywords
UPDATE boss_config SET keywords = '["Python","Data Analysis","Machine Learning"]' WHERE id = 1;

# Update city
UPDATE boss_config SET city_code = 'Beijing' WHERE id = 1;

# Update salary range
UPDATE boss_config SET salary = '[15-30K]' WHERE id = 1;

# View configuration
SELECT keywords, city_code, salary, say_hi FROM boss_config;

# Exit
.quit
```

### Interactive Configuration

```bash
./update_config.sh
```

---

## 📁 Project Structure

```
Func2_AutoApplication/
├── README.md                   # This file
├── LICENSE                     # License
│
├── resume.json                 # Your resume data (EDIT THIS)
├── .env                        # AI API configuration (OPTIONAL)
│
├── auto_start.sh              # 🚀 Main automated startup
├── stop.sh                    # 🛑 Stop all services
├── quick_setup.sh             # ⚙️  Initial setup wizard
├── config_from_json.py        # 🔧 Auto-config from resume
├── update_config.sh           # 🔧 Interactive config
├── check_setup.sh             # ✅ Verify requirements
│
├── build.gradle.kts           # Gradle build config
├── settings.gradle            # Gradle settings
├── gradlew                    # Gradle wrapper (Unix)
├── gradlew.bat                # Gradle wrapper (Windows)
├── gradle/                    # Gradle wrapper files
│
├── src/                       # Java source code
│   └── main/
│       ├── java/              # Application code
│       │   └── com/getjobs/
│       │       ├── GetJobsApplication.java      # Main entry
│       │       ├── application/                 # App layer
│       │       │   ├── config/                 # Spring config
│       │       │   ├── controller/             # REST APIs
│       │       │   ├── entity/                 # DB entities
│       │       │   ├── service/                # Business logic
│       │       │   └── init/                   # Initialization
│       │       └── worker/                     # Worker layer
│       │           ├── boss/                   # Boss Zhipin
│       │           ├── liepin/                 # Liepin
│       │           ├── manager/                # Browser automation
│       │           ├── service/                # Job services
│       │           └── dto/                    # Data objects
│       └── resources/
│           ├── application.yaml                # App config
│           └── banner.txt                      # Startup banner
│
└── db/                        # SQLite database
    └── getjobs.db            # Application data
        ├── boss_config       # Boss configuration
        ├── liepin_config     # Liepin configuration
        ├── boss_job_data     # Boss applications
        ├── liepin_data       # Liepin applications
        ├── cookie            # Login cookies
        └── blacklist         # Company blacklist
```

---

## 📊 Monitoring

### View Logs

```bash
# Real-time application logs
tail -f logs/app.log

# Boss delivery progress (SSE stream)
curl http://localhost:8888/api/jobs/boss/stream

# Liepin status
curl http://localhost:8888/api/liepin/status
```

### Check Statistics

```bash
# Boss statistics
curl http://localhost:8888/api/boss/analytics/stats

# Liepin statistics
curl http://localhost:8888/api/liepin/stats
```

### View Database

```bash
sqlite3 db/getjobs.db

# View recent Boss applications
SELECT company_name, job_name, created_at 
FROM boss_job_data 
ORDER BY created_at DESC 
LIMIT 10;

# View recent Liepin applications
SELECT * FROM liepin_data 
ORDER BY created_at DESC 
LIMIT 10;

# View blacklist
SELECT * FROM blacklist;

# Exit
.quit
```

---

## 🔧 Troubleshooting

### Java Not Found

```bash
# Install JDK 21
brew install openjdk@21

# Verify
java -version
```

### Port 8888 Already in Use

```bash
# Stop everything
./stop.sh

# Wait and restart
sleep 5
./auto_start.sh

# Or kill process manually
lsof -ti :8888 | xargs kill -9
```

### No Jobs Found

```bash
# Re-configure from resume
python3 config_from_json.py

# Or check/update keywords manually
sqlite3 db/getjobs.db "SELECT keywords FROM boss_config;"
```

### Database Locked

```bash
# Stop all processes
./stop.sh

# Wait for locks to release
sleep 5

# Restart
./auto_start.sh
```

### Application Won't Start

```bash
# Check logs for errors
tail -f logs/app.log

# Verify Java version
java -version

# Check if port is available
lsof -i :8888
```

### Login Not Detected

```bash
# Check Boss login status (via database)
sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='boss';"

# Check Liepin login status (via API)
curl http://localhost:8888/api/liepin/login-status

# Clear cookies and re-login
sqlite3 db/getjobs.db "DELETE FROM cookie WHERE platform='boss';"
```

---

## 🛠️ API Reference

### Boss Zhipin

```bash
# Start delivery
POST http://localhost:8888/api/jobs/boss/execute

# Stop delivery
POST http://localhost:8888/api/jobs/boss/stop

# Check status
GET http://localhost:8888/api/jobs/boss/status

# Get configuration
GET http://localhost:8888/api/boss/config

# Get statistics
GET http://localhost:8888/api/boss/analytics/stats

# Stream progress (SSE)
GET http://localhost:8888/api/jobs/boss/stream
```

### Liepin

```bash
# Start delivery
POST http://localhost:8888/api/liepin/start

# Stop delivery
POST http://localhost:8888/api/liepin/stop

# Check login status
GET http://localhost:8888/api/liepin/login-status

# Get status
GET http://localhost:8888/api/liepin/status

# Get statistics
GET http://localhost:8888/api/liepin/stats

# Get configuration
GET http://localhost:8888/api/liepin/config
```

---

## ⚠️ Important Notes

### Platform Limitations

- **Boss Zhipin**: Daily greeting limit is **150 messages**
- **Liepin**: **No limit** on greetings (recommended platform)
- **51job & Zhilian**: Disabled (poor success rate)

### Best Practices

1. **Start Small**: Test with 2-3 keywords first
2. **Monitor Closely**: Watch the first 10-20 applications
3. **Adjust Filters**: Update blacklist and filters based on results
4. **Respect Limits**: Don't exceed Boss's 150/day limit
5. **Use AI Wisely**: AI greetings cost ~$0.06 per 100 applications

### First Time Login

- You must login via **WeChat QR code** on first run
- Cookies are saved in database for future use
- No need to login again unless cookies expire
- Cookies typically last 1-2 weeks

### Privacy & Security

- All data stored locally in `db/getjobs.db`
- No data sent to external servers except:
  - AI API (if configured)
  - Enterprise WeChat (if configured)
- Review code before use for sensitive data

### Responsible Use

- Comply with platform terms of service
- Don't abuse automation features
- Respect daily limits and rate limits
- Ensure accuracy of submitted applications
- **Use at your own risk**

---

## 📝 Quick Command Reference

### Using Unified Script (Recommended)

```bash
# ===== MAIN COMMANDS =====
./job-app.sh start                  # Start with full automation
./job-app.sh stop                   # Stop everything
./job-app.sh status                 # Check system status
./job-app.sh logs                   # View logs in real-time

# ===== SETUP =====
./job-app.sh check                  # Verify requirements
./job-app.sh setup                  # Initial setup wizard
./job-app.sh config                 # Update config from resume.json

# ===== HELP =====
./job-app.sh help                   # Show all commands
```

### Using Classic Shortcuts

```bash
# ===== SETUP =====
./check_setup.sh                    # Verify requirements
./quick_setup.sh                    # Initial setup
python3 config_from_json.py         # Update from resume

# ===== RUN =====
./auto_start.sh                     # Full automation
./gradlew bootRun                   # Manual start

# ===== CONTROL =====
./stop.sh                           # Stop everything
```

### Direct API Calls

```bash
# Boss control
curl -X POST http://localhost:8888/api/jobs/boss/execute   # Start
curl -X POST http://localhost:8888/api/jobs/boss/stop      # Stop

# Liepin control
curl -X POST http://localhost:8888/api/liepin/start        # Start
curl -X POST http://localhost:8888/api/liepin/stop         # Stop

# ===== MONITOR =====
tail -f logs/app.log                                        # View logs
curl http://localhost:8888/api/jobs/boss/status            # Boss status
curl http://localhost:8888/api/liepin/status               # Liepin status
curl http://localhost:8888/api/boss/analytics/stats        # Boss stats
curl http://localhost:8888/api/liepin/stats                # Liepin stats

# ===== DATABASE =====
sqlite3 db/getjobs.db                                       # Open DB
# Then run SQL queries...
```

---

## 📄 License

See [LICENSE](LICENSE) file.

---

## ⚠️ Disclaimer

This tool is for **educational and personal use only**. Users are responsible for:

- Complying with platform terms of service
- Not abusing automation features
- Respecting daily limits and rate limits
- Ensuring accuracy of applications

**Use at your own risk.** The authors are not responsible for any account suspensions or other consequences.

---

**Happy Job Hunting! 🎉**

---

*For detailed step-by-step instructions, check the inline comments in scripts.*
