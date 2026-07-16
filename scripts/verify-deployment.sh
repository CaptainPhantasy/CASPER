#!/bin/bash

# CASPER Prime Deployment Verification Script
# Comprehensive verification of deployment success

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BASE_URL=${BASE_URL:-"http://localhost:8742"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost"}
TIMEOUT=${TIMEOUT:-60}
RETRY_COUNT=${RETRY_COUNT:-5}
RETRY_DELAY=${RETRY_DELAY:-10}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_failure() {
    echo -e "${RED}[FAILURE]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Utility functions
wait_for_service() {
    local service_name="$1"
    local url="$2"
    local max_attempts="$3"

    log_info "Waiting for $service_name to be ready..."

    for i in $(seq 1 "$max_attempts"); do
        if curl -f -s --max-time 10 "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready"
            return 0
        fi

        log_info "Attempt $i/$max_attempts failed, waiting ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
    done

    log_failure "$service_name failed to become ready after $max_attempts attempts"
    return 1
}

test_endpoint() {
    local endpoint="$1"
    local expected_status="$2"
    local description="$3"

    local actual_status
    actual_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$endpoint" 2>/dev/null || echo "000")

    if [ "$actual_status" = "$expected_status" ]; then
        log_success "$description (HTTP $actual_status)"
        return 0
    else
        log_failure "$description (Expected HTTP $expected_status, got HTTP $actual_status)"
        return 1
    fi
}

# Verification functions
verify_infrastructure() {
    log_info "Verifying infrastructure deployment..."

    # Check if all containers are running
    local required_services=("casper-prime" "postgres" "redis" "nginx")
    local all_running=true

    for service in "${required_services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "Container $service is running"
        else
            log_failure "Container $service is not running"
            all_running=false
        fi
    done

    if [ "$all_running" = "false" ]; then
        log_failure "Some required containers are not running"
        return 1
    fi

    # Check container health
    local unhealthy_containers
    unhealthy_containers=$(docker-compose ps --filter "health=unhealthy" --format "{{.Service}}" 2>/dev/null || true)

    if [ -n "$unhealthy_containers" ]; then
        log_failure "Unhealthy containers detected: $unhealthy_containers"
        return 1
    else
        log_success "All containers are healthy"
    fi

    return 0
}

verify_database() {
    log_info "Verifying database deployment..."

    # Wait for database to be ready
    if ! wait_for_service "PostgreSQL" "http://localhost:5432" "$RETRY_COUNT"; then
        return 1
    fi

    # Test database connection
    if docker-compose exec -T postgres pg_isready -U casper -d casper_prime > /dev/null 2>&1; then
        log_success "Database connection is working"
    else
        log_failure "Database connection failed"
        return 1
    fi

    # Verify schema exists
    local table_count
    table_count=$(docker-compose exec -T postgres psql -U casper casper_prime -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'casper';" 2>/dev/null | tr -d '[:space:]' || echo "0")

    if [ "$table_count" -gt 0 ]; then
        log_success "Database schema is deployed ($table_count tables)"
    else
        log_failure "Database schema is missing or empty"
        return 1
    fi

    # Test sample query
    if docker-compose exec -T postgres psql -U casper casper_prime -c "SELECT COUNT(*) FROM casper.users;" > /dev/null 2>&1; then
        log_success "Database queries are working"
    else
        log_failure "Database queries are failing"
        return 1
    fi

    return 0
}

verify_redis() {
    log_info "Verifying Redis deployment..."

    # Test Redis connection
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis connection is working"
    else
        log_failure "Redis connection failed"
        return 1
    fi

    # Test Redis operations
    local test_key="deployment_verification_$(date +%s)"
    local test_value="verification_test"

    if docker-compose exec -T redis redis-cli set "$test_key" "$test_value" > /dev/null 2>&1; then
        local stored_value
        stored_value=$(docker-compose exec -T redis redis-cli get "$test_key" 2>/dev/null | tr -d '\r')

        if [ "$stored_value" = "$test_value" ]; then
            log_success "Redis read/write operations are working"
            docker-compose exec -T redis redis-cli del "$test_key" > /dev/null 2>&1
        else
            log_failure "Redis read operation failed"
            return 1
        fi
    else
        log_failure "Redis write operation failed"
        return 1
    fi

    return 0
}

verify_application() {
    log_info "Verifying application deployment..."

    # Wait for application to be ready
    if ! wait_for_service "CASPER Prime API" "$BASE_URL/health" "$RETRY_COUNT"; then
        return 1
    fi

    # Test API endpoints
    local endpoints=(
        "$BASE_URL/health:200:Application health endpoint"
        "$BASE_URL/api/health:200:API health endpoint"
        "$BASE_URL/metrics:200:Metrics endpoint"
    )

    local all_endpoints_ok=true
    for endpoint_config in "${endpoints[@]}"; do
        IFS=':' read -r url expected_status description <<< "$endpoint_config"
        if ! test_endpoint "$url" "$expected_status" "$description"; then
            all_endpoints_ok=false
        fi
    done

    if [ "$all_endpoints_ok" = "false" ]; then
        return 1
    fi

    # Verify application configuration
    local app_info
    app_info=$(curl -s --max-time "$TIMEOUT" "$BASE_URL/health" 2>/dev/null)

    if echo "$app_info" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        log_success "Application reports healthy status"
    else
        log_failure "Application does not report healthy status"
        return 1
    fi

    return 0
}

verify_nginx() {
    log_info "Verifying Nginx deployment..."

    # Test Nginx configuration
    if docker-compose exec -T nginx nginx -t > /dev/null 2>&1; then
        log_success "Nginx configuration is valid"
    else
        log_failure "Nginx configuration is invalid"
        return 1
    fi

    # Test frontend routing
    if ! wait_for_service "Frontend (via Nginx)" "$FRONTEND_URL" "$RETRY_COUNT"; then
        return 1
    fi

    # Test API proxying
    if test_endpoint "$FRONTEND_URL/api/health" "200" "API proxying through Nginx"; then
        log_success "Nginx is correctly proxying API requests"
    else
        log_failure "Nginx API proxying is not working"
        return 1
    fi

    return 0
}

verify_terminal_system() {
    log_info "Verifying terminal system deployment..."

    # Test terminal API endpoints
    local terminal_endpoints=(
        "$BASE_URL/api/terminal/sessions:401:Terminal sessions endpoint (auth required)"
        "$BASE_URL/ws/terminal:426:WebSocket endpoint (upgrade required)"
    )

    local terminal_ok=true
    for endpoint_config in "${terminal_endpoints[@]}"; do
        IFS=':' read -r url expected_status description <<< "$endpoint_config"

        local actual_status
        actual_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")

        # For WebSocket endpoint, we expect 426 (Upgrade Required) or similar
        if [ "$actual_status" = "$expected_status" ] || [ "$actual_status" = "426" ] || [ "$actual_status" = "400" ]; then
            log_success "$description (HTTP $actual_status)"
        else
            log_failure "$description (Expected HTTP $expected_status, got HTTP $actual_status)"
            terminal_ok=false
        fi
    done

    if [ "$terminal_ok" = "false" ]; then
        return 1
    fi

    # Verify terminal backend is loaded
    if docker-compose exec -T casper-prime python -c "from core.terminal.pty_manager import PTYManager; print('Terminal system loaded')" > /dev/null 2>&1; then
        log_success "Terminal backend system is loaded"
    else
        log_warn "Terminal backend system may not be fully loaded"
    fi

    return 0
}

verify_monitoring() {
    log_info "Verifying monitoring deployment..."

    # Check optional monitoring services
    local monitoring_services=("prometheus" "grafana" "loki")
    local monitoring_ok=true

    for service in "${monitoring_services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up" 2>/dev/null; then
            log_success "Monitoring service $service is running"
        else
            log_warn "Monitoring service $service is not running (optional)"
        fi
    done

    # Test Prometheus if available
    if curl -f -s --max-time 10 "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
        log_success "Prometheus is accessible"

        # Test metrics collection
        local metrics_count
        metrics_count=$(curl -s --max-time 10 "http://localhost:9090/api/v1/label/__name__/values" | jq -r '.data | length' 2>/dev/null || echo "0")

        if [ "$metrics_count" -gt 0 ]; then
            log_success "Prometheus is collecting metrics ($metrics_count metric types)"
        else
            log_warn "Prometheus is not collecting metrics yet"
        fi
    else
        log_warn "Prometheus is not accessible (optional)"
    fi

    # Test Grafana if available
    if curl -f -s --max-time 10 "http://localhost:3001/api/health" > /dev/null 2>&1; then
        log_success "Grafana is accessible"
    else
        log_warn "Grafana is not accessible (optional)"
    fi

    return 0
}

verify_security() {
    log_info "Verifying security configuration..."

    # Check that sensitive endpoints require authentication
    local protected_endpoints=(
        "$BASE_URL/api/terminal/sessions:401:Terminal sessions require auth"
        "$BASE_URL/api/admin:401:Admin endpoints require auth"
    )

    local security_ok=true
    for endpoint_config in "${protected_endpoints[@]}"; do
        IFS=':' read -r url expected_status description <<< "$endpoint_config"

        local actual_status
        actual_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")

        if [ "$actual_status" = "$expected_status" ] || [ "$actual_status" = "403" ]; then
            log_success "$description (HTTP $actual_status)"
        else
            log_warn "$description (Expected HTTP $expected_status, got HTTP $actual_status)"
        fi
    done

    # Check for proper HTTP headers
    local security_headers
    security_headers=$(curl -I -s --max-time 10 "$FRONTEND_URL" 2>/dev/null || true)

    if echo "$security_headers" | grep -qi "x-frame-options"; then
        log_success "Security headers are present"
    else
        log_warn "Some security headers may be missing"
    fi

    return 0
}

run_integration_tests() {
    log_info "Running integration tests..."

    # Test database -> application integration
    local user_count
    user_count=$(curl -s --max-time "$TIMEOUT" "$BASE_URL/api/health" | jq -r '.checks.database.user_count' 2>/dev/null || echo "unknown")

    if [ "$user_count" != "unknown" ] && [ "$user_count" != "null" ]; then
        log_success "Database-Application integration is working"
    else
        log_warn "Database-Application integration status is unclear"
    fi

    # Test load handling
    log_info "Testing concurrent request handling..."
    local concurrent_success=0
    for i in {1..10}; do
        if curl -f -s --max-time 10 "$BASE_URL/health" > /dev/null 2>&1; then
            ((concurrent_success++))
        fi &
    done
    wait

    if [ $concurrent_success -ge 8 ]; then
        log_success "Concurrent request handling is working ($concurrent_success/10 succeeded)"
    else
        log_warn "Concurrent request handling may have issues ($concurrent_success/10 succeeded)"
    fi

    return 0
}

generate_deployment_report() {
    local report_file="$PROJECT_ROOT/deployment-verification-$(date +%Y%m%d_%H%M%S).txt"

    log_info "Generating deployment verification report..."

    {
        echo "CASPER Prime Deployment Verification Report"
        echo "Generated: $(date)"
        echo "=========================================="
        echo ""

        echo "Infrastructure Status:"
        docker-compose ps

        echo ""
        echo "Container Resource Usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

        echo ""
        echo "System Information:"
        echo "- Host OS: $(uname -s)"
        echo "- Host Architecture: $(uname -m)"
        echo "- Docker Version: $(docker --version)"
        echo "- Docker Compose Version: $(docker-compose --version)"

        echo ""
        echo "Network Configuration:"
        docker network ls

        echo ""
        echo "Volume Information:"
        docker volume ls | grep casper

        echo ""
        echo "Application Logs (last 50 lines):"
        docker-compose logs --tail=50 casper-prime

    } > "$report_file"

    log_success "Deployment report saved to: $report_file"
}

# Main verification function
main() {
    log_info "Starting CASPER Prime Deployment Verification..."
    echo "=============================================="

    # Change to project root
    cd "$PROJECT_ROOT"

    local verification_failed=false

    # Run all verification steps
    if ! verify_infrastructure; then
        verification_failed=true
    fi

    if ! verify_database; then
        verification_failed=true
    fi

    if ! verify_redis; then
        verification_failed=true
    fi

    if ! verify_application; then
        verification_failed=true
    fi

    if ! verify_nginx; then
        verification_failed=true
    fi

    if ! verify_terminal_system; then
        verification_failed=true
    fi

    # Optional verifications (don't fail deployment)
    verify_monitoring
    verify_security
    run_integration_tests

    # Generate report
    generate_deployment_report

    echo "=============================================="
    if [ "$verification_failed" = "false" ]; then
        log_success "✅ Deployment verification completed successfully!"
        log_info "CASPER Prime is ready for use."
        log_info "Access the dashboard at: $FRONTEND_URL"
        log_info "API documentation at: $BASE_URL/docs"
        exit 0
    else
        log_failure "❌ Deployment verification failed!"
        log_failure "Please check the issues above and re-run the verification."
        exit 1
    fi
}

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -u, --base-url URL      Base URL for API (default: http://localhost:8742)"
    echo "  -f, --frontend-url URL  Frontend URL (default: http://localhost)"
    echo "  -t, --timeout SECONDS   Request timeout (default: 60)"
    echo "  -r, --retry-count N     Number of retries for service startup (default: 5)"
    echo "  -d, --retry-delay N     Delay between retries in seconds (default: 10)"
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
        -r|--retry-count)
            RETRY_COUNT="$2"
            shift 2
            ;;
        -d|--retry-delay)
            RETRY_DELAY="$2"
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
for cmd in curl docker docker-compose jq; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_failure "$cmd is required but not installed. Aborting."
        exit 1
    fi
done

# Run main function
main