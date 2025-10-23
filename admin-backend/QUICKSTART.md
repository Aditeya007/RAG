# Quick Start Guide

Get the Admin Backend API running in 5 minutes.

## Prerequisites

- Node.js 16+ installed
- MongoDB running (local or Atlas)
- Python FastAPI bot running (optional, for bot features)

## Step 1: Install Dependencies

```bash
cd admin-backend
npm install
```

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required - Change these!
NODE_ENV=development
PORT=5000
MONGO_URI=mongodb://localhost:27017/rag-admin
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
CORS_ORIGIN=http://localhost:3000,http://localhost:3001
FASTAPI_BOT_URL=http://localhost:8000
```

**⚠️ IMPORTANT**: Generate a secure JWT secret:
```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

## Step 3: Start Server

```bash
# Development (with auto-reload)
npm run dev

# Production
npm start
```

## Step 4: Verify

Open http://localhost:5000/api/health in your browser. You should see:
```json
{
  "status": "OK",
  "timestamp": "2025-10-23T12:34:56.789Z",
  "service": "admin-backend",
  "mongodb": "connected"
}
```

## Quick Test

### Register a User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "username": "testuser",
    "password": "test123"
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test123"
  }'
```

Save the `token` from the response.

### Get Profile
```bash
curl http://localhost:5000/api/user/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Ask Bot (if FastAPI bot is running)
```bash
curl -X POST http://localhost:5000/api/bot/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"input": "What is AI?"}'
```

## Common Issues

### MongoDB Connection Failed
```
Error: MongoDB URI not found in environment variables!
```
**Fix**: Ensure `MONGO_URI` is set in `.env`

### CORS Error
```
Access blocked by CORS policy
```
**Fix**: Add your frontend URL to `CORS_ORIGIN` in `.env`

### Bot Service Unavailable
```
Bot service is currently unavailable
```
**Fix**: Ensure Python FastAPI bot is running at `FASTAPI_BOT_URL`

## Next Steps

- 📖 Read [README.md](./README.md) for complete documentation
- 🔒 Review [SECURITY.md](./SECURITY.md) before deploying to production
- 🚀 Check [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment options
- 📡 See [API.md](./API.md) for complete API reference

## Production Deployment

**Before deploying to production:**

1. Set `NODE_ENV=production` in `.env`
2. Generate a strong `JWT_SECRET` (64+ random bytes)
3. Use production MongoDB with authentication
4. Set specific `CORS_ORIGIN` domains (NO wildcards!)
5. Enable HTTPS/SSL
6. Review the complete [Security Checklist](./SECURITY.md)

---

**Need Help?** Check the troubleshooting sections in README.md or DEPLOYMENT.md
