# CASPER Prime Deployment Guide

## Overview

This comprehensive deployment guide covers production deployment of CASPER Prime, including the terminal UI enhancement system, monitoring stack, and all supporting infrastructure.

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB available space
- Network: Stable internet connection

**Recommended Requirements:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- Network: High-speed internet with low latency

### Software Dependencies

```bash
# Required software
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+
- Python 3.11+ (for development)
- Node.js 18+ (for frontend development)

# Optional but recommended
- nginx (for production proxy)
- certbot (for SSL certificates)
- monitoring tools (htop, iotop, etc.)
```

### Environment Preparation

1. **Update System**:
   ```bash
   sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
   sudo yum update -y                      # CentOS/RHEL
   ```

2. **Install Docker**:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

3. **Install Docker Compose**:
   ```bash
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

## Quick Start Deployment

### 1. Clone Repository

```bash
git clone https://github.com/your-org/casper-prime.git
cd casper-prime
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```env
# API Keys (Required)
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Database Configuration
DATABASE_URL=postgresql://casper:casper@postgres:5432/casper_prime

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=casperredis

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=info
SECRET_KEY=your_secret_key_here

# Monitoring (Optional)
GRAFANA_PASSWORD=your_grafana_password
```

### 3. Deploy Services

```bash
# Deploy with monitoring stack
docker-compose up -d

# Deploy without monitoring (minimal)
docker-compose -f docker-compose.yml up -d casper-prime postgres redis nginx
```

### 4. Verify Deployment

```bash
# Run automated verification
./scripts/verify-deployment.sh

# Check service status
docker-compose ps

# View logs
docker-compose logs -f casper-prime
```

## Production Deployment

### 1. SSL Certificate Setup

**Option A: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chown -R $USER:$USER nginx/ssl/
```

**Option B: Self-Signed Certificate**
```bash
# Generate self-signed certificate
mkdir -p nginx/ssl
openssl req -x509 -newkey rsa:4096 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem -days 365 -nodes -subj "/CN=yourdomain.com"
```

### 2. Production Configuration

**Update docker-compose.yml for production:**
```yaml
# Add to casper-prime service
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
  restart: unless-stopped
```

**Update nginx configuration:**
```bash
# Uncomment HTTPS server block in nginx/nginx.conf
# Update server_name to your domain
```

### 3. Database Optimization

```bash
# Create production database backup directory
mkdir -p backups

# Configure automatic backups
cat > scripts/backup-database.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U casper casper_prime > "$BACKUP_DIR/casper_backup_$TIMESTAMP.sql"
# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "casper_backup_*.sql" -mtime +7 -delete
EOF

chmod +x scripts/backup-database.sh
```

### 4. Monitoring Setup

**Configure Prometheus for production:**
```yaml
# Update monitoring/prometheus.yml
global:
  scrape_interval: 15s
  external_labels:
    cluster: 'casper-production'
    environment: 'production'
```

**Set up log rotation:**
```bash
sudo tee /etc/logrotate.d/casper-prime << 'EOF'
/var/log/casper/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 casper casper
}
EOF
```

## Advanced Configuration

### High Availability Setup

**Load Balancer Configuration:**
```yaml
# docker-compose.ha.yml
version: '3.8'
services:
  casper-prime-1:
    extends:
      file: docker-compose.yml
      service: casper-prime
    container_name: casper-prime-1
    ports: []

  casper-prime-2:
    extends:
      file: docker-compose.yml
      service: casper-prime
    container_name: casper-prime-2
    ports: []

  haproxy:
    image: haproxy:alpine
    ports:
      - "8742:8742"
    volumes:
      - ./haproxy/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - casper-prime-1
      - casper-prime-2
```

### Database Clustering

**PostgreSQL Master-Replica Setup:**
```yaml
postgres-master:
  image: postgres:15-alpine
  environment:
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: replicator_password
  volumes:
    - postgres-master-data:/var/lib/postgresql/data
    - ./postgres/master.conf:/etc/postgresql/postgresql.conf

postgres-replica:
  image: postgres:15-alpine
  environment:
    PGUSER: replicator
    POSTGRES_MASTER_SERVICE: postgres-master
  volumes:
    - postgres-replica-data:/var/lib/postgresql/data
  depends_on:
    - postgres-master
```

### Auto-scaling Configuration

**Docker Swarm Setup:**
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.swarm.yml casper-prime

# Scale services
docker service scale casper-prime_casper-prime=3
```

## Maintenance Procedures

### Regular Maintenance Tasks

**Daily:**
```bash
# Check service health
./scripts/health-check.sh

# Backup database
./scripts/backup-database.sh

# Clean up old logs
docker-compose exec casper-prime find /app/logs -name "*.log" -mtime +7 -delete
```

**Weekly:**
```bash
# Update Docker images (if needed)
docker-compose pull
docker-compose up -d

# Analyze database performance
docker-compose exec postgres psql -U casper casper_prime -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Clean up Docker resources
docker system prune -f
```

**Monthly:**
```bash
# Full system backup
tar -czf casper-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml nginx/ monitoring/ backups/

# Update SSL certificates (if using Let's Encrypt)
sudo certbot renew --quiet

# Security audit
./scripts/security-audit.sh
```

### Upgrade Procedures

**Application Updates:**
```bash
# 1. Backup current state
./scripts/deploy.sh --backup

# 2. Pull latest changes
git pull origin main

# 3. Update containers
docker-compose pull
docker-compose up -d

# 4. Verify deployment
./scripts/verify-deployment.sh

# 5. Run database migrations (if needed)
docker-compose exec casper-prime python -m alembic upgrade head
```

**Database Migrations:**
```bash
# Check current migration status
docker-compose exec casper-prime python -m alembic current

# Run migrations
docker-compose exec casper-prime python -m alembic upgrade head

# Rollback if needed
docker-compose exec casper-prime python -m alembic downgrade -1
```

## Monitoring and Alerting

### Grafana Dashboard Setup

1. **Access Grafana**: http://localhost:3001 (admin/admin)

2. **Import Dashboard**:
   - Navigate to Dashboards → Import
   - Upload `monitoring/grafana/dashboards/casper-terminal.json`
   - Configure data sources

3. **Set up Alerts**:
   - Configure notification channels (email, Slack, etc.)
   - Set alert thresholds based on your requirements

### Log Management

**Centralized Logging with Loki:**
```bash
# Query logs with LogCLI
docker-compose exec loki logcli query '{job="casper-prime"}' --limit=100

# Set up log retention
docker-compose exec loki ls /loki/chunks/
```

**Custom Log Analysis:**
```bash
# Real-time log monitoring
docker-compose logs -f casper-prime | grep ERROR

# Performance analysis
docker-compose logs casper-prime | grep "terminal_command" | tail -100
```

## Security Hardening

### Network Security

**Firewall Configuration:**
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8742/tcp    # API (if direct access needed)
sudo ufw enable
```

**Docker Security:**
```bash
# Run containers as non-root
# Update Dockerfile to use non-root user
USER casper

# Limit container capabilities
docker-compose.yml:
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
```

### Application Security

**Environment Security:**
```bash
# Secure .env file
chmod 600 .env
chown root:root .env

# Use Docker secrets for production
docker secret create anthropic_api_key anthropic_key.txt
docker secret create openai_api_key openai_key.txt
```

**Database Security:**
```sql
-- Create read-only user for monitoring
CREATE USER casper_monitor WITH PASSWORD 'monitor_password';
GRANT CONNECT ON DATABASE casper_prime TO casper_monitor;
GRANT USAGE ON SCHEMA casper TO casper_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA casper TO casper_monitor;
```

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check logs
docker-compose logs casper-prime

# Check port conflicts
netstat -tulpn | grep :8742

# Restart services
docker-compose restart casper-prime
```

**Database Connection Issues:**
```bash
# Test database connectivity
docker-compose exec casper-prime nc -zv postgres 5432

# Check database logs
docker-compose logs postgres

# Reset database connection
docker-compose restart postgres
docker-compose restart casper-prime
```

**Performance Issues:**
```bash
# Check resource usage
docker stats

# Analyze slow queries
docker-compose exec postgres psql -U casper casper_prime -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

# Monitor system resources
htop
iotop
```

For detailed troubleshooting, see [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md).

## Support and Documentation

### Getting Help

- **Documentation**: [docs/](docs/)
- **API Reference**: [docs/TERMINAL_API_REFERENCE.md](docs/TERMINAL_API_REFERENCE.md)
- **User Guide**: [docs/TERMINAL_USER_GUIDE.md](docs/TERMINAL_USER_GUIDE.md)
- **GitHub Issues**: [Repository Issues](https://github.com/your-org/casper-prime/issues)
- **Email Support**: support@casper-prime.ai

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution guidelines.

---

*Last Updated: September 2024*
*Version: 1.0.0*