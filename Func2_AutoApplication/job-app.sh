#!/bin/bash
# Unified Job Application System Manager
# All-in-one script for managing the automated job application system

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PORT=8888
MAX_WAIT=180
CHECK_INTERVAL=5

# ============================================================================
# Helper Functions
# ============================================================================

show_banner() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Automated Job Application System${NC}"
    echo -e "${BLUE}========================================${NC}"
}

show_help() {
    show_banner
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start       Start the job application system (full automation)"
    echo "  stop        Stop all running services"
    echo "  status      Check system status"
    echo "  check       Verify system requirements and setup"
    echo "  setup       Quick setup wizard"
    echo "  config      Update configuration from resume.json"
    echo "  logs        View application logs"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start        # Start with full automation"
    echo "  $0 stop         # Stop everything"
    echo "  $0 status       # Check what's running"
    echo "  $0 logs         # View logs in real-time"
    echo ""
    echo "API Endpoints:"
    echo "  Boss:   curl -X POST http://localhost:$PORT/api/jobs/boss/execute"
    echo "  Liepin: curl -X POST http://localhost:$PORT/api/liepin/start"
    echo ""
}

check_port() {
    lsof -i :$PORT > /dev/null 2>&1
    return $?
}

check_app_ready() {
    curl -s http://localhost:$PORT/api/boss/config > /dev/null 2>&1
    return $?
}

check_login_status() {
    local platform=$1

    if [ "$platform" = "boss" ]; then
        cookie_count=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='boss' AND cookie_value IS NOT NULL AND cookie_value != '';" 2>/dev/null || echo "0")
        if [ "$cookie_count" -gt 0 ]; then
            return 0
        else
            return 1
        fi
    fi

    local response=$(curl -s http://localhost:$PORT/api/${platform}/login-status 2>/dev/null)

    if echo "$response" | grep -q '"isLoggedIn":true'; then
        return 0
    else
        return 1
    fi
}

start_delivery() {
    local platform=$1
    local endpoint=$2

    echo -e "\n${BLUE}▶ Starting $platform job delivery...${NC}"

    response=$(curl -s -X POST http://localhost:$PORT${endpoint})

    if echo "$response" | grep -q '"success":true' || echo "$response" | grep -q '"status":"started"'; then
        echo -e "${GREEN}✓ $platform delivery started successfully!${NC}"
        return 0
    elif echo "$response" | grep -q '"status":"running"' || echo "$response" | grep -q "已在运行"; then
        echo -e "${YELLOW}⚠ $platform delivery is already running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $platform delivery failed to start${NC}"
        echo "Response: $response"
        return 1
    fi
}

# ============================================================================
# Command: START
# ============================================================================

cmd_start() {
    show_banner

    # Step 1: Check if already running
    echo -e "\n${BLUE}[1/6] Checking if application is already running...${NC}"
    if check_port; then
        echo -e "${YELLOW}⚠ Application is already running on port $PORT${NC}"
        read -p "Do you want to stop it and restart? (y/n): " answer
        if [ "$answer" = "y" ]; then
            echo "Stopping existing process..."
            lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
            sleep 2
        else
            echo "Using existing instance..."
            SKIP_START=true
        fi
    fi

    # Step 2: Start the application
    if [ "$SKIP_START" != "true" ]; then
        echo -e "\n${BLUE}[2/6] Starting the application...${NC}"
        echo "Command: ./gradlew bootRun"

        mkdir -p logs

        nohup ./gradlew bootRun > logs/app.log 2>&1 &
        APP_PID=$!
        echo $APP_PID > .app.pid

        echo -e "${GREEN}✓ Application started (PID: $APP_PID)${NC}"
        echo "  Log file: logs/app.log"
        echo "  Monitor with: tail -f logs/app.log"
    else
        echo -e "\n${BLUE}[2/6] Skipping application start (already running)${NC}"
    fi

    # Step 3: Wait for application to be ready
    echo -e "\n${BLUE}[3/6] Waiting for application to start...${NC}"
    waited=0
    while [ $waited -lt $MAX_WAIT ]; do
        if check_app_ready; then
            echo -e "${GREEN}✓ Application is ready!${NC}"
            break
        fi

        echo -n "."
        sleep $CHECK_INTERVAL
        waited=$((waited + CHECK_INTERVAL))
    done

    if [ $waited -ge $MAX_WAIT ]; then
        echo -e "\n${RED}✗ Application failed to start within $MAX_WAIT seconds${NC}"
        echo "Please check logs/app.log for errors"
        exit 1
    fi

    # Step 4: Wait for user login
    echo -e "\n${BLUE}[4/6] Waiting for user login...${NC}"
    echo -e "${YELLOW}📌 Please login to Boss/Liepin in the opened browser window${NC}"
    echo ""

    echo -n "Checking Boss login status"
    waited=0
    while [ $waited -lt 300 ]; do
        if check_login_status "boss"; then
            echo -e "\n${GREEN}✓ Boss login successful!${NC}"
            BOSS_LOGGED_IN=true
            break
        fi

        echo -n "."
        sleep $CHECK_INTERVAL
        waited=$((waited + CHECK_INTERVAL))
    done

    if [ "$BOSS_LOGGED_IN" != "true" ]; then
        echo -e "\n${YELLOW}⚠ Boss login timeout. You can login later and start manually.${NC}"
    fi

    # Step 5: Start Boss delivery
    echo -e "\n${BLUE}[5/7] Starting Boss Zhipin delivery${NC}"
    echo ""

    if [ "$BOSS_LOGGED_IN" = "true" ]; then
        echo -e "${GREEN}✓ Boss is logged in${NC}"
        read -p "Start Boss delivery now? (y/n): " start_boss

        if [ "$start_boss" = "y" ]; then
            start_delivery "Boss" "/api/jobs/boss/execute"
            BOSS_STARTED=$?

            if [ $BOSS_STARTED -eq 0 ]; then
                echo -e "\n${GREEN}✓ Boss delivery is running${NC}"
                echo "Monitor progress: tail -f logs/app.log"
            fi
        else
            echo -e "${YELLOW}Boss delivery skipped${NC}"
        fi
    else
        echo -e "${RED}✗ Boss not logged in, cannot start delivery${NC}"
    fi

    # Step 6: Ask about Liepin
    echo -e "\n${BLUE}[6/7] Liepin delivery (optional)${NC}"
    echo ""
    read -p "Do you want to start Liepin delivery? (y/n): " want_liepin

    if [ "$want_liepin" != "y" ]; then
        echo -e "${YELLOW}Liepin delivery skipped${NC}"
        echo "You can start it later manually:"
        echo "  curl -X POST http://localhost:$PORT/api/liepin/start"
    else
        if [ $BOSS_STARTED -eq 0 ] 2>/dev/null; then
            echo -e "\n${YELLOW}⚠ Stopping Boss delivery before starting Liepin...${NC}"
            curl -s -X POST http://localhost:$PORT/api/jobs/boss/stop > /dev/null
            sleep 2
            echo -e "${GREEN}✓ Boss delivery stopped${NC}"
        fi

        echo -e "\n${BLUE}[7/7] Checking Liepin login...${NC}"
        liepin_cookie_count=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='liepin' AND cookie_value IS NOT NULL AND cookie_value != '';" 2>/dev/null || echo "0")

        if [ "$liepin_cookie_count" -gt 0 ]; then
            echo -e "${GREEN}✓ Liepin already logged in (found cookies)${NC}"
        else
            echo -e "${YELLOW}⚠ Liepin not logged in yet${NC}"
            echo "Please login to Liepin in the browser window"
            echo "Waiting for Liepin login (up to 3 minutes)..."

            waited=0
            while [ $waited -lt 180 ]; do
                liepin_cookie_count=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='liepin' AND cookie_value IS NOT NULL AND cookie_value != '';" 2>/dev/null || echo "0")
                if [ "$liepin_cookie_count" -gt 0 ]; then
                    echo -e "\n${GREEN}✓ Liepin login detected!${NC}"
                    break
                fi
                echo -n "."
                sleep $CHECK_INTERVAL
                waited=$((waited + CHECK_INTERVAL))
            done

            if [ "$liepin_cookie_count" -eq 0 ]; then
                echo -e "\n${RED}✗ Liepin login timeout${NC}"
                echo "You can start Liepin manually after login:"
                echo "  curl -X POST http://localhost:$PORT/api/liepin/start"
                LIEPIN_LOGGED_IN=false
            else
                LIEPIN_LOGGED_IN=true
            fi
        fi

        if [ "$liepin_cookie_count" -gt 0 ]; then
            echo -e "\n${BLUE}Starting Liepin delivery...${NC}"
            start_delivery "Liepin" "/api/liepin/start"
            LIEPIN_STARTED=$?
        fi
    fi

    # Final summary
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Automated Job Application System Started!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Status:"
    echo "  Application: Running (PID: $(cat .app.pid 2>/dev/null || echo 'N/A'))"
    echo "  Boss Delivery: $([ $BOSS_STARTED -eq 0 ] 2>/dev/null && echo -e "${GREEN}Running${NC}" || echo -e "${YELLOW}Not started${NC}")"
    echo "  Liepin Delivery: $([ $LIEPIN_STARTED -eq 0 ] 2>/dev/null && echo -e "${GREEN}Running${NC}" || echo -e "${YELLOW}Not started${NC}")"
    echo ""
    echo "Monitoring:"
    echo "  Application logs: tail -f logs/app.log"
    echo "  Boss progress: curl http://localhost:$PORT/api/jobs/boss/stream"
    echo "  Liepin status: curl http://localhost:$PORT/api/liepin/status"
    echo ""
    echo "Control:"
    echo "  Stop Boss: curl -X POST http://localhost:$PORT/api/jobs/boss/stop"
    echo "  Stop Liepin: curl -X POST http://localhost:$PORT/api/liepin/stop"
    echo "  Stop All: $0 stop"
    echo ""
    echo -e "${BLUE}========================================${NC}"
}

# ============================================================================
# Command: STOP
# ============================================================================

cmd_stop() {
    show_banner
    echo -e "${BLUE}  Stopping All Services${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Stop delivery tasks
    echo -e "\n${BLUE}Stopping delivery tasks...${NC}"
    curl -s -X POST http://localhost:$PORT/api/jobs/boss/stop > /dev/null 2>&1 && echo -e "${GREEN}✓ Boss delivery stopped${NC}" || echo -e "${YELLOW}⚠ Boss not running${NC}"
    curl -s -X POST http://localhost:$PORT/api/liepin/stop > /dev/null 2>&1 && echo -e "${GREEN}✓ Liepin delivery stopped${NC}" || echo -e "${YELLOW}⚠ Liepin not running${NC}"

    # Stop application
    echo -e "\n${BLUE}Stopping application...${NC}"
    if [ -f .app.pid ]; then
        PID=$(cat .app.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo -e "${GREEN}✓ Application stopped (PID: $PID)${NC}"
            rm .app.pid
        else
            echo -e "${YELLOW}⚠ Process $PID not found${NC}"
            rm .app.pid
        fi
    else
        PID=$(lsof -ti :$PORT 2>/dev/null)
        if [ ! -z "$PID" ]; then
            kill $PID
            echo -e "${GREEN}✓ Application stopped (PID: $PID)${NC}"
        else
            echo -e "${YELLOW}⚠ No application running on port $PORT${NC}"
        fi
    fi

    echo -e "\n${GREEN}✅ System stopped${NC}"
}

# ============================================================================
# Command: STATUS
# ============================================================================

cmd_status() {
    show_banner
    echo -e "${BLUE}  System Status${NC}"
    echo -e "${BLUE}========================================${NC}"

    echo -e "\n${BLUE}Application:${NC}"
    if check_port; then
        PID=$(lsof -ti :$PORT 2>/dev/null)
        echo -e "  ${GREEN}✓ Running${NC} (PID: $PID, Port: $PORT)"
    else
        echo -e "  ${RED}✗ Not running${NC}"
    fi

    if check_port; then
        echo -e "\n${BLUE}Boss Zhipin:${NC}"
        boss_status=$(curl -s http://localhost:$PORT/api/jobs/boss/status 2>/dev/null || echo "{}")
        if echo "$boss_status" | grep -q '"isRunning":true'; then
            echo -e "  ${GREEN}✓ Delivery running${NC}"
        else
            echo -e "  ${YELLOW}○ Not running${NC}"
        fi

        boss_cookies=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='boss' AND cookie_value IS NOT NULL;" 2>/dev/null || echo "0")
        if [ "$boss_cookies" -gt 0 ]; then
            echo -e "  ${GREEN}✓ Logged in${NC}"
        else
            echo -e "  ${YELLOW}○ Not logged in${NC}"
        fi

        echo -e "\n${BLUE}Liepin:${NC}"
        liepin_status=$(curl -s http://localhost:$PORT/api/liepin/status 2>/dev/null || echo "{}")
        if echo "$liepin_status" | grep -q '"isRunning":true'; then
            echo -e "  ${GREEN}✓ Delivery running${NC}"
        else
            echo -e "  ${YELLOW}○ Not running${NC}"
        fi

        liepin_cookies=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='liepin' AND cookie_value IS NOT NULL;" 2>/dev/null || echo "0")
        if [ "$liepin_cookies" -gt 0 ]; then
            echo -e "  ${GREEN}✓ Logged in${NC}"
        else
            echo -e "  ${YELLOW}○ Not logged in${NC}"
        fi
    fi

    echo -e "\n${BLUE}========================================${NC}"
}

# ============================================================================
# Command: CHECK
# ============================================================================

cmd_check() {
    show_banner
    echo -e "${BLUE}  System Requirements Check${NC}"
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

    # Check resume.json
    echo -e "\n${BLUE}Checking resume.json...${NC}"
    if [ -f "resume.json" ]; then
        echo -e "${GREEN}✓ resume.json found${NC}"
        name=$(python3 -c "import json; print(json.load(open('resume.json')).get('name', 'N/A'))" 2>/dev/null)
        echo "  Name: $name"
    else
        echo -e "${RED}✗ resume.json not found${NC}"
    fi

    # Check database
    echo -e "\n${BLUE}Checking database...${NC}"
    if [ -f "db/getjobs.db" ]; then
        echo -e "${GREEN}✓ Database found${NC}"
        config_count=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM boss_config;" 2>/dev/null || echo "0")
        echo "  Config entries: $config_count"
    else
        echo -e "${YELLOW}⚠ Database not found (will be created on first run)${NC}"
    fi

    echo -e "\n${BLUE}========================================${NC}"
    if command -v java &> /dev/null && [ -f "resume.json" ]; then
        echo -e "${GREEN}✅ System is ready!${NC}"
        echo "  Run: $0 start"
    else
        echo -e "${YELLOW}⚠ Setup incomplete${NC}"
        echo "  Run: $0 setup"
    fi
    echo -e "${BLUE}========================================${NC}"
}

# ============================================================================
# Command: SETUP
# ============================================================================

cmd_setup() {
    show_banner
    echo -e "${BLUE}  Quick Setup Wizard${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Check resume.json
    echo -e "\n${BLUE}[1/3] Checking resume.json...${NC}"
    if [ ! -f "resume.json" ]; then
        echo -e "${RED}✗ resume.json not found${NC}"
        echo "Please create resume.json with your resume data"
        exit 1
    else
        echo -e "${GREEN}✓ resume.json found${NC}"
    fi

    # Check .env
    echo -e "\n${BLUE}[2/3] Checking .env configuration...${NC}"
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}⚠ Creating .env template...${NC}"
        cat > .env << 'EOF'
# AI API Configuration (optional)
BASE_URL=https://api.openai.com
API_KEY=sk-your-api-key-here
MODEL=gpt-4o-mini

# Enterprise WeChat Webhook (optional)
HOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
EOF
        echo -e "${GREEN}✓ .env template created${NC}"
        echo -e "${YELLOW}  Edit .env to add your API key (optional)${NC}"
    else
        echo -e "${GREEN}✓ .env found${NC}"
    fi

    # Configure from JSON
    echo -e "\n${BLUE}[3/3] Configuring from resume.json...${NC}"
    python3 config_from_json.py

    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ Setup Complete!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Next step:"
    echo "  $0 start"
    echo ""
}

# ============================================================================
# Command: CONFIG
# ============================================================================

cmd_config() {
    show_banner
    echo -e "${BLUE}  Updating Configuration${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    python3 config_from_json.py

    echo ""
    echo -e "${GREEN}✅ Configuration updated!${NC}"
}

# ============================================================================
# Command: LOGS
# ============================================================================

cmd_logs() {
    if [ ! -f "logs/app.log" ]; then
        echo -e "${RED}✗ Log file not found${NC}"
        echo "  Start the application first: $0 start"
        exit 1
    fi

    echo -e "${BLUE}Showing logs (Ctrl+C to exit)...${NC}"
    tail -f logs/app.log
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    case "${1:-help}" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        status)
            cmd_status
            ;;
        check)
            cmd_check
            ;;
        setup)
            cmd_setup
            ;;
        config)
            cmd_config
            ;;
        logs)
            cmd_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Error: Unknown command '$1'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
