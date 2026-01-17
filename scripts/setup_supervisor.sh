#!/bin/bash
#
# Setup Supervisor for Restaurant Management System
# ==================================================
#
# This script installs Supervisor and configures all services
# (Gunicorn, Daphne, Celery Worker, Celery Beat)
#
# Usage:
#   chmod +x scripts/setup_supervisor.sh
#   ./scripts/setup_supervisor.sh

set -e  # Exit on error

echo "======================================"
echo "  SUPERVISOR SETUP SCRIPT"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as restaurant user
if [ "$USER" != "restaurant" ]; then
    echo -e "${RED}❌ This script must be run as 'restaurant' user${NC}"
    echo "   Switch user: sudo su - restaurant"
    exit 1
fi

# 1. Install Supervisor (requires sudo)
echo -e "\n${YELLOW}📦 Step 1: Installing Supervisor...${NC}"
sudo apt update
sudo apt install -y supervisor

echo -e "${GREEN}✅ Supervisor installed${NC}"

# 2. Create logs directory
echo -e "\n${YELLOW}📁 Step 2: Creating logs directory...${NC}"
mkdir -p ~/app/logs
echo -e "${GREEN}✅ Logs directory created${NC}"

# 3. Copy Supervisor configs
echo -e "\n${YELLOW}📋 Step 3: Copying Supervisor configs...${NC}"
sudo cp ~/app/BE_restaurantV2/supervisor/*.conf /etc/supervisor/conf.d/

# Verify configs copied
if [ -f "/etc/supervisor/conf.d/gunicorn.conf" ]; then
    echo -e "${GREEN}✅ Configs copied to /etc/supervisor/conf.d/${NC}"
else
    echo -e "${RED}❌ Failed to copy configs${NC}"
    exit 1
fi

# 4. Reload Supervisor
echo -e "\n${YELLOW}🔄 Step 4: Reloading Supervisor...${NC}"
sudo supervisorctl reread
sudo supervisorctl update

echo -e "${GREEN}✅ Supervisor reloaded${NC}"

# 5. Start all services
echo -e "\n${YELLOW}🚀 Step 5: Starting all services...${NC}"
sudo supervisorctl start restaurant:*

# Wait a bit for services to start
sleep 3

# 6. Check status
echo -e "\n${YELLOW}📊 Step 6: Checking service status...${NC}"
sudo supervisorctl status

# 7. Verify services are running
echo -e "\n${YELLOW}🔍 Step 7: Verifying services...${NC}"

FAILED=0

# Check Gunicorn
if sudo supervisorctl status gunicorn | grep -q "RUNNING"; then
    echo -e "${GREEN}✅ Gunicorn: RUNNING${NC}"
else
    echo -e "${RED}❌ Gunicorn: NOT RUNNING${NC}"
    FAILED=1
fi

# Check Daphne
if sudo supervisorctl status daphne | grep -q "RUNNING"; then
    echo -e "${GREEN}✅ Daphne: RUNNING${NC}"
else
    echo -e "${RED}❌ Daphne: NOT RUNNING${NC}"
    FAILED=1
fi

# Check Celery Worker
if sudo supervisorctl status celery_worker | grep -q "RUNNING"; then
    echo -e "${GREEN}✅ Celery Worker: RUNNING${NC}"
else
    echo -e "${RED}❌ Celery Worker: NOT RUNNING${NC}"
    FAILED=1
fi

# Check Celery Beat
if sudo supervisorctl status celery_beat | grep -q "RUNNING"; then
    echo -e "${GREEN}✅ Celery Beat: RUNNING${NC}"
else
    echo -e "${RED}❌ Celery Beat: NOT RUNNING${NC}"
    FAILED=1
fi

# Final result
echo ""
echo "======================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL SERVICES RUNNING!${NC}"
    echo ""
    echo "Useful commands:"
    echo "  sudo supervisorctl status          - Check status"
    echo "  sudo supervisorctl restart all     - Restart all"
    echo "  sudo supervisorctl restart gunicorn - Restart specific service"
    echo "  sudo supervisorctl tail -f gunicorn - View logs"
    echo "  tail -f ~/app/logs/gunicorn-*.log  - View raw logs"
else
    echo -e "${RED}⚠️  SOME SERVICES FAILED TO START${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  sudo supervisorctl tail -1000 gunicorn      - Check logs"
    echo "  sudo supervisorctl tail -1000 daphne        - Check logs"
    echo "  sudo supervisorctl tail -1000 celery_worker - Check logs"
    echo "  cat ~/app/logs/gunicorn-supervisor-error.log"
fi
echo "======================================"

exit $FAILED
