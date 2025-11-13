#!/bin/bash
# Automated Job Application System Launcher
# This script automatically starts the job delivery system

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PORT=8888
MAX_WAIT=180  # Maximum wait time in seconds
CHECK_INTERVAL=5  # Check interval in seconds

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Automated Job Application System${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to check if port is listening
check_port() {
    lsof -i :$PORT > /dev/null 2>&1
    return $?
}

# Function to check if application is ready
check_app_ready() {
    curl -s http://localhost:$PORT/api/boss/config > /dev/null 2>&1
    return $?
}

# Function to check login status
check_login_status() {
    local platform=$1

    # Boss doesn't have login-status endpoint, check database directly
    if [ "$platform" = "boss" ]; then
        cookie_count=$(sqlite3 db/getjobs.db "SELECT COUNT(*) FROM cookie WHERE platform='boss' AND cookie_value IS NOT NULL AND cookie_value != '';" 2>/dev/null || echo "0")
        if [ "$cookie_count" -gt 0 ]; then
            return 0
        else
            return 1
        fi
    fi

    # Liepin has login-status API
    local response=$(curl -s http://localhost:$PORT/api/${platform}/login-status 2>/dev/null)

    if echo "$response" | grep -q '"isLoggedIn":true'; then
        return 0
    else
        return 1
    fi
}

# Function to start job delivery
start_delivery() {
    local platform=$1
    local endpoint=$2

    echo -e "\n${BLUE}▶ Starting $platform job delivery...${NC}"

    response=$(curl -s -X POST http://localhost:$PORT${endpoint})

    if echo "$response" | grep -q '"success":true'; then
        echo -e "${GREEN}✓ $platform delivery started successfully!${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $platform delivery failed to start${NC}"
        echo "Response: $response"
        return 1
    fi
}

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

# Step 2: Start the application (if needed)
if [ "$SKIP_START" != "true" ]; then
    echo -e "\n${BLUE}[2/6] Starting the application...${NC}"
    echo "Command: ./gradlew bootRun"

    # Start in background and save PID
    nohup ./gradlew bootRun > logs/app.log 2>&1 &
    APP_PID=$!
    echo $APP_PID > .app.pid

    echo -e "${GREEN}✓ Application started (PID: $APP_PID)${NC}"
    echo "  Log file: logs/app.log"
    echo "  You can monitor with: tail -f logs/app.log"
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

# Check Boss login
echo -n "Checking Boss login status"
waited=0
while [ $waited -lt 300 ]; do  # Wait up to 5 minutes for login
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

# Check Liepin login
echo -n "Checking Liepin login status"
waited=0
while [ $waited -lt 60 ]; do  # Wait up to 1 minute for Liepin
    if check_login_status "liepin"; then
        echo -e "\n${GREEN}✓ Liepin login successful!${NC}"
        LIEPIN_LOGGED_IN=true
        break
    fi

    echo -n "."
    sleep $CHECK_INTERVAL
    waited=$((waited + CHECK_INTERVAL))
done

if [ "$LIEPIN_LOGGED_IN" != "true" ]; then
    echo -e "\n${YELLOW}⚠ Liepin login timeout. Skipping Liepin delivery.${NC}"
fi

# Step 5: Confirm before starting delivery
echo -e "\n${BLUE}[5/6] Ready to start automatic job delivery${NC}"
echo ""
echo "Login Status:"
echo "  Boss: $([ "$BOSS_LOGGED_IN" = "true" ] && echo -e "${GREEN}✓ Logged in${NC}" || echo -e "${RED}✗ Not logged in${NC}")"
echo "  Liepin: $([ "$LIEPIN_LOGGED_IN" = "true" ] && echo -e "${GREEN}✓ Logged in${NC}" || echo -e "${RED}✗ Not logged in${NC}")"
echo ""

read -p "Start automatic delivery now? (y/n): " start_now

if [ "$start_now" != "y" ]; then
    echo -e "\n${YELLOW}Job delivery not started. You can start manually with:${NC}"
    echo "  Boss: curl -X POST http://localhost:$PORT/api/jobs/boss/execute"
    echo "  Liepin: curl -X POST http://localhost:$PORT/api/liepin/start"
    exit 0
fi

# Step 6: Start job delivery
echo -e "\n${BLUE}[6/6] Starting job delivery...${NC}"

if [ "$BOSS_LOGGED_IN" = "true" ]; then
    start_delivery "Boss" "/api/jobs/boss/execute"
    BOSS_STARTED=$?
fi

if [ "$LIEPIN_LOGGED_IN" = "true" ]; then
    start_delivery "Liepin" "/api/liepin/start"
    LIEPIN_STARTED=$?
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
echo "  Stop Application: kill \$(cat .app.pid)"
echo ""
echo -e "${BLUE}========================================${NC}"
