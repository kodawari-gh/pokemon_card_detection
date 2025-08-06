#!/bin/bash

# Script to run all tests for the Pokemon Card Detection project

set -e  # Exit on error

echo "========================================="
echo "Pokemon Card Detection - Test Suite"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
    fi
}

# Track overall status
OVERALL_STATUS=0

# Frontend Tests
echo -e "${YELLOW}Running Frontend Tests...${NC}"
echo "----------------------------------------"
cd frontend
npm install --silent 2>/dev/null || npm install
npx playwright install chromium firefox webkit 2>/dev/null || true
npm test
FRONTEND_STATUS=$?
print_status $FRONTEND_STATUS "Frontend tests"
if [ $FRONTEND_STATUS -ne 0 ]; then
    OVERALL_STATUS=1
fi
cd ..
echo ""

# Python Tests (Database and Core)
echo -e "${YELLOW}Running Python Tests...${NC}"
echo "----------------------------------------"

# Check if virtual environment exists
if [ -d "ai-backend/venv" ]; then
    echo "Activating virtual environment..."
    source ai-backend/venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv ai-backend/venv
    source ai-backend/venv/bin/activate
    echo "Installing Python dependencies..."
    pip install -q -r database/requirements.txt
    pip install -q pytest pytest-cov pytest-asyncio
fi

# Run pytest
python -m pytest
PYTHON_STATUS=$?
print_status $PYTHON_STATUS "Python tests"
if [ $PYTHON_STATUS -ne 0 ]; then
    OVERALL_STATUS=1
fi
echo ""

# Linting Checks
echo -e "${YELLOW}Running Linting Checks...${NC}"
echo "----------------------------------------"

# Frontend linting
echo "Frontend linting..."
cd frontend
npm run lint
FRONTEND_LINT_STATUS=$?
print_status $FRONTEND_LINT_STATUS "Frontend linting"
if [ $FRONTEND_LINT_STATUS -ne 0 ]; then
    OVERALL_STATUS=1
fi
cd ..

# Python linting
echo "Python linting..."
if command -v flake8 &> /dev/null; then
    flake8 database/ core/ --max-line-length=120 --exclude=venv,__pycache__,.git
    PYTHON_LINT_STATUS=$?
    print_status $PYTHON_LINT_STATUS "Python linting"
    if [ $PYTHON_LINT_STATUS -ne 0 ]; then
        OVERALL_STATUS=1
    fi
else
    echo "flake8 not installed, skipping Python linting"
fi
echo ""

# Coverage Report
echo -e "${YELLOW}Coverage Report:${NC}"
echo "----------------------------------------"
if [ -f "htmlcov/index.html" ]; then
    echo "HTML coverage report generated at: htmlcov/index.html"
fi
if [ -f "coverage.xml" ]; then
    echo "XML coverage report generated at: coverage.xml"
fi
echo ""

# Final Summary
echo "========================================="
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully!${NC}"
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
fi
echo "========================================="

exit $OVERALL_STATUS