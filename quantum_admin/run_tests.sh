#!/bin/bash
# Quantum Admin - Test Runner Script

set -e

echo "🧪 Quantum Admin Test Suite"
echo "=========================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo "Install dependencies: pip install -r requirements-admin.txt"
    exit 1
fi

# Default: run all tests
TEST_TYPE="${1:-all}"

case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}Running unit tests...${NC}"
        pytest tests/unit/ -v
        ;;

    integration)
        echo -e "${YELLOW}Running integration tests...${NC}"
        pytest tests/integration/ -v
        ;;

    e2e)
        echo -e "${YELLOW}Running e2e tests...${NC}"
        pytest tests/e2e/ -v
        ;;

    coverage)
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        pytest --cov=backend --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}✅ Coverage report: htmlcov/index.html${NC}"
        ;;

    fast)
        echo -e "${YELLOW}Running fast tests (no coverage)...${NC}"
        pytest -v --tb=short
        ;;

    auth)
        echo -e "${YELLOW}Running auth tests...${NC}"
        pytest tests/unit/test_auth.py -v
        ;;

    ai)
        echo -e "${YELLOW}Running AI tests...${NC}"
        pytest tests/unit/test_ai_agent.py -v
        ;;

    all)
        echo -e "${YELLOW}Running all tests with coverage...${NC}"
        pytest --cov=backend --cov-report=html --cov-report=term
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [type]"
        echo ""
        echo "Available types:"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests"
        echo "  e2e          - Run end-to-end tests"
        echo "  coverage     - Run with full coverage report"
        echo "  fast         - Run without coverage"
        echo "  auth         - Run auth tests"
        echo "  ai           - Run AI tests"
        echo "  all          - Run all tests (default)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests completed!${NC}"
