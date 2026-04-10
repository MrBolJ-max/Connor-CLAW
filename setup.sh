#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  SYN Systems — Connor-CLAW  |  Setup Script
#  Run once to get fully operational.
# ─────────────────────────────────────────────────────────────────────────────

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}  ╔═══════════════════════════════════════╗"
echo -e "  ║   SYN Systems — Connor-CLAW Setup    ║"
echo -e "  ║       AI Workforce Platform           ║"
echo -e "  ╚═══════════════════════════════════════╝${NC}"
echo ""

# ── 1. Python check ───────────────────────────────────────────────
echo -e "${CYAN}[1/6] Checking Python...${NC}"
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}Python 3 is required. Install from https://python.org${NC}"
  exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}  ✓ Python $PYTHON_VERSION found${NC}"

# ── 2. Virtual environment ────────────────────────────────────────
echo -e "${CYAN}[2/6] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
  python3 -m venv venv
  echo -e "${GREEN}  ✓ venv created${NC}"
else
  echo -e "${GREEN}  ✓ venv already exists${NC}"
fi
source venv/bin/activate

# ── 3. Install dependencies ───────────────────────────────────────
echo -e "${CYAN}[3/6] Installing dependencies...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}  ✓ Dependencies installed${NC}"

# ── 4. Create .env ────────────────────────────────────────────────
echo -e "${CYAN}[4/6] Environment configuration...${NC}"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${YELLOW}  ⚠  .env created from template${NC}"
  echo -e "${YELLOW}     You MUST fill in at minimum:${NC}"
  echo -e "${YELLOW}       ANTHROPIC_API_KEY    — get from console.anthropic.com${NC}"
  echo -e "${YELLOW}       TELEGRAM_BOT_TOKEN   — get from @BotFather on Telegram${NC}"
  echo -e "${YELLOW}       TELEGRAM_ADMIN_CHAT_ID — your Telegram user ID${NC}"
else
  echo -e "${GREEN}  ✓ .env already exists${NC}"
fi

# ── 5. Create data directories ────────────────────────────────────
echo -e "${CYAN}[5/6] Creating data directories...${NC}"
mkdir -p data/knowledge_bases data/reports data/logs
echo -e "${GREEN}  ✓ data/ directories ready${NC}"

# ── 6. Verify config ──────────────────────────────────────────────
echo -e "${CYAN}[6/6] Verifying configuration...${NC}"
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['ANTHROPIC_API_KEY', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ADMIN_CHAT_ID']
missing = [k for k in required if not os.getenv(k) or 'your_' in os.getenv(k, '')]
if missing:
    print('  MISSING keys in .env: ' + ', '.join(missing))
    exit(1)
else:
    print('  Core config OK')
" 2>/dev/null || echo -e "${YELLOW}  ⚠  Fill in .env before running${NC}"

echo ""
echo -e "${GREEN}  ════════════════════════════════════════${NC}"
echo -e "${GREEN}   Setup complete! How to run:${NC}"
echo -e "${GREEN}  ════════════════════════════════════════${NC}"
echo ""
echo -e "   Start Telegram bot:     ${CYAN}python main.py telegram${NC}"
echo -e "   Start API server:       ${CYAN}python main.py api${NC}"
echo -e "   Start everything:       ${CYAN}python main.py all${NC}"
echo -e "   Run demo:               ${CYAN}python scripts/demo.py${NC}"
echo -e "   Onboard new client:     ${CYAN}python scripts/new_client.py${NC}"
echo ""
echo -e "${YELLOW}  → Edit .env with your API keys first!${NC}"
echo ""
