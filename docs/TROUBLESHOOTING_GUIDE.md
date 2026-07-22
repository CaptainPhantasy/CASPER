# CASPER Prime Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide covers common issues, diagnostic procedures, and solutions for the CASPER Prime platform, with special focus on the terminal system and deployment scenarios.

## Quick Diagnostic Commands

Before diving into specific issues, run these diagnostic commands to gather system information:

```bash
# Check service status
docker-compose ps

# View logs for all services
docker-compose logs --tail=100

# Check resource usage
docker stats

# Test connectivity
curl -f http://localhost:8742/health
curl -f http://localhost/health
```

## Terminal System Issues

### Terminal Won't Load or Connect

#### Symptoms
- Terminal panel shows "Connecting..." indefinitely
- "Connection failed" error message
- Blank terminal screen with no cursor

#### Diagnostic Steps
1. **Check WebSocket Connection**:
   ```bash
   # Check if WebSocket endpoint is accessible
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:8742/ws/terminal
   ```

2. **Verify Backend Service**:
   ```bash
   # Check if CASPER backend is running
   curl -f http://localhost:8742/health

   # Check backend logs
   docker-compose logs casper-prime
   ```

3. **Check Browser Console**:
   - Open browser developer tools (F12)
   - Look for WebSocket connection errors in Console tab
   - Check Network tab for failed requests

#### Common Solutions

**Solution 1: Backend Service Issues**
```bash
# Restart CASPER backend
docker-compose restart casper-prime

# Check if ports are available
netstat -tulpn | grep :8742
```

**Solution 2: WebSocket Configuration**
- Verify nginx configuration includes WebSocket upgrade headers
- Check if firewall is blocking WebSocket connections
- Ensure proxy settings don't interfere with WebSocket connections

**Solution 3: Browser Issues**
```bash
# Clear browser cache and cookies
# Disable browser extensions that might block WebSockets
# Try incognito/private browsing mode
```

### Commands Not Executing

#### Symptoms
- Commands typed but no output appears
- "Command execution failed" error
- Commands hang indefinitely

#### Diagnostic Steps
1. **Check PTY Manager**:
   ```bash
   # Check backend logs for PTY errors
   docker-compose logs casper-prime | grep -i "pty\|terminal"

   # Verify terminal session creation
   docker-compose exec casper-prime ps aux | grep pty
   ```

2. **Test Command Execution**:
   ```bash
   # Test simple command via API
   curl -X POST http://localhost:8742/api/terminal/execute \
     -H "Content-Type: application/json" \
     -d '{"command": "echo test", "session_id": "test"}'
   ```

3. **Check Security Restrictions**:
   - Review command whitelist configuration
   - Check if commands are being blocked by security policies
   - Verify user permissions

#### Common Solutions

**Solution 1: PTY Manager Reset**
```bash
# Restart terminal service
docker-compose restart casper-prime

# Clear terminal session cache
docker-compose exec casper-prime rm -rf /app/.casper/terminal/*
```

**Solution 2: Permission Issues**
```bash
# Check container user permissions
docker-compose exec casper-prime whoami
docker-compose exec casper-prime ls -la /app

# Fix permissions if needed
docker-compose exec -u root casper-prime chown -R casper:casper /app
```

**Solution 3: Resource Limits**
```bash
# Check system resources
docker stats casper-prime

# Increase memory limits in docker-compose.yml if needed
# restart: unless-stopped
# mem_limit: 1g
# cpu_count: 2
```

### Terminal Performance Issues

#### Symptoms
- Slow terminal response times
- High memory usage
- Terminal freezing or becoming unresponsive

#### Diagnostic Steps
1. **Performance Metrics**:
   ```bash
   # Check resource usage
   docker stats casper-prime --no-stream

   # Monitor terminal-specific metrics
   curl http://localhost:8742/metrics | grep terminal
   ```

2. **Session Analysis**:
   ```bash
   # Check active terminal sessions
   docker-compose exec casper-prime ps aux | grep -E "(pty|terminal)"

   # Monitor database for session information
   docker-compose exec postgres psql -U casper casper_prime -c "SELECT COUNT(*) FROM terminal_sessions WHERE status='active';"
   ```

#### Common Solutions

**Solution 1: Session Cleanup**
```bash
# Clean up orphaned terminal sessions
docker-compose exec casper-prime python -c "
from core.terminal.pty_manager import PTYManager
manager = PTYManager()
manager.cleanup_orphaned_sessions()
"

# Restart with clean state
docker-compose down
docker-compose up -d
```

**Solution 2: Resource Optimization**
```yaml
# Update docker-compose.yml with resource limits
casper-prime:
  # ... existing config
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '1.0'
      reservations:
        memory: 512M
        cpus: '0.5'
```

## Deployment Issues

### Docker Build Failures

#### Symptoms
- "Docker build failed" during deployment
- "No such file or directory" errors
- Package installation failures

#### Diagnostic Steps
1. **Check Build Context**:
   ```bash
   # Verify all required files exist
   ls -la Dockerfile .dockerignore
   ls -la dashboard/package.json pyproject.toml

   # Check build logs
   docker-compose build --no-cache 2>&1 | tee build.log
   ```

2. **Dependency Issues**:
   ```bash
   # Check Poetry lock file
   poetry check

   # Verify npm dependencies
   cd dashboard && npm audit
   ```

#### Common Solutions

**Solution 1: Clean Build Environment**
```bash
# Remove all existing images and containers
docker system prune -af --volumes

# Rebuild from scratch
docker-compose build --no-cache --pull
```

**Solution 2: Fix Dependencies**
```bash
# Update Poetry dependencies
poetry update
poetry lock --no-update

# Update npm dependencies
cd dashboard
npm update
npm audit fix
```

### Database Connection Issues

#### Symptoms
- "Database connection failed" errors
- Migration errors during startup
- "Connection refused" to PostgreSQL

#### Diagnostic Steps
1. **Database Status**:
   ```bash
   # Check PostgreSQL container
   docker-compose ps postgres

   # Test database connection
   docker-compose exec postgres psql -U casper casper_prime -c "\l"

   # Check database logs
   docker-compose logs postgres
   ```

2. **Network Connectivity**:
   ```bash
   # Test network connection from app container
   docker-compose exec casper-prime nc -zv postgres 5432

   # Check Docker network
   docker network ls
   docker network inspect casper-dev_casper-network
   ```

#### Common Solutions

**Solution 1: Database Initialization**
```bash
# Recreate database with fresh data
docker-compose down -v
docker-compose up -d postgres
sleep 10
docker-compose up -d
```

**Solution 2: Connection Configuration**
```bash
# Verify environment variables
docker-compose exec casper-prime env | grep DATABASE_URL

# Update connection string if needed
export DATABASE_URL="postgresql://casper:casper@postgres:5432/casper_prime"
```

### SSL/TLS and HTTPS Issues

#### Symptoms
- "SSL certificate not found" errors
- Mixed content warnings in browser
- HTTPS redirection failures

#### Diagnostic Steps
1. **Certificate Status**:
   ```bash
   # Check SSL certificates
   ls -la nginx/ssl/

   # Verify certificate validity
   openssl x509 -in nginx/ssl/cert.pem -text -noout
   ```

2. **Nginx Configuration**:
   ```bash
   # Test nginx configuration
   docker-compose exec nginx nginx -t

   # Check SSL configuration
   docker-compose logs nginx | grep -i ssl
   ```

#### Common Solutions

**Solution 1: Generate Self-Signed Certificates**
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes -subj "/CN=localhost"

# Update nginx configuration to enable HTTPS
# Uncomment HTTPS server block in nginx/nginx.conf
```

**Solution 2: Use Let's Encrypt**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## Monitoring and Alerting Issues

### Grafana Dashboard Not Loading

#### Symptoms
- Grafana login page not accessible
- Dashboard panels showing "No data"
- Connection errors to Prometheus

#### Diagnostic Steps
1. **Service Status**:
   ```bash
   # Check Grafana service
   docker-compose ps grafana
   docker-compose logs grafana

   # Test Grafana endpoint
   curl -f http://localhost:3001
   ```

2. **Data Source Configuration**:
   ```bash
   # Check Prometheus connectivity from Grafana
   docker-compose exec grafana wget -qO- http://prometheus:9090/api/v1/query?query=up

   # Verify data source configuration
   docker-compose logs grafana | grep -i "datasource"
   ```

#### Common Solutions

**Solution 1: Service Restart**
```bash
# Restart monitoring stack
docker-compose restart prometheus grafana loki

# Check service dependencies
docker-compose up -d --remove-orphans
```

**Solution 2: Configuration Fix**
```bash
# Reset Grafana database
docker-compose down
docker volume rm casper-dev_grafana-data
docker-compose up -d

# Reimport dashboards
# Access http://localhost:3001 (admin/admin)
# Import dashboard from monitoring/grafana/dashboards/casper-terminal.json
```

### Prometheus Metrics Missing

#### Symptoms
- Empty Prometheus targets
- Metrics not being collected
- "Target down" alerts

#### Diagnostic Steps
1. **Target Status**:
   ```bash
   # Check Prometheus targets
   curl http://localhost:9090/api/v1/targets

   # Verify metrics endpoint
   curl http://localhost:8742/metrics
   ```

2. **Configuration Validation**:
   ```bash
   # Validate Prometheus config
   docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

#### Common Solutions

**Solution 1: Metrics Endpoint Fix**
```bash
# Ensure metrics endpoint is implemented in FastAPI app
# Add to core/server.py:
# from prometheus_client import make_wsgi_app
# app.mount("/metrics", make_wsgi_app())

# Restart application
docker-compose restart casper-prime
```

## Performance Optimization

### High Memory Usage

#### Diagnostic Steps
```bash
# Monitor memory usage by service
docker stats --no-stream

# Check for memory leaks
docker-compose exec casper-prime python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
print(f'Available: {psutil.virtual_memory().available / (1024**3):.1f} GB')
"
```

#### Solutions
```bash
# Optimize container memory limits
# Update docker-compose.yml with appropriate limits

# Enable memory monitoring
docker-compose exec casper-prime python -m memory_profiler your_script.py

# Implement graceful degradation
# Configure connection pooling and caching
```

### Database Performance

#### Diagnostic Steps
```bash
# Check database performance
docker-compose exec postgres psql -U casper casper_prime -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
"

# Monitor slow queries
docker-compose exec postgres psql -U casper casper_prime -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

#### Solutions
```bash
# Add database indexes
docker-compose exec postgres psql -U casper casper_prime -c "
CREATE INDEX CONCURRENTLY idx_terminal_sessions_active
ON terminal_sessions(status)
WHERE status = 'active';
"

# Configure connection pooling
# Update DATABASE_URL with connection pooling parameters
```

## Getting Help

### Log Collection for Support

When reporting issues, collect these logs:

```bash
# Collect all service logs
docker-compose logs > casper-logs.txt

# System information
docker-compose ps > services-status.txt
docker stats --no-stream > resource-usage.txt

# Configuration files
tar -czf casper-config.tar.gz docker-compose.yml nginx/ monitoring/ .env

# Database schema
docker-compose exec postgres pg_dump -U casper casper_prime --schema-only > schema.sql
```

### Emergency Recovery

**Complete System Reset**:
```bash
# Stop all services
docker-compose down -v

# Remove all data (WARNING: This deletes all data!)
docker system prune -af --volumes

# Restore from backup
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz
docker-compose up -d
```

**Database Recovery**:
```bash
# Restore database from backup
docker-compose exec -T postgres psql -U casper casper_prime < database_backup.sql

# Verify data integrity
docker-compose exec postgres psql -U casper casper_prime -c "SELECT COUNT(*) FROM users;"
```

### Contact Support

For issues not covered in this guide:

1. **GitHub Issues**: Report bugs and feature requests at [GitHub Repository]
2. **Community Forum**: Get help from the community at [CASPER Forum]
3. **Email Support**: contact support@casper-prime.ai
4. **Emergency Support**: For production issues, use priority support channel

**When contacting support, include**:
- Error messages and logs
- Steps to reproduce the issue
- System configuration details
- Expected vs. actual behavior

---

*Last Updated: September 2024*
*For additional help, visit: https://docs.casper-prime.ai*