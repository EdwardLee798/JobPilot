#!/bin/bash
# Quick Setup Script
# This script helps you configure the system quickly

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Quick Setup Wizard${NC}"
echo -e "${BLUE}========================================${NC}"

# Step 1: Check resume.json
echo -e "\n${BLUE}[1/4] Checking resume.json...${NC}"
if [ ! -f "resume.json" ]; then
    echo -e "${YELLOW}⚠ resume.json not found${NC}"
    echo "Please create resume.json with your resume data"
    echo "Example structure:"
    cat << 'EOF'
{
  "name": "Your Name",
  "contacts": {
    "email": "your@email.com",
    "phone": "13800138000"
  },
  "skills": ["Python", "Java", "Data Analysis"],
  "experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "role": "Your Role"
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
EOF
    exit 1
else
    echo -e "${GREEN}✓ resume.json found${NC}"
fi

# Step 2: Check .env file
echo -e "\n${BLUE}[2/4] Checking AI configuration (.env)...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating template...${NC}"
    cat > .env << 'EOF'
# Enterprise WeChat Webhook (optional)
HOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key_here

# AI API Configuration (for intelligent greeting generation)
BASE_URL=https://api.openai.com
API_KEY=sk-your-api-key-here
MODEL=gpt-4o-mini

# Note: AI is optional. Set enable_ai=0 in database to disable
EOF
    echo -e "${GREEN}✓ .env template created${NC}"
    echo -e "${YELLOW}⚠ Please update .env with your API key if you want to use AI features${NC}"
else
    echo -e "${GREEN}✓ .env found${NC}"
fi

# Step 3: Run first time to create database
echo -e "\n${BLUE}[3/4] Initializing database...${NC}"
if [ ! -f "db/getjobs.db" ]; then
    echo "Starting application briefly to create database..."
    echo "This may take 30-60 seconds..."

    # Start and stop quickly
    timeout 60 ./gradlew bootRun > /dev/null 2>&1 || true
    sleep 5

    if [ -f "db/getjobs.db" ]; then
        echo -e "${GREEN}✓ Database created${NC}"
    else
        echo -e "${YELLOW}⚠ Database not created. Will be created on first run.${NC}"
    fi
else
    echo -e "${GREEN}✓ Database already exists${NC}"
fi

# Step 4: Configure from JSON
echo -e "\n${BLUE}[4/4] Configuring from resume.json...${NC}"
if [ -f "db/getjobs.db" ]; then
    python3 config_from_json.py
else
    echo -e "${YELLOW}⚠ Skipping configuration (database not ready)${NC}"
    echo "Run 'python3 config_from_json.py' after first application start"
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review configuration:"
echo "     sqlite3 db/getjobs.db 'SELECT keywords, city_code, salary FROM boss_config;'"
echo ""
echo "  2. Start the system:"
echo "     ./auto_start.sh"
echo ""
echo "Or run manually:"
echo "  ./gradlew bootRun"
echo ""
echo -e "${BLUE}========================================${NC}"
