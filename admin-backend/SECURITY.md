# Production Security Checklist

This document provides a comprehensive security checklist for deploying the Admin Backend API to production.

## ✅ Critical Security Requirements

### 1. Environment Configuration

- [ ] **NODE_ENV** set to `production`
- [ ] **JWT_SECRET** is a cryptographically strong random string (64+ bytes)
  - Generate: `node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"`
  - Never use example/default values
  - Store securely (e.g., AWS Secrets Manager, Azure Key Vault)
- [ ] **MONGO_URI** uses authentication and encryption
  - Format: `mongodb+srv://username:password@...`
  - Use strong database passwords
  - Enable IP whitelisting
- [ ] **CORS_ORIGIN** contains only specific domains
  - ❌ Never use `*` in production
  - ✅ Use: `https://yourdomain.com,https://admin.yourdomain.com`
- [ ] **FASTAPI_BOT_URL** points to production bot service
  - Use HTTPS in production
  - Verify service is accessible and secured

### 2. Database Security

- [ ] MongoDB authentication enabled
- [ ] Database user has minimal required permissions
  - Create application-specific user
  - Grant only necessary database/collection access
- [ ] Connection string uses SSL/TLS (`ssl=true`)
- [ ] IP whitelist configured (only allow backend servers)
- [ ] Regular automated backups configured
- [ ] Backup restoration tested
- [ ] Database monitoring enabled
- [ ] Connection pooling configured appropriately

### 3. Authentication & Authorization

- [ ] Password hashing uses bcrypt with sufficient salt rounds (10-12)
- [ ] JWT tokens have reasonable expiration (1 day or less)
- [ ] Token algorithm explicitly set to HS256
- [ ] Bearer token format enforced
- [ ] Authentication errors don't leak information
  - Same error for "user not found" and "wrong password"
- [ ] Consider implementing refresh tokens for extended sessions
- [ ] Consider implementing JWT blacklist for logout

### 4. Rate Limiting

- [ ] Rate limiting enabled on all routes
- [ ] Strict limits on authentication endpoints:
  - Login: 5 attempts per 15 minutes
  - Registration: 5 attempts per 15 minutes
- [ ] Moderate limits on bot endpoints (10 per minute)
- [ ] General API rate limit (100 per 15 minutes)
- [ ] Rate limiting persists across server restarts (use Redis for distributed)

### 5. Input Validation & Sanitization

- [ ] All user inputs validated before processing
- [ ] Email format validation
- [ ] Username pattern validation (alphanumeric + underscore)
- [ ] Password strength requirements enforced
- [ ] Input length limits enforced
- [ ] HTML/script injection prevention
- [ ] SQL injection prevention (mongoose handles this)
- [ ] Request body size limits enforced (10mb default)

### 6. Error Handling & Logging

- [ ] Stack traces disabled in production
- [ ] Error messages don't expose internal details
- [ ] Sensitive data not logged (passwords, tokens, PII)
- [ ] Structured logging implemented
- [ ] Log aggregation service configured (e.g., ELK, Splunk)
- [ ] Error monitoring service configured (e.g., Sentry)
- [ ] Audit logs for critical operations (login, data changes)

### 7. HTTPS & Transport Security

- [ ] HTTPS/TLS enabled (SSL certificate installed)
- [ ] HTTP redirects to HTTPS
- [ ] HSTS header enabled (Strict-Transport-Security)
- [ ] Certificate is valid and not expired
- [ ] Certificate auto-renewal configured
- [ ] Strong TLS configuration (TLS 1.2+ only)
- [ ] Secure ciphers only

### 8. Security Headers (Helmet.js)

- [ ] Helmet.js middleware enabled
- [ ] Content-Security-Policy configured
- [ ] X-Content-Type-Options: nosniff
- [ ] X-Frame-Options: DENY or SAMEORIGIN
- [ ] X-XSS-Protection enabled
- [ ] Referrer-Policy configured
- [ ] Permissions-Policy configured

### 9. API Security

- [ ] CORS configured with specific origins only
- [ ] Authentication required on all protected endpoints
- [ ] Authorization checks implemented (if role-based)
- [ ] No sensitive data in URLs/query parameters
- [ ] API versioning implemented (e.g., /api/v1/)
- [ ] Request throttling for expensive operations
- [ ] Pagination for list endpoints

### 10. Dependency Security

- [ ] All dependencies updated to latest stable versions
- [ ] `npm audit` shows no vulnerabilities
  - Run: `npm audit`
  - Fix: `npm audit fix`
- [ ] Automated dependency updates configured (e.g., Dependabot)
- [ ] Regular security patches applied
- [ ] Unused dependencies removed
- [ ] Lock file committed (package-lock.json)

## 🔍 Additional Security Measures

### Infrastructure Security

- [ ] Firewall configured to allow only necessary ports
- [ ] Server OS patched and updated
- [ ] SSH key-based authentication (disable password auth)
- [ ] Fail2ban or similar intrusion prevention
- [ ] DDoS protection enabled (Cloudflare, AWS Shield)
- [ ] Web Application Firewall (WAF) configured

### Monitoring & Alerting

- [ ] Uptime monitoring configured
- [ ] Performance monitoring configured
- [ ] Error rate alerting configured
- [ ] Failed login attempt alerting
- [ ] Unusual traffic pattern alerting
- [ ] Database connection monitoring
- [ ] Disk space monitoring
- [ ] Memory/CPU usage monitoring

### Backup & Recovery

- [ ] Automated database backups configured
- [ ] Backup restoration tested regularly
- [ ] Disaster recovery plan documented
- [ ] Multiple backup locations (geographic redundancy)
- [ ] Point-in-time recovery capability
- [ ] Configuration backups (not just data)

### Compliance & Privacy

- [ ] GDPR compliance (if serving EU users)
  - User data deletion capability
  - Data export capability
  - Privacy policy published
- [ ] CCPA compliance (if serving California users)
- [ ] User consent mechanisms
- [ ] Data retention policies defined and implemented
- [ ] Privacy policy and terms of service published

## 🧪 Security Testing

### Pre-Deployment Testing

- [ ] Authentication flow tested
  - Registration with various inputs
  - Login with correct/incorrect credentials
  - Token expiration handling
  - Logout functionality
- [ ] Authorization tested
  - Accessing protected routes without token
  - Accessing with expired token
  - Accessing with manipulated token
- [ ] Rate limiting tested
  - Exceed limits on auth endpoints
  - Exceed limits on bot endpoints
  - Verify reset after window expires
- [ ] Input validation tested
  - Invalid emails, usernames, passwords
  - Extremely long inputs
  - Special characters and Unicode
  - SQL injection attempts (should fail)
  - XSS attempts (should be sanitized)
- [ ] Error handling tested
  - Database connection failure
  - Bot service unavailable
  - Invalid JSON payloads
  - Missing required fields

### Penetration Testing

- [ ] OWASP Top 10 vulnerabilities checked
- [ ] Automated security scanning (e.g., OWASP ZAP)
- [ ] Manual penetration testing (or hire professionals)
- [ ] Third-party security audit (recommended for production)

## 📋 Deployment Checklist

### Before Deployment

- [ ] All code reviewed and approved
- [ ] All tests passing
- [ ] Security checklist reviewed
- [ ] Environment variables verified
- [ ] SSL certificate installed and verified
- [ ] Database connection tested
- [ ] Bot service connection tested
- [ ] Backup procedures tested
- [ ] Rollback plan documented

### During Deployment

- [ ] Use blue-green or canary deployment
- [ ] Monitor error rates during deployment
- [ ] Monitor response times
- [ ] Verify health endpoint returns OK
- [ ] Test critical user flows (register, login, bot query)

### After Deployment

- [ ] Verify all endpoints accessible
- [ ] Check logs for errors
- [ ] Monitor for 24-48 hours
- [ ] Performance metrics within acceptable range
- [ ] Set up ongoing monitoring alerts

## 🚨 Incident Response

### Preparation

- [ ] Incident response plan documented
- [ ] Contact list for security incidents
- [ ] Escalation procedures defined
- [ ] Communication templates prepared

### Detection

- [ ] Monitoring alerts configured
- [ ] Log analysis procedures defined
- [ ] Anomaly detection enabled

### Response

- [ ] Incident response runbook created
- [ ] Team roles and responsibilities defined
- [ ] Communication plan for users/stakeholders

## 📚 Documentation

- [ ] API documentation up to date
- [ ] Security procedures documented
- [ ] Deployment procedures documented
- [ ] Runbooks for common issues
- [ ] Architecture diagrams current
- [ ] Access control matrix documented

## 🔄 Ongoing Security

### Monthly

- [ ] Review and rotate secrets/credentials
- [ ] Review access logs for suspicious activity
- [ ] Check for dependency updates
- [ ] Review error logs and patterns

### Quarterly

- [ ] Security audit
- [ ] Disaster recovery drill
- [ ] Review and update security policies
- [ ] Access control review

### Annually

- [ ] Comprehensive security assessment
- [ ] Third-party penetration test
- [ ] Compliance audit
- [ ] Update incident response plan

---

## 🛠️ Quick Commands

### Check for vulnerabilities
```bash
npm audit
npm audit fix
```

### Generate secure JWT secret
```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

### Test SSL/TLS configuration
```bash
openssl s_client -connect yourdomain.com:443
```

### Check security headers
```bash
curl -I https://yourdomain.com
```

---

**Remember**: Security is an ongoing process, not a one-time task. Regularly review and update security measures as threats evolve.
