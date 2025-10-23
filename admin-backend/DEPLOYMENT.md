# Deployment Guide

Complete guide for deploying the Admin Backend API to production environments.

## 📑 Table of Contents

- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [Deployment Methods](#deployment-methods)
- [Post-Deployment](#post-deployment)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### 1. Pre-Deployment Checklist

✅ Complete the [Security Checklist](./SECURITY.md) first!

- [ ] Production MongoDB database ready
- [ ] SSL certificate obtained
- [ ] Domain configured
- [ ] Environment variables prepared
- [ ] FastAPI bot service deployed and accessible

### 2. Install Dependencies

```bash
cd admin-backend
npm ci --only=production
```

### 3. Set Environment Variables

```bash
# Copy and configure .env file
cp .env.example .env

# Edit with production values
nano .env
```

### 4. Test Locally

```bash
# Start server
npm start

# Test health endpoint
curl http://localhost:5000/api/health
```

## ⚙️ Environment Setup

### Production Environment Variables

Create a `.env` file with these production values:

```env
# =============================================================================
# PRODUCTION CONFIGURATION
# =============================================================================

# Server Configuration
NODE_ENV=production
PORT=5000

# Database - MongoDB Atlas (recommended for production)
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/rag-admin?retryWrites=true&w=majority

# Authentication - MUST be changed from example!
# Generate with: node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
JWT_SECRET=<your-64-byte-hex-string-here>
JWT_EXPIRATION=1d
BCRYPT_SALT_ROUNDS=10

# CORS - Specific domains only, NO wildcards!
CORS_ORIGIN=https://yourdomain.com,https://admin.yourdomain.com

# FastAPI Bot Service
FASTAPI_BOT_URL=https://api.yourdomain.com
BOT_REQUEST_TIMEOUT=30000
```

### Securing Environment Variables

#### Option 1: Environment Variables (Recommended)
```bash
# On Linux/Mac
export NODE_ENV=production
export MONGO_URI="mongodb+srv://..."
export JWT_SECRET="your-secret"

# On Windows PowerShell
$env:NODE_ENV="production"
$env:MONGO_URI="mongodb+srv://..."
$env:JWT_SECRET="your-secret"
```

#### Option 2: Cloud Secret Managers

**AWS Secrets Manager:**
```javascript
// Load secrets at startup
const AWS = require('aws-sdk');
const secretsManager = new AWS.SecretsManager();
const secret = await secretsManager.getSecretValue({ SecretId: 'prod/admin-backend' }).promise();
```

**Azure Key Vault:**
```javascript
const { SecretClient } = require("@azure/keyvault-secrets");
const credential = new DefaultAzureCredential();
const client = new SecretClient(vaultUrl, credential);
const secret = await client.getSecret("JWT-SECRET");
```

## 🌐 Deployment Methods

### Method 1: PM2 (Process Manager)

**Best for:** VPS, dedicated servers, bare metal

#### Install PM2
```bash
npm install -g pm2
```

#### Create PM2 Ecosystem File

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'admin-backend',
    script: './server.js',
    instances: 'max', // Use all CPU cores
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 5000
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    max_memory_restart: '500M'
  }]
};
```

#### Deploy with PM2
```bash
# Start application
pm2 start ecosystem.config.js

# Configure auto-start on system reboot
pm2 startup
pm2 save

# Monitor
pm2 monit

# View logs
pm2 logs admin-backend

# Restart
pm2 restart admin-backend

# Stop
pm2 stop admin-backend

# Delete
pm2 delete admin-backend
```

#### PM2 with Nginx Reverse Proxy

**Install Nginx:**
```bash
sudo apt update
sudo apt install nginx
```

**Configure Nginx (`/etc/nginx/sites-available/admin-backend`):**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to Node.js app
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/admin-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Get SSL Certificate (Let's Encrypt):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

### Method 2: Docker

**Best for:** Containerized deployments, cloud platforms

#### Create Dockerfile

```dockerfile
# Use official Node.js LTS image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 && \
    chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node -e "require('http').get('http://localhost:5000/api/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); });"

# Start application
CMD ["node", "server.js"]
```

#### Create .dockerignore

```
node_modules
npm-debug.log
.env
.git
.gitignore
README.md
.DS_Store
logs/
*.log
```

#### Build and Run

```bash
# Build image
docker build -t admin-backend:latest .

# Run container
docker run -d \
  --name admin-backend \
  -p 5000:5000 \
  --env-file .env \
  --restart unless-stopped \
  admin-backend:latest

# View logs
docker logs -f admin-backend

# Stop container
docker stop admin-backend

# Remove container
docker rm admin-backend
```

#### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  admin-backend:
    build: .
    container_name: admin-backend
    ports:
      - "5000:5000"
    environment:
      NODE_ENV: production
      PORT: 5000
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - app-network
    depends_on:
      - mongodb
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:5000/api/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); });"]
      interval: 30s
      timeout: 10s
      retries: 3

  mongodb:
    image: mongo:7
    container_name: mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: secure_password
    volumes:
      - mongodb_data:/data/db
    networks:
      - app-network
    restart: unless-stopped

networks:
  app-network:
    driver: bridge

volumes:
  mongodb_data:
```

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

---

### Method 3: Cloud Platforms

#### Heroku

```bash
# Install Heroku CLI
npm install -g heroku

# Login
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set NODE_ENV=production
heroku config:set MONGO_URI="mongodb+srv://..."
heroku config:set JWT_SECRET="your-secret"
heroku config:set CORS_ORIGIN="https://yourfrontend.com"
heroku config:set FASTAPI_BOT_URL="https://yourbot.com"

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

**Procfile:**
```
web: node server.js
```

#### AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init

# Create environment
eb create admin-backend-prod

# Set environment variables
eb setenv NODE_ENV=production MONGO_URI="..." JWT_SECRET="..."

# Deploy
eb deploy

# Open app
eb open
```

#### Google Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/admin-backend

# Deploy
gcloud run deploy admin-backend \
  --image gcr.io/PROJECT_ID/admin-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars NODE_ENV=production,MONGO_URI=...,JWT_SECRET=...
```

#### Azure App Service

```bash
# Login
az login

# Create resource group
az group create --name admin-backend-rg --location eastus

# Create App Service plan
az appservice plan create \
  --name admin-backend-plan \
  --resource-group admin-backend-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --resource-group admin-backend-rg \
  --plan admin-backend-plan \
  --name admin-backend \
  --runtime "NODE|18-lts"

# Configure app settings
az webapp config appsettings set \
  --resource-group admin-backend-rg \
  --name admin-backend \
  --settings NODE_ENV=production MONGO_URI="..." JWT_SECRET="..."

# Deploy code
az webapp deployment source config-zip \
  --resource-group admin-backend-rg \
  --name admin-backend \
  --src admin-backend.zip
```

---

## ✅ Post-Deployment

### 1. Verify Deployment

```bash
# Health check
curl https://api.yourdomain.com/api/health

# Expected response:
# {"status":"OK","timestamp":"...","service":"admin-backend","mongodb":"connected"}
```

### 2. Test Critical Flows

#### Register User
```bash
curl -X POST https://api.yourdomain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","username":"testuser","password":"test123"}'
```

#### Login
```bash
curl -X POST https://api.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}'
```

#### Bot Query (with token)
```bash
curl -X POST https://api.yourdomain.com/api/bot/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"input":"What is AI?"}'
```

### 3. Monitor Logs

```bash
# PM2
pm2 logs admin-backend

# Docker
docker logs -f admin-backend

# Heroku
heroku logs --tail

# Check for errors
grep "ERROR" logs/*.log
```

### 4. Set Up Monitoring

- Configure uptime monitoring (UptimeRobot, Pingdom)
- Set up error tracking (Sentry, Rollbar)
- Enable performance monitoring (New Relic, DataDog)
- Configure log aggregation (ELK Stack, Splunk)

### 5. Performance Testing

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Load test health endpoint
ab -n 1000 -c 10 https://api.yourdomain.com/api/health

# Load test with auth
ab -n 100 -c 5 -H "Authorization: Bearer TOKEN" \
   -p post_data.json -T application/json \
   https://api.yourdomain.com/api/bot/run
```

## 🔧 Troubleshooting

### Common Issues

#### 1. MongoDB Connection Failed

**Error:**
```
❌ Failed to connect to MongoDB: MongoServerError: bad auth
```

**Solutions:**
- Verify MONGO_URI credentials
- Check MongoDB user permissions
- Verify IP whitelist includes server IP
- Test connection: `mongosh "MONGO_URI"`

#### 2. CORS Errors

**Error:**
```
Access to fetch has been blocked by CORS policy
```

**Solutions:**
- Add frontend origin to CORS_ORIGIN
- Verify no trailing slashes in origins
- Check if frontend uses correct protocol (http vs https)

#### 3. Bot Service Unavailable

**Error:**
```
Bot service is currently unavailable
```

**Solutions:**
- Verify FASTAPI_BOT_URL is correct
- Check if bot service is running
- Test bot service directly: `curl FASTAPI_BOT_URL/health`
- Check network connectivity between services

#### 4. High Memory Usage

**Solutions:**
```bash
# Check memory usage
pm2 show admin-backend

# Set memory limit in ecosystem.config.js
max_memory_restart: '500M'

# Or limit Node.js heap
node --max-old-space-size=512 server.js
```

#### 5. SSL Certificate Issues

**Solutions:**
```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Test SSL configuration
openssl s_client -connect api.yourdomain.com:443
```

### Emergency Procedures

#### Rollback Deployment

**PM2:**
```bash
pm2 stop admin-backend
git checkout previous-version
npm ci
pm2 start admin-backend
```

**Docker:**
```bash
docker stop admin-backend
docker run -d --name admin-backend admin-backend:previous-tag
```

**Heroku:**
```bash
heroku releases
heroku rollback v123
```

#### Scale Resources

**PM2 (increase instances):**
```bash
pm2 scale admin-backend +2
```

**Docker (restart with more memory):**
```bash
docker run -d --memory="1g" --name admin-backend ...
```

---

## 📊 Monitoring Endpoints

- **Health:** `GET /api/health`
- **Root:** `GET /` (API info)

Monitor these regularly for uptime and health checks.

---

## 🔄 Updates & Maintenance

### Regular Updates

```bash
# Pull latest code
git pull origin main

# Install dependencies
npm ci --only=production

# Restart service
pm2 restart admin-backend
```

### Database Migrations

```bash
# Backup before migration
mongodump --uri="MONGO_URI" --out=backup/

# Run migration script
node scripts/migrate.js

# Verify
node scripts/verify-migration.js
```

---

**Need Help?** Refer to [SECURITY.md](./SECURITY.md) for security best practices and [README.md](./README.md) for general documentation.
