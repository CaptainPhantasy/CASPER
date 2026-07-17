#!/bin/bash

# CASPER Prime Deployment Script
# This script handles deployment to production environment

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${ENVIRONMENT:-production}
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -e, --environment ENV    Deployment environment (default: production)"
    echo "  -b, --backup            Create backup before deployment"
    echo "  -s, --skip-tests        Skip running tests before deployment"
    echo "  -f, --force             Force deployment without confirmation"
    echo "  -h, --help              Show this help message"
    exit 1
}

# Parse command line arguments
BACKUP=false
SKIP_TESTS=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -b|--backup)
            BACKUP=true
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Main deployment function
main() {
    log_info "Starting CASPER Prime deployment to $ENVIRONMENT environment..."

    # Change to project root
    cd "$PROJECT_ROOT"

    # Verify environment file exists
    if [[ ! -f .env ]]; then
        log_error "Environment file (.env) not found!"
        exit 1
    fi

    # Load environment variables
    source .env

    # Check required environment variables
    check_environment

    # Pre-deployment checks
    pre_deployment_checks

    # Create backup if requested
    if [[ "$BACKUP" == "true" ]]; then
        create_backup
    fi

    # Run tests unless skipped
    if [[ "$SKIP_TESTS" == "false" ]]; then
        run_tests
    fi

    # Build and deploy
    build_application
    deploy_application

    # Post-deployment verification
    post_deployment_verification

    log_info "Deployment completed successfully!"
}

# Check required environment variables
check_environment() {
    log_info "Checking environment configuration..."

    required_vars=("ANTHROPIC_API_KEY" "OPENAI_API_KEY")
    missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        exit 1
    fi

    log_info "Environment configuration is valid."
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed. Please install it and try again."
        exit 1
    fi

    # Check available disk space (require at least 2GB)
    available_space=$(df . | tail -1 | awk '{print $4}')
    required_space=2097152  # 2GB in KB

    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. At least 2GB required."
        exit 1
    fi

    log_info "Pre-deployment checks passed."
}

# Create backup
create_backup() {
    log_info "Creating backup..."

    mkdir -p "$BACKUP_DIR"

    # Backup database
    if docker-compose ps postgres | grep -q "Up"; then
        log_info "Backing up database..."
        docker-compose exec -T postgres pg_dump -U casper casper_prime > "$BACKUP_DIR/database_backup_$TIMESTAMP.sql"
    fi

    # Backup CASPER data
    if [[ -d ".casper" ]]; then
        log_info "Backing up CASPER data..."
        tar -czf "$BACKUP_DIR/casper_data_backup_$TIMESTAMP.tar.gz" .casper/
    fi

    # Backup configuration
    log_info "Backing up configuration files..."
    tar -czf "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" \
        .env docker-compose.yml nginx/ monitoring/ 2>/dev/null || true

    log_info "Backup created successfully."
}

# Run tests
run_tests() {
    log_info "Running tests..."

    # Backend tests
    log_info "Running backend tests..."
    if ! poetry run pytest tests/ --cov=core --cov-report=term-missing; then
        log_error "Backend tests failed!"
        exit 1
    fi

    # Frontend tests
    log_info "Running frontend tests..."
    cd dashboard
    if ! npm test; then
        log_error "Frontend tests failed!"
        exit 1
    fi
    cd ..

    log_info "All tests passed."
}

# Build application
build_application() {
    log_info "Building application..."

    # Build frontend
    log_info "Building frontend..."
    cd dashboard
    npm ci
    npm run build
    cd ..

    # Build Docker images
    log_info "Building Docker images..."
    docker-compose build --no-cache

    log_info "Application built successfully."
}

# Deploy application
deploy_application() {
    log_info "Deploying application..."

    # Stop existing containers
    docker-compose down

    # Start new containers
    docker-compose up -d

    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 30

    # Check service health
    check_service_health

    log_info "Application deployed successfully."
}

# Check service health
check_service_health() {
    log_info "Checking service health..."

    # Check main application
    if ! curl -f http://localhost:8742/health > /dev/null 2>&1; then
        log_error "Main application health check failed!"
        return 1
    fi

    # Check database
    if ! docker-compose exec -T postgres pg_isready -U casper > /dev/null 2>&1; then
        log_error "Database health check failed!"
        return 1
    fi

    # Check Redis
    if ! docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_error "Redis health check failed!"
        return 1
    fi

    log_info "All services are healthy."
}

# Post-deployment verification
post_deployment_verification() {
    log_info "Running post-deployment verification..."

    # Test API endpoints
    log_info "Testing API endpoints..."

    # Health check
    if ! curl -f http://localhost:8742/health; then
        log_error "API health endpoint failed!"
        exit 1
    fi

    # WebSocket terminal test
    log_info "Testing terminal WebSocket..."
    # Note: This would require a more complex test script

    # Test dashboard accessibility
    log_info "Testing dashboard accessibility..."
    if ! curl -f http://localhost > /dev/null 2>&1; then
        log_error "Dashboard accessibility test failed!"
        exit 1
    fi

    log_info "Post-deployment verification completed."
}

# Cleanup on exit
cleanup() {
    log_info "Cleaning up..."
    # Remove any temporary files or processes if needed
}

trap cleanup EXIT

# Confirmation prompt
if [[ "$FORCE" == "false" ]]; then
    read -p "Deploy to $ENVIRONMENT environment? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled."
        exit 0
    fi
fi

# Run main deployment
main