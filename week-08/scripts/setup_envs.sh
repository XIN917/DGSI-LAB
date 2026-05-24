#!/bin/bash

# DGSI Supply Chain - Environment Setup Script
# Automates venv creation and dependency installation for all services.

# Colors for output
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color

APPS=("provider" "manufacturer" "retailer")

echo -e "${BLUE}🚀 Starting Environment Setup for DGSI Supply Chain...${NC}"

# Check for uv (faster) or fallback to pip
if command -v uv &> /dev/null; then
    INSTALLER="uv"
    echo -e "✨ Found ${GREEN}uv${NC}. Using it for faster installation."
else
    INSTALLER="pip"
    echo -e "⚠️  ${BLUE}uv${NC} not found. Falling back to standard ${BLUE}venv + pip${NC}."
fi

for app in "${APPS[@]}"; do
    echo -e "\n${BLUE}--- Setting up [$app] ---${NC}"
    
    if [ ! -d "$app" ]; then
        echo -e "${RED}❌ Error: Directory $app not found. Skipping.${NC}"
        continue
    fi

    cd "$app" || continue

    if [ "$INSTALLER" == "uv" ]; then
        # Use uv for setup, forcing 'venv' name
        uv venv venv &> /dev/null
        source venv/bin/activate
        uv pip install -r requirements.txt &> /dev/null
        uv pip install -e . &> /dev/null
    else
        # Use standard python venv + pip
        python3 -m venv venv &> /dev/null
        source venv/bin/activate
        pip install --quiet -r requirements.txt
        pip install --quiet -e .
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ [$app] setup complete.${NC}"
    else
        echo -e "${RED}❌ [$app] setup failed.${NC}"
    fi

    deactivate 2>/dev/null
    cd ..
done

echo -e "\n${GREEN}🎉 All environments are ready!${NC}"
echo -e "Next steps:"
echo -e "  1. Run ${BLUE}./scripts/start_all.sh${NC} to start servers."
echo -e "  2. Run ${BLUE}./scripts/test_scenario.sh${NC} to initialize data."
