#!/bin/bash
# Quantum Admin - Performance Testing Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 Quantum Admin - Performance Test Suite"
echo "========================================"
echo ""

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${RED}❌ Locust not found${NC}"
    echo "Install: pip install locust"
    exit 1
fi

# Check if server is running
echo -e "${YELLOW}Checking if server is running...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Server is running${NC}"
else
    echo -e "${RED}❌ Server not running at http://localhost:8000${NC}"
    echo "Start server: uvicorn main:app --reload"
    exit 1
fi

# Create results directory
mkdir -p performance_results

# Test type
TEST_TYPE="${1:-quick}"

case $TEST_TYPE in
    quick)
        echo -e "\n${YELLOW}Running QUICK performance test (10 users, 1 min)${NC}"
        locust -f locustfile.py MixedWorkloadUser \\
            --host=http://localhost:8000 \\
            --users 10 \\
            --spawn-rate 2 \\
            --run-time 1m \\
            --headless \\
            --csv=performance_results/quick_test \\
            --html=performance_results/quick_test.html
        ;;

    moderate)
        echo -e "\n${YELLOW}Running MODERATE load test (100 users, 5 min)${NC}"
        locust -f locustfile.py MixedWorkloadUser \\
            --host=http://localhost:8000 \\
            --users 100 \\
            --spawn-rate 10 \\
            --run-time 5m \\
            --headless \\
            --csv=performance_results/moderate_test \\
            --html=performance_results/moderate_test.html
        ;;

    heavy)
        echo -e "\n${YELLOW}Running HEAVY load test (500 users, 10 min)${NC}"
        locust -f locustfile.py MixedWorkloadUser \\
            --host=http://localhost:8000 \\
            --users 500 \\
            --spawn-rate 50 \\
            --run-time 10m \\
            --headless \\
            --csv=performance_results/heavy_test \\
            --html=performance_results/heavy_test.html
        ;;

    spike)
        echo -e "\n${YELLOW}Running SPIKE test (1000 users rapidly)${NC}"
        locust -f locustfile.py MixedWorkloadUser \\
            --host=http://localhost:8000 \\
            --users 1000 \\
            --spawn-rate 100 \\
            --run-time 2m \\
            --headless \\
            --csv=performance_results/spike_test \\
            --html=performance_results/spike_test.html
        ;;

    endurance)
        echo -e "\n${YELLOW}Running ENDURANCE test (100 users, 30 min)${NC}"
        locust -f locustfile.py MixedWorkloadUser \\
            --host=http://localhost:8000 \\
            --users 100 \\
            --spawn-rate 10 \\
            --run-time 30m \\
            --headless \\
            --csv=performance_results/endurance_test \\
            --html=performance_results/endurance_test.html
        ;;

    ui)
        echo -e "\n${YELLOW}Starting Locust Web UI${NC}"
        echo "Open http://localhost:8089 in your browser"
        locust -f locustfile.py --host=http://localhost:8000
        ;;

    all)
        echo -e "\n${YELLOW}Running ALL performance tests${NC}"

        ./performance_test.sh quick
        echo ""
        ./performance_test.sh moderate
        echo ""
        ./performance_test.sh heavy

        echo -e "\n${GREEN}✅ All tests complete!${NC}"
        echo "Results: performance_results/"
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./performance_test.sh [type]"
        echo ""
        echo "Available types:"
        echo "  quick      - 10 users, 1 minute (default)"
        echo "  moderate   - 100 users, 5 minutes"
        echo "  heavy      - 500 users, 10 minutes"
        echo "  spike      - 1000 users, 2 minutes"
        echo "  endurance  - 100 users, 30 minutes"
        echo "  ui         - Start web UI for manual testing"
        echo "  all        - Run all automated tests"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Performance test completed!${NC}"
echo "Results saved to: performance_results/"
echo ""
echo "View HTML report: open performance_results/${TEST_TYPE}_test.html"
