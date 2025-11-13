#!/bin/bash
# System Setup Checker

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  System Setup Checker${NC}"
echo -e "${BLUE}========================================${NC}"

# Check Java
echo -e "\n${BLUE}Checking Java...${NC}"
if command -v java &> /dev/null; then
    java_version=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | cut -d'.' -f1)
    if [ "$java_version" -ge 21 ]; then
        echo -e "${GREEN}✓ Java $java_version installed${NC}"
    else
        echo -e "${RED}✗ Java $java_version found, but JDK 21+ required${NC}"
        echo "  Install with: brew install openjdk@21"
    fi
else
    echo -e "${RED}✗ Java not found${NC}"
    echo "  Install with: brew install openjdk@21"
fi

# Check Python
echo -e "\n${BLUE}Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python $python_version installed${NC}"
else
    echo -e "${RED}✗ Python 3 not found${NC}"
fi

# Check Gradle
echo -e "\n${BLUE}Checking Gradle...${NC}"
if [ -f "./gradlew" ]; then
    echo -e "${GREEN}✓ Gradle wrapper found${NC}"
else
    echo -e "${RED}✗ Gradle wrapper not found${NC}"
fi

# Check resume.json
echo -e "\n${BLUE}Checking resume.json...${NC}"
if [ -f "resume.json" ]; then
    echo -e "${GREEN}✓ resume.json found${NC}"
    name=$(python3 -c "import json; print(json.load(open('resume.json')).get('name', 'N/A'))" 2>/dev/null)
    echo "  Name: $name"
else
    echo -e "${RED}✗ resume.json not found${NC}"
    echo "  Copy CV1.json to resume.json and edit it"
fi

# Check .env
echo -e "\n${BLUE}Checking .env (optional)...${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env found${NC}"
    if grep -q "API_KEY=sk-" .env; then
        echo -e "${GREEN}  API key configured${NC}"
    else
        echo -e "${YELLOW}  ⚠ API key not configured (AI features disabled)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env not found (AI features will be disabled)${NC}"
fi

# Check database
echo -e "\n${BLUE}Checking database...${NC}"
if [ -f "db/getjobs.db" ]; then
    echo -e "${GREEN}✓ Database found${NC}"
    config_count=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM boss_config;" 2>/dev/null || echo "0")
    echo "  Boss config entries: $config_count"
else
    echo -e "${YELLOW}⚠ Database not found (will be created on first run)${NC}"
fi

# Check scripts
echo -e "\n${BLUE}Checking scripts...${NC}"
scripts=("auto_start.sh" "stop.sh" "quick_setup.sh" "config_from_json.py")
for script in "${scripts[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        echo -e "${GREEN}✓ $script${NC}"
    elif [ -f "$script" ]; then
        echo -e "${YELLOW}⚠ $script (not executable)${NC}"
        chmod +x "$script"
        echo "  Made executable"
    else
        echo -e "${RED}✗ $script not found${NC}"
    fi
done

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if command -v java &> /dev/null && [ -f "resume.json" ] && [ -f "./gradlew" ]; then
    echo -e "${GREEN}✅ System is ready!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. ./quick_setup.sh     # Configure from resume.json"
    echo "  2. ./auto_start.sh      # Start the system"
else
    echo -e "${YELLOW}⚠ Setup incomplete${NC}"
    echo ""
    echo "Required actions:"
    [ ! -f "resume.json" ] && echo "  - Create/edit resume.json"
    ! command -v java &> /dev/null && echo "  - Install JDK 21"
    echo ""
    echo "Then run: ./quick_setup.sh"
fi

echo -e "${BLUE}========================================${NC}"
