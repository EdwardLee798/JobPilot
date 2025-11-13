# Getting Started Guide

## Prerequisites Check

Before starting, ensure you have:

- ✅ JDK 21 installed (`java -version`)
- ✅ Python 3 installed (`python3 --version`)
- ✅ Your resume prepared

## Step-by-Step Guide

### Step 1: Verify Installation

```bash
# Check Java
java -version
# Should show: openjdk version "21.x.x"

# Check Python
python3 --version
# Should show: Python 3.x.x

# Check Gradle wrapper
./gradlew --version
```

### Step 2: Prepare Resume

Edit `resume.json`:

```json
{
  "name": "Zhang San",
  "contacts": {
    "email": "zhangsan@example.com",
    "phone": "13800138000"
  },
  "skills": ["Python", "Java", "Data Analysis"],
  "experience": [
    {
      "company": "Tech Corp",
      "title": "Data Analyst",
      "role": "Data Analyst"
    }
  ],
  "education": [
    {
      "school": "Tsinghua University",
      "degree": "Master",
      "major": "Computer Science"
    }
  ]
}
```

### Step 3: Configure AI (Optional)

Create/edit `.env`:

```
BASE_URL=https://api.openai.com
API_KEY=sk-your-key-here
MODEL=gpt-4o-mini
```

Skip this if you don't want AI features.

### Step 4: Run Setup

```bash
./quick_setup.sh
```

Watch for success messages.

### Step 5: Start System

```bash
./auto_start.sh
```

### Step 6: Login

When browser opens:
1. Scan QR code for Boss Zhipin
2. Scan QR code for Liepin
3. Wait for auto-detection

### Step 7: Monitor

```bash
# In a new terminal
tail -f logs/app.log
```

### Step 8: Stop When Done

```bash
./stop.sh
```

## Common Issues

**Issue: Java not found**
```bash
brew install openjdk@21
```

**Issue: Port 8888 already in use**
```bash
lsof -ti :8888 | xargs kill -9
```

**Issue: Database locked**
```bash
./stop.sh
sleep 5
./auto_start.sh
```

**Issue: No jobs found**
```bash
# Update keywords
python3 config_from_json.py

# Or manually
sqlite3 db/getjobs.db
UPDATE boss_config SET keywords = '["Python","Backend"]' WHERE id = 1;
.quit
```

## Tips

1. **Start small**: Test with 2-3 keywords first
2. **Monitor closely**: Watch the first 10 applications
3. **Adjust as needed**: Update blacklist and filters
4. **Be patient**: Login detection may take 30-60 seconds

## Next Steps

- Read `README.md` for detailed documentation
- Check `resume.json` structure
- Review database configuration
- Monitor application logs

---

Need help? Check `README.md` for full documentation.
