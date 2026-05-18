#!/bin/bash

# Colors for log output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting JUNO Assist integrated environment...${NC}"

# Define the root directory
ROOT_DIR=$(pwd)

# Function to handle script termination
cleanup() {
    echo -e "\n${RED}Caught termination signal! Shutting down all processes...${NC}"
    # Kill all child processes of the current shell
    pkill -P $$
    echo -e "${GREEN}All processes terminated successfully. Goodbye!${NC}"
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM to call the cleanup function
trap cleanup SIGINT SIGTERM

# 1. Build ROS Workspace (if needed)
echo -e "${BLUE}[ROS] Checking ROS Workspace...${NC}"
if [ ! -d "devel" ]; then
    echo -e "${YELLOW}[ROS] Workspace not built. Building now...${NC}"
    catkin_make
fi

# 2. Start roscore
# (Removed to prevent race conditions with roslaunch starting its own master)

# 3. Launch ROS Nodes
echo -e "${BLUE}[ROS] Sourcing workspace and launching juno_bringup...${NC}"
source devel/setup.bash
roslaunch juno_bringup juno_robot.launch 2>&1 | sed -e "s/^/[ROS] /" &

# 4. Start Backend
echo -e "${GREEN}[Backend] Starting FastAPI backend...${NC}"
cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}[Backend] Creating virtual environment...${NC}"
    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

export JUNO_ROBOT_INTERFACE=ros
export JUNO_DASHBOARD_URL=http://localhost:5173
python main.py 2>&1 | sed -e "s/^/[Backend] /" &

# 5. Start Dashboard
echo -e "${BLUE}[Dashboard] Starting React dashboard...${NC}"
cd "$ROOT_DIR/dashboard"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[Dashboard] Installing dependencies...${NC}"
    npm install
fi
npm run dev 2>&1 | sed -e "s/^/[Dashboard] /" &

# Wait for all background processes to keep the script running
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   All systems started successfully!    ${NC}"
echo -e "${GREEN}   Press Ctrl+C to stop everything.     ${NC}"
echo -e "${GREEN}========================================${NC}\n"

wait
