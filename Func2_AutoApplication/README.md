# 🚀 Automated Job Application System

An intelligent, fully automated job application system that automatically submits resumes to **Boss Zhipin** and **Liepin** recruitment platforms with AI-powered personalized greetings.

## ✨ Features

- **🤖 Fully Automated**: Automatically searches, filters, and applies to relevant job positions
- **🧠 AI-Powered**: Uses LLM to generate personalized greetings based on job descriptions
- **📋 Resume-Driven**: Automatically extracts keywords and preferences from your resume JSON
- **🎯 Smart Filtering**: Filters inactive HRs, headhunters, and unsuitable positions
- **📊 Real-time Monitoring**: Track application progress in real-time
- **🔄 Persistent Login**: Saves login cookies for seamless re-use
- **🚫 Blacklist Management**: Automatically maintains blacklist of unsuitable companies

## 📋 Prerequisites

- **JDK 21** (required)
- **Gradle** (included via wrapper)
- **Python 3** (for configuration script)
- **macOS/Linux** (tested on macOS)

### Install JDK 21 (if not installed)

\`\`\`bash
# macOS
brew install openjdk@21

# Verify installation
java -version  # Should show 21.x.x
\`\`\`

## 🚀 Quick Start

### 1. Prepare Your Resume

Create or update \`resume.json\` with your information:

\`\`\`json
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
\`\`\`

### 2. Configure AI (Optional)

If you want AI-generated personalized greetings, update \`.env\`:

\`\`\`bash
# .env file
BASE_URL=https://api.openai.com
API_KEY=sk-your-api-key-here
MODEL=gpt-4o-mini
\`\`\`

> **Note**: AI is optional. The system works without it using default greetings.

### 3. Run Quick Setup

\`\`\`bash
./quick_setup.sh
\`\`\`

This will:
- Check your resume.json
- Create .env template if needed
- Initialize database
- Auto-configure from your resume

### 4. Start the System

**Option A: Fully Automated (Recommended)**

\`\`\`bash
./auto_start.sh
\`\`\`

This script will:
1. Start the application
2. Wait for you to login in the browser
3. Automatically start job delivery

**Option B: Manual Control**

\`\`\`bash
# Terminal 1: Start application
./gradlew bootRun

# Terminal 2: Wait for login, then start delivery
curl -X POST http://localhost:8888/api/jobs/boss/execute
curl -X POST http://localhost:8888/api/liepin/start
\`\`\`

### 5. Login to Platforms

When the browser opens:
- Login to **Boss Zhipin** (via WeChat/QR code)
- Login to **Liepin** (via WeChat/QR code)

The system will automatically detect login and start job delivery.

## 🎮 Usage

### Start Job Delivery

\`\`\`bash
# Automated (recommended)
./auto_start.sh

# Manual
./gradlew bootRun
# Then in another terminal:
curl -X POST http://localhost:8888/api/jobs/boss/execute
curl -X POST http://localhost:8888/api/liepin/start
\`\`\`

### Stop Job Delivery

\`\`\`bash
# Stop everything
./stop.sh

# Or stop individually
curl -X POST http://localhost:8888/api/jobs/boss/stop
curl -X POST http://localhost:8888/api/liepin/stop
\`\`\`

### Update Configuration from Resume

\`\`\`bash
# Re-extract keywords and preferences from resume.json
python3 config_from_json.py
\`\`\`

### Manual Configuration

\`\`\`bash
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
\`\`\`

## 📊 Monitoring

### View Logs

\`\`\`bash
# Application logs
tail -f logs/app.log

# Real-time Boss delivery progress
curl http://localhost:8888/api/jobs/boss/stream

# Check Liepin status
curl http://localhost:8888/api/liepin/status
\`\`\`

### Check Statistics

\`\`\`bash
# Boss statistics
curl http://localhost:8888/api/boss/analytics/stats

# Liepin statistics
curl http://localhost:8888/api/liepin/stats
\`\`\`

## ⚙️ Configuration

### Search Criteria

Edit via database or re-run \`python3 config_from_json.py\`:

| Field | Description | Example |
|-------|-------------|---------|
| \`keywords\` | Job search keywords (JSON array) | \`["Python","AI","Backend"]\` |
| \`city_code\` | Target city | \`"Shanghai"\`, \`"Beijing"\` |
| \`salary\` | Salary range | \`"[15-30K]"\` |
| \`experience\` | Required experience | \`"[3-5年,5-10年]"\` |
| \`say_hi\` | Greeting message | Custom or AI-generated |
| \`enable_ai\` | Enable AI greetings | \`1\` (yes) or \`0\` (no) |

## 🛠️ API Reference

### Boss Zhipin

\`\`\`bash
# Start delivery
POST http://localhost:8888/api/jobs/boss/execute

# Stop delivery
POST http://localhost:8888/api/jobs/boss/stop

# Get configuration
GET http://localhost:8888/api/boss/config
\`\`\`

### Liepin

\`\`\`bash
# Start delivery
POST http://localhost:8888/api/liepin/start

# Stop delivery
POST http://localhost:8888/api/liepin/stop

# Check login status
GET http://localhost:8888/api/liepin/login-status
\`\`\`

## 🔧 Troubleshooting

### Application won't start

\`\`\`bash
# Check if JDK 21 is installed
java -version

# Check if port 8888 is available
lsof -i :8888

# View logs
tail -f logs/app.log
\`\`\`

### Job delivery not working

\`\`\`bash
# Check configuration
sqlite3 db/getjobs.db "SELECT * FROM boss_config;"

# Re-configure from resume
python3 config_from_json.py
\`\`\`

## 📝 Important Notes

### Platform Limitations

- **Boss Zhipin**: Daily greeting limit is 150
- **Liepin**: No limit on greetings (recommended platform)
- **51job**: Disabled (poor success rate)
- **Zhilian**: Disabled (poor success rate)

### Best Practices

1. **Test First**: Run with a small set of keywords to test
2. **Monitor Closely**: Watch the first 10-20 applications
3. **Adjust Filters**: Update blacklist and filters based on results
4. **Don't Overuse Boss**: Respect the 150/day limit to avoid account issues

## 🎯 Quick Command Reference

\`\`\`bash
# Setup
./quick_setup.sh                    # Initial setup

# Run
./auto_start.sh                     # Start everything automatically
./gradlew bootRun                   # Manual start

# Configure
python3 config_from_json.py         # Update from resume.json
sqlite3 db/getjobs.db               # Manual database config

# Control
curl -X POST http://localhost:8888/api/jobs/boss/execute   # Start Boss
curl -X POST http://localhost:8888/api/liepin/start        # Start Liepin
./stop.sh                                                    # Stop all

# Monitor
tail -f logs/app.log                                        # View logs
curl http://localhost:8888/api/boss/analytics/stats        # Boss stats
\`\`\`

---

**Happy Job Hunting! 🎉**
