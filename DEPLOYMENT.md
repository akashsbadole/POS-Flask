# Production Deployment Guide

This guide covers deploying the Restaurant POS system to production using Docker and Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL database server
- Redis server (for caching and sessions)
- SSL certificates (for HTTPS)
- Domain name configured to point to your server

## Quick Start

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd restaurant-pos
```

### 2. Configure Environment Variables
```bash
# Copy and modify the environment configuration
cp config.py.example config.py

# Edit production settings
nano config.py
```

### 3. Deploy with Docker Compose
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Configuration

### Environment Variables
Create a `.env` file with the following variables:

```bash
# Database Configuration
POSTGRES_DB=restaurant_pos
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Flask Configuration
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=your_very_secure_secret_key
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/restaurant_pos
REDIS_URL=redis://localhost:6379/0

# SSL Configuration (if using HTTPS)
SSL_CERT_PATH=/path/to/ssl/cert.pem
SSL_KEY_PATH=/path/to/ssl/key.pem
```

### Database Configuration
For production, use PostgreSQL instead of SQLite:

1. **Create Database:**
   ```sql
   CREATE DATABASE restaurant_pos;
   CREATE USER postgres WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE restaurant_pos TO postgres;
   ```

2. **Update Flask Config:**
   ```python
   # In config.py
   SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:your_secure_password@localhost:5432/restaurant_pos'
   ```

### Nginx Configuration
Create `nginx/nginx.conf` for production:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server web:8000;
    }

    server {
        listen 80;
        listen 443 ssl;
        server_name your-domain.com;
        
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        client_max_body_size 50M;
        
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## Deployment Steps

### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Application Deployment
```bash
# Clone the repository
git clone <your-repo-url>
cd restaurant-pos

# Set up environment
cp config.py.example config.py
nano config.py  # Edit production settings

# Create necessary directories
mkdir -p instance uploads static/uploads

# Set proper permissions
chmod 755 instance uploads
chmod 644 static/uploads

# Build and deploy
docker-compose up -d --build
```

### 3. SSL Certificate Setup
```bash
# Using Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com --email admin@your-domain.com

# Auto-renewal
sudo crontab -e
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### 4. Service Management
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis

# Restart services
docker-compose restart web
docker-compose restart db
docker-compose restart redis

# Scale web application
docker-compose up -d --scale web=3
```

## Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl -f http://localhost:8000/health

# Database health
docker-compose exec db pg_isready -U postgres

# Redis health
docker-compose exec redis redis-cli ping
```

### Backup Strategy
```bash
# Database backup
docker-compose exec db pg_dump -U postgres restaurant_pos > backup_$(date +%Y%m%d_%H%M%S).sql

# Application data backup
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz instance uploads static/uploads

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U postgres restaurant_pos > $BACKUP_DIR/db_$DATE.sql

# Files backup
tar -czf $BACKUP_DIR/files_$DATE.tar.gz instance uploads static/uploads

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql" -o -name "*.tar.gz" -mtime +7 -delete
```

### Log Management
```bash
# Log rotation
sudo nano /etc/logrotate.d/restaurant-pos

# Content:
/path/to/app/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644
    postrotate
        docker-compose restart web
}
```

## Performance Optimization

### Database Optimization
```sql
-- Create indexes for better performance
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_menu_items_category_id ON menu_items(category_id);
CREATE INDEX idx_menu_items_name ON menu_items(name);

-- Analyze query performance
ANALYZE orders;
ANALYZE order_items;
ANALYZE menu_items;
```

### Application Caching
```python
# In config.py
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_DEFAULT_TIMEOUT = 300

# Cache frequently accessed data
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'redis'})

@cache.memoize(timeout=300)
def get_menu_items():
    return MenuItem.query.all()
```

## Security Considerations

### 1. Firewall Configuration
```bash
# Open necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 6379/tcp  # Redis
sudo ufw enable
```

### 2. SSL/TLS
- Use HTTPS in production
- Implement HSTS headers
- Use strong cipher suites
- Regular certificate renewal

### 3. Application Security
```python
# Security headers in Flask
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

## Troubleshooting

### Common Issues and Solutions

1. **Database Connection Errors**
   ```bash
   # Check database connectivity
   docker-compose exec db psql -U postgres -d restaurant_pos -c "SELECT 1;"
   
   # Check network connectivity
   docker network ls
   docker-compose logs db
   ```

2. **Application Not Starting**
   ```bash
   # Check port conflicts
   sudo netstat -tulpn | grep :8000
   
   # Check application logs
   docker-compose logs web
   
   # Verify environment variables
   docker-compose exec web printenv | grep FLASK
   ```

3. **Static Files Not Loading**
   ```bash
   # Check Nginx configuration
   docker-compose exec web ls -la /app/static/
   
   # Check file permissions
   docker-compose exec web ls -la /app/
   
   # Rebuild without cache
   docker-compose build --no-cache web
   ```

4. **Performance Issues**
   ```bash
   # Monitor resource usage
   docker stats
   
   # Check database performance
   docker-compose exec db psql -U postgres -d restaurant_pos -c "SELECT * FROM pg_stat_activity;"
   
   # Optimize database
   docker-compose exec db psql -U postgres -d restaurant_pos -c "VACUUM ANALYZE;"
   ```

## Scaling Considerations

### Horizontal Scaling
```yaml
# docker-compose.yml for multiple web instances
services:
  web:
    build: .
    command: gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 app:app
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Database Scaling
- Use managed database service (AWS RDS, Google Cloud SQL)
- Implement read replicas for reporting
- Use connection pooling

### Load Balancing
```nginx
upstream app {
    server web1:8000;
    server web2:8000;
    server web3:8000;
}

server {
    location / {
        proxy_pass http://app;
        # Load balancing configuration
    }
}
```

## Maintenance and Updates

### Zero-Downtime Deployment
```bash
# Blue-green deployment strategy
docker-compose -f docker-compose.blue.yml up -d
# Test new version
# Switch traffic when ready
docker-compose -f docker-compose.green.yml up -d
# Remove old version
docker-compose -f docker-compose.blue.yml down
```

### Rolling Updates
```bash
# Update one service at a time
docker-compose up -d --no-deps web
# Wait for health check
sleep 30
# Update next service
docker-compose up -d --no-deps db
```

This deployment guide provides a comprehensive approach to deploying the Restaurant POS system in a production environment with proper security, monitoring, and scaling considerations.