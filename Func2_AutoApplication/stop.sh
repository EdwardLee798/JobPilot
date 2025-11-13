#!/bin/bash
# Stop the Automated Job Application System

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Stopping Job Application System${NC}"
echo -e "${BLUE}========================================${NC}"

PORT=8888

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
    # Try to find by port
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ ! -z "$PID" ]; then
        kill $PID
        echo -e "${GREEN}✓ Application stopped (PID: $PID)${NC}"
    else
        echo -e "${YELLOW}⚠ No application running on port $PORT${NC}"
    fi
fi

echo -e "\n${GREEN}✅ System stopped${NC}"
