#!/bin/bash
# RigSherpa Installation Script
# Targets: Raspberry Pi 5 (8GB) with Raspberry Pi OS 64-bit

set -e

echo "=========================================="
echo "       RigSherpa Installation Script       "
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   exit 1
fi

# Check system requirements
echo -e "\n${YELLOW}Checking system requirements...${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo -e "${RED}Python 3.11+ is required. Found: $PYTHON_VERSION${NC}"
    echo "Install with: sudo apt install python3.11 python3.11-venv"
    exit 1
fi
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Check available memory
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
if [[ $TOTAL_MEM -lt 3500 ]]; then
    echo -e "${RED}At least 4GB RAM required. Found: ${TOTAL_MEM}MB${NC}"
    exit 1
fi
if [[ $TOTAL_MEM -lt 7000 ]]; then
    echo -e "${YELLOW}⚠ Less than 8GB RAM (${TOTAL_MEM}MB) — performance may be limited${NC}"
fi
echo -e "${GREEN}✓ Memory: ${TOTAL_MEM}MB${NC}"

# Check available disk space (model ~1.4GB + KB + deps ≈ 10GB)
AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
if [[ $AVAILABLE_SPACE -lt 10 ]]; then
    echo -e "${YELLOW}⚠ Warning: Less than 10GB free space detected (${AVAILABLE_SPACE}GB)${NC}"
fi
echo -e "${GREEN}✓ Disk space: ${AVAILABLE_SPACE}GB available${NC}"

# Create project directory if needed
PROJECT_DIR="${HOME}/rigsherpa"
if [[ ! -d "$PROJECT_DIR" ]]; then
    echo -e "\n${YELLOW}Creating project directory...${NC}"
    mkdir -p "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# Create virtual environment
echo -e "\n${YELLOW}Setting up Python virtual environment...${NC}"
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Install RigSherpa
echo -e "\n${YELLOW}Installing RigSherpa...${NC}"
if [[ -f "pyproject.toml" ]]; then
    pip install -e .
else
    echo -e "${RED}pyproject.toml not found. Please clone the repository first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ RigSherpa installed${NC}"

# Install Ollama if not present
echo -e "\n${YELLOW}Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo -e "${GREEN}✓ Ollama already installed${NC}"
fi

# Start Ollama service
echo -e "\n${YELLOW}Starting Ollama service...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 5
fi

# Pull the primary model (Qwen3 1.7B — ~1.4 GB download)
echo -e "\n${YELLOW}Downloading LLM model (Qwen3 1.7B)...${NC}"
ollama pull qwen3:1.7b
echo -e "${GREEN}✓ Primary model downloaded${NC}"

# Optionally pull the fallback model
echo -e "${YELLOW}Download fallback model Gemma3 1B? (y/n)${NC}"
read -r PULL_FALLBACK
if [[ "$PULL_FALLBACK" == "y" ]]; then
    ollama pull gemma3:1b
    echo -e "${GREEN}✓ Fallback model downloaded${NC}"
fi

# Create data directories
echo -e "\n${YELLOW}Creating data directories...${NC}"
mkdir -p data/{db,chromadb,logs/{chat,obd2},vehicles}
echo -e "${GREEN}✓ Data directories created${NC}"

# Copy example config
if [[ -f ".env.example" ]] && [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from example${NC}"
fi

# Install systemd service (optional)
echo -e "\n${YELLOW}Do you want to install RigSherpa as a system service? (y/n)${NC}"
read -r INSTALL_SERVICE

if [[ "$INSTALL_SERVICE" == "y" ]]; then
    echo "Installing systemd service..."
    sudo cp src/scripts/systemd/rigsherpa.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable rigsherpa
    echo -e "${GREEN}✓ Systemd service installed${NC}"
    echo "  Start with: sudo systemctl start rigsherpa"
fi

# Final instructions
echo -e "\n${GREEN}=========================================="
echo "       Installation Complete!             "
echo "==========================================${NC}"
echo ""
echo "To start RigSherpa:"
echo "  1. Activate the virtual environment:"
echo "     source ${PROJECT_DIR}/.venv/bin/activate"
echo ""
echo "  2. Start the server:"
echo "     cd ${PROJECT_DIR}"
echo "     python -m backend.main"
echo ""
echo "  3. Open in browser:"
echo "     http://localhost:8000"
echo ""
echo "For more information, see:"
echo "  ${PROJECT_DIR}/docs/README.md"
echo ""
