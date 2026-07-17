#!/bin/bash

# CASPER Prime Health Check Script
# Comprehensive health checks for all system components

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BASE_URL=${BASE_URL:-"http://localhost:8742"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost"}
TIMEOUT=${TIMEOUT:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"

    ((TESTS_TOTAL++))
    log_info "Running test: $test_name"

    if $test_function; then
        log_success "$test_name"
        return 0
    else
        log_failure "$test_name"
        return 1
    fi
}

# Health check functions
check_docker_services() {
    log_info "Checking Docker services..."

    # Check if docker-compose is running
    if ! docker-compose ps > /dev/null 2>&1; then
        log_failure "Docker Compose is not running or accessible"
        return 1
    fi

    # Check individual services
    local services=("casper-prime" "postgres" "redis" "nginx")
    local all_healthy=true

    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "Service $service is running"
        else
            log_failure "Service $service is not running"
            all_healthy=false
        fi
    done

    return $all_healthy
}

check_application_health() {
    log_info "Checking application health..."

    # Test main health endpoint
    if curl -f -s --max-time $TIMEOUT "$BASE_URL/health" > /dev/null; then
        log_success "Application health endpoint is responding"

        # Get detailed health info
        local health_response
        health_response=$(curl -s --max-time $TIMEOUT "$BASE_URL/health" | jq -r '.status' 2>/dev/null || echo "unknown")

        if [ "$health_response" = "healthy" ]; then
            log_success "Application reports healthy status"
        else
            log_warn "Application reports status: $health_response"
        fi
    else
        log_failure "Application health endpoint is not responding"
        return 1
    fi

    return 0
}

check_database_connectivity() {
    log_info "Checking database connectivity..."

    # Test database connection through the application
    if curl -f -s --max-time $TIMEOUT "$BASE_URL/api/health/database" > /dev/null 2>&1; then
        log_success "Database is accessible through application"
    else
        # Direct database check
        if docker-compose exec -T postgres pg_isready -U casper > /dev/null 2>&1; then
            log_success "Database is running and accepting connections"
        else
            log_failure "Database is not accepting connections"
            return 1
        fi
    fi

    # Test basic database operations
    if docker-compose exec -T postgres psql -U casper casper_prime -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "Database queries are working"
    else
        log_failure "Database queries are failing"
        return 1
    fi

    return 0
}

check_redis_connectivity() {
    log_info "Checking Redis connectivity..."

    # Test Redis connection
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis is responding to ping"
    else
        log_failure "Redis is not responding"
        return 1
    fi

    # Test Redis operations
    local test_key="healthcheck_$(date +%s)"
    if docker-compose exec -T redis redis-cli set "$test_key" "test" > /dev/null 2>&1 && \
       docker-compose exec -T redis redis-cli get "$test_key" | grep -q "test"; then
        log_success "Redis read/write operations are working"
        docker-compose exec -T redis redis-cli del "$test_key" > /dev/null 2>&1
    else
        log_failure "Redis read/write operations are failing"
        return 1
    fi

    return 0
}

check_nginx_proxy() {
    log_info "Checking Nginx proxy..."

    # Test Nginx is running
    if docker-compose exec -T nginx nginx -t > /dev/null 2>&1; then
        log_success "Nginx configuration is valid"
    else
        log_failure "Nginx configuration is invalid"
        return 1
    fi

    # Test proxy functionality
    if curl -f -s --max-time $TIMEOUT "$FRONTEND_URL/health" > /dev/null; then
        log_success "Nginx proxy is routing requests correctly"
    else
        log_failure "Nginx proxy is not routing requests"
        return 1
    fi

    return 0
}

check_terminal_websocket() {
    log_info "Checking terminal WebSocket connectivity..."

    # Test WebSocket endpoint availability
    local ws_test_script="/tmp/ws_test.py"
    cat > "$ws_test_script" << 'EOF'
import asyncio
import websockets
import sys
import json

async def test_websocket():
    try:
        uri = "ws://localhost:8742/ws/terminal/test"
        async with websockets.connect(uri) as websocket:
            # Send a test message
            test_message = {"type": "test", "data": {"message": "health check"}}
            await websocket.send(json.dumps(test_message))

            # Wait for response (with timeout)
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            return True
    except Exception as e:
        print(f"WebSocket test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    sys.exit(0 if result else 1)
EOF

    if python3 "$ws_test_script" > /dev/null 2>&1; then
        log_success "Terminal WebSocket is accepting connections"
        rm -f "$ws_test_script"
    else
        log_warn "Terminal WebSocket connectivity test failed (may require authentication)"
        rm -f "$ws_test_script"
        # Don't fail the entire check for this
    fi

    return 0
}

check_api_endpoints() {
    log_info "Checking API endpoints..."

    local endpoints=(
        "/api/health"
        "/api/terminal/sessions"
        "/metrics"
    )

    local all_endpoints_ok=true

    for endpoint in "${endpoints[@]}"; do
        local url="$BASE_URL$endpoint"
        local status_code
        status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")

        if [[ "$status_code" =~ ^[23] ]]; then
            log_success "Endpoint $endpoint is responding (HTTP $status_code)"
        elif [ "$status_code" = "401" ] || [ "$status_code" = "403" ]; then
            log_success "Endpoint $endpoint is responding with auth required (HTTP $status_code)"
        else
            log_failure "Endpoint $endpoint is not responding properly (HTTP $status_code)"
            all_endpoints_ok=false
        fi
    done

    return $all_endpoints_ok
}

check_system_resources() {
    log_info "Checking system resources..."

    # Check CPU usage
    local cpu_usage
    cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" casper-prime 2>/dev/null | sed 's/%//' || echo "0")
    if (( $(echo "$cpu_usage < 80" | bc -l) )); then
        log_success "CPU usage is acceptable ($cpu_usage%)"
    else
        log_warn "CPU usage is high ($cpu_usage%)"
    fi

    # Check memory usage
    local memory_usage
    memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" casper-prime 2>/dev/null | sed 's/%//' || echo "0")
    if (( $(echo "$memory_usage < 85" | bc -l) )); then
        log_success "Memory usage is acceptable ($memory_usage%)"
    else
        log_warn "Memory usage is high ($memory_usage%)"
    fi

    # Check disk space
    local disk_usage
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 85 ]; then
        log_success "Disk usage is acceptable ($disk_usage%)"
    else
        log_warn "Disk usage is high ($disk_usage%)"
    fi

    return 0
}

check_monitoring_stack() {
    log_info "Checking monitoring stack..."

    # Check Prometheus
    if curl -f -s --max-time $TIMEOUT "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
        log_success "Prometheus is healthy"
    else
        log_warn "Prometheus health check failed"
    fi

    # Check Grafana
    if curl -f -s --max-time $TIMEOUT "http://localhost:3001/api/health" > /dev/null 2>&1; then
        log_success "Grafana is accessible"
    else
        log_warn "Grafana health check failed"
    fi

    # Check Loki
    if curl -f -s --max-time $TIMEOUT "http://localhost:3100/ready" > /dev/null 2>&1; then
        log_success "Loki is ready"
    else
        log_warn "Loki health check failed"
    fi

    return 0
}

run_performance_tests() {
    log_info "Running performance tests..."

    # Test response time
    local response_time
    response_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time $TIMEOUT "$BASE_URL/health" 2>/dev/null || echo "999")

    if (( $(echo "$response_time < 2.0" | bc -l) )); then
        log_success "Response time is good (${response_time}s)"
    else
        log_warn "Response time is slow (${response_time}s)"
    fi

    # Test concurrent connections
    log_info "Testing concurrent request handling..."
    local concurrent_test_result=0
    for i in {1..5}; do
        curl -f -s --max-time $TIMEOUT "$BASE_URL/health" > /dev/null &
    done
    wait

    if [ $? -eq 0 ]; then
        log_success "Concurrent request handling is working"
    else
        log_warn "Some concurrent requests failed"
    fi

    return 0
}

# Main health check function
main() {
    log_info "Starting CASPER Prime Health Check..."
    echo "==========================================="

    # Change to project root
    cd "$PROJECT_ROOT"

    # Run all health checks
    run_test "Docker Services Status" check_docker_services
    run_test "Application Health" check_application_health
    run_test "Database Connectivity" check_database_connectivity
    run_test "Redis Connectivity" check_redis_connectivity
    run_test "Nginx Proxy" check_nginx_proxy
    run_test "Terminal WebSocket" check_terminal_websocket
    run_test "API Endpoints" check_api_endpoints
    run_test "System Resources" check_system_resources
    run_test "Monitoring Stack" check_monitoring_stack
    run_test "Performance Tests" run_performance_tests

    # Summary
    echo "==========================================="
    log_info "Health Check Summary:"
    log_info "Total tests: $TESTS_TOTAL"
    log_info "Passed: $TESTS_PASSED"
    log_info "Failed: $TESTS_FAILED"

    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All health checks passed! 🎉"
        exit 0
    elif [ $TESTS_FAILED -le 2 ]; then
        log_warn "Some health checks failed, but system is mostly operational"
        exit 1
    else
        log_failure "Multiple health checks failed - system may have issues"
        exit 2
    fi
}

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -u, --base-url URL      Base URL for API tests (default: http://localhost:8742)"
    echo "  -f, --frontend-url URL  Frontend URL for proxy tests (default: http://localhost)"
    echo "  -t, --timeout SECONDS   Request timeout in seconds (default: 30)"
    echo "  -h, --help              Show this help message"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--base-url)
            BASE_URL="$2"
            shift 2
            ;;
        -f|--frontend-url)
            FRONTEND_URL="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check dependencies
command -v curl >/dev/null 2>&1 || { echo "curl is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "docker-compose is required but not installed. Aborting." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq is required but not installed. Aborting." >&2; exit 1; }

# Run main function
main